module.exports = function(eleventyConfig) {
    // Pass through assets so your images don't break
    eleventyConfig.addPassthroughCopy("assets");
    eleventyConfig.addPassthroughCopy("reviews/*.jpg");

    // Create the reviews collection sorted by date (newest first)
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