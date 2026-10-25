#!/usr/bin/env python3
"""Hotfix 9.6w plants (U-9): each guard is broken on purpose in a scratch COPY of the tree, the test is run, and the cases that go
red are named. The real tree is never touched. A plant whose text is not found exactly once exits non-zero, and so does any
plant that leaves the test green.
usage: python3 scripts/sprint96w_plants.py <scratch dir> > docs/sprint96w-plants.log
Each plant is (name, file, old text, new text, whether the whole-build case is run)."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTS = [
    ("the omission put back in render_wire: no entries in the window returns None again", "site_build.py",
     "        return _wire_empty_page(items, dateline, now)\n", "        return None\n", False),
    ("the omission put back in the build: wire.html written only when there are rows", "site_build.py",
     '    w("wire.html", _wire)\n', '    if _wire and _wire_rows(items):\n        w("wire.html", _wire)\n', True),
    ("the omission put back in the build: the old `if _wire:` guard", "site_build.py",
     '    w("wire.html", _wire)\n', '    if _wire:\n        w("wire.html", _wire)\n', False),
    ("the stale mark removed: the empty page is never stale", "site_build.py",
     'promise_hours=WIRE_HOURS, what="The Wire", now=now)', 'promise_hours=10 ** 9, what="The Wire", now=now)', True),
    ("the stale stamp reads the wall clock, not the build's clock", "site_build.py",
     "age_h = ((now or _dt.datetime.now(_dt.timezone.utc)) - gen)", "age_h = (_dt.datetime.now(_dt.timezone.utc) - gen)", False),
    ("the empty page invents a line (a fixture entry listed in the window)", "site_build.py",
     "f'<p class=\"wr-none\">No wire entries fall in the last {WIRE_HOURS} hours. '",
     "f'<p class=\"wr-none\"><li class=\"wr-r\">FIXTURE</li>No wire entries fall in the last {WIRE_HOURS} hours. '", False),
    ("the empty page does not name its window", "site_build.py",
     "f'<p class=\"wr-none\">No wire entries fall in the last {WIRE_HOURS} hours. '", "f'<p class=\"wr-none\">Nothing here. '", False),
    ("the page with entries changes by a byte", "site_build.py",
     '        f\'<span class="wr-c">{len(rows)} entries, last {WIRE_HOURS} hours</span></div>\'',
     '        f\'<span class="wr-c">{len(rows)} entries, last {WIRE_HOURS} hours.</span></div>\'', False),
    ("the mini-board file left out when the Top 100 is empty", "site_build.py",
     '    w(os.path.join("data", "coins-mini.json"),\n      json.dumps(_cm_payload, separators=(",", ":")))\n',
     '    if _cm_payload:\n        w(os.path.join("data", "coins-mini.json"),\n          json.dumps(_cm_payload, separators=(",", ":")))\n', True),
    ("the 9.4 clock unpinned: the sitemap is handed every /why/ page again, Bitcoin's wall-clock one included", "scripts/sprint94_test.py",
     'for b in built if b["path"] in mv_paths])', "for b in built])", False),
]


def run(cwd, extra):
    r = subprocess.run([sys.executable, "scripts/sprint96w_test.py"] + extra, cwd=cwd, capture_output=True, text=True, timeout=1500)
    return [l.strip() for l in r.stdout.splitlines() if "FAIL" in l], r.returncode


def main():
    work = os.path.join(sys.argv[1], "plant-tree")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(HERE, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "publish", "node_modules"))
    n_red = 0
    for name, rel, old, new, build in PLANTS:
        path = os.path.join(work, rel)
        orig = open(path, encoding="utf-8").read()
        if orig.count(old) != 1:
            print(f"PLANT DID NOT APPLY (text found {orig.count(old)} times in {rel}): {name}")
            return 2
        open(path, "w", encoding="utf-8").write(orig.replace(old, new))
        try:
            fails, rc = run(work, ["--build"] if build else [])
        finally:
            open(path, "w", encoding="utf-8").write(orig)
        print(f"PLANT: {name}\n  file {rel}; exit {rc}; {len(fails)} case(s) red")
        for f in fails:
            print("    " + f[:230])
        n_red += 1 if fails and rc != 0 else 0
    fails, rc = run(work, ["--build"])
    print(f"\nRESTORED TREE: exit {rc}; {len(fails)} case(s) red")
    print(f"PLANTS: {len(PLANTS)}, {n_red} went red, restored tree {'green' if rc == 0 else 'RED'}")
    return 0 if n_red == len(PLANTS) and rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
