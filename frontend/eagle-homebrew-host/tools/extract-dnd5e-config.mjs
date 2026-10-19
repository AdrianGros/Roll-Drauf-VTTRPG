// Evaluates dnd5e's module/config.mjs outside Foundry and writes a JSON snapshot of CONFIG.DND5E,
// localized with dnd5e's own language file. Foundry-only imports are replaced with inert stubs.
import { build } from "esbuild";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const [dnd5eRoot, lang, outFile] = process.argv.slice(2);
const configPath = path.join(dnd5eRoot, "module/config.mjs");

const stubPlugin = {
  name: "stub-foundry-imports",
  setup(b) {
    b.onResolve({ filter: /.*/ }, (args) => {
      if (args.kind === "entry-point") return undefined;
      return { path: args.path, namespace: "stub" };
    });
    b.onLoad({ filter: /.*/, namespace: "stub" }, (args) => ({
      contents: args.path.endsWith("utils.mjs")
        ? "export function preLocalize() {} export function formatNumber(n){return String(n);} export default {};"
        : "const S = globalThis.__stub; export default S; export const ConsumptionTargetData = S; export const CalendarGreyhawk = S, CalendarHarptos = S, CalendarKhorvaire = S; export const CALENDAR_OF_GREYHAWK = {}, CALENDAR_OF_HARPTOS = {}, CALENDAR_OF_KHORVAIRE = {};",
      loader: "js",
    }));
  },
};

// Deep callable proxy: any property access or call on a Foundry global yields another inert proxy.
const stub = new Proxy(function () {}, {
  get: (_t, key) => (key === Symbol.toPrimitive ? () => "" : key === "prototype" ? {} : stub),
  apply: () => stub,
  construct: () => stub,
});
globalThis.__stub = stub;
for (const name of ["foundry", "CONST", "game", "ui", "Hooks", "CONFIG"]) globalThis[name] ??= stub;

const result = await build({ entryPoints: [configPath], bundle: true, write: false, format: "esm", plugins: [stubPlugin], logLevel: "silent" });
const bundled = path.join(path.dirname(outFile), ".dnd5e-config.bundle.mjs");
writeFileSync(bundled, result.outputFiles[0].text);
// Any further Foundry global the config touches at load time (Color, ...) becomes an inert stub on demand.
let mod;
for (let attempt = 0; attempt < 50 && !mod; attempt += 1) {
  try {
    mod = await import(`${bundled}?attempt=${attempt}`);
  } catch (error) {
    const missing = error instanceof ReferenceError && /^(\w+) is not defined$/.exec(error.message);
    if (!missing) throw error;
    globalThis[missing[1]] = stub;
  }
}
const DND5E = mod.default;

const flat = {};
const flatten = (obj, prefix = "") => {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object") flatten(v, key);
    else flat[key] = v;
  }
};
flatten(JSON.parse(readFileSync(path.join(dnd5eRoot, "lang", `${lang}.json`), "utf8")));
if (lang !== "en") {
  const en = {};
  const save = Object.assign({}, flat);
  for (const k of Object.keys(flat)) delete flat[k];
  flatten(JSON.parse(readFileSync(path.join(dnd5eRoot, "lang", "en.json"), "utf8")));
  Object.assign(flat, save);
}

// JSON-safe copy: drops functions, classes and stub proxies; localizes string values that are i18n keys.
const seen = new WeakSet();
const clean = (value) => {
  if (value === stub || typeof value === "function" || typeof value === "symbol") return undefined;
  if (typeof value === "string") return flat[value] ?? value;
  if (!value || typeof value !== "object") return value;
  if (seen.has(value)) return undefined;
  seen.add(value);
  let out;
  if (value instanceof Set) out = [...value].map(clean);
  else if (Array.isArray(value)) out = value.map(clean).filter((v) => v !== undefined);
  else {
    out = {};
    for (const key of Object.keys(value)) {
      let v;
      try { v = clean(value[key]); } catch { v = undefined; }
      if (v !== undefined) out[key] = v;
    }
  }
  seen.delete(value);
  return out;
};
const snapshot = clean(DND5E);
writeFileSync(outFile, JSON.stringify(snapshot, null, 1));
console.log("keys:", Object.keys(snapshot).length);
