module.exports = function(eleventyConfig) {
    // Ensure CSS and Images are copied to the final build
    eleventyConfig.addPassthroughCopy("assets");
    eleventyConfig.addPassthroughCopy("reviews/*.jpg");
    eleventyConfig.addPassthroughCopy("reviews/*.png");
    eleventyConfig.addPassthroughCopy("reviews/*.jpeg");

    // Filter to limit the number of items in the grid loop
    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    return {
        dir: {
            input: ".",
            includes: "_includes",
            output: "_site"
        }
    };
};