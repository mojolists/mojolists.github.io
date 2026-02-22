---
permalink: /reviews/index.html
layout: false
---
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Archive | MojoLists</title>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0b1120; color: #94a3b8; }
        .serif { font-family: 'Playfair Display', serif; }
        .logo-font { font-family: 'Cormorant Garamond', serif; }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.3s ease;
        }
        .glass-card:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: #c5a059;
            transform: translateY(-4px);
        }
    </style>
</head>
<body class="min-h-screen pb-20">
    <nav class="p-8 mb-12 flex justify-between items-center max-w-7xl mx-auto">
        <a href="/" class="logo-font text-3xl text-white font-light tracking-widest uppercase">MojoLists</a>
        <a href="/" class="text-xs uppercase tracking-[0.4em] text-slate-500 hover:text-[#c5a059] transition-colors font-bold">Back Home</a>
    </nav>

    <main class="max-w-7xl mx-auto px-6">
        <header class="mb-16">
            <h1 class="serif text-5xl text-white mb-6">The Archive</h1>
            <div class="max-w-md relative">
                <input type="text" id="reviewSearch" 
                       placeholder="Search artist or album..." 
                       class="w-full bg-slate-900/50 border border-white/10 rounded-sm py-3 px-6 text-white focus:outline-none focus:border-[#c5a059] transition-colors italic">
            </div>
        </header>

        <div id="cardGrid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {% for review in collections.all | reverse %}
                {% if review.data.tags and ("reviews" in review.data.tags or "posts" in review.data.tags) %}
                <a href="{{ review.url }}" 
                   class="review-card-item block group" 
                   data-title="{{ review.data.album or review.data.title }}" 
                   data-artist="{{ review.data.artist }}">
                    <div class="glass-card p-4 rounded-sm h-full flex flex-col">
                        <div class="aspect-square mb-4 overflow-hidden rounded-sm bg-slate-900 border border-white/5">
                            {% set imgPath = review.data.image or review.data.img or review.data.coverImage %}
                            {# Smart Image Pathing: Prepend assets path only if not already present #}
                            <img src="{% if '/assets/img/' in imgPath %}{{ imgPath }}{% else %}/assets/img/{{ imgPath }}{% endif %}" 
                                 alt="{{ review.data.artist }}" 
                                 class="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity">
                        </div>
                        <div class="flex-grow">
                            <h3 class="text-white font-bold text-sm leading-tight group-hover:text-[#c5a059] transition-colors">
                                {{ review.data.album or review.data.title }}
                            </h3>
                            <p class="text-[9px] uppercase tracking-[0.2em] text-slate-500 font-bold mt-2">
                                {{ review.data.artist }}
                            </p>
                        </div>
                        <div class="mt-4 pt-4 border-t border-white/5 flex justify-between items-center">
                            <span class="text-[#c5a059] font-black italic serif text-xl">
                                {{ review.data.score or review.data.mojoScore or 0 }}%
                            </span>
                            <span class="text-[8px] uppercase tracking-widest text-slate-600 font-bold">Mojo Rating</span>
                        </div>
                    </div>
                </a>
                {% endif %}
            {% endfor %}
        </div>

        <div id="noResults" class="hidden py-20 text-center">
            <p class="serif text-2xl text-slate-600 italic">No matches found in the archive.</p>
        </div>
    </main>

    <script>
        const searchInput = document.getElementById('reviewSearch');
        const cards = document.querySelectorAll('.review-card-item');
        const grid = document.getElementById('cardGrid');
        const noResults = document.getElementById('noResults');

        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            let hasResults = false;

            cards.forEach(card => {
                const title = (card.getAttribute('data-title') || "").toLowerCase();
                const artist = (card.getAttribute('data-artist') || "").toLowerCase();

                if (title.includes(term) || artist.includes(term)) {
                    card.style.display = 'block';
                    hasResults = true;
                } else {
                    card.style.display = 'none';
                }
            });

            noResults.classList.toggle('hidden', hasResults);
            grid.classList.toggle('hidden', !hasResults);
        });
    </script>
</body>
</html>