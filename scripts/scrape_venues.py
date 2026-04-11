#!/usr/bin/env python3
"""
scrape_venues.py
----------------
Weekly venue scraper for mojo-shows.json.

Each venue uses a targeted strategy based on its actual tech stack:
  mec_wp_api   — WordPress + Modern Events Calendar plugin (Parish)
                 Calls the WP REST API directly — no browser needed.
  tw_js        — WordPress + TicketWeb plugin (Antone's)
                 Playwright renders page, then reads EventData.events via JS eval.
  nextjs_js    — Next.js app (Emo's)
                 Playwright renders page, reads __NEXT_DATA__ via JS eval.
  html_generic — Simple HTML sites (Continental Club)
                 requests + BeautifulSoup, JSON-LD / microdata / class heuristics.

Requires env vars:
    GITHUB_TOKEN  — repo PAT with contents:write scope
    GITHUB_REPO   — e.g. mojolists/mojolists.github.io
    DIAGNOSE      — set to "true" to enable verbose HTML diagnostics
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
SCRIPT_DIR  = Path(__file__).parent
VENUES_FILE = SCRIPT_DIR / "venues.json"
SHOWS_PATH  = "_data/mojo-shows.json"
REPO        = os.environ.get("GITHUB_REPO", "mojolists/mojolists.github.io")
TOKEN       = os.environ.get("GITHUB_TOKEN", "")
DIAGNOSE    = os.environ.get("DIAGNOSE", "").lower() in ("1", "true", "yes")

HEADERS     = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

TODAY       = date.today()
END_OF_YEAR = date(TODAY.year, 12, 31)
MAX_DATE    = max(END_OF_YEAR, TODAY + timedelta(days=90))
FETCH_DELAY = 1.2


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT — shared browser instance, lazy-initialised
# ─────────────────────────────────────────────────────────────────────────────
_pw_instance = None
_pw_browser  = None
_pw_context  = None

def _get_pw_context():
    global _pw_instance, _pw_browser, _pw_context
    if _pw_browser is None:
        from playwright.sync_api import sync_playwright
        _pw_instance = sync_playwright().start()
        _pw_browser  = _pw_instance.chromium.launch(headless=True)
        _pw_context  = _pw_browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 900},
        )
    return _pw_context

def _close_pw():
    global _pw_instance, _pw_browser, _pw_context
    if _pw_browser:
        try: _pw_browser.close()
        except: pass
        try: _pw_instance.stop()
        except: pass
    _pw_browser = _pw_context = _pw_instance = None

def playwright_get(url, wait_selector=None, wait_ms=10000, js_eval=None):
    """
    Load url in headless Chrome. Returns (html, js_result).
    wait_selector: CSS selector to wait for (up to 12s).
    js_eval: JavaScript expression to evaluate after load — result is returned.
    """
    ctx  = _get_pw_context()
    page = ctx.new_page()
    js_result = None
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=12000)
            except Exception:
                pass   # selector didn't appear — carry on and parse what we have
        # Always let the network settle
        try:
            page.wait_for_load_state("networkidle", timeout=wait_ms)
        except Exception:
            pass
        if js_eval:
            try:
                js_result = page.evaluate(js_eval)
            except Exception:
                pass
        html = page.content()
    finally:
        page.close()
    return html, js_result


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB API
# ─────────────────────────────────────────────────────────────────────────────
def _gh_headers():
    return {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

def load_shows():
    url = f"https://api.github.com/repos/{REPO}/contents/{SHOWS_PATH}"
    r   = requests.get(url, headers=_gh_headers(), timeout=15)
    if r.status_code == 404:
        return {"meta": {}, "shows": []}, None
    r.raise_for_status()
    d = r.json()
    return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]

def save_shows(data, sha, msg):
    url     = f"https://api.github.com/repos/{REPO}/contents/{SHOWS_PATH}"
    content = base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()
    body    = {"message": msg, "content": content}
    if sha: body["sha"] = sha
    r = requests.put(url, headers=_gh_headers(), json=body, timeout=15)
    r.raise_for_status()
    print(f"✓ {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# SHOW ID + DATE PARSING
# ─────────────────────────────────────────────────────────────────────────────
def show_id(venue_key, d, artist):
    raw = f"{venue_key}|{d}|{artist.lower().strip()}"
    return "scraped-" + hashlib.md5(raw.encode()).hexdigest()[:10]

MONTHS = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
           "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}

def parse_date(raw):
    if not raw: return None
    raw = str(raw).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m: return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", raw)
    if m:
        mon = MONTHS.get(m[1][:3].lower())
        if mon: return date(int(m[3]), mon, int(m[2]))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", raw)
    if m:
        yr = int(m[3]); yr = yr+2000 if yr<100 else yr
        return date(yr, int(m[1]), int(m[2]))
    m = re.match(r"(?:[A-Za-z]+,\s+)?([A-Za-z]+)\s+(\d{1,2})\b", raw)
    if m:
        mon = MONTHS.get(m[1][:3].lower())
        if mon:
            try:
                d = date(TODAY.year, mon, int(m[2]))
                return d if d >= TODAY else date(TODAY.year+1, mon, int(m[2]))
            except ValueError: pass
    return None

def parse_time(raw):
    if not raw: return None
    raw = str(raw).strip().upper()
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?", raw)
    if not m: return None
    h = int(m[1]); mins = int(m[2]) if m[2] else 0
    if m[3]=="PM" and h<12: h+=12
    elif m[3]=="AM" and h==12: h=0
    return f"{h:02d}:{mins:02d}"

def in_window(d):
    return d and TODAY <= d <= MAX_DATE

def build_show(venue, d, artist, url="", time_str=None, price=None, opener=None):
    return {
        "id":      show_id(venue["key"], str(d), artist),
        "date":    str(d),
        "time":    parse_time(time_str),
        "artist":  artist.strip(),
        "opener":  opener,
        "venue":   venue["name"],
        "region":  venue["region"],
        "city":    venue["city"],
        "price":   price,
        "url":     url,
        "source":  "scraped",
        "addedAt": datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY: mec_wp_api
# WordPress + Modern Events Calendar plugin (Parish)
# Calls WP REST API directly — much more reliable than scraping AJAX HTML.
# ─────────────────────────────────────────────────────────────────────────────
def strategy_mec_wp_api(venue):
    base = venue.get("api_base", "").rstrip("/")
    if not base:
        # Derive from url: take up to first path segment
        from urllib.parse import urlparse
        p = urlparse(venue["url"])
        base = f"{p.scheme}://{p.netloc}"

    endpoints = [
        f"{base}/wp-json/mec/v1/events",
        f"{base}/wp-json/wp/v2/mec-events",
        f"{base}/wp-json/tribe/events/v1/events",
    ]
    params = {"per_page": 100, "status": "publish", "after": TODAY.isoformat()}

    for ep in endpoints:
        try:
            r = requests.get(ep, headers=HEADERS, params=params, timeout=15)
            if not r.ok:
                continue
            data = r.json()
            events = data if isinstance(data, list) else data.get("events", [])
            if not events:
                continue
            print(f"    REST API hit: {ep}  ({len(events)} events)")
            shows = []
            for ev in events:
                # MEC events use various date field names
                raw_date = (ev.get("date") or ev.get("start_date") or
                            ev.get("meta", {}).get("mec_start_date", "") or
                            ev.get("date_gmt",""))
                d = parse_date(str(raw_date)[:10])
                if not in_window(d): continue
                artist = (ev.get("title", {}).get("rendered") or
                          ev.get("title") or ev.get("name","")).strip()
                artist = re.sub(r"<[^>]+>", "", artist)  # strip HTML tags
                if not artist: continue
                url = ev.get("link") or ev.get("url") or ""
                shows.append(build_show(venue, d, artist, url=url))
            return shows
        except Exception as e:
            print(f"    ⚠ {ep}: {e}")
            continue

    print(f"    ⚠ No WP REST API endpoint responded — falling back to Playwright")
    return strategy_pw_generic(venue)


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY: tw_js
# WordPress + TicketWeb plugin (Antone's)
# Playwright renders page, then reads window.EventData.events via JS eval.
# ─────────────────────────────────────────────────────────────────────────────
TW_JS_EVAL = """
() => {
  try {
    if (window.EventData && Array.isArray(window.EventData.events) && window.EventData.events.length > 0) {
      return JSON.stringify(window.EventData.events);
    }
  } catch(e) {}
  return null;
}
"""

def strategy_tw_js(venue):
    print(f"    (Playwright + JS eval — waiting for TicketWeb AJAX)")
    html, events_json = playwright_get(
        venue["url"],
        wait_selector=".tw-event-item, .tw-plugin-upcoming-event-list li",
        wait_ms=12000,
        js_eval=TW_JS_EVAL,
    )
    if events_json:
        try:
            events = json.loads(events_json)
            print(f"    EventData.events: {len(events)} items")
            shows = []
            for ev in events:
                raw_date = (ev.get("date") or ev.get("startDate") or
                            ev.get("start_date") or ev.get("event_date",""))
                d = parse_date(str(raw_date)[:10])
                if not in_window(d): continue
                artist = (ev.get("title") or ev.get("name") or
                          ev.get("headliner","")).strip()
                if not artist: continue
                url = ev.get("url") or ev.get("link") or ev.get("ticket_url","")
                shows.append(build_show(venue, d, artist, url=url))
            return shows
        except Exception as e:
            print(f"    ⚠ EventData parse failed: {e}")
    # Fallback: parse rendered HTML
    return strategy_html(html, venue)


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY: nextjs_js
# Next.js app (Emo's)
# Playwright renders, reads __NEXT_DATA__ or page component state via JS eval.
# ─────────────────────────────────────────────────────────────────────────────
NEXTJS_JS_EVAL = """
() => {
  try {
    // Standard Next.js Pages Router data
    if (window.__NEXT_DATA__) {
      const nd = window.__NEXT_DATA__;
      const pp = nd.props && nd.props.pageProps;
      if (pp) return JSON.stringify(pp);
    }
  } catch(e) {}
  return null;
}
"""

def strategy_nextjs_js(venue):
    print(f"    (Playwright + __NEXT_DATA__ extraction)")
    html, page_props_json = playwright_get(
        venue["url"],
        wait_ms=12000,
        js_eval=NEXTJS_JS_EVAL,
    )
    if page_props_json:
        try:
            props = json.loads(page_props_json)
            # Look for events in common prop names
            events = (props.get("events") or props.get("shows") or
                      props.get("data", {}).get("events") or [])
            if events:
                print(f"    __NEXT_DATA__ events: {len(events)}")
                shows = []
                for ev in events:
                    if not isinstance(ev, dict): continue
                    raw_date = (ev.get("date") or ev.get("startDate") or
                                ev.get("start_date",""))
                    d = parse_date(str(raw_date)[:10])
                    if not in_window(d): continue
                    artist = (ev.get("title") or ev.get("name") or
                              ev.get("headliner","")).strip()
                    if not artist: continue
                    url = ev.get("url") or ev.get("link") or ""
                    shows.append(build_show(venue, d, artist, url=url))
                return shows
        except Exception as e:
            print(f"    ⚠ __NEXT_DATA__ parse failed: {e}")
    # Fall back to HTML parsing of rendered DOM
    return strategy_html(html, venue)


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY: pw_generic
# Generic Playwright + extended wait, then HTML parse.
# Useful as a fallback when the specific strategy returns nothing.
# ─────────────────────────────────────────────────────────────────────────────
def strategy_pw_generic(venue):
    print(f"    (Playwright generic — {venue.get('wait_selector','networkidle')})")
    html, _ = playwright_get(
        venue["url"],
        wait_selector=venue.get("wait_selector"),
        wait_ms=10000,
    )
    return strategy_html(html, venue)


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY: html_generic
# Plain requests + BeautifulSoup. JSON-LD → microdata → class heuristics.
# ─────────────────────────────────────────────────────────────────────────────
def strategy_html_fetch(venue):
    r = requests.get(venue["url"], headers=HEADERS, timeout=20)
    r.raise_for_status()
    return strategy_html(r.text, venue)

def strategy_html(html, venue):
    soup  = BeautifulSoup(html, "lxml")
    shows = []

    # ── JSON-LD ──────────────────────────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data   = json.loads(script.string or "")
            events = data if isinstance(data, list) else [data]
            for ev in events:
                if ev.get("@type") not in ("MusicEvent","Event","TheaterEvent"):
                    continue
                raw = ev.get("startDate","")
                d   = parse_date(raw[:10])
                if not in_window(d): continue
                artist  = _ld_artist(ev)
                url     = ev.get("url","")
                time_s  = raw[11:16] if len(raw)>10 else None
                price   = _ld_price(ev)
                shows.append(build_show(venue, d, artist, url=url,
                                        time_str=time_s, price=price))
        except Exception:
            continue
    if shows: return shows

    # ── Inline JSON blobs ────────────────────────────────────────────────────
    for script in soup.find_all("script"):
        text = script.string or ""
        for m in re.finditer(
            r'(?:window\.\w+|var \w+|\w+)\s*=\s*(\[{.{50,}?\}]|\{{.{100,}?\}})\s*[;,]',
            text, re.S
        ):
            try:
                obj   = json.loads(m.group(1))
                items = obj if isinstance(obj, list) else obj.get("events", obj.get("items",[]))
                if not isinstance(items, list): continue
                for item in items:
                    if not isinstance(item, dict): continue
                    raw = (item.get("date") or item.get("startDate") or
                           item.get("start_date") or item.get("start",""))
                    if isinstance(raw, dict): raw = raw.get("date") or raw.get("local","")
                    d = parse_date(str(raw)[:10])
                    if not in_window(d): continue
                    artist = (item.get("name") or item.get("title") or
                              item.get("headliner","")).strip()
                    if not artist: continue
                    url = item.get("url") or item.get("link","")
                    shows.append(build_show(venue, d, artist, url=url))
            except Exception:
                continue
    if shows: return shows

    # ── Schema.org microdata ─────────────────────────────────────────────────
    for ev in soup.find_all(attrs={"itemtype": re.compile(r"schema.org/(Music)?Event")}):
        name_el = ev.find(attrs={"itemprop":"name"})
        date_el = ev.find(attrs={"itemprop":"startDate"})
        if not (name_el and date_el): continue
        d = parse_date((date_el.get("content") or date_el.get_text())[:10])
        if not in_window(d): continue
        artist = name_el.get_text(strip=True)
        link   = ev.find("a", href=True)
        url    = _abs(link["href"], venue["url"]) if link else ""
        shows.append(build_show(venue, d, artist, url=url))
    if shows: return shows

    # ── Class-name heuristics ────────────────────────────────────────────────
    DATE_RE   = re.compile(r"(event|show)[_-]?(date|day|time)", re.I)
    ARTIST_RE = re.compile(r"(event|show|artist)[_-]?(title|name|headline|headliner)", re.I)
    for block in soup.find_all(["article","li","div"],
                                class_=re.compile(r"event|show|gig|listing|concert", re.I)):
        date_el   = block.find(class_=DATE_RE)
        artist_el = block.find(class_=ARTIST_RE)
        if not (date_el and artist_el): continue
        d = parse_date(date_el.get_text(strip=True))
        if not in_window(d): continue
        artist = artist_el.get_text(strip=True)
        if not artist: continue
        link = block.find("a", href=True)
        url  = _abs(link["href"], venue["url"]) if link else ""
        shows.append(build_show(venue, d, artist, url=url))

    return shows


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _ld_artist(ev):
    p = ev.get("performer") or ev.get("performers")
    if isinstance(p, dict):  return p.get("name", ev.get("name","Unknown"))
    if isinstance(p, list) and p: return p[0].get("name", ev.get("name","Unknown"))
    return ev.get("name","Unknown")

def _ld_price(ev):
    o = ev.get("offers")
    if not o: return None
    if isinstance(o, list): o = o[0]
    price = o.get("price") or o.get("lowPrice")
    if price:
        cur = o.get("priceCurrency","USD")
        return f"{'$' if cur=='USD' else cur}{price}"
    return None

def _abs(path, base):
    from urllib.parse import urljoin
    return urljoin(base, path)


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────
def diagnose(venue, html):
    soup = BeautifulSoup(html, "lxml")
    title  = soup.find("title")
    jld    = soup.find_all("script", type="application/ld+json")
    scripts = [s for s in soup.find_all("script") if s.string and len(s.string)>200]
    classes = set()
    for el in soup.find_all(["div","article","li","section","ul"], class_=True):
        for c in el.get("class",[]):
            if any(k in c.lower() for k in ["event","show","gig","concert","listing","card"]):
                classes.add(c)
    dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', html)
    print(f"    ── DIAG: {venue['name']} ──────────────────")
    print(f"    HTML: {len(html):,} chars  |  title: {title.get_text(strip=True) if title else '?'}")
    print(f"    JSON-LD: {len(jld)}  |  data scripts: {len(scripts)}  |  date strings: {len(dates)}")
    for s in scripts[:2]:
        print(f"      → {(s.string or '')[:100].replace(chr(10),' ')}…")
    print(f"    event classes: {sorted(classes)[:12]}")
    print(f"    ─────────────────────────────────────────")


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────────────────
STRATEGIES = {
    "mec_wp_api":    strategy_mec_wp_api,
    "tw_js":         strategy_tw_js,
    "nextjs_js":     strategy_nextjs_js,
    "pw_generic":    strategy_pw_generic,
    "html_generic":  strategy_html_fetch,
}


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPE ONE VENUE
# ─────────────────────────────────────────────────────────────────────────────
def scrape_venue(venue):
    strat = venue.get("strategy", "html_generic")
    print(f"  [{strat}]  {venue['name']}")
    try:
        fn    = STRATEGIES.get(strat, strategy_html_fetch)
        shows = fn(venue)
        if DIAGNOSE and shows == [] and strat in ("html_generic", "pw_generic"):
            # Re-fetch for diagnosis only if we got nothing
            if strat == "html_generic":
                try:
                    r = requests.get(venue["url"], headers=HEADERS, timeout=20)
                    diagnose(venue, r.text)
                except Exception: pass
            else:
                html, _ = playwright_get(venue["url"], wait_ms=8000)
                diagnose(venue, html)
        print(f"    → {len(shows)} show(s)")
        return shows
    except Exception as e:
        print(f"    ⚠ {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MERGE + NEW SHOWS DIFF
# ─────────────────────────────────────────────────────────────────────────────
def merge(existing, fresh):
    kept = [s for s in existing if s.get("source") != "scraped"]
    kept.extend(fresh)
    return [s for s in kept if s.get("date","") >= str(TODAY) <= str(MAX_DATE)
            and s.get("date","") <= str(MAX_DATE)]

def new_shows_summary(old_ids, fresh):
    new = sorted([s for s in fresh if s["id"] not in old_ids],
                 key=lambda s: (s["date"], s.get("time") or ""))
    return [{"id":s["id"],"date":s["date"],"artist":s["artist"],
             "venue":s["venue"],"region":s["region"]} for s in new]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n=== MojoLists Venue Scraper — {TODAY} ===")
    if DIAGNOSE: print("⚑ DIAGNOSTIC MODE\n")

    with open(VENUES_FILE) as f:
        config = json.load(f)
    active = [v for v in config["venues"] if v.get("active")]
    if not active:
        print("No active venues. Edit scripts/venues.json.")
        return

    js_venues = [v for v in active if v.get("strategy","") in ("tw_js","nextjs_js","pw_generic")]
    print(f"Active: {len(active)} venues  ({len(js_venues)} use headless browser)\n")

    data, sha = load_shows()
    if "meta"  not in data: data["meta"]  = {}
    if "shows" not in data: data["shows"] = []

    old_ids   = {s["id"] for s in data["shows"] if s.get("source")=="scraped"}
    all_fresh = []
    errors    = []

    for i, venue in enumerate(active):
        fresh = scrape_venue(venue)
        all_fresh.extend(fresh)
        if not fresh: errors.append(venue["name"])
        if i < len(active)-1 and venue.get("strategy","") == "html_generic":
            time.sleep(FETCH_DELAY)

    _close_pw()

    print(f"\nTotal scraped: {len(all_fresh)}")
    if errors: print(f"⚠ Zero results: {', '.join(errors)}")

    data["shows"] = merge(data["shows"], all_fresh)
    summary = new_shows_summary(old_ids, all_fresh)
    now = datetime.utcnow().isoformat() + "Z"
    data["meta"].update({
        "lastUpdated": now, "lastScraperRun": now,
        "lastRunNewShows": summary,
        "lastRunVenueCount": len(active),
        "lastRunFoundCount": len(all_fresh),
        "lastRunNewCount": len(summary),
    })
    data["meta"].pop("scraperIndex", None)

    print(f"In store: {len(data['shows'])}  |  New: {len(summary)}")
    save_shows(data, sha,
               f"chore: scrape {len(all_fresh)} shows / {len(active)} venues / "
               f"{len(summary)} new [{TODAY}]")
    print("Done.\n")

if __name__ == "__main__":
    main()
