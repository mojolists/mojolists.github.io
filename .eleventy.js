module.exports = function(eleventyConfig) {
    eleventyConfig.addPassthroughCopy("assets/img");

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