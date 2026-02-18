module.exports = function(eleventyConfig) {
    // 1. Keep your images in assets/img/
    eleventyConfig.addPassthroughCopy("assets/img");

    // 2. DEFINE THE LIMIT FILTER (This fixes the crash)
    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    // 3. Setup the automated review feed
    eleventyConfig.addCollection("reviews", function(collectionApi) {
        return collectionApi.getFilteredByGlob("reviews/*.md").sort((a, b) => {
            return (b.date || 0) - (a.date || 0);
        });
    });

    return {
        dir: {
            input: ".",
            output: "_site",
            includes: "_includes"
        }
    };
};