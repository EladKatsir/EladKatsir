"""Listing sources.

Each source knows how to talk to one website and return a list of
normalized `Listing` objects. To add a new site, subclass `Source` and
register it in `ALL_SOURCES`.
"""

from .base import Source
from .yad2 import Yad2Source
from .facebook import FacebookSource

# Order matters only for display.
ALL_SOURCES: dict[str, type[Source]] = {
    Yad2Source.name: Yad2Source,
    FacebookSource.name: FacebookSource,
}

__all__ = ["Source", "Yad2Source", "FacebookSource", "ALL_SOURCES"]
