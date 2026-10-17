#!/usr/bin/env python3
"""
tile.py: the one tile (Program 5, section 7; Sprint 2 item 0).

Every tile on the site is drawn by `render()` and by nothing else, and the five rules of
Tile.dc.html are enforced here, where a tile is made, rather than hoped for in each caller:

  1. The label in plain words.
  2. The figure in the mono, colored ONLY when direction means something. Whether it does
     is a property of the reading (READINGS[key].directional), never of the caller: a
     funding rate or a Fear & Greed figure printed in green says "good" about a number
     that has no good direction.
  3. The window written on the tile.
  4. The since-yesterday line in words.
  5. The source and the stamp with its zone on the tile, with "what this means" opening
     the Learn page at that reading's anchor.

No icons, no gradients, no persona art, no explainer paragraph under a tile. A tile that
breaks a rule is not drawn wrong: it raises TileError, and the build names the tile.

The Learn page's anchors are READINGS, so a reading a tile can show and the anchor its
"what this means" opens are one table. Funding's calm, warm and hot are narrative.py's
FUNDING_BANDS and Fear & Greed's bands are site_build.FNG_WORD_BANDS; the Learn page prints
both from those tables, so the words on a tile, the narrative line and the Learn page
cannot disagree.
"""

import re

LEARN_PAGE = "/learn.html"


class TileError(ValueError):
    """A tile that breaks one of the five rules."""


class Reading:
    __slots__ = ("key", "name", "directional", "what")

    def __init__(self, key, name, directional, what):
        self.key, self.name, self.directional, self.what = key, name, directional, what


# Every reading a tile can show, in Board order. `directional`: does up or down mean
# something a reader can act on? Price, the whole market's cap, money in or out of the
# ETFs and coins on or off the exchanges do; a funding rate, open interest, the float,
# a sentiment index and a fee do not, so they print in ink.
READINGS = {r.key: r for r in (
    Reading("bitcoin", "Bitcoin", True,
            "Bitcoin's price in US dollars, its 24-hour change and where it sits against "
            "its 200-day average."),
    Reading("total-cap", "Whole market", True,
            "Every coin's market value added together, and Bitcoin's share of it "
            "(dominance)."),
    Reading("etf-net", "Spot ETF net", True,
            "Dollars that went into US spot Bitcoin ETFs, less dollars that came out, for "
            "one trading day."),
    Reading("whale-net", "Whale net", True,
            "Transfers of $50 million and up between wallets and exchanges, netted: off "
            "exchanges is positive, onto exchanges is negative."),
    Reading("stablecoin-float", "Stablecoin float", False,
            "The dollar value of every stablecoin in circulation, read now: money "
            "parked inside crypto."),
    Reading("funding", "Funding", False,
            "What traders holding leveraged long positions pay short holders every 8 "
            "hours on Bitcoin perpetual futures. The tile gives the current 8-hour "
            "period's rate and, under it, the rate at the settlement 24 hours before the "
            "latest. The Leverage tile on the Board is the same rate times 1,095, the "
            "number of 8-hour periods in a year."),
    Reading("open-interest", "Open interest", False,
            "The value of leveraged Bitcoin futures positions open right now on one "
            "venue. When a close is kept for yesterday, the tile's figure is the change "
            "since that close across the five coins the desk tracks on that venue, and "
            "the line under it is Bitcoin's open interest now."),
    Reading("fear-greed", "Fear & Greed", False,
            "A daily index from 0 to 100 built from price, volatility, volume and social "
            "data."),
    # Program 7 Sprint 6.4 (13 October 2026): the coin page's readings grid. Price, cap,
    # volume and RSI have no good direction; a change and the distance from the 200-day
    # line do, and each is colored by its own sign only.
    Reading("coin-price", "Price", False,
            "The coin's last price in US dollars, from the Top 100 read the Board was "
            "built on."),
    Reading("coin-24h", "24 hours", True,
            "How far the coin's price moved over the last 24 hours, in percent."),
    Reading("coin-7d", "7 days", True,
            "How far the coin's price moved over the last seven days, in percent."),
    Reading("coin-cap", "Market cap", False,
            "Price times circulating supply: the market's total bet on the coin, and the "
            "basis of its rank."),
    Reading("coin-volume", "24-hour volume", False,
            "Dollars of the coin traded across the exchanges CoinGecko reads, over the last "
            "24 hours."),
    Reading("coin-200d", "Against 200-day", True,
            "How far the price sits above or below its 200-day average, in percent. Only "
            "the coins the Board tracks have one."),
    Reading("rsi-14", "RSI (14)", False,
            "A 0 to 100 reading of recent daily closes. Under 30 is called oversold and "
            "over 70 overbought; between is neither."),
    Reading("network-fee", "Network fees", False,
            "What it costs to get a Bitcoin transaction into the next block, in satoshis "
            "per virtual byte."),
)}

_ZONE = re.compile(r"\b(ET|UTC)\b")
# What a tile may never carry. Checked on the tile's own markup.
_FORBIDDEN = re.compile(r"<(svg|img|picture|i)\b|gradient|class=\"[^\"]*\bicon\b", re.I)


def anchor(key):
    return f"{LEARN_PAGE}#{key}"


def _e(s):
    """The site's own escape (site_build.esc): &, <, > and the double quote."""
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


ARROW = {"up": "\u25b2", "down": "\u25bc"}
_SINCE_CHG = re.compile(r"\b(Up|Down) (\d[\d,]*(?:\.\d+)?%)")


def _sign(v):
    if not isinstance(v, (int, float)) or v == 0:
        return ""
    return "up" if v > 0 else "down"


def render(key, figure, *, window, since, source, stamp, label=None, direction=None,
           change=None, since_change=None):
    """One tile. `key` names its reading (READINGS); `direction` is "up", "down" or None
    and colors the figure only when the reading is directional. Every argument a rule
    needs is required and checked; a missing one raises TileError naming the tile.

    COLOR TRUTH (Jack, 12 October 2026): a figure's color and arrow come from the change
    printed WITH it, in the same window. `change` is that change: it prints beside the
    figure with its arrow, and the figure's color is its sign, so a caller cannot color
    a figure one way beside a number that says the other (a `direction` that disagrees
    raises). `since_change` is the since-yesterday line's own change, a different window:
    it gets its own small arrow and color on that line and never colors the figure."""
    r = READINGS.get(key)
    name = label or (r.name if r else key)
    if r is None:
        raise TileError(f"tile {name!r}: no Learn anchor for reading {key!r}")
    if figure is None or not str(figure).strip():
        raise TileError(f"tile {name!r}: no figure")
    if not str(window or "").strip():
        raise TileError(f"tile {name!r}: no window written on the tile")
    if not str(since or "").strip():
        raise TileError(f"tile {name!r}: no since-yesterday line")
    if not str(source or "").strip():
        raise TileError(f"tile {name!r}: no source")
    if not _ZONE.search(str(stamp or "")):
        raise TileError(f"tile {name!r}: no stamp with its zone ({stamp!r})")
    badge = ""
    if change is not None:
        own = _sign(change)
        if direction in ("up", "down") and direction != own:
            raise TileError(f"tile {name!r}: colored {direction} beside its own change "
                            f"{change:+.2f}%")
        direction = own
        badge = (f' <span class="tl-c chg {own or "flat"}">'
                 f'{ARROW.get(own, "")}{" " if own else ""}{abs(change):.2f}%</span>')
    cls = ""
    if r.directional and direction in ("up", "down"):
        cls = f" {direction}"
    since_h = _e(since)
    sd = _sign(since_change)
    if sd:
        since_h = _SINCE_CHG.sub(
            lambda m: (f'<span class="chg {sd}">{ARROW[sd]} {m.group(1)} {m.group(2)}</span>'
                       if (m.group(1) == "Up") == (sd == "up") else m.group(0)),
            since_h, count=1)
    try:
        import snapshot as _sn
        _asof = _sn.asof_attr(_sn.ts_for_stamp(stamp))
    except Exception:                                   # pragma: no cover
        _asof = ""
    out = (f'<article class="tl" data-reading="{_e(key)}"{_asof}>'
           f'<h3 class="tl-l">{_e(name)}</h3>'
           f'<p class="tl-f{cls}">{_e(figure)}{badge}</p>'
           f'<p class="tl-w">{_e(window)}</p>'
           f'<p class="tl-s">{since_h}</p>'
           f'<p class="tl-src">{_e(source)} &middot; {_e(stamp)} &middot; '
           f'<a href="{_e(anchor(key))}">what this means</a></p>'
           f'</article>')
    if _FORBIDDEN.search(out):
        raise TileError(f"tile {name!r}: an icon or a gradient")
    return out


def card(key, figure, line, *, label=None, direction=None):
    """THE SMALL CARD (Program 7, Sprint 7.1, the home page's money): the label, which
    opens the Learn anchor, the figure in the mono, colored only when the reading is
    directional (the same rule as a tile), and one line of window or source."""
    r = READINGS.get(key)
    name = label or (r.name if r else key)
    if r is None:
        raise TileError(f"card {name!r}: no Learn anchor for reading {key!r}")
    if figure is None or not str(figure).strip():
        raise TileError(f"card {name!r}: no figure")
    if not str(line or "").strip():
        raise TileError(f"card {name!r}: no line of window or source")
    cls = f" {direction}" if r.directional and direction in ("up", "down") else ""
    return (f'<article class="tl tl-card" data-reading="{_e(key)}">'
            f'<h3 class="tl-l"><a href="{_e(anchor(key))}">{_e(name)}</a></h3>'
            f'<p class="tl-f{cls}">{_e(figure)}</p>'
            f'<p class="tl-w">{_e(line)}</p></article>')


def grid(tiles, cls=""):
    """Tiles in a row. `tiles` are already-rendered strings."""
    tiles = [t for t in tiles if t]
    if not tiles:
        return ""
    extra = f" {cls}" if cls else ""
    return f'<div class="tl-row{extra}">{"".join(tiles)}</div>'


# ---- the Learn page's anchors ---------------------------------------------------------------

def _pct(v):
    return f"{v:.3f}"


def funding_thresholds():
    """[(word, low, high)] from narrative.FUNDING_BANDS, per 8 hours, absolute value."""
    import narrative
    out, lo = [], 0.0
    for top, word in narrative.FUNDING_BANDS:
        out.append((word, lo, None if top == float("inf") else top))
        lo = top
    return out


def fng_thresholds():
    """[(word, low, high)] inclusive, from site_build.FNG_WORD_BANDS."""
    import site_build
    out, lo = [], 0
    for top, word in site_build.FNG_WORD_BANDS:
        out.append((word, lo, top))
        lo = top + 1
    return out


def learn_readings(explainer_href=None):
    """The block the Learn page carries: one anchored entry per reading, and the two
    threshold tables. `explainer_href(key)` gives the long explainer for a reading."""
    rows = []
    for key, r in READINGS.items():
        extra = ""
        if key == "funding":
            lis = []
            for word, lo, hi in funding_thresholds():
                if hi is None:
                    rng = f"{_pct(lo)}% or more"
                elif lo == 0:
                    rng = f"under {_pct(hi)}%"
                else:
                    rng = f"{_pct(lo)}% to under {_pct(hi)}%"
                lis.append(f'<li data-band="{_e(word)}"><b>{_e(word.capitalize())}</b> '
                           f'<span class="lr-t">{_e(rng)}</span></li>')
            extra = ('<p class="lr-k">Per 8 hours, either sign. The word on the funding '
                     'tile and in the narrative line comes from this table.</p>'
                     f'<ul class="lr-b">{"".join(lis)}</ul>')
        elif key == "fear-greed":
            lis = [f'<li data-band="{_e(w)}"><b>{_e(w)}</b> '
                   f'<span class="lr-t">{lo} to {hi}</span></li>'
                   for w, lo, hi in fng_thresholds()]
            extra = ('<p class="lr-k">The word on the Fear &amp; Greed tile and in the '
                     'narrative line comes from this table.</p>'
                     f'<ul class="lr-b">{"".join(lis)}</ul>')
        more = ""
        href = explainer_href(key) if explainer_href else ""
        if href:
            more = f' <a href="{_e(href)}">The full explainer</a>'
        rows.append(f'<section class="lr" id="{_e(key)}"><h3>{_e(r.name)}</h3>'
                    f'<p>{_e(r.what)}{more}</p>{extra}</section>')
    return ('<section class="bd-mod lr-all" aria-labelledby="lr-h">'
            '<div class="bd-sec"><div class="bd-sec-l">'
            '<span class="bd-eyebrow">What this means</span>'
            '<h2 class="bd-h2" id="lr-h">Every reading a tile can show</h2></div></div>'
            f'{"".join(rows)}</section>')
