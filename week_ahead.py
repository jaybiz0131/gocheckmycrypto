#!/usr/bin/env python3
"""
week_ahead.py: the Monday Week Ahead story (audit item 2, 2026-07-27). The audit's biggest
coverage gap was the missing consensus forward story (FOMC Wednesday, Coinbase and Strategy
earnings). This adds it as a CALENDAR-DRIVEN story type: report what is scheduled and what
observers are watching, never what will happen.

THE NO-FORECAST LAW IS ENFORCED BY CONSTRUCTION: no model writes here. The story renders
deterministically from data/week_calendar.json, a curated static file of publicly announced
dates, each entry carrying its source. "The Fed meets Wednesday" is reporting; "expect
volatility" is a forecast and cannot occur because no sentence exists that the calendar
file does not supply. Same event-calendar pattern as the Sports desk.

BEHAVIOR
  - Runs every brief slot, publishes only on Monday (UTC), only once per week (id
    week-ahead-<monday>), and only if the week actually has calendar events. Empty week or
    non-Monday: clean exit, nothing written. Fail-open for the schedule, fail-closed for
    content (an unreadable calendar publishes nothing).
  - Writes a standard story JSON into site/content, same shape as the Daily Editions, so
    the normal build/commit path ships it with no special handling.

USAGE  python3 week_ahead.py [--force]     (--force ignores the Monday check, for testing)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CALENDAR = os.path.join(HERE, "data", "week_calendar.json")
CONTENT = os.path.join(HERE, "site", "content")

WEEKDAY = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def build_item(monday, events, now_iso):
    """The story, every sentence sourced from the calendar file."""
    events = sorted(events, key=lambda e: (e.get("date", ""), e.get("kind", "")))
    date = monday.strftime("%Y-%m-%d")
    parts = []
    for e in events:
        d = datetime.strptime(e["date"], "%Y-%m-%d")
        parts.append(f"{WEEKDAY[d.weekday()]}, {d.strftime('%B %d').replace(' 0', ' ')}: "
                     f"{e['title']}. {e.get('detail', '')}".strip())
    titles = [e["title"] for e in events[:3]]
    body = ([f"This is the week's known calendar: scheduled dates only, published in "
             f"advance by the institutions involved. What happens at them is the week's "
             f"news; this story only tells you when to watch."] + parts)
    return {
        "id": f"week-ahead-{date}",
        "slug": f"week-ahead-{date}",
        "kind": "brief",
        "date": date,
        "published_utc": now_iso,
        "category": "week ahead",
        "rank": -1,
        "author": "Crypto Cronkite",
        "title": "The Week Ahead: " + "; ".join(titles),
        "dek": (f"What is on the calendar for the week of "
                f"{monday.strftime('%B %d').replace(' 0', ' ')}: scheduled events only, "
                f"no predictions."),
        "key_fact": parts[0] if parts else "",
        "body": body,
        "bottom_line": "",
        "human_take": "",
        "sources": [{"url": e.get("source", ""), "name": e.get("source_name", "calendar")}
                    for e in events if e.get("source")],
    }


def run(force=False):
    now = datetime.now(timezone.utc)
    if now.weekday() != 0 and not force:
        print("week_ahead: not Monday; nothing to publish.")
        return 0
    monday = now - timedelta(days=now.weekday())
    out = os.path.join(CONTENT, f"{monday.strftime('%Y-%m-%d')}-week-ahead.json")
    if os.path.exists(out):
        print("week_ahead: this week's story already exists; not repeating it.")
        return 0
    try:
        cal = json.load(open(CALENDAR, encoding="utf-8"))
    except Exception as e:
        print(f"::warning::week_ahead: calendar unreadable ({e}) -> publishing nothing "
              f"(fail-closed for content).")
        return 0
    week_end = monday + timedelta(days=6)
    events = [e for e in cal.get("events", [])
              if monday.strftime("%Y-%m-%d") <= e.get("date", "") <=
              week_end.strftime("%Y-%m-%d")]
    if not events:
        print("week_ahead: no scheduled events in the calendar for this week; a Week "
              "Ahead with nothing in it is not a story.")
        return 0
    item = build_item(monday, events, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    item["slug"] = f"week-ahead-{monday.strftime('%Y-%m-%d')}"
    os.makedirs(CONTENT, exist_ok=True)
    json.dump(item, open(out, "w", encoding="utf-8"), indent=1)
    print(f"week_ahead: wrote {os.path.relpath(out)} with {len(events)} scheduled "
          f"event(s).")
    return 0


if __name__ == "__main__":
    sys.exit(run(force="--force" in sys.argv[1:]))
