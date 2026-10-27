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
    text = f"{et.strftime('%-I:%M %p')} ET on {et.strftime('%b')} {et.day}"
    _STAMP_TS[text] = str(ts).strip()
    return text


# THE STALE STATE (Sprint 9.1, AUDIT.md 3.4 item 2). A stamp prints as text; the text that went
# to a surface is remembered with the instant it came from, so any surface that prints a
# stamp (a tile, the tape, a stamp line) can also carry the instant, and the browser can
# measure the reading's age at the moment it is read.
_STAMP_TS = {}
STALE_HOURS = 3        # a reading older than this, when read, prints its age and dims


def ts_for_stamp(text):
    """The instant a stamp text was made from, or ''."""
    return _STAMP_TS.get(str(text or "").strip(), "")


def asof_attr(ts, hours=None):
    """' data-asof="..."' for a UTC instant, or '' when it is not one."""
    if not _utc(ts):
        return ""
    h = f' data-asof-hours="{hours}"' if hours else ""
    return f' data-asof="{str(ts).strip()}"{h}'


def age_hours(ts, now=None):
    """Hours between a UTC instant and `now`, or None when the instant is unreadable."""
    dt = _utc(ts)
    if not dt:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return (now - dt).total_seconds() / 3600.0


def is_stale(ts, now=None, hours=None):
    """THE ONE STALE RULE (Sprint 9.1; the app-ready feeds of Sprint 9.7 read it too). A reading is stale
    when it is MORE than `hours` old (STALE_HOURS unless a surface names its own) at `now`. asof.js applies
    the same comparison in the browser, from data-asof. An instant that cannot be read returns None: the
    page prints no age for it, and a feed, which must say something, calls it stale."""
    h = age_hours(ts, now)
    if h is None:
        return None
    return h > (STALE_HOURS if hours is None else hours)


def age_phrase(ts, now=None):
    """'9 hours ago', '2 days ago', or '' when the reading is within STALE_HOURS (or the
    instant is unreadable). `now` is an aware datetime; default the wall clock."""
    if not is_stale(ts, now):
        return ""
    h = age_hours(ts, now)
    return f"{int(h)} hours ago" if h < 48 else f"{int(h // 24)} days ago"


def _read(pulse, field):
    sec = _SECTION.get(field)
    return (((pulse or {}).get("sections_utc") or {}).get(sec)
            or (pulse or {}).get("generated_utc") or "")


# THE WHOLE-MARKET CHANGE IS CHECKED BEFORE IT PRINTS (Sprint 9.1, AUDIT.md 1.3 item 1).
# CoinGecko /global's 24-hour market-cap change was printed as it came. On 16 October it read
# -0.62% while Bitcoin was +1.48% (59% of the market) and Ether +4.13%; on 15 October -2.13%
# against Bitcoin +0.80% and Ether +0.96%. The desk can compute the same quantity from the
# Top 100 it already holds (each coin's cap and its own 24-hour change), so the reported
# figure is read against that, and against Bitcoin and Ether, and is withheld when they
# disagree. Withheld means the number is None and the state says "unchecked": never a
# fake zero, never a figure printed as fact that the desk's own numbers contradict.
MARKET_TOLERANCE_PTS = 1.0     # how far the reported figure may sit from the Top 100's
MARKET_SIGN_FLOOR = 0.5        # below this a move is too small to have a side
MARKET_MIN_COINS = 50          # fewer Top 100 rows than this and the desk's own figure is not computed


def top100_change(coins):
    """The Top 100's own 24-hour change, from each coin's cap and its change: the cap a day
    ago is cap / (1 + change), and the group's change is today's total over that total.
    None when too few rows carry both figures to call it the Top 100."""
    now = before = 0.0
    n = 0
    for c in (coins or {}).values():
        cap, chg = c.get("mcap_usd"), c.get("chg_24h_pct")
        if (isinstance(cap, (int, float)) and cap > 0 and isinstance(chg, (int, float))
                and chg > -100):
            now += cap
            before += cap / (1 + chg / 100.0)
            n += 1
    if n < MARKET_MIN_COINS or before <= 0:
        return None
    return round((now / before - 1) * 100.0, 2)


def check_market_change(reported, coins):
    """(state, reason, top100_pct). state is "checked" when the reported figure agrees with
    the Top 100's own and does not contradict Bitcoin and Ether, "unchecked" otherwise."""
    if not isinstance(reported, (int, float)) or isinstance(reported, bool):
        return "unchecked", "the source sent no 24-hour market change", top100_change(coins)
    own = top100_change(coins)
    btc = ((coins or {}).get("BTC") or {}).get("chg_24h_pct")
    eth = ((coins or {}).get("ETH") or {}).get("chg_24h_pct")
    side = lambda v: 0 if abs(v) < MARKET_SIGN_FLOOR else (1 if v > 0 else -1)
    if (isinstance(btc, (int, float)) and isinstance(eth, (int, float))
            and side(btc) and side(btc) == side(eth) and side(reported) == -side(btc)):
        return ("unchecked", f"{reported:+.2f}% contradicts Bitcoin ({btc:+.2f}%) and Ether "
                             f"({eth:+.2f}%), which moved the other way", own)
    if own is not None and abs(reported - own) > MARKET_TOLERANCE_PTS:
        return ("unchecked", f"{reported:+.2f}% is {abs(reported - own):.1f} points from the "
                             f"Top 100's own {own:+.2f}%", own)
    if own is None and not (isinstance(btc, (int, float)) and isinstance(eth, (int, float))):
        return "unchecked", "no Top 100, Bitcoin or Ether figures to check it against", own
    return "checked", "", own


def total_cap_value(usd, reported, coins):
    """The snapshot's total_cap value: the cap, the change only if it passed the check, the
    state, and what was checked, so a surface can say why a number is missing."""
    state, why, own = check_market_change(reported, coins)
    v = {"usd": usd, "chg_24h_pct": round(float(reported), 2) if state == "checked" else None,
         "chg_state": state}
    if own is not None:
        v["top100_chg_24h_pct"] = own
    if state != "checked":
        v["chg_withheld"] = why
        if isinstance(reported, (int, float)) and not isinstance(reported, bool):
            v["chg_reported_pct"] = round(float(reported), 2)
    return v


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
            # THE 24-HOUR HIGH AND LOW (13 October 2026): the same /coins/markets row as the
            # price, so every surface that prints them prints this pair and no other
            for k in ("high_24h", "low_24h"):
                if isinstance(r.get(k), (int, float)):
                    coins[sym][k] = r[k]
            if r.get("stablecoin"):
                coins[sym]["stablecoin"] = True
            # THE ET DAY'S MOVE (Sprint 9.1): the price at the last midnight Eastern and the
            # change since it, from the same read as the price
            if isinstance(r.get("open_et"), (int, float)) and r["open_et"] > 0 and r.get("open_et_day"):
                coins[sym]["open_et"] = r["open_et"]
                coins[sym]["open_et_day"] = r["open_et_day"]
                coins[sym]["chg_et_day_pct"] = round((r["price"] / r["open_et"] - 1) * 100.0, 2)
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
        put("total_cap", total_cap_value(mkt["total_mcap_usd"], mkt.get("mcap_change_24h_pct"),
                                         coins))

    etf = {}
    for k in ("btc", "eth"):
        e = (pulse.get("etf_flows") or {}).get(k) or {}
        if isinstance(e.get("latest_net_usd_m"), (int, float)):
            etf[k] = {"latest_net_usd_m": e["latest_net_usd_m"],
                      "latest_date": e.get("latest_date"),
                      "cumulative_usd_m": e.get("cumulative_usd_m")}
    put("etf_flows", etf)

    vol = flows.get("volatile") or {}
    # an absent volatile reading (no row, no inflow, no outflow) is never a zero
    # (8 October 2026: /data/snapshot.json carried net 0 "off exchanges" from one)
    if isinstance(vol.get("net_usd"), (int, float)) and (
            flows.get("by_asset") or vol.get("inflow_usd") or vol.get("outflow_usd")):
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


def week_pair(snap, sym):
    """(low, high) of the coin's seven stored daily closes, or None: THE 7D PAIR. The tape's
    HIGH and LOW and the coin page's "7D high" and "7D low" are this pair and nothing else
    (13 October 2026: the coin page had printed a second pair from the hourly sparkline).
    They are CLOSES and are worded so (Sprint 9.1): a day's close can sit above today's low, and
    a "7D low" that is not the lowest price read as false beside the 24-hour range."""
    wk = (value(snap, "week") or {}).get(sym) or {}
    cl = wk.get("closes")
    vals = list(cl.values()) if isinstance(cl, dict) else list(cl or [])
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    return (min(vals), max(vals)) if len(vals) >= 2 else None


def day_pair(snap, sym):
    """(low, high) of the coin's 24 hours from the snapshot's own field, or None."""
    c = coin(snap, sym)
    lo, hi = c.get("low_24h"), c.get("high_24h")
    return (lo, hi) if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) else None


def series_window(snap, sym, which):
    """The snapshot's own week ("7d") or month ("30d") change for a Board coin, or None."""
    v = ((((snap or {}).get("series") or {}).get("value") or {}).get(sym) or {})
    return v.get(f"chg_{which}_pct")


# THE MOVERS LIST RULES (Sprint 9.1, AUDIT.md 1.2). A list headed "top 5 losers" listed #107
# Starknet (outside the top 100) and PayPal USD at 0.0% (a stablecoin) on a morning when only
# three top-100 coins had fallen more than 1%. So: no stablecoin, rank 100 or better, a move of
# at least MOVER_FLOOR_PCT in the list's own direction, and no padding to fill five.
MOVER_FLOOR_PCT = 1.0
MOVER_RANK_MAX = 100
_PEGGED_NAME = re.compile(r"usd|dollar|stable|tether|\bdai\b|eur", re.I)


def is_stablecoin(row):
    """True for a coin flagged a stablecoin, or one priced within 3% of a dollar whose name
    says it is dollars (a stablecoin the flag file has not caught yet is still not a mover)."""
    if row.get("stablecoin"):
        return True
    px = row.get("price")
    return (isinstance(px, (int, float)) and 0.97 <= px <= 1.03
            and bool(_PEGGED_NAME.search(f"{row.get('name') or ''} {row.get('symbol') or ''}")))


def mover_rows(rows, side, n=5, floor=MOVER_FLOOR_PCT):
    """The list for one side ("gainers" or "losers") from top-100 rows, at most n, fewer when
    fewer qualify, empty when none does."""
    sign = 1 if side == "gainers" else -1
    ok = [r for r in (rows or [])
          if isinstance(r.get("chg_24h_pct"), (int, float))
          and isinstance(r.get("rank"), int) and r["rank"] <= MOVER_RANK_MAX
          and not is_stablecoin(r) and sign * r["chg_24h_pct"] >= floor]
    ok.sort(key=lambda r: -sign * r["chg_24h_pct"])
    return ok[:n]


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
        # the lists every renderer reads obey the movers rules, whatever the stored ones held
        if mv.get("top100"):
            mv["gainers"] = [dict(r) for r in mover_rows(mv["top100"], "gainers")]
            mv["losers"] = [dict(r) for r in mover_rows(mv["top100"], "losers")]
        mkt = p.setdefault("market", {})
        dom, cap = value(snap, "dominance"), value(snap, "total_cap")
        mkt["btc_dominance_pct"] = (dom or {}).get("btc_pct")
        mkt["total_mcap_usd"] = (cap or {}).get("usd")
        mkt["mcap_change_24h_pct"] = (cap or {}).get("chg_24h_pct")
        mkt["mcap_change_state"] = (cap or {}).get("chg_state")
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


def level(row, key):
    """SPRINT 9.9.2: a stored average or 90-day level at its asset's price precision, or None when it cannot be had.
    market_pulse stored these rounded to the cent until this sprint, so DOGE's 200-day average of $0.086658 read 0.09 and
    printed as $0.09000 beside a price of $0.07711 (and its distance from the price read -14.3% instead of -11.0%). An
    average's full value is the last point of the record's own averaged series (spark_sma50 and spark_sma200 end at the
    newest close, to six decimals), taken only when it rounds to the stored figure, which proves it is that figure. A
    sub-dollar level stored to the cent with no such series is None: it is left out, never padded."""
    v = (row or {}).get(key)
    if not isinstance(v, (int, float)):
        return None
    px = (row or {}).get("price")
    if not isinstance(px, (int, float)) or px >= 1 or round(v, 2) != v or v == 0:
        return v
    ser = (row or {}).get("spark_" + key) if key in ("sma50", "sma200") else None
    last = ser[-1] if ser else None
    if isinstance(last, (int, float)) and round(last, 2) == round(v, 2):
        return float(last)
    return None
