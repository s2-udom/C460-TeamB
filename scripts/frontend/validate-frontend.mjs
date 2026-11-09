// Lightweight contract checks for the existing prototype. These verify that the
// frontend remains structurally usable without inventing backend/API tests.
import { readFile } from "node:fs/promises";

const html = await readFile("app/templates/index-prototype.html", "utf8");
const failures = [];

// These are the frontend features that the current prototype is expected to expose.
const requiredPatterns = [
  ["HTML5 doctype", /^<!doctype html>/i],
  ["English document language", /<html\b[^>]*\blang=["']en["']/i],
  ["responsive viewport", /<meta\b[^>]*name=["']viewport["']/i],
  ["application mount point", /id=["']app["']/i],
  ["hash-based router", /addEventListener\(["']hashchange["']/],
  ["login route", /pages\.login\s*=/],
  ["home route", /pages\.home\s*=/],
  ["event route", /pages\.event\s*=/],
  ["seat-selection route", /pages\.seats\s*=/],
  ["checkout route", /pages\.checkout\s*=/],
  ["confirmation route", /pages\.confirmation\s*=/],
  ["tickets route", /pages\.tickets\s*=/],
  ["admin route", /pages\.admin\s*=/]
];

for (const [description, pattern] of requiredPatterns) {
  if (!pattern.test(html)) failures.push(`Missing ${description}.`);
}

// Keep the prototype's single-file structure explicit until assets are split later.
const styleBlocks = html.match(/<style\b[^>]*>[\s\S]*?<\/style>/gi) ?? [];
const scriptBlocks = html.match(/<script\b(?![^>]*\bsrc\s*=)[^>]*>[\s\S]*?<\/script>/gi) ?? [];

if (styleBlocks.length !== 1) failures.push(`Expected exactly one inline style block; found ${styleBlocks.length}.`);
if (scriptBlocks.length !== 1) failures.push(`Expected exactly one inline script block; found ${scriptBlocks.length}.`);
if (/<script\b[^>]*\bsrc\s*=/i.test(html)) failures.push("External JavaScript was added; review the frontend dependency policy.");

if (failures.length > 0) {
  console.error("Frontend validation failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Frontend structural validation passed.");
