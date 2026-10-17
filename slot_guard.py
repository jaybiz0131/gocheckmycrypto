#!/usr/bin/env python3
"""slot_guard.py: ONE EDITION PER EVENING (Jack, 16 October 2026).

The served-slot guard in crypto-news-brief.yml asked one question: is this slot's Edition on
origin/main? On 15 October the 7:10 PM run (a workflow_dispatch, run 38822001905) was withheld at
the consistency gate and wrote no Edition, so the 7:40 PM dispatch (run 38825025985) found none and
spent a second full run (about $0.08). Both were Worker dispatches under Jack's token; neither was
the schedule or the catch-up cron (the schedule's own tick fired at 01:11 UTC on the 16th).

THE RULE: once a run has STARTED for a slot, no other run for that slot proceeds, unless every
earlier run ended with nothing published and the ledger says so. "Started" is a ledger row for
that slot and day that spent a model call or pushed (ledger.json only keeps rows that did
something), or another run of the workflow in progress. "Nothing published" is the row's own
statement: pushed false and edition_published not true. A breaking run is not decided here: it
regenerates a slot on purpose.

Pure: `decide` reads its arguments only; the workflow gathers the ledger (origin/main's
ledger.json) and the in-progress runs and hands them over. Fail-open on missing information, the
rule for every gate on this desk: None for the ledger or the run list means "could not read".
"""
import datetime

BRIEF_WORKFLOW = "Crypto Cronkite daily brief"


def row_slot(row):
    """(slot, day) of a ledger row. Rows written since 9.1 carry both; older rows are the evening
    slot, dated as wrap.py dates it: a run before 05:00 UTC belongs to the previous day."""
    if row.get("slot") and row.get("slot_day"):
        return row["slot"], row["slot_day"]
    try:
        t = datetime.datetime.strptime(str(row.get("t") or ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return "", ""
    d = t.date() - datetime.timedelta(days=1) if t.hour < 5 else t.date()
    return "evening-brief", d.isoformat()


def started(row):
    """True when the row is a brief run that actually began: it did not stand down at the guard
    and it spent a model call or pushed."""
    if row.get("wf") != BRIEF_WORKFLOW or row.get("breaking"):
        return False
    if row.get("guard") == "false" or row.get("outcome") == "stood down":
        return False
    return bool(row.get("tokens") or row.get("pushed"))


def published_nothing(row):
    """The row says the run ended with nothing published: no push and no Edition."""
    return not row.get("pushed") and not row.get("edition_published")


def decide(slot, day, ledger_rows, my_run="", in_progress=None, breaking=False):
    """(serve, reason). serve False means stand down before any model call."""
    if breaking:
        return True, "a breaking run regenerates a slot on purpose"
    earlier = [r for r in (ledger_rows or [])
               if str(r.get("run") or "") != str(my_run) and started(r)
               and row_slot(r) == (slot, day)]
    if earlier:
        if all(published_nothing(r) for r in earlier):
            return True, ("every earlier run for this slot ended with nothing published "
                          f"({', '.join(str(r.get('run')) for r in earlier)}); one retry may serve it")
        names = ", ".join(str(r.get("run")) for r in earlier)
        return False, (f"run {names} already started for {slot} on {day} and the ledger does not say "
                       f"it published nothing; one Edition per evening")
    # only a run that started BEFORE this one counts (Actions run ids rise with time), so two
    # runs that begin together cannot both stand down
    def _earlier(r):
        try:
            return int(r.get("run_id")) < int(my_run)
        except (TypeError, ValueError):
            return str(r.get("run_id") or "") != str(my_run)
    others = [r for r in (in_progress or []) if _earlier(r)]
    if others:
        return False, (f"run {others[0].get('run_id')} of this workflow is in progress; it started "
                       f"before this one, so this one stands down")
    return True, ""
