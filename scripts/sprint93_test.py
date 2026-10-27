#!/usr/bin/env python3
"""Program 9, Sprint 9.3: the verdict. Each case is named after what it guards.

  python3 scripts/sprint93_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() on the tree)

Fix round 4 (October 19, 2026) rewrote this file to the strategist's rulings of that day (docs/RULINGS.md):
the flat test and the card's direction words read the window /today/ uses (the ET day, or the rolling 24
hours when open_et is absent, said by its basis); Unclear is "no candidate passes the timing test" and
nothing else; Disputed is outlets naming different causes, or a named cause failing the timing test while
another event passes it; Likely is one event passing the timing test with the readings agreeing and no
primary source; Confirmed needs a primary source; a move under the threshold gets no card; the timing
thresholds live once, in why_evidence.TIMING_TEST; each model attempt is reserved against the day's cap
before it is made and settled after. The earlier rounds' file is in the branch history.

The records are 9.2's, built from the recorded fixtures under fixtures/why/ (real answers for the 24 hours
ending at the 14 and 15 October Editions; fixtures/why/README.txt), and the real 19 October morning record
(site/data/why/2026-10-19-morning.json). The day's moves come from the same pulses: the 14 and 15 October
fixtures carry no open_et, so those days read the rolling 24 hours; 19 October reads the ET day. Cases marked
SYNTHETIC change a real record by hand to reach a rule the real days do not; they are labeled (Jack, 13
October 2026). NO LIVE MODEL CALL: the API is mocked at the HTTP layer (llm.urllib.request.urlopen).
"""
import contextlib
import copy
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
GRADE = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b")
BECAUSE = re.compile(r"\bbecause\b", re.I)
DENY = re.compile(r"does not say (any|one)|not say (any|one) of them|did not (cause|move)|"
                  r"no (event|report) (caused|moved)", re.I)
AI_WORDS = re.compile(r"\b(AI|model|Claude|Haiku|Sonnet|machine|automated|algorithm|budget|spend|cap)\b", re.I)


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


def s92():
    import sprint92_test
    return sprint92_test


def rec(day):
    return s92().rec(day)


def D14():
    return s92().D14


def D15():
    return s92().D15


def visible(html):
    return s92().visible(html)


def today_rec(day):
    return json.load(open(os.path.join(HERE, "site", "data", "today", f"{day}.json"), encoding="utf-8"))


def r19():
    return json.load(open(os.path.join(HERE, "site", "data", "why", "2026-10-19-morning.json"), encoding="utf-8"))


# The pulse rows the 19 October morning read carried (site/data/pulse.json at 22c92f6, generated
# 2026-10-19T12:16:18Z), copied so the case does not move when a later run rewrites that file.
PULSE19 = {"generated_utc": "2026-10-19T12:16:18Z", "movers": {"top100": [
    {"symbol": "BTC", "price": 82428, "chg_24h_pct": 0.53, "open_et": 82385.26, "open_et_day": "2026-10-19"},
    {"symbol": "ETH", "price": 2421.84, "chg_24h_pct": 0.23, "open_et": 2422.59, "open_et_day": "2026-10-19"}]}}


def day14():
    import verdict
    return verdict.day_moves(s92().load(f"pulse_{D14()}.json"), "2026-10-14")


def day15():
    import verdict
    return verdict.day_moves(s92().load(f"pulse_{D15()}.json"), "2026-10-15")


def day19():
    import verdict
    return verdict.day_moves(PULSE19, "2026-10-19")


# ---- the mocked API -----------------------------------------------------------------------------------

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class MockAPI:
    """Stands in for https://api.anthropic.com/v1/messages. `draft` and `check` are functions of the
    request's user text returning the model's JSON answer, or an exception to raise. Every request body
    is kept, so a case can read the model id and the thinking field that were sent."""

    def __init__(self, draft=None, check=None, usage=(1200, 300)):
        self.draft, self.check, self.usage, self.bodies = draft, check, usage, []

    def __call__(self, req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        self.bodies.append(body)
        user = body["messages"][0]["content"]
        fn = self.draft if body["model"] == "claude-haiku-5-5" else self.check
        out = fn(user) if fn else {}
        if isinstance(out, BaseException):
            raise out
        return _Resp(json.dumps({"content": [{"type": "text", "text": json.dumps(out)}],
                                 "stop_reason": "end_turn",
                                 "usage": {"input_tokens": self.usage[0],
                                           "output_tokens": self.usage[1]}}).encode("utf-8"))


@contextlib.contextmanager
def mocked(api, key="test-key-not-real"):
    import llm
    old_open, old_key = llm.urllib.request.urlopen, os.environ.get("ANTHROPIC_API_KEY")
    old_sleep = llm.time.sleep
    llm.urllib.request.urlopen = api
    llm.time.sleep = lambda s: None
    if key is None:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    else:
        os.environ["ANTHROPIC_API_KEY"] = key
    try:
        yield api
    finally:
        llm.urllib.request.urlopen = old_open
        llm.time.sleep = old_sleep
        if old_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = old_key


def phrases_in(user):
    m = re.search(r"PHRASES:\n(\[.*?\])\n", user, re.S)
    return json.loads(m.group(1)) if m else []


def copy_two(user):
    p = phrases_in(user)
    return {"sentences": p[:2]}


def stands_all(user):
    m = re.search(r"SENTENCES:\n(\[.*?\])\n", user, re.S)
    sents = json.loads(m.group(1)) if m else []
    return {"claims": [{"sentence": i + 1, "claim": s, "why": "the phrases carry it", "stands": True}
                       for i, s in enumerate(sents)]}


def run(r, api, ledger, day_et="2026-10-14", slot="evening", gate=None, cap=None, day=None):
    import verdict
    with mocked(api):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            v, row = verdict.write_run(r, day_et, slot, gate=gate, ledger_path=ledger, directory=None,
                                       save=False, cap=cap, day=day if day is not None else day14())
    return v, row, out.getvalue()


# ---- the records: real, and SYNTHETIC where a rule is out of the real days' reach -----------------------------

def _cpi(r):
    return next(x for x in r["candidates"] if x["id"] == "bls-20261014-consumer-price-index")


def _test_of(r, sym, cid):
    return next(t for t in r["coins"][sym]["tests"] if t["id"] == cid)


def synthetic_confirmed():
    """SYNTHETIC, from the real 14 October record: the CPI candidate made a primary source's own line that
    states the cause (a primary wire item). Its timing and the readings of the hour after it stay real."""
    r = rec(D14())
    _cpi(r).update(kind="wire", line="Bitcoin fell after hotter inflation data sent rate-hike odds higher",
                   links=[{"outlet": "Bureau of Labor Statistics", "url": "https://example.invalid/bls"}],
                   source_count=1, primary=True)
    return r


def synthetic_two_outlets():
    """SYNTHETIC: as synthetic_confirmed, but two outlets and no primary source: two outlets no longer
    make Confirmed (ruling 2), so it reads Likely."""
    r = synthetic_confirmed()
    _cpi(r).update(primary=False, source_count=2,
                   links=[{"outlet": "CoinDesk", "url": "https://example.invalid/a"},
                          {"outlet": "The Block", "url": "https://example.invalid/b"}])
    return r


def synthetic_disputed_fail():
    """SYNTHETIC, from the real 15 October record with the linked reports withheld (the wire as it stood):
    the producer-price line names a cause and fails the timing test; the Brooklyn takedown is made to pass
    it, so one named cause fails while another event passes."""
    r = s92().rec_bare(D15())
    c = next(x for x in r["candidates"] if x["line"].startswith("Brooklyn DA"))
    _test_of(r, "BTC", c["id"])["result"].update(before_onset=False, share_pct=62.0, done_pct=0.0,
                                                  moved_first=False, in_window=True)
    return r


def synthetic_disputed_two():
    """SYNTHETIC, from the real 14 October record: the CPI release's first report given back the wire's
    own line (it names inflation as the cause), and the Kraken line rewritten to name the Saldo deal as
    the cause and made to pass the timing test: outlets name different causes."""
    r = rec(D14())
    wire = s92().load(f"wire_{D14()}.json")
    _cpi(r)["report_line"] = next(w["line"] for w in wire["items"] if w["line"].startswith("U.S. inflation"))
    k = next(x for x in r["candidates"] if x["line"].startswith("Kraken"))
    k["line"] = "Kraken parent Payward agreed to acquire Saldo Bank, sending Bitcoin lower as traders sold"
    _test_of(r, "BTC", k["id"])["result"].update(share_pct=55.0, done_pct=10.0, moved_first=False,
                                                  before_onset=False, in_window=True)
    return r


def synthetic_likely_onset():
    """SYNTHETIC, from the real 14 October record without the readings of the hour after: the onset moved
    to 15 minutes after CPI and the onset hour's pattern set to risk-off across assets."""
    r = rec(D14())
    for c in r["coins"].values():
        c.pop("event_hours", None)
    coin = r["coins"]["BTC"]
    t = int(dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc).timestamp())
    coin["run"]["start_t"] = t + 15 * 60
    coin["mechanics"]["patterns"] = [{"label": "risk-off across assets", "rule": "synthetic"}]
    _test_of(r, "BTC", _cpi(r)["id"])["result"].update(lead_min=15.0, before_onset=True, done_pct=0.0,
                                                        moved_first=False)
    return r


def synthetic_no_readings():
    """SYNTHETIC: the real 14 October record without the readings of the hour after (as written before
    9.3): CPI passes the timing test and the onset hour's readings are silent on it."""
    r = rec(D14())
    for c in r["coins"].values():
        c.pop("event_hours", None)
    return r


def synthetic_collision():
    """SYNTHETIC, from the real 14 October record: a second listed item that also names the Consumer Price
    Index, from another outlet, so the event's name alone matches two listed items."""
    r = rec(D14())
    r["candidates"].append({"id": "wire-synth-cpi", "kind": "wire", "line": "Consumer Price Index data drew traders",
                            "event_utc": None, "scheduled": False, "report_utc": "2026-10-14T15:00:00Z",
                            "source_count": 1, "primary": False, "secondary": False,
                            "links": [{"outlet": "Decrypt", "url": "https://example.invalid/d"}]})
    return r


def records():
    """(name, evidence record, date, slot, day moves) for the page matrix: every record that grades."""
    return [("14 Oct Likely (real)", rec(D14()), "2026-10-14", "evening", day14()),
            ("15 Oct Unclear (real)", rec(D15()), "2026-10-15", "evening", day15()),
            ("SYNTHETIC Confirmed", synthetic_confirmed(), "2026-10-14", "evening", day14()),
            ("SYNTHETIC Disputed, a named cause fails", synthetic_disputed_fail(), "2026-10-15", "evening", day15()),
            ("SYNTHETIC Disputed, two named causes", synthetic_disputed_two(), "2026-10-14", "evening", day14()),
            ("SYNTHETIC Likely on the onset hour", synthetic_likely_onset(), "2026-10-14", "evening", day14()),
            ("SYNTHETIC name collision", synthetic_collision(), "2026-10-14", "evening", day14())]


# ---- 1. each grade under the rulings of October 19 ----------------------------------------------------------

def grade_cases(fails):
    import verdict
    print("1. each grade, by the rules in code (the strategist's rulings of October 19)")
    g = verdict.grade(rec(D14()), "BTC", day14())
    guarded(fails, "14 October Bitcoin (real, rolling 24 hours: no open_et that day): Likely, on the CPI release, "
                   "the timing passes and the readings of the hour after it agree, no primary source",
            lambda: g["grade"] == "Likely" and g["cand"]["line"].startswith("Consumer Price Index")
            and g["cand"]["readings"] == "agree" and g["basis"] == "rolling_24h")
    g = verdict.grade(rec(D15()), "BTC", day15())
    guarded(fails, "15 October Bitcoin (real): Unclear, no candidate passes the timing test, and the line says "
                   "exactly 'No reported event lines up with this move.'",
            lambda: g["grade"] == "Unclear" and g["line"][0] == "No reported event lines up with this move.")
    g = verdict.grade(r19(), "BTC", day19())
    guarded(fails, "19 October Bitcoin (real): flat on the ET day (up 0.05% since midnight ET), no card",
            lambda: g["kind"] == "flat" and g["grade"] is None and g["basis"] == "et_day")
    for nm, r, d in (("14 Oct", rec(D14()), day14()), ("15 Oct", rec(D15()), day15()), ("19 Oct", r19(), day19())):
        e = verdict.grade(r, "ETH", d)
        guarded(fails, f"{nm} Ether (real): within 2 points of Bitcoin, no card", lambda: e["kind"] == "with_btc"
                and e["grade"] is None)
    g = verdict.grade(s92().rec_bare(D15()), "BTC", day15())
    guarded(fails, "15 October with the reports withheld (real wire): the named producer-price cause fails and no "
                   "other event passes, so Unclear (no longer Disputed)", lambda: g["grade"] == "Unclear")
    g = verdict.grade(synthetic_confirmed(), "BTC", day14())
    guarded(fails, "SYNTHETIC: a primary source states the cause, the timing passes, the readings agree: Confirmed",
            lambda: g["grade"] == "Confirmed")
    g = verdict.grade(synthetic_two_outlets(), "BTC", day14())
    guarded(fails, "SYNTHETIC: two outlets and no primary source no longer make Confirmed: Likely",
            lambda: g["grade"] == "Likely")
    g = verdict.grade(synthetic_disputed_fail(), "BTC", day15())
    guarded(fails, "SYNTHETIC: a named cause fails the timing test while another event passes: Disputed, both "
                   "sides named", lambda: g["grade"] == "Disputed" and len(g["refs"]) == 2)
    g = verdict.grade(synthetic_disputed_two(), "BTC", day14())
    guarded(fails, "SYNTHETIC: outlets name different causes: Disputed, both named",
            lambda: g["grade"] == "Disputed" and len(g["refs"]) == 2)
    g = verdict.grade(synthetic_no_readings(), "BTC", day14())
    # CHANGED BY the strategist's October 20 ruling on J-8 (a): this was "no card (kind no_verdict)"; it is now Unclear
    # with its own line, the event named
    guarded(fails, "SYNTHETIC: an event passes the timing test but the readings do not agree: Unclear, with the line "
                   "'A reported event lines up in time, but the market readings do not match it.' and the event named "
                   "(October 20, J-8 a)",
            lambda: g["kind"] == "graded" and g["grade"] == "Unclear"
            and g["line"][0] == "A reported event lines up in time, but the market readings do not match it."
            and g["refs"] and g["refs"][0]["text"] in g["line"][1])
    g = verdict.grade(rec(D14()), "BTC", {"basis": "rolling_24h", "BTC": 1.4, "ETH": 1.0})
    # CHANGED BY the strategist's October 20 ruling on J-8 (b): this was kind no_verdict, nothing printed; it is now
    # kind next_read, and the page prints "Verdict at the next read" in the card's place
    guarded(fails, "SYNTHETIC: the page's window rose while the measured run fell: no card, never a fall's "
                   "evidence under a rise; kind next_read, printing 'Verdict at the next read' (October 20, J-8 b)",
            lambda: g["kind"] == "next_read" and g["grade"] is None and g["line"] == ["Verdict at the next read"])
    r = rec(D14())
    for tst in r["coins"]["BTC"]["tests"]:                                 # both 8:30 AM releases moved to
        if tst["t_utc"] == "2026-10-14T12:30:00Z":                         # 10 PM ET the night before
            tst["t_utc"] = "2026-10-14T02:00:00Z"
    g = verdict.grade(r, "BTC", {"basis": "et_day", "BTC": -2.6, "ETH": -3.8})
    guarded(fails, "SYNTHETIC: on the ET day, an event from before 11 PM ET the night before is outside the "
                   "window, so nothing passes: Unclear", lambda: g["grade"] == "Unclear")
    guarded(fails, "the definitions follow the rulings: Confirmed needs a primary source; Unclear is no event "
                   "passing the timing test; no definition says 'two outlets' or 'silent'",
            lambda: "primary source" in verdict.DEFINITIONS["Confirmed"]
            and verdict.DEFINITIONS["Unclear"] == "No reported event passes the timing test with the market readings and the move's direction agreeing."  # CHANGED BY the coordinator's correction of October 20 (J-8 a, J-9 3): the definition must agree with the cards
            and not any(re.search(r"two outlets|silent", d, re.I) for d in verdict.DEFINITIONS.values()))


# ---- 2. one window per page: the ET day, named --------------------------------------------------------------

def window_cases(fails):
    import verdict
    print("2. the flat test and the direction words read the window /today/ uses, named")
    d = day19()
    guarded(fails, "19 October: the ET day from open_et (82385.26 to 82428, up 0.05%), basis et_day",
            lambda: d["basis"] == "et_day" and abs(d["BTC"] - 0.05) < 0.01)
    guarded(fails, "14 October: no open_et that day, so the rolling 24 hours (down 2.08%), basis rolling_24h",
            lambda: day14()["basis"] == "rolling_24h" and day14()["BTC"] == -2.08)
    t19 = today_rec("2026-10-19-morning")
    guarded(fails, "19 October: the verdict's flat test agrees with /today/'s own direction (flat, et_day)",
            lambda: t19["direction"] == "flat" and t19["direction_basis"] == "et_day"
            and verdict.grade(r19(), "BTC", d)["kind"] == "flat")
    for nm, r, dd in (("Likely", rec(D14()), day14()), ("Confirmed", synthetic_confirmed(), day14()),
                      ("et_day Likely", synthetic_confirmed(), {"basis": "et_day", "BTC": -2.6, "ETH": -3.8})):
        g = verdict.grade(r, "BTC", dd)
        words = "since midnight ET" if dd["basis"] == "et_day" else "over the last 24 hours"
        guarded(fails, f"{nm}: every direction word names the page's window ('{words}') and no other window",
                lambda: all(words in p for p in g["phrases"] + g["phrases_sec"] if re.search(r"\b(fall|rise|fell|rose)\b", p))
                and not any(re.search(r"24-hour|24 hours to", p) for p in g["phrases"] + g["phrases_sec"]))


# ---- 3. the timing thresholds live once, in why_evidence.TIMING_TEST ------------------------------------------

def timing_cases(fails):
    import verdict
    import why_evidence as we
    print("3. the timing test's thresholds, one versioned constant in why_evidence.py")
    guarded(fails, "why_evidence.TIMING_TEST holds 25% and 40%, versioned, citing the audit",
            lambda: we.TIMING_TEST["done_max_pct"] == 25.0 and we.TIMING_TEST["share_min_pct"] == 40.0
            and we.TIMING_TEST.get("version") and "3.1" in we.TIMING_TEST.get("source", ""))
    guarded(fails, "verdict.py keeps no copy of the thresholds", lambda: not hasattr(verdict, "TIMING")
            and "share_min_pct\": 4" not in open(os.path.join(HERE, "verdict.py"), encoding="utf-8").read())

    def res(day, pat):
        r = rec(day)
        c = next(x for x in r["candidates"] if re.search(pat, x["line"]))
        return _test_of(r, "BTC", c["id"])["result"]
    cpi, ppi = res(D14(), r"^Consumer Price Index"), res(D15(), r"^Producer Price Index")
    guarded(fails, "14 October CPI passes (8.5% of the run before it, 71.2% in the hour after)",
            lambda: verdict.timing_pass(cpi) == "share")
    guarded(fails, "15 October PPI fails (the hour after it ran against the rise)", lambda: verdict.timing_pass(ppi) is None)
    guarded(fails, "26% of the run done before the event disqualifies it", lambda: verdict.timing_pass(
        dict(cpi, done_pct=26.0, moved_first=False)) is None)
    guarded(fails, "39% of the move in the hour after is under the bar", lambda: verdict.timing_pass(
        dict(cpi, share_pct=39.0)) is None)
    old = dict(we.TIMING_TEST)
    try:
        we.TIMING_TEST["share_min_pct"] = 75.0
        guarded(fails, "the verdict reads the constant: raised to 75%, 14 October CPI fails",
                lambda: verdict.timing_pass(cpi) is None)
    finally:
        we.TIMING_TEST.clear()
        we.TIMING_TEST.update(old)


# ---- 4. "because" only on Confirmed; both sides on Disputed ---------------------------------------------------

def because_cases(fails):
    import verdict
    print("4. 'because' only on Confirmed; 'lines up with' on Likely; both sides on Disputed; nothing predicts")
    by = {"Confirmed": verdict.grade(synthetic_confirmed(), "BTC", day14()),
          "Likely": verdict.grade(rec(D14()), "BTC", day14()),
          "Disputed": verdict.grade(synthetic_disputed_fail(), "BTC", day15()),
          "Unclear": verdict.grade(rec(D15()), "BTC", day15())}
    for gname, v in by.items():
        words = " ".join(v["line"] + v["phrases"] + v["phrases_sec"])
        if gname == "Confirmed":
            guarded(fails, "Confirmed: its line says 'because'", lambda: BECAUSE.search(" ".join(v["line"])))
        else:
            guarded(fails, f"{gname}: no 'because' in any phrase", lambda: not BECAUSE.search(words))
        guarded(fails, f"{gname}: nothing predicts, nothing advises",
                lambda: not re.search(r"\b(will|expect\w*|forecast\w*|should|buy|sell)\b", words, re.I))
        guarded(fails, f"{gname}: no line quoted, in any form", lambda: '"' not in words)
    guarded(fails, "Likely: 'lines up with'", lambda: "lines up with" in by["Likely"]["line"][0])
    d = by["Disputed"]
    guarded(fails, "Disputed: the card states the named cause and the event that passes, both sides, in its line",
            lambda: "named the producer-price data" in d["line"][0] and "as the cause" in d["line"][0]
            and "fails the timing test" in d["line"][0] and "passes the timing test" in d["line"][1]
            and "producer-price data" in d["phrases_sec"][0] and "passes the timing test" in d["phrases_sec"][1])
    vb = copy.deepcopy(by["Likely"])
    vb["phrases"][1] = "It came because of the release."
    guarded(fails, "the belt refuses 'because' on a Likely draft built from whole phrases",
            lambda: "because" in verdict.belts(vb, [vb["phrases"][0], vb["phrases"][1]]))


# ---- 5. the model path, checked, and the fail-open path ---------------------------------------------------------

def model_cases(fails):
    import llm
    import verdict
    print("5. Haiku 5.5 drafts, Sonnet 5.5 checks with 'stands' per claim; a failure fails open to the phrases")
    with tempfile.TemporaryDirectory() as td:
        api = MockAPI(copy_two, stands_all)
        v, row, out = run(rec(D14()), api, os.path.join(td, "l.json"))
        b = v["coins"]["BTC"]
        guarded(fails, "whole phrases and every claim standing: the model's two sentences print",
                lambda: b["by"] == "model" and b["text"] == b["phrases"][:2])
        guarded(fails, "the draft went to claude-haiku-5-5 and the check to claude-sonnet-5-5, no thinking field",
                lambda: [x["model"] for x in api.bodies] == ["claude-haiku-5-5", "claude-sonnet-5-5"]
                and all("thinking" not in x for x in api.bodies) and llm.thinking_param("claude-sonnet-5-5") is None)
        guarded(fails, "llm.PRICING carries the 5.5 rates", lambda: llm.PRICING["claude-haiku-5-5"] == (0.10, 0.50)
                and llm.PRICING["claude-sonnet-5-5"] == (2.0, 10.0))

    def failing(why):
        return lambda user: why
    cases = {
        "the draft call fails (HTTP 500 on every attempt)": MockAPI(failing(llm.urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages", 500, "boom", {}, io.BytesIO(b"{}"))), stands_all),
        "the check withdraws a claim (stands false)": MockAPI(copy_two, lambda u: {"claims": [
            dict(c, stands=(i == 0)) for i, c in enumerate(stands_all(u)["claims"])]}),
        "the check leaves a sentence unjudged": MockAPI(copy_two, lambda u: {"claims": stands_all(u)["claims"][:1]}),
        "the check answers out of contract": MockAPI(copy_two, lambda u: {"verdict": "fine"}),
        "the draft adds a figure": MockAPI(lambda u: {"sentences": [phrases_in(u)[0], "Bitcoin fell 9.9% in an hour."]},
                                           stands_all),
        "the draft rewords a phrase": MockAPI(
            lambda u: {"sentences": [phrases_in(u)[0].replace("lines up with", "tracks"), phrases_in(u)[1]]}, stands_all),
    }
    for name, api in cases.items():
        with tempfile.TemporaryDirectory() as td:
            v, row, out = run(rec(D14()), api, os.path.join(td, "l.json"))
            b = v["coins"]["BTC"]
            guarded(fails, f"fail open when {name}: the graded line, no model sentence",
                    lambda: b["by"] == "phrases" and b["text"] == b["line"] and b["grade"] == "Likely")

    class DropAll:
        def text(self, t, surface, **kw):
            return ""
    with tempfile.TemporaryDirectory() as td:
        v, row, out = run(rec(D14()), MockAPI(copy_two, stands_all), os.path.join(td, "l.json"), gate=DropAll())
        b = v["coins"]["BTC"]
        guarded(fails, "the twins gate checks the model's sentences, the graded line and the section forms: a gate "
                       "that drops every sentence leaves nothing of them to print",
                lambda: b["by"] == "phrases" and not b["line"] and not any(b["phrases_sec"])
                and verdict.text_sec(b) == [])
    v = copy.deepcopy(verdict.record_from(rec(D14()), "2026-10-14", "evening", day=day14())["coins"]["BTC"])
    v["text"] = ["A sentence the phrases never carried."]
    guarded(fails, "a stored sentence that cannot be traced to whole phrases prints nothing on a section page "
                   "(the old fallback to unchecked section forms is gone)", lambda: verdict.text_sec(v) == [])


# ---- 6. the spend: reserved before each attempt, settled after, at the cap withheld ---------------------------

def spend_cases(fails):
    import llm
    import verdict
    print("6. the spend: each attempt reserved against the day's cap first and settled after (ruling 4)")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        v, row, out = run(rec(D14()), MockAPI(copy_two, stands_all, usage=(2000, 500)), led)
        rows = json.load(open(led, encoding="utf-8"))
        calls = [r for r in rows if r.get("kind") == "call"]
        want = round((2000 * 0.10 + 500 * 0.50) / 1e6 + (2000 * 2.0 + 500 * 10.0) / 1e6, 6)
        guarded(fails, "each call reserved and settled to its actual cost; one run row with the day's total and the cap",
                lambda: [c["status"] for c in calls] == ["settled", "settled"]
                and abs(sum(c["usd"] for c in calls) - want) < 1e-6
                and all(c["est_usd"] >= c["usd"] for c in calls)
                and [r for r in rows if r.get("kind") == "run"][0]["cap_usd"] == 1.5
                and abs(verdict.day_spend("2026-10-14", led) - want) < 1e-6)
        guarded(fails, "the run prints the day's spend against the $1.50 cap",
                lambda: re.search(r"today \$0\.0\d+ of the \$1\.50 cap", out))

    # a call cut off by the deadline still counts
    def late(user):
        verdict.STOP["set"] = True
        return verdict._Late("the step's budget is spent")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        try:
            api = MockAPI(late, stands_all)
            v, row, out = run(rec(D14()), api, led)
        finally:
            verdict.STOP["set"] = False
        rows = json.load(open(led, encoding="utf-8"))
        cut = [r for r in rows if r.get("kind") == "call"]
        guarded(fails, "a call cut off by the deadline stays reserved at its estimate and counts in the day's spend",
                lambda: len(api.bodies) == 1 and cut and cut[0]["status"] == "reserved"
                and verdict.day_spend("2026-10-14", led) == cut[0]["est_usd"] > 0)

    # the reservation is on disk before the call goes out: a process killed mid-call leaves it counted
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        seen = {}

        def peek(user):
            seen["rows"] = json.load(open(led, encoding="utf-8")) if os.path.exists(led) else []
            return copy_two(user)
        run(rec(D14()), MockAPI(peek, stands_all), led)
        guarded(fails, "the reservation is written to the ledger on disk before the call is made",
                lambda: [r.get("status") for r in seen.get("rows", []) if r.get("kind") == "call"] == ["reserved"])

    # a retry that would pass the cap is refused before it is made
    v14 = verdict.grade(rec(D14()), "BTC", day14())
    est = verdict.estimate("verdict_draft", verdict.DRAFT_SYSTEM, verdict.draft_user(v14))
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        api = MockAPI(lambda u: llm.urllib.error.URLError("connection reset"), stands_all)
        v, row, out = run(rec(D14()), api, led, cap=est * 1.5)
        guarded(fails, "a transport failure keeps its reservation, and the automatic retry that would pass the cap "
                       "is refused: one attempt made",
                lambda: len(api.bodies) == 1 and v["coins"]["BTC"]["kind"] == "withheld")

    # the empty-response retry is guarded too
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        n = {"i": 0}

        class Empty(MockAPI):
            def __call__(self, req, timeout=None):
                self.bodies.append(json.loads(req.data.decode("utf-8")))
                return _Resp(json.dumps({"content": [], "stop_reason": "end_turn",
                                         "usage": {"input_tokens": 1000, "output_tokens": 2900}}).encode("utf-8"))
        api = Empty()
        cost1 = (1000 * 0.10 + 2900 * 0.50) / 1e6
        v, row, out = run(rec(D14()), api, led, cap=cost1 + est * 0.9)
        guarded(fails, "llm.py's empty-response retry is checked against the cap before it is made",
                lambda: len(api.bodies) == 1 and v["coins"]["BTC"]["kind"] == "withheld")

    # at the cap the verdict is withheld, with the desk's line and no grade
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        json.dump([{"kind": "call", "date": "2026-10-14", "slot": "morning", "status": "settled", "usd": 1.4999,
                    "est_usd": 1.4999}], open(led, "w"))
        api = MockAPI(copy_two, stands_all)
        v, row, out = run(rec(D14()), api, led)
        b = v["coins"]["BTC"]
        card = verdict.card_html(v, "BTC", where="today")
        guarded(fails, "at the cap: no call, the verdict withheld, no grade and no URL",
                lambda: not api.bodies and b["kind"] == "withheld" and not b["grade"] and not b.get("url"))
        guarded(fails, "at the cap the card says the desk's check did not run today, and nothing about AI or a cap",
                lambda: "The desk's check of this move did not run today." in visible(card)
                and not GRADE.search(visible(card)) and not AI_WORDS.search(visible(card)))
    guarded(fails, "the cap is $1.50 a day, in one place", lambda: verdict.CAP_USD == 1.50)


# ---- 7. no card where no verdict is computed --------------------------------------------------------------

def no_card_cases(fails):
    import today
    import verdict
    print("7. no card where no verdict was computed; no grade word outside a card")
    v19 = verdict.record_from(r19(), "2026-10-19", "morning", day=day19())
    for where in ("home", "today", "coin", "page"):
        guarded(fails, f"19 October (flat ET day): no Bitcoin card on {where}",
                lambda: verdict.card_html(v19, "BTC", where=where) == "")
    guarded(fails, "19 October: Ether moved with Bitcoin is one plain line on the Ether page, naming the page's "
                   "window, not a card",
            lambda: verdict.card_html(v19, "ETH", where="coin")
            == '<p class="vd-plain">Ether moved with Bitcoin since midnight ET.</p>'
            and verdict.card_html(v19, "ETH", where="today") == "")
    vn = verdict.record_from(synthetic_no_readings(), "2026-10-14", "evening", day=day14())
    # CHANGED BY the strategist's October 20 rulings on J-8: a record with no readings of the hour after, whose event
    # passes the timing test, is now an Unclear card (a); a window that ran the other way draws the notice (b)
    # CHANGED BY Sprint 9.9.1 (the ruling on J-8 of October 20, "always prints why and the time of the next read, in one line"): the
    # notice is no longer the bare words; it is the ruled words, the reason and the next read, inside a card of its own. The time
    # of the next read depends on the clock that drew it, so it is matched as a shape here and exactly in scripts/sprint991_test.py.
    # CHANGED AGAIN BY Sprint 9.9.1, round 4 (entry 2026-10-26-C6): the reason is the ruled wording, the measured run's direction against the page window's.
    nr = verdict.card_html(verdict.record_from(synthetic_no_readings(), "2026-10-14", "evening",
                                               day={"basis": "rolling_24h", "BTC": 1.4, "ETH": 1.0}), "BTC")
    guarded(fails, "an event that passes with silent readings draws the Unclear card (October 20, J-8 a); a window that ran "
                   "the other way draws only 'Verdict at the next read' with its reason and the next read, no URL (J-8 b)",
            lambda: "Unclear" in verdict.card_html(vn, "BTC") and vn["coins"]["BTC"].get("url")
            and re.search(r'<p class="vd-plain vd-next" data-vd-next="next_read">Verdict at the next read: the run the last read '
                          r'measured went (up|down); the move [^<;]* is (up|down)\. Next read: [^<]*\.</p>', nr) and "vd-badge" not in nr and "href" not in nr)
    d19 = today_rec("2026-10-19-morning")
    page = today.body_html(d19, [], "dated", evidence=r19(), verdict=v19)
    guarded(fails, "/today/2026-10-19 with the real records: no card, no grade word, and 9.2's notes",
            lambda: 'class="vd' not in page and not GRADE.search(visible(page))
            and "it does not say any of them moved the price" in visible(page))
    guarded(fails, "a record with no coin draws nothing and raises nothing",
            lambda: verdict.card_html({"coins": {}}, "BTC") == "" and verdict.card_html(None, "BTC") == "")


# ---- 8. the pages: the card, the URL, corrections, notes, chips, slots ---------------------------------------

def _css_tokens():
    """{theme: {token: value}} as the browser resolves them: site.css first, system.css after it."""
    out = {"light": {}, "dark": {}}
    for f in ("site.css", "system.css"):
        css = re.sub(r"/\*.*?\*/", "", open(os.path.join(HERE, "site", "assets", f), encoding="utf-8").read(), flags=re.S)
        for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
            sel, pre = m.group(1), css[:m.start()]
            dark = "prefers-color-scheme:dark" in pre[-400:] or 'data-theme="dark"' in sel
            if ":root" not in sel or ('data-theme="light"]' in sel and "not" not in sel):
                continue
            theme = "dark" if (dark or ':not([data-theme="light"])' in sel) else "light"
            for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+)", m.group(2)):
                out[theme][k] = v.strip()
    for k, v in out["light"].items():
        out["dark"].setdefault(k, v)
    return out


def _coin_page_for(sym, ev, v):
    import site_build as sb
    import snapshot
    p = copy.deepcopy(s92().load(f"pulse_{D15()}.json"))
    p["generated_utc"] = ev["window"]["end_utc"]
    pos, c = next((i + 1, x) for i, x in enumerate(p["movers"]["top100"]) if x["symbol"] == sym)
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, s92().load(f"flows_{D15()}.json"))
    try:
        return sb.render_coin_page(c, pos, p, [], "DATELINE", wire={"items": []}, cm={}, evidence=ev, verdict=v)
    finally:
        sb.SNAP = old


def _home_html(v):
    import home
    import site_build as sb
    import snapshot
    p = s92().load(f"pulse_{D15()}.json")
    snap = snapshot.build(p, s92().load(f"flows_{D15()}.json"))
    now = dt.datetime(2026, 10, 15, 23, 50, tzinfo=dt.timezone.utc)
    return home.above_fold(snap, p, {}, sb.board_deltas(p), s92().load(f"wire_{D15()}.json"), {}, {},
                           sb.NEWS_CADENCE_LINE, now=now, verdict=v)


def page_cases(fails):
    import home
    import site_build as sb
    import today
    import verdict
    print("8. one card on the home, /today/, Bitcoin; a URL per graded verdict; corrections; notes; chips; slots")
    v14 = verdict.record_from(rec(D14()), "2026-10-14", "evening", day=day14())
    v15 = verdict.record_from(rec(D15()), "2026-10-15", "evening", day=day15())
    d15 = today_rec("2026-10-15-evening")
    pages = {"/today/": today.body_html(d15, [], "living", evidence=rec(D15()), verdict=v15),
             "/coins/btc": _coin_page_for("BTC", rec(D15()), v15), "home": _home_html(v15)}
    for name, h in pages.items():
        guarded(fails, f"{name}: the verdict card, one shape (aside.vd with data-vd)",
                lambda: re.search(r'<aside class="vd[^"]*" data-vd="BTC"', h or ""))
        guarded(fails, f"{name}: no em dash or en dash", lambda: not re.search("[\u2013\u2014]", h or ""))
    guarded(fails, "the home keeps its ten blocks in section 2's order",
            lambda: tuple(re.findall(r'data-block="([a-z]+)"', pages["home"])) == home.ABOVE_FOLD
            and pages["home"].count("<section") == len(home.ABOVE_FOLD))
    guarded(fails, "the URL of a graded verdict is /why/<date>-<coin>, and the card links it",
            lambda: v14["coins"]["BTC"]["url"] == "/why/2026-10-14-bitcoin"
            and 'href="/why/2026-10-15-bitcoin"' in pages["/today/"])
    outside = re.sub(r'<aside class="vd.*?</aside>', "", pages["/today/"], flags=re.S)
    guarded(fails, "/today/: no grade word outside the card", lambda: not GRADE.search(visible(outside)))
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        for d, v, r in (("2026-10-14", v14, rec(D14())), ("2026-10-15", v15, rec(D15()))):
            json.dump(v, open(os.path.join(vd, f"{d}-evening.json"), "w"))
            json.dump(r, open(os.path.join(wd, f"{d}-evening.json"), "w"))
        v19 = verdict.record_from(r19(), "2026-10-19", "morning", day=day19())
        json.dump(v19, open(os.path.join(vd, "2026-10-19-morning.json"), "w"))
        built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))
        rels = sorted(b["rel"] for b in built)
        guarded(fails, "a page per graded verdict (14 and 15 October Bitcoin); none for a flat day or Ether",
                lambda: rels == ["why/2026-10-14-bitcoin.html", "why/2026-10-15-bitcoin.html"])
        sm = sb.render_news_sitemap([], extra=[{"loc": b["path"], "published_utc": b["published_utc"],
                                                 "title": b["title"]} for b in built])
        guarded(fails, "the verdict URLs are in the news sitemap", lambda: f"{sb.ORIGIN}/why/2026-10-14-bitcoin</loc>" in sm)
        guarded(fails, "/why/ does not link a /today/<day> that does not exist",
                lambda: all('href="/today/20' not in b["html"] for b in built))
        vc = copy.deepcopy(v15)
        vc["coins"]["BTC"]["corrections"] = [{"date": "October 16, 2026", "text": "This verdict named the wrong hour."}]
        json.dump(vc, open(os.path.join(vd, "2026-10-15-evening.json"), "w"))
        p15 = next(b for b in verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))
                   if b["rel"] == "why/2026-10-15-bitcoin.html")
        guarded(fails, "a correction on the verdict renders on its page and its card",
                lambda: "Correction, October 16, 2026." in visible(p15["html"]))
    for name, vv in (("Confirmed", verdict.record_from(synthetic_confirmed(), "2026-10-14", "evening", day=day14())),
                     ("Likely", v14)):
        ev = synthetic_confirmed() if name == "Confirmed" else rec(D14())
        trec = dict(d15, date_et="2026-10-14", corrections=[])
        for pn, h in (("/today/", today.body_html(trec, [], "dated", evidence=ev, verdict=vv)),
                      ("/coins/btc", _coin_page_for("BTC", ev, vv))):
            guarded(fails, f"{pn} with a {name} card: no sentence denies causation",
                    lambda: "Checked:" in visible(h) and not DENY.search(visible(h)))
    tok = _css_tokens()
    css = re.sub(r"/\*.*?\*/", "", open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read(), flags=re.S)
    chip = [m.group(2) for m in re.finditer(r"([^{}]*vd-badge[^{}]*)\{([^{}]*)\}", css)]
    used = set(re.findall(r"var\((--[\w-]+)\)", " ".join(chip)))
    for theme in ("light", "dark"):
        t = tok[theme]
        bad = {t.get(k, "").lower() for k in ("--up", "--down", "--up-line", "--down-line", "--up-tint", "--down-tint")}
        hits = sorted(k for k in used if t.get(k, "?").lower() in bad)
        guarded(fails, f"{theme}: no grade chip token resolves to an up or down color ({', '.join(hits) or 'none'})",
                lambda: used and not hits)
    plain = today.body_html(d15, [], "dated", evidence=rec(D15()))
    guarded(fails, "/today/ with no verdict is 9.2's layout (no empty card slot)",
            lambda: "</p>\n  <section class=\"td-sec\"><h2>What moved</h2>" in plain)
    xrp = _coin_page_for("XRP", rec(D15()), v15)
    guarded(fails, "a coin page with no card is 9.2's layout (no empty card slot)",
            lambda: "</p>\n  \n  \n  <section class=\"cn-cm\"" in xrp)


# ---- 9. on a page with the section: one fact printed once, and a pointer to exactly one item -------------------

FACT_RES = [r"\b\d{1,2}:\d{2} [AP]M\b", r"[▲▼]?\s?\d[\d,]*\.?\d*\s?(?:%|bp)",
            r"\$[\d,]+(?:\.\d+)?(?:[KMB]| million| billion)?",
            r"risk-(?:on|off) across assets|crypto only|leverage flush|coin-specific|did not trade|none of the four"]


def _facts(text):
    out = set()
    for rx in FACT_RES:
        out.update(" ".join(m.split()) for m in re.findall(rx, text))
    return out


def _parts(html):
    card = (re.search(r'<aside class="vd.*?</aside>', html, re.S) or re.match("", "")).group(0)
    sec = (re.search(r'<section class="td-sec ev".*?</section>', html, re.S) or re.match("", "")).group(0)
    crow = {visible(x) for x in re.findall(r"<li>.*?</li>", card, re.S)}
    srow = {visible(x) for x in re.findall(r'<li class="td-row">.*?</li>', sec, re.S)}
    ctext = visible(re.sub(r'<ul class="vd-rows">.*?</ul>', " ", card, flags=re.S))
    return card, sec, ctext, crow, srow


def pointer_problems(card, sec):
    """Every way a card's pointer can fail to name exactly one listed item: by its id and marker, and by
    the words of its name."""
    out = []
    refs = re.findall(r'<b class="vd-ref" data-vd-ref="([^"]+)" data-vd-key="([^"]*)">(.*?)</b>', card)
    items = re.findall(r'(<li class="ev-c[^"]*" data-ev-id="([^"]+)".*?</li>)', sec, re.S)
    marked = [i for i, _id in items if "ev-graded" in i.split(">")[0]]
    if len(marked) != len({r[0] for r in refs}):
        out.append(f"{len(marked)} item(s) marked for {len({r[0] for r in refs})} name(s)")
    for rid, key, text in refs:
        hits = [i for i, iid in items if iid == rid]
        if len(hits) != 1:
            out.append(f"{text!r} points at {len(hits)} listed item(s)")
            continue
        if "ev-graded" not in hits[0].split(">")[0] or "ev-mark" not in hits[0]:
            out.append(f"{text!r}'s item carries no visible marker")
        toks = [k for k in key.split("|") if k]
        if toks:
            by_words = [i for i, _iid in items if all(k.lower() in visible(i).lower() for k in toks)]
            if len(by_words) != 1 or by_words[0] != hits[0]:
                out.append(f"{text!r}'s words match {len(by_words)} listed item(s)")
    return out


def _with_text(vrec, sym, joined):
    v = copy.deepcopy(vrec)
    c = v["coins"].get(sym) or {}
    ph = c.get("phrases") or []
    if c.get("grade") and len(ph) >= 2:
        two = [ph[0], ph[1]]
        if joined and len(ph) >= 3:
            two[1] = ph[1][:-1] + "; " + ph[2][:1].lower() + ph[2][1:]
        c.update(text=two, by="model")
    return v


def matrix_cases(fails):
    import today
    import verdict
    print("9. on a page with the section: no fact in both, and every name points at exactly one listed item")
    d15 = today_rec("2026-10-15-evening")
    for name, ev, day, slot, mv in records():
        base = verdict.record_from(ev, day, slot, day=mv)
        guarded(fails, f"{name}: graded, with a card", lambda: base["coins"]["BTC"].get("grade"))
        for variant, vrec in (("graded line", base), ("model text", _with_text(base, "BTC", False)),
                              ("model text joined", _with_text(base, "BTC", True))):
            pages = {}
            trec = dict(d15, date_et=day, slot=slot, corrections=[])
            pages["/today/ living"] = today.body_html(trec, [], "living", evidence=ev, verdict=vrec)
            pages["/today/ dated"] = today.body_html(trec, [], "dated", evidence=ev, verdict=vrec)
            pages["/coins/btc"] = _coin_page_for("BTC", ev, vrec)
            with tempfile.TemporaryDirectory() as td:
                vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
                os.makedirs(vd)
                os.makedirs(wd)
                json.dump(vrec, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
                json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
                for b in verdict.build_pages(vd, wd, tdir=os.path.join(td, "none")):
                    pages["/" + b["rel"][:-5]] = b["html"]
            for pname, html in pages.items():
                card, sec, ctext, crow, srow = _parts(html)
                if not card or not sec:
                    guarded(fails, f"{name}, {variant}, {pname}: card and section both present", lambda: False)
                    continue
                both = sorted((_facts(ctext) & _facts(visible(sec))) | (crow & srow))
                guarded(fails, f"{name}, {variant}, {pname}: no fact in both ({'; '.join(both) or 'none'})",
                        lambda: not both)
                if "No reported event lines up" in ctext:
                    continue
                probs = pointer_problems(card, sec)
                guarded(fails, f"{name}, {variant}, {pname}: the event is named and points at exactly one "
                               f"listed item ({'; '.join(probs) or 'one'})",
                        lambda: not probs and 'data-vd-ref="' in card)
    for name, ev, day, slot, mv in records()[1:2]:
        h = verdict.card_html(verdict.record_from(ev, day, slot, day=mv), "BTC", where="home", live=True)
        guarded(fails, f"{name}: the home card, with no section beside it, still states the onset hour's reading",
                lambda: re.search(r"risk-on across assets", visible(h)))


# ---- 10. wiring ------------------------------------------------------------------------------------------------

def wiring_cases(fails):
    print("10. wired into both workflows after why_evidence.py, inside a time budget, never a gate")
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: runs verdict.py --write after why_evidence.py, with a timeout, never as a gate",
                lambda: re.search(r"why_evidence\.py --write \|\| true.*?timeout \d+ python3 verdict\.py --write \|\| true",
                                  y, re.S))
        step = re.search(r"- name: [^\n]*[Vv]erdict[^\n]*\n(.*?)(?=\n      - name:)", y, re.S)
        guarded(fails, f"{wf}: the key comes from the repository secret",
                lambda: step and "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in step.group(1))
        guarded(fails, f"{wf}: commits the verdict records and the spend ledger",
                lambda: "git add site/data/verdict" in y and "data/verdict-ledger.json" in y)
    src = open(os.path.join(HERE, "verdict.py"), encoding="utf-8").read()
    guarded(fails, "verdict.py carries no em dash and prints no key",
            lambda: not re.search("[\u2013\u2014]", src) and not re.search(r"print\([^)]*API_KEY", src))
    llm_src = open(os.path.join(HERE, "llm.py"), encoding="utf-8").read()
    guarded(fails, "llm.py checks the attempt guard before every HTTP attempt, inside the retry loop",
            lambda: re.search(r"for i in range\(attempts\):\s+retry_after = None\s+if getattr\(self, \"attempt_guard\"",
                              llm_src))


def unit():
    fails = []
    for name, fn in (("grades", grade_cases), ("window", window_cases), ("timing", timing_cases),
                     ("because", because_cases), ("model", model_cases), ("spend", spend_cases),
                     ("no card", no_card_cases), ("pages", page_cases), ("matrix", matrix_cases),
                     ("wiring", wiring_cases)):
        group(fails, name, fn)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.3: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
