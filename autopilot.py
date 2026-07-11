#!/usr/bin/env python3
"""
Autopilot: full-auto release for the daily brief, on Jack's standing instruction (2026-07-11).

Policy (supersedes the launch-era always-human gate; recorded in DEVIATIONS):
  - VERIFIED stories publish automatically: the adversarial verifier IS the gate.
  - NEEDS-HUMAN-REVIEW stories are never auto-published; they stay in the review queue for a
    human take (publish.py still enforces that override rule independently).
  - REJECT never publishes. A failed run publishes nothing (fail-closed inheritance).

Runs after run.py in the daily workflow: writes an approval file that approves exactly the
VERIFIED set, runs Stage 6 (publish.py), then ingests approved payloads into site content
(site_build.py --ingest). The workflow then commits site/content and pushes, which deploys.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def main():
    tpl_path = os.path.join(OUT, "approval_template.json")
    report_path = os.path.join(OUT, "run_report.json")
    if not (os.path.exists(tpl_path) and os.path.exists(report_path)):
        print("autopilot: no run outputs found -> nothing to publish (fail-closed)")
        return 1
    report = json.load(open(report_path, encoding="utf-8"))
    if report.get("mode") != "live" or report.get("status") not in ("ok", "OK", None) and not report.get("review_queue"):
        print(f"autopilot: run not live/ok -> nothing to publish (mode={report.get('mode')})")
        return 1

    approval = json.load(open(tpl_path, encoding="utf-8"))
    approved = held = 0
    for cid, story in approval.get("stories", {}).items():
        if story.get("verifier_verdict") == "VERIFIED":
            story["decision"] = "approve"
            approved += 1
        else:
            story["decision"] = "hold"
            held += 1
    json.dump(approval, open(os.path.join(OUT, "approval.json"), "w", encoding="utf-8"), indent=1)
    print(f"autopilot: auto-approved {approved} VERIFIED, held {held} for human review")
    if approved == 0:
        print("autopilot: nothing VERIFIED today -> site publish skipped, queue kept for human")
        return 0

    r = subprocess.run([sys.executable, os.path.join(HERE, "publish.py")], cwd=HERE)
    if r.returncode != 0:
        print("autopilot: publish.py failed -> fail-closed")
        return 1
    r = subprocess.run([sys.executable, os.path.join(HERE, "site_build.py"), "--ingest"], cwd=HERE)
    if r.returncode != 0:
        print("autopilot: ingest/build failed -> fail-closed")
        return 1
    print("autopilot: published + ingested; workflow commit/push makes it live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
