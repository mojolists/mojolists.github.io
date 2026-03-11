const Image = require("@11ty/eleventy-img");
const path = require("path");

async function imageShortcode(src, alt, sizes = "100vw") {
  let metadata = await Image(src, {
    widths: [400, 800, 1200],
    formats: ["webp", "jpeg"],
    outputDir: "./_site/img/",
    urlPath: "/img/",
    filenameFormat: function (id, src, width, format, options) {
      const extension = path.extname(src);
      const name = path.basename(src, extension);
      return `${name}-${width}w.${format}`;
    }
  });
  let imageAttributes = {
    alt,
    sizes,
    loading: "lazy",
    decoding: "async",
    class: "w-full h-full object-cover",
  };

  return Image.generateHTML(metadata, imageAttributes);
}

module.exports = function(eleventyConfig) {
    // Force build even if dates are in the "future" relative to server time
    eleventyConfig.addGlobalData("eleventyComputed.permalink", function() {
        return (data) => data.permalink;
    });

    eleventyConfig.addPassthroughCopy("assets/img");
    eleventyConfig.addPassthroughCopy("assets/css");
    eleventyConfig.addPassthroughCopy("CNAME");
    eleventyConfig.addPassthroughCopy("admin");

    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    // Filter: build row 2 for the index page.
    // Row 1 = top 3 by date (any type). Row 2 picks the latest review from each
    // type NOT already shown, in priority order: current → classics → new-wave →
    // any other replay series. Fills remaining slots with next-most-recent.
    // Scales automatically when new series are added.
    eleventyConfig.addFilter("buildRow2", function(allReviews, row1Reviews) {
        const row1Urls = new Set((row1Reviews || []).map(r => r.url));
        const remaining = (allReviews || []).filter(r => !row1Urls.has(r.url));
        const row2 = [];
        const used = new Set();

        const streams = [
            r => r.data.type !== 'replay',                                      // current
            r => r.data.type === 'replay' && r.data.series === 'classics',      // Re-Play Classic
            r => r.data.type === 'replay' && r.data.series === 'new-wave',      // Re-Play New Wave
            r => r.data.type === 'replay',                                       // any other replay
        ];

        for (const match of streams) {
            if (row2.length >= 3) break;
            const found = remaining.find(r => !used.has(r.url) && match(r));
            if (found) { row2.push(found); used.add(found.url); }
        }

        // Fill any remaining slots with next-most-recent
        for (const r of remaining) {
            if (row2.length >= 3) break;
            if (!used.has(r.url)) { row2.push(r); used.add(r.url); }
        }

        return row2;
    });

    // Helper: returns true if a review's date is today or in the past
    const isPublished = (item) => {
        if (item.data.draft) return false;
        const pub = new Date(item.data.date || item.date);
      pub.setUTCHours(0, 0, 0, 0); // normalize to UTC midnight so today's reviews publish immediately
        return pub <= new Date();
    };

    // Re-Play Classics collection
    eleventyConfig.addCollection("replaysClassics", function(collectionApi) {
        return collectionApi.getFilteredByGlob("**/reviews/*.{md,MD,markdown}")
            .filter(item => isPublished(item) && item.data.type === "replay" && item.data.series === "classics")
            .sort((a, b) => new Date(b.data.date || b.date) - new Date(a.data.date || a.date));
    });

    // Filter: exclude specific items by URL
    eleventyConfig.addFilter("rejectItems", function(array, itemsToExclude) {
        if (!array) return [];
        const excludeUrls = (itemsToExclude || []).map(i => i && i.url).filter(Boolean);
        return array.filter(item => !excludeUrls.includes(item.url));
    });

    // Filter: format a series slug into a display label
    eleventyConfig.addFilter("seriesLabel", function(series) {
        const labels = {
            "classics":  "Classic",
            "new-wave":  "New Wave",
            "disco":     "Disco",
            "punk":      "Punk",
            "rap":       "Rap",
            "grunge":    "Grunge"
        };
        return labels[series] || (series || "").replace(/-/g, " ");
    });

    // Filter: exclude items whose genres overlap with the given genre list
    eleventyConfig.addFilter("rejectGenres", function(array, genresToExclude) {
        if (!array) return [];
        if (!genresToExclude || !genresToExclude.length) return array;
        return array.filter(item => {
            const genres = item.data.genre || [];
            return !genres.some(g => genresToExclude.includes(g));
        });
    });

    eleventyConfig.addNunjucksAsyncShortcode("image", imageShortcode);

    // Robust Collection Logic — only includes published reviews (date <= today, no draft flag)
    eleventyConfig.addCollection("reviews", function(collectionApi) {
        return collectionApi.getFilteredByGlob("**/reviews/*.{md,MD,markdown}")
            .filter(item => isPublished(item))
            .sort((a, b) => {
                const dateA = new Date(a.data.date || a.date);
                const dateB = new Date(b.data.date || b.date);
                return dateB - dateA;
            });
    });

    return {
        dir: {
            input: ".",
            includes: "_includes",
            output: "_site"
        },
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        templateFormats: ["html", "njk", "md"]
    };
};
