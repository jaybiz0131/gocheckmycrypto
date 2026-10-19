#!/usr/bin/env python3
"""Program 9, Sprint 9.2: the evidence. Each case is named after what it guards.

  python3 scripts/sprint92_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() on the tree)

Fixtures (fixtures/why/, see README.txt there): every answer the evidence's sources gave for the
24 hours ending at the Board's reading at the 14 and 15 October Editions (2026-10-14T23:43:23Z and
2026-10-15T23:43:27Z), recorded 18 October by `why_evidence.py --record`; the wire as it stood at
those Editions (site/data/wire.json at 7d9008b and 94dd6af); the 15 October Edition's pulse and
flows (94dd6af). Cases marked SYNTHETIC build a small series by hand to reach a rule the two real
days do not; they are labeled as such (Jack, 13 October 2026). Every case catches its own
exceptions, so on a tree without why_evidence.py the run prints FAIL lines instead of crashing.
"""
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FX = os.path.join(HERE, "fixtures", "why")
D14, D15 = "2026-10-14T2343Z", "2026-10-15T2343Z"
GRADE = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b")
BECAUSE = re.compile(r"\bbecause\b", re.I)


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


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


_CACHE = {}


def rec(day):
    """The evidence record built from the recorded answers, as the run would have built it."""
    if day not in _CACHE:
        import why_evidence as we
        fx = load(f"sources_{day}.json")
        r = we.build(fx["end_utc"], load(f"wire_{day}.json"), now_utc=fx["recorded_utc"],
                     fetch=we.Replay(fx["responses"]), pulse=load(f"pulse_{day}.json"))
        r.update(date_et=day[:10], slot="evening")
        _CACHE[day] = r
    return copy.deepcopy(_CACHE[day])


def rec_bare(day):
    """The record with the linked reports withheld: 9.1's source check cannot speak, so every wire
    line stays as the wire held it (for the cases about times, not about the check)."""
    import why_evidence as we
    fx = load(f"sources_{day}.json")
    bare = {u: v for u, v in fx["responses"].items() if not u.startswith("article:")}
    return we.build(fx["end_utc"], load(f"wire_{day}.json"), now_utc=fx["recorded_utc"], fetch=we.Replay(bare))


def cand(r, pat):
    return next(c for c in r["candidates"] if re.search(pat, c["line"]))


def test_of(r, sym, c):
    return next(t for t in r["coins"][sym]["tests"] if t["id"] == c["id"])["result"]


def visible(html):
    """The words a reader sees: scripts, styles and tags out."""
    import html as _h
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return _h.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))


# ---- 1. the intraday series --------------------------------------------------------------------------

def series_cases(fails):
    import why_evidence as we
    print("1. the intraday series: 5-minute prices from a named venue, a second venue beside it")
    r14 = rec(D14)
    b = r14["coins"]["BTC"]
    guarded(fails, "14 Oct: Bitcoin's series is Coinbase's 5-minute candles, 287 closes inside the 24-hour window",
            lambda: b["series"]["source"] == "Coinbase 5-minute candles" and len(b["series"]["points"]) == 287
            and b["series"]["points"][0][0] >= 1792021403 - 86400 and b["series"]["points"][-1][0] <= 1792021403)
    guarded(fails, "14 Oct: OKX is the second read and agrees within 0.1 point (gap 0.03)",
            lambda: b["second"]["source"] == "OKX 5-minute candles" and b["second"]["gap_pts"] == 0.03)
    guarded(fails, "a candle's close is stamped at its bar's end: Coinbase's 23:35Z bar closes at 23:40Z, $81,453.58",
            lambda: [1792021200, 81453.58] in b["series"]["points"])
    un = {u["name"]: u["why"] for u in r14["unread"]}
    guarded(fails, "CoinGecko days=1 is not asked for a window that ended days ago, and is named with the reason",
            lambda: "24 hours before now" in un.get("Bitcoin prices: CoinGecko 5-minute prices", ""))
    guarded(fails, "Kraken's 5-minute candles cannot reach back to 14 Oct, and are named with the reason",
            lambda: "720 five-minute candles" in un.get("Bitcoin prices: Kraken 5-minute candles", ""))
    fx = load(f"sources_{D14}.json")
    resp = dict(fx["responses"])
    cb = next(u for u in resp if "coinbase.com/products/BTC-USD" in u)
    resp[cb] = {"__error__": "HTTP 429"}
    r = we.build(fx["end_utc"], None, now_utc=fx["recorded_utc"], fetch=we.Replay(resp), coins=("BTC",))
    guarded(fails, "a venue that answers 429 is left out and named; the next venue (OKX) carries the series",
            lambda: r["coins"]["BTC"]["series"]["source"] == "OKX 5-minute candles"
            and any(u["name"].endswith("Coinbase 5-minute candles") and u["why"] == "HTTP 429" for u in r["unread"]))
    resp2 = {u: v for u, v in resp.items() if "okx.com/api/v5/market" not in u and "binance.vision" not in u}
    r = we.build(fx["end_utc"], None, now_utc=fx["recorded_utc"], fetch=we.Replay(resp2), coins=("BTC",))
    guarded(fails, "no venue answers: no Bitcoin entry at all (never an invented series), every venue named",
            lambda: "BTC" not in r["coins"] and sum(1 for u in r["unread"] if u["name"].startswith("Bitcoin prices")) == 5)


# ---- 2. the candidates, with event and first-report times ------------------------------------------

def candidate_cases(fails):
    print("2. the candidates: event time, first-report time, primary flag, commentary marked secondary")
    r14, r15 = rec(D14), rec(D15)
    cpi = cand(r14, r"^Consumer Price Index")
    guarded(fails, "14 Oct: CPI from the BLS schedule, event 8:30 AM ET (12:30Z), scheduled, primary",
            lambda: cpi["event_utc"] == "2026-10-14T12:30:00Z" and cpi["scheduled"] and cpi["primary"]
            and cpi["event_basis"] == "BLS release schedule")
    guarded(fails, "14 Oct: the wire's inflation line (12:33:56Z) is CPI's first report, folded in, not listed twice",
            lambda: cpi["report_utc"] == "2026-10-14T12:33:56Z" and "inflation accelerated to 3.7%" in cpi["report_line"]
            and not any(c["kind"] == "wire" and "inflation accelerated" in c["line"] for c in r14["candidates"]))
    guarded(fails, "14 Oct: a wire item keeps its own first-report time and outlets counted (Standard Chartered, 06:12:46Z, 5)",
            lambda: (lambda c: c["report_utc"] == "2026-10-14T06:12:46Z" and c["source_count"] == 5
                     and c["event_utc"] is None)(cand(r14, "Standard Chartered")))
    ppi = cand(r15, r"^Producer Price Index")
    guarded(fails, "15 Oct: PPI from the BLS schedule, event 8:30 AM ET (12:30Z)",
            lambda: ppi["event_utc"] == "2026-10-15T12:30:00Z")
    r15b = rec_bare(D15)
    ppi = cand(r15b, r"^Producer Price Index")
    guarded(fails, "15 Oct: the producer-price wire line stamped 04:25Z, BEFORE the 8:30 AM release, is not taken as its first report",
            lambda: ppi.get("report_utc") is None and any(c["kind"] == "wire" and c["report_utc"] == "2026-10-15T04:25:15Z"
                                                          for c in r15b["candidates"]))
    fr = cand(r14, r"Federal Register")
    guarded(fails, "a source that gives only a day (the Federal Register) carries no invented time; its test cannot run",
            lambda: fr["event_utc"] is None and test_of(r14, "BTC", fr) is None and fr["event_day"] == "2026-10-13")
    import why_evidence as we
    w = {"items": [{"id": "x1", "line": "Bitcoin slid as analysts said rising yields weighed on risk assets.",
                    "reported_utc": "2026-10-14T15:00:00Z", "source_count": 1, "links": [{"url": "https://e.x/a", "outlet": "E"}]},
                   {"id": "x2", "line": "SEC approved the first spot Solana ETF.",
                    "reported_utc": "2026-10-14T15:05:00Z", "source_count": 2, "links": [{"url": "https://e.x/b", "outlet": "E"}]}]}
    cs = we._wire_candidates(w, 1792021403 - 86400, 1792021403)
    guarded(fails, "SYNTHETIC wire lines: a cause given only as commentary ('analysts said') is kept and marked secondary",
            lambda: cs[0]["secondary"] and "commentary" in cs[0]["secondary_why"])
    guarded(fails, "SYNTHETIC wire lines: a reported event is not marked secondary", lambda: not cs[1]["secondary"])


# ---- 3. the timing test on the recorded days -----------------------------------------------------------

def timing_cases(fails):
    import why_evidence as we
    print("3. the timing test on the recorded fixtures")
    r14, r15 = rec(D14), rec(D15)
    run = r14["coins"]["BTC"]["run"]
    guarded(fails, "14 Oct: the largest same-direction run is DOWN 3.144%, from $84,011.46 at 4:10 AM ET to $81,369.99 at 6:45 PM ET",
            lambda: run["dir"] == "down" and run["pct"] == -3.144 and run["start_p"] == 84011.46
            and we.clock(run["start_t"]) == "4:10 AM ET" and we.clock(run["end_t"]) == "6:45 PM ET"
            and run["end_p"] == 81369.99)
    t = test_of(r14, "BTC", cand(r14, r"^Consumer Price Index"))
    guarded(fails, "14 Oct CPI: it came 260 minutes after the onset, so not before it",
            lambda: t["lead_min"] == -260.0 and t["before_onset"] is False)
    guarded(fails, "14 Oct CPI: the next 60 minutes carried 71.2% of the window's fall (Bitcoin -1.45% in that hour)",
            lambda: t["share_pct"] == 71.2 and t["after_pct"] == -1.45)
    guarded(fails, "14 Oct CPI: the price had not moved first (8.5% of the run done before 8:30 AM)",
            lambda: t["done_pct"] == 8.5 and t["moved_first"] is False)
    t = test_of(r14, "BTC", cand(r14, "Payward"))
    guarded(fails, "14 Oct Payward/Saldo (13:07:45Z): the price moved first, 50.7% of the run done before the first report",
            lambda: t["moved_first"] is True and t["done_pct"] == 50.7)
    t = test_of(r14, "BTC", cand(r14, "Standard Chartered"))
    guarded(fails, "14 Oct Standard Chartered: 117 minutes before the onset is outside the 60-minute lead",
            lambda: t["lead_min"] == 117.2 and t["before_onset"] is False)
    run = r15["coins"]["BTC"]["run"]
    guarded(fails, "15 Oct: the largest run is UP 3.384%, from $79,790.86 at 9:55 AM ET to $82,491.34 at 6:25 PM ET",
            lambda: run["dir"] == "up" and run["pct"] == 3.384 and we.clock(run["start_t"]) == "9:55 AM ET"
            and run["start_p"] == 79790.86 and run["end_p"] == 82491.34)
    t = test_of(r15, "BTC", cand(r15, r"^Producer Price Index"))
    guarded(fails, "15 Oct PPI: released 85 minutes before the onset, outside the lead and not at the onset",
            lambda: t["lead_min"] == 85.0 and t["before_onset"] is False)
    guarded(fails, "15 Oct PPI: the hour after it ran against the window's rise (Bitcoin -1.04%, share -160.4%)",
            lambda: t["share_pct"] == -160.4 and t["after_pct"] == -1.04)
    t = test_of(r15, "BTC", cand(r15, "Russia's Central Bank"))
    guarded(fails, "15 Oct Russia P2P line (20:31:04Z): the price moved first, 92.7% of the run done",
            lambda: t["moved_first"] and t["done_pct"] == 92.7)
    e = r15["coins"]["ETH"]["run"]
    guarded(fails, "15 Oct Ether: its own run, UP 5.939% from 9:55 AM ET", lambda: e["dir"] == "up" and e["pct"] == 5.939
            and we.clock(e["start_t"]) == "9:55 AM ET")
    # SYNTHETIC: a hand-made series, to reach the two "before the onset" branches the real days do not
    base = 1_800_000_000
    pts = [(base + i * 300, 100.0) for i in range(24)] + [(base + (24 + i) * 300, 100.0 - (i + 1) * 0.5) for i in range(12)]
    run = we.onset(pts)
    guarded(fails, "SYNTHETIC: a flat line then a fall: the onset is the last point before the fall",
            lambda: run["start_t"] == base + 23 * 300 and run["dir"] == "down")
    guarded(fails, "SYNTHETIC: an event 30 minutes before the onset comes before it, within the lead",
            lambda: we.timing(pts, run, run["start_t"] - 1800)["before_onset"] is True)
    guarded(fails, "SYNTHETIC: an event 61 minutes before does not",
            lambda: we.timing(pts, run, run["start_t"] - 61 * 60)["before_onset"] is False)
    guarded(fails, "SYNTHETIC: a scheduled release 5 minutes AFTER the detected onset is at its release time",
            lambda: we.timing(pts, run, run["start_t"] + 300, scheduled=True)["before_onset"] is True
            and we.timing(pts, run, run["start_t"] + 300, scheduled=False)["before_onset"] is False)
    guarded(fails, "SYNTHETIC: the hour after the onset carries the whole fall (share 100%)",
            lambda: we.timing(pts, run, run["start_t"])["share_pct"] == 100.0)


# ---- 4. the mechanics of the onset hour ----------------------------------------------------------------

def mechanics_cases(fails):
    import why_evidence as we
    print("4. the mechanics pattern for the onset hour")
    r14, r15 = rec(D14), rec(D15)
    m = r15["coins"]["BTC"]["mechanics"]
    row = {x["key"]: x for x in m["rows"]}
    guarded(fails, "15 Oct, 9:55 to 10:55 AM ET: Bitcoin +2.50%, S&P 500 futures +0.58%, Nasdaq 100 futures +0.94% (Yahoo)",
            lambda: row["BTC"]["value"] == 2.5 and row["ES=F"]["value"] == 0.58 and row["NQ=F"]["value"] == 0.94)
    guarded(fails, "15 Oct: the pattern is 'risk-on across assets', with its rule",
            lambda: [p["label"] for p in m["patterns"]] == ["risk-on across assets"])
    guarded(fails, "15 Oct: the 10-year yield moves in basis points (+1.7 bp), the VIX in percent (-5.12%)",
            lambda: row["^TNX"]["unit"] == "bp" and row["^TNX"]["value"] == 1.7 and row["^VIX"]["value"] == -5.12)
    guarded(fails, "15 Oct: OKX's hourly open interest is read for the hour from 9:00 AM ET (+0.67%)",
            lambda: row["oi"]["value"] == 0.67 and "9:00 AM ET" in row["oi"]["label"])
    guarded(fails, "OKX liquidations cannot reach back to the onset hour: not read, with the reason, never a zero",
            lambda: row["liq"].get("unread") and "latest 100 orders" in row["liq"]["why"] and "longs_usd" not in row["liq"])
    m14 = r14["coins"]["BTC"]["mechanics"]
    r = {x["key"]: x for x in m14["rows"]}
    guarded(fails, "14 Oct, 4:10 AM ET: the 10-year yield did not trade in the hour: None, not 0",
            lambda: r["^TNX"]["value"] is None)
    guarded(fails, "14 Oct: Bitcoin -0.74% with stock futures mixed (+0.03%, -0.11%): no pattern is claimed",
            lambda: m14["patterns"] == [])
    e = r15["coins"]["ETH"]["mechanics"]
    guarded(fails, "15 Oct Ether: 30-day beta 1.074 from the stored closes; excess +0.19 point is not coin-specific",
            lambda: e["beta"] == 1.074 and e["excess_pts"] == 0.19 and "coin-specific" not in [p["label"] for p in e["patterns"]])
    # SYNTHETIC: hand-made hour readings to reach the rules the real days do not
    base = 1_800_000_000
    run = {"dir": "down", "start_t": base, "end_t": base + 7200, "start_p": 100.0, "end_p": 95.0, "pct": -5.0}
    flat = [[base - 300, 50.0], [base, 50.0], [base + 1800, 50.0], [base + 3600, 50.0]]
    btc = [[base - 300, 100.0], [base, 100.0], [base + 3600, 98.0]]
    oi = {"period": "5m", "points": [[base, 1000.0], [base + 3600, 940.0]]}
    liq = {"orders": [[base - 600, "long", 1], [base + 600, "long", 8_000_000], [base + 900, "short", 1_000_000]]}
    m = we.mechanics("BTC", run, btc, {}, {"ES=F": {"points": flat}, "NQ=F": {"points": flat}}, oi, liq, None, None)
    labels = [p["label"] for p in m["patterns"]]
    guarded(fails, "SYNTHETIC: Bitcoin -2% with stock futures flat is 'crypto only'", lambda: "crypto only" in labels)
    guarded(fails, "SYNTHETIC: open interest -6% with 89% of liquidations long is a 'leverage flush'",
            lambda: "leverage flush" in labels)
    eth = [[base - 300, 10.0], [base, 10.0], [base + 3600, 9.5]]
    m = we.mechanics("ETH", run, eth, {"BTC": {"points": btc}}, {}, None, None, None, 1.0)
    guarded(fails, "SYNTHETIC: Ether -5% against Bitcoin -2% at beta 1.0 is 'coin-specific' (excess -3 points)",
            lambda: "coin-specific" in [p["label"] for p in m["patterns"]] and m["excess_pts"] == -3.0)


# ---- 5. the chart from a fixture ---------------------------------------------------------------------------

def chart_cases(fails):
    import why_evidence as we
    print("5. the timing chart from a fixture")
    r15, r14 = rec(D15), rec(D14)
    html = we.section_html(r15, "BTC")
    svg = re.search(r'<svg class="ev-chart".*?</svg>', html, re.S)
    guarded(fails, "15 Oct: the section draws one timing chart", lambda: svg is not None)
    s = svg.group(0) if svg else ""
    line = re.search(r'class="ev-line"[^>]*stroke="([^"]+)"[^>]*points="([^"]+)"', s)
    guarded(fails, "the price line has a point per 5-minute close (287)", lambda: len(line.group(2).split()) == 287)
    guarded(fails, "15 Oct (an up window) draws in the up line color; 14 Oct (down) in the down color",
            lambda: line.group(1) == "var(--up-line)" and 'stroke="var(--down-line)"' in we.section_html(r14, "BTC"))
    run = r15["coins"]["BTC"]["run"]
    pts = r15["coins"]["BTC"]["series"]["points"]
    x_on = we._x(run["start_t"], pts[0][0], pts[-1][0], we.CHART_X0, we.CHART_X1)
    guarded(fails, "the onset mark sits at the onset's time on the axis (9:55 AM ET)",
            lambda: f'class="ev-onset" cx="{x_on:.1f}"' in s)
    rect = re.search(r'class="ev-run" x="([\d.]+)" y="\d+" width="([\d.]+)"', s)
    x_end = we._x(run["end_t"], pts[0][0], pts[-1][0], we.CHART_X0, we.CHART_X1)
    guarded(fails, "the shaded run spans onset to the run's end",
            lambda: abs(float(rect.group(1)) - x_on) < 0.11 and abs(float(rect.group(1)) + float(rect.group(2)) - x_end) < 0.2)
    pins = re.findall(r'<g class="ev-pin">.*?>(\d+)</text></g>', s)
    items = re.findall(r'<li class="ev-c"><span class="ev-n" aria-hidden="true">(\d+)</span>', html)
    timed = sum(1 for t in r15["coins"]["BTC"]["tests"] if t["t_utc"])
    guarded(fails, f"every pinned number is a numbered item in the list below the chart ({timed} pins, one per timed item)",
            lambda: pins and set(pins) <= set(items) and len(pins) == timed == 5)
    guarded(fails, "the chart says what it is in words (role=img, its window, its range)",
            lambda: 'role="img"' in s and "the 24 hours to 7:43 PM ET Thursday, October 15" in s)
    guarded(fails, "the PPI release is pinned at 8:30 AM ET on the line",
            lambda: "8:30 AM ET (scheduled)" in visible(html))


# ---- 6. the pages ----------------------------------------------------------------------------------------

def _coin_html(sym, ev):
    import site_build as sb
    import snapshot
    p = load(f"pulse_{D15}.json")
    coins = p["movers"]["top100"]
    pos, c = next((i + 1, x) for i, x in enumerate(coins) if x["symbol"] == sym)
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, load(f"flows_{D15}.json"))
    try:
        return sb.render_coin_page(c, pos, p, [], "THURSDAY, OCTOBER 15, 2026", wire=load(f"wire_{D15}.json"),
                                   cm={}, evidence=ev)
    finally:
        sb.SNAP = old


def page_cases(fails):
    import today
    import why_evidence as we
    print("6. /today/ and the Bitcoin and Ether pages: the section, the chart, no grade, fail open")
    r15 = rec(D15)
    d15 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))
    pages = {}
    try:
        pages["/today/ (living)"] = today.body_html(d15, [], "living", evidence=r15)
        pages["/today/2026-10-15"] = today.body_html(d15, [], "dated", evidence=r15)
    except Exception as e:                                   # noqa: BLE001
        guarded(fails, f"today.body_html takes the evidence record [{type(e).__name__}: {e}]", lambda: False)
    try:
        pages["/coins/btc"] = _coin_html("BTC", r15)
        pages["/coins/eth"] = _coin_html("ETH", r15)
    except Exception as e:                                   # noqa: BLE001
        guarded(fails, f"render_coin_page takes the evidence record [{type(e).__name__}: {e}]", lambda: False)
    for name, html in pages.items():
        guarded(fails, f"{name}: 'What lined up with the move' with its timing chart",
                lambda: "<h2>What lined up with the move</h2>" in html and 'class="ev-chart"' in html)
        # Sprint 9.3 puts the grade on these pages in one place, the verdict card (aside.vd); outside
        # it the page carries no grade word and no "because", as 9.2 built it.
        guarded(fails, f"{name}: no grade word (Confirmed, Likely, Disputed, Unclear) and no 'because' anywhere on the page outside the verdict card",
                lambda: not GRADE.search(visible(re.sub(r'<aside class="vd.*?</aside>', "", html, flags=re.S)))
                and not BECAUSE.search(visible(re.sub(r'<aside class="vd.*?</aside>', "", html, flags=re.S))))
        guarded(fails, f"{name}: no em dash or en dash", lambda: not re.search("[\u2013\u2014]", html))
        guarded(fails, f"{name}: the section never prints 'market_chart' (the coin page guard against inline chart code)",
                lambda: "market_chart" not in re.search(r'<section class="td-sec ev".*?</section>', html, re.S).group(0))
    guarded(fails, "/today/ shows Bitcoin's evidence; the Ether page shows Ether's",
            lambda: 'data-ev="BTC"' in pages["/today/ (living)"] and 'data-ev="ETH"' in pages["/coins/eth"]
            and 'data-ev="BTC"' not in pages["/coins/eth"])
    guarded(fails, "the living page's window stamp carries data-asof (the stale state); the dated page's does not",
            lambda: 'class="ev-win" data-asof="2026-10-15T23:43:27Z"' in pages["/today/ (living)"]
            and 'class="ev-win" data-asof' not in pages["/today/2026-10-15"])
    btc = visible(pages.get("/coins/btc", ""))
    guarded(fails, "a wire item is printed once: the Russia P2P line is in the section, not again under the page's own lists",
            lambda: btc.count("Russia's Central Bank confirmed ban") == 1)
    guarded(fails, "each unread source is named on the page with its reason",
            lambda: "Not read, so not shown:" in btc and "Hyperliquid liquidations" in btc)
    planted = copy.deepcopy(r15)
    planted["candidates"][0]["line"] = "Likely the trigger, because traders said so."
    h = we.section_html(planted, "BTC")
    guarded(fails, "a candidate line carrying a grade word or 'because' is not printed; its outlet stands in",
            lambda: "Likely the trigger" not in h and not BECAUSE.search(visible(h)))
    # FAIL OPEN: no record, a broken record, an old record
    plain = today.body_html(d15, [], "dated")
    guarded(fails, "/today/ with no evidence renders as before, with no section",
            lambda: "What lined up with the move" not in plain and "<h2>What moved</h2>" in plain)
    guarded(fails, "a broken record draws no section and raises nothing",
            lambda: we.section_html({"coins": {"BTC": {"series": {"points": "x"}}}}, "BTC") == "")
    guarded(fails, "a record whose window ended 20 hours before the Board's reading is not shown on a coin page",
            lambda: we.from_snapshot_coin(r15, "BTC", "2026-10-16T19:43:27Z") is None
            and we.from_snapshot_coin(r15, "BTC", "2026-10-15T23:50:00Z") is not None)
    import tempfile
    old_dir = we.DIR
    try:
        we.DIR = tempfile.mkdtemp(prefix="why-empty-")       # no evidence on disk, whatever the tree holds
        nohtml = _coin_html("BTC", None)
        guarded(fails, "the Bitcoin page with no evidence on disk renders without the section",
                lambda: "What lined up with the move" not in nohtml and "Bitcoin" in nohtml)
    except Exception as e:                                   # noqa: BLE001
        guarded(fails, f"the Bitcoin page with no evidence renders [{type(e).__name__}: {e}]", lambda: False)
    finally:
        we.DIR = old_dir


# ---- 7. no model, and the run path -------------------------------------------------------------------------

def wiring_cases(fails):
    import datetime as dt
    import tempfile
    import today
    print("7. no model call; wired into the run path like the daily answer")
    src = open(os.path.join(HERE, "why_evidence.py"), encoding="utf-8").read()
    guarded(fails, "why_evidence.py never imports or calls the model layer (llm.py)",
            lambda: not re.search(r"^\s*(import llm|from llm)|llm\.", src, re.M))
    guarded(fails, "why_evidence.py carries no em dash", lambda: not re.search("[\u2013\u2014]", src))
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: runs why_evidence.py --write after the daily answer's record, never as a gate",
                lambda: re.search(r"today\.py --write \|\| true.*?why_evidence\.py --write \|\| true", y, re.S))
        guarded(fails, f"{wf}: commits the evidence records with the push",
                lambda: "git add site/data/why" in y)
    r15 = rec(D15)
    d15 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        json.dump(r15, open(os.path.join(td, "2026-10-15-evening.json"), "w"))
        now = dt.datetime(2026, 10, 15, 23, 50, tzinfo=dt.timezone.utc)
        built = today.build_pages(None, None, None, None, None, now, None, stored=[d15], why_dir=td)
        guarded(fails, "today.build_pages reads the stored record for the page's day and slot",
                lambda: any("What lined up with the move" in h for _r, h, _p, _m in built))
        built = today.build_pages(None, None, None, None, None, now, None, stored=[d15], why_dir=os.path.join(td, "none"))
        guarded(fails, "and with no stored record builds the same pages without the section",
                lambda: built and not any("What lined up with the move" in h for _r, h, _p, _m in built))


# ---- 8. every source the audit names is read, or named with a true reason ------------------------------

# The audit's section 3.1 list (layers 1 to 3) and the reviewer's additions, kept here by hand so the
# module cannot satisfy the test by shortening its own list.
CATALOG = ["CoinGecko", "Coinbase", "OKX 5-minute candles", "Binance", "Kraken", "BLS release schedule",
           "BEA release dates", "FOMC calendar", "Federal Reserve press releases", "SEC press releases",
           "EDGAR", "CFTC press releases", "Federal Register", "Exchange listing notices", "DefiLlama hacks",
           "DefiLlama stablecoin supply", "Nasdaq economic calendar", "ForexFactory calendar",
           "OKX liquidations", "Gate liquidations", "Hyperliquid liquidations", "OKX open interest",
           "OKX taker flow", "OKX funding", "Farside", "S&P 500 futures", "Nasdaq 100 futures", "Dollar index",
           "10-year Treasury yield", "2-year Treasury note futures", "Gold futures", "Oil futures", "VIX",
           "IBIT", "FBTC", "Kalshi"]


def _answer(day, frag):
    fx = load(f"sources_{day}.json")
    return next(v for u, v in fx["responses"].items() if frag in u)


def source_cases(fails):
    import why_evidence as we
    print("8. every source the audit names is read, or left out and named with a true reason")
    for day in (D14, D15):
        r = rec(day)
        names = [x["name"] for x in r["read"]] + [x["name"] for x in r["unread"]]
        missing = [c for c in CATALOG if not any(c in n for n in names)]
        guarded(fails, f"{day[:10]}: every catalogued source is in the read or the not-read list (missing: {missing})",
                lambda: not missing)
        guarded(fails, f"{day[:10]}: every not-read source carries a reason",
                lambda: all(x.get("why") for x in r["unread"]))
    r14, r15 = rec(D14), rec(D15)
    rd15 = {x["name"] for x in r15["read"]}
    un = {x["name"]: x["why"] for x in r15["unread"]}
    guarded(fails, "Binance's data-api.binance.vision mirror is read as a series venue, its gap kept beside the others",
            lambda: any("Binance" in n for n in rd15)
            and any("Binance" in o["source"] for o in r15["coins"]["BTC"].get("seconds") or []))
    row = {x["key"]: x for x in r15["coins"]["BTC"]["mechanics"]["rows"]}
    tk = _answer(D15, "taker-volume-contract?instId=BTC-USDT-SWAP")["data"][0]
    guarded(fails, "15 Oct: OKX taker flow is read hourly for the onset hour, buys and sells as OKX sent them (USDT)",
            lambda: row["taker"]["buy_usd"] == round(float(tk[2])) and row["taker"]["sell_usd"] == round(float(tk[1])))
    gate = _answer(D15, "gateio.ws/api/v4/futures/usdt/liq_orders?contract=BTC_USDT")
    q = float(_answer(D15, "gateio.ws/api/v4/futures/usdt/contracts/BTC_USDT")["quanto_multiplier"])
    longs = round(sum(abs(float(o["size"])) * q * float(o["fill_price"]) for o in gate if float(o["size"]) > 0))
    guarded(fails, "15 Oct: Gate's liquidations are read for the onset hour (longs summed from its own answer)",
            lambda: row["liq-gate"]["longs_usd"] == longs and isinstance(row["liq-gate"]["shorts_usd"], int))
    guarded(fails, "Hyperliquid's liquidations are named, with the reason they cannot be read",
            lambda: "liquidation history" in un.get("Hyperliquid liquidations", ""))
    ks = [x for x in r15["coins"]["BTC"]["mechanics"]["rows"] if x["key"].startswith("kalshi")]
    guarded(fails, "15 Oct: Kalshi's Fed markets for the next meeting are read for the onset hour (yes price, both ends)",
            lambda: ks and all(isinstance(k["from_pct"], float) and isinstance(k["to_pct"], float) for k in ks))
    guarded(fails, "15 Oct: IBIT and FBTC volume in the onset hour (9:55 AM ET, market open) are read, in shares",
            lambda: row["IBIT"]["value"] > 0 and row["FBTC"]["value"] > 0 and row["IBIT"]["unit"] == "shares")
    r = {x["key"]: x for x in r14["coins"]["BTC"]["mechanics"]["rows"]}
    guarded(fails, "14 Oct: at 4:10 AM ET IBIT did not trade: None, never 0", lambda: r["IBIT"]["value"] is None)
    guarded(fails, "the 2-year Treasury note future is read", lambda: "ZT=F" in row)
    guarded(fails, "Nasdaq's calendar is named with the true reason (its dates come back a day late)",
            lambda: "a day late" in un.get("Nasdaq economic calendar", ""))
    guarded(fails, "ForexFactory's calendar, which keeps only the current week, is named for a past window",
            lambda: "current week" in un.get("ForexFactory calendar", ""))
    html = we.section_html(r15, "BTC")
    guarded(fails, "the page says what was read but is not shown in the hour (Farside's daily ETF flow, DefiLlama's daily supply)",
            lambda: "Farside" in visible(html) and "Read, not shown in this hour:" in visible(html))
    nr = re.search(r"Not read, so not shown: (.*?)</p>", html, re.S)
    guarded(fails, "the not-read paragraph lists every not-read source of the record, and nothing read",
            lambda: nr and all(x["name"] in visible(nr.group(1)) for x in r15["unread"]))


# ---- 9. corrections reach the section; the wire's source check runs on candidates -----------------------

def correction_cases(fails):
    import today
    import why_evidence as we
    print("9. a correction on the page applies to the section; unsupported wire clauses are cut")
    d15 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))
    fx = load(f"sources_{D15}.json")
    bare = {u: v for u, v in fx["responses"].items() if not u.startswith("article:")}
    r = we.build(fx["end_utc"], load(f"wire_{D15}.json"), now_utc=fx["recorded_utc"], fetch=we.Replay(bare))
    guarded(fails, "with the articles unread the source check cannot speak, and the producer-price line stays in the record",
            lambda: any("$940 million" in c["line"] for c in r["candidates"]))
    page = visible(today.body_html(d15, [], "dated", evidence=r))
    guarded(fails, "15 Oct: the page's correction drops the corrected line from the section; it prints once, inside the correction",
            lambda: page.count("Hot US producer-price data triggered nearly $940 million") == 1
            and "The line has been removed." in page)
    sec = we.section_html(r, "BTC", corrections=d15["corrections"])
    guarded(fails, "section_html with the corrections never prints the corrected line",
            lambda: "$940 million" not in visible(sec))
    guarded(fails, "without them (a page with no correction) the line is still printed, so the test bites",
            lambda: "$940 million" in visible(we.section_html(r, "BTC")))
    full = rec(D15)
    guarded(fails, "with the articles read, 9.1's source check cuts the unsupported producer-price line before it is printed",
            lambda: not any("$940 million" in c["line"] for c in full["candidates"])
            and any("$940 million" in (x.get("line") or "") for x in full.get("source_cuts") or []))


# ---- 10. every window labeled with its own times; the run step bounded --------------------------------

def window_cases(fails):
    print("10. each row's window is the one its label states (Kalshi's hourly closes)")
    for day, a, b in ((D15, "9:00 AM ET close", "10:00 AM ET close"), (D14, "4:00 AM ET close", "5:00 AM ET close")):
        ks = [x for x in rec(day)["coins"]["BTC"]["mechanics"]["rows"] if x["key"].startswith("kalshi")]
        guarded(fails, f"{day[:10]}: the Kalshi row names the candle closes it reads ('{a} to {b}')",
                lambda: ks and all(f"{a} to {b}" in k["label"] for k in ks))
        guarded(fails, f"{day[:10]}: and carries those closes as stamps (from_utc, to_utc an hour apart)",
                lambda: ks and all(k["to_utc"] and k["from_utc"]
                                   and (int(_ts(k["to_utc"])) - int(_ts(k["from_utc"]))) == 3600 for k in ks))
    import why_evidence as we
    html = we.section_html(rec(D15), "BTC")
    guarded(fails, "the page prints the Kalshi row with its closes", lambda: "9:00 AM ET close to 10:00 AM ET close" in visible(html))


def _ts(s):
    import datetime as dt
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def budget_cases(fails):
    import why_evidence as we
    print("11. the run step: a deadline inside build(), Kalshi capped, no blind sleeps, the core always kept")
    fx = load(f"sources_{D15}.json")
    replay = we.Replay(fx["responses"])
    clock = _Clock()

    def slow(url, kind="json"):
        body = replay(url, kind)
        if "chart/ES=F" in url:
            clock.t += 250          # a source that answers after the whole budget is gone
        return body
    try:
        r = we.build(fx["end_utc"], load(f"wire_{D15}.json"), now_utc=fx["recorded_utc"], fetch=slow,
                     pulse=load(f"pulse_{D15}.json"), clock=clock)
    except Exception as e:                                   # noqa: BLE001
        guarded(fails, f"build() takes a clock and a deadline [{type(e).__name__}: {e}]", lambda: False)
        return
    late = {u["name"]: u["why"] for u in r["unread"] if "not read in time" in u["why"]}
    guarded(fails, "a source past the deadline: the sources after it are named 'not read in time' (Gate, Kalshi, OKX taker flow)",
            lambda: any(n.startswith("Gate liquidations") for n in late) and any(n.startswith("Kalshi") for n in late)
            and any(n.startswith("OKX taker flow") for n in late))
    guarded(fails, "and the core is whole: both series, the runs and the timing test, as without the delay",
            lambda: r["coins"]["BTC"]["run"] == rec(D15)["coins"]["BTC"]["run"]
            and r["coins"]["ETH"]["run"] == rec(D15)["coins"]["ETH"]["run"]
            and [t["result"] for t in r["coins"]["BTC"]["tests"]] == [t["result"] for t in rec(D15)["coins"]["BTC"]["tests"]])
    guarded(fails, "and the late sources print in the section's not-read list",
            lambda: "not read in time" in visible(we.section_html(r, "BTC")))

    def broken(url, kind="json"):
        if any(h in url for h in ("coinbase.com", "okx.com/api/v5/market", "binance.vision")):
            return replay(url, kind)
        raise we.Unread("HTTP 503")
    r2 = we.build(fx["end_utc"], load(f"wire_{D15}.json"), now_utc=fx["recorded_utc"], fetch=broken)
    guarded(fails, "every optional source failing: the record still carries both series and the timing test",
            lambda: r2["coins"]["BTC"]["run"] and r2["coins"]["ETH"]["run"]
            and all("result" in t for t in r2["coins"]["BTC"]["tests"]) and len(r2["unread"]) > 20)
    calls = []

    def count(url, kind="json"):
        if "kalshi.com" in url:
            calls.append(url)
        return replay(url, kind)
    we.build(fx["end_utc"], load(f"wire_{D15}.json"), now_utc=fx["recorded_utc"], fetch=count)
    # a fixed bound, not the module's own constant: the October meeting has 11 strikes, and the record
    # reads at most 2 calls plus 4 strikes for both coins together
    guarded(fails, f"Kalshi's calls are bounded for the whole record, both coins: {len(calls)} <= 6, none repeated",
            lambda: 0 < len(calls) <= 6 and len(set(calls)) == len(calls))
    guarded(fails, "no blind 60-second wait: a 429's Retry-After is capped at 3 seconds, and a missing one waits 2",
            lambda: we.retry_wait("60") == 3 and we.retry_wait(None) == 2 and we.retry_wait("1") == 1)
    src = open(os.path.join(HERE, "why_evidence.py"), encoding="utf-8").read()
    guarded(fails, "the evidence step no longer reads through market_pulse.get_json (its 60-second waits)",
            lambda: "market_pulse.get_json" not in src)
    b = we.Budget(200, clock=_Clock())
    we.STOP["set"] = True
    try:
        guarded(fails, "a SIGTERM (the stop flag) spends the budget at once, and says so",
                lambda: b.spent() and "stopped" in b.why())
    finally:
        we.STOP["set"] = False


def unit():
    fails = []
    group(fails, "1 (series)", series_cases)
    group(fails, "2 (candidates)", candidate_cases)
    group(fails, "3 (timing test)", timing_cases)
    group(fails, "4 (mechanics)", mechanics_cases)
    group(fails, "5 (chart)", chart_cases)
    group(fails, "6 (pages)", page_cases)
    group(fails, "7 (wiring)", wiring_cases)
    group(fails, "8 (sources)", source_cases)
    group(fails, "9 (corrections)", correction_cases)
    group(fails, "10 (windows)", window_cases)
    group(fails, "11 (run step)", budget_cases)
    return fails


def main():
    fails = unit()
    print("\nSPRINT 9.2:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
