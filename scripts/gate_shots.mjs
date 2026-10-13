#!/usr/bin/env node
// gate_shots.mjs <outdir> <spec.json>      Program 7 Sprint 7.3: before beside after, 375 wide, light and dark.
//
// BEFORE is the live production page as it stands today. AFTER is the same page with only the
// sentences this sprint changes swapped in by the DOM (nothing else on the page moves):
//   home    the Brief card's narrative line: the clause table's line for TODAY'S real readings
//           (data/narrative.json on production), old pairing beside the new one;
//   edition the 10 October Edition with the three sentences the old gate cut put back, verbatim
//           from the run's own wrap-status.json. Their paragraph is the gate's; the place inside
//           the field is inferred (end of the dek and bottom line, second sentence of body 3)
//           and every restored sentence is outlined so a reader sees exactly what changed.
// U-7: the browser is launched with a timeout and closed in a finally block.
import { createRequire } from "module";
import fs from "fs";
import path from "path";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); }
catch { pw = require(process.env.PLAYWRIGHT_MODULE || "/opt/node-tools/node_modules/playwright"); }

const [outdir, specFile] = process.argv.slice(2);
if (!outdir || !specFile) { console.log("usage: gate_shots.mjs <outdir> <spec.json>"); process.exit(2); }
const spec = JSON.parse(fs.readFileSync(specFile, "utf8"));
fs.mkdirSync(outdir, { recursive: true });

const MARK = "outline:2px solid #C8261B;outline-offset:2px;border-radius:2px;";

async function shoot(browser, theme, url, edit, file, clipFn) {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 900 }, colorScheme: theme,
                                          deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: "load", timeout: 45000 });
    await page.waitForTimeout(2500);
    if (edit) await page.evaluate(edit);
    await page.waitForTimeout(300);
    const clip = clipFn ? await page.evaluate(clipFn) : null;
    if (clip) await page.screenshot({ path: file, clip, fullPage: true });
    else await page.screenshot({ path: file, fullPage: true });
  } finally { await ctx.close(); }
}

const browser = await pw.chromium.launch({ timeout: 60000 });
try {
  for (const theme of ["light", "dark"]) {
    // ---- home: the Brief card
    const homeClip = `(() => { const el = document.querySelector('section.h-band'); const r = el.getBoundingClientRect();
      return { x: 0, y: Math.max(0, r.top + window.scrollY - 8), width: 375, height: r.height + 16 }; })()`;
    await shoot(browser, theme, spec.home.url, null, path.join(outdir, `home-before-${theme}.png`), homeClip);
    const homeEdit = `(() => { const p = document.querySelector('p.h-nline'); p.textContent = ${JSON.stringify(spec.home.newLine)};
      p.style.cssText += ${JSON.stringify(MARK)}; })()`;
    await shoot(browser, theme, spec.home.url, homeEdit, path.join(outdir, `home-after-${theme}.png`), homeClip);
    // ---- edition
    await shoot(browser, theme, spec.edition.url, null, path.join(outdir, `edition-before-${theme}.png`), null);
    const ed = spec.edition;
    const edEdit = `(() => {
      const mark = ${JSON.stringify(MARK)};
      const add = (p, text, where) => { const s = document.createElement('span'); s.textContent = text; s.style.cssText = mark;
        if (where === 'after-first') { const t = p.textContent; const i = t.indexOf('. ') + 2; const a = t.slice(0, i); const b = t.slice(i);
          p.textContent = a; p.appendChild(s); p.appendChild(document.createTextNode(' ' + b)); }
        else { p.appendChild(document.createTextNode(' ')); p.appendChild(s); } };
      add(document.querySelector('p.dek'), ${JSON.stringify(ed.dek)}, 'end');
      add(document.querySelector('.bottomline p'), ${JSON.stringify(ed.bottomLine)}, 'end');
      const ps = document.querySelectorAll('.prose p'); add(ps[2], ${JSON.stringify(ed.body3)}, 'after-first');
    })()`;
    await shoot(browser, theme, spec.edition.url, edEdit, path.join(outdir, `edition-after-${theme}.png`), null);
  }
} finally { await browser.close(); }

// ---- side by side sheets (before | after), one per surface and theme
const b2 = await pw.chromium.launch({ timeout: 60000 });
try {
  for (const theme of ["light", "dark"]) {
    for (const surf of ["home", "edition"]) {
      const bg = theme === "dark" ? "#0B1422" : "#FFFFFF", fg = theme === "dark" ? "#E8EEF7" : "#0F1B2D";
      const b64 = f => "data:image/png;base64," + fs.readFileSync(path.join(outdir, f)).toString("base64");
      const html = `<body style="margin:0;background:${bg};color:${fg};font:600 13px/1.3 system-ui;padding:12px">
        <div style="display:flex;gap:16px;align-items:flex-start">
        <div><div style="margin:0 0 6px">BEFORE (production, ${spec.stamp})</div><img src="${b64(`${surf}-before-${theme}.png`)}" style="width:375px;display:block"></div>
        <div><div style="margin:0 0 6px">AFTER (this branch's gate and clause table)</div><img src="${b64(`${surf}-after-${theme}.png`)}" style="width:375px;display:block"></div>
        </div></body>`;
      const pg = await b2.newPage({ viewport: { width: 800, height: 400 }, deviceScaleFactor: 1 });
      await pg.setContent(html);
      await pg.waitForTimeout(400);
      await pg.screenshot({ path: path.join(outdir, `sheet-${surf}-375-${theme}.png`), fullPage: true });
      await pg.close();
    }
  }
} finally { await b2.close(); }
console.log("wrote", fs.readdirSync(outdir).filter(f => f.startsWith("sheet-")).join(", "));
