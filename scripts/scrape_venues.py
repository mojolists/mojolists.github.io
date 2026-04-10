#!/usr/bin/env python3
"""
scrape_venues.py
----------------
Weekly venue scraper for mojo-shows.json.

Runs every Wednesday via GitHub Actions. Scrapes ALL active venues in one
pass, merges results into the data store, and records which shows are new
since the last run (for the "new shows" notification in the calendar UI).

Usage:
    python scripts/scrape_venues.py

Requires env vars (set as GitHub Actions secrets):
    GITHUB_TOKEN  — repo PAT with contents:write scope
    GITHUB_REPO   — owner/repo  (e.g. mojolists/mojolists.github.io)

Deps (install via requirements.txt):
    requests
    beautifulsoup4
    lxml
"""

import json
import os
import re
import time
import base64
import hashlib
from datetime import datetime, date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
VENUES_FILE  = SCRIPT_DIR / "venues.json"
SHOWS_PATH   = "_data/mojo-shows.json"
REPO         = os.environ.get("GITHUB_REPO", "mojolists/mojolists.github.io")
TOKEN        = os.environ.get("GITHUB_TOKEN", "")

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (compatible; MojoLists-Scraper/1.0; +https://mojolists.github.io)",
    "Accept": "text/html,application/xhtml+xml",
}

# How far ahead to collect shows
TODAY        = date.today()
END_OF_YEAR  = date(TODAY.year, 12, 31)
NINETY_DAYS  = TODAY + timedelta(days=90)
MAX_DATE     = max(END_OF_YEAR, NINETY_DAYS)

# Courtesy delay between venue fetches (seconds)
FETCH_DELAY  = 1.5


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB API HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def gh_headers():
    return {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def load_shows_from_github():
    """Fetch mojo-shows.json from the repo via GitHub Contents API."""
    url = f"https://api.github.com/repos/{REPO}/contents/{SHOWS_PATH}"
    res = requests.get(url, headers=gh_headers(), timeout=15)
    if res.status_code == 404:
        print("mojo-shows.json not found — starting fresh.")
        return {"meta": {}, "shows": []}, None
    res.raise_for_status()
    data    = res.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), data["sha"]


def write_shows_to_github(shows_data, sha, commit_msg):
    """Write updated mojo-shows.json back to the repo."""
    url     = f"https://api.github.com/repos/{REPO}/contents/{SHOWS_PATH}"
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
# SHOW ID GENERATION (deterministic, for deduplication)
# ─────────────────────────────────────────────────────────────────────────────
def make_show_id(venue_key, show_date, artist):
    raw = f"{venue_key}|{show_date}|{artist.lower().strip()}"
    return "scraped-" + hashlib.md5(raw.encode()).hexdigest()[:10]


# ─────────────────────────────────────────────────────────────────────────────
# DATE PARSING UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def parse_date_string(raw):
    """Attempt to parse a variety of date string formats into a date object."""
    if not raw:
        return None
    raw = raw.strip()

    # ISO: 2026-04-15
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Apr 15, 2026  /  April 15, 2026
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m:
        mon = MONTH_MAP.get(m.group(1)[:3].lower())
        if mon:
            return date(int(m.group(3)), mon, int(m.group(2)))

    # 04/15/2026  or  04/15/26
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", raw)
    if m:
        yr = int(m.group(3))
        if yr < 100:
            yr += 2000
        return date(yr, int(m.group(1)), int(m.group(2)))

    # Friday, April 15  (no year — assume current/next)
    m = re.match(r"(?:[A-Za-z]+,\s+)?([A-Za-z]+)\s+(\d{1,2})", raw)
    if m:
        mon = MONTH_MAP.get(m.group(1)[:3].lower())
        if mon:
            day = int(m.group(2))
            try:
                d = date(TODAY.year, mon, day)
                if d < TODAY:
                    d = date(TODAY.year + 1, mon, day)
                return d
            except ValueError:
                pass

    return None


def parse_time_string(raw):
    """Parse a time string into HH:MM (24h). Returns None if unparseable."""
    if not raw:
        return None
    raw = raw.strip().upper()
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", raw)
    if not m:
        return None
    h    = int(m.group(1))
    mins = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3)
    if ampm == "PM" and h < 12:
        h += 12
    elif ampm == "AM" and h == 12:
        h = 0
    return f"{h:02d}:{mins:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_prekindle(html, venue):
    """
    Prekindle-powered pages. Tries JSON-LD first, falls back to generic HTML.
    """
    shows = []
    soup  = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data   = json.loads(script.string or "")
            events = data if isinstance(data, list) else [data]
            for ev in events:
                if ev.get("@type") not in ("MusicEvent", "Event"):
                    continue
                raw_date = ev.get("startDate", "")
                d = parse_date_string(raw_date[:10])
                if not d or d < TODAY or d > MAX_DATE:
                    continue
                artist = _extract_artist(ev)
                url    = ev.get("url", "")
                shows.append({
                    "id":      make_show_id(venue["key"], str(d), artist),
                    "date":    str(d),
                    "time":    parse_time_string(raw_date[11:16]) if len(raw_date) > 10 else None,
                    "artist":  artist,
                    "opener":  None,
                    "venue":   venue["name"],
                    "region":  venue["region"],
                    "city":    venue["city"],
                    "price":   _extract_price(ev),
                    "url":     url,
                    "source":  "scraped",
                    "addedAt": datetime.utcnow().isoformat() + "Z",
                })
        except (json.JSONDecodeError, AttributeError):
            continue

    return shows if shows else parse_html_generic(html, venue)


def parse_html_generic(html, venue):
    """
    Generic HTML parser. Tries microdata first, then common class-name patterns.
    """
    shows = []
    soup  = BeautifulSoup(html, "lxml")

    # Strategy 1: schema.org microdata
    for ev in soup.find_all(attrs={"itemtype": re.compile(r"schema.org/(Music)?Event")}):
        name_el = ev.find(attrs={"itemprop": "name"})
        date_el = ev.find(attrs={"itemprop": "startDate"})
        url_el  = ev.find("a", href=True)
        if not (name_el and date_el):
            continue
        raw_date = date_el.get("content") or date_el.get_text()
        d = parse_date_string(raw_date[:10])
        if not d or d < TODAY or d > MAX_DATE:
            continue
        artist = name_el.get_text(strip=True)
        url    = url_el["href"] if url_el else ""
        if url and not url.startswith("http"):
            url = _make_absolute(url, venue["url"])
        shows.append(_build_show(venue, d, artist, url=url))

    if shows:
        return shows

    # Strategy 2: common class name heuristics
    DATE_CLASSES   = re.compile(r"(event|show)[_-]?(date|day|time)", re.I)
    ARTIST_CLASSES = re.compile(r"(event|show|artist)[_-]?(title|name|headline|headliner)", re.I)

    candidates = soup.find_all(["article", "li", "div"],
                                class_=re.compile(r"event|show|gig|listing", re.I))
    for block in candidates:
        date_el   = block.find(class_=DATE_CLASSES)
        artist_el = block.find(class_=ARTIST_CLASSES)
        if not (date_el and artist_el):
            continue
        d = parse_date_string(date_el.get_text(strip=True))
        if not d or d < TODAY or d > MAX_DATE:
            continue
        artist = artist_el.get_text(strip=True)
        if not artist:
            continue
        link = block.find("a", href=True)
        url  = link["href"] if link else ""
        if url and not url.startswith("http"):
            url = _make_absolute(url, venue["url"])
        shows.append(_build_show(venue, d, artist, url=url))

    return shows


def parse_eventbrite(html, venue):
    """Eventbrite pages embed event JSON in __SERVER_DATA__."""
    m = re.search(r'__SERVER_DATA__\s*=\s*({.+?})\s*;', html, re.S)
    if not m:
        return parse_html_generic(html, venue)

    shows = []
    try:
        data   = json.loads(m.group(1))
        events = (
            data.get("search_data", {}).get("events", {}).get("results", [])
            or data.get("structured_content", {}).get("components", [])
        )
        for ev in events:
            raw_date = ev.get("start_date") or ev.get("start", {}).get("local", "")
            d = parse_date_string(raw_date[:10])
            if not d or d < TODAY or d > MAX_DATE:
                continue
            artist = ev.get("name", {}).get("text") or ev.get("name", "")
            url    = ev.get("url", "")
            shows.append(_build_show(venue, d, artist, url=url,
                                     time_str=raw_date[11:16] if len(raw_date) > 10 else None))
    except (json.JSONDecodeError, AttributeError):
        return parse_html_generic(html, venue)

    return shows


PARSERS = {
    "prekindle":    parse_prekindle,
    "eventbrite":   parse_eventbrite,
    "html_generic": parse_html_generic,
    "ticketweb":    parse_html_generic,
    "custom":       parse_html_generic,
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _extract_artist(ev):
    performer = ev.get("performer") or ev.get("performers")
    if isinstance(performer, dict):
        return performer.get("name", ev.get("name", "Unknown"))
    if isinstance(performer, list) and performer:
        return performer[0].get("name", ev.get("name", "Unknown"))
    return ev.get("name", "Unknown")


def _extract_price(ev):
    offers = ev.get("offers")
    if not offers:
        return None
    if isinstance(offers, list):
        offers = offers[0]
    price    = offers.get("price") or offers.get("lowPrice")
    currency = offers.get("priceCurrency", "USD")
    if price:
        symbol = "$" if currency == "USD" else currency
        return f"{symbol}{price}"
    return None


def _build_show(venue, d, artist, url="", time_str=None):
    return {
        "id":      make_show_id(venue["key"], str(d), artist),
        "date":    str(d),
        "time":    parse_time_string(time_str) if time_str else None,
        "artist":  artist.strip(),
        "opener":  None,
        "venue":   venue["name"],
        "region":  venue["region"],
        "city":    venue["city"],
        "price":   None,
        "url":     url,
        "source":  "scraped",
        "addedAt": datetime.utcnow().isoformat() + "Z",
    }


def _make_absolute(path, base_url):
    from urllib.parse import urljoin
    return urljoin(base_url, path)


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPE ONE VENUE
# ─────────────────────────────────────────────────────────────────────────────
def scrape_venue(venue):
    print(f"  [{venue['strategy']}] {venue['name']}  →  {venue['url']}")
    try:
        res = requests.get(venue["url"], headers=HEADERS_BASE, timeout=20)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"    ⚠ Fetch failed: {e}")
        return []

    parser = PARSERS.get(venue["strategy"], parse_html_generic)
    shows  = parser(res.text, venue)
    print(f"    → {len(shows)} show(s) in window")
    return shows


# ─────────────────────────────────────────────────────────────────────────────
# MERGE — replace all scraped shows with fresh data, preserve manual + TM
# ─────────────────────────────────────────────────────────────────────────────
def merge_all_scraped(existing_shows, fresh_scraped_shows):
    """
    Drop all old scraped shows and replace with the fresh batch.
    Manual and Ticketmaster entries are preserved unchanged.
    Also prunes shows that have passed or exceed the max date.
    """
    kept = [s for s in existing_shows if s.get("source") != "scraped"]
    kept.extend(fresh_scraped_shows)
    kept = [s for s in kept
            if s.get("date", "") >= str(TODAY) and s.get("date", "") <= str(MAX_DATE)]
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# NEW SHOWS SUMMARY — for the calendar notification banner
# ─────────────────────────────────────────────────────────────────────────────
def build_new_shows_summary(old_show_ids, new_shows):
    """
    Returns a list of slim dicts for shows that weren't in the previous data,
    sorted by date. These get stored in meta.lastRunNewShows for the UI.
    """
    new = [s for s in new_shows if s["id"] not in old_show_ids]
    new.sort(key=lambda s: (s["date"], s.get("time") or ""))
    return [
        {
            "id":     s["id"],
            "date":   s["date"],
            "artist": s["artist"],
            "venue":  s["venue"],
            "region": s["region"],
        }
        for s in new
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n=== MojoLists Venue Scraper — {TODAY} ===\n")

    with open(VENUES_FILE) as f:
        config = json.load(f)

    active_venues = [v for v in config["venues"] if v.get("active")]
    if not active_venues:
        print("No active venues configured. Edit scripts/venues.json to add venues.")
        return

    print(f"Scraping {len(active_venues)} active venue(s)…\n")

    # Load current data from GitHub
    shows_data, file_sha = load_shows_from_github()
    if "meta"  not in shows_data: shows_data["meta"]  = {}
    if "shows" not in shows_data: shows_data["shows"] = []

    # Snapshot existing scraped IDs for new-shows diff
    old_scraped_ids = {s["id"] for s in shows_data["shows"] if s.get("source") == "scraped"}

    # ── Scrape all venues ────────────────────────────────────────────────────
    all_fresh = []
    errors    = []

    for i, venue in enumerate(active_venues):
        fresh = scrape_venue(venue)
        all_fresh.extend(fresh)
        if not fresh:
            errors.append(venue["name"])
        if i < len(active_venues) - 1:
            time.sleep(FETCH_DELAY)   # be polite

    print(f"\nTotal scraped shows in window: {len(all_fresh)}")
    if errors:
        print(f"⚠ No results from: {', '.join(errors)} (scraper may need tuning)")

    # ── Merge into data store ────────────────────────────────────────────────
    shows_data["shows"] = merge_all_scraped(shows_data["shows"], all_fresh)

    # ── Compute new-shows summary ────────────────────────────────────────────
    new_summary = build_new_shows_summary(old_scraped_ids, all_fresh)
    print(f"New shows since last run: {len(new_summary)}")

    # ── Update metadata ──────────────────────────────────────────────────────
    now = datetime.utcnow().isoformat() + "Z"
    shows_data["meta"].update({
        "lastUpdated":      now,
        "lastScraperRun":   now,
        "lastRunNewShows":  new_summary,    # consumed by calendar UI for banner
        "lastRunVenueCount": len(active_venues),
        "lastRunFoundCount": len(all_fresh),
        "lastRunNewCount":   len(new_summary),
    })
    # Remove legacy rotation key if present
    shows_data["meta"].pop("scraperIndex", None)

    total = len(shows_data["shows"])
    print(f"Total shows in store: {total}")

    # ── Write back ───────────────────────────────────────────────────────────
    commit_msg = (
        f"chore: weekly scrape — {len(all_fresh)} shows across "
        f"{len(active_venues)} venues, {len(new_summary)} new [{TODAY}]"
    )
    write_shows_to_github(shows_data, file_sha, commit_msg)
    print("Done.\n")


if __name__ == "__main__":
    main()
