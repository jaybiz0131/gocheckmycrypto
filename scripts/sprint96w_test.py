#!/usr/bin/env python3
"""Hotfix 9.6w: the Wire never vanishes, and sprint 9.4's sitemap check stops reading today's date.

  python3 scripts/sprint96w_test.py            # unit cases; exit 1 on any failure
  python3 scripts/sprint96w_test.py --build    # also a whole throwaway build with every story older than the window
  (verify_pipeline.py's canary calls unit() on the tree it builds)

THE INCIDENT, from the evening of October 21, 2026: every Edition, morning read and watcher run failed at the canary.
Two causes. (1) site_build.py wrote wire.html only `if _wire:` and render_wire returned None when no entry fell in the
48 hour window; with the runs failing nothing new came in, the old entries aged out, the page left the build, the
canary's "no URL removed" case went red, and that red stopped the runs that would have refreshed the data. (2) the
9.4 case "every mover's /why/ URL is in the news sitemap inside its 48 hours" built the sitemap from fixed October
16 to 19 fixtures plus the Bitcoin /why/ page the canary stamps with the wall clock, so the sitemap's own "newest
item" anchor was today and the fixtures aged out of it 48 hours after October 19, 10:07 PM ET.

NO NETWORK, no model call. Fixtures are labeled FIXTURE and are never written to site/data.
"""
import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
FX = os.path.join(HERE, "fixtures", "hotfix96w")
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 20, 18, 0, tzinfo=UTC)             # the fixture's own clock
LATER = dt.datetime(2026, 10, 25, 18, 0, tzinfo=UTC)           # every fixture entry is past the 48 hour window
MAIN_REF = "3be7684"
TMPS = []


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


def norm(html):
    """The masthead prints the wall clock (its build date and its UPDATED time) and the head names the build commit; everything else is the page."""
    html = re.sub(r'data-build-date="[^"]*">[^<]*<', 'data-build-date="X">X<', html or "")
    html = re.sub(r'data-asof="[^"]*"', 'data-asof="X"', html)
    html = re.sub(r'(name="build-commit" content=")[^"]*"', r'\1X"', html)       # the commit the page was built from
    return re.sub(r'<span class="mh-lt">[^<]*</span>', '<span class="mh-lt">X</span>', html)


def items():
    return json.load(open(os.path.join(FX, "wire_items.json"), encoding="utf-8"))


def wire_cases(fails):
    """The Wire also quotes Bitcoin readings from site/data/snapshots; a build run before this test leaves a stray one there, so the
    cases read an empty site directory and the fixture stories alone."""
    import site_build as sb
    empty_site = tempfile.mkdtemp(prefix="s96w-nosite-")
    TMPS.append(empty_site)
    saved_site, sb.SITE = sb.SITE, empty_site
    try:
        _wire_cases(fails, sb)
    finally:
        sb.SITE = saved_site


def _wire_cases(fails, sb):
    print("1. the Wire page: the same bytes with entries, an honest page without")
    dl = "OCTOBER 20, 2026"
    with_entries = sb.render_wire(items(), dl, NOW)
    golden = open(os.path.join(FX, "render_wire_main.html"), encoding="utf-8").read()
    guarded(fails, "with entries in the window the page is byte-identical to main's render_wire (stored copy of main's output)",
            lambda: norm(with_entries) == norm(golden))
    live = None
    try:
        src = subprocess.run(["git", "show", f"{MAIN_REF}:site_build.py"], cwd=HERE, capture_output=True, text=True).stdout
        if src:
            tmp = tempfile.mkdtemp(prefix="s96w-main-")
            TMPS.append(tmp)
            open(os.path.join(tmp, "site_build_main.py"), "w", encoding="utf-8").write(
                src.replace("HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = {HERE!r}", 1))
            sys.path.insert(0, tmp)
            try:
                import site_build_main as m
                live = m.render_wire(items(), dl, NOW)
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("site_build_main", None)
    except Exception:                                        # noqa: BLE001  a shallow clone has no such ref
        live = None
    if live is not None:
        guarded(fails, f"...and to main's own render_wire run now from git ({MAIN_REF})", lambda: norm(with_entries) == norm(live))
    else:
        print(f"  --   main's render_wire could not be run from git ({MAIN_REF} not in this clone); the stored copy above stands")
    guarded(fails, "with entries it lists the three fixture rows", lambda: with_entries.count('class="wr-r"') == 3)
    old = sb.render_wire(items(), dl, LATER)
    guarded(fails, "with every entry past the window render_wire still returns a page (it returned None on main)",
            lambda: isinstance(old, str) and len(old) > 2000)
    txt = re.sub(r"<[^>]+>", " ", old or "")
    txt = re.sub(r"\s+", " ", txt)
    guarded(fails, "...it keeps the Wire's frame: title, h1 and the page path",
            lambda: "<title>The Wire - " in old and "<h1>The Wire</h1>" in old and 'href="https://gocheckmycrypto.com/wire"' in old)
    guarded(fails, "...it names the window and says plainly that no entries fall in it",
            lambda: "No wire entries fall in the last 48 hours." in txt and "0 entries, last 48 hours" in txt)
    guarded(fails, "...it invents no entry: no row, no filter, none of the fixture titles", lambda: 'class="wr-r"' not in old
            and 'class="wr-d"' not in old and "FIXTURE" not in old)
    guarded(fails, "...the data's own as-of stamp is shown stale by the site's rule, with the newest entry's date",
            lambda: 'class="data-stamp stale"' in old and "Stale data." in old and "Oct 20, 2026" in txt)
    bare = sb._wire_empty_page([], dl, NOW) or ""               # the site directory is empty: no snapshot either
    guarded(fails, "...and with no entry of any age on record it is still stale, and says so",
            lambda: 'class="data-stamp stale"' in bare and "no entry on record" in bare)
    guarded(fails, "...a page just inside the window is not marked stale",
            lambda: 'class="data-stamp stale"' not in sb.render_wire(items(), dl, dt.datetime(2026, 10, 20, 15, 0, tzinfo=UTC)))
    guarded(fails, "...the empty page carries no em dash", lambda: not DASH.search(old))
    guarded(fails, "the stale stamp reads the build's clock it is handed, not the wall clock (same input, same bytes)",
            lambda: norm(sb.render_wire(items(), dl, LATER)) == norm(old))
    # the old callers of data_stamp are untouched
    far = dt.datetime(2027, 1, 1, tzinfo=UTC)
    far_txt = re.sub(r"<[^>]+>", " ", sb.render_wire(items(), dl, far) or "")
    guarded(fails, "the stale stamp's age is counted to the clock the build holds (72 days to January 1, 2027), not the wall clock",
            lambda: "about 72 days ago" in far_txt)
    guarded(fails, "data_stamp without a clock still reads the wall clock (the Board's callers are unchanged)",
            lambda: "Stale data." in sb.data_stamp({"generated_utc": "2026-01-01T00:00:00Z"}))


def source_cases(fails):
    print("2. the build writes the page whatever the window holds")
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "wire.html is written without an `if _wire:` guard", lambda: not re.search(r"if _wire:\s*\n\s*w\(\"wire\.html\"", src)
            and re.search(r'w\("wire\.html", _wire\)', src))
    guarded(fails, "data/coins-mini.json is written without an `if _cm_payload:` guard",
            lambda: not re.search(r"if _cm_payload:\s*\n\s*w\(", src))
    import site_build as sb
    guarded(fails, "the mini-board file is an empty list, not nothing, when the Top 100 is empty",
            lambda: json.dumps(sb.coins_mini_payload({}), separators=(",", ":")) == "[]")
    guarded(fails, "this script and the build have no em dash", lambda: not DASH.search(open(__file__, encoding="utf-8").read())
            and not DASH.search(src))


def clock_cases(fails):
    print("3. sprint 9.4's sitemap case reads the fixtures' own clock, not today's")
    import sprint94_test as s94
    import verify_pipeline as vp
    tmp = tempfile.mkdtemp(prefix="s96w-vd-")
    TMPS.append(tmp)
    # the canary's own 9.3 fixture: the October 15 evening Bitcoin verdict, whose made_utc verdict.record_from takes from
    # the WALL CLOCK. It is restamped 2099 here so the case does not depend on the day it is run: any stamp later than
    # October 21 reproduces the incident, and 2099 always does.
    old = vp._verdict_fixture_dir(tmp)
    f = os.path.join(tmp, "verdict", "2026-10-15-evening.json")
    d = json.load(open(f, encoding="utf-8"))
    d["made_utc"] = "2099-01-01T00:00:00Z"
    json.dump(d, open(f, "w", encoding="utf-8"))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            got = s94.unit()
    finally:
        vp._verdict_restore(old)
        for m in ("sprint94_test", "sprint93_test", "sprint92_test"):
            sys.modules.pop(m, None)
    bad = [x for x in got if "news sitemap inside its 48 hours" in x]
    guarded(fails, f"with a non-mover /why/ page stamped far in the future, every mover's /why/ URL is still in the news sitemap ({bad or 'ok'})",
            lambda: not bad)
    guarded(fails, "...and nothing else in sprint 9.4's cases moved", lambda: not got)
    s = open(os.path.join(HERE, "scripts", "sprint94_test.py"), encoding="utf-8").read()
    guarded(fails, "the check still asserts every mover URL (it was pinned, not loosened): all of mv_paths in the sitemap",
            lambda: "all(f\"{sb.ORIGIN}{p}<\" in news for p in mv_paths)" in s)


def unit():
    fails = []
    for name, fn in (("the page", wire_cases), ("the build writes it", source_cases), ("9.4 clock", clock_cases)):
        group(fails, name, fn)
    cleanup()
    return fails


def canary_unit():
    """The cases the canary runs: the page and the build's source. The 9.4 clock case is left to the suite (it runs sprint 9.4's
    whole unit again, and the canary already runs that once)."""
    fails = []
    for name, fn in (("the page", wire_cases), ("the build writes it", source_cases)):
        group(fails, name, fn)
    cleanup()
    return fails


def tree(root):
    """The cases that read a built tree: the Wire and the mini-board file are built, and the Wire is either a list or the honest page."""
    fails = []
    print(f"5. the built tree {root}")
    rd = lambda rel: open(os.path.join(root, rel), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(root, rel)) else ""
    w = rd("wire.html")
    guarded(fails, "wire.html is built", lambda: bool(w))
    guarded(fails, "wire.html lists entries, or says plainly that none fall in the window with a stale stamp",
            lambda: 'class="wr-r"' in w or ("No wire entries fall in the last 48 hours." in w and 'class="data-stamp stale"' in w))
    guarded(fails, "data/coins-mini.json is built", lambda: os.path.exists(os.path.join(root, "data", "coins-mini.json")))
    return fails


LAST_PUB = None


def build_case(fails):
    """A WHOLE THROWAWAY BUILD with the build clock past every story's window and every source refusing: the loop's state.
    The canary's own structural list (fixtures/sprint95/urls_main.txt) is then checked against the tree."""
    global LAST_PUB
    print("4. a whole build with every story older than the Wire's window")
    import site_build as sb
    import living_tables as lt
    import sprint96h_test as h

    def lines(cmd):
        r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        return set(x for x in r.stdout.split("\n") if x)
    before, before_new = lines(["git", "diff", "--name-only"]), lines(["git", "ls-files", "--others", "--exclude-standard"])
    tmp = tempfile.mkdtemp(prefix="s96w-build-")
    TMPS.append(tmp)
    stored = os.path.join(tmp, "living-tables.json")
    shutil.copy(os.path.join(HERE, "site", "data", "living-tables.json"), stored)
    saved = (sb.PUBLISH, lt.OUT, lt._get, lt.FLOWS, sb._NOW_CACHE)
    sb.PUBLISH, lt.OUT, lt._get, lt.FLOWS = os.path.join(tmp, "publish"), stored, h.refusing, os.path.join(tmp, "no-flows.json")
    sb._NOW_CACHE = dt.datetime(2027, 1, 1, tzinfo=UTC)
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            sb.build()
        pub = LAST_PUB = sb.PUBLISH
        rows = sb._wire_rows(sb.load_content(), sb._build_now())
        guarded(fails, f"the state under test: no story or reading falls in the window ({len(rows)} rows)", lambda: not rows)
        w = os.path.join(pub, "wire.html")
        guarded(fails, "the build wrote wire.html", lambda: os.path.exists(w))
        txt = open(w, encoding="utf-8").read() if os.path.exists(w) else ""
        guarded(fails, "...honest and stale", lambda: "No wire entries fall in the last 48 hours." in txt and "data-stamp stale" in txt)
        guarded(fails, "data/coins-mini.json is built", lambda: os.path.exists(os.path.join(pub, "data", "coins-mini.json")))
        urls = [ln.strip() for ln in open(os.path.join(HERE, "fixtures", "sprint95", "urls_main.txt"), encoding="utf-8") if ln.strip()]
        missing = [u for u in urls if not os.path.exists(os.path.join(pub, u))]
        guarded(fails, f"NO URL REMOVED: every page of the structural set is built ({len(urls)}; missing {missing[:6]})", lambda: not missing)
    finally:
        sb.PUBLISH, lt.OUT, lt._get, lt.FLOWS, sb._NOW_CACHE = saved
        sys.modules.pop("sprint96h_test", None)
        for f in lines(["git", "diff", "--name-only"]) - before:
            subprocess.run(["git", "checkout", "--", f], cwd=HERE)
        for f in lines(["git", "ls-files", "--others", "--exclude-standard"]) - before_new:
            try:
                os.remove(os.path.join(HERE, f))
            except OSError:
                pass


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--build" in args:
        group(fails, "build", build_case)
    cleanup()
    print(f"\nHOTFIX 9.6w: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
