#!/usr/bin/env python3
"""U-9 plants for Sprint 9.5b: each guarded thing broken on purpose in a throwaway copy, the test run, the break left in that copy only.
A plant is "red" when scripts/sprint95b_test.py (or its browser half) fails on it. The restore is the untouched repository and tree.
usage: sprint95b_plants.py <repo> <built publish dir> <workdir> <log>      env PLANTS_ONLY=3,4 runs only those numbers"""
import os
import shutil
import subprocess
import sys
import time

repo, tree, work, log = sys.argv[1:5]
SITE = "site/assets/site.css"
SYS = "site/assets/system.css"
# (name, where, file, old, new, browser sections or "" for the unit cases)
PLANTS = [
    ("wrapper: the 1400 rule is gone (the wrapper stays 1080 at 1440)", "repo", SITE, "  .wrap{max-width:1400px}\n", "", ""),
    ("wrapper: the widening starts at 1100 instead of 1280 (a width under the line changes)", "repo", SITE,
     "@media (min-width:1280px){\n  .wrap{max-width:1400px}", "@media (min-width:1100px){\n  .wrap{max-width:1400px}", ""),
    ("under 1280: a 9.5 rule outside the block changes (the home's two-column gap, 40 to 36)", "repo", SYS,
     "grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:0 40px;", "grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:0 36px;", ""),
    ("under 1280: a rule in the block is not behind the 1280 query (the Brief card's margin)", "repo", SYS,
     "body .h-eline{display:none}\n", "body .h-eline{display:none}\nbody .h-band{margin-bottom:19px}\n", ""),
    ("tokens: a raw hex color in the block", "repo", SYS, "  body .h-coin[data-tile=\"ethereum\"]{display:none}\n",
     "  body .h-coin[data-tile=\"ethereum\"]{display:none}\n  body .h-eline .h-w{color:#123456}\n", ""),
    ("markup: the Ether line is not marked data-wide", "repo", "home.py", "<p class=\"h-bline h-eline\" data-eth-line data-wide>", "<p class=\"h-bline h-eline\" data-eth-line>", ""),
    ("markup: the Ether line prints Solana's price", "repo", "home.py", 'eth = snapshot.coin(snap, "ETH")\n    if not isinstance(eth.get("price")', 'eth = snapshot.coin(snap, "SOL")\n    if not isinstance(eth.get("price")', ""),
    ("markup: the Ether line names no source", "repo", "home.py", 'tail = " \\u00b7 ".join(x for x in (["24h"] if chg_html else []) + ([_e(src)] if src else []))',
     'tail = " \\u00b7 ".join(x for x in (["24h"] if chg_html else []))', ""),
    ("markup: the Ether line is drawn before the one stamp (it is not under it)", "repo", "home.py",
     "f'<p class=\"h-live\" id=\"tapeLive\" data-built=\"{_e(asof)}\"{_asof_attr(read)}>as of {_e(asof)}</p>'\n             f'{eth_line(snap)}')",
     "f'{eth_line(snap)}<p class=\"h-live\" id=\"tapeLive\" data-built=\"{_e(asof)}\"{_asof_attr(read)}>as of {_e(asof)}</p>')", ""),
    ("markup: no Ether change prints a fake zero", "repo", "home.py", "chg_html = (change_html(chg, \"h-badge\", ' data-tape-chg=\"ethereum\"')\n                if isinstance(chg, (int, float)) else \"\")",
     "chg_html = change_html(chg if isinstance(chg, (int, float)) else 0.0, \"h-badge\", ' data-tape-chg=\"ethereum\"')", ""),
    ("markup: no Ether price still draws a line (a blank price)", "repo", "home.py", "    if not isinstance(eth.get(\"price\"), (int, float)):\n        return \"\"\n    chg = eth.get(\"chg_24h_pct\")",
     "    eth = dict(eth, price=eth.get(\"price\") or 0)\n    chg = eth.get(\"chg_24h_pct\")", ""),
    ("script: the tape's script is edited (one character)", "repo", "home.py", "var RM=window.matchMedia", "var  RM=window.matchMedia", ""),
    ("print once: the Ether tile is no longer hidden from 1280", "repo", SYS, "  body .h-coin[data-tile=\"ethereum\"]{display:none}\n", "", ""),
    ("print once: the Ether line is shown at every width (the hide rule is gone)", "repo", SYS, "body .h-eline{display:none}\n", "", ""),
    ("glance board: the left column is not a grid", "repo", SYS, "  body .h-l{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:36px;align-content:start}\n", "", ""),
    ("edition: the Edition's own 1080 sheet is not widened", "tree", "edition/2026-10-19.html", "@media(min-width:1280px){.ed-sheet{max-width:1400px}}", "", "tree"),
    ("beacon: the home loses the analytics beacon", "tree", "index.html", "data-cf-beacon=", "data-cf-beacon-x=", "5"),
    ("browser: the built wrapper is 1200 at 1440", "tree", "assets/site.css", "  .wrap{max-width:1400px}\n", "  .wrap{max-width:1200px}\n", "1"),
    ("browser: the Ether tile stays drawn at 1280 (Ether prints twice)", "tree", "assets/system.css", "  body .h-coin[data-tile=\"ethereum\"]{display:none}\n", "", "3"),
    ("browser: the grid is gone, the Brief card falls below the first screen (grid row 12)", "tree", "assets/system.css", "  body .h-l>[data-block=\"narrative\"]{grid-column:1;grid-row:3;align-self:start}\n",
     "  body .h-l>[data-block=\"narrative\"]{grid-column:1;grid-row:12;align-self:start}\n", "2"),
    ("browser: the Ether line is shown at 375 (display:flex at every width)", "tree", "assets/system.css", "body .h-eline{display:none}\n", "body .h-eline{display:flex}\n", "3"),
    ("browser: a 9.5 rule moves under 1280 (the Brief card's bottom margin, 18 to 19)", "tree", "assets/system.css", "body .h-band{margin-bottom:18px}", "body .h-band{margin-bottom:19px}", "3"),
    ("browser: the stamp takes a padding when the live price lands, at 1440 (a shift)", "tree", "assets/system.css", "  body .h-tape .h-live{grid-column:1 / -1;grid-row:2;max-width:none}\n",
     "  body .h-tape .h-live{grid-column:1 / -1;grid-row:2;max-width:none}\n  body .h-live.on{padding-bottom:40px}\n", "4"),
    ("browser: the prose cap is gone (paragraphs stretch to 1356 px)", "tree", "assets/site.css", "  body :is(p,li,dd,blockquote,figcaption){max-width:62ch}\n", "", "6"),
    ("browser: the wide charts are not capped (labels swell to 27 px)", "tree", "assets/site.css", "  .rc-w>svg{max-width:1040px!important;margin-left:auto;margin-right:auto}\n", "", "6"),
    ("browser: the Whale Watch chart keeps 13 unit labels (11 px at 1280)", "tree", "assets/site.css", "  .board-grid .chartcard svg .ax,.board-grid .chartcard svg .sym,.board-grid .chartcard svg .val{font-size:15px}\n", "", "6"),
    ("browser: the coin chart's caption is capped like prose (its rewrite moves the page at 1440)", "tree", "assets/site.css", "  body .cc-cap{max-width:none}\n", "", "7"),
]

lines = ["Sprint 9.5b, U-9: a copy of the repository or of a built tree, one break planted in it, the test run (unit, or the browser half's sections). "
         + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
ONLY = [int(x) for x in os.environ.get("PLANTS_ONLY", "").split(",") if x]
red = 0
ran = 0
for i, (name, where, rel, old, new, sec) in enumerate(PLANTS, 1):
    if ONLY and i not in ONLY:
        continue
    d = os.path.join(work, f"p{i}")
    shutil.rmtree(d, ignore_errors=True)
    src = repo if where == "repo" else tree
    shutil.copytree(src, d, ignore=shutil.ignore_patterns(".git", "publish") if where == "repo" else None)
    p = os.path.join(d, rel)
    s = open(p, encoding="utf-8").read()
    if old not in s:
        lines.append(f"PLANT {i} {name}: NOT APPLIED (text not found in {rel})")
        continue
    open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
    env = dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(work, f"pyc{i}"), SITE_BUILD_NOW="2026-10-20T07:20:00Z")
    if where == "repo":
        cmd = [sys.executable, os.path.join(d, "scripts", "sprint95b_test.py")]
        cwd = d
    elif sec == "tree":
        cmd = [sys.executable, os.path.join(repo, "scripts", "sprint95b_test.py"), "--tree", d]
        cwd = repo
        env["S95B_ONLY"] = "0"            # the browser half runs no section: this plant is read by the tree cases
    else:
        cmd = [sys.executable, os.path.join(repo, "scripts", "sprint95b_test.py"), "--tree", d]
        cwd = repo
        env["S95B_ONLY"] = sec
        env["S95B_N"] = "2"
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=3000)
    out = r.stdout + r.stderr
    fl = [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ") or ln.startswith("FAIL ")]
    ran += 1
    if r.returncode != 0 and fl:
        red += 1
        lines.append(f"PLANT {i} {name}: RED ({len(fl)} failing line(s)); first: {fl[0][:230]}")
    else:
        lines.append(f"PLANT {i} {name}: NOT RED (exit {r.returncode}); the test did not catch it")
    shutil.rmtree(d, ignore_errors=True)
    print(lines[-1], flush=True)
lines.append(f"PLANTS: {red} of {ran} red")
open(log, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(lines[-1])
