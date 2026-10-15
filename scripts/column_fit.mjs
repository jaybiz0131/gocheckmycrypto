#!/usr/bin/env node
// column_fit.mjs <built-site-dir> <path> [--widths 1440,375]
// Sprint 8.1 (item 3). For each width: list every element inside <main> whose box is wider than
// the column it sits in, ignoring boxes that scroll on purpose (overflow-x auto/scroll/hidden is
// the scroll box doing its job), and report the smallest text size on the page's tables.
// Prints one JSON object per width and exits 1 if any element overflows or any table text is under 12 px.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const argv = process.argv.slice(2);
const [dir, pg] = argv;
const wi = argv.indexOf("--widths");
const WIDTHS = (wi > -1 ? argv[wi + 1] : "1440,375").split(",").map(Number);
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".webp": "image/webp" };
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
let browser, bad = 0;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.route(/^https?:/, r => new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort());
    await page.goto(base + pg, { waitUntil: "load", timeout: 30000 });
    await page.waitForTimeout(400);
    const res = await page.evaluate(() => {
      const scrolls = el => { for (let e = el; e && e !== document.body; e = e.parentElement) {
        const o = getComputedStyle(e).overflowX; if (e !== el && (o === "auto" || o === "scroll" || o === "hidden")) return true; } return false; };
      const out = { docW: document.documentElement.scrollWidth, winW: window.innerWidth, over: [], small: [] };
      const main = document.querySelector("main") || document.body;
      for (const el of main.querySelectorAll("*")) {
        if (el.closest("svg")) continue;        // a chart's own drawing is not a layout box
        if (scrolls(el)) continue;
        const par = el.parentElement; if (!par) continue;
        const r = el.getBoundingClientRect(), pr = par.getBoundingClientRect();
        if (r.width < 1) continue;
        if (r.right > pr.right + 1 && !["TD", "TH", "TR", "TBODY", "THEAD", "TABLE"].includes(el.tagName) || r.right > window.innerWidth + 1)
          out.over.push({ tag: el.tagName, cls: el.className && el.className.baseVal === undefined ? el.className : "", w: Math.round(r.width), right: Math.round(r.right), parentRight: Math.round(pr.right) });
      }
      for (const t of main.querySelectorAll("table td, table th")) {
        const fs = parseFloat(getComputedStyle(t).fontSize);
        if (fs < 12 && (t.textContent || "").trim()) out.small.push({ txt: t.textContent.trim().slice(0, 20), fs });
      }
      for (const tb of main.querySelectorAll(".movetable")) {
        const t = tb.querySelector("table"); if (!t) continue;
        if (tb.getBoundingClientRect().right > window.innerWidth + 1) out.over.push({ tag: "movetable", w: Math.round(tb.getBoundingClientRect().width) });
      }
      if (out.docW > out.winW + 1) out.over.push({ tag: "document", w: out.docW });
      return out;
    });
    console.log(JSON.stringify({ width: w, path: pg, docW: res.docW, over: res.over.slice(0, 8), nOver: res.over.length, small: res.small.slice(0, 4) }));
    bad += res.over.length + res.small.length;
    await ctx.close();
  }
} finally { if (browser) await browser.close(); server.close(); }
process.exit(bad ? 1 : 0);
