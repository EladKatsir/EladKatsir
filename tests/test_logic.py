"""Offline tests for parsing and filtering.

These don't touch the network. They feed a Yad2-shaped JSON sample through
the parser and check the criteria matching, so the core logic is verified
even where outbound internet is blocked.

Run: python -m tests.test_logic   (or: pytest)
"""

from __future__ import annotations

from beersheva_rentals.models import Listing, SearchCriteria
from beersheva_rentals.sources.yad2 import _find_listing_array, _parse_item


# A trimmed sample shaped like the gw.yad2.co.il rent feed.
SAMPLE = {
    "data": {
        "markers": [
            {
                "token": "abc123",
                "price": 3200,
                "address": {
                    "street": {"text": "רחוב הרצל"},
                    "neighborhood": {"text": "רמות"},
                    "city": {"text": "באר שבע"},
                },
                "additionalDetails": {"roomsCount": 3, "squareMeter": 85},
            },
            {
                "token": "def456",
                "price": 4200,  # over budget -> filtered out
                "additionalDetails": {"roomsCount": 3, "squareMeter": 90},
                "neighborhood": "נווה זאב",
            },
            {
                "token": "ghi789",
                "price": 3000,
                "additionalDetails": {"roomsCount": 3, "squareMeter": 65},  # too small
            },
            {
                "token": "jkl012",
                "price": 2800,
                "additionalDetails": {"roomsCount": 4, "squareMeter": 100},  # too many rooms
            },
        ]
    }
}

CRITERIA = SearchCriteria()  # defaults: 3 rooms, >70 sqm, <=3500


def test_find_array_and_parse():
    items = _find_listing_array(SAMPLE)
    assert len(items) == 4
    first = _parse_item(items[0])
    assert first.listing_id == "abc123"
    assert first.price == 3200
    assert first.rooms == 3
    assert first.size_sqm == 85
    assert "באר שבע" in (first.address or "")
    assert first.url.endswith("abc123")


def test_criteria_matching():
    listings = [_parse_item(it) for it in _find_listing_array(SAMPLE)]
    matches = [l for l in listings if l.matches(CRITERIA)]
    ids = {l.listing_id for l in matches}
    assert ids == {"abc123"}, f"unexpected matches: {ids}"


def test_strict_size_boundary():
    exactly_70 = Listing(source="x", title="t", url="u", price=3000, rooms=3, size_sqm=70)
    assert not exactly_70.matches(CRITERIA), "70 should fail a '>70' rule"
    just_over = Listing(source="x", title="t", url="u", price=3000, rooms=3, size_sqm=70.5)
    assert just_over.matches(CRITERIA)


def test_unknown_price_excluded_by_default():
    no_price = Listing(source="x", title="t", url="u", price=None, rooms=3, size_sqm=80)
    assert not no_price.matches(CRITERIA)
    lenient = SearchCriteria(allow_unknown_price=True)
    assert no_price.matches(lenient)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
