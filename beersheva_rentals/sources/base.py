"""Base class every source inherits from."""

from __future__ import annotations

from typing import List

from ..models import Listing, SearchCriteria


class Source:
    """Abstract source. Subclasses fetch and normalize listings."""

    #: short machine name, e.g. "yad2"
    name: str = "base"
    #: human label for printouts
    label: str = "Base source"

    def search(self, criteria: SearchCriteria) -> List[Listing]:
        """Return listings from this source that roughly match `criteria`.

        Implementations should push as many filters as possible to the
        server (price/rooms/size), but the caller will re-check every
        listing against the criteria anyway, so being approximate is fine.
        """
        raise NotImplementedError
