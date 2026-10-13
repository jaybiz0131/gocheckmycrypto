#!/usr/bin/env node
// coin_pages_browser.mjs <built-site-dir> [--only name,name] [--all-pages]
//
// Program 7 Sprint 6.4 (13 October 2026): the browser half of the coin-page tests. It serves a
// built tree from a local port, answers CoinGecko's market_chart route from recorded fixtures
// (fixtures/coingecko/*.json) or from shaped series where a test needs a window to run the
// opposite way to the 24-hour badge, and prints one line per check:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//
// Exit 1 when any check fails. Nothing leaves the machine: every other host is aborted.
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FIX = path.join(HERE, "..", "fixtures", "coingecko");
const argv = process.argv.slice(2);
const dir = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
if (!dir) { console.log("usage: coin_pages_browser.mjs <built-site-dir> [--only a,b] [--all-pages]"); process.exit(2); }
const ONLY = opt("--only", "").split(",").filter(Boolean);
const ALL_PAGES = argv.includes("--all-pages");

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2", ".xml": "application/xml" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let f = path.join(root, p);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = fs.existsSync(path.join(f, "index.html")) ? path.join(f, "index.html") : f + ".html";
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;

// ---- the data the page's chart asks CoinGecko for ----------------------------------------
const DAY = 86400000, NOW = 1791830000000;
function shaped(n, step, f) {                       // [[ms, price]], oldest first, f(i/(n-1)) in 0..1
  const prices = [], vols = [];
  for (let i = 0; i < n; i++) {
    prices.push([NOW - (n - 1 - i) * step, f(i / (n - 1))]);
    vols.push([NOW - (n - 1 - i) * step, 1e8 + ((i * 7919) % 50) * 1e6]);
  }
  return { prices, total_volumes: vols, market_caps: prices };
}
// "aptos" is the coin whose windows run in different directions: 1D up, 7D down, and a year
// that rose until the last month and then fell, so 1M is down and 1Y is up.
function synthetic(days) {
  if (days === 1) return shaped(289, 300000, t => 0.90 + 0.04 * t);
  if (days === 7) return shaped(169, 3600000, t => 0.95 - 0.08 * t);
  return shaped(366, DAY, t => (t < 0.915 ? 0.30 + 0.90 * (t / 0.915) : 1.20 - 0.40 * ((t - 0.915) / 0.085)));
}
function recorded(id, days) {
  const f = (id) => path.join(FIX, `${id}-${days}.json`);
  const use = fs.existsSync(f(id)) ? id : "bitcoin";
  return JSON.parse(fs.readFileSync(f(use), "utf8"));
}
let cgRequests = [];
async function route(page, mode) {
  await page.route(/^https?:/, async r => {
    const u = new URL(r.request().url());
    if (u.host === new URL(base).host) return r.continue();
    if (u.host === "api.coingecko.com") {
      cgRequests.push(u.pathname + u.search);
      const m = u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      const days = parseInt(u.searchParams.get("days") || "7", 10);
      if (m) {
        const body = (mode === "shaped" && m[1] === "aptos") ? synthetic(days) : recorded(m[1], days <= 1 ? 1 : days <= 7 ? 7 : 365);
        return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(body) });
      }
    }
    return r.abort();
  });
}

// ---- the checks --------------------------------------------------------------------------
const results = [];
const check = (name, ok, detail = "") => { results.push([name, ok, detail]); console.log(ok ? `PASS ${name}` : `FAIL ${name}: ${detail}`); };
const want = name => !ONLY.length || ONLY.some(o => name.startsWith(o));
const overflow = page => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const tab = (page, r) => page.locator(`[data-coin-chart] [role=tab][data-range="${r}"]`);
async function pick(page, r) {
  await tab(page, r).click();
  await page.waitForFunction(rr => document.querySelector("[data-coin-chart]")?.getAttribute("data-range") === rr
    && !!document.querySelector("[data-coin-chart] svg.cc-svg"), r, { timeout: 8000 });
  await page.waitForTimeout(60);
}

let browser;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const mk = async (w = 375, extra = {}) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, ...extra });
    const page = await ctx.newPage();
    page.setDefaultTimeout(7000);
    return [ctx, page];
  };

  // 1. each chart is colored by its own window
  if (want("chart-own-window")) {
    const [ctx, page] = await mk();
    await route(page, "shaped");
    await page.goto(base + "/coins/apt", { waitUntil: "load" });
    const seen = {};
    try {
      for (const r of ["1d", "7d", "1m", "1y"]) {
        await pick(page, r);
        seen[r] = await page.evaluate(() => {
          const l = document.querySelector("[data-coin-chart] .cc-line");
          const c = document.querySelector("[data-coin-chart] .cc-chg");
          return { dir: l && l.getAttribute("data-dir"), cls: l && l.getAttribute("class"),
                   chg: c && c.textContent.trim(), chgDir: c && c.getAttribute("data-dir"),
                   stroke: l && getComputedStyle(l).stroke };
        });
      }
    } catch (e) { seen.error = String(e).slice(0, 120); }
    const exp = { "1d": "up", "7d": "down", "1m": "down", "1y": "up" };
    const bad = Object.entries(exp).filter(([r, d]) => !seen[r] || seen[r].dir !== d || seen[r].chgDir !== d
      || !(seen[r].cls || "").includes(d)
      || (d === "down" ? !/^[-−]/.test(seen[r].chg || "") : !/^\+/.test(seen[r].chg || "")));
    check("chart-own-window: line and printed change take the window's own direction, recolored per tab",
      !bad.length, JSON.stringify(seen).slice(0, 400));
    const strokes = new Set(["1d", "7d"].map(r => seen[r]?.stroke));
    check("chart-own-window: the stroke color really differs between an up and a down window", strokes.size === 2, [...strokes].join(" | "));
    await ctx.close();
  }

  // 2. the 50-day and 200-day lines only on 1M and 1Y
  if (want("chart-averages")) {
    const [ctx, page] = await mk();
    await route(page, "recorded");
    await page.goto(base + "/coins/btc", { waitUntil: "load" });
    const out = {};
    try {
      for (const r of ["1d", "7d", "1m", "1y"]) {
        await pick(page, r);
        out[r] = await page.evaluate(() => [...document.querySelectorAll("[data-coin-chart] .cc-ma")]
          .map(e => ({ ma: e.getAttribute("data-ma"), tag: e.tagName.toLowerCase(), curves: ((e.getAttribute("d") || "").match(/C/g) || []).length,
            dash: getComputedStyle(e).strokeDasharray })));
        out[r + "_labels"] = await page.evaluate(() => [...document.querySelectorAll("[data-coin-chart] .cc-ma-label")].map(e => e.textContent.trim()));
        // the labels sit in the right gutter: right of the plot, right of the price labels, inside the svg, never on a line
        out[r + "_gutter"] = await page.evaluate(() => {
          const svg = document.querySelector("[data-coin-chart] svg.cc-svg").getBoundingClientRect();
          const labs = [...document.querySelectorAll("[data-coin-chart] .cc-ma-label")].map(e => e.getBoundingClientRect());
          const px = [...document.querySelectorAll("[data-coin-chart] text.cc-ax[data-axis=price]")].map(e => e.getBoundingClientRect());
          const grid = [...document.querySelectorAll("[data-coin-chart] .cc-grid")].map(e => e.getBoundingClientRect());
          const plotRight = Math.max(...grid.map(g => g.right));
          const lines = [...document.querySelectorAll("[data-coin-chart] .cc-ma, [data-coin-chart] .cc-line")].map(e => e.getBoundingClientRect());
          const hit = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
          return { n: labs.length, inside: labs.every(l => l.left >= svg.left && l.right <= svg.right - 1),
            beyondPlot: labs.every(l => l.left >= plotRight), clearOfPrices: labs.every(l => px.every(q => !hit(l, q))),
            clearOfLines: labs.every(l => lines.every(b => !(l.left < b.right && b.left < l.right))),
            apart: labs.every((l, i) => labs.every((m, j) => i === j || !hit(l, m))) };
        });
      }
    } catch (e) { out.error = String(e).slice(0, 120); }
    const ok = !out.error && out["1d"].length === 0 && out["7d"].length === 0 && out["1m"].length === 2 && out["1y"].length === 2
      && out["1m"].every(m => m.dash && m.dash !== "none")
      && out["1y_labels"].includes("50D") && out["1y_labels"].includes("200D") && out["1m_labels"].includes("50D") && out["1m_labels"].includes("200D");
    check("chart-averages: dashed 50-day and 200-day lines, labeled, on 1M and 1Y only", ok, JSON.stringify(out).slice(0, 400));
    const smoothOk = !out.error && ["1m", "1y"].every(r => out[r].every(m => m.tag === "path" && m.curves >= 10));
    check("chart-averages: each average is one smooth curve through the daily values, never a zig-zag polyline", smoothOk, JSON.stringify([out["1m"], out["1y"]]).slice(0, 300));
    const gutOk = !out.error && ["1m", "1y"].every(r => { const g = out[r + "_gutter"]; return g.n === 2 && g.inside && g.beyondPlot && g.clearOfPrices && g.clearOfLines && g.apart; });
    check("chart-averages: labels sit in the right gutter beside the price axis, inside the chart, never on a line or a price label", gutOk, JSON.stringify([out["1m_gutter"], out["1y_gutter"]]));
    await ctx.close();
  }

  // 3. the tabs, the axes, volume, the readout
  if (want("chart-anatomy")) {
    const [ctx, page] = await mk();
    await route(page, "recorded");
    await page.goto(base + "/coins/btc", { waitUntil: "load" });
    let a = {};
    try {
      await pick(page, "1y");
      a = await page.evaluate(() => {
        const q = s => [...document.querySelectorAll("[data-coin-chart] " + s)];
        const box = e => { const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; };
        const labs = q("text.cc-ax");
        const px = labs.filter(e => e.getAttribute("data-axis") === "price");
        const dt = labs.filter(e => e.getAttribute("data-axis") === "date");
        const boxes = labs.map(box);
        let overlap = 0;
        for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
          const A = boxes[i], B = boxes[j];
          if (A.x < B.x + B.w && B.x < A.x + A.w && A.y < B.y + B.h && B.y < A.y + A.h) overlap++;
        }
        const svg = document.querySelector("[data-coin-chart] svg.cc-svg").getBoundingClientRect();
        return { tabs: q("[role=tab]").map(e => box(e)), price: px.length, dates: dt.length,
          pxSize: Math.min(...px.map(e => parseFloat(getComputedStyle(e).fontSize))),
          pxFont: px[0] && getComputedStyle(px[0]).fontFamily, overlap,
          pxRight: px.every(e => box(e).x > svg.x + svg.width * 0.6),
          vol: q(".cc-vol rect").length, volUp: q(".cc-vol rect.up").length, volDown: q(".cc-vol rect.down").length,
          hi: q(".gl-hi").length, lo: q(".gl-lo").length, now: q(".gl-now").length,
          hilabels: q("text.cc-hl").length, area: q(".cc-area").length,
          lineW: getComputedStyle(document.querySelector("[data-coin-chart] .cc-line")).strokeWidth };
      });
    } catch (e) { a.error = String(e).slice(0, 120); }
    check("chart-anatomy: four tabs of at least 44 px", !a.error && a.tabs.length === 4 && a.tabs.every(t => t.h >= 43.5 && t.w >= 43.5), JSON.stringify(a.tabs || a.error));
    check("chart-anatomy: price labels on the right in mono at 12 px or more", !a.error && a.price >= 3 && a.pxSize >= 12 && /mono/i.test(a.pxFont || "") && a.pxRight, `n=${a.price} size=${a.pxSize} font=${a.pxFont} right=${a.pxRight}`);
    check("chart-anatomy: three to five date labels, no label overlaps another at 375", !a.error && a.dates >= 3 && a.dates <= 5 && a.overlap === 0, `dates=${a.dates} overlap=${a.overlap}`);
    check("chart-anatomy: volume bars carry up and down by that period's close", !a.error && a.vol > 100 && a.volUp > 0 && a.volDown > 0, `vol=${a.vol} up=${a.volUp} down=${a.volDown}`);
    const vols = {};
    try {
      for (const r of ["1d", "7d", "1m", "1y"]) {
        await pick(page, r);
        vols[r] = await page.evaluate(() => ({ bars: document.querySelectorAll("[data-coin-chart] .cc-vol rect").length,
          cap: (document.querySelector("[data-coin-cap]") || {}).textContent || "" }));
      }
    } catch (e) { vols.error = String(e).slice(0, 120); }
    check("chart-volume: bars on 1M and 1Y only (daily volumes); none on 1D and 7D, and the caption says nothing of them there",
      !vols.error && vols["1d"].bars === 0 && vols["7d"].bars === 0 && vols["1m"].bars >= 20 && vols["1y"].bars > 100
      && !/volume/i.test(vols["1d"].cap) && !/volume/i.test(vols["7d"].cap) && /each day/i.test(vols["1y"].cap), JSON.stringify(vols).slice(0, 400));
    check("chart-anatomy: Program 7 line (3 px, glow, area, high/low dots with labels, last-point halo)", !a.error && parseFloat(a.lineW) === 3 && a.hi >= 1 && a.lo >= 1 && a.now === 1 && a.hilabels >= 2 && a.area === 1, JSON.stringify(a).slice(0, 300));
    await ctx.close();
  }

  // 4. crosshair: touch, hover, keyboard; the readout stays in the box
  if (want("chart-readout")) {
    const [ctx, page] = await mk(375, { hasTouch: true });
    await route(page, "recorded");
    await page.goto(base + "/coins/btc", { waitUntil: "load" });
    let r = {};
    try {
      await pick(page, "7d");
      const wrap = await page.locator("[data-coin-chart] .cc-box").boundingBox();
      const svgb = await page.locator("[data-coin-chart] svg.cc-svg").boundingBox();
      const edges = [0.97, 0.5, 0.03];
      r.reads = [];
      for (const f of edges) {
        const x = svgb.x + svgb.width * f, y = svgb.y + svgb.height * 0.4;
        // a touch: dispatch pointer events the way a finger on a phone does
        await page.evaluate(({ x, y }) => {
          const s = document.querySelector("[data-coin-chart] svg.cc-svg");
          const o = { clientX: x, clientY: y, pointerType: "touch", pointerId: 7, bubbles: true, isPrimary: true };
          s.dispatchEvent(new PointerEvent("pointerdown", o)); s.dispatchEvent(new PointerEvent("pointermove", o));
        }, { x, y });
        r.reads.push(await page.evaluate(() => {
          const e = document.querySelector("[data-coin-chart] .cc-readout"), b = e.getBoundingClientRect(), w = document.querySelector("[data-coin-chart] .cc-box").getBoundingClientRect();
          return { text: e.textContent.trim(), hidden: e.hidden || getComputedStyle(e).display === "none", inside: b.left >= w.left - 0.5 && b.right <= w.right + 0.5 && b.top >= w.top - 0.5 && b.bottom <= w.bottom + 0.5 };
        }));
      }
      // keyboard: focus the chart, step with the arrows
      await page.evaluate(() => document.querySelector("[data-coin-chart] .cc-box").focus());
      await page.keyboard.press("End"); const k1 = await page.locator("[data-coin-chart] .cc-readout").textContent();
      await page.keyboard.press("ArrowLeft"); const k2 = await page.locator("[data-coin-chart] .cc-readout").textContent();
      r.kbd = k1 !== k2;
    } catch (e) { r.error = String(e).slice(0, 120); }
    try {
      await pick(page, "1y");
      const sb = await page.locator("[data-coin-chart] svg.cc-svg").boundingBox();
      await page.evaluate(({ x, y }) => {
        const s = document.querySelector("[data-coin-chart] svg.cc-svg");
        s.dispatchEvent(new PointerEvent("pointerdown", { clientX: x, clientY: y, pointerType: "touch", pointerId: 8, bubbles: true, isPrimary: true }));
      }, { x: sb.x + sb.width * 0.5, y: sb.y + sb.height * 0.4 });
      r.daily = (await page.locator("[data-coin-chart] .cc-readout").textContent()).trim();
    } catch (e) { r.error = String(e).slice(0, 120); }
    const good = !r.error && r.reads.every(x => !x.hidden && x.inside && /\$[\d,]+/.test(x.text) && /\d/.test(x.text) && !/vol/i.test(x.text)) && /vol/i.test(r.daily || "");
    check("chart-readout: a touch shows price and date (and volume on the daily windows), and never leaves the chart box", good, JSON.stringify(r).slice(0, 400));
    check("chart-readout: keyboard users step through points", !r.error && r.kbd === true, JSON.stringify(r).slice(0, 200));
    await ctx.close();
  }

  // 5. no storage, motion drawn once, reduced motion whole
  if (want("chart-session-motion")) {
    const [ctx, page] = await mk();
    await route(page, "recorded");
    await page.goto(base + "/coins/btc", { waitUntil: "load" });
    let m = {};
    try {
      await pick(page, "7d");
      const before = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie]);
      await pick(page, "1m");
      await page.setViewportSize({ width: 360, height: 900 }); await page.waitForTimeout(400);
      m.after = await page.evaluate(() => [localStorage.length, sessionStorage.length, document.cookie, document.querySelector("[data-coin-chart]").getAttribute("data-range")]);
      m.before = before;
      m.infinite = await page.evaluate(() => document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity).length);
    } catch (e) { m.error = String(e).slice(0, 120); }
    check("chart-session: the chosen window is kept across a redraw, with nothing written to storage or cookies",
      !m.error && m.after[3] === "1m" && m.after[0] === m.before[0] && m.after[1] === m.before[1] && m.after[2] === m.before[2], JSON.stringify(m));
    check("chart-motion: nothing loops", !m.error && m.infinite === 0, JSON.stringify(m));
    await ctx.close();
    const [ctx2, page2] = await mk(375, { reducedMotion: "reduce" });
    await route(page2, "recorded");
    await page2.goto(base + "/coins/btc", { waitUntil: "load" });
    let rm = {};
    try {
      await page2.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 8000 });
      rm = await page2.evaluate(() => { const l = document.querySelector("[data-coin-chart] .cc-line"); const cs = getComputedStyle(l);
        return { anim: document.getAnimations().length, off: cs.strokeDashoffset, dash: cs.strokeDasharray, op: cs.opacity }; });
    } catch (e) { rm.error = String(e).slice(0, 120); }
    check("chart-motion: with reduced motion the line is whole at once", !rm.error && rm.anim === 0 && (rm.dash === "none" || parseFloat(rm.off) === 0), JSON.stringify(rm));
    await ctx2.close();
  }

  // 6. the Top 100: search, sparklines, columns, the row as the target
  if (want("top100")) {
    const [ctx, page] = await mk();
    await route(page, "recorded");
    await page.goto(base + "/pulse/prices", { waitUntil: "load" });
    const visible = () => page.evaluate(() => [...document.querySelectorAll(".prices-table tbody tr")].filter(r => r.offsetParent !== null && !r.hidden).length);
    let s = {};
    try {
      s.total = await visible();
      cgRequests = []; const reqs = []; page.on("request", q => reqs.push(q.url()));
      await page.locator("input[data-coin-search]").fill("bit");
      await page.waitForTimeout(150);
      s.bit = await page.evaluate(() => [...document.querySelectorAll(".prices-table tbody tr")].filter(r => !r.hidden).map(r => r.textContent.toLowerCase()));
      s.net = reqs.length;
      await page.locator("input[data-coin-search]").fill("zzzzqq");
      await page.waitForTimeout(150);
      s.none = await visible();
      s.msg = await page.evaluate(() => { const e = document.querySelector("[data-coin-empty]"); return e && !e.hidden ? e.textContent.trim() : null; });
      await page.locator("[data-coin-empty] button, [data-coin-clear]").first().click();
      await page.waitForTimeout(150);
      s.cleared = await visible(); s.value = await page.locator("input[data-coin-search]").inputValue();
      await page.locator("input[data-coin-search]").fill("ETH"); await page.waitForTimeout(120);
      s.eth = await page.evaluate(() => [...document.querySelectorAll(".prices-table tbody tr")].filter(r => !r.hidden).length);
    } catch (e) { s.error = String(e).slice(0, 120); }
    check("top100-search: filters by name or ticker as you type, with no network call",
      !s.error && s.total === 100 && s.bit.length >= 1 && s.bit.length < 100 && s.bit.every(t => t.includes("bit")) && s.net === 0 && s.eth >= 1, JSON.stringify({ ...s, bit: s.bit && s.bit.length }));
    check("top100-search: an empty result says \"No coin matches\" and the clear button restores the list",
      !s.error && s.none === 0 && /No coin matches/.test(s.msg || "") && s.cleared === 100 && s.value === "", JSON.stringify({ none: s.none, msg: s.msg, cleared: s.cleared, value: s.value }));

    let c = {};
    try {
      await page.goto(base + "/pulse/prices", { waitUntil: "load" });
      c = await page.evaluate(() => {
        const rows = [...document.querySelectorAll(".prices-table tbody tr")];
        const spark = rows.map(r => r.querySelector(".row-spark"));
        const bad = [];
        spark.forEach((s, i) => {
          if (!s) { bad.push(`row ${i + 1} has no line`); return; }
          const pts = (s.querySelector("polyline")?.getAttribute("points") || "").trim().split(/\s+/).map(p => parseFloat(p.split(",")[1]));
          const dir = pts.length > 1 ? (pts[pts.length - 1] < pts[0] ? "up" : pts[pts.length - 1] > pts[0] ? "down" : "flat") : null; // SVG y runs down
          const tag = s.getAttribute("data-dir");
          const stroke = getComputedStyle(s.querySelector("polyline")).stroke;
          if (dir && tag !== dir) bad.push(`row ${i + 1}: drawn ${dir}, tagged ${tag}`);
          if (s.querySelector("[filter], filter")) bad.push(`row ${i + 1}: glow at sparkline size`);
          s._stroke = stroke;
        });
        const strokes = new Set(spark.filter(Boolean).map(s => getComputedStyle(s.querySelector("polyline")).stroke));
        return { n: rows.length, bad: bad.slice(0, 5), nbad: bad.length, strokes: strokes.size };
      });
    } catch (e) { c.error = String(e).slice(0, 120); }
    check("top100-sparkline: each row's line is colored by its own seven days, with no glow", !c.error && c.n === 100 && c.nbad === 0 && c.strokes >= 2, JSON.stringify(c).slice(0, 300));

    let k = {};
    try {
      k = await page.evaluate(() => {
        const vis = sel => [...document.querySelectorAll(".prices-table thead " + sel)].filter(e => e.offsetParent !== null).map(e => e.textContent.trim());
        return { heads: [...document.querySelectorAll(".prices-table thead th")].filter(e => getComputedStyle(e).display !== "none").map(e => e.textContent.trim()),
          overflow: document.documentElement.scrollWidth - window.innerWidth };
      });
    } catch (e) { k.error = String(e).slice(0, 120); }
    const norm = h => h.map(x => x.replace(/[↑↓]/g, "").trim().toLowerCase());
    check("top100-columns: at 375 rank, coin, price, 24h and the seven-day line only, and no sideways scroll",
      !k.error && JSON.stringify(norm(k.heads)) === JSON.stringify(["#", "coin", "price", "24h", "7d"]) && k.overflow <= 0, JSON.stringify(k));
    let g = {};
    try {
      g = await page.evaluate(() => {
        const rows = [...document.querySelectorAll(".prices-table tbody tr")];
        const gaps = rows.map(r => {
          const pc = r.querySelector("td.pnum"), ch = r.querySelector("td:nth-child(4) .chip");
          const range = document.createRange(); range.selectNodeContents(pc);
          const t = range.getBoundingClientRect(), c = ch.getBoundingClientRect();
          return { gap: c.left - t.right, textRight: t.right, cellRight: pc.getBoundingClientRect().right };
        });
        return { n: gaps.length, min: Math.min(...gaps.map(x => x.gap)), worst: gaps.sort((a, b) => a.gap - b.gap)[0] };
      });
    } catch (e) { g.error = String(e).slice(0, 120); }
    check("top100-gap: at 375 the price and the 24h pill are at least 12 px apart on every row", !g.error && g.n === 100 && g.min >= 12, JSON.stringify(g));
    await page.setViewportSize({ width: 768, height: 900 });
    const wide = await page.evaluate(() => [...document.querySelectorAll(".prices-table thead th")].filter(e => getComputedStyle(e).display !== "none").map(e => e.textContent.trim().toLowerCase()));
    check("top100-columns: market cap and volume appear at 768", wide.some(t => t.includes("market cap")) && wide.some(t => t.includes("volume")), wide.join("|"));
    await page.setViewportSize({ width: 375, height: 900 });
    let t = {};
    try {
      await page.goto(base + "/pulse/prices", { waitUntil: "load" });
      const row = page.locator(".prices-table tbody tr").nth(4);
      const expect = await row.locator("a").first().getAttribute("href");
      await row.scrollIntoViewIfNeeded();
      const b = await row.locator("td.pnum").boundingBox();   // a real tap on the price, not on the name
      await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
      await page.waitForURL(u => u.pathname.startsWith("/coins/"), { timeout: 5000 });
      t = { expect, got: new URL(page.url()).pathname };
    } catch (e) { t.error = String(e).slice(0, 120); }
    check("top100-row: the whole row is the link (a click on the price opens the coin page)", !t.error && !!t.expect && (t.got === t.expect || t.got === t.expect.replace(/\.html$/, "")), JSON.stringify(t));
    await ctx.close();
  }

  // 7. no sideways scroll at 375 on every coin page and the Top 100
  if (want("no-sideways-scroll")) {
    const [ctx, page] = await mk();
    await route(page, "recorded");
    const files = fs.readdirSync(path.join(root, "coins")).filter(f => f.endsWith(".html")).sort();
    const pages = ["/pulse/prices", ...files.map(f => "/coins/" + f.replace(/\.html$/, ""))];
    const bad = [];
    for (const p of pages) {
      await page.goto(base + p, { waitUntil: "load" });
      if (p.startsWith("/coins/") && await page.locator("[data-coin-chart]").count()) await page.waitForSelector("[data-coin-chart] svg", { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(40);
      const o = await overflow(page);
      if (o > 0) bad.push(`${p} +${o}px`);
    }
    check(`no-sideways-scroll: ${pages.length} pages at 375`, bad.length === 0, bad.slice(0, 6).join(", "));
    await ctx.close();
  }
} finally {
  if (browser) await browser.close();
  server.close();
}
const failed = results.filter(r => !r[1]);
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`);
process.exit(failed.length ? 1 : 0);
