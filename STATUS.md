# Mojolists — Project Status

_Last updated: 2026-04-09_

## What this is
A personal music review site built with Eleventy (11ty) + Tailwind, hosted on GitHub Pages. Reviews are markdown files with frontmatter. The radar (`_data/mojo-radar.json`) tracks upcoming releases to review.

## Tech stack
- **Framework:** Eleventy 3.x (Nunjucks templates)
- **Styles:** Tailwind CSS
- **Hosting:** GitHub Pages (`mojolists.github.io`)
- **Review format:** Markdown + frontmatter → `reviews/` folder
- **Data:** `_data/mojo-radar.json` tracks upcoming releases

## Review format (quick ref)
```
---
layout: review.njk
title: "Album Title"
artist: "Artist Name"
album: "Album Title"
label: "Label"
year: "YYYY"
image: "filename.jpg"
score1: 85   (originality)
score2: 90   (production)
score3: 88   (replay value)
tags: reviews
genre: ["Soul", "Funk"]
date: YYYY-MM-DD
youtubeId: "xxxxxxxxxxx"
---
```

## Radar — upcoming reviews
| Artist | Album | Release | Priority |
|--------|-------|---------|----------|
| Les Imprimés | Fading Forward | Apr 10 2026 | High |
| Parlor Greens | Emeralds | Apr 10 2026 | High |
| Doctor Bionic | Electric Pollen | May 15 2026 | Medium |
| Joey Quiñones | Inna Soul Steady Situation | May 29 2026 | High |
| Thee Marloes | Di Hotel Malibu | May 22 2026 | High |
| Jalen Ngonda | Doctrine of Love | Jun 5 2026 | High |

## Recently published reviews
(update this list when new reviews go live)
- The Olympians — *In Search of a Revival* (Feb 2026)
- Meters — *Look-Ka Py Py* (recent)
- Parlor Greens — *Emeralds* (Apr 4 2026)

## Current focus / next steps
- Les Imprimés *Fading Forward* drops Apr 10 — review needed
- Check if any radar albums need to be added or updated in mojo-radar.json

## Notes for Claude
- Review voice: opinionated, production-aware, analog-leaning, no fluff
- Use `review-writer` skill when writing reviews
- Replay reviews are longer deep-dives on classic albums
- `new-review.html` and `admin/` contain tooling for adding releases to the radar
- To rebuild locally: `npm start` (Eleventy dev server)
