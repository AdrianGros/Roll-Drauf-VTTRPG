// Builds the Creation Engine's browser bundle into vtt/static/eagle-homebrew/ (served by Flask, git-ignored).
import { build } from "esbuild";
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const host = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.resolve(host, "../..");
const out = path.join(root, "vtt/static/eagle-homebrew");
const vendor = path.join(root, "vendor/eagle-homebrew");
const pin = Object.fromEntries(
  readFileSync(path.join(host, "eagle-homebrew.pin"), "utf8").split("\n").filter((line) => /^[A-Z_]+=/.test(line)).map((line) => line.split("=")),
);

mkdirSync(out, { recursive: true });
await build({
  entryPoints: [path.join(host, "src/entry.ts")],
  bundle: true,
  format: "esm",
  target: "es2022",
  minify: true,
  sourcemap: true,
  legalComments: "eof",
  tsconfig: path.join(host, "tsconfig.json"),
  outfile: path.join(out, "creation-engine.js"),
  logLevel: "info",
});
copyFileSync(path.join(vendor, "v13/styles/eagle-homebrew.css"), path.join(out, "eagle-homebrew.css"));
copyFileSync(path.join(host, "src/shim.css"), path.join(out, "shim.css"));
writeFileSync(path.join(out, "build.json"), JSON.stringify({ eagleHomebrewCommit: pin.EAGLE_HOMEBREW_COMMIT, dnd5e: "5.3.3" }, null, 2) + "\n");
