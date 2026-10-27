#!/usr/bin/env python3
"""U-9 plants for Sprint 9.9.1: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint991_test.py
run, the break undone in that copy and the test run again. usage: sprint991_plants.py <repo> <workdir> <log>"""
import os, shutil, subprocess, sys, time
repo, work, log = sys.argv[1:4]
PLANTS = [
 ("the notice loses the time of the next read", "verdict.py",
  '''return f"{NEXT_READ}: {why}{f' ({detail})' if detail else ''}. Next read: {when}."''',
  '''return f"{NEXT_READ}: {why}{f' ({detail})' if detail else ''}."'''),
 ("the notice loses its reason (the bare ruled words again)", "verdict.py",
  '''return f"{NEXT_READ}: {why}{f' ({detail})' if detail else ''}. Next read: {when}."''',
  '''return f"{NEXT_READ}. Next read: {when}."'''),
 ("the no-read reason is worded differently", "verdict.py", 'WHY_NO_READ = "no read yet today"', 'WHY_NO_READ = "nothing yet"'),
 ("the not-graded reason is worded differently", "verdict.py", 'WHY_NOT_GRADED = "the last read did not grade the move"', 'WHY_NOT_GRADED = "the window changed"'),
 ("the notice drops the way the move ran in the page's window (no detail)", "verdict.py",
  'detail = f"it is {wd}" if wd else ""', 'detail = ""'),
 ("the notice names a second window again (the 24-hour run beside the ET day), the words of Review 2 failure 2", "verdict.py",
  'notice_line(f"{WHY_NOT_GRADED} {ww}", _next_read_when(now, vrec), detail)', 'notice_line("the window flipped since the run", _next_read_when(now, vrec), detail)'),
 ("a verdict page's card carries the window attributes again (outside the item)", "verdict.py",
  'if where in ("home", "today", "coin"):', 'if True:'),
 ("the notice leaves its card (a bare paragraph again)", "verdict.py",
  '''    return (f'<aside class="vd vd-next" data-vd="{_e(sym)}" data-vd-kind="{_e(kind)}"{at} aria-label="Why {_e(name)} moved">'
            f'<h2 class="vd-h">Why {_e(name)} moved</h2>'
            f'<p class="vd-plain vd-next" data-vd-next="{_e(kind)}">{_e(line)}</p></aside>')''',
  '''    return f'<p class="vd-plain vd-next" data-vd-next="{_e(kind)}">{_e(line)}</p>\''''),
 ("the notice stops naming its window and direction", "verdict.py",
  'notice_line(f"{WHY_NOT_GRADED} {ww}", _next_read_when(now, vrec), detail), v.get("basis"), wd)', 'notice_line(f"{WHY_NOT_GRADED} {ww}", _next_read_when(now, vrec), detail), None, None)'),
 ("a graded card stops carrying its basis and direction", "verdict.py",
  '''    at = (f' data-vd-basis="{_e(v.get("basis"))}"' if v.get("basis") else "") + (''', '''    at = ("" if True else "") + ('''),
 ("the flip's record stops stating both directions as fields", "verdict.py",
  'out.update(kind="next_read", line=[NEXT_READ], window_dir=ddir, run_dir=run["dir"],', 'out.update(kind="next_read", line=[NEXT_READ],'),
 ("the stored line is reworded to the drawn one (J-10)", "verdict.py",
  'out.update(kind="next_read", line=[NEXT_READ], window_dir', 'out.update(kind="next_read", line=[NEXT_READ + ": rewritten"], window_dir'),
 ("the next read's time reads the wrong function (always tomorrow)", "verdict.py",
  "    return home.next_slot(t)[1]", "    return 'tomorrow at 8:15 AM ET'"),
 ("is_today compares the wrong day", "verdict.py",
  'return str(vrec.get("date_et") or "") == now.astimezone(_we().ET).date().isoformat()', 'return str(vrec.get("date_et") or "") != now.astimezone(_we().ET).date().isoformat()'),
 ("home: the tape leads again when the card carries the next-read line", "home.py",
  'graded = kind in ("graded", "next_read", "no_read")', 'graded = kind == "graded"'),
 ("home: no read yet today is not drawn", "home.py",
  "if now is not None and not _verdict.is_today(verdict, now):", "if False and not _verdict.is_today(verdict, now):"),
 ("home: the notice follows the tape (card under the tape line)", "home.py",
  '''        left = card + "".join(blocks[k] for k in LEFT)''', '''        left = blocks["tape"] + card + "".join(blocks[k] for k in LEFT[1:])'''),
 ("today: the window line is not drawn", "today.py", "  {window_line(rec, res if ev_html else None, evidence if ev_html else None)}\n", ""),
 ("today: the window line stops naming the evidence's window", "today.py", "    if res and evidence:\n        import why_evidence as _we", "    if False:\n        import why_evidence as _we"),
 ("today: the rolling fallback is given a reason the record does not state", "today.py",
  'text = "The direction above is read over the last 24 hours, the named fallback."',
  'text = "The direction above is read over the last 24 hours; the Board holds no midnight ET open for this day."'),
 ("today: an unstated window is given a claim about the Board (Review 1, failure 4)", "today.py",
  'text = "This record does not state which window its direction was read over."',
  'text = "The direction above is read over the last 24 hours; the Board holds no midnight ET open for this day."'),
 ("today: the living page's notice takes the record's clock, not the build's (Review 1, failure 3)", "today.py",
  'now=(clock if (clock is not None and here != "dated")', 'now=(None if (clock is not None and here != "dated")'),
 ("today: the living page is not handed the build's clock", "today.py", "verdict=_verdict(living, verdict_dir), clock=now)", "verdict=_verdict(living, verdict_dir))"),
 ("today: the evidence is drawn on the 24 hours again (Review 1, failure 1)", "today.py",
  '_win = rec.get("direction_basis") if rec.get("direction_basis") in ("et_day", "rolling_24h") else "rolling_24h"', '_win = "rolling_24h"'),
 ("evidence: the run figure says 'the window' again", "why_evidence.py", '{_e(wname) if wname else "in the window"}', 'in the window'),
 ("evidence: the section stops naming its window", "why_evidence.py", ' data-ev="{_e(sym)}"{wattr}>', ' data-ev="{_e(sym)}">'),
 ("evidence: the ET day is not cut (the 24 hours under an ET-day headline)", "why_evidence.py", '    if window != "et_day":', '    if True:'),
 ("evidence: the cut may run the other way from the page's direction", "why_evidence.py", '    if want_dir in ("up", "down") and (', '    if False and ('),
 ("evidence: the candidates of the day before stay in the day's list", "why_evidence.py", "int(tu.timestamp()) < since:", "int(tu.timestamp()) < 0:"),
 ("evidence: the stored readings of another run's hour are drawn under the day", "why_evidence.py", 'not res["run_same"] and mrows:', 'False and mrows:'),
 ("evidence: the timing figures drop their window's name", "why_evidence.py", 'timing_words(tst.get("result"), c, name, (run or {}).get("dir") or "down", wname)', 'timing_words(tst.get("result"), c, name, (run or {}).get("dir") or "down")'),
 ("evidence: the fallback does not say why", "why_evidence.py", '    if res and res.get("why"):', '    if False:'),
 ("coin page: the section reads the 24 hours unnamed again", "site_build.py", "marks=_marks, vrec=_vrec, named=True)", "marks=_marks, vrec=_vrec, named=False)"),
 ("coin page: no read yet today is not drawn", "site_build.py",
  "if sym in (\"BTC\", \"ETH\") and read_clock is not None and not _vd.is_today(rec, read_clock):", "if False:"),
 # ---- Review 2 (October 26, 2026, FAIL at f3f6c7f): each guard of the six failures
 ("page_view: a graded card is kept whatever the cut reads (failures 1 and 3)", "verdict.py",
  "        v = ((vrec or {}).get(\"coins\") or {}).get(sym)\n        if not v or v.get(\"kind\") not in (\"graded\", \"next_read\") or not ev:",
  "        return vrec\n        v = ((vrec or {}).get(\"coins\") or {}).get(sym)\n        if not v or v.get(\"kind\") not in (\"graded\", \"next_read\") or not ev:"),
 ("page_view: the cut need not find the stored run (failure 1)", "verdict.py", "    if not res.get(\"run_same\"):\n        return False", "    if False:\n        return False"),
 ("page_view: each candidate's pass or fail may change in the cut (failure 3)", "verdict.py",
  "        if _sig((stored.get(t[\"id\"]) or {}).get(\"result\")) != _sig(t.get(\"result\")):", "        if False:"),
 ("page_view: a card graded in one window may stand over a list read in another (failure 1)", "verdict.py",
  "        if shown == stored and (v[\"kind\"] == \"next_read\" or shown != \"et_day\" or _reproduces(ev, res, sym)):", "        if True:"),
 ("page_view: the notice's direction is not the window's (failure 2)", "verdict.py", "        wd = _shown_dir(res, sym)\n", "        wd = None\n"),
 ("home: the card is not put through the page view (the three pages grade apart)", "home.py",
  "            verdict = _verdict.page_view(verdict, evidence, \"BTC\")\n", ""),
 ("home: the build does not hand the view its evidence", "site_build.py", "verdict=_current_verdict(pulse), evidence=_latest_evidence())", "verdict=_current_verdict(pulse))"),
 ("coin page: the card is not put through the page view", "site_build.py",
  "        _vrec = _coin_view(sym, pulse, _vrec, evidence)          # Review 2: the card as the section's window may show it\n", ""),
 ("coin page: the Ether page keeps yesterday's line past its day (failure 6)", "site_build.py",
  "if sym in (\"BTC\", \"ETH\") and read_clock is not None", "if sym == \"BTC\" and read_clock is not None"),
 ("today: the card is not put through the page view (failures 1 and 3)", "today.py",
  "        verdict = _vview.page_view(verdict, evidence, \"BTC\", _win, _dir)\n", ""),
 ("today: the footer prints the stored next update, already past (failure 5)", "today.py",
  "    nxt = next_update(rec[\"slot\"], clock) if (clock is not None and here != \"dated\") else rec[\"next\"]", "    nxt = rec[\"next\"]"),
 ("evidence: the second sources are dropped without a word (failure 4)", "why_evidence.py", "        seconds_unread=unread)})", "        seconds_unread=[])})"),
 ("evidence: the line that says the second sources are not read is not drawn (failure 4)", "why_evidence.py",
  "    head = (f'<p class=\"ev-win\"{asof}>{_e(name)}, {_e(win)}. Prices: {src}.{said}</p>')", "    head = (f'<p class=\"ev-win\"{asof}>{_e(name)}, {_e(win)}. Prices: {src}.</p>')"),
 ("fixtures: the stored verdict fixture is reworded (it must stay the stored October 26 read byte for byte)", "fixtures/sprint991/real-2026-10-26-morning/verdict_2026-10-26-morning.json",
  "the next slot's run grades the move as it then stands", "the next slot's run grades the move afresh"),
]
def run(cwd):
    r = subprocess.run([sys.executable, "scripts/sprint991_test.py"], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(cwd, ".pyc-" + str(time.time()))))
    out = r.stdout + r.stderr
    return r.returncode, [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ")]
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
lines = ["Sprint 9.9.1, U-9: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint991_test.py run, the "
         "same copy run again with the break undone. Fresh copy per plant. " + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
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
    rc, fails = run(d)
    open(p, "w", encoding="utf-8").write(s)
    rc2, fails2 = run(d)
    lines.append(f"PLANT {i} {name} ({rel}): exit {rc}, {len(fails)} red; restored: exit {rc2}")
    for f in fails[:5]:
        lines.append("      " + f[:220])
    if len(fails) > 5:
        lines.append(f"      ... and {len(fails) - 5} more")
    print(lines[-1] if not fails else lines[-len(fails[:5]) - (2 if len(fails) > 5 else 1)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
open(log, "w").write("\n".join(lines) + "\n")
print("done")
