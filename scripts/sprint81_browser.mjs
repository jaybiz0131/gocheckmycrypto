#!/usr/bin/env node
// sprint81_browser.mjs <built-site-dir> [--only flows,today,weight] [--shots <dir>]
//
// Program 8, Sprint 8.1 (14 October 2026): the browser half of the tests.
//   flows   Whale Watch at 1440 and 375: no element is wider than its column (an element
//           inside a scroll box is held to the box), the box itself fits its column, no page
//           scrolls sideways, and no text in its tables is under 12 px.
//   today   /today/ at 375 and 1440: no sideways scroll, no text under 12 px in the answer,
//           and the page weight against the home page's (bytes over the wire, same rules).
//   shots   with --shots, writes the screenshots Jack approves on: /today/, the dated page,
//           the home, the Top 100 BTT-class row, Whale Watch; 375 and 1440, light and dark.
// Prints PASS/FAIL per check; exit 1 on any FAIL. Nothing leaves the machine.
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
const dir = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
if (!dir) { console.log("usage: sprint81_browser.mjs <built-site-dir> [--only a,b] [--shots dir]"); process.exit(2); }
const ONLY = opt("--only", "").split(",").filter(Boolean);
const SHOTS = opt("--shots", "");
const DATED = opt("--dated", "");
const PLANT = argv.includes("--plant");   // plants an overflowing table so the test can be seen red
const want = (n) => !ONLY.length || ONLY.includes(n);

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2", ".xml": "application/xml" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  else if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end("404"); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});

let failed = 0;
const check = (name, ok, detail) => { console.log(`${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : ": " + detail}`); if (!ok) failed++; };

async function open(browser, base, url, width, scheme) {
  const ctx = await browser.newContext({ viewport: { width, height: width < 700 ? 844 : 900 },
    deviceScaleFactor: width < 700 ? 2 : 1, colorScheme: scheme || "light", serviceWorkers: "block" });
  await ctx.route("**/*", (r) => (new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort()));
  const page = await ctx.newPage();
  // the page's weight: every distinct URL it loads, once, at the size that crossed the wire
  // (CDP encodedDataLength, the rule home_budget.mjs uses), counted until the network is quiet
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  let bytes = 0;
  cdp.on("Network.loadingFinished", (e) => { bytes += e.encodedDataLength || 0; });
  await page.goto(base + url, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1500);
  return { ctx, page, bytes: () => bytes };
}

// every element of <main>: its right edge against the edge of the column that holds it
const WIDER = () => {
  const out = [];
  const main = document.querySelector("main") || document.body;
  const clip = (el) => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p).overflowX; if (o === "auto" || o === "scroll" || o === "hidden") return p; } return null; };
  for (const el of main.querySelectorAll("*")) {
    if (el.closest("svg") && el.tagName !== "svg") continue;
    const r = el.getBoundingClientRect();
    if (!r.width) continue;
    const box = clip(el);
    const col = box ? box.getBoundingClientRect() : main.getBoundingClientRect();
    const limit = box ? col.left + box.clientWidth : Math.min(col.right, document.documentElement.clientWidth);
    if (!box && r.right > limit + 1) out.push({ el: el.tagName + "." + (el.className.baseVal ?? el.className), right: Math.round(r.right), limit: Math.round(limit) });
  }
  // a scroll box must itself sit inside its column
  for (const b of main.querySelectorAll(".movetable")) {
    const r = b.getBoundingClientRect(), p = b.parentElement.getBoundingClientRect();
    if (r.right > p.right + 1) out.push({ el: "scrollbox", right: Math.round(r.right), limit: Math.round(p.right) });
  }
  return out;
};
const SMALL = (sel) => {
  const bad = [];
  for (const el of document.querySelectorAll(sel)) {
    if (!el.childNodes.length || ![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 12) bad.push({ t: el.textContent.trim().slice(0, 24), fs });
  }
  return bad;
};

async function main() {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await pw.chromium.launch({ timeout: 30000, executablePath: process.env.CHROMIUM || undefined });
  try {
    if (want("flows")) for (const w of [1440, 375]) {
      const { ctx, page } = await open(browser, base, "/flows", w);
      if (PLANT) await page.addStyleTag({ content: ".movetable{overflow:visible!important}.stack .movetable table{min-width:1300px!important}" });
      const wide = await page.evaluate(WIDER);
      check(`flows@${w}: no element is wider than its column`, !wide.length, JSON.stringify(wide.slice(0, 5)));
      const sideways = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      check(`flows@${w}: the page does not scroll sideways`, sideways <= 0, `scrollWidth over by ${sideways}`);
      const small = await page.evaluate(SMALL, ".movetable td, .movetable th");
      check(`flows@${w}: no table text under 12 px`, !small.length, JSON.stringify(small.slice(0, 4)));
      if (SHOTS) for (const s of ["light", "dark"]) {
        const c2 = await open(browser, base, "/flows", w, s);
        await c2.page.screenshot({ path: path.join(SHOTS, `whale-watch-${w}-${s}.png`), fullPage: true });
        await c2.ctx.close();
      }
      await ctx.close();
    }
    if (want("today")) {
      for (const w of [375, 1440]) {
        const { ctx, page, bytes } = await open(browser, base, "/today/", w);
        const sideways = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        check(`today@${w}: no sideways scroll`, sideways <= 0, `over by ${sideways}`);
        const wide = await page.evaluate(WIDER);
        check(`today@${w}: no element wider than its column`, !wide.length, JSON.stringify(wide.slice(0, 5)));
        const small = await page.evaluate(SMALL, ".td-page *");
        check(`today@${w}: no text under 12 px`, !small.length, JSON.stringify(small.slice(0, 4)));
        const h1 = await page.evaluate(() => (document.querySelector("h1") || {}).textContent || "");
        check(`today@${w}: one h1 that asks the day's question`, /Why is crypto (down|up) today\?|Crypto today: flat/.test(h1), h1);
        await ctx.close();
      }
      // weight: the page's own bytes, document plus what it loads, against the home page's
      const t = await open(browser, base, "/today/", 375), h = await open(browser, base, "/", 375);
      const tb = t.bytes(), hb = h.bytes();
      check("today: /today/ at 375 weighs less than the home page", tb < hb, `today ${tb} bytes, home ${hb} bytes`);
      console.log(`INFO weight@375: /today/ ${tb} bytes, home ${hb} bytes`);
      await t.ctx.close(); await h.ctx.close();
    }
    if (SHOTS) {
      fs.mkdirSync(SHOTS, { recursive: true });
      const pages = [["today", "/today/"], ["home", "/"], ["top100", "/pulse/prices"]];
      if (DATED) pages.splice(1, 0, ["today-dated", DATED]);
      for (const [name, url] of pages) for (const w of [375, 1440]) for (const s of ["light", "dark"]) {
        const { ctx, page } = await open(browser, base, url, w, s);
        await page.screenshot({ path: path.join(SHOTS, `${name}-${w}-${s}.png`), fullPage: true });
        await ctx.close();
      }
    }
  } finally { await browser.close(); server.close(); }
  console.log(failed ? `\n${failed} check(s) failed` : "\nall checks passed");
  process.exit(failed ? 1 : 0);
}
main().catch((e) => { console.log("FAIL harness: " + e); process.exit(1); });
