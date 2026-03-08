# Re-Play Review Prompt — Influential New Wave Albums

## What a Re-Play Review Is

Re-Play reviews look back at landmark albums: how they landed at the time of release, the influence they've had on music in the years since, and where they stand today. The tone is authoritative and direct. No hedging, no filler, no sentences that could appear in a press release. Write like someone who has lived with this music for decades and has strong, earned opinions about it.

---

## Frontmatter (required fields)

```yaml
---
layout: replay.njk
title: "Artist Name"
artist: "Artist Name"
album: "Album Title"
label: "Label Name"
year: "YYYY"
image: "filename.jpg"
score1: 00
score2: 00
score3: 00
tags: reviews
genre: ["New Wave"]
type: replay
date: YYYY-MM-DD
---
```

**Scoring rubric:**
- `score1` — Performance (the playing, the performances captured on record)
- `score2` — Production (how the album sounds, the choices made in the studio)
- `score3` — Impact (how much it moved the needle — culturally, sonically, historically)

---

## Structure

Every Re-Play review has three sections, each at least two full paragraphs. Six paragraphs total is the floor — go longer if the album warrants it.

---

### `## At Release`

Set the scene. Where did this album come from, what was going on in music at the time, and how did people react? Be specific about the cultural moment. New Wave emerged from the wreckage of punk and the commercial excess of late-70s rock and disco — place this album in that context. What did critics say? What did audiences do? Did it chart? Did it confuse people? Was it ahead of its time or did it land exactly right?

Two paragraphs minimum. The first should paint the wider picture; the second should zero in on the specific critical and commercial reception of this album.

After the second paragraph, insert the pull quote using this exact HTML:

```html
<p class="inline-quote">Your chosen quote from the body text.</p>
```

Pick the sharpest, most specific sentence from what you just wrote. Not something vague — something that would make a reader stop.

---

### `## The Influence`

This is the heart of the review. Who heard this record and changed what they were doing? Name names. Be specific — not "many artists were influenced" but "The Cure took the icy synth textures and built a career on them" or "every Talking Heads record from this point forward owes a structural debt to this one."

For New Wave albums, consider the following angles:

- Which post-punk and alternative bands absorbed this directly?
- What sonic or production innovations did it introduce — synthesizers, drum machines, tape manipulation, studio-as-instrument thinking — and who picked those up and ran with them?
- Did it bridge genres in a way that opened new doors? New Wave sat at the intersection of punk energy, electronic experimentation, art school sensibility, and pop ambition — which of those threads got pulled by later artists?
- Did its influence skip a generation? Many New Wave albums were ignored in the 90s and rediscovered in the 2000s indie revival.

Two paragraphs minimum. After the second paragraph, embed the YouTube video using this exact HTML:

```html
<div class="inline-video"><iframe src="https://www.youtube.com/embed/VIDEO_ID" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>
```

Choose a live performance, a classic music video, or the album's most representative track.

---

### `## Where It Stands Today`

How does the album hold up right now? Does it sound dated or does it sound prescient? Has its reputation grown, shrunk, or stayed the same since release? Is it regularly cited in best-of lists? Is it a record that casual listeners know or one that lives in the crates of obsessives?

Be honest. Not every influential album is a great listen today — say so if that's true. Not every classic ages gracefully. Conversely, some New Wave records sound more modern now than they did in 1980.

Two paragraphs minimum. End the second paragraph with a sentence that lands with some weight — this is the last thing the reader takes away.

After the final paragraph, insert the buy link:

```html
<a href="AMAZON_LINK" target="_blank" class="buy-btn">Buy Album</a>
```

---

## Tone and Style Notes

- Write in third person. This is a critical review, not a personal essay.
- Past tense for historical events; present tense when discussing how the album sounds or stands today.
- Specific beats vague every time. "The drum machine pattern on Side B rewired how producers thought about rhythm" is better than "the production was innovative."
- Avoid: "seminal," "iconic," "timeless," "ahead of its time" as standalone claims — make the argument instead of just stating the conclusion.
- The inline quote should be pulled verbatim from your own text, not invented separately. Write the review first, then find the line that deserves to stand alone.

---

## New Wave Context — Reference Points

When framing the album's place in the movement, consider where it sits relative to the broader New Wave story:

**The origins** — New Wave grew out of punk (1976–77) but shed the aggressive, anti-musicianship stance. Art school influence, synthesizers, and a fascination with European electronic music (Kraftwerk, krautrock) were central.

**The peak years** — 1978–1983. The window when New Wave was commercially dominant and artistically restless at the same time.

**The splintering** — By 1983–84, New Wave had fragmented into synth-pop (polished, chart-friendly), post-punk (darker, more abrasive), college rock, and eventually alternative. Which branch does this album belong to, and which branches did it help create?

**The legacy artists to name-check** — The Cure, Joy Division/New Order, Talking Heads, Devo, Elvis Costello, The Police, Blondie, XTC, Wire, Gang of Four, The Pretenders, Echo & the Bunnymen, The Psychedelic Furs, Siouxsie and the Banshees, Simple Minds. Use whichever are genuinely relevant — don't force connections that aren't there.
