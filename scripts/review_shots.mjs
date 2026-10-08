#!/usr/bin/env node
// review_shots.mjs <url> <outdir> [--expect <commit>]
//
// The four review captures of the home page: 390 and 1440 wide, light and dark, full page,
// written as home-<width>-<theme>.png. Asserts the page's build-commit meta when --expect is
// given (U-10) and prints, per capture, the stamp it read, the tape's stamp line and the
// width's horizontal overflow. The tape's line is captured after its one draw has finished.
//
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const [url, outdir] = process.argv.slice(2);
const i = process.argv.indexOf("--expect");
const EXPECT = i > -1 ? process.argv[i + 1] : "";
if (!url || !outdir) { console.log("usage: review_shots.mjs <url> <outdir> [--expect commit]"); process.exit(2); }

let browser, code = 1;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  let ok = true;
  for (const width of [390, 1440]) {
    for (const theme of ["light", "dark"]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 },
        deviceScaleFactor: width < 700 ? 2 : 1, colorScheme: theme });
      try {
        const page = await ctx.newPage();
        await page.goto(url, { waitUntil: "load", timeout: 60000 });
        await page.waitForTimeout(2500);
        const meta = await page.evaluate(() =>
          (document.querySelector('meta[name="build-commit"]') || {}).content || "");
        const tape = await page.evaluate(() =>
          ((document.getElementById("tapeLive") || {}).textContent || "").trim());
        const over = await page.evaluate(() =>
          document.documentElement.scrollWidth - document.documentElement.clientWidth);
        const file = `${outdir}/home-${width}-${theme}.png`;
        await page.screenshot({ path: file, fullPage: true });
        const good = !EXPECT || meta.startsWith(EXPECT.slice(0, 7));
        ok = ok && good;
        console.log(JSON.stringify({ file, width, theme, build_commit: meta, tape_stamp: tape,
          overflow_px: over, stamp_ok: good }));
      } finally {
        await ctx.close();
      }
    }
  }
  code = ok ? 0 : 1;
} catch (e) {
  console.log(`review_shots: ${e && e.message}`);
} finally {
  if (browser) await browser.close();
}
process.exit(code);
