// Drives the spike page in Chromium: every one of the 18 editors renders, and a Weapon with an Attack
// activity is created as a Library + world pair with native dnd5e data.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = path.resolve(process.argv[2]);
const shots = path.resolve(process.argv[3]);
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };
const server = createServer(async (req, res) => {
  try {
    const file = path.join(root, decodeURIComponent(new URL(req.url, "http://x").pathname.replace(/^\/$/, "/index.html")));
    if (!file.startsWith(root)) throw new Error("outside");
    res.writeHead(200, { "content-type": types[path.extname(file)] ?? "application/octet-stream" }).end(await readFile(file));
  } catch { res.writeHead(404).end(); }
}).listen(0);
const url = `http://127.0.0.1:${server.address().port}/`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 640, height: 820 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
await page.goto(url);
await page.evaluate(() => window.__eagle.open());
const win = page.locator("#eagle-homebrew-window");
await win.waitFor();
await page.screenshot({ path: `${shots}/01-art.png` });

// Every kind's editor: open it, count its form groups and builder sections, go back.
const report = [];
for (const art of ["Item", "Actor", "RollTable"]) {
  await win.locator(`[data-action=selectArt][data-art=${art}]`).click();
  const keys = art === "RollTable" ? [null] : await win.locator("[data-action=selectKind]").evaluateAll((b) => b.map((x) => x.dataset.key));
  if (art !== "RollTable") await win.locator("[data-action=back]").click();
  for (const key of keys) {
    if (key) {
      await win.locator(`[data-action=selectArt][data-art=${art}]`).click();
      await win.locator(`[data-action=selectKind][data-key=${key}]`).click();
    }
    await win.locator("[data-action=create]").waitFor();
    const stats = await win.evaluate((w) => ({
      title: w.querySelector("h3")?.textContent,
      formGroups: w.querySelectorAll(".form-group").length,
      sections: [...w.querySelectorAll("details > summary")].map((s) => s.textContent),
      builders: [...w.querySelectorAll("fieldset > legend")].map((l) => l.textContent),
      notBuilt: !!w.textContent.match(/does not have an editor yet/),
    }));
    report.push({ key: key ?? "rolltables", ...stats });
    await win.locator("[data-action=back]").click();
    if (art !== "RollTable") await win.locator("[data-action=back]").click();
  }
}

// Create: Weapon with one Attack activity.
await win.locator("[data-action=selectArt][data-art=Item]").click();
await win.locator("[data-action=selectKind][data-key=weapons]").click();
await page.screenshot({ path: `${shots}/02-weapon-form.png` });
await win.locator("input[name=name]").fill("Flammenklinge");
await win.locator("select[name='type.value']").selectOption("martialM");
await page.waitForTimeout(200);
await page.screenshot({ path: `${shots}/03-weapon-filled.png` });
await win.locator("[data-action=addAction]").click();
await win.locator("[data-action=pickActivityType][data-type=attack]").click();
await page.screenshot({ path: `${shots}/04-attack-builder.png` });
await win.locator("[data-action=confirmActivity]").click();
await win.locator("[data-action=create]").click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${shots}/05-created.png` });
const stored = await page.evaluate(() => [...window.__eagle.backend.documents.values()].map((d) => ({
  uuid: d.uuid, name: d.source.name, type: d.source.type, weaponType: d.source.system?.type?.value,
  rules: d.source.system?.source?.rules, flags: d.source.flags,
  activities: Object.values(d.source.system?.activities ?? {}).map((a) => ({ type: a.type, activation: a.activation?.type })),
})));

// Duplicate naming: the same name again becomes "Flammenklinge (Duplicate)".
await win.locator("[data-action=back]").click().catch(() => {});
const formVisible = await win.locator("input[name=name]").count();
if (!formVisible) {
  await win.locator("[data-action=selectArt][data-art=Item]").click().catch(() => {});
  await win.locator("[data-action=selectKind][data-key=weapons]").click().catch(() => {});
}
await win.locator("input[name=name]").fill("Flammenklinge");
await win.locator("[data-action=create]").click();
await page.waitForTimeout(800);
const names = await page.evaluate(() => [...window.__eagle.backend.documents.values()].map((d) => d.source.name));

console.log(JSON.stringify({ report, stored, names, errors }, null, 1));
await browser.close();
server.close();
