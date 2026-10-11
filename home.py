#!/usr/bin/env python3
"""
home.py: the home page, the five-minute read (Program 5, sections 2 and 3; Sprint 2).

Above the fold, phone first at 390, in the order of section 2 and nothing else:

    tape, narrative, since yesterday, why, moving the market,
    the money, the mood, moving today (top 20), today, mine

The desktop at 1440 is the same blocks in two columns (left: tape to the wire; right: the
money to mine), so the DOM order is the phone order and the desktop only places it.

Every block renders from what the build hands it: the snapshot (the data contract of
October 5), its views of pulse.json and flows.json, wire.json, narrative.json and
calendar.json. Nothing here reads an endpoint; the tape's live read and the mine block's
snapshot read are the page's only runtime requests. A block with no data says what it is
waiting for in one line and invents nothing. The markets read's percentage fields are
never printed (the twins gate's rule from Sprint 1b): the tape's week is drawn from its
closes, never from a 7-day percentage.

`above_fold(...)` is pure on its arguments, so the canary renders it from fixtures.
"""

import datetime as _dt
import json
import os

ABOVE_FOLD = ("tape", "narrative", "since", "why", "wire", "money", "mood", "movers",
              "today", "mine")
LEFT = ABOVE_FOLD[:5]
TAPE_ALTS = (("ETH", "Ether", "ethereum"), ("SOL", "Solana", "solana"),
             ("XRP", "XRP", "ripple"))
# The Edition's cron, 23:08 UTC (crypto-news-brief.yml), said in Eastern time on the day.
EDITION_UTC = (23, 8)
EMPTY_MINE = "Pins come from any coin page."
NO_CAL = "nothing scheduled"

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                  # pragma: no cover
    _ET = _dt.timezone(_dt.timedelta(hours=-4))


def _e(s):
    """The site's own escape (site_build.esc): &, <, > and the double quote."""
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


def _utc(ts):
    try:
        return _dt.datetime.strptime(str(ts or "").strip(),
                                     "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _stamp(ts):
    import snapshot
    return snapshot.stamp_et(ts)


def _now():
    return _dt.datetime.now(_dt.timezone.utc)


def edition_time_et(now=None):
    """'7:08 PM ET', the Edition's scheduled time on the day of `now`, in Eastern."""
    now = now or _now()
    t = now.replace(hour=EDITION_UTC[0], minute=EDITION_UTC[1], second=0, microsecond=0)
    return t.astimezone(_ET).strftime("%-I:%M %p ET")


def _pctx(v, dp=2):
    return f"{v:+.{dp}f}%"


def _dir(v):
    if not isinstance(v, (int, float)) or v == 0:
        return ""
    return "up" if v > 0 else "down"


def _tn(key):
    """A destination's task name, from the one table in site_build (Sprint 6.3)."""
    import site_build as sb
    return sb.task_name(key)


def _block(name, inner, label=None, cls=""):
    lab = f'<h2 class="h-h">{_e(label)}</h2>' if label else ""
    extra = f" {cls}" if cls else ""
    return f'<section class="h-b h-{name}{extra}" data-block="{name}">{lab}{inner}</section>'


# ---- the tape ------------------------------------------------------------------------------

def spark_points(closes, w=300, h=56, pad=3):
    """The seven-day line to scale: x evenly by close, y from the week's own low to high.
    Straight segments between published points; nothing interpolated."""
    if isinstance(closes, dict):                  # {UTC date: close}, the snapshot's shape
        closes = [closes[k] for k in sorted(closes)]
    vals = [float(c) for c in closes or [] if isinstance(c, (int, float))]
    if len(vals) < 2:
        return []
    lo, hi = min(vals), max(vals)
    rg = (hi - lo) or 1.0
    step = (w - 2 * pad) / (len(vals) - 1)
    return [(round(pad + i * step, 1), round(pad + (h - 2 * pad) * (1 - (v - lo) / rg), 1))
            for i, v in enumerate(vals)]


# THE TAPE'S CHART (Program 6, Sprint 6.2): the week to scale in a box the full width of the
# tape, CHART_H px tall, the line's band inset by CHART_PAD so the low and high figures sit
# beside their marks inside the box. The SVG stretches to the box (non-scaling stroke); the
# marks and their figures are placed over it in percent of the box, so a dot stays round
# at every width and height.
CHART_W, CHART_H, CHART_PAD = 1000, 72, 16


def tape_chart(week, fmt):
    """The tape's week: line, soft fill, the low and high marked on the line with their
    figures, a dot on the last point. "" when fewer than two closes were published."""
    closes = (week or {}).get("closes")
    if isinstance(closes, dict):
        closes = [closes[k] for k in sorted(closes)]
    vals = [float(c) for c in closes or [] if isinstance(c, (int, float))]
    pts = spark_points(vals, CHART_W, CHART_H - 2 * CHART_PAD, 0)
    if not pts:
        return ""
    pts = [(x, round(y + CHART_PAD, 1)) for x, y in pts]
    poly = " ".join(f"{x},{y}" for x, y in pts)
    area = (f"M{pts[0][0]},{CHART_H} " + " ".join(f"L{x},{y}" for x, y in pts)
            + f" L{pts[-1][0]},{CHART_H} Z")
    lo_i, hi_i = vals.index(min(vals)), vals.index(max(vals))
    last = len(vals) - 1

    def mark(i, cls, label):
        x, y = pts[i]
        left = round(100 * x / CHART_W, 2)
        side = " h-k-r" if left > 70 else " h-k-l" if left < 30 else ""
        cls += " h-k-last" if i == last else ""
        fig = (f'<span class="h-kf{side}">{_e(label)} <b>{_e(fmt(vals[i]))}</b></span>'
               if label else "")
        top = round(100 * y / CHART_H, 2)
        return (f'<span class="h-k {cls}" style="left:{left}%;top:{top}%">'
                f'<i></i>{fig}</span>')
    # The line is the daily closes, so its marks are the week's lowest and highest CLOSE.
    # The snapshot's week low and high are hourly extremes and lie off this line; printed
    # beside it they would mark a point the line does not reach.
    marks = mark(hi_i, "h-k-hi", "high close") + mark(lo_i, "h-k-lo", "low close")
    if last not in (lo_i, hi_i):
        marks += mark(last, "", "")
    return (f'<div class="h-chart" style="height:{CHART_H}px">'
            f'<svg class="h-spark" viewBox="0 0 {CHART_W} {CHART_H}" '
            f'preserveAspectRatio="none" role="img" aria-label="Bitcoin, {len(pts)} daily '
            f'closes, low {_e(fmt(min(vals)))}, high {_e(fmt(max(vals)))}">'
            f'<path class="h-area" d="{area}"/>'
            f'<polyline pathLength="1" points="{poly}"/></svg>{marks}</div>')


def tape(snap):
    import site_build as sb
    import snapshot
    btc = snapshot.coin(snap, "BTC")
    if not isinstance(btc.get("price"), (int, float)):
        return _block("tape", '<p class="h-wait">The tape is waiting for the snapshot\'s '
                              'Bitcoin price (CoinGecko /coins/markets).</p>')
    chg = btc.get("chg_24h_pct")
    chg_html = (f'<span class="h-chg {_dir(chg)}" data-tape-chg="bitcoin">{_pctx(chg)}</span>'
                if isinstance(chg, (int, float)) else "")
    week = (snapshot.value(snap, "week") or {}).get("BTC") or {}
    chart = tape_chart(week, sb._price_fmt)
    alts = []
    for sym, name, gid in TAPE_ALTS:
        c = snapshot.coin(snap, sym)
        if not isinstance(c.get("price"), (int, float)):
            continue
        ch = c.get("chg_24h_pct")
        alts.append(f'<li><span class="h-as">{_e(name)}</span>'
                    f'<span class="h-ap" data-tape="{gid}">{_e(sb._price_fmt(c["price"]))}</span>'
                    + (f'<span class="h-ac {_dir(ch)}" data-tape-chg="{gid}">{_pctx(ch)}</span>'
                       if isinstance(ch, (int, float)) else "") + '</li>')
    cap = snapshot.value(snap, "total_cap") or {}
    if isinstance(cap.get("usd"), (int, float)):
        cc = cap.get("chg_24h_pct")
        alts.append(f'<li class="h-cap"><span class="h-as">Total cap</span>'
                    f'<span class="h-ap">{_e(sb.fmt_usd(cap["usd"]))}</span>'
                    + (f'<span class="h-ac {_dir(cc)}">{_pctx(cc)}</span>'
                       if isinstance(cc, (int, float)) else "") + '</li>')
    read = ((snap.get("fields") or {}).get("coins") or {}).get("read_utc")
    asof = _stamp(read) or snap.get("stamp_et") or ""
    inner = (f'<div class="h-tape-in"><div class="h-main">'
             f'<p class="h-name">Bitcoin <span class="h-w">24h</span></p>'
             f'<p class="h-big"><span class="h-px" data-tape="bitcoin">'
             f'{_e(sb._price_fmt(btc["price"]))}</span>{chg_html}</p>'
             f'</div>{chart}'
             f'<ul class="h-alts">{"".join(alts)}</ul></div>'
             f'<p class="h-live" id="tapeLive" data-built="{_e(asof)}">as of {_e(asof)}</p>'
             f'<p class="h-board">Everything below the tape is the Board, as of '
             f'{_e(snap.get("stamp_et") or asof)}.</p>')
    return _block("tape", inner)


# ---- the narrative band -------------------------------------------------------------------

def narrative_band(narr, snap):
    line = str((narr or {}).get("line") or "").strip()
    stamp = snap.get("stamp_et") or ""
    if not line:
        return _block("narrative", f'<p class="h-nsmall">The Board as of {_e(stamp)}.</p>',
                      cls="h-band")
    # the small line names the readings the sentence was written from and prints none of
    # their figures (Sprint 6.2): each prints once on the page, Bitcoin's day change on the
    # tape only. A record with no readings stored keeps no small line rather than print the
    # stored one, which carries the figures.
    small = ""
    if narr.get("readings"):
        try:
            import narrative as _n
            small = _n.band_names(narr["readings"])
        except Exception:
            small = ""
    when = narr.get("written_et") or ""
    tail = f" ({when})" if when and small else ""
    return _block("narrative", f'<p class="h-nline">{_e(line)}</p>'
                               + (f'<p class="h-nsmall">{_e(small)}{_e(tail)}.</p>'
                                  if small else ""), cls="h-band")


# ---- since yesterday ----------------------------------------------------------------------

def since(pulse, deltas):
    """Since yesterday (Sprint 6.2): Bitcoin against its 200-day average first, then
    Bitcoin's share of the whole market. No day change here: Bitcoin's prints on the tape
    only, the whole market's on the tape, and Fear & Greed's in the mood."""
    import site_build as sb
    rows = []
    btc = sb._btc(pulse) or {}
    px, sma = btc.get("price"), btc.get("sma200")
    if isinstance(px, (int, float)) and isinstance(sma, (int, float)) and sma:
        gap = (px / sma - 1) * 100
        thru = sb._series_stamp(btc, pulse, html=False)
        thru = f' <span class="h-thru">({_e(thru)})</span>' if thru else ""
        rows.append(f'<li>Bitcoin is <span class="h-d">{abs(gap):.1f}%</span> '
                    f'{"above" if gap >= 0 else "below"} its 200-day average of '
                    f'<span class="h-d">{_e(sb._price_fmt(sma))}</span>{thru}.</li>')
    mkt = (pulse or {}).get("market") or {}
    dom = mkt.get("btc_dominance_pct")
    if isinstance(dom, (int, float)):
        rows.append(f'<li>Bitcoin is <span class="h-d">{dom:.1f}%</span> of the whole '
                    f'market.</li>')
    if not rows:
        return _block("since", '<p class="h-wait">Waiting for the Board\'s readings.</p>',
                      "Where Bitcoin stands")
    return _block("since", f'<ul class="h-since">{"".join(rows)}</ul>', "Where Bitcoin stands")


# ---- the why and the wire -----------------------------------------------------------------

def _wire_items(wire):
    return [w for w in ((wire or {}).get("items") or []) if w.get("line")]


def why(wire, now=None):
    note = (wire or {}).get("checked") or {}
    items = {w.get("id"): w for w in _wire_items(wire)}
    if wire is None:
        return _block("why", f'<p class="h-wait">The day\'s checked note arrives with the '
                             f'Edition at {_e(edition_time_et(now))}.</p>', "The checked story")
    w = items.get(note.get("id")) if note else None
    if not note or not w:
        return _block("why", '<p class="h-wait">No wire item cleared the checks today, so '
                             'there is no checked note.</p>', "The checked story")
    src = note.get("source") or ((w.get("links") or [{}])[0]).get("url") or ""
    reads = (f'<p class="h-reads">Reads with {_e(w["board_reading"])}</p>'
             if w.get("board_reading") else "")
    link = (f' <a href="{_e(src)}" rel="noopener">The source</a>' if src else "")
    return _block("why", f'<p><span class="badge verified">{_e(note.get("badge"))}</span></p>'
                         f'<h3 class="h-why-h">{_e(w["line"])}</h3>'
                         f'<p class="h-why-p">{_e(note.get("says"))} '
                         f'{_e(note.get("unconfirmed"))}{link}</p>{reads}',
                  "The checked story")


def wire_top(wire, cadence, now=None):
    import wire as _w
    head = f'<p class="h-cad">{_e(cadence)}</p>' if cadence else ""
    if wire is None:
        return _block("wire", head + f'<p class="h-wait">The day\'s wire arrives with the '
                                     f'Edition at {_e(edition_time_et(now))}.</p>',
                      "Moving the market")
    items = _wire_items(wire)[:5]
    note = (wire or {}).get("checked") or {}
    rows = []
    for w in items:
        links = w.get("links") or []
        lead = links[0] if links else {}
        checked = bool(note) and note.get("id") == w.get("id")
        mark = (f'<span class="badge verified">{_e(note.get("badge"))}</span>' if checked
                else '<span class="h-wm">Wire</span>')
        n = int(w.get("source_count") or 0)
        bits = []
        if w.get("board_reading"):
            bits.append(f'Reads with {_e(w["board_reading"])}')
        bits.append(f'{n} source{"" if n == 1 else "s"}')
        if w.get("primary"):
            bits.append('<span class="h-prim">Primary source</span>')
        if lead.get("url"):
            bits.append(f'<a href="{_e(lead["url"])}" rel="noopener">'
                        f'{_e(lead.get("outlet") or "Source")}</a>')
        rows.append(f'<li class="h-wi">{mark}<span class="h-wl">{_e(w["line"])}</span>'
                    f'<span class="h-wmeta">{" &middot; ".join(bits)}</span></li>')
    what = (wire or {}).get("what_a_wire_line_is") or _w.WHAT_A_WIRE_LINE_IS
    body = (f'<ol class="h-wire">{"".join(rows)}</ol>' if rows else
            '<p class="h-wait">The wire has no items today.</p>')
    ranked = (wire or {}).get("ranked_et")
    st = f'<p class="h-st">Ranked {_e(ranked)}</p>' if ranked else ""
    return _block("wire", head + body + f'<p class="h-what">{_e(what)}</p>' + st,
                  "Moving the market")


# ---- the money and the mood ---------------------------------------------------------------

def _field(snap, name):
    """(value, source, stamp). ONE STAMP FOR THE BOARD (Jack, 7 October 2026): every tile
    carries the snapshot's stamp, the oldest reading among its fields, which is the stamp
    the tape's line under it gives the Board; a field's own read time never stands in for
    it, so the Board never shows Oct 5 in one place and Oct 6 in another."""
    f = ((snap or {}).get("fields") or {}).get(name) or {}
    if not f:
        return None, "", ""
    return f.get("value"), f.get("source") or "", (snap or {}).get("stamp_et") or ""


def _tile(fn, *a):
    """A tile builder's output, or "" when its reading is absent."""
    try:
        return fn(*a) or ""
    except KeyError:
        return ""


def t_etf(snap, pulse):
    import site_build as sb
    import tile
    etf, src, st = _field(snap, "etf_flows")
    b = (etf or {}).get("btc") or {}
    net = b.get("latest_net_usd_m")
    if not isinstance(net, (int, float)) or not st:
        return ""
    fig = (f"{'+' if net > 0 else '-' if net < 0 else ''}{sb.fmt_usd(abs(net) * 1e6)}"
           if net else "flat")
    rec = [r for r in ((((pulse or {}).get("etf_flows") or {}).get("btc") or {})
                       .get("recent") or []) if isinstance(r.get("net_usd_m"), (int, float))]
    word = "inflow" if net > 0 else "outflow" if net < 0 else "flat"
    if len(rec) >= 2:
        pm = rec[-2]["net_usd_m"]
        pw = "in" if pm > 0 else "out" if pm < 0 else "flat"
        since_t = (f"Net {word}; the session before was {sb.fmt_usd(abs(pm) * 1e6)} {pw}"
                   if pm else f"Net {word}; the session before was flat")
    else:
        since_t = f"Net {word}; no session before it on record"
    day = sb.us_date(b.get("latest_date")) or b.get("latest_date")
    return tile.render("etf-net", fig, direction=_dir(net),
                       window=f"one trading day, {day}", since=since_t,
                       source=src.split(" (")[0], stamp=st)


def t_float(snap, deltas):
    import site_build as sb
    import tile
    stv, src, st = _field(snap, "stablecoin_float")
    if not isinstance((stv or {}).get("total_usd"), (int, float)) or not st:
        return ""
    d = (deltas.get("stables") or {}).get("pct")
    since_t = (f"{'Up' if d > 0 else 'Down' if d < 0 else 'Level'} {abs(d):.2f}% since "
               f"yesterday" if isinstance(d, (int, float)) else "No close kept for yesterday")
    return tile.render("stablecoin-float", sb.fmt_usd(stv["total_usd"]),
                       window="all stablecoins, now",
                       since=since_t, source=src.split(" ")[0], stamp=st)


def t_whale(snap, flows):
    import site_build as sb
    import tile
    wv, src, st = _field(snap, "whale_net")
    if not isinstance((wv or {}).get("net_usd"), (int, float)) or not st \
            or not sb._flows_have_data(flows):
        return ""
    amt, words, cls = sb.flow_words(wv["net_usd"])
    # flows.json keeps weekly history, not a daily record, so there is no yesterday to
    # compare with, and the tile says so rather than pass a week off as a day.
    return tile.render("whale-net", amt, direction=cls,
                       window=f"{sb._win_phrase(wv.get('window_hours', 24))}, all coins",
                       since=f"Net {words}; no reading kept for yesterday",
                       source="Whale Alert", stamp=st)


def _funding_hist(pulse):
    for a in (((pulse or {}).get("leverage") or {}).get("assets") or []):
        if a.get("symbol") == "BTC":
            return [h for h in a.get("funding_history_pct") or []
                    if isinstance(h, (int, float))]
    return []


def _funding_since(word, pulse):
    hist = _funding_hist(pulse)
    if len(hist) >= 4:
        return f"{word.capitalize()}; {hist[-4]:+.4f}% a day earlier"
    return f"{word.capitalize()}; no settlement a day back on record"


def t_funding(snap, pulse):
    import narrative
    import tile
    fund, src, st = _field(snap, "funding")
    f = (fund or {}).get("BTC") or {}
    v = f.get("funding_8h_pct")
    if not isinstance(v, (int, float)) or not st:
        return ""
    return tile.render("funding", f"{v:+.4f}%", label="Funding, per 8 hours",
                       window="Bitcoin perpetual, current 8-hour period",
                       since=_funding_since(narrative.funding_band(v), pulse),
                       source=f.get("venue") or "OKX", stamp=st)


def t_leverage(snap, pulse):
    """The Board's Leverage tile (K-5): Bitcoin's funding rate, annualized."""
    import narrative
    import tile
    fund, src, st = _field(snap, "funding")
    f = (fund or {}).get("BTC") or {}
    ann, v = f.get("funding_annual_pct"), f.get("funding_8h_pct")
    if not isinstance(ann, (int, float)) or not isinstance(v, (int, float)) or not st:
        return ""
    return tile.render("funding", f"{ann:+.1f}%", label="Leverage, funding annualized",
                       window=f"Bitcoin perpetual, {v:+.4f}% per 8 hours times 1,095",
                       since=_funding_since(narrative.funding_band(v), pulse),
                       source=f.get("venue") or "OKX", stamp=st)


def t_oi(snap, deltas):
    import site_build as sb
    import tile
    oi, src, st = _field(snap, "open_interest")
    o = (oi or {}).get("BTC") or {}
    if not isinstance(o.get("usd"), (int, float)) or not st:
        return ""
    venue = o.get("venue") or "OKX"
    d = (deltas.get("leverage") or {}).get("pct")
    if isinstance(d, (int, float)):
        return tile.render(
            "open-interest", f"{d:+.2f}%", label="Open interest change",
            window=f"since yesterday's close, five coins on {venue}",
            since=f"Bitcoin {sb.fmt_usd(o['usd'])} open now",
            source=venue, stamp=st)
    return tile.render(
        "open-interest", sb.fmt_usd(o["usd"]), label="Open interest",
        window=f"Bitcoin perpetuals on {venue}, now",
        since="No close kept for yesterday, so no change", source=venue, stamp=st)


def t_fng(snap, deltas):
    import site_build as sb
    import tile
    fg, src, st = _field(snap, "fear_greed")
    if not isinstance((fg or {}).get("value"), (int, float)) or not st:
        return ""
    val = fg["value"]
    fd = deltas.get("fng") or {}
    word = sb._fng_band(val)
    since_t = (f"{word}; {fd['prev']:g} yesterday" if isinstance(fd.get("prev"), (int, float))
               else f"{word}; no figure kept for yesterday")
    return tile.render("fear-greed", f"{val:g}", window="today",
                       since=since_t, source="alternative.me", stamp=st)


def t_bitcoin(snap, pulse, deltas):
    """The Board's Bitcoin tile: the snapshot's price, its 24 hours, and the 200-day from
    the stored series with that series' through date (ruling 2b, 6 October)."""
    import site_build as sb
    import snapshot
    import tile
    c = snapshot.coin(snap, "BTC")
    st = (snap or {}).get("stamp_et") or ""         # one stamp for the Board (7 October)
    if not isinstance(c.get("price"), (int, float)) or not st:
        return ""
    btc = sb._btc(pulse) or {}
    d = (deltas.get("bitcoin") or {}).get("pct")
    since_t = (f"{'Up' if d > 0 else 'Down' if d < 0 else 'Level'} {abs(d):.2f}% since "
               f"yesterday's close" if isinstance(d, (int, float))
               else "No close kept for yesterday")
    ch = c.get("chg_24h_pct")
    win = "24 hours" + (f", {ch:+.2f}%" if isinstance(ch, (int, float)) else "")
    sma = btc.get("sma200")
    if isinstance(sma, (int, float)) and sma:
        gap = (c["price"] / sma - 1) * 100
        since_t += f"; {abs(gap):.1f}% {'above' if gap >= 0 else 'below'} its 200-day average"
        thru = sb._series_stamp(btc, pulse, html=False)
        if thru:
            win += f"; 200-day from {thru}"
    return tile.render("bitcoin", sb._price_fmt(c["price"]), direction=_dir(ch),
                       window=win,
                       since=since_t, source="CoinGecko", stamp=st)


def t_cap(snap, deltas):
    import site_build as sb
    import tile
    cap, src, st = _field(snap, "total_cap")
    if not isinstance((cap or {}).get("usd"), (int, float)) or not st:
        return ""
    dom = (snapshot_value(snap, "dominance") or {}).get("btc_pct")
    d = (deltas.get("market") or {}).get("pct")
    since_t = (f"{'Up' if d > 0 else 'Down' if d < 0 else 'Level'} {abs(d):.2f}% since "
               f"yesterday's close" if isinstance(d, (int, float))
               else "No close kept for yesterday")
    if isinstance(dom, (int, float)):
        since_t += f"; Bitcoin is {dom:.1f}% of it"
    ch = cap.get("chg_24h_pct")
    return tile.render("total-cap", sb.fmt_usd(cap["usd"]), direction=_dir(ch),
                       window="every coin, 24 hours" + (f", {ch:+.2f}%"
                                                         if isinstance(ch, (int, float)) else ""),
                       since=since_t, source="CoinGecko", stamp=st)


def t_fee(snap, deltas):
    import tile
    nw, src, st = _field(snap, "network_fee")
    fee = (nw or {}).get("fastest_fee")
    if not isinstance(fee, (int, float)) or not st:
        return ""
    nd = deltas.get("network") or {}
    pts = nd.get("points")
    since_t = ("No figure kept for yesterday" if pts is None else
               "Unchanged since yesterday" if pts == 0 else
               f"{'Up' if pts > 0 else 'Down'} {abs(pts):g} sat/vB since yesterday")
    return tile.render("network-fee", f"{fee:g} sat/vB", window="next block, fastest rate",
                       since=since_t, source="mempool.space", stamp=st)


def snapshot_value(snap, name):
    import snapshot
    return snapshot.value(snap, name)


def money(snap, pulse, flows, deltas):
    tiles = [t_etf(snap, pulse), t_float(snap, deltas), t_whale(snap, flows)]
    if not any(tiles):
        return _block("money", '<p class="h-wait">Waiting for the snapshot\'s flows.</p>',
                      "The money")
    import tile
    return _block("money", tile.grid(tiles), "The money")


def mood(snap, pulse, deltas):
    tiles = [t_funding(snap, pulse), t_oi(snap, deltas), t_fng(snap, deltas)]
    if not any(tiles):
        return _block("mood", '<p class="h-wait">Waiting for the snapshot\'s mood readings.'
                              '</p>', "The mood")
    import tile
    return _block("mood", tile.grid(tiles), "The mood")


# ---- moving today, today, mine ------------------------------------------------------------

def movers(snap):
    import snapshot
    mv = snapshot.value(snap, "movers") or {}
    if not mv:
        return _block("movers", '<p class="h-wait">Waiting for the snapshot\'s top 100.</p>',
                      "Moving today, top 20")

    def row(c):
        ch = c.get("chg_24h_pct")
        return (f'<li><span class="h-mr">#{_e(c.get("rank"))}</span>'
                f'<a href="/coins/{_e(str(c.get("symbol")).lower())}">{_e(c.get("symbol"))}</a>'
                f'<span class="h-mn">{_e(c.get("name") or "")}</span>'
                f'<span class="h-mc {_dir(ch)}">{_pctx(ch)}</span></li>')
    # nothing twice: a coin the tape prints is not listed again here (Sprint 6.2)
    taped = {"BTC"} | {sym for sym, _n, _g in TAPE_ALTS}
    rises = [c for c in mv.get("top20_rises") or [] if c.get("symbol") not in taped]
    fall = mv.get("top20_fall")
    if fall and fall.get("symbol") in taped:
        fall = None
    lis = "".join(row(c) for c in rises)
    if fall:
        lis += row(fall)
    stand = [c for c in mv.get("standouts") or [] if c.get("symbol") not in taped]
    if stand:
        sl = ", ".join(f'{_e(c["symbol"])} <span class="h-mc {_dir(c["chg_24h_pct"])}">'
                       f'{_pctx(c["chg_24h_pct"])}</span>' for c in stand)
    else:
        sl = _e(mv.get("standouts_line") or "none today")
    return _block("movers", f'<ol class="h-movers">{lis}</ol>'
                            f'<p class="h-stand">Top 100 beyond 5% either way: {sl}</p>',
                  "Moving today, top 20")


def today(cal, now=None):
    now = now or _now()
    day = now.astimezone(_ET).date().isoformat()
    ents = [e for e in ((cal or {}).get("entries") or []) if e.get("date") == day]
    if not ents:
        return _block("today", f'<p class="h-cal-none">{_e(NO_CAL.capitalize())}.</p>',
                      "Today")
    lis = []
    for e in ents:
        src = e.get("source") or {}
        s = (f'<a href="{_e(src["url"])}" rel="noopener">{_e(src.get("name") or "Source")}</a>'
             if src.get("url") else _e(src.get("name") or ""))
        lis.append(f'<li><span class="h-ct">{_e(e.get("time_et") or "time not published")}'
                   f'</span><span class="h-ce">{_e(e.get("title"))}</span>'
                   f'<span class="h-cs">{s}</span></li>')
    return _block("today", f'<ul class="h-cal">{"".join(lis)}</ul>', "Today")


def mine():
    return _block("mine", f'<div class="h-mine" data-mine>'
                          f'<p class="h-mine-empty">{_e(EMPTY_MINE)}</p></div>', "Mine")


# ---- below the fold --------------------------------------------------------------------

BELOW_FOLD = ("board", "whales", "brief", "record")


# NOTHING TWICE (Program 6, Sprint 6.2): every reading the fold above already prints, by its
# tile key. Bitcoin's price and the whole market are on the tape, the 200-day in since
# yesterday, the ETF, the float and the whales in the money, funding (and so its annualized
# Leverage tile), open interest and Fear & Greed in the mood. The Board below the fold
# draws only what is left, and links the full Board for the rest.
ABOVE_READINGS = ("bitcoin", "total-cap", "etf-net", "whale-net", "stablecoin-float",
                  "funding", "open-interest", "fear-greed")


def board(snap, pulse, flows, deltas):
    """The Board below the fold: the Board's tiles, every one through tile.render, less
    every reading already printed above the fold."""
    import re
    tiles = [t_bitcoin(snap, pulse, deltas), t_cap(snap, deltas), t_etf(snap, pulse),
             t_whale(snap, flows), t_leverage(snap, pulse), t_float(snap, deltas),
             t_fng(snap, deltas), t_fee(snap, deltas)]
    tiles = [t for t in tiles if t and re.search(r'data-reading="([a-z-]+)"', t).group(1)
             not in ABOVE_READINGS]
    import tile
    head = (f'<p class="h-sub">As of {_e(snap.get("stamp_et") or "")}. '
            f'<a href="/pulse.html">{_e(_tn("markets"))}, in full</a></p>')
    if not any(tiles):
        return _block("board", head + '<p class="h-wait">Waiting for the snapshot.</p>',
                      _tn("markets"))
    return _block("board", head + tile.grid(tiles, "tl-4" if len(tiles) >= 4 else ""),
                  _tn("markets"))


SIGN_LINE = ("Each bar is one week's net, transfers of $50 million and up, all coins. Off "
             "exchanges is positive and drawn up in green; onto exchanges is negative and "
             "drawn down in red.")


def whale_bars(history, w=600, h=150, pad=4):
    """[(x, y, width, height, cls)] for each published week: one bar per point, from the
    zero line, to scale against the largest week either way. Nothing interpolated."""
    pts = [r for r in history or [] if isinstance(r.get("net_usd"), (int, float))]
    if not pts:
        return []
    top = max(abs(r["net_usd"]) for r in pts) or 1.0
    mid = h / 2
    slot = (w - 2 * pad) / len(pts)
    bw = max(2.0, slot * 0.7)
    out = []
    for i, r in enumerate(pts):
        v = r["net_usd"]
        bh = (h / 2 - pad) * abs(v) / top
        x = pad + i * slot + (slot - bw) / 2
        y = mid - bh if v >= 0 else mid
        out.append((round(x, 1), round(y, 1), round(bw, 1), round(max(bh, 0.5), 1),
                    "up" if v > 0 else "down" if v < 0 else "flat", r))
    return out


def whales(flows):
    import site_build as sb
    hist = (flows or {}).get("history") or []
    bars = whale_bars(hist)
    if not bars:
        return _block("whales", '<p class="h-wait">Waiting for Whale Alert\'s weekly '
                                'history.</p>', "Whales, 13 weeks")
    rects = "".join(
        f'<rect class="{c}" x="{x}" y="{y}" width="{bw}" height="{bh}">'
        f'<title>Week ending {_e(r.get("week_ending"))}: {_e(sb.flow_words(r["net_usd"])[0])} '
        f'{_e(sb.flow_words(r["net_usd"])[1])}</title></rect>'
        for x, y, bw, bh, c, r in bars)
    first, last = bars[0][5].get("week_ending"), bars[-1][5].get("week_ending")
    svg = (f'<svg class="h-wbars" viewBox="0 0 600 150" preserveAspectRatio="none" role="img" '
           f'aria-label="Weekly whale net, {len(bars)} weeks, week ending {_e(first)} to '
           f'{_e(last)}"><line x1="0" y1="75" x2="600" y2="75"/>{rects}</svg>')
    n = len(bars)
    return _block("whales", f'<p class="h-sub">{n} weeks, week ending {_e(first)} to '
                            f'{_e(last)}. <a href="/flows.html">{_e(_tn("flows"))}</a></p>{svg}'
                            f'<p class="h-sign">{_e(SIGN_LINE)} Source: Whale Alert public '
                            f'archive.</p>', f"Whales, {n} weeks")


def brief(ed, now=None):
    """The Brief, the day's edition as current_bottom_line resolved it, with its stamp."""
    if not ed:
        return _block("brief", f'<p class="h-wait">The Brief arrives with the Edition at '
                               f'{_e(edition_time_et(now))}.</p>', _tn("brief"))
    st = _stamp(ed.get("published_utc"))
    lead = ed.get("bottom_line") or ed.get("dek") or ""
    return _block("brief", f'<h3 class="h-bh"><a href="/articles/{_e(ed.get("slug"))}.html">'
                           f'{_e(ed.get("title"))}</a></h3>'
                           + (f'<p class="h-bl">{_e(lead)}</p>' if lead else "")
                           + f'<p class="h-st">Published {_e(st)}</p>', _tn("brief"))


def record(items):
    """The Record's lanes, one piece each: the lane's first evergreen pick."""
    import site_build as sb
    by_lane, _ = sb._record_inventory(items)
    lis = []
    for slug, name, _tags, _home in sb.RECORD_LANES:
        it = (by_lane.get(slug) or [None])[0]
        if not it:
            continue
        lis.append(f'<li data-lane="{_e(slug)}"><span class="h-ln">{_e(name)}</span>'
                   f'<a href="/articles/{_e(it.get("slug"))}.html">{_e(it.get("title"))}</a>'
                   f'<span class="h-st">{_e(sb.fmt_date(it.get("date")) if it.get("date") else "")}'
                   f'</span></li>')
    if not lis:
        return _block("record", '<p class="h-wait">Record has no pieces yet.</p>',
                      _tn("record"))
    return _block("record", f'<ul class="h-rec">{"".join(lis)}</ul>'
                            f'<p class="h-sub"><a href="/record.html">{_e(_tn("record"))}, in full</a></p>',
                  _tn("record"))


def below_fold(snap, pulse, flows, deltas, items, ed, now=None):
    return (f'<div class="h-below" data-fold="below">'
            f'{board(snap, pulse, flows, deltas)}{whales(flows)}{brief(ed, now)}'
            f'{record(items)}</div>')



# ---- the page -----------------------------------------------------------------------------

def above_fold(snap, pulse, flows, deltas, wire, narr, cal, cadence, now=None):
    """The ten blocks of section 2, in order, as one string."""
    blocks = {
        "tape": tape(snap), "narrative": narrative_band(narr, snap),
        "since": since(pulse, deltas), "why": why(wire, now),
        "wire": wire_top(wire, cadence, now), "money": money(snap, pulse, flows, deltas),
        "mood": mood(snap, pulse, deltas), "movers": movers(snap),
        "today": today(cal, now), "mine": mine(),
    }
    left = "".join(blocks[k] for k in LEFT)
    right = "".join(blocks[k] for k in ABOVE_FOLD if k not in LEFT)
    return (f'<div class="h-cols" data-fold="above"><div class="h-l">{left}</div>'
            f'<div class="h-r">{right}</div></div>')


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


# THE RUNTIME HALF: the tape's live read and the mine block. One script, first party, no
# library. The tape asks CoinGecko once on load; a price that changes fades its digits; the
# stamp says "live" only after an OK answer that carried a price. Mine reads the device's
# pins and, only when there are some, the snapshot.
HOME_JS = """<script>(function(){
  var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  function etClock(){try{return new Date().toLocaleTimeString('en-US',{timeZone:'America/New_York',hour:'numeric',minute:'2-digit'})+' ET';}catch(e){return '';}}
  function px(n){return '$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:n>=1?2:6,maximumFractionDigits:n>=1?2:6});}
  function pc(p){return (p>=0?'+':'')+p.toFixed(2)+'%';}
  fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd&include_24hr_change=true')
   .then(function(r){if(!r.ok)throw new Error(r.status);return r.json();}).then(function(d){
    var landed=0;
    document.querySelectorAll('[data-tape]').forEach(function(el){
      var v=d[el.getAttribute('data-tape')]; if(!v||typeof v.usd!=='number')return;
      landed++; var s=px(v.usd);
      if(el.textContent!==s){el.textContent=s; if(!RM){el.classList.remove('h-fade');void el.offsetWidth;el.classList.add('h-fade');}}
    });
    if(!landed)return;
    document.querySelectorAll('[data-tape-chg]').forEach(function(el){
      var v=d[el.getAttribute('data-tape-chg')]; if(!v||typeof v.usd_24h_change!=='number')return;
      el.textContent=pc(v.usd_24h_change); el.className=el.className.replace(/ ?(up|down)/g,'')+(v.usd_24h_change>0?' up':v.usd_24h_change<0?' down':'');
    });
    var st=document.getElementById('tapeLive'); if(st){st.textContent='live \\u00b7 '+etClock();st.classList.add('on');}
  }).catch(function(){});
  var host=document.querySelector('[data-mine]'); if(!host)return;
  var picks=[]; try{picks=JSON.parse(localStorage.getItem('gcmc_coins')||'[]');}catch(e){return;}
  if(!picks.length)return;
  fetch('/data/snapshot.json').then(function(r){return r.ok?r.json():null;}).then(function(s){
    var coins=(((s||{}).fields||{}).coins||{}).value||{};
    var rows=picks.filter(function(k){return coins[k]&&typeof coins[k].price==='number';});
    if(!rows.length)return;
    host.innerHTML='<ul class="h-mine-l">'+rows.map(function(k){var c=coins[k],ch=c.chg_24h_pct;
      return '<li><a href="/coins/'+k.toLowerCase()+'">'+k+'</a><span class="h-mp">'+px(c.price)+'</span>'
        +(typeof ch==='number'?'<span class="h-mc '+(ch>0?'up':ch<0?'down':'')+'">'+pc(ch)+'</span>':'')+'</li>';}).join('')
      +'</ul><p class="h-st">As of '+(s.stamp_et||'')+'</p>';
  }).catch(function(){});
})();</script>"""
