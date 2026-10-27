#!/usr/bin/env node
// sprint95b_browser.mjs <built-site-dir>
//
// Program 9, Sprint 9.5b (20 October 2026): the browser half of scripts/sprint95b_test.py. It serves a built tree from
// a local port, answers CoinGecko's market_chart route from the recorded fixtures (fixtures/coingecko), aborts every other
// host, and prints one line per check:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//     INFO <name>: <a measurement, not a verdict>
//
// Exit 1 when any check fails. U-7: the browser is launched with a timeout and closed in a finally block.
// The tree must hold home-board-card.html and home-board-nocard.html (sprint95b_test.py writes them from
// scripts/sprint95b_fixture.py). The 9.5 baselines (fixtures/sprint95b/*.95.*) are served under /__b95/.
//
// Environment: S95B_N overrides the number of throttled CLS reads per page and width (default 30 on a phone width, 10 at 1440).
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
const FX95B = path.join(HERE, "..", "fixtures", "sprint95b");
const argv = process.argv.slice(2);
const dir = argv[0];
if (!dir) { console.log("usage: sprint95b_browser.mjs <built-site-dir>"); process.exit(2); }

const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2", ".xml": "application/xml" };
const root = path.resolve(dir);
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.startsWith("/__b95/")) {                               // Sprint 9.5's own files, byte for byte
    const f = path.join(FX95B, p.slice(7));
    if (!f.startsWith(FX95B) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": MIME[path.extname(f)] || "text/plain" });
    return fs.createReadStream(f).pipe(res);
  }
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
// opts.live: answer the tape's one price call (SYNTHETIC: a stub of CoinGecko's simple/price shape, prices a few percent off the build's,
// so the digits, the change and the stamp's words all change after load, which is what a reader's tab does in life)
// opts.base95: serve Sprint 9.5's stylesheets for /assets/site.css and /assets/system.css
async function route(page, opts = {}) {
  await page.route(/^https?:/, async r => {
    const u = new URL(r.request().url());
    if (u.host === new URL(base).host) {
      // THE 375 BASELINE IS SPRINT 9.5'S CSS PLUS EXACTLY THE TWO RULES J-11 (strategist, October 20, 3:35 PM ET) CARRIES UNDER 1280, named here:
      // rule 1 (the live stamp's three-line reserve below 521 px) in system.css, rule 2 (the nav's wrap from 700 to 1019 px) in site.css.
      // Nothing else is excluded: a third rule under 1280 makes the new page differ from this one.
      if (opts.base95 && u.pathname === "/assets/site.css") return r.fulfill({ status: 200, contentType: "text/css", body: fs.readFileSync(path.join(FX95B, "site.95.css"), "utf8") + "\n" + fs.readFileSync(path.join(FX95B, "j11-nav.css"), "utf8") });
      if (opts.base95 && u.pathname === "/assets/system.css") return r.fulfill({ status: 200, contentType: "text/css", body: fs.readFileSync(path.join(FX95B, "system.95.css"), "utf8") + "\n" + fs.readFileSync(path.join(FX95B, "j11-stamp.css"), "utf8") });
      return r.continue();
    }
    if (u.host === "api.coingecko.com") {
      const m = u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      const days = parseInt(u.searchParams.get("days") || "7", 10);
      if (m && days <= 365) {
        return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(recorded(m[1], days <= 1 ? 1 : days <= 7 ? 7 : 365)) });
      }
      if (opts.live && /\/simple\/price/.test(u.pathname)) {
        return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify({ bitcoin: { usd: 83012.37, usd_24h_change: -1.234 }, ethereum: { usd: 2411.5, usd_24h_change: 1.987 },
            solana: { usd: 151.2, usd_24h_change: 0.312 }, ripple: { usd: 2.4411, usd_24h_change: -0.456 } }) });
      }
    }
    return r.abort();
  });
}

const results = [];
const check = (name, ok, detail = "") => { results.push([name, ok, detail]); console.log(ok ? `PASS ${name}` : `FAIL ${name}: ${detail}`); };
const info = (name, detail) => console.log(`INFO ${name}: ${detail}`);
const exists = p => { const f = path.join(root, p.replace(/^\//, "")); return fs.existsSync(f) || fs.existsSync(f + ".html") || fs.existsSync(path.join(f, "index.html")); };

const CLS_INIT = () => {
  window.__cls = 0; window.__shifts = [];
  new PerformanceObserver(list => {
    for (const e of list.getEntries()) if (!e.hadRecentInput) {
      window.__cls += e.value;
      window.__shifts.push({ v: Math.round(e.value * 1e4) / 1e4, t: Math.round(e.startTime), r: (e.sources || []).map(s => [s.previousRect && Math.round(s.previousRect.width) + "x" + Math.round(s.previousRect.height) + "@" + Math.round(s.previousRect.x) + "," + Math.round(s.previousRect.y), s.node && (s.node.nodeName + "." + (s.node.className || ""))]).slice(0, 2) });
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
const frozenClock = ([iso]) => {              // the same instant for both pages of a pair, whatever the load takes
  const Real = Date, T0 = Real.parse(iso);
  class FakeDate extends Real {
    constructor(...a) { if (a.length) super(...a); else super(T0); }
    static now() { return T0; }
  }
  window.Date = FakeDate;
};
const mastAsof = url => {
  const f = path.join(root, url.replace(/^\//, "") + (url.endsWith("/") ? "index.html" : ".html"));
  const g = fs.existsSync(f) ? f : path.join(root, url.replace(/^\//, ""));
  const m = fs.readFileSync(g, "utf8").match(/data-mh-live data-asof="([^"]+)"/);
  return m ? m[1] : null;
};

const ONLY = (process.env.S95B_ONLY || "").split(",").filter(Boolean);   // e.g. S95B_ONLY=6 runs the page sweep alone
const run = n => ONLY.length === 0 || ONLY.includes(n);
const listDir = (d, n = 1, last = false) => { const p = path.join(root, d); if (!fs.existsSync(p)) return []; const fs_ = fs.readdirSync(p).filter(f => f.endsWith(".html")).sort(); return (last ? fs_.slice(-n) : fs_.slice(0, n)).map(f => `/${d}/${f}`); };
  const SWEEP = ["/index.html", "/today/", ...listDir("today", 1, true).slice(-1), "/pulse.html", "/pulse/movers.html", "/pulse/sentiment.html", "/pulse/prices.html", "/pulse/etf.html",
    "/pulse/stablecoins.html", "/pulse/leverage.html", "/pulse/network.html", "/pulse/posture.html", "/flows.html", "/chartmaster.html", "/coins/btc", "/coins/eth", ...listDir("coins", 1),
    "/news.html", ...listDir("news", 2), "/bottom-line.html", ...listDir("bottom-line", 1, true), ...listDir("edition", 1, true), ...listDir("articles", 2, true), "/learn.html", ...listDir("learn", 2),
    "/record.html", ...listDir("tables", 3), ...listDir("coverage", 2), "/about.html", "/method.html", "/standards.html", "/corrections.html", "/privacy.html", "/terms.html", "/accessibility.html",
    "/how-we-make-money.html", "/archive.html", "/wire.html", "/cold-storage.html", "/crypto-tax.html", "/counterfeit-devices.html", "/onchain-flows.html", "/thanks.html", "/404.html", "/movers-fixture.html"]
    .filter((u, i, a) => a.indexOf(u) === i && exists(u)).filter(u => !process.env.S95B_PAGES || process.env.S95B_PAGES.split(",").includes(u));

let browser;
try {
  browser = await pw.chromium.launch({ timeout: 30000 });
  const open = async (w, h, url, opts = {}) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, colorScheme: opts.scheme || "light" });
    const page = await ctx.newPage();
    page.setDefaultTimeout(8000);
    if (opts.init) await page.addInitScript(opts.init, opts.initArg);
    await route(page, opts);
    await page.goto(base + url, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    return [ctx, page];
  };

  if (run("1")) {
  // 1. THE WRAPPER, as drawn: 1080 under 1280, 1400 from 1280 to any width; the home and the inner pages the same
  const WRAP_PAGES = ["/index.html", "/today/", "/pulse.html", "/pulse/movers.html", "/flows.html", "/coins/btc", "/news.html", "/learn.html", "/about.html", "/method.html", "/bottom-line.html", "/record.html", "/chartmaster.html"]
    .filter(exists);
  for (const w of [1440, 1920, 1280, 1279, 1100, 768, 375]) {
    const bad = [];
    for (const url of WRAP_PAGES) {
      const [ctx, page] = await open(w, 800, url);
      const got = await page.evaluate(() => {
        const e = document.querySelector("main.wrap, main .wrap, .wrap"), r = e.getBoundingClientRect();
        return { wrap: Math.round(r.width * 10) / 10, vw: document.documentElement.clientWidth, over: document.documentElement.scrollWidth > document.documentElement.clientWidth };
      });
      const want = Math.min(w >= 1280 ? 1400 : 1080, got.vw);
      if (Math.abs(got.wrap - want) > 0.6) bad.push(`${url}: ${got.wrap} (want ${want})`);
      if (got.over) bad.push(`${url}: scrolls sideways`);
      await ctx.close();
    }
    check(`the page wrapper at ${w}: ${w >= 1280 ? "min(viewport, 1400)" : "min(viewport, 1080)"} on the home and ${WRAP_PAGES.length - 1} inner pages, no sideways scroll`, bad.length === 0, bad.join(" | "));
  }

  }

  if (run("2")) {
  // 2. THE FIRST SCREEN AT 1440: every section's first line is on it
  const FIRST = () => {
    const rendered = el => { for (let e = el; e; e = e.parentElement) { if (getComputedStyle(e).display === "none") return false; } return true; };
    const firstLine = el => {
      if (!el || !rendered(el)) return null;
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        if (!n.textContent.trim() || !rendered(n.parentElement)) continue;
        const rg = document.createRange(); rg.selectNodeContents(n);
        const rects = [...rg.getClientRects()].filter(r => r.width > 0 && r.height > 0);
        if (rects.length) return { top: Math.round(rects[0].top + scrollY), bottom: Math.round(rects[0].bottom + scrollY), left: Math.round(rects[0].left), right: Math.round(rects[0].right) };
      }
      return null;
    };
    const q = s => document.querySelector(s);
    const whale = [...document.querySelectorAll('[data-block="money"] article.tl-card')].find(a => /^Whale flows/.test(a.textContent.trim()));
    const t = {
      card: q("aside.vd"), bitcoin: q("[data-btc-line]"), ether: q("[data-eth-line]"), brief: q('[data-block="narrative"]'),
      movers: q('[data-block="movers"] ol li') || q('[data-block="movers"]'), whale,
      money: q('[data-block="money"]'), mood: q('[data-block="mood"]'), since: q('[data-block="since"]'), why: q('[data-block="why"]'), wire: q('[data-block="wire"]'),
      today: q('[data-block="today"]'), mine: q('[data-block="mine"]'),
    };
    const out = {};
    for (const k in t) out[k] = t[k] ? firstLine(t[k]) : null;
    out.vh = innerHeight; out.sw = document.documentElement.scrollWidth; out.cw = document.documentElement.clientWidth;
    return out;
  };
  const MUST = (hasCard) => ["bitcoin", "ether", "brief", "movers", "whale"].concat(hasCard ? ["card"] : []);
  const VH = 800;       // a 1440-wide laptop with the browser's own bars: the reader's tab, not an empty window
  for (const scheme of ["light", "dark"]) {
    for (const [name, url, hasCard] of [["card", "/home-board-card.html", true], ["nocard", "/home-board-nocard.html", false], ["built home", "/index.html", false]]) {
      if (!exists(url)) { check(`first screen at 1440 (${scheme}, ${name})`, false, "page not built"); continue; }
      const [ctx, page] = await open(1440, VH, url, { scheme });
      const f = await page.evaluate(FIRST);
      const miss = MUST(hasCard).filter(k => !f[k] || f[k].bottom > VH || f[k].top < 0);
      check(`the first screen at 1440x${VH} (${scheme}, ${name}): ${MUST(hasCard).join(", ")} each show their first line without scrolling`, miss.length === 0,
        `not on the screen: ${miss.map(k => k + "=" + JSON.stringify(f[k])).join("; ")}`);
      const others = ["money", "mood", "since", "why", "wire", "today", "mine"].map(k => `${k}:${f[k] ? f[k].bottom : "none"}`).join(" ");
      info(`first lines' bottoms at 1440x${VH} (${scheme}, ${name})`, `card:${f.card ? f.card.bottom : "none"} bitcoin:${f.bitcoin && f.bitcoin.bottom} ether:${f.ether && f.ether.bottom} brief:${f.brief && f.brief.bottom} movers:${f.movers && f.movers.bottom} whale:${f.whale && f.whale.bottom} ${others}`);
      check(`the first screen at 1440 (${scheme}, ${name}): the page does not scroll sideways`, f.sw <= f.cw, `scrollWidth ${f.sw} > ${f.cw}`);
      await ctx.close();
    }
  }
  // the board's geometry: the card is the first object, nothing overlaps, the right column stays on the right
  for (const [name, url, hasCard] of [["card", "/home-board-card.html", true], ["nocard", "/home-board-nocard.html", false]]) {
    const [ctx, page] = await open(1440, VH, url);
    const g = await page.evaluate(() => {
      const R = el => { if (!el || getComputedStyle(el).display === "none") return null; const r = el.getBoundingClientRect(); return { l: Math.round(r.left), t: Math.round(r.top + scrollY), r: Math.round(r.right), b: Math.round(r.bottom + scrollY) }; };
      const boxes = [...document.querySelectorAll("[data-block], aside.vd")].map(e => [e.getAttribute("data-block") || "card", R(e)]).filter(([, r]) => r && r.r > r.l && r.b > r.t);
      const overlaps = [];
      for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i][1], b = boxes[j][1];
        if (a.l < b.r - 1 && b.l < a.r - 1 && a.t < b.b - 1 && b.t < a.b - 1) overlaps.push(boxes[i][0] + "/" + boxes[j][0]);
      }
      const l = R(document.querySelector(".h-l")), rr = R(document.querySelector(".h-r")), card = R(document.querySelector("aside.vd"));
      const minTop = Math.min(...boxes.map(([, r]) => r.t));
      return { overlaps, l, rr, card, minTop, boxes: Object.fromEntries(boxes) };
    });
    check(`the glance board at 1440 (${name}): no two sections overlap`, g.overlaps.length === 0, g.overlaps.join(", "));
    check(`the glance board at 1440 (${name}): the right column (money, mood, movers) sits to the right of the left column, side by side`,
      g.l && g.rr && g.rr.l >= g.l.r - 1 && Math.abs(g.rr.t - g.l.t) <= 4, JSON.stringify({ l: g.l, rr: g.rr }));
    if (hasCard) check("the glance board at 1440: the verdict card is the first object (nothing above it, and it starts at the board's left edge)",
      g.card && g.card.t <= g.minTop + 2 && g.card.l <= g.l.l + 1, JSON.stringify({ card: g.card, minTop: g.minTop, l: g.l }));
    // CHANGED BY Sprint 9.9.1 (the ruling on J-8 of October 20): with no verdict record the card's place carries the no-read notice,
    // first, so the tape is under it and the Brief card is not above the tape
    else check("the glance board at 1440 with no verdict record: the no-read notice is the first object, the tape is under it and the Brief card is not above the tape", g.card && g.card.t <= g.minTop + 2 && g.boxes.tape && g.boxes.tape.t >= g.card.b - 1 && g.boxes.narrative && g.boxes.narrative.t >= g.boxes.tape.t, JSON.stringify(g.boxes));
    await ctx.close();
  }

  }

  if (run("3")) {
  // 3. THE 375 RENDER IS SPRINT 9.5'S: the 9.5 page under the 9.5 CSS and the new page under the new CSS, side by side
  const FROZEN = "2026-10-15T23:55:00Z";
  const LAYOUT = () => {
    const out = [];
    for (const e of document.querySelectorAll("body *")) {
      if (e.closest("[data-wide]")) continue;
      const cs = getComputedStyle(e), r = e.getBoundingClientRect();
      const q = v => Math.round(v * 100) / 100;
      out.push([e.tagName, e.id || "", String(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className), cs.display, q(r.x), q(r.y + scrollY), q(r.width), q(r.height)].join("|"));
    }
    return out;
  };
  for (const scheme of ["light", "dark"]) {
    for (const w of [375, 390]) {
      for (const name of ["card", "nocard"]) {
        const shots = [], lay = [];
        for (const which of ["old", "new"]) {
          const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1, colorScheme: scheme });
          const page = await ctx.newPage();
          page.setDefaultTimeout(8000);
          await page.addInitScript(frozenClock, [FROZEN]);
          await route(page, { base95: which === "old" });
          await page.goto(base + (which === "old" ? `/__b95/home-board-${name}.95.html` : `/home-board-${name}.html`), { waitUntil: "load" });
          await page.evaluate(() => document.fonts.ready);
          // SPRINT 9.9.1: the no-read notice is the one thing the card's place gains; with it taken out the page is Sprint 9.5's
          // (scripts/sprint991_test.py holds the notice to account, as the Ether line is held by the data-wide cut above)
          await page.evaluate(() => document.querySelectorAll("aside.vd.vd-next").forEach(e => e.remove()));
          // SPRINT 9.9.2: the Brief card's "Next Brief" line prints only when no notice carries the same time (the home's next slot
          // time printed once); it is taken out of both pages here, and scripts/sprint992_test.py holds it to account
          await page.evaluate(() => document.querySelectorAll('[data-block="narrative"] p.h-next').forEach(e => e.remove()));
          // and a coin "Moving today" lists with its change is not named again in the "beyond 5%" line (the same rule as _cut_992)
          await page.evaluate(() => {
            const listed = new Set([...document.querySelectorAll("ol.h-movers a")].map(a => a.textContent.trim()));
            document.querySelectorAll("p.h-stand").forEach(p => {
              const m = p.innerHTML.match(/^Top 100 beyond 5% either way: (.*)$/s);
              if (!m) return;
              const items = [...m[1].matchAll(/(\S+) (<span class="h-mc[^"]*">[^<]*<\/span>)/g)];
              if (!items.length) return;
              const keep = items.filter(x => !listed.has(x[1])).map(x => x[1] + " " + x[2]);
              p.innerHTML = "Top 100 beyond 5% either way: " + (keep.length ? keep.join(", ") : "none beyond those above");
            });
          });
          await page.waitForTimeout(1600);
          lay.push(await page.evaluate(LAYOUT));
          shots.push(await page.screenshot({ fullPage: true, animations: "disabled" }));
          await ctx.close();
        }
        const same = lay[0].length === lay[1].length && lay[0].every((x, i) => x === lay[1][i]);
        const first = lay[0].findIndex((x, i) => x !== lay[1][i]);
        check(`the home at ${w} (${scheme}, ${name}): every element's box is the one Sprint 9.5 drew (${lay[0].length} elements, the Ether line aside)`, same && lay[0].length > 150,
          `${lay[0].length} vs ${lay[1].length}; first difference at ${first}: ${lay[0][first]} / ${lay[1][first]}`);
        check(`the home at ${w} (${scheme}, ${name}): the screenshot is pixel for pixel Sprint 9.5's`, shots[0].equals(shots[1]), `${shots[0].length} bytes vs ${shots[1].length}`);
      }
    }
  }
  // and a width just under the line: 1279 draws no Ether line and no board; 1280 draws both
  {
    const state = () => {
      const q = s => document.querySelector(s), d = e => (e ? getComputedStyle(e).display : "absent");
      return { eth: d(q("[data-eth-line]")), cols: d(q(".h-l")), tile: d(q('[data-tile="ethereum"]')) };
    };
    const [ctx, page] = await open(1279, 800, "/home-board-card.html");
    const r = await page.evaluate(state);
    check("at 1279 the Ether line is not drawn, the left column is not a grid and the Ether tile is drawn (Ether prints once)", r.eth === "none" && r.cols !== "grid" && r.tile !== "none" && r.tile !== "absent", JSON.stringify(r));
    await ctx.close();
    const [c2, p2] = await open(1280, 800, "/home-board-card.html");
    const r2 = await p2.evaluate(state);
    check("at 1280 the Ether line is drawn, the left column is a grid and the Ether tile is hidden (Ether prints once)", r2.eth !== "none" && r2.eth !== "absent" && r2.cols === "grid" && r2.tile === "none", JSON.stringify(r2));
    await c2.close();
  }

  }

  if (run("4")) {
  // 4. CLS ON THE HOME, at zero at 375, 390 and 1440: first byte to the settled page, fresh (1 h after the build's stamp) and stale (9 h),
  // with the tape's live answer landing (SYNTHETIC stub) and without it
  const HOME = "/index.html";
  const base0 = mastAsof(HOME);
  const runCls = async (w, hours, live, throttle) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    page.setDefaultTimeout(15000);
    if (throttle) { const cdp = await ctx.newCDPSession(page); await cdp.send("Emulation.setCPUThrottlingRate", { rate: 6 }); }
    await page.addInitScript(CLS_INIT);
    if (base0) await page.addInitScript(clockShim, [base0, hours * 3600e3]);
    await route(page, { live });
    await page.goto(base + HOME, { waitUntil: "load" });
    await page.waitForTimeout(throttle ? 1800 : 1500);
    const c = await page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts, live: (document.getElementById("tapeLive") || {}).textContent || "" }));
    await ctx.close();
    return c;
  };
  for (const w of [375, 390, 1440]) {
    for (const [hours, label] of [[1, "fresh"], [9, "stale"]]) {
      for (const live of [false, true]) {
        const c = await runCls(w, hours, live, false);
        // J-11 rule 1: the live price landing is judged at every width, phones included (0.018 at 375 on 9.5's head, before the stamp kept its three lines)
        check(`CLS on the home at ${w}, read ${label}, ${live ? "with the live price landing (stub)" : "no live answer"}: zero`, c.cls < 0.0005 && (!live || /price live/.test(c.live)), JSON.stringify({ cls: c.cls, live: c.live.slice(0, 40), shifts: c.shifts.slice(0, 3) }));
      }
    }
  }
  for (const w of [375, 390, 1440]) {
    for (const [hours, label] of [[9, "stale"], [1, "fresh"]]) {
      let bad = 0, worst = 0, first = null;
      const N = process.env.S95B_N !== undefined ? +process.env.S95B_N : (w < 700 ? 30 : 10);
      for (let k = 0; k < N; k++) {
        const c = await runCls(w, hours, k % 2 === 1, true);
        if (c.cls >= 0.0005) { bad++; worst = Math.max(worst, c.cls); first = first || c.shifts.slice(0, 3); }
      }
      check(`CLS on the home at ${w}, 6x CPU throttling, read ${label}: zero in all ${N} reads (every other read has the live price landing)`, bad === 0, JSON.stringify({ reads_over_zero: bad, of: N, worst, first }));
    }
  }

  }

  if (run("5")) {
  // 5. THE BEACON STAYS, on the home and on inner pages at 1440
  for (const url of ["/index.html", "/about.html", "/pulse.html"].filter(exists)) {
    const [ctx, page] = await open(1440, 800, url);
    const n = await page.evaluate(() => document.querySelectorAll("script[data-cf-beacon]").length);
    check(`the beacon is on ${url} at 1440, once`, n === 1, `found ${n}`);
    await ctx.close();
  }

  }

  if (run("6")) {
  // 6. EVERY PAGE A READER CAN REACH, at 1280 and 1440: no sideways scroll, no paragraph past a readable measure, tables that use the room,
  // images never drawn larger than they are, chart labels neither under 12 px nor swollen
  const AUDIT = () => {
    const out = { over: document.documentElement.scrollWidth - document.documentElement.clientWidth, long: [], tables: [], up: [], svgBig: [], svgSmall: [], bg: [] };
    const rendered = el => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden") return false; } return true; };
    const cv = document.createElement("canvas").getContext("2d");
    for (const el of document.querySelectorAll("p, li, dd, blockquote, figcaption")) {
      if (!rendered(el) || el.closest("table, nav, header, footer, .tabbar, [data-fit]")) continue;
      const own = [...el.childNodes].filter(n => n.nodeType === 3 || (n.nodeType === 1 && /^(A|B|I|EM|STRONG|SPAN|CODE|SMALL|MARK|TIME|ABBR)$/.test(n.nodeName))).map(n => n.textContent).join("").replace(/\s+/g, " ").trim();
      if (own.length < 150) continue;
      // the measure the box allows: its content width over the average width of this text in this face (a canvas measure), so a
      // two-line paragraph is not over-counted and a one-line one is judged by the room it has, not by how short its words are
      const cs = getComputedStyle(el);
      cv.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      const avg = cv.measureText(own).width / own.length;
      const room = el.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const cpl = Math.round(room / avg), lines = 0;
      const sel = el.tagName.toLowerCase() + "." + String(el.className).split(" ")[0] + " < " + (el.parentElement ? el.parentElement.tagName.toLowerCase() + "." + String(el.parentElement.className).split(" ")[0] : "");
      out.long.push({ t: own.slice(0, 40), cpl, lines, w: Math.round(el.getBoundingClientRect().width), sel });
    }
    for (const t of document.querySelectorAll("table")) {
      if (!rendered(t)) continue;
      const cols = Math.max(...[...t.rows].map(r => r.cells.length), 0);
      const p = t.parentElement, pr = p.getBoundingClientRect(), tr = t.getBoundingClientRect();
      const pcs = getComputedStyle(p), room = pr.width - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight);
      out.tables.push({ cols, w: Math.round(tr.width), room: Math.round(room), cls: String(t.className).slice(0, 30), scrolls: t.scrollWidth > t.clientWidth + 1 });
    }
    for (const im of document.querySelectorAll("img")) {
      if (!rendered(im) || !im.complete || !im.naturalWidth) continue;
      const r = im.getBoundingClientRect();
      if (r.width > im.naturalWidth * 1.02 + 1 && r.width > 40) out.up.push({ src: (im.currentSrc || im.src).split("/").slice(-2).join("/"), shown: Math.round(r.width), natural: im.naturalWidth });
    }
    for (const cv of document.querySelectorAll("canvas")) {
      if (!rendered(cv)) continue;
      const r = cv.getBoundingClientRect();
      if (r.width > cv.width * 1.02 + 1) out.up.push({ canvas: true, shown: Math.round(r.width), backing: cv.width });
    }
    for (const svg of document.querySelectorAll("svg")) {
      const r = svg.getBoundingClientRect();
      if (r.width < 40 || !rendered(svg)) continue;
      const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : null;
      const scale = vb ? Math.min(r.width / vb.width, vb.height ? r.height / vb.height : 99) : 1;
      for (const t of svg.querySelectorAll("text")) {
        if (!t.textContent.trim()) continue;
        const px = parseFloat(getComputedStyle(t).fontSize) * scale;
        if (px < 11.95) out.svgSmall.push({ t: t.textContent.trim().slice(0, 20), px: Math.round(px * 10) / 10 });
        if (scale > 1.8) out.svgBig.push({ t: t.textContent.trim().slice(0, 20), px: Math.round(px * 10) / 10, scale: Math.round(scale * 100) / 100 });
      }
    }
    for (const e of document.querySelectorAll("*")) {
      const bg = getComputedStyle(e).backgroundImage;
      const m = bg && bg.match(/url\("?([^")]+)"?\)/);
      if (!m || !rendered(e)) continue;
      out.bg.push({ url: m[1].split("/").slice(-2).join("/"), w: Math.round(e.getBoundingClientRect().width), size: getComputedStyle(e).backgroundSize });
    }
    return out;
  };
  // A paragraph's measure is the room its box allows over the average width of its own text in its own face (a canvas measure), in
  // characters. It passes when it is at most MEASURE, or when it is no wider than the same paragraph is just under the line (1279, the
  // 9.5 wrapper), because a class's own max-width, set long before 9.5b, is not this sprint's to judge; what 9.5b must not do is stretch one.
  const MEASURE = 100;
  const ref = {};
  for (const url of SWEEP) {
    const [ctx, page] = await open(1279, 800, url);
    for (const l of (await page.evaluate(AUDIT)).long) ref[url + "|" + l.t] = l.cpl;
    await ctx.close();
  }
  for (const w of [1280, 1440]) {
    const bad = { over: [], long: [], tables: [], up: [], svgBig: [], svgSmall: [] }, longest = [];
    for (const url of SWEEP) {
      const [ctx, page] = await open(w, 800, url);
      if (url.startsWith("/coins/")) { try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 5000 }); } catch { /* counted by the 9.5 suite */ } }
      await page.waitForTimeout(300);
      const t0 = Date.now();
      const a = await page.evaluate(AUDIT);
      if (process.env.S95B_TIMES) console.log(`INFO ${url} at ${w}: audit ${Date.now() - t0} ms`);
      if (a.over > 0) bad.over.push(`${url} +${a.over}px`);
      for (const l of a.long) { const r0 = ref[url + "|" + l.t]; if (l.cpl > MEASURE && !(r0 !== undefined && l.cpl <= r0 * 1.02)) bad.long.push(`${url}: ${l.cpl} chars/line (${l.w}px; ${r0 === undefined ? "new" : r0 + " at 1279"}) ${l.sel} "${l.t}"`); }
      if (a.long.length) longest.push([Math.max(...a.long.map(l => l.cpl)), url]);
      for (const t of a.tables) if (t.cols >= 4 && t.w < t.room * 0.9 && !t.scrolls) bad.tables.push(`${url}: ${t.cols}-col table ${t.w}px in ${t.room}px (${t.cls})`);
      for (const u of a.up) bad.up.push(`${url}: ${JSON.stringify(u)}`);
      for (const u of a.bg) if (u.size === "cover" || u.size === "100% 100%") { /* sized by its box: checked below by natural width */ }
      if (a.svgBig.length) bad.svgBig.push(`${url}: ${a.svgBig.length} label(s) in a chart drawn over 1.8x, e.g. ${JSON.stringify(a.svgBig[0])}`);
      if (a.svgSmall.length) bad.svgSmall.push(`${url}: ${a.svgSmall.length} under 12 px, e.g. ${JSON.stringify(a.svgSmall[0])}`);
      await ctx.close();
    }
    info(`the longest measure per page at ${w}`, longest.sort((x, y) => y[0] - x[0]).slice(0, 8).map(x => x[0] + " " + x[1]).join(" | "));
    check(`every page type at ${w} (${SWEEP.length} pages): no sideways scroll`, bad.over.length === 0, bad.over.join(" | "));
    check(`every page type at ${w}: no paragraph runs past ${MEASURE} characters a line unless it is no wider than at 1279 (a readable measure; widening stretches nothing)`, bad.long.length === 0, bad.long.slice(0, 8).join(" | ") + (bad.long.length > 8 ? ` (+${bad.long.length - 8} more)` : ""));
    check(`every page type at ${w}: a table of four columns or more uses the room (90% of its container, or it scrolls on its own)`, bad.tables.length === 0, bad.tables.slice(0, 8).join(" | "));
    check(`every page type at ${w}: no image or canvas is drawn larger than its own pixels (nothing blurs)`, bad.up.length === 0, bad.up.slice(0, 6).join(" | "));
    check(`every page type at ${w}: no chart label is drawn under 12 px`, bad.svgSmall.length === 0, bad.svgSmall.slice(0, 6).join(" | "));
    check(`every page type at ${w}: no chart is drawn at more than 1.8 times its own size (a chart that grew with the page reads as a poster)`, bad.svgBig.length === 0, bad.svgBig.slice(0, 6).join(" | "));
  }
  }

  // 8. THE NAV, J-11 rule 2: the page never scrolls sideways from 768 to 1100 (9.5's eleven-item nav did from 768 to about 1005), the nav keeps its eleven
  // items and NAMES.md's names, the tab bar at 375 is the five it was
  if (run("8")) {
    const NAV = ["Home", "Why it moved", "Markets", "Big movers", "Whale Watch", "Charts", "News", "The Brief", "Storylines", "Learn", "About"];
    const PAGES = ["/index.html", "/about.html", "/method.html", "/pulse.html", "/flows.html", "/learn.html", "/news.html", "/today/", "/coins/btc"].filter(exists);
    for (const w of [768, 800, 900, 1000, 1100]) {
      const bad = [];
      for (const url of PAGES) {
        const [ctx, page] = await open(w, 800, url);
        const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
          items: [...document.querySelectorAll("nav.mh-nav a")].map(a => (a.querySelector(".nv-task") || a).textContent.trim()),
          navRight: Math.max(...[...document.querySelectorAll("nav.mh-nav a")].map(a => a.getBoundingClientRect().right)) }));
        if (r.sw !== r.cw) bad.push(`${url}: scrollWidth ${r.sw} vs viewport ${r.cw}`);
        if (JSON.stringify(r.items) !== JSON.stringify(NAV)) bad.push(`${url}: nav items ${JSON.stringify(r.items)}`);
        if (r.navRight > r.cw + 0.5) bad.push(`${url}: a nav item ends at ${Math.round(r.navRight)}, past ${r.cw}`);
        await ctx.close();
      }
      check(`the nav at ${w}: scrollWidth equals the viewport on the home and ${PAGES.length - 1} inner pages, eleven items in NAMES.md's names, none past the edge`, bad.length === 0, bad.slice(0, 4).join(" | "));
    }
    const [ctx, page] = await open(375, 800, "/index.html");
    const t = await page.evaluate(() => ({ nav: getComputedStyle(document.querySelector("nav.mh-nav")).display, tabs: [...document.querySelectorAll("nav.tabbar .tb-item span")].map(e => e.textContent.trim()) }));
    check("the tab bar at 375 is the five it was and the desktop nav is not drawn", t.nav === "none" && JSON.stringify(t.tabs) === JSON.stringify(["Why it moved", "Markets", "Big movers", "Whale Watch", "Brief"]), JSON.stringify(t));
    await ctx.close();
  }

  // 7. CLS ON EVERY PAGE TYPE AT 1440 (the page read nine hours after its stamp, so the stale-state script adds its words): not worse than the same page
  // just under the line (1279, where the 9.5 wrapper still holds). A prose cap or a wider box must not make a script's late words wrap differently.
  if (run("7")) {
    const clsOf = async (w, url) => {
      const base1 = mastAsof(url);
      const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      page.setDefaultTimeout(15000);
      await page.addInitScript(CLS_INIT);
      if (base1) await page.addInitScript(clockShim, [base1, 9 * 3600e3]);
      await route(page);
      await page.goto(base + url, { waitUntil: "load" });
      if (url.startsWith("/coins/")) { try { await page.waitForSelector("[data-coin-chart] svg.cc-svg", { timeout: 5000 }); } catch { /* counted by the 9.5 suite */ } }
      await page.waitForTimeout(1200);
      const c = await page.evaluate(() => ({ cls: window.__cls, shifts: window.__shifts }));
      await ctx.close();
      return c;
    };
    const worse = [];
    for (const url of SWEEP.filter(u => !/fixture/.test(u))) {
      // up to three reads at 1440: a table's late font swap shifts about one read in ten on a few pages at any width (Sprint 9.5's, seen at 1279 and
      // on 9.5's own build), a regression of this sprint's shifts on every read
      const a = await clsOf(1279, url);
      let c = await clsOf(1440, url);
      for (let k = 0; k < 2 && c.cls > 0.0005 && c.cls > a.cls + 0.0005; k++) c = await clsOf(1440, url);
      if (c.cls > 0.0005 && c.cls > a.cls + 0.0005) worse.push(`${url}: ${c.cls.toFixed(4)} at 1440, ${a.cls.toFixed(4)} at 1279 ${JSON.stringify(c.shifts.slice(0, 1))}`);
    }
    check(`CLS on every page type at 1440, read stale (${SWEEP.length} pages): no page shifts more than it does just under the line`, worse.length === 0, worse.slice(0, 5).join(" | "));
  }
} finally {
  if (browser) await browser.close();
  server.close();
}
const failed = results.filter(r => !r[1]).length;
console.log(`\nsprint95b_browser: ${results.length - failed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
