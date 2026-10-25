// Tests for the live-price route. Run: node worker/live-prices.test.mjs (in gcm-newsroom the patch puts it at slot-trigger/test/ with the import pointed at ../src/)
// Every answer is a recorded-shape stand-in for CoinGecko's; no network is touched.
import { routeLivePrices, parseIds, LIVE_TTL_S, DEFAULT_IDS, SITE_ORIGINS } from "./live-prices.mjs";

let pass = 0, fail = 0;
const ok = (c, w) => { if (c) { pass++; console.log("  ok   " + w); } else { fail++; console.log("  FAIL " + w); } };

// a cache that honors max-age against an injected clock, as the edge cache does
function fakeCache(clock) {
  const m = new Map();
  return { m,
    async match(req) {
      const e = m.get(req.url);
      if (!e || clock.t >= e.expires) return undefined;
      return new Response(e.body, { headers: e.headers });
    },
    async put(req, res) {
      const cc = res.headers.get("Cache-Control") || "";
      const ttl = parseInt((cc.match(/max-age=(\d+)/) || [])[1] || "0", 10);
      m.set(req.url, { body: await res.text(), headers: [...res.headers], expires: clock.t + ttl * 1000 });
    } };
}
const SIMPLE = { bitcoin: { usd: 82893, usd_24h_change: 1.15 }, ethereum: { usd: 2447.08, usd_24h_change: 1.78 } };
const GLOBAL = { data: { total_market_cap: { usd: 2.79e12 }, market_cap_change_percentage_24h_usd: -1.43, market_cap_percentage: { btc: 59.5 } } };
function upstream(calls, mode) {
  return async (url) => {
    calls.push(url);
    if (mode.down) return new Response("busy", { status: 429 });
    if (mode.bad) return new Response("{}", { status: 200 });
    const body = url.includes("/global") ? GLOBAL : SIMPLE;
    return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
  };
}
const req = (path, init) => new Request("https://w.example/live/prices" + path, init);
const clock = { t: Date.parse("2026-10-21T05:00:00Z") };
const now = () => new Date(clock.t);

{ // shape, and the cache
  const calls = [], mode = {}, cache = fakeCache(clock);
  const deps = { fetchFn: upstream(calls, mode), cache };
  let r = await routeLivePrices(req(""), {}, now(), deps);
  let b = await r.json();
  ok(r.status === 200 && b.stale === false && b.as_of_utc === "2026-10-21T05:00:00Z", "a miss reads CoinGecko and answers fresh, stamped with its read time");
  ok(b.simple.bitcoin.usd === 82893 && b.global.data.market_cap_percentage.btc === 59.5, "the body carries CoinGecko's /simple/price and /global answers verbatim");
  ok(b.schema === "gocheckmycrypto.com/live-prices/1" && b.cache_seconds === LIVE_TTL_S && /CoinGecko/.test(b.source), "the schema, the cache window and the source are named");
  ok(calls.length === 2 && calls[0].includes("ids=" + DEFAULT_IDS.slice().sort().join(",")) && calls[0].includes("include_24hr_change=true"), "two upstream reads, the default four coins");
  clock.t += 30_000;
  r = await routeLivePrices(req(""), {}, now(), deps); b = await r.json();
  ok(calls.length === 2 && r.headers.get("x-live-cache") === "hit" && b.as_of_utc === "2026-10-21T05:00:00Z", "30 seconds on: served from the cache, no new upstream read, the original read time");
  ok(/max-age=60/.test(r.headers.get("Cache-Control")), "the answer is cacheable for 60 seconds");
  clock.t += 31_000;
  r = await routeLivePrices(req(""), {}, now(), deps); b = await r.json();
  ok(calls.length === 4 && b.as_of_utc === "2026-10-21T05:01:01Z" && b.stale === false, "past 60 seconds: one new read of each, a new read time");
  ok(r.headers.get("set-cookie") === null, "no cookie is set");
  // CoinGecko down: the last good answer, flagged stale
  mode.down = true; clock.t += 120_000;
  r = await routeLivePrices(req(""), {}, now(), deps); b = await r.json();
  ok(r.status === 200 && b.stale === true && b.as_of_utc === "2026-10-21T05:01:01Z" && r.headers.get("x-live-cache") === "last-good",
     "CoinGecko refusing: the last good answer is served flagged stale, with its own read time, never re-stamped");
  ok(r.headers.get("Cache-Control") === "no-store", "a stale answer is not cacheable");
  clock.t += 3_700_000;
  r = await routeLivePrices(req(""), {}, now(), deps); b = await r.json();
  ok(r.status === 502 && b.ok === false, "CoinGecko down and nothing held (an hour past): 502 and no invented figure");
  mode.down = false; mode.bad = true;
  r = await routeLivePrices(req("?ids=bitcoin"), {}, now(), deps);
  ok(r.status === 502, "a malformed answer from CoinGecko is not cached or served");
}
{ // ids
  const u = (q) => new URL("https://w/live/prices" + q);
  ok(JSON.stringify(parseIds(u("?ids=Ethereum,bitcoin,bitcoin"))) === '["bitcoin","ethereum"]', "ids are lower-cased, de-duplicated and sorted");
  ok(parseIds(u("?ids=")) === null && parseIds(u("?ids=a b")) === null && parseIds(u("?ids=../x")) === null, "empty, spaced and path-like ids are refused");
  ok(parseIds(u("?ids=" + Array.from({ length: 26 }, (_, i) => "c" + i).join(","))) === null, "more than 25 ids are refused");
  const calls = [], cache = fakeCache(clock);
  const r = await routeLivePrices(req("?ids=a;b"), {}, now(), { fetchFn: upstream(calls, {}), cache });
  ok(r.status === 400 && calls.length === 0, "a bad id is a 400 and costs no upstream read");
}
{ // methods and CORS
  const deps = { fetchFn: upstream([], {}), cache: fakeCache(clock) };
  let r = await routeLivePrices(req("", { method: "POST" }), {}, now(), deps);
  ok(r.status === 405 && r.headers.get("Allow") === "GET, OPTIONS", "POST is a 405");
  r = await routeLivePrices(req("", { method: "OPTIONS", headers: { Origin: SITE_ORIGINS[0] } }), {}, now(), deps);
  ok(r.status === 204 && r.headers.get("Access-Control-Allow-Origin") === SITE_ORIGINS[0], "the preflight allows the site's origin");
  r = await routeLivePrices(req("", { headers: { Origin: "https://evil.example" } }), {}, now(), deps);
  ok(r.status === 200 && r.headers.get("Access-Control-Allow-Origin") === null, "another origin gets no allow header (a browser there cannot read it)");
  r = await routeLivePrices(req("", { headers: { Origin: SITE_ORIGINS[1] } }), {}, now(), deps);
  ok(r.headers.get("Access-Control-Allow-Origin") === SITE_ORIGINS[1] && r.headers.get("Vary") === "Origin", "the www origin is allowed and Vary: Origin is set");
}
{ // wired into the Worker's fetch handler (present only where this test sits beside the Worker's source)
  let worker = null;
  try { worker = (await import("../src/worker.js")).default; } catch (e) { worker = null; }
  if (worker) {
    const calls = [];
    globalThis.fetch = upstream(calls, {});
    globalThis.caches = { default: fakeCache(clock) };
    const r = await worker.fetch(req("?ids=bitcoin"), {});
    const b = await r.json();
    ok(r.status === 200 && b.stale === false && b.simple.bitcoin.usd === 82893, "GET /live/prices on the Worker's fetch handler reaches the route");
    const s = await worker.fetch(new Request("https://w.example/counts/today"), {});
    ok(s.status === 503 || s.status === 200, "the Worker's other routes still answer (counts, with no KV bound here)");
  } else {
    console.log("  note the Worker's source is not beside this test; the wiring case is skipped");
  }
}
console.log(`\nlive-prices: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
