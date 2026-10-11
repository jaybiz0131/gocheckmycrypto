#!/usr/bin/env node
// page_shots.mjs <built-site-dir> <outdir> <label> [--paths /pulse,/flows,...] [--weights] [--combos 375:light,...]
//
// Program 6 Sprint 6.1 proof: screenshots (full page) of the named pages from a LOCAL build, at 375 and
// 1440, light and dark, written as <outdir>/<label>/<slug>-<width>-<theme>.png, and, with --weights,
// the bytes each page moves at 375 (every response body from navigation until quiet, served
// from the local copy, so before and after compare like for like) written to <outdir>/<label>/weights.json.
// Nothing leaves the machine: any request to another host is aborted.
//
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const argv = process.argv.slice(2);
const [dir, outdir, label] = argv;
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
if (!dir || !outdir || !label) { console.log("usage: page_shots.mjs <dir> <outdir> <label> [--paths a,b] [--weights] [--combos 375:light,...]"); process.exit(2); }
const WEIGHTS = argv.includes("--weights");
const PATHS = (opt("--paths", "/")).split(",").filter(Boolean);
const COMBOS = opt("--combos", "375:light,375:dark,1440:light,1440:dark").split(",").map(s => s.split(":"));
const SHOTS = !argv.includes("--no-shots");

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".mp4": "video/mp4",
  ".woff2": "font/woff2", ".webmanifest": "application/manifest+json", ".xml": "application/xml" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = fs.existsSync(path.join(f, "index.html")) ? path.join(f, "index.html") : f + ".html";
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  const st = fs.statSync(f);
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream", "content-length": st.size });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const slug = p => (p === "/" ? "home" : p.replace(/^\//, "").replace(/\.html$/, "").replace(/[^a-z0-9]+/gi, "_"));
const out = path.join(outdir, label);
fs.mkdirSync(out, { recursive: true });

let browser; const weights = {};
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  for (const [w, theme] of COMBOS) {
    const ctx = await browser.newContext({ viewport: { width: +w, height: 900 }, colorScheme: theme, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    let bytes = 0;
    page.on("response", async r => { try { const b = await r.body(); bytes += b.length; } catch {} });
    await page.route(/^https?:/, r => (new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort()));
    for (const p of PATHS) {
      bytes = 0;
      const resp = await page.goto(base + p, { waitUntil: "load", timeout: 30000 }).catch(() => null);
      if (!resp) { console.log(`no response ${p}`); continue; }
      await page.addStyleTag({ content: ".tabbar{position:static!important}body{padding-bottom:0!important}" }).catch(() => {});
      await page.waitForTimeout(700);
      if (WEIGHTS && +w === 375 && theme === "light") weights[p] = { status: resp.status(), bytes };
      if (SHOTS) await page.screenshot({ path: path.join(out, `${slug(p)}-${w}-${theme}.png`), fullPage: true });
    }
    await ctx.close();
  }
  if (WEIGHTS) fs.writeFileSync(path.join(out, "weights.json"), JSON.stringify(weights, null, 1));
} finally {
  if (browser) await browser.close();
  server.close();
}
console.log("done", label, PATHS.length, "pages");
