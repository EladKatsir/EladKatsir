# Be'er Sheva Rental Finder 🏠

Scans rental sources and surfaces apartments in **Be'er Sheva** that match
your criteria. Defaults are tuned to the original request:

- **3 rooms** (2 bedrooms + a living room — in Israel the salon counts as a room)
- **larger than 70 m²**
- **up to 3,500 NIS / month**

## Quick start

```bash
pip install -r requirements.txt          # only needs `requests`
python -m beersheva_rentals               # run with the defaults above
```

Results are printed cheapest-first and saved to `results/listings.json` and
`results/listings.csv`.

## Options

```bash
python -m beersheva_rentals --max-price 3200 --min-size 75
python -m beersheva_rentals --min-rooms 3 --max-rooms 3.5   # allow 3.5-room flats
python -m beersheva_rentals --sources yad2                  # Yad2 only
python -m beersheva_rentals --allow-unknown-price           # keep "call for price" listings
python -m beersheva_rentals --no-save                       # print only
```

Run `python -m beersheva_rentals --help` for the full list.

## How it works

| Source | What it does |
| --- | --- |
| **Yad2** | Queries Yad2's JSON feed API directly, filters server-side by city/price/rooms/size, then re-checks every listing against your exact criteria (including the strict `> 70 m²`). |
| **Facebook** | Does **not** auto-scrape (see below). Instead it prints ready-to-open Marketplace and Be'er Sheva rental-group links, pre-filtered by your budget, for your logged-in browser. |

The code is organized so adding a site is easy: subclass `Source` in
`beersheva_rentals/sources/`, return a list of `Listing` objects, and register
it in `sources/__init__.py`. The shared filtering, de-duplication, printing,
and saving all work automatically.

## A few honest caveats

- **Yad2 bot protection.** Yad2 sits behind anti-bot defenses and often
  returns `403` from data centers / CI / cloud IPs. From a normal home or
  office connection it usually works. If you keep getting 403, run it from
  your own machine or put a proxy in front of it. (For that reason it cannot
  be exercised live inside a sandboxed/no-internet environment.)
- **Facebook is intentionally not scraped.** Marketplace and groups require a
  logged-in session, there is no public listings API, and automated scraping
  violates Facebook's Terms of Service and risks an account ban. The generated
  links get you to the right filtered views in one click instead.
- **Feed shape drift.** Yad2 changes its JSON layout periodically. The parser
  is deliberately forgiving (it hunts for the listings array and reads each
  field from several likely key names), but if Yad2 reworks things you may need
  to tweak `sources/yad2.py`.

## Tests

Offline tests cover parsing and the criteria logic (no network needed):

```bash
python -m tests.test_logic     # or: pytest
```

## Ideas for later

- Add more sources (Madlan, Komo, OnMap, Homeless) as new `Source` subclasses.
- Schedule it (cron / GitHub Actions) and diff against the last run to get
  alerts on *new* matching listings only.
- Wire a logged-in browser session (Playwright) into the Facebook source if
  you have authorization and want real automation there.
```
