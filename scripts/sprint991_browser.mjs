#!/usr/bin/env node
// sprint991_browser.mjs <dir>
//
// Sprint 9.9.1 (26 October 2026): the browser half of scripts/sprint991_test.py. It serves a directory that holds the site's
// assets and home-991-next-read.html, home-991-no-read.html and home-991-graded.html (written by the test from the real
// October 26 and October 15 records), aborts every other host, and for each page at 375 and 1440 pixels measures the first
// object below the masthead:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//     INFO <name>: <a measurement, not a verdict>
//
// S991_SHOTS=<dir> also saves a screenshot per page and width. Exit 1 when any check fails. U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const dir = process.argv[2];
if (!dir) { console.log("usage: sprint991_browser.mjs <dir>"); process.exit(2); }
const root = path.resolve(dir);
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2" };
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const f = path.join(root, p);
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

const CASES = [["next-read", "the window-flipped notice"], ["no-read", "the no-read notice"], ["graded", "a graded card"]];
let browser;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  for (const [name, label] of CASES) {
    for (const w of [375, 1440]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
      const page = await ctx.newPage();
      await page.route((u) => !u.href.startsWith(base), (r) => r.abort());
      await page.goto(`${base}/home-991-${name}.html`, { waitUntil: "load", timeout: 30000 });
      const m = await page.evaluate(() => {
        const rect = (e) => { const r = e.getBoundingClientRect(); return { top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY), left: Math.round(r.left), width: Math.round(r.width) }; };
        const masthead = document.querySelector("header.masthead"), nav = document.querySelector("nav.mh-nav");
        const mhBottom = Math.max(masthead ? rect(masthead).bottom : 0, nav ? rect(nav).bottom : 0);
        const main = document.querySelector("main");
        // every visible block of the home, in its two columns
        const blocks = [...main.querySelectorAll(".h-l > *, .h-r > *")].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const first = main.querySelector(".h-l > *");
        const card = main.querySelector("aside.vd");
        const tape = main.querySelector(".h-tape");
        const topmost = blocks.reduce((a, e) => (rect(e).top < rect(a).top ? e : a), blocks[0]);
        return {
          mhBottom, firstTag: first.tagName.toLowerCase(), firstIsCard: first === card, card: card ? rect(card) : null,
          tape: tape ? rect(tape) : null, topmostIsCard: topmost === card, topmost: topmost.className, topmostTop: rect(topmost).top,
          cardText: card ? card.innerText.replace(/\s+/g, " ").trim().slice(0, 400) : "", firstHeading: card && card.querySelector("h2") ? card.querySelector("h2").innerText : "",
          scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
        };
      });
      const tag = `${label} at ${w}`;
      m.firstIsCard ? pass(`${tag}: the first block of the home is the verdict card`) : fail(`${tag}: first block`, `the first block is <${m.firstTag}>, not the card`);
      m.card && m.card.top >= m.mhBottom - 1 && m.card.top - m.mhBottom <= 60
        ? pass(`${tag}: the card starts directly below the masthead (${m.card.top - m.mhBottom}px under it)`)
        : fail(`${tag}: card position`, `card top ${m.card && m.card.top}, masthead bottom ${m.mhBottom}`);
      m.tape && m.card && m.tape.top >= m.card.bottom - 1
        ? pass(`${tag}: the Bitcoin line (the tape) sits under the card (${m.tape.top - m.card.bottom}px below it)`)
        : fail(`${tag}: tape under card`, `tape top ${m.tape && m.tape.top}, card bottom ${m.card && m.card.bottom}`);
      // nothing above it: no block of either column starts higher than the card, give or take the column gap
      m.topmostIsCard || (m.card && m.card.top - m.topmostTop <= 12)
        ? pass(`${tag}: no home block starts above the card`)
        : fail(`${tag}: nothing above`, `a block with class "${m.topmost}" starts at ${m.topmostTop}, the card at ${m.card && m.card.top}`);
      m.card && m.card.top < 900 ? pass(`${tag}: the card is on the first screen`) : fail(`${tag}: first screen`, `card top ${m.card && m.card.top}`);
      m.scrollW <= m.clientW ? pass(`${tag}: no sideways scroll`) : fail(`${tag}: sideways scroll`, `${m.scrollW} > ${m.clientW}`);
      info(`${tag}`, `card ${JSON.stringify(m.card)}, tape ${JSON.stringify(m.tape)}, masthead bottom ${m.mhBottom}`);
      if (process.env.S991_SHOTS) { fs.mkdirSync(process.env.S991_SHOTS, { recursive: true }); await page.screenshot({ path: path.join(process.env.S991_SHOTS, `home-${name}-${w}.png`) }); }
      await ctx.close();
    }
  }
} catch (e) {
  fail("browser", String(e).slice(0, 200));
} finally {
  if (browser) await browser.close();
  server.close();
}
process.exit(bad ? 1 : 0);
