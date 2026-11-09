// The prototype keeps CSS and JavaScript inside index-prototype.html. Extract each
// block into temporary repository-local files so standard linters can inspect it.
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { ESLint } from "eslint";
import stylelint from "stylelint";

const htmlPath = "app/templates/index-prototype.html";
const html = await readFile(htmlPath, "utf8");
const tempDirectory = await mkdtemp(join(process.cwd(), ".frontend-lint-"));

// Return the contents of every block matching the supplied HTML element pattern.
function extractBlocks(pattern) {
  return [...html.matchAll(pattern)].map((match) => match[1]);
}

const cssBlocks = extractBlocks(/<style\b[^>]*>([\s\S]*?)<\/style>/gi);
const javascriptBlocks = extractBlocks(/<script\b(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)<\/script>/gi);

if (cssBlocks.length === 0 || javascriptBlocks.length === 0) {
  throw new Error("Expected at least one inline style block and one inline script block.");
}

const cssFiles = [];
const javascriptFiles = [];

try {
  await mkdir(tempDirectory, { recursive: true });

  for (const [index, css] of cssBlocks.entries()) {
    const file = join(tempDirectory, `inline-${index}.css`);
    await writeFile(file, `${css.trim()}\n`, "utf8");
    cssFiles.push(file);
  }

  for (const [index, javascript] of javascriptBlocks.entries()) {
    const file = join(tempDirectory, `inline-${index}.js`);
    await writeFile(file, `${javascript.trim()}\n`, "utf8");
    javascriptFiles.push(file);
  }

  // Stylelint checks CSS semantics without requiring a formatting rewrite.
  const cssResult = await stylelint.lint({
    configFile: ".stylelintrc.json",
    files: cssFiles,
    formatter: "string"
  });
  if (cssResult.report) process.stdout.write(cssResult.report);

  // ESLint checks the extracted browser script for syntax and unsafe references.
  const eslint = new ESLint({
    overrideConfigFile: "scripts/frontend/eslint.config.mjs"
  });
  const javascriptResults = await eslint.lintFiles(javascriptFiles);
  const formatter = await eslint.loadFormatter("stylish");
  const javascriptOutput = await formatter.format(javascriptResults);
  if (javascriptOutput) process.stdout.write(javascriptOutput);

  if (cssResult.errored || javascriptResults.some((result) => result.errorCount > 0)) {
    process.exitCode = 1;
  }
} finally {
  // Never leave generated source files in the working tree or Jenkins workspace.
  await rm(tempDirectory, { recursive: true, force: true });
}
