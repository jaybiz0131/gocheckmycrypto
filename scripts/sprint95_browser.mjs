#!/usr/bin/env node
// sprint95_browser.mjs <built-site-dir>
//
// Program 9, Sprint 9.5 (20 October 2026): the browser half of scripts/sprint95_test.py. It serves a built tree
// from a local port, answers CoinGecko's market_chart route from the recorded fixtures (fixtures/coingecko), aborts
// every other host, and prints one line per check:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//
// Exit 1 when any check fails. U-7: the browser is launched with a timeout and closed in a finally block.
// The tree must hold home-fixture-card.html and home-fixture-nocard.html (sprint95_test.py writes them: the home
// built from the recorded 15 October Board with its real verdict card, and with none).
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
if (!dir) { console.log("usage: sprint95_browser.mjs <built-site-dir>"); process.exit(2); }

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

function recorded(id, days) {
  const f = (i) => path.join(FIX, `${i}-${days}.json`);
  return JSON.parse(fs.readFileSync(fs.existsSync(f(id)) ? f(id) : f("bitcoin"), "utf8"));
}
async function route(page) {
  await page.route(/^https?:/, async r => {
    const u = new URL(r.request().url());
    if (u.host === new URL(base).host) return r.continue();
    if (u.host === "api.coingecko.com") {
      const m = u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      const days = parseInt(u.searchParams.get("days") || "7", 10);
      if (m && days <= 365) {
        return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(recorded(m[1], days <= 1 ? 1 : days <= 7 ? 7 : 365)) });
      }
    }
    return r.abort();
  });
}

const results = [];
const check = (name, ok, detail = "") => { results.push([name, ok, detail]); console.log(ok ? `PASS ${name}` : `FAIL ${name}: ${detail}`); };
const base_url = u => base + u;
const exists = p => { const f = path.join(root, p.replace(/^\//, "")); return fs.existsSync(f) || fs.existsSync(f + ".html") || fs.existsSync(path.join(f, "index.html")); };

let browser;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const open = async (w, url, opts = {}) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, ...(opts.ctx || {}) });
    const page = await ctx.newPage();
    page.setDefaultTimeout(8000);
    if (opts.init) await page.addInitScript(opts.init);
    await route(page);
    await page.goto(base + url, { waitUntil: "load" });
    return [ctx, page];
  };

  // 1. THE TAB BAR: exactly five, in Jack's order, at 375 and 390; each one fits its cell and is a 44 px target
  const TABS = ["Why it moved", "Markets", "Big movers", "Whale Watch", "Brief"];
  for (const w of [375, 390]) {
    const [ctx, page] = await open(w, "/index.html");
    const t = await page.evaluate(() => {
      const bar = document.querySelector("nav.tabbar");
      const vis = bar && getComputedStyle(bar).display !== "none";
      const items = [...document.querySelectorAll("nav.tabbar .tb-item")].map(a => {
        const s = a.querySelector("span"), r = a.getBoundingClientRect();
        return { text: s.textContent.trim(), h: Math.round(r.height), fits: s.scrollWidth <= a.clientWidth, w: Math.round(r.width) };
      });
      return { vis, items };
    });
    check(`tab bar at ${w}: shown, exactly five, ${TABS.join(", ")}`,
      t.vis && JSON.stringify(t.items.map(i => i.text)) === JSON.stringify(TABS), JSON.stringify(t));
    check(`tab bar at ${w}: every label fits its cell and every tab is a 44 px target`,
      t.items.every(i => i.fits && i.h >= 44), JSON.stringify(t.items));
    await ctx.close();
  }

  // 2. THE HOME'S FIRST OBJECT, at 375 and 1440, from the recorded 15 October Board
  for (const w of [375, 1440]) {
    const [ctx, page] = await open(w, "/home-fixture-card.html");
    const r = await page.evaluate(() => {
      const top = el => el ? Math.round(el.getBoundingClientRect().top + scrollY) : null;
      const card = document.querySelector("aside.vd");
      const blocks = [...document.querySelectorAll("[data-block]")].map(b => ({ n: b.getAttribute("data-block"), top: top(b), left: !!b.closest(".h-l") }));
      const l = document.querySelector(".h-l");
      const first = l && l.firstElementChild;
      const tape = document.querySelector('[data-block="tape"]');
      return { card: top(card), cardH: card && Math.round(card.getBoundingClientRect().height), blocks,
        firstIsCard: !!first && first === card, tapeH: tape && Math.round(tape.getBoundingClientRect().height),
        tapeSvg: tape && tape.querySelectorAll("svg").length, tapeText: tape && tape.textContent.replace(/\s+/g, " ").trim() };
    });
    check(`home at ${w} with a graded card: the verdict card is first in its column, above every block in it, and no lower than the other column's first`,
      r.firstIsCard && r.card !== null && r.blocks.every(b => (b.left ? r.card < b.top : r.card <= b.top + 2)), JSON.stringify(r));
    check(`home at ${w} with a graded card: it is on the first screen (its top is within 760 px of the page top)`,
      r.card !== null && r.card < 760, `top ${r.card}`);
    check(`home at ${w}: Bitcoin is one line (the tape block is under 130 px, draws no chart, prints price and change once)`,
      r.tapeH !== null && r.tapeH <= 130 && r.tapeSvg === 0 && (r.tapeText.match(/\$[\d,]+/g) || []).length === 1, JSON.stringify({ h: r.tapeH, svg: r.tapeSvg, t: r.tapeText }));
    await ctx.close();
    const [ctx2, page2] = await open(w, "/home-fixture-nocard.html");
    const n = await page2.evaluate(() => {
      const top = el => el ? Math.round(el.getBoundingClientRect().top + scrollY) : null;
      const l = document.querySelector(".h-l");
      const first = l && l.firstElementChild;
      const tape = document.querySelector('[data-block="tape"]');
      const band = document.querySelector('[data-block="narrative"]');
      return { vd: document.querySelectorAll("aside.vd").length, firstIsTape: !!first && first === tape, firstH: first && Math.round(first.getBoundingClientRect().height),
        tape: top(tape), band: top(band), bandH: band && Math.round(band.getBoundingClientRect().height) };
    });
    check(`home at ${w} with no graded card: no card, no empty slot; the first object is the tape's line, the Brief card next`,
      n.vd === 0 && n.firstIsTape && n.firstH > 20 && n.band !== null && n.tape < n.band && n.band < 560, JSON.stringify(n));
    await ctx2.close();
  }

  // 3. CLS ON THE COIN PAGE, at zero: layout shifts from the first byte to the chart drawn and settled, with the page read
  // fresh (an hour after its build stamp) and stale (nine hours after it, when the stale state adds an age to every stamp)
  const CLS_INIT = () => {
    window.__cls = 0; window.__shifts = [];
    new PerformanceObserver(list => {
      for (const e of list.getEntries()) if (!e.hadRecentInput) {
        window.__cls += e.value;
        window.__shifts.push({ v: Math.round(e.value * 1e4) / 1e4, t: Math.round(e.startTime), n: (e.sources || []).map(s => s.node && (s.node.nodeName + "." + (s.node.className && s.node.className.baseVal !== undefined ? s.node.className.baseVal : s.node.className || ""))).slice(0, 3) });
      }
    }).observe({ type: "layout-shift", buffered: true });
  };
  const clockShim = ([base, offsetMs]) => {
    const Real = Date, start = Real.now();
    const T0 = Real.parse(base) + offsetMs;
    const now = () => T0 + (Real.now() - start);
    class FakeDate extends Real {
      constructor(...a) { if (a.length) super(...a); else super(now()); }
      static now() { return now(); }
    }
    window.Date = FakeDate;
  };
  const mastAsof = url => {
    const f = path.join(root, url.replace(/^\//, "") + (url.endsWith("/") ? "index.html" : ".html"));
    const g = fs.existsSync(f) ? f : path.join(root, url.replace(/^\//, ""));
    const m = fs.readFileSync(g, "utf8").match(/data-mh-live data-asof="([^"]+)"/);
    return m ? m[1] : null;
  };
  for (const [w, url, hours, label] of [[375, "/coins/btc", 1, "fresh"], [375, "/coins/btc", 9, "stale"], [390, "/coins/btc", 1, "fresh"],
    [390, "/coins/btc", 9, "stale"], [1440, "/coins/btc", 9, "stale"], [375, "/coins/eth", 9, "stale"]]) {
    if (!exists(url)) { check(`CLS on ${url} at ${w}, ${label}`, false, "page not built"); continue; }
    const base = mastAsof(url);
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.setDefaultTimeout(8000);
    await page.addInitScript(CLS_INIT);
    if (base) await page.addInitScript(clockShim, [base, hours * 3600e3]);
    await route(page);
    await page.goto(base_url(url), { waitUntil: "load" });
    let drawn = true;
    try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 8000 }); } catch { drawn = false; }
    await page.waitForTimeout(1500);
    const c = await page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts }));
    check(`CLS on ${url} at ${w}, read ${label} (${hours} h after its stamp): zero (the chart drew and the page settled)`,
      drawn && c.cls < 0.0005, JSON.stringify({ drawn, cls: c.cls, shifts: c.shifts.slice(0, 4) }));
    await ctx.close();
  }

  // 3b. CLS UNDER CPU THROTTLING (6x), ten reads of each page at each width, fresh and stale: the stale-state script must
  // have run before the first frame on a slow phone too, not only on a fast machine
  for (const [w, url] of [[375, "/coins/btc"], [390, "/coins/btc"], [375, "/coins/eth"], [390, "/coins/eth"]]) {
    if (!exists(url)) { check(`CLS throttled on ${url} at ${w}`, false, "page not built"); continue; }
    const base0 = mastAsof(url);
    for (const [hours, label] of [[9, "stale"], [1, "fresh"]]) {
      let bad = 0, worst = 0, first = null;
      const N = 10;
      for (let k = 0; k < N; k++) {
        const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
        const page = await ctx.newPage();
        page.setDefaultTimeout(15000);
        const cdp = await ctx.newCDPSession(page);
        await cdp.send("Emulation.setCPUThrottlingRate", { rate: 6 });
        await page.addInitScript(CLS_INIT);
        if (base0) await page.addInitScript(clockShim, [base0, hours * 3600e3]);
        await route(page);
        await page.goto(base_url(url), { waitUntil: "load" });
        try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 12000 }); } catch { /* counted below */ }
        await page.waitForTimeout(1200);
        const c = await page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts }));
        if (c.cls >= 0.0005) { bad++; worst = Math.max(worst, c.cls); first = first || c.shifts.slice(0, 3); }
        await ctx.close();
      }
      check(`CLS on ${url} at ${w}, 6x CPU throttling, read ${label}: zero in all ${N} reads`, bad === 0,
        JSON.stringify({ reads_over_zero: bad, of: N, worst, first }));
    }
  }

  // 4. CHARTS THAT READ ON A PHONE: no svg label under 12 px as drawn, at 375 and 390
  const CHART_PAGES = ["/index.html", "/today/", "/why/2026-10-15-bitcoin", "/coins/btc", "/coins/eth", "/chartmaster.html",
    "/flows.html", "/pulse.html", "/pulse/movers.html", "/pulse/sentiment.html", "/pulse/posture.html", "/pulse/prices.html",
    "/pulse/stablecoins.html", "/pulse/etf.html", "/pulse/leverage.html", "/pulse/network.html"];
  for (const w of [375, 390]) {
    const bad = [];
    for (const url of CHART_PAGES) {
      if (!exists(url)) continue;
      const [ctx, page] = await open(w, url);
      try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 2500 }); } catch { /* not a coin page */ }
      const found = await page.evaluate(() => {
        const out = [];
        for (const svg of document.querySelectorAll("svg")) {
          const r = svg.getBoundingClientRect();
          if (r.width < 40 || getComputedStyle(svg).display === "none") continue;
          const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : null;
          const scale = vb ? Math.min(r.width / vb.width, vb.height ? r.height / vb.height : 99) : 1;
          for (const t of svg.querySelectorAll("text")) {
            if (!t.textContent.trim()) continue;
            const px = parseFloat(getComputedStyle(t).fontSize) * scale;
            if (px < 11.95) out.push({ t: t.textContent.trim().slice(0, 24), px: Math.round(px * 10) / 10 });
          }
        }
        for (const el of document.querySelectorAll(".h-k, .h-days span")) {
          const px = parseFloat(getComputedStyle(el).fontSize);
          if (px < 11.95) out.push({ t: el.textContent.trim().slice(0, 24), px });
        }
        return out;
      });
      if (found.length) bad.push(`${url}: ${found.length} under 12 px, e.g. ${JSON.stringify(found[0])}`);
      await ctx.close();
    }
    check(`charts at ${w}: every axis label, tick and pin draws at 12 px or more`, bad.length === 0, bad.join(" | "));
  }

  // 4b. CONTRAST: in dark mode and in light, every svg label clears 4.5:1 against the surface under it (the card or the page)
  for (const scheme of ["dark", "light"]) {
    const bad = [];
    for (const url of CHART_PAGES) {
      if (!exists(url)) continue;
      const ctx = await browser.newContext({ viewport: { width: 375, height: 900 }, deviceScaleFactor: 1, colorScheme: scheme });
      const page = await ctx.newPage();
      page.setDefaultTimeout(8000);
      await route(page);
      await page.goto(base + url, { waitUntil: "load" });
      try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 2500 }); } catch { /* not a coin page */ }
      const found = await page.evaluate(() => {
        const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(",").map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
        const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
        const out = [];
        for (const svg of document.querySelectorAll("svg")) {
          const r = svg.getBoundingClientRect();
          if (r.width < 40 || getComputedStyle(svg).display === "none" || svg.closest("[hidden]")) continue;
          let bg = null;
          for (let e = svg.parentElement; e && !bg; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0.5) bg = c; }
          if (!bg) bg = { r: 255, g: 255, b: 255, a: 1 };
          for (const t of svg.querySelectorAll("text")) {
            if (!t.textContent.trim()) continue;
            const cs = getComputedStyle(t);
            const f = parse(cs.fill);
            if (!f) continue;
            const a = f.a * parseFloat(cs.opacity || 1) * parseFloat(cs.fillOpacity || 1);
            const mix = { r: f.r * a + bg.r * (1 - a), g: f.g * a + bg.g * (1 - a), b: f.b * a + bg.b * (1 - a) };
            const l1 = lum(mix), l2 = lum(bg);
            const cr = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
            if (cr < 4.5) out.push({ t: t.textContent.trim().slice(0, 18), cr: Math.round(cr * 100) / 100 });
          }
        }
        return out;
      });
      if (found.length) bad.push(`${url}: ${found.length} under 4.5:1, e.g. ${JSON.stringify(found[0])}`);
      await ctx.close();
    }
    check(`chart labels in ${scheme} mode: every svg label clears 4.5:1 against its surface`, bad.length === 0, bad.join(" | "));
  }

  // 5. TABLES THAT FIT 375: the Big movers list and Whale Watch by exchange, with the rest behind a tap
  for (const url of ["/movers-fixture.html", "/flows.html"]) {
    if (!exists(url)) continue;
    const [ctx, page] = await open(375, url);
    const t = await page.evaluate(() => {
      const wraps = [...document.querySelectorAll(".fit-tbl")];
      return wraps.map(w => {
        const tb = w.querySelector("table");
        const hidden = [...w.querySelectorAll(".xs-x")].every(c => getComputedStyle(c).display === "none");
        return { fits: tb.scrollWidth <= w.clientWidth + 1, hidden, n: w.querySelectorAll(".xs-x").length,
                 toggle: !!(w.previousElementSibling && w.previousElementSibling.classList.contains("fit-more")) };
      });
    });
    check(`${url} at 375: the table fits its box with its secondary columns hidden, and a toggle sits before it`,
      t.length > 0 && t.every(x => x.fits && x.hidden && x.n > 0 && x.toggle), JSON.stringify(t));
    const label = await page.$(".fit-more");
    if (label) {
      await label.click();
      const shown = await page.evaluate(() => [...document.querySelectorAll(".fit-tbl")][0]
        && [...document.querySelectorAll(".fit-tbl")][0].querySelectorAll(".xs-x").length > 0
        && [...document.querySelectorAll(".fit-tbl")][0].querySelector(".xs-x") && getComputedStyle([...document.querySelectorAll(".fit-tbl")][0].querySelector(".xs-x")).display !== "none");
      check(`${url} at 375: the toggle brings the hidden columns back`, !!shown, "still hidden after the tap");
    }
    const sw = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    check(`${url} at 375: the page does not scroll sideways`, sw <= 0, `overflow ${sw}`);
    await ctx.close();
    const [ctx2, page2] = await open(1440, url);
    const wide = await page2.evaluate(() => { const m = document.querySelector(".fit-more");
      return !!m && [...document.querySelectorAll(".fit-tbl .xs-x")].every(c => getComputedStyle(c).display !== "none")
        && getComputedStyle(m).display === "none"; });
    check(`${url} at 1440: every column shows and the toggle is not drawn`, wide, "a column is hidden or the toggle shows");
    await ctx2.close();
  }

  // 5b. the liquidations table on the leverage page (when the Board carries liquidations): the same rule
  if (exists("/pulse/leverage.html")) {
    const [ctx, page] = await open(375, "/pulse/leverage.html");
    const t = await page.evaluate(() => [...document.querySelectorAll(".fit-tbl")].map(w => ({
      fits: w.querySelector("table").scrollWidth <= w.clientWidth + 1,
      hidden: [...w.querySelectorAll(".xs-x")].every(c => getComputedStyle(c).display === "none"),
      toggle: !!(w.previousElementSibling && w.previousElementSibling.classList.contains("fit-more")) })));
    const any = await page.evaluate(() => [...document.querySelectorAll(".movetable")].filter(w => w.querySelector("table").scrollWidth > w.clientWidth + 1).length);
    check("/pulse/leverage.html at 375: no table scrolls sideways inside its box (liquidations: the rule, when the Board carries them)",
      any === 0 && t.every(x => x.fits && x.hidden && x.toggle), JSON.stringify({ any, t }));
    await ctx.close();
  }

  // 6. NO PAGE SCROLLS SIDEWAYS at 375 or 390
  for (const w of [375, 390]) {
    const bad = [];
    for (const url of ["/index.html", "/home-fixture-card.html", "/today/", "/coins/btc", "/pulse.html", "/pulse/movers.html", "/movers-fixture.html", "/flows.html",
      "/bottom-line.html", "/method.html", "/corrections.html", "/about.html", "/record.html", "/learn.html", "/chartmaster.html", "/news.html"]) {
      if (!exists(url)) continue;
      const [ctx, page] = await open(w, url);
      const sw = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (sw > 0) bad.push(`${url} +${sw}`);
      await ctx.close();
    }
    check(`no horizontal page scroll at ${w}`, bad.length === 0, bad.join(", "));
  }

  // 7. THE BRIEF ARCHIVE IS A MONTH TO A PAGE
  {
    const [ctx, page] = await open(375, "/bottom-line.html");
    const b = await page.evaluate(() => ({ entries: document.querySelectorAll(".bl-hist").length,
      months: document.querySelectorAll(".bl-months a").length, h: document.documentElement.scrollHeight }));
    check("Brief archive at 375: one month of entries and a list of months (not every Brief on one page)",
      b.entries > 0 && b.entries <= 70 && b.months >= 2 && b.h < 40000, JSON.stringify(b));
    await ctx.close();
  }
} catch (e) {
  check("browser run", false, String(e).slice(0, 300));
} finally {
  if (browser) await browser.close();
  server.close();
}
const failed = results.filter(r => !r[1]);
console.log(`\nSPRINT 9.5 BROWSER: ${failed.length ? "FAIL" : "PASS"} (${results.length - failed.length} of ${results.length} checks hold)`);
process.exit(failed.length ? 1 : 0);
