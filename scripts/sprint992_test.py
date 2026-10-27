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
    guarded(fails, "a tile states its figure's window on its window line: XRP's +0.65% over 7 days (the chart) and its price badge "
                   "+0.65% over 24 hours (the morning of October 27) are two facts",
            lambda: not fs.sweep_page(page('<p class="cc-chg">+0.65% over the last 7 days</p><div class="tl-row"><article class="tl">'
                                            '<p class="tl-f">$1.30 <span>\u25b2 0.65%</span></p><p class="tl-w">Spot, US dollars; the '
                                            'change is the rolling 24 hours</p></article></div>'), CSS, "coins/xrp.html"))
    guarded(fails, "two reading tiles are two readings: 1.7% of market cap and +1.7% against the 200-day",
            lambda: not fs.sweep_page(page('<div class="tl-row"><article class="tl"><p class="tl-f">$1B</p><p class="tl-s">1.7% of market cap</p>'
                                            '</article><article class="tl"><p class="tl-f">+1.7%</p><p class="tl-w">Price against its 200-day '
                                            'average</p></article></div>'), CSS, "coins/xrp.html"))
    guarded(fails, "and a tile that repeats another tile's figure in the same window is still a finding",
            lambda: kinds(sweep(page('<div class="tl-row"><article class="tl"><p class="tl-s">24 hours: Down 0.26%</p></article>'
                                     '<article class="tl"><p class="tl-f">-0.26%</p><p class="tl-w">Rolling 24 hours</p></article></div>'))) == ["twice"])
    guarded(fails, "rows by class (a ledger's lrow): two weeks at -$1.04B are two weeks",
            lambda: not sweep(page('<div class="ledger"><div class="lrow"><span>Sep 29</span><span>-$1.04B</span></div>'
                                   '<div class="lrow"><span>Aug 25</span><span>-$1.04B</span></div></div>')))
    guarded(fails, "a grid of tiles named tl-row is not a row: a sentence and a tile in two grids still pair",
            lambda: kinds(sweep(page('<section class="cm-card"><p>Bitcoin up since yesterday, and $1.59B onto exchanges in 7 days.</p></section>'
                                     '<div class="tl-row"><article class="tl"><p class="tl-f">-$1.59B</p><p class="tl-w">onto exchanges, 7 days</p></article></div>'
                                     '<div class="tl-row"><article class="tl"><p class="tl-f">48</p></article></div>'))) == ["twice"])
    guarded(fails, "the finer printing rounded to the coarser is one figure ($79,771 and $79,771.00)",
            lambda: kinds(sweep(page("<p>at $79,771, a change</p><p>Price $79,771.00</p>"))) == ["twice"])
    guarded(fails, "a coarse headline figure never pairs with a price ($100 million beside $99.86)",
            lambda: not sweep(page("<p>Solana $99.86</p><p>a $100 million stake</p>")))
    guarded(fails, "a coarse figure in writing with no subject word in common is not paired ('$3.8B in three weeks' and a bare "
                   "'$3.8B') (fix round 2: this case read the dek as prose at 81b63fa)",
            lambda: not sweep(page('<p class="dek">$3.8B in three weeks</p><div class="prose"><p>$3.8B</p></div>')))
    guarded(fails, "a story link printing a tile's digits on another subject is two facts (Kaiko raises $110.3M; ETF flows +$110.3M) "
                   "(fix round 2: this case read the link as prose at 81b63fa)",
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


# ---- 1b. review 1's five failures, on the pages 81b63fa built (fix round 2) -------------------------------------------------

R2 = os.path.join(HERE, "fixtures", "sprint992", "round2-81b63fa")


def r2_sweep(rel, h=None):
    """The sweep of one page of the 81b63fa build (fixtures/sprint992/round2-81b63fa), or of `h` given as that page's planted copy."""
    import fact_sweep as fs
    if h is None:
        h = open(os.path.join(R2, rel), encoding="utf-8").read()
    return fs.sweep_page(h, fs.site_css(R2, h), rel)


def round2_cases(fails):
    import fact_sweep as fs
    print("1b. review 1 at 81b63fa: each failure, on the page that build printed (fixtures/sprint992/round2-81b63fa)")
    home = r2_sweep("index.html")
    guarded(fails, "failure 1: the home's ETF figure, the Brief line's '$110.3M on the day' beside the ETF tile's +$110.3M, is a finding",
            lambda: any(k == "twice" and "$110.3M" in t for k, _w, t in home))
    guarded(fails, "failure 1: the home's Fear & Greed, the Brief line's 'reads 48' beside the Sentiment tile's 48, is a finding",
            lambda: any(k == "label" and "Fear & Greed" in t for k, _w, t in home))
    # failure 2: no class of the page is set aside as prose. SYNTHETIC pages: a tile's figure beside the same figure inside each
    # class the 81b63fa sweep read as prose.
    tile = '<div class="tl-row"><article class="tl"><p class="tl-l">ETF flows</p><p class="tl-f">+$110.3M</p></article></div>'
    for cls in ("h-nline", "h-bt", "cm-read", "td-read", "summary", "callout", "bp-row", "dek", "keyfact", "bottomline", "bl-read",
                "ed-brief", "nh-x"):
        guarded(fails, f"failure 2: a figure inside class {cls} beside a tile printing it is a finding (SYNTHETIC)",
                lambda cls=cls: "twice" in kinds(sweep(page(tile + f'<div class="{cls}"><p>Spot Bitcoin ETFs took in $110.3M on the '
                                                                     f'day.</p></div>'))))
    guarded(fails, "failure 2: a story link's headline printing a tile's figure is a finding (SYNTHETIC)",
            lambda: "twice" in kinds(sweep(page(tile + '<a href="/articles/x.html">Bitcoin ETFs take in $110.3M</a>'))))
    guarded(fails, "failure 2: a summary sentence restating its story's body is a finding (SYNTHETIC)",
            lambda: "twice" in kinds(sweep(page('<p class="dek">Inflows reached $3.8B in three weeks.</p>'
                                                '<div class="prose"><p>Inflows reached $3.8B in three weeks.</p></div>'))))
    guarded(fails, "a headline restating its own body is one printing under entry 2026-10-27-C8: no finding (SYNTHETIC)",
            lambda: fs.sweep_page(page(
                '<article class="article"><h1>MARA Acquires Texas Site From HIF in $600M Deal</h1><div class="prose"><p>MARA has agreed '
                'to acquire a Texas site from HIF in a $600 million deal.</p></div></article>'), CSS, "articles/x.html") == [])
    guarded(fails, "failure 2: '$600 million' and '$600M' are one figure (SYNTHETIC)",
            lambda: "twice" in kinds(sweep(page('<p class="dek">MARA buys a Texas site for $600 million.</p>'
                                                '<div class="prose"><p>MARA pays $600M for the Texas site.</p></div>'))))
    guarded(fails, "failure 2 (the other side): two facts that share digits in stored writing are two facts, a 25% tariff and a 25% "
                   "stake (SYNTHETIC)",
            lambda: not sweep(page('<div class="ed-brief"><p>The U.S. will impose a 25% tariff on Brazilian goods.</p><p>Polygon '
                                   'Labs sold a 25% stake to Animoca.</p></div>')))
    cm = r2_sweep("chartmaster.html")
    guarded(fails, "failure 3: /chartmaster's Bitcoin RSI, the gauge's 40.8 and the chart read's BTC row 40.6, is a finding",
            lambda: any(k == "label" and "RSI" in t for k, _w, t in cm))
    raw = open(os.path.join(R2, "chartmaster.html"), encoding="utf-8").read()
    for old, new, what in (("<td class=\"xs-x\">$0.0870</td>", "<td class=\"xs-x\">$0.09</td>", "DOGE 50-day $0.0870 planted as $0.09"),
                           ("<td class=\"xs-x\">$0.2302</td>", "<td class=\"xs-x\">$0.23</td>", "ADA 50-day $0.2302 planted as $0.23"),
                           ("<td class=\"xs-x\">$2,539.25</td>", "<td class=\"xs-x\">$2,539</td>", "ETH 50-day $2,539.25 planted as $2,539")):
        guarded(fails, f"failure 4: the Chart Master table's row precision is read: {what} is a precision finding",
                lambda old=old, new=new: old in raw and any(k == "precision" and new.split(">")[1].split("<")[0] in t
                                                            for k, _w, t in r2_sweep("chartmaster.html", raw.replace(old, new))))
    guarded(fails, "failure 4: the unplanted Chart Master table holds its rows at one precision (no precision finding)",
            lambda: not any(k == "precision" for k, _w, t in cm))
    usdt = r2_sweep("coins/usdt.html")
    guarded(fails, "failure 5: /coins/usdt's two stories on the Xinbi seizure ($52.8M twice) is a finding",
            lambda: any(k == "twice" and "$52.8M" in t for k, _w, t in usdt))
    card = ('<article class="card"><h3><a href="/articles/{u}.html">{h}</a></h3><p class="summary">{s}</p></article>')
    grid = lambda *c: page('<div class="grid">' + "".join(c) + "</div>")
    guarded(fails, "a card's headline and its own summary printing one figure in other words are one story's own repeat, one printing "
                   "under C8 ('$90T Market' over 'the $90 trillion market'; the stored headline and summary of August 31, in a SYNTHETIC "
                   "grid)",
            lambda: not sweep(grid(card.format(u="a", h="Ex-Regulators Warn Strict Perps Rules Will Keep $90T Market "
                                                                    "Offshore", s="Former SEC and CFTC officials are urging "
                                                                    "lighter-touch regulation of perpetual futures to bring the $90 "
                                                                    "trillion market into US jurisdiction."),
                                                card.format(u="b", h="Circle buys IBM patents", s="Circle bought patents."))))
    guarded(fails, "two story cards on one event are not two subjects (an archive's two Xinbi cards) (SYNTHETIC)",
            lambda: "twice" in kinds(sweep(grid(card.format(u="a", h="US seizes Xinbi Telegram channels, restrains $52.8M in USDT",
                                                            s="Seized."),
                                                card.format(u="b", h="U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee Scam",
                                                            s="Frozen.")))))
    ev = lambda w, n: (f'<li class="ev-c"><span class="ev-l">{w}</span><span class="ev-t">It came {n} hours after the run began. '
                       f'In the next 60 minutes Bitcoin rose 0.13%, 11% of the rise in the 24 hours.</span></li>')
    guarded(fails, "evidence rows sharing a measured figure and only the list's own wording are two subjects (two events) (SYNTHETIC)",
            lambda: not sweep(page('<ul class="ev-cands">' + ev("US bitcoin ETFs drew $526.7M on Oct. 20.", 7)
                                   + ev("Drift exploit wallet moved $61M in stolen ETH.", 8)
                                   + ev("Switzerland approved a retail bitcoin ETF.", 9).replace("0.13%", "0.21%").replace("11%", "19%")
                                   + "</ul>")))
    rl = lambda u, h: f'<li><a href="/articles/{u}">{h}</a></li>'
    guarded(fails, "a list of headlines mostly about one subject still pairs two that print one figure (BitMine's 4.8% of supply) "
                   "(SYNTHETIC)",
            lambda: "twice" in kinds(sweep(page('<div class="related"><ul>' + rl("a", "Bitmine Accumulates 4.8% of Ethereum Supply")
                                                + rl("b", "BitMine Adds $73 Million in ETH, Pushing Holdings to 4.8% of Supply")
                                                + rl("c", "Bitmine buys 28,086 ETH") + rl("d", "BitMine Ethereum supply update")
                                                + "</ul></div>"))))
    import site_build as sb
    xin = [json.load(open(os.path.join(HERE, "site", "content", f), encoding="utf-8")) for f in
           ("2026-09-11-us-seizes-xinbi-telegram-channels-restrains-52-8m-in-usdt-tied-to-24b-black-market.json",
            "2026-09-09-u-s-freezes-52-8m-in-usdt-tied-to-xinbi-guarantee-scam-marketplace.json")]
    sb._PAGE_USED.clear()
    got = sb._coin_stories({"name": "Tether", "symbol": "USDT"}, xin)
    sb._PAGE_USED.clear()
    guarded(fails, f"failure 5: a coin page lists one event's stories once (the two stored Xinbi stories give {len(got)} item(s))",
            lambda: len(got) == 1)


def _r2_withheld(rel):
    """The 81b63fa build's page passed through the build's own pass (fact_once.withhold), as site_build's w() now writes it."""
    import fact_once as fo
    return fo.withhold(open(os.path.join(R2, rel), encoding="utf-8").read(), rel)


def round2_build_cases(fails):
    import fact_sweep as fs
    print("1c. the build's fixes for review 1, each at its cause (fact_once.py, the gauge, the coin page, the citations)")
    home, gone = _r2_withheld("index.html")
    line = re.search(r'<p class="h-nline">(.*?)</p>', home, re.S)
    lead = "Bitcoin lower over the past 24 hours as spot Bitcoin ETFs took in $110.3M on the day, October 26, and the Fear & Greed index reads 48, neutral."
    guarded(fails, "failure 1: the Morning Brief's lead sentence stands on the home as stored (the feed names the home as its page)",
            lambda: line is not None and _html.unescape(line.group(1)).startswith(lead))
    guarded(fails, "failure 1: the ETF tile yields: no +$110.3M; it says 'In the Brief' and keeps its label, window and source",
            lambda: "+$110.3M" not in home and re.search(r'data-reading="etf-net">.*?<p class="tl-f[^"]*">In the Brief</p>.*?'
                                                        r'one trading day, Oct 26, 2026 \u00b7 Farside Investors', home, re.S) is not None)
    guarded(fails, "failure 1: the Sentiment gauge yields its number (48) and keeps its drawing, its word and its source",
            lambda: '<p class="h-g-n">' not in home and 'class="h-g-arc"' in home and "alternative.me" in home)
    guarded(fails, "failure 1: the home the pass writes holds no finding at 375 or 1440",
            lambda: not fs.sweep_page(home, fs.site_css(R2, home), "index.html"))
    import fact_once as fo
    ed_front = page('<div class="ed-front"><article class="ed-lead"><h2><a href="/articles/a.html">Bitcoin ETFs Draw $197M</a></h2>'
                    '<p class="ed-dek">Bitcoin ETFs drew $197M.</p></article><aside class="ed-rail"><article><h3><a '
                    'href="/articles/b.html">Circle buys IBM patents</a></h3></article></aside></div><section class="ed-brief">'
                    '<p>Bitcoin ETFs drew $197 million on the day.</p></section>')
    ef, _g = fo.withhold(ed_front, "news.html")
    guarded(fails, "K-1: an Edition's lead card prints whole beside its own Brief (the lead is the Brief's own unit, C8) (SYNTHETIC)",
            lambda: "/articles/a.html" in ef and '<p class="ed-dek">Bitcoin ETFs drew $197M.</p>' in ef)
    guarded(fails, "K-1: the lead beside its own Brief is one printing under C8: no finding (SYNTHETIC)",
            lambda: fs.sweep_page(ef, CSS, "news.html") == [])
    art, gone = _r2_withheld("articles/mara-acquires-texas-site-from-hif-in-600m-deal.html")
    raw = open(os.path.join(R2, "articles/mara-acquires-texas-site-from-hif-in-600m-deal.html"), encoding="utf-8").read()
    body = re.search(r'<div class="prose">.*?</div>', raw, re.S).group(0)
    guarded(fails, "a story page's own dek, key fact and body print whole beside its headline (one story, one printing, C8)",
            lambda: raw.count('<p class="dek">') == art.count('<p class="dek">') == 1 and 'class="keyfact"' in art and body in art
                    and "<h1>MARA Acquires Texas Site From HIF in $600M Deal</h1>" in art)
    guarded(fails, "the take stands", lambda: '<div class="take">' in art)
    guarded(fails, "the story's own repeats are one printing: the page holds no finding",
            lambda: fs.sweep_page(art, fs.site_css(R2, art), "articles/mara-acquires-texas-site-from-hif-in-600m-deal.html") == [])
    rel_page = page('<article class="article"><h1>Kaiko Raises $110M</h1><div class="prose"><p>Kaiko raised $110M in a Series B '
                    'extension led by S&amp;P Global.</p></div><div class="related"><h2>Related stories</h2><ul>'
                    '<li><a href="/articles/a">S&amp;P Global leads $110M extension of Kaiko&#x27;s Series B</a></li>'
                    '<li><a href="/articles/b">Circle buys 1,000 patents from IBM</a></li></ul></div></article>')
    import fact_once as fo
    out, _g = fo.withhold(rel_page, "articles/x.html")
    guarded(fails, "failure 2: a related story whose headline prints the body's figure on its subject is withheld; the other stays "
                   "(SYNTHETIC)", lambda: "/articles/a" not in out and "/articles/b" in out and "Related stories" in out)
    lone, _g = fo.withhold(page('<article class="article"><h1>Kaiko Raises $110M</h1><div class="prose"><p>Kaiko raised $110M.</p>'
                                '</div><div class="related"><h2>Related stories</h2><ul><li><a href="/articles/a">S&amp;P Global '
                                'leads $110M extension of Kaiko&#x27;s Series B</a></li></ul></div></article>'), "articles/x.html")
    guarded(fails, "failure 2: a Related stories box left with no story goes with its heading (SYNTHETIC)",
            lambda: "Related stories" not in lone and "/articles/a" not in lone)
    listing = page('<div class="nh-list"><div class="nh-row"><a class="nh-t" href="/articles/a.html">US seizes Xinbi Telegram channels, '
                   'restrains $52.8M in USDT</a><span class="bd-stamp">September 10</span></div><div class="nh-row"><a class="nh-t" '
                   'href="/articles/b.html">U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee Scam Marketplace</a><span '
                   'class="bd-stamp">September 9</span></div></div>')
    lst, _g = fo.withhold(listing, "news/archive/2026-09.html")
    guarded(fails, "a complete listing keeps every entry whole: both stories on one event keep their rows, links and headlines, and no "
                   "pointer line is printed (SYNTHETIC)",
            lambda: lst == listing and "Another report" not in lst)
    guarded(fails, "a page with nothing to withhold comes back byte for byte",
            lambda: fo.withhold(page("<p>Ether $2,313.67 today</p>"), "x.html")[0] == page("<p>Ether $2,313.67 today</p>"))
    fg, _g = fo.withhold(page('<div class="h-mood"><p class="h-g-n">48</p><p class="h-mood-l">Fear &amp; Greed</p></div>'
                              '<section class="h-b h-narrative"><p class="h-nline">The wire leads with a tax delay. The Fear &amp; Greed '
                              'index reads 48, neutral.</p></section>'),
                         "index.html")
    guarded(fails, "the home's Brief card prints whole; the gauge's number that repeats its Fear & Greed reading yields (SYNTHETIC)",
            lambda: "index reads 48" in fg and "The wire leads with a tax delay." in fg and '<p class="h-g-n">' not in fg)
    import site_build as sb
    g = sb.cm_rsi_chart({"rsi14": 40.6, "_rsi_read": "Oct 26, 7:14 PM ET"})
    guarded(fails, "failure 3: the Chart Master gauge reading the chart read's BTC row prints no number of its own and names the read",
            lambda: ">40.6<" not in g and "printed in its BTC row below" in g and "Oct 26, 7:14 PM ET" in g)
    g2 = sb.cm_rsi_chart({"rsi14": 40.8, "_rsi_stamp": "8:17 AM ET on Oct 27"})
    guarded(fails, "failure 3: with no read table on the page the gauge prints its own reading, names Bitcoin and its read time",
            lambda: ">40.8<" in g2 and "Bitcoin\u2019s 14-day RSI, one reading, read 8:17 AM ET on Oct 27" in g2)
    item = json.load(open(os.path.join(HERE, "site", "content",
                                       "2026-08-01-coinkite-warns-coldcard-seeds-carry-far-less-entropy-than-intended.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(HERE, "site", "content",
                                       "2026-08-01-coinkite-warns-coldcard-seeds-carry-far-less-entropy-than-intended.json")) else None
    if item is None:
        import glob
        item = json.load(open(glob.glob(os.path.join(HERE, "site", "content", "*coinkite-warns-coldcard*.json"))[0], encoding="utf-8"))
    with quiet():
        ah = sb.render_article(item, [item])
    guarded(fails, "a source's stored title printing the story's figure ('Decrypt: $38M in Bitcoin Drained ...') is cited by its "
                   "outlet's name, the link kept", lambda: "Drained by Coldcard" not in ah and ">Decrypt</a>" in ah
                   and "decrypt.co/374766/" in ah)
    with fixture_world() as (sbx, pulse, _flows):
        with quiet():
            cmh = sbx.render_chartmaster(getattr(sbx, "_precise_cm", lambda c: c)(load("chartmaster.json")), "DATELINE", pulse)
    guarded(fails, "failure 3: /chartmaster built from the stored data card prints Bitcoin's RSI once (the BTC row), the gauge naming "
                   "the read", lambda: "printed in its BTC row below" in cmh and not any(
                       k == "label" and "RSI" in t for k, _w, t in fs.sweep_page(cmh, CSS, "chartmaster.html")))
    import edition
    ed = json.load(open(os.path.join(HERE, "site", "content", "2026-07-14-morning-brief.json"), encoding="utf-8"))
    src = next(x for x in ed["sources"] if x.get("title") == "Bitcoin ETFs Draw $197M, Ending Eight-Week Outflow Streak")
    guarded(fails, "an Edition brief's citation whose title prints the brief's figure ('Bitcoin ETFs Draw $197M ...' under a brief "
                   "printing $197 million) is cited by the story's date, never dropped (the stored July 14 morning Brief)",
            lambda: edition._cite_label(src, ed, sb.load_content()) == "The desk\u2019s story of July 13, 2026 \u00b7 7:40 AM ET")
    import today
    rec = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))
    with quiet():
        th = today.body_html(rec, [], here="2026-10-15")
    rec20 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-20-evening.json"), encoding="utf-8"))
    with quiet():
        t20 = today.body_html(rec20, [], here="dated")
    guarded(fails, "/today/2026-10-20: a reported wire line stating the stored answer's fact (France's 31% tax) is not listed beside "
                   "it; the answer stands", lambda: _html.unescape(t20).count("31%") == 1 if "31%" in " ".join(rec20.get("answer") or [])
                   else False)
    guarded(fails, "/today/2026-10-15: a row's figure its printed correction quotes (Bitcoin up 0.80%) is not printed again; the "
                   "correction stands whole", lambda: th.count("0.80%") == 1 and "contradicted Bitcoin (up 0.80%)" in _html.unescape(th))


# ---- 1d. fix round 3: review 2 at 3afc3b4, under entry 2026-10-27-C8 (J-18 option (1)) ------------------------------------------

def _units_whole(raw, out, rx):
    """Every element `rx` finds in `raw` is in `out` byte for byte, or not at all: a stored unit printed whole or withheld whole."""
    return all(m.group(0) in out or m.group(1) not in out for m in re.finditer(rx, raw, re.S))


def round3_cases(fails):
    import fact_once as fo
    import fact_sweep as fs
    import site_build as sb
    print("1d. review 2 at 3afc3b4, fixed under entry 2026-10-27-C8: each failure at its cause")
    # FAILURE 1. One printing is exactly what C8 names; every other pair is a finding. SYNTHETIC pages.
    plant = ('<article class="article"><h1>Bitcoin ETFs Draw $150 million</h1><p class="dek">Spot bitcoin ETFs drew $150 million on '
             'Monday.</p><div class="prose"><p>Spot bitcoin ETFs took in $150 million on Monday, the desk\'s figures show.</p></div>'
             '</article>')
    guarded(fails, "failure 1: review 2's plant, '$150 million' three times in one stored article (headline, dek, body), is one printing "
                   "under C8: no finding (SYNTHETIC)", lambda: sweep(page(plant), "articles/x.html") == [])
    guarded(fails, "failure 1: the same article with the figure also in a line the build writes on that page is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page(plant.replace("</article>", '<aside class="board-panel"><div class="bp-row"><span class="bp-k">'
                                                    'ETF flows</span><span class="bp-v">$150 million</span></div></aside></article>')),
                                "articles/x.html")) == ["twice"])
    two_briefs = page('<section class="ed-brief"><div class="ed-brief-cols"><p>Spot bitcoin ETFs took in $150 million on Monday.</p></div>'
                      '</section><section class="ed-brief"><div class="ed-brief-cols"><p>On Monday spot bitcoin ETFs drew $150 million.'
                      '</p></div></section>')
    guarded(fails, "failure 1: one figure in two stored units (two Briefs) is a finding: across units is two printings (SYNTHETIC)",
            lambda: kinds(sweep(two_briefs)) == ["twice"])
    guarded(fails, "failure 1: one figure twice in text the build writes is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page('<p class="lx-dek">Spot bitcoin ETFs took in $150 million on Monday.</p><p class="pc-note">ETFs '
                                     'drew $150 million on Monday.</p>'))) == ["twice"])
    guarded(fails, "failure 1: a stored Brief line beside a data tile printing its figure is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page('<section class="h-b h-narrative"><p class="h-nline">Spot Bitcoin ETFs took in $110.3M on the day.'
                                     '</p></section><div class="tl-row"><article class="tl"><p class="tl-l">ETF flows</p><p class="tl-f">'
                                     '+$110.3M</p></article></div>'))) == ["twice"])
    lead = page('<div class="ed-front"><article class="ed-lead"><h2><a href="/articles/a.html">Bitcoin ETFs Draw $197M</a></h2><p '
                'class="ed-dek">Bitcoin ETFs drew $197M.</p></article></div><section class="ed-brief"><div class="ed-brief-cols"><p>'
                'Bitcoin ETFs drew $197 million on the day.</p></div></section>')
    guarded(fails, "failure 1: an Edition lead beside its own Brief is one printing under C8: no finding (SYNTHETIC)",
            lambda: sweep(lead, "edition/x.html") == [])
    corr = page('<ol class="co-l"><li><p class="co-t">The page showed Bitcoin down 2.13% where it rose 0.80%.</p></li><li><p class="co-t">'
                'The page showed Bitcoin down 2.05% where it rose 0.80%.</p></li></ol>')
    guarded(fails, "failure 1: two corrections quoting one figure are one printing under C8: no finding (SYNTHETIC)",
            lambda: sweep(corr, "corrections.html") == [])
    guarded(fails, "failure 1: a story page's own correction quoting the story's figure is one printing: no finding (SYNTHETIC, the Ostium "
                   "story's shape)",
            lambda: sweep(page('<article class="article"><h1>Ostium loses $18 million to an oracle attack</h1><div class="callout corrected">'
                               '<b>Correction.</b> Ostium\'s loss was first reported at about $18 million; tracing has since put it at $24 '
                               'million.</div><div class="prose"><p>Ostium lost $18 million.</p></div></article>'), "articles/x.html") == [])
    guarded(fails, "failure 1: the sweep has no HELD kind: every pair is a finding or one printing for a reason C8 names",
            lambda: not hasattr(fs, "stands") and not hasattr(fs, "STAND") and '"held"' not in open(fs.__file__, encoding="utf-8").read())
    # /today/2026-10-20 (C8): the evidence item carries the figure, the answer links it; the answer's words are as stored
    import today
    import why_evidence
    rec20 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-20-evening.json"), encoding="utf-8"))
    # the stored records by their own directory: the canary points the module defaults at its 15 October fixture
    ev20 = why_evidence.load("2026-10-20", "evening", os.path.join(HERE, "site", "data", "why"))
    vd20 = None
    try:
        import verdict as _vd
        vd20 = _vd.load("2026-10-20", "evening", os.path.join(HERE, "site", "data", "verdict"))
    except Exception:                                    # noqa: BLE001
        vd20 = None
    with quiet():
        t20 = today.body_html(rec20, [], here="dated", evidence=ev20, verdict=vd20)
    ans = re.search(r'aria-label="The answer"><p>(.*?)</p>', t20, re.S)
    guarded(fails, "/today/2026-10-20: the stored answer prints word for word, its 31% an in-page link to the evidence item that carries it",
            lambda: ans is not None and _html.unescape(re.sub(r"<[^>]+>", "", ans.group(1))) == " ".join(rec20["answer"])
                    and re.search(r'<a class="td-ref" href="#ev-([^"]+)">31%</a>', ans.group(1)) is not None
                    and f'id="ev-{re.search(r"#ev-([^\"]+)", ans.group(1)).group(1)}"' in t20)
    guarded(fails, "/today/2026-10-20: the dated page holds no finding (the answer links the figure the evidence item prints)",
            lambda: sweep(page(t20), "today/2026-10-20.html") == [])

    guarded(fails, "a headline's title case is read: '$730 Million' and '$730 million' are one figure (SYNTHETIC)",
            lambda: kinds(sweep(page('<p class="lx-dek">BitMine adds $730 Million in ETH.</p><p class="pc-note">BitMine added $730 million '
                                     'of ETH.</p>'))) == ["twice"])
    fgi = page('<div class="h-mood"><p class="h-g-n">48</p><p class="h-mood-l">Fear &amp; Greed</p></div><div class="related"><ul><li>'
               '<a href="/articles/a">Fear &amp; Greed index reads 48 as traders wait</a></li><li><a href="/articles/b">Circle buys IBM '
               'patents</a></li></ul></div>')
    fgo, _g = fo.withhold(fgi, "articles/x.html")
    guarded(fails, "a quoted story whose only fact is a named reading the page prints (Fear & Greed 48) is withheld; the other stays "
                   "(SYNTHETIC)", lambda: "/articles/a" not in fgo and "/articles/b" in fgo)
    guarded(fails, "the audit sees a hidden figure: a page that lost its only $1.2B is reported (SYNTHETIC)",
            lambda: fo.vanished(page("<p>Kaiko is valued at $1.2B.</p><p>Kaiko raised $110M.</p>"), page("<p>Kaiko raised $110M.</p>"))
                    == ["$1.2B"])
    # each cause on a story page, read on the stored stories that showed it
    by = {i.get("slug"): i for i in sb.load_content()}

    def art(slug):
        with quiet():
            return sb.render_article(by[slug], list(by.values()))
    ab = art("afternoon-brief-2026-09-10")
    guarded(fails, "a story's related and 'More on' picks pass over a story whose headline prints a figure the story prints (the stored "
                   "afternoon Brief of September 10 and the Xinbi seizure story, $52.8 million)",
            lambda: "us-seizes-xinbi-telegram-channels" not in ab.split('class="related"')[-1] and "$52.8 million" in ab)
    xf = art("u-s-freezes-52-8m-in-usdt-tied-to-xinbi-guarantee-scam-marketplace")
    guarded(fails, "an update callout names a later story by its date when that story's headline prints this story's figure (the Xinbi "
                   "freeze of September 9)",
            lambda: re.search(r'superseded by later reporting: <a href="/articles/us-seizes-xinbi[^"]*">the desk’s story of ', xf)
                    is not None)
    mb = art("morning-brief-2026-09-16")
    guarded(fails, "a second citation on an event an earlier citation names is cited by its date (two DOJ stories on one $61 million "
                   "forfeiture, the stored morning Brief of September 16)",
            lambda: mb.count("$61M in Binance Accounts") == 0 and "DOJ Files $61 Million Forfeiture" in mb)
    sq = art("bitcoin-short-squeeze-open-interest-collapses-as-price-rallies-to-78-465")
    guarded(fails, "the board panel's cell says 'In the story' where the story's headline prints its figure ($78,465)",
            lambda: '<span class="bp-v">In the story</span>' in sq and "$78,465" not in sq.split('class="board-panel"')[1].split("</aside>")[0])
    # FAILURE 2. Only a whole quoted unit goes, only when every fact it prints stays printed; a complete index keeps every entry
    items = sb.load_content()
    with quiet():
        rec_raw = sb.render_record(items, "DATELINE")
    rec_out, _g = fo.withhold(rec_raw, "record.html")
    feats = re.findall(r'<div class="bd-card bd-rec-feat">.*?</div></div>', rec_raw, re.S)
    guarded(fails, f"failure 2: /record.html keeps every lane's feature card whole, headline and summary ({len(feats)} cards; the ETFs and "
                   "institutions card among them)",
            lambda: feats and all(f in rec_out for f in feats) and any("ETFs and institutions" in f for f in feats))
    idx = lambda h: re.findall(r'<a href="(/articles/[^"]+)">', (re.search(r'<section class="bd-mod bd-rec-index">(.*?)</section>', h, re.S)
                                                                or re.match("()", "")).group(1))
    guarded(fails, f"failure 2: /record.html's full index keeps every entry ({len(idx(rec_raw))} of {len(idx(rec_raw))})",
            lambda: idx(rec_raw) and idx(rec_out) == idx(rec_raw) and len(idx(rec_raw)) == len(sb.evergreen_picks(items, n=40)))
    xrp = next(i for i in items if i.get("slug") == "bitcoin-etf-inflows-reach-3-52b-in-august-best-month-of-2026")
    with quiet():
        xa = sb.render_article(xrp, items)
    xo, _g = fo.withhold(xa, "articles/bitcoin-etf-inflows-reach-3-52b-in-august-best-month-of-2026.html")
    guarded(fails, "failure 2: the stored dek carrying XRP ETFs' $502 million prints whole on its story page",
            lambda: f'<p class="dek">{sb.esc(xrp["dek"])}</p>' in xo and "$502 million" in xrp["dek"])
    rel_pg = page('<article class="article"><h1>Kaiko Raises $110M</h1><div class="prose"><p>Kaiko raised $110M in a Series B extension.'
                  '</p></div><div class="related"><h2>Related stories</h2><ul><li><a href="/articles/a">Kaiko raises $110M from S&amp;P '
                  'Global at a $1.2B valuation</a></li><li><a href="/articles/b">S&amp;P Global leads $110M extension of Kaiko&#x27;s '
                  'Series B</a></li></ul></div></article>')
    ro, _g = fo.withhold(rel_pg, "articles/x.html")
    guarded(fails, "failure 2: a quoted story that also prints a fact the page prints nowhere else ($1.2B) is not withheld; one whose "
                   "every fact stays printed is (SYNTHETIC)", lambda: "/articles/a" in ro and "/articles/b" not in ro and not fo.vanished(rel_pg, ro))
    # FAILURE 3. A stored unit prints whole as published or is withheld whole
    for slug, cls, key in (("150m-in-long-positions-liquidated-in-24-hours", "bottomline", "bottom_line"),
                           ("ostium-loses-18-million-to-oracle-manipulation-attack-via-priceupkeep-exploit", "callout corrected", "corrected")):
        it = next((i for i in items if i.get("slug") == slug), None)
        if it is None:
            guarded(fails, f"failure 3: the stored story {slug} is in the tree", lambda: False)
            continue
        with quiet():
            ah = sb.render_article(it, items)
        ao, _g = fo.withhold(ah, f"articles/{slug}.html")
        guarded(fails, f"failure 3: {slug}: its {key.replace('_', ' ')} prints whole as stored",
                lambda ao=ao, it=it, key=key: sb.esc(sb.destyle(it[key]) if key == "corrected" else it[key]) in ao)
    import edition
    days = edition.edition_days(items)
    front = page(edition.render_front(edition.DESK, items, "2026-07-14", days))
    fo_, _g = fo.withhold(front, "edition/2026-07-14.html")
    guarded(fails, "failure 3: edition/2026-07-14: every card prints whole as composed or is withheld whole, and nothing withheld hid a fact",
            lambda: _units_whole(front, fo_, r'<article>\s*(?:<span class="ed-kicker">.*?</span>\s*)?(<h3><a href="[^"]+">.*?</h3>).*?</article>')
                    and _units_whole(front, fo_, r'(<section class="ed-brief").*?</section>') and not fo.vanished(front, fo_))
    guarded(fails, "failure 3: the pass never cuts inside an element: its only edits remove a whole element or yield a data figure",
            lambda: not hasattr(fo, "sentences") and "sentences(" not in open(fo.__file__, encoding="utf-8").read())
    # FAILURE 4. No pointer line; the second listing is dropped
    with quiet():
        nh = sb.render_news_hub(items, "DATELINE")
    nho, _g = fo.withhold(nh, "news.html")
    body = nho[nho.find("<main"):nho.find("</main>")]
    links = re.findall(r'href="(/articles/[^"#]+)"', body)
    dup = sorted({u for u in links if links.count(u) > 1})
    guarded(fails, f"failure 4: news.html prints no pointer line and lists each story once ({len(dup)} listed twice: {dup[:3]})",
            lambda: "Another report on an event this page lists" not in nho and not dup)
    # FAILURE 5. One Bitcoin RSI the reader sees at 375 and at 1440, with no control opened
    with fixture_world() as (sbx, pulse, _flows):
        with quiet():
            cmh = sbx.render_chartmaster(getattr(sbx, "_precise_cm", lambda c: c)(load("chartmaster.json")), "DATELINE", pulse)
    dom = fs.parse(cmh)
    # the page as it loads, no control opened: the stylesheets without their ":checked" rules ("Show all columns" left unticked)
    as_loaded = [re.sub(r"[^{}]*:checked[^{}]*\{[^}]*\}", "", c) for c in CSS]
    for w in fs.WIDTHS:
        nodes = fs.printed(dom, fs.Sheet(as_loaded, w))
        btc = [r for r in fs.table_readings(dom, nodes) + fs.figure_readings(dom, nodes) if r[0] == "RSI" and r[1] in ("BTC", None)]
        guarded(fails, f"failure 5: /chartmaster at {w}, as it loads: one Bitcoin RSI the reader sees, in the BTC row the gauge names "
                       f"({[r[2] for r in btc]})",
                lambda btc=btc: len(btc) == 1 and btc[0][1] == "BTC" and "printed in its BTC row below" in cmh)


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
    guarded(fails, "SYNTHETIC: an average just over $0.10 beside a price just under prints at the price's five decimals ($0.10030), "
                   "not its own four", lambda: sb._price_fmt_as(0.1003, 0.0995) == "$0.10030" and sb._price_fmt(0.1003) == "$0.1003")
    with quiet():
        tbl = sb.render_chartmaster({"date": "2026-10-26", "headline": "x", "paragraphs": [], "data_only": True,
                                     "levels": [{"symbol": "ZZZ", "price": 1.02, "sma50": 0.9871, "sma200": 0.9644, "rsi14": 50}]}, "T", None)
    guarded(fails, "SYNTHETIC: a table row whose price is over $1 and whose averages are under prints all three at two decimals",
            lambda: '<td>$1.02</td><td class="xs-x">$0.99</td><td>$0.96</td>' in tbl)
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
                lambda: '<th scope="col" style="white-space:nowrap">RSI-14</th>' in h)
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


# ---- 1e. review 3 under entry 2026-10-27-C9 (J-19 option (1)): reprinted whole units are one printing -----------------------------

def _bl_hist(read, when="August 31, 2026 · 7:59 PM ET", slug="evening-brief-2026-08-31"):
    return (f'<div class="bl-hist"><div class="bl-head"><span class="bl-label">The Evening Brief</span><span class="dateline">{when}</span>'
            f'</div><p class="bl-read">{read}</p><p style="margin:6px 0 0"><a href="/articles/{slug}.html">The full Brief &rarr;</a></p>'
            f'</div>')


def _ed_card(slug, head, dek):
    return f'<article><span class="ed-kicker">The Desk</span><h3><a href="/articles/{slug}.html">{head}</a></h3><p>{dek}</p></article>'


def _ar_card(slug, head, summary):
    return (f'<article class="card reveal"><div class="row"><span class="tag">news</span></div><h3><a href="/articles/{slug}.html">{head}'
            f'</a></h3><p class="summary">{summary}</p><div class="foot"><span class="dateline">September 9, 2026</span></div></article>')


def round4_cases(fails):
    import fact_sweep as fs
    print("1e. review 3 under entry 2026-10-27-C9: a page that reprints whole published units is one printing of each figure they carry, "
          "for three named reasons; every other pair is still a finding")
    # REASON A: a Brief month archive's dated reads (bottom-line/<yyyy-mm>). SYNTHETIC pages in the archive's own markup.
    reads = ('<h2 class="bl-mh">August 2026</h2>'
             + _bl_hist("Spot bitcoin ETFs took in $150 million on Monday, the desk's figures show.")
             + _bl_hist("On Monday spot bitcoin ETFs drew $150 million as the week opened.", "August 30, 2026 · 1:04 PM ET",
                        "morning-brief-2026-08-30"))
    guarded(fails, "reason A: two dated Brief reads on a month archive quoting one figure are one printing under C9: no finding "
                   "(SYNTHETIC, bottom-line/2026-08)", lambda: sweep(page(reads), "bottom-line/2026-08.html") == [])
    fg = ('<h2 class="bl-mh">July 2026</h2>'
          + _bl_hist("Bitcoin held at $64,603.64 with Fear & Greed at 26 as the week closed.")
          + _bl_hist("The desk's Market Pulse shows Fear & Greed at 26 and bitcoin roughly flat.", "July 30, 2026 · 7:40 PM ET",
                     "evening-brief-2026-07-30"))
    guarded(fails, "reason A: one named reading (Fear & Greed) in two dated reads on a month archive is one printing under C9: no finding "
                   "(SYNTHETIC, bottom-line/2026-07)", lambda: sweep(page(fg), "bottom-line/2026-07.html") == [])
    guarded(fails, "reason A is named narrowly: the same two reads on the current Brief page (bottom-line.html, not a month archive) are "
                   "a finding (SYNTHETIC)", lambda: kinds(sweep(page(reads), "bottom-line.html")) == ["twice"])
    guarded(fails, "reason A is named narrowly: a dated read beside a line the build writes on a month archive is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page('<p class="pc-note">Spot bitcoin ETFs drew $150 million on Monday.</p>'
                                     + _bl_hist("Spot bitcoin ETFs took in $150 million on Monday, the desk's figures show.")),
                                "bottom-line/2026-08.html")) == ["twice"])
    # REASON B: an Edition page's Brief beside its day's story cards (the rail and the down-page). SYNTHETIC, the Edition's markup.
    brief = ('<section class="ed-brief" aria-label="The Evening Brief"><div class="ed-brief-head"><span class="ed-kicker">The Evening Brief'
             '</span></div><div class="ed-brief-cols"><p>Strategy sold 1,690 bitcoin for $108.6 million and raised $653.1 million from '
             'MSTR shares.</p></div></section>')
    rail = ('<div class="ed-front"><aside class="ed-rail" aria-label="Top stories">'
            + _ed_card("strategy-sells", "Strategy Sells 1,690 Bitcoin, Raises $653 Million From MSTR Shares",
                       "Strategy sold 1,690 bitcoin for $108.6 million and raised $653.1 million through common stock sales.")
            + '</aside></div>')
    down = ('<section class="ed-downpage" aria-label="More from the desk">'
            + _ed_card("strategy-sells", "Strategy Sells 1,690 Bitcoin, Raises $653 Million From MSTR Shares",
                       "Strategy sold 1,690 bitcoin for $108.6 million and raised $653.1 million through common stock sales.")
            + '</section>')
    guarded(fails, "reason B: an Edition page's Brief beside its day's rail card printing one figure is one printing under C9: no finding "
                   "(SYNTHETIC, edition/2026-08-10)", lambda: sweep(page(rail + brief), "edition/2026-08-10.html") == [])
    guarded(fails, "reason B: an Edition page's Brief beside its day's down-page card printing one figure is one printing under C9: no "
                   "finding (SYNTHETIC, edition/2026-08-10)", lambda: sweep(page(brief + down), "edition/2026-08-10.html") == [])
    guarded(fails, "reason B is named narrowly: the same Brief beside the same card on a page that is not a dated Edition is a finding "
                   "(SYNTHETIC, index.html)", lambda: "twice" in kinds(sweep(page(rail + brief), "index.html")))
    guarded(fails, "reason B is named narrowly: two Briefs quoting one figure on an Edition page are a finding (SYNTHETIC)",
            lambda: kinds(sweep(page(brief + brief.replace("Strategy sold", "Strategy, the treasury company, sold")),
                                "edition/2026-08-10.html")) == ["twice", "twice"])
    guarded(fails, "reason B is named narrowly: an Edition page's Brief beside a line the build writes is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page(brief + '<p class="pc-note">Strategy sold 1,690 bitcoin for $108.6 million.</p>'),
                                "edition/2026-08-10.html")) == ["twice"])
    guarded(fails, "reason B is named narrowly: two of the day's cards on one event on an Edition page are a finding (SYNTHETIC)",
            lambda: kinds(sweep(page('<aside class="ed-rail">'
                                     + _ed_card("us-seizes-xinbi", "US seizes Xinbi Telegram channels, restrains $52.8M in USDT",
                                                "Federal prosecutors moved against the Xinbi marketplace.")
                                     + _ed_card("us-freezes-xinbi", "U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee Scam Marketplace",
                                                "The Justice Department filed to forfeit the funds.") + '</aside>'),
                                "edition/2026-09-10.html")) == ["twice"])
    # REASON C: a complete index's entries, two stories on one event and an archive summary with facts of its own. SYNTHETIC.
    xinbi = ('<div class="grid">'
             + _ar_card("us-seizes-xinbi", "US seizes Xinbi Telegram channels, restrains $52.8M in USDT tied to $24B black market",
                        "Federal prosecutors moved against the Xinbi marketplace.")
             + _ar_card("us-freezes-xinbi", "U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee Scam Marketplace",
                        "The Justice Department filed to forfeit the funds.") + '</div>')
    guarded(fails, "reason C: two stories the desk published on one event, both entries of the archive, are one printing under C9: no "
                   "finding (SYNTHETIC, archive.html)", lambda: sweep(page(xinbi), "archive.html") == [])
    rows = ('<div class="nh-rows"><div class="nh-row"><a class="nh-t" href="/articles/orionx-halts.html">Chilean exchange Orionx halts '
            'withdrawals after forensic audit finds $7M in asset transfers</a><span class="nh-m"><span class="bd-stamp">September 8, 2026'
            '</span></span></div><div class="nh-row"><a class="nh-t" href="/articles/orionx-shuts.html">Tether-Backed Orionx Shuts Down '
            'After Audit Finds $7M Custody Gap</a><span class="nh-m"><span class="bd-stamp">September 9, 2026</span></span></div></div>')
    guarded(fails, "reason C: two stories on one event, both rows of a storyline's complete list, are one printing under C9: no finding "
                   "(SYNTHETIC, news/exchanges-and-security/page/2)",
            lambda: sweep(page(rows), "news/exchanges-and-security/page/2.html") == [])
    jgb = ('<div class="grid">'
           + _ar_card("stablecoin-consortium", "Banks Target 2027 for a Dollar Stablecoin",
                      "A consortium of 21 global banks is targeting an H1 2027 launch for a dollar stablecoin, while Japan's 10-year "
                      "government bond yield reached 3% on September 1, a 30-year high.")
           + _ar_card("japan-yield", "Japan's Bond Yield Reaches a 30-Year High",
                      "Japan's 10-year government bond yield reached 3% on September 1, 2026, a 30-year high.") + '</div>')
    guarded(fails, "reason C: an archive summary with facts of its own beside another entry printing one of them is one printing under "
                   "C9: no finding (SYNTHETIC, archive.html)", lambda: sweep(page(jgb), "archive.html") == [])
    guarded(fails, "reason C is named narrowly: the same two entries on the news front (news.html, not a complete index) are a finding "
                   "(SYNTHETIC)", lambda: kinds(sweep(page(xinbi), "news.html")) == ["twice"])
    guarded(fails, "reason C is named narrowly: an archive entry beside a line the build writes on the archive is a finding (SYNTHETIC)",
            lambda: kinds(sweep(page('<p class="pc-note">U.S. prosecutors restrained $52.8M in USDT tied to Xinbi.</p>'
                                     + xinbi.replace(_ar_card("us-freezes-xinbi", "U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee "
                                                              "Scam Marketplace", "The Justice Department filed to forfeit the funds."),
                                                     "")), "archive.html")) == ["twice"])
    # the three are named in the sweep, so the canary's tally prints each by its name on every run
    guarded(fails, "one_printing names C9's three reasons",
            lambda: all(s in open(fs.__file__, encoding="utf-8").read() for s in (
                "a Brief month archive's dated reads", "an Edition page's Brief beside its day's story cards",
                "a complete index's entries")))


def unit(only=()):
    fails = []
    for name, fn in (("model", model_cases), ("round2", round2_cases), ("round2b", round2_build_cases), ("round3", round3_cases), ("round4", round4_cases), ("coin", coin_cases), ("precision", precision_cases), ("today", today_home_cases),
                     ("markets", markets_cases), ("evidence", evidence_cases), ("k1", k1_cases), ("article", article_cases)):
        if only and name not in only:
            continue
        group(fails, name, fn)
    return fails


def tree(root):
    import fact_sweep as fs
    fails = []
    print("11. the tree this build wrote: every page in it, at 375 and 1440, prints each fact once")
    fs.ONE.clear()
    with quiet():
        res = fs.sweep(root, history_dir=os.path.join(HERE, "data", "history"))
    bad = [(rel, k, t) for rel, v in res.items() for k, _w, t in v]
    n = len(bad)
    pages = sum(1 for dp, _d, f in os.walk(root) for x in f if x.endswith(".html"))
    print(f"  INFO {pages} page(s) swept")
    guarded(fails, f"the built tree has pages to sweep ({pages})", lambda: pages >= 50)
    for rel, k, t in bad:
        print(f"  FAIL {t[:230]}")
    # no HELD (entry 2026-10-27-C8): a pair is a finding, or one printing for a reason the ruling names, tallied here on every run
    print("  INFO one printing under entries 2026-10-27-C8 and C9: " + ("; ".join(f"{why}: {k}" for why, k in sorted(fs.ONE.items())) or "none"))
    guarded(fails, f"the sweep finds no figure printed twice and no derived figure off its row's precision ({n} finding(s))",
            lambda: n == 0)
    # the build's own pass, in this process (the canary's build): nothing it withheld was the only printing of a figure on its page
    import site_build as _sbm
    hidden = [x for x in getattr(_sbm, "_FACT_ONCE", []) if x[0] == "hidden"]
    for _k, rel, t in hidden[:20]:
        print(f"  FAIL the pass hid {t!r} on {rel}: printed nowhere else on the page")
    guarded(fails, f"the build's pass hid no figure: every unit it withheld quotes facts the page still prints ({len(hidden)} hidden)",
            lambda: not hidden)
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
