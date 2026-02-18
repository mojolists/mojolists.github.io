module.exports = function(eleventyConfig) {
    eleventyConfig.addPassthroughCopy("assets/img");

    eleventyConfig.addCollection("reviews", function(collectionApi) {
        return collectionApi.getFilteredByGlob("reviews/*.md").sort((a, b) => {
            return b.date - a.date;
        });
    });

    eleventyConfig.addFilter("calculateMojo", function(mojo) {
        if (!mojo) return 0;
        const score = Math.round(((mojo.soundQuality + mojo.music + mojo.boogieLevel) / 30) * 100);
        return score;
    });

    return {
        dir: {
            input: ".",
            output: "_site",
            includes: "_includes"
        }
    };
};