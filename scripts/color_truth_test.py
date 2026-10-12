#!/usr/bin/env python3
"""
color_truth_test.py: the fixture where Bitcoin's 24-hour change and its since-close change
disagree in sign, and so does the whole market's (Program 7 Sprint 7.1, section 4), and where
the 24-hour change is up while the week's chart runs down (Jack, 12 October, 3:00 PM).

Renders the Markets tiles (home.t_bitcoin, home.t_cap, the same functions the Board page
calls), the home tape and the home band from a fixture snapshot, and runs
scripts/color_truth.py over the result. Exit 1 and every contradiction named when the
rendered page lets a color disagree with the number beside it; exit 0 when none does.
No network, no model, no file written.

    PYTHONPYCACHEPREFIX=$(mktemp -d) python3 scripts/color_truth_test.py
"""

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

import color_truth  # noqa: E402
import home  # noqa: E402


def fixture():
    snap = json.load(open(os.path.join(HERE, "site", "data", "snapshot.json"), encoding="utf-8"))
    snap = copy.deepcopy(snap)
    coins = snap["fields"]["coins"]["value"]
    coins["BTC"]["chg_24h_pct"] = 0.05           # green on the day
    # and the week down: the 24-hour and 7-day signs disagree (Jack, 3:00 PM)
    snap["fields"]["week"]["value"]["BTC"]["closes"] = {
        "2026-10-04": 86489.73, "2026-10-05": 85945.29, "2026-10-06": 85597.01,
        "2026-10-07": 83129.92, "2026-10-08": 81629.96, "2026-10-09": 82481.93,
        "2026-10-10": 82978.30}
    snap["fields"]["total_cap"]["value"]["chg_24h_pct"] = -0.31   # red on the day
    deltas = {"bitcoin": {"pct": -0.67},          # but down since yesterday's close
              "market": {"pct": 0.40}}            # and the market up since it
    narr = {"line": "Bitcoin drifted up 0.79 percent on the day as whales moved coins onto "
                    "exchanges; the news is quiet.",
            "by": "edition", "written_et": "7:16 PM ET on Oct 11",
            "readings": {"btc_24h_pct": 0.79, "fear_greed": 61, "fear_greed_band": "Greed",
                         "etf_net_usd_m": 21.1, "funding_8h_pct": 0.0,
                         "funding_band": "calm"}}
    pulse = {"market": {"btc_dominance_pct": 58.2}}
    return snap, deltas, narr, pulse


def main():
    snap, deltas, narr, pulse = fixture()
    html = (home.t_bitcoin(snap, pulse, deltas) + home.t_cap(snap, deltas)
            + home.tape(snap) + home.narrative_band(narr, snap))
    found = color_truth.contradictions(html)
    for f in found:
        print("CONTRADICTION:", f)
    if found:
        print(f"color truth: FAIL, {len(found)} contradiction(s)")
        return 1
    print("color truth: PASS, every color agrees with the number beside it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
