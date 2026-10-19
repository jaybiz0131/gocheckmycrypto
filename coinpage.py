#!/usr/bin/env python3
"""
coinpage.py: the coin page's parts and the Top 100's row line (Program 7, Sprint 6.4,
13 October 2026).

Pure functions that take the build's own data and return markup, so each can be tested on
its own and the 9,000-line site_build.py only has to place them. Nothing here fetches.

  window_pct / window_dir  a series' own change, first point to last, and its direction. A
                           chart or a sparkline is colored by THIS and by nothing else
                           (Jack, 12 October 2026: each chart is colored by its own window,
                           never by the 24-hour badge).
  row_spark                the Top 100's seven-day line: a plain polyline, colored by its own
                           seven days, with no glow (glow is for charts that can carry it).
  reading_tiles            the readings grid, every tile drawn by tile.render.
  chartmaster_card         the Chart Master's read on this coin, dated, or the coin's levels.
  stories                  the wire items that name the coin, newest first, each with its
                           sources.
  unlock_line              the next token unlock, only where the hand-kept file has one.

A figure the source did not send is absent, not zero: a coin the Board does not track has no
200-day tile and no RSI tile, and no placeholder where they would be.
"""

import datetime as _dt
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
UNLOCKS = os.path.join(HERE, "data", "calendar", "unlocks.json")

WINDOWS = (("1d", "1D", "24 hours"), ("7d", "7D", "7 days"), ("1m", "1M", "1 month"),
           ("1y", "1Y", "1 year"))


def _nums(values):
    return [float(v) for v in (values or []) if isinstance(v, (int, float))]


def window_pct(values):
    """Percent change from the series' first point to its last; None when it cannot be read."""
    v = _nums(values)
    if len(v) < 2 or not v[0]:
        return None
    return (v[-1] - v[0]) / abs(v[0]) * 100.0


def window_dir(values):
    """'up', 'down' or 'flat' from the series' own first and last points."""
    v = _nums(values)
    if len(v) < 2 or v[-1] == v[0]:
        return "flat"
    return "up" if v[-1] > v[0] else "down"


def signed_pct(v, dp=2):
    """+2.31% / -0.40% / 0.00%. A change that rounds to nothing carries no sign."""
    if v is None:
        return ""
    if round(float(v), dp) == 0:
        return f"{0:.{dp}f}%"
    return f"{float(v):+.{dp}f}%"


def row_spark(values, w=64, h=22):
    """The Top 100's seven-day line. A polyline in a w by h box, no filter and no dots (the
    glow rules: glow only where there is room for it), colored by the series' own first and
    last point through the data-dir attribute the stylesheet reads. SVG y runs down, so a
    rising series ends higher on the page, at a smaller y."""
    v = _nums(values)
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{1 + i * (w - 2) / (len(v) - 1):.1f},{1.5 + (h - 3) * (1 - (x - lo) / rng):.1f}"
                   for i, x in enumerate(v))
    d = window_dir(v)
    # A line is tagged by what is DRAWN (Sprint 9.1): ALGO's first and last points differ by
    # 0.01%, which rounds to the same pixel row, so it was drawn flat and tagged up, and origin/main's
    # canary read red on it. The tag is read from the same one-decimal y values the line is drawn with: equal ends are flat.
    ys = [float(pt.split(",")[1]) for pt in pts.split()]
    if ys[0] == ys[-1]:
        d = "flat"
    elif d == "flat":
        d = "up" if ys[-1] < ys[0] else "down"      # SVG y runs down: a smaller last y is a rise
    return (f'<span class="row-spark" data-dir="{d}">'
            f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true" '
            f'focusable="false"><polyline class="rs-l {d}" points="{pts}" '
            f'vector-effect="non-scaling-stroke"/></svg></span>')


# ---- the readings grid --------------------------------------------------------------------

def _since(label, pct):
    """'7 days: Up 2.15%' with the sign worded, which tile.render colors by since_change."""
    if pct is None:
        return None
    if round(pct, 2) == 0:
        return f"{label}: unchanged"
    return f"{label}: {'Up' if pct > 0 else 'Down'} {abs(pct):.2f}%"


def reading_tiles(c, pos, asset, stamp, source="CoinGecko"):
    """The readings grid for one coin: price, 24 hours, 7 days, market cap, volume, and,
    where the Board tracks the coin, the distance from its 200-day line and RSI-14. Each is
    one tile under the tile law (label, figure, window, since line, source and stamp), and
    each is colored only by its own change. Returns the markup of the grid, or ''."""
    import site_build as sb
    import tile

    price = c.get("price")
    c24, c7, c30 = c.get("chg_24h_pct"), c.get("chg_7d_pct"), c.get("chg_30d_pct")
    mcap, vol = c.get("mcap_usd"), c.get("volume_24h")
    out = []

    def add(*a, **k):
        k.setdefault("source", source)
        out.append(tile.render(*a, stamp=stamp, **k))

    if price:
        add("coin-price", sb._price_fmt(price), window="Spot, US dollars",
            since=_since("24 hours", c24) or "24 hours: not reported", since_change=c24)
    if c24 is not None:
        add("coin-24h", signed_pct(c24), window="Rolling 24 hours", direction=_dir(c24),
            since=_since("7 days", c7) or "7 days: not reported", since_change=c7)
    if c7 is not None:
        add("coin-7d", signed_pct(c7), window="Rolling 7 days", direction=_dir(c7),
            since=_since("30 days", c30) or "30 days: not reported", since_change=c30)
    if mcap:
        add("coin-cap", sb.fmt_usd(mcap), window="Price times circulating supply",
            since=f"Rank {pos} of the Top 100")
    if vol:
        share = f"{vol / mcap * 100:.1f}% of market cap" if mcap else "Traded in the last 24 hours"
        add("coin-volume", sb.fmt_usd(vol), window="Last 24 hours", since=share)
    if asset:
        sma200 = asset.get("sma200")
        if isinstance(sma200, (int, float)) and sma200 and price:
            dist = (price - sma200) / sma200 * 100
            add("coin-200d", signed_pct(dist, 1), window="Price against its 200-day average",
                direction=_dir(dist), since=f"200-day line {sb._price_fmt(sma200)}",
                source=f"{source}, daily closes")
        rsi = asset.get("rsi14")
        if isinstance(rsi, (int, float)):
            zone = "Oversold, under 30" if rsi < 30 else "Overbought, over 70" if rsi > 70 \
                else "Between 30 and 70"
            add("rsi-14", f"{rsi:.0f}", window="14 daily closes", since=zone,
                source=f"{source}, daily closes")
    return tile.grid(out, "tl-4 cn-tiles") if out else ""


def _dir(v):
    return "up" if v and v > 0 else "down" if v and v < 0 else None


# ---- the Chart Master's read on this coin ---------------------------------------------------

def _names(c):
    """The two words a read can name a coin by: its name and its ticker as a standalone word.
    The ticker alone is a shallow key (SOL in 'sold', OP in 'open'), so it counts only as a
    whole upper-case word and only beside the name rule below."""
    name, sym = (c.get("name") or "").strip(), (c.get("symbol") or "").strip()
    return name, sym


def coin_sentences(c, cm):
    """The sentences of the night's read that name this coin, in the order the read gave
    them. The name must appear as a whole word, or the ticker as a whole upper-case word."""
    name, sym = _names(c)
    if not name or not cm or cm.get("data_only"):
        return []
    rxs = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.I)]
    if sym:
        rxs.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(sym) + r"(?![A-Za-z0-9])"))
    try:
        import twins_gate
        split = twins_gate.sentences
    except Exception:
        split = lambda t: re.split(r"(?<=[.!?])\s+", t)
    out = []
    for p in (cm.get("paragraphs") or []):
        for s in split(str(p)):
            if any(rx.search(s) for rx in rxs):
                out.append(s.strip())
    # SPRINT 9.1 (8.3 item 2): a lifted sentence stands alone. One that opens on a
    # connective ("However, Doge ...") answers a sentence this card does not carry, so
    # as the card's FIRST sentence the connective comes off and the clause stands.
    if out:
        out[0] = lead_alone(out[0])
    return out


_LEAD = re.compile(r"^(?:however|but|yet|still|meanwhile|separately|additionally|moreover|"
                   r"furthermore|instead|conversely|nevertheless|nonetheless|likewise|similarly|"
                   r"also|even so|that said|by contrast|in contrast|on the other hand|"
                   r"in addition|at the same time)\s*,?\s+", re.I)


def lead_alone(sentence):
    """A sentence without a leading connective, first letter capitalised; unchanged when it
    has none."""
    m = _LEAD.match(sentence or "")
    if not m or not sentence[m.end():].strip():
        return sentence
    rest = sentence[m.end():]
    return rest[:1].upper() + rest[1:]


_WEEK_FIGURE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|percent)[^.]{0,40}\b(?:week|seven days|7 days|7-day|seven-day)\b|"
    r"\b(?:week|seven days|7 days|7-day|seven-day)\b[^.]{0,40}\d+(?:\.\d+)?\s*(?:%|percent))", re.I)


def has_week_figure(sentence):
    """True when a sentence states a percentage over a week or seven days. A coin page
    carries ONE seven-day figure, the readings tile's; a sentence that states another is not
    lifted onto it (Sprint 9.1, AUDIT.md 1.3 item 3)."""
    return bool(_WEEK_FIGURE.search(sentence or ""))


def chartmaster_card(c, cm, asset, today, esc, fmt_date, destyle=lambda t: t,
                     price_fmt=str, board_day=""):
    """The Chart Master card for one coin, always under a date.

    1. The coin's own read when the night's read names it: its sentences, in the order the
       read gave them, and no others, under the read's date.
    2. The levels card otherwise: price, 50-day, 200-day and RSI. When the night published
       the data-only card (7.2's last path) the row is the Chart Master's own for that coin
       and wears the read's date; when the night published prose that does not name the coin,
       the levels are the Board's and wear the Board's date, because that is where they came
       from.
    3. Nothing for a coin with neither, because nothing is invented.

    A read older than one day says how old it is above its text and is never presented as
    today's."""
    cm = cm or {}
    rday = str(cm.get("date") or "")[:10]
    name = c.get("name") or c.get("symbol") or ""
    sents = [x for x in coin_sentences(c, cm) if not has_week_figure(x)]
    row, day = None, rday
    if not sents:
        sym = (c.get("symbol") or "").upper()
        if cm.get("data_only"):
            row = next((r for r in (cm.get("levels") or [])
                        if str(r.get("symbol") or "").upper() == sym), None)
        elif asset:
            row, day = asset, str(board_day or "")[:10]
    elif not rday:
        return ""
    if not sents and not row:
        return ""
    try:
        age = (today - _dt.date.fromisoformat(day)).days
    except ValueError:
        return ""
    stale = (f'<p class="cn-cm-old">This is {age} days old; the readings above are newer.</p>'
             if age > 1 else "")
    if sents:
        body = " ".join(esc(destyle(s)) for s in sents[:3])
        return (f'<section class="cn-cm" aria-label="Chart Master\'s read on {esc(name)}">'
                f'<h2 class="cn-h">Chart Master\'s read on {esc(name)}, {esc(fmt_date(day))}</h2>'
                f'{stale}<p class="cn-cm-p">{body}</p>'
                f'<p class="cn-cm-f"><a href="/chartmaster.html">The whole read</a></p></section>')
    rows = []
    for k, lab in (("price", "Price"), ("sma50", "50-day average"), ("sma200", "200-day average")):
        if isinstance(row.get(k), (int, float)):
            rows.append((lab, price_fmt(row[k])))
    if isinstance(row.get("rsi14"), (int, float)):
        rows.append(("RSI (14)", f'{row["rsi14"]:.0f}'))
    if not rows:
        return ""
    cells = "".join(f'<div class="cn-lv"><span class="lab">{esc(k)}</span>'
                    f'<span class="cn-lvv">{esc(v)}</span></div>' for k, v in rows)
    return (f'<section class="cn-cm" aria-label="Chart Master\'s levels for {esc(name)}">'
            f'<h2 class="cn-h">Chart Master\'s levels for {esc(name)}, {esc(fmt_date(day))}</h2>'
            f'{stale}<p class="cn-cm-p">The latest read does not name {esc(name)}. '
            f'These are its levels.</p><div class="cn-lvs">{cells}</div>'
            f'<p class="cn-cm-f"><a href="/chartmaster.html">The whole read</a></p></section>')


# ---- the coin's stories ---------------------------------------------------------------------

# Names a wire line may use for a coin besides the one the Top 100 prints. "Ether" is what the
# desk's own wire lines call Ethereum, and the whole word is as specific as the name itself.
ALIASES = {"ETH": ("Ether",)}


def _matchers(c):
    name, sym = _names(c)
    if not name:
        return []
    rxs = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.I)]
    for a in ALIASES.get((sym or "").upper(), ()):
        rxs.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])", re.I))
    if sym:
        rxs.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(sym) + r"(?![A-Za-z0-9])"))
    return rxs


def names_coin(c, w):
    text = " ".join([w.get("line") or ""] + list(w.get("titles") or []))
    return any(rx.search(text) for rx in _matchers(c))


def wire_stories(c, wire):
    """The wire items that name this coin, newest first. The coin's NAME is the identity
    (whole word, any case); its ticker counts only as a whole upper-case word, the same
    floor the page's published-story match uses. Items the wire dropped are not here."""
    hits = [w for w in ((wire or {}).get("items") or []) if names_coin(c, w)]
    hits.sort(key=lambda w: w.get("reported_utc") or "", reverse=True)
    return hits


# ---- Why <coin> moved today (Program 8, Sprint 8.2) -----------------------------------------

TOP_N = 20              # the coins that get the block
WHY_HOURS = 24          # "today": reported within a day of the Board read the page carries


def cause_free(w):
    """False when the desk's one line carries a cause word (because, due to, driven by...) that
    none of its cited sources carries in a title. The desk never says "because" unless a
    cited source does (today.CAUSAL is the one list)."""
    import today as _today
    line = w.get("line") or ""
    titles = " ".join(w.get("titles") or [])
    for m in _today.CAUSAL.finditer(line):
        if not re.search(re.escape(m.group(0)), titles, re.I):
            return False
    return True


def vet(items, gate, name, surface):
    """The wire items that may print on a coin page: the desk's line carries no cause word its
    sources lack, and the line passes the twins gate (a sentence that fails is dropped, the rest
    of the line stands, an item left with nothing is out). Used for the Why block and the
    stories list alike: one rule for every line the page prints in the desk's voice."""
    out = []
    for w in items:
        if not cause_free(w):
            continue
        if gate is not None:
            kept = gate.text(w.get("line") or "", f"the {name} page, {surface}", dollars=True).strip()
            if not kept:
                continue
            w = dict(w, line=kept)
        out.append(w)
    return out


def why_items(c, pos, wire, stamp_utc, hours=WHY_HOURS):
    """The wire items that name the coin and were reported in the `hours` ending at the Board read
    the page carries (never after it: the number sits under that read), for the top 20 only; [] for every other coin."""
    if not pos or pos > TOP_N:
        return []
    try:
        end = _dt.datetime.fromisoformat(str(stamp_utc).replace("Z", "+00:00"))
    except ValueError:
        return []
    out = []
    for w in wire_stories(c, wire):
        try:
            t = _dt.datetime.fromisoformat(str(w.get("reported_utc") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if end - _dt.timedelta(hours=hours) <= t <= end:       # the 24 hours ending at the read
            out.append(w)
    return out


def why_block(c, pos, wire, stamp_utc, esc, stamp_et, move="", gate=None, graded=None):
    """(html, items): the "Why <coin> moved today" block and the items it shows. Nothing ('', [])
    when no item names the coin. Every sentence the block prints from the desk's own hand goes
    through the twins gate: the move line from the Board and each wire line. The block's own voice
    never says "because"; it says what moved and what was reported, and that the desk does not say
    one moved the other."""
    name = (c.get("name") or c.get("symbol") or "").strip()
    items = vet(why_items(c, pos, wire, stamp_utc), gate, name, "why it moved today")
    if not items:
        return "", []
    if move and gate is not None:
        move = gate.text(move, f"the {name} page, why it moved today", dollars=True).strip()
    mv = f'<p class="cn-why-m">{esc(move)}</p>' if move else ""
    html = (f'<section class="cn-why" aria-label="Why {esc(name)} moved today">'
            f'<h2 class="cn-h">Why {esc(name)} moved today</h2>{mv}'
            f'{stories_html(items, esc, stamp_et)}'
            f'<p class="pc-note">These reports name {esc(name)}. '
            # Sprint 9.3, review 1: with a graded verdict on the page, the note points at it instead of
            # denying a cause the verdict may state
            + ("The verdict above grades what lines up with the move. " if graded else
               "The desk does not say any of them moved its price. ")
            + 'Wire lines are the desk\'s one-line summaries of what outlets '
            f'reported, with the sources counted and linked.</p></section>')
    return html, items


def stories_html(hits, esc, stamp_et):
    """Each wire item: the desk's one line, then its sources as links with the count and the
    time it was reported. 'Primary source' is printed when the wire marked it."""
    rows = []
    for w in hits:
        # AN OUTLET IS LISTED, AND COUNTED, ONCE (Sprint 9.1, 8.3 item 3): "2 sources: Decrypt,
        # Decrypt, Bitcoin Magazine" named one outlet twice beside a count of two. Two links to the
        # same outlet are one source; the first link stands for it.
        seen, links = set(), []
        for l in (w.get("links") or []):
            key = re.sub(r"[^a-z0-9]+", "", str(l.get("outlet") or l.get("url") or "").lower())
            if key and key not in seen:
                seen.add(key)
                links.append(l)
        srcs = ", ".join(
            f'<a href="{esc(l["url"])}" rel="noopener">{esc(l.get("outlet") or "Source")}</a>'
            for l in links if l.get("url"))
        n = len(links) if links else int(w.get("source_count") or 0)
        bits = [f'{n} source{"" if n == 1 else "s"}' + (f': {srcs}' if srcs else "")]
        if w.get("primary"):
            bits.append('<span class="wl-primary">Primary source</span>')
        st = stamp_et(w.get("reported_utc"))
        if st:
            bits.append(f'<span class="bd-stamp">{esc(st)}</span>')
        rows.append(f'<li class="cn-wi"><p class="cn-wl">{esc(w.get("line") or "")}</p>'
                    f'<p class="cn-wm">{" &middot; ".join(bits)}</p></li>')
    return f'<ul class="cn-wire">{"".join(rows)}</ul>' if rows else ""


# ---- the unlock line ------------------------------------------------------------------------

def unlock_line(c, today, esc, fmt_short_date, path=UNLOCKS):
    """The coin's next token unlock, from the hand-kept file, only where the file has one with
    a date on or after today and a source. Its source and the date the desk read it are on the
    line. '' for every coin without that: nothing is printed for a coin without data."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    gid = (c.get("gecko_id") or "").strip()
    sym = (c.get("symbol") or "").strip().upper()
    for p in d.get("projects") or []:
        if not ((gid and p.get("gecko_id") == gid) or (not gid and p.get("symbol") == sym)):
            continue
        u = p.get("next_unlock") or {}
        if not (u.get("date") and u["date"] >= today.isoformat() and p.get("source_url")):
            return ""
        bits = [f'Next unlock: {esc(fmt_short_date(u["date"]))}']
        if u.get("amount"):
            bits.append(esc(str(u["amount"])))
        if u.get("share"):
            bits.append(f'{esc(str(u["share"]))} of supply')
        if u.get("computed_from"):
            bits.append("computed from the project's stated schedule")
        read = p.get("read_date") or d.get("read_date") or ""
        return (f'<p class="cn-unlock">{", ".join(bits)}. Source: '
                f'<a href="{esc(p["source_url"])}" rel="noopener">the project\'s own page</a>'
                f'{", read " + esc(fmt_short_date(read)) if read else ""}.</p>')
    return ""
