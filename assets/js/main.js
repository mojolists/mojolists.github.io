const reviews = [
    {
        artist: "The Nightowls",
        album: "Good As Gold",
        url: "reviews/good-as-gold.html",
        img: "assets/img/gag.jpg",
        excerpt: "Austin soul journey beginning around 2011. A catchy series of funk-infused soul syrup."
    },
    {
        artist: "No Show Ponies",
        album: "A Manual For Defeat",
        url: "reviews/no-show-ponies.html",
        img: "assets/img/noshowponies.jpg",
        excerpt: "Three-piece rock recorded live to tape. Raw, room-driven, and honest."
    },
    {
        artist: "The Bamboos",
        album: "Fever In The Road",
        url: "reviews/fever-in-the-road.html",
        img: "assets/img/feveritr.jpg",
        excerpt: "Australian funk/soul giants return with their sixth full-length masterpiece."
    },
    {
        artist: "Trombone Shorty",
        album: "Say That To Say This",
        url: "reviews/say-that-to-say-this.html",
        img: "assets/img/ts.jpg",
        excerpt: "The maturation of an artist mastering his craft. Pure NOLA soul."
    }
];

document.addEventListener("DOMContentLoaded", () => {
    const strip = document.getElementById('action-strip');
    const feed = document.getElementById('main-feed');

    if (strip) {
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
    }

    if (feed) {
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
    }
});
