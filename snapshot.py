#!/usr/bin/env python3
"""snapshot.py: the data contract (Jack, 5 October 2026). ONE object, every surface.

The build writes one snapshot and every surface reads it: the ticker's server-side fill,
the Board, the coin pages, the Top 100 and the Brief's lead line. Before this, the Board
read a coin's price from CoinGecko's `/coins/{id}/market_chart` and the coin page read it
from `/coins/markets`, so one stamp sat over $84,794.54 on one page and $84,796.00 on the
next. Now ONE endpoint feeds each field, and the object names it beside the field.

    {"stamp_utc": "...Z", "stamp_et": "7:26 PM ET on Oct 3",
     "board_coins": ["BTC", ...],
     "fields": {"coins": {"source": "CoinGecko /coins/markets", "read_utc": "...",
                          "value": {"BTC": {"price": ..., "chg_24h_pct": ...}, ...}},
                ...}}

The stamp is the OLDEST read among the fields, so no figure on a page is older than the
moment the page claims for it.

`views()` is how the existing renderers read it: it returns copies of pulse.json and
flows.json in which every figure the contract names has been REPLACED by the snapshot's
value, and the stamp by the snapshot's stamp. A renderer handed a view cannot print a
second endpoint's number for a contract figure, because the second endpoint's number is
no longer in what it was handed. Series (sparklines, daily closes, ETF rows by day) are
charts, not figures, and stay as the build read them.
"""
import copy
import datetime as _dt
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "data", "snapshot.json")

# The coins the Board and the ticker name, in market_pulse.ASSETS order.
BOARD_COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA"]

# One endpoint per field, named. Changing a source is changing this table.
SOURCES = {
    "coins": "CoinGecko /coins/markets",
    "dominance": "CoinGecko /global",
    "total_cap": "CoinGecko /global",
    "etf_flows": "Farside Investors (farside.co.uk)",
    "whale_net": "Whale Alert public archive",
    "funding": "OKX /api/v5/public/funding-rate",
    "open_interest": "OKX /api/v5/public/open-interest",
    "stablecoin_float": "DefiLlama stablecoincharts/all",
    "fear_greed": "alternative.me /fng",
    "network_fee": "mempool.space /api/v1/fees/recommended",
    "week": "CoinGecko /coins/markets sparkline=true (sparkline_in_7d, hourly, timed "
            "back from last_updated)",
    "movers": "computed from CoinGecko /coins/markets price_change_percentage_24h",
}
STANDOUT_PCT = 5.0          # a top-100 coin moving MORE than this either way is a standout
# The daily closes the 200-day, RSI, drawdown and lines are computed from.
SERIES_SOURCE = "CoinGecko /coins/{id}/market_chart, stored daily closes in data/history/"
# The pulse.json section each field is read from, for its read time.
_SECTION = {"coins": "movers", "week": "movers", "movers": "movers", "dominance": "market", "total_cap": "market",
            "etf_flows": "etf_flows", "funding": "leverage", "open_interest": "leverage",
            "stablecoin_float": "stables", "fear_greed": "fng", "network_fee": "network"}

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                  # pragma: no cover
    _ET = _dt.timezone(_dt.timedelta(hours=-5))


def _utc(ts):
    try:
        return _dt.datetime.strptime(str(ts or "").strip(), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def stamp_et(ts):
    """'2026-10-03T23:26:00Z' to '7:26 PM ET on Oct 3'. The zone is never left off."""
    dt = _utc(ts)
    if not dt:
        return ""
    et = dt.astimezone(_ET)
    return f"{et.strftime('%-I:%M %p')} ET on {et.strftime('%b')} {et.day}"


def _read(pulse, field):
    sec = _SECTION.get(field)
    return (((pulse or {}).get("sections_utc") or {}).get(sec)
            or (pulse or {}).get("generated_utc") or "")


def build(pulse, flows):
    """The snapshot, from what the two data desks wrote. Pure: reads its arguments only."""
    pulse, flows = pulse or {}, flows or {}
    fields = {}

    def put(name, value, read_utc=None, source=None):
        if value is None or value == {} or value == []:
            return
        fields[name] = {"source": source or SOURCES[name],
                        "read_utc": read_utc or _read(pulse, name), "value": value}

    rows = ((pulse.get("movers") or {}).get("top100")) or []
    coins = {}
    for r in rows:
        sym = r.get("symbol")
        if sym and isinstance(r.get("price"), (int, float)) and sym not in coins:
            coins[sym] = {"price": r["price"], "chg_24h_pct": r.get("chg_24h_pct"),
                          "id": r.get("gecko_id"), "name": r.get("name"),
                          "mcap_usd": r.get("mcap_usd"), "rank": r.get("rank")}
            if r.get("stablecoin"):
                coins[sym]["stablecoin"] = True
    put("coins", coins)
    # THE WEEK (6 October 2026): seven daily closes and the week's low and high per coin,
    # from the same /coins/markets read with its sparkline field; no second request.
    week = {}
    for r in rows:
        sym = r.get("symbol")
        if sym in coins and r.get("closes7d") and sym not in week:
            week[sym] = {"closes": r["closes7d"], "low": r.get("low7d"),
                         "high": r.get("high7d")}
    put("week", week)
    put("movers", movers(coins))

    mkt = pulse.get("market") or {}
    if isinstance(mkt.get("btc_dominance_pct"), (int, float)):
        put("dominance", {"btc_pct": mkt["btc_dominance_pct"]})
    if isinstance(mkt.get("total_mcap_usd"), (int, float)):
        put("total_cap", {"usd": mkt["total_mcap_usd"],
                          "chg_24h_pct": mkt.get("mcap_change_24h_pct")})

    etf = {}
    for k in ("btc", "eth"):
        e = (pulse.get("etf_flows") or {}).get(k) or {}
        if isinstance(e.get("latest_net_usd_m"), (int, float)):
            etf[k] = {"latest_net_usd_m": e["latest_net_usd_m"],
                      "latest_date": e.get("latest_date"),
                      "cumulative_usd_m": e.get("cumulative_usd_m")}
    put("etf_flows", etf)

    vol = flows.get("volatile") or {}
    if isinstance(vol.get("net_usd"), (int, float)):
        put("whale_net", {"net_usd": vol["net_usd"], "direction": vol.get("direction"),
                          "inflow_usd": vol.get("inflow_usd"),
                          "outflow_usd": vol.get("outflow_usd"),
                          "window_hours": flows.get("window_hours", 24),
                          "window_widened_from": flows.get("window_widened_from"),
                          "scope": "all coins"},
            read_utc=flows.get("generated_utc") or "",
            source=flows.get("source") or SOURCES["whale_net"])

    fund, oi = {}, {}
    venue = None
    for a in ((pulse.get("leverage") or {}).get("assets") or []):
        s = a.get("symbol")
        venue = venue or a.get("venue")
        if s and a.get("funding_8h_pct") is not None:
            fund[s] = {"funding_8h_pct": a["funding_8h_pct"],
                       "funding_annual_pct": a.get("funding_annual_pct"),
                       "venue": a.get("venue")}
        if s and isinstance(a.get("open_interest_usd"), (int, float)):
            oi[s] = {"usd": a["open_interest_usd"], "venue": a.get("venue")}
    _ven = "" if (venue or "OKX") == "OKX" else f" ({venue})"
    put("funding", fund, source=SOURCES["funding"] + _ven)
    put("open_interest", oi, source=SOURCES["open_interest"] + _ven)

    st = pulse.get("stables") or {}
    if isinstance(st.get("total_usd"), (int, float)):
        put("stablecoin_float", {"total_usd": st["total_usd"],
                                 "change_30d_pct": st.get("change_30d_pct")})
    fg = pulse.get("fng") or {}
    if fg.get("value") is not None:
        put("fear_greed", {"value": fg["value"], "label": fg.get("label")})
    nw = pulse.get("network") or {}
    if nw.get("fastest_fee") is not None:
        put("network_fee", {"fastest_fee": nw.get("fastest_fee"),
                            "hour_fee": nw.get("hour_fee")})

    reads = [f["read_utc"] for f in fields.values() if _utc(f["read_utc"])]
    stamp = min(reads) if reads else ""
    snap = {"contract": "one snapshot, every surface (5 October 2026)",
            "stamp_utc": stamp, "stamp_et": stamp_et(stamp),
            "board_coins": [c for c in BOARD_COINS if c in coins],
            "fields": fields}
    # THE STORED SERIES (6 October 2026). Not a reading and not in `fields`, so it never
    # sets the stamp above: each coin's daily closes carry their own through date, which
    # the tiles computed from them print.
    hist = {}
    for a in (pulse.get("assets") or []):
        if a.get("symbol") and a.get("through"):
            hist[a["symbol"]] = {"through": a["through"], "source": a.get("history_source")}
            # the week and month the desk's text may print, from the stored closes
            for k in ("chg_7d_pct", "chg_30d_pct", "windows_through"):
                if a.get("series_" + k) is not None:
                    hist[a["symbol"]][k] = a["series_" + k]
    import stablecoins as _st
    _sl = _st.load()
    snap["stablecoins"] = {"source": _sl.get("source"), "read_utc": _sl.get("read_utc"),
                           "symbols": sorted(k for k, v in coins.items() if v.get("stablecoin"))}
    if hist:
        snap["series"] = {"source": SERIES_SOURCE, "through": min(
            v["through"] for v in hist.values()), "value": hist}
    return snap


def series_windows(closes):
    """THE SERIES' WEEK AND MONTH (7 October 2026). From a coin's stored daily closes,
    {date: close}: the change from the close seven days, and thirty days, before the
    through date to the through date's close. Returns {"series_chg_7d_pct",
    "series_chg_30d_pct", "series_windows_through"}, a window omitted when its start
    date is not in the series. Never from the downsampled spark (64 points over 90 days,
    so "seven points back" was about ten days) and never from /coins/markets' own
    percentage fields, which end at the read rather than at a close: on 6 October the
    Brief printed 1.3% and 8.3% from the spark while the series said 2.75% and 7.45%."""
    c = {d: v for d, v in (closes or {}).items() if isinstance(v, (int, float)) and v}
    if not c:
        return {}
    t = max(c)
    out = {"series_windows_through": t}
    for key, back in (("series_chg_7d_pct", 7), ("series_chg_30d_pct", 30)):
        d0 = (_dt.date.fromisoformat(t) - _dt.timedelta(days=back)).isoformat()
        if d0 in c:
            out[key] = round((c[t] / c[d0] - 1) * 100, 2)
    return out


def series_window(snap, sym, which):
    """The snapshot's own week ("7d") or month ("30d") change for a Board coin, or None."""
    v = ((((snap or {}).get("series") or {}).get("value") or {}).get(sym) or {})
    return v.get(f"chg_{which}_pct")


def movers(coins):
    """Moving today (6 October 2026). Among the top 20 by market cap, the three largest
    24-hour rises and the largest fall, each with its rank; among the top 100, every coin
    moving more than STANDOUT_PCT either way, or "none today". Stablecoins are never
    movers: they are in the top 20 and the top 100, and excluded from both lists."""
    ranked = sorted((dict(v, symbol=k) for k, v in (coins or {}).items()
                     if isinstance(v.get("rank"), int)), key=lambda c: c["rank"])
    if not ranked:
        return {}

    def row(c):
        return {"symbol": c["symbol"], "name": c.get("name"), "rank": c["rank"],
                "chg_24h_pct": c["chg_24h_pct"]}
    live = [c for c in ranked if not c.get("stablecoin")
            and isinstance(c.get("chg_24h_pct"), (int, float))]
    # CoinGecko's rank, 1 to 20, so a coin the screen dropped leaves its number unused
    # rather than pulling rank 21 into a "top 20" list.
    top20 = [c for c in live if c["rank"] <= 20]
    rises = sorted((c for c in top20 if c["chg_24h_pct"] > 0),
                   key=lambda c: -c["chg_24h_pct"])[:3]
    falls = sorted((c for c in top20 if c["chg_24h_pct"] < 0),
                   key=lambda c: c["chg_24h_pct"])[:1]
    stand = [row(c) for c in live if c["rank"] <= 100
             and abs(c["chg_24h_pct"]) > STANDOUT_PCT]
    return {"top20_rises": [row(c) for c in rises],
            "top20_fall": row(falls[0]) if falls else None,
            "standouts": stand,
            "standouts_line": "" if stand else "none today",
            "rule": f"top 20 by market cap: the three largest 24-hour rises and the largest "
                    f"fall; top 100: every coin moving more than {STANDOUT_PCT:g}% either "
                    f"way; stablecoins excluded"}


def value(snap, field):
    return (((snap or {}).get("fields") or {}).get(field) or {}).get("value")


def coin(snap, sym):
    return (value(snap, "coins") or {}).get(sym) or {}


def write(snap, path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Compact (6 October 2026): the home page requests this file at runtime in Sprint 2,
    # and its budget is 60 KB; the seven closes per coin put the indented form at 56 KB.
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, separators=(",", ":"))


def load(path=OUT):
    """The object the build wrote; when no build has run here, the same function over the
    same two files the build reads, so a reader never assembles figures its own way."""
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    d = os.path.join(HERE, "site", "data")

    def _j(n):
        p = os.path.join(d, n)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return build(_j("pulse.json"), _j("flows.json"))


def views(snap, pulse, flows):
    """(pulse_view, flows_view): copies whose contract figures are the snapshot's.

    Every renderer is handed these and never the raw files. A field the snapshot does not
    carry is REMOVED from the view rather than left at the raw value, so a missing figure
    is omitted on the page (rule 5) instead of printed from another endpoint.
    """
    p = copy.deepcopy(pulse) if pulse else None
    f = copy.deepcopy(flows) if flows else None
    if p is not None:
        coins = value(snap, "coins") or {}
        for a in p.get("assets") or []:
            c = coins.get(a.get("symbol"))
            a["price"] = c.get("price") if c else None
            a["chg_24h_pct"] = c.get("chg_24h_pct") if c else None
        mv = p.get("movers") or {}
        for key in ("top100", "gainers", "losers"):
            for r in mv.get(key) or []:
                c = coins.get(r.get("symbol"))
                if c:
                    r["price"], r["chg_24h_pct"] = c["price"], c.get("chg_24h_pct")
        mkt = p.setdefault("market", {})
        dom, cap = value(snap, "dominance"), value(snap, "total_cap")
        mkt["btc_dominance_pct"] = (dom or {}).get("btc_pct")
        mkt["total_mcap_usd"] = (cap or {}).get("usd")
        mkt["mcap_change_24h_pct"] = (cap or {}).get("chg_24h_pct")
        etf = value(snap, "etf_flows") or {}
        for k, e in (p.get("etf_flows") or {}).items():
            if isinstance(e, dict):
                s = etf.get(k) or {}
                e["latest_net_usd_m"] = s.get("latest_net_usd_m")
                e["latest_date"] = s.get("latest_date")
        fund, oi = value(snap, "funding") or {}, value(snap, "open_interest") or {}
        for a in ((p.get("leverage") or {}).get("assets") or []):
            s = a.get("symbol")
            a["funding_8h_pct"] = (fund.get(s) or {}).get("funding_8h_pct")
            a["funding_annual_pct"] = (fund.get(s) or {}).get("funding_annual_pct")
            a["open_interest_usd"] = (oi.get(s) or {}).get("usd")
        st, fg, nw = value(snap, "stablecoin_float"), value(snap, "fear_greed"), \
            value(snap, "network_fee")
        if p.get("stables") is not None:
            p["stables"]["total_usd"] = (st or {}).get("total_usd")
            p["stables"]["change_30d_pct"] = (st or {}).get("change_30d_pct")
        if p.get("fng") is not None:
            p["fng"]["value"] = (fg or {}).get("value")
            p["fng"]["label"] = (fg or {}).get("label")
        if p.get("network") is not None:
            p["network"]["fastest_fee"] = (nw or {}).get("fastest_fee")
            p["network"]["hour_fee"] = (nw or {}).get("hour_fee")
        # The Board's Bitcoin delta is now measured on the markets price, so it is carried
        # (and suppressed) exactly when that section is.
        cf = [x for x in (p.get("carried_forward") or []) if x != "assets"]
        if "movers" in cf:
            cf.append("assets")
        p["carried_forward"] = cf
        p["generated_utc"] = snap.get("stamp_utc") or p.get("generated_utc")
        p["snapshot_stamp_et"] = snap.get("stamp_et")
    if f is not None:
        w = value(snap, "whale_net")
        vol = f.setdefault("volatile", {})
        for k in ("net_usd", "direction", "inflow_usd", "outflow_usd"):
            vol[k] = (w or {}).get(k)
        if w:
            f["window_hours"] = w.get("window_hours", 24)
    return p, f


# ---- the twins check: a story's number against the Board's, both from this object ----

_BTC_PRICE = re.compile(
    r"\b(?:bitcoin|btc)\b[^.$]{0,60}?\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,6}(?:\.\d+)?)",
    re.I)


def twins(text, snap, tolerance_pct=3.0):
    """Every Bitcoin price a story states that sits further than `tolerance_pct` from the
    price the Board prints, both read from `snap`. Returns a list of (stated, board, pct).

    It reads the Board's number from the object it is handed and from nothing else, which
    is what lets it hold a story rather than advise. Its ACTION stays advisory until the
    seven-Edition record is in (the September order); its READING is the snapshot's."""
    board = coin(snap, "BTC").get("price")
    out = []
    if not isinstance(board, (int, float)) or not board:
        return out
    for m in _BTC_PRICE.finditer(text or ""):
        try:
            stated = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if stated < 1000:
            continue
        pct = (stated - board) / board * 100.0
        if abs(pct) > tolerance_pct:
            out.append((stated, board, round(pct, 1)))
    return out


if __name__ == "__main__":
    s = load()
    print(json.dumps({k: v for k, v in s.items() if k != "fields"}, indent=1))
    for k, v in s["fields"].items():
        print(f"  {k:17s} {v['read_utc']}  {v['source']}")
