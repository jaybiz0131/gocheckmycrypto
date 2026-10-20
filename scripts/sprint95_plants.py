#!/usr/bin/env python3
"""U-9 plants for Sprint 9.5: each guarded thing broken on purpose in a throwaway copy of the tree, the tests run,
the break left in that copy only. usage: plants.py <repo> <workdir> <log>"""
import os, re, shutil, subprocess, sys, time
repo, work, log = sys.argv[1:4]
PLANTS = [
 ("names: the Markets page takes its brand name back (NAMES['markets'] second name 'The Board')", "site_build.py",
  '"markets": ("Markets", "", "/pulse.html"),', '"markets": ("Markets", "The Board", "/pulse.html"),'),
 ("names: Whale Watch is 'Flows' again in the one table", "site_build.py",
  '"flows":   ("Whale Watch", "", "/flows.html"),', '"flows":   ("Flows", "", "/flows.html"),'),
 ("names: the Record is 'Worth keeping' again", "site_build.py",
  '"record":  ("Storylines", "", "/record.html"),', '"record":  ("Worth keeping", "", "/record.html"),'),
 ("nav: the why leaves the desktop nav", "site_build.py",
  '       ("why",) + NAMES["why"],\n', ''),
 ("tab bar: the old five (Markets, Flows, Charts, News, Brief)", "site_build.py",
  '    ("why", "M4 5h12v8H9l-3 3v-3H4zM7 8h6M7 10.5h4"),          # a speech card\n', ''),
 ("tab bar: a sixth tab (Charts) is added", "site_build.py",
  '    ("brief", "M5 3h10v14H5zM8 7h4M8 10h4M8 13h3"),           # the brief\n]', '    ("brief", "M5 3h10v14H5zM8 7h4M8 10h4M8 13h3"),           # the brief\n    ("charts", "M3 17h14M5 13l3-4 3 2 5-6"),\n]'),
 ("front: the verdict card moves back under the Brief card (the 9.3 place)", "home.py",
  '    if graded:\n        left = card + "".join(blocks[k] for k in LEFT)', '    if graded:\n        left = "".join(blocks[k] + (card if k == "narrative" else "") for k in LEFT)'),
 ("front: Bitcoin's whole card (chart, range, tiles) goes back into the tape", "home.py",
  "    return _block(\"tape\", inner)\n\n\ndef bitcoin_card(snap):", "    return _block(\"tape\", inner + bitcoin_card(snap))\n\n\ndef bitcoin_card(snap):"),
 ("front: a withheld notice leads the home", "home.py",
  'left = blocks["tape"] + card + "".join(blocks[k] for k in LEFT[1:])', 'left = card + "".join(blocks[k] for k in LEFT)'),
 ("home: 'Related data:' is 'Reads with' again", "home.py",
  "bits.append(f'Related data: {_e(_reading(w[\"board_reading\"]))}')", "bits.append(f'Reads with {_e(_reading(w[\"board_reading\"]))}')"),
 ("home: the wire mark is 'Wire' again", "home.py", '<span class="h-wm">Reported</span>', '<span class="h-wm">Wire</span>'),
 ("home: the mood block is 'The mood' again", "home.py", 'return _block("mood", inner, "Sentiment")', 'return _block("mood", inner, "The mood")'),
 ("tiles: 'Whale net' is back on the tile", "tile.py", 'Reading("whale-net", "Whale flows", True,', 'Reading("whale-net", "Whale net", True,'),
 ("tiles: 'Spot ETF net' is back on the tile", "tile.py", 'Reading("etf-net", "ETF flows", True,', 'Reading("etf-net", "Spot ETF net", True,'),
 ("wire: the tag rule names 'Stablecoin float' again", "wire.py", '"stablecoins": "Stablecoin supply",', '"stablecoins": "Stablecoin float",'),
 ("daily answer: the evening slot is 'Evening Edition' again", "today.py", '"evening": "Evening Brief"}', '"evening": "Evening Edition"}'),
 ("pages: the Chart Master's card title is back", "site_build.py", 'f\'<h2 class="cm-card-h">The chart read, {esc(fmt_short_date(day))}</h2>\'', 'f\'<h2 class="cm-card-h">Chart Master\\\'s read, {esc(fmt_short_date(day))}</h2>\''),
 ("pages: Whale Watch's stablecoin line is 'Stablecoin buying power' again", "site_build.py", '<span class="lab">Stablecoins onto exchanges</span>', '<span class="lab">Stablecoin buying power</span>'),
 ("pages: the footer says 'How we work' again", "site_build.py", '("How we check", "/method.html"),', '("How we work", "/method.html"),'),
 ("trust: How we check says the text is written by an AI model", "site_build.py", "<h2>Sourcing</h2>\n  <p>Stories link the sources they draw on.", "<h2>Sourcing</h2>\n  <p>Our stories are drafted by an AI model. Stories link the sources they draw on."),
 ("trust: How we check names a person", "site_build.py", "{esc(EDITOR)} is the desk's editor. The editor sets", "Jack is the desk's editor. The editor sets"),
 ("trust: About says a human editor-in-chief oversees the desk", "site_build.py", "{esc(EDITOR)} is the\n     desk's editor: the editor reviews", "A human editor-in-chief is the\n     desk's editor: the editor reviews"),
 ("corrections: the page invents a date for a correction that has none", "site_build.py", "else \"Correction date not recorded\")", "else \"Corrected September 1, 2026\")"),
 ("brief: /bottom-line.html lists every month on one page again", "site_build.py", "    newest = next(iter(months))\n    return _brief_month_page(newest, months, dateline, newest)", "    newest = next(iter(months))\n    months = {newest: [e for es in months.values() for e in es]}\n    return _brief_month_page(newest, months, dateline, newest)"),
 ("ledger: the card is drawn on a coin that moved past the line", "site_build.py", 'ledger_html = "" if _past_mover_line(c, sym, pulse, movers, _mover) else _coin_cold_storage()', 'ledger_html = _coin_cold_storage()'),
 ("ledger: the card is back above the stories", "site_build.py", "  {stories_html}\n  {unlock_html}\n  {supply_html}\n  {ledger_html}\n", "  {ledger_html}\n  {stories_html}\n  {unlock_html}\n  {supply_html}\n"),
 ("charts: the timing chart's labels go back to 11.5 units in a 420 box", "why_evidence.py", "CHART_W, CHART_H, CHART_X0, CHART_X1 = 340, 200, 62, 332\nLABEL_FS = 12.5", "CHART_W, CHART_H, CHART_X0, CHART_X1 = 420, 216, 62, 410\nLABEL_FS = 11.5"),
 ("charts: the home chart's labels go back to 10.5 px", "site/assets/system.css", "body .h-chart .h-k{font-size:12px}", "body .h-chart .h-k{font-size:10.5px}"),
 ("tables: the shared rule loses its toggle", "site/assets/system.css", ".fit-cb:checked+.fit-more+.fit-tbl .xs-x{display:table-cell}", ".fit-cb:checked+.fit-more+.fit-tbl .xs-x{display:none}"),
 ("tables: the Big movers list drops its xs-x columns", "movers.py", '<td class="xs-x">{_e(exc)}</td>', '<td>{_e(exc)}</td>'),
 ("chart box: the coin chart's head loses its reserved room", "site/assets/system.css", ".cc-head{min-height:44px}", ".cc-head{min-height:0}"),
]
def run(cwd, extra=()):
    t = time.time()
    r = subprocess.run([sys.executable, "scripts/sprint95_test.py", *extra], cwd=cwd, capture_output=True, text=True)
    out = r.stdout + r.stderr
    fails = [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ")]
    return r.returncode, fails, time.time() - t
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
lines = ["Sprint 9.5, U-9: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint95_test.py run, "
         "the same copy run again with the break undone. Fresh copy per plant. " + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
for i, (name, rel, old, new) in enumerate(PLANTS, 1):
    d = os.path.join(work, f"p{i}")
    os.makedirs(d)
    subprocess.run("tar --exclude=./.git --exclude=./site/publish --exclude=./review --exclude=__pycache__ -cf - . | (cd %s && tar xf -)" % d, shell=True, cwd=repo, check=True)
    p = os.path.join(d, rel)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        lines.append(f"PLANT {i} {name}: NOT APPLIED ({s.count(old)} matches of the line to break)")
        print(lines[-1]); continue
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    rc, fails, secs = run(d)
    open(p, "w", encoding="utf-8").write(s)
    rc2, fails2, _ = run(d)
    lines.append(f"PLANT {i} {name} ({rel}): exit {rc}, {len(fails)} red; restored: exit {rc2}")
    for f in fails[:6]:
        lines.append("      " + f[:230])
    if len(fails) > 6:
        lines.append(f"      ... and {len(fails) - 6} more")
    print(lines[-1] if not fails else lines[-len(fails[:6]) - (2 if len(fails) > 6 else 1)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
open(log, "w").write("\n".join(lines) + "\n")
print("done")
