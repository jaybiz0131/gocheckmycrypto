#!/usr/bin/env python3
"""Program 9, Sprint 9.8: the verdict record. Each case is named after what it guards.

  python3 scripts/sprint98_test.py                       # unit cases; exit 1 on any failure
  python3 scripts/sprint98_test.py --tree <built dir>    # also the cases that read a built tree
  (verify_pipeline.py's canary also calls unit() and tree() on the tree it builds)

THE RECORDS ARE 9.3'S AND 9.4'S: the real 14 October evening evidence record (Bitcoin Likely, on the Consumer Price Index
release and the Real Earnings release), the real 15 October one (Bitcoin Unclear), and the real 16 October morning Big movers
record (five coins Unclear, graded with the model mocked at the HTTP layer as in Sprint 9.4's tests). No recorded day gives a
later read of the same move, so the fixture restamps and regrades those real records by hand to make the later reads the
record scores; every such record says SYNTHETIC on its line (Jack, 13 October 2026). NO MODEL CALL and no network.

THE FIXTURE'S TALLY, worked by hand:
  2026-10-14 morning  Bitcoin Likely (CPI, Real Earnings)   later: 14 evening Confirmed on the CPI release  -> confirmed later
  2026-10-14 evening  Bitcoin Confirmed (CPI)                                                             -> context
  2026-10-15 morning  Bitcoin Likely (CPI, Real Earnings)   later: 15 evening Unclear (real)            -> reversed
  2026-10-15 evening  Bitcoin Unclear (real)                                                              -> context
  2026-10-16 morning  five Big movers Unclear (real)                                                      -> context
  2026-10-16 evening  Bitcoin Likely (CPI, Real Earnings)   no later read of the same move              -> awaiting
  2026-10-17 evening  Bitcoin Disputed                                                                    -> context
  Likely 3: confirmed later 1, reversed 1, awaiting 1. Confirmed 1, Disputed 1, Unclear 6.
"""
import contextlib
import copy
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
BECAUSE = re.compile(r"\bbecause\b", re.I)
AI = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bHaiku\b|\bSonnet\b|"
                r"\bOpenAI\b|\bchatbot\b", re.I)
PERSON = re.compile(r"\bJack\b|\bBerno\b|editor-in-chief", re.I)
ORIGIN = "https://gocheckmycrypto.com"
URL = "/why/record/"
RC_KEYS = ("likely", "likely_confirmed_later", "likely_reversed", "likely_awaiting", "confirmed", "disputed", "unclear",
           "reads_coins", "reads_movers")
WANT = {"likely": 3, "likely_confirmed_later": 1, "likely_reversed": 1, "likely_awaiting": 1,
        "confirmed": 1, "disputed": 1, "unclear": 6}


def info(msg):
    print("  INFO " + msg)


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


def s93():
    import sprint93_test
    return sprint93_test


def s94():
    import sprint94_test
    return sprint94_test


def vr():
    import verdict_record
    return verdict_record


def visible(h):
    return s93().visible(h)


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def t(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


# ---- the fixture -------------------------------------------------------------------------------------------------

def _base():
    """(Likely record, Unclear record): the real 14 and 15 October evening verdict records, graded by code (no model)."""
    import verdict as vd
    m = s93()
    v14 = vd.record_from(m.rec(m.D14()), "2026-10-14", "evening", now=t("2026-10-14T23:16:00Z"), day=m.day14())
    v15 = vd.record_from(m.rec(m.D15()), "2026-10-15", "evening", now=t("2026-10-15T23:16:00Z"), day=m.day15())
    assert v14["coins"]["BTC"]["grade"] == "Likely" and v15["coins"]["BTC"]["grade"] == "Unclear"
    return v14, v15


def _put(vdir, src, day, slot, made, mutate=None):
    import verdict as vd
    r = copy.deepcopy(src)
    r.update(date_et=day, slot=slot, made_utc=made)
    for sym, v in r["coins"].items():
        if v.get("url"):
            v["url"] = vd.url(day, sym)
    if mutate:
        mutate(r["coins"]["BTC"])
    json.dump(r, open(os.path.join(vdir, f"{day}-{slot}.json"), "w", encoding="utf-8"))
    return r


def to_confirmed(v):
    """SYNTHETIC: the Likely's first named event (the CPI release) made the one event a primary source states."""
    v["grade"] = "Confirmed"
    v["refs"] = [v["refs"][0]]
    v["cand"] = dict(v["cand"], primary=True, stated=True)


def to_disputed(v):
    """SYNTHETIC: the same move graded Disputed."""
    v["grade"] = "Disputed"


def movers_dir(td, made="2026-10-16T12:40:00Z"):
    """The real 16 October morning Big movers record (five Unclear), its made time set to the morning slot's (the recorded
    record carries the moment it was recorded, October 19)."""
    mdir = os.path.join(td, "movers")
    os.makedirs(mdir, exist_ok=True)
    with quiet():
        r = s94().graded16(td)
    r["made_utc"] = made
    json.dump(r, open(os.path.join(mdir, "2026-10-16-morning.json"), "w", encoding="utf-8"))
    return mdir


_FX = {}


def fixture(td, with_movers=True):
    """{vdir, mdir, wdir, store}: the fixture of the module docstring, in scratch directories under `td`."""
    v14, v15 = _base()
    d = {k: os.path.join(td, k) for k in ("verdict", "why", "store")}
    for p in d.values():
        os.makedirs(p, exist_ok=True)
    vdir = d["verdict"]
    _put(vdir, v14, "2026-10-14", "morning", "2026-10-14T12:18:00Z")                     # SYNTHETIC restamp of a real Likely
    _put(vdir, v14, "2026-10-14", "evening", "2026-10-14T23:16:00Z", to_confirmed)       # SYNTHETIC
    _put(vdir, v14, "2026-10-15", "morning", "2026-10-15T12:18:00Z")                     # SYNTHETIC restamp of a real Likely
    _put(vdir, v15, "2026-10-15", "evening", "2026-10-15T23:16:00Z")                     # REAL Unclear
    _put(vdir, v14, "2026-10-16", "evening", "2026-10-16T23:16:00Z")                     # SYNTHETIC restamp of a real Likely
    _put(vdir, v14, "2026-10-17", "evening", "2026-10-17T23:16:00Z", to_disputed)        # SYNTHETIC
    if with_movers:
        if "movers" not in _FX:
            _FX["movers"] = json.load(open(os.path.join(movers_dir(tempfile.mkdtemp(prefix="s98m-")), "2026-10-16-morning.json"),
                                           encoding="utf-8"))
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir, exist_ok=True)
        json.dump(_FX["movers"], open(os.path.join(mdir, "2026-10-16-morning.json"), "w", encoding="utf-8"))
    else:
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir, exist_ok=True)
    return {"vdir": vdir, "mdir": mdir, "wdir": d["why"], "store": d["store"]}


def view_of(fx, now=None, built=None):
    with quiet():
        return vr().view(now or t("2026-10-17T23:30:00Z"), vdir=fx["vdir"], mdir=fx["mdir"], wdir=fx["wdir"],
                         store=fx["store"], built=built)


def page_of(v):
    with quiet():
        return vr().render(v, "OCTOBER 17, 2026")


def rc(html):
    """{key: [values]} from the page's data-rc counts."""
    out = {}
    for k, val in re.findall(r'data-rc="([a-z_]+)"[^>]*>\s*(\d+)\s*<', html):
        out.setdefault(k, []).append(int(val))
    return out


def outside_counts(html):
    """Count phrases (a number beside a count word) in the page's visible text outside the tally section and the list. The
    tally is the one place a count prints; a count anywhere else is the same fact printed twice."""
    h = re.sub(r'<section class="vr-tally".*?</section>', " ", html, flags=re.S)
    h = re.sub(r'<ol class="vr-l".*?</ol>', " ", h, flags=re.S)
    h = re.sub(r"<header.*?</header>|<nav.*?</nav>|<footer.*?</footer>", " ", h, flags=re.S)
    txt = visible(h)
    return re.findall(r"\b\d+\s+(?:[A-Za-z]+\s+){0,3}?(?:verdicts?|reads?|grades?|confirmed|reversed|awaiting|likely|"
                      r"disputed|unclear|moves?)\b", txt, re.I)


# ---- 1. the tally from a fixture of verdicts and later sources -----------------------------------------------------

def tally_cases(fails):
    print("1. the tally from a fixture of verdicts and later sources")
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td)
        v = view_of(fx)
        c = v["counts"]
        for k, want in WANT.items():
            guarded(fails, f"the tally's {k} is {want} (got {c.get(k)})", lambda k=k, want=want: c.get(k) == want)
        guarded(fails, "the Likely parts sum to the Likely verdicts (confirmed later, reversed, awaiting)",
                lambda: c["likely_confirmed_later"] + c["likely_reversed"] + c["likely_awaiting"] == c["likely"])
        rows = {(r["date_et"], r["slot"], r["coin_sym"]): r for r in v["rows"]}
        guarded(fails, "each graded verdict is one row: 6 of Bitcoin and 5 Big movers, and Ether moving with Bitcoin is none",
                lambda: len(v["rows"]) == 11 and not any(r["coin_sym"] == "ETH" for r in v["rows"]))
        guarded(fails, "14 October morning's Likely is confirmed later, by the evening read's Confirmed on the CPI release",
                lambda: rows[("2026-10-14", "morning", "BTC")]["outcome"] == "confirmed_later"
                and rows[("2026-10-14", "morning", "BTC")]["outcome_detail"]["later_grade"] == "Confirmed"
                and rows[("2026-10-14", "morning", "BTC")]["outcome_detail"]["later_slot"] == "evening")
        guarded(fails, "16 October evening's Likely has no later read: awaiting, never confirmed",
                lambda: rows[("2026-10-16", "evening", "BTC")]["outcome"] == "awaiting")
        guarded(fails, "only a Likely verdict carries an outcome; the other grades are counted as graded at the time",
                lambda: all((r["outcome"] is None) == (r["grade"] != "Likely") for r in v["rows"]))
        guarded(fails, "every row carries its /why/ address: /why/<date>-bitcoin, and /why/<date>-<coin id> for a Big mover",
                lambda: rows[("2026-10-14", "morning", "BTC")]["url"] == "/why/2026-10-14-bitcoin"
                and rows[("2026-10-16", "morning", "TIA")]["url"] == "/why/2026-10-16-celestia")
        guarded(fails, "rows are newest first",
                lambda: [r["made_utc"] for r in v["rows"]] == sorted((r["made_utc"] for r in v["rows"]), reverse=True))
        guarded(fails, "the record begins at the first stored verdict record and runs through the newest read",
                lambda: v["begins_utc"] == "2026-10-14T12:18:00Z" and v["through_utc"] == "2026-10-17T23:16:00Z")
        guarded(fails, "the reads are counted: 6 of Bitcoin and Ether, 1 of Big movers",
                lambda: v["reads"] == {"coins": 6, "movers": 1})
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 2. a reversed verdict counted as reversed ---------------------------------------------------------------------

def reversed_cases(fails):
    print("2. a reversed verdict is counted as reversed")
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td, with_movers=False)
        v = view_of(fx)
        row = next(r for r in v["rows"] if (r["date_et"], r["slot"]) == ("2026-10-15", "morning"))
        guarded(fails, "15 October morning's Likely, regraded Unclear by the evening read (real), is reversed",
                lambda: row["outcome"] == "reversed" and row["outcome_detail"]["later_grade"] == "Unclear")
        guarded(fails, "the reversed verdict is in the reversed count and not in confirmed later",
                lambda: v["counts"]["likely_reversed"] == 1 and v["counts"]["likely_confirmed_later"] == 1)
        # a later Likely or Confirmed that names none of the events the Likely named reverses it
        import verdict as vd
        v14, _v15 = _base()
        fx2 = {k: os.path.join(td, "b", k) for k in ("verdict", "why", "store", "movers")}
        for p in fx2.values():
            os.makedirs(p, exist_ok=True)
        fx2 = {"vdir": fx2["verdict"], "wdir": fx2["why"], "store": fx2["store"], "mdir": fx2["movers"]}

        def other_event(v):
            v["refs"] = [{"id": "fr-2026-20888", "text": "the Federal Register notice", "key": []}]
            v["cand"] = dict(v["cand"], id="fr-2026-20888")
        _put(fx2["vdir"], v14, "2026-10-20", "morning", "2026-10-20T12:18:00Z")
        _put(fx2["vdir"], v14, "2026-10-20", "evening", "2026-10-20T23:16:00Z", lambda v: (to_confirmed(v), other_event(v)))
        _put(fx2["vdir"], v14, "2026-10-21", "morning", "2026-10-21T12:18:00Z")
        _put(fx2["vdir"], v14, "2026-10-21", "evening", "2026-10-21T23:16:00Z", other_event)
        _put(fx2["vdir"], v14, "2026-10-22", "morning", "2026-10-22T12:18:00Z")
        _put(fx2["vdir"], v14, "2026-10-22", "evening", "2026-10-22T23:16:00Z")
        w = view_of(fx2, now=t("2026-10-22T23:30:00Z"))
        out = {(r["date_et"], r["slot"]): r["outcome"] for r in w["rows"]}
        guarded(fails, "SYNTHETIC: a later Confirmed on a different event reverses the Likely (another cause was confirmed)",
                lambda: out[("2026-10-20", "morning")] == "reversed")
        guarded(fails, "SYNTHETIC: a later Likely naming none of the Likely's events reverses it",
                lambda: out[("2026-10-21", "morning")] == "reversed")
        guarded(fails, "SYNTHETIC: a later Likely naming the same events leaves it awaiting (still no primary source)",
                lambda: out[("2026-10-22", "morning")] == "awaiting" and out[("2026-10-22", "evening")] == "awaiting")
        _ = vd
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 3. never inferred: identity of an event, what is not a verdict ------------------------------------------------

def _entry(key, day, slot, made, grade, events, links=(), sym="BTC"):
    return {"key": key, "date_et": day, "slot": slot, "made_utc": made, "grade": grade, "events": list(events),
            "links": list(links), "coin_sym": sym, "coin_slug": "bitcoin", "coin_name": "Bitcoin",
            "url": f"/why/{day}-bitcoin", "source": "verdict"}


def identity_cases(fails):
    print("3. an outcome is never inferred: the event's identity, and what is not a verdict")
    m = vr()
    a = _entry("a", "2026-10-20", "morning", "2026-10-20T12:18:00Z", "Likely", ["wire-c019"],
               ["https://www.theblock.co/news/regulation/2026-10-19-blackrock-files"])
    b_link = _entry("b", "2026-10-20", "evening", "2026-10-20T23:16:00Z", "Confirmed", ["wire-c044"],
                    ["https://www.theblock.co/news/regulation/2026-10-19-blackrock-files?utm_source=rss"])
    b_word = _entry("b", "2026-10-20", "evening", "2026-10-20T23:16:00Z", "Confirmed", ["wire-c044"],
                    ["https://www.coindesk.com/blackrock-bitcoin-etf"])
    guarded(fails, "a later Confirmed whose cluster id changed but whose source article is the same is the same event: confirmed",
            lambda: m.resolve([a, b_link])["a"]["outcome"] == "confirmed_later")
    guarded(fails, "a later Confirmed sharing only a word ('blackrock'), not an id or an article, is not the same event: reversed",
            lambda: m.resolve([a, b_word])["a"]["outcome"] == "reversed")
    other_day = _entry("c", "2026-10-21", "evening", "2026-10-21T23:16:00Z", "Confirmed", ["wire-c019"])
    guarded(fails, "a read on a later ET day is a different move: it resolves nothing, and the Likely stays awaiting",
            lambda: "a" not in m.resolve([a, other_day]))
    earlier = _entry("e", "2026-10-20", "morning", "2026-10-20T08:00:00Z", "Confirmed", ["wire-c019"])
    guarded(fails, "an earlier read never resolves a later Likely", lambda: "a" not in m.resolve([earlier, a]))
    same = _entry("s", "2026-10-20", "morning", "2026-10-20T12:40:00Z", "Likely", ["wire-c019"])
    guarded(fails, "the same slot re-stored with the same grade and events is not a second verdict and resolves nothing",
            lambda: len(m.dedupe([a, same])) == 1 and "a" not in m.resolve([a, same]))
    # no grade, no entry: the kinds that draw no graded card
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        vdir, wdir, mdir, store = (os.path.join(td, k) for k in ("verdict", "why", "movers", "store"))
        for p in (vdir, wdir, mdir, store):
            os.makedirs(p, exist_ok=True)
        for n in ("2026-10-19-evening.json", "2026-10-20-morning.json", "2026-10-20-evening.json"):
            shutil.copy(os.path.join(HERE, "site", "data", "verdict", n), vdir)
        v14, _v15 = _base()

        def withheld(v):
            v.update(kind="withheld", grade_withheld=v["grade"], grade=None, url=None)
        _put(vdir, v14, "2026-10-21", "evening", "2026-10-21T23:16:00Z", withheld)
        with quiet():
            es = m.entries(vdir, mdir, wdir)
        guarded(fails, "REAL 19 and 20 October (next read, flat, with Bitcoin, no grade fits) and a verdict withheld at the cap "
                       "are no entries: nothing ungraded is scored", lambda: es == [])
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 4. append-only and frozen -------------------------------------------------------------------------------------

def frozen_cases(fails):
    print("4. the record is stored append-only, and a stored entry or outcome is frozen")
    m = vr()
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td, with_movers=False)
        with quiet():
            got = m.sync(fx["vdir"], fx["mdir"], fx["wdir"], fx["store"], save=True)
        files = sorted(os.listdir(fx["store"]))
        n_ent = len([f for f in files if not f.endswith(".outcome.json")])
        n_out = len([f for f in files if f.endswith(".outcome.json")])
        guarded(fails, f"the first sync stores one file per graded verdict (6) and one per resolved Likely (2): {n_ent}, {n_out}",
                lambda: n_ent == 6 and n_out == 2 and len(got["written"]) == 8)
        snap = {f: open(os.path.join(fx["store"], f), "rb").read() for f in files}
        with quiet():
            again = m.sync(fx["vdir"], fx["mdir"], fx["wdir"], fx["store"], save=True)
        guarded(fails, "a second sync over the same records writes nothing", lambda: again["written"] == [])
        # the 14 October evening slot is rewritten (a newer read of the slot), now Unclear
        v14, v15 = _base()
        _put(fx["vdir"], v15, "2026-10-14", "evening", "2026-10-14T23:59:00Z")
        with quiet():
            third = m.sync(fx["vdir"], fx["mdir"], fx["wdir"], fx["store"], save=True)
        after = sorted(os.listdir(fx["store"]))
        guarded(fails, "a rewritten slot adds its new verdict and every stored file stays byte for byte",
                lambda: all(open(os.path.join(fx["store"], f), "rb").read() == b for f, b in snap.items())
                and len(after) == len(files) + 1 and len(third["written"]) == 1)
        with quiet():
            v = m.view(t("2026-10-17T23:30:00Z"), vdir=fx["vdir"], mdir=fx["mdir"], wdir=fx["wdir"], store=fx["store"])
        r14 = [r for r in v["rows"] if (r["date_et"], r["slot"]) == ("2026-10-14", "morning")][0]
        guarded(fails, "the stored outcome stands: 14 October morning stays confirmed later though its slot was regraded after",
                lambda: r14["outcome"] == "confirmed_later")
        guarded(fails, "the overwritten 14 October evening Confirmed is still in the record (published, then replaced)",
                lambda: [r["grade"] for r in v["rows"] if (r["date_et"], r["slot"]) == ("2026-10-14", "evening")]
                == ["Unclear", "Confirmed"])
        # an entry file never rewritten even when sync is handed one that differs
        k = sorted(f for f in files if not f.endswith(".outcome.json"))[0]
        p = os.path.join(fx["store"], k)
        before = open(p, "rb").read()
        with quiet():
            m.store_entry(fx["store"], dict(json.loads(before), grade="Disputed"))
        guarded(fails, "an entry already stored is never rewritten", lambda: open(p, "rb").read() == before)
        # the build's view never writes
        td2 = os.path.join(td, "s2")
        os.makedirs(td2)
        with quiet():
            m.view(t("2026-10-17T23:30:00Z"), vdir=fx["vdir"], mdir=fx["mdir"], wdir=fx["wdir"], store=td2)
        guarded(fails, "the build's read of the record writes no file", lambda: os.listdir(td2) == [])
    finally:
        shutil.rmtree(td, ignore_errors=True)
    src = lambda f: open(os.path.join(HERE, f), encoding="utf-8").read()
    body = lambda f, fn: src(f).split(f"\ndef {fn}(", 1)[1].split("\ndef ", 1)[0]
    guarded(fails, "the run steps store the record: verdict.py's main() calls _sync_record(), which calls verdict_record.sync, "
                   "and movers.py's main() calls verdict_record.sync",
            lambda: "_sync_record()" in body("verdict.py", "main") and "verdict_record.sync(save=True)" in body("verdict.py", "_sync_record")
            and "verdict_record.sync(save=True)" in body("movers.py", "main"))
    # a stored outcome is never recomputed, even when the records now say otherwise
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td, with_movers=False)
        with quiet():
            es = m.entries(fx["vdir"], fx["mdir"], fx["wdir"])
        k14 = next(e["key"] for e in es if (e["date_et"], e["slot"]) == ("2026-10-14", "morning"))
        m.store_outcome(fx["store"], {"key": k14, "outcome": "reversed", "basis": "later_read", "rule": "stored by an earlier run",
                                      "later": {"grade": "Unclear", "slot": "evening", "made_utc": "2026-10-14T23:00:00Z"}})
        with quiet():
            v = m.view(t("2026-10-17T23:30:00Z"), vdir=fx["vdir"], mdir=fx["mdir"], wdir=fx["wdir"], store=fx["store"])
            m.sync(fx["vdir"], fx["mdir"], fx["wdir"], fx["store"], save=True)
        got = json.load(open(os.path.join(fx["store"], k14 + ".outcome.json"), encoding="utf-8"))
        guarded(fails, "an outcome stored by an earlier run stands: never recomputed from the records, never rewritten by a sync",
                lambda: next(r for r in v["rows"] if r["key"] == k14)["outcome"] == "reversed" and got["outcome"] == "reversed")
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 5. the page ---------------------------------------------------------------------------------------------------

def page_cases(fails):
    print("5. the page: the tally, every verdict linked, windowed and labeled, nothing twice")
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td)
        v = view_of(fx)
        h = page_of(v)
        txt = visible(h)
        got = rc(h)
        guarded(fails, "each count prints exactly once, in the tally: " + ", ".join(RC_KEYS),
                lambda: all(len(got.get(k, [])) == 1 for k in RC_KEYS))
        guarded(fails, "the page's counts are the tally's", lambda: all(got[k][0] == WANT[k] for k in WANT))
        guarded(fails, "no count prints outside the tally (the same fact never twice)", lambda: outside_counts(h) == [])
        guarded(fails, "every graded verdict is listed and links to its /why/ address",
                lambda: all(f'href="{r["url"]}"' in h for r in v["rows"]) and h.count('class="vr-r"') == len(v["rows"]))
        win = re.search(r'<p class="vr-win[^"]*" data-asof="2026-10-17T23:16:00Z"[^>]*>(.*?)</p>', h, re.S)
        wt = visible(win.group(1)) if win else ""
        guarded(fails, "the window is labeled on the tally: from the first verdict record through the newest read, in ET, with the "
                       "newest read's data-asof", lambda: "Counted from" in wt and "8:18 AM ET on Oct 14, 2026" in wt
                and "7:16 PM ET on Oct 17, 2026" in wt)
        guarded(fails, "the page's own rules ride in its head, tokens only (the shared stylesheets stay Sprint 9.5's)",
                lambda: ".page .vr-tally{" in h.split("</head>", 1)[0]
                and not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|@font-face|url\(", vr().RECORD_STYLE))
        guarded(fails, "the page says how many verdicts are still awaiting a later source",
                lambda: re.search(r'data-rc="likely_awaiting"[^>]*>1<', h) and "awaiting" in txt.lower())
        guarded(fails, "'because' appears nowhere (the page prints no verdict sentence)", lambda: not BECAUSE.search(txt))
        guarded(fails, "no em or en dash, no AI word, no personal name",
                lambda: not DASH.search(h) and not AI.search(txt) and not PERSON.search(txt))
        guarded(fails, "the page is /why/record/: canonical, h1 'The verdict record', the Why it moved nav marked",
                lambda: f'<link rel="canonical" href="{ORIGIN}{URL}">' in h and "<h1>The verdict record</h1>" in h
                and re.search(r'href="/today/"[^>]*aria-current="page"', h))
        guarded(fails, "each outcome is said in words on its row: confirmed later, reversed, awaiting a later source",
                lambda: all(w in txt for w in ("Confirmed later", "Reversed", "Awaiting a later source")))
        guarded(fails, "the definitions are on the page: a later read of the same coin on the same ET day, and never confirmed "
                       "without a primary source", lambda: "same ET day" in txt and "primary source" in txt)
        # a /why/ address the build did not write gets no link
        built = {r["url"] for r in v["rows"] if r["coin_sym"] == "BTC"}
        v2 = view_of(fx, built=built)
        h2 = page_of(v2)
        guarded(fails, "a row whose /why/ page was not built links nowhere and says so",
                lambda: 'href="/why/2026-10-16-celestia"' not in h2 and "No page was built" in visible(h2))
        # stale: the site's one rule
        fresh = page_of(view_of(fx, now=t("2026-10-18T01:16:00Z")))
        old = page_of(view_of(fx, now=t("2026-10-18T04:16:01Z")))
        guarded(fails, "two hours after the newest read: not stale, no age printed (the browser adds it later)",
                lambda: 'class="vr-win"' in fresh and "hours ago" not in visible(fresh))
        guarded(fails, "five hours after: stale by snapshot.is_stale, the age printed once",
                lambda: 'class="vr-win stale"' in old and visible(old).count("5 hours ago") == 1)
        guarded(fails, "the view's stale flag is snapshot.is_stale on the newest read",
                lambda: view_of(fx, now=t("2026-10-18T02:16:00Z"))["stale"] is False
                and view_of(fx, now=t("2026-10-18T02:16:01Z"))["stale"] is True)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def empty_cases(fails):
    print("6. honest empty and degrade states: the page is always built")
    m = vr()
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        dirs = {k: os.path.join(td, k) for k in ("verdict", "why", "movers", "store")}
        for p in dirs.values():
            os.makedirs(p, exist_ok=True)
        with quiet():
            v = m.view(t("2026-10-25T18:00:00Z"), vdir=dirs["verdict"], mdir=dirs["movers"], wdir=dirs["why"], store=dirs["store"])
            h = m.render(v, "OCTOBER 25, 2026")
        txt = visible(h)
        guarded(fails, "no stored record at all: the page builds, every count zero, and it says no record is stored yet",
                lambda: all(x == [0] for x in rc(h).values()) and len(rc(h)) == len(RC_KEYS)
                and "No verdict record is stored yet" in txt)
        guarded(fails, "no stored record: no as-of is claimed for the record", lambda: not re.search(r'class="vr-win[^"]*"[^>]*data-asof', h))
        # REAL: the stored 19 and 20 October records graded nothing
        for n in ("2026-10-19-evening.json", "2026-10-20-morning.json", "2026-10-20-evening.json"):
            shutil.copy(os.path.join(HERE, "site", "data", "verdict", n), dirs["verdict"])
        for n in ("2026-10-20-morning.json", "2026-10-20-evening.json"):
            shutil.copy(os.path.join(HERE, "site", "data", "movers", n), dirs["movers"])
        with quiet():
            v = m.view(t("2026-10-25T18:00:00Z"), vdir=dirs["verdict"], mdir=dirs["movers"], wdir=dirs["why"], store=dirs["store"])
            h = m.render(v, "OCTOBER 25, 2026")
        txt = visible(h)
        guarded(fails, "REAL 19 and 20 October: zero graded, the page says no move has been graded since the record began",
                lambda: v["counts"]["likely"] == 0 and "No move has been graded" in txt and "Oct 19, 2026" in txt
                and "7:16 PM ET" in txt)
        guarded(fails, "REAL: the reads that ran are counted (3 of Bitcoin and Ether, 2 of Big movers)",
                lambda: rc(h).get("reads_coins") == [3] and rc(h).get("reads_movers") == [2])
        guarded(fails, "REAL: stale on October 25 (the newest read is October 20), the age printed once",
                lambda: 'class="vr-win stale"' in h and txt.count("days ago") == 1)
        # zero resolved
        v14, _v15 = _base()
        vd2 = os.path.join(td, "v2")
        os.makedirs(vd2)
        _put(vd2, v14, "2026-10-16", "evening", "2026-10-16T23:16:00Z")
        with quiet():
            v = m.view(t("2026-10-17T00:00:00Z"), vdir=vd2, mdir=dirs["movers"] + "-none", wdir=dirs["why"], store=dirs["store"])
            h = m.render(v, "OCTOBER 17, 2026")
        guarded(fails, "SYNTHETIC one Likely, nothing resolved: it says no Likely verdict has a later source yet",
                lambda: "No Likely verdict has a later source yet" in visible(h) and rc(h)["likely_awaiting"] == [1])
        # the build writes the page whatever happens
        import site_build as sb
        written = {}
        with quiet():
            sb._write_verdict_record(lambda rel, html: written.__setitem__(rel, html), "OCTOBER 25, 2026", built=set(),
                                     vdir=os.path.join(td, "nothing"), mdir=os.path.join(td, "nothing"),
                                     wdir=os.path.join(td, "nothing"), store=os.path.join(td, "nothing"))
        guarded(fails, "the build writes why/record/index.html with no stored record (never omitted on empty)",
                lambda: "why/record/index.html" in written and "The verdict record" in written["why/record/index.html"])
        real = m.render
        written.clear()
        try:
            def boom(*a, **k):
                raise RuntimeError("planted")
            m.render = boom
            with quiet():
                sb._write_verdict_record(lambda rel, html: written.__setitem__(rel, html), "OCTOBER 25, 2026", built=set(),
                                         vdir=dirs["verdict"], mdir=dirs["movers"], wdir=dirs["why"], store=dirs["store"])
        finally:
            m.render = real
        guarded(fails, "when the record cannot be drawn the page is still written, and says the record could not be read",
                lambda: "why/record/index.html" in written and "could not be read" in visible(written["why/record/index.html"]))
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 7. the feed and the index -------------------------------------------------------------------------------------

def feed_cases(fails):
    print("7. the feed under /api/v1/ in 9.7's shape, and in the index")
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td)
        now = t("2026-10-17T23:30:00Z")
        v = view_of(fx, now=now)
        f = vr().feed(v, now)
        guarded(fails, "the envelope: schema, version, name, path, page, as_of_utc, built_utc, stale, sources, data",
                lambda: all(k in f for k in ("schema", "version", "name", "path", "page", "as_of_utc", "built_utc", "stale",
                                             "stale_after_hours", "sources", "data"))
                and f["path"] == "/api/v1/why/record.json" and f["page"] == URL and f["name"] == "why/record")
        guarded(fails, "as_of_utc is the newest read; stale is the site's rule", lambda: f["as_of_utc"] == "2026-10-17T23:16:00Z"
                and f["stale"] is False and vr().feed(v, t("2026-10-18T03:00:00Z"))["stale"] is True)
        guarded(fails, "the feed's counts are the page's", lambda: all(f["data"]["counts"][k] == WANT[k] for k in WANT))
        guarded(fails, "the feed lists every verdict with its address, grade and outcome, and the window it counts",
                lambda: len(f["data"]["verdicts"]) == 11 and all(x["url"] and x["grade"] for x in f["data"]["verdicts"])
                and f["data"]["window"]["begins_utc"] == "2026-10-14T12:18:00Z")
        json.dumps(f, allow_nan=False)
        import api_feeds as af
        with quiet():
            allf = af.build_all({"now": now, "pulse": None, "snap": None, "flows": None, "items": [], "wire": None, "ed": None,
                                 "morning": None, "movers_rec": None, "board_tiles": [], "coin_tiles": {},
                                 "vdir": fx["vdir"], "wdir": fx["wdir"], "mdir": fx["mdir"], "rstore": fx["store"]})
        guarded(fails, "build_all writes why/record.json and the index lists it with its as-of and stale flag",
                lambda: "why/record.json" in allf and any(r["path"] == "/api/v1/why/record.json"
                                                         and r["as_of_utc"] == "2026-10-17T23:16:00Z"
                                                         for r in allf["index.json"]["data"]["feeds"]))
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ---- 8. the links to it --------------------------------------------------------------------------------------------

def link_cases(fails):
    print("8. linked from How we check and from every /why/ page; in the sitemap")
    import site_build as sb
    with quiet():
        h = sb.render_method([], "OCTOBER 25, 2026")
    guarded(fails, "How we check links the verdict record", lambda: f'href="{URL}"' in h)
    td = tempfile.mkdtemp(prefix="s98-")
    try:
        fx = fixture(td)
        import verdict as vd
        import movers as mv
        with quiet():
            vp = vd.build_pages(vdir=fx["vdir"], wdir=fx["wdir"], tdir=os.path.join(td, "today"))
            mp = mv.build_pages(directory=fx["mdir"])
        guarded(fails, f"every Bitcoin /why/ page links the record ({len(vp)})", lambda: vp and all(f'href="{URL}"' in p["html"] for p in vp))
        guarded(fails, f"every Big movers /why/ page links the record ({len(mp)})", lambda: mp and all(f'href="{URL}"' in p["html"] for p in mp))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    locs = src.split("    locs = [", 1)[1].split("]", 1)[0]
    guarded(fails, "the sitemap's priority list names /why/record/ (read in the tree cases too)", lambda: '"/why/record/"' in locs)


def unit():
    fails = []
    for name, fn in (("tally", tally_cases), ("reversed", reversed_cases), ("identity", identity_cases),
                     ("frozen", frozen_cases), ("page", page_cases), ("empty", empty_cases), ("feed", feed_cases),
                     ("links", link_cases)):
        group(fails, name, fn)
    return fails


# ---- the built tree ------------------------------------------------------------------------------------------------

def tree(root):
    fails = []
    print(f"9. the built tree {root}")
    pub = lambda rel: os.path.join(root, rel)
    rd = lambda rel: open(pub(rel), encoding="utf-8", errors="replace").read() if os.path.exists(pub(rel)) else ""
    h = rd("why/record/index.html")
    guarded(fails, "why/record/index.html is built", lambda: "<h1>The verdict record</h1>" in h)
    if not h:
        return fails
    try:
        f = json.loads(rd("api/v1/why/record.json"))
    except ValueError:
        f = {}
    guarded(fails, "api/v1/why/record.json is built in 9.7's shape",
            lambda: f.get("name") == "why/record" and "as_of_utc" in f and "stale" in f and "data" in f)
    try:
        idx = json.loads(rd("api/v1/index.json"))
    except ValueError:
        idx = {}
    guarded(fails, "the api index lists it", lambda: any(r["path"] == "/api/v1/why/record.json" for r in idx["data"]["feeds"]))
    got = rc(h)
    guarded(fails, "each count prints once, and equals the feed's",
            lambda: all(len(got.get(k, [])) == 1 for k in RC_KEYS)
            and all(got[k][0] == f["data"]["counts"][k] for k in f["data"]["counts"])
            and got["reads_coins"][0] == f["data"]["reads"]["coins"] and got["reads_movers"][0] == f["data"]["reads"]["movers"])
    guarded(fails, "no count prints outside the tally", lambda: outside_counts(h) == [])
    rows = re.findall(r'<li class="vr-r".*?</li>', h, re.S)
    hrefs = re.findall(r'<li class="vr-r".*?href="(/why/[^"]+)"', h, re.S)
    guarded(fails, f"every listed verdict links to a /why/ page this tree holds ({len(rows)} listed)",
            lambda: len(hrefs) == len(rows) and all(os.path.exists(pub(x.lstrip("/") + ".html")) for x in hrefs))
    guarded(fails, "the page's as-of is the feed's", lambda: (f.get("as_of_utc") is None and not re.search(r'class="vr-win[^"]*"[^>]*data-asof', h))
            or re.search(r'class="vr-win[^"]*" data-asof="' + re.escape(str(f.get("as_of_utc"))) + '"', h))
    guarded(fails, "no 'because', no dash, no AI word, no personal name",
            lambda: not BECAUSE.search(visible(h)) and not DASH.search(h) and not AI.search(visible(h)) and not PERSON.search(visible(h)))
    guarded(fails, "the sitemap's priority file lists /why/record/", lambda: f"<loc>{ORIGIN}{URL}</loc>" in rd("sitemap-priority.xml"))
    guarded(fails, "How we check links it", lambda: f'href="{URL}"' in rd("method.html"))
    pages = sorted(n for n in os.listdir(pub("why")) if n.endswith(".html")) if os.path.isdir(pub("why")) else []
    guarded(fails, f"every /why/ verdict page links it ({len(pages)})", lambda: all(f'href="{URL}"' in rd("why/" + n) for n in pages))
    return fails


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1])
    print(f"\nSPRINT 9.8: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
