"""FROZEN REFERENCE, not pipeline code. market_pulse.section_assets as it stood at
4d8a23d (6 October 2026), before the stored series, copied verbatim except that its
fetcher and coin list are arguments. The stored-series canary computes the Board's
indicators both ways on the same closes and requires them equal to the cent."""
from market_pulse import (macd, sma, rolling_sma, rsi14, realized_vol_30d, downsample,
                          _date_label, _date_iso)


def section_assets(get_json, ASSETS):
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
            # keep cents on cheap coins: $1.10 must not flatten to $1 (4 decimals below $100)
            "symbol": sym, "name": cid, "price": round(last, 2 if last >= 100 else 4),
            "chg_24h_pct": round((last / closes[-2] - 1) * 100, 2),
            "rsi14": round(rsi14(closes), 1),
            "macd_above_signal": bool(m and m["hist"] >= 0),
            "sma50": round(s50, 2), "sma200": round(s200, 2),
            "above_sma200": last >= s200,
            "golden_cross": s50 >= s200,
            # Ship the percentage AND the price it is measured against. Without the
            # second field a writer wanting "X% below its 12-month high of $Y" has only
            # spark_high to reach for, which is the 90-DAY high used for chart scaling, and
            # pairing the two produces a sentence where the percentage and the dollar
            # figure describe different windows. The edition shipped exactly that on
            # 2026-07-28 ("49% below its 12-month high of $82,018.37", when 49% is measured
            # against roughly $124,700) and the trace check caught it. Same source, one
            # field apart, so they cannot disagree.
            "pct_from_high_12m": round((last / hi - 1) * 100, 1),
            "high_12m_usd": round(hi, 2 if hi >= 100 else 4),
            "vol30_pct": round(realized_vol_30d(closes), 1),
            "spark": downsample(win, 64),
            "spark_sma50": downsample(sma50_win, 64),
            "spark_sma200": downsample(sma200_win, 64),
            "spark_high": round(max(win), 2), "spark_low": round(min(win), 2),
            "window": {"start": _date_label(rows[-90][0] / 1000),
                       "end": _date_label(rows[-1][0] / 1000),
                       "start_iso": _date_iso(rows[-90][0] / 1000),
                       "end_iso": _date_iso(rows[-1][0] / 1000)},
        })
    return out
