const Image = require("@11ty/eleventy-img");
const path = require("path");

module.exports = function(eleventyConfig) {
    // 1. FORCE ELEVENTY TO BUILD ALL POSTS REGARDLESS OF DATE
    eleventyConfig.addGlobalData("eleventyComputed.permalink", function() {
        return (data) => data.permalink;
    });

    eleventyConfig.addPassthroughCopy("assets/img");
    eleventyConfig.addPassthroughCopy("assets/css");
    eleventyConfig.addPassthroughCopy("CNAME");

    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    // 2. ROBUST COLLECTION LOGIC
    eleventyConfig.addCollection("reviews", function(collectionApi) {
        // This grabs EVERYTHING in the reviews folder regardless of date
        return collectionApi.getFilteredByGlob("reviews/*.md").sort((a, b) => {
            return b.date - a.date;
        });
    });

    return {
        dir: {
            input: ".",
            includes: "_includes",
            output: "_site"
        },
        // 3. ENSURE NUNJUCKS IS THE ENGINE FOR EVERYTHING
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        templateFormats: ["html", "njk", "md"]
    };
};