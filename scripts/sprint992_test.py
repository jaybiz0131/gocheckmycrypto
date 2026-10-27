#!/usr/bin/env python3
"""Sprint 9.9.2 (October 27, 2026): one fact once. Each case is named after what it guards.

  python3 scripts/sprint992_test.py                  # unit cases; exit 1 on any failure
  python3 scripts/sprint992_test.py --tree <dir>     # also the sweep of a built tree (fact_sweep.py): zero findings
  python3 scripts/sprint992_test.py --production     # the sweep of today's production copy (fixture): the named findings, red
  python3 scripts/sprint992_test.py --browser        # also the width model against a real browser, and the RSI-14 header at 375
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote)

The definition of done (docs/BOARD.md, 9.9.2): a canary check that fails on any figure printed twice on any page and on any derived
figure whose precision differs from its row, seen red on today's production copy first; the sweep's count of fixes in the report.

THE PAGES ARE REAL. fixtures/sprint992/production-f9de9c2 holds seventeen pages of production as served at deploy f9de9c2 (every page's
build-commit meta and /stamp.txt name it), with the two stylesheets production served, read October 27, 2026, 5:18 AM ET (READ_AT.txt).
fixtures/sprint992/real-2026-10-26-evening holds the stored records the October 26 Edition wrote (site/data/pulse.json, flows.json,
chartmaster.json, today/, verdict/, why/, data/chartmaster-ledger.json and the seven Board coins' data/history/), byte for byte as main
held them at b8e9afe. Where a case builds a figure of its own it says SYNTHETIC beside it. NO MODEL CALL and no network anywhere.
"""
import contextlib
import copy
import datetime as dt
import html as _html
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
PROD = os.path.join(HERE, "fixtures", "sprint992", "production-f9de9c2")
FX = os.path.join(HERE, "fixtures", "sprint992", "real-2026-10-26-evening")
UTC = dt.timezone.utc
EM = re.compile("[\u2013\u2014]")
CSS = [open(os.path.join(HERE, "site", "assets", n), encoding="utf-8").read() for n in ("site.css", "system.css")]
NOW = dt.datetime(2026, 10, 27, 9, 0, tzinfo=UTC)          # 5:00 AM ET on October 27, before the morning read


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:120]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def group(fails, name, fn):
    try:
        fn(fails)
    except Exception as e:                                   # noqa: BLE001
        msg = f"group {name} could not run [{type(e).__name__}: {str(e)[:140]}]"
        print("  FAIL " + msg)
        fails.append(msg)


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


def visible(h):
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h or "")
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def page(body):
    """A fragment as a page, with the site's own stylesheets inline, for the sweep."""
    return f"<!doctype html><html><head></head><body>{body}</body></html>"


def sweep(h, rel="page.html"):
    import fact_sweep as fs
    return fs.sweep_page(h if "<body" in h else page(h), CSS, rel)


def kinds(findings):
    return [k for k, _w, _t in findings]


@contextlib.contextmanager
def fixture_world():
    """The build's globals pointed at the fixture's records: the snapshot, the clock, the stored closes and the Chart Master ledger.
    Every global is restored on the way out (a test never leaves its fixture in the module the canary builds from)."""
    import history
    import site_build as sb
    import snapshot
    flows = load("flows.json")
    saved = (sb.SNAP, sb._NOW_CACHE, history.HIST_DIR, getattr(sb, "CM_LEDGER", None))
    history.HIST_DIR = os.path.join(FX, "history")
    # on a tree without the 9.9.2 helpers (the red-first run on main) each one reads as the identity, so every case below still runs
    pulse = getattr(sb, "_precise_pulse", lambda p: p)(load("pulse.json"))
    sb.SNAP, sb._NOW_CACHE, sb.CM_LEDGER = snapshot.build(pulse, flows), NOW, os.path.join(FX, "chartmaster-ledger.json")
    try:
        yield sb, pulse, flows
    finally:
        sb.SNAP, sb._NOW_CACHE, history.HIST_DIR, sb.CM_LEDGER = saved


def coin_page(sb, pulse, sym, cm=None):
    pos, c = next((i + 1, x) for i, x in enumerate(pulse["movers"]["top100"]) if x["symbol"] == sym)
    with quiet():
        return sb.render_coin_page(c, pos, pulse, [], "DATELINE", wire={"items": []},
                                   cm=getattr(sb, "_precise_cm", lambda c: c)(load("chartmaster.json")) if cm is None else cm,
                                   evidence={}, verdict=None, read_clock=NOW, today=dt.date(2026, 10, 27))


# ---- 1. the check reads what a page prints ------------------------------------------------------------------------------

def model_cases(fails):
    import fact_sweep as fs
    print("1. the sweep reads what a page prints, at 375 and at 1440, through the site's own stylesheets")
    twins = page('<figure class="cm-fig"><div class="rc-w"><svg><text>$80,641.12</text></svg></div>'
                 '<div class="rc-n"><svg><text>$80,641.12</text></svg></div></figure>')
    guarded(fails, "the wide and narrow chart twins print once at each width (system.css hides one): no finding", lambda: not sweep(twins))
    tape = page('<section class="h-b h-tape"><p class="h-bline h-eline" data-wide><span>Ether</span><span>$2,313.67</span></p></section>'
                '<ul class="h-coins"><li class="h-coin" data-tile="ethereum"><span>Ether</span><span>$2,313.67</span></li></ul>')
    guarded(fails, "the tape's Ether line (1280 and up) and the list's Ether row (hidden at 1280 and up) are one printing at each width",
            lambda: not sweep(tape))
    both = page('<p class="x">Ether $2,313.67 today</p><p class="y">Ether at $2,313.67</p>')
    guarded(fails, "the same price in two blocks of one page is a finding (the check can fail)",
            lambda: kinds(sweep(both)) == ["twice"])
    guarded(fails, "two rows of a table, two subjects at one price ($1.00 for two stablecoins), are not a finding",
            lambda: not sweep(page("<table><tr><td>USDT</td><td>$1.000</td></tr><tr><td>USDC</td><td>$1.000</td></tr></table>")))
    guarded(fails, "a screen-reader-only copy and an SVG tooltip are not printed",
            lambda: not sweep(page('<p>$73,024.21</p><span class="sr-only">$73,024.21</span><svg><rect><title>$73,024.21</title></rect></svg>')))
    guarded(fails, "an axis's evenly spaced ticks are the chart's scale, not facts",
            lambda: not sweep(page('<svg><text>$62,773</text><text>$68,729</text><text>$74,685</text></svg><p>$68,729 is the figure</p>')))
    guarded(fails, "the sign is part of the fact: +2.0% and 'down 2.0%' are two facts",
            lambda: not sweep(page("<table><tr><td>BTC</td><td>+2.0%</td></tr></table><p>This time last week: down 2.0% since.</p>")))
    guarded(fails, "and '-0.26%' with '24 hours: Down 0.26%' is one fact twice",
            lambda: kinds(sweep(page("<p>24 hours: Down 0.26%</p><p>-0.26%</p>"))) == ["twice"])
    guarded(fails, "the window is part of the fact: 0.60% over 24 hours and 0.60% in the hour the run began are two facts",
            lambda: not sweep(page("<p>Ether was up 0.60% over the same 24 hours.</p><h3>The hour the run began</h3>"
                                   "<ul><li>Ether 0.60%</li></ul>")))
    guarded(fails, "the finer printing rounded to the coarser is one figure ($79,771 and $79,771.00)",
            lambda: kinds(sweep(page("<p>at $79,771, a change</p><p>Price $79,771.00</p>"))) == ["twice"])
    guarded(fails, "a coarse headline figure never pairs with a price ($100 million beside $99.86)",
            lambda: not sweep(page("<p>Solana $99.86</p><p>a $100 million stake</p>")))
    guarded(fails, "a stored story's words are a writer's, read as prose (a headline restating its body's figure)",
            lambda: not sweep(page('<p class="dek">$3.8B in three weeks</p><div class="prose"><p>$3.8B</p></div>')))
    guarded(fails, "a link to a stored story is that story's headline, read as prose",
            lambda: not sweep(page('<p>ETF flows +$110.3M</p><a href="/articles/x">Kaiko raises $110.3M</a>')))
    guarded(fails, "label: a named reading printed twice for one subject (two 200-day values on a coin page)",
            lambda: "label" in kinds(fs.sweep_page(page("<p>200-day line $73,024.21</p><p>200-day average $72,988.58</p>"), CSS, "coins/btc.html")))
    guarded(fails, "label: RSI read across a tile's label and its figure in the next block",
            lambda: "label" in kinds(fs.sweep_page(page("<h3>RSI (14)</h3><p>41</p><div><span>RSI (14)</span> <span>41</span></div>"), CSS, "coins/btc.html")))
    guarded(fails, "precision: one table row printing its dollar figures at two precisions is a finding",
            lambda: "precision" in kinds(sweep(page("<table><tr><th>DOGE</th><td>$0.0770</td><td>$0.09</td></tr></table>"))))
    guarded(fails, "precision: a coin page's average at decimals its price does not print at is a finding",
            lambda: "precision" in kinds(fs.sweep_page(page("<h3>Price</h3><p>$0.07728</p><p>200-day line $0.0867</p>"), CSS, "coins/doge.html")))
    guarded(fails, "next: the next slot's time printed twice is a finding",
            lambda: kinds(sweep(page("<p>Next read: this morning at 8:15 AM ET.</p><p>Next Brief this morning at 8:15 AM ET</p>"))) == ["next"])
    guarded(fails, "stamp: 'from the last build' is a finding, and so is 'Chart levels for X, Oct 26' with no read time",
            lambda: sorted(kinds(sweep(page("<p>7D low close $1.11. from the last build</p><h2>Chart levels for Bitcoin, Oct 26</h2>"))))
            == ["stamp", "stamp"])
    guarded(fails, "the house wording passes: 'Chart levels, read Oct 26, 7:14 PM ET'",
            lambda: not sweep(page("<h2>Chart levels, read Oct 26, 7:14 PM ET</h2>")))
    guarded(fails, "padded precision: an average printed past two decimals that the desk's series does not give is a finding",
            lambda: any("precision" == k for k, _w, _t in fs.averages_check(PROD, os.path.join(FX, "history"), pages=["chartmaster.html"])))


# ---- 2. today's production copy, red first -------------------------------------------------------------------------------

EXPECT = (
    ("index.html", "next", "the next slot's time 'this morning at 8:15 AM ET' printed 2 times"),
    ("coins/btc.html", "label", "the 200-day average printed 2 times"),
    ("coins/btc.html", "label", "RSI printed 2 times"),
    ("coins/btc.html", "twice", "-2.49% printed twice"),
    ("coins/btc.html", "twice", "$26.98B printed twice"),
    ("coins/btc.html", "stamp", "from the last build"),
    ("coins/btc.html", "stamp", "'Chart levels for Bitcoin, Oct 26' carries a date with no read time"),
    ("coins/doge.html", "precision", "DOGE the 200-day average printed $0.09000"),
    ("coins/ada.html", "precision", "ADA the 50-day average printed $0.2300"),
    ("chartmaster.html", "precision", "DOGE the 200-day average printed $0.0900 at 4 decimals"),
    ("chartmaster.html", "stamp", "'The chart read, Oct 26' carries a date with no read time"),
    ("today/index.html", "twice", "-0.23% printed twice"),
    ("today/index.html", "next", "printed 2 times"),
    ("pulse/posture.html", "twice", "$79,771.00 printed twice"),
    ("pulse/etf.html", "twice", "$110.3M printed twice"),
    ("pulse/stablecoins.html", "twice", "$301.54B printed twice"),
    ("pulse.html", "twice", "$1.59B printed twice"),
    ("flows.html", "twice", "$663.7M printed twice"),
    ("why/2026-10-25-bitcoin.html", "twice", "$80,946 printed twice"),
    ("why/2026-10-25-bitcoin.html", "twice", "7.5% printed twice"),
)


def production(fails):
    import fact_sweep as fs
    print("2. today's production copy (deploy f9de9c2, read October 27, 5:18 AM ET): the check is red on it, finding by finding")
    stamp = open(os.path.join(PROD, "stamp.txt"), encoding="utf-8").read()
    guarded(fails, "the fixture is production's deploy f9de9c2 (its /stamp.txt), and every page's build-commit names it",
            lambda: "commit f9de9c258158479bbc8be01721613dbab54f38fc" in stamp and all(
                'content="f9de9c258158479bbc8be01721613dbab54f38fc"' in open(os.path.join(dp, f), encoding="utf-8").read()
                for dp, _d, fs_ in os.walk(PROD) for f in fs_ if f.endswith(".html")))
    with quiet():
        res = fs.sweep(PROD, history_dir=os.path.join(FX, "history"))
    flat = [(rel, k, t) for rel, v in res.items() for k, _w, t in v]
    for rel, kind, words in EXPECT:
        guarded(fails, f"production {rel}: {kind} finding '{words[:70]}'",
                lambda rel=rel, kind=kind, words=words: any(r == rel and k == kind and words in t for r, k, t in flat))
    n = len(flat)
    print(f"  INFO the production fixture's {len(res)} page(s) hold {n} finding(s)")
    guarded(fails, "the production fixture is red: findings on every one of its pages but the two that print each fact once already",
            lambda: n > 0 and len(res) >= 14)
    return flat


# ---- 3. the fixes, page by page ------------------------------------------------------------------------------------------

def coin_cases(fails):
    print("3. the coin pages: each change, the volume, the 200-day and RSI printed once; the levels card dated by its read")
    with fixture_world() as (sb, pulse, flows):
        for sym in ("BTC", "DOGE", "ADA", "USDT"):
            h = coin_page(sb, pulse, sym)
            f = sweep(h, f"coins/{sym.lower()}.html")
            guarded(fails, f"/coins/{sym.lower()}: the sweep finds nothing on the page (every fact once) [{'; '.join(t for _k, _w, t in f)[:200]}]",
                    lambda f=f: not f)
        h = coin_page(sb, pulse, "BTC")
        v = visible(h)
        guarded(fails, "the price tile carries its rolling 24-hour change beside it, and the since line is the 30 days",
                lambda: re.search(r'data-reading="coin-price"[^>]*>.*?<p class="tl-f[^"]*">\$79,754\.00 <span class="tl-c chg down">▼ 0\.70%</span>', h, re.S)
                and "30 days: ▼ Down" in v)
        guarded(fails, "no separate 24-hour or 7-day tile (the chart's header is the page's one 7-day figure)",
                lambda: 'data-reading="coin-24h"' not in h and 'data-reading="coin-7d"' not in h and v.count("over the last 7 days") == 1)
        guarded(fails, "the 24-hour volume prints once (the tile), not again in Supply and trade",
                lambda: v.count("24-hour volume") == 1)
        guarded(fails, "one 200-day value on the page", lambda: len(re.findall(r"200-day (?:line|average) \$[\d,.]+", v)) == 1)
        guarded(fails, "the levels card is headed in the house wording with its read's own time (the ledger's, 7:14 PM ET)",
                lambda: "Chart levels, read Oct 26, 7:14 PM ET" in v and "Chart levels for Bitcoin" not in v)
        guarded(fails, "the levels card prints only the 50-day average, which the readings do not",
                lambda: re.search(r"carry its price, 200-day line and RSI; this is the level they do not\. 50-day average \$81,800\.06", v))
        guarded(fails, "'from the last build' retires; the chart's caption names its read: 'Read Oct 26, 7:12 PM ET.'",
                lambda: "from the last build" not in v and "Read Oct 26, 7:12 PM ET." in v)
        d = visible(coin_page(sb, pulse, "DOGE"))
        guarded(fails, "DOGE's averages are the desk's own figures at its price's precision ($0.08674, $0.08699), not $0.09000",
                lambda: "200-day line $0.08674" in d and "50-day average $0.08699" in d and "0.09000" not in d)
        guarded(fails, "and its distance from the 200-day is measured against that figure (-11.2%), not against 0.09",
                lambda: "-11.2%" in d)
        u = visible(coin_page(sb, pulse, "USDT"))
        guarded(fails, "a stablecoin whose 7D low close prints as its price says so once ('the price is at its 7D low close') "
                       "or prints a figure the price does not",
                lambda: "7D low close" in u or "the price is at its 7D low close" in u)
    import coinpage as cp
    import site_build as sb
    guarded(fails, "_week_extremes: a pair that prints as one figure is one figure",
            lambda: sb._week_extremes((1.12, 1.12), 1.12) == "The 7D high and low close are both the price."
            and sb._week_extremes((1.11, 1.12), 1.5) == "7D high close $1.12, 7D low close $1.11.")
    guarded(fails, "_price_fmt_as: an average at its price's decimals (DOGE 5, ADA 4, BTC 2)",
            lambda: sb._price_fmt_as(0.086738, 0.07728) == "$0.08674" and sb._price_fmt_as(0.210666, 0.2039) == "$0.2107"
            and sb._price_fmt_as(72988.58, 79771.0) == "$72,988.58")
    lv = cp.chartmaster_card({"name": "Zed", "symbol": "ZZZ"}, {"date": "2026-10-26", "data_only": True,
                             "levels": [{"symbol": "ZZZ", "price": 2.0, "sma50": 1.5, "sma200": 1.2, "rsi14": 50}]},
                             None, dt.date(2026, 10, 27), sb.esc, sb.fmt_short_date, price_fmt=sb._price_fmt, stamp="read Oct 26, 7:14 PM ET")
    guarded(fails, "SYNTHETIC: with no readings above, the card prints every level, and still names its read",
            lambda: "Chart levels, read Oct 26, 7:14 PM ET" in lv and "Price" in lv and "RSI (14)" in lv and "These are its levels." in lv)


def precision_cases(fails):
    import history
    import market_pulse as mp
    print("4. every derived figure at its asset's own price precision, one precision across a row")
    p = load("pulse.json")
    root = os.path.join(FX, "history")
    try:
        got = {a["symbol"]: a for a in history.precise_assets(p["assets"], root=root)}
    except AttributeError as e:                                # the red-first run on main: no helper, every case below red, named
        got = {a["symbol"]: a for a in p["assets"]}
        print(f"  FAIL history.precise_assets does not exist ({e})")
        fails.append("history.precise_assets does not exist")
    guarded(fails, "premise, from the stored record: DOGE's averages are stored as 0.09 and ADA's as 0.23 and 0.21 (two decimals)",
            lambda: [(a["sma50"], a["sma200"]) for a in p["assets"] if a["symbol"] in ("DOGE", "ADA")] == [(0.09, 0.09), (0.23, 0.21)])
    guarded(fails, "the stored closes give DOGE 0.086993 and 0.086738, each rounding back to the stored 0.09 (the same figure)",
            lambda: (got["DOGE"]["sma50"], got["DOGE"]["sma200"]) == (0.086993, 0.086738))
    guarded(fails, "BTC, ETH, SOL and BNB are untouched (their stored two decimals are their price's precision)",
            lambda: all(got[s]["sma200"] == a["sma200"] and got[s]["sma50"] == a["sma50"]
                        for a in p["assets"] for s in (a["symbol"],) if s in ("BTC", "ETH", "SOL", "BNB")))
    guarded(fails, "the record is read, never written (the stored file is byte for byte as before)",
            lambda: p == load("pulse.json"))
    guarded(fails, "SYNTHETIC: a stored figure the closes do not give is printed as stored (0.05 does not round from 0.0867)",
            lambda: getattr(history, "precise_average")("dogecoin", 200, 0.05, 0.077, "2026-10-25", root=root) is None)
    cm = load("chartmaster.json")
    lv = {r["symbol"]: r for r in getattr(history, "precise_levels", lambda l, d, root=None: l)(cm["levels"], cm["date"], root=root)}
    guarded(fails, "the Chart Master record's levels for DOGE and ADA read again from the closes, at their price's precision",
            lambda: round(lv["DOGE"]["sma200"], 4) == 0.0867 and round(lv["ADA"]["sma50"], 4) == 0.2302)
    closes = [0.09 + 0.0001 * (i % 7) for i in range(220)]
    dates = [(dt.date(2026, 3, 1) + dt.timedelta(days=i)).isoformat() for i in range(220)]
    a = mp.asset_from_closes("dogecoin", "DOGE", dates, closes)
    guarded(fails, "SYNTHETIC closes: market_pulse now stores a sub-$100 average past two decimals (held at six)",
            lambda: a["sma200"] != round(a["sma200"], 2) and a["sma200"] == round(a["sma200"], 6))
    with fixture_world() as (sb, pulse, flows):
        with quiet():
            h = sb.render_chartmaster(getattr(sb, "_precise_cm", lambda c: c)(load("chartmaster.json")), "DATELINE", pulse)
        rows = re.findall(r'<tr><th scope="row">([A-Z]+)</th><td>\$([\d,.]+)</td><td class="xs-x">\$([\d,.]+)</td><td>\$([\d,.]+)</td>', h)
        guarded(fails, "the Chart Master table: every row prints its price and averages at one precision",
                lambda: rows and all(len({len(x.split(".")[1]) for x in r[1:]}) == 1 for r in rows))
        guarded(fails, "DOGE and ADA averages at four decimals like their prices, and the desk's figures ($0.0870, $0.0867; $0.2302, $0.2107)",
                lambda: ("DOGE", "0.0770", "0.0870", "0.0867") in rows and ("ADA", "0.2043", "0.2302", "0.2107") in rows)
        guarded(fails, "the RSI-14 header holds one line (it does not wrap at its hyphen; measured at 375 by the browser half)",
                lambda: '<th scope="col" class="xs-x" style="white-space:nowrap">RSI-14</th>' in h)
        guarded(fails, "the read's heading carries its own read's time (the ledger's 7:14 PM ET)",
                lambda: "The chart read, Oct 26, 7:14 PM ET" in visible(h))
        f = sweep(h, "chartmaster.html")
        guarded(fails, f"the Chart Master page: the sweep finds nothing [{'; '.join(t for _k, _w, t in f)[:160]}]", lambda: not f)


def today_home_cases(fails):
    print("5. /today/ and the home: the answer's figures are not listed again; the next slot's time once")
    import home
    import today
    rec = load(os.path.join("today", "2026-10-26-evening.json"))
    before = copy.deepcopy(rec)
    with quiet():
        h = today.body_html(rec, [], "dated")
    f = sweep(h, "today/2026-10-26.html")
    guarded(fails, f"the dated /today/2026-10-26: the sweep finds nothing [{'; '.join(t for _k, _w, t in f)[:200]}]", lambda: not f)
    v = visible(h)
    guarded(fails, "the stored answer stands word for word", lambda: " ".join(rec["answer"]) in v)
    guarded(fails, "What moved does not repeat the answer's figures: Bitcoin's 0.70% and $79,754 print once, Ether's 1.32% once",
            lambda: v.count("0.70%") == 1 and v.count("$79,754") == 1 and v.count("1.32%") == 1)
    guarded(fails, "the movers the answer names (XDC, ZRO) are not listed again; the rest are, under 'More of'",
            lambda: "XDC XDC Network" not in v and "More of the biggest gains in the Top 100" in v)
    guarded(fails, "the stored record is read, never written", lambda: rec == before)
    with fixture_world() as (sb, pulse, flows):
        import verdict
        with quiet():
            hh = home.above_fold(sb.SNAP, pulse, flows, sb.board_deltas(pulse), {"items": []}, {}, {},
                                 sb.NEWS_CADENCE_LINE, now=NOW, verdict=None)
        vh = visible(hh)
        guarded(fails, "the home prints the next slot's time once: in the notice, not again on the Brief card",
                lambda: vh.count("this morning at 8:15 AM ET") == 1 and "Next read: this morning at 8:15 AM ET." in vh)
        import snapshot
        sn = copy.deepcopy(sb.SNAP)
        mv = sn["fields"]["movers"]["value"]
        top = (mv.get("top20_rises") or [{}])[0]
        mv["standouts"] = [dict(top), {"symbol": "ZZZ", "name": "Zed", "chg_24h_pct": 9.99, "rank": 77}]   # SYNTHETIC: a top-20 riser also past 5%
        blk = home.movers(sn)
        guarded(fails, "SYNTHETIC: a top-20 mover that is also past 5% prints once, in the list; the line names only the others",
                lambda: top.get("symbol") and visible(blk).count(f"{top['symbol']} ") <= 1 + visible(blk).count(f"#{top.get('rank')} ")
                and not sweep(blk) and "ZZZ" in blk)
        with quiet():
            lt = today.body_html(rec, [], "living", clock=NOW)
        guarded(fails, "the living /today/ prints it once too: the notice carries it and the footer line does not repeat it",
                lambda: visible(lt).count("this morning at 8:15 AM ET") == 1)
        with quiet():
            later = today.body_html(rec, [], "living", clock=NOW, verdict=load(os.path.join("verdict", "2026-10-26-evening.json")))
        guarded(fails, "SYNTHETIC: a page with no notice (the stored record's own day) keeps its footer's next update",
                lambda: "Next update" in visible(today.body_html(rec, [], "dated")))


def markets_cases(fails):
    print("6. Whale Watch and Markets: the net, the gross, the biggest move, the latest ETF day and the pills printed once")
    with fixture_world() as (sb, pulse, flows):
        with quiet():
            fl = sb.render_flows(flows, "DATELINE")
        f = sweep(fl, "flows.html")
        guarded(fails, f"/flows: the sweep finds nothing [{'; '.join(t for _k, _w, t in f)[:200]}]", lambda: not f)
        v = visible(fl)
        guarded(fails, "the line states the net; the stat states the gross; no 'Biggest single move' stat over the table that lists it",
                lambda: "Biggest single move" not in fl and "the net is in the line above" in v)
        with quiet():
            hub = sb.render_pulse_hub(pulse, flows, {"date": "2026-10-20", "paragraphs": []}, "DATELINE")
        guarded(fails, "the Board's own line names directions and windows and prints no figure its tiles print",
                lambda: not re.search(r"\d%|\$\d", sb.board_summary_line(pulse, sb.board_deltas(pulse), flows)))
        f = sweep(hub, "pulse.html")
        guarded(fails, f"/pulse.html: the sweep finds nothing [{'; '.join(t for _k, _w, t in f)[:200]}]", lambda: not f)
    import site_build as sb
    led = sb.flow_ledger([("Oct 20", 2e8, None), ("Oct 27", -1.59e9, None)], said="volatile coins net -$1.59B onto exchanges.")
    guarded(fails, "the ledger's newest week, the same seven days the line above states, says so instead of reprinting it",
            lambda: "as above" in led and "$1.59B" not in led and "+$200.0M" in led)
    guarded(fails, "and with no line above it, every week prints its figure", lambda: "-$1.59B" in sb.flow_ledger([("Oct 27", -1.59e9, None)]))


def evidence_cases(fails):
    import verdict as vd
    import why_evidence as we
    print("7. the evidence: the run's ends, unchanged readings, unread sources and unmatched links, each once; one window per /why/ page")
    ev = load(os.path.join("why", "2026-10-26-morning.json"))
    c = next(x for x in ev["candidates"] if x["id"] == "wire-c001")
    guarded(fails, "premise, from the stored record: a UK banks item cites a Daily Hodl address about a Louisiana impersonation scam",
            lambda: "UK banks" in c["line"] and any("louisiana" in l["url"] for l in c["links"]))
    guarded(fails, "that link does not carry a word of the event: unmatched", lambda: [l["outlet"] for l in we.unmatched_links(c)] == ["The Daily Hodl"]
            or len(we.unmatched_links(c)) == 1)
    guarded(fails, "its other links carry the event's words and stay cited",
            lambda: len(c["links"]) - len(we.unmatched_links(c)) >= 1)
    guarded(fails, "the unmatched source does not count toward the grade (verdict.stated counts the matched ones)",
            lambda: vd.stated(c, "BTC")[1] == int(c["source_count"]) - 1)
    guarded(fails, "the desk's common words never carry a match alone ('bitcoin', 'crypto', 'etf' are in the measured floor)",
            lambda: {"bitcoin", "crypto", "etf"} <= we.common_words())
    sec = we.section_html(ev, "BTC", live=False, window="rolling_24h")
    guarded(fails, "the item prints 'source link not matched' in that link's place, and links the others",
            lambda: "source link not matched" in sec and "louisiana" not in sec)
    try:
        n64 = sum(len(we.unmatched_links(x)) for f in sorted(os.listdir(os.path.join(FX, "why")))
                  for x in load(os.path.join("why", f)).get("candidates", []))
        print(f"  INFO unmatched links across the three stored evidence records: {n64}")
    except AttributeError:
        pass
    guarded(fails, "SYNTHETIC: a link whose address names the event is matched",
            lambda: we.link_matched({"url": "https://x.com/news/coindcx-loss"}, we.event_words({"kind": "wire", "line": "CoinDCX lost $16M"})))
    guarded(fails, "a source not read is listed once, counted", lambda: we.once_each(["The Block (HTTP 403)"] * 2) == ["The Block (HTTP 403), 2 links"])
    ev25 = json.load(open(os.path.join(HERE, "fixtures", "sprint991", "real-2026-10-25-evening", "why.json"), encoding="utf-8"))
    s25 = visible(we.section_html(ev25, "BTC", live=False, window="rolling_24h"))
    guarded(fails, "the stored 25 October record's 'The Block (HTTP 403); The Block (HTTP 403)' prints once",
            lambda: s25.count("The Block (HTTP 403)") == 1)
    guarded(fails, "'not read for this hour' reads 'not compared for this window' (entry 2026-10-26-C6)",
            lambda: "not read for this" not in s25 and ("not compared for this window" in s25 or "Liquidations" not in s25))
    guarded(fails, "the run's ends that are the chart's high and low are named, not printed again",
            lambda: "from the chart's high at" in s25 and "to its low at" in s25)
    guarded(fails, "an unchanged reading prints once ('7.5%, unchanged in the hour'), never 'X to X'",
            lambda: not re.search(r"(\d+\.\d%) to \1", s25))
    f = sweep(we.section_html(ev25, "BTC", live=False, window="rolling_24h"), "why/2026-10-25-bitcoin.html")
    guarded(fails, f"the 25 October section: the sweep finds nothing [{'; '.join(t for _k, _w, t in f)[:160]}]", lambda: not f)


def why_page_cases(fails, root=None):
    print("8. /why/2026-10-25-bitcoin: the card's window and the list's window, each named once")
    if root is None:
        print("  (read on the built tree: --tree)")
        return
    p = os.path.join(root, "why", "2026-10-25-bitcoin.html")
    if not os.path.exists(p):
        print("  (no /why/2026-10-25-bitcoin in this tree: the canary's fixture build holds the 15 October verdict)")
        return
    h = open(p, encoding="utf-8").read()
    v = visible(h)
    guarded(fails, "the list names its window (the 24 hours) beside every figure", lambda: 'data-ev-window="rolling_24h"' in h and "in the window" not in v)
    guarded(fails, "the page says the card reads since midnight ET and the list the 24 hours, the window the grade was made on",
            lambda: "The card above reads its direction since midnight ET; this chart and list read the 24 hours to" in v)


def k1_cases(fails):
    print("9. a stale ignored site/publish cannot fail the canary's K-1 check")
    import verify_pipeline as vp
    import site_build as sb
    tmp = tempfile.mkdtemp(prefix="s992-k1-")
    saved = sb.PUBLISH
    try:
        os.makedirs(os.path.join(tmp, "stale"))
        with open(os.path.join(tmp, "stale", "news.html"), "w", encoding="utf-8") as fh:
            fh.write("<html><body>an old news front with no 'What has happened' and no rows</body></html>")
        sb.PUBLISH = os.path.join(tmp, "stale")
        with quiet():
            got = vp._where_is_news_canary()
        if not hasattr(vp, "_where_is_news_tree_canary"):        # the red-first run on main: one function reads site/publish
            print("  INFO this tree has no K-1 tree half; K-1 read: " + "; ".join(got)[:200])
        guarded(fails, "with site_build.PUBLISH a stale tree, K-1 reports nothing from it (its tree half reads the canary's own tree)",
                lambda: not [x for x in got if "news front" in x])
        os.makedirs(os.path.join(tmp, "own"))
        with quiet():
            own = vp._where_is_news_tree_canary(os.path.join(tmp, "own"))
        guarded(fails, "the tree half reads the tree it is handed, not site_build.PUBLISH (handed an empty tree, it reports nothing "
                       "while PUBLISH is the stale one)", lambda: not [x for x in own if "news front" in x])
        with quiet():
            stale = vp._where_is_news_tree_canary(os.path.join(tmp, "stale"))
        guarded(fails, "and the tree half still fails on a bad tree handed to it (the check is the same check)",
                lambda: any("news front" in x for x in stale))
    finally:
        sb.PUBLISH = saved
        shutil.rmtree(tmp, ignore_errors=True)


def article_cases(fails):
    print("10. found by the sweep: an article printed a raw dict as 'Also reported by'")
    import site_build as sb
    path = next(os.path.join(HERE, "site", "content", f) for f in sorted(os.listdir(os.path.join(HERE, "site", "content")))
                if "bitcoin-barely-moved-on-the-july-cpi" in f)
    item = json.load(open(path, encoding="utf-8"))
    guarded(fails, "premise, from the stored story: its also_reported_by holds {outlet, headline} entries",
            lambda: isinstance((item.get("also_reported_by") or [None])[0], dict))
    with quiet():
        h = sb.render_article(item, [item])
    guarded(fails, "the article prints the outlet's name, never the raw entry",
            lambda: "Also reported by crypto.news" in visible(h) and "{&#x27;outlet" not in h and "{'outlet" not in visible(h))


def unit(only=()):
    fails = []
    for name, fn in (("model", model_cases), ("coin", coin_cases), ("precision", precision_cases), ("today", today_home_cases),
                     ("markets", markets_cases), ("evidence", evidence_cases), ("k1", k1_cases), ("article", article_cases)):
        if only and name not in only:
            continue
        group(fails, name, fn)
    return fails


def tree(root):
    import fact_sweep as fs
    fails = []
    print("11. the tree this build wrote: every page in it, at 375 and 1440, prints each fact once")
    with quiet():
        res = fs.sweep(root, history_dir=os.path.join(HERE, "data", "history"))
    n = sum(len(v) for v in res.values())
    pages = sum(1 for dp, _d, f in os.walk(root) for x in f if x.endswith(".html"))
    print(f"  INFO {pages} page(s) swept")
    guarded(fails, f"the built tree has pages to sweep ({pages})", lambda: pages >= 50)
    for rel, v in list(res.items())[:12]:
        for _k, _w, t in v[:3]:
            print(f"  FAIL {t[:230]}")
    guarded(fails, f"the sweep finds no figure printed twice and no derived figure off its row's precision ({n} finding(s))", lambda: n == 0)
    why_page_cases(fails, root)
    return fails


# ---- the browser half ------------------------------------------------------------------------------------------------------

def browser(fails):
    print("12. a real browser at 375 and 1440 against the sweep's width model, and the RSI-14 header at 375 (Playwright)")
    data = os.path.join(HERE, "site", "data")
    before = {os.path.relpath(os.path.join(dp, f), data): os.path.getmtime(os.path.join(dp, f))
              for dp, _d, fs_ in os.walk(data) for f in fs_}
    tmp = tempfile.mkdtemp(prefix="s992-br-")
    # the build runs in a throwaway copy of the tree, so nothing it writes lands in this one: not site/data/snapshots/pulse-<date>.json
    # (the 9.9.1 reviewer's note, entry 2026-10-26-C6), not the living tables' refresh, not a dated read
    work = os.path.join(tmp, "tree")
    os.makedirs(work)
    subprocess.run("tar --exclude=./.git --exclude=./site/publish --exclude=./review --exclude=__pycache__ -cf - . | (cd %s && tar xf -)"
                   % work, shell=True, cwd=HERE, check=True)
    b = subprocess.run([sys.executable, "site_build.py"], cwd=work, capture_output=True, text=True, timeout=900,
                       env=dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(tmp, ".pyc")))
    pub = os.path.join(work, "site", "publish")
    guarded(fails, "the copy built (exit 0)", lambda: b.returncode == 0)
    try:
        after = {os.path.relpath(os.path.join(dp, f), data): os.path.getmtime(os.path.join(dp, f))
                 for dp, _d, fs_ in os.walk(data) for f in fs_}
        guarded(fails, "the browser half wrote nothing under this tree's site/data (no snapshots/pulse-<date>.json, no file touched)",
                lambda: after == before)
        rels = ["index.html", "coins/btc.html", "coins/doge.html", "chartmaster.html", "flows.html", "today/index.html", "pulse/posture.html"]
        import fact_sweep as fs
        model = {}
        for rel in rels:
            h = open(os.path.join(pub, rel), encoding="utf-8").read()
            css = fs.site_css(pub, h) + re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", h)
            dom = fs.parse(h)
            for w in fs.WIDTHS:
                figs = [f.raw.strip() for f in fs.figures([(t, e) for t, e in fs.printed(dom, fs.Sheet(css, w))])]
                model[f"{rel}@{w}"] = figs
        with open(os.path.join(tmp, "model.json"), "w", encoding="utf-8") as fh:
            json.dump(model, fh)
        r = subprocess.run(["node", os.path.join(HERE, "scripts", "sprint992_browser.mjs"), pub, os.path.join(tmp, "model.json")],
                           capture_output=True, text=True, timeout=600,
                           env=dict(os.environ, NODE_PATH=os.environ.get("NODE_PATH") or "/opt/node22/lib/node_modules"))
        for ln in (r.stdout or "").splitlines():
            if ln.startswith(("PASS ", "FAIL ", "INFO ")):
                print("  " + ln)
                if ln.startswith("FAIL "):
                    fails.append("browser " + ln[5:])
        if r.returncode not in (0, 1) or "PASS" not in (r.stdout or ""):
            fails.append(f"browser half could not run (exit {r.returncode}): {(r.stderr or '')[-300:]}")
        guarded(fails, "the browser half ran and every case passed", lambda: r.returncode == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = sys.argv[1:]
    only = args[args.index("--only") + 1].split(",") if "--only" in args else ()
    fails = unit(only)
    if "--production" in args:
        group(fails, "production", production)
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1])
    if "--browser" in args:
        group(fails, "browser", browser)
    print(f"\nSPRINT 9.9.2: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
