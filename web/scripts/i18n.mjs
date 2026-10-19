// Collects every t("…") string in src/ into src/i18n/en.json, the catalog a
// translation starts from, and reports keys a translation is missing.
//
//   node scripts/i18n.mjs          rewrite en.json
//   node scripts/i18n.mjs --check  fail if en.json is out of date
//
// Labels passed to t() through a variable (a tab's name, a callout's kicker)
// are listed in EXTRA so they are translated too.

import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC = new URL("../src/", import.meta.url).pathname;
const CATALOG = join(SRC, "i18n", "en.json");
const EXTRA = ["MonsterTix", "Venue panel", "ADK web UI", "The point", "Developer's note", "Careful",
];

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : /\.tsx?$/.test(name) ? [path] : [];
  });
}

const keys = new Set(EXTRA);
const call = /\bt\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g;
for (const file of files(SRC)) {
  for (const match of readFileSync(file, "utf8").matchAll(call)) keys.add(JSON.parse(match[1].replace(/^'|'$/g, '"')));
}
const catalog = Object.fromEntries([...keys].sort().map((k) => [k, k]));
const text = JSON.stringify(catalog, null, 2) + "\n";

if (process.argv.includes("--check")) {
  const current = readFileSync(CATALOG, "utf8");
  if (current !== text) {
    console.error("src/i18n/en.json is out of date: run node scripts/i18n.mjs");
    process.exit(1);
  }
  for (const name of readdirSync(join(SRC, "i18n")).filter((n) => n.endsWith(".json") && n !== "en.json")) {
    const other = JSON.parse(readFileSync(join(SRC, "i18n", name), "utf8"));
    const missing = [...keys].filter((k) => !(k in other));
    if (missing.length) console.log(`${name}: ${missing.length} string(s) not translated yet (English is shown)`);
  }
} else {
  writeFileSync(CATALOG, text);
  console.log(`${keys.size} strings in src/i18n/en.json`);
}
