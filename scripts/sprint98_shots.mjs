#!/usr/bin/env node
// sprint98_shots.mjs <built-site-dir> <out-dir>
//
// Program 9, Sprint 9.8: the verdict record at 390 and 1440, light and dark, full page.
//   record-REAL-<w>-<scheme>.png                  /why/record/ as the built tree draws it from the stored records
//   record-FIXTURE-SYNTHETIC-<w>-<scheme>.png     /why/record-fixture/ (written into the tree copy by sprint98_fixture_page.py):
//                                                 the test fixture, populated, with a reversed verdict
// Every host but the local server is refused.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const [dir, out] = process.argv.slice(2);
if (!dir || !out) { console.log("usage: sprint98_shots.mjs <built-site-dir> <out-dir>"); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await pw.chromium.launch({ timeout: 60000 });
try {
  for (const scheme of ["light", "dark"]) for (const w of [390, 1440]) {
    for (const [name, url] of [["record-REAL", "/why/record/"], ["record-FIXTURE-SYNTHETIC", "/why/record-fixture/"]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: w === 390 ? 844 : 900 }, colorScheme: scheme, serviceWorkers: "block" });
      await ctx.route(/^https?:/, r => new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort());
      const page = await ctx.newPage();
      await page.goto(base + url, { waitUntil: "load" });
      await page.evaluate(() => document.fonts.ready);
      await new Promise(r => setTimeout(r, 400));
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      const file = path.join(out, `${name}-${w}-${scheme}.png`);
      await page.screenshot({ path: file, fullPage: true });
      console.log(`wrote ${file} (page width ${sw} at viewport ${w}${sw > w ? ", SIDEWAYS SCROLL" : ""})`);
      await ctx.close();
    }
  }
} finally {
  await browser.close();
  server.close();
}
