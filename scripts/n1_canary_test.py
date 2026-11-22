#!/usr/bin/env python3
"""N-1 (November 22, 2026): the offline canary stops reading the day's stored wire as a wiring fault.

From November 13 every Brief, morning read and watcher run died at the offline canary, before the slot guard and before any
model call, on two cases that scan the news feed built from the STORED wire (site/data/wire.json) for an AI word:

  sprint 9.7  "no feed has a dash; none but the coin identity feeds ... has an AI word"
  hotfix 9.9h "the news feed built from the stored wire passes the AI-word scan"

The stored wire of 6:13 PM ET November 12 carries the desk's own line on a reported subject: "... disrupts FaceStealer
deepfake scheme that used AI to steal $400M in crypto." Its one stored title carries no AI word, so the J-20 excuse does not
reach it. The wire is rotated only by the Brief, and the canary in front of the Brief read the wire, so the desk stayed dark.
This is the fourth episode of one class in thirty days (October 23, October 29, November 9, November 13): a hard gate that
proves wiring, failing on the day's data.

The rule, unchanged for every line the canary makes or plants: an AI word fails unless a source title carries it, and any
disclosure phrasing always fails. The one change: a line that is VERBATIM a line of the stored live wire and carries no
disclosure phrasing is a reading of yesterday's published data, not a wiring fault. The canary names it as a warning and
the run goes on, so the Brief can rotate the wire. Fixture: fixtures/n1/wire-2026-11-12.json is the stored wire as main held
it at c2e4c30, byte for byte.

  python3 scripts/n1_canary_test.py      # exit 1 on any failure
NO MODEL CALL and no network.
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc
FACESTEALER = ("DOJ wins court order to seize $1.2B from North Korea's Binance hack; disrupts FaceStealer deepfake scheme "
               "that used AI to steal $400M in crypto.")


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:120]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def unit():
    fails = []
    print("N-1. the stored wire's own reported line is a warning, never a wiring fault")
    import api_feeds
    import sprint97_test as s97
    wire = json.load(open(os.path.join(HERE, "fixtures", "n1", "wire-2026-11-12.json"), encoding="utf-8"))
    now = dt.datetime(2026, 11, 13, 0, 40, tzinfo=UTC)
    news = api_feeds.news_feed(wire, now)
    live = s97.wire_lines(wire)
    guarded(fails, "the premise: the November 12 wire carries the FaceStealer line and the plain scan finds its AI word",
            lambda: FACESTEALER in live and s97.AI.search(s97.feed_prose(news, titles={})))
    guarded(fails, "the canary's scan passes the November 12 news feed when that wire is the stored one",
            lambda: not s97.hard_ai_hits(news, live, titles={}))
    guarded(fails, "and names the line it let through, so the run can say so",
            lambda: s97.reported_ai_lines(news, live) == [FACESTEALER])
    guarded(fails, "the same line NOT in the stored wire still fails (a line the pipeline makes today is still scanned)",
            lambda: s97.hard_ai_hits(news, set(), titles={}))
    plant = json.loads(json.dumps(wire))
    plant["items"][0]["line"] = "Ranked first by the desk's AI editor: Luxor raised $16 million."
    pnews = api_feeds.news_feed(plant, now)
    guarded(fails, "a disclosure that IS a stored wire line still fails",
            lambda: s97.hard_ai_hits(pnews, s97.wire_lines(plant), titles={}))
    guarded(fails, "the dash scan is untouched: a dash in a stored wire line still fails",
            lambda: s97.DASH.search(json.dumps(api_feeds.news_feed(
                dict(wire, items=[dict(wire["items"][0], line="Bitcoin " + chr(0x2014) + " up")]), now), ensure_ascii=False)))
    return fails


def main():
    fails = unit()
    print(f"\nN-1 canary: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
