module.exports = function(eleventyConfig) {
    // This tells the system to include your images
    eleventyConfig.addPassthroughCopy("assets/img");

    // This creates the automated feed of reviews
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