#!/usr/bin/env python3
"""
calendar_check.py: the desk should never be surprised by a date it already knew (audit
item 5, 2026-07-28). The Zcash Ironwood upgrade activated on a published, weeks-known
schedule while the desk's protocol-upgrade beat looked the other way, because nothing
checked the calendar against what had actually been covered.

One file, data/week_calendar.json, read every run. For each event now due (activated or
reported today or in the last few days), this asks a dumb, deterministic question: does the
desk's own published corpus contain a story matching this event's terms? If not, the event
is an UNCOVERED KNOWN EVENT and gets flagged.

Advisory by design, never a gate: it warns, writes out/calendar_gaps.json for the editor,
and always exits 0. A missed story is a coverage judgment for a human, not a reason to
block a publish. The flag is loud enough to act on and cheap enough to ignore when the desk
decided the event was not worth covering.

USAGE  python3 calendar_check.py [--days-back N] [--days-ahead N]
"""

import datetime
import glob
import json
import os
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
CALENDAR = os.path.join(HERE, "data", "week_calendar.json")
FEDREG = os.path.join(HERE, "data", "fedreg_calendar.json")
CONTENT = os.path.join(HERE, "site", "content")

DAYS_BACK = 3    # an event stays "due" for a few days; the desk gets more than one slot
DAYS_AHEAD = 0   # only events that have actually happened count as uncovered


def _corpus(within_days=14):
    """(publication date, lowercased text) for the desk's recent stories."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=within_days)).isoformat()
    out = []
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("example") or (d.get("date", "") < cutoff):
            continue
        body = d.get("body") or []
        body = body if isinstance(body, list) else [str(body)]
        out.append((d.get("date", ""),
                    " ".join([str(d.get("title", "")), str(d.get("dek", "")),
                              str(d.get("key_fact", ""))] + [str(b) for b in body]).lower()))
    return out


def gaps(days_back=DAYS_BACK, days_ahead=DAYS_AHEAD, today=None):
    """Events that are due and carry no matching story in the desk's recent corpus."""
    today = today or datetime.date.today()
    # TWO calendars: the curated one, and the one fedreg.py generates from the Federal
    # Register. Both are checked here because an uncovered federal rule is the same kind of
    # miss as an uncovered scheduled event. Note that week_ahead.py reads ONLY the curated
    # file: this check is editor-facing, the Week Ahead is reader-facing, and machine-
    # selected entries do not belong in published copy without review. See fedreg.py.
    events = []
    for path, label in ((CALENDAR, "calendar"), (FEDREG, "federal register calendar")):
        try:
            events += (json.load(open(path, encoding="utf-8")) or {}).get("events") or []
        except FileNotFoundError:
            pass  # fedreg has simply not run yet; the curated calendar still checks
        except Exception as e:
            common.gh("warning", f"calendar_check: {label} unreadable ({e})")
    if not events:
        return []
    cal = {"events": events}
    lo = (today - datetime.timedelta(days=days_back)).isoformat()
    hi = (today + datetime.timedelta(days=days_ahead)).isoformat()
    corpus = _corpus()
    out = []
    for e in cal.get("events", []):
        if not (lo <= e.get("date", "") <= hi):
            continue
        groups = [[t.lower() for t in grp if t] for grp in (e.get("match") or []) if grp]
        if not groups:
            continue
        # Covered when ONE story dated on or after the event carries EVERY term of ANY
        # group. Two rules, both learned the hard way on the Zcash case:
        #   - groups are AND-sets, so a bare entity name cannot claim coverage (an old
        #     Zcash story is not coverage of the Ironwood upgrade);
        #   - the story must not PREDATE the event. The desk's 2026-07-19 Zcash piece named
        #     the Ironwood activation date in passing, nine days early. Knowing a date in
        #     advance is not covering the thing when it happens.
        when = e.get("date", "")
        if any(all(t in story for t in grp)
               for date, story in corpus if date >= when for grp in groups):
            continue
        out.append(e)
    return out


def main():
    argv = sys.argv[1:]

    def opt(name, default):
        return int(argv[argv.index(name) + 1]) if name in argv else default

    missed = gaps(opt("--days-back", DAYS_BACK), opt("--days-ahead", DAYS_AHEAD))
    common.write_out("calendar_gaps.json",
                     {"checked_utc": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "uncovered": missed})
    if not missed:
        print("calendar_check: every event now due has coverage on the desk.")
        return 0
    for e in missed:
        common.gh("warning",
                  f"calendar_check: UNCOVERED KNOWN EVENT ({e.get('kind')}) "
                  f"{e.get('date')}: {e.get('title')}. The desk has published nothing "
                  f"matching {e.get('match')}. Source: {e.get('source', 'n/a')}")
    print(f"calendar_check: {len(missed)} known event(s) due with no coverage "
          f"-> out/calendar_gaps.json (advisory; the editor decides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
