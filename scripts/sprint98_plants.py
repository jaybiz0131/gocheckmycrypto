#!/usr/bin/env python3
"""U-9 plants for Sprint 9.8: each guarded thing broken on purpose in a throwaway copy, scripts/sprint98_test.py run, the break
undone and the test run again. Fresh copy per run; the runner is scripts/sprint97_plants.py's, unchanged but for the test it runs.

usage: sprint98_plants.py <repo> <built publish dir> <workdir> <log>

A SOURCE plant breaks one of the repository's files in a copy of the repository and runs the unit cases. A TREE plant breaks one
file of a copy of the built tree and runs the tree cases. Every old text must occur exactly once in its file or the plant is
reported NOT APPLIED. The restore is from the saved copy of the file, never a git checkout (the 1 October rule)."""
import os
import shutil
import subprocess
import sys

repo, tree_src, work, log = sys.argv[1:5]
VR, SB = "verdict_record.py", "site_build.py"
T = "verdict-record.html"
PLANTS = [
    # ---- the tally
    ("tally: a confirmation outranks a reversal", "src", [(VR, 'status = "reversed" if rev else "confirmed" if con else "open"', 'status = "confirmed" if con else "reversed" if rev else "open"')]),
    ("tally: a reversed verdict is counted as confirmed", "src", [(VR, 'by_grade[r["grade"]][r["status"]] += 1', 'by_grade[r["grade"]]["confirmed" if r["status"] == "reversed" else r["status"]] += 1')]),
    ("tally: a source published before the verdict counts", "src", [(VR, "if made is None or pub <= made:", "if made is None:")]),
    ("tally: a source that is not primary counts", "src", [(VR, '    if entry.get("primary") is not True:\n        why.append("not a primary source")\n', '')]),
    ("tally: a finding of any word counts", "src", [(VR, '    if entry.get("finding") not in FINDINGS:', '    if entry.get("finding") not in FINDINGS + ("weakens",):'), (VR, 'rev = [e for e in srcs if e["finding"] == "reverses"]', 'rev = [e for e in srcs if e["finding"] in ("reverses", "weakens")]')]),
    ("tally: a source with no link counts", "src", [(VR, '    if not re.match(r"^https?://\\S+$", str(entry.get("url") or "")):\n        why.append("no link a reader can open")\n', '')]),
    ("tally: a source for an unstored verdict is dropped silently", "src", [(VR, '            ignored.append({"entry": e, "why": why})', '            pass')]),
    ("graded: the morning's grade stands for a day graded at both slots", "src", [(VR, 'recs.sort(key=lambda r: r.get("slot") == "evening", reverse=True)', 'recs.sort(key=lambda r: r.get("slot") == "evening", reverse=False)')]),
    ("graded: a verdict withheld at the cap is counted", "src", [(VR, 'g = [r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade")]', 'g = [r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade") or ((r.get("coins") or {}).get(sym) or {}).get("grade_withheld")]'), (VR, '            v = g[0]["coins"][sym]\n', '            v = dict(g[0]["coins"][sym]); v["grade"] = v.get("grade") or v.get("grade_withheld")\n')]),
    ("graded: the Big movers are left off the record", "src", [(VR, "for r in mv.records(mdir):", "for r in []:")]),
    ("first day: the record starts at the first graded verdict, not the first stored record", "src", [(VR, "    return min(days) if days else None", "    days = [v['day'] for v in graded(vdir, mdir)]\n    return min(days) if days else None")]),
    # ---- the page
    ("page: the headline prints every grade's total as Likely", "src", [(VR, '(lk["graded"], "Likely verdicts")', '(tot["graded"], "Likely verdicts")')]),
    ("page: the empty state claims a record it does not have", "src", [(VR, "No graded verdict is stored yet, so there is nothing to score.", "The desk's verdicts have held up.")]),
    ("page: the lede says because", "src", [(VR, "How the desk's own grades held up after the fact:", "How the desk's own grades held up after the fact, because they are checked:")]),
    ("review 1: the page prints a Likely definition of its own again", "src", [(VR, "How the desk's own grades held up after the fact:", "A Likely verdict names an event that passed the timing test. How the desk's own grades held up after the fact:")]),
    ("review 1: one count, two names again (Held up in the table)", "src", [(VR, '<th scope="col">Confirmed later</th>', '<th scope="col">Held up</th>')]),
    ("review 1: a Bitcoin or Ether /why/ page loses its standing line", "src", [("verdict.py", "  {card}\n  {record}\n  {ev_html}", "  {card}\n  {ev_html}")]),
    ("review 1: a Big mover's /why/ page loses its standing line", "src", [("movers.py", "  {card}\n  {record}\n  {sec}", "  {card}\n  {sec}")]),
    ("review 1: the standing line ignores the record's rules (any stored source counts)", "src", [(VR, '    t = tally([v | {"day": "", "grade": "Likely"}], load_later() if later is None else later)', '    t = tally([v | {"day": "", "grade": "Likely"}], [])\n    srcs = [e for e in (load_later() if later is None else later) if e.get("verdict") == url]\n    t["rows"][0].update(status=("reversed" if srcs[-1]["finding"] == "reverses" else "confirmed") if srcs else "open", source=srcs[-1] if srcs else None)')]),
    ("review 1: /today/ no longer links the record", "src", [("today.py", "is counted on <a href=\"/verdict-record.html\">the verdict record</a>", "is counted on the verdict record")]),
    ("page: a row is left out", "src", [(VR, '"".join(_row(r) for r in t["rows"])', '"".join(_row(r) for r in t["rows"][1:])')]),
    ("page: the reversing source is not named", "src", [(VR, "{word} <a href=", "<a href=")]),
    ("page: a dash in the page", "src", [(VR, "<h2>By grade</h2>", "<h2>By grade " + chr(0x2014) + " all four</h2>")]),
    # ---- adding a later source
    ("add: a refused source is stored anyway", "src", [(VR, "    if why:\n        return False, why\n    p = path or STORE", "    p = path or STORE")]),
    ("add: a dash in a statement is allowed", "src", [(VR, "        if DASH.search(s):\n            why.append(f\"{k} carries a dash\")\n", "")]),
    ("add: 'because' in a statement is allowed", "src", [(VR, "        if BECAUSE.search(s):\n            why.append(f\"{k} says 'because'\")\n", "")]),
    ("store: the store of later sources is missing", "src", [("site/data/verdict-record.json", None, None)]),
    # ---- the wiring
    ("wiring: the build does not write the page", "src", [(SB, '        w("verdict-record.html", html)\n', '        pass\n')]),
    ("wiring: the sitemap does not list it", "src", [(SB, '"/corrections.html", "/verdict-record.html",', '"/corrections.html",')]),
    ("wiring: How we check does not link it", "src", [(SB, '<a href="/verdict-record.html">the verdict record</a>', 'the verdict record')]),
    ("wiring: an old address in the sitemap changes", "src", [(SB, '"/corrections.html", "/verdict-record.html",', '"/corrections", "/verdict-record.html",')]),
    # ---- the built tree
    ("tree: the page is not in the tree", "tree", [(T, None, None)]),
    ("tree: the headline count differs from the rows", "tree", [(T, "<li><b>0</b><span>Likely verdicts</span></li>", "<li><b>1</b><span>Likely verdicts</span></li>")]),
    ("tree: a row for a verdict page the tree does not have", "tree", [(T, "<h2>By grade</h2>", '<ol class="vr-l"><li class="vr-r vr-open"><p><a href="/why/2026-10-24-bitcoin">Why Bitcoin moved</a></p><p class="vr-s">Graded Likely. Not yet revisited.</p></li></ol><h2>By grade</h2>')]),
    ("tree: the empty state is gone", "tree", [(T, "No graded verdict is stored yet", "Nothing to show")]),
    ("tree: 'because' on the page", "tree", [(T, "How the desk's own grades held up after the fact:", "How the desk's own grades held up, because they are checked:")]),
    ("tree: the built /today/ does not link the record", "tree", [("today/index.html", 'is counted on <a href="/verdict-record.html">the verdict record</a>', "is counted on the verdict record")]),
    ("tree: the sitemap does not list it", "tree", [("sitemap-priority.xml", "<url><loc>https://gocheckmycrypto.com/verdict-record</loc></url>", "")]),
    ("tree: How we check does not link it", "tree", [("method.html", 'href="/verdict-record.html"', 'href="/corrections.html"')]),
]

SKIP = {".git", "node_modules", "shots", "review", "docs", "out", "__pycache__"}


def ignore(d, names):
    rel = os.path.relpath(d, repo)
    out = {n for n in names if n == "__pycache__"}
    if rel == ".":
        out |= {n for n in names if n in SKIP}
    if rel == "site":
        out |= {n for n in names if n == "publish"}
    return out


def fresh_repo(dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(repo, dst, ignore=ignore, symlinks=True)


def run(cmd, cwd, timeout=1200):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    reds = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.startswith("  FAIL")]
    return r.returncode, reds


def apply(root, edits):
    saved = {}
    for f, old, new in edits:
        p = os.path.join(root, f)
        if old is None and new is None:
            saved[f] = None
            saved[f + "::bytes"] = open(p, "rb").read()
            os.remove(p)
            continue
        txt = open(p, encoding="utf-8").read()
        if new == "drop-head-script":
            a = txt.index("<script>(function(){try{var v=JSON.parse(localStorage.getItem('gcmc_coins')")
            b = txt.index("</script>", a) + len("</script>")
            saved.setdefault(f, txt)
            open(p, "w", encoding="utf-8").write(txt[:a] + txt[b:])
            continue
        if txt.count(old) != 1:
            if saved:
                restore(root, saved)
            return None, f"NOT APPLIED: {f}: old text occurs {txt.count(old)} time(s)"
        saved.setdefault(f, txt)            # the file as it was before ANY edit of this plant, so two edits to one file restore whole
        open(p, "w", encoding="utf-8").write(txt.replace(old, new, 1))
    return saved, ""


def restore(root, saved):
    for f, txt in saved.items():
        if f.endswith("::bytes"):
            open(os.path.join(root, f[:-7]), "wb").write(txt)
        elif txt is not None:
            open(os.path.join(root, f), "w", encoding="utf-8").write(txt)


lines = []
done_red = 0
n_applied = 0
tree_copy = os.path.join(work, "tree")
os.makedirs(work, exist_ok=True)
repo_copy = os.path.join(work, "repo")
fresh_repo(repo_copy)
print(f"{len(PLANTS)} plants")
for i, (name, kind, edits) in enumerate(PLANTS, 1):
    if kind == "src":
        saved, why = apply(repo_copy, edits)
        if saved is None:
            lines.append(f"PLANT {i} {name}: {why}")
            print(lines[-1])
            continue
        n_applied += 1
        rc, reds = run([sys.executable, "scripts/sprint98_test.py"], repo_copy)
        restore(repo_copy, saved)
        rc2, reds2 = run([sys.executable, "scripts/sprint98_test.py"], repo_copy)
    else:
        if os.path.exists(tree_copy):
            shutil.rmtree(tree_copy)
        shutil.copytree(tree_src, tree_copy)
        saved, why = apply(tree_copy, edits)
        if saved is None:
            lines.append(f"PLANT {i} {name}: {why}")
            print(lines[-1])
            continue
        n_applied += 1
        flag = []
        rc, reds = run([sys.executable, os.path.join(repo, "scripts", "sprint98_test.py"), "--tree", tree_copy] + flag, repo)
        restore(tree_copy, saved)
        rc2, reds2 = run([sys.executable, os.path.join(repo, "scripts", "sprint98_test.py"), "--tree", tree_copy] + flag, repo)
    went_red = rc != 0
    done_red += 1 if (went_red and rc2 == 0) else 0
    lines.append(f"PLANT {i} {name}: exit {rc}, {len(reds)} red; restored: exit {rc2}")
    for r in reds[:2]:
        lines.append("      " + r)
    if rc2 != 0:
        lines.append("      STILL RED AFTER RESTORE: " + "; ".join(reds2[:2]))
    print(lines[-1] if not reds else "\n".join(lines[-1 - min(2, len(reds)):]))
lines.append(f"SUMMARY: {done_red} of {len(PLANTS)} plants went red and came back green ({n_applied} applied)")
open(log, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(lines[-1])
