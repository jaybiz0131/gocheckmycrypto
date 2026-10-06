#!/usr/bin/env node
// ticker_mark_375.mjs <url> [--wait ms] [--expect-live] [--width 375]
//
// The ticker's live mark at phone width (Jack, 6 October 2026: shown, never hidden). The
// ticker is the only live surface on the site and the phone is most readers, so at 375 the
// label "#mktAsOf" must be rendered, in the mono, at the tape's smallest size, with its
// whole box inside the viewport and not covered. Exit 0 only when every check holds; the
// checks and the label's text are printed either way.
//
// U-7: Chrome is launched with a timeout and killed in a finally block.
import { spawn } from "child_process";

const CHROME = process.env.CHROME_BIN ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const argv = process.argv.slice(2);
const url = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > -1 ? argv[i + 1] : d; };
const WIDTH = parseInt(opt("--width", "375"), 10);
const HEIGHT = 812;
const WAIT = parseInt(opt("--wait", "6000"), 10);
const EXPECT_LIVE = argv.includes("--expect-live");
const LIMIT_MS = 60000;
if (!url) { console.log("usage: ticker_mark_375.mjs <url> [--wait ms] [--expect-live]"); process.exit(2); }

const PORT = 9300 + (process.pid % 400);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const PROBE = `(() => {
  const el = document.getElementById("mktAsOf");
  if (!el) return {found: false};
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  // the tape's smallest size: the smallest font-size among the strip's text at this width
  const sizes = [...document.querySelectorAll(
      ".markets .lab, .markets .tick .sym, .markets .tick .px, .markets .tick .chg")]
    .map(n => parseFloat(getComputedStyle(n).fontSize)).filter(n => n > 0);
  let hiddenBy = null;
  for (let n = el; n && n !== document.documentElement; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity) === 0) {
      hiddenBy = n.id ? "#" + n.id : n.className || n.tagName; break; }
  }
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hit = document.elementFromPoint(cx, cy);
  const board = document.querySelector(".bd-value");
  return {found: true, text: el.textContent.trim(), display: cs.display,
    visibility: cs.visibility, fontFamily: cs.fontFamily, fontSize: parseFloat(cs.fontSize),
    tapeMin: sizes.length ? Math.min(...sizes) : null,
    monoVar: getComputedStyle(document.documentElement).getPropertyValue("--mono").trim(),
    box: {left: r.left, top: r.top, right: r.right, bottom: r.bottom, w: r.width, h: r.height},
    vw: document.documentElement.clientWidth, vh: innerHeight, hiddenBy,
    covered: !(hit && (hit === el || el.contains(hit))),
    stripH: (document.querySelector(".markets") || {}).offsetHeight || null,
    ticks: [...document.querySelectorAll(".markets .tick[data-id]")].map(t => {
      const b = t.getBoundingClientRect(); return [t.dataset.sym, Math.round(b.left), Math.round(b.right)]; }),
    boardTop: board ? Math.round(board.getBoundingClientRect().top + scrollY) : null};
})()`;

let chrome = null;
let killTimer = null;
let code = 1;
try {
  chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--force-device-scale-factor=1", `--remote-debugging-port=${PORT}`, "about:blank"],
    { stdio: "ignore" });
  killTimer = setTimeout(() => { console.log("FAIL timeout"); try { chrome.kill("SIGKILL"); } catch {} process.exit(1); }, LIMIT_MS);
  let tgt = null;
  for (let i = 0; i < 80 && !tgt; i++) {
    await sleep(250);
    try { tgt = (await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl; } catch {}
  }
  if (!tgt) throw new Error("chrome did not start");
  const ws = new WebSocket(tgt); const pend = new Map(); let id = 0;
  const cmd = (m, p, s) => new Promise(res => { const n = ++id; pend.set(n, res);
    ws.send(JSON.stringify({ id: n, method: m, params: p, ...(s ? { sessionId: s } : {}) })); });
  await new Promise(r => ws.onopen = r);
  ws.onmessage = e => { const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); } };
  const { targetId } = await cmd("Target.createTarget", { url: "about:blank" });
  const { sessionId: S } = await cmd("Target.attachToTarget", { targetId, flatten: true });
  await cmd("Page.enable", {}, S);
  await cmd("Emulation.setDeviceMetricsOverride",
    { width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: true }, S);
  await cmd("Page.navigate", { url }, S);
  await sleep(WAIT);
  const r = await cmd("Runtime.evaluate", { expression: PROBE, returnByValue: true }, S);
  const v = r.result.value;
  const checks = [];
  const ck = (name, ok, got) => checks.push([name, !!ok, got]);
  ck("label present", v.found, v.found);
  if (v.found) {
    ck("display is not none", v.display !== "none", v.display);
    ck("no ancestor hides it", !v.hiddenBy, v.hiddenBy || "none");
    ck("visibility visible", v.visibility === "visible", v.visibility);
    ck("box has size", v.box.w > 0 && v.box.h > 0, `${v.box.w.toFixed(1)}x${v.box.h.toFixed(1)}`);
    ck("box inside the viewport", v.box.left >= 0 && v.box.top >= 0 &&
       v.box.right <= v.vw && v.box.bottom <= v.vh,
       `l${v.box.left.toFixed(1)} t${v.box.top.toFixed(1)} r${v.box.right.toFixed(1)} b${v.box.bottom.toFixed(1)} in ${v.vw}x${v.vh}`);
    ck("not covered", !v.covered, v.covered ? "covered" : "on top");
    ck("in the mono", /plex mono|mono/i.test(v.fontFamily), v.fontFamily);
    ck("at the tape's smallest size", v.tapeMin != null && Math.abs(v.fontSize - v.tapeMin) < 0.01,
       `${v.fontSize}px vs ${v.tapeMin}px`);
    ck("has text", v.text.length > 0, JSON.stringify(v.text));
    if (EXPECT_LIVE) ck("says live with its zone", /^live · \d{1,2}:\d{2} [AP]M ET$/.test(v.text),
                        JSON.stringify(v.text));
  }
  for (const [n, ok, got] of checks) console.log(`${ok ? "ok  " : "FAIL"} ${n}: ${got}`);
  console.log(`strip height ${v.stripH}px; first Board figure at ${v.boardTop}px; ticks ${JSON.stringify(v.ticks)}`);
  code = checks.every(c => c[1]) ? 0 : 1;
  console.log(code === 0 ? "PASS ticker live mark at " + WIDTH : "RED ticker live mark at " + WIDTH);
} catch (e) {
  console.log("FAIL harness: " + String(e).slice(0, 160));
  code = 1;
} finally {
  if (killTimer) clearTimeout(killTimer);
  if (chrome) { try { chrome.kill("SIGKILL"); } catch {} }
}
process.exit(code);
