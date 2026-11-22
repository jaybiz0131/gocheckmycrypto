#!/usr/bin/env python3
"""N-1 (November 22, 2026): the run reaches "failure" only when the desk did not do its job, and each workflow has one trigger.

  1. One trigger per workflow (class D). The Worker (gcm-newsroom/slot-trigger) dispatches the Brief (three times a night),
     the morning read (8:15 AM Eastern) and the watcher (every 30 minutes, 8 AM to 10:59 PM Eastern). Their GitHub crons
     doubled each failing run and each mail; they are removed. A workflow the Worker does not dispatch keeps its cron.
  2. The edition-gap step is a warning (class A). It runs dead last, after publish, and reports a gap; the run it closes has
     already done everything it could. The gap issue edition_check files is unchanged, and the health gate is the mail.
  3. Every workflow that pushes to main is in the one publish group, crypto-publish, so two never write at once.
  4. The health gate (Phase 3) exists, runs daily at 7 AM Eastern, pushes nothing and holds no publish lock.

Stdlib only: the workflows install nothing but Pillow.
  python3 scripts/n1_workflows_test.py      # exit 1 on any failure
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(HERE, ".github", "workflows")
WORKER_DISPATCHED = ("crypto-news-brief.yml", "morning-read.yml", "watcher.yml")


def read(name):
    p = os.path.join(WF, name)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def active_crons(txt):
    return re.findall(r'^\s*-\s*cron:\s*["\']([^"\']+)["\']', txt, re.M)


def on_block(txt):
    m = re.search(r"^on:\s*\n(.*?)(?=^\S)", txt, re.M | re.S)
    return m.group(1) if m else ""


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
    print("N-1 workflows")
    for name in WORKER_DISPATCHED:
        t = read(name)
        guarded(fails, f"{name}: the Worker dispatches it, so it has no GitHub cron and no schedule: key",
                lambda t=t: t and not active_crons(t) and not re.search(r"^\s+schedule:", on_block(t), re.M))
        guarded(fails, f"{name}: it still takes workflow_dispatch", lambda t=t: "workflow_dispatch" in on_block(t))
    brief = read("crypto-news-brief.yml")
    step = re.search(r"- name: (?:Warn|Fail the run) if the edition gap breached.*?(?=\n      - name:|\Z)", brief, re.S)
    guarded(fails, "the edition-gap step warns and never sets the run failed",
            lambda: step and "core.setFailed" not in step.group(0) and "core.warning" in step.group(0))
    guarded(fails, "the Edition stage failing still fails the run (the desk did not publish its Edition)",
            lambda: "core.setFailed(`Edition stage failed" in brief)
    for name in sorted(os.listdir(WF)):
        t = read(name)
        if re.search(r"^\s*(?:if |)git push\b|\bgit push\b", t, re.M) and "git push" in t:
            guarded(fails, f"{name}: pushes to main, so it holds the crypto-publish group",
                    lambda t=t: re.search(r"concurrency:\s*\n\s+group:\s*crypto-publish\b", t))
    h = read("health.yml")
    guarded(fails, "health.yml exists, runs scripts/health_gate.py on a daily cron at 7 AM Eastern (11:03 and 12:03 UTC, "
                   "one per offset; the script stands down before 7 AM ET and after the day's first gate)",
            lambda: h and "scripts/health_gate.py" in h and set(active_crons(h)) == {"3 11 * * *", "3 12 * * *"})
    guarded(fails, "health.yml pushes nothing and holds no publish lock",
            lambda: h and "git push" not in h and "crypto-publish" not in h)
    return fails


def main():
    fails = unit()
    print(f"\nN-1 workflows: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
