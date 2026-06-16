"""Command-line entry point.

Run it:

    python -m beersheva_rentals                 # use defaults
    python -m beersheva_rentals --max-price 3200 --min-size 75
    python -m beersheva_rentals --sources yad2  # skip Facebook link output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .models import Listing, SearchCriteria
from .output import print_manual_links, print_results, save_csv, save_json
from .sources import ALL_SOURCES, FacebookSource


def build_criteria(args: argparse.Namespace) -> SearchCriteria:
    return SearchCriteria(
        min_rooms=args.min_rooms,
        max_rooms=args.max_rooms,
        min_size_sqm=args.min_size,
        max_price=args.max_price,
        allow_unknown_price=args.allow_unknown_price,
    )


def dedupe(listings: List[Listing]) -> List[Listing]:
    seen: set[str] = set()
    out: List[Listing] = []
    for lst in listings:
        k = lst.key()
        if k not in seen:
            seen.add(k)
            out.append(lst)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="beersheva_rentals",
        description="Find Be'er Sheva apartments for rent matching your criteria.",
    )
    p.add_argument("--max-price", type=int, default=3500, help="max monthly rent in NIS (default 3500)")
    p.add_argument("--min-rooms", type=float, default=3.0, help="min rooms incl. living room (default 3)")
    p.add_argument("--max-rooms", type=float, default=3.0, help="max rooms incl. living room (default 3)")
    p.add_argument("--min-size", type=float, default=70.0, help="size must be greater than this (sqm, default 70)")
    p.add_argument(
        "--sources",
        nargs="+",
        choices=list(ALL_SOURCES),
        default=list(ALL_SOURCES),
        help="which sources to query (default: all)",
    )
    p.add_argument(
        "--allow-unknown-price",
        action="store_true",
        help="keep listings whose price the source didn't report",
    )
    p.add_argument("--out-dir", type=Path, default=Path("results"), help="where to save json/csv")
    p.add_argument("--no-save", action="store_true", help="don't write result files")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    criteria = build_criteria(args)

    print(f"Searching for: {criteria.describe()}")
    print(f"Sources: {', '.join(args.sources)}")

    all_matches: List[Listing] = []
    for name in args.sources:
        source = ALL_SOURCES[name]()
        try:
            found = source.search(criteria)
        except Exception as exc:  # noqa: BLE001 - keep going if one source fails
            print(f"  ! {source.label}: {exc}", file=sys.stderr)
            found = []

        matches = [l for l in found if l.matches(criteria)]
        if found or matches:
            print(f"  {source.label}: {len(found)} fetched, {len(matches)} match")
        all_matches.extend(matches)

        # Facebook can't be auto-scraped; show the manual links instead.
        if isinstance(source, FacebookSource):
            print_manual_links(source.label, source.search_links(criteria))

    all_matches = dedupe(all_matches)
    # Cheapest first; unknown prices last.
    all_matches.sort(key=lambda l: (l.price is None, l.price or 0))

    print_results(all_matches, criteria)

    if all_matches and not args.no_save:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        save_json(all_matches, args.out_dir / "listings.json")
        save_csv(all_matches, args.out_dir / "listings.csv")
        print(f"Saved {len(all_matches)} listing(s) to {args.out_dir}/listings.json and listings.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
