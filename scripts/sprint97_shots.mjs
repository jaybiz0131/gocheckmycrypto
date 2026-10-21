#!/usr/bin/env node
// sprint97_shots.mjs <built-site-dir> <out-dir>
//
// Program 9, Sprint 9.7: the screenshots of the two pages whose look changes, at 375 and 1440, light and dark.
//   coin-btc-<w>-<scheme>.png          /coins/btc: the heading is now an h1 with the h2's look
//   watchlist-top100-<w>-<scheme>.png  /pulse/prices with three saved coins (BTC, ETH, SOL) in the panel
//   watchlist-empty-top100-<w>-<scheme>.png  the same page with nothing saved (the panel takes no room)
// The pages are the built tree's own (the branch's committed site/data); every other host is refused, so the coin page's chart
// shows its own fallback line. The saved coins are set by this script in the capture browser's storage, as a reader's click would.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const [dir, out] = process.argv.slice(2);
if (!dir || !out) { console.log("usage: sprint97_shots.mjs <built-site-dir> <out-dir>"); process.exit(2); }
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
const browser = await pw.chromium.launch();
try {
  for (const scheme of ["light", "dark"]) for (const w of [375, 1440]) {
    for (const [name, url, pins] of [["coin-btc", "/coins/btc.html", null], ["watchlist-top100", "/pulse/prices.html", ["BTC", "ETH", "SOL"]], ["watchlist-empty-top100", "/pulse/prices.html", null]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: w === 375 ? 812 : 900 }, colorScheme: scheme, serviceWorkers: "block" });
      if (pins) await ctx.addInitScript(p => { try { localStorage.setItem("gcmc_coins", JSON.stringify(p)); } catch (e) {} }, pins);
      await ctx.route(/^https?:/, r => new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort());
      const page = await ctx.newPage();
      await page.goto(base + url, { waitUntil: "load" });
      await page.evaluate(() => document.fonts.ready);
      await new Promise(r => setTimeout(r, 500));
      const file = path.join(out, `${name}-${w}-${scheme}.png`);
      // the first screens: what a reader sees before scrolling, which is where both changes are
      await page.screenshot({ path: file, clip: { x: 0, y: 0, width: w, height: w === 375 ? 812 : 900 } });
      console.log("wrote " + file);
      await ctx.close();
    }
  }
} finally {
  await browser.close();
  server.close();
}
