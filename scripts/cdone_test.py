#!/usr/bin/env python3
"""C-DONE (November 2026): the cases this session's items are held to, one group per item, each seen red first.

  1. The home's left column at 1280 and up: every block it can carry has its own cell. The Why Bitcoin moved paragraph
     (Sprint A's "lead" block) was added after the desktop board's grid was written and had no place in it, so the
     browser put it in the first free cell: the top left, above the price line, with an empty cell beside it.
  2. The Netlify ignore rule (U-11): a commit of documents, review screenshots, reports or workflow files alone never
     builds the site. review/ and .github/ were not on the list, so a commit of either alone spent a production build.
  3. Fresh (point 1). The Board's stamp is its freshest read, and a section read earlier prints its own time, so one
     refused source never ages the whole Board. The stale banner's window and cadence are read from the real schedule
     (home.MORNING_ET, home.EDITION_UTC), never typed. A 429's Retry-After cannot stall a build past a bound, and the
     stored series answers when CoinGecko refuses. Fixtures: fixtures/sprint91/pulse and flows of October 16, 12:16 UTC.

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
LEFT_ORDER = ("tape", "narrative", "lead", "since", "why", "wire")
FIRST_COLUMN = ("narrative", "lead", "why", "wire")


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
    for name in LEFT_ORDER:
        guarded(fails, f"'{name}' is placed by a rule (a column and a row), never left to the browser's first free cell",
                lambda name=name: name in cells)
    guarded(fails, "in the first column the blocks keep the page's own order, one row each, below the price line: Brief card, Why Bitcoin moved, the wire",
            lambda: all(cells[b][0] == "1" for b in FIRST_COLUMN)
            and [cells[b][1] for b in FIRST_COLUMN] == sorted({cells[b][1] for b in FIRST_COLUMN})
            and cells["narrative"][1] > cells["tape"][1] and all(cells[b][1] == cells[b][2] for b in FIRST_COLUMN))
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


def unit():
    fails = []
    print("C-DONE")
    try:
        lead_place_cases(fails)
        ignore_rule_cases(fails)
        fresh_cases(fails)
    finally:
        for m in ("sprint95b_test", "sprint95b_fixture", "sprint95_test", "sprint94_test", "sprint93_test", "sprint92_test"):
            sys.modules.pop(m, None)
    return fails


if __name__ == "__main__":
    f = unit()
    print("C-DONE:", "FAIL" if f else "PASS", f"({len(f)} failing)" if f else "")
    for x in f:
        print("  FAILING:", x)
    sys.exit(1 if f else 0)
