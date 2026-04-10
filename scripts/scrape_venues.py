#!/usr/bin/env python3
"""
scrape_venues.py
----------------
Weekly venue scraper for mojo-shows.json.

Uses requests+BeautifulSoup for simple HTML venues.
Uses Playwright (headless Chromium) for JS-rendered venues (Prekindle, etc.)
so the page fully loads before we extract event data.

Runs every Wednesday via GitHub Actions. Scrapes ALL active venues in one
pass, then records which shows are new since the last run for the banner.

Requires env vars:
    GITHUB_TOKEN  — repo PAT with contents:write scope
    GITHUB_REPO   — owner/repo  (e.g. mojolists/mojolists.github.io)
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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TODAY        = date.today()
END_OF_YEAR  = date(TODAY.year, 12, 31)
NINETY_DAYS  = TODAY + timedelta(days=90)
MAX_DATE     = max(END_OF_YEAR, NINETY_DAYS)
FETCH_DELAY  = 1.0   # seconds between requests (be polite)


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT — lazy-loaded so simple-HTML venues don't pay the import cost
# ─────────────────────────────────────────────────────────────────────────────
_pw_browser = None
_pw_context = None

def get_browser():
    """Return a shared Playwright browser instance (Chromium, headless)."""
    global _pw_browser, _pw_context
    if _pw_browser is None:
        from playwright.sync_api import sync_playwright
        _pw = sync_playwright().start()
        _pw_browser = _pw.chromium.launch(headless=True)
        _pw_context = _pw_browser.new_context(
            user_agent=HEADERS_BASE["User-Agent"],
            viewport={"width": 1280, "height": 900},
        )
    return _pw_browser, _pw_context

def fetch_with_playwright(url, wait_selector=None, wait_ms=3000):
    """
    Load a URL in headless Chromium, wait for JS to render, return HTML.
    wait_selector: CSS selector to wait for before extracting HTML (optional).
    wait_ms: fallback networkidle wait in milliseconds.
    """
    _, ctx = get_browser()
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=8000)
            except Exception:
                pass  # selector didn't appear — still try to parse what we have
        else:
            # Wait for network to go quiet (JS data loads settle)
            try:
                page.wait_for_load_state("networkidle", timeout=wait_ms)
            except Exception:
                pass
        html = page.content()
    finally:
        page.close()
    return html

def close_browser():
    global _pw_browser, _pw_context
    if _pw_browser:
        _pw_browser.close()
        _pw_browser = None
        _pw_context = None


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB API
# ─────────────────────────────────────────────────────────────────────────────
def gh_headers():
    return {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

def load_shows_from_github():
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
# SHOW ID
# ─────────────────────────────────────────────────────────────────────────────
def make_show_id(venue_key, show_date, artist):
    raw = f"{venue_key}|{show_date}|{artist.lower().strip()}"
    return "scraped-" + hashlib.md5(raw.encode()).hexdigest()[:10]


# ─────────────────────────────────────────────────────────────────────────────
# DATE / TIME PARSING
# ─────────────────────────────────────────────────────────────────────────────
MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12
}

def parse_date_string(raw):
    if not raw: return None
    raw = raw.strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m: return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m:
        mon = MONTH_MAP.get(m.group(1)[:3].lower())
        if mon: return date(int(m.group(3)), mon, int(m.group(2)))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", raw)
    if m:
        yr = int(m.group(3))
        if yr < 100: yr += 2000
        return date(yr, int(m.group(1)), int(m.group(2)))
    m = re.match(r"(?:[A-Za-z]+,\s+)?([A-Za-z]+)\s+(\d{1,2})", raw)
    if m:
        mon = MONTH_MAP.get(m.group(1)[:3].lower())
        if mon:
            day = int(m.group(2))
            try:
                d = date(TODAY.year, mon, day)
                if d < TODAY: d = date(TODAY.year+1, mon, day)
                return d
            except ValueError: pass
    return None

def parse_time_string(raw):
    if not raw: return None
    raw = raw.strip().upper()
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", raw)
    if not m: return None
    h = int(m.group(1)); mins = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3)
    if ampm == "PM" and h < 12: h += 12
    elif ampm == "AM" and h == 12: h = 0
    return f"{h:02d}:{mins:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_json_ld(soup, venue):
    """Extract events from JSON-LD <script> blocks — works on many sites."""
    shows = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data   = json.loads(script.string or "")
            events = data if isinstance(data, list) else [data]
            for ev in events:
                if ev.get("@type") not in ("MusicEvent", "Event", "TheaterEvent"): continue
                raw_date = ev.get("startDate", "")
                d = parse_date_string(raw_date[:10])
                if not d or d < TODAY or d > MAX_DATE: continue
                artist = _extract_artist(ev)
                shows.append(_build_show(
                    venue, d, artist,
                    url=ev.get("url",""),
                    time_str=raw_date[11:16] if len(raw_date)>10 else None,
                    price=_extract_price(ev),
                ))
        except Exception:
            continue
    return shows


def parse_inline_json(soup, venue):
    """
    Many JS-heavy sites embed their event data as a JSON blob in a <script> tag,
    e.g.  window.__DATA__ = {...}  or  var events = [...]
    We fish those out and look for date + name fields.
    """
    shows = []
    candidates = []

    for script in soup.find_all("script"):
        text = script.string or ""
        # Look for JSON arrays or objects assigned to a variable
        for m in re.finditer(r'(?:window\.\w+|var \w+|\w+)\s*=\s*(\[{.{50,}?\}]|\{{.{50,}?\}})\s*;', text, re.S):
            try:
                candidates.append(json.loads(m.group(1)))
            except Exception:
                pass

    for obj in candidates:
        items = obj if isinstance(obj, list) else obj.get("events", obj.get("items", []))
        if not isinstance(items, list): continue
        for item in items:
            if not isinstance(item, dict): continue
            # Look for a date field
            raw_date = (item.get("date") or item.get("startDate") or
                        item.get("start_date") or item.get("eventDate") or
                        item.get("start") or "")
            if isinstance(raw_date, dict):
                raw_date = raw_date.get("date") or raw_date.get("local") or ""
            d = parse_date_string(str(raw_date)[:10])
            if not d or d < TODAY or d > MAX_DATE: continue
            # Look for a name/title field
            artist = (item.get("name") or item.get("title") or
                      item.get("headliner") or item.get("artist") or "").strip()
            if not artist: continue
            url = item.get("url") or item.get("link") or ""
            shows.append(_build_show(venue, d, artist, url=url))

    return shows


def parse_prekindle(html, venue):
    """
    Prekindle pages. After JS renders, events appear in the DOM and JSON-LD
    is injected. Try JSON-LD → inline JSON → generic HTML fallback.
    """
    soup = BeautifulSoup(html, "lxml")

    shows = parse_json_ld(soup, venue)
    if shows: return shows

    shows = parse_inline_json(soup, venue)
    if shows: return shows

    return parse_html_generic(html, venue)


def parse_html_generic(html, venue):
    """Generic HTML parser — microdata, then class-name heuristics."""
    soup  = BeautifulSoup(html, "lxml")
    shows = []

    # Try JSON-LD first
    shows = parse_json_ld(soup, venue)
    if shows: return shows

    # Try inline JSON blobs
    shows = parse_inline_json(soup, venue)
    if shows: return shows

    # Microdata
    for ev in soup.find_all(attrs={"itemtype": re.compile(r"schema.org/(Music)?Event")}):
        name_el = ev.find(attrs={"itemprop": "name"})
        date_el = ev.find(attrs={"itemprop": "startDate"})
        if not (name_el and date_el): continue
        raw_date = date_el.get("content") or date_el.get_text()
        d = parse_date_string(raw_date[:10])
        if not d or d < TODAY or d > MAX_DATE: continue
        artist = name_el.get_text(strip=True)
        link   = ev.find("a", href=True)
        url    = _abs(link["href"], venue["url"]) if link else ""
        shows.append(_build_show(venue, d, artist, url=url))
    if shows: return shows

    # Class-name heuristics
    DATE_RE   = re.compile(r"(event|show)[_-]?(date|day|time)", re.I)
    ARTIST_RE = re.compile(r"(event|show|artist)[_-]?(title|name|headline|headliner)", re.I)
    for block in soup.find_all(["article","li","div"],
                                class_=re.compile(r"event|show|gig|listing", re.I)):
        date_el   = block.find(class_=DATE_RE)
        artist_el = block.find(class_=ARTIST_RE)
        if not (date_el and artist_el): continue
        d = parse_date_string(date_el.get_text(strip=True))
        if not d or d < TODAY or d > MAX_DATE: continue
        artist = artist_el.get_text(strip=True)
        if not artist: continue
        link = block.find("a", href=True)
        url  = _abs(link["href"], venue["url"]) if link else ""
        shows.append(_build_show(venue, d, artist, url=url))

    return shows


def parse_eventbrite(html, venue):
    soup = BeautifulSoup(html, "lxml")
    # Try JSON-LD first (Eventbrite injects it)
    shows = parse_json_ld(soup, venue)
    if shows: return shows
    # Fallback: __SERVER_DATA__
    m = re.search(r'__SERVER_DATA__\s*=\s*({.+?})\s*;', html, re.S)
    if not m: return parse_html_generic(html, venue)
    shows = []
    try:
        data   = json.loads(m.group(1))
        events = data.get("search_data",{}).get("events",{}).get("results",[])
        for ev in events:
            raw_date = ev.get("start_date") or ev.get("start",{}).get("local","")
            d = parse_date_string(raw_date[:10])
            if not d or d < TODAY or d > MAX_DATE: continue
            artist = (ev.get("name") or {}).get("text") or ev.get("name","")
            url    = ev.get("url","")
            shows.append(_build_show(venue, d, artist, url=url,
                                     time_str=raw_date[11:16] if len(raw_date)>10 else None))
    except Exception:
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
    p = ev.get("performer") or ev.get("performers")
    if isinstance(p, dict):  return p.get("name", ev.get("name","Unknown"))
    if isinstance(p, list) and p: return p[0].get("name", ev.get("name","Unknown"))
    return ev.get("name","Unknown")

def _extract_price(ev):
    offers = ev.get("offers")
    if not offers: return None
    if isinstance(offers, list): offers = offers[0]
    price = offers.get("price") or offers.get("lowPrice")
    if price:
        cur = offers.get("priceCurrency","USD")
        return f"{'$' if cur=='USD' else cur}{price}"
    return None

def _build_show(venue, d, artist, url="", time_str=None, price=None):
    return {
        "id":      make_show_id(venue["key"], str(d), artist),
        "date":    str(d),
        "time":    parse_time_string(time_str) if time_str else None,
        "artist":  artist.strip(),
        "opener":  None,
        "venue":   venue["name"],
        "region":  venue["region"],
        "city":    venue["city"],
        "price":   price,
        "url":     url,
        "source":  "scraped",
        "addedAt": datetime.utcnow().isoformat() + "Z",
    }

def _abs(path, base):
    from urllib.parse import urljoin
    return urljoin(base, path)


# ─────────────────────────────────────────────────────────────────────────────
# FETCH — chooses requests vs Playwright based on venue config
# ─────────────────────────────────────────────────────────────────────────────
def fetch_html(venue):
    """Return page HTML, using Playwright for JS-rendered venues."""
    if venue.get("js_rendered"):
        print(f"    (headless browser)")
        wait_sel = venue.get("wait_selector")
        html = fetch_with_playwright(venue["url"], wait_selector=wait_sel)
    else:
        res = requests.get(venue["url"], headers=HEADERS_BASE, timeout=20)
        res.raise_for_status()
        html = res.text
    return html


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPE ONE VENUE
# ─────────────────────────────────────────────────────────────────────────────
def scrape_venue(venue):
    print(f"  [{venue['strategy']}{'*' if venue.get('js_rendered') else ''}]  {venue['name']}")
    try:
        html   = fetch_html(venue)
        parser = PARSERS.get(venue["strategy"], parse_html_generic)
        shows  = parser(html, venue)
        print(f"    → {len(shows)} show(s)")
        return shows
    except Exception as e:
        print(f"    ⚠ Failed: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MERGE
# ─────────────────────────────────────────────────────────────────────────────
def merge_all_scraped(existing_shows, fresh_scraped):
    kept = [s for s in existing_shows if s.get("source") != "scraped"]
    kept.extend(fresh_scraped)
    kept = [s for s in kept
            if s.get("date","") >= str(TODAY) and s.get("date","") <= str(MAX_DATE)]
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# NEW SHOWS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
def build_new_shows_summary(old_ids, new_shows):
    new = [s for s in new_shows if s["id"] not in old_ids]
    new.sort(key=lambda s: (s["date"], s.get("time") or ""))
    return [{"id":s["id"],"date":s["date"],"artist":s["artist"],
             "venue":s["venue"],"region":s["region"]} for s in new]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n=== MojoLists Venue Scraper — {TODAY} ===\n")

    with open(VENUES_FILE) as f:
        config = json.load(f)

    active = [v for v in config["venues"] if v.get("active")]
    if not active:
        print("No active venues. Edit scripts/venues.json.")
        return

    js_count = sum(1 for v in active if v.get("js_rendered"))
    print(f"Venues: {len(active)} active  ({js_count} need headless browser)\n")

    shows_data, file_sha = load_shows_from_github()
    if "meta"  not in shows_data: shows_data["meta"]  = {}
    if "shows" not in shows_data: shows_data["shows"] = []

    old_scraped_ids = {s["id"] for s in shows_data["shows"] if s.get("source") == "scraped"}

    all_fresh = []
    errors    = []

    for i, venue in enumerate(active):
        fresh = scrape_venue(venue)
        all_fresh.extend(fresh)
        if not fresh:
            errors.append(venue["name"])
        if i < len(active) - 1 and not venue.get("js_rendered"):
            time.sleep(FETCH_DELAY)

    try:
        close_browser()
    except Exception:
        pass

    print(f"\nTotal scraped: {len(all_fresh)}")
    if errors:
        print(f"⚠ Zero results from: {', '.join(errors)}")

    shows_data["shows"] = merge_all_scraped(shows_data["shows"], all_fresh)
    new_summary = build_new_shows_summary(old_scraped_ids, all_fresh)

    now = datetime.utcnow().isoformat() + "Z"
    shows_data["meta"].update({
        "lastUpdated":       now,
        "lastScraperRun":    now,
        "lastRunNewShows":   new_summary,
        "lastRunVenueCount": len(active),
        "lastRunFoundCount": len(all_fresh),
        "lastRunNewCount":   len(new_summary),
    })
    shows_data["meta"].pop("scraperIndex", None)

    print(f"Total in store: {len(shows_data['shows'])}  |  New this run: {len(new_summary)}")

    commit_msg = (f"chore: weekly scrape — {len(all_fresh)} shows / "
                  f"{len(active)} venues / {len(new_summary)} new [{TODAY}]")
    write_shows_to_github(shows_data, file_sha, commit_msg)
    print("Done.\n")


if __name__ == "__main__":
    main()
