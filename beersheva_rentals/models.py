"""Data models shared across the project.

`Listing` is the normalized shape every source must produce, so the rest
of the program (filtering, printing, saving) never has to care which site a
listing came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class SearchCriteria:
    """What the user is looking for.

    Rooms note: in Israel the living room (salon) counts as a room, so
    "2 bedrooms + a living room" is a 3-room apartment.
    """

    city: str = "Be'er Sheva"
    city_code: int = 9000  # Yad2's internal id for באר שבע
    min_rooms: float = 3.0
    max_rooms: float = 3.0
    min_size_sqm: float = 70.0
    max_price: int = 3500
    # Listings with no price ("call for price") are excluded by default
    # because we can't prove they're under budget.
    allow_unknown_price: bool = False

    def describe(self) -> str:
        return (
            f"{self.city}: {self.min_rooms:g}-{self.max_rooms:g} rooms, "
            f">{self.min_size_sqm:g} sqm, up to {self.max_price} NIS/month"
        )


@dataclass
class Listing:
    """A single rental listing, normalized to a common shape."""

    source: str
    title: str
    url: str
    price: Optional[int] = None          # monthly rent in NIS
    rooms: Optional[float] = None        # total rooms (salon included)
    size_sqm: Optional[float] = None     # floor area in square meters
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    floor: Optional[str] = None
    listing_id: Optional[str] = None
    image: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    def key(self) -> str:
        """Stable identity used for de-duplication across runs/sources."""
        if self.listing_id:
            return f"{self.source}:{self.listing_id}"
        return self.url or f"{self.source}:{self.title}"

    def matches(self, c: SearchCriteria) -> bool:
        """True if this listing satisfies every hard requirement."""
        if self.price is None:
            if not c.allow_unknown_price:
                return False
        elif self.price > c.max_price:
            return False

        if self.rooms is not None and not (c.min_rooms <= self.rooms <= c.max_rooms):
            return False

        # Size strictly greater than the floor ("greater than 70").
        if self.size_sqm is not None and self.size_sqm <= c.min_size_sqm:
            return False

        return True

    def missing_fields(self, c: SearchCriteria) -> list[str]:
        """Criteria we couldn't verify because the source omitted the data.

        Useful to flag "looks good but couldn't confirm size" type results.
        """
        missing = []
        if self.price is None:
            missing.append("price")
        if self.rooms is None:
            missing.append("rooms")
        if self.size_sqm is None:
            missing.append("size")
        return missing

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d

    def one_line(self) -> str:
        bits = []
        bits.append(f"{self.price} NIS" if self.price is not None else "price ?")
        bits.append(f"{self.rooms:g} rooms" if self.rooms is not None else "rooms ?")
        bits.append(f"{self.size_sqm:g} sqm" if self.size_sqm is not None else "size ?")
        where = self.neighborhood or self.address or ""
        meta = " | ".join(bits)
        return f"{meta}  {where}".strip()
