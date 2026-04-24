#!/usr/bin/env python3
"""
Download album cover images for every record in _data/vinyl.json.

Sources (in order):
  1. iTunes Search API (keyless, permissive CORS, fast)
  2. Discogs by release ID (requires DISCOGS_TOKEN in env)
  3. Discogs by artist/album search (same token)

Writes:
  assets/img/covers/<slug>.jpg      -- the cover (600x600ish JPG)
  scripts/covers-progress.json      -- checkpoint, updated after each record
  scripts/covers-log.txt            -- one line per record processed

Crash-safe:
  - Re-running skips records whose cover file already exists on disk.
  - Progress file is flushed to disk after every record.
  - Safe to SIGINT at any time and resume later.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ---- Paths -----------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
VINYL_JSON = ROOT / "_data" / "vinyl.json"
COVERS_DIR = ROOT / "assets" / "img" / "covers"
PROGRESS_FILE = Path(__file__).resolve().parent / "covers-progress.json"
LOG_FILE = Path(__file__).resolve().parent / "covers-log.txt"

# ---- HTTP ------------------------------------------------------------------

UA = "mojolists-vinyl-catalog/1.0 (+https://mojolists.com)"
ITUNES_URL = "https://itunes.apple.com/search"
ITUNES_DELAY_S = 1.05
DISCOGS_DELAY_S = 1.10
HTTP_TIMEOUT = 20


def http_json(url, params=None, headers=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def http_bytes(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return r.read()


# ---- Source: iTunes --------------------------------------------------------

def itunes_lookup(artist, album):
    term = f"{artist} {album}".strip()
    if not term:
        return None
    try:
        data = http_json(ITUNES_URL, {
            "term": term, "entity": "album", "limit": 5, "media": "music",
        })
    except Exception:
        return None
    results = data.get("results") or []
    if not results:
        return None
    art = results[0].get("artworkUrl100") or ""
    if not art:
        return None
    return art.replace("100x100bb.jpg", "600x600bb.jpg")


# ---- Source: Discogs -------------------------------------------------------

def discogs_cover(release_id, token):
    if not release_id or not token:
        return None
    try:
        data = http_json(
            f"https://api.discogs.com/releases/{release_id}",
            headers={"Authorization": f"Discogs token={token}"},
        )
    except Exception:
        return None
    images = data.get("images") or []
    for im in images:
        if im.get("type") == "primary" and im.get("resource_url"):
            return im["resource_url"]
    if images and images[0].get("resource_url"):
        return images[0]["resource_url"]
    return None


def discogs_search_cover(artist, album, token):
    """Fallback: search Discogs by artist/album, fetch cover from the top match."""
    if not token:
        return None
    try:
        data = http_json(
            "https://api.discogs.com/database/search",
            params={"artist": artist, "release_title": album, "type": "release", "per_page": 5},
            headers={"Authorization": f"Discogs token={token}"},
        )
    except Exception:
        return None
    results = data.get("results") or []
    for r in results:
        url = r.get("cover_image") or ""
        if url and "spacer.gif" not in url:
            return url
    return None


# ---- Progress / log --------------------------------------------------------

def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {"done": {}, "miss": {}, "errors": {}, "counts": {"itunes": 0, "discogs": 0, "miss": 0, "skip": 0}}


def save_progress(p):
    tmp = PROGRESS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(p, indent=2, ensure_ascii=False))
    tmp.replace(PROGRESS_FILE)


def log(line):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---- Main ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="Stop after N new downloads (0 = no limit)")
    ap.add_argument("--start", type=int, default=0, help="Start index into the records list")
    ap.add_argument("--no-discogs", action="store_true", help="Skip Discogs fallback (iTunes-only)")
    ap.add_argument("--refetch-misses", action="store_true", help="Retry records previously marked missed")
    args = ap.parse_args()

    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not VINYL_JSON.exists():
        sys.exit(f"ERROR: {VINYL_JSON} not found. Run build_vinyl_json.py first.")
    payload = json.loads(VINYL_JSON.read_text())
    records = payload["records"]

    progress = load_progress()
    discogs_token = os.environ.get("DISCOGS_TOKEN", "").strip()
    use_discogs = bool(discogs_token) and not args.no_discogs

    log(f"=== run started {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    log(f"total records: {len(records)}, discogs={'on' if use_discogs else 'off'}")

    new_downloads = 0
    t0 = time.time()

    for idx, rec in enumerate(records[args.start:], start=args.start):
        slug = rec["slug"]
        target = COVERS_DIR / f"{slug}.jpg"

        if target.exists() and target.stat().st_size > 1000:
            progress["counts"]["skip"] = progress["counts"].get("skip", 0) + 1
            continue

        if slug in progress.get("miss", {}) and not args.refetch_misses:
            continue

        artist = rec["artist"]
        album = rec["album"]
        release_id = rec.get("id", "")
        discogs_id = release_id if release_id.isdigit() else ""

        cover_url = None
        source = None

        # --- iTunes ---
        cover_url = itunes_lookup(artist, album)
        if cover_url:
            source = "itunes"
        time.sleep(ITUNES_DELAY_S)

        # --- Discogs by release ID ---
        if not cover_url and use_discogs and discogs_id:
            cover_url = discogs_cover(discogs_id, discogs_token)
            if cover_url:
                source = "discogs"
            time.sleep(DISCOGS_DELAY_S)

        # --- Discogs by artist/album search ---
        if not cover_url and use_discogs:
            cover_url = discogs_search_cover(artist, album, discogs_token)
            if cover_url:
                source = "discogs-search"
            time.sleep(DISCOGS_DELAY_S)

        if not cover_url:
            progress["miss"][slug] = {"artist": artist, "album": album}
            progress["counts"]["miss"] = progress["counts"].get("miss", 0) + 1
            log(f"[{idx:04d}] MISS {artist} -- {album}")
            save_progress(progress)
            continue

        try:
            blob = http_bytes(cover_url)
            target.write_bytes(blob)
        except Exception as e:
            progress["errors"][slug] = str(e)
            log(f"[{idx:04d}] ERR  {artist} -- {album}: {e}")
            save_progress(progress)
            continue

        progress["done"][slug] = {"src": source, "url": cover_url, "size": len(blob)}
        progress["counts"][source] = progress["counts"].get(source, 0) + 1
        progress.get("miss", {}).pop(slug, None)
        new_downloads += 1
        log(f"[{idx:04d}] OK   {source:14} {len(blob):>7}B  {artist} -- {album}")

        if new_downloads % 5 == 0:
            save_progress(progress)

        if args.limit and new_downloads >= args.limit:
            log(f"reached --limit {args.limit}, stopping")
            break

    save_progress(progress)
    elapsed = time.time() - t0
    log(f"=== run ended {time.strftime('%Y-%m-%d %H:%M:%S')}, {new_downloads} new, {elapsed:.1f}s ===")
    log(f"counts: {progress['counts']}")
    print(f"Done. new={new_downloads} elapsed={elapsed:.1f}s counts={progress['counts']}")


if __name__ == "__main__":
    main()
