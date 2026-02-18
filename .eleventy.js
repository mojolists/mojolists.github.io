module.exports = function(eleventyConfig) {
    // 1. Handle Images
    eleventyConfig.addPassthroughCopy("assets/img");

    // 2. The missing "Limit" filter (Fixes Error 2)
    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    // 3. Automated Review Feed
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