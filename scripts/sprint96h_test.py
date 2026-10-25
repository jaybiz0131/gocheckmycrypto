#!/usr/bin/env python3
"""Hotfix 9.6h: the ETF table never vanishes. Each case is named after what it guards.

  python3 scripts/sprint96h_test.py            # unit cases; exit 1 on any failure
  python3 scripts/sprint96h_test.py --build    # also a whole throwaway build with Farside refusing
  python3 scripts/sprint96h_test.py --tree <built publish dir>   # also the cases that read a built tree
  (verify_pipeline.py's canary calls unit() and tree() on the tree it builds)

THE INCIDENT, October 21, 2026: Farside refused GitHub's build machines, the ETF table was left out of
site/data/living-tables.json, and tables/etf-flows-by-issuer.html answered 404 from about 5:10 AM ET. The fix is the
degrade path (entry 2026-10-21-C3): the page is built from the last stored copy, marked stale with its own as-of date,
and the refresh keeps the last good copy of every table it failed to fetch.

NO NETWORK and no model call: every fetcher is replaced by one that refuses. The stored tables below are FIXTURES
(fund names say so); they are written to a scratch file and never to site/data.
"""
import contextlib
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import shutil
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
STORED_AT = "2026-10-20T11:00:00Z"          # 7:00 AM ET on October 20
FILE_AT = "2026-10-19T12:00:00Z"            # the file's own stamp, deliberately not any table's
COMMITTED = os.path.join(HERE, "site", "data", "living-tables.json")
SLUGS = {"etf_by_issuer": "etf-flows-by-issuer", "stables_by_issuer": "stablecoin-supply-by-issuer",
         "whales_by_week": "whale-flows-by-week"}


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


def fixture_tables():
    return {
        "etf_by_issuer": {"issuers": ["FIXTURE A", "FIXTURE B", "FIXTURE C"],
                          "days": [{"date": f"{d} Oct 2026", "total_usd_m": 6.0,
                                    "funds": {"FIXTURE A": 1.0, "FIXTURE B": 2.0, "FIXTURE C": 3.0}}
                                   for d in (14, 15, 16, 17, 20)],
                          "source": "Fixture source"},
        "stables_by_issuer": {"rows": [{"symbol": f"FX{i}", "name": f"Fixture coin {i}",
                                        "circulating_usd": 1_000_000_000 * (9 - i), "chg_7d_pct": 0.5,
                                        "peg": "peggedUSD", "share_pct": 10.0} for i in range(5)],
                              "total_usd": 40_000_000_000, "source": "Fixture source"},
        "whales_by_week": {"weeks": [{"week_ending": f"2026-10-{d:02d}", "net_usd": -5e8, "moves": 3}
                                     for d in (3, 10, 17, 18)], "source": "Fixture source"},
    }


def write_stored(path, tables=None, at=STORED_AT):
    t = fixture_tables()
    if tables is not None:
        t = {k: v for k, v in t.items() if k in tables}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": FILE_AT, "fetched": {k: at for k in t}, "tables": t}, f, indent=1, sort_keys=True)


def refusing(url, as_json=True):
    raise OSError("HTTP Error 403: Forbidden (fixture refusal)")


@contextlib.contextmanager
def scratch_living(stored_tables=None, getter=refusing, flows_ok=False):
    """living_tables pointed at a scratch OUT with every source refusing (or `getter`)."""
    import living_tables as lt
    d = tempfile.mkdtemp(prefix="s96h-")
    TMPS.append(d)
    out = os.path.join(d, "living-tables.json")
    if stored_tables != "none":
        write_stored(out, stored_tables)
    saved = (lt.OUT, lt._get, lt.FLOWS)
    lt.OUT, lt._get = out, getter
    if not flows_ok:
        lt.FLOWS = os.path.join(d, "no-flows.json")
    if hasattr(lt, "FRESH"):
        lt.FRESH = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield lt, out
    finally:
        lt.OUT, lt._get, lt.FLOWS = saved
        if hasattr(lt, "FRESH"):
            lt.FRESH = None


def page_for(key, data):
    import site_build as sb
    spec = next(s for s in sb.CC_TABLES if s["key"] == key)
    got = sb.render_living_table_page(spec, data, "dateline")
    return got[1] if got else None


def refresh_cases(fails):
    print("1. the refresh keeps the last good copy of every table it failed to fetch")
    with scratch_living() as (lt, out):
        before = open(out, "rb").read()
        lt.refresh()
        after = open(out, "rb").read()
    guarded(fails, "every source refusing: living-tables.json is byte for byte what it was", lambda: before == after)

    def one_fails():
        def getter(url, as_json=True):
            if "llama" in url:
                return {"peggedAssets": [{"symbol": f"N{i}", "name": f"New {i}",
                                          "circulating": {"peggedUSD": 1e9 * (i + 1)},
                                          "circulatingPrevWeek": {"peggedUSD": 1e9 * (i + 1)}, "pegType": "peggedUSD"}
                                         for i in range(6)]}
            return refusing(url, as_json)
        with scratch_living(getter=getter) as (lt, out):
            lt.refresh()
            d = json.load(open(out, encoding="utf-8"))
        return d
    d = one_fails()
    guarded(fails, "Farside refusing while DefiLlama answers: the stored ETF table is still in the file, untouched",
            lambda: d["tables"].get("etf_by_issuer") == fixture_tables()["etf_by_issuer"])
    guarded(fails, "...and the table that did refresh is the new one",
            lambda: d["tables"]["stables_by_issuer"]["rows"][0]["symbol"].startswith("N"))
    guarded(fails, "...and the whale table, which could not be rebuilt, is also kept",
            lambda: d["tables"].get("whales_by_week") == fixture_tables()["whales_by_week"])

    def per_table_dates():
        t = d.get("fetched") or {}
        return (t.get("etf_by_issuer") == STORED_AT and t.get("whales_by_week") == STORED_AT
                and t.get("stables_by_issuer") not in (None, STORED_AT))
    guarded(fails, "each table keeps its own as-of time: the kept ones the old stamp, the refreshed one a new stamp",
            per_table_dates)

    with scratch_living() as (lt, out):
        lt.refresh()
        data = lt.load()
    guarded(fails, "load() hands back stored tables however old the file is (it used to return nothing after 30 hours)",
            lambda: data and set(data["tables"]) == set(SLUGS))
    guarded(fails, "load() names the tables that were not refreshed this run as stale",
            lambda: data and set(data.get("stale") or ()) == set(SLUGS))


def page_cases(fails):
    print("2. the page is present and marked stale, with its own as-of date")
    with scratch_living() as (lt, out):
        lt.refresh()
        data = lt.load()
    h = page_for("etf_by_issuer", data) if data else None
    guarded(fails, "Farside refusing: the ETF page is built (not None) from the stored table", lambda: h and "FIXTURE A" in h)
    guarded(fails, "the page says it is stale", lambda: h and re.search(r'class="data-stamp stale"', h))
    guarded(fails, "the stale line carries the table's own as-of date and time (Oct 20, 2026, 7:00 AM ET)",
            lambda: h and "Oct 20, 2026" in re.search(r'class="data-stamp stale".*?</span>', h, re.S).group(0)
            and "7:00 AM ET" in re.search(r'class="data-stamp stale".*?</span>', h, re.S).group(0))
    guarded(fails, "the page does not claim to be rebuilt fresh while it is stale", lambda: h and "Rebuilt at every site build" not in h)
    guarded(fails, "no em dash on the page", lambda: h and not DASH.search(h))
    fresh = dict(data)
    fresh["stale"] = []
    hf = page_for("etf_by_issuer", fresh)
    guarded(fails, "a table that was refreshed carries no stale mark", lambda: hf and "data-stamp stale" not in hf)

    print("3. no stored table: the page says Not read yet")
    with scratch_living(stored_tables="none") as (lt, out):
        lt.refresh()
        d2 = lt.load()
    guarded(fails, "nothing stored and nothing read: load() still returns a dict, not None, so the build goes on",
            lambda: isinstance(d2, dict))
    h2 = page_for("etf_by_issuer", d2 or {"tables": {}})
    guarded(fails, "the ETF page is still built, and says 'Not read yet'", lambda: h2 and "Not read yet" in h2)
    guarded(fails, "...and carries no table and no invented number", lambda: h2 and "<tbody>" not in h2)
    with scratch_living(stored_tables="none") as (lt, out):
        lt.refresh()
        guarded(fails, "a refresh that read nothing and had nothing stored writes no file", lambda: not os.path.exists(out))

    print("4. every other living table has the same path")
    for key in ("stables_by_issuer", "whales_by_week"):
        hp = page_for(key, data)
        guarded(fails, f"{key}: source refusing, the page is built from the stored table and marked stale with its date",
                lambda hp=hp: hp and "data-stamp stale" in hp and "Oct 20, 2026" in hp)
        hn = page_for(key, d2 or {"tables": {}})
        guarded(fails, f"{key}: nothing stored, the page says Not read yet", lambda hn=hn: hn and "Not read yet" in hn)
    only = {"tables": {k: v for k, v in fixture_tables().items() if k != "etf_by_issuer"}, "fetched": {},
            "fetched_at": STORED_AT, "stale": []}
    guarded(fails, "a data dict with no ETF table (the file as main has it today) still yields all three pages",
            lambda: all(page_for(k, only) for k in SLUGS))


def committed_cases(fails):
    print("5. the committed file at head, read by a build with every source refusing")
    try:
        d = json.load(open(COMMITTED, encoding="utf-8"))
    except Exception:
        d = {}
    etf = (d.get("tables") or {}).get("etf_by_issuer") or {}
    guarded(fails, "site/data/living-tables.json carries an ETF table with at least 4 reconciled days and its own stamp",
            lambda: len(etf.get("days") or []) >= 4 and (d.get("fetched") or {}).get("etf_by_issuer"))
    guarded(fails, "every committed table carries its own as-of stamp",
            lambda: all((d.get("fetched") or {}).get(k) for k in (d.get("tables") or {})))
    if not etf:
        return
    dd = tempfile.mkdtemp(prefix="s96h-head-")
    TMPS.append(dd)
    shutil.copy(COMMITTED, os.path.join(dd, "living-tables.json"))
    with scratch_living(stored_tables="none") as (lt, out):
        lt.OUT = os.path.join(dd, "living-tables.json")
        before = open(lt.OUT, "rb").read()
        lt.refresh()
        data = lt.load()
        after = open(lt.OUT, "rb").read()
    h = page_for("etf_by_issuer", data) if data else None
    when = (d["fetched"]["etf_by_issuer"])
    import site_build as sb
    want = sb._cc_stamp(when)
    guarded(fails, "refusing sources: the committed file is left byte for byte as it was", lambda: before == after)
    guarded(fails, "refusing sources: the ETF page built from the committed file is marked stale",
            lambda: h and "data-stamp stale" in h and "Not read yet" not in h)
    guarded(fails, f"...and carries the committed table's own as-of ({want})", lambda: h and want and want in h)


def wording_cases(fails):
    print("6. the stale line is in the house form")
    with scratch_living() as (lt, out):
        lt.refresh()
        data = lt.load()
    h = page_for("etf_by_issuer", data) if data else ""
    m = re.search(r'<span class="data-stamp stale">(.*?)</span>', h or "", re.S)
    txt = re.sub(r"<[^>]+>", "", m.group(1)) if m else ""
    guarded(fails, "the label is closed as its own sentence, <b>Stale data.</b>, as the Board's stamp does",
            lambda: m and m.group(1).startswith("<b>Stale data.</b> "))
    guarded(fails, "the line reads as sentences: capitalized, each closed with a period, and ends on the as-of date",
            lambda: txt.startswith("Stale data. The source did not answer this build. These 5 rows are from the last good read, as of ")
            and txt.endswith("2026."))


def workflow_cases(fails):
    print("7. the workflows keep the file, and a merge never drops a stored table")
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: refreshes the living tables with a timeout, never as a gate",
                lambda y=y: re.search(r"timeout \d+ python3 living_tables\.py \|\| true", y))
        guarded(fails, f"{wf}: stages site/data/living-tables.json with the commit",
                lambda y=y: re.search(r"(?m)^ {10}\[ -f site/data/living-tables\.json \] && git add site/data/living-tables\.json$", y))
        guarded(fails, f"{wf}: and keeps it staged when a rebase auto-resolve continues",
                lambda y=y: re.search(r"(?m)^ {18}\[ -f site/data/living-tables\.json \] && git add site/data/living-tables\.json$", y))
    import merge_state as ms
    up = {"fetched_at": "2026-10-21T15:00:00Z", "fetched": {"a": "2026-10-21T15:00:00Z", "b": "2026-10-20T15:00:00Z"},
          "tables": {"a": {"v": "up"}, "b": {"v": "up-old"}}}
    me = {"fetched_at": "2026-10-21T14:00:00Z", "fetched": {"a": "2026-10-21T14:00:00Z", "b": "2026-10-21T14:00:00Z", "c": "2026-10-21T14:00:00Z"},
          "tables": {"a": {"v": "me"}, "b": {"v": "me-new"}, "c": {"v": "me-only"}}}
    got = ms.merge_living(up, me)
    guarded(fails, "merge_state resolves living-tables.json per table: the later stamp wins, a tie goes upstream, no table is dropped",
            lambda: got["tables"] == {"a": {"v": "up"}, "b": {"v": "me-new"}, "c": {"v": "me-only"}}
            and got["fetched_at"] == "2026-10-21T15:00:00Z")
    guarded(fails, "merge_state lists the file as one it may resolve",
            lambda: "site/data/living-tables.json" in ms.KNOWN and "site/data/living-tables.json" in ms.MERGERS)


def wiring_cases(fails):
    print("8. wiring")
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "the build links a living table's lane entry only to a page it wrote: CC_BUILT holds every spec that built",
            lambda: "CC_BUILT.add" in src)
    lsrc = open(os.path.join(HERE, "living_tables.py"), encoding="utf-8").read()
    guarded(fails, "living_tables.py has no em dash", lambda: not DASH.search(lsrc))
    guarded(fails, "this script has no em dash", lambda: not DASH.search(open(__file__, encoding="utf-8").read()))
    guarded(fails, "no URL list entry was removed: the three tables are still in the structural baseline",
            lambda: all(f"tables/{s}.html" in open(os.path.join(HERE, "fixtures", "sprint95", "urls_main.txt"),
                                                  encoding="utf-8").read() for s in SLUGS.values()))


def unit():
    fails = []
    for name, fn in (("refresh keeps last good", refresh_cases), ("pages", page_cases), ("committed file", committed_cases),
                     ("stale wording", wording_cases), ("workflows and merge", workflow_cases), ("wiring", wiring_cases)):
        group(fails, name, fn)
    cleanup()
    return fails


LAST_PUB = None


def build_case(fails):
    """A WHOLE THROWAWAY BUILD with every source refusing, reading a copy of the COMMITTED site/data/living-tables.json (the
    shipped data, not a stand-in), and with the whale source's flows.json out of reach so that table too can only come from the
    stored copy. Tracked files the build dirties are put back."""
    global LAST_PUB
    print("10. a whole build with Farside refusing, reading the committed file")
    import site_build as sb
    import living_tables as lt

    def dirty():
        r = subprocess.run(["git", "diff", "--name-only"], cwd=HERE, capture_output=True, text=True)
        return set(x for x in r.stdout.split("\n") if x)
    def untracked():
        r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=HERE, capture_output=True, text=True)
        return set(x for x in r.stdout.split("\n") if x)
    before, before_new = dirty(), untracked()
    tmp = tempfile.mkdtemp(prefix="s96h-build-")
    TMPS.append(tmp)
    stored = os.path.join(tmp, "living-tables.json")
    shutil.copy(COMMITTED, stored)
    want = sb._cc_stamp((json.load(open(COMMITTED, encoding="utf-8")).get("fetched") or {}).get("etf_by_issuer") or "")
    saved = (sb.PUBLISH, lt.OUT, lt._get, lt.FLOWS)
    sb.PUBLISH, lt.OUT, lt._get = os.path.join(tmp, "publish"), stored, refusing
    lt.FLOWS = os.path.join(tmp, "no-flows.json")
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            sb.build()
        pub = LAST_PUB = sb.PUBLISH
        h = open(os.path.join(pub, "tables", "etf-flows-by-issuer.html"), encoding="utf-8").read() \
            if os.path.exists(os.path.join(pub, "tables", "etf-flows-by-issuer.html")) else ""
        sm = "".join(open(os.path.join(pub, f), encoding="utf-8").read() for f in ("sitemap-archive.xml", "sitemap-priority.xml")
                     if os.path.exists(os.path.join(pub, f)))
        rec = open(os.path.join(pub, "record.html"), encoding="utf-8").read() if os.path.exists(os.path.join(pub, "record.html")) else ""
        guarded(fails, "the build wrote tables/etf-flows-by-issuer.html with Farside refusing", lambda: bool(h))
        guarded(fails, f"...marked stale with the committed table's own as-of ({want})", lambda: "data-stamp stale" in h and bool(want) and want in h)
        guarded(fails, "...and its URL is still in the sitemap", lambda: "/tables/etf-flows-by-issuer<" in sm)
        guarded(fails, "...and the Record still links it", lambda: "/tables/etf-flows-by-issuer.html" in rec)
        for slug in SLUGS.values():
            pg = os.path.join(pub, "tables", slug + ".html")
            guarded(fails, f"every living table page is built with every source refusing, from the stored copy and marked stale: {slug}",
                    lambda pg=pg: os.path.exists(pg) and "data-stamp stale" in open(pg, encoding="utf-8").read())
    finally:
        sb.PUBLISH, lt.OUT, lt._get, lt.FLOWS = saved
        for f in dirty() - before:
            subprocess.run(["git", "checkout", "--", f], cwd=HERE)
        for f in untracked() - before_new:
            os.remove(os.path.join(HERE, f))


def tree(root):
    """The cases that read a built tree. Returns the failures."""
    fails = []
    print(f"9. the built tree {root}")
    pub = lambda rel: os.path.join(root, rel)
    rd = lambda rel: open(pub(rel), encoding="utf-8", errors="replace").read() if os.path.exists(pub(rel)) else ""
    sm = rd("sitemap-archive.xml") + rd("sitemap-priority.xml")
    try:
        stored_keys = set((json.load(open(COMMITTED, encoding="utf-8")).get("tables") or {}))
    except Exception:
        stored_keys = set()
    for key, slug in SLUGS.items():
        h = rd(f"tables/{slug}.html")
        guarded(fails, f"tables/{slug}.html: the committed file holds this table, so the page is never 'Not read yet'",
                lambda key=key, h=h: key not in stored_keys or (h and "Not read yet" not in h))
        guarded(fails, f"tables/{slug}.html is built and in the sitemap", lambda slug=slug, h=h: h and f"/tables/{slug}<" in sm)
        guarded(fails, f"tables/{slug}.html says what it is: a fresh as-of line, a stale mark, or Not read yet",
                lambda h=h: h and (", as of " in h or "data-stamp stale" in h or "Not read yet" in h))
        guarded(fails, f"tables/{slug}.html is never stale without a date",
                lambda h=h: not ("data-stamp stale" in h) or re.search(r"data-stamp stale.*?\d{4}", h, re.S))
    return fails


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--build" in args:
        group(fails, "build", build_case)
    if "--build-tree" in args and LAST_PUB:
        fails += tree(LAST_PUB)
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1])
    cleanup()
    print(f"\nSPRINT 9.6h: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
