#!/usr/bin/env python3
"""Program 9, Sprint 9.3: the verdict. Each case is named after what it guards.

  python3 scripts/sprint93_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() on the tree)

The records are 9.2's, built from the recorded fixtures under fixtures/why/ (real answers for the 24
hours ending at the 14 and 15 October Editions; see fixtures/why/README.txt). Cases marked SYNTHETIC
change a real record by hand to reach a rule the two real days do not (a Confirmed, a flat day);
they are labeled as such (Jack, 13 October 2026). NO LIVE MODEL CALL: the Anthropic API is mocked at
the HTTP layer (llm.urllib.request.urlopen), so llm.py's real request, pricing and budget path runs
and nothing leaves the machine. Every case catches its own exceptions, so on a tree without
verdict.py the run prints FAIL lines instead of crashing.
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


# ---- the mocked API -----------------------------------------------------------------------------------

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class MockAPI:
    """Stands in for https://api.anthropic.com/v1/messages. `draft` and `check` are functions of the
    request's user text returning the model's JSON answer (or an Exception to raise). Every request
    body is kept, so a case can read the model id and the thinking field that were sent."""

    def __init__(self, draft=None, check=None, usage=(1200, 300)):
        self.draft, self.check, self.usage, self.bodies = draft, check, usage, []

    def __call__(self, req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        self.bodies.append(body)
        user = body["messages"][0]["content"]
        fn = self.draft if body["model"] == "claude-haiku-5-5" else self.check
        out = fn(user) if fn else {}
        if isinstance(out, Exception):
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
    """The phrases block the draft request carries, as the list the model is handed."""
    m = re.search(r"PHRASES:\n(\[.*?\])\n", user, re.S)
    return json.loads(m.group(1)) if m else []


def copy_two(user):
    """A well-behaved draft: the first two phrases the request lists, copied whole."""
    p = phrases_in(user)
    return {"sentences": p[:2]}


def stands_all(user):
    m = re.search(r"SENTENCES:\n(\[.*?\])\n", user, re.S)
    sents = json.loads(m.group(1)) if m else []
    return {"claims": [{"sentence": i + 1, "claim": s, "why": "the phrases carry it", "stands": True}
                       for i, s in enumerate(sents)]}


def run(r, api, ledger, day="2026-10-14", slot="evening", gate=None, cap=None):
    import verdict
    with mocked(api):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            v, row = verdict.write_run(r, day, slot, gate=gate, ledger_path=ledger, directory=None,
                                       save=False, cap=cap)
    return v, row, out.getvalue()


# ---- 1. each grade from a fixture -------------------------------------------------------------------------

def synthetic_confirmed():
    """SYNTHETIC, from the real 14 October record: the CPI release's first report is given back the
    wire's own line as the wire held it before 9.1's source check cut its Bitcoin clause, and a second
    outlet, and the run's onset is moved to the release with the onset hour's pattern set to
    risk-off across assets, so the three conditions of Confirmed hold."""
    r = rec(D14())
    c = next(x for x in r["candidates"] if x["line"].startswith("Consumer Price Index"))
    wire = s92().load(f"wire_{D14()}.json")
    c["report_line"] = next(w["line"] for w in wire["items"] if w["line"].startswith("U.S. inflation"))
    c["source_count"] = 2
    coin = r["coins"]["BTC"]
    t = int(dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc).timestamp())
    coin["run"]["start_t"] = t + 15 * 60
    coin["mechanics"]["patterns"] = [{"label": "risk-off across assets", "rule": "synthetic"}]
    for tst in coin["tests"]:
        if tst["id"] == c["id"]:
            tst["result"].update(lead_min=15.0, before_onset=True, done_pct=0.0, moved_first=False)
    return r


def synthetic_flat():
    """SYNTHETIC, from the real 15 October record: Bitcoin's series ends within 0.5% of its start."""
    r = rec(D15())
    pts = r["coins"]["BTC"]["series"]["points"]
    pts[-1] = [pts[-1][0], pts[0][1] * 1.003]
    return r


def grade_cases(fails):
    import verdict
    print("1. each grade from a fixture, by the rules in code")
    g14 = verdict.grade(rec(D14()), "BTC")
    guarded(fails, "14 October, Bitcoin (real): Likely, on the CPI release: its timing passes and the readings of "
                   "the hour after it agree (risk-off across assets); no source-checked report states it",
            lambda: g14["grade"] == "Likely" and g14["cand"]["line"].startswith("Consumer Price Index")
            and g14["cand"]["readings"] == "agree" and g14["cand"]["readings_hour"] == "after"
            and not g14["cand"]["stated"])
    guarded(fails, "a record written before 9.3 (no readings of the hour after) grades on the onset hour only: "
                   "14 October then reads Unclear, an event in time with no report or reading behind it",
            lambda: (lambda r: [c.pop("event_hours", None) for c in r["coins"].values()]
                     and verdict.grade(r, "BTC")["grade"] == "Unclear"
                     and "came in time with the 24-hour fall" in verdict.grade(r, "BTC")["line"][0])(rec(D14())))
    g15 = verdict.grade(rec(D15()), "BTC")
    guarded(fails, "15 October, Bitcoin (real): Unclear, no reported event passes the timing test",
            lambda: g15["grade"] == "Unclear" and g15["line"][0] == "No reported event lines up with this move.")
    guarded(fails, "Unclear still shows the mechanics: its line names the onset hour's pattern",
            lambda: "risk-on across assets" in " ".join(g15["line"]))
    bare = s92().rec_bare(D15())
    gb = verdict.grade(bare, "BTC")
    guarded(fails, "15 October with the linked reports withheld (real wire as it stood): Disputed, the reported "
                   "producer-price cause fails the timing test",
            lambda: gb["grade"] == "Disputed" and "producer-price" in gb["cand"]["line"])
    gc = verdict.grade(synthetic_confirmed(), "BTC")
    guarded(fails, "SYNTHETIC Confirmed: two outlets state it, the timing passes, the readings agree",
            lambda: gc["grade"] == "Confirmed")
    for day in (D14(), D15()):
        ge = verdict.grade(rec(day), "ETH")
        guarded(fails, f"{day[:10]}, Ether (real): within 2 points of Bitcoin, so one line, 'moved with Bitcoin', no grade",
                lambda: ge["kind"] == "with_btc" and ge["grade"] is None
                and ge["line"] == ["Ether moved with Bitcoin."])
    gf = verdict.grade(synthetic_flat(), "BTC")
    guarded(fails, "SYNTHETIC flat day: 'Flat: nothing to explain', no grade",
            lambda: gf["kind"] == "flat" and gf["grade"] is None and gf["line"] == ["Flat: nothing to explain."])


def timing_cases(fails):
    import verdict
    import why_evidence as we
    print("2. the timing test's second path (the onset question carried from 9.2), thresholds in one place")
    guarded(fails, "the thresholds live in one named place, verdict.TIMING",
            lambda: set(verdict.TIMING) >= {"done_max_pct", "share_min_pct"}
            and verdict.TIMING["lead_min"] == we.LEAD_MIN)

    def res(day, pat, sym="BTC"):
        r = rec(day)
        c = next(x for x in r["candidates"] if re.search(pat, x["line"]))
        return next(t for t in r["coins"][sym]["tests"] if t["id"] == c["id"])["result"]
    cpi = res(D14(), r"^Consumer Price Index")
    guarded(fails, "14 October CPI passes timing although it came after the 4:10 AM onset: 8.5% of the run done "
                   "before it, 71.2% of the move in the hour after (9.2's figures, unchanged)",
            lambda: cpi["before_onset"] is False and cpi["done_pct"] == 8.5 and cpi["share_pct"] == 71.2
            and verdict.timing_pass(cpi) == "share")
    ppi = res(D15(), r"^Producer Price Index")
    guarded(fails, "15 October PPI fails timing: the hour after it ran against the rise",
            lambda: ppi["share_pct"] < 0 and verdict.timing_pass(ppi) is None)
    guarded(fails, "the price moved first: a candidate after half the run fails whatever the share",
            lambda: verdict.timing_pass(dict(cpi, done_pct=60.0, moved_first=True)) is None)
    guarded(fails, "a candidate under the share threshold fails",
            lambda: verdict.timing_pass(dict(cpi, share_pct=verdict.TIMING["share_min_pct"] - 1)) is None)
    guarded(fails, "9.2's onset is unchanged (14 October Bitcoin onset 4:10 AM ET)",
            lambda: we.clock(rec(D14())["coins"]["BTC"]["run"]["start_t"]) == "4:10 AM ET")


# ---- 3. "because" only on Confirmed ---------------------------------------------------------------------------

def because_cases(fails):
    import verdict
    print("3. 'because' only on Confirmed; 'lines up with' on Likely; both sides on Disputed")
    by = {"Confirmed": verdict.grade(synthetic_confirmed(), "BTC"),
          "Likely": verdict.grade(rec(D14()), "BTC"),
          "Disputed": verdict.grade(s92().rec_bare(D15()), "BTC"),
          "Unclear": verdict.grade(rec(D15()), "BTC")}
    for g, v in by.items():
        words = " ".join(v["line"] + v["phrases"])
        if g == "Confirmed":
            guarded(fails, "Confirmed: the graded line says 'because'", lambda: BECAUSE.search(" ".join(v["line"])))
        else:
            guarded(fails, f"{g}: no 'because' in its line or in any phrase the model is handed",
                    lambda: not BECAUSE.search(words))
    guarded(fails, "Likely: the line says 'lines up with'", lambda: "lines up with" in " ".join(by["Likely"]["line"]))
    d = " ".join(by["Disputed"]["line"])
    guarded(fails, "Disputed: both sides, the reported cause and the timing against it",
            lambda: len(by["Disputed"]["line"]) == 2 and "reported a cause" in by["Disputed"]["line"][0]
            and "moved against the 24-hour rise" in by["Disputed"]["line"][1])
    for g, v in by.items():
        guarded(fails, f"{g}: nothing predicts and nothing advises",
                lambda: not re.search(r"\b(will|expect\w*|forecast\w*|should|buy|sell)\b", " ".join(v["line"]), re.I))

    # SYNTHETIC: the 14 October CPI candidate turned into a wire line that itself says "because"; the
    # verdict grades it Likely and never quotes the line
    r = rec(D14())
    c = next(x for x in r["candidates"] if x["line"].startswith("Consumer Price Index"))
    c.update(kind="wire", line="Bitcoin fell because hot inflation data lifted rate-hike bets",
             links=[{"outlet": "CoinDesk", "url": "https://example.invalid/x"}], source_count=1, primary=False)
    vq = verdict.grade(r, "BTC")
    guarded(fails, "SYNTHETIC: a wire line that says 'because' is never quoted on a Likely verdict",
            lambda: vq["grade"] == "Likely" and not BECAUSE.search(" ".join(vq["line"] + vq["phrases"]))
            and "a report from CoinDesk" in vq["line"][0])
    vb = copy.deepcopy(by["Likely"])
    vb["phrases"][1] = "It came because of the release."
    guarded(fails, "the belt itself refuses 'because' on a Likely draft, even one built from whole phrases",
            lambda: "because" in verdict.belts(vb, [vb["phrases"][0], vb["phrases"][1]]))

    # a model sentence that says "because" on a Likely day never prints
    def says_because(user):
        p = phrases_in(user)
        return {"sentences": [p[0].replace("lines up with", "fell because of"), p[1]]}
    with tempfile.TemporaryDirectory() as td:
        v, _row, _o = run(rec(D14()), MockAPI(says_because, stands_all), os.path.join(td, "l.json"))
        b = v["coins"]["BTC"]
        guarded(fails, "a draft saying 'because' on a Likely day fails the belt and the graded line prints instead",
                lambda: b["by"] == "phrases" and not BECAUSE.search(" ".join(b["text"])))


# ---- 4. the model path, checked, and the fail-open path ---------------------------------------------------------

def model_cases(fails):
    import llm
    import verdict
    print("4. Haiku 5.5 drafts, Sonnet 5.5 checks with 'stands' per claim; any failure fails open to the phrases")
    with tempfile.TemporaryDirectory() as td:
        api = MockAPI(copy_two, stands_all)
        v, row, out = run(rec(D14()), api, os.path.join(td, "l.json"))
        b = v["coins"]["BTC"]
        guarded(fails, "a draft that copies whole phrases and a check that lets every claim stand: the model's two sentences print",
                lambda: b["by"] == "model" and len(b["text"]) == 2 and b["text"] == b["phrases"][:2])
        guarded(fails, "the draft went to claude-haiku-5-5 and the check to claude-sonnet-5-5",
                lambda: [x["model"] for x in api.bodies] == ["claude-haiku-5-5", "claude-sonnet-5-5"])
        guarded(fails, "no thinking field sent to a 5.5 model (Sonnet 5.5 answers {type: disabled} with a 400)",
                lambda: all("thinking" not in x for x in api.bodies)
                and llm.thinking_param("claude-sonnet-5-5") is None and llm.thinking_param("claude-haiku-5-5") is None)
        guarded(fails, "llm.PRICING carries the 5.5 rates (Haiku $0.10/$0.50, Sonnet $2/$10 per million)",
                lambda: llm.PRICING["claude-haiku-5-5"] == (0.10, 0.50) and llm.PRICING["claude-sonnet-5-5"] == (2.0, 10.0))
        guarded(fails, "Ether moved with Bitcoin: no model call for it", lambda: len(api.bodies) == 2)

    def failing(why):
        return lambda user: why

    cases = {
        "the draft call fails (HTTP 500 on every attempt)": MockAPI(failing(llm.urllib.error.HTTPError(
            "https://api.anthropic.com/v1/messages", 500, "boom", {}, io.BytesIO(b"{}"))), stands_all),
        "the check withdraws a claim (stands false)": MockAPI(copy_two, lambda u: {"claims": [
            dict(c, stands=(i == 0)) for i, c in enumerate(stands_all(u)["claims"])]}),
        "the check leaves a sentence unjudged": MockAPI(copy_two, lambda u: {"claims": stands_all(u)["claims"][:1]}),
        "the check answers out of contract": MockAPI(copy_two, lambda u: {"verdict": "fine"}),
        "the draft adds a figure the phrases do not carry": MockAPI(
            lambda u: {"sentences": [phrases_in(u)[0], "Bitcoin fell 9.9% in an hour."]}, stands_all),
        "the draft rewords a phrase": MockAPI(
            lambda u: {"sentences": [phrases_in(u)[0].replace("lines up with", "tracks"), phrases_in(u)[1]]}, stands_all),
    }
    for name, api in cases.items():
        with tempfile.TemporaryDirectory() as td:
            v, row, out = run(rec(D14()), api, os.path.join(td, "l.json"))
            b = v["coins"]["BTC"]
            guarded(fails, f"fail open when {name}: the graded line from phrases, no model sentence",
                    lambda: b["by"] == "phrases" and b["text"] == b["line"] and b["grade"] == "Likely"
                    and b.get("fail_reason"))
    with tempfile.TemporaryDirectory() as td:
        import verdict as _v
        with mocked(MockAPI(copy_two, stands_all), key=None):
            with contextlib.redirect_stdout(io.StringIO()):
                v, row = _v.write_run(rec(D14()), "2026-10-14", "evening", ledger_path=os.path.join(td, "l.json"),
                                      save=False)
        guarded(fails, "fail open with no API key: the graded line, and the ledger row says no call was made",
                lambda: v["coins"]["BTC"]["by"] == "phrases" and row["calls"] == 0)

    # the step's deadline firing inside the API call: the coin fails open, no further call starts, and the
    # run still writes its ledger row (the deadline is not swallowed by llm.py's retry loop)
    def late(user):
        verdict.STOP["set"] = True
        raise verdict._Late("the step's budget is spent")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "l.json")
        try:
            api = MockAPI(late, stands_all)
            v, row, out = run(rec(D14()), api, led)
        finally:
            verdict.STOP["set"] = False
        guarded(fails, "the deadline mid-call fails open, makes no second attempt, and the ledger row is written",
                lambda: v["coins"]["BTC"]["by"] == "phrases" and len(api.bodies) == 1
                and len(json.load(open(led))) == 1)

    # the twins gate checks every figure of the model's sentences
    class DropAll:
        def text(self, t, surface, **kw):
            return ""
    with tempfile.TemporaryDirectory() as td:
        v, row, out = run(rec(D14()), MockAPI(copy_two, stands_all), os.path.join(td, "l.json"), gate=DropAll())
        guarded(fails, "a model sentence the twins gate drops fails open, never prints",
                lambda: v["coins"]["BTC"]["by"] == "phrases")


# ---- 5. the spend ledger row ------------------------------------------------------------------------------------

def spend_cases(fails):
    import verdict
    print("5. the spend: a ledger row per run, the day's spend printed against the $1.50 cap (ruling 2)")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "verdict-ledger.json")
        v, row, out = run(rec(D14()), MockAPI(copy_two, stands_all, usage=(2000, 500)), led)
        rows = json.load(open(led, encoding="utf-8"))
        want = round((2000 * 0.10 + 500 * 0.50) / 1e6 + (2000 * 2.0 + 500 * 10.0) / 1e6, 6)
        guarded(fails, "one ledger row for the run, with its calls, tokens, dollars by stage and the cap",
                lambda: len(rows) == 1 and rows[0]["calls"] == 2 and rows[0]["tokens"] == 5000
                and abs(rows[0]["usd"] - want) < 1e-6 and rows[0]["cap_usd"] == 1.5
                and set(rows[0]["by_stage"]) == {"verdict_draft", "verdict_check"}
                and rows[0]["date"] == "2026-10-14" and rows[0]["slot"] == "evening")
        guarded(fails, "the run prints the day's spend against the $1.50 cap",
                lambda: re.search(r"today \$0\.0\d+ of the \$1\.50 cap", out))
        v, row, out = run(rec(D14()), MockAPI(copy_two, stands_all, usage=(2000, 500)), led, slot="evening")
        rows = json.load(open(led, encoding="utf-8"))
        guarded(fails, "a second run the same day adds its own row and the day's total sums both",
                lambda: len(rows) == 2 and abs(rows[1]["day_usd"] - 2 * want) < 1e-6)
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "verdict-ledger.json")
        json.dump([{"date": "2026-10-14", "slot": "morning", "usd": 1.4999, "calls": 4, "tokens": 1}],
                  open(led, "w"))
        api = MockAPI(copy_two, stands_all)
        v, row, out = run(rec(D14()), api, led)
        guarded(fails, "with the day's spend at the cap, no call is made and the verdict fails open to the phrases",
                lambda: not api.bodies and v["coins"]["BTC"]["by"] == "phrases"
                and "cap" in (v["coins"]["BTC"].get("fail_reason") or ""))
    guarded(fails, "the cap is $1.50 a day, in one named place", lambda: verdict.CAP_USD == 1.50)


# ---- 6. no grade word where no grade was computed ---------------------------------------------------------------

def no_grade_cases(fails):
    import verdict
    print("6. no grade word where no grade was computed")
    vf = verdict.record_from(synthetic_flat(), "2026-10-15", "evening")
    flat = verdict.card_html(vf, "BTC", where="today")
    guarded(fails, "a flat day's card: 'Flat: nothing to explain' and no grade word, no 'because'",
            lambda: "Flat: nothing to explain." in visible(flat) and not GRADE.search(visible(flat))
            and not BECAUSE.search(visible(flat)))
    v15 = verdict.record_from(rec(D15()), "2026-10-15", "evening")
    eth = verdict.card_html(v15, "ETH", where="coin")
    guarded(fails, "Ether moving with Bitcoin: one line and no grade word",
            lambda: "Ether moved with Bitcoin." in visible(eth) and not GRADE.search(visible(eth)))
    guarded(fails, "an ungraded coin has no verdict URL", lambda: not v15["coins"]["ETH"].get("url"))
    btc = verdict.card_html(v15, "BTC", where="today")
    guarded(fails, "a graded card carries its grade as 'Checked: Unclear'",
            lambda: "Checked: Unclear" in visible(btc))
    guarded(fails, "a record with no coin draws no card and raises nothing",
            lambda: verdict.card_html({"coins": {}}, "BTC") == "" and verdict.card_html(None, "BTC") == "")
    import today
    d15 = today_rec("2026-10-15-evening")
    page = today.body_html(d15, [], "dated", evidence=rec(D15()), verdict=v15)
    ev = re.search(r'<section class="td-sec ev".*?</section>', page, re.S).group(0)
    guarded(fails, "/today/: the evidence section beside the card still carries no grade word",
            lambda: not GRADE.search(visible(ev)) and not BECAUSE.search(visible(ev)))
    outside = re.sub(r'<aside class="vd.*?</aside>', "", page, flags=re.S)
    guarded(fails, "/today/: no grade word anywhere outside the verdict card",
            lambda: not GRADE.search(visible(outside)))


# ---- 7. the card on four pages, one shape; the URL; corrections --------------------------------------------------

def page_cases(fails):
    import home
    import site_build as sb
    import today
    import verdict
    print("7. one card on the home, /today/, Bitcoin and Ether; a URL per graded verdict; corrections on it")
    v14 = verdict.record_from(rec(D14()), "2026-10-14", "evening")
    v15 = verdict.record_from(rec(D15()), "2026-10-15", "evening")
    d15 = today_rec("2026-10-15-evening")
    pages = {"/today/": today.body_html(d15, [], "living", evidence=rec(D15()), verdict=v15)}
    pages["/coins/btc"] = _coin_html("BTC", rec(D15()), v15)
    pages["/coins/eth"] = _coin_html("ETH", rec(D15()), v15)
    pages["home"] = _home_html(v15)
    for name, h in pages.items():
        guarded(fails, f"{name}: the verdict card, one shape (aside.vd with data-vd)",
                lambda: re.search(r'<aside class="vd[^"]*" data-vd="(BTC|ETH)"', h or ""))
        guarded(fails, f"{name}: no em dash or en dash", lambda: not re.search("[\u2013\u2014]", h or ""))
    guarded(fails, "the Ether page carries Ether's card, Bitcoin's pages Bitcoin's",
            lambda: 'data-vd="ETH"' in pages["/coins/eth"] and 'data-vd="BTC"' in pages["/coins/btc"]
            and 'data-vd="BTC"' not in pages["/coins/eth"])
    guarded(fails, "the home keeps its ten blocks in section 2's order (the card is an aside, not a block)",
            lambda: tuple(re.findall(r'data-block="([a-z]+)"', pages["home"])) == home.ABOVE_FOLD
            and pages["home"].count("<section") == len(home.ABOVE_FOLD))
    guarded(fails, "the URL of a graded verdict is /why/<date>-<coin>, e.g. /why/2026-10-14-bitcoin",
            lambda: v14["coins"]["BTC"]["url"] == "/why/2026-10-14-bitcoin")
    guarded(fails, "the card links its verdict URL", lambda: 'href="/why/2026-10-15-bitcoin"' in pages["/today/"])
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        for d, v, r in (("2026-10-14", v14, rec(D14())), ("2026-10-15", v15, rec(D15()))):
            json.dump(v, open(os.path.join(vd, f"{d}-evening.json"), "w"))
            json.dump(r, open(os.path.join(wd, f"{d}-evening.json"), "w"))
        built = verdict.build_pages(vd, wd)
        rels = [b["rel"] for b in built]
        guarded(fails, "a page per graded verdict: why/2026-10-14-bitcoin.html and why/2026-10-15-bitcoin.html, none for Ether",
                lambda: "why/2026-10-14-bitcoin.html" in rels and "why/2026-10-15-bitcoin.html" in rels
                and not any("ether" in r for r in rels))
        p14 = next(b for b in built if b["rel"] == "why/2026-10-14-bitcoin.html")
        guarded(fails, "the verdict page carries the card, the evidence, and the grade",
                lambda: 'class="vd' in p14["html"] and "What lined up with the move" in p14["html"]
                and "Checked: Likely" in visible(p14["html"]))
        sm = sb.render_news_sitemap([], extra=[{"loc": b["path"], "published_utc": b["published_utc"],
                                                 "title": b["title"]} for b in built])
        guarded(fails, "the verdict URL is in the news sitemap",
                lambda: f"{sb.ORIGIN}/why/2026-10-15-bitcoin</loc>" in sm and "<news:title>" in sm)
        # corrections render on the verdict
        vc = copy.deepcopy(v15)
        vc["coins"]["BTC"]["corrections"] = [{"date": "October 16, 2026",
                                              "text": "This verdict named the wrong release time."}]
        json.dump(vc, open(os.path.join(vd, "2026-10-15-evening.json"), "w"))
        built = verdict.build_pages(vd, wd)
        p15 = next(b for b in built if b["rel"] == "why/2026-10-15-bitcoin.html")
        guarded(fails, "a correction on the verdict renders on its page",
                lambda: "Correction, October 16, 2026." in visible(p15["html"]))
        card = verdict.card_html(vc, "BTC", where="today", corrections=d15["corrections"])
        guarded(fails, "the card renders the verdict's own correction and the page's corrections",
                lambda: "This verdict named the wrong release time." in visible(card)
                and "has been removed" in visible(card))


def _coin_html(sym, ev, v):
    import site_build as sb
    import snapshot
    p = s92().load(f"pulse_{D15()}.json")
    coins = p["movers"]["top100"]
    pos, c = next((i + 1, x) for i, x in enumerate(coins) if x["symbol"] == sym)
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, s92().load(f"flows_{D15()}.json"))
    try:
        return sb.render_coin_page(c, pos, p, [], "THURSDAY, OCTOBER 15, 2026", wire=s92().load(f"wire_{D15()}.json"),
                                   cm={}, evidence=ev, verdict=v)
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


# ---- 8. wired into both workflows, after the evidence, never a gate ------------------------------------------

def wiring_cases(fails):
    print("8. wired into both workflows after why_evidence.py, inside a time budget, never a gate")
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: runs verdict.py --write after why_evidence.py, with a timeout, never as a gate",
                lambda: re.search(r"why_evidence\.py --write \|\| true.*?timeout \d+ python3 verdict\.py --write \|\| true",
                                  y, re.S))
        step = re.search(r"- name: [^\n]*[Vv]erdict[^\n]*\n(.*?)(?=\n      - name:)", y, re.S)
        guarded(fails, f"{wf}: the verdict step reads the key from the repository secret, never a literal",
                lambda: step and "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in step.group(1)
                and not re.search(r"sk-ant-", y))
        guarded(fails, f"{wf}: commits the verdict records and the spend ledger with the push",
                lambda: "git add site/data/verdict" in y and "data/verdict-ledger.json" in y)
    src = open(os.path.join(HERE, "verdict.py"), encoding="utf-8").read()
    guarded(fails, "verdict.py carries no em dash and prints no key",
            lambda: not re.search("[\u2013\u2014]", src) and not re.search(r"print\([^)]*API_KEY", src))


# ---- 9. review 1: the four failures and the four items beside them -------------------------------------------

DENY = re.compile(r"does not say (any|one)|not say (any|one) of them|did not (cause|move)|"
                  r"no (event|report) (caused|moved)", re.I)


def _no_event_hours(r):
    for c in r["coins"].values():
        c.pop("event_hours", None)
    return r


def _likely_silent():
    """SYNTHETIC, from the real 14 October record: the CPI release's first report given back the wire's
    own line (it states the cause, one outlet), and the record stripped of the readings of the hour
    after, as a record written before 9.3: the timing passes, a report states it, the readings are
    silent."""
    r = _no_event_hours(rec(D14()))
    c = next(x for x in r["candidates"] if x["line"].startswith("Consumer Price Index"))
    wire = s92().load(f"wire_{D14()}.json")
    c["report_line"] = next(w["line"] for w in wire["items"] if w["line"].startswith("U.S. inflation"))
    return r


def _css_tokens():
    """{theme: {token: value}} as the browser resolves them: site.css first, system.css after it."""
    out = {"light": {}, "dark": {}}
    for f in ("site.css", "system.css"):
        css = open(os.path.join(HERE, "site", "assets", f), encoding="utf-8").read()
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
            sel = m.group(1)
            pre = css[:m.start()]
            dark = pre.rfind("prefers-color-scheme:dark") > pre.rfind("}\n}") and "prefers-color-scheme:dark" in pre[-400:] \
                or 'data-theme="dark"' in sel
            if ":root" not in sel or 'data-theme="light"]' in sel and "not" not in sel:
                continue
            theme = "dark" if (dark or 'data-theme="dark"' in sel or ":not([data-theme=\"light\"])" in sel) else "light"
            for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+)", m.group(2)):
                out[theme][k] = v.strip()
    for k, v in out["light"].items():
        out["dark"].setdefault(k, v)
    return out


def review1_cases(fails):
    import today
    import verdict
    print("9. review 1: Likely needs the readings; the readings shown; no page denies its own grade; neutral chips")
    # 1. Likely only where the timing test and the readings agree (ruling 1)
    v = verdict.grade(_likely_silent(), "BTC")
    guarded(fails, "SYNTHETIC: a report states it and the timing passes, but the readings are silent: Unclear, "
                   "never Likely, and the line says a report named it",
            lambda: v["grade"] == "Unclear" and "reported it as the cause" in v["line"][0]
            and "the market readings do not show it" in v["line"][0])
    guarded(fails, "the printed definitions: Likely needs the readings to agree, and no definition says 'silent'",
            lambda: "agree" in verdict.DEFINITIONS["Likely"]
            and not any("silent" in d for d in verdict.DEFINITIONS.values()))
    for day in (D14(), D15()):
        for sym in ("BTC", "ETH"):
            g = verdict.grade(rec(day), sym)
            guarded(fails, f"{day[:10]} {sym}: a Likely or Confirmed grade always has readings that agree",
                    lambda: g["grade"] not in ("Likely", "Confirmed") or g["cand"]["readings"] == "agree")
    # 2. the readings behind the grade are on the page, labeled with their own hour
    v14 = verdict.record_from(rec(D14()), "2026-10-14", "evening")
    card = verdict.card_html(v14, "BTC", where="page")
    guarded(fails, "the Likely card names the readings its grade rests on, with their own hour: the hour after the "
                   "release, 8:30 to 9:30 AM ET, risk-off across assets",
            lambda: "the hour after it, 8:30 AM ET to 9:30 AM ET" in visible(card)
            and "risk-off across assets" in visible(card))
    guarded(fails, "the card off the home lists those readings' figures (S&P 500 futures, 10-year yield)",
            lambda: "S&P 500 futures" in visible(card) and "10-year Treasury yield" in visible(card))
    guarded(fails, "the card never prints its own coin's hour figure (the evidence list prints it)",
            lambda: "Bitcoin" not in re.sub(r"<[^>]+>", " ", (re.search(r'<ul class="vd-rows">.*?</ul>', card, re.S)
                                                             or re.match("", "")).group(0)))
    r19 = json.load(open(os.path.join(HERE, "site", "data", "why", "2026-10-19-morning.json"), encoding="utf-8"))
    c19 = verdict.card_html(verdict.record_from(r19, "2026-10-19", "morning"), "BTC", where="today")
    guarded(fails, "a grade read on the onset hour names that hour and lists no rows (the evidence section prints "
                   "them under 'The hour the run began'; one fact, printed once)",
            lambda: "the hour the run began, 4:20 PM ET to 5:20 PM ET" in visible(c19) and "vd-rows" not in c19)
    # 3. no page with a graded verdict denies causation; an ungraded page keeps its disclaimer
    d15 = today_rec("2026-10-15-evening")
    for name, vv in (("Confirmed", verdict.record_from(synthetic_confirmed(), "2026-10-15", "evening")),
                     ("Likely", v14)):
        page = today.body_html(d15, [], "dated", evidence=rec(D15()), verdict=vv)
        guarded(fails, f"/today/ with a {name} card: no sentence denies causation",
                lambda: "Checked:" in visible(page) and not DENY.search(visible(page)))
        coin = _coin_html("BTC", rec(D15()), dict(vv, window=rec(D15())["window"]))
        guarded(fails, f"/coins/btc with a {name} card: no sentence denies causation",
                lambda: "Checked:" in visible(coin) and not DENY.search(visible(coin)))
    nev = today.body_html(d15, [], "dated", verdict=v14)
    guarded(fails, "/today/ with a Likely card and no evidence section: the reported note prints and denies nothing",
            lambda: "These are separate reports." in visible(nev) and not DENY.search(visible(nev)))
    plain = today.body_html(d15, [], "dated", evidence=rec(D15()))
    guarded(fails, "/today/ with no verdict keeps the evidence's disclaimer as 9.2 wrote it",
            lambda: "it does not say any of them moved the price" in visible(plain))
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v14, open(os.path.join(vd, "2026-10-14-evening.json"), "w"))
        json.dump(rec(D14()), open(os.path.join(wd, "2026-10-14-evening.json"), "w"))
        built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))
        p14 = built[0]["html"] if built else ""
        guarded(fails, "/why/2026-10-14-bitcoin (Likely): no sentence denies causation",
                lambda: p14 and not DENY.search(visible(p14)))
        guarded(fails, "(d) /why/ links /today/<day> only when that dated page exists",
                lambda: p14 and 'href="/today/2026-10-14"' not in p14)
        json.dump({"date_et": "2026-10-14", "slot": "evening", "corrections": []},
                  open(os.path.join(td, "2026-10-14-evening.json"), "w"))
        built = verdict.build_pages(vd, wd, tdir=td)
        guarded(fails, "(d) and links it when the day's record exists",
                lambda: built and 'href="/today/2026-10-14"' in built[0]["html"])
    # 4. the grade chips are neutral: no chip color equals the up or down tokens, in either theme
    tok = _css_tokens()
    css = re.sub(r"/\*.*?\*/", "", open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read(),
                 flags=re.S)
    chip = [m.group(2) for m in re.finditer(r"([^{}]*vd-badge[^{}]*)\{([^{}]*)\}", css)]
    used = set(re.findall(r"var\((--[\w-]+)\)", " ".join(chip)))
    for theme in ("light", "dark"):
        t = tok[theme]
        bad = {t.get(k, "").lower() for k in ("--up", "--down", "--up-line", "--down-line", "--up-tint", "--down-tint")}
        hits = sorted(k for k in used if t.get(k, "?").lower() in bad)
        guarded(fails, f"{theme}: no grade chip token resolves to an up or down color ({', '.join(hits) or 'none'})",
                lambda: used and not hits and not re.search(r"#[0-9a-fA-F]{3,6}", " ".join(chip)))
    # (a) the card names its window wherever its direction word appears
    for nm, r in (("Likely", rec(D14())), ("Disputed", s92().rec_bare(D15())), ("Confirmed", synthetic_confirmed())):
        g = verdict.grade(r, "BTC")
        guarded(fails, f"(a) {nm}: every phrase with a direction word (fall, rise, fell, rose) names the 24-hour window",
                lambda: all(re.search(r"24 hours|24-hour", p) for p in g["phrases"]
                            if re.search(r"\b(fall|rise|fell|rose)\b", p)))
    # (b) the section and the card agree when stock futures did not trade (19 October, real record)
    import why_evidence as we
    r19 = json.load(open(os.path.join(HERE, "site", "data", "why", "2026-10-19-morning.json"), encoding="utf-8"))
    sec = we.section_html(r19, "BTC", live=False)
    guarded(fails, "(b) 19 October: the section does not label 'crypto only' in an hour stock futures did not trade",
            lambda: "Pattern: crypto only" not in visible(sec) and "did not trade" in visible(sec))
    shut = we.mechanics("BTC", {"dir": "down", "start_t": 1000000, "start_p": 1, "end_t": 1003600, "end_p": 1},
                        [(1000000, 100.0), (1003600, 98.0)], {}, {"ES=F": {"points": []}, "NQ=F": {"points": []}},
                        None, None, None, None)
    guarded(fails, "(b) SYNTHETIC: a new record labels no 'crypto only' when the futures have no bar in the hour",
            lambda: not any(p["label"] == "crypto only" for p in shut["patterns"]))
    # (c) a release or hack line with 'because' or a grade word is never quoted
    for kind in ("release", "hack", "press", "wire"):
        c = {"kind": kind, "line": "Likely rally because rates fell", "links": [{"outlet": "BLS"}]}
        guarded(fails, f"(c) a {kind} line carrying 'because' or a grade word is not quoted",
                lambda: not re.search(r"because|Likely", verdict._ref(c, 1792000000, 1792000000)))


# ---- 10. review 2: a fact the section prints is never printed again by the card ---------------------------------

FACT_RES = [r"\b\d{1,2}:\d{2} [AP]M\b",                       # a time stamp
            r"[▲▼]?\s?\d[\d,]*\.?\d*\s?(?:%|bp)",    # a percentage or basis points
            r"\$[\d,]+(?:\.\d+)?(?:[KMB]| million| billion)?",  # a dollar figure
            r"risk-(?:on|off) across assets|crypto only|leverage flush|coin-specific|did not trade|"
            r"none of the four"]                               # a pattern


def _facts(text):
    out = set()
    for rx in FACT_RES:
        out.update(" ".join(m.split()) for m in re.findall(rx, text))
    return out


def _parts(html):
    """(card sentences' facts, card rows, section text, section rows) from one page."""
    card = (re.search(r'<aside class="vd.*?</aside>', html, re.S) or re.match("", "")).group(0)
    sec = (re.search(r'<section class="td-sec ev".*?</section>', html, re.S) or re.match("", "")).group(0)
    crow = {visible(x) for x in re.findall(r"<li>.*?</li>", card, re.S)}
    srow = {visible(x) for x in re.findall(r'<li class="td-row">.*?</li>', sec, re.S)}
    ctext = visible(re.sub(r'<ul class="vd-rows">.*?</ul>', " ", card, flags=re.S))
    return card, sec, ctext, crow, srow


def _with_text(vrec, sym, joined):
    """The record with the model's two sentences in place of the graded line: whole phrases, the
    second joined to a third with '; ' when there is one (the shape a model draft takes)."""
    v = copy.deepcopy(vrec)
    c = v["coins"].get(sym) or {}
    ph = c.get("phrases") or []
    if c.get("grade") and len(ph) >= 2:
        two = [ph[0], ph[1]]
        if joined and len(ph) >= 3:
            two[1] = ph[1][:-1] + "; " + ph[2][:1].lower() + ph[2][1:]
        c.update(text=two, by="model")
    return v


def synthetic_likely_onset():
    """SYNTHETIC, from the real 14 October record without the readings of the hour after (a record
    written before 9.3): the onset moved to 15 minutes after CPI and the onset hour's pattern set to
    risk-off across assets, so the grade is Likely on the onset hour's readings."""
    r = rec(D14())
    for c in r["coins"].values():
        c.pop("event_hours", None)
    c = next(x for x in r["candidates"] if x["line"].startswith("Consumer Price Index"))
    coin = r["coins"]["BTC"]
    t = int(dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc).timestamp())
    coin["run"]["start_t"] = t + 15 * 60
    coin["mechanics"]["patterns"] = [{"label": "risk-off across assets", "rule": "synthetic"}]
    for tst in coin["tests"]:
        if tst["id"] == c["id"]:
            tst["result"].update(lead_min=15.0, before_onset=True, done_pct=0.0, moved_first=False)
    return r


def _records():
    import verdict
    r19 = json.load(open(os.path.join(HERE, "site", "data", "why", "2026-10-19-morning.json"), encoding="utf-8"))
    return [("14 Oct Likely", rec(D14()), "2026-10-14", "evening"),
            ("15 Oct Unclear", rec(D15()), "2026-10-15", "evening"),
            ("19 Oct real", r19, "2026-10-19", "morning"),
            ("SYNTHETIC Confirmed", synthetic_confirmed(), "2026-10-14", "evening"),
            ("SYNTHETIC Likely on the onset hour", synthetic_likely_onset(), "2026-10-14", "evening"),
            ("15 Oct Disputed (reports withheld)", s92().rec_bare(D15()), "2026-10-15", "evening")]


def _coin_page_for(sym, ev, v):
    import site_build as sb
    import snapshot
    p = copy.deepcopy(s92().load(f"pulse_{D15()}.json"))
    p["generated_utc"] = ev["window"]["end_utc"]           # the Board reading the record was written for
    pos, c = next((i + 1, x) for i, x in enumerate(p["movers"]["top100"]) if x["symbol"] == sym)
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, s92().load(f"flows_{D15()}.json"))
    try:
        return sb.render_coin_page(c, pos, p, [], "DATELINE", wire={"items": []}, cm={}, evidence=ev, verdict=v)
    finally:
        sb.SNAP = old


def review2_cases(fails):
    import today
    import verdict
    print("10. review 2: on a page with the section, no fact (time, figure, pattern) prints in both")
    d15 = today_rec("2026-10-15-evening")
    for name, ev, day, slot in _records():
        base = verdict.record_from(ev, day, slot)
        for variant, vrec in (("graded line", base), ("model text", _with_text(base, "BTC", False)),
                              ("model text joined", _with_text(base, "BTC", True))):
            pages = {}
            trec = dict(d15, date_et=day, slot=slot, corrections=[])
            pages["/today/ living"] = today.body_html(trec, [], "living", evidence=ev, verdict=vrec)
            pages["/today/ dated"] = today.body_html(trec, [], "dated", evidence=ev, verdict=vrec)
            pages["/coins/btc"] = _coin_page_for("BTC", ev, vrec)
            pages["/coins/eth"] = _coin_page_for("ETH", ev, vrec)
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
                    continue
                both = sorted((_facts(ctext) & _facts(visible(sec))) | (crow & srow))
                guarded(fails, f"{name}, {variant}, {pname}: no fact in both the card and the section "
                               f"({'; '.join(both) or 'none'})", lambda: not both)
    # a row of the hour after that the section's onset hour prints with the same figure is not printed again
    v14 = verdict.record_from(rec(D14()), "2026-10-14", "evening")
    sp = next(r for r in v14["coins"]["BTC"]["readings"]["rows"] if r["key"] == "ES=F")
    v14["coins"]["BTC"]["readings"]["onset_rows"].append([sp["key"], sp["value"]])
    guarded(fails, "SYNTHETIC: a row the onset hour prints with the same figure is left to the section; off a "
                   "section page it prints",
            lambda: "S&P 500 futures" not in visible(verdict.card_html(v14, "BTC", where="today", with_section=True))
            and "S&P 500 futures" in visible(verdict.card_html(v14, "BTC", where="today")))
    # a coin page never pairs a card and a section for different windows
    v15 = verdict.record_from(rec(D15()), "2026-10-15", "evening")
    other = copy.deepcopy(v15)
    other["window"] = dict(other["window"], end_utc="2026-10-15T20:43:27Z")
    h = _coin_page_for("BTC", rec(D15()), other)
    guarded(fails, "a coin page whose verdict is for another window than its evidence shows no card, and 9.2's notes",
            lambda: 'class="vd' not in h and "What lined up with the move" in h
            and "it does not say any of them moved the price" in visible(h))
    # a /why/ page carries one card: the day's lead verdict
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v15, open(os.path.join(vd, "2026-10-15-evening.json"), "w"))
        json.dump(dict(copy.deepcopy(v15), slot="morning"), open(os.path.join(vd, "2026-10-15-morning.json"), "w"))
        json.dump(rec(D15()), open(os.path.join(wd, "2026-10-15-evening.json"), "w"))
        built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))
        guarded(fails, "a /why/ page with a morning and an evening verdict carries one card, the evening's",
                lambda: built and built[0]["html"].count('<aside class="vd') == 1)
    # a record graded before the section forms existed: on a section page it prints no fact twice
    for name, ev, day, slot in _records():
        old = verdict.record_from(ev, day, slot)
        for c in old["coins"].values():
            c.pop("phrases_sec", None)
            (c.get("readings") or {}).pop("onset_rows", None)
        h = today.body_html(dict(d15, date_et=day, slot=slot, corrections=[]), [], "dated", evidence=ev, verdict=old)
        card, sec, ctext, crow, srow = _parts(h)
        both = sorted((_facts(ctext) & _facts(visible(sec))) | (crow & srow))
        guarded(fails, f"{name}, a record with no section forms, /today/: no fact in both ({'; '.join(both) or 'none'})",
                lambda: card and not both)
    # the home has no section: its card keeps the onset hour's reading in words
    guarded(fails, "SYNTHETIC: the onset-hour record grades Likely on the onset hour's readings",
            lambda: verdict.grade(synthetic_likely_onset(), "BTC")["cand"]["readings_hour"] == "onset"
            and verdict.grade(synthetic_likely_onset(), "BTC")["grade"] == "Likely")
    for name, ev, day, slot in _records()[1:3]:
        h = verdict.card_html(verdict.record_from(ev, day, slot), "BTC", where="home", live=True)
        guarded(fails, f"{name}: the home card, with no section beside it, still states the onset hour's reading",
                lambda: re.search(r"risk-on across assets|did not trade", visible(h)))
    # (c) no verdict, no slot: the page is the page as it was
    plain = today.body_html(d15, [], "dated", evidence=rec(D15()))
    guarded(fails, "(c) /today/ with no verdict carries no empty card slot (byte-identical to 9.2's layout)",
            lambda: "</p>\n  <section class=\"td-sec\"><h2>What moved</h2>" in plain)
    xrp = _coin_page_for("XRP", rec(D15()), verdict.record_from(rec(D15()), "2026-10-15", "evening"))
    guarded(fails, "(c) a coin page with no card carries no empty card slot (9.2's layout: the readings note, the "
                   "empty evidence and wire slots, then the Chart Master card)",
            lambda: "</p>\n  \n  \n  <section class=\"cn-cm\"" in xrp)


def unit():
    fails = []
    for name, fn in (("grades", grade_cases), ("timing", timing_cases), ("because", because_cases),
                     ("model", model_cases), ("spend", spend_cases), ("no grade", no_grade_cases),
                     ("pages", page_cases), ("wiring", wiring_cases),
                     ("review 1", review1_cases), ("review 2", review2_cases)):
        group(fails, name, fn)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.3: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
