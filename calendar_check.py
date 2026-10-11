#!/usr/bin/env python3
"""
calendar_check.py: the desk should never be surprised by a date it already knew (audit
item 5, 2026-07-28). The Zcash Ironwood upgrade activated on a published, weeks-known
schedule while the desk's protocol-upgrade beat looked the other way, because nothing
checked the calendar against what had actually been covered.

One file, site/data/calendar.json (desk_calendar.py's, retired data/week_calendar.json
on 11 October 2026), read every run. For each event now due (activated or
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
import re
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
CALENDAR = os.path.join(HERE, "site", "data", "calendar.json")
FEDREG = os.path.join(HERE, "data", "fedreg_calendar.json")
CONTENT = os.path.join(HERE, "site", "content")

DAYS_BACK = 3    # an event stays "due" for a few days; the desk gets more than one slot
DAYS_AHEAD = 0   # only events that have actually happened count as uncovered
STALE_DAYS = 3   # a calendar whose own generated stamp is older than this was not rebuilt


def _events_of(doc):
    """Events from either file: calendar.json's `entries` or fedreg's `events`."""
    doc = doc or {}
    return doc.get("entries") or doc.get("events") or []


# calendar.json's kinds that carry a coverage duty, and the term that proves coverage. A
# difficulty retarget, an options expiry or a market holiday is a calendar line, not a story
# the desk owes; a macro release or an FOMC decision is. Derived here, not stored on the
# entry, so desk_calendar.py's schema (date, title, kind, source, read stamp) is unchanged.
def _match_for(e):
    if e.get("match"):
        return e["match"]
    kind, title = e.get("kind"), str(e.get("title", ""))
    if kind == "fomc":
        return [["fomc"], ["federal reserve", "rate decision"]] if "concludes" in title.lower() else []
    if kind == "macro":
        head = title.split(":")[0].strip().lower()
        return [[head]] if head else []
    return []


def staleness_days(today=None):
    """Days since calendar.json was last generated (its own generated_utc), or None when
    the file is unreadable or carries no stamp. Deterministic. WHY (2026-08-31, reworked
    2026-10-11): the old curated calendar's newest entry sat at 2026-07-30 while Jackson Hole
    came and went unflagged. calendar.json is rebuilt every brief run from its five sources,
    so the clock that matters is when it was last built, not the date of its newest entry."""
    today = today or datetime.date.today()
    try:
        gen = str((json.load(open(CALENDAR, encoding="utf-8")) or {}).get("generated_utc", ""))
        return (today - datetime.date.fromisoformat(gen[:10])).days
    except Exception:
        return None


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
        # Headline fields ONLY, deliberately not the body (2026-08-02): a story ABOUT an
        # event names it in the title, dek, or key fact. Body-wide matching let the
        # Coinbase earnings story claim coverage of Strategy's Q2 because its body used
        # the common noun "strategy" near "earnings", and the desk's promised event
        # sailed by marked covered. An event genuinely handled inside a broader story
        # now fires the duty anyway, and the editor's stated pass ("covered within X")
        # is the honest, logged answer.
        out.append((d.get("date", ""),
                    " ".join([str(d.get("title", "")), str(d.get("dek", "")),
                              str(d.get("key_fact", ""))]).lower()))
    return out


def gaps(days_back=DAYS_BACK, days_ahead=DAYS_AHEAD, today=None):
    """Events that are due and carry no matching story in the desk's recent corpus."""
    today = today or datetime.date.today()
    # TWO calendars: calendar.json, and the one fedreg.py generates from the Federal
    # Register. Both are checked here because an uncovered federal rule is the same kind of
    # miss as an uncovered scheduled event. Note that week_ahead.py reads ONLY calendar.json:
    # this check is editor-facing, the Week Ahead is reader-facing, and machine-selected
    # entries do not belong in published copy without review. See fedreg.py.
    events = []
    for path, label in ((CALENDAR, "calendar"), (FEDREG, "federal register calendar")):
        try:
            events += _events_of(json.load(open(path, encoding="utf-8")))
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
        groups = [[t.lower() for t in grp if t] for grp in _match_for(e) if grp]
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

    stale = staleness_days()
    if stale is not None and stale > STALE_DAYS:
        common.gh("warning",
                  f"calendar_check: site/data/calendar.json was last generated {stale} "
                  f"days ago. A calendar nobody rebuilds can flag nothing; desk_calendar.py "
                  f"writes it on every brief run.")

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
