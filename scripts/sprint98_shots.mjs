#!/usr/bin/env node
// sprint98_shots.mjs <built-site-dir> <out-dir>
//
// Program 9, Sprint 9.8: the verdict record, /verdict-record.html, at 375, 390 and 1440, light and dark, the whole page, and How we
// check's and /today/'s new lines. The pages are the built tree's own (the branch's committed site/data, real records only); every other host is
// refused. Each capture prints whether the page scrolls sideways (document width against the viewport).
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
  for (const scheme of ["light", "dark"]) for (const w of [375, 390, 1440]) {
    for (const [name, url, full] of [["verdict-record", "/verdict-record.html", true], ["method-link", "/method.html", false], ["today-link", "/today/", false]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: w < 1000 ? 844 : 900 }, colorScheme: scheme, serviceWorkers: "block" });
      await ctx.route(/^https?:/, r => new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort());
      const page = await ctx.newPage();
      await page.goto(base + url, { waitUntil: "load" });
      await page.evaluate(() => document.fonts.ready);
      await new Promise(r => setTimeout(r, 500));
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      // the grade table must fit its box too (its own scroll would hide a column)
      const tw = await page.evaluate(() => { const t = document.querySelector(".vr-tw"); return t ? t.scrollWidth - t.clientWidth : 0; });
      const file = path.join(out, `${name}-${w}-${scheme}.png`);
      if (full) {
        await page.screenshot({ path: file, fullPage: true });
      } else {
        // How we check: the paragraph that links the record, in view
        const el = page.locator('a[href="/verdict-record.html"]').first();
        await el.scrollIntoViewIfNeeded();
        const box = await el.boundingBox();
        const y = Math.max(0, Math.round(box.y + (await page.evaluate(() => window.scrollY)) - 300));
        await page.evaluate(yy => window.scrollTo(0, yy), y);
        await new Promise(r => setTimeout(r, 200));
        await page.screenshot({ path: file });
      }
      console.log(`wrote ${file}; document width ${sw} at viewport ${w}: ${sw <= w ? "no sideways scroll" : "SCROLLS SIDEWAYS"}; ${tw > 0 ? "THE GRADE TABLE IS CUT BY " + tw + "px" : "grade table fits"}`);
      await ctx.close();
    }
  }
} finally {
  await browser.close();
  server.close();
}
