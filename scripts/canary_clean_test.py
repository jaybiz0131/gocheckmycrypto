#!/usr/bin/env python3
"""canary_clean_test.py: after a canary run, git status must be exactly what it was before.

Sprint 6.3, item 3 (12 October 2026). Every canary run used to leave two untracked data
files behind, site/data/chartmaster/<date>.json and site/data/snapshots/pulse-<date>.json,
written by the live-layer canary's render of the home page into the real data directories.
This runs the canary, compares `git status --porcelain` before and after, and fails naming
whatever the run left. It also requires the canary itself to pass, so a clean tree cannot be
bought by a canary that died early.

    python3 scripts/canary_clean_test.py        # exit 0 clean, 1 left files, 2 canary red
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def status():
    r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                       capture_output=True, text=True, check=True)
    return set(l for l in r.stdout.split("\n") if l)


def main():
    before = status()
    r = subprocess.run([sys.executable, "verify_pipeline.py", "canary"], cwd=ROOT,
                       capture_output=True, text=True)
    after = status()
    left = sorted(after - before)
    gone = sorted(before - after)
    if "LAYER 1 CANARY: PASS" not in r.stdout:
        print("canary_clean_test: the canary did not pass, so the tree proves nothing")
        print("\n".join(r.stdout.split("\n")[-6:]))
        return 2
    if left or gone:
        print(f"canary_clean_test: FAIL, the canary left {len(left)} change(s) and removed "
              f"{len(gone)}:")
        for l in left:
            print("  left   " + l)
        for l in gone:
            print("  gone   " + l)
        return 1
    print("canary_clean_test: PASS, git status is the same after the canary as before it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
