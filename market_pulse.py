#!/usr/bin/env python3
"""
market_pulse.py: the Market Pulse data desk. Free, keyless market context, explained honestly.

Fetches four independent, keyless sources at build time and writes site/data/pulse.json,
which site_build.py renders as the "Market Pulse" page:

  1. Fear & Greed Index        alternative.me          crowd sentiment gauge + 90d history
  2. Price history             CoinGecko (keyless)     365d daily closes for BTC/ETH/SOL ->
                               RSI-14, MACD(12,26,9), 50/200-day SMAs, 12-month-high
                               distance, 30d realized volatility. All stdlib arithmetic.
  3. Stablecoin supply         DefiLlama (keyless)     total USD-pegged float: crypto's
                               dry powder, current + 30d change + 1y trend
  4. Bitcoin network           mempool.space           recommended fees + difficulty change

FAIL-OPEN, PER SECTION: each source is fetched independently; a failed source is warned and
omitted while the others still publish. If every source fails, nothing is written and the
previously committed snapshot stands (the site renders whatever sections exist). This is
market DATA, not news: it never touches the editorial pipeline or the human gate, and the
page says so. Like the Whale Watch board, it refreshes at every Netlify build (see
netlify.toml and DEVIATIONS D8).

USAGE
  python3 market_pulse.py            # live fetch -> site/data/pulse.json (+ out/ copy)
"""

import json
import math
import os
import urllib.request
from datetime import datetime, timezone

import common

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DATA = os.path.join(HERE, "site", "data", "pulse.json")
UA = "CryptoCronkite-MarketPulse/1.0 (+https://gocheckmycrypto.com)"

ASSETS = [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL"), ("ripple", "XRP")]


def get_json(url, timeout=30, attempts=3):
    """Fetch JSON with polite backoff: keyless CoinGecko rate-limits bursts, so a 429 (or a
    transient 5xx) waits and retries instead of dropping the section."""
    import time
    import urllib.error
    delay = 20
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503):
                raise
            last = e
        except Exception as e:
            last = e
        if i < attempts - 1:
            time.sleep(delay)
            delay *= 2
    raise last


# ---- indicator math (standard definitions, stdlib only) -----------------------

def sma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def ema_series(values, n):
    if len(values) < n:
        return []
    k = 2 / (n + 1)
    out = [sum(values[:n]) / n]  # seed with SMA
    for v in values[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rolling_sma(values, n):
    """Full rolling SMA series; result[k] corresponds to values[k + n - 1]."""
    if len(values) < n:
        return []
    out = []
    s = sum(values[:n])
    out.append(s / n)
    for i in range(n, len(values)):
        s += values[i] - values[i - n]
        out.append(s / n)
    return out


def _date_label(ts_seconds):
    return datetime.fromtimestamp(int(ts_seconds), timezone.utc).strftime("%b %d")


def rsi14(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for a, b in zip(closes[:-1], closes[1:]):
        d = b - a
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains[:n]) / n
    avg_l = sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):  # Wilder smoothing
        avg_g = (avg_g * (n - 1) + g) / n
        avg_l = (avg_l * (n - 1) + l) / n
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - 100 / (1 + rs)


def macd(closes, fast=12, slow=26, signal_n=9):
    if len(closes) < slow + signal_n:
        return None
    ema_f = ema_series(closes, fast)
    ema_s = ema_series(closes, slow)
    line = [f - s for f, s in zip(ema_f[len(ema_f) - len(ema_s):], ema_s)]
    sig = ema_series(line, signal_n)
    if not sig:
        return None
    return {"macd": line[-1], "signal": sig[-1], "hist": line[-1] - sig[-1]}


def realized_vol_30d(closes):
    if len(closes) < 31:
        return None
    rets = [math.log(b / a) for a, b in zip(closes[-31:-1], closes[-30:]) if a > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(365) * 100


def downsample(values, n=48):
    if len(values) <= n:
        return [round(v, 6) for v in values]
    step = (len(values) - 1) / (n - 1)
    return [round(values[int(i * step)], 6) for i in range(n)]


# ---- sections (each independently fail-open) ----------------------------------

def section_fng():
    d = get_json("https://api.alternative.me/fng/?limit=90")["data"]
    newest = d[0]
    hist = [int(x["value"]) for x in reversed(d)]  # oldest -> newest
    return {"value": int(newest["value"]), "label": newest["value_classification"],
            "history": hist,
            "window": {"start": _date_label(d[-1]["timestamp"]),
                       "end": _date_label(newest["timestamp"])}}


def section_assets():
    import time
    out = []
    for i, (cid, sym) in enumerate(ASSETS):
        if i:
            time.sleep(7)  # keyless CoinGecko dislikes bursts; a build can afford politeness
        d = get_json(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
                     f"?vs_currency=usd&days=365&interval=daily")
        rows = [p for p in d.get("prices", []) if p and p[1]]
        closes = [p[1] for p in rows]
        if len(closes) < 210:
            raise ValueError(f"{sym}: only {len(closes)} daily closes from CoinGecko")
        last = closes[-1]
        hi = max(closes)
        m = macd(closes)
        s50, s200 = sma(closes, 50), sma(closes, 200)
        win = closes[-90:]
        # rolling SMA series sliced to the same 90-day window and downsampled in step with
        # the price spark, so the dashboard can overlay them on one chart
        sma50_win = rolling_sma(closes, 50)[-90:]
        sma200_win = rolling_sma(closes, 200)[-90:]
        out.append({
            "symbol": sym, "name": cid, "price": round(last, 2),
            "rsi14": round(rsi14(closes), 1),
            "macd_above_signal": bool(m and m["hist"] >= 0),
            "sma50": round(s50, 2), "sma200": round(s200, 2),
            "above_sma200": last >= s200,
            "golden_cross": s50 >= s200,
            "pct_from_high_12m": round((last / hi - 1) * 100, 1),
            "vol30_pct": round(realized_vol_30d(closes), 1),
            "spark": downsample(win, 64),
            "spark_sma50": downsample(sma50_win, 64),
            "spark_sma200": downsample(sma200_win, 64),
            "spark_high": round(max(win), 2), "spark_low": round(min(win), 2),
            "window": {"start": _date_label(rows[-90][0] / 1000),
                       "end": _date_label(rows[-1][0] / 1000)},
        })
    return out


def section_stables():
    d = get_json("https://stablecoins.llama.fi/stablecoincharts/all")
    pts = [(int(p["date"]), (p.get("totalCirculatingUSD") or {}).get("peggedUSD"))
           for p in d if (p.get("totalCirculatingUSD") or {}).get("peggedUSD")]
    pts.sort()
    year_pts = pts[-365:]
    year = [v for _, v in year_pts]
    cur = year[-1]
    prev30 = year[-31] if len(year) > 31 else year[0]
    return {"total_usd": round(cur), "change_30d_pct": round((cur / prev30 - 1) * 100, 2),
            "spark": downsample(year, 64),
            "spark_high": round(max(year)), "spark_low": round(min(year)),
            "window": {"start": _date_label(year_pts[0][0]),
                       "end": _date_label(year_pts[-1][0])}}


def section_movers(top_n=5, universe=100):
    """Top gainers and losers over 24h, drawn ONLY from the top-100 coins by market cap so
    micro-cap pump coins never make the board."""
    d = get_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
                 f"&order=market_cap_desc&per_page={universe}&page=1"
                 "&price_change_percentage=24h")
    rows = [c for c in d if c.get("price_change_percentage_24h") is not None]
    rows.sort(key=lambda c: c["price_change_percentage_24h"])

    def pack(c):
        return {"symbol": (c.get("symbol") or "").upper(), "name": c.get("name") or "",
                "price": c.get("current_price"), "chg_24h_pct": round(c["price_change_percentage_24h"], 2),
                "mcap_usd": c.get("market_cap"), "rank": c.get("market_cap_rank")}

    return {"universe": universe,
            "gainers": [pack(c) for c in reversed(rows[-top_n:])],
            "losers": [pack(c) for c in rows[:top_n]]}


def section_network():
    fees = get_json("https://mempool.space/api/v1/fees/recommended")
    diff = get_json("https://mempool.space/api/v1/difficulty-adjustment")
    return {"fastest_fee": fees.get("fastestFee"), "hour_fee": fees.get("hourFee"),
            "difficulty_change_pct": round(diff.get("difficultyChange", 0), 1),
            "retarget_blocks": diff.get("remainingBlocks")}


def main():
    pulse = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "note": ("Free public market data, computed with standard formulas at build time: "
                 "sentiment from alternative.me, prices from CoinGecko, stablecoin float from "
                 "DefiLlama, Bitcoin network data from mempool.space. Market data, not news, "
                 "not advice."),
    }
    sections = [("fng", section_fng), ("assets", section_assets),
                ("movers", section_movers), ("stables", section_stables),
                ("network", section_network)]
    got = 0
    for name, fn in sections:
        try:
            pulse[name] = fn()
            got += 1
        except Exception as e:
            common.gh("warning", f"market_pulse: section '{name}' failed ({e}) -> omitted")
    if got == 0:
        common.gh("warning", "market_pulse: every source failed -> nothing written "
                             "(the previous snapshot stands).")
        return 0
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    json.dump(pulse, open(SITE_DATA, "w", encoding="utf-8"), indent=2)
    common.write_out("market_pulse.json", pulse)
    parts = [n for n, _ in sections if n in pulse]
    print(f"market_pulse: {got}/5 sections -> {os.path.relpath(SITE_DATA)} ({', '.join(parts)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
