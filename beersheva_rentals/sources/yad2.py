"""Yad2 source — Israel's biggest classifieds site.

Yad2 serves its real-estate results from a JSON gateway API
(gw.yad2.co.il). We query that directly instead of scraping HTML, which is
both more reliable and lighter.

Two practical notes:

* Yad2 sits behind bot protection. From a normal home/office connection
  with the browser-like headers below it usually answers fine; from data
  centers / CI it often returns 403. If you hit 403 repeatedly, run this
  from your own machine or put a proxy in front of it.

* The JSON shape changes every so often, so the parser here is deliberately
  forgiving: it hunts for the listings array and reads each field from a
  list of likely key names rather than assuming one fixed layout.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

import requests

from ..models import Listing, SearchCriteria
from .base import Source

# The gateway endpoint that backs the rent search page.
API_URL = "https://gw.yad2.co.il/realestate-feed/rent/map"
ITEM_URL = "https://www.yad2.co.il/realestate/item/{token}"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.yad2.co.il/realestate/rent",
    "Origin": "https://www.yad2.co.il",
}


def _deep_find_first(obj: Any, keys: tuple[str, ...]) -> Optional[Any]:
    """Return the first value found for any of `keys`, searching nested dicts."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        for v in obj.values():
            found = _deep_find_first(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_first(item, keys)
            if found is not None:
                return found
    return None


def _to_number(value: Any) -> Optional[float]:
    """Pull a number out of ints, floats, or strings like '3,500 ₪'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _find_listing_array(payload: Any) -> List[dict]:
    """Locate the array of listing objects inside the JSON response.

    Tries the known locations first, then falls back to scanning for the
    longest list of dicts that look like listings (have a price-ish field).
    """
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        for path in ("markers", "feed_items"):
            if isinstance(data, dict) and isinstance(data.get(path), list):
                return data[path]
        feed = data.get("feed") if isinstance(data, dict) else None
        if isinstance(feed, dict) and isinstance(feed.get("feed_items"), list):
            return feed["feed_items"]

    # Fallback: deep scan for the best candidate list.
    best: List[dict] = []

    def scan(obj: Any) -> None:
        nonlocal best
        if isinstance(obj, list):
            dicts = [x for x in obj if isinstance(x, dict)]
            looks_like = [
                x for x in dicts
                if any(k in x for k in ("price", "Price", "token", "orderId"))
            ]
            if len(looks_like) > len(best):
                best = looks_like
            for x in obj:
                scan(x)
        elif isinstance(obj, dict):
            for v in obj.values():
                scan(v)

    scan(payload)
    return best


def _parse_item(item: dict) -> Listing:
    token = _deep_find_first(item, ("token", "orderId", "id", "link_token"))
    token = str(token) if token is not None else None

    price = _to_number(_deep_find_first(item, ("price", "Price")))
    rooms = _to_number(
        _deep_find_first(item, ("roomsCount", "rooms", "Rooms_text", "room"))
    )
    size = _to_number(
        _deep_find_first(item, ("squareMeter", "square_meters", "SquareMeter", "size"))
    )

    neighborhood = _deep_find_first(item, ("neighborhood", "neighborhood_text"))
    street = _deep_find_first(item, ("street", "address", "title_1"))
    city = _deep_find_first(item, ("city", "cityText", "title_2"))
    address_parts = [str(p) for p in (street, neighborhood, city) if p]
    address = ", ".join(dict.fromkeys(address_parts)) or None

    floor = _deep_find_first(item, ("floor", "Floor_text"))
    image = _deep_find_first(item, ("image", "img_url", "coverImage"))

    title = address or (f"Yad2 listing {token}" if token else "Yad2 listing")
    url = ITEM_URL.format(token=token) if token else "https://www.yad2.co.il/realestate/rent"

    return Listing(
        source=Yad2Source.name,
        title=title,
        url=url,
        price=int(price) if price is not None else None,
        rooms=rooms,
        size_sqm=size,
        address=address,
        neighborhood=str(neighborhood) if neighborhood else None,
        floor=str(floor) if floor else None,
        listing_id=token,
        image=str(image) if image else None,
        raw=item,
    )


class Yad2Source(Source):
    name = "yad2"
    label = "Yad2"

    def __init__(self, timeout: int = 20, retries: int = 3, session: requests.Session | None = None):
        self.timeout = timeout
        self.retries = retries
        self.session = session or requests.Session()
        self.session.headers.update(BROWSER_HEADERS)

    def _build_params(self, c: SearchCriteria) -> dict:
        params = {
            "city": c.city_code,
            "propertyGroup": "apartments",
            "minPrice": 0,
            "maxPrice": c.max_price,
        }
        # Yad2 filters on whole rooms; mirror the criteria when it makes sense.
        if c.min_rooms:
            params["minRooms"] = c.min_rooms
        if c.max_rooms:
            params["maxRooms"] = c.max_rooms
        if c.min_size_sqm:
            # Server-side floor; we re-check the strict ">" ourselves.
            params["minSquaremeter"] = int(c.min_size_sqm)
        return params

    def search(self, criteria: SearchCriteria) -> List[Listing]:
        params = self._build_params(criteria)
        last_error: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(API_URL, params=params, timeout=self.timeout)
                if resp.status_code == 403:
                    raise PermissionError(
                        "Yad2 returned 403 (bot protection). Try running from a "
                        "residential connection or behind a proxy."
                    )
                resp.raise_for_status()
                payload = resp.json()
                items = _find_listing_array(payload)
                return [_parse_item(it) for it in items]
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                last_error = exc
                if attempt < self.retries:
                    time.sleep(2 ** attempt)  # 2s, 4s, ...

        raise RuntimeError(f"Yad2 search failed after {self.retries} attempts: {last_error}")
