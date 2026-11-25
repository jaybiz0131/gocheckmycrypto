#!/usr/bin/env python3
"""C-DONE (November 2026): the cases this session's items are held to, one group per item, each seen red first.

  1. The home's left column at 1280 and up: every block it can carry has its own cell. The Why Bitcoin moved paragraph
     (Sprint A's "lead" block) was added after the desktop board's grid was written and had no place in it, so the
     browser put it in the first free cell: the top left, above the price line, with an empty cell beside it.
  2. The Netlify ignore rule (U-11): a commit of documents, review screenshots, reports or workflow files alone never
     builds the site. review/ and .github/ were not on the list, so a commit of either alone spent a production build.

Stdlib only.
  python3 scripts/cdone_test.py      # exit 1 on any failure, every failing case named
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
SYSTEM_CSS = os.path.join(HERE, "site", "assets", "system.css")

# the blocks home.py can put in the left column, in the order it writes them (home.LEFT, with "lead" after the Brief card)
LEFT_ORDER = ("tape", "narrative", "lead", "since", "why", "wire")
FIRST_COLUMN = ("narrative", "lead", "why", "wire")


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:120]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def read(p):
    return open(p, encoding="utf-8").read()


def left_cells(css):
    """{block: (column text, first row, last row)} for each .h-l block placed from 1280 px, read from the desktop board's rules."""
    import sprint95b_test as s
    _rest, blk = s.block_of(css)
    cells = {}
    for conds, sel, body in s.flatten(blk or ""):
        if not any("min-width:1280px" in c for c in conds):
            continue
        m = re.search(r'\.h-l>\[data-block="([a-z]+)"\]', sel)
        if not m:
            continue
        col = re.search(r"grid-column:\s*([^;]+)", body)
        row = re.search(r"grid-row:\s*(\d+)(?:\s*/\s*span\s+(\d+))?", body)
        if col and row:
            first = int(row.group(1))
            cells[m.group(1)] = (col.group(1).strip(), first, first + int(row.group(2) or 1) - 1)
    return cells


def lead_place_cases(fails):
    print("1. the home's left column from 1280: every block has its own cell")
    import home
    cells = left_cells(read(SYSTEM_CSS))
    guarded(fails, "the block list here is home.py's own (home.LEFT with the lead after the Brief card)",
            lambda: tuple(b for b in LEFT_ORDER if b != "lead") == tuple(home.LEFT) and '_block("lead"' in read(os.path.join(HERE, "home.py")))
    for name in LEFT_ORDER:
        guarded(fails, f"'{name}' is placed by a rule (a column and a row), never left to the browser's first free cell",
                lambda name=name: name in cells)
    guarded(fails, "in the first column the blocks keep the page's own order, one row each, below the price line: Brief card, Why Bitcoin moved, the wire",
            lambda: all(cells[b][0] == "1" for b in FIRST_COLUMN)
            and [cells[b][1] for b in FIRST_COLUMN] == sorted({cells[b][1] for b in FIRST_COLUMN})
            and cells["narrative"][1] > cells["tape"][1] and all(cells[b][1] == cells[b][2] for b in FIRST_COLUMN))
    guarded(fails, "Where Bitcoin stands fills the second column beside all of them (its rows run from the Brief card's to the wire's)",
            lambda: cells["since"][0] == "2" and cells["since"][1] == cells["narrative"][1] and cells["since"][2] == cells["wire"][1])


def ignore_rule_cases(fails):
    print("2. the ignore rule: documents, review screenshots, reports and workflow files never build the site")
    import netlify_ignore as ni
    no_build = ("docs/REPORTS/C-DONE-REPORT.md", "docs/REPORTS/C-DONE-shots/home-375-before.png", "docs/HANDOFF.md",
                "review/sprint-9-5b/home-1440.png", "review/c-done/board-375.png", ".github/workflows/health.yml",
                "shots/a.png", "scripts/cdone_test.py", "HANDOFF-2026-08-17.md")
    builds = ("site_build.py", "market_pulse.py", "netlify.toml", "site/assets/system.css", "site/content/2026-11-24-evening-brief.json",
              "learn/what-is-bitcoin.md", "scripts/og_render.py", "site/data/pulse.json", "home.py")
    for p in no_build:
        guarded(fails, f"a commit of {p} alone does not build", lambda p=p: ni.decide([p])[0] is True)
    for p in builds:
        guarded(fails, f"a commit of {p} still builds", lambda p=p: ni.decide([p])[0] is False)
    guarded(fails, "a commit of a report beside a site file still builds (one site file is enough)",
            lambda: ni.decide(["docs/REPORTS/C-DONE-REPORT.md", "review/c-done/a.png", "home.py"])[0] is False)
    src = read(os.path.join(HERE, "verify_pipeline.py"))
    m = re.search(r"TOOL_TREES = \(([^)]*)\)", src)
    guarded(fails, "the canary's read recorder walks review/ and .github/ too, so the list is proven against what a build opens",
            lambda: m and '"review/"' in m.group(1) and '".github/"' in m.group(1))


def unit():
    fails = []
    print("C-DONE")
    try:
        lead_place_cases(fails)
        ignore_rule_cases(fails)
    finally:
        for m in ("sprint95b_test", "sprint95b_fixture", "sprint95_test", "sprint94_test", "sprint93_test", "sprint92_test"):
            sys.modules.pop(m, None)
    return fails


if __name__ == "__main__":
    f = unit()
    print("C-DONE:", "FAIL" if f else "PASS", f"({len(f)} failing)" if f else "")
    for x in f:
        print("  FAILING:", x)
    sys.exit(1 if f else 0)
