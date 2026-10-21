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
 ("review 1: the lanes say 'in the Record' again", "site_build.py", 'f"{len(lane_items)} in Storylines · newest', 'f"{len(lane_items)} in the Record · newest'),
 ("review 1: the news page links 'Record: what stays true'", "site_build.py", "'<a href=\"/record.html\">Storylines: what stays true", "'<a href=\"/record.html\">Record: what stays true"),
 ("review 1: the table pages' breadcrumb is 'Record /' again", "site_build.py", '<a href="/record.html">{esc(task_name("record"))}</a> / {esc(spec["title"])}', '<a href="/record.html">Record</a> / {esc(spec["title"])}'),
 ("review 1: the Brief card's line says 'spot ETF net' again", "narrative.py", '("etf_net_usd_m", "ETF flows")', '("etf_net_usd_m", "spot ETF net")'),
 ("review 1: the stablecoin page's explainer is 'Dry powder 101' again", "site_build.py", "<h2>Stablecoin supply 101</h2>", "<h2>Dry powder 101</h2>"),
 ("review 1: the Learn page says Markets calls it dry powder again", "learn/06-stablecoin-dry-powder.md", "Traders call it dry powder for that reason.", "Markets calls it dry powder for that reason."),
 ("review 1: the chart page's eyebrow is 'The tape' again", "site_build.py", """f'<span class="bd-eyebrow">{esc(task_name("charts"))}</span>'""", """'<span class="bd-eyebrow">The tape</span>'"""),
 ("review 1: How we check shows the example story again", "site_build.py", "    grades = \"\".join(", "    grades = '<p><a href=\"/articles/example-sec-enforcement.html\">Open the example story</a></p>' + \"\".join("),
 ("review 1: the example page says an AI never writes the take", "site/content/example-format.json", "In a real story, the desk's own take sits here, in a sentence or two.", "The AI never writes this line; a person does."),
 ("review 1: the editorial loses its correction", "site/content/0000-why-crypto-cronkite.json", '"corrected": "2026-10-20:', '"corrected_off": "2026-10-20:'),
 ("review 1: the editorial says a person approves what publishes again", "site/content/0000-why-crypto-cronkite.json", "reviews what they produce, and can hold or remove anything.", "reviews what they produce, and a human approves what publishes."),
 ("rulings of Oct 20: the prompt names Whale net again", "prompts/chartmaster.md", "Whale flows direction", "Whale net direction"),
 ("rulings of Oct 20: 25 percent done no longer disqualifies (strictly more than 25)", "verdict.py", '''isinstance(done, (int, float)) and done >= tt["done_max_pct"]):
        return None
    if r.get("before_onset"):''', '''isinstance(done, (int, float)) and done > tt["done_max_pct"]):
        return None
    if r.get("before_onset"):'''),
 ("rulings of Oct 20: the clock measures from the event time again", "why_evidence.py", 'if ev is not None and (c.get("scheduled") or rp is None):', 'if ev is not None:'),
 ("rulings of Oct 20: TIMING_TEST keeps the October 19 version", "why_evidence.py", 'TIMING_TEST = {"version": "2026-10-20"', 'TIMING_TEST = {"version": "2026-10-19"'),
 ("rulings of Oct 20: Likely's definition is the old one-event sentence", "verdict.py", '"Likely": "The reported events that pass the timing test, with the market readings agreeing.",', '"Likely": "One reported event passes the timing test and the market readings agree, with no primary source stating the cause.",'),
 ("rulings of Oct 20: Likely names only the first event that passes", "verdict.py", 'g, grp = ("Confirmed", [prim[0]]) if prim else ("Likely", agree)', 'g, grp = ("Confirmed", [prim[0]]) if prim else ("Likely", agree[:1])'),
 ("rulings of Oct 20: events pointing opposite ways no longer make Disputed", "verdict.py", "if agree and against:", "if False and against:"),
 ("rulings of Oct 20: the readings-mismatch case prints no line of its own", "verdict.py", "top = OTHER_WAY if other_way else READINGS_MISMATCH", "top = NO_EVENT"),
 ("rulings of Oct 20: the other-way case prints the readings line", "verdict.py", "top = OTHER_WAY if other_way else READINGS_MISMATCH", "top = READINGS_MISMATCH"),
 ("rulings of Oct 20: a window that ran the other way prints nothing", "verdict.py", "return f'<p class=\"vd-plain vd-next\">", "return '' and f'<p class=\"vd-plain vd-next\">"),
 ("rulings of Oct 20: a primary flag on a listing confirms", "verdict.py", 'prim = [p for p in agree if p["primary"]]', 'prim = [p for p in agree if p["c"].get("primary")]'),
 ("definitions: Unclear's printed definition is the old 'no event passes' sentence again", "verdict.py", '''"Unclear": "No reported event passes the timing test with the market readings and the move's direction agreeing.",''', '''"Unclear": "No reported event passes the timing test.",'''),
 ("definitions: Disputed leaves out events pointing opposite ways", "verdict.py", '''or "
                "the events that pass point opposite ways.",''', '''or "
                "another passes.",'''),
 ("merge canary: the coin pages check expects the Ledger card on every coin again", "scripts/coin_pages_test.py", "past = f[:-5].lower() in no_ledger", "past = False"),
 ("merge canary: the coin pages check's mover line is 20 percent, not the gate's 10", "scripts/coin_pages_test.py", 'abs(chg) >= mv.GATE["move_min_pct"]', 'abs(chg) >= 20'),
 ("merge canary: the data card's headline names the Chart Master again", "chartmaster.py", '"headline": "Chart data card: levels, 50-day and 200-day lines, RSI"', '"headline": "Chart Master data card: levels, 50-day and 200-day lines, RSI"'),
 ("review 3: the Earlier reads rows print a data card's stored headline again", "site_build.py", "+ ('<p class=\"cm-entry-h\">Levels, 50-day and 200-day lines, RSI</p>' if r.get(\"data_only\") else", "+ ('<p class=\"cm-entry-h\">Levels, 50-day and 200-day lines, RSI</p>' if False else"),
 ("review 3: the canary's stored-read exclusion drops every Earlier reads entry again", "verify_pipeline.py", 'cm-entry" data-date="2026-10-19">', 'cm-entry">'),
 ("review 3: the Earlier reads rows say 'The read' again", "site_build.py", '"Chart data card" if r.get("data_only") else "The chart read"', '"Chart data card" if r.get("data_only") else "The read"'),
 ("review 3: the data card's table loses the shared rule's region (role, label, tabindex)", "site_build.py", 'class="movetable fit-tbl" tabindex="0" role="region" aria-label="Chart data card (scrollable)"', 'class="movetable fit-tbl"'),
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
