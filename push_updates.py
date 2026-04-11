#!/usr/bin/env python3
"""
push_updates.py  —  one-time helper to push the scraper files via GitHub API
Run:  python push_updates.py ghp_YOURTOKEN
"""
import sys, json, base64, pathlib, urllib.request, urllib.error

TOKEN = sys.argv[1] if len(sys.argv) > 1 else input("Paste your GitHub token: ").strip()
REPO  = "mojolists/mojolists.github.io"
ROOT  = pathlib.Path(__file__).parent

FILES = [
    "scripts/scrape_venues.py",
    "scripts/venues.json",
    ".github/workflows/scrape-shows.yml",
    ".github/workflows/ticketmaster-shows.yml",
    ".github/workflows/deploy.yml",
]

def gh(method, path, body=None):
    url = f"https://api.github.com/repos/{REPO}/{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method,
           headers={"Authorization": f"token {TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:200]}")

print(f"\nPushing {len(FILES)} files to {REPO} ...\n")
for rel in FILES:
    content = (ROOT / rel).read_bytes()
    b64     = base64.b64encode(content).decode()
    # get current SHA so the PUT is an update not a create
    try:
        existing = gh("GET", f"contents/{rel}")
        sha = existing["sha"]
    except Exception:
        sha = None
    body = {"message": f"feat: update {rel} (scraper rewrite)", "content": b64}
    if sha:
        body["sha"] = sha
    gh("PUT", f"contents/{rel}", body)
    print(f"  ✓  {rel}")

print("\nAll done! Go to https://github.com/mojolists/mojolists.github.io/actions")
print("and click  Actions → Scrape Shows (Weekly) → Run workflow  to test.\n")
