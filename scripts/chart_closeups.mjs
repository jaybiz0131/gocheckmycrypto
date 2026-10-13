#!/usr/bin/env node
// chart_closeups.mjs <built-site-dir> <outdir> [--coin btc] [--cg fixtures/coingecko]
// Sprint 6.4 proof: close-ups of one coin's chart at 375, on 1D and 1Y, light and dark, with the crosshair
// shown once (the touch lands at 62 percent of the plot). CoinGecko is answered from recorded fixtures.
import { createRequire } from "module"; import http from "http"; import fs from "fs"; import path from "path";
const require = createRequire(import.meta.url);
let pw; try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }
const a = process.argv.slice(2), opt = (k, d) => { const i = a.indexOf(k); return i > -1 ? a[i + 1] : d; };
const root = path.resolve(a[0]), out = a[1], coin = opt("--coin", "btc"), CG = opt("--cg", "fixtures/coingecko");
fs.mkdirSync(out, { recursive: true });
const server = http.createServer((q, s) => { let p = decodeURIComponent(new URL(q.url, "http://x").pathname), f = path.join(root, p);
  if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html"; if (!fs.existsSync(f)) { s.writeHead(404); return s.end(); }
  s.writeHead(200, { "content-type": { ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png" }[path.extname(f)] || "text/html" }); fs.createReadStream(f).pipe(s); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
let b;
try {
  b = await pw.chromium.launch({ timeout: 30000 });
  for (const theme of ["light", "dark"]) {
    const ctx = await b.newContext({ viewport: { width: 375, height: 900 }, colorScheme: theme, hasTouch: true });
    const pg = await ctx.newPage(); pg.setDefaultTimeout(8000);
    await pg.route(/^https?:/, r => { const u = new URL(r.request().url()); if (u.host === new URL(base).host) return r.continue();
      const m = u.host === "api.coingecko.com" && u.pathname.match(/\/coins\/([^/]+)\/market_chart/);
      if (!m) return r.abort(); const d = +u.searchParams.get("days"), k = d <= 1 ? 1 : d <= 7 ? 7 : d <= 365 ? 365 : 565;
      const f = fs.existsSync(path.join(CG, `${m[1]}-${k}.json`)) ? `${m[1]}-${k}.json` : `bitcoin-${k}.json`;
      return r.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: fs.readFileSync(path.join(CG, f)) }); });
    await pg.goto(`${base}/coins/${coin}`, { waitUntil: "load" });
    for (const rg of ["1d", "1y"]) {
      await pg.locator(`[data-coin-chart] [role=tab][data-range="${rg}"]`).click();
      await pg.waitForFunction(r => document.querySelector("[data-coin-chart]").getAttribute("data-range") === r, rg);
      await pg.waitForTimeout(1200);
      const box = await pg.locator("[data-coin-chart] .cc-stage svg.cc-svg").boundingBox();
      await pg.evaluate(({ x, y }) => { const s = document.querySelector("[data-coin-chart] svg.cc-svg");
        const o = { clientX: x, clientY: y, pointerType: "touch", pointerId: 3, bubbles: true, isPrimary: true };
        s.dispatchEvent(new PointerEvent("pointerdown", o)); }, { x: box.x + box.width * 0.62, y: box.y + 80 });
      await pg.waitForTimeout(150);
      await pg.locator("[data-coin-chart]").screenshot({ path: path.join(out, `${coin}-chart-${rg}-375-${theme}.png`) });
    }
    await ctx.close();
  }
} finally { if (b) await b.close(); server.close(); }
console.log("done");
