module.exports = function(eleventyConfig) {
    eleventyConfig.addPassthroughCopy("assets/img");

    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    eleventyConfig.addCollection("reviews", function(collectionApi) {
        return collectionApi.getFilteredByGlob("reviews/*.md").sort((a, b) => {
            return (b.date || 0) - (a.date || 0);
        });
    });

    return {
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        dataTemplateEngine: "njk",
        dir: {
            input: ".",
            output: "_site",
            includes: "_includes"
        }
    };
};