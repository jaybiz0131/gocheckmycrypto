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
                     and "came in time with the fall" in verdict.grade(r, "BTC")["line"][0])(rec(D14())))
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
            and "moved against the rise" in by["Disputed"]["line"][1])
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


def unit():
    fails = []
    for name, fn in (("grades", grade_cases), ("timing", timing_cases), ("because", because_cases),
                     ("model", model_cases), ("spend", spend_cases), ("no grade", no_grade_cases),
                     ("pages", page_cases), ("wiring", wiring_cases)):
        group(fails, name, fn)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.3: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
