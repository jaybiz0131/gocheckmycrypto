#!/usr/bin/env python3
"""Program 9, Sprint 9.1: numbers that agree. Each case is named after the audit's evidence.

  python3 scripts/sprint91_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() on the tree)

Fixtures (fixtures/sprint91/): the 16 October 12:16 UTC pulse and flows as the desk held them (the
numbers the audit read: Bitcoin +1.48%, Ether +4.13%, whole market -0.62%, stablecoins -$233.2M net
with no inflow) and the 15 October 7:43 PM wire with the producer-price line. Every case catches its
own exceptions, so on origin/main (no snapshot check, no stable_flow_words) the run prints FAIL
lines instead of crashing.
"""
import copy
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FX = os.path.join(HERE, "fixtures", "sprint91")


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


def pulse16():
    return load("pulse_2026-10-16T1216Z.json")


def flows16():
    return load("flows_2026-10-16T1216Z.json")


def snap16():
    import snapshot
    return snapshot.build(pulse16(), flows16())


# ---- item 1: the whole-market change ------------------------------------------------------------

def market_cases(fails):
    import snapshot
    print("1. the whole-market change is cross-checked before it prints")
    s = snap16()
    cap = snapshot.value(s, "total_cap") or {}
    guarded(fails, "16 October: market -0.62% beside Bitcoin +1.48% and Ether +4.13% is withheld (None), not printed",
            lambda: cap.get("chg_24h_pct") is None)
    guarded(fails, "16 October: the state says unchecked, with the reason",
            lambda: cap.get("chg_state") == "unchecked" and "contradicts" in (cap.get("chg_withheld") or ""))
    guarded(fails, "16 October: the cap itself still prints", lambda: cap.get("usd") == 2783826930884)
    p = pulse16()
    for r in p["movers"]["top100"]:
        r["chg_24h_pct"] = 1.0
    p["market"]["mcap_change_24h_pct"] = 1.1
    ok = snapshot.value(snapshot.build(p, flows16()), "total_cap") or {}
    guarded(fails, "a figure that agrees with Bitcoin, Ether and the Top 100 prints (checked)",
            lambda: ok.get("chg_24h_pct") == 1.1 and ok.get("chg_state") == "checked")
    p["market"]["mcap_change_24h_pct"] = 4.0
    far = snapshot.value(snapshot.build(p, flows16()), "total_cap") or {}
    guarded(fails, "a figure 3 points from the Top 100's own is withheld even on the right side of zero",
            lambda: far.get("chg_24h_pct") is None and far.get("chg_state") == "unchecked")
    p["market"]["mcap_change_24h_pct"] = None
    none = snapshot.value(snapshot.build(p, flows16()), "total_cap") or {}
    guarded(fails, "a missing change is None and unchecked, never a fake 0.00%",
            lambda: none.get("chg_24h_pct") is None and none.get("chg_state") == "unchecked")
    import market_pulse
    real = market_pulse.get_json
    try:
        market_pulse.get_json = lambda *a, **k: {"data": {"total_market_cap": {"usd": 1e12},
                                                         "market_cap_percentage": {"btc": 50}}}
        m = market_pulse.section_market()
    finally:
        market_pulse.get_json = real
    guarded(fails, "market_pulse: a /global answer with no change field gives None, not 0", lambda: m["mcap_change_24h_pct"] is None)
    import site_build as sb
    strip = sb.market_strip(snapshot.views(s, pulse16(), flows16())[0])
    guarded(fails, "the ticker's total cap says 'unchecked' and prints no -0.6%",
            lambda: 'class="chg unchecked"' in strip and "-0.6%" not in strip)
    guarded(fails, "the ticker script reads live Bitcoin and Ether before it prints /global's change",
            lambda: "okChg(" in strip)


# ---- item 2: Whale Watch's stablecoin sign -------------------------------------------------------

def whale_cases(fails):
    import site_build as sb
    print("2. Whale Watch: the $233.2M case")
    guarded(fails, "negative buying power reads 'off exchanges'", lambda: sb.stable_flow_words(-233245281)[1] == "off exchanges")
    guarded(fails, "positive buying power reads 'onto exchanges'", lambda: sb.stable_flow_words(5e7)[1] == "onto exchanges")
    f = flows16()
    html = sb.render_flows(f, "FRIDAY")
    guarded(fails, "the page says 'net stablecoins off exchanges' for transfers that left",
            lambda: "net stablecoins off exchanges" in html)
    guarded(fails, "the page never says 'net stablecoins onto exchanges' for them",
            lambda: "net stablecoins onto exchanges" not in html)
    guarded(fails, "the signed amount stays -$233.2M", lambda: "-$233.2M" in html)
    import chartmaster
    guarded(fails, "the Chart Master is handed the stablecoin convention in words",
            lambda: "stablecoin_convention" in open(os.path.join(HERE, "chartmaster.py"), encoding="utf-8").read())


# ---- item 3: one seven-day figure per page -------------------------------------------------------

def week_cases(fails):
    import coinpage
    import site_build as sb
    print("3. one seven-day figure per page")
    p = pulse16()
    coins = p["movers"]["top100"]
    pos, btc = next((i + 1, c) for i, c in enumerate(coins) if c["symbol"] == "BTC")
    btc["chg_7d_pct"] = 0.08
    cm = {"date": "2026-10-16", "paragraphs": [
        "However, Bitcoin is down 2.0% over the week while Ether holds. Bitcoin sits above its 200-day average."]}
    import snapshot
    _old_snap = sb.SNAP
    sb.SNAP = snapshot.build(p, flows16())
    try:
        html = sb.render_coin_page(btc, pos, p, [], "FRIDAY, OCTOBER 16, 2026", wire=None, cm=cm,
                                   today=dt.date(2026, 10, 16))
    finally:
        sb.SNAP = _old_snap          # a test never leaves its fixture in the module the canary builds from
    head = re.search(r'<p class="cc-chg"[^>]*>(.*?)</p>', html)
    guarded(fails, "the chart header carries the readings tile's rolling 7-day figure (+0.08%), not its own series",
            lambda: head and head.group(1).startswith("+0.08%") and "over the last 7 days" in head.group(1))
    guarded(fails, "the chart carries the figure for the script, so it does not change between loads",
            lambda: 'data-chg7="0.08"' in html)
    guarded(fails, "the Chart Master sentence with 'down 2.0% over the week' is not lifted onto the page",
            lambda: "2.0% over the week" not in html)
    guarded(fails, "the Chart Master's other sentence stands, whole, without its 'However,'",
            lambda: "Bitcoin sits above its 200-day average." in html and "However, Bitcoin" not in html)
    guarded(fails, "the readings tile names its window in words (Rolling 7 days)", lambda: "Rolling 7 days" in html)
    js = open(os.path.join(HERE, "site", "assets", "coinchart.js"), encoding="utf-8").read()
    guarded(fails, "the script prints the same figure on 7D and names every window 'the last ...'",
            lambda: "data-chg7" in js and "the last 7 days" in js and "the last 24 hours" in js)
    guarded(fails, "8.3 item 2: a connective comes off a lifted first sentence",
            lambda: coinpage.lead_alone("However, Doge sits below its 200-day.") == "Doge sits below its 200-day.")


# ---- item 4: the movers list rules ---------------------------------------------------------------

def mover_cases(fails):
    import snapshot
    import site_build as sb
    print("4. the movers list rules")
    p = pulse16()
    rows = p["movers"]["top100"]
    rows[0]["price"] = 1.0
    extra = [
        {"symbol": "PYUSD", "name": "PayPal USD", "rank": 39, "price": 1.0, "chg_24h_pct": -1.2, "stablecoin": True},
        {"symbol": "NOFLAG", "name": "Some Dollar", "rank": 50, "price": 0.999, "chg_24h_pct": -1.5},
        {"symbol": "STRK", "name": "Starknet", "rank": 107, "price": 0.1, "chg_24h_pct": -9.0},
        {"symbol": "ZZZ", "name": "Zed", "rank": 80, "price": 3.0, "chg_24h_pct": -2.0},
        {"symbol": "YYY", "name": "Why", "rank": 81, "price": 2.0, "chg_24h_pct": -0.4},
    ]
    losers = snapshot.mover_rows(extra, "losers")
    syms = [r["symbol"] for r in losers]
    guarded(fails, "no stablecoin: PayPal USD (flagged) and a dollar-priced 'Dollar' coin (not flagged) are out",
            lambda: "PYUSD" not in syms and "NOFLAG" not in syms)
    guarded(fails, "rank 100 or better: #107 Starknet is out", lambda: "STRK" not in syms)
    guarded(fails, "no padding: a coin down 0.4% is not a loser; one coin qualifies, one row prints", lambda: syms == ["ZZZ"])
    guarded(fails, "gainers are the same rule (nothing qualifies from this list)", lambda: snapshot.mover_rows(extra, "gainers") == [])
    pv = snapshot.views(snap16(), pulse16(), flows16())[0]
    mv = pv["movers"]
    guarded(fails, "the view's lists obey the rules: every row ranked 100 or better, none a stablecoin",
            lambda: all(r["rank"] <= 100 and not snapshot.is_stablecoin(r) for r in mv["gainers"] + mv["losers"]))
    guarded(fails, "16 October (only 3 top-100 coins fell more than 1%): at most 3 losers, not 5",
            lambda: len(mv["losers"]) <= 3)
    html = sb.render_pulse_movers(pv, "FRIDAY")
    guarded(fails, "the page says it stops short when it does ('Only N top-100 coins fell more than 1%')",
            lambda: ("Only " in html and "more than 1%" in html) or len(mv["losers"]) == 5)
    pv["movers"]["losers"] = []
    html2 = sb.render_pulse_movers(pv, "FRIDAY")
    guarded(fails, "no loser at all: 'No top-100 coin fell more than 1% in the last 24 hours.'",
            lambda: "No top-100 coin fell more than 1% in the last 24 hours." in html2)
    row = sb._mover_rows([{"symbol": "ZZZ", "name": "Zed", "rank": 80, "price": 3.0, "chg_24h_pct": -2.0, "mcap_usd": 1e9}])
    guarded(fails, "the 24h figure is the first column after the coin, before the price",
            lambda: row.index("-2.0") < row.index("$3.00"))
    guarded(fails, "the name and the cap wait for 768 px (c-wide)", lambda: row.count("c-wide") == 2)
    guarded(fails, "the unsourced 'someone's exit' line is gone", lambda: "someone's exit" not in html and "someone&#x27;s exit" not in html)


# ---- item 5: the Top 100 does not claim to be live ------------------------------------------------

def top100_cases(fails):
    import snapshot
    import site_build as sb
    print("5. no 'live' claim on the Top 100")
    pv = snapshot.views(snap16(), pulse16(), flows16())[0]
    html = sb.render_pulse_prices(pv, "FRIDAY")
    desc = re.search(r'<meta name="description" content="(.*?)"', html, re.S).group(1)
    guarded(fails, "the description no longer says 'Live prices' or 'updated in your browser'",
            lambda: "Live prices" not in desc and "updated in your browser" not in desc)
    guarded(fails, "the page carries its time and the instant for the stale state", lambda: re.search(r'class="live-stamp" data-asof="', html))
    body = html.split("<main", 1)[1]
    guarded(fails, "no 'live' claim in the page body", lambda: not re.search(r"\blive prices\b|\bupdates live\b", body, re.I))


# ---- item 6: the stale state ----------------------------------------------------------------------

def stale_cases(fails):
    import snapshot
    import site_build as sb
    import tile
    print("6. the stale state")
    now = dt.datetime(2026, 10, 16, 21, 18, tzinfo=dt.timezone.utc)
    guarded(fails, "age_phrase: nothing within 3 hours", lambda: snapshot.age_phrase("2026-10-16T19:00:00Z", now) == "")
    guarded(fails, "age_phrase: '9 hours ago' for the 12:16 read at 9:18 PM UTC", lambda: snapshot.age_phrase("2026-10-16T12:16:53Z", now) == "9 hours ago")
    guarded(fails, "age_phrase: days past 48 hours", lambda: snapshot.age_phrase("2026-10-13T12:00:00Z", now) == "3 days ago")
    st = snapshot.stamp_et("2026-10-16T12:16:53Z")
    t = tile.render("total-cap", "$2.78T", window="every coin, 24 hours", since="Up 0.24% since yesterday's close",
                    source="CoinGecko", stamp=st)
    guarded(fails, "a tile carries the instant its stamp came from", lambda: 'data-asof="2026-10-16T12:16:53Z"' in t)
    p = pulse16()
    p["generated_utc"] = "2026-10-16T12:16:53Z"
    old = sb._build_now
    try:
        sb._build_now = lambda: dt.datetime(2026, 10, 16, 21, 18, tzinfo=dt.timezone.utc)
        strip = sb._ticker_built(p)
    finally:
        sb._build_now = old
    guarded(fails, "the ticker's stamp prints its age: 'as of 8:16 AM ET on Oct 16, 9 hours ago'",
            lambda: "9 hours ago" in strip and "8:16 AM ET on Oct 16" in strip)
    html = sb.render_pulse_prices(snapshot.views(snap16(), pulse16(), flows16())[0], "FRIDAY")
    guarded(fails, "every page loads the stale-state script", lambda: "/assets/asof.js" in html)
    js = open(os.path.join(HERE, "site", "assets", "asof.js"), encoding="utf-8").read()
    guarded(fails, "the script measures against the clock at the moment of reading and appends the age",
            lambda: "Date.now()" in js and "asof-age" in js and "is-stale" in js and "data-asof-hours" in js)
    css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read()
    guarded(fails, "a stale reading's figure dims", lambda: ".is-stale .tl-f" in css)
    fh = sb.render_flows(flows16(), "FRIDAY")
    guarded(fails, "Whale Watch's stamp carries its instant and each transfer's age is recomputed at the reading (data-ago)",
            lambda: 'class="bd-src" data-asof="2026-10-16T12:16:53Z"' in fh and 'data-ago="' in fh)
    asof_js = open(os.path.join(HERE, "site", "assets", "asof.js"), encoding="utf-8").read()
    guarded(fails, "a transfer older than 24 hours at the reading dims its row and says so",
            lambda: "data-ago" in asof_js and "outside the 24-hour window" in asof_js)
    home_src = open(os.path.join(HERE, "home.py"), encoding="utf-8").read()
    guarded(fails, "the masthead is never swapped to LIVE", lambda: "LIVE'" not in home_src.split("HOME_JS")[1])
    guarded(fails, "the tape says what is live: price live, range and chart as of the build",
            lambda: "price live" in home_src and "range and chart as of" in home_src)
    guarded(fails, "the strip says 'live' only when prices and /global have both answered",
            lambda: "liveP&&liveG" in open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read())


# ---- item 7: /today/'s direction follows the ET day -------------------------------------------------

def today_cases(fails):
    import today
    import twins_gate
    import market_pulse
    import snapshot
    print("7. /today/'s direction follows the ET day")
    pts = [100 + i * 0.1 for i in range(168)]
    guarded(fails, "et_open: the price at the last midnight Eastern, for the ET day it belongs to",
            lambda: market_pulse.et_open(pts, "2026-10-16T12:18:00.000Z") == {"open_et": 115.8, "open_et_day": "2026-10-16"})
    s = snap16()
    c = s["fields"]["coins"]["value"]["BTC"]
    c.update({"price": 82216.0, "chg_24h_pct": -2.60, "open_et": 80990.0, "open_et_day": "2026-10-16",
              "chg_et_day_pct": 1.52})
    now = dt.datetime(2026, 10, 16, 23, 30, tzinfo=dt.timezone.utc)
    ed = {"published_utc": "2026-10-16T23:10:00Z", "bottom_line": "Bitcoin fell 2.6 percent over 24 hours."}
    rec = today.compose(s, snapshot.views(s, pulse16(), flows16())[0], None, ed, None, now,
                        twins_gate.Gate(s, log_path="", quiet=True))
    guarded(fails, "rolling 24h -2.60% but +1.52% since midnight ET: the day is UP (title, direction, basis)",
            lambda: rec and rec["direction"] == "up" and rec["h1"].startswith("Why is crypto up today?")
            and rec["direction_basis"] == "et_day")
    ans = " ".join(rec["answer"]) if rec else ""
    guarded(fails, "the answer states the ET day's move and the 24-hour move, each with its window",
            lambda: "up 1.52% since midnight ET" in ans and "down 2.60%" in ans and "last 24 hours" in ans)
    guarded(fails, "the page shows both Bitcoin windows",
            lambda: "since midnight ET" in today.body_html(rec, [], "living") and "last 24 hours" in today.body_html(rec, [], "living"))
    c["open_et_day"] = "2026-10-15"
    rec2 = today.compose(s, snapshot.views(s, pulse16(), flows16())[0], None, ed, None, now,
                         twins_gate.Gate(s, log_path="", quiet=True))
    guarded(fails, "an open that belongs to another ET day is not used: rolling 24 hours, said in direction_basis",
            lambda: rec2 and rec2["direction_basis"] == "rolling_24h" and rec2["direction"] == "down")
    guarded(fails, "the whole-market line is not in the answer while its change is withheld",
            lambda: ans and "whole market" not in ans.lower())
    c["open_et_day"] = "2026-10-16"
    g = twins_gate.Gate(s, log_path="", quiet=True)
    kept = g.text("Bitcoin was rising since midnight ET, to $82,216.", "t")
    guarded(fails, "the twins gate reads 'since midnight ET' against the ET day's figure (+1.52), not the 24-hour one (-2.60)",
            lambda: kept.strip() and not g.drops)
    g = twins_gate.Gate(s, log_path="", quiet=True)
    guarded(fails, "and still drops the wrong direction for that window",
            lambda: g.text("Bitcoin was falling since midnight ET.", "t").strip() == "" and len(g.drops) == 1)
    d15 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))
    guarded(fails, "15 October's dated page: the unsupported producer-price line is off it and a visible correction names why",
            lambda: all("$940 million" not in w["line"] for w in d15["reported"]) and d15["corrections"]
            and "does not carry" in d15["corrections"][0]["text"] and d15["direction"] == "up")
    d16 = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-16-morning.json"), encoding="utf-8"))
    guarded(fails, "the contradicting whole-market figures are off the 15 and 16 October pages, each with a correction naming Bitcoin and Ether",
            lambda: d15["cap"] is None and d16["cap"] is None
            and not any("whole market" in a.lower() for a in d16["answer"])
            and "contradicted Bitcoin (up 1.48%)" in d16["corrections"][-1]["text"]
            and "contradicted Bitcoin (up 0.80%)" in d15["corrections"][-1]["text"])
    d16e = json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-16-evening.json"), encoding="utf-8"))
    guarded(fails, "the 16 October evening record (stored before the cross-check) carries no whole-market figure and says why",
            lambda: d16e["cap"] is None and "contradicted Bitcoin (down 0.61%)" in d16e["corrections"][-1]["text"])
    html = today.body_html(d15, [], "dated")
    guarded(fails, "the correction line renders on the page", lambda: "Correction, October 16, 2026." in html)


# ---- items 8 and 9, "last 1 hours", llm.py ----------------------------------------------------------

def label_cases(fails):
    import common
    import home
    import llm
    print("8. labels, the lede, the hour, llm.py")
    html = home.wire_top({"items": [{"rank": 1, "id": "c1", "line": "A line.", "links": [], "source_count": 1}]}, "")
    guarded(fails, "the home label reads 'What was reported', not 'Moving the market'",
            lambda: "What was reported" in html and "Moving the market" not in html)
    import site_build as sb
    lede = sb.render_bottom_line([]) if hasattr(sb, "render_bottom_line") else ""
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "the /bottom-line lede no longer says 'once a day'", lambda: "Once a day the desk closes" not in src
            and "Every morning and every evening the desk closes its edition" in src)
    guarded(fails, "hours_phrase: '1 hour', '2 hours', '3 days'",
            lambda: (common.hours_phrase(1), common.hours_phrase(2), common.hours_phrase(72)) == ("1 hour", "2 hours", "3 days"))
    import today
    board = today.board_rows(snap16(), {"leverage": {"assets": [{"symbol": "BTC", "liquidations": {
        "window_hours": 1, "longs_usd": 1e6, "shorts_usd": 2e6}}]}})
    guarded(fails, "the liquidation window prints 'last 1 hour', not 'last 1 hours'",
            lambda: any(r.get("window") == "last 1 hour" for r in board))
    guarded(fails, "llm: Sonnet 5.5 is sent no {type: disabled} thinking (it answers 400)", lambda: llm.thinking_param("claude-sonnet-5-5") is None)
    guarded(fails, "llm: Sonnet 5 still has thinking disabled", lambda: llm.thinking_param("claude-sonnet-5") == {"type": "disabled"})
    guarded(fails, "llm: PRICING has the three 5.5 models at their own rates",
            lambda: llm.PRICING["claude-haiku-5-5"] == (0.10, 0.50) and llm.PRICING["claude-sonnet-5-5"] == (2.0, 10.0)
            and llm.PRICING["claude-opus-5-5"] == (4.0, 20.0))


# ---- the wire's source check ------------------------------------------------------------------------

def wire_cases(fails):
    import wire
    print("9. a source check on every wire line")
    src = open(os.path.join(FX, "coindesk_2026-10-15_excerpt.txt"), encoding="utf-8").read() * 2
    line = ("Hot US producer-price data triggered nearly $940 million in crypto liquidations "
            "as Fed rate-hike bets spiked to 50%.")
    kept, cuts = wire.source_check(line, [src])
    guarded(fails, "15 October: the producer-price line (a cause and two figures its source lacks) is out",
            lambda: kept == "" and len(cuts) >= 1)
    guarded(fails, "the cut is logged with its reason", lambda: "do not carry" in cuts[0]["why"])
    good = "Nearly $483 million in bitcoin and ether futures positions were liquidated as uncertainty about the Fed's next rate decision weighed on markets."
    guarded(fails, "a line its source supports stands as written", lambda: wire.source_check(good, [src]) == (good, []))
    k2, c2 = wire.source_check("Bitcoin fell, with $900 million in liquidations as traders fled.", [src])
    guarded(fails, "the part is not the whole: a later clause with a smuggled figure is cut and the line stands",
            lambda: k2 == "Bitcoin fell as traders fled." and len(c2) == 1)
    guarded(fails, "sources not read (under 300 characters): the check does not speak", lambda: wire.source_check(line, ["short"]) == (line, []))
    guarded(fails, "a date is not a figure: 'Oct. 21' and 'Nov. 12' need no source",
            lambda: wire.source_check("Solana confirmed its Oct. 21 upgrade, activating rules Nov. 12.", [src])[1] == [])
    w = load("wire_2026-10-15T2343Z.json")
    cluster = {"id": "c011", "headline": "Nearly $1 billion in crypto bets liquidated as bitcoin, ether and XRP slide",
               "snippet": src[:400], "feed_text": src, "source": "CoinDesk", "url": "https://example.com/a",
               "corroboration": []}
    ed = {"ranked": [{"id": "c011", "wire_line": line, "source_urls": ["https://example.com/a"],
                      "source_outlets": ["CoinDesk"]}]}
    out = wire.build(ed, {"clusters": [cluster]}, {"verdicts": []}, {"stamp_utc": "t"}, "2026-10-15T23:43:00Z",
                     log=lambda *a: None)
    guarded(fails, "wire.build keeps the line off the wire, logged in 'dropped' and 'source_cuts'",
            lambda: out["items"] == [] and out["dropped"] and out["source_cuts"])
    guarded(fails, "the live wire.json no longer carries the line",
            lambda: all("$940 million" not in i["line"] for i in json.load(
                open(os.path.join(HERE, "site", "data", "wire.json"), encoding="utf-8"))["items"]))


# ---- 8.3 items 1, 3, 4, 5 -------------------------------------------------------------------------------

def carry_cases(fails):
    import snapshot
    import coinpage
    import twins_gate
    import consistency_gate
    import today
    print("10. Program 8.3's items 1 to 5")
    s = snap16()
    s["fields"]["coins"]["value"]["BTC"].update({"price": 80896.0, "low_24h": 79806.0, "high_24h": 82816.0})
    s["fields"]["week"]["value"]["BTC"]["closes"] = {"2026-10-12": 81794.0, "2026-10-13": 83115.0, "2026-10-14": 81630.0}
    lo, hi = snapshot.week_pair(s, "BTC")
    guarded(fails, "item 1: the 7D pair stays the closes' pair (one pair on the home tape and the coin page)",
            lambda: (lo, hi) == (81630.0, 83115.0))
    p2 = pulse16()
    _sbm = __import__("site_build")
    _prev = _sbm.SNAP
    _sbm.SNAP = snapshot.build(p2, flows16())
    coin_html = __import__("site_build").render_coin_page(
        next(c for c in p2["movers"]["top100"] if c["symbol"] == "BTC"), 1, p2, [], "FRIDAY", wire=None, cm={},
        today=dt.date(2026, 10, 16))
    _sbm.SNAP = _prev
    guarded(fails, "item 1: the coin page words the pair as closes, so a 7D low above today's low is not a false 'low'",
            lambda: "7D high close" in coin_html and "7D low close" in coin_html)
    guarded(fails, "item 1: the chart script words them the same way",
            lambda: "7D closing" in open(os.path.join(HERE, "site", "assets", "coinchart.js"), encoding="utf-8").read())
    import home
    guarded(fails, "item 1: the tape's closes say they are closes ('7D LOW CLOSE')",
            lambda: "7D LOW CLOSE" in home.tape_chart({"closes": {"2026-10-12": 1, "2026-10-13": 2, "2026-10-14": 1.5}}))
    w = {"line": "x", "source_count": 2, "links": [
        {"url": "https://decrypt.co/1", "outlet": "Decrypt"}, {"url": "https://decrypt.co/2", "outlet": "Decrypt"},
        {"url": "https://bitcoinmagazine.com/3", "outlet": "Bitcoin Magazine"}]}
    out = coinpage.stories_html([w], lambda x: x, lambda x: "")
    guarded(fails, "item 3: an outlet is listed once and counted once ('2 sources: Decrypt, Bitcoin Magazine')",
            lambda: out.count(">Decrypt<") == 1 and "2 sources" in out)
    snap = snap16()
    snap["fields"]["stablecoin_float"] = {"value": {"change_30d_pct": 0.60, "total_usd": 3e11}}
    sent = ("Separately, the board shows $150,019,159 in USDT moving off Bitfinex in the same window, a "
            "stablecoin outflow that the board's convention reads as buying power leaving.")
    g = twins_gate.Gate(snap, log_path="", quiet=True)
    kept = g.text(sent, "the Edition")
    guarded(fails, "item 4: USDT moving off an exchange is not bound to the 30-day stablecoin float (kept)",
            lambda: kept.strip() == sent and not g.drops)
    g2 = twins_gate.Gate(snap, log_path="", quiet=True)
    g2.text("The stablecoin float had a net outflow of $2B this month.", "the Edition")
    guarded(fails, "item 4: a real wrong claim about the float is still dropped",
            lambda: len(g2.drops) == 1)
    long = ("The stablecoin float had a net outflow of $2B this month, " + "with traders watching every venue closely, " * 6
            + "and nothing else changed.")
    g3 = twins_gate.Gate(snap, log_path="", quiet=False)
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        g3.text(long, "the Edition")
    guarded(fails, "item 4: the run log and the drop keep the whole dropped sentence (the ledger cut it at 70, the run log at 140)",
            lambda: len(g3.drops) == 1 and g3.drops[0]["dropped"] == long and "nothing else changed" in buf.getvalue())
    guarded(fails, "item 4: the ops ledger keeps the whole sentence",
            lambda: '[:70]' not in open(os.path.join(HERE, "scripts", "ops_ledger.py"), encoding="utf-8").read())
    lines = consistency_gate.announce_edition_withheld(
        ["story:2026-10-15-evening-brief"], {"story:2026-10-15-evening-brief": "site/content/2026-10-15-evening-brief.json"},
        summary_path=os.devnull)
    guarded(fails, "item 5: a withheld Edition prints one visible line on the run: 'Edition withheld, slot still open'",
            lambda: len(lines) == 1 and lines[0].startswith("Edition withheld, slot still open")
            and "evening Edition for 2026-10-15" in lines[0])
    guarded(fails, "item 5: a withheld Chart Master is not an Edition line",
            lambda: consistency_gate.announce_edition_withheld(["chart-master"], {"chart-master": "site/data/chartmaster.json"},
                                                              summary_path=os.devnull) == [])
    # today.py: the slot comes from the read, and a numbers-only page takes the clock's slot
    now = dt.datetime(2026, 10, 16, 23, 15, tzinfo=dt.timezone.utc)          # 7:15 PM ET, no Edition yet
    old_ed = {"published_utc": "2026-10-15T23:45:00Z", "bottom_line": "Bitcoin rose."}
    s2 = snap16()
    s2["fields"]["coins"]["value"]["BTC"].update({"chg_24h_pct": 1.48})
    rec = today.compose(s2, pulse16(), None, old_ed, None, now, twins_gate.Gate(s2, log_path="", quiet=True))
    guarded(fails, "item 5: at 7:15 PM with no Edition, the numbers-only page is filed as EVENING (flagged fallback), never as a morning",
            lambda: rec and rec["fallback"] is True and rec["slot"] == "evening")
    now_am = dt.datetime(2026, 10, 16, 12, 30, tzinfo=dt.timezone.utc)       # 8:30 AM ET
    rec_am = today.compose(s2, pulse16(), None, old_ed, None, now_am, twins_gate.Gate(s2, log_path="", quiet=True))
    guarded(fails, "item 5: at 8:30 AM with no read, the same page is filed as the morning", lambda: rec_am and rec_am["slot"] == "morning")


def unit():
    fails = []
    group(fails, "1 (whole market)", market_cases)
    group(fails, "2 (whale sign)", whale_cases)
    group(fails, "3 (one seven-day figure)", week_cases)
    group(fails, "4 (movers)", mover_cases)
    group(fails, "5 (Top 100)", top100_cases)
    group(fails, "6 (stale state)", stale_cases)
    group(fails, "7 (ET day)", today_cases)
    group(fails, "8 (labels)", label_cases)
    group(fails, "9 (wire source check)", wire_cases)
    group(fails, "10 (8.3 items)", carry_cases)
    return fails


def main():
    fails = unit()
    print("\nSPRINT 9.1:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
