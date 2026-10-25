#!/usr/bin/env python3
"""U-9 plants for Sprint 9.8: each guarded thing broken on purpose in a throwaway copy, scripts/sprint98_test.py run, the break
undone and the test run again. Fresh copy of the repository once; each plant restored from its saved copy, never a git checkout
(the 1 October rule). Every Python run gets a fresh PYTHONPYCACHEPREFIX (U-10's addition).

usage: sprint98_plants.py <repo> <built publish dir> <workdir> <log>
       sprint98_plants.py --self-check <repo> <workdir> <log>     # one plant whose old text is absent: must exit non-zero

A plant is (name, kind, [(file, old text, new text), ...]); kind "src" breaks the repository copy and runs the unit cases, kind
"tree" breaks a copy of the built tree and runs the tree cases. Every old text must occur exactly once in its file, or the plant
is NOT APPLIED. The harness exits 0 only when every plant applied, went red, and came back green after its restore."""
import os
import shutil
import subprocess
import sys
import tempfile

VR, SB, VD, MV, AF = "verdict_record.py", "site_build.py", "verdict.py", "movers.py", "api_feeds.py"
REC = "why/record/index.html"
PLANTS = [
    # ---- the definition of done: the tally, and a reversed verdict counted as reversed
    ("the reversed verdict counted as confirmed", "src",
     [(VR, 'res, why = "reversed", f"a later read of the same move graded it {g}"',
       'res, why = "confirmed_later", f"a later read of the same move graded it {g}"')]),
    ("an awaiting verdict counted as confirmed", "src",
     [(VR, 'outcome = "awaiting" if window_open(e, now, rd["evening"]) else "unresolved"', 'outcome = "confirmed_later"')]),
    ("the page omitted on empty", "src",
     [(SB, "    w(_vr.REL, html)\n    return v\n", "    if v and v.get(\"graded\"):\n        w(_vr.REL, html)\n    return v\n")]),
    ("a duplicated figure (the awaiting count printed again in the lede)", "src",
     [(VR, "  {_tally(v)}\n  <h2 class=\"vr-h\">How a verdict is scored here</h2>",
       "  <p>{v['counts']['likely_awaiting']} Likely verdicts are still awaiting a later source.</p>\n  {_tally(v)}\n"
       "  <h2 class=\"vr-h\">How a verdict is scored here</h2>")]),
    # ---- never inferred
    ("a later ET day's read resolves the Likely (a different move)", "src",
     [(VR, 'by.setdefault((e.get("date_et"), e.get("coin_slug") or e.get("coin_sym")), []).append(e)',
       'by.setdefault((e.get("coin_slug") or e.get("coin_sym"),), []).append(e)')]),
    ("any two sourced events are the same event (a shallow key)", "src",
     [(VR, 'return bool((la - {""}) & (lb - {""}))', 'return bool((la - {""}) and (lb - {""}))')]),
    ("an earlier read resolves a later Likely (the reads taken newest first)", "src",
     [(VR, '        group.sort(key=lambda e: (e.get("made_utc") or "", e["key"]))\n',
       '        group.sort(key=lambda e: (e.get("made_utc") or "", e["key"]), reverse=True)\n')]),
    ("a later Likely on the same events reverses it", "src",
     [(VR, '                if g == "Likely" and same:\n                    continue', '                if False:\n                    continue')]),
    ("a rewritten slot counts as a second verdict", "src",
     [(VR, 'last[(e.get("date_et"), _slot_key(e.get("slot")), e.get("coin_slug") or e.get("coin_sym"))] = e', 'last[e["key"]] = e')]),
    ("a verdict withheld at the cap is scored", "src",
     [(VR, '                    if v.get("grade") not in GRADES:\n                        continue\n                    if ev is None:',
       '                    if v.get("grade") not in GRADES and v.get("kind") != "withheld":\n                        continue\n'
       '                    v = dict(v, grade=v.get("grade") or v.get("grade_withheld"))\n                    if ev is None:')]),
    # ---- append-only and frozen
    ("a stored file is rewritten (no exclusive create)", "src",
     [(VR, "    if os.path.exists(path):\n        return False\n    import tempfile", "    import tempfile"),
      (VR, "os.link(tmp, path)", "os.replace(tmp, path)")]),
    ("a stored outcome is recomputed", "src",
     [(VR, "    new_outs = {k: o for k, o in computed.items() if k not in s_outs}\n", "    new_outs = dict(computed)\n")]),
    ("the build's read writes the store", "src",
     [(VR, "    es, outs, _n, _o = merged(vdir, mdir, wdir, store, skips)\n    rd = reads(vdir, mdir)",
       "    _r = sync(vdir, mdir, wdir, store, save=True)\n    es, outs = _r['entries'], _r['outcomes']\n    rd = reads(vdir, mdir)")]),
    ("the verdict run step stops storing the record", "src", [(VD, "    _sync_record()\n    return 0\n", "    return 0\n")]),
    ("the movers run step stops storing the record", "src",
     [(MV, "        import verdict_record\n        verdict_record.sync(save=True)\n", "        import verdict_record\n")]),
    # ---- the page
    ("the stale rule is the page's own (6 hours), not the site's", "src",
     [(VR, "stale = snapshot.is_stale(through, now) if through else None", "stale = snapshot.is_stale(through, now, 6) if through else None")]),
    ("the window's label is dropped", "src",
     [(VR, "        stamp = (f'Counted from the first verdict record, {_e(_when(v[\"begins_utc\"]))}, through the newest read, '\n"
           "                 f'{_e(_when(v[\"through_utc\"]))}.')\n", "        stamp = ''\n")]),
    ("a listed verdict loses its link", "src",
     [(VR, "head = (f'<a href=\"{_e(r[\"url\"])}\">{_e(title)}</a>' if r[\"linked\"] else",
       "head = (f'<span>{_e(title)}</span>' if r[\"linked\"] else")]),
    ("a row whose page was not built is linked anyway", "src", [(VR, '"linked": built is None or e.get("url") in built,', '"linked": True,')]),
    ("'because' on the page", "src",
     [(VR, "    <li><b>Reversed.</b> A later read", "    <li><b>Reversed.</b> Reversed because a later read")]),
    ("the zero-graded state is not said", "src", [(VR, "        status = '<p class=\"vr-st\">No move has been graded since the record began.</p>'\n", "        status = ''\n")]),
    ("the empty store is not said", "src",
     [(VR, "        win = '<p class=\"vr-win\">No verdict record is stored yet, so there is no window to count.</p>'\n", "        win = ''\n")]),
    ("the record cannot be drawn and the page is left out", "src",
     [(SB, "            html = _vr.render_unreadable(dateline)\n", "            return None\n")]),
    # ---- the feed and the links
    ("the feed is left out of /api/v1/", "src", [(AF, '    put("why/record.json", lambda: _record_feed(ctx, now))\n', "")]),
    ("the feed's as-of is the build moment", "src", [(VR, "    return af.envelope(FEED, URL, v[\"through_utc\"], now,", "    return af.envelope(FEED, URL, af._iso(now), now,")]),
    ("How we check loses its link", "src", [(SB, 'is kept on <a href="/why/record/">the verdict record</a>.</p>', 'is kept on the verdict record.</p>')]),
    ("the page's own rules are dropped from its head", "src", [(VR, 'path=URL, schema_extra="\\n" + RECORD_STYLE)', 'path=URL)')]),
    ("the page's rules bring their own color", "src", [(VR, ".page .vr-c.vr-dn{border-left:3px solid var(--rule)}", ".page .vr-c.vr-dn{border-left:3px solid #C8261B}")]),
    ("the Bitcoin /why/ page loses its link", "src", [(VD, '<a href="/why/record/">the verdict record</a>', "the verdict record")]),
    ("the Big movers /why/ page loses its link", "src", [(MV, '<a href="/why/record/">the verdict record</a>', "the verdict record")]),
    ("the sitemap loses the page", "src", [(SB, '"/corrections.html", "/why/record/",', '"/corrections.html",')]),
    # ---- the built tree
    ("tree: the page is missing", "tree", [(REC, None, None)]),
    ("tree: the sitemap does not list it", "tree", [("sitemap-priority.xml", "<loc>https://gocheckmycrypto.com/why/record/</loc>", "<loc>https://gocheckmycrypto.com/why/recorded/</loc>")]),
    ("tree: the feed is missing from the index", "tree", [("api/v1/index.json", '"path":"/api/v1/why/record.json"', '"path":"/api/v1/why/recorded.json"')]),
    ("tree: the page's count disagrees with the feed's", "tree", [(REC, 'data-rc="reads_coins">', 'data-rc="reads_coins">9')]),
    ("tree: a count printed outside the tally", "tree", [(REC, '<h2 class="vr-h">How a verdict is scored here</h2>', '<p>0 Likely verdicts.</p><h2 class="vr-h">How a verdict is scored here</h2>')]),
    ("tree: How we check loses the link", "tree", [("method.html", 'href="/why/record/"', 'href="/why/"')]),
    # ---- review 1
    ("R1: a wire position counts as an identity (same id, different story)", "src",
     [(VR, '    sa = {x for x in a.get("events") or [] if is_stable_id(x)}\n    sb_ = {x for x in b.get("events") or [] if is_stable_id(x)}\n',
       '    sa = set(a.get("events") or [])\n    sb_ = set(b.get("events") or [])\n')]),
    ("R1: the stable families admit a wire id", "src",
     [(VR, '_STABLE_RX = re.compile("|".join(f"(?:{rx})" for rx, _why in STABLE_IDS.values()))',
       '_STABLE_RX = re.compile("|".join(f"(?:{rx})" for rx, _why in STABLE_IDS.values()) + r"|wire-c\\d+")')]),
    ("R1: a release's shared schedule page counts as an identity", "src",
     [(VR, 'if not isinstance(c, dict) or c.get("id") not in ids or is_stable_id(c.get("id")) or c.get("kind") != "wire":',
       'if not isinstance(c, dict) or c.get("id") not in ids:')]),
    ("R1: a store file of another type stops the record (only OSError and ValueError caught, no shape check)", "src",
     [(VR, '        except Exception as e:                               # noqa: BLE001\n            _skip(skips, f"record/{n}", type(e).__name__)\n',
       '        except (OSError, ValueError) as e:\n            _skip(skips, f"record/{n}", type(e).__name__)\n'),
      (VR, "        elif _entry_ok(obj):", '        elif obj.get("kind") == "verdict":'),
      (VR, "            if _outcome_ok(obj):", '            if obj.get("kind") == "outcome":')]),
    ("R1: a slot record with a malformed coin stops the record", "src",
     [(VR, '                    if not isinstance(v, dict):\n                        raise TypeError(f"{sym} is a {type(v).__name__}")\n', ""),
      (VR, '                except Exception as e:                       # noqa: BLE001\n                    bad = True\n                    print(f"::warning::verdict record: verdict/{n}',
       '                except KeyError as e:\n                    bad = True\n                    print(f"::warning::verdict record: verdict/{n}'),
      (VR, '        except Exception as e:                               # noqa: BLE001\n            _skip(skips, f"verdict/{n}", type(e).__name__)',
       '        except KeyError as e:\n            _skip(skips, f"verdict/{n}", type(e).__name__)')]),
    ("R1: the feed is left out when the record cannot be drawn", "src", [(AF, 'return vr.feed_unreadable(now, f"{type(e).__name__}")', "raise")]),
    ("R1: the skipped files are not said on the page", "src", [(VR, 'if v.get("skipped") else "")', 'if False else "")')]),
    ("R1: a cut write leaves a frozen half file (written in place)", "src",
     [(VR, 'fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))',
       'fd, tmp = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY), path + ".x"')]),
    ("R1: a movers record with no date_et is dropped in silence", "src",
     [(VR, '                print(f"::warning::verdict record: movers/{n} has no date_et; its verdicts are left out, never dated by guess")\n', "")]),
    ("R1: verdict.py stores the record with its alarm still armed", "src",
     [(VD, "        signal.alarm(0)\n        signal.signal(signal.SIGALRM, signal.SIG_DFL)\n        signal.signal(signal.SIGTERM, signal.SIG_DFL)\n        import verdict_record",
       "        import verdict_record")]),
    ("R1: the record's start printed twice", "src",
     [(VR, "  <p>Each graded verdict is listed newest first",
       "  <p>The record begins with the desk's first stored verdict record, {_e(_when(v['begins_utc']))}. Each graded verdict is listed newest first")]),
    ("R1: nothing-graded printed twice", "src",
     [(VR, """<ol class="vr-l">{rows}</ol>' if rows else "")""",
       """<ol class="vr-l">{rows}</ol>' if rows else '<p class="vr-empty">No graded verdict to list yet.</p>')""")]),
    ("R1: an evening Likely counted as awaiting", "src",
     [(VR, 'if _slot_key(e.get("slot")) == "evening" or (e.get("source"), e.get("date_et")) in evening:',
       'if (e.get("source"), e.get("date_et")) in evening:')]),
    ("R1: the ET day's end ignored (awaiting forever)", "src", [(VR, "    return now < day_end.astimezone(_dt.timezone.utc)", "    return True")]),
    ("R1: the day's stored evening read ignored", "src",
     [(VR, 'if _slot_key(e.get("slot")) == "evening" or (e.get("source"), e.get("date_et")) in evening:',
       'if _slot_key(e.get("slot")) == "evening":')]),
]
BOGUS = [("self-check: a plant whose old text is not in the file", "src", [(VR, "THIS TEXT IS NOT IN THE FILE", "x")])]

SKIP = {".git", "node_modules", "shots", "review", "docs", "out", "__pycache__"}


def env():
    e = dict(os.environ)
    e["PYTHONPYCACHEPREFIX"] = tempfile.mkdtemp(prefix="s98pyc-")
    return e


def fresh_repo(repo, dst):
    def ignore(d, names):
        rel = os.path.relpath(d, repo)
        out = {n for n in names if n == "__pycache__"}
        if rel == ".":
            out |= {n for n in names if n in SKIP}
        if rel == "site":
            out |= {n for n in names if n == "publish"}
        return out
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(repo, dst, ignore=ignore, symlinks=True)


def run(cmd, cwd, timeout=1200):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env())
    reds = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.startswith("  FAIL")]
    return r.returncode, reds


def apply(root, edits):
    saved = {}
    for f, old, new in edits:
        p = os.path.join(root, f)
        if old is None and new is None:
            saved[f + "::bytes"] = open(p, "rb").read()
            os.remove(p)
            continue
        txt = open(p, encoding="utf-8").read()
        if txt.count(old) != 1:
            restore(root, saved)
            return None, f"NOT APPLIED: {f}: old text occurs {txt.count(old)} time(s)"
        saved.setdefault(f, txt)
        open(p, "w", encoding="utf-8").write(txt.replace(old, new, 1))
    return saved, ""


def restore(root, saved):
    for f, txt in saved.items():
        if f.endswith("::bytes"):
            open(os.path.join(root, f[:-7]), "wb").write(txt)
        else:
            open(os.path.join(root, f), "w", encoding="utf-8").write(txt)


def main(argv):
    if argv[:1] == ["--self-check"]:
        repo, work, log = argv[1:4]
        plants, tree_src = BOGUS, None
    else:
        repo, tree_src, work, log = argv[:4]
        plants = PLANTS
    os.makedirs(work, exist_ok=True)
    repo_copy = os.path.join(work, "repo")
    tree_copy = os.path.join(work, "tree")
    fresh_repo(repo, repo_copy)
    lines, good, applied = [], 0, 0
    print(f"{len(plants)} plants")
    for i, (name, kind, edits) in enumerate(plants, 1):
        if kind == "src":
            root = repo_copy
            cmd = [sys.executable, "scripts/sprint98_test.py"]
            cwd = repo_copy
        else:
            if os.path.exists(tree_copy):
                shutil.rmtree(tree_copy)
            shutil.copytree(tree_src, tree_copy)
            root = tree_copy
            cmd = [sys.executable, os.path.join(repo_copy, "scripts", "sprint98_test.py"), "--tree", tree_copy]
            cwd = repo_copy
        saved, why = apply(root, edits)
        if saved is None:
            lines.append(f"PLANT {i} {name}: {why}")
            print(lines[-1])
            continue
        applied += 1
        rc, reds = run(cmd, cwd)
        restore(root, saved)
        rc2, reds2 = run(cmd, cwd)
        ok = rc != 0 and rc2 == 0
        good += 1 if ok else 0
        lines.append(f"PLANT {i} {name}: exit {rc}, {len(reds)} red; restored: exit {rc2}" + ("" if ok else "  <== NOT A PROPER RED"))
        for r in reds[:2]:
            lines.append("      " + r)
        if rc2 != 0:
            lines.append("      STILL RED AFTER RESTORE: " + "; ".join(reds2[:2]))
        print("\n".join(lines[-1 - min(2, len(reds)):]))
    status = 0 if (good == len(plants) and applied == len(plants)) else 1
    lines.append(f"SUMMARY: {good} of {len(plants)} plants went red and came back green ({applied} applied); exit {status}")
    open(log, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(lines[-1])
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
