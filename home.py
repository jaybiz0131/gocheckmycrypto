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
    pts = spark_points(week.get("closes"))
    spark = ""
    if pts:
        poly = " ".join(f"{x},{y}" for x, y in pts)
        spark = (f'<svg class="h-spark" viewBox="0 0 300 56" preserveAspectRatio="none" '
                 f'role="img" aria-label="Bitcoin, {len(pts)} daily closes">'
                 f'<polyline pathLength="1" points="{poly}"/></svg>')
    rng = ""
    if isinstance(week.get("low"), (int, float)) and isinstance(week.get("high"), (int, float)):
        rng = (f'<p class="h-rng"><span>7-day low <b>{_e(sb._price_fmt(week["low"]))}</b></span>'
               f'<span>high <b>{_e(sb._price_fmt(week["high"]))}</b></span></p>')
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
             f'{spark}{rng}</div>'
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
    small = str(narr.get("small_line") or "").strip()
    when = narr.get("written_et") or ""
    tail = f" ({when})" if when and small else ""
    return _block("narrative", f'<p class="h-nline">{_e(line)}</p>'
                               + (f'<p class="h-nsmall">{_e(small)}{_e(tail)}.</p>'
                                  if small else ""), cls="h-band")


# ---- since yesterday ----------------------------------------------------------------------

def since(pulse, deltas):
    import site_build as sb
    rows = []
    btc = sb._btc(pulse) or {}
    px, sma = btc.get("price"), btc.get("sma200")
    if isinstance(px, (int, float)) and isinstance(sma, (int, float)) and sma:
        gap = (px / sma - 1) * 100
        d = (deltas.get("bitcoin") or {}).get("pct")
        tail = (f', <span class="h-d {_dir(d)}">{_pctx(d)}</span> since yesterday'
                if isinstance(d, (int, float)) else ", with no close kept for yesterday")
        rows.append(f'<li>Bitcoin is <span class="h-d">{abs(gap):.1f}%</span> '
                    f'{"above" if gap >= 0 else "below"} its 200-day average of '
                    f'<span class="h-d">{_e(sb._price_fmt(sma))}</span>{tail}.</li>')
    mkt = (pulse or {}).get("market") or {}
    if isinstance(mkt.get("total_mcap_usd"), (int, float)):
        d = (deltas.get("market") or {}).get("pct")
        dom = mkt.get("btc_dominance_pct")
        mid = (f', <span class="h-d {_dir(d)}">{_pctx(d)}</span> since yesterday'
               if isinstance(d, (int, float)) else ", with no close kept for yesterday")
        tail = (f', with Bitcoin at <span class="h-d">{dom:.1f}%</span> of it'
                if isinstance(dom, (int, float)) else "")
        rows.append(f'<li>The whole market is <span class="h-d">'
                    f'{_e(sb.fmt_usd(mkt["total_mcap_usd"]))}</span>{mid}{tail}.</li>')
    fg = (pulse or {}).get("fng") or {}
    if isinstance(fg.get("value"), (int, float)):
        fd = deltas.get("fng") or {}
        word = sb._fng_band(fg["value"])
        if isinstance(fd.get("prev"), (int, float)):
            pts = fd.get("points") or 0
            tail = (f', <span class="h-d">{pts:+g}</span> from <span class="h-d">'
                    f'{fd["prev"]:g}</span> yesterday')
        else:
            tail = ", with no figure kept for yesterday"
        rows.append(f'<li>Fear &amp; Greed reads <span class="h-d">{fg["value"]:g}</span>, '
                    f'{_e(word.lower())}{tail}.</li>')
    if not rows:
        return _block("since", '<p class="h-wait">Waiting for the Board\'s readings.</p>',
                      "Since yesterday")
    return _block("since", f'<ul class="h-since">{"".join(rows)}</ul>', "Since yesterday")


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


def money(snap, pulse, flows, deltas):
    import site_build as sb
    import tile
    tiles = []
    etf, src, st = _field(snap, "etf_flows")
    b = (etf or {}).get("btc") or {}
    net = b.get("latest_net_usd_m")
    if isinstance(net, (int, float)) and st:
        fig = (f"{'+' if net > 0 else '-' if net < 0 else ''}{sb.fmt_usd(abs(net) * 1e6)}"
               if net else "flat")
        rec = [r for r in ((((pulse or {}).get("etf_flows") or {}).get("btc") or {})
                           .get("recent") or []) if isinstance(r.get("net_usd_m"), (int, float))]
        word = "inflow" if net > 0 else "outflow" if net < 0 else "flat"
        if len(rec) >= 2:
            pm = rec[-2]["net_usd_m"]
            pw = "in" if pm > 0 else "out" if pm < 0 else "flat"
            since_t = (f"Net {word}; the session before was "
                       f"{sb.fmt_usd(abs(pm) * 1e6)} {pw}" if pm else
                       f"Net {word}; the session before was flat")
        else:
            since_t = f"Net {word}; no session before it on record"
        tiles.append(tile.render("etf-net", fig, direction=_dir(net),
                                 window=f"one trading day, {sb.us_date(b.get('latest_date')) or b.get('latest_date')}",
                                 since=since_t, source=src.split(" (")[0], stamp=st))
    stv, src, st = _field(snap, "stablecoin_float")
    if isinstance((stv or {}).get("total_usd"), (int, float)) and st:
        d = (deltas.get("stables") or {}).get("pct")
        since_t = (f"{'Up' if d > 0 else 'Down' if d < 0 else 'Level'} "
                   f"{abs(d):.2f}% since yesterday" if isinstance(d, (int, float))
                   else "No close kept for yesterday")
        tiles.append(tile.render("stablecoin-float", sb.fmt_usd(stv["total_usd"]),
                                 window="all stablecoins in circulation, now",
                                 since=since_t, source=src.split(" ")[0], stamp=st))
    wv, src, st = _field(snap, "whale_net")
    if isinstance((wv or {}).get("net_usd"), (int, float)) and st \
            and sb._flows_have_data(flows):
        amt, words, cls = sb.flow_words(wv["net_usd"])
        # flows.json keeps weekly history, not a daily record, so there is no yesterday
        # to compare with, and the tile says so rather than pass a week off as a day.
        since_t = f"Net {words}; no reading kept for yesterday"
        tiles.append(tile.render("whale-net", amt, direction=cls,
                                 window=f"{sb._win_phrase(wv.get('window_hours', 24))}, all coins",
                                 since=since_t, source="Whale Alert", stamp=st))
    if not tiles:
        return _block("money", '<p class="h-wait">Waiting for the snapshot\'s flows.</p>',
                      "The money")
    return _block("money", tile.grid(tiles), "The money")


def mood(snap, pulse, deltas):
    import narrative
    import site_build as sb
    import tile
    tiles = []
    fund, src, st = _field(snap, "funding")
    f = (fund or {}).get("BTC") or {}
    v = f.get("funding_8h_pct")
    if isinstance(v, (int, float)) and st:
        word = narrative.funding_band(v)
        hist = []
        for a in (((pulse or {}).get("leverage") or {}).get("assets") or []):
            if a.get("symbol") == "BTC":
                hist = [h for h in a.get("funding_history_pct") or []
                        if isinstance(h, (int, float))]
        if len(hist) >= 4:
            since_t = (f"{word.capitalize()}; {hist[-4]:+.4f}% at the settlement 24 hours "
                       f"before the latest")
        else:
            since_t = f"{word.capitalize()}; no settlement a day back on record"
        tiles.append(tile.render("funding", f"{v:+.4f}%", label="Funding, per 8 hours",
                                 window="Bitcoin perpetual, current 8-hour period",
                                 since=since_t, source=f.get("venue") or "OKX", stamp=st))
    oi, src, st = _field(snap, "open_interest")
    o = (oi or {}).get("BTC") or {}
    if isinstance(o.get("usd"), (int, float)) and st:
        venue = o.get("venue") or "OKX"
        d = (deltas.get("leverage") or {}).get("pct")
        if isinstance(d, (int, float)):
            tiles.append(tile.render(
                "open-interest", f"{d:+.2f}%", label="Open interest change",
                window=f"since yesterday's close, the five coins tracked on {venue}",
                since=f"Bitcoin: {sb.fmt_usd(o['usd'])} open on {venue} now",
                source=venue, stamp=st))
        else:
            tiles.append(tile.render(
                "open-interest", sb.fmt_usd(o["usd"]), label="Open interest",
                window=f"Bitcoin perpetuals on {venue}, now",
                since="No close kept for yesterday, so no change", source=venue, stamp=st))
    fg, src, st = _field(snap, "fear_greed")
    if isinstance((fg or {}).get("value"), (int, float)) and st:
        val = fg["value"]
        fd = deltas.get("fng") or {}
        word = sb._fng_band(val)
        since_t = (f"{word}; {fd['prev']:g} yesterday" if isinstance(fd.get("prev"), (int, float))
                   else f"{word}; no figure kept for yesterday")
        tiles.append(tile.render("fear-greed", f"{val:g}", window="today, scale 0 to 100",
                                 since=since_t, source="alternative.me", stamp=st))
    if not tiles:
        return _block("mood", '<p class="h-wait">Waiting for the snapshot\'s mood readings.'
                              '</p>', "The mood")
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
    rises = mv.get("top20_rises") or []
    fall = mv.get("top20_fall")
    lis = "".join(row(c) for c in rises)
    if fall:
        lis += row(fall)
    stand = mv.get("standouts") or []
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
