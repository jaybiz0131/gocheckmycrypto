#!/usr/bin/env python3
"""N-1: the health gate's rules on fixed inputs (no network, no token, no model call).

The crypto case is the desk's own November 22 morning: the live feeds read at 1:00 AM ET that day
said the newest Brief was the Evening Brief of November 12 (as_of 2026-11-12T23:16:26Z) and the
Board's prices were stamped one second before the noon build of November 21. The gate at 7 AM ET
would have sent one mail, for the Brief, and none for the Board.

  python3 scripts/health_gate_test.py      # exit 1 on any failure
"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc


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
    print("N-1 health gate")
    import health_gate as hg
    u = hg.utc
    now = u("2026-11-22T12:03:00Z")                         # 7:03 AM EST
    built, board_asof, board_built = u("2026-11-21T17:01:29Z"), u("2026-11-21T17:01:02Z"), u("2026-11-21T17:01:29Z")
    got = hg.crypto_findings(now, built, u("2026-11-12T23:16:26Z"), board_asof, board_built)
    guarded(fails, "Nov 22: the Brief of Nov 12 is a finding, named with its ET time",
            lambda: len(got) == 1 and got[0].startswith("No Brief or morning read for a full day")
            and "Nov 12, 6:16 PM ET" in got[0])
    guarded(fails, "a Brief from last evening is no finding",
            lambda: not hg.crypto_findings(now, built, u("2026-11-22T00:16:00Z"), board_asof, board_built))
    guarded(fails, "a Brief 23 hours old is no finding; 25 hours is",
            lambda: not hg.crypto_findings(now, built, now - dt.timedelta(hours=23), board_asof, board_built)
            and hg.crypto_findings(now, built, now - dt.timedelta(hours=25), board_asof, board_built))
    guarded(fails, "the Board 18 hours old at its build (a CoinGecko refusal) is a finding",
            lambda: any("Board's prices were 18.0 hours old" in f for f in hg.crypto_findings(
                now, built, now - dt.timedelta(hours=2), board_built - dt.timedelta(hours=18), board_built)))
    guarded(fails, "the Board 5 hours old at its build is no finding (six is the line)",
            lambda: not hg.crypto_findings(now, built, now - dt.timedelta(hours=2), board_built - dt.timedelta(hours=5),
                                           board_built))
    guarded(fails, "the Board's wall-clock age is not the rule: 19 hours after a fresh build is no finding",
            lambda: not hg.crypto_findings(now, built, now - dt.timedelta(hours=2), now - dt.timedelta(hours=19),
                                           now - dt.timedelta(hours=19)))
    guarded(fails, "a site that has not built for 25 hours is a finding, and an unreadable stamp is one",
            lambda: hg.site_finding(now, now - dt.timedelta(hours=25)) and hg.site_finding(now, None)
            and not hg.site_finding(now, now - dt.timedelta(hours=13)))
    guarded(fails, "one gate a day: 6:03 AM ET stands down, 7:03 runs, a second 7 AM run stands down, a dispatch runs",
            lambda: not hg.should_run(u("2026-11-22T11:03:00Z"), "schedule", 0)[0]
            and hg.should_run(u("2026-11-22T12:03:00Z"), "schedule", 0)[0]
            and not hg.should_run(u("2026-11-22T13:20:00Z"), "schedule", 1)[0]
            and hg.should_run(u("2026-11-22T03:00:00Z"), "workflow_dispatch", 3)[0])
    guarded(fails, "in summer the 11:03 UTC tick is 7:03 AM EDT and runs",
            lambda: hg.should_run(u("2026-07-20T11:03:00Z"), "schedule", 0)[0])
    return fails


def main():
    fails = unit()
    print(f"\nN-1 health gate: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
