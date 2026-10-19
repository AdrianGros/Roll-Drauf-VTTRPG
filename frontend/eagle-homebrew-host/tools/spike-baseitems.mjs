import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
const root = path.resolve(process.argv[2]);
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };
const server = createServer(async (req, res) => {
  try { const f = path.join(root, new URL(req.url, "http://x").pathname.replace(/^\/$/, "/index.html")); res.writeHead(200, { "content-type": types[path.extname(f)] }).end(await readFile(f)); }
  catch { res.writeHead(404).end(); }
}).listen(0);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${server.address().port}/`);
await page.evaluate(() => window.__eagle.open());
const win = page.locator("#eagle-homebrew-window");
await win.locator("[data-art=Item]").click();
await win.locator("[data-key=weapons]").click();
const out = {};
for (const t of ["simpleM", "martialM", "martialR"]) {
  await win.locator("select[name='type.value']").selectOption(t);
  await page.waitForTimeout(300);
  out[t] = await win.locator("select[name='type.baseItem'] option").allTextContents();
}
console.log(JSON.stringify(out));
await browser.close(); server.close();
