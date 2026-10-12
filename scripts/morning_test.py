#!/usr/bin/env python3
"""The fixture morning (Program 7, Sprint 7.2): Tuesday 13 October 2026, 8:30 AM ET.

Last night's Edition is Monday's evening Brief. Case A: the morning read ran at 8:17 AM, so
the Brief card must read "THE BRIEF · TUESDAY MORNING", carry the read, quote no change and
name the real next slot. Case B: it did not run, so the card keeps Monday's Brief and says
"Last night's Brief" with its time. On main, case A shows last night's Brief at 8:30 AM.

  python3 scripts/morning_test.py          # prints every case; exit 1 on any failure
"""
import datetime as dt
import inspect
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

NOW = dt.datetime(2026, 10, 13, 12, 30, tzinfo=dt.timezone.utc)          # 8:30 AM EDT
ED = {"slug": "2026-10-12-evening-brief", "date": "2026-10-12",
      "title": "The Evening Brief: Whales moved onto exchanges as the wire stayed quiet",
      "published_utc": "2026-10-12T23:16:21Z"}
MORNING = {"date_et": "2026-10-13", "slot": "morning", "published_utc": "2026-10-13T12:17:04Z",
           "published_et": "8:17 AM ET on Oct 13",
           "headline": "The wire opens on a Treasury stablecoin rule and a quiet Board",
           "sentences": ["The wire's top line this morning is a Treasury proposal on stablecoin reserves, "
                         "carried by four outlets.",
                         "The Board shows Fear & Greed in the greed band and funding calm."],
           "line": "The tape is calm and the news is mostly regulation."}


def fixtures():
    sys.path.insert(0, HERE)
    import snapshot as s

    def L(n):
        return json.load(open(os.path.join(HERE, "fixtures", "home", n), encoding="utf-8"))
    snap = L("snapshot_from_2026-10-06_files.json")
    return snap, L("narrative.json"), L("wire.json")


def card(h, narr, snap, morning):
    ps = inspect.signature(h.narrative_band).parameters
    if "morning" in ps:
        return h.narrative_band(narr, snap, ED, NOW, morning=morning)
    return h.narrative_band(narr, snap, ED, NOW)               # main: it cannot take one


def check(cond, fails, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def text(html):
    return re.sub(r"<[^>]+>", " ", html)


def main():
    import home as h
    snap, narr, wire = fixtures()
    fails = []
    print("A. the morning read ran (8:17 AM), the page is built at 8:30 AM")
    a = card(h, narr, snap, MORNING)
    print("   card:", " ".join(text(a).split())[:260])
    check("THE BRIEF · TUESDAY MORNING" in a, fails, "the eyebrow names Tuesday morning")
    check("MONDAY EVENING" not in a, fails, "the card is not last night's Brief")
    check(MORNING["headline"] in a and MORNING["sentences"][0] in a and MORNING["line"] in a,
          fails, "the headline, the sentences and the narrative line are on the card")
    check("Next Brief tonight at 7:08 PM ET" in a, fails, "the next slot is tonight at 7:08 PM ET")
    check(not re.search(r"\d\s*(%|percent)", text(a)), fails, "the card quotes no change")
    print("B. the morning run fell back, the page is built at 8:30 AM")
    b = card(h, narr, snap, None)
    print("   card:", " ".join(text(b).split())[:260])
    check("MONDAY EVENING" in b, fails, "the card keeps Monday's Brief and names it")
    check("Last night's Brief, 7:16 PM ET" in b, fails, "it says Last night's Brief with its time")
    check("Next Brief tonight at 7:08 PM ET" in b, fails, "the next slot is tonight at 7:08 PM ET")
    print("C. clocks")
    for iso, want in (("2026-10-13T11:00:00", "this morning at 8:15 AM ET"),
                      ("2026-10-13T23:30:00", "tomorrow at 8:15 AM ET"),
                      ("2026-11-03T17:00:00", "tonight at 6:08 PM ET")):      # after the EST change
        got = h.next_brief(None, dt.datetime.fromisoformat(iso).replace(tzinfo=dt.timezone.utc))
        check(got.endswith(want), fails, f"{iso}Z reads {got!r}")
    print("D. Moving the market is stamped with its ranking time")
    w = h.wire_top(wire, "", NOW)
    check("Ranked" in w and (wire.get("ranked_et") or "?") in w, fails,
          f"the wire block prints 'Ranked {wire.get('ranked_et')}'")
    try:
        import morning as m
    except ImportError:
        check(False, fails, "morning.py exists (main has none)")
        return finish(fails)
    print("E. the copy law and the run")
    import llm
    gate = None
    obj = {"headline": "The wire opens quiet", "narrative_line": "x",
           "sentences": ["Bitcoin rose 2.1 percent overnight.", "Prices will rise by Friday.",
                         "The wire's top line is a Treasury proposal.", "The Board shows calm funding.",
                         "Four outlets carry the proposal."]}
    head, sents, line = m.clean(obj, gate)
    check(len(sents) == 3 and not any("percent" in s or "will" in s for s in sents), fails,
          f"sentences with a change or a prediction are cut and the rest stand: {sents}")
    try:
        m.clean(dict(obj, sentences=obj["sentences"][:2]), gate)
        check(False, fails, "a read left with fewer than two sentences is refused")
    except llm.LLMError:
        check(True, fails, "a read left with fewer than two sentences is refused")
    tmp = tempfile.mkdtemp(prefix="morning-")
    m.OUT, m.LEDGER = os.path.join(tmp, "morning.json"), os.path.join(tmp, "ledger.json")

    class Budget:
        tokens, usd = 2400, 0.0031

    class Fake:
        mode = "live"
        budget = Budget()

        def __init__(self, good):
            self.good = good

        def call_json(self, stage, system, user, validate=None, max_rungs=3):
            if not self.good:
                raise llm.LLMError("planted: the API is down")
            return validate({"headline": "The wire opens on a Treasury proposal",
                             "sentences": ["The wire's top line is a Treasury proposal.",
                                           "The Board shows calm funding."],
                             "narrative_line": "The tape is calm and the news is mostly regulation."})
    rec = m.run(now=NOW, client=Fake(True), snapshot=snap, wire=wire)
    check(rec and os.path.exists(m.OUT) and rec["date_et"] == "2026-10-13", fails,
          "a good morning writes morning.json for its Eastern date")
    check(not m.second_fallback(m.LEDGER), fails, "one good morning raises no alarm")
    os.remove(m.OUT)
    for day, good in ((dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc), False),
                      (dt.datetime(2026, 10, 15, 12, 30, tzinfo=dt.timezone.utc), False)):
        r = m.run(now=day, client=Fake(good), snapshot=snap, wire=wire)
        check(r is None and not os.path.exists(m.OUT), fails,
              f"{day.date()}: a failed morning falls back cleanly and writes nothing")
        if day.day == 14:
            check(not m.second_fallback(m.LEDGER), fails, "one fallback raises no alarm")
    check(m.second_fallback(m.LEDGER), fails, "two mornings in a row raise the one alarm")
    return finish(fails)


def finish(fails):
    print("\nRESULT:", "all green" if not fails else f"{len(fails)} failing")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
