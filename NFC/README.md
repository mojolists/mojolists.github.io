# NFC — pilot album pages

Short, info-packed decision prompts for NFC-chip tags inside vinyl sleeves. Tap the chip, get enough info in a few seconds to decide whether to spin it.

## Shape of each page

- Artist / album / year / label
- One-line description (what it is, in a breath)
- 3-5 scannable facts: chart, personnel, guests, context
- "Spin it for:" — one line of vibe/mood
- Standout tracks — separated by `·`
- If a full Mojolists review exists: link to it at the bottom

No prose paragraphs. Pure scan-and-decide.

## Pilot files

| Album | Has Mojolists review? | Link at bottom? |
|---|---|---|
| Parlor Greens — *Emeralds* | Yes | Yes |
| The Olympians — *In Search of a Revival* | Yes | Yes |
| Ezra Collective — *Dance, No One's Watching* | No | No (sources inline instead) |

All three carry `source: "auto-generated"` in frontmatter so they're distinguishable from Doug's first-person reviews.

## Still open

- Cover image for Ezra Collective — not yet fetched (frontmatter references `ezra-collective-dance.jpg`)
- Final folder destination once approved
- Whether the `review.njk` layout is right or we want a tighter `card.njk` / `tag.njk` layout for these short pages
