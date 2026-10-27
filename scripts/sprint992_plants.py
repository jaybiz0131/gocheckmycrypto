#!/usr/bin/env python3
"""U-9 plants for Sprint 9.9.2: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint992_test.py
run (the unit groups), the break undone in that copy from the saved text and the test run again. usage:
sprint992_plants.py <repo> <workdir> <log>"""
import os, shutil, subprocess, sys, time
repo, work, log = sys.argv[1:4]
PLANTS = [
 # the checker (one_fact.py)
 ("checker: two rows of one table count as one fact twice", "one_fact.py",
  "    if a.grid is not None and a.grid is b.grid:\n        return False", "    if False:\n        return False"),
 ("checker: a stored read's own repeats count", "one_fact.py",
  "    if a.read is not None and a.read is b.read:\n        return False", "    if False:\n        return False"),
 ("checker: no subject floor (a row's figure pairs with any line)", "one_fact.py",
  "    if True:\n        for x, y in ((a, b), (b, a)):", "    if False:\n        for x, y in ((a, b), (b, a)):"),
 ("checker: two quantities named differently pair anyway", "one_fact.py",
  '    if a.key[0] == "money" and a.quals != b.quals:\n        return False', '    if False:\n        return False'),
 ("checker: the sign is ignored", "one_fact.py",
  "    if a.sign is not None and b.sign is not None and a.sign != b.sign:", "    if False:"),
 ("checker: the window is ignored", "one_fact.py",
  "    if a.window is not None and b.window is not None and a.window != b.window:", "    if False:"),
 ("checker: data-wide is printed under 1280", "one_fact.py",
  '    if view == "narrow" and n.has("data-wide"):', '    if False:'),
 ("checker: a screen-reader span is counted as printed", "one_fact.py",
  '    if "sr-only" in c or "visually-hidden" in c:', '    if False:'),
 ("checker: one figure at two precisions is two figures", "one_fact.py",
  '    t = f"{v:,.6f}".rstrip("0").rstrip(".")\n    return t', '    return num'),
 ("checker: zeros are counted", "one_fact.py", "    return not re.sub(r\"[^1-9]\", \"\", num)", "    return False"),
 ("checker: a printed correction is read for figures", "one_fact.py", '    return n.has("data-quote")', "    return False"),
 ("checker: the 200-day average is not read as one value per page", "one_fact.py",
  'AVERAGES = (("200-day average", re.compile(r"200-day")),', 'AVERAGES = (("200-day average", re.compile(r"NO-SUCH-LABEL")),'),
 ("checker: the precision row rule never fires", "one_fact.py", "            if len(decs) > 1:", "            if False:"),
 ("checker: the stored-precision rule never fires", "one_fact.py",
  '        pads = {f"${v:,.{p}f}" for p in range(max(d, 2) + 1, 7)}', "        pads = set()"),
 ("checker: the next slot's time is not read", "one_fact.py",
  'NEXT_SLOT = re.compile(r"\\bNext\\b', 'NEXT_SLOT = re.compile(r"\\bNEVERNEXT\\b'),
 # the home
 ("home: the list's Ether item is not the narrow one", "home.py", '        tile_attr += " data-narrow"', "        pass"),
 ("home: the morning card withholds nothing", "home.py",
  '    return [x for x in (sentences or []) if not one_fact.twins_between(f"<p>{_e(x)}</p>", rest)]',
  "    return list(sentences or [])"),
 ("home: the Brief card's next line never yields to the notice", "home.py",
  'show_next=kind not in ("next_read", "no_read") or not card)', "show_next=True)"),
 ("home: the wire prints the checked item's line again", "home.py",
  'line = "The top story, checked, above." if checked and why_shown else _e(w["line"])', 'line = _e(w["line"])'),
 ("home: the week's labels and 24-hour pair at whole dollars again", "home.py",
  "f'{word} <b>{_e(fmt(vals[i]))}</b></span>')", "f'{word} <b>{_e(_whole(vals[i]))}</b></span>')"),
 # the coin pages
 ("coin: the 24-hour tile is back", "coinpage.py", "    if c24 is not None and not price:", "    if c24 is not None:"),
 ("coin: the chart header prints the 7-day figure again", "site_build.py",
  "        chg_html = f'<p class=\"cc-chg\" data-dir=\"{up}\">Over the last 7 days</p>'",
  "        chg_html = f'<p class=\"cc-chg\" data-dir=\"{up}\">{esc(_cp.signed_pct(chg))} over the last 7 days</p>'"),
 ("coin: the volume row is back under Supply and trade", "site_build.py",
  "    # SPRINT 9.9.2: the 24-hour volume prints once, on its Readings tile, not again here\n",
  "    if c.get(\"volume_24h\"):\n        rows.append((\"24-hour volume\", esc(fmt_usd(c[\"volume_24h\"]))))\n"),
 ("coin: the levels card prints every level again", "coinpage.py", "    on_page = set()\n    if c.get(\"price\"):",
  "    on_page = set()\n    if False:"),
 ("coin: the levels card's age is not said", "coinpage.py",
  '    return f"This is {n} {unit}{\'\' if n == 1 else \'s\'} old; the readings above are newer."', '    return ""'),
 ("coin: 'from the last build' is back", "site_build.py",
  "            note += f'<span class=\"cn-stamp\">{esc(_rw[:1].upper() + _rw[1:])}</span>'",
  "            note += '<span class=\"cn-stamp\">from the last build</span>'"),
 # precision
 ("precision: a stored rounding is taken as the figure (padded)", "snapshot.py",
  "    if not isinstance(px, (int, float)) or px >= 1 or round(v, 2) != v or v == 0:\n        return v",
  "    if True:\n        return v"),
 ("precision: market_pulse rounds the averages to the cent again", "market_pulse.py",
  '"sma50": round(s50, 2 if s50 >= 100 else 6), "sma200": round(s200, 2 if s200 >= 100 else 6),',
  '"sma50": round(s50, 2), "sma200": round(s200, 2),'),
 ("precision: the Chart Master's table prints the stored rounding", "site_build.py",
  "            v = level(lv, k)\n            if v is None and isinstance(lv.get(k), (int, float)):",
  "            v = lv.get(k)\n            if v is None and isinstance(lv.get(k), (int, float)):"),
 # /today/
 ("today: the lists never yield to the answer", "today.py",
  "    return bool(keys) and keys <= said", "    return False"),
 ("today: the answer withholds nothing the evidence prints", "today.py",
  "    return kept or answer", "    return answer"),
 ("today: the footer's next update never yields to the notice", "today.py",
  "    if 'class=\"vd vd-next\"' in vd_html:\n        nxt = \"\"", "    if False:\n        nxt = \"\""),
 ("today: a correction is not marked as a quotation", "today.py", 'class="td-corr" data-quote>', 'class="td-corr">'),
 ("today: the answer withholds nothing the reported list prints", "today.py",
  'answer_sentences(rec["answer"], ev_html + rep)', 'answer_sentences(rec["answer"], ev_html)'),
 ("charts: the data card's age line is not drawn", "site_build.py",
  '  {newer_note}\n  <article class="pulse-card cm-read cm-datacard">', '  <article class="pulse-card cm-read cm-datacard">'),
 ("flows: the 13-week list's newest week prints the 7-day net again", "site_build.py",
  '        _newest_said = "the 7 days above"', '        _newest_said = ""'),
 # the tree
 ("tree: 9.9.1's browser half writes through to the real dated writers", "scripts/sprint991_test.py",
  "        sb.SNAPSHOT_DIR, sb.CM_ARCHIVE = os.path.join(scratch, \"snapshots\"), os.path.join(scratch, \"chartmaster\")\n        yield scratch",
  "        yield scratch"),
 ("tree: btc_hilo_test's build leaves what it added", "scripts/btc_hilo_test.py",
  "                if p not in saved:", "                if False:"),
 ("tree: K-1 reads the working copy's site/publish again", "verify_pipeline.py",
  "    return _where_is_news_tree(tree, fails) if tree else fails", "    return _where_is_news_tree(tree or _sb5.PUBLISH, fails)"),
 # the words
 ("words: 'not read for this hour' again", "why_evidence.py", "not compared for this hour: ", "not read for this hour: "),
 ("words: a not-read source listed as often as it was refused", "why_evidence.py",
  '    return m.group(1) + "; ".join(dict.fromkeys(parts)) + m.group(3)', '    return why'),
 ("words: every link is cited, whatever its address", "wire.py",
  "    if len(keep) == len(links):\n        return w", "    if True:\n        return w"),
 ("words: the verdict page does not name which window is which", "verdict.py",
  '    _note = list_note(lead, ev, sym) if ev_html else ""', '    _note = ""'),
]


def run(cwd):
    r = subprocess.run([sys.executable, "scripts/sprint992_test.py"], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(cwd, ".pyc-" + str(time.time()))))
    out = r.stdout + r.stderr
    return r.returncode, [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ")]


shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
lines = ["Sprint 9.9.2, U-9: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint992_test.py run, the "
         "same copy run again with the break undone from the saved text (never git checkout). Fresh copy per plant. "
         + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
red = 0
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
    red += 1 if (rc and fails and not rc2) else 0
    lines.append(f"PLANT {i} {name} ({rel}): exit {rc}, {len(fails)} red; restored: exit {rc2}, {len(fails2)} red")
    for f in fails[:5]:
        lines.append("      " + f[:220])
    if len(fails) > 5:
        lines.append(f"      ... and {len(fails) - 5} more")
    print(lines[-1 - min(len(fails), 5) - (1 if len(fails) > 5 else 0)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
lines.append(f"PLANTS: {len(PLANTS)}, red when broken and green when restored: {red}")
open(log, "w").write("\n".join(lines) + "\n")
print(lines[-1])
