/** @type {import('prettier').Config} */
const config = {
    // Resolve the plugin from the pre-commit node environment, not from the repo.
    plugins: [require.resolve("@prettier/plugin-xml")],
    bracketSpacing: false,
    printWidth: 88,
    proseWrap: "always",
    semi: true,
    trailingComma: "es5",
    xmlWhitespaceSensitivity: "strict",
    overrides: [
        {files: "*.xml", options: {tabWidth: 4}},
        {files: ["*.yml", "*.yaml"], options: {tabWidth: 2}},
        {files: "*.md", options: {proseWrap: "preserve"}},
    ],
};

module.exports = config;
