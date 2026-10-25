#!/usr/bin/env node
// sprint97_browser.mjs <built-site-dir>
//
// Program 9, Sprint 9.7 (21 October 2026): the browser half of scripts/sprint97_test.py. It serves a built tree from a local
// port and answers every other host from a stub: CoinGecko (the page's own price read, SYNTHETIC numbers a stub of its
// shape: 11,111.11), the Worker route (a stub of the shape worker/live-prices.mjs returns: 22,222.22), and nothing else (every
// other host is refused, which is how "no network" is made). It prints one line per check:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//     INFO <name>: <a measurement, not a verdict>
//
// Exit 1 when any check fails. U-7: the browser is launched with a timeout and closed in a finally block.
//
//  1. THE WATCHLIST (the Top 100 page): works with every third host refused and no cookie; nothing is requested by it;
//     removing a coin updates the one stored list; a corrupt or unavailable store hides it and throws nothing; a coin
//     page's Pin writes the list the Top 100 shows; CLS is zero with and without saved coins at 375 and 1440.
//  2. THE COIN PAGE: exactly one h1, with the look the h2 had (computed, in both schemes).
//  3. THE LIVE ROUTE: absent (today's page, no route address), present and answering (the route's numbers show and CoinGecko
//     is not asked), and present but failing in each way (404, 500, refused, malformed, stale, no Bitcoin price, hung):
//     the CoinGecko numbers show on the home tape (the one page that reads a live price; no page renders the ticker strip).
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
const dir = process.argv[2];
if (!dir) { console.log("usage: sprint97_browser.mjs <built-site-dir>"); process.exit(2); }

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
  const ct = MIME[path.extname(f)] || "application/octet-stream";
  if (f.endsWith(".html") && new URL(req.url, "http://x").searchParams.get("slow") === "1") {
    // a slow network, deterministically: the first part (to the end of the Top 100 table) is sent, the browser paints it, and the
    // rest arrives 700 ms later. Anything a script at the end of the page changes after that moves what was painted.
    const html = fs.readFileSync(f, "utf8"), cut = html.indexOf("</table></div>") + "</table></div>".length;
    res.writeHead(200, { "content-type": ct });
    res.write(html.slice(0, cut));
    return setTimeout(() => res.end(html.slice(cut)), 700);
  }
  res.writeHead(200, { "content-type": ct });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const BASE_HOST = new URL(base).host;
const WORKER = "https://worker.test/live/prices";

const results = [];
const check = (name, ok, detail = "") => { results.push([name, ok, detail]); console.log(ok ? `PASS ${name}` : `FAIL ${name}: ${detail}`); };
const info = (name, detail) => console.log(`INFO ${name}: ${detail}`);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const CG_SIMPLE = { bitcoin: { usd: 11111.11, usd_24h_change: 1.5 }, ethereum: { usd: 2222.22, usd_24h_change: 0.5 },
  solana: { usd: 111.11, usd_24h_change: -0.5 }, ripple: { usd: 1.1111, usd_24h_change: 0.1 } };
const CG_GLOBAL = { data: { total_market_cap: { usd: 2.5e12 }, market_cap_change_percentage_24h_usd: 1.1, market_cap_percentage: { btc: 58.3 } } };
const RT_SIMPLE = { bitcoin: { usd: 22222.22, usd_24h_change: -2.5 }, ethereum: { usd: 3333.33, usd_24h_change: -1.5 },
  solana: { usd: 222.22, usd_24h_change: -1.0 }, ripple: { usd: 2.2222, usd_24h_change: -0.2 } };
const RT_GLOBAL = { data: { total_market_cap: { usd: 3e12 }, market_cap_change_percentage_24h_usd: -2.0, market_cap_percentage: { btc: 61.2 } } };
const ROUTE_BODY = { schema: "gocheckmycrypto.com/live-prices/1", as_of_utc: "2026-10-21T05:00:00Z", stale: false, cache_seconds: 60,
  source: "SYNTHETIC stub of the route's shape", simple: RT_SIMPLE, global: RT_GLOBAL };
const CORS = { "access-control-allow-origin": "*" };

function recorded(id, days) {
  const f = (i) => path.join(FIX, `${i}-${days}.json`);
  return JSON.parse(fs.readFileSync(fs.existsSync(f(id)) ? f(id) : f("bitcoin"), "utf8"));
}

// opts.meta: add the route address to the page's head (the build does this only after Jack deploys the route)
// opts.worker: ok | 404 | 500 | refused | malformed | stale | nobtc | noglobal | hang
// log: { reqs: [{host, path, type}], cg: {simple, global}, worker: n }
async function route(ctx, opts, log) {
  await ctx.route(/^https?:/, async r => {
    const rq = r.request(), u = new URL(rq.url());
    log.reqs.push({ host: u.host, path: u.pathname, type: rq.resourceType() });
    if (u.host === BASE_HOST) {
      if (opts.meta && rq.resourceType() === "document") {
        const resp = await r.fetch();
        let body = await resp.text();
        body = body.replace("<title>", `<meta name="gcm-live-prices" content="${WORKER}">\n<title>`);
        return r.fulfill({ response: resp, body });
      }
      return r.continue();
    }
    if (u.host === "api.coingecko.com") {
      const m = u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      if (m) {
        const days = parseInt(u.searchParams.get("days") || "7", 10);
        return r.fulfill({ status: 200, contentType: "application/json", headers: CORS, body: JSON.stringify(recorded(m[1], days <= 1 ? 1 : days <= 7 ? 7 : 365)) });
      }
      if (/\/simple\/price/.test(u.pathname)) { log.cg.simple++; return r.fulfill({ status: 200, contentType: "application/json", headers: CORS, body: JSON.stringify(CG_SIMPLE) }); }
      if (/\/global/.test(u.pathname)) { log.cg.global++; return r.fulfill({ status: 200, contentType: "application/json", headers: CORS, body: JSON.stringify(CG_GLOBAL) }); }
      return r.abort();
    }
    if (u.host === "worker.test") {
      log.worker++;
      const w = opts.worker || "ok";
      const j = b => r.fulfill({ status: 200, contentType: "application/json", headers: CORS, body: JSON.stringify(b) });
      if (w === "ok") return j(ROUTE_BODY);
      if (w === "404") return r.fulfill({ status: 404, headers: CORS, body: "no" });
      if (w === "500") return r.fulfill({ status: 500, headers: CORS, body: "no" });
      if (w === "refused") return r.abort();
      if (w === "malformed") return r.fulfill({ status: 200, contentType: "application/json", headers: CORS, body: "not json {" });
      if (w === "stale") return j({ ...ROUTE_BODY, stale: true });
      if (w === "nobtc") return j({ ...ROUTE_BODY, simple: {} });
      if (w === "noglobal") return j({ ...ROUTE_BODY, global: undefined });
      if (w === "hang") { await sleep(6000); return r.abort().catch(() => {}); }
    }
    return r.abort();                                          // every other host: no network
  });
}
const newLog = () => ({ reqs: [], cg: { simple: 0, global: 0 }, worker: 0 });

// What the panel could add: a shift that moves the search box, the table as a block, the panel or the stamp above it. The Top 100's table
// cells (TH, TD) also shift now and then on their own when the price column's font swaps in, with no panel, in Sprint 9.6's page too
// (measured on 9.6's tree: 0.019 at 1440 in one load in three on a slow delivery, 0.0164 at 375 from the stale-state age text); that
// is not the panel's, is reported as INFO, and is named for the proposals.
const pushed = c => Math.round(c.shifts.filter(s => s.n.some(x => /coin-search|movetable|wp-panel|live-stamp/.test(x))).reduce((a, s) => a + s.v, 0) * 1e4) / 1e4;

const CLS_INIT = () => {
  window.__cls = 0; window.__shifts = [];
  new PerformanceObserver(list => {
    for (const e of list.getEntries()) if (!e.hadRecentInput) {
      window.__cls += e.value;
      window.__shifts.push({ v: Math.round(e.value * 1e4) / 1e4, n: (e.sources || []).map(s => s.node && (s.node.nodeName + "." + (s.node.className || ""))).slice(0, 2) });
    }
  }).observe({ type: "layout-shift", buffered: true });
};

let browser;
const timer = setTimeout(() => { console.log("FAIL the browser script did not finish in 9 minutes"); process.exit(1); }, 9 * 60 * 1000);
try {
  browser = await pw.chromium.launch();
  const mk = async (width, opts = {}, init = null) => {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: opts.scheme || "light", serviceWorkers: "block" });
    await ctx.addInitScript(CLS_INIT);
    if (opts.freezeAt) await ctx.addInitScript(([at]) => { const Real = Date, T = Real.parse(at); class F extends Real { constructor(...a) { if (a.length) super(...a); else super(T); } static now() { return T; } } window.Date = F; }, [opts.freezeAt]);
    if (init) await ctx.addInitScript(init);
    const log = newLog();
    await route(ctx, opts, log);
    const page = await ctx.newPage();
    const errs = [];
    page.on("pageerror", e => errs.push(String(e.message || e)));
    return { ctx, page, log, errs };
  };
  const price = async (page, sel, want, ms = 4800) => {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) {
      const t = await page.evaluate(s => { const e = document.querySelector(s); return e ? e.textContent.trim() : null; }, sel);
      if (t === want) return t;
      await sleep(120);
    }
    return page.evaluate(s => { const e = document.querySelector(s); return e ? e.textContent.trim() : null; }, sel);
  };

  // ---- 1. the watchlist on the Top 100 page ----------------------------------------------------------------------------------
  const PINS = () => { try { if (!localStorage.getItem("gcmc_coins") && !sessionStorage.getItem("__seeded")) { localStorage.setItem("gcmc_coins", JSON.stringify(["BTC", "ETH", "ZZZNOTACOIN"])); sessionStorage.setItem("__seeded", "1"); } } catch (e) {} };
  {
    // nothing saved: the panel stays hidden
    const t = await mk(375);
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(400);
    check("watchlist: with nothing saved the panel is not displayed and takes no room (and the root carries no reserve)", await t.page.evaluate(() => { const p = document.querySelector("[data-wl-panel]"); return !!p && getComputedStyle(p).display === "none" && p.getBoundingClientRect().height === 0 && !document.documentElement.hasAttribute("data-wl-n"); }));
    await t.ctx.close();
  }
  const FEED = JSON.parse(fs.readFileSync(path.join(root, "api/v1/top100.json"), "utf8"));
  const FRESH = new Date(Date.parse(FEED.as_of_utc) + 3600e3).toISOString();      // one hour after the Board's stamp: not stale, so no age text is added
  for (const w of [375, 1440]) for (const pins of [false, true]) {
    const t = await mk(w, { freezeAt: FRESH }, pins ? PINS : null);
    await t.page.goto(base + "/pulse/prices.html?slow=1", { waitUntil: "load" }); await sleep(1500);
    const c = await t.page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts, shown: getComputedStyle(document.querySelector("[data-wl-panel]")).display !== "none" }));
    check(`the Top 100 at ${w} on a slow network (the page arrives in two parts, 700 ms apart), ${pins ? "with" : "without"} saved coins: nothing the panel could move moves, and the panel is ${pins ? "there" : "absent"}`,
      pushed(c) < 0.0005 && c.shown === pins, JSON.stringify(c));
    if (c.cls >= 0.0005) info(`the Top 100 at ${w}, ${pins ? "with" : "without"} saved coins`, `a table-cell shift of ${c.cls.toFixed(4)} on its own (not the panel's): ${JSON.stringify(c.shifts)}`);
    await t.ctx.close();
  }
  for (const w of [375, 1440]) {
    const t = await mk(w, { freezeAt: FRESH }, PINS);
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(900);
    const got = await t.page.evaluate(() => {
      const p = document.querySelector("[data-wl-panel]");
      const vis = sel => { const e = document.querySelector(sel); if (!e) return false; const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.height > 0 && r.width > 0 && cs.visibility === "visible" && cs.display !== "none"; };
      const mark = s => { const tr = document.querySelector(`tbody[data-live="top100"] tr[data-sym="${s}"] td.sym2`); return tr ? getComputedStyle(tr, "::after").content : null; };
      const px = document.querySelector('tbody[data-live="top100"] tr[data-sym="BTC"] [data-cell="price"]').textContent;
      const body = document.body.innerText;
      return { hidden: getComputedStyle(p).display === "none", h: Math.round(p.getBoundingClientRect().height * 10) / 10, wn: document.documentElement.getAttribute("data-wl-n"),
        btcMark: mark("BTC"), ethMark: mark("ETH"), solMark: mark("SOL"), panelText: p.innerText, px, pxCount: body.split(px).length - 1,
        marked: [...document.querySelectorAll('tbody[data-live="top100"] tr')].filter(tr => /Saved|\u2605/.test(getComputedStyle(tr.querySelector("td.sym2"), "::after").content)).map(tr => tr.getAttribute("data-sym")),
        cookie: document.cookie, cls: window.__cls, shifts: window.__shifts,
        seen: ["[data-wl-panel] .wp-h", "[data-wl-panel] .wp-note", "[data-wl-only-btn]", "[data-wl-clear]"].map(vis) };
    });
    check(`watchlist at ${w}: with no network (every third host refused) and no cookie, the saved coins' rows are marked in the table`, !got.hidden && got.marked.join(",") === "BTC,ETH" && got.cookie === "" && (await t.ctx.cookies()).length === 0, JSON.stringify(got.marked));
    check(`watchlist at ${w}: a saved coin the table lacks (ZZZNOTACOIN) marks nothing and is not invented`, got.marked.length === 2);
    check(`watchlist at ${w}: the panel prints no price and no change (no $ and no %): each figure prints once, in the table`, !/[$%]/.test(got.panelText) && got.pxCount === 1, `${JSON.stringify(got.panelText)} count of ${got.px}: ${got.pxCount}`);
    check(`watchlist at ${w}: the panel is exactly the height the CSS reserves (127px), whatever is saved`, Math.abs(got.h - 127) < 0.5 && got.wn === "2", `height ${got.h}, data-wl-n ${got.wn}`);
    check(`watchlist at ${w}: the heading, the device-only line, Show only saved and Clear are all visible`, got.seen.every(Boolean), JSON.stringify(got.seen));
    check(`watchlist at ${w}: nothing the panel could move moves, with saved coins`, pushed(got) < 0.0005, `cls ${got.cls} ${JSON.stringify(got.shifts)}`);
    if (got.cls >= 0.0005) info(`watchlist at ${w}`, `a table-cell shift of ${got.cls.toFixed(4)} on its own (not the panel's): ${JSON.stringify(got.shifts)}`);
    const bad = t.log.reqs.filter(r => r.host !== BASE_HOST && r.host !== "api.coingecko.com" && r.host !== "static.cloudflareinsights.com");
    check(`watchlist at ${w}: no request goes to any host but the site, the tape's CoinGecko read and the beacon`, bad.length === 0, JSON.stringify(bad.slice(0, 3)));
    const own = t.log.reqs.filter(r => r.host === BASE_HOST && ["fetch", "xhr", "ping", "websocket", "eventsource"].includes(r.type));
    check(`watchlist at ${w}: the page makes no fetch, XHR or ping to its own host either`, own.length === 0, JSON.stringify(own.slice(0, 3)));
    if (w === 375) {
      await t.ctx.setOffline(true);
      await t.page.click("[data-wl-only-btn]");
      const only = await t.page.evaluate(() => ({ rows: [...document.querySelectorAll('tbody[data-live="top100"] tr')].filter(tr => getComputedStyle(tr).display !== "none").map(tr => tr.getAttribute("data-sym")), pressed: document.querySelector("[data-wl-only-btn]").getAttribute("aria-pressed") }));
      check("watchlist: Show only saved (offline) leaves exactly the saved coins' rows", only.rows.join(",") === "BTC,ETH" && only.pressed === "true", JSON.stringify(only));
      await t.page.click("[data-wl-only-btn]");
      const all = await t.page.evaluate(() => document.querySelectorAll('tbody[data-live="top100"] tr').length === [...document.querySelectorAll('tbody[data-live="top100"] tr')].filter(tr => getComputedStyle(tr).display !== "none").length);
      check("watchlist: toggled back, every row shows again", all);
      await t.page.click("[data-wl-clear]");
      const cleared = await t.page.evaluate(() => ({ stored: localStorage.getItem("gcmc_coins"), hidden: getComputedStyle(document.querySelector("[data-wl-panel]")).display === "none", marks: document.querySelectorAll("#wp-marks").length }));
      check("watchlist: Clear (offline) empties the one stored list, removes the marks and hides the panel", cleared.stored === "[]" && cleared.hidden && cleared.marks === 0, JSON.stringify(cleared));
      check("watchlist: the page threw nothing", t.errs.length === 0, t.errs.join(" | "));
    }
    await t.ctx.close();
  }
  {
    const t = await mk(375, {}, PINS);
    await t.page.goto(base + "/coins/btc.html", { waitUntil: "load" });
    await t.page.evaluate(() => localStorage.setItem("gcmc_coins", "[]"));
    await t.page.reload({ waitUntil: "load" });
    await t.page.click(".cn-pin"); await sleep(150);
    const stored = await t.page.evaluate(() => localStorage.getItem("gcmc_coins"));
    check("watchlist: Pin on a coin page writes the one list the Top 100 reads", JSON.parse(stored).join(",") === "BTC", stored);
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(400);
    const seen = await t.page.evaluate(() => [...document.querySelectorAll('tbody[data-live="top100"] tr')].filter(tr => /Saved|\u2605/.test(getComputedStyle(tr.querySelector("td.sym2"), "::after").content)).map(tr => tr.getAttribute("data-sym")).join(","));
    check("watchlist: the coin pinned on its page is marked on the Top 100", seen === "BTC", seen);
    await t.ctx.close();
  }
  {
    const t = await mk(375, {}, () => { try { localStorage.setItem("gcmc_coins", JSON.stringify(["BTC", "ZZZ", "ETH", "BTC", "constructor", "x\"]a"])); } catch (e) {} });
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(400);
    const c = await t.page.evaluate(() => ({ n: document.documentElement.getAttribute("data-wl-n"), marked: [...document.querySelectorAll('tbody[data-live="top100"] tr')].filter(tr => /Saved|\u2605/.test(getComputedStyle(tr.querySelector("td.sym2"), "::after").content)).map(tr => tr.getAttribute("data-sym")).join(",") }));
    check("watchlist: a repeat, an unknown coin, an object key and a quote-and-bracket string saved: only the real coins are marked, once each, and nothing breaks", c.marked === "BTC,ETH" && t.errs.length === 0, JSON.stringify(c));
    await t.ctx.close();
  }
  for (const [label, init] of [
    ["storage that throws", () => { Storage.prototype.setItem = function () { throw new Error("denied"); }; Storage.prototype.getItem = function () { throw new Error("denied"); }; }],
    ["a corrupt stored list", () => { try { localStorage.setItem("gcmc_coins", "not json {"); } catch (e) {} }],
    ["a stored list that is not a list", () => { try { localStorage.setItem("gcmc_coins", JSON.stringify({ a: 1 })); } catch (e) {} }]]) {
    const t = await mk(375, {}, init);
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(500);
    const st = await t.page.evaluate(() => ({ hidden: getComputedStyle(document.querySelector("[data-wl-panel]")).display === "none", rows: document.querySelectorAll("#coin-q, tbody[data-live='top100'] tr").length }));
    check(`watchlist: ${label}: the panel stays hidden, the table is intact and nothing throws`, st.hidden && st.rows > 50 && t.errs.length === 0, JSON.stringify(st) + t.errs.join("|"));
    await t.ctx.close();
  }
  {
    // nothing saved: the page is the page Sprint 9.6 shipped (no marks, no reserve, no extra style)
    const t = await mk(375, { freezeAt: FRESH });
    await t.page.goto(base + "/pulse/prices.html", { waitUntil: "load" }); await sleep(300);
    const n = await t.page.evaluate(() => ({ style: document.querySelectorAll("#wp-marks").length, attr: document.documentElement.hasAttribute("data-wl-n"), marked: [...document.querySelectorAll('tbody[data-live="top100"] td.sym2')].filter(td => getComputedStyle(td, "::after").content !== "none" && getComputedStyle(td, "::after").content !== "normal").length }));
    check("watchlist: with nothing saved there are no marks, no injected style and no reserve", n.style === 0 && !n.attr && n.marked === 0, JSON.stringify(n));
    await t.ctx.close();
  }

  // ---- 1b. the feed's stale flag and the page's stale state are one rule -------------------------------------------------
  {
    const feed = JSON.parse(fs.readFileSync(path.join(root, "api/v1/top100.json"), "utf8"));
    const T0 = Date.parse(feed.as_of_utc), win = feed.stale_after_hours;
    for (const [pg, sel, f, label] of [["/pulse/prices.html", ".live-stamp", feed, "the Top 100 stamp"]]) {
      for (const hrs of [win - 0.1, win + 0.1]) {
        const iso = new Date(T0 + hrs * 3600e3).toISOString();
        const t = await mk(1440, {}, null);
        await t.ctx.addInitScript(([at]) => { const Real = Date, T = Real.parse(at); class F extends Real { constructor(...a) { if (a.length) super(...a); else super(T); } static now() { return T; } } window.Date = F; }, [iso]);
        await t.page.goto(base + pg, { waitUntil: "load" }); await sleep(300);
        const pageStale = await t.page.evaluate(s => document.querySelector(s).classList.contains("is-stale"), sel);
        const feedStale = hrs > f.stale_after_hours;
        check(`${label} read ${hrs.toFixed(1)} hours after its stamp: the page's stale state (${pageStale}) is the feed's rule (${feedStale})`, pageStale === feedStale);
        await t.ctx.close();
      }
    }
    info("the feed's own flag at build", `${feed.stale} (as of ${feed.as_of_utc}, built ${feed.built_utc})`);
  }

  // ---- 2. the coin page's h1 ------------------------------------------------------------------------------------------
  for (const scheme of ["light", "dark"]) for (const w of [375, 1440]) {
    const t = await mk(w, { scheme });
    await t.page.goto(base + "/coins/btc.html", { waitUntil: "load" });
    await t.page.evaluate(() => document.fonts.ready);
    const h = await t.page.evaluate(() => {
      const hs = document.querySelectorAll("h1"); const e = document.querySelector(".cn-head h1"); if (!e) return { n: hs.length };
      const cs = getComputedStyle(e), r = e.getBoundingClientRect();
      return { n: hs.length, text: e.textContent, size: cs.fontSize, weight: cs.fontWeight, lh: cs.lineHeight, mt: cs.marginTop, mb: cs.marginBottom,
        ls: cs.letterSpacing, family: cs.fontFamily.split(",")[0], h: Math.round(r.height * 10) / 10, cls: window.__cls };
    });
    check(`coin page at ${w} (${scheme}): one h1, the coin's name, with the look the h2 had (23px, 700, 27.6px line, 1.4em and .4em margins)`,
      h.n === 1 && /Bitcoin/.test(h.text || "") && h.size === "23px" && h.weight === "700" && h.lh === "27.6px" && h.mt === "32.2px" && h.mb === "9.2px", JSON.stringify(h));
    await t.ctx.close();
  }

  // ---- 3. the live route ----------------------------------------------------------------------------------------------
  const cases = [
    { name: "absent (no address in the page: today's path)", opts: { meta: false }, route: false },
    { name: "present and answering", opts: { meta: true, worker: "ok" }, route: true },
    { name: "present, 404", opts: { meta: true, worker: "404" }, route: false },
    { name: "present, 500", opts: { meta: true, worker: "500" }, route: false },
    { name: "present, refused", opts: { meta: true, worker: "refused" }, route: false },
    { name: "present, malformed", opts: { meta: true, worker: "malformed" }, route: false },
    { name: "present, stale: true", opts: { meta: true, worker: "stale" }, route: false },
    { name: "present, no Bitcoin price", opts: { meta: true, worker: "nobtc" }, route: false },
    { name: "present, no global answer", opts: { meta: true, worker: "noglobal" }, route: false },
    { name: "present, hung past 3 seconds", opts: { meta: true, worker: "hang" }, route: false },
  ];
  for (const c of cases) {
    for (const [pg, sel] of [["/index.html", '.h-px[data-tape="bitcoin"]']]) {
      const t = await mk(1440, c.opts);
      await t.page.goto(base + pg, { waitUntil: "load" });
      const want = c.route ? "$22,222.22" : "$11,111.11";
      const got = await price(t.page, sel, want, c.opts.worker === "hang" ? 6500 : 4800);
      const where = "the home tape";
      check(`live route ${c.name}: ${where} shows ${c.route ? "the route's" : "CoinGecko's"} price`, got === want, `got ${got}, want ${want}`);
      if (!c.opts.meta) check(`live route ${c.name}: the route is never asked (no request to its host)`, t.log.worker === 0, `worker requests ${t.log.worker}`);
      else check(`live route ${c.name}: the route is asked once`, t.log.worker === 1, `worker requests ${t.log.worker}`);
      if (c.route) check(`live route ${c.name}: ${where}: CoinGecko is not asked at all`, t.log.cg.simple === 0 && t.log.cg.global === 0, JSON.stringify(t.log.cg));
      else check(`live route ${c.name}: ${where}: CoinGecko is asked for the prices`, t.log.cg.simple >= 1, JSON.stringify(t.log.cg));
      const lab = await t.page.evaluate(() => (document.getElementById("tapeLive") || {}).textContent || "");
      check(`live route ${c.name}: the tape's line says the price is live, with the build's range stamp kept`, /^price live/.test(lab) && /range and chart as of/.test(lab), lab);
      const bad = t.log.reqs.filter(r => ![BASE_HOST, "api.coingecko.com", "static.cloudflareinsights.com", "worker.test"].includes(r.host));
      check(`live route ${c.name}: ${where}: no host but the site, CoinGecko, the beacon and (only when named) the route`, bad.length === 0, JSON.stringify(bad.slice(0, 3)));
      await t.ctx.close();
    }
  }
  for (const w of [375, 1440]) for (const opts of [{ meta: false }, { meta: true, worker: "ok" }]) {
    const t = await mk(w, opts);
    await t.page.goto(base + "/index.html", { waitUntil: "load" });
    await price(t.page, '.h-px[data-tape="bitcoin"]', opts.meta ? "$22,222.22" : "$11,111.11"); await sleep(1200);
    const cls = await t.page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts }));
    check(`the home at ${w} (${opts.meta ? "route answering" : "route absent"}): layout shift is zero when the live price lands`, cls.cls < 0.0005, `cls ${cls.cls} ${JSON.stringify(cls.shifts)}`);
    await t.ctx.close();
  }
  // the beacon stays
  {
    const t = await mk(375);
    for (const p of ["/index.html", "/pulse/prices.html", "/coins/btc.html"]) {
      await t.page.goto(base + p, { waitUntil: "load" });
      const n = await t.page.evaluate(() => document.querySelectorAll("script[data-cf-beacon]").length);
      check(`the beacon stays on ${p}: exactly one`, n === 1, `found ${n}`);
    }
    await t.ctx.close();
  }
} catch (e) {
  console.log(`FAIL the browser script raised ${e && e.message || e}`);
  results.push(["raise", false, String(e)]);
} finally {
  clearTimeout(timer);
  if (browser) await browser.close().catch(() => {});
  server.close();
}
const failed = results.filter(r => !r[1]).length;
console.log(`\nsprint 9.7 browser: ${results.length - failed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
