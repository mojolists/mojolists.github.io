// --- THE MOJOLISTS SOURCE OF TRUTH ---
// The FIRST item in this list is the NEWEST. 
// It will automatically go to the Header and the Top-Left of the grid.
const reviews = [
    {
        artist: "The Nightowls",
        album: "Good As Gold",
        url: "reviews/good-as-gold.html",
        img: "assets/img/gag.jpg",
        excerpt: "Austin band, The Nightowls began their soul journey around 2011 and recently released their first album..."
    },
    {
        artist: "No Show Ponies",
        album: "A Manual For Defeat",
        url: "reviews/no-show-ponies.html",
        img: "assets/img/noshowponies.jpg",
        excerpt: "Three-piece rock music recorded mostly live to tape. What you’ll hear is the sound of a band in a room..."
    },
    {
        artist: "The Bamboos",
        album: "Fever In The Road",
        url: "reviews/fever-in-the-road.html",
        img: "assets/img/feveritr.jpg",
        excerpt: "Australian funk/soul band that has thrived doing what they love. Their sixth full-length album."
    },
    {
        artist: "Trombone Shorty",
        album: "Say That To Say This",
        url: "reviews/say-that-to-say-this.html",
        img: "assets/img/ts.jpg",
        excerpt: "The maturation of an artist mastering his craft. Rock, jazz, blues, hip-hop, soul and the taste of NOLA."
    },
    {
        artist: "Jonny Lang",
        album: "Fight For My Soul",
        url: "reviews/fight-for-my-soul.html",
        img: "assets/img/ffys.jpg",
        excerpt: "After a seven year hiatus, Jonny Lang returns with a mature, polished, and soulful vision."
    }
];

document.addEventListener("DOMContentLoaded", () => {
    const strip = document.getElementById('action-strip');
    const feed = document.getElementById('main-feed');

    // 1. GENERATE THE ACTION STRIP
    // Card 1 & 2 are static editorials. Card 3 is the dynamic NEWEST review.
    strip.innerHTML = `
        <a href="reviews/changes-in-collecting.html" class="mini-card">
            <span class="mini-label">Editorial</span>
            <h3 class="mini-title">Collecting Media</h3>
        </a>
        <a href="reviews/changes-in-music.html" class="mini-card">
            <span class="mini-label">Industry</span>
            <h3 class="mini-title">Changes in Music</h3>
        </a>
        <a href="${reviews[0].url}" class="mini-card">
            <span class="mini-label">Newest Review</span>
            <h3 class="mini-title"><i>${reviews[0].album}</i></h3>
        </a>
    `;

    // 2. GENERATE THE 3-COLUMN GRID
    // Because the array is in order, the first item [0] is the top-left item.
    feed.innerHTML = reviews.map(rev => `
        <article class="feed-item">
            <a href="${rev.url}">
                <div class="image-wrap"><img src="${rev.img}" alt="${rev.album}"></div>
                <div class="item-meta">
                    <span class="artist">${rev.artist}</span>
                    <h2 class="album"><i>${rev.album}</i></h2>
                    <p class="excerpt">${rev.excerpt}</p>
                </div>
            </a>
        </article>
    `).join('');
});
