#!/usr/bin/env python3
"""morning_line.py: THE DATA LEAD (Sprint A, A2, Nov 7 2026 site audit).

The Why it moved block renders a read on every build from the boards already on the page, with no
model call and no stored text: Bitcoin since midnight ET and over 24 hours, the latest ETF net flow
with its date, the whale net with its direction in words, funding, Fear and Greed with yesterday's
value, and the top 20 and top 100 movers. Two sentences, the same shape every day. A reading the
snapshot does not carry is left out of the sentence; a prior value the desk did not keep is called
a "first reading". Nothing here names a Brief, a missing Brief or an earlier one.

`movers_board(snap)` is the one movers list: the top 20 by market cap ordered by the size of the
24-hour move, then the top 100 beyond 5% either way, ordered by magnitude. Stablecoins are never
movers. The home's Moving today block, /pulse/movers and this lead all read it.

Pure on its arguments, so the canary renders it from fixtures.
"""

import datetime as _dt

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:                                  # pragma: no cover
    _ET = _dt.timezone(_dt.timedelta(hours=-5))

BEYOND_PCT = 5.0
FLAT_PCT = 0.05


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _move(v):
    """'up 0.40%', 'down 0.40%', or 'flat' inside FLAT_PCT."""
    if abs(v) < FLAT_PCT:
        return "flat"
    return f"{'up' if v > 0 else 'down'} {abs(v):.2f}%"


def _whole(v):
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}"


def movers_board(snap):
    """(top20, beyond): the top 20 by market cap sorted by absolute 24-hour change, largest first, and the
    top 100 coins past 5% either way sorted by magnitude. Each row: symbol, name, rank, chg_24h_pct."""
    import snapshot
    coins = snapshot.value(snap, "coins") or {}
    rows = []
    for sym, c in coins.items():
        if not isinstance(c.get("rank"), int) or not _num(c.get("chg_24h_pct")):
            continue
        if c.get("stablecoin") or snapshot.is_stablecoin(dict(c, symbol=sym)):
            continue
        rows.append({"symbol": sym, "name": c.get("name") or sym, "rank": c["rank"],
                     "chg_24h_pct": c["chg_24h_pct"]})
    mag = lambda r: (-abs(r["chg_24h_pct"]), r["rank"])
    top20 = sorted((r for r in rows if r["rank"] <= 20), key=mag)
    beyond = sorted((r for r in rows if r["rank"] <= 100 and abs(r["chg_24h_pct"]) > BEYOND_PCT), key=mag)
    return top20, beyond


def lead(snap, deltas=None, now=None):
    """{date_et, dateline, stamp_et, sentences, text} or None when the snapshot holds no Bitcoin price."""
    import snapshot
    import site_build as sb
    import narrative
    now = (now or _dt.datetime.now(_dt.timezone.utc)).astimezone(_ET)
    btc = snapshot.coin(snap, "BTC")
    if not _num(btc.get("price")):
        return None
    day = now.date()
    dateline = f"{day.strftime('%A, %B')} {day.day}"
    stamp = (snap or {}).get("stamp_et") or ""
    clock = stamp.split(" on ")[0] if stamp else ""

    # sentence one: Bitcoin, since midnight ET (only when the snapshot's open is today's) and over 24 hours
    parts = []
    if _num(btc.get("chg_et_day_pct")) and btc.get("open_et_day") == day.isoformat():
        parts.append(f"{_move(btc['chg_et_day_pct'])} since midnight ET")
    if _num(btc.get("chg_24h_pct")):
        parts.append(f"{_move(btc['chg_24h_pct'])} over 24 hours")
    when = f"As of {clock} on {dateline}" if clock else f"On {dateline}"
    s1 = f"{when}, Bitcoin is at {_whole(btc['price'])}"
    s1 += (", " + " and ".join(parts) + ".") if parts else "."

    # sentence two: the money, the mood and the movers, each clause only when its reading is there
    clauses = []
    etf = ((snapshot.value(snap, "etf_flows") or {}).get("btc") or {})
    net = etf.get("latest_net_usd_m")
    if _num(net):
        d = sb.us_date(etf.get("latest_date")) or etf.get("latest_date") or ""
        d = d.rsplit(",", 1)[0] if d.endswith(str(day.year)) else d
        on = f" on {d}" if d else ""
        if net:
            clauses.append(f"spot Bitcoin ETFs took a net {'inflow' if net > 0 else 'outflow'} of "
                           f"{sb.fmt_usd(abs(net) * 1e6)}{on}")
        else:
            clauses.append(f"spot Bitcoin ETF flows were flat{on}")
    wv = snapshot.value(snap, "whale_net") or {}
    if _num(wv.get("net_usd")):
        amt, words, _cls = sb.flow_words(wv["net_usd"])
        clauses.append(f"whales moved a net {amt.lstrip('+-')} {words} over "
                       f"{sb._win_phrase(wv.get('window_hours', 24))}")
    f = ((snapshot.value(snap, "funding") or {}).get("BTC") or {})
    if _num(f.get("funding_8h_pct")):
        v = f["funding_8h_pct"]
        fig = "0.0000%" if abs(v) < 0.00005 else f"{v:+.4f}%"
        clauses.append(f"funding is {narrative.funding_band(v)} at {fig} per 8 hours")
    fg = snapshot.value(snap, "fear_greed") or {}
    if _num(fg.get("value")):
        prev = ((deltas or {}).get("fng") or {}).get("prev")
        was = f"from {prev:g} yesterday" if _num(prev) else "a first reading"
        clauses.append(f"Fear and Greed reads {fg['value']:g} ({sb._fng_band(fg['value'])}), {was}")
    top20, beyond = movers_board(snap)
    if top20:
        m = top20[0]
        clauses.append(f"the top 20's biggest mover is {m['symbol']}, {_move(m['chg_24h_pct'])}")
    if beyond:
        b = beyond[0]
        n = len(beyond)
        clauses.append(f"{n} top 100 coin{'' if n == 1 else 's'} moved more than {BEYOND_PCT:g}%, "
                       f"led by {b['symbol']}, {_move(b['chg_24h_pct'])}")
    elif top20:
        clauses.append(f"no top 100 coin moved more than {BEYOND_PCT:g}%")
    sents = [s1]
    if clauses:
        body = "; ".join(clauses)
        sents.append(body[0].upper() + body[1:] + ".")
    return {"date_et": day.isoformat(), "dateline": dateline, "stamp_et": stamp,
            "sentences": sents, "text": " ".join(sents)}


def card_html(ld, brief_html=""):
    """The Why it moved block when no graded read stands for today: the heading, the date, the written
    Brief above when it exists, and the lead. An aside, as the verdict card is, so it leads the home."""
    import home
    if not ld:
        return ""
    return (f'<aside class="vd vd-lead" data-lead="{home._e(ld["date_et"])}" aria-label="Why Bitcoin moved">'
            f'<h2 class="vd-h">Why Bitcoin moved</h2>'
            f'{brief_html}'
            f'<p class="vd-line h-lead">{home._e(ld["text"])}</p></aside>')


def para_html(ld):
    """The lead as one paragraph under a graded card or a notice (the read is always on the page)."""
    import home
    if not ld:
        return ""
    return f'<p class="vd-line h-lead" data-lead="{home._e(ld["date_et"])}">{home._e(ld["text"])}</p>'
