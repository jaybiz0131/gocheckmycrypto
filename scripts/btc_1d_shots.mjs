#!/usr/bin/env node
// btc_1d_shots.mjs <built-site-dir> <outdir> <label>      Program 7 Sprint 7.3: Bitcoin's 1D close-up at 375.
//
// Serves a built tree, answers CoinGecko's market_chart from the recorded fixtures (the browser
// reads nothing else), loads /coins/btc, opens the 1D and 7D tabs and
//   * writes a close-up of the chart block (light and dark) as <label>-1d-375-<theme>.png, and
//     <label>-7d-375-<theme>.png;
//   * prints the high and low labels the chart DREW on each window, beside the pair the home
//     tape prints (its "24h high ... low" line and its 7D HIGH and LOW), so a person can read
//     that they are the same figures. The browser-level half of scripts/btc_hilo_test.py.
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const [dir, outdir, label] = process.argv.slice(2);
if (!dir || !outdir || !label) { console.log("usage: btc_1d_shots.mjs <dir> <outdir> <label>"); process.exit(2); }
const CG = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "fixtures", "coingecko");
fs.mkdirSync(outdir, { recursive: true });
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const report = {};
let browser;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 900 }, colorScheme: theme, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.route(/^https?:/, r => {
      const u = new URL(r.request().url());
      if (u.host === new URL(base).host) return r.continue();
      const m = u.host === "api.coingecko.com" && u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      if (m) {
        const d = parseInt(u.searchParams.get("days") || "7", 10), k = d <= 1 ? 1 : d <= 7 ? 7 : 365;
        const f = fs.existsSync(path.join(CG, `${m[1]}-${k}.json`)) ? `${m[1]}-${k}.json` : `bitcoin-${k}.json`;
        return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: fs.readFileSync(path.join(CG, f)) });
      }
      return r.abort();
    });
    await page.goto(base + "/", { waitUntil: "load", timeout: 30000 });
    const tape = await page.evaluate(() => ({
      h24: (document.querySelector("[data-hl24]") || {}).textContent || null,
      hi7: (document.querySelector(".h-k-hi") || {}).textContent || null,
      lo7: (document.querySelector(".h-k-lo") || {}).textContent || null }));
    await page.goto(base + "/coins/btc", { waitUntil: "load", timeout: 30000 });
    await page.addStyleTag({ content: ".tabbar{position:static!important}body{padding-bottom:0!important}" });
    const drawn = {};
    for (const r of ["1d", "7d"]) {
      await page.click(`.cc-tab[data-range="${r}"]`);
      await page.waitForFunction(rr => document.querySelector("[data-coin-chart]").getAttribute("data-range") === rr
        && document.querySelector(".cc-svg"), r, { timeout: 15000 });
      await page.waitForTimeout(1500);
      drawn[r] = await page.evaluate(() => [...document.querySelectorAll(".cc-hl")].map(e => e.textContent));
      const box = await page.locator("section.cc").boundingBox();
      await page.screenshot({ path: path.join(outdir, `${label}-${r}-375-${theme}.png`),
        clip: { x: 0, y: box.y - 8, width: 375, height: Math.min(box.height + 16, 700) } });
    }
    report[theme] = { tape, chartDrew: drawn };
    await ctx.close();
  }
} finally {
  if (browser) await browser.close();
  server.close();
}
console.log(JSON.stringify(report, null, 1));
