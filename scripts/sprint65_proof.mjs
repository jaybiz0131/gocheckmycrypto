#!/usr/bin/env node
// sprint65_proof.mjs <before-tree> <after-tree> <rows-dir> <outdir>
// Sprint 6.5 proof shots at 375, light and dark, from recorded data only:
//   top100-first-<before|after>-<theme>.png   the Top 100's first screen (375 x 812), the build's own rows
//   row-<SYM>-<before|after>-<theme>.png      one row of production's recorded Top 100 (rows-before.html in the
//                                             before tree's CSS and markup, rows-after.html in the after tree's)
import { createRequire } from "module"; import http from "http"; import fs from "fs"; import path from "path";
const require = createRequire(import.meta.url);
let pw; try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const [beforeDir, afterDir, rowsDir, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const MIME = { ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png" };
const serve = async root => { const s = http.createServer((q, r) => { const p = decodeURIComponent(new URL(q.url, "http://x").pathname); let f = path.join(path.resolve(root), p);
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
  if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": MIME[path.extname(f)] || "text/html" }); fs.createReadStream(f).pipe(r); });
  await new Promise(r => s.listen(0, "127.0.0.1", r)); return [s, `http://127.0.0.1:${s.address().port}`]; };
const ROWS = ["BTT", "SHIB", "HYPE", "CAKE", "FET", "币安人生"];
let b; const servers = [];
try {
  b = await pw.chromium.launch({ timeout: 30000 });
  for (const [label, dir, rf] of [["before", beforeDir, "rows-before.html"], ["after", afterDir, "rows-after.html"]]) {
    const [srv, base] = await serve(dir); servers.push(srv);
    for (const theme of ["light", "dark"]) {
      const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, colorScheme: theme, deviceScaleFactor: 2 });
      const pg = await ctx.newPage(); pg.setDefaultTimeout(8000);
      await pg.route(/^https?:/, r => new URL(r.request().url()).host === new URL(base).host ? r.continue() : r.abort());
      await pg.goto(base + "/pulse/prices", { waitUntil: "load" }); await pg.waitForTimeout(500);
      await pg.screenshot({ path: path.join(out, `top100-first-${label}-${theme}.png`) });
      await pg.evaluate(h => { document.querySelector(".prices-table tbody").innerHTML = h; }, fs.readFileSync(path.join(rowsDir, rf), "utf8"));
      await pg.waitForTimeout(300);
      for (const sym of ROWS) {
        const row = pg.locator(`.prices-table tbody tr[data-sym="${sym}"]`);
        await row.scrollIntoViewIfNeeded();
        await row.screenshot({ path: path.join(out, `row-${sym === "币安人生" ? "BinanceLife" : sym}-${label}-${theme}.png`) });
      }
      await ctx.close();
    }
  }
} finally { if (b) await b.close(); servers.forEach(s => s.close()); }
console.log("done");
