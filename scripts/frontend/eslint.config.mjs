// ESLint configuration for JavaScript extracted from the prototype's inline script.
// The browser globals match the APIs used by the static frontend.
export default [
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        Array: "readonly",
        Date: "readonly",
        Error: "readonly",
        JSON: "readonly",
        Math: "readonly",
        Map: "readonly",
        Number: "readonly",
        Object: "readonly",
        Promise: "readonly",
        RegExp: "readonly",
        Set: "readonly",
        String: "readonly",
        URL: "readonly",
        clearInterval: "readonly",
        clearTimeout: "readonly",
        console: "readonly",
        document: "readonly",
        location: "readonly",
        scrollTo: "readonly",
        scrollY: "readonly",
        setInterval: "readonly",
        setTimeout: "readonly",
        window: "readonly"
      }
    },
    rules: {
      "no-constant-condition": ["error", { "checkLoops": false }],
      "no-dupe-args": "error",
      "no-dupe-keys": "error",
      "no-func-assign": "error",
      "no-undef": "error",
      "no-unreachable": "error"
    }
  }
];
