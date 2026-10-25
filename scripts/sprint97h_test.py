#!/usr/bin/env python3
"""Hotfix 9.7h: the canary never takes the desk dark. Each case is named after what it guards.

  python3 scripts/sprint97h_test.py            # unit cases; exit 1 on any failure
  python3 scripts/sprint97h_test.py --tree <built publish dir>   # also the cases that read a built tree
  python3 scripts/sprint97h_test.py --canary   # also run the whole canary three times as subprocesses (today's clock, a week ahead, a new publication; about 5 minutes each)
  (verify_pipeline.py's canary calls unit() and tree() on the tree it builds; --canary is never called from there)

THE INCIDENT (J-13), October 21, 2026: every Brief run from the evening slot on stopped at the offline canary.
  1. verify_pipeline._verdict_fixture_dir graded the 15 October fixture verdict with no fixed time, so verdict.record_from
     stamped it with the wall clock and the news sitemap's 48 hours (relative to the newest item) moved off the 16 October
     movers' pages from 2026-10-21T22:07Z on. The fixture verdict now carries the fixture's own time.
  2. site_build.render_wire returned nothing when no entry was under 48 hours old, so wire.html was not built and the
     "no URL removed" check failed on any tree whose newest work is older than that, which a dark desk makes certain.
     The Wire page is now always built, with an empty state in plain wording.
NO NETWORK and no model call in the unit cases.
"""
import ast
import contextlib
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
TMPS = []
WEEK_AHEAD = "2026-11-01T15:00:00Z"


def cleanup():
    while TMPS:
        shutil.rmtree(TMPS.pop(), ignore_errors=True)


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def group(fails, name, fn):
    try:
        fn(fails)
    except Exception as e:                                   # noqa: BLE001
        msg = f"group {name} could not run [{type(e).__name__}: {str(e)[:100]}]"
        print("  FAIL " + msg)
        fails.append(msg)


def vp():
    """verify_pipeline as the canary has it loaded (it runs as __main__), else imported."""
    m = sys.modules.get("__main__")
    if m is not None and hasattr(m, "_verdict_fixture_dir") and hasattr(m, "_movers_fixture_dir"):
        return m
    import verify_pipeline
    return verify_pipeline


def newest_committed():
    """The newest committed item's stamp, read the way the news sitemap reads it (examples left out)."""
    d = os.path.join(HERE, "site", "content")
    best = ""
    for fn in os.listdir(d):
        if fn.startswith("_") or not fn.endswith(".json"):
            continue
        c = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        if c.get("example"):
            continue
        t = (c.get("published_utc") or (c.get("date", "") + "T00:00:00Z"))
        best = max(best, t)
    return best


def wire_cases(fails):
    import site_build as sb
    print("1. the Wire is always built; with nothing inside its 48 hours it says so")
    now = dt.datetime(2026, 10, 25, 15, 0, tzinfo=dt.timezone.utc)
    old = [{"title": "An old fixture story", "slug": "old-fixture", "date": "2026-10-01",
            "published_utc": "2026-10-01T12:00:00Z", "category": "news"}]
    for label, items in (("an empty items list", []), ("only items older than 48 hours", old)):
        h = sb.render_wire(items, "DATELINE", now=now)
        guarded(fails, f"{label}: the page is returned (not None)", lambda h=h: bool(h))
        guarded(fails, f"{label}: the h1 'The Wire' is present", lambda h=h: h and "<h1>The Wire</h1>" in h)
        guarded(fails, f"{label}: the empty-state line is present, with no claim about the newest item",
                lambda h=h: h and "Nothing in the last 48 hours. Earlier work is in " in re.sub(r"<[^>]+>", "", h)
                and "newest work" not in h and "archive" not in re.search(r'<p class="wr-empty">.*?</p>', h, re.S).group(0))
        for key, path in (("news", "/news.html"), ("brief", "/bottom-line.html")):
            guarded(fails, f"{label}: the link to {path} reads the page's own name, as NAMES has it ({sb.task_name(key)!r})",
                    lambda h=h, key=key, path=path: sb.NAMES[key][2] == path and
                    re.search(r'<a href="' + re.escape(path) + r'">' + re.escape(sb.task_name(key)) + r"</a>",
                              re.search(r'<p class="wr-empty">.*?</p>', h, re.S).group(0)))
        guarded(fails, f"{label}: the count line never says '0 entries'",
                lambda h=h: h and "0 entries" not in h and "0 entr" not in h)
        guarded(fails, f"{label}: the page's canonical address is /wire", lambda h=h: h and re.search(r'rel="canonical" href="[^"]*/wire"', h))
        guarded(fails, f"{label}: no em or en dash in the page's own wording",
                lambda h=h: h and not DASH.search(re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)))
    fresh = [{"title": "A fresh fixture story", "slug": "fresh-fixture", "date": "2026-10-25",
              "published_utc": "2026-10-25T14:00:00Z", "category": "news"}]
    h = sb.render_wire(fresh, "DATELINE", now=now)
    guarded(fails, "an entry inside 48 hours: the page lists it and has no empty-state line",
            lambda: h and "A fresh fixture story" in h and "Nothing in the last 48 hours." not in h
            and "1 entries" not in h)


def verdict_cases(fails):
    print("2. the fixture verdicts carry the fixture's own time, never the wall clock")
    v = vp()
    tmp = tempfile.mkdtemp(prefix="s97h-")
    TMPS.append(tmp)
    import verdict as _vd
    saved = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            saved = v._verdict_fixture_dir(tmp)
        want = json.load(open(os.path.join(HERE, "fixtures", "why", "sources_2026-10-15T2343Z.json"),
                              encoding="utf-8"))["recorded_utc"]
        newest = newest_committed()
        expect = max(want, newest)
        rec = json.load(open(os.path.join(tmp, "verdict", "2026-10-15-evening.json"), encoding="utf-8"))
        guarded(fails, f"the 15 October fixture verdict's made_utc is the fixture's recorded time ({want}), or the newest "
                       f"committed item's ({newest}) when that is later: {expect}",
                lambda: rec.get("made_utc") == expect)
        guarded(fails, "...and never the wall clock (it is no later than the newest committed item or the fixture)",
                lambda: rec.get("made_utc") <= expect)
        guarded(fails, "...inside the news sitemap's 48 hours of the newest item, whatever the clock",
                lambda: (dt.datetime.fromisoformat(newest.replace("Z", "+00:00"))
                         - dt.datetime.fromisoformat(rec["made_utc"].replace("Z", "+00:00"))) < dt.timedelta(hours=48))
    finally:
        v._verdict_restore(saved)
    mv_saved = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            mv_saved = v._movers_fixture_dir(tmp)
        d = os.path.join(tmp, "movers")
        files = [f for f in os.listdir(d) if f.endswith(".json")] if os.path.isdir(d) else []
        mrec = json.load(open(os.path.join(d, files[0]), encoding="utf-8")) if files else {}
        stamps = {e["verdict"]["made_utc"] for e in (mrec.get("coins") or {}).values() if e.get("verdict")}
        guarded(fails, "the 16 October movers record was written with graded verdicts", lambda: bool(stamps))
        mexp = max("2026-10-19T22:07:10Z", newest_committed())
        guarded(fails, f"every mover verdict's made_utc, and the record's, is the fixture's time ({mexp}), never the clock",
                lambda: stamps == {mexp} and mrec.get("made_utc") == mexp)
    finally:
        if mv_saved is not None:
            v._movers_restore(mv_saved)


def source_cases(fails):
    print("3. the guards in the source")
    src = open(os.path.join(HERE, "verify_pipeline.py"), encoding="utf-8").read()
    tree_ = ast.parse(src)
    for name in ("_verdict_fixture_dir", "_movers_fixture_dir"):
        fn = next(n for n in ast.walk(tree_) if isinstance(n, ast.FunctionDef) and n.name == name)
        calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "record_from"]
        guarded(fails, f"{name}: every record_from call ({len(calls)}) passes now=",
                lambda calls=calls: calls and all(any(k.arg == "now" for k in c.keywords) for c in calls))
    sbs = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    names_md = open(os.path.join(HERE, "docs", "audit-2026-10", "NAMES.md"), encoding="utf-8").read()
    import site_build as _sbn
    guarded(fails, "NAMES.md carries the names the Wire's empty state links by (News, The Brief)",
            lambda: all(_sbn.task_name(k) in names_md for k in ("news", "brief")))
    locs = sbs.split("    locs = [", 1)[1].split("]", 1)[0]
    guarded(fails, "/wire.html is in site_build's sitemap list (the priority tier, beside /news.html)",
            lambda: '"/wire.html"' in locs)
    s94 = open(os.path.join(HERE, "scripts", "sprint94_test.py"), encoding="utf-8").read()
    guarded(fails, "sprint94_test's sitemap case points verdict.DIR and why_evidence.DIR at scratch directories for _write_verdicts",
            lambda: "_vdm.DIR, _wem.DIR = _tmp_vd, _tmp_we" in s94
            and s94.index("_vdm.DIR, _wem.DIR = _tmp_vd, _tmp_we") < s94.index("sb._write_verdicts("))
    guarded(fails, "...and removes both scratch directories in the same finally that restores the DIRs",
            lambda: "rmtree(_tmp_vd" in s94 and "rmtree(_tmp_we" in s94
            and s94.index("movers.DIR, _vdm.DIR, _wem.DIR = old_dir") < s94.index("rmtree(_tmp_vd"))
    guarded(fails, "scripts/sprint97h_test.py carries no em dash",
            lambda: not DASH.search(open(__file__, encoding="utf-8").read()))


def unit():
    fails = []
    for name, fn in (("wire empty state", wire_cases), ("fixture verdict time", verdict_cases),
                     ("source guards", source_cases)):
        group(fails, name, fn)
    cleanup()
    return fails


def tree(root):
    """The cases that read a built tree. Returns the failures."""
    fails = []
    print(f"4. the built tree {root}")
    rd = lambda rel: open(os.path.join(root, rel), encoding="utf-8", errors="replace").read() \
        if os.path.exists(os.path.join(root, rel)) else ""
    h = rd("wire.html")
    guarded(fails, "wire.html is built, with its h1", lambda: h and "<h1>The Wire</h1>" in h)
    guarded(fails, "wire.html is in the priority sitemap", lambda: re.search(r"/wire(\.html)?<", rd("sitemap-priority.xml")))
    return fails


def canary_runs(fails):
    """The whole canary three times: at the wall clock, a week ahead, and on a scratch clone of the tree holding a new
    content item stamped at the build's time (the next real publication). Slow; run by hand into the log. The real
    site/content is never written: the third run uses a copy of the tracked files in a temp directory."""
    py = sys.executable
    runs = [("SITE_BUILD_NOW unset (today's clock)", None, HERE),
            (f"SITE_BUILD_NOW={WEEK_AHEAD}", WEEK_AHEAD, HERE)]
    clone = tempfile.mkdtemp(prefix="s97h-clone-")
    TMPS.append(clone)
    files = subprocess.run(["git", "ls-files", "-z"], cwd=HERE, stdout=subprocess.PIPE, check=True).stdout
    tar_c = subprocess.Popen(["tar", "--null", "-T", "-", "-cf", "-"], cwd=HERE, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    tar_x = subprocess.Popen(["tar", "-xf", "-", "-C", clone], stdin=tar_c.stdout)
    tar_c.stdin.write(files)
    tar_c.stdin.close()
    tar_x.communicate()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    src = json.load(open(os.path.join(HERE, "site", "content", "2026-10-20-evening-brief.json"), encoding="utf-8"))
    new_slug = "evening-brief-" + now.strftime("%Y-%m-%d")
    src.update(id="wrap-pm-" + now.strftime("%Y-%m-%d"), slug=new_slug, date=now.strftime("%Y-%m-%d"),
               published_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    json.dump(src, open(os.path.join(clone, "site", "content", now.strftime("%Y-%m-%d") + "-evening-brief.json"), "w",
                        encoding="utf-8"), indent=1)
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=scratch", "-c", "user.email=scratch@example.invalid", "commit", "-q", "-m", "scratch clone"]):
        subprocess.run(cmd, cwd=clone, check=True, stdout=subprocess.DEVNULL)
    runs.append((f"a new content item stamped {src['published_utc']} added to a scratch clone (the next publication)", None, clone))
    for label, env_now, cwd in runs:
        env = dict(os.environ)
        env.pop("SITE_BUILD_NOW", None)
        if env_now:
            env["SITE_BUILD_NOW"] = env_now
        p = subprocess.run([py, os.path.join(cwd, "verify_pipeline.py"), "canary"], cwd=cwd, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        last = [ln for ln in p.stdout.splitlines() if ln.strip()][-1:] or [""]
        errs = [ln for ln in p.stdout.splitlines() if ln.startswith("::error::canary:")]
        for e in errs:
            print("    " + e[:200])
        guarded(fails, f"the full canary is green with {label}: exit {p.returncode}, last line '{last[0][:80]}'",
                lambda p=p, last=last: p.returncode == 0 and last[0].startswith("LAYER 1 CANARY: PASS"))


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1])
    if "--canary" in args:
        group(fails, "canary subprocesses", canary_runs)
    cleanup()
    print(f"\nSPRINT 9.7h: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
