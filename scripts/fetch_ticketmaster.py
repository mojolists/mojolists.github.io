#!/usr/bin/env python3
"""
fetch_ticketmaster.py
---------------------
Monthly Ticketmaster Discovery API pull for mojo-shows.json.

Fetches live music events for:
  • Austin, TX  (city-wide)
  • San Antonio, TX  (city-wide)
  • Mission Ballroom, Denver, CO  (venue ID)
  • Red Rocks Amphitheatre, Morrison, CO  (venue ID)

Run monthly via GitHub Actions on the 1st of each month.

Usage:
    python scripts/fetch_ticketmaster.py

Requires env vars (set as GitHub Actions secrets):
    GITHUB_TOKEN  — repo PAT with contents:write scope
    GITHUB_REPO   — owner/repo  (e.g. mojolists/mojolists.github.io)
    TM_API_KEY    — Ticketmaster Discovery API key (free at developer.ticketmaster.com)
"""

import json
import os
import re
import base64
import hashlib
from datetime import datetime, date, timedelta

import requests


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO", "mojolists/mojolists.github.io")
TM_API_KEY   = os.environ.get("TM_API_KEY", "")
SHOWS_PATH   = "_data/mojo-shows.json"

TODAY        = date.today()
END_OF_YEAR  = date(TODAY.year, 12, 31)
NINETY_DAYS  = TODAY + timedelta(days=90)
MAX_DATE     = max(END_OF_YEAR, NINETY_DAYS)

TM_BASE      = "https://app.ticketmaster.com/discovery/v2"
PAGE_SIZE    = 200   # max per TM page

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH TARGETS
# Cities use city + stateCode; venues use their Ticketmaster venue ID.
# To find a venue ID: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/#search-venues-v2
# ─────────────────────────────────────────────────────────────────────────────
TARGETS = [
    {
        "key":    "austin",
        "label":  "Austin",
        "region": "austin",
        "type":   "city",
        "city":   "Austin",
        "stateCode": "TX",
    },
    {
        "key":    "san-antonio",
        "label":  "San Antonio",
        "region": "san-antonio",
        "type":   "city",
        "city":   "San Antonio",
        "stateCode": "TX",
    },
    {
        "key":    "mission-ballroom",
        "label":  "Mission Ballroom",
        "region": "denver",
        "type":   "venue",
        # Ticketmaster venue ID for Mission Ballroom, Denver
        # Verify at: https://app.ticketmaster.com/discovery/v2/venues.json?apikey=YOUR_KEY&keyword=mission+ballroom&city=Denver
        "venueId": "KovZpZAaFelA",
    },
    {
        "key":    "red-rocks",
        "label":  "Red Rocks Amphitheatre",
        "region": "denver",
        "type":   "venue",
        # Ticketmaster venue ID for Red Rocks
        "venueId": "KovZpZAFnI0A",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB HELPERS  (shared with scrape_venues.py)
# ─────────────────────────────────────────────────────────────────────────────
def gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def load_shows_from_github():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SHOWS_PATH}"
    res = requests.get(url, headers=gh_headers(), timeout=15)
    if res.status_code == 404:
        return {"meta": {}, "shows": []}, None
    res.raise_for_status()
    data    = res.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), data["sha"]


def write_shows_to_github(shows_data, sha, commit_msg):
    url     = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SHOWS_PATH}"
    content = base64.b64encode(
        json.dumps(shows_data, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    body = {"message": commit_msg, "content": content}
    if sha:
        body["sha"] = sha
    res = requests.put(url, headers=gh_headers(), json=body, timeout=15)
    res.raise_for_status()
    print(f"✓ Committed: {commit_msg}")


# ─────────────────────────────────────────────────────────────────────────────
# TICKETMASTER HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def tm_params_base():
    return {
        "apikey":          TM_API_KEY,
        "classificationName": "Music",
        "size":            PAGE_SIZE,
        "startDateTime":   f"{TODAY}T00:00:00Z",
        "endDateTime":     f"{MAX_DATE}T23:59:59Z",
        "sort":            "date,asc",
    }


def fetch_tm_page(params):
    url = f"{TM_BASE}/events.json"
    res = requests.get(url, params=params, timeout=20)
    res.raise_for_status()
    return res.json()


def fetch_all_for_target(target):
    """Fetch all pages of TM results for a city or venue target."""
    params = tm_params_base()

    if target["type"] == "city":
        params["city"]      = target["city"]
        params["stateCode"] = target["stateCode"]
    else:  # venue
        params["venueId"] = target["venueId"]

    all_events = []
    page = 0

    while True:
        params["page"] = page
        try:
            data = fetch_tm_page(params)
        except requests.HTTPError as e:
            print(f"  ⚠ TM API error (page {page}): {e}")
            break

        embedded = data.get("_embedded", {})
        events   = embedded.get("events", [])
        if not events:
            break

        all_events.extend(events)

        # Pagination
        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages", 1)
        if page >= total_pages - 1:
            break
        page += 1

        # Rate limiting — TM allows 5 req/sec on free tier
        import time
        time.sleep(0.25)

    return all_events


# ─────────────────────────────────────────────────────────────────────────────
# PARSE TM EVENT → SHOW DICT
# ─────────────────────────────────────────────────────────────────────────────
def make_show_id_tm(tm_id):
    return f"tm-{tm_id}"


def parse_tm_event(ev, target):
    """Convert a raw TM event object into a mojo-shows entry."""
    try:
        dates    = ev.get("dates", {})
        start    = dates.get("start", {})
        raw_date = start.get("localDate", "")
        raw_time = start.get("localTime", "")

        if not raw_date:
            return None

        show_date = date.fromisoformat(raw_date)
        if show_date < TODAY or show_date > MAX_DATE:
            return None

        # Artist / headliner name
        artist = ev.get("name", "Unknown")

        # Venue name from TM data (more specific than our target label)
        venues_emb  = ev.get("_embedded", {}).get("venues", [])
        venue_name  = venues_emb[0].get("name", target["label"]) if venues_emb else target["label"]

        # Price
        price_ranges = ev.get("priceRanges", [])
        price = None
        if price_ranges:
            lo = price_ranges[0].get("min")
            if lo is not None:
                price = f"${lo:.0f}+"

        # Ticket URL
        url = ev.get("url", "")

        return {
            "id":      make_show_id_tm(ev.get("id", "")),
            "date":    raw_date,
            "time":    raw_time[:5] if raw_time else None,
            "artist":  artist,
            "opener":  None,
            "venue":   venue_name,
            "region":  target["region"],
            "city":    target["label"] if target["type"] == "city" else venues_emb[0].get("city", {}).get("name", "") if venues_emb else "",
            "price":   price,
            "url":     url,
            "source":  "ticketmaster",
            "addedAt": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        print(f"  ⚠ Failed to parse TM event {ev.get('id', '?')}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MERGE — replace all TM shows, preserve scraped + manual
# ─────────────────────────────────────────────────────────────────────────────
def merge_tm_shows(existing_shows, new_tm_shows):
    # Remove stale TM entries
    kept = [s for s in existing_shows if s.get("source") != "ticketmaster"]
    # Add fresh TM data
    kept.extend(new_tm_shows)
    # Prune past / too-far-future entries
    kept = [s for s in kept if s.get("date", "") >= str(TODAY) and s.get("date", "") <= str(MAX_DATE)]
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n=== MojoLists Ticketmaster Pull — {TODAY} ===")

    if not TM_API_KEY:
        print("⚠ TM_API_KEY not set. Add it as a GitHub Actions secret.")
        return

    # Load current data
    shows_data, file_sha = load_shows_from_github()
    if "meta" not in shows_data:
        shows_data["meta"] = {}
    if "shows" not in shows_data:
        shows_data["shows"] = []

    all_new_tm = []

    for target in TARGETS:
        print(f"\nFetching: {target['label']} ({target['type']})…")
        raw_events = fetch_all_for_target(target)
        print(f"  Raw events returned: {len(raw_events)}")

        parsed = [parse_tm_event(ev, target) for ev in raw_events]
        parsed = [p for p in parsed if p]
        print(f"  Parsed + in-window:  {len(parsed)}")
        all_new_tm.extend(parsed)

    print(f"\nTotal new TM shows: {len(all_new_tm)}")

    # Deduplicate TM shows by ID
    seen_ids = set()
    deduped  = []
    for s in all_new_tm:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            deduped.append(s)
    print(f"After dedup: {len(deduped)}")

    # Merge with existing
    shows_data["shows"] = merge_tm_shows(shows_data["shows"], deduped)
    shows_data["meta"]["lastTMPull"]  = datetime.utcnow().isoformat() + "Z"
    shows_data["meta"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    total = len(shows_data["shows"])
    print(f"Total shows in store: {total}")

    commit_msg = f"chore: ticketmaster pull — {len(deduped)} shows [{TODAY}]"
    write_shows_to_github(shows_data, file_sha, commit_msg)
    print("Done.\n")


if __name__ == "__main__":
    main()
