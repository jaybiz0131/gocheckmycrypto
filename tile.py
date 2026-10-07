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

import html
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
            "The dollar value of every stablecoin in circulation: money parked inside "
            "crypto."),
    Reading("funding", "Funding", False,
            "What traders holding leveraged long positions pay short holders every 8 "
            "hours on Bitcoin perpetual futures."),
    Reading("open-interest", "Open interest", False,
            "The value of leveraged Bitcoin futures positions open right now on one "
            "venue."),
    Reading("fear-greed", "Fear & Greed", False,
            "A daily index from 0 to 100 built from price, volatility, volume and social "
            "data."),
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
    return html.escape(str(s), quote=True)


def render(key, figure, *, window, since, source, stamp, label=None, direction=None):
    """One tile. `key` names its reading (READINGS); `direction` is "up", "down" or None
    and colors the figure only when the reading is directional. Every argument a rule
    needs is required and checked; a missing one raises TileError naming the tile."""
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
    cls = ""
    if r.directional and direction in ("up", "down"):
        cls = f" {direction}"
    out = (f'<article class="tl" data-reading="{_e(key)}">'
           f'<h3 class="tl-l">{_e(name)}</h3>'
           f'<p class="tl-f{cls}">{_e(figure)}</p>'
           f'<p class="tl-w">{_e(window)}</p>'
           f'<p class="tl-s">{_e(since)}</p>'
           f'<p class="tl-src">{_e(source)} &middot; {_e(stamp)} &middot; '
           f'<a href="{_e(anchor(key))}">what this means</a></p>'
           f'</article>')
    if _FORBIDDEN.search(out):
        raise TileError(f"tile {name!r}: an icon or a gradient")
    return out


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
