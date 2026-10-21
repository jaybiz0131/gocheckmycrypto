// sprint97_h1_identity.mjs <old built tree> <new built tree> [page]: Sprint 9.7, the coin page heading is an h1 with the h2 look. Compares the two trees at 375, 768, 1440, light and dark: the top 420 pixels and the heading metrics.
import { createRequire } from "module";
import http from "http"; import fs from "fs"; import path from "path";
const require = createRequire(import.meta.url);
const pw = require("/opt/node-tools/node_modules/playwright");
const [oldDir, newDir, pageUrl = "/coins/btc.html"] = process.argv.slice(2);
const MIME = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
function serve(root) {
  return new Promise(res => {
    const s = http.createServer((req, rsp) => {
      let p = decodeURIComponent(new URL(req.url, "http://x").pathname); let f = path.join(root, p);
      if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
      if (!fs.existsSync(f) && fs.existsSync(f + ".html")) f += ".html";
      if (!fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" }); fs.createReadStream(f).pipe(rsp);
    });
    s.listen(0, "127.0.0.1", () => res([s, `http://127.0.0.1:${s.address().port}`]));
  });
}
const [s1, b1] = await serve(oldDir), [s2, b2] = await serve(newDir);
const browser = await pw.chromium.launch();
const out = [];
for (const scheme of ["light", "dark"]) for (const w of [375, 768, 1440]) {
  const rows = [];
  for (const [b, tag] of [[b1, "old"], [b2, "new"]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, colorScheme: scheme });
    const page = await ctx.newPage();
    await page.route(/^https?:/, r => new URL(r.request().url()).host === new URL(b).host ? r.continue() : r.abort());
    await page.goto(b + pageUrl, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    const m = await page.evaluate(() => {
      const h = document.querySelector(".cn-head h1, .cn-head h2"); const cs = getComputedStyle(h); const hd = document.querySelector(".cn-head");
      const r = e => { const b = e.getBoundingClientRect(); return [Math.round(b.x * 100) / 100, Math.round(b.y * 100) / 100, Math.round(b.width * 100) / 100, Math.round(b.height * 100) / 100]; };
      const nxt = hd.nextElementSibling; const pin = document.querySelector(".cn-pinwrap");
      return { tag: h.tagName, style: ["fontFamily", "fontSize", "fontWeight", "lineHeight", "letterSpacing", "marginTop", "marginBottom", "marginLeft", "color", "whiteSpace", "display", "textTransform"].map(k => cs[k]).join(" | "),
        h: r(h), head: r(hd), next: nxt ? r(nxt) : null, pin: pin ? r(pin) : null, docH: document.documentElement.scrollHeight };
    });
    const shot = await page.screenshot({ clip: { x: 0, y: 0, width: w, height: 420 } });
    rows.push({ tag, m, shot });
    await ctx.close();
  }
  const same = Buffer.compare(rows[0].shot, rows[1].shot) === 0;
  const dm = JSON.stringify({ ...rows[0].m, tag: 0 }) === JSON.stringify({ ...rows[1].m, tag: 0 });
  console.log(`${scheme} ${w}: top-420px screenshot identical=${same}; metrics identical=${dm}`);
  if (!dm) { console.log("  old", JSON.stringify(rows[0].m)); console.log("  new", JSON.stringify(rows[1].m)); }
}
await browser.close(); s1.close(); s2.close();
