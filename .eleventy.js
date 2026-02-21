const Image = require("@11ty/eleventy-img");
const path = require("path");

async function imageShortcode(src, alt, sizes = "100vw") {
  let metadata = await Image(src, {
    widths: [400, 800, 1200],
    formats: ["webp", "jpeg"],
    outputDir: "./_site/img/",
    urlPath: "/img/",
    filenameFormat: function (id, src, width, format, options) {
      const extension = path.extname(src);
      const name = path.basename(src, extension);
      return `${name}-${width}w.${format}`;
    }
  });

  let imageAttributes = {
    alt,
    sizes,
    loading: "lazy",
    decoding: "async",
    class: "w-full h-full object-cover", // Keeps your current styling
  };

  return Image.generateHTML(metadata, imageAttributes);
}

module.exports = function(eleventyConfig) {
    // Image and Asset Passthrough
    eleventyConfig.addPassthroughCopy("assets/img");
    eleventyConfig.addPassthroughCopy("assets/css");

    // Filters
    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    // Shortcodes
    eleventyConfig.addNunjucksAsyncShortcode("image", imageShortcode);

    // Collections: Reviews sorted by date
    eleventyConfig.addCollection("reviews", function(collectionApi) {
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
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk",
        templateFormats: ["html", "njk", "md"]
    };
};