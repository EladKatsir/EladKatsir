"""Rendering and saving results."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import Listing, SearchCriteria


def print_results(listings: List[Listing], criteria: SearchCriteria) -> None:
    if not listings:
        print("\nNo matching listings found.")
        return

    print(f"\nFound {len(listings)} matching listing(s) for {criteria.describe()}:\n")
    for i, lst in enumerate(listings, 1):
        flags = lst.missing_fields(criteria)
        note = f"  (unconfirmed: {', '.join(flags)})" if flags else ""
        print(f"{i:>2}. [{lst.source}] {lst.one_line()}{note}")
        if lst.title and lst.title not in (lst.address or ""):
            print(f"    {lst.title}")
        print(f"    {lst.url}")
    print()


def print_manual_links(label: str, links: Iterable[tuple[str, str]]) -> None:
    links = list(links)
    if not links:
        return
    print(f"\n{label} — open these in a logged-in browser:")
    for text, url in links:
        print(f"  - {text}\n    {url}")
    print()


def save_json(listings: List[Listing], path: Path) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(listings),
        "listings": [l.to_dict() for l in listings],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(listings: List[Listing], path: Path) -> None:
    fields = [
        "source", "price", "rooms", "size_sqm", "neighborhood",
        "address", "floor", "title", "url",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for lst in listings:
            writer.writerow(lst.to_dict())
