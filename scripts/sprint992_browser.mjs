#!/usr/bin/env node
// sprint992_browser.mjs <tree>
//
// Sprint 9.9.2 (27 October 2026): the browser half of scripts/sprint992_test.py. It serves a built tree (the site's own
// pages and assets), aborts every other host, and measures:
//
//   1. the Chart Master's table at 375 pixels, as it opens and with "Show all columns" ticked: every column header,
//      RSI-14 by name, on one line (its text's line boxes counted with a Range, so a wrap is seen, not guessed);
//   2. the pages whose figures moved in this sprint (the home, /coins/btc, /coins/doge, /pulse/etf.html, /flows.html,
//      /chartmaster.html) at 375 and 1440: no sideways scroll, and on the home the week chart's two labels inside the chart.
//
//     PASS <name>
//     FAIL <name>: <what was found>
//     INFO <name>: <a measurement, not a verdict>
//
// S992_SHOTS=<dir> also saves a screenshot per page and width. Exit 1 when any check fails. U-7: the browser is launched with a
// timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const dir = process.argv[2];
if (!dir) { console.log("usage: sprint992_browser.mjs <tree>"); process.exit(2); }
const root = path.resolve(dir);
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2" };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  let f = path.join(root, p);
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
let bad = 0;
const pass = (n) => console.log(`PASS ${n}`);
const fail = (n, w) => { bad++; console.log(`FAIL ${n}: ${w}`); };
const info = (n, w) => console.log(`INFO ${n}: ${w}`);
const shots = process.env.S992_SHOTS || "";

let browser;
try {
  browser = await pw.chromium.launch({ timeout: 60000 });
  const mk = async (width) => {
    const ctx = await browser.newContext({ viewport: { width, height: width === 375 ? 812 : 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.setDefaultTimeout(15000);
    await page.route("**/*", (r) => (r.request().url().startsWith(base) ? r.continue() : r.abort()));
    return [ctx, page];
  };

  // 1. the Chart Master's table headers at 375
  {
    const [ctx, page] = await mk(375);
    try {
      await page.goto(base + "/chartmaster.html", { waitUntil: "load" });
      const heads = async () => page.evaluate(() => {
        const t = document.querySelector(".cm-datacard table");
        if (!t) return null;
        return Array.from(t.querySelectorAll("thead th")).map((th) => {
          const shown = getComputedStyle(th).display !== "none";
          const r = document.createRange();
          r.selectNodeContents(th);
          const tops = new Set(Array.from(r.getClientRects()).filter((x) => x.width > 0).map((x) => Math.round(x.top)));
          return { text: th.textContent.trim(), shown, lines: tops.size, width: Math.round(th.getBoundingClientRect().width) };
        });
      });
      for (const state of ["as it opens", "with every column shown"]) {
        if (state !== "as it opens") {
          const lab = await page.$("label.fit-more[for='fit-cm']");
          if (lab) await lab.click();
        }
        const h = await heads();
        if (!h) { fail(`the Chart Master's table at 375, ${state}`, "no data card table on the page"); continue; }
        info(`the Chart Master's table at 375, ${state}`, JSON.stringify(h));
        const rsi = h.find((x) => x.text === "RSI-14");
        if (state === "with every column shown" || (rsi && rsi.shown)) {
          if (!rsi || !rsi.shown) fail(`the RSI-14 header at 375, ${state}`, "not shown");
          else if (rsi.lines !== 1) fail(`the RSI-14 header at 375, ${state}`, `wraps onto ${rsi.lines} lines at ${rsi.width}px`);
          else pass(`the RSI-14 header fits on one line at 375, ${state}`);
        }
        const wrapped = h.filter((x) => x.shown && x.lines > 1).map((x) => x.text);
        if (wrapped.length) fail(`every column header at 375, ${state}`, `wraps: ${wrapped.join(", ")}`);
        else pass(`every column header fits on one line at 375, ${state}`);
      }
      if (shots) await page.screenshot({ path: path.join(shots, "375_chartmaster-table.png"), fullPage: false });
    } catch (e) { fail("the Chart Master's table at 375", String(e).slice(0, 160)); }
    finally { await ctx.close(); }
  }

  // 2. no sideways scroll where figures moved; the home's week labels inside the chart
  for (const width of [375, 1440]) {
    for (const p of ["/", "/coins/btc", "/coins/doge", "/pulse/etf.html", "/flows.html", "/chartmaster.html"]) {
      const [ctx, page] = await mk(width);
      try {
        await page.goto(base + p, { waitUntil: "load" });
        const m = await page.evaluate(() => {
          const d = document.documentElement;
          const out = { sw: d.scrollWidth, cw: d.clientWidth };
          const box = document.querySelector("[data-btc-card] .h-chart, [data-btc-card]");
          const ks = Array.from(document.querySelectorAll(".h-k"));
          if (box && ks.length) {
            const b = box.getBoundingClientRect();
            out.labels = ks.map((k) => { const r = k.getBoundingClientRect(); return { l: Math.round(r.left - b.left), r: Math.round(b.right - r.right), t: k.textContent.trim() }; });
          }
          return out;
        });
        if (m.sw > m.cw) fail(`${p} at ${width}`, `scrolls sideways: page ${m.sw}px in a ${m.cw}px window`);
        else pass(`${p} at ${width}: no sideways scroll`);
        if (m.labels) {
          const out = m.labels.filter((x) => x.l < 0 || x.r < 0);
          if (out.length) fail(`the home's week labels at ${width}`, `outside the chart: ${JSON.stringify(out)}`);
          else pass(`the home's week labels at ${width} sit inside the chart (${m.labels.map((x) => x.t).join("; ")})`);
        }
        if (shots) await page.screenshot({ path: path.join(shots, `${width}_${p === "/" ? "home" : p.replace(/^\//, "").replace(/[/.]/g, "-")}.png`), fullPage: false });
      } catch (e) { fail(`${p} at ${width}`, String(e).slice(0, 160)); }
      finally { await ctx.close(); }
    }
  }
} finally {
  if (browser) await browser.close();
  server.close();
}
console.log(bad ? `FAIL ${bad} check(s)` : "PASS every check");
process.exit(bad ? 1 : 0);
