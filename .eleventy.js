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
    class: "w-full h-full object-cover",
  };

  return Image.generateHTML(metadata, imageAttributes);
}

module.exports = function(eleventyConfig) {
    // Force build even if dates are in the "future" relative to server time
    eleventyConfig.addGlobalData("eleventyComputed.permalink", function() {
        return (data) => data.permalink;
    });

    eleventyConfig.addPassthroughCopy("assets/img");
    eleventyConfig.addPassthroughCopy("assets/css");
    eleventyConfig.addPassthroughCopy("CNAME");

    eleventyConfig.addFilter("limit", function(array, limit) {
        return array.slice(0, limit);
    });

    eleventyConfig.addNunjucksAsyncShortcode("image", imageShortcode);

    // Robust Collection Logic
    eleventyConfig.addCollection("reviews", function(collectionApi) {
        // Looks in 'reviews' folder regardless of casing or exact depth
        return collectionApi.getFilteredByGlob("**/reviews/*.{md,MD,markdown}")
            .sort((a, b) => {
                const dateA = new Date(a.data.date || a.date);
                const dateB = new Date(b.data.date || b.date);
                return dateB - dateA;
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