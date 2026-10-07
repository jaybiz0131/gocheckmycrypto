#!/usr/bin/env node
// live_read.mjs <url> [--width 375] [--expect <commit>] [--wire]
//
// A production read by stamp (U-10, U-11): the page's own <meta name="build-commit"> must
// name the commit the report means, or the read fails before it measures anything. Prints
// the stamp, the viewport, horizontal overflow, and with --wire the News page's wire block:
// the cadence line, the item count, and each element the program asks every item to carry.
// Exit 0 only when every check holds.
//
// Cloud sessions: Playwright's Chromium (PLAYWRIGHT_BROWSERS_PATH). U-7: launched with a
// timeout, closed in a finally block.
import { createRequire } from "module";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const argv = process.argv.slice(2);
const url = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
const WIDTH = parseInt(opt("--width", "375"), 10);
const EXPECT = opt("--expect", "");
const WIRE = argv.includes("--wire");
if (!url) { console.log("usage: live_read.mjs <url> [--width N] [--expect commit] [--wire]"); process.exit(2); }

let browser, code = 1;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const page = await browser.newPage({ viewport: { width: WIDTH, height: 900 } });
  await page.goto(url, { waitUntil: "load", timeout: 45000 });
  const r = await page.evaluate((wire) => {
    const meta = document.querySelector('meta[name="build-commit"]');
    const out = {
      commit: meta ? meta.content : null,
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      title: document.title,
    };
    if (wire) {
      const sec = document.querySelector("section.wl");
      const cad = document.querySelector(".ed-cadence");
      out.cadence = cad ? cad.textContent.trim() : null;
      out.wire = !!sec;
      if (sec) {
        const items = [...sec.querySelectorAll("li.wl-i")];
        out.items = items.length;
        out.head = (sec.querySelector(".bd-sec .bd-stamp") || {}).textContent || "";
        out.what = (sec.querySelector(".wl-what") || {}).textContent || "";
        out.rows = items.map(li => ({
          line: (li.querySelector(".wl-line") || {}).textContent || "",
          mark: (li.querySelector(".badge, .wl-mark") || {}).textContent || "",
          reads: (li.querySelector(".wl-reads") || {}).textContent || "",
          meta: (li.querySelector(".wl-meta") || {}).textContent || "",
          link: !!li.querySelector(".wl-meta a[href^='http']"),
          stamp: !!li.querySelector(".wl-meta .bd-stamp"),
          note: (li.querySelector(".wl-note") || {}).textContent || "",
        }));
      }
    }
    return out;
  }, WIRE);
  console.log(JSON.stringify({ url, width: WIDTH, ...r }, null, 1));
  const ok = (!EXPECT || (r.commit || "").startsWith(EXPECT)) && r.overflow <= 0 &&
    (!WIRE || (r.wire && r.items > 0 && r.rows.every(x => x.line && x.mark && x.link && x.stamp)));
  console.log(ok ? "live_read: PASS" : "live_read: FAIL");
  code = ok ? 0 : 1;
} catch (e) {
  console.log(`live_read: ERROR ${e && e.message}`);
  code = 1;
} finally {
  if (browser) await browser.close().catch(() => {});
}
process.exit(code);
