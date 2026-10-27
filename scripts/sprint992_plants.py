#!/usr/bin/env python3
"""U-9 plants for Sprint 9.9.2: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint992_test.py run
(with --production), the break undone in that copy from the saved text and the test run again. Fresh copy per plant.
usage: sprint992_plants.py <repo> <workdir> <log>"""
import os, shutil, subprocess, sys, time
repo, work, log = sys.argv[1:4]
PLANTS = [
 # the check itself
 ("sweep: the width model reads no stylesheet (every element printed at every width)", "fact_sweep.py",
  "        sheet = Sheet(css_texts, w)\n        nodes = [(t, e) for t, e in printed(dom, sheet) if not in_prose(e)]",
  "        sheet = Sheet([], w)\n        nodes = [(t, e) for t, e in printed(dom, sheet) if not in_prose(e)]"),
 ("sweep: two rows are no longer two subjects", "fact_sweep.py",
  "    if ra is not None and rb is not None and ra is not rb:\n        return True", "    if False:\n        return True"),
 ("sweep: the sign is not part of the fact", "fact_sweep.py",
  "        if self.sign and other.sign and self.sign != other.sign:", "        if False and self.sign != other.sign:"),
 ("sweep: the window is not part of the fact", "fact_sweep.py",
  "        if self.window and other.window and self.window != other.window:", "        if False:"),
 ("sweep: stored writing is read as data (PROSE empty)", "fact_sweep.py",
  "def in_prose(e):\n    \"\"\"Inside stored writing", "def in_prose(e):\n    return False\n    \"\"\"Inside stored writing"),
 ("sweep: the label check never reports", "fact_sweep.py", "            if len(vals) > 1:\n                findings.append((\"label\"",
  "            if False:\n                findings.append((\"label\""),
 ("sweep: the row precision check never reports", "fact_sweep.py", "            if len(decs) > 1:", "            if False:"),
 ("sweep: a padded average is not judged", "fact_sweep.py",
  '            padded = dec > 2 and re.fullmatch(r"\\d*\\.\\d\\d0+", num) is not None', "            padded = False"),
 ("sweep: the next slot's time is never counted", "fact_sweep.py", "            if k > 1:\n                findings.append((\"next\"",
  "            if False:\n                findings.append((\"next\""),
 ("sweep: 'from the last build' passes", "fact_sweep.py", '        if re.search(r"\\bfrom the last build\\b", vis):', "        if False:"),
 ("sweep: an axis tick is a fact again", "fact_sweep.py", "        facts = [f for f in figs if id(f) not in ticks and significant(f)]",
  "        facts = [f for f in figs if significant(f)]"),
 # the coin pages
 ("coin page: the price tile's since line repeats the 24 hours again", "coinpage.py",
  'change=c24, since=_since("30 days", c30) or "30 days: not reported", since_change=c30)',
  'change=c24, since=_since("24 hours", c24) or "24 hours: not reported", since_change=c24)'),
 ("coin page: the 7-day tile comes back", "coinpage.py",
  "    if mcap:\n        add(\"coin-cap\"",
  "    if c7 is not None:\n        add(\"coin-7d\", signed_pct(c7), window=\"Rolling 7 days\", direction=_dir(c7), since=\"x\")\n    if mcap:\n        add(\"coin-cap\""),
 ("coin page: the levels card prints the levels the readings print", "coinpage.py",
  '        if isinstance(row.get(k), (int, float)) and k not in shown:', '        if isinstance(row.get(k), (int, float)):'),
 ("coin page: the levels card is headed by its date alone", "coinpage.py",
  "            f'<h2 class=\"cn-h\">Chart levels, {esc(when) if when else esc(fmt_date(day))}</h2>'",
  "            f'<h2 class=\"cn-h\">Chart levels for {esc(name)}, {esc(fmt_date(day))}</h2>'"),
 ("coin page: Supply and trade prints the volume again", "site_build.py",
  "    if c.get(\"volume_24h\") and volume:", "    if c.get(\"volume_24h\"):"),
 ("coin page: the caption says 'from the last build' again", "site_build.py",
  "        note += f'<span class=\"cn-stamp\">{esc(_rs) + \".\" if _rs else \"Time of read not recorded.\"}</span>'",
  "        note += '<span class=\"cn-stamp\">from the last build</span>'"),
 ("an average is printed at its own decimals, not its price's", "site_build.py",
  "    if not isinstance(v, (int, float)) or not isinstance(ref, (int, float)) or not ref or _compressed(ref):\n        return _price_fmt(v)",
  "    if True:\n        return _price_fmt(v)"),
 ("the build prints the stored two-decimal averages as stored", "site_build.py",
  "            pulse = dict(pulse, assets=_h.precise_assets(pulse[\"assets\"]))", "            pass"),
 ("history: a re-read average is taken without rounding back to the stored figure", "history.py",
  "    if round(a, max(_decimals(stored), 0)) != round(float(stored), max(_decimals(stored), 0)):\n        return None",
  "    if False:\n        return None"),
 ("market_pulse: averages stored at two decimals again", "market_pulse.py",
  '"sma50": round(s50, 2 if last >= 100 else 6), "sma200": round(s200, 2 if last >= 100 else 6),', '"sma50": round(s50, 2), "sma200": round(s200, 2),'),
 ("Chart Master table: an average at its own precision, not its row's", "site_build.py",
  "            ref = v if ref is None else ref", "            ref = v"),
 ("Chart Master table: the RSI-14 header loses its no-wrap class", "site_build.py",
  '<th scope="col" class="xs-x" style="white-space:nowrap">RSI-14</th>', '<th scope="col" class="xs-x">RSI-14</th>'),
 ("Chart Master page: the read is headed by its date alone", "site_build.py",
  '    read_title = f"The chart read, {_rst or _md}" if _md else "The chart read"', '    read_title = f"The chart read, {_md}" if _md else "The chart read"'),
 # /today/ and the home
 ("today: What moved lists the answer's figures again", "today.py", "    if answer is None:\n        return False", "    if True:\n        return False"),
 ("home: the Brief card repeats the notice's next time", "home.py", "        if card and f\"Next read: {when}\" in card:", "        if False:"),
 ("today: the footer repeats the notice's next time", "today.py", "    if _m and f\"Next read: {_m.group(1)}\" in (vd_html or \"\"):", "    if False:"),
 ("home: a top-20 mover past 5% is named again in the line under the list", "home.py",
  '    stand = [c for c in stand_all if c.get("symbol") not in listed]', "    stand = stand_all"),
 # Whale Watch and Markets
 ("flows: the stat prints the net the line states", "site_build.py",
  '    elif ww.get("net") is not None and fmt_usd(abs(net)) in ww["sentence"]:', "    elif False:"),
 ("flows: the 'Biggest single move' stat comes back", "site_build.py",
  '    big_html = ""\n', '    big_html = \'<div class="stat"><span class="lab">Biggest single move</span></div>\'\n'),
 ("ledger: the newest week reprints the line's net", "site_build.py",
  "if not (newest and said and fmt_usd(abs(val)) in said)", "if True"),
 ("the Board's line quotes the whale figure again", "site_build.py",
  "        bits.append(f\"whales net {'onto' if vol['net_usd'] < 0 else 'off'} exchanges over \"",
  "        bits.append(f\"{fmt_usd(abs(vol['net_usd']))} {'onto' if vol['net_usd'] < 0 else 'off'} exchanges over \""),
 # the evidence
 ("evidence: the run's ends print their prices again", "why_evidence.py", "            if t == _hi:", "            if False:"),
 ("evidence: an unchanged reading prints as 'X to X'", "why_evidence.py",
  "                   if f'{r[\"from_pct\"]:.1f}' == f'{r[\"to_pct\"]:.1f}' else", "                   if False else"),
 ("evidence: a stored unread list prints its repeats", "why_evidence.py", '    k = t.find("not read: ")\n    if k < 0:', '    k = -1\n    if k < 0:'),
 ("evidence: the uncompared reading says 'not read for this hour' again", "why_evidence.py",
  "not compared for this window: {_e(r[\"why\"])}", "not read for this hour: {_e(r[\"why\"])}"),
 ("evidence: every link is matched", "why_evidence.py", "    return bool(have & words)", "    return True"),
 ("evidence: the common-word floor is empty (a shallow key matches)", "why_evidence.py",
  "    _COMMON[d] = frozenset(w for w, k in cnt.items() if k >= floor)", "    _COMMON[d] = frozenset()"),
 ("verdict: an unmatched source counts toward the grade", "verdict.py", "        n = _we().counted_sources(c)", '        n = int(c.get("source_count") or 0)'),
 ("K-1: the tree half reads site_build.PUBLISH again", "verify_pipeline.py",
  "    _pub = pub\n    _nh = os.path.join(_pub, \"news.html\")", "    _pub = _sb5.PUBLISH\n    _nh = os.path.join(_pub, \"news.html\")"),
 ("article: an {outlet, headline} entry prints raw again", "site_build.py",
  '    also = [str(x.get("outlet") or "") if isinstance(x, dict) else str(x) for x in (item.get("also_reported_by") or [])]',
  '    also = [str(x) for x in (item.get("also_reported_by") or [])]'),
 ("fixture: the production copy's stamp is altered (it must be deploy f9de9c2 byte for byte)", "fixtures/sprint992/production-f9de9c2/stamp.txt",
  "commit f9de9c258158479bbc8be01721613dbab54f38fc", "commit 0000000000000000000000000000000000000000"),
]


def run(cwd):
    r = subprocess.run([sys.executable, "scripts/sprint992_test.py", "--production"], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(cwd, ".pyc-" + str(time.time()))))
    out = r.stdout + r.stderr
    return r.returncode, [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ")]


shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
lines = ["Sprint 9.9.2, U-9: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint992_test.py --production "
         "run, the same copy run again with the break undone from the saved text. Fresh copy per plant. "
         + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
for i, (name, rel, old, new) in enumerate(PLANTS, 1):
    d = os.path.join(work, f"p{i}")
    os.makedirs(d)
    subprocess.run("tar --exclude=./.git --exclude=./site/publish --exclude=./review --exclude=__pycache__ -cf - . | (cd %s && tar xf -)" % d,
                   shell=True, cwd=repo, check=True)
    p = os.path.join(d, rel)
    s = open(p, encoding="utf-8").read()
    if s.count(old) != 1:
        lines.append(f"PLANT {i} {name}: NOT APPLIED ({s.count(old)} matches of the line to break)")
        print(lines[-1], flush=True)
        shutil.rmtree(d, ignore_errors=True)
        continue
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    rc, fails = run(d)
    open(p, "w", encoding="utf-8").write(s)
    rc2, fails2 = run(d)
    lines.append(f"PLANT {i} {name} ({rel}): exit {rc}, {len(fails)} red; restored: exit {rc2}, {len(fails2)} red")
    for f in fails[:4]:
        lines.append("      " + f[:220])
    if len(fails) > 4:
        lines.append(f"      ... and {len(fails) - 4} more")
    print(lines[-1 - min(4, len(fails)) - (1 if len(fails) > 4 else 0)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
open(log, "w").write("\n".join(lines) + "\n")
print("done")
