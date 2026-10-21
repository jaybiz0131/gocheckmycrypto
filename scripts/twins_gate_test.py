#!/usr/bin/env python3
"""The twins gate stops cutting true sentences (Program 7, Sprint 7.3, item 0 and item 1).

Jack's rulings of 13 October 2026: (1) a true sentence must never be cut and a false pairing
must never print; the gate catches wrong claims, it does not thin out right ones. (2) a
sentence the gate cannot parse is not dropped silently: it is logged with the reason and
the drop is counted in the night's report.

  python3 scripts/twins_gate_test.py          # prints every case; exit 1 on any failure

THE SEVEN FIXTURES are the seven drops of 9 and 10 October, all wrong (docs/HANDOFF.md,
section 3, as it stood on 12 October). Six are VERBATIM: the full text is in `wrap-status.json`
(key `twins_gate`) inside the `crypto-review-queue` artifact of Actions runs 38003059379 (9
October) and 38094093202 (10 October), and the run log prints the same sentence cut at 140
characters. The seventh, the narrative line (F7), is not in any artifact (the table's line
replaced it); the log keeps its first 140 characters and F7's tail is RECONSTRUCTED, marked
[TAIL RECONSTRUCTED]. Each fails on main with the reason the log printed, and passes on the
branch.

THE FIVE TRUE NEGATIVES are sentences the gate must still drop. The record holds no gate
drop that was RIGHT since 6 October (every drop logged on 7, 9 and 10 October was judged
wrong), so none is a recorded drop. TN1 is a real wrong figure from the 6 October Edition
(docs/HANDOFF-2026-10-06.md line 116) and TN2 is the real Oct 7 failure class (the stale
Chart Master read, positive ETF flows against -66.9M); the sentence text of TN2 to TN5 is
SYNTHETIC and labeled so.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import twins_gate as tg                                     # noqa: E402
import narrative as nar                                     # noqa: E402


def snap_for(day):
    return json.load(open(os.path.join(HERE, "fixtures", "twins", f"snapshot_{day}.json"),
                          encoding="utf-8"))


def gate(day_or_snap):
    snap = snap_for(day_or_snap) if isinstance(day_or_snap, str) else day_or_snap
    return tg.Gate(snap, log_path=os.path.join(tempfile.mkdtemp(prefix="tg-test-"), "tg.json"),
                   quiet=True)


# (id, day, surface, sentence, note)
KEEP = [
    ("F1", "2026-10-09", "bottom line",
     "The desk's ETF flow board shows bitcoin funds posted a net outflow of $244.1 million on "
     "October 8, 2026, and a net outflow of $510.1 million over the last five sessions, while "
     "the Whale Watch board shows $119,468,889 in bitcoin moving onto exchanges over the last "
     "48 hours, continuing four straight weeks of net onto-exchange bitcoin flow.",
     "ETF outflow read as whale net (misattributed). [verbatim from wrap-status.json]"),
    ("F2", "2026-10-09", "body 1",
     "That is not a contradiction so much as a market that rallied intraday within a choppier "
     "multi-week stretch, and it means any single word like \"rising\" or \"falling\" for "
     "bitcoin today would be incomplete without naming which window it describes.",
     "a quoted word is not a claim. [verbatim from wrap-status.json]"),
    ("F3", "2026-10-09", "body 6",
     "Taken together, the tape shows a market with greed-labeled sentiment and a positive "
     "daily bitcoin print sitting alongside weekly ETF outflows and sustained onto-exchange "
     "bitcoin flows, boards that do not tell the same short-term story and are reported here "
     "as both true in their own windows.",
     "two windows in one sentence. [verbatim from wrap-status.json]"),
    ("F4", "2026-10-10", "dek",
     "ETF flows remain split between the day's modest inflow and a five-session net outflow.",
     "'five-session' is a window. [verbatim from wrap-status.json]"),
    ("F5", "2026-10-10", "bottom line",
     "Funding rates on OKX stayed negative for bitcoin and ethereum while Solana shorts took "
     "heavy liquidation hits.",
     "'funding' beats the coin named after it. [verbatim from wrap-status.json]"),
    ("F6", "2026-10-10", "body 3",
     "Bitcoin ETF flows showed an inflow of $21.1 million on October 9, but the five-session "
     "net stands at an outflow of $678.9 million.",
     "'five-session' is a window. [verbatim from wrap-status.json]"),
    ("F8", "2026-10-13", "body paragraph 4",
     "Ethereum ETFs show the same pattern: a $16.7 million net inflow on Oct 13 against a "
     "five-session net outflow of $358.2 million.",
     "FOUND LIVE at 7:17 PM ET 13 Oct by the old gate, the eighth wrong drop: read against "
     "Bitcoin's ETF net (+6.7M) with a five-session window. [verbatim from run 38482566029's log]"),
    ("F7", "2026-10-10", "narrative line",
     "Bitcoin gained 0.53% on the day while falling 2.3% on the week as whale deposits to "
     "exchanges hit weekly highs; Saturday's tape held steady and the news is mixed.",
     "'falling' is a sign word. [TAIL RECONSTRUCTED after \"Saturday's tape held steady\"]"),
]

# sentences the gate must STILL drop: (id, snapshot day or dict, sentence, note)
PLUS_WEEK = {"stamp_utc": "2026-10-12T23:10:00Z", "fields": {
    "coins": {"value": {"BTC": {"price": 100000.0, "chg_24h_pct": 0.4}}}},
    "series": {"value": {"BTC": {"through": "2026-10-11", "chg_7d_pct": 2.30,
                                 "chg_30d_pct": 5.0}}}}
DROP = [
    ("TN1", "6oct", "Bitcoin is up 1.3% on the week and up 8.3% on the month.",
     "REAL: the 6 October Edition's figures from the spark; the series said 2.75% and 7.45%"),
    ("TN2", "7oct", "Spot ETF flows were positive on the day.",
     "SYNTHETIC text of the real 7 October class: the stale read said positive, the snapshot "
     "-66.9M"),
    ("TN3", "2026-10-09", "Bitcoin is rising over seven days.",
     "SYNTHETIC: a week claim is checked against the series (-3.72%)"),
    ("TN4", "2026-10-10", "Funding rates stayed negative for bitcoin and solana.",
     "SYNTHETIC: 'funding' binds, and every coin named is checked (Solana is positive)"),
    ("TN5", PLUS_WEEK, "Bitcoin is falling 2.3% on the week.",
     "SYNTHETIC: falling 2.3% means -2.3; the series says +2.30, so the sentence is wrong"),
    ("TN8", "2026-10-10", "Ether ETF flows turned positive on the day.",
     "SYNTHETIC: an Ether ETF sentence is read against the ETH net (-56.1M on 9 Oct), not Bitcoin's"),
    ("TN6", "2026-10-10", "Bitcoin was rising on the week.",
     "SYNTHETIC: 'rising' on the week against the series' -2.30"),
    ("TN7", "2026-10-09", "The index said \"ETF flows turned positive\" on the day.",
     "SYNTHETIC: a quoted CLAUSE (four words) is still a claim; ETF net is -244.1M"),
]

UNPARSED = [
    ("U1", "2026-10-09", "ETF flows turned \"positive on the day.",
     "an odd number of quotation marks around a direction word"),
]

results = []


def check(cid, ok, line):
    results.append((cid, ok))
    print(f"{'ok  ' if ok else 'FAIL'} {cid}: {line}")


def main():
    print("== the seven wrong drops of 9 and 10 October (must be KEPT)")
    for cid, day, surface, s, note in KEEP:
        g = gate(day)
        out = g.text(s, surface)
        check(cid, out == s and not g.drops,
              f"{surface}: {'kept' if out == s else 'DROPPED: ' + (g.drops[0]['why'] if g.drops else '')}"
              f" | {note}")

    print("== an Ether ETF sentence is read against the ETH net")
    g = gate("2026-10-10")
    s = ("Ether ETFs saw an outflow of $56.1 million on October 9 while Bitcoin ETFs saw an "
         "inflow of $21.1 million.")
    out = g.text(s, "t")
    check("E1", out == s, f"{'kept' if out == s else 'DROPPED: ' + g.drops[0]['why']} | both true on "
                          f"9 Oct (ETH -56.1M, BTC +21.1M); main reads the Ether outflow against Bitcoin's net")

    print("== found by the replay: a true sentence the first cut of the fix would have cut")
    g = gate("2026-10-09")
    s = ("No desk stories published today, but the boards show a market pulling in two "
         "directions: bitcoin up on the day while weekly ETF outflows and exchange inflows "
         "continue.")
    out = g.text(s, "dek")
    check("R1", out == s, f"{'kept' if out == s else 'DROPPED: ' + g.drops[0]['why']} | the 9 "
                          f"October dek: 'exchange inflows' are the whale board's (-119M, onto "
                          f"exchanges), not the ETF net's")
    g = gate("2026-10-09")
    s = "Whale inflows to exchanges rose while ETF outflows continued."
    out = g.text(s, "t")
    check("R2", out == s, f"{'kept' if out == s else 'DROPPED: ' + g.drops[0]['why']}")

    print("== true negatives (must still be DROPPED)")
    for cid, day, s, note in DROP:
        g = gate(day_snap(day) if day in ("6oct", "7oct") else day)
        out = g.text(s, "test")
        check(cid, out == "" and len(g.drops) == 1,
              f"{'dropped' if out == '' else 'KEPT'}: {s} | {note}")

    print("== the five causes, each alone")
    g = gate("2026-10-10")
    for name, s in (("hyphen windows: seven-day ETF", "ETF flows were an outflow on a seven-day basis."),
                    ("hyphen windows: 24-hour", "Funding stayed negative over 24-hour trading.")):
        out = g.text(s, "t")
        check("C1 " + name, out == s, f"{'kept' if out == s else 'DROPPED'}")
    for name, day, s in (("quoted word", "2026-10-09", 'Do not read "falling" into one weak day.'),
                         ("sign word", "2026-10-10", "Bitcoin is falling 2.3% on the week.")):
        g = gate(day)
        out = g.text(s, "t")
        check("C4/5 " + name, out == s, f"{'kept' if out == s else 'DROPPED'}")

    g = gate("2026-10-09")
    s = "Bitcoin is rising on a seven-day basis."
    out = g.text(s, "t")
    check("C1 hyphen window is CHECKED", out == "" and len(g.drops) == 1,
          f"{'dropped (series -3.72%)' if out == '' else 'KEPT'}: {s} (main kept it: the "
          f"hyphen hid the window)")

    print("== a sentence the gate cannot parse is logged, with the reason, and counted")
    for cid, day, s, note in UNPARSED:
        g = gate(day)
        out = g.text(s, "t")
        d = g.drops[0] if g.drops else {}
        check(cid, out == "" and d.get("kind") == "unparsed" and "quot" in d.get("why", "")
              and getattr(g, "unparsed", 0) == 1,
              f"{'dropped as unparsed' if d.get('kind') == 'unparsed' else 'NOT flagged'} "
              f"({d.get('why', '')}) | {note}")
    g = gate("2026-10-09")
    g._direction = lambda s: 1 / 0
    try:
        out = g.text("Bitcoin was positive today.", "t")
    except ZeroDivisionError:
        out = "CRASHED"          # main: a check that raises takes the whole stage down
    d = g.drops[0] if g.drops else {}
    check("U2", out == "" and d.get("kind") == "unparsed" and "ZeroDivisionError" in d.get("why", ""),
          f"a check that raises is an unparsed drop ({d.get('why', '')})")
    g.save()
    saved = json.load(open(g.log_path, encoding="utf-8"))
    check("U3", (saved.get("counts") or {}).get("unparsed") == 1
          and (saved.get("counts") or {}).get("wrong") == 0,
          f"the saved log counts the drop: {saved.get('counts')}")

    print("== item 1: a direction pairs with a driver only when the driver's sign supports it")
    base = {"stamp_utc": "x", "fear_greed": 50, "fear_greed_band": "Neutral"}
    cases = [
        ("higher + inflows", 0.93, 244.1, "Bitcoin is drifting higher on spot ETF inflows"),
        ("lower + outflows", -1.2, -244.1, "Bitcoin is drifting lower on spot ETF outflows"),
        ("higher + outflows (9 Oct)", 0.93, -244.1,
         "Bitcoin is drifting higher while spot ETFs saw outflows"),
        ("lower + inflows", -1.2, 212.4, "Bitcoin is drifting lower while spot ETFs saw inflows"),
        ("flat + outflows", 0.1, -5.0, "Bitcoin is holding flat while spot ETFs saw outflows"),
        ("flat + inflows", -0.2, 5.0, "Bitcoin is holding flat while spot ETFs saw inflows"),
    ]
    for name, p, e, want in cases:
        r = dict(base, btc_24h_pct=p, etf_net_usd_m=e)
        got = nar._tape_clause(r)
        check("I1 " + name, got == want, f"{got!r}" + ("" if got == want else f" (want {want!r})"))
    # and the neutral clause passes the gate it will meet (the Edition's table line)
    g = gate("2026-10-09")
    r = dict(base, btc_24h_pct=0.93, etf_net_usd_m=-244.1)
    ln = nar.table_line(r, [])
    check("I1 gate", g.text(ln, "t") == ln and not g.drops, f"the 9 October table line holds the "
                                                           f"gate: {ln!r}")

    print("== the ledger row carries the night's drops and their reasons")
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    import ops_ledger as ol
    g = gate("2026-10-09")
    g._direction = lambda s: 1 / 0
    try:
        g.text("Bitcoin was positive today.", "the Brief's bottom line")
    except ZeroDivisionError:
        pass                     # main: the check's crash is not caught
    g.save()
    tf = ol.twins_fields(g.log_path)
    check("L1", tf.get("twins_unparsed") == 1 and tf.get("twins_drops") == 0
          and tf.get("twins_log") and tf["twins_log"][0]["k"] == "unparsed"
          and "ZeroDivisionError" in tf["twins_log"][0]["why"], f"{tf}")
    check("L2", ol.twins_fields("/nonexistent/twins-gate.json") == {},
          "no gate log, no fields (a run the gate never touched)")

    print("== item 2.3: the Board's Whale tags")
    import wire
    for cid, text, want in (
            ("W1 L2 shutdown", "Base-built L2 Zora Network shuts down and winds down its chain", ""),
            ("W2 bank custody approval", "OCC approves first national bank custody charter for "
                                         "digital assets", ""),
            ("W3 exchange still reads", "Exchange X pauses withdrawals after wallet incident",
             "Whale flows"),
            ("W4 exchange shutdown still reads", "Bitmex shuts down its spot market",
             "Whale flows")):
        got = wire.board_reading(text)
        check(cid, got == want, f"{text!r} -> {got!r}")

    print("== item 2.4: a coin whose vesting page the desk cannot read shows no unlock line")
    import datetime
    import coinpage
    for sym, gid in (("HYPE", "hyperliquid"), ("WBT", "whitebit"), ("RAIN", "rain")):
        out = coinpage.unlock_line({"symbol": sym, "gecko_id": gid}, datetime.date(2026, 10, 13),
                                   lambda s: s, lambda d: d)
        check("N-" + sym, out == "", f"{sym}: {out!r} (data/calendar/unlocks.json: page not "
                                     f"readable from the desk; read again 13 October: HTTP 403)")

    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)} of {len(results)} cases hold" +
          (f"; FAILED: {', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


def day_snap(day):
    """The 6 and 7 October fixture snapshots, built from the figures the record names."""
    if day == "6oct":
        return {"stamp_utc": "2026-10-06T23:10:00Z", "fields": {
            "coins": {"value": {"BTC": {"price": 100000.0, "chg_24h_pct": 0.1}}}},
            "series": {"value": {"BTC": {"through": "2026-10-05", "chg_7d_pct": 2.75,
                                         "chg_30d_pct": 7.45}}}}
    return {"stamp_utc": "2026-10-07T23:10:00Z", "fields": {
        "coins": {"value": {"BTC": {"price": 100000.0, "chg_24h_pct": -2.77}}},
        "etf_flows": {"value": {"btc": {"latest_net_usd_m": -66.9, "latest_date": "2026-10-06"}}}}}


if __name__ == "__main__":
    sys.exit(main())
