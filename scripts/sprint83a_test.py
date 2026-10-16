#!/usr/bin/env python3
"""Program 8, Sprint 8.3 Part A: the fix list (Jack, 15 and 16 October 2026). Part B, the share loop, is held.

  1. The coin chart runs to the current reading and its 7D high and low match it.
  2. Chart Master's read on a coin page lifts whole sentences only (never one that opens on "However,").
  3. A wire item's sources are listed once per outlet and counted as listed.
  4. The twins gate does not bind "outflow" in a sentence about USDT leaving an exchange to the stablecoin
     float; the dropped sentence is logged whole.
  5. The consistency gate says, once and visibly, that an Edition was withheld and the slot is still open;
     an evening run never stores a morning record.

  python3 scripts/sprint83a_test.py
Each case catches its own exceptions, so origin/main prints FAIL lines instead of crashing.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


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


# ---- 1. the chart ------------------------------------------------------------------------------

CLOSES = {"2026-10-09": 82481.93, "2026-10-10": 82978.3, "2026-10-11": 83430.99, "2026-10-12": 82508.64,
          "2026-10-13": 83457.39, "2026-10-14": 81630.0, "2026-10-15": 82350.63}


def week_snap(price):
    return {"fields": {"coins": {"value": {"BTC": {"price": price}}},
                       "week": {"value": {"BTC": {"closes": dict(CLOSES)}}}}}


def chart_cases(fails):
    print("1. the chart runs to the current reading")
    import snapshot
    lo, hi = snapshot.week_pair(week_snap(80896), "BTC")
    guarded(fails, "price $80,896 under every close: the 7D low is the reading, not $81,630", lambda: lo == 80896 and hi == 83457.39)
    lo, hi = snapshot.week_pair(week_snap(84000), "BTC")
    guarded(fails, "price over every close: the 7D high is the reading", lambda: lo == 81630.0 and hi == 84000)
    lo, hi = snapshot.week_pair(week_snap(82000), "BTC")
    guarded(fails, "price inside the range: the pair is the closes' own, unchanged", lambda: (lo, hi) == (81630.0, 83457.39))
    guarded(fails, "no price reading: the closes' own pair", lambda: snapshot.week_pair({"fields": {"week": {"value": {"BTC": {"closes": dict(CLOSES)}}}}}, "BTC") == (81630.0, 83457.39))
    import site_build as sb
    sb.SNAP = week_snap(80896)
    c = {"symbol": "BTC", "name": "Bitcoin", "gecko_id": "bitcoin", "price": 80896}
    html = sb.render_coin_chart(c, "Bitcoin", "bitcoin", [82000, 81800, 81630, 81000])
    m = re.search(r'data-lo7="([\d.]+)" data-hi7="([\d.]+)"', html)
    guarded(fails, "the chart's data-lo7 and data-hi7 hold the price", lambda: m and float(m.group(1)) <= 80896 <= float(m.group(2)))
    guarded(fails, "the caption's '7D low' is not above the price it sits beside",
            lambda: "7D low $80,896" in html.replace(",", ",") and "81,630" not in html)
    import coinpage
    run = coinpage.run_to_reading([82000, 81800, 81630, 81000], 80896)
    guarded(fails, "the fallback series ends on the current reading", lambda: run[-1] == 80896 and run[:4] == [82000, 81800, 81630, 81000])
    guarded(fails, "a series already ending on the reading is not doubled", lambda: coinpage.run_to_reading([1, 2, 3], 3) == [1, 2, 3])


# ---- 2. Chart Master: whole sentences ----------------------------------------------------------

def cm_cases(fails):
    print("2. Chart Master's read lifts whole sentences")
    import coinpage
    c = {"name": "Bitcoin", "symbol": "BTC"}
    cm = {"date": "2026-10-15", "data_only": False, "paragraphs": [
        "Bitcoin is down 2.1 percent on the day. However, Bitcoin holds above its 200-day average. "
        "Bitcoin's RSI reads 44, between oversold and overbought. But Bitcoin is still off its high. "
        "Meanwhile Bitcoin's funding stays calm."]}
    s = coinpage.coin_sentences(c, cm)
    guarded(fails, "a sentence opening on 'However,' is not lifted", lambda: not any(x.startswith("However") for x in s))
    guarded(fails, "'But' and 'Meanwhile' openers are not lifted either", lambda: not any(re.match(r"(But|Meanwhile)\b", x) for x in s))
    guarded(fails, "the whole sentences stand, in the read's order",
            lambda: s == ["Bitcoin is down 2.1 percent on the day.", "Bitcoin's RSI reads 44, between oversold and overbought."])
    cm2 = {"date": "2026-10-15", "data_only": False, "paragraphs": ["However, Bitcoin holds above its 200-day average."]}
    guarded(fails, "a comparative opener ('More worrying is...', 15 October's read) is not lifted either",
            lambda: not coinpage.whole_sentence("More worrying is the concentration in Bitcoin.")
            and coinpage.whole_sentence("Moreover is not the word; Bitcoin is steady.") is False
            and coinpage.whole_sentence("Morning reads show Bitcoin steady."))
    guarded(fails, "a read whose only Bitcoin sentence is a dependent one lifts nothing (the levels card follows)",
            lambda: coinpage.coin_sentences(c, cm2) == [])
    guarded(fails, "a fragment that starts lower-case, or has no end, is not a whole sentence",
            lambda: not coinpage.whole_sentence("it then fell.") and not coinpage.whole_sentence("Bitcoin rose")
            and coinpage.whole_sentence("Bitcoin rose 2 percent."))


# ---- 3. sources --------------------------------------------------------------------------------

def sources_cases(fails):
    print("3. a wire item's sources are listed once per outlet")
    import coinpage
    w = {"line": "Russia's Central Bank confirmed a ban.", "source_count": 2, "primary": False,
         "reported_utc": "2026-10-15T20:31:00Z",
         "links": [{"url": "https://d.example/a", "outlet": "Decrypt"}, {"url": "https://d.example/b", "outlet": "Decrypt"},
                   {"url": "https://bm.example/c", "outlet": "Bitcoin Magazine"}]}
    esc = lambda t: str(t)
    html = coinpage.stories_html([w], esc, lambda u: "4:31 PM ET on Oct 15")
    guarded(fails, "Decrypt is listed once", lambda: html.count(">Decrypt<") == 1 and html.count("Bitcoin Magazine") == 1)
    guarded(fails, "the count is the outlets listed ('2 sources: Decrypt, Bitcoin Magazine')", lambda: "2 sources: " in html)
    w1 = dict(w, source_count=3, links=[{"url": "https://a/x", "outlet": "CoinDesk"}])
    guarded(fails, "an item whose links name fewer outlets than the wire counted keeps the wire's count, never inflated",
            lambda: "3 sources" in coinpage.stories_html([w1], esc, lambda u: ""))


# ---- 4. the twins gate -------------------------------------------------------------------------

USDT = ("Separately, the board shows $150,019,159 in USDT moving off Bitfinex in the same window, a stablecoin "
        "movement the board's convention treats as an outflow from the exchange.")


def gate_cases(fails):
    print("4. the twins gate and the 15 October 7:49 PM drop")
    import twins_gate
    s = json.load(open(os.path.join(HERE, "fixtures", "twins", "snapshot_2026-10-13.json"), encoding="utf-8"))
    g = twins_gate.Gate(s, log_path="", quiet=True)
    out = g.text(USDT, "the Brief's body paragraph 4", dollars=False)
    guarded(fails, "USDT leaving an exchange is not a claim about the stablecoin float: the sentence stands", lambda: out == USDT and not g.drops)
    g2 = twins_gate.Gate(s, log_path="", quiet=True)
    wrong = "Stablecoin supply saw an outflow over the month."
    guarded(fails, "a real claim about the float against its sign is still dropped", lambda: g2.text(wrong, "t", dollars=False) == "" and len(g2.drops) == 1)
    g3 = twins_gate.Gate(s, log_path="", quiet=True)
    long_s = "Stablecoin supply saw an outflow over the month, " + "with a long tail of words that follows. " * 8
    g3.text(long_s, "t", dollars=False)
    guarded(fails, "a dropped sentence is logged whole, not cut at 140 characters", lambda: g3.drops and g3.drops[0]["dropped"].startswith("Stablecoin supply") and len(g3.drops[0]["dropped"]) > 300)
    src = open(os.path.join(HERE, "scripts", "ops_ledger.py"), encoding="utf-8").read()
    guarded(fails, "the ops ledger keeps up to 400 characters of a dropped sentence (it kept 70)", lambda: "[:70]" not in src and re.search(r"\[:\s*4\d\d\]", src))


# ---- 5. the withheld Edition, the evening record ------------------------------------------------

def withhold_cases(fails):
    print("5. a withheld Edition says so; an evening run stores no morning record")
    import consistency_gate as cg
    line = cg.edition_withheld_line("story:evening-brief-2026-10-15")
    guarded(fails, "an Edition withheld names itself and says the slot is still open and will be served on the next dispatch",
            lambda: "Edition withheld" in line and "slot is still open" in line and line.startswith("::warning::"))
    guarded(fails, "a withheld Chart Master or story is not an Edition and prints no such line",
            lambda: cg.edition_withheld_line("chart-master") == "" and cg.edition_withheld_line("story:some-story") == "")
    src = open(os.path.join(HERE, "consistency_gate.py"), encoding="utf-8").read()
    guarded(fails, "_quarantine prints it when it withholds", lambda: "edition_withheld_line(victim)" in src)
    import datetime as dt
    import today
    ET = today.ET
    evening = dt.datetime(2026, 10, 15, 19, 15, tzinfo=ET).astimezone(dt.timezone.utc)
    morning = dt.datetime(2026, 10, 16, 8, 18, tzinfo=ET).astimezone(dt.timezone.utc)
    rec = {"slot": "morning", "fallback": True, "date_et": "2026-10-15"}
    ok_e, why_e = today.storable(rec, evening)
    ok_m, _ = today.storable(rec, morning)
    guarded(fails, "7:15 PM, no Edition today: the fallback morning record is NOT stored, and says why",
            lambda: not ok_e and "slot" in why_e)
    guarded(fails, "8:18 AM, the read fell back: the honest fallback morning record is still stored (8.1)", lambda: ok_m)
    guarded(fails, "a real evening record at 7:49 PM is stored", lambda: today.storable({"slot": "evening", "fallback": False}, evening)[0])


def spark_cases(fails):
    print("6. a row line that draws flat is tagged flat (found by the canary on 16 October, row 60, ALGO)")
    import coinpage
    algo = [0.118754] + [0.109112, 0.132875, 0.12, 0.125] * 6 + [0.118769]        # +0.013%, range 0.109 to 0.133
    h = coinpage.row_spark(algo)
    pts = [tuple(map(float, p.split(","))) for p in re.search(r'points="([^"]+)"', h).group(1).split()]
    drawn_flat = pts[0][1] == pts[-1][1]
    guarded(fails, "the case draws flat at one decimal (the premise)", lambda: drawn_flat)
    guarded(fails, "so its tag is flat, not up", lambda: 'data-dir="flat"' in h and 'class="rs-l flat"' in h)
    up = coinpage.row_spark([1, 2, 3, 4, 5])
    guarded(fails, "a line that visibly rises is still up", lambda: 'data-dir="up"' in up)


def unit():
    fails = []
    group(fails, "1 (chart)", chart_cases)
    group(fails, "2 (Chart Master)", cm_cases)
    group(fails, "3 (sources)", sources_cases)
    group(fails, "4 (twins gate)", gate_cases)
    group(fails, "5 (withheld Edition)", withhold_cases)
    group(fails, "6 (row line)", spark_cases)
    return fails


def main():
    fails = unit()
    print("\nSPRINT 8.3 PART A:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
