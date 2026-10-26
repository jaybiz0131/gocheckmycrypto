#!/usr/bin/env python3
"""
phrases.py: every number a model is handed, already labeled (Program 8, Sprint 8.2, item 0).

Three failures in two days had one cause: the model worked out a sign or a window itself and got
it wrong.
  - 14 Oct, 7:17 PM Edition: the ETF window, three times (floored in 8.1).
  - 14 Oct, 7:46 PM re-run: "Bitcoin +2.83% on the week" for -2.83%, "Ether +7.44%" for -7.44%
    (one direction word stood in front of two figures; the twins gate read the second as
    positive and dropped both sentences).
  - 15 Oct, 8:18 AM morning read: fell back. The wire's top line carried "up to 2% spread" and
    the funding reading arrived as "0.0047", which the model wrote as "percent": the copy law
    cut every sentence.

The fix is at the source and costs no model call. A number reaches a model only as a phrase that
carries its own sign, unit and window in words ("Bitcoin down 2.83% over seven days"). The model
chooses among phrases and copies one whole; it never computes a direction or a window. The
trace checker and the belts keep reading the raw digest; only the model-facing copy is changed.

The words are the ones the desk's belts and the twins gate already read: "over seven days" and
"over thirty days" bucket as the week and the month, "on the day, October 14" as the day,
"over the week through October 14" as the week.
"""
import copy
import datetime as _dt
import re

# The market dashboard's old name (docs/audit-2026-10/NAMES.md: the page is "Markets"). The morning read's prompt now says
# Markets; this is the belt: a sentence a model writes with the old name is cut by morning.clean, and the home withholds a
# STORED sentence that carries it (home.usable_morning). Withholding is not rewording (Jack, J-10: stored reads are never
# reworded). "the Board of ..." is a board of people, not the dashboard.
OLD_BOARD_NAME = re.compile(r"\b[Tt]he Board(?:'s|\u2019s)?\b(?! of\b)")


def has_old_name(text):
    """True when the text calls the market dashboard 'the Board'."""
    return bool(OLD_BOARD_NAME.search(str(text or "")))


NAMES = {"BTC": "Bitcoin", "ETH": "Ether", "SOL": "Solana", "XRP": "XRP", "BNB": "BNB",
         "DOGE": "Dogecoin", "ADA": "Cardano"}
WINDOWS = {"24h": "over 24 hours", "7d": "over seven days", "30d": "over thirty days"}
FLAT_PCT = 0.05            # under this a figure prints as no change, never as "up 0.00%"
MORNING_FLAT_PCT = 0.5     # the morning read says "little changed" inside half a percent


def pct(name, v, window):
    """'Bitcoin down 2.83% over seven days'. The word is the figure's own sign."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return ""
    w = WINDOWS[window]
    if abs(v) < FLAT_PCT:
        return f"{name} little changed {w}"
    return f"{name} {'up' if v > 0 else 'down'} {abs(v):.2f}% {w}"


def long_date(raw):
    """'October 14' from '2026-10-14' or '14 Oct 2026' (Farside's form); '' when it is neither."""
    raw = str(raw or "").strip()
    for fmt, n in (("%Y-%m-%d", 10), ("%d %b %Y", 11), ("%d %B %Y", 17)):
        try:
            d = _dt.datetime.strptime(raw[:n].strip() if fmt == "%Y-%m-%d" else raw, fmt).date()
        except ValueError:
            continue
        return f"{d.strftime('%B')} {d.day}"
    return ""


def change(v, window):
    """'down 3.37% over 24 hours', the phrase without a name; '' with no figure."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return ""
    w = WINDOWS[window]
    if abs(v) < FLAT_PCT:
        return f"little changed {w}"
    return f"{'up' if v > 0 else 'down'} {abs(v):.2f}% {w}"


def money_m(v):
    return f"${abs(v):,.1f}M"


def etf_day(v, when):
    d = long_date(when) or "the latest session"
    on = f"on the day, {d}" if long_date(when) else "on the day"
    if abs(v) < 0.05:
        return f"spot Bitcoin ETFs saw no net flow {on}"
    verb = f"took in {money_m(v)}" if v > 0 else f"saw net outflows of {money_m(v)}"
    return f"spot Bitcoin ETFs {verb} {on}"


def etf_week(v, when):
    d = long_date(when)
    tail = f" through {d}" if d else ""
    if abs(v) < 0.05:
        return f"spot Bitcoin ETFs saw no net flow over the week{tail}"
    verb = f"took in {money_m(v)}" if v > 0 else f"saw net outflows of {money_m(v)}"
    return f"spot Bitcoin ETFs {verb} over the week{tail}"


def _asset_name(sym):
    return NAMES.get(str(sym).upper(), str(sym))


def edition_numbers(boards):
    """The labeled numbers for the Edition: [{"what": ..., "say": [...]}]. Each phrase is one
    claim with its sign and window in words."""
    out = []
    for a in (boards or {}).get("assets") or []:
        sym, name = a.get("symbol"), _asset_name(a.get("symbol"))
        say = [p for p in (pct(name, a.get("chg_24h_pct"), "24h"), pct(name, a.get("chg_7d_pct"), "7d"),
                           pct(name, a.get("chg_30d_pct"), "30d")) if p]
        if say:
            out.append({"what": f"{name} price change", "say": say})
    etf = ((boards or {}).get("etf_flows") or {}).get("btc") or {}
    when = etf.get("latest_date")
    say = []
    if isinstance(etf.get("latest_net_usd_m"), (int, float)):
        say.append(etf_day(etf["latest_net_usd_m"], when))
    if isinstance(etf.get("last5_sessions_net_usd_m"), (int, float)):
        say.append(etf_week(etf["last5_sessions_net_usd_m"], when))
    if say:
        out.append({"what": "Bitcoin spot ETF net flows", "say": say})
    mv = (boards or {}).get("movers") or {}
    for side, label in (("gainers", "gainers"), ("losers", "losers")):
        say = [pct(_asset_name(m.get("symbol")), m.get("chg_24h_pct"), "24h") for m in mv.get(side) or []]
        say = [s for s in say if s]
        if say:
            out.append({"what": f"top {label} among the largest coins", "say": say})
    return out


NUMBERS_RULE = (
    "labeled_numbers (EVERY price change and ETF flow below is already worded with its own sign and "
    "window. Copy a phrase whole. Never put two figures behind one direction word: give each its own "
    "\"up\" or \"down\". Never work out a direction or a window yourself, and never restate a number "
    "that is not in this block):\n")


def numbers_block(boards):
    """The text block the Edition's user message carries. '' with no boards."""
    rows = edition_numbers(boards)
    if not rows:
        return ""
    import json
    return NUMBERS_RULE + json.dumps(rows, indent=1) + "\n\n"


# the raw signed fields the model no longer sees: its phrases replace them
_RAW_ASSET = ("chg_24h_pct", "chg_7d_pct", "chg_30d_pct")


def model_boards(boards):
    """A copy of the digest for the model: the signed window changes and the ETF nets are gone
    (the labeled_numbers block says them), everything else stays. The trace checker and the belts
    keep the original."""
    d = copy.deepcopy(boards or {})
    for a in d.get("assets") or []:
        for k in _RAW_ASSET:
            a.pop(k, None)
    for side in ("gainers", "losers"):
        for m in ((d.get("movers") or {}).get(side) or []):
            m.pop("chg_24h_pct", None)
    for k in ("btc", "eth"):
        e = (d.get("etf_flows") or {}).get(k)
        if k == "btc" and isinstance(e, dict):
            for f in ("latest_net_usd_m", "last5_sessions_net_usd_m"):
                e.pop(f, None)
    d.pop("window_signs", None)
    d.pop("flow_signs", None)
    return d


# ---- the morning read: phrases with no percent in them (the copy law quotes no change) --------

_PCT_TAIL = re.compile(r"(?:,\s+|\s+(?:with|at|by|amid|as|while|after)\s+)", re.I)
_HAS_PCT = re.compile(r"\d\s*(?:%|percent)|\bpercent(?:age)?\b|\bbasis points?\b|\bbps\b", re.I)


def percent_free(line):
    """The wire line with its percent clause cut, or None when it cannot be cut cleanly. The
    morning read quotes no change, and a wire line that carries "up to 2% spread" had every
    sentence built on it cut by the copy law (15 Oct). The clause that holds the figure is cut
    from the nearest connector before it when that clause ends the line; a figure in the middle
    of a line leaves the line out."""
    line = " ".join(str(line or "").split())
    if not _HAS_PCT.search(line):
        return line
    m = _HAS_PCT.search(line)
    cuts = [c for c in _PCT_TAIL.finditer(line[:m.start()])]
    if not cuts:
        return None
    cut = cuts[-1].start()
    tail = line[m.end():]
    if re.search(r"[,;]|\b(?:and|but|while)\b", tail) or cut < 0.4 * len(line):
        return None
    head = line[:cut].rstrip(" ,;:")
    if _HAS_PCT.search(head):
        return None
    return head + ("." if line.rstrip().endswith(".") else "")


def morning_phrases(r):
    """The Board's readings as percent-free phrases: direction in words, flows in dollars, bands
    by name. `r` is narrative.readings(snapshot)."""
    out = []
    p = (r or {}).get("btc_24h_pct")
    if isinstance(p, (int, float)):
        out.append("Bitcoin little changed over the past 24 hours" if abs(p) < MORNING_FLAT_PCT
                   else f"Bitcoin {'higher' if p > 0 else 'lower'} over the past 24 hours")
    e = (r or {}).get("etf_net_usd_m")
    if isinstance(e, (int, float)):
        out.append(etf_day(e, r.get("etf_date")))
    if isinstance((r or {}).get("fear_greed"), (int, float)):
        out.append(f"the Fear & Greed index reads {r['fear_greed']:g}, "
                   f"{str(r.get('fear_greed_band') or '').lower()}")
    if r and r.get("funding_band"):
        out.append(f"funding on Bitcoin perpetual futures is {str(r['funding_band']).lower()}")
    return out


# ---- the headline: why it failed, and the deterministic repair --------------------------------

def headline_problem(head, limit):
    """'' when the headline will do, else why not, in words the model can act on."""
    h = str(head or "").strip()
    if not h:
        return "is missing; write a plain headline of 100 characters or fewer in the headline field"
    if len(h) > limit:
        return (f"is too long ({len(h)} characters; the limit is {limit}); shorten it to {limit} "
                f"characters or fewer")
    return ""


_CLAUSE = re.compile(r"(?:,\s+|\s+(?:through|with|as|amid|for|after|while|but|and)\s+)", re.I)


def trim_headline(h, limit):
    """At a word boundary, under the limit, with no dangling connector or punctuation. When a
    clause break sits late enough in what fits, the headline ends there instead of mid-phrase."""
    h = " ".join(str(h or "").split())
    if len(h) <= limit:
        return h
    cut = h[:limit + 1]
    cut = cut[:cut.rfind(" ")] if " " in cut else h[:limit]
    breaks = [m.start() for m in _CLAUSE.finditer(cut) if m.start() >= max(45, len(cut) - 20)]
    if breaks:
        cut = cut[:breaks[-1]]
    cut = cut.rstrip(" ,;:-")
    while True:
        nxt = re.sub(r"\s+(?:and|or|but|of|to|for|in|on|at|with|the|a|an|as|by)$", "", cut, flags=re.I).rstrip(" ,;:-")
        if nxt == cut:
            return cut
        cut = nxt


def derive_headline(top_lines, limit):
    """The headline from the top phrase: the wire's first usable line, trimmed, else the plain
    fixed line. Honest by construction: it says what the note is."""
    for ln in top_lines or []:
        ln = str(ln or "").strip().rstrip(".")
        if ln:
            return trim_headline(ln, limit)
    return "This morning's read: what the wire carries and what the Board shows"
