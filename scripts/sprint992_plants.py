#!/usr/bin/env python3
"""U-9 plants for Sprint 9.9.2: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint992_test.py run
(with --production), the break undone in that copy from the saved text and the test run again. Fresh copy per plant.
usage: sprint992_plants.py <repo> <workdir> <log> [plant numbers, comma-separated: run only those and append to the log]"""
import os, shutil, subprocess, sys, time
repo, work, log = sys.argv[1:4]
ONLY = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
PLANTS = [
 # the check itself
 ("sweep: the width model reads no stylesheet (every element printed at every width)", "fact_sweep.py",
  "        sheet = Sheet(css_texts, w)\n        nodes = printed(dom, sheet)",
  "        sheet = Sheet([], w)\n        nodes = printed(dom, sheet)"),
 ("sweep: two rows are no longer two subjects", "fact_sweep.py",
  "    if ra is not None and rb is not None and ra is not rb:\n        if ra.tag", "    if False:\n        if ra.tag"),
 ("sweep: the sign is not part of the fact", "fact_sweep.py",
  "        if self.sign and other.sign and self.sign != other.sign:", "        if False and self.sign != other.sign:"),
 ("sweep: the window is not part of the fact", "fact_sweep.py",
  "        if self.window and other.window and self.window != other.window:", "        if False:"),
 # fix round 2 (review 1 at 81b63fa): no exemption for writing, and the tests that hold it
 ("sweep: stored writing is set aside again (81b63fa's prose exemption)", "fact_sweep.py",
  "        sheet = Sheet(css_texts, w)\n        nodes = printed(dom, sheet)",
  "        sheet = Sheet(css_texts, w)\n        nodes = [(t, e) for t, e in printed(dom, sheet) if not in_text(e)]"),
 ("sweep: '$600 million' is not read as $600M", "fact_sweep.py",
  '                f = Fig("$", m.group(2), m.group(3) or MAG_WORD.get((m.group(4) or "").lower()), m.group(0), el, m.start())',
  '                f = Fig("$", m.group(2), m.group(3), m.group(0), el, m.start())'),
 ("sweep: writing pairs by digits alone (a 25% tariff and a 25% stake)", "fact_sweep.py",
  "    if in_text(f.el) or in_text(g.el):\n        return shared_subject(f, g)\n    return True",
  "    if in_text(f.el) or in_text(g.el):\n        return True\n    return True"),
 ("sweep: story cards are two subjects whatever they say (the tile rule)", "fact_sweep.py",
  "        if fa is not None and fb is not None and _has_story(ta) and _has_story(tb):", "        if False:"),
 ("sweep: two list rows on one event are two subjects", "fact_sweep.py",
  "        return not _one_event(fa, fb, ra, rb)", "        return True"),
 ("sweep: a list's own wording counts as a subject", "fact_sweep.py",
  "    return len(shared - _template(ra) - _template(rb)) >= 2", "    return len(shared) >= 2"),
 ("sweep: a headline list's subject words are read as its template", "fact_sweep.py",
  "    if is_head(fa.el) or is_head(fb.el):\n        return len(shared) >= 2", "    if False:\n        return len(shared) >= 2"),
 ("sweep: a chart's printed reading is not read (the RSI gauge)", "fact_sweep.py",
  "            label_text = ctext", "            break\n            label_text = ctext"),
 ("sweep: a table column's readings are not read (the RSI-14 column)", "fact_sweep.py",
  "        cols = {}\n        for i, h in enumerate(head):", "        cols = {}\n        for i, h in enumerate([]):"),
 ("sweep: an unnamed reading beside named ones passes", "fact_sweep.py",
  "            if named and un is not None and not coin:", "            if False:"),
 ("sweep: a value printed before its label is not read (the Sentiment tile's 48)", "fact_sweep.py",
  "        if not b or svg_of(el) is not None:\n            continue", "        if True:\n            continue"),
 ("pass: nothing is withheld", "fact_once.py", '    if "<body" not in src:\n        return src, []', '    if True:\n        return src, []'),
 ("today: a reported line stating the answer's fact is listed again", "today.py",
  '    reported_left = [w for w in reported_left if not any(_fs.one_event(w.get("line") or "", a) for a in _ans)]', "    pass"),
 ("coin page: one event's stories listed twice", "site_build.py",
  '        if any(_fs.one_event(i.get("title") or "", k.get("title") or "") for k in kept):',
  '        if False:'),
 ("Chart Master gauge: prints its number beside the read's", "site_build.py",
  '    label = "" if btc.get("_rsi_read") else (', '    label = "" if False else ('),
 ("Chart Master page: the gauge reads the Board, not the read's BTC row", "site_build.py",
  "        if _lv is not None:\n            _gauge", "        if False:\n            _gauge"),
 ("article: a source's stored title prints the story's figure again", "site_build.py",
  "            if _src_twin(lab) or any(_fs.one_event(lab, x, coarse=True) for x in _src_seen):",
  "            if any(_fs.one_event(lab, x, coarse=True) for x in _src_seen):"),
 ("Edition: a citation's title prints the brief's figure again", "edition.py",
  "    if not any(x.same(y) for x in _fs.figures([(lab, None)]) for y in own):", "    if True:"),
 ("today: a row prints the figure its correction quotes", "today.py",
  '    said = " ".join(list(rec.get("answer") or []) + [str(c.get("text") or "") for c in rec.get("corrections") or []])',
  '    said = " ".join(rec.get("answer") or [])'),
 ("sweep: the label check never reports", "fact_sweep.py", "            if len(vals) > 1:\n                pins =",
  "            if False:\n                pins ="),
 ("sweep: the row precision check never reports", "fact_sweep.py", "            if len(decs) > 1:", "            if False:"),
 ("sweep: a padded average is not judged", "fact_sweep.py",
  '            padded = dec > 2 and re.fullmatch(r"\\d*\\.\\d\\d0+", num) is not None', "            padded = False"),
 ("sweep: the next slot's time is never counted", "fact_sweep.py", "            if k > 1:\n                findings.append((\"next\"",
  "            if False:\n                findings.append((\"next\""),
 ("sweep: 'from the last build' passes", "fact_sweep.py", '        if re.search(r"\\bfrom the last build\\b", vis):', "        if False:"),
 ("sweep: an axis tick is a fact again", "fact_sweep.py",
  "        facts = [f for f in figs if id(f) not in ticks and (significant(f) or in_text(f.el))]",
  "        facts = [f for f in figs if (significant(f) or in_text(f.el))]"),
 ("sweep: two reading tiles are one subject again", "fact_sweep.py",
  "            and not (wa and wb and wa == wb):\n        if fa", "            and False:\n        if fa"),
 ("sweep: a tile's window line is not read", "fact_sweep.py",
  "        if f.window is None and tile_of(f.el) is not None:", "        if False:"),
 ("sweep: a row by its class is not a row", "fact_sweep.py",
  "        rc = {c for c in a.cls if ROW_CLASS.search(c)}", "        rc = set()"),
 ("sweep: the figure's clause does not decide its window", "fact_sweep.py",
  "        f.window = _window_of(clause) if clause and _window_of(clause) else _window_of(sent, at)", "        f.window = _window_of(sent)"),
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
 # fix round 3 (review 2 at 3afc3b4, entry 2026-10-27-C8)
 ("sweep: every pair is one printing (C8's cases widened to all)", "fact_sweep.py",
  "    ua, ub = unit_of(f.el, own), unit_of(g.el, own)\n", "    return \"any pair\"\n    ua, ub = unit_of(f.el, own), unit_of(g.el, own)\n"),
 ("sweep: a stored unit's own repeat is a finding again", "fact_sweep.py",
  "    if ua is not None and ua == ub:\n        return", "    if False:\n        return"),
 ("sweep: two corrections quoting one figure are two printings", "fact_sweep.py",
  "    if in_corr(f.el) and in_corr(g.el):\n        return \"two", "    if False:\n        return \"two"),
 ("sweep: an Edition lead beside its own Brief is two printings", "fact_sweep.py",
  "    if (_in_lead(f.el) and _in_brief(g.el)) or (_in_lead(g.el) and _in_brief(f.el)):", "    if False:"),
 ("sweep: a story's own correction is a twin of its story", "fact_sweep.py",
  "        if _own_note(x.el, own) and unit_of(y.el, own)", "        if False and unit_of(y.el, own)"),
 ("sweep: an in-page link to the evidence item is not read", "fact_sweep.py", "            t = _ref_target(x.el, dom_ids)", "            t = None"),
 ("sweep: a card's summary is not its story's", "fact_sweep.py", "        if card_field and story_item(a):", "        if False:"),
 ("sweep: two stored units are one printing (any stored text)", "fact_sweep.py",
  "        if a.cls & STORED_ROOT:\n            return (\"text\", id(a))", "        if a.cls & STORED_ROOT:\n            return (\"text\", 0)"),
 ("sweep: a title-case magnitude word is not read", "fact_sweep.py", "|\\s((?i:thousand|million|billion|trillion))\\b)?\"",
  "|\\s(thousand|million|billion|trillion)\\b)?\""),
 ("pass: nothing it withholds is checked for its other facts (failure 2)", "fact_once.py", "        if shown and twin and covered:", "        if shown and twin:"),
 ("pass: a complete index loses entries again", "fact_once.py",
  '    if rel == "archive.html" or (rel.startswith("news/") and rel.endswith(".html")):\n        return True',
  '    if False:\n        return True'),
 ("pass: a named reading is not read in a quoted unit", "fact_once.py", "            for s, n in mine_r:\n", "            for s, n in ():\n"),
 ("pass: a list left with no item keeps its heading", "fact_once.py",
  '            edits.append((holder.s0, holder.e1, ""))\n            gone.append(holder)', "            pass"),
 ("pass: home data does not yield to the Brief card", "fact_once.py",
  "                    if any(fs.one_fact(x, g) for x in mine) and _leaf_figure(g):", "                    if False:"),
 ("pass: the home gauge's number does not yield", "fact_once.py", '                    if fs.BARE.match(fs._text(el) or ""):', "                    if False:"),
 ("pass: the audit sees nothing", "fact_once.py", "    return sorted(lost)", "    return []"),
 ("today: the answer's figure is not linked to its evidence item", "today.py",
  "                    h = h.replace(_e(f.raw), f'<a class=\"td-ref\" href=\"#ev-{_e(ev_id)}\">{_e(f.raw)}</a>', 1)", "                    pass"),
 ("news: a storyline section lists a story the newest-first list carries", "site_build.py",
  "    shown = [i for i in rows if f\"/articles/{i.get('slug')}.html\" not in (listed or ())][:NEWS_PER_SECTION]",
  "    shown = rows[:NEWS_PER_SECTION]"),
 ("article: a pick repeating the story's figure is kept", "site_build.py",
  "        return _quotes_own(t) or any(_fs.one_event(t, x, coarse=True) for x in _listed)", "        return False"),
 ("article: an update callout prints the other story's headline whatever it repeats", "site_build.py",
  "        return (esc(other.get(\"title\")) if not _quotes_own(other.get(\"title\"))", "        return (esc(other.get(\"title\")) if True"),
 ("article: a second citation on one event prints its title", "site_build.py",
  "            if _src_twin(lab) or any(_fs.one_event(lab, x, coarse=True) for x in _src_seen):", "            if _src_twin(lab):"),
 ("board panel: a cell prints the story's own figure again", "site_build.py",
  "        return (\"In the story\" if any(x.same(y)", "        return (text if True else \"In the story\" if any(x.same(y)"),
 ("Chart Master table: the RSI-14 column waits behind 'Show all columns' again (failure 5)", "site_build.py",
  '<th scope="col">200-day</th><th scope="col" style="white-space:nowrap">RSI-14</th>',
  '<th scope="col">200-day</th><th scope="col" class="xs-x" style="white-space:nowrap">RSI-14</th>'),
 ("Chart Master table: the RSI-14 cell waits behind 'Show all columns' again (failure 5)", "site_build.py",
  "            f'<td>{esc(str(lv.get(\"rsi14\") if lv.get(\"rsi14\") is not None else \"\"))}</td></tr>'",
  "            f'<td class=\"xs-x\">{esc(str(lv.get(\"rsi14\") if lv.get(\"rsi14\") is not None else \"\"))}</td></tr>'"),
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
         + __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("America/New_York")).strftime("%a %b %d %Y, %I:%M %p %Z")]
for i, (name, rel, old, new) in enumerate(PLANTS, 1):
    if ONLY is not None and i not in ONLY:
        continue
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
open(log, "a" if ONLY else "w").write(("\n" if ONLY else "") + "\n".join(lines) + "\n")
print("done")
