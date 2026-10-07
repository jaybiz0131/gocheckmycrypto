#!/usr/bin/env node
// home_budget.mjs <url> [--width 375] [--runs 3] [--expect <commit>] [--theme light|dark]
//                       [--shot <file.png>] [--full] [--no-throttle]
//
// The home page's budget (Program 5 section 7, Sprint 2 item 3), read in headless Chromium:
//   bytes   every byte the page moves over the network from navigation until it has been
//           quiet for 3 seconds after load, before any interaction (CDP encodedDataLength,
//           so a compressed response counts at its compressed size, as the wire carries it)
//   hosts   every host a request went to; the page's own host plus the tape's live read
//           (api.coingecko.com) are the only ones allowed, so a third host is a red
//   lcp     largest contentful paint, on a phone: Lighthouse's mobile profile, 4x CPU slowdown
//           and 150 ms RTT, 1.6 Mbps down, 750 Kbps up; the median of --runs cold loads
// It also asserts the page's <meta name="build-commit"> when --expect is given (U-10), and
// prints horizontal overflow. --shot writes a screenshot of that width and theme.
// Exit 0 only when bytes < 300 KB, no third host, and (unless --no-lcp-gate) LCP < 2500 ms.
//
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const argv = process.argv.slice(2);
const url = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
const WIDTH = parseInt(opt("--width", "375"), 10);
const RUNS = parseInt(opt("--runs", "3"), 10);
const EXPECT = opt("--expect", "");
const THEME = opt("--theme", "light");
const SHOT = opt("--shot", "");
const FULL = argv.includes("--full");
const THROTTLE = !argv.includes("--no-throttle");
const LCP_GATE = !argv.includes("--no-lcp-gate");
const BUDGET = 300 * 1024;
const LIVE_HOST = "api.coingecko.com";
if (!url) { console.log("usage: home_budget.mjs <url> [--width N] [--runs N] [--expect commit]"); process.exit(2); }
const OWN = new URL(url).host;

async function once(browser, shot) {
  const ctx = await browser.newContext({
    viewport: { width: WIDTH, height: WIDTH < 700 ? 844 : 900 },
    deviceScaleFactor: WIDTH < 700 ? 3 : 1, isMobile: WIDTH < 700, hasTouch: WIDTH < 700,
    colorScheme: THEME === "dark" ? "dark" : "light", serviceWorkers: "allow",
  });
  try {
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    if (THROTTLE) {
      await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150,
        downloadThroughput: 1.6384 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 });
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    }
    const reqs = new Map();
    let bytes = 0, last = Date.now();
    cdp.on("Network.requestWillBeSent", (e) => { reqs.set(e.requestId, e.request.url); last = Date.now(); });
    cdp.on("Network.loadingFinished", (e) => { bytes += e.encodedDataLength || 0; last = Date.now(); });
    await page.addInitScript(() => {
      window.__lcp = 0;
      new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; })
        .observe({ type: "largest-contentful-paint", buffered: true });
    });
    await page.goto(url, { waitUntil: "load", timeout: 90000 });
    while (Date.now() - last < 3000) await page.waitForTimeout(250);
    const lcp = await page.evaluate(() => window.__lcp);
    const meta = await page.evaluate(() =>
      (document.querySelector('meta[name="build-commit"]') || {}).content || "");
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const hosts = [...new Set([...reqs.values()].filter((u) => /^https?:/.test(u))
      .map((u) => new URL(u).host))];
    if (shot) {
      await page.waitForTimeout(1500);   // the line's one draw has finished
      await page.screenshot({ path: shot, fullPage: FULL });
    }
    return { bytes, lcp, meta, overflow, hosts, requests: [...reqs.values()] };
  } finally {
    await ctx.close();
  }
}

let browser, code = 1;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const runs = [];
  for (let i = 0; i < RUNS; i++) runs.push(await once(browser, i === 0 ? SHOT : ""));
  const lcps = runs.map((r) => r.lcp).sort((a, b) => a - b);
  const r0 = runs[0];
  const med = lcps[Math.floor(lcps.length / 2)];
  const third = r0.hosts.filter((h) => h !== OWN && h !== LIVE_HOST);
  const stampOk = !EXPECT || (r0.meta && r0.meta.startsWith(EXPECT.slice(0, 7)));
  console.log(JSON.stringify({
    url, width: WIDTH, theme: THEME, build_commit: r0.meta, throttled: THROTTLE,
    bytes: r0.bytes, kb: +(r0.bytes / 1024).toFixed(1), budget_kb: 300,
    lcp_ms_runs: lcps.map((x) => Math.round(x)), lcp_ms_median: Math.round(med),
    hosts: r0.hosts, third_hosts: third, requests: r0.requests.length,
    overflow_px: r0.overflow, shot: SHOT || null,
  }, null, 1));
  if (!stampOk) console.log(`STAMP: page says ${r0.meta}, expected ${EXPECT}`);
  const ok = stampOk && r0.bytes < BUDGET && third.length === 0 && (!LCP_GATE || med < 2500);
  code = ok ? 0 : 1;
} catch (e) {
  console.log(`home_budget: ${e && e.message}`);
  code = 1;
} finally {
  if (browser) await browser.close();
}
process.exit(code);
