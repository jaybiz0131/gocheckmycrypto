#!/usr/bin/env python3
"""Hotfix 9.6h plants: each test is broken on purpose in a scratch COPY of the tree, run, and the cases that go red are
named. The real tree is never touched. usage: python3 scripts/sprint96h_plants.py <scratch dir> > docs/sprint96h-review1-red.log
Each plant is (name, file, old text, new text, whether the whole-build case is run)."""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTS = [
    ("refresh starts from an empty table set (drops every table it did not fetch)", "living_tables.py",
     'tables = dict(stored["tables"])', "tables = {}", True),
    ("refresh stamps every kept table with the new time", "living_tables.py",
     "    FRESH = fresh\n", "    FRESH = fresh\n    for _k in tables:\n        fetched[_k] = now\n", False),
    ("refresh rewrites the file even when nothing was read", "living_tables.py",
     '    if not fresh:\n        print("living_tables: nothing resolved; committed file left alone")\n        return None\n', "", False),
    ("load() returns nothing when no file exists", "living_tables.py",
     'return {"fetched_at": "", "fetched": {}, "tables": {}, "stale": list(KEYS)}', "return None", False),
    ("load() returns nothing when the file is over 30 hours old", "living_tables.py",
     "    now = datetime.datetime.now(datetime.timezone.utc)\n    stale = []\n",
     "    now = datetime.datetime.now(datetime.timezone.utc)\n    stale = []\n"
     "    if (now - datetime.datetime.strptime(d['fetched_at'], '%Y-%m-%dT%H:%M:%SZ').replace("
     "tzinfo=datetime.timezone.utc)).total_seconds() / 3600 > STALE_HOURS:\n        return None\n", False),
    ("load() names no table stale", "living_tables.py", '    d["stale"] = stale\n', '    d["stale"] = []\n', True),
    ("the page builder returns no page for a missing table", "site_build.py",
     "    if not t:\n        body = head", "    if not t:\n        return None\n        body = head", True),
    ("the page never shows the stale mark", "site_build.py",
     'is_stale = spec["key"] in (data.get("stale") or ())', "is_stale = False", True),
    ("the page prints the file's stamp, not the table's own", "site_build.py",
     '(data.get("fetched") or {}).get(spec["key"]) or data.get("fetched_at") or ""', 'data.get("fetched_at") or ""', False),
    ("the stale label runs into the sentence (no closed label)", "site_build.py",
     "<b>Stale data.</b> The source did not answer this build. ", "<b>Stale</b> the source did not answer this build; ", False),
    ("the build skips the ETF page", "site_build.py",
     "            if _got:\n                _u, _html = _got", '            if _got and _spec["key"] != "etf_by_issuer":\n                _u, _html = _got', True),
    ("merge_state drops a table only one side holds", "merge_state.py",
     'if k not in tables or str(mine) > str(fetched.get(k, "")):', 'if k in tables and str(mine) > str(fetched.get(k, "")):', False),
    ("merge_state does not list the file", "merge_state.py", ', "site/data/living-tables.json")', ")", False),
    ("the morning workflow does not stage the file", ".github/workflows/morning-read.yml",
     "          [ -f site/data/living-tables.json ] && git add site/data/living-tables.json\n          for f in",
     "          for f in", False),
    ("the brief workflow's rebase path does not stage the file", ".github/workflows/crypto-news-brief.yml",
     "                  [ -f site/data/living-tables.json ] && git add site/data/living-tables.json\n", "", False),
    ("the brief workflow does not refresh the tables", ".github/workflows/crypto-news-brief.yml",
     "run: timeout 120 python3 living_tables.py || true", "run: echo skipped", False),
]


def run(cwd, extra):
    r = subprocess.run([sys.executable, "scripts/sprint96h_test.py"] + extra, cwd=cwd, capture_output=True, text=True, timeout=1500)
    return [l.strip() for l in r.stdout.splitlines() if "FAIL" in l], r.returncode


def main():
    work = os.path.join(sys.argv[1], "plant-tree")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(HERE, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "publish", "node_modules"))
    n_red = 0
    for name, rel, old, new, build in PLANTS:
        path = os.path.join(work, rel)
        orig = open(path, encoding="utf-8").read()
        assert orig.count(old) == 1, f"plant text not found once in {rel}: {name}"
        open(path, "w", encoding="utf-8").write(orig.replace(old, new))
        try:
            fails, rc = run(work, ["--build", "--build-tree"] if build else [])
        finally:
            open(path, "w", encoding="utf-8").write(orig)
        print(f"PLANT: {name}\n  file {rel}; exit {rc}; {len(fails)} case(s) red")
        for f in fails:
            print("    " + f)
        n_red += 1 if fails else 0
    # the committed data: the file as it was before the seed (no ETF table), the shipped-data cases must go red
    old = subprocess.run(["git", "show", "487ed9a:site/data/living-tables.json"], cwd=HERE, capture_output=True, text=True).stdout
    path = os.path.join(work, "site/data/living-tables.json")
    orig = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(old)
    try:
        fails, rc = run(work, ["--build", "--build-tree"])
    finally:
        open(path, "w", encoding="utf-8").write(orig)
    print(f"PLANT: the committed living-tables.json is the Sept 14 file with no ETF table (c5f171e's data)\n"
          f"  file site/data/living-tables.json; exit {rc}; {len(fails)} case(s) red")
    for f in fails:
        print("    " + f)
    n_red += 1 if fails else 0
    fails, rc = run(work, ["--build", "--build-tree"])
    print(f"\nRESTORED TREE: exit {rc}; {len(fails)} case(s) red")
    print(f"PLANTS: {len(PLANTS) + 1}, {n_red} went red, restored tree {'green' if rc == 0 else 'RED'}")
    return 0 if n_red == len(PLANTS) + 1 and rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
