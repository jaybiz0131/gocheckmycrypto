#!/usr/bin/env python3
"""Program 9, Sprint 9.1 (Jack, 16 October 2026): ONE EDITION PER EVENING.

  python3 scripts/slot_guard_test.py        # unit cases; exit 1 on any failure

15 October ran the evening slot twice: run 38822001905 (a workflow_dispatch at 7:10 PM ET, ledger
row 160c657) and run 38825025985 (a workflow_dispatch at 7:40 PM, ledger 00a405e), about $0.08 each.
The first was withheld at the consistency gate (no Edition file), so the served-slot guard, which
asked only "is the Edition on origin/main?", let the second spend a full run. The rule now: once a
run has STARTED for a slot (a ledger row for that slot and day that spent or pushed, or another run
of the workflow in progress), no other run for that slot proceeds, unless every earlier run ended
with nothing published and the ledger says so (pushed false, edition_published false).

Fixtures: fixtures/slot_guard/ledger_rows_2026-10-15.json, the real rows of 15 and 16 October.
Every case catches its own exceptions, so on origin/main (no slot_guard.py) the run prints FAIL
lines instead of crashing.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FX = os.path.join(HERE, "fixtures", "slot_guard")


def rows():
    return json.load(open(os.path.join(FX, "ledger_rows_2026-10-15.json"), encoding="utf-8"))


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def unit():
    fails = []
    class _L:
        def __getattr__(self, n):
            import slot_guard
            return getattr(slot_guard, n)
    sg = _L()
    r = rows()
    first = next(x for x in r if x["run"] == "38822001905")
    second = next(x for x in r if x["run"] == "38825025985")
    dec = lambda rr, **k: sg.decide("evening-brief", "2026-10-15", rr, **k)
    print("1. 15 October: the second run")
    guarded(fails, "the 7:40 PM dispatch stands down once the 7:10 PM run has a ledger row for the slot (it pushed, the Edition was withheld)",
            lambda: dec([first], my_run="38825025985")[0] is False)
    guarded(fails, "the reason names the earlier run", lambda: "38822001905" in dec([first], my_run="38825025985")[1])
    guarded(fails, "the late scheduled tick at 01:11 UTC on 16 October (the evening slot of the 15th) stands down too",
            lambda: dec([first, second], my_run="38833807996")[0] is False)
    guarded(fails, "the first run itself, with nothing before it, proceeds", lambda: dec([], my_run="38822001905")[0] is True)
    guarded(fails, "a run is not stopped by its own row", lambda: dec([first], my_run="38822001905")[0] is True)
    print("2. the exception: the first ended with nothing published, and the ledger says so")
    empty = dict(first, pushed=False, edition_published=False, tokens=60000)
    guarded(fails, "pushed false and edition_published false: the retry proceeds", lambda: dec([empty], my_run="x")[0] is True)
    guarded(fails, "pushed false but the ledger does not say the Edition is absent (a legacy row): the retry proceeds only on pushed false",
            lambda: dec([dict(first, pushed=False)], my_run="x")[0] is True)
    guarded(fails, "edition_published true: stands down", lambda: dec([dict(empty, edition_published=True)], my_run="x")[0] is False)
    guarded(fails, "two earlier runs, one of which published: stands down",
            lambda: dec([empty, dict(first, run="y")], my_run="x")[0] is False)
    print("3. what does not count")
    guarded(fails, "a row that stood down at the guard is not a started run",
            lambda: dec([dict(first, guard="false", outcome="stood down", tokens=0)], my_run="x")[0] is True)
    guarded(fails, "another workflow's row (the watcher) is not a started brief",
            lambda: dec([dict(first, wf="Breaking-news watcher")], my_run="x")[0] is True)
    guarded(fails, "a row for another slot day does not block this one",
            lambda: sg.decide("evening-brief", "2026-10-16", [first], my_run="x")[0] is True)
    guarded(fails, "a breaking run is never stopped here", lambda: dec([first], my_run="x", breaking=True)[0] is True)
    print("4. a run that has started but written no row yet")
    guarded(fails, "another run of the workflow in progress stands this one down",
            lambda: dec([], my_run="200", in_progress=[{"run_id": "100", "created_utc": "2026-10-15T23:10:56Z"}])[0] is False)
    guarded(fails, "a run that started AFTER this one does not stop it (two together cannot both stand down)",
            lambda: dec([], my_run="200", in_progress=[{"run_id": "300"}])[0] is True)
    guarded(fails, "an in-progress list that is only this run does not",
            lambda: dec([], my_run="100", in_progress=[{"run_id": "100"}])[0] is True)
    guarded(fails, "no ledger and no API answer (None): fail open, the checkout's own rule stands",
            lambda: dec(None, my_run="b", in_progress=None)[0] is True)
    print("5. the ledger writes what the guard reads")
    src = open(os.path.join(HERE, "scripts", "ops_ledger.py"), encoding="utf-8").read()
    guarded(fails, "ops_ledger records slot, slot_day and edition_published",
            lambda: all(k in src for k in ('"slot"', '"slot_day"', '"edition_published"')))
    yml = open(os.path.join(HERE, ".github", "workflows", "crypto-news-brief.yml"), encoding="utf-8").read()
    guarded(fails, "the guard step calls slot_guard on origin/main's ledger", lambda: "import slot_guard" in yml and "ledger.json" in yml)
    guarded(fails, "the ledger step is handed the slot", lambda: re.search(r"SLOT_SLUG:\s*\$\{\{\s*steps\.guard\.outputs\.slot_slug", yml))
    return fails


def main():
    fails = unit()
    print("\nONE EDITION PER EVENING:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
