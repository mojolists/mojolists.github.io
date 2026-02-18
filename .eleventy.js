module.exports = function(eleventyConfig) {
    // Keeps your images where they belong
    eleventyConfig.addPassthroughCopy("assets/img");

    // Automatically sorts reviews by date (newest first)
    eleventyConfig.addCollection("reviews", function(collectionApi) {
        return collectionApi.getFilteredByGlob("reviews/*.md").sort((a, b) => {
            return b.date - a.date;
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