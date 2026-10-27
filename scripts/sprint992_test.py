#!/usr/bin/env python3
"""Sprint 9.9.2 (October 27, 2026): one fact once. Each case is named after what it guards.

  python3 scripts/sprint992_test.py                          # unit cases; exit 1 on any failure
  python3 scripts/sprint992_test.py --tree <dir> [--data <dir>]  # also the whole-site sweep of a built tree
  python3 scripts/sprint992_test.py --sweep <dir> [--data <dir>] # the sweep alone, every finding printed by page
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote, with the data it read)

The definition of done (docs/BOARD.md, 9.9.2): a canary check that fails on any figure printed twice on any page and on
any derived figure whose precision differs from its row, seen red on today's production copy first; the sweep's count of
fixes in the report. The sweep is one_fact.py: every page in the sitemaps, not a sample.

The HTML in the checker cases below is SYNTHETIC, written for the case and labeled so; the tree cases read a real build.
NO MODEL CALL and no network anywhere.
"""
import contextlib
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
UTC = dt.timezone.utc
EM = re.compile("[\u2013\u2014]")


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


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def visible(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h or "", flags=re.S | re.I)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def page(body):
    """A SYNTHETIC page around a body."""
    return f"<!doctype html><html><head><title>t</title></head><body><main>{body}</main></body></html>"


def kinds(h):
    import one_fact
    return [k for k, _t in one_fact.page_findings(page(h))]


# ---- 1. the checker: what is a twin and what is not ---------------------------------------------------------------------

def checker_cases(fails):
    print("1. the checker (SYNTHETIC pages): a figure printed twice is red; two facts that share a number are not")
    import one_fact
    guarded(fails, "a tile and a sentence printing one figure are a twin",
            lambda: kinds('<p>ETFs took in $110.3M on the day.</p><article class="tl"><h3>ETF flows</h3>'
                          '<p class="tl-f">+$110.3M</p></article>') == ["twin"])
    guarded(fails, "'$110.3 million' in words and '$110.3M' on a tile are one figure",
            lambda: kinds('<p>ETFs took in $110.3 million.</p><p>ETF flows +$110.3M</p>') == ["twin"])
    guarded(fails, "a percentage in the answer and in its own table row is a twin (the row's subject named in the sentence)",
            lambda: kinds('<p>Ether was down 0.64% over the same 24 hours.</p><ul><li>Ether <span>$2,313</span> '
                          '<span>0.64%</span></li></ul>') == ["twin"])
    guarded(fails, "two coins in one table that fell the same amount are two facts",
            lambda: kinds('<table><tr><td>SOL</td><td>-0.6%</td></tr><tr><td>XRP</td><td>-0.6%</td></tr></table>') == [])
    guarded(fails, "two columns of one table row with the same reading are two readings (Kalshi 7.5% at 11 AM, 7.5% at noon)",
            lambda: kinds('<table><tr><td>Kalshi</td><td>7.5%</td><td>7.5%</td></tr></table>') == [])
    guarded(fails, "a row's figure beside a sentence about another subject is not a twin (the subject floor)",
            lambda: kinds('<p>In the next 60 minutes Bitcoin fell 1.00%.</p><ul><li>Ether <span>1.00%</span></li></ul>') == [])
    guarded(fails, "a figure a stored read repeats inside itself is the read's (J-10), not a twin",
            lambda: kinds('<div data-read><h1>Conduit sues over $2.76 million</h1><p>The $2.76 million was frozen.</p></div>') == [])
    guarded(fails, "a stored read and the page's own tile printing one figure are a twin",
            lambda: kinds('<div data-read><p>The index reads 48, and ETFs took in $5.1 million.</p></div>'
                          '<p class="tl-f">+$5.1M</p>') == ["twin"])
    guarded(fails, "two records of a declared list (data-records) are two facts",
            lambda: kinds('<div data-records><div><p>Whales moved $1.5 billion.</p></div><div><p>Inflows hit $1.5 billion.</p></div></div>') == [])
    guarded(fails, "a price and a 7-day high close that are both $1.00 are two facts (named as different quantities)",
            lambda: kinds('<p>Seven days. 7D high close $1.00, 7D low close $0.9998.</p><article><h3>Price</h3><p>$1.00</p></article>') == [])
    guarded(fails, "the Ether line shown only from 1280 and the Ether tile shown only under 1280 print once at each width",
            lambda: kinds('<p data-wide>Ether $2,312.84</p><ul><li data-narrow>Ether $2,312.84</li></ul>') == [])
    guarded(fails, "...and the same pair with neither marked is a twin at every width",
            lambda: kinds('<p>Ether $2,312.84</p><ul><li>Ether $2,312.84</li></ul>') == ["twin"])
    guarded(fails, "text in a hidden element or a screen-reader span is not printed",
            lambda: kinds('<p>$110.3M</p><p hidden>$110.3M</p><span class="sr-only">$110.3M</span>') == [])
    guarded(fails, "ONE 200-DAY VALUE PER PAGE: two different 200-day values are red",
            lambda: kinds('<p>200-day line $73,024.55</p><div><span>200-day average</span><span>$72,988.58</span></div>') == ["twin"])
    guarded(fails, "ONE RSI PER PAGE: a tile's RSI and a levels block's RSI are red, whatever the values",
            lambda: kinds('<article><h3>RSI (14)</h3><p>41</p></article><div><span>RSI (14)</span><span>40</span></div>') == ["twin"])
    guarded(fails, "ONE FEAR AND GREED PER PAGE: a sentence's reading and the gauge's are red",
            lambda: kinds('<p>The Fear &amp; Greed index reads 48, neutral.</p><div><div><p>48</p></div>'
                          '<div><p>Fear &amp; Greed</p><p>Neutral</p></div></div>') == ["twin"])
    guarded(fails, "PRECISION: a row printing a price at four decimals and an average at two is red",
            lambda: kinds('<table><tr><th>DOGE</th><td>$0.0771</td><td>$0.09</td></tr></table>') == ["precision"])
    guarded(fails, "...and a row at one precision is not",
            lambda: kinds('<table><tr><th>DOGE</th><td>$0.0771</td><td>$0.0867</td></tr></table>') == [])
    guarded(fails, "...a marked row (data-row) is read like a table row",
            lambda: kinds('<div data-row><p>Price $79,839.00</p><p>200-day line $73,024</p></div>') == ["precision"])
    guarded(fails, "one figure printed at two precisions is one figure (0.8% and 0.80%; $82,119 and $82,119.00)",
            lambda: kinds('<p>Bitcoin at $82,119, up 0.8% on the day.</p><p>Bitcoin $82,119.00 up 0.80%</p>') == ["twin", "twin"])
    guarded(fails, "a printed correction (data-quote) quoting the figure it reconciles is not counted",
            lambda: kinds('<p>Bitcoin was up 0.80%.</p><p data-quote>Correction: the market figure contradicted Bitcoin '
                          '(up 0.80%).</p>') == [])
    guarded(fails, "-0.01% and +0.01% are two values, not one figure twice",
            lambda: kinds('<article><h3>7 days</h3><p>-0.01%</p></article><p>30 days: Up 0.01%</p>') == [])
    guarded(fails, "a 24-hour change and a 7-day change that are both 0.65% are two facts (each named with its window)",
            lambda: kinds('<p>24 hours: Up 0.65%</p><article><h3>7 days</h3><p>+0.65%</p></article>') == [])
    guarded(fails, "a move in a list marked as the onset hour (data-window) is not the 24-hour move with the same figure",
            lambda: kinds('<p>Ether was up 0.60% over the same 24 hours.</p><ul data-window="hour"><li>Ether +0.60%</li></ul>') == [])
    guarded(fails, "two rows of one list that read alike are two records (two transfers, each 'BTC $51.8M to Coinbase')",
            lambda: kinds('<ul><li>BTC $51.8M to Coinbase, 166h ago</li><li>BTC $51.8M to Coinbase, 98h ago</li></ul>') == [])
    guarded(fails, "a figure printed with opposite directions is two values (funding -0.0100% and +0.0100%)",
            lambda: kinds('<p>Funding on OKX -0.0100% per 8 hours</p><p>Funding on Bybit +0.0100% per 8 hours</p>') == [])
    guarded(fails, "THE NEXT SLOT ONCE: the notice's 'Next read' and the Brief card's 'Next Brief' at one time are red",
            lambda: kinds('<p>Verdict at the next read: no read yet today. Next read: tonight at 7:08 PM ET.</p>'
                          '<p>Next Brief tonight at 7:08 PM ET</p>') == ["twin"])
    guarded(fails, "a zero is not counted ($0 and 0.00% are printed by many unrelated rows)",
            lambda: kinds('<p>$0 shorts</p><p>0.00%</p><p>$0 longs</p><p>0.00%</p>') == [])
    # the data-aware rule: a stored average printed with more decimals than it carries
    tmp = tempfile.mkdtemp(prefix="s992-prec-")
    try:
        os.makedirs(os.path.join(tmp, "data"))
        os.makedirs(os.path.join(tmp, "site", "coins"))
        json.dump({"assets": [{"symbol": "DOGE", "price": 0.0771, "sma50": 0.09, "sma200": 0.086658}]},
                  open(os.path.join(tmp, "data", "pulse.json"), "w"))
        open(os.path.join(tmp, "site", "coins", "doge.html"), "w").write(
            page('<div data-row><p>Price $0.07711</p><p>50-day average $0.09000</p><p>200-day line $0.08666</p></div>'))
        r = one_fact.precision_findings(os.path.join(tmp, "site"), os.path.join(tmp, "data"))
        guarded(fails, "PRECISION, STORED: an average stored as 0.09 and printed $0.09000 is red (a rounding printed as the figure)",
                lambda: list(r) == ["/coins/doge"] and len(r["/coins/doge"]) == 1 and "sma50" in r["/coins/doge"][0][1])
        guarded(fails, "...and one stored at six decimals and printed at five is not",
                lambda: not any("sma200" in t for _k, t in r.get("/coins/doge", [])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # the sweep reads every page the sitemaps list, and names a listed page the tree lacks
    tmp = tempfile.mkdtemp(prefix="s992-sweep-")
    try:
        locs = "".join(f"<url><loc>https://gocheckmycrypto.com{u}</loc></url>" for u in ("/", "/a", "/b/", "/gone"))
        open(os.path.join(tmp, "sitemap-priority.xml"), "w").write(f"<urlset>{locs}</urlset>")
        open(os.path.join(tmp, "index.html"), "w").write(page("<p>$1.63B</p><p>-$1.63B</p>"))
        open(os.path.join(tmp, "a.html"), "w").write(page("<p>$1.63B</p>"))
        os.makedirs(os.path.join(tmp, "b"))
        open(os.path.join(tmp, "b", "index.html"), "w").write(page("<p>5.2%</p><p>5.2%</p>"))
        res, n = one_fact.sweep(tmp)
        guarded(fails, "the sweep reads every sitemap page (4 listed), finds the twin on / and on /b/, and names /gone missing",
                lambda: n == 4 and sorted(res) == ["/", "/b/", "/gone"] and res["/gone"][0][0] == "missing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- 2. the home: Ether once at each width, the morning card's figures once, the next slot once ------------------------

def s991():
    import sprint991_test
    return sprint991_test


def home_cases(fails):
    print("2. the home (the real October 26 morning records, scripts/sprint991_test.py's fixture): every figure once")
    import one_fact
    t = s991()
    with quiet():
        with t.Draw() as d:
            h = d.home()
            morning = getattr(d, "morning", None)
        with t.Draw(t.NOW_NEXT_DAY) as d:
            early = d.home()
    f = one_fact.page_findings(page(h))
    guarded(fails, "Ether's price prints once at each width (the list's Ether item is the narrow one, the tape's line the wide one)",
            lambda: not [x for k, x in f if "2,328.20" in x or "0.17%" in x])
    guarded(fails, "...the list's Ether item says it is the narrow one (data-narrow), the line that the stylesheet hides from 1280",
            lambda: re.search(r'<li class="h-coin [a-z]+" data-tile="ethereum" data-narrow>', h))
    guarded(fails, "the morning card prints no figure the home prints elsewhere (no twin on the fixture home)", lambda: not f)
    wl = re.findall(r'<li class="h-wi">(.*?)</li>', h, flags=re.S)
    guarded(fails, "the wire keeps the checked item in its re-count place, and its line points at the top story above "
                   "instead of printing it a second time",
            lambda: len(wl) == 5 and sum("The top story, checked, above." in x for x in wl) == 1
            and all('class="badge verified"' in x for x in wl if "The top story, checked, above." in x))
    fe = one_fact.page_findings(page(early))
    guarded(fails, "the next slot's time prints once on the home when the verdict notice names it (no read yet today)",
            lambda: not [x for k, x in fe if "next slot" in x] and visible(early).count("8:15 AM ET") == 1)
    guarded(fails, "...and it is the notice that prints it (the ruled line keeps its time)",
            lambda: "Next read: this morning at 8:15 AM ET." in visible(early) and "Next Brief" not in visible(early))
    guarded(fails, "...a home with no notice keeps the Brief card's next line",
            lambda: "Next Brief tonight at 7:08 PM ET" in visible(home_without_notice()))
    # the morning card's sentences: withheld whole when they carry a figure printed elsewhere, never reworded (J-10)
    import home
    import json as _j
    stored = _j.load(open(os.path.join(HERE, "fixtures", "sprint992", "morning-2026-10-27.json"), encoding="utf-8"))
    printed = ('<article class="tl"><h3>ETF flows</h3><p class="tl-f">+$110.3M</p></article>'
               '<div><div><p>48</p></div><div><p>Fear &amp; Greed</p></div></div>')
    kept = home.morning_sentences(stored["sentences"], printed)
    guarded(fails, "the stored morning sentence carrying the ETF figure and the Fear and Greed reading is withheld on a home printing both",
            lambda: not any("$110.3M" in x for x in kept) and len(kept) == len(stored["sentences"]) - 1)
    guarded(fails, "...and every sentence kept is printed exactly as stored (nothing reworded, J-10)",
            lambda: all(x in stored["sentences"] for x in kept))
    guarded(fails, "...a home that prints neither keeps every sentence",
            lambda: home.morning_sentences(stored["sentences"], "<p>Solana $99.96</p>") == stored["sentences"])


def home_without_notice():
    t = s991()
    import verdict
    with quiet():
        with t.Draw(t.NOW_MORNING) as d:
            v = dict(d.v, coins={"BTC": {"kind": "flat"}})
            return d.home(verdict=v)


# ---- 3. the coin pages: one 24-hour change, one 7-day change, one volume, one 200-day value, one RSI ---------------------

CM_READ_UTC = "2026-10-26T23:14:51Z"     # data/chartmaster-ledger.json: the October 26 card's run, 7:14 PM ET


FX = os.path.join(HERE, "fixtures", "sprint992")
NOW_27 = dt.datetime(2026, 10, 27, 12, 40, tzinfo=UTC)   # the build after the October 27 morning read (main's tree: 12:40Z)


def fx(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


@contextlib.contextmanager
def board27():
    """The build globals set to the real October 27 morning Board (main's site/data/pulse.json and flows.json at 82e8c43,
    byte for byte in fixtures/sprint992), and put back."""
    import site_build as sb
    import snapshot
    p, fl = fx("pulse-2026-10-27-morning.json"), fx("flows-2026-10-27-morning.json")
    old = (sb.SNAP, sb._NOW_CACHE)
    sb.SNAP, sb._NOW_CACHE = snapshot.build(p, fl), NOW_27
    try:
        yield p, fl
    finally:
        sb.SNAP, sb._NOW_CACHE = old


def coin_page(sym="BTC", cm="real"):
    """A coin page from the real October 27 morning Board with the stored October 26 Chart Master card
    (fixtures/sprint992/chartmaster-2026-10-26.json, main's site/data/chartmaster.json) read at its ledger time: the pair
    production printed on October 27."""
    import site_build as sb
    card = dict(fx("chartmaster-2026-10-26.json"), read_utc=CM_READ_UTC)
    with quiet():
        with board27() as (p, _fl):
            pos, c = next((i + 1, x) for i, x in enumerate(p["movers"]["top100"]) if x["symbol"] == sym)
            return sb.render_coin_page(c, pos, p, [], "DATELINE", wire={"items": []}, cm=(card if cm == "real" else cm),
                                       read_clock=NOW_27, today=dt.date(2026, 10, 27))


def coin_cases(fails):
    print("3. the coin pages (the real October 27 Board, the October 26 card): every reading once, the Chart Master's levels dated with their age")
    import one_fact
    h = coin_page("BTC")
    f = one_fact.page_findings(h)
    for k, x in f:
        print("     finding: " + x[:200])
    guarded(fails, "/coins/btc prints no figure twice (24 hours, 7 days, volume, 200-day, RSI) on the real records", lambda: not f)
    v = visible(h)
    guarded(fails, "the 24-hour change prints once, on the Price tile's since line (no separate 24-hour tile)",
            lambda: 'data-reading="coin-24h"' not in h and re.search(r'data-reading="coin-price".*?24 hours: ', h, flags=re.S))
    head = re.search(r'<p class="cc-chg"[^>]*>(.*?)</p>', h)
    guarded(fails, "the chart's header names its 7-day window without printing the Readings tile's figure a second time",
            lambda: head and head.group(1) == "Over the last 7 days" and 'data-chg7="' in h)
    guarded(fails, "the volume prints once (the tile), not again under Supply and trade",
            lambda: v.count("24-hour volume") == 1)
    guarded(fails, "'from the last build' is retired from the chart's caption", lambda: "from the last build" not in h)
    guarded(fails, "...the caption carries its own read's date in the house wording",
            lambda: re.search(r'<span class="cn-stamp">Read Oct 27, 8:17 AM ET</span>', h))
    cmb = re.search(r'<section class="cn-cm".*?</section>', h, flags=re.S)
    cmt = visible(cmb.group(0)) if cmb else ""
    guarded(fails, "the Chart Master's levels block carries its read's date and time in the house wording",
            lambda: cmt.startswith("Chart levels for Bitcoin, read Oct 26, 7:14 PM ET"))
    guarded(fails, "...and its age against the readings above it ('This is 13 hours old; the readings above are newer.')",
            lambda: "This is 13 hours old; the readings above are newer." in cmt)
    guarded(fails, "...and prints only the level the page does not already print: the 50-day average, no second price, "
                   "200-day value or RSI", lambda: "50-day average $81,800.06" in cmt and "200-day" not in cmt
            and "RSI" not in cmt and "Price" not in cmt)
    guarded(fails, "one 200-day value on /coins/btc: the Readings tile's", lambda: len(re.findall(r"200-day (?:line|average) \$", v)) == 1)


# ---- 4. precision: every average and derived figure at its asset's price precision --------------------------------------

def precision_cases(fails):
    print("4. precision: the averages stored at the price's precision, printed at it, and a rounding never padded")
    import market_pulse
    import site_build as sb
    import one_fact
    # SYNTHETIC closes: 250 days of a coin near eight cents
    closes = [0.0803 + 0.01 * ((i * 37) % 11) / 11 for i in range(250)]
    dates = [(dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(250)]
    a = market_pulse.asset_from_closes("dogecoin", "DOGE", dates, closes)
    guarded(fails, "market_pulse stores a sub-dollar coin's 50-day and 200-day averages past the cent (SYNTHETIC closes)",
            lambda: one_fact._decimals(a["sma50"]) > 2 and one_fact._decimals(a["sma200"]) > 2)
    guarded(fails, "...and its 90-day high and low past the cent", lambda: one_fact._decimals(a["spark_high"]) > 2
            and one_fact._decimals(a["spark_low"]) > 2)
    big = market_pulse.asset_from_closes("bitcoin", "BTC", dates, [80000 + i * 3.3 for i in range(250)])
    guarded(fails, "...a coin over $100 keeps cents", lambda: one_fact._decimals(big["sma200"]) <= 2)
    p = fx("pulse-2026-10-27-morning.json")
    doge = next(x for x in p["assets"] if x["symbol"] == "DOGE")
    guarded(fails, "the stored 0.09 (October 27) is read at its full value from the same record's averaged series: 0.086658",
            lambda: sb.level(doge, "sma200") == 0.086658 and sb.level(doge, "sma50") == 0.086739)
    guarded(fails, "...a stored average with no series to prove it is left out, never padded",
            lambda: sb.level({"price": 0.077024, "sma50": 0.09}, "sma50") is None)
    guarded(fails, "...an average over a dollar is taken as stored", lambda: sb.level({"price": 79839, "sma200": 73024.55}, "sma200") == 73024.55)
    h = coin_page("DOGE")
    v = visible(h)
    guarded(fails, "/coins/doge prints its 200-day line at the price's precision ($0.08666 beside $0.07711), not $0.09000",
            lambda: "200-day line $0.08666" in v and "$0.09000" not in v)
    guarded(fails, "...and the distance from it is measured from that value (-11.0%), not from the rounding (-14.3%)",
            lambda: "-11.0%" in v and "-14.3%" not in v)
    cmb = re.search(r'<section class="cn-cm".*?</section>', h, flags=re.S)
    guarded(fails, "...the stored October 26 card's 50-day average, kept only to the cent, is left out and the card says so",
            lambda: cmb and "rounded to the cent, coarser than its price, so it is not shown" in visible(cmb.group(0))
            and "$0.09" not in visible(cmb.group(0)))
    tmp = tempfile.mkdtemp(prefix="s992-p-")
    try:
        os.makedirs(os.path.join(tmp, "site", "coins"))
        os.makedirs(os.path.join(tmp, "data"))
        open(os.path.join(tmp, "site", "coins", "doge.html"), "w").write(h)
        shutil.copy(os.path.join(FX, "pulse-2026-10-27-morning.json"), os.path.join(tmp, "data", "pulse.json"))
        shutil.copy(os.path.join(FX, "chartmaster-2026-10-26.json"), os.path.join(tmp, "data", "chartmaster.json"))
        r = one_fact.precision_findings(os.path.join(tmp, "site"), os.path.join(tmp, "data"))
        guarded(fails, "...the stored-precision rule finds no rounding printed as a figure on /coins/doge", lambda: not r)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    guarded(fails, "/coins/doge prints no figure twice", lambda: not one_fact.page_findings(h))
    # the Chart Master's table: the stored October 26 card, DOGE and ADA rounded to the cent
    cm = chartmaster_page()
    rows = {m.group(1): visible(m.group(0)) for m in re.finditer(r'<tr><th scope="row">([A-Z]+)</th>.*?</tr>', cm, flags=re.S)}
    guarded(fails, "the Chart Master's table prints no DOGE or ADA average as a padded rounding ($0.0900, $0.2300, $0.2100)",
            lambda: rows and not re.search(r"\$0\.(0900|2300|2100)\b", rows.get("DOGE", "") + rows.get("ADA", "")))
    guarded(fails, "...says why those cells are empty", lambda: "rounded to the cent" in visible(cm))
    guarded(fails, "...and every row prints its figures at one precision (no precision finding on the page)",
            lambda: not [x for k, x in one_fact.page_findings(cm) if k == "precision"])
    guarded(fails, "the Chart Master's dated card says its read's time and its age (the data card too)",
            lambda: "The chart read, Oct 26, 7:14 PM ET" in visible(cm)
            and "This is 13 hours old; the readings above are newer." in visible(cm))
    new = sb._cm_n
    guarded(fails, "...a card stored in full prints DOGE's averages at four decimals like its price ($0.0867 beside $0.0770)",
            lambda: new(0.086658) == "0.0867" and new(0.077024) == "0.0770")
    # the home's derived Bitcoin figures at the tape's precision
    with quiet():
        with board27() as (p27, fl27):
            import home
            hb = home.since(p27, sb.board_deltas(p27), home.bitcoin_card(sb.SNAP))
    guarded(fails, "the home's 24-hour high and low and 7-day closes print at Bitcoin's price precision (cents, as the tape)",
            lambda: re.search(r"24h high <b>\$[\d,]+\.\d\d</b>", hb) and re.search(r"7D HIGH CLOSE <b>\$[\d,]+\.\d\d</b>", hb))


def chartmaster_page():
    """/chartmaster.html with the stored October 26 card and the real October 27 Board."""
    import site_build as sb
    card = dict(fx("chartmaster-2026-10-26.json"), read_utc=CM_READ_UTC)
    with quiet():
        with board27() as (p, fl):
            return sb.render_chartmaster(card, "DATELINE", p)


# ---- 5. /today/: the answer as published, and the lists under it never print its figures again ---------------------------

def today_pages():
    """[(name, html)]: every stored /today/ record the fixtures hold, drawn as its dated page: the real October 15, 16, 25
    and 26 records (fixtures/sprint991, byte for byte as main held them) and the October 27 morning record
    (fixtures/sprint992, main's site/data at 82e8c43), each with its evidence and verdict where stored."""
    import today
    out = []
    s91 = os.path.join(HERE, "fixtures", "sprint991")
    for d in sorted(os.listdir(s91)):
        f = os.path.join(s91, d)
        files = os.listdir(f)
        pick = lambda pre: next((json.load(open(os.path.join(f, x), encoding="utf-8")) for x in files
                                 if x.startswith(pre)), None)
        rec = pick("today")
        if rec:
            with quiet():
                out.append((d, today.body_html(rec, [], "dated", evidence=pick("why"), verdict=pick("verdict"))))
    with quiet():
        out.append(("real-2026-10-27-morning", today.body_html(fx("today_2026-10-27-morning.json"), [], "dated",
                                                                 evidence=fx("why_2026-10-27-morning.json"),
                                                                 verdict=fx("verdict_2026-10-27-morning.json"))))
    return out


def today_cases(fails):
    print("5. /today/ (every stored record the fixtures hold): the answer prints as published, the lists yield its figures")
    import one_fact
    import today
    pages = today_pages()
    guarded(fails, f"the fixtures hold the five stored records ({len(pages)})", lambda: len(pages) == 5)
    for name, h in pages:
        f = one_fact.page_findings(page(h))
        for k, x in f:
            print("     finding: " + x[:200])
        guarded(fails, f"{name}: no figure printed twice", lambda f=f: not f)
    r20 = fx("today_2026-10-20-evening.json")
    with quiet():
        h20 = today.body_html(r20, [], "dated", evidence=fx("why_2026-10-20-evening.json"),
                              verdict=fx("verdict_2026-10-20-evening.json"))
    f20 = one_fact.page_findings(page(h20))
    guarded(fails, "October 20 (the Edition lifted as the answer names France's 31% tax, which the evidence lists): no twin",
            lambda: not f20)
    a20 = visible((re.search(r'<section class="td-answer".*?</section>', h20, flags=re.S) or re.match("", "")).group(0))
    guarded(fails, "...the answer's sentence carrying it is withheld whole, every other sentence printed exactly as stored",
            lambda: "31%" not in a20 and a20 and all((x in a20) == ("31%" not in x) for x in r20["answer"]))
    guarded(fails, "...and the evidence list prints the item whole", lambda: "31% capital-gains tax" in visible(h20))
    with quiet():
        h20b = today.body_html(r20, [], "dated", evidence=None, verdict=fx("verdict_2026-10-20-evening.json"))
    # /flows on the real October 27 flows: the 13-week list's newest week is the 7-day net the sentence states
    import site_build as sb
    with quiet():
        with board27() as (_p, fl27):
            hf = sb.render_flows(fl27, "DATELINE")
    vf = visible(hf)
    guarded(fails, "/flows prints the 7-day net once (the sentence's), not again as the 13-week list's newest week",
            lambda: vf.count("1.63B") == 1 and "Oct 27 the 7 days above" in vf)
    guarded(fails, "...and prints the count and the floor once, in the sentence", lambda: vf.count("$50M") == 1 and vf.count(" 65 ") <= 1)
    guarded(fails, "...and the biggest single move once, as the first row of its table", lambda: vf.count("$663.7M") == 1)
    guarded(fails, "...and with no evidence record (the canary's build), the list of what was reported carries the item and the "
                   "answer still prints it once", lambda: not one_fact.page_findings(page(h20b))
            and "31% capital-gains tax" in visible(h20b))
    rec = fx("today_2026-10-27-morning.json")
    h27 = dict(pages)["real-2026-10-27-morning"]
    ans = re.search(r'<section class="td-answer".*?</section>', h27, flags=re.S)
    guarded(fails, "the stored answer prints exactly as stored (J-10)", lambda: ans and visible(ans.group(0)) == " ".join(rec["answer"]))
    moved = re.search(r"<h2>What moved</h2>(.*?)</section>", h27, flags=re.S)
    mv = visible(moved.group(1)) if moved else ""
    guarded(fails, "What moved keeps what the answer does not print: Ether's price, the next gainers and losers",
            lambda: "$2,313" in mv and "XDC" in mv and "SKY" in mv and "MORPHO" not in mv and "QNT" not in mv)
    guarded(fails, "...and says so in its headings when the answer named the biggest move",
            lambda: "Other big gains in the Top 100" in mv and "Other big losses in the Top 100" in mv)
    # the living page with no read yet today: the notice names the next read; the footer does not print it again
    with quiet():
        living = today.body_html(rec, [], "living", evidence=None, verdict=None, clock=dt.datetime(2026, 10, 28, 10, 0, tzinfo=UTC))
    fl = one_fact.page_findings(page(living))
    guarded(fails, "the living page with no read yet today prints the next slot's time once (the notice's)",
            lambda: not [x for k, x in fl if "next slot" in x] and visible(living).count("8:15 AM ET") == 1)


# ---- 6. the tree: no test writes a dated snapshot into it, and a stale site/publish cannot fail K-1 ----------------------

def hygiene_cases(fails):
    print("6. the tree: the tests' builds and browser halves leave site/data as they found it; K-1 reads the canary's own tree")
    import site_build as sb
    real = sb.SNAPSHOT_DIR
    before = set(os.listdir(real)) if os.path.isdir(real) else set()
    t = s991()
    ok = hasattr(t, "scratch_writers")
    guarded(fails, "9.9.1's browser half draws its pages with the dated writers pointed at scratch (scripts/sprint991_test.py)",
            lambda: ok)
    if ok:
        with t.scratch_writers():
            with quiet():
                sb.snapshot_pulse({"generated_utc": "2026-10-27T12:17:33Z"})     # a render path that writes the snapshot
        after = set(os.listdir(real)) if os.path.isdir(real) else set()
        guarded(fails, "...so a snapshot written while it draws lands in scratch, not in site/data/snapshots", lambda: after == before)
    # btc_hilo_test's own build (no --tree): a file the build adds to site/data is taken out again
    import btc_hilo_test as bh
    probe = os.path.join(HERE, "site", "data", "snapshots", "pulse-1999-01-01.json")
    saved = (sb.build, sb.load_pulse)

    def fake_build():
        with open(probe, "w") as f:
            f.write("{}")
        os.makedirs(os.path.join(sb.PUBLISH, "coins"), exist_ok=True)
        open(os.path.join(sb.PUBLISH, "index.html"), "w").write("<html></html>")
        open(os.path.join(sb.PUBLISH, "coins", "btc.html"), "w").write("<html></html>")
    try:
        sb.build = fake_build
        with quiet():
            bh.build_tree()
        guarded(fails, "btc_hilo_test's build takes out the dated snapshot it added to site/data (SYNTHETIC build: writes one file)",
                lambda: not os.path.exists(probe))
    finally:
        sb.build, sb.load_pulse = saved
        if os.path.exists(probe):
            os.remove(probe)
    # K-1 reads the tree the canary built, never a stale site/publish
    import verify_pipeline as vp
    stale = tempfile.mkdtemp(prefix="s992-stale-")
    old = sb.PUBLISH
    try:
        open(os.path.join(stale, "news.html"), "w").write("<html><body><h1>News</h1><p>a stale page</p></body></html>")
        sb.PUBLISH = stale
        with quiet():
            f = vp._where_is_news_canary()
        guarded(fails, "a stale site/publish (a news front from an older build) does not fail the canary's K-1 check",
                lambda: not [x for x in f if "K-1 canary: the news front" in x])
        built = tempfile.mkdtemp(prefix="s992-built-")
        open(os.path.join(built, "news.html"), "w").write("<html><body><h1>News</h1></body></html>")
        with quiet():
            g = vp._where_is_news_tree(built) if hasattr(vp, "_where_is_news_tree") else []
        guarded(fails, "...and K-1 still reads the tree the canary's build wrote, and fails a news front with no 'What has happened'",
                lambda: [x for x in g if "does not lead with what happened" in x])
        shutil.rmtree(built, ignore_errors=True)
    finally:
        sb.PUBLISH = old
        shutil.rmtree(stale, ignore_errors=True)
        sys.modules.pop("verify_pipeline", None)


# ---- 7. the words: not compared, a not-read source once, a source link that is not about the event, one window named ------

def s91(name):
    return json.load(open(os.path.join(HERE, "fixtures", "sprint991", "real-2026-10-25-evening", name), encoding="utf-8"))


def wording_cases(fails):
    print("7. the words: 'not compared for this window', a not-read source once, 'source link not matched', the window named")
    import why_evidence as we
    import wire
    ev27 = fx("why_2026-10-27-morning.json")
    with quiet():
        h = we.section_html(ev27, "BTC", live=False, window="rolling_24h")
    v = visible(h)
    guarded(fails, "a venue read whose records do not reach the hour says 'not compared for this hour', never 'not read' "
                   "(the real October 27 record: OKX keeps its latest 100 orders)",
            lambda: "not compared for this hour: OKX keeps its latest 100 orders" in v and "not read for this" not in v)
    ev25 = s91("why.json")
    with quiet():
        h25 = we.section_html(ev25, "BTC", live=False, window="rolling_24h")
    guarded(fails, "a not-read source is listed once: The Block refused twice (HTTP 403) is named once (the real October 25 record)",
            lambda: visible(h25).count("The Block (HTTP 403)") == 1)
    guarded(fails, "...and a new record's reason is written once too", lambda: we.once("not read: A (HTTP 403); A (HTTP 403); B (x)")
            == "not read: A (HTTP 403); B (x)")
    # the source link rule, on the real October 27 wire (fixtures/sprint992/wire-2026-10-27.json, main's site/data/wire.json)
    doc = wire.cite_all(fx("wire-2026-10-27.json"))
    occ = next(i for i in doc["items"] if i["line"].startswith("OCC urges"))
    guarded(fails, "the Daily Hodl link to a UK story is not cited on the OCC item: its address carries no word of the event",
            lambda: all("uk-government" not in (l.get("url") or "") for l in occ["links"]) and occ.get("unmatched") == 1)
    guarded(fails, "...and it does not count as a source (6 counted before, 5 now)", lambda: occ["source_count"] == 5)
    guarded(fails, "...every other item keeps every link (each address names its event)",
            lambda: all(not i.get("unmatched") for i in doc["items"] if i is not occ))
    import home
    with quiet():
        hw = home.wire_top(doc, "", NOW_27)
    guarded(fails, "the home's wire list prints 'source link not matched' on that item, beside its count of 5",
            lambda: re.search(r"OCC urges.*?5 sources &middot; source link not matched", hw, flags=re.S))
    cand = {"id": "w1", "kind": "wire", "line": occ["line"], "titles": [], "report_utc": "2026-10-26T15:45:00Z",
            "source_count": 6, "links": [{"outlet": "CoinDesk", "url": "https://www.coindesk.com/policy/2026/10/26/occ-calls-on-community-banks"},
                                          {"outlet": "The Daily Hodl", "url": "https://dailyhodl.com/2026/10/26/uk-government-placing-cryptoassets-firms-under-fca-oversight/"}]}
    cw = we._wire_candidates({"items": [dict(occ, links=cand["links"], source_count=6, id="x", reported_utc="2026-10-26T15:45:00Z")]},
                             1793010000, 1793030000)
    guarded(fails, "a new evidence record keeps only the matched link and counts 5, so the unmatched source never counts "
                   "toward the grade (verdict.stated reads that count)",
            lambda: cw and len(cw[0]["links"]) == 1 and cw[0]["source_count"] == 5 and cw[0]["unmatched"] == 1)
    import verdict
    guarded(fails, "...verdict.stated counts the 5", lambda: verdict.stated(cw[0], "BTC")[1] == 5)
    # /why/2026-10-25-bitcoin: the card as published, its windows named
    tmp = tempfile.mkdtemp(prefix="s992-why-")
    try:
        for sub, name in (("verdict", "verdict.json"), ("why", "why.json"), ("today", "today.json")):
            os.makedirs(os.path.join(tmp, sub))
            shutil.copy(os.path.join(HERE, "fixtures", "sprint991", "real-2026-10-25-evening", name),
                        os.path.join(tmp, sub, "2026-10-25-evening.json"))
        lead = json.load(open(os.path.join(tmp, "verdict", "2026-10-25-evening.json"), encoding="utf-8"))
        with quiet():
            res = verdict._page("2026-10-25", "BTC", [lead], lead, os.path.join(tmp, "verdict"), os.path.join(tmp, "why"),
                                os.path.join(tmp, "today"), "DATELINE")
        hp = res[0] if isinstance(res, tuple) else (res.get("html") if isinstance(res, dict) else str(res))
        vp_ = visible(hp)
        guarded(fails, "/why/2026-10-25-bitcoin keeps its card as published (Checked: Unclear, its line as stored)",
                lambda: "Checked: Unclear" in vp_ and "No reported event lines up with this move." in vp_)
        guarded(fails, "...and says which window is which: the card's direction since midnight ET, the list's 24 hours, the window "
                       "the grade was made on", lambda: "The card above reads its direction since midnight ET; this chart and list read "
                                                         "the 24 hours to 7:13 PM ET, the window the grade was made on." in vp_)
        guarded(fails, "...and the list names its window beside its figures ('in the 24 hours', never 'the window's fall')",
                lambda: "of the window's fall" not in vp_ and "in the 24 hours" in vp_)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- the tree this build wrote ------------------------------------------------------------------------------------------

def sweep_report(root, data_dir=None):
    import one_fact
    res, n = one_fact.sweep(root)
    if data_dir:
        for u, fs in one_fact.precision_findings(root, data_dir).items():
            res.setdefault(u, []).extend(fs)
    return res, n


def tree(root, data_dir=None):
    fails = []
    print("9. the whole site, every page in the sitemaps: one fact once, every derived figure at its row's precision")
    res, n = sweep_report(root, data_dir if data_dir is not None else os.path.join(HERE, "site", "data"))
    guarded(fails, f"the sweep read the sitemaps ({n} pages)", lambda: n >= 100)
    for u in sorted(res):
        for kind, t in res[u][:6]:
            fails.append(f"{u}: {kind}: {t[:300]}")
            print(f"  FAIL {u}: {kind}: {t[:300]}")
    if not res:
        print("  ok   no figure printed twice on any page, no derived figure off its row's precision")
    return fails


def browser(fails, root):
    print("10. the browser half (scripts/sprint992_browser.mjs): the RSI-14 header at 375, no sideways scroll where figures moved")
    r = subprocess.run(["node", os.path.join(HERE, "scripts", "sprint992_browser.mjs"), root], capture_output=True, text=True,
                       timeout=600)
    for ln in (r.stdout or "").splitlines():
        if ln.startswith(("PASS ", "FAIL ", "INFO ")):
            print("  " + ln[:300])
            if ln.startswith("FAIL ") and not ln.startswith("FAIL 1 check") and "check(s)" not in ln:
                fails.append("browser " + ln[5:])
    if r.returncode not in (0, 1) or not (r.stdout or "").strip():
        fails.append(f"browser half could not run (exit {r.returncode}): {(r.stderr or '')[-200:]}")
    guarded(fails, "the browser half ran every case and none failed", lambda: r.returncode == 0)


def unit(only=()):
    fails = []
    for name, fn in (("checker", checker_cases), ("home", home_cases), ("coin", coin_cases), ("precision", precision_cases), ("today", today_cases), ("hygiene", hygiene_cases), ("wording", wording_cases)):
        if only and name not in only:
            continue
        group(fails, name, fn)
    return fails


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else None
    if "--sweep" in args:
        res, n = sweep_report(args[args.index("--sweep") + 1], data)
        for u in sorted(res):
            for kind, t in res[u]:
                print(f"{u}\t{kind}\t{t}")
        print(f"ONE FACT SWEEP: {n} pages read, {len(res)} with a finding, {sum(len(v) for v in res.values())} finding(s)")
        return 1 if res else 0
    only = args[args.index("--only") + 1].split(",") if "--only" in args else ()
    fails = unit(only)
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1], data)
        if "--browser" in args:
            group(fails, "browser", lambda f: browser(f, args[args.index("--tree") + 1]))
    print(f"\nSPRINT 9.9.2: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
