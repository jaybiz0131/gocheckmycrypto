#!/usr/bin/env python3
"""
edition_check.py: the daily edition is supposed to be guaranteed. Prove it, or say so.

WHY THIS EXISTS
  The workflow runs the edition as `python3 wrap.py || echo "::warning::daily edition failed
  its gates; stories unaffected"`. Fail-open is the right call: an edition failure must never
  block story publishing, and it does not. But `|| echo` also means the job stays green, the
  warning scrolls past in a 700-line log, and nothing anywhere counts how long it has been.

  It went unnoticed for three days. On 2026-07-31 the newest edition on the site was the
  July 28 Evening Brief, still holding the homepage hero and still telling readers to watch
  an FOMC decision that had happened two days earlier. The desk published 13 stories in that
  window. Nobody knew the edition had stopped, because nothing was watching the one thing
  that would have said so: the gap.

  The root cause that day was real and fixable (an unstated sign convention on the whale
  board, see chartmaster._net_plain). The reason it lasted three days was not. A fail-open
  step with no gap check is indistinguishable from a step that works.

WHAT IT DOES
  Reads the committed editions and reports the age of the newest one. Over the threshold it
  emits a ::error:: annotation the workflow raises a flag from, exactly like the calendar and
  hacks-ledger checks. It never fails the run: whether a missing edition is worth acting on
  is an editorial judgment, and a check that could block publishing over one would be worse
  than the problem it reports.

THE THRESHOLD is per-slot, not a single age (2026-08-31). The old 26-hour rule measured
the age of the single NEWEST edition, so a desk shipping one edition a day never breached:
on Aug 31 at 01:32 it printed OK while the desk had delivered 0-1 of its 3 promised slots
on each of the previous four days. The breach now counts slot windows: fewer than 2 of the
last 3 CLOSED slot windows carrying their edition file is a breach. The current in-progress
slot is excluded (conservative grace: drift and the watcher's recovery may still serve it),
so a single legitimately failed slot still never breaches on its own.

USAGE  python3 edition_check.py
"""

import datetime
import glob
import json
import os
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")

# The slot schedule, mirroring the brief workflow's crons and wrap.py's day anchoring.
# close > 24h means the slot's window (its recovery net included) crosses midnight, and
# such a window belongs to the day it STARTED on; keep in sync with watcher.SLOT_DEADLINES.
SLOTS = (  # (edition slug, scheduled minutes-of-UTC-day, window-close minutes)
    ("morning-brief", 10 * 60 + 40, 17 * 60),
    ("afternoon-brief", 17 * 60 + 8, 23 * 60),
    ("evening-brief", 23 * 60 + 8, 29 * 60),
)


def _when(item):
    raw = item.get("published_utc") or ((item.get("date") or "") + "T00:00:00Z")
    try:
        return datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def newest(kind, content=None):
    """The newest committed item, either 'edition' (a wrap) or 'story' (anything else)."""
    best = None
    for p in glob.glob(os.path.join(content or CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("example"):
            continue
        is_wrap = str(d.get("id") or "").startswith("wrap-")
        if (kind == "edition") != is_wrap:
            continue
        when = _when(d)
        if when and (best is None or when > best[0]):
            best = (when, d)
    return best


def gap_hours(now=None, content=None):
    """(hours since the newest edition, the edition) or (None, None) if there are none."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    best = newest("edition", content)
    if not best:
        return None, None
    return (now - best[0]).total_seconds() / 3600, best[1]


def slot_ledger(now=None, content=None, count=3):
    """The last `count` slot windows that have CLOSED, oldest first, each as
    (slot day ISO, slug, edition file exists). A window still open, the in-progress
    slot, is not counted: grace, conservatively, because drift and the watcher's
    recovery may yet serve it. Pure function for tests."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    content = content or CONTENT
    rows = []
    for back in range(3, -1, -1):
        day = now.date() - datetime.timedelta(days=back)
        midnight = datetime.datetime.combine(
            day, datetime.time(tzinfo=datetime.timezone.utc))
        for slug, _start, close in SLOTS:
            if midnight + datetime.timedelta(minutes=close) > now:
                continue
            rows.append((day.isoformat(), slug,
                         os.path.exists(os.path.join(content, f"{day.isoformat()}-{slug}.json"))))
    return rows[-count:]


# HOW LATE, NOT JUST WHETHER (2026-09-08). This file counted the AGE of the newest
# edition, which catches an outage and is blind to the failure the desk actually has:
# every slot served, every slot hours late. Measured over 2026-09-05 to 09-07, the morning
# brief published a median 194 minutes after its slot on this desk, so a "Morning Brief"
# reached readers at 9am Eastern instead of 5:40am. Nothing in the pipeline reported that,
# because nothing was measuring it.
#
# The cause is upstream and known: GitHub delivers this repo's crons a median 103 minutes
# late and drops some outright. The fix is an external trigger. This is the instrument
# that says whether the fix is working, and it will go quiet on its own when it is.
PUNCTUAL_MIN = 45          # a slot within this of its target is on time
PUNCTUAL_DAYS = 5


def slot_targets():
    """Edition slug -> (hour, minute) UTC, read from the workflow's OWN slot-guard map.

    Deliberately not a hand-kept list here. The crons, wrap.CRON_SLOT and the guard have
    drifted apart before, and a fourth copy would be a fourth thing to forget. The
    earliest cron mapped to a slug is that slot's real target; the later ones are retries.
    """
    import re
    wf_dir = os.path.join(HERE, ".github", "workflows")
    try:
        wf = next(os.path.join(wf_dir, f) for f in sorted(os.listdir(wf_dir))
                  if "brief" in f and f.endswith(".yml"))
        text = open(wf, encoding="utf-8").read()
    except Exception:
        return {}
    out = {}
    for cron, slug in re.findall(r'"(\d+ \d+ \* \* \*)":\s*"([a-z-]+)"', text):
        m, h = cron.split()[0], cron.split()[1]
        t = (int(h), int(m))
        if slug not in out or t < out[slug]:
            out[slug] = t
    return out


def punctuality(days=PUNCTUAL_DAYS, content=None):
    """(date, slug, published_hhmm, minutes_late) for recent editions, newest first."""
    targets = slot_targets()
    if not targets:
        return []
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days)).date().isoformat()
    rows = []
    for path in glob.glob(os.path.join(content or CONTENT, "*.json")):
        base = os.path.basename(path)[:-len(".json")]
        parts = base.split("-")
        # "2026-09-07-morning-brief" -> date "2026-09-07", key "morning-brief"
        if len(parts) != 5:
            continue
        date, key = "-".join(parts[:3]), "-".join(parts[3:])
        if date < cutoff or key not in targets:
            continue
        try:
            d = json.load(open(path, encoding="utf-8"))
            when = datetime.datetime.fromisoformat(
                (d.get("published_utc") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        h, m = targets[key]
        tgt = when.replace(hour=h, minute=m, second=0, microsecond=0)
        rows.append((date, key, when.strftime("%H:%M"),
                     round((when - tgt).total_seconds() / 60)))
    rows.sort(reverse=True)
    return rows


def report_punctuality():
    """Advisory. Never blocks: a late edition is still an edition."""
    rows = punctuality()
    if len(rows) < 3:
        return
    late = sorted(abs(r[3]) for r in rows)
    median = late[len(late) // 2]
    worst = max(rows, key=lambda r: abs(r[3]))
    on_time = sum(1 for r in rows if abs(r[3]) <= PUNCTUAL_MIN)
    line = (f"{on_time} of {len(rows)} recent editions landed within {PUNCTUAL_MIN} min of "
            f"their slot; median drift {median} min, worst {worst[0]} {worst[1]} at "
            f"{worst[2]}Z ({worst[3]:+d} min)")
    if median > PUNCTUAL_MIN:
        common.gh("warning",
                  f"edition_check: slots are being served LATE. {line}. The editions are "
                  f"landing, so nothing here is lost; the trigger is what is late. If the "
                  f"external trigger is running, this line is how you tell.")
    else:
        print(f"edition_check: punctuality OK, {line}.")


def main():
    hours, ed = gap_hours()
    if hours is None:
        common.gh("error", "edition_check: the desk has published NO daily edition at all.")
        return 0

    # Stories since the edition are what make a gap visible to a reader: the front page
    # carries newer reporting than the read that is supposed to summarise the day.
    since = 0
    latest = newest("story")
    if latest:
        ed_when = _when(ed)
        since = sum(1 for p in glob.glob(os.path.join(CONTENT, "*.json"))
                    if _newer_story(p, ed_when))

    # STALE-CHECKOUT GUARD (owner ruling 2026-08-03, note 1): this check reads a local
    # tree, so its finding carries the tree's HEAD; a reader can see at a glance whether
    # the alarm is about the desk or about an unpulled checkout (the news desk's phantom
    # 62-hour gap was exactly that).
    import subprocess
    try:
        head = subprocess.run(["git", "log", "-1", "--format=%h %cd", "--date=format:%Y-%m-%dT%H:%M"],
                              cwd=HERE, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        head = "unknown"
    # PER-SLOT ACCOUNTING (2026-08-31): the desk promises three editions a day, so
    # the breach question is "are the slots being served?", never "how old is the
    # newest edition?". The old newest-age rule printed OK on Aug 31 at 01:32 while
    # the desk had delivered 0-1 of 3 slots on each of the previous four days.
    ledger = slot_ledger()
    served = sum(1 for _, _, ok in ledger if ok)
    missing = [f"{d} {slug}" for d, slug, ok in ledger if not ok]
    msg = (f"{served} of the last {len(ledger)} closed slot windows served"
           + (f" (missing: {', '.join(missing)})" if missing else "")
           + f"; newest edition is {hours:.0f}h old ({ed.get('date')}, "
             f"{(ed.get('title') or '')[:60]}), {since} story/stories published since "
             f"[tree HEAD: {head}]")
    if served < 2:
        common.gh("error",
                  f"edition_check: {msg}. The edition is supposed to run three times a day "
                  f"and the workflow step is fail-open, so a broken edition is silent unless "
                  f"something counts the slots. Read the wrap step's log for the gate it failed.")
        _flag_issue(msg)
        report_punctuality()
        # AN ABSTAINED EDITION IS AS LOUD AS A FAILED ONE (owner directive 2026-08-25):
        # wrap declining with zero stories is correct behaviour, but repeated
        # honest silences is an outage, and this counter is the only thing that sees
        # it. Exit 3 so the workflow's dead-last gate can mark the run failed AFTER
        # stories publish; the annotation and the issue above are unchanged.
        return 3
    print(f"edition_check: OK, {msg}.")
    report_punctuality()
    return 0


def _flag_issue(msg):
    """A warning inside a green run is a named anti-pattern (owner ruling 2026-08-03):
    every fail-open either fails closed or escalates to a flag issue. The edition step
    stays fail-open, so breach of the gap threshold files ONE deduplicated issue. Three
    sports editions died in a row on 2026-08-02..03 with only ::warning:: lines to show
    for it; this is the bell that was missing. No token -> the annotation above is the
    whole alarm, stated here so the gap in coverage is visible in the log."""
    import urllib.request
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        print("edition_check: no GH token in env; gap reported in annotations only")
        return
    title = "Edition gap: the guaranteed daily edition has stopped"
    hdrs = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues?state=open&labels=pipeline",
            headers=hdrs)
        if any(i["title"] == title for i in json.load(urllib.request.urlopen(req))):
            print("edition-gap issue already open; not duplicating")
            return
        body = (f"{msg}.\n\nThe edition step is fail-open by design (stories must never "
                "be blocked by a dead edition), so this issue is the loud part. Read the "
                "wrap step's log in the most recent brief runs for the belt or gate the "
                "edition died on. Close after the next published edition.")
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues",
            data=json.dumps({"title": title, "body": body,
                             "labels": ["pipeline"]}).encode(),
            headers=hdrs, method="POST")
        urllib.request.urlopen(req)
        print("edition-gap issue opened")
    except Exception as e:
        print(f"edition_check: could not file the gap issue ({e.__class__.__name__})")


def _newer_story(path, cutoff):
    if not cutoff:
        return False
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return False
    if d.get("example") or str(d.get("id") or "").startswith("wrap-"):
        return False
    when = _when(d)
    return bool(when and when > cutoff)


if __name__ == "__main__":
    sys.exit(main())
