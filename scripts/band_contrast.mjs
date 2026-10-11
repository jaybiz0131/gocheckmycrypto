#!/usr/bin/env node
// band_contrast.mjs <url-or-dir> [--all] [--ratio 7]
//
// The narrative band's ink (11 October 2026). In light mode `.page p,.page li{color:var(--ink)}`
// beat the colour the band's paragraph would inherit, so the sentence was ink on the band's ink.
// Two checks, at 375 and 1440, light and dark:
//   1. the home page's narrative sentence (and every text in the band) has a computed colour
//      with at least --ratio:1 contrast against the band's background;
//   2. (--all) the sweep: on every page in the built site, any `p` or `li` that sits inside a
//      dark surface (an ancestor whose background is dark, an image or a gradient) must clear
//      the same ratio against that surface's own colours.
// <url-or-dir> is a base URL, or a built site directory that is served locally.
// The sweep's floor is --sweep-ratio (default 4.5, WCAG AA): the band's sentence is held to 7.
// --list prints every dark surface the sweep met, with its lowest ratio.
// Exit 0 only when nothing is below the ratio.
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
const target = argv[0];
const ALL = argv.includes("--all");
const ri = argv.indexOf("--ratio");
const RATIO = ri > -1 ? parseFloat(argv[ri + 1]) : 7;
const si = argv.indexOf("--sweep-ratio");
const SWEEP_RATIO = si > -1 ? parseFloat(argv[si + 1]) : 4.5;
const LIST = argv.includes("--list");
const seen = new Map();
if (!target) { console.log("usage: band_contrast.mjs <url-or-dir> [--all] [--ratio 7]"); process.exit(2); }

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".mp4": "video/mp4" };
let server, base = target;
if (!/^https?:/.test(target)) {
  const root = path.resolve(target);
  server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    let f = path.join(root, p);
    if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
    if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
    fs.createReadStream(f).pipe(res);
  });
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${server.address().port}`;
}

// runs in the page: returns [{sel, text, color, bg, ratio}] for every offender
function inPage({ band, sweep, ratio, list }) {
  const parse = s => {
    const m = s.match(/rgba?\(([^)]+)\)/g) || [];
    return m.map(x => { const n = x.match(/[\d.]+/g).map(Number); return { r: n[0], g: n[1], b: n[2], a: n.length > 3 ? n[3] : 1 }; });
  };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const cr = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const label = el => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") +
    (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : "");
  // the surface behind an element: the nearest ancestor with a painted background, as a list
  // of colours (a gradient or image contributes every colour stop it names; an image with no
  // stop is read as the ancestor's own colour)
  const surface = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      const stops = parse(cs.backgroundImage).filter(c => c.a > 0.5);
      if (cs.backgroundImage !== "none" && stops.length) return { el: n, cols: stops };
      const bg = parse(cs.backgroundColor)[0];
      if (bg && bg.a > 0.5) return { el: n, cols: [bg] };
      if (cs.backgroundImage !== "none") { const b2 = parse(cs.backgroundColor)[0]; if (b2 && b2.a > 0) return { el: n, cols: [b2] }; }
    }
    return { el: document.documentElement, cols: [{ r: 255, g: 255, b: 255, a: 1 }] };
  };
  const out = [];
  const check = el => {
    const txt = (el.textContent || "").trim();
    if (!txt) return;
    const fg = parse(getComputedStyle(el).color)[0];
    const s = surface(el);
    const worst = Math.min(...s.cols.map(c => cr(fg, c)));
    if (worst < ratio) out.push({ sel: label(el), surface: label(s.el), text: txt.slice(0, 60),
      color: getComputedStyle(el).color, bg: s.cols.map(c => `rgb(${c.r},${c.g},${c.b})`).join(" / "), ratio: +worst.toFixed(2) });
  };
  if (band) {
    const b = document.querySelector(".h-band");
    if (!b) return { error: "no .h-band on the page" };
    const line = b.querySelector(".h-nline");
    if (line) check(line);
    b.querySelectorAll("p,li,span,a").forEach(e => { if (e !== line) check(e); });
    return { found: !!line, out };
  }
  // the sweep: the fault is `.page p,.page li{color:var(--ink)}` winning over the colour a
  // dark surface meant to hand down, so the sweep is those elements, on a dark surface
  // (luminance under 0.2) that is not the page itself. Other low-contrast greys (the muted
  // footnote, the tile's down colour) are palette choices, not this fault.
  document.querySelectorAll(".page p,.page li").forEach(el => {
    const s = surface(el);
    if (s.el === document.documentElement || s.el === document.body) return;
    const dark = s.cols.some(c => lum(c) < 0.2);
    if (dark) {
      check(el);
      if (list) { const fg = parse(getComputedStyle(el).color)[0];
        out.push({ info: true, surface: label(s.el), ratio: +Math.min(...s.cols.map(c => cr(fg, c))).toFixed(2) }); }
    }
  });
  return { out };
}

let browser, bad = 0;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const pages = ["/"];
  if (ALL) {
    const root = /^https?:/.test(target) ? null : path.resolve(target);
    if (root) {
      const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e =>
        e.isDirectory() ? walk(path.join(d, e.name)) : e.name.endsWith(".html") ? [path.join(d, e.name)] : []);
      for (const f of walk(root)) { const r = "/" + path.relative(root, f); if (r !== "/index.html") pages.push(r); }
    }
  }
  for (const scheme of ["light", "dark"]) {
    for (const width of [375, 1440]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: scheme });
      const page = await ctx.newPage();
      const own = new URL(base).host;
      await page.route(/^https?:/, r => (new URL(r.request().url()).host === own ? r.continue() : r.abort()));
      await page.goto(base + "/", { waitUntil: "load", timeout: 30000 });
      const r = await page.evaluate(inPage, { band: true, sweep: false, ratio: RATIO });
      if (r.error) { console.log(`FAIL ${scheme} ${width}: ${r.error}`); bad++; }
      else if (!r.found) { console.log(`FAIL ${scheme} ${width}: no narrative sentence (.h-nline) in the band`); bad++; }
      else if (r.out.length) { for (const o of r.out) console.log(`FAIL band ${scheme} ${width}: ${JSON.stringify(o)}`); bad += r.out.length; }
      else console.log(`ok   band ${scheme} ${width}`);
      if (ALL) {
        let n = 0;
        for (const p of pages) {
          const resp = await page.goto(base + p, { waitUntil: "load", timeout: 30000 }).catch(() => null);
          if (!resp || !resp.ok()) continue;
          n++;
          const s = await page.evaluate(inPage, { band: false, sweep: true, ratio: SWEEP_RATIO, list: LIST });
          for (const o of s.out) {
            if (o.info) { const k = o.surface, v = seen.get(k) || { n: 0, min: 99 }; v.n++; v.min = Math.min(v.min, o.ratio); seen.set(k, v); continue; } console.log(`FAIL sweep ${scheme} ${width} ${p}: ${JSON.stringify(o)}`); bad++; }
        }
        console.log(`     swept ${n} pages ${scheme} ${width}`);
      }
      await ctx.close();
    }
  }
} finally {
  if (browser) await browser.close();
  if (server) server.close();
}
for (const [k, v] of seen) console.log(`surface ${k}: ${v.n} p/li, lowest ${v.min}:1`);
console.log(bad ? `BAND CONTRAST: FAIL (${bad})` : "BAND CONTRAST: PASS");
process.exit(bad ? 1 : 0);
