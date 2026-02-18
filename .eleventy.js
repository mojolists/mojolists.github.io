module.exports = function(eleventyConfig) {
    // This tells the engine where your images are
    eleventyConfig.addPassthroughCopy("assets/img");

    // This creates the automated review list
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