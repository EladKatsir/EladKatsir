"""Facebook source.

Important and deliberate: this source does **not** silently scrape Facebook.

Facebook Marketplace and rental groups require a logged-in session, and
automated scraping violates Facebook's Terms of Service and is aggressively
blocked (and can get your account banned). There is no official public API
for Marketplace listings.

So instead of pretending, this source does the genuinely useful thing: it
builds the exact Marketplace search URL and links to the active Be'er Sheva
rental groups, pre-filtered by your budget where possible, so you can open
them in your already-logged-in browser and skim them in seconds.

If you have explicit authorization and want real automation, the supported
route is a logged-in browser session you drive yourself (e.g. Playwright
with your own cookies) — wire that into `search()` here.
"""

from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from ..models import Listing, SearchCriteria
from .base import Source

# Be'er Sheva Marketplace location id used by Facebook's URL scheme.
_BEERSHEVA_MARKETPLACE_ID = "112237795457493"

# Well-known, active public rental groups for the city. Searching within a
# group needs you to be logged in; these links jump you straight there.
_RENTAL_GROUPS = [
    ("דירות להשכרה בבאר שבע", "https://www.facebook.com/groups/116937065006385"),
    ("שכירות בבאר שבע - ללא תיווך", "https://www.facebook.com/groups/beersheva.rent"),
    ("דירות להשכרה באר שבע והסביבה", "https://www.facebook.com/groups/beersheva.apartments"),
]


class FacebookSource(Source):
    name = "facebook"
    label = "Facebook"

    def search(self, criteria: SearchCriteria) -> List[Listing]:
        # No automated results by design (see module docstring).
        return []

    def search_links(self, criteria: SearchCriteria) -> list[tuple[str, str]]:
        """Return (label, url) pairs to open manually in a logged-in browser."""
        links: list[tuple[str, str]] = []

        # Marketplace: property-rentals category, filtered by max price.
        query = urlencode({
            "minPrice": 0,
            "maxPrice": criteria.max_price,
            "exact": "false",
        })
        marketplace = (
            f"https://www.facebook.com/marketplace/{_BEERSHEVA_MARKETPLACE_ID}"
            f"/propertyrentals?{query}"
        )
        links.append(("Marketplace — Be'er Sheva rentals (≤ budget)", marketplace))

        # A keyword search across Marketplace as a backup.
        kw = urlencode({"query": f"להשכרה באר שבע {criteria.min_rooms:g} חדרים"})
        links.append((
            "Marketplace — keyword search",
            f"https://www.facebook.com/marketplace/{_BEERSHEVA_MARKETPLACE_ID}/search?{kw}",
        ))

        links.extend(_RENTAL_GROUPS)
        return links
