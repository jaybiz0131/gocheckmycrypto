#!/usr/bin/env python3
"""C-DONE (November 2026): the cases this session's items are held to, one group per item, each seen red first.

  1. The home's left column at 1280 and up: every block it can carry has its own cell. The Why Bitcoin moved paragraph
     (Sprint A's "lead" block) was added after the desktop board's grid was written and had no place in it, so the
     browser put it in the first free cell: the top left, above the price line, with an empty cell beside it. (Group 6
     moved the block under the tape as one line; the rule this group holds is that every block is placed.)
  2. The Netlify ignore rule (U-11): a commit of documents, review screenshots, reports or workflow files alone never
     builds the site. review/ and .github/ were not on the list, so a commit of either alone spent a production build.
  3. Fresh (point 1). The Board's stamp is its freshest read, and a section read earlier prints its own time, so one
     refused source never ages the whole Board. The stale banner's window and cadence are read from the real schedule
     (home.MORNING_ET, home.EDITION_UTC), never typed. A 429's Retry-After cannot stall a build past a bound, and the
     stored series answers when CoinGecko refuses. Fixtures: fixtures/sprint91/pulse and flows of October 16, 12:16 UTC.
  4. The publish-time gate (points 2 and 8). A red canary at the top of a publishing run stops the run only when the
     code is red. scripts/canary_gate.py runs the canary again on the last code commit; green there means the red is
     data the desk stored since, and the run goes on with every case named in a warning. Proved in a throwaway git
     repository with a stand-in canary (said beside each case, U-10): the real canary is what the workflows run.
  5. Quiet (point 8). The edition gap check's finding on a run that published is a warning, never an ::error::
     annotation on a green run; the gap issue and the exit status are unchanged. The cost ledger states a week's spend
     by Eastern day across the four ledgers the runs write (ops_ledger.week), from fixture rows.
  6. The answer first (point 3; Jack's reading of the home, November 25). The Board leads the home: the tape, then one
     line for Bitcoin since midnight ET, then the Brief card, then the movers and the next dated event, in that order at
     375 (the stylesheet's order) and with the tape in the first row at 1280. The home prints nothing twice: the long
     Why Bitcoin moved paragraph stays on /today/ and the home keeps the one figure no other block prints. With nothing
     scheduled today the block names the next dated event; an empty watchlist draws no block.
  7. Clean and whole (points 4 and 5), from the production crawl of November 25 (stamp 3d286ab, 915 pages). No built page
     links to a page that is not there: a link to a story the desk never published, or to a coin page that is no longer
     built, is drawn as its text. Edition pages print Eastern time and no place. An empty rail is not drawn. "Also
     reported by" names outlets, not their lowercased headlines. A price under a cent is never "$0.00". US spelling.
  8. Found (point 9; Jack's rulings of November 24). The editor's byline is Crypto Cronkite on every story and in each
     NewsArticle's schema, with the story's own published time. The home's title and description say what the site is in
     a searcher's words. About names Go Check My Brands LLC and says nothing about method. An Edition page's title
     carries its date, so no two share one.

Stdlib only.
  python3 scripts/cdone_test.py      # exit 1 on any failure, every failing case named
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
SYSTEM_CSS = os.path.join(HERE, "site", "assets", "system.css")

# the blocks home.py can put in the left column, in the order it writes them (home.LEFT, with "lead" after the Brief card)
LEFT_ORDER = ("tape", "lead", "narrative", "since", "why", "wire")
FIRST_COLUMN = ("narrative", "why", "wire")


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:120]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def read(p):
    return open(p, encoding="utf-8").read()


def left_cells(css):
    """{block: (column text, first row, last row)} for each .h-l block placed from 1280 px, read from the desktop board's rules."""
    import sprint95b_test as s
    _rest, blk = s.block_of(css)
    cells = {}
    for conds, sel, body in s.flatten(blk or ""):
        if not any("min-width:1280px" in c for c in conds):
            continue
        m = re.search(r'\.h-l>\[data-block="([a-z]+)"\]', sel)
        if not m:
            continue
        col = re.search(r"grid-column:\s*([^;]+)", body)
        row = re.search(r"grid-row:\s*(\d+)(?:\s*/\s*span\s+(\d+))?", body)
        if col and row:
            first = int(row.group(1))
            cells[m.group(1)] = (col.group(1).strip(), first, first + int(row.group(2) or 1) - 1)
    return cells


def lead_place_cases(fails):
    print("1. the home's left column from 1280: every block has its own cell")
    import home
    cells = left_cells(read(SYSTEM_CSS))
    guarded(fails, "the block list here is home.py's own (home.LEFT with the lead after the Brief card)",
            lambda: tuple(b for b in LEFT_ORDER if b != "lead") == tuple(home.LEFT) and '_block("lead"' in read(os.path.join(HERE, "home.py")))
    # (the day's line moved from under the Brief card to under the tape with point 3; the rule stands: every block placed)
    for name in LEFT_ORDER:
        guarded(fails, f"'{name}' is placed by a rule (a column and a row), never left to the browser's first free cell",
                lambda name=name: name in cells)
    guarded(fails, "in the first column the blocks keep the page's own order, one row each, below the tape and the day's line: Brief card, top story, the wire",
            lambda: all(cells[b][0] == "1" for b in FIRST_COLUMN)
            and [cells[b][1] for b in FIRST_COLUMN] == sorted({cells[b][1] for b in FIRST_COLUMN})
            and cells["narrative"][1] > cells["lead"][1] > cells["tape"][1] and all(cells[b][1] == cells[b][2] for b in FIRST_COLUMN))
    guarded(fails, "Where Bitcoin stands fills the second column beside all of them (its rows run from the Brief card's to the wire's)",
            lambda: cells["since"][0] == "2" and cells["since"][1] == cells["narrative"][1] and cells["since"][2] == cells["wire"][1])


def ignore_rule_cases(fails):
    print("2. the ignore rule: documents, review screenshots, reports and workflow files never build the site")
    import netlify_ignore as ni
    no_build = ("docs/REPORTS/C-DONE-REPORT.md", "docs/REPORTS/C-DONE-shots/home-375-before.png", "docs/HANDOFF.md",
                "review/sprint-9-5b/home-1440.png", "review/c-done/board-375.png", ".github/workflows/health.yml",
                "shots/a.png", "scripts/cdone_test.py", "HANDOFF-2026-08-17.md")
    builds = ("site_build.py", "market_pulse.py", "netlify.toml", "site/assets/system.css", "site/content/2026-11-24-evening-brief.json",
              "learn/what-is-bitcoin.md", "scripts/og_render.py", "site/data/pulse.json", "home.py")
    for p in no_build:
        guarded(fails, f"a commit of {p} alone does not build", lambda p=p: ni.decide([p])[0] is True)
    for p in builds:
        guarded(fails, f"a commit of {p} still builds", lambda p=p: ni.decide([p])[0] is False)
    guarded(fails, "a commit of a report beside a site file still builds (one site file is enough)",
            lambda: ni.decide(["docs/REPORTS/C-DONE-REPORT.md", "review/c-done/a.png", "home.py"])[0] is False)
    src = read(os.path.join(HERE, "verify_pipeline.py"))
    m = re.search(r"TOOL_TREES = \(([^)]*)\)", src)
    guarded(fails, "the canary's read recorder walks review/ and .github/ too, so the list is proven against what a build opens",
            lambda: m and '"review/"' in m.group(1) and '".github/"' in m.group(1))


NEW, OLD = "2026-10-16T12:16:53Z", "2026-10-16T07:05:00Z"


def _fx(name):
    import json
    return json.load(open(os.path.join(HERE, "fixtures", "sprint91", name), encoding="utf-8"))


def _carried(sections=("movers", "market")):
    """The October 16 pulse as market_pulse writes it when `sections` were refused and carried from 07:05 UTC."""
    p = _fx("pulse_2026-10-16T1216Z.json")
    for s in sections:
        p["sections_utc"][s] = OLD
    p["carried_forward"] = list(sections)
    p["generated_utc"] = OLD
    return p


def fresh_cases(fails):
    print("3. fresh: the Board's stamp is its freshest read, an older section prints its own time")
    import datetime as dt
    import json
    import tempfile
    import urllib.error
    import urllib.request
    import home
    import market_pulse as mp
    import site_build as sb
    import snapshot
    flows = _fx("flows_2026-10-16T1216Z.json")
    whole, part = _fx("pulse_2026-10-16T1216Z.json"), _carried()
    s_all, s_c = snapshot.build(whole, flows), snapshot.build(part, flows)
    new_et, old_et = snapshot.stamp_et(NEW), snapshot.stamp_et(OLD)
    at = lambda iso: dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    guarded(fails, "every source answered: the fresh stamp is the snapshot's stamp, so nothing on the page changes",
            lambda: s_all.get("fresh_utc") == s_all["stamp_utc"] == NEW and s_all.get("fresh_et") == s_all["stamp_et"]
            and snapshot.older(s_all) == [])
    guarded(fails, "prices and the whole market carried from 07:05: the fresh stamp is 12:16, the contract's oldest read stays 07:05",
            lambda: s_c.get("fresh_utc") == NEW and s_c["stamp_utc"] == OLD)
    guarded(fails, "the older sections are named once each with their own time (Prices, Whole market), and no fresh one is",
            lambda: [(o["label"], o["read_utc"]) for o in snapshot.older(s_c)] == [("Prices", OLD), ("Whole market", OLD)])
    guarded(fails, "reads a few minutes apart in one run are one reading (the whale board is read a minute before the Board)",
            lambda: (lambda s: s["fresh_utc"] == "2026-10-16T12:15:10Z" and snapshot.older(s) == [])(
                snapshot.build(whole, dict(flows, generated_utc="2026-10-16T12:15:10Z"))))
    pv, _fv = snapshot.views(s_c, part, flows)
    fng, btc = home.t_fng(s_c, {}), home.t_bitcoin(s_c, pv, {})
    guarded(fails, "the Fear and Greed tile, read at 12:16, prints 12:16 and not the carried prices' 07:05",
            lambda: fng and new_et in fng and old_et not in fng and f'data-asof="{NEW}"' in fng)
    guarded(fails, "the Bitcoin tile, carried, prints its own 07:05 inline and carries that instant for the browser's age",
            lambda: btc and old_et in btc and new_et not in btc and f'data-asof="{OLD}"' in btc)
    one_h = at(NEW) + dt.timedelta(hours=1)
    hub = sb.data_stamp(pv, what="Markets", now=one_h)
    guarded(fails, "the Board's stamp line is the fresh read, with no stale banner over five fresh sections",
            lambda: "Stale data" not in hub and f"As of {new_et}" in hub.replace(", 2026", "") and f'data-asof="{NEW}"' in hub)
    guarded(fails, "and it names the older sections on their own line, with their own instant: 'Prices and whole market as of 3:05 AM ET on Oct 16.'",
            lambda: f'<p class="data-stamp ds-older" data-asof="{OLD}">Prices and whole market as of {old_et}.</p>' in hub
            and hub.count("data-asof=") == 2)
    guarded(fails, "the home's Board line says the same in one sentence",
            lambda: snapshot.older_note(s_c) == f" Prices and whole market as of {old_et}." and snapshot.older_note(s_all) == "")
    guarded(fails, "a section's own page stamps that section's own read (sentiment fresh, prices carried)",
            lambda: f'data-asof="{NEW}"' in sb.data_stamp(pv, section="fng", now=one_h)
            and f'data-asof="{OLD}"' in sb.data_stamp(pv, section="movers", now=one_h))
    all_v, _f2 = snapshot.views(s_all, whole, flows)
    late = sb.data_stamp(all_v, what="Markets", now=at(NEW) + dt.timedelta(hours=20))
    cad = home.cadence(at(NEW) + dt.timedelta(hours=20))
    guarded(fails, "the cadence is read from the schedule: the morning slot and the evening slot in Eastern time on the day",
            lambda: cad == "8:15 AM ET and 7:08 PM ET" and home.cadence(at("2026-11-25T12:00:00Z")) == "8:15 AM ET and 6:08 PM ET")
    guarded(fails, "the schedule's own record agrees (desk.json: the Worker dispatches at 23:08 UTC and 8:15 AM New York)",
            lambda: (lambda d: any("23:08" in x for x in d) and any("8:15" in x for x in d))(
                json.load(open(os.path.join(HERE, "desk.json"), encoding="utf-8"))["worker_dispatches"])
            and home.EDITION_UTC == (23, 8) and home.MORNING_ET == (8, 15))
    guarded(fails, "every section 20 hours old: the stale banner, with the cadence from the schedule and no hand-typed 'several times a day'",
            lambda: "Stale data" in late and cad in late and "several times a day" not in late)
    guarded(fails, "'several times a day' is in no banner the build can write (site_build.py's source)",
            lambda: "refreshes it several times a" not in read(os.path.join(HERE, "site_build.py")))
    # the evening read of Nov 24 (23:12 UTC) seen at 8:10 AM ET the next morning is 13 h 58 min old: inside the schedule
    ev = "2026-11-24T23:12:59Z"
    night = dict(all_v, generated_utc=ev, fresh_utc=ev, sections_utc={k: ev for k in all_v["sections_utc"]})
    guarded(fails, "the evening read seen at 8:10 the next morning is inside the schedule's longest gap: no stale banner",
            lambda: "Stale data" not in sb.data_stamp(night, what="Markets", now=at("2026-11-25T13:10:00Z")))
    guarded(fails, "the same read at noon, a morning slot missed, is past it: the stale banner",
            lambda: "Stale data" in sb.data_stamp(night, what="Markets", now=at("2026-11-25T17:00:00Z")))
    guarded(fails, "the ticker's vintage is the prices' own read, not the oldest section's (the ETF table carried a day)",
            lambda: (lambda p: snapshot.stamp_et(NEW) in sb._ticker_built(p))(
                dict(_carried(("etf_flows",)), generated_utc="2026-10-15T12:00:00Z")))
    s_etf = snapshot.build(_carried(("etf_flows",)), flows)
    ld = __import__("morning_line").lead(s_etf, {}, now=one_h)
    guarded(fails, "Why Bitcoin moved opens 'As of' the prices' read when only the ETF table is older",
            lambda: ld and ld["text"].startswith(f"As of {new_et.split(' on ')[0]}"))

    # the bound: a 429 that asks for an hour cannot stall the build
    waits = []

    def refuse(req, timeout=0):
        raise urllib.error.HTTPError("https://api.coingecko.com/x", 429, "Too Many Requests", {"Retry-After": "3600"}, None)
    keep = (mp._sleep, urllib.request.urlopen, mp._last_cg[0])
    mp._sleep, urllib.request.urlopen = waits.append, refuse
    try:
        try:
            mp.get_json("https://api.coingecko.com/api/v3/global")
            raised = False
        except urllib.error.HTTPError:
            raised = True
    finally:
        mp._sleep, urllib.request.urlopen, mp._last_cg[0] = keep
    guarded(fails, "a 429 asking for an hour is tried three times and waits no more than the bound between tries",
            lambda: raised and waits and max(waits) <= mp.RETRY_WAIT_CAP_S <= 120 and sum(waits) <= 3 * mp.RETRY_WAIT_CAP_S)

    # the stored series is the cache: CoinGecko refusing leaves the Board's averages standing, with their through date
    now = at("2026-10-16T12:16:53Z")
    with tempfile.TemporaryDirectory() as root:
        d0 = dt.date(2026, 10, 13)
        closes = {(d0 - dt.timedelta(days=i)).isoformat(): 80000.0 + 10 * i for i in range(260)}
        json.dump({"coin": "bitcoin", "symbol": "BTC", "through": d0.isoformat(), "closes": closes},
                  open(os.path.join(root, "bitcoin.json"), "w", encoding="utf-8"))

        def no(url):
            raise RuntimeError("HTTP Error 429: Too Many Requests")
        assets, notes = mp.section_assets({"BTC": 81000.0}, now=now, fetch=no, root=root, log=lambda m: None)
    guarded(fails, "with CoinGecko refusing every history read, Bitcoin's averages come from the stored series, through its own date",
            lambda: [a["symbol"] for a in assets] == ["BTC"] and assets[0]["through"] == "2026-10-13"
            and assets[0]["price"] == 81000.0 and any("BTC" in n and "429" in n for n in notes))


def publish_gate_cases(fails):
    print("4. the publish-time gate: stored data cannot lock the desk, red code still stops the run")
    import json
    import subprocess
    import tempfile
    try:
        import canary_gate as cg
    except ImportError:
        cg = None
    guarded(fails, "scripts/canary_gate.py exists", lambda: cg is not None)
    if cg is None:
        return
    guarded(fails, "what a run commits is told from code: stories, boards, ledgers and queues are run-written",
            lambda: all(cg.is_run_written(p) for p in ("site/content/2026-11-24-evening-brief.json", "site/data/wire.json",
                                                       "site/data/today/2026-11-24-evening.json", "data/history/bitcoin.json",
                                                       "data/verdict-ledger.json", "ledger.json", "editorial-log.json",
                                                       "share-queue/2026-11-24.json", "regwatch.json")))
    guarded(fails, "and code, tests, fixtures, workflows, styles and the learn pages are not",
            lambda: not any(cg.is_run_written(p) for p in ("site_build.py", "verify_pipeline.py", "scripts/cdone_test.py",
                                                           "fixtures/n1/wire-2026-11-12.json", ".github/workflows/watcher.yml",
                                                           "site/assets/system.css", "learn/what-is-bitcoin.md", "netlify.toml",
                                                           "desk.json", "prompts/editor.md", "config.json")))
    every = set()
    for wf in sorted(os.listdir(os.path.join(HERE, ".github", "workflows"))):
        for m in re.finditer(r"git add ([^&|;\n]*)", read(os.path.join(HERE, ".github", "workflows", wf))):
            every |= {a.strip('"') for a in m.group(1).split() if a not in ("-A", "\\") and not a.startswith("$") and a != '"$f"'}
    guarded(fails, "every path a workflow stages is on the run-written list (the list is the workflows' own)",
            lambda: len(every) >= 15 and all(cg.is_run_written(p.rstrip("/") + "/") or cg.is_run_written(p) for p in every))
    log = [("r3", ["ledger.json"]), ("r2", ["site/content/a.json", "site/data/wire.json"]), ("c1", ["site_build.py", "site/data/pulse.json"]),
           ("r1", ["ledger.json"]), ("c0", ["home.py"])]
    guarded(fails, "the last code commit is the newest one that changed something no run writes",
            lambda: cg.last_code_commit(log) == "c1" and cg.last_code_commit(log[:2]) is None
            and cg.parse_log("@r3\n\nledger.json\n@c1\n\nsite_build.py\nsite/data/pulse.json\n") == [("r3", ["ledger.json"]), ("c1", ["site_build.py", "site/data/pulse.json"])])
    guarded(fails, "the verdict: green passes; red on HEAD's own code stops; red with the code green on its merge tree is data; red both times stops; no base stops",
            lambda: [cg.verdict(0, False, None), cg.verdict(1, True, None), cg.verdict(1, False, 0), cg.verdict(1, False, 1),
                     cg.verdict(1, False, None)] == ["pass", "wiring", "data", "wiring", "wiring"])
    guarded(fails, "red at HEAD's own code is never data, whatever a second run says (HEAD is the code under test)",
            lambda: cg.verdict(1, True, 0) == "wiring")
    guarded(fails, "the failing cases are read from the canary's own lines, once each",
            lambda: cg.failing_cases("  ok   a\n  FAIL the news feed built from the stored wire passes the AI-word scan\n"
                                     "::error::canary: hotfix 9.9h: the news feed built from the stored wire passes the AI-word scan\n"
                                     "LAYER 1 CANARY: FAIL (2 problem(s)) -> promotion BLOCKED (exit 1)\n")
            == ["the news feed built from the stored wire passes the AI-word scan",
                "hotfix 9.9h: the news feed built from the stored wire passes the AI-word scan"])

    # a throwaway repository with a STAND-IN canary (it fails when the stored wire holds the word BAD, or when the code says so)
    def git(repo, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *a], cwd=repo, capture_output=True, text=True)
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, "site", "data"))
        stand_in = ("import sys\nbad = 'BAD' in open('site/data/wire.json').read()\nBROKEN = False\n"
                    "if bad: print('  FAIL the stored wire holds no BAD line')\n"
                    "if BROKEN: print('  FAIL the code is wired')\n"
                    "print('LAYER 1 CANARY: ' + ('FAIL' if bad or BROKEN else 'PASS'))\nsys.exit(1 if bad or BROKEN else 0)\n")
        open(os.path.join(repo, "verify_pipeline.py"), "w").write(stand_in)
        open(os.path.join(repo, "site", "data", "wire.json"), "w").write('{"line": "fine"}')
        git(repo, "init", "-q", "-b", "main"); git(repo, "add", "."); git(repo, "commit", "-q", "-m", "code, gated green")
        cmd = [sys.executable, "verify_pipeline.py", "canary"]
        keep = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            green = cg.gate(repo, cmd)
            open(os.path.join(repo, "site", "data", "wire.json"), "w").write('{"line": "BAD"}')
            git(repo, "add", "site/data/wire.json"); git(repo, "commit", "-q", "-m", "brief: the run stored a line")
            data = cg.gate(repo, cmd)
            trees = git(repo, "worktree", "list").stdout.strip().splitlines()
            open(os.path.join(repo, "verify_pipeline.py"), "w").write(stand_in.replace("BROKEN = False", "BROKEN = True"))
            git(repo, "add", "verify_pipeline.py"); git(repo, "commit", "-q", "-m", "code, broken")
            wiring = cg.gate(repo, cmd)
            open(os.path.join(repo, "site", "data", "wire.json"), "w").write('{"line": "BAD again"}')
            git(repo, "add", "site/data/wire.json"); git(repo, "commit", "-q", "-m", "brief: another line")
            both = cg.gate(repo, cmd)
        finally:
            sys.stdout.close()
            sys.stdout = keep
        stored = json.load(open(os.path.join(repo, "out", "canary-gate.json")))
    guarded(fails, "stand-in canary, green tree: the gate passes, exit 0", lambda: (green["verdict"], green["exit"]) == ("pass", 0))
    guarded(fails, "stand-in canary, a run stored a bad line: the verdict is data, the run goes on (exit 0), the case is named",
            lambda: (data["verdict"], data["exit"], data["canary_exit"], data["base_exit"]) == ("data", 0, 1, 0)
            and data["cases"] == ["the stored wire holds no BAD line"])
    guarded(fails, "the worktree it ran the code commit in is gone afterwards", lambda: len(trees) == 1)
    guarded(fails, "stand-in canary, the code itself broken at HEAD: wiring, the run stops (exit 1)",
            lambda: (wiring["verdict"], wiring["exit"]) == ("wiring", 1))
    guarded(fails, "stand-in canary, bad data on top of broken code: still wiring, the run stops, and the record says so",
            lambda: (both["verdict"], both["exit"], both["base_exit"]) == ("wiring", 1, 1) and stored["verdict"] == "wiring")
    for wf in ("crypto-news-brief.yml", "morning-read.yml"):
        y = read(os.path.join(HERE, ".github", "workflows", wf))
        step = re.search(r"- name: Offline canary.*?(?=\n      - name:)", y, re.S)
        guarded(fails, f"{wf}: the canary step runs the gate, prints its verdict after the quiet block, and leaves with the gate's status",
                lambda step=step: step and "python3 scripts/canary_gate.py || rc=$?" in step.group(0)
                and "python3 verify_pipeline.py canary" not in step.group(0)
                and step.group(0).index('echo "::$token::"') < step.group(0).index("canary_gate.py --annotate")
                and "exit $rc" in step.group(0))
    guarded(fails, "the push-time check still runs the canary itself, hard (verify-crypto-pipeline.yml)",
            lambda: "run: python3 verify_pipeline.py canary" in read(os.path.join(HERE, ".github", "workflows", "verify-crypto-pipeline.yml")))


def quiet_cases(fails):
    print("5. quiet: an advisory finding warns, and the ledger states the week's spend")
    import contextlib
    import datetime as dt
    import io
    import json
    import tempfile
    import edition_check as ec
    import ops_ledger as ol
    keep = (ec.gap_hours, ec.slot_ledger, ec._flag_issue, ec.report_punctuality, ec.newest)
    filed, buf = [], io.StringIO()
    ec.gap_hours = lambda *a, **k: (50.0, {"date": "2026-11-20", "title": "The Evening Brief"})
    ec.slot_ledger = lambda *a, **k: [("2026-11-21", "evening-brief", False), ("2026-11-22", "evening-brief", False),
                                      ("2026-11-23", "evening-brief", True)]
    ec._flag_issue, ec.report_punctuality, ec.newest = filed.append, (lambda *a, **k: None), (lambda *a, **k: None)
    try:
        with contextlib.redirect_stdout(buf):
            rc = ec.main()
    finally:
        ec.gap_hours, ec.slot_ledger, ec._flag_issue, ec.report_punctuality, ec.newest = keep
    out = buf.getvalue()
    guarded(fails, "two of three slots missed: the finding is a ::warning::, there is no ::error:: on the run",
            lambda: "::warning::edition_check: 1 of the last 3 closed slot windows served" in out and "::error::" not in out)
    guarded(fails, "and the gap issue is still filed and the status is still 3 (the workflow's last step reads it)",
            lambda: rc == 3 and len(filed) == 1)
    # the health gate's Board line is about prices: it reads the prices' own read, not the oldest read on the Board
    import api_feeds
    import health_gate as hg
    import snapshot
    s_etf = snapshot.build(_carried(("etf_flows",)), _fx("flows_2026-10-16T1216Z.json"))
    built = dt.datetime(2026, 10, 16, 12, 17, 20, tzinfo=dt.timezone.utc)
    mk = api_feeds.markets_feed([], s_etf, built)
    guarded(fails, "the markets feed names the prices' own read beside the Board's oldest (the ETF table carried five hours)",
            lambda: mk["data"].get("prices_as_of_utc") == NEW and mk["as_of_utc"] == OLD)
    guarded(fails, "the health gate reads it: an ETF table carried seven hours is no 'prices were old' finding, prices carried seven hours is",
            lambda: hg.board_asof({"as_of_utc": "2026-10-16T05:00:00Z", "data": {"prices_as_of_utc": NEW}}) == hg.utc(NEW)
            and hg.board_asof({"as_of_utc": "2026-10-16T05:00:00Z", "data": {}}) == hg.utc("2026-10-16T05:00:00Z")
            and not [f for f in hg.crypto_findings(built, built, built, hg.board_asof(mk), built) if "prices were" in f]
            and [f for f in hg.crypto_findings(built, built, built, hg.utc("2026-10-16T05:00:00Z"), built) if "prices were" in f])
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "data"))
        json.dump({"since": "2026-09-16T16:27Z", "runs": [
            {"t": "2026-11-18T03:59:00Z", "tokens": 100, "usd": 0.01},                                  # Nov 17, 10:59 PM ET: outside
            {"t": "2026-11-18T23:10:00Z", "tokens": 70000, "usd": 0.09, "chartmaster_tokens": 14000, "chartmaster_usd": 0.02},
            {"t": "2026-11-24T14:43:11Z", "tokens": 143294, "usd": 0.2142, "breaking": True},
            {"t": "2026-11-25T04:21:08Z", "tokens": 75488, "usd": 0.0936, "chartmaster_tokens": 14216, "chartmaster_usd": 0.0265},  # Nov 24, 11:21 PM ET
            {"t": "2026-11-25T05:30:00Z", "tokens": 9, "usd": 0.5}]},                                     # Nov 25 ET: outside
            open(os.path.join(root, "ledger.json"), "w"))
        json.dump([{"date": "2026-11-17", "tokens": 5, "usd": 0.3}, {"date": "2026-11-24", "outcome": "read", "tokens": 793, "usd": 0.0015}],
                  open(os.path.join(root, "data", "morning-ledger.json"), "w"))
        json.dump([{"kind": "call", "date": "2026-11-24", "t": "2026-11-24T14:39:29Z", "tokens": 366, "usd": 0.000732},
                   {"kind": "call", "date": "2026-11-24", "t": "2026-11-24T14:39:30Z", "tokens": 530, "usd": 0.00012},
                   {"kind": "run", "date": "2026-11-24", "t": "2026-11-24T14:38:10Z", "tokens": 896, "usd": 0.000852, "day_usd": 0.000852}],
                  open(os.path.join(root, "data", "verdict-ledger.json"), "w"))
        wk = ol.week(dt.date(2026, 11, 24), root=root) if hasattr(ol, "week") else None
        lines = ol.week_lines(wk) if wk and hasattr(ol, "week_lines") else []
    guarded(fails, "the week is seven Eastern days ending on the day named, each day present even when nothing ran",
            lambda: wk and [d["day"] for d in wk["days"]] == ["2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21",
                                                               "2026-11-22", "2026-11-23", "2026-11-24"]
            and wk["days"][1]["runs"] == 0 and wk["days"][1]["usd"] == 0)
    guarded(fails, "a run is counted on its Eastern day (11:21 PM ET on the 24th is the 24th; 10:59 PM on the 17th is outside); the 24th has the breaking run, the Brief and the morning read",
            lambda: wk["days"][6]["runs"] == 3 and wk["days"][0]["runs"] == 1)
    guarded(fails, "the day's tokens and dollars add the Brief's row, the chart read on that row, the morning read and each verdict call once (a verdict run row is its calls' sum, not counted again)",
            lambda: wk["days"][6]["tokens"] == 143294 + 75488 + 14216 + 793 + 366 + 530
            and abs(wk["days"][6]["usd"] - (0.2142 + 0.0936 + 0.0265 + 0.0015 + 0.000732 + 0.00012)) < 1e-9)
    guarded(fails, "the week's totals are the days' sums, and the printed lines end with the total",
            lambda: wk["tokens"] == sum(d["tokens"] for d in wk["days"]) and abs(wk["usd"] - sum(d["usd"] for d in wk["days"])) < 1e-9
            and len(lines) == 9 and lines[-1].startswith("  total") and "$0.4467" in lines[-1])


def _css_rules(width_cond):
    """[(selector, body)] of system.css rules under a media condition containing `width_cond`, comments stripped."""
    import sprint95b_test as s
    return [(sel, body) for conds, sel, body in s.flatten(read(SYSTEM_CSS)) if any(width_cond in c for c in conds)]


def answer_first_cases(fails):
    print("6. the answer first: the Board leads the home, nothing twice, the next dated event, no empty block")
    import copy
    import datetime as dt
    import home
    import morning_line
    import site_build as sb
    import snapshot
    flows, pulse = _fx("flows_2026-10-16T1216Z.json"), _fx("pulse_2026-10-16T1216Z.json")
    snap = snapshot.build(pulse, flows)
    snap["fields"]["coins"]["value"]["BTC"].update(chg_et_day_pct=-0.54, open_et_day="2026-10-16")
    now = dt.datetime(2026, 10, 16, 13, 0, tzinfo=dt.timezone.utc)
    ld = morning_line.lead(snap, {}, now=now)
    guarded(fails, "the home's line is one sentence: Bitcoin since midnight ET with the read's time, and no price",
            lambda: ld.get("home") == "Bitcoin is down 0.54% since midnight ET, as of 8:16 AM ET on Oct 16."
            and "$" not in ld["home"])
    guarded(fails, "the full read /today/ prints is unchanged: the price, the 24 hours, the money, the mood and the movers",
            lambda: ld["text"].startswith("As of 8:16 AM ET on Friday, October 16, Bitcoin is at $") and "Fear and Greed reads" in ld["text"]
            and len(ld["sentences"]) == 2)
    s2 = copy.deepcopy(snap)
    s2["fields"]["coins"]["value"]["BTC"]["open_et_day"] = "2026-10-15"
    guarded(fails, "no ET-day open in the snapshot: the home has no such line (the tape's 24 hours is not printed again)",
            lambda: morning_line.lead(s2, {}, now=now).get("home") == "")
    guarded(fails, "a page built the next morning from last night's read has no such line either (it is not that day's midnight)",
            lambda: morning_line.lead(snap, {}, now=now + dt.timedelta(days=1)).get("home") == "")
    pv, fv = snapshot.views(snap, pulse, flows)
    cal = {"entries": [{"date": "2026-10-19", "time_et": "8:30 AM ET", "title": "CPI: Consumer Price Index",
                        "source": {"name": "FRED release dates", "url": "https://fred.stlouisfed.org/x"}},
                       {"date": "2026-10-19", "time_et": None, "title": "Retail sales", "source": {"name": "FRED release dates"}},
                       {"date": "2026-10-21", "time_et": None, "title": "A later date", "source": {"name": "FRED"}}]}
    above = home.above_fold(snap, pv, fv, {}, None, {}, cal, "", now=now, lead=ld)
    blk = lambda name: (re.search(rf'<section class="[^"]*" data-block="{name}">(.*?)</section>', above, re.S) or [None, ""])[1]
    guarded(fails, "on the home the long paragraph is gone (no card, no 'Spot Bitcoin ETFs took', no second Bitcoin price) and the line stands under the tape",
            lambda: "vd-lead" not in above and "took a net" not in above and "Bitcoin is at $" not in above
            and "Bitcoin is down 0.54% since midnight ET" in blk("lead")
            and above.index('data-block="tape"') < above.index('data-block="lead"') < above.index('data-block="narrative"'))
    guarded(fails, "nothing today: the block is 'Next date', it names Monday, October 19 and both of that day's entries, and says nothing about an empty day",
            lambda: ">Next date: Mon, Oct 19<" in above and "CPI: Consumer Price Index" in blk("today") and "8:30 AM ET" in blk("today")
            and "Retail sales" in blk("today") and "A later date" not in blk("today") and "othing scheduled" not in above
            and "time not published" not in blk("today"))
    today_cal = {"entries": [{"date": "2026-10-16", "time_et": "8:30 AM ET", "title": "Today's print", "source": {"name": "FRED"}}] + cal["entries"]}
    guarded(fails, "an entry today: the block is 'Today' and lists today's only",
            lambda: (lambda b: ">Today<" in b and "Today's print" in b and "CPI" not in b)(home.today(today_cal, now)))
    guarded(fails, "no dated entry ahead: no block at all, never an empty one",
            lambda: home.today({"entries": [{"date": "2026-10-01", "title": "past", "source": {}}]}, now) == "" and home.today({}, now) == "")
    order = {}
    for sel, body in _css_rules("max-width:1099.98px"):
        m, o = re.search(r'\.h-[lr]>(?:\[data-block="([a-z]+)"\]|aside\.(vd))', sel), re.search(r"(?<![a-z-])order:\s*(\d+)", body)
        if m and o:
            order[m.group(1) or m.group(2)] = int(o.group(1))
    guarded(fails, "at 375 the stylesheet orders the blocks: the tape, the day's line, the Brief card, the movers, the next date, then the rest",
            lambda: [k for k, _v in sorted(order.items(), key=lambda kv: kv[1])][:5] == ["tape", "lead", "narrative", "movers", "today"]
            and len(set(order.values())) == len(order) and {"vd", "since", "why", "wire", "money", "mood", "mine"} <= set(order))
    phone = dict(_css_rules("max-width:1099.98px"))
    guarded(fails, "the two columns give their blocks to one column at 375 (display:contents inside a flex column), so the order can cross them",
            lambda: any(".h-cols" in s and "flex-direction:column" in b.replace(" ", "") for s, b in phone.items())
            and any(".h-l" in s and ".h-r" in s and "display:contents" in b.replace(" ", "") for s, b in phone.items()))
    cells = left_cells(read(SYSTEM_CSS))
    guarded(fails, "from 1280 the tape is the first row and the day's line the second, both full width; the verdict card follows",
            lambda: cells["tape"][:2] == ("1 / -1", 1) and cells["lead"][:2] == ("1 / -1", 2)
            and any("aside.vd" in s and re.search(r"grid-row:\s*3", b) for s, b in _css_rules("min-width:1280px")))
    guarded(fails, "an empty watchlist draws no block (the block is hidden while it holds only its empty line)",
            lambda: re.search(r'\[data-block="mine"\]:has\(\.h-mine-empty\)\{display:none\}', re.sub(r"\s+", "", read(SYSTEM_CSS))))


def clean_cases(fails):
    print("7. clean and whole: no dead internal link, Eastern time on the Edition, no empty rail, outlets by name")
    import inspect
    import json
    import tempfile
    import deadlinks
    import edition
    import site_build as sb
    import why_evidence
    with tempfile.TemporaryDirectory() as pub:
        os.makedirs(os.path.join(pub, "articles"))
        page = ('<main><p>See <a href="/articles/gone.html">the story the desk never published</a> and '
                '<a class="x" href="/pulse">the Board</a>, <a href="/old">an old path</a>, '
                '<a href="https://example.org/x">a source</a>, <a href="/coins/sei"><b>SEI</b></a>, '
                '<a href="/articles/gone.html#part">again</a>.</p>'
                "<script>var s='<a href=\"/coins/'+k.toLowerCase()+'\">';</script></main>")
        open(os.path.join(pub, "index.html"), "w").write(page)
        open(os.path.join(pub, "pulse.html"), "w").write("<main>Board</main>")
        open(os.path.join(pub, "_redirects"), "w").write("/old  /pulse  301\n")
        dead0 = deadlinks.check(pub)[0] if "publish" in inspect.signature(deadlinks.check).parameters else None
        n = deadlinks.unlink(pub) if hasattr(deadlinks, "unlink") else None
        after = open(os.path.join(pub, "index.html")).read()
        dead1 = deadlinks.check(pub)[0] if dead0 is not None else None
    guarded(fails, "the check finds the two dead targets and does not read a script's string as a link",
            lambda: dead0 is not None and set(dead0) == {"/articles/gone.html", "/coins/sei"})
    guarded(fails, "unlink draws each dead link as its text (three anchors), keeps the markup inside it, and leaves the live link, the redirect and the outside link alone",
            lambda: n == 3 and "See the story the desk never published and" in after and "<b>SEI</b>, again." in after
            and '<a class="x" href="/pulse">the Board</a>' in after and '<a href="/old">an old path</a>' in after
            and '<a href="https://example.org/x">a source</a>' in after and "'<a href=\"/coins/'+k.toLowerCase()+'\">'" in after)
    guarded(fails, "after it the same check finds nothing", lambda: dead1 == {})
    guarded(fails, "the build runs it last and the list of known dead links is empty (none is excused any more)",
            lambda: "deadlinks.unlink(PUBLISH)" in inspect.getsource(sb.build)
            and json.load(open(os.path.join(HERE, "deadlinks-baseline.json"), encoding="utf-8"))["targets"] == [])
    stamp = getattr(edition, "_et_stamp", None)
    guarded(fails, "an Edition's time is Eastern, on both sides of the clock change: 23:15 UTC is 6:15 PM ET in November and 7:15 PM ET in August",
            lambda: stamp and stamp({"published_utc": "2026-11-24T23:15:00Z"}) == "6:15 PM ET"
            and stamp({"published_utc": "2026-08-19T23:15:00Z"}) == "7:15 PM ET" and stamp({"date": "2026-08-19"}) == "")
    src = read(os.path.join(HERE, "edition.py"))
    guarded(fails, "no Edition page prints UTC or a place (the code holds neither)",
            lambda: "_utc_stamp" not in src and 'desk["place"]' not in src and '"place"' not in src and " UTC\"" not in src)
    guarded(fails, "an empty rail is not drawn; a rail with stories is",
            lambda: edition._rail("") == "" and edition._rail("<article>x</article>") == '<aside class="ed-rail" aria-label="Top stories"><article>x</article></aside>')
    also = getattr(sb, "also_reported", None)
    guarded(fails, "'Also reported by' names each outlet once and prints no lowercased headline and no note about itself",
            lambda: also and also(["Bitcoin Magazine: sec proposes crypto custody rules",
                                   "CoinDesk: u s sec maps out crypto custody in new proposal that furthers its digital...",
                                   "CoinDesk: another line", "Decrypt"]) == '<p class="also-reported">Also reported by Bitcoin Magazine, CoinDesk, Decrypt.</p>'
            and also([]) == "" and also(["", "  "]) == "")
    guarded(fails, "a price under a cent prints its digits, never $0.00; other prices print as they did",
            lambda: why_evidence._price(0.00000347) == sb._price_fmt(0.00000347) != "$0.00" and "0.00" != why_evidence._price(0.0000091)[1:5]
            and why_evidence._price(59348.2) == "$59,348" and why_evidence._price(12.3456) == "$12.35" and why_evidence._price(0.92) == "$0.92")
    guarded(fails, "US spelling in the site's own copy (About, the on-chain explainer)",
            lambda: "clearly labelled" not in read(os.path.join(HERE, "site_build.py"))
            and "nobody has labelled" not in read(os.path.join(HERE, "learn_pages.py")))


def found_cases(fails):
    print("8. found: the Crypto Cronkite byline and schema, the home's title and description, About, dated Edition titles")
    import html as _html
    import json
    import edition
    import site_build as sb
    vis = lambda h: _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S))))
    for stored in ("Crypto Cronkite", "GoCheckMyCrypto", ""):
        story = {"slug": "s", "title": "A story", "dek": "A dek.", "date": "2026-11-24", "author": stored, "body": ["One."],
                 "published_utc": "2026-11-24T23:15:43Z", "kind": "brief", "category": "news", "verdict": "VERIFIED", "sources": []}
        art = sb.render_article(story, [story])
        lds = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', art, re.S)]
        news = [o for d in lds for o in (d.get("@graph") or [d]) if o.get("@type") == "NewsArticle"]
        guarded(fails, f"a story stored under {stored or 'no name'!r} prints 'By Crypto Cronkite', once, and no other byline",
                lambda art=art: vis(art).count("By Crypto Cronkite") == 1 and "By GoCheckMyCrypto" not in vis(art))
        guarded(fails, f"...and its NewsArticle names the author Crypto Cronkite, with the story's own published time and the publisher",
                lambda news=news: len(news) == 1 and news[0]["author"]["name"] == "Crypto Cronkite"
                and news[0]["datePublished"] == "2026-11-24T23:15:43Z" and news[0]["headline"] == "A story"
                and news[0]["publisher"]["name"] and news[0]["author"].get("url", "").endswith("/about.html"))
    guarded(fails, "the Edition's byline is the same name",
            lambda: edition._byline({"author": "GoCheckMyCrypto"}, edition.DESK) == "Crypto Cronkite"
            and edition._byline({}, edition.DESK) == "Crypto Cronkite" and edition.DESK["editor"] == sb.EDITOR)
    guarded(fails, "an Edition page's title carries its date (70 shared 'Evening Brief - GoCheckMyCrypto')",
            lambda: edition._title({"title": "The Evening Brief: A headline"}, "2026-11-24", edition.DESK)
            == "Evening Brief, November 24, 2026 - GoCheckMyCrypto"
            and edition._title({"title": "The Evening Brief: A headline"}, "2026-11-23", edition.DESK)
            != edition._title({"title": "The Evening Brief: A headline"}, "2026-11-24", edition.DESK))
    guarded(fails, "the home's title says it in a searcher's words, inside 70 characters: why crypto moved today, prices, big movers",
            lambda: sb.HOME_TITLE == "Why crypto moved today: prices and big movers - GoCheckMyCrypto" and len(sb.HOME_TITLE) <= 70)
    guarded(fails, "the description names what the site is: why crypto moved today, the Board, the big movers, no hype (inside 170 characters)",
            lambda: all(w in sb.FAMILY_DESC for w in ("Why crypto moved today", "the Board", "the big movers", "No hype"))
            and len(sb.FAMILY_DESC) <= 170 and "shill" not in sb.FAMILY_DESC)
    about = sb.render_about("TEST")
    main = vis(about[about.find("<main"):about.find("</main>")])
    guarded(fails, "About names Go Check My Brands LLC and the editor's byline",
            lambda: "Go Check My Brands LLC" in main and "Crypto Cronkite" in main)
    guarded(fails, "About says nothing about method: no 'How we check' section or link, no word of checks, sources weighed, grading or review",
            lambda: 'href="/method.html"' not in about[about.find("<main"):about.find("</main>")]
            and not re.search(r"how we check|source check|checked against|numbers are checked|is graded|reviews what|we weight|we link every source", main, re.I))


def unit():
    fails = []
    print("C-DONE")
    try:
        lead_place_cases(fails)
        ignore_rule_cases(fails)
        fresh_cases(fails)
        publish_gate_cases(fails)
        quiet_cases(fails)
        answer_first_cases(fails)
        clean_cases(fails)
        found_cases(fails)
    finally:
        for m in ("sprint95b_test", "sprint95b_fixture", "sprint95_test", "sprint94_test", "sprint93_test", "sprint92_test",
                  "canary_gate", "ops_ledger", "health_gate", "deadlinks"):
            sys.modules.pop(m, None)
    return fails


if __name__ == "__main__":
    f = unit()
    print("C-DONE:", "FAIL" if f else "PASS", f"({len(f)} failing)" if f else "")
    for x in f:
        print("  FAILING:", x)
    sys.exit(1 if f else 0)
