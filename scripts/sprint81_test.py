#!/usr/bin/env python3
"""Program 8, Sprint 8.1 (14 October 2026): the small items.

  1. the morning re-ranks the wire and stamps "Moving the market" with its own time
  2. a price under $0.0001 prints with compressed zeros at normal size; its label reads in full
  3. the cadence line is Jack's words of 14 October

  python3 scripts/sprint81_test.py       # prints every case; exit 1 on any failure
(The Whale Watch width is a browser test: scripts/sprint81_browser.mjs.)
"""
import copy
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def item1():
    print("1. the morning re-ranks the wire and stamps it with its own time")
    import home as h
    import wire as w
    wire = json.load(open(os.path.join(HERE, "fixtures", "home", "wire.json"), encoding="utf-8"))
    # Tuesday's evening ranking, as the Edition wrote it
    wire = dict(wire, ranked_utc="2026-10-13T23:14:25Z", ranked_et="7:14 PM ET on Oct 13",
                refreshed_utc="2026-10-13T23:14:25Z", refreshed_et="7:14 PM ET on Oct 13", refreshes=0)
    now = dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc)
    evening = text(h.wire_top(wire, "", now))
    check("Ranked 7:14 PM ET on Oct 13" in evening, "the evening ranking is stamped by its own time")
    # the morning run: wire.refresh() re-counts against fresh clusters and re-orders
    last = wire["items"][-1]
    clusters = [{"url": last["links"][0]["url"], "source": "A", "headline": (last.get("titles") or [last["line"]])[0],
                 "corroboration": [{"url": f"https://example.com/{i}", "name": f"Outlet{i}",
                                    "headline": (last.get("titles") or [last["line"]])[0]} for i in range(9)]}]
    new = w.refresh(wire, clusters, "2026-10-14T12:18:00Z")
    check(new["items"][0]["id"] == last["id"], "the morning's refresh re-orders: the best-corroborated item leads")
    morning = text(h.wire_top(new, "", now))
    print("   ", morning[-160:])
    check("8:18 AM ET on Oct 14" in morning, "'Moving the market' carries the morning's own time, 8:18 AM ET")
    check(not re.search(r"(?<!irst )Ranked 7:14 PM ET on Oct 13", morning),
          "last night's time is not the stamp the morning prints")
    check("Re-ranked 8:18 AM ET on Oct 14" in morning, "the stamp says Re-ranked, with the time")
    # no refresh happened (feeds down): the stamp stays honest
    check("Re-ranked" not in text(h.wire_top(wire, "", now)), "no re-rank, no 'Re-ranked'")


def item2():
    print("2. small prices: compressed zeros at normal size")
    import site_build as sb
    check(sb._price_fmt(0.0000003682) == "$0.0₆3682", f"BTT: {sb._price_fmt(0.0000003682)!r} is $0.0₆3682")
    check(sb._price_fmt(0.00009) == "$0.0₄9", f"$0.00009: {sb._price_fmt(0.00009)!r} is $0.0₄9")
    check(sb._price_fmt(0.000099999) == "$0.0001000", f"rounding up out of the tier: {sb._price_fmt(0.000099999)!r}")
    check(sb._price_fmt(0.00009999) == "$0.0\u20849999", f"four digits kept: {sb._price_fmt(0.00009999)!r}")
    check(sb._price_fmt(0.0001234) == "$0.0001234", "$0.0001234 keeps fixed notation")
    check(sb._price_fmt(0.5) == "$0.5000" and sb._price_fmt(103.5) == "$103.50", "ordinary prices are unchanged")
    check(sb._price_label(0.0000003682) == "0.0000003682 dollars", f"label: {sb._price_label(0.0000003682)!r}")
    check(sb._price_label(0.00009) == "0.00009 dollars", f"label: {sb._price_label(0.00009)!r}")
    import top100_fixture_rows as fx
    row = fx.rows()["price"]
    check('aria-label="0.0000003682 dollars"' in row, "the BTT-class row's price cell reads the full number")
    check("$0.0₆3682" in row, "the row prints the compressed form")
    check("pn-xlong" not in row, "the row carries no 10 px tier")
    css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read()
    check("pn-xlong" not in css and not re.search(r"pnum[^{]*\{[^}]*font-size:\s*10px", css),
          "site.css has no 10 px price tier")
    check(sb._price_class("$0.0₆3682") == "", "a compressed price needs no size step")


def item3():
    print("3. the cadence line")
    import site_build as sb
    check(sb.NEWS_CADENCE_LINE == "The Brief, every morning and evening.", f"cadence: {sb.NEWS_CADENCE_LINE!r}")
    check(not re.search(r"[–—]", sb.NEWS_CADENCE_LINE), "no dash in it")


def main():
    for f in (item1, item2, item3):
        try:
            f()
        except Exception as e:
            check(False, f"{f.__name__} raised {type(e).__name__}: {e}")
    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
