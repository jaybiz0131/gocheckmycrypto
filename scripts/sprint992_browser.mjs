#!/usr/bin/env node
// sprint992_browser.mjs <publish dir> <model.json>
//
// Sprint 9.9.2 (October 27, 2026): the browser half of scripts/sprint992_test.py. It serves a built tree, aborts every other host,
// and for each page and width the model names (375 and 1440) reads the figures the page prints (the innerText of the body, which a
// browser computes from the real stylesheets) and compares them with the figures fact_sweep.py's width model says print there:
//
//     PASS <name>
//     FAIL <name>: <what was found>
//     INFO <name>: <a measurement, not a verdict>
//
// It also measures the Chart Master table's RSI-14 header at 375 with its columns shown: one line; and (fix round 3) Bitcoin's RSI as the
// page loads at 375 and 1440: printed once, in the BTC row the gauge names. Exit 1 when any check fails.
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import http from "http";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch (e) { console.log("FAIL playwright is not installed: " + e.message); process.exit(2); }
const [root, modelPath] = process.argv.slice(2);
const model = JSON.parse(fs.readFileSync(modelPath, "utf8"));
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml", ".json": "application/json",
                ".woff2": "font/woff2", ".png": "image/png", ".webp": "image/webp", ".ico": "image/x-icon", ".xml": "application/xml" };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]);
  let f = path.join(root, p);
  if (p.endsWith("/")) f = path.join(f, "index.html");
  else if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f = f + ".html";
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
  fs.createReadStream(f).pipe(res);
});
// the sweep's own figure pattern (fact_sweep.FIG), magnitude words included since fix round 2 ("$730.8 million"), in a headline's
// title case too since fix round 3 ("$73 Million")
const FIG = /(?<![\w$.,])[+\-−]?\$\d[\d,]*(?:\.\d+)?(?:\s?[KMBT]\b|\s(?:[Tt]housand|[Mm]illion|[Bb]illion|[Tt]rillion|THOUSAND|MILLION|BILLION|TRILLION)\b)?|(?<![\w.,$])[+\-−]?\d[\d,]*(?:\.\d+)?%/g;
let bad = 0;
const say = (ok, name, why) => { if (ok) console.log("PASS " + name); else { bad++; console.log("FAIL " + name + (why ? ": " + why : "")); } };
let browser;
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = "http://127.0.0.1:" + server.address().port;
try {
  browser = await pw.chromium.launch({ timeout: 60000 });
  for (const key of Object.keys(model)) {
    const [rel, w] = key.split("@");
    const ctx = await browser.newContext({ viewport: { width: +w, height: 900 }, javaScriptEnabled: false });
    await ctx.route("**/*", r => r.request().url().startsWith(base) ? r.continue() : r.abort());
    const pg = await ctx.newPage();
    await pg.goto(base + "/" + rel, { waitUntil: "load", timeout: 60000 });
    if (rel === "chartmaster.html") {
      // fix round 3 (review 2, failure 5): as the page loads, no control opened, the reader sees Bitcoin's RSI once, in the data card's
      // BTC row the gauge names, and the table fits its box
      const seen = await pg.evaluate(() => {
        const tbl = document.querySelector(".cm-datacard table");
        const gauge0 = [...document.querySelectorAll("figure")].filter(f => /RSI/.test(f.innerText));
        if (!tbl) return { card: false, gaugeNums: gauge0.map(f => f.innerText.match(/(?:^|\s)(\d{1,3}\.\d)(?:\s|$)/g) || []).flat(),
                           pointer: gauge0.some(f => /printed in its BTC row below/.test(f.innerText)) };
        const heads = [...tbl.querySelectorAll("thead th")].map(x => x.textContent.trim());
        const k = heads.indexOf("RSI-14");
        const row = [...tbl.querySelectorAll("tbody tr")].find(r => r.querySelector("th") && r.querySelector("th").textContent.trim() === "BTC");
        const cell = row && k > 0 ? row.children[k] : null;
        const wrap = tbl.parentElement;
        const gauge = [...document.querySelectorAll("figure")].filter(f => /RSI/.test(f.innerText));
        const gaugeNums = gauge.map(f => f.innerText.match(/(?:^|\s)(\d{1,3}\.\d)(?:\s|$)/g) || []).flat();
        return { cell: cell ? cell.innerText.trim() : null, shown: cell ? getComputedStyle(cell).display !== "none" && cell.getClientRects().length > 0 : false,
                 fits: wrap ? tbl.scrollWidth <= wrap.clientWidth + 1 : null, gaugeNums, pointer: gauge.some(f => /printed in its BTC row below/.test(f.innerText)) };
      });
      console.log(`INFO chartmaster.html at ${w}, as it loads: ` + JSON.stringify(seen));
      if (seen && seen.card === false) {
        // a written read carries no data card: the gauge prints Bitcoin's RSI itself, once, and points nowhere
        say(seen.gaugeNums.length === 1 && !seen.pointer, `chartmaster.html at ${w}: with no data card the gauge prints Bitcoin's RSI once`,
            JSON.stringify(seen));
      } else {
        say(seen && seen.shown && /^\d{1,3}(\.\d)?$/.test(seen.cell || "") && seen.gaugeNums.length === 0 && seen.pointer,
            `chartmaster.html at ${w}: Bitcoin's RSI is printed once where the reader sees it, the BTC row the gauge names`, JSON.stringify(seen));
        say(seen && seen.fits, `chartmaster.html at ${w}: the data card's table fits its box with the RSI-14 column shown`, JSON.stringify(seen));
      }
    }
    // innerText omits what CSS hides and carries an SVG's <text>; an SVG <title> is a tooltip and is not printed
    // what a reader can reveal counts as printed, as the model reads it: every "Show all columns" box checked, every <details> open
    const shown = await pg.evaluate(() => {
      document.querySelectorAll("input.fit-cb").forEach(x => { x.checked = true; });
      document.querySelectorAll("details").forEach(x => { x.open = true; });
      const t = [document.body.innerText];
      document.querySelectorAll(".sr-only,.visually-hidden").forEach(x => t.push("\u0000" + x.innerText));
      return t;
    });
    const srOnly = shown.filter(x => x.startsWith("\u0000")).join(" ");
    const text = shown.filter(x => !x.startsWith("\u0000")).join(" \n ");
    const got = (text.match(FIG) || []).map(s => s.trim());
    const sr = new Set((srOnly.match(FIG) || []).map(s => s.trim()));
    const want = model[key];
    const count = a => a.reduce((m, x) => (m[x] = (m[x] || 0) + 1, m), {});
    const g = count(got.filter(x => !sr.has(x))), m = count(want.filter(x => !sr.has(x)));
    const diff = [...new Set([...Object.keys(g), ...Object.keys(m)])].filter(k => (g[k] || 0) !== (m[k] || 0));
    say(diff.length === 0, `${rel} at ${w}: the figures the browser prints are the figures the sweep's width model reads`,
        diff.slice(0, 6).map(k => `${k} browser ${g[k] || 0} model ${m[k] || 0}`).join("; "));
    if (rel === "chartmaster.html" && +w === 375) {
      const box = await pg.evaluate(() => {
        const cb = document.querySelector(".cm-datacard .fit-cb, .fit-cb");
        if (cb) { cb.checked = true; }
        const th = [...document.querySelectorAll("th")].find(x => x.textContent.trim() === "RSI-14");
        if (!th) return null;
        const r = document.createRange(); r.selectNodeContents(th);
        const lines = new Set([...r.getClientRects()].map(q => Math.round(q.top)));
        return { lines: lines.size, display: getComputedStyle(th).display, ws: getComputedStyle(th).whiteSpace };
      });
      console.log("INFO chartmaster.html at 375: RSI-14 header " + JSON.stringify(box));
      say(box && box.display !== "none" && box.lines === 1, "the RSI-14 header fits one line at 375 with every column shown",
          JSON.stringify(box));
    }
    await ctx.close();
  }
} catch (e) {
  bad++;
  console.log("FAIL the browser half raised: " + (e && e.message));
} finally {
  if (browser) await browser.close();
  server.close();
}
process.exit(bad ? 1 : 0);
