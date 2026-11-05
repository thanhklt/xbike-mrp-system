import js from "@eslint/js";
import globals from "globals";
export default [
  { ignores: ["dist", "node_modules", ".npm-cache"] },
  {
    ...js.configs.recommended,
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^[A-Z]" }],
      eqeqeq: "error",
      "no-var": "error",
      "prefer-const": "error",
    },
  },
];
