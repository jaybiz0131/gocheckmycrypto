// live-prices.mjs: GET /live/prices, the gcm-newsroom Worker's live-price route (Program 9, Sprint 9.7; AUDIT.md 3.5 item 4).
//
// WHY. Every reader's browser asked CoinGecko's free tier for the ticker's prices and was refused about three loads in
// four. This route asks CoinGecko once a minute for everyone and serves the answer from the edge cache. It serves the site's
// tape now and the app and widgets later.
//
// WHAT IT RETURNS. The two answers the page already reads, verbatim and in the shape CoinGecko sent them, so a page can swap
// one source for the other without changing a line of its own handling:
//   { schema, as_of_utc, stale, cache_seconds, source, simple: <CoinGecko /simple/price body>, global: <CoinGecko /global body> }
// `stale` is false for an answer read inside the last 60 seconds, and true when CoinGecko failed and the last good answer
// (kept an hour) is served instead. A page treats stale: true as "route absent" and asks CoinGecko itself.
//
// WHAT IT IS NOT. It keeps no log of who asked, sets no cookie, and calls nothing but CoinGecko. It answers one origin.
//
// Wiring: in worker.js, `import { routeLivePrices } from "./live-prices.mjs";` and, first in fetch():
//   if (url.pathname === "/live/prices") return routeLivePrices(request, env, now);
export const LIVE_TTL_S = 60;           // an answer is fresh for a minute
export const LAST_GOOD_TTL_S = 3600;    // and the last good one is kept an hour, for a CoinGecko outage
export const DEFAULT_IDS = ["bitcoin", "ethereum", "solana", "ripple"];
export const MAX_IDS = 25;
export const ID_RX = /^[a-z0-9][a-z0-9-]{0,59}$/;
export const SITE_ORIGINS = ["https://gocheckmycrypto.com", "https://www.gocheckmycrypto.com"];
const CG = "https://api.coingecko.com/api/v3";
const KEY_BASE = "https://live-prices.cache.invalid/";

function cors(request) {
  const origin = request.headers.get("Origin") || "";
  const h = { "Vary": "Origin" };
  if (SITE_ORIGINS.includes(origin)) h["Access-Control-Allow-Origin"] = origin;
  return h;
}

function json(request, body, status, extra) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...cors(request), ...(extra || {}) },
  });
}

export function parseIds(url) {
  const raw = url.searchParams.get("ids");
  const ids = raw === null ? DEFAULT_IDS.slice() : raw.split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
  if (!ids.length || ids.length > MAX_IDS || !ids.every(i => ID_RX.test(i))) return null;
  return [...new Set(ids)].sort();
}

async function readCache(cache, key) {
  const hit = await cache.match(new Request(key));
  if (!hit) return null;
  try { return await hit.json(); } catch (e) { return null; }
}

async function writeCache(cache, key, body, ttl) {
  await cache.put(new Request(key), new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json", "Cache-Control": `max-age=${ttl}` },
  }));
}

// deps: { fetchFn, cache } are injected by the tests; in the Worker they are fetch and caches.default.
export async function routeLivePrices(request, env, now, deps = {}) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: { ...cors(request), "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Max-Age": "86400" } });
  }
  if (request.method !== "GET") return json(request, { ok: false, why: "GET only" }, 405, { "Allow": "GET, OPTIONS" });
  const ids = parseIds(new URL(request.url));
  if (!ids) return json(request, { ok: false, why: `ids: 1 to ${MAX_IDS} lower-case CoinGecko ids` }, 400);
  const fetchFn = deps.fetchFn || fetch;
  const cache = deps.cache || caches.default;
  const stamp = ids.join(",");
  const freshKey = `${KEY_BASE}fresh/${stamp}`, goodKey = `${KEY_BASE}good/${stamp}`;

  const fresh = await readCache(cache, freshKey);
  if (fresh) return json(request, { ...fresh, stale: false }, 200, { "Cache-Control": `public, max-age=${LIVE_TTL_S}`, "x-live-cache": "hit" });

  try {
    const hdr = { "accept": "application/json", "user-agent": "gocheckmycrypto-live-prices/1" };
    const [p, g] = await Promise.all([
      fetchFn(`${CG}/simple/price?ids=${ids.join(",")}&vs_currencies=usd&include_24hr_change=true`, { headers: hdr }),
      fetchFn(`${CG}/global`, { headers: hdr }),
    ]);
    if (!p.ok || !g.ok) throw new Error(`CoinGecko answered ${p.status} and ${g.status}`);
    const simple = await p.json(), glob = await g.json();
    if (!simple || typeof simple !== "object" || !glob || typeof glob.data !== "object") throw new Error("malformed answer");
    const body = { schema: "gocheckmycrypto.com/live-prices/1", as_of_utc: now.toISOString().replace(/\.\d{3}Z$/, "Z"),
                   cache_seconds: LIVE_TTL_S, source: "CoinGecko /simple/price and /global", simple, global: glob };
    await writeCache(cache, freshKey, body, LIVE_TTL_S);
    await writeCache(cache, goodKey, body, LAST_GOOD_TTL_S);
    return json(request, { ...body, stale: false }, 200, { "Cache-Control": `public, max-age=${LIVE_TTL_S}`, "x-live-cache": "miss" });
  } catch (e) {
    const good = await readCache(cache, goodKey);
    if (good) return json(request, { ...good, stale: true }, 200, { "Cache-Control": "no-store", "x-live-cache": "last-good" });
    return json(request, { ok: false, why: "CoinGecko did not answer and no earlier answer is held" }, 502, { "Cache-Control": "no-store" });
  }
}
