#!/usr/bin/env python3
"""
lastmod.py: the sitemap's real change times (Program 8, Sprint 8.2, item 4).

A sitemap's <lastmod> is when the page last changed, and a crawler that finds it equal to the
build time on every page learns to ignore it. The build time is never used here. A page's change
time is the newest moment something ON it was made:

  an article        when it was published (or its date at midnight UTC)
  a coin page       the newest of the Board read the page carries and the wire items it shows
  a board page      the Board read the page carries
  a page with no known change time carries none; absent is honest, a guess is not.
"""


def _latest(*stamps):
    s = [x for x in stamps if x]
    return max(s) if s else ""


def article(item):
    raw = (item or {}).get("published_utc") or ""
    if raw:
        return raw
    d = (item or {}).get("date") or ""
    return d[:10] + "T00:00:00Z" if d else ""


def coin(board_utc, wire_hits):
    """A coin page: its Board read and the wire items shown on it. '' with neither."""
    return _latest(board_utc, *[w.get("reported_utc") for w in wire_hits or []])


def board(board_utc):
    return board_utc or ""
