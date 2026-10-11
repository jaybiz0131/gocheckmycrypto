#!/usr/bin/env node
// type_audit.mjs <built-site-dir> <paths...>
// Program 6, 6.1: the type rule on every page checked. Long text (60+ characters in one element) in the
// mono, long serif body text under 22px, and italic blocks, each listed by page and class so the
// stylesheet can be fixed at the class. Prints a count per class; exit 0 always (a report).
import { createRequire } from "module";
import http from "http"; import fs from "fs"; import path from "path";
const require = createRequire(import.meta.url);
let pw; try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const [dir, ...paths] = process.argv.slice(2);
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname); let f = path.join(root, p);
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = fs.existsSync(path.join(f, "index.html")) ? path.join(f, "index.html") : f + ".html";
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
let browser; const tally = {};
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const ctx = await browser.newContext({ viewport: { width: 375, height: 900 } });
  const page = await ctx.newPage();
  await page.route(/^https?:/, r => (new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort()));
  for (const p of paths) {
    await page.goto(base + p, { waitUntil: "load" }).catch(() => null);
    const rows = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll("main *, footer *").forEach(el => {
        if (!el.childNodes.length) return;
        const own = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
        if (own.length < 60) return;
        const cs = getComputedStyle(el); const fam = cs.fontFamily.toLowerCase(); const size = parseFloat(cs.fontSize);
        const kind = fam.includes("mono") ? "mono-long" : (fam.includes("newsreader") || fam.includes("georgia")) && size < 22 && el.tagName !== "H1" && !/^H[1-6]$/.test(el.tagName) ? "serif-body" : cs.fontStyle === "italic" ? "italic-block" : "";
        if (kind) out.push({ kind, cls: el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : "") });
      });
      return out;
    });
    for (const r of rows) { const k = `${r.kind} ${r.cls}`; (tally[k] = tally[k] || new Set()).add(p); }
  }
} finally { if (browser) await browser.close(); server.close(); }
for (const [k, v] of Object.entries(tally).sort((a, b) => b[1].size - a[1].size)) console.log(`${String(v.size).padStart(3)} pages  ${k}  e.g. ${[...v][0]}`);
console.log("type audit: " + Object.keys(tally).length + " class(es) flagged");
