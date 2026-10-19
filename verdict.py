#!/usr/bin/env python3
"""
verdict.py: the verdict under "Why it moved" (Program 9, Sprint 9.3; AUDIT.md section 3.1, layer 4).

THE GRADE IS COMPUTED HERE, NEVER CHOSEN BY A MODEL. It reads one evidence record (why_evidence.py,
9.2) and grades each coin by the rules below. A model only writes the two sentences that say it, from
finished phrases this file builds (8.2's phrases.py rule: every figure, sign and window already in
words; the model copies phrases whole), and a stronger model checks them, stating `stands` per claim
(the wrap.check rule). Any failure prints the graded line built from the same phrases, with no model
sentence: an unchecked sentence never prints.

THE GRADES (AUDIT.md 3.1; Jack's ruling 1 of October 16):
  Confirmed  a primary source, or two independent outlets, state the cause; the timing test passes;
             the market readings agree. The only grade whose line says "because".
  Likely     the timing test passes and the readings agree, with no source stating the cause; or a
             source states it and the timing passes while the readings are silent. Says "lines up with".
  Disputed   a reported cause fails the timing test, or the readings contradict it. Shows both sides.
  Unclear    nothing passes the timing test: "No reported event lines up with this move", and the
             onset hour's readings still print. When an event passes the timing test with no report
             naming it and no reading behind it, the grade is Unclear too, and its line says so (it
             cannot say no event lines up, because one does in time).
  No grade   Bitcoin flat (within 0.5%, Program 8's rule): "Flat: nothing to explain". Ether within 2
             points of Bitcoin: one line, "Ether moved with Bitcoin".

THE TIMING TEST (the onset question carried from 9.2). 9.2's onset is the start of the largest run
measured from the window's own peak, so on 14 October it is 4:10 AM ET and CPI at 8:30 AM reads
"after the run began", although 8.5% of the run was done before it and the hour after it carried
71.2% of the fall. A candidate passes when EITHER
  (a) 9.2's own test: it came within 60 minutes before the onset, or the onset fell at its
      scheduled release time, and the price had not moved first; OR
  (b) the price had not moved first, measured strictly: no more than TIMING["done_max_pct"] of the
      run was done before it, AND at least TIMING["share_min_pct"] of the window's move came in the
      60 minutes after it.
9.2's onset and its printed figures are unchanged; this file only reads them.

THE READINGS (the mechanics) are those of the hour the run began, so they can speak only to a
candidate within 60 minutes of the onset; for any other candidate they are silent. A macro event
(a US release, the Fed, a rate or inflation report) agrees with "risk-off/on across assets" and is
contradicted by "crypto only"; a crypto event agrees with "crypto only" or "coin-specific" and is
contradicted by a move across assets. "Leverage flush" is a mechanism, not a cause, and is silent.

THE SPEND (ruling 2): every model call is priced by llm.py at the 5.5 rates and the run writes one row
to data/verdict-ledger.json with the day's total, printed against the $1.50 cap. A call that could
take the day past the cap is not made; the verdict fails open.

    python3 verdict.py --write        # the run's step, after why_evidence.py; exits 0 whatever happens
"""
import datetime as _dt
import html as _html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "site", "data", "verdict")
LEDGER = os.path.join(HERE, "data", "verdict-ledger.json")

# ---- the rules, in one place ------------------------------------------------------------------------------

# The timing test's second path (see the docstring). lead_min is 9.2's own and is read from it.
TIMING = {"lead_min": 60, "done_max_pct": 25.0, "share_min_pct": 40.0}
FLAT_PCT = 0.5                 # Program 8: Bitcoin within plus or minus 0.5% is flat
WITH_BTC_PTS = 2.0             # Ether within 2 points of Bitcoin's move "moved with Bitcoin"
MECH_REACH_S = 3600            # the onset hour's readings speak to a candidate within 60 minutes of it
CAP_USD = 1.50                 # ruling 2: new model spend for the why, capped at $1.50 a day
DEADLINE_S = 100               # the run step's own budget; the workflow's timeout is 150
MODEL_DRAFT = "claude-haiku-5-5"
MODEL_CHECK = "claude-sonnet-5-5"
CFG = {"models": {"verdict_draft": {"model": MODEL_DRAFT, "max_tokens": 3000},
                  "verdict_check": {"model": MODEL_CHECK, "max_tokens": 6000}},
       "budget": {"max_tokens_per_run": 120000, "max_usd_per_run": CAP_USD}}
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")
RANK = {"Confirmed": 0, "Disputed": 1, "Likely": 2, "Unclear": 3}
DEFINITIONS = {
    "Confirmed": "A primary source or two outlets state the cause, the timing test passes, and the market "
                 "readings agree.",
    "Likely": "The timing test passes and the market readings agree, or a report states the cause and the "
              "timing passes while the readings are silent.",
    "Disputed": "A reported cause fails the timing test, or the market readings contradict it.",
    "Unclear": "No reported event passes the timing test with a report or the market readings behind it.",
}
NAMES = {"BTC": ("Bitcoin", "bitcoin"), "ETH": ("Ether", "ether")}
NO_EVENT = "No reported event lines up with this move."
GRADE_WORDS = re.compile(r"\b(confirmed|likely|disputed|unclear)\b", re.I)
BECAUSE = re.compile(r"\bbecause\b", re.I)
DASH = re.compile("[\u2013\u2014]")

# "A source states the cause": the line names the coin (or crypto), a price move, and a link between
# the event and the move. Grep-class, and in code: no model decides it.
SUBJECT = {"BTC": r"\b(bitcoin|btc|crypto\w*|digital assets?)\b",
           "ETH": r"\b(ether|eth|ethereum|crypto\w*|digital assets?)\b"}
MOVE = re.compile(r"\b(fell|falls?|falling|dropp\w*|drops?|slid|slides?|sliding|slump\w*|tumbl\w*|plung\w*|"
                  r"sank|sinks?|rose|rises?|rising|rall(?:y|ied|ies|ying)|jump\w*|surg\w*|climb\w*|soar\w*|"
                  r"liquidat\w*|sell-?offs?|selloffs?)\b|\b(?:below|above|under|past) \$", re.I)
LINK = re.compile(r"\b(because|due to|driven by|caused by|owing to|after|amid|following|on the back of|as|"
                  r"send\w*|sent|trigger\w*|spark\w*|push\w*|drag\w*|lift\w*|knock\w*|weigh\w*|hit|fuel\w*|"
                  r"prompt\w*|led to)\b", re.I)
MACRO = re.compile(r"\b(inflation|cpi|consumer price|producer[- ]price|ppi|payrolls?|jobs report|unemployment|"
                   r"gdp|fed|federal reserve|fomc|rate[- ](?:hike|cut)s?|interest rates?|treasury yields?|"
                   r"bond yields?|tariffs?)\b", re.I)


def _we():
    import why_evidence
    return why_evidence


def _parse(s):
    return _we()._parse_utc(s)


def _iso(t):
    return _we()._iso(t)


def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


# ---- the timing test, the statement, the readings -----------------------------------------------------------

def timing_pass(r):
    """'lead' (9.2's own test), 'share' (the second path), or None. `r` is a 9.2 timing result."""
    if not r or not r.get("in_window", True):
        return None
    if r.get("moved_first"):
        return None
    if r.get("before_onset"):
        return "lead"
    share, done = r.get("share_pct"), r.get("done_pct")
    if (isinstance(share, (int, float)) and isinstance(done, (int, float))
            and done <= TIMING["done_max_pct"] and share >= TIMING["share_min_pct"]):
        return "share"
    return None


def stated(c, sym):
    """(states the cause, outlets, primary) for a candidate. A release's statement is its first
    report's; a wire item's is its own line. Commentary (9.2's secondary mark) states nothing."""
    if c.get("secondary"):
        return False, 0, False
    text = c.get("line") if c.get("kind") in ("wire", "press") else (c.get("report_line") or "")
    text = str(text or "")
    ok = bool(text) and bool(re.search(SUBJECT.get(sym, SUBJECT["BTC"]), text, re.I)) and bool(
        MOVE.search(text)) and bool(LINK.search(text))
    n = int(c.get("source_count") or 0)
    primary = ok and ((c.get("kind") == "wire" and bool(c.get("primary"))) or c.get("kind") == "press")
    return ok, n, primary


def is_macro(c):
    if c.get("kind") == "release":
        return True
    outlet = " ".join(l.get("outlet") or "" for l in c.get("links") or [])
    if c.get("kind") == "press" and "Federal Reserve" in (outlet + " " + c.get("line", "")):
        return True
    return bool(MACRO.search(str(c.get("line") or "") + " " + str(c.get("report_line") or "")))


def _labels(pats, rows):
    """(labels, shut). A stock market that was shut is not a reading: 9.2 labels "crypto only" when
    stock futures stayed quiet OR did not trade, and on a weekend every crypto move is "crypto only".
    For the grade, and for the verdict's words, it counts only when the futures traded in that hour;
    `shut` says the label was set aside for that reason."""
    labels = [p.get("label") for p in pats or [] if p.get("label")]
    traded = any(r.get("key") in ("ES=F", "NQ=F") and r.get("value") is not None for r in rows or [])
    if "crypto only" in labels and not traded:
        return [l for l in labels if l != "crypto only"], True
    return labels, False


def mech_fit(c, coin, t):
    """(fit, labels, hour): what the market readings say of this candidate. fit is 'agree',
    'contradict' or 'silent'; hour is 'after' (the readings of the hour after the candidate, stored by
    the evidence record since 9.3) or 'onset' (the hour the run began, which speaks only to a
    candidate within 60 minutes of it). A record written before 9.3 has only the onset hour."""
    run = (coin or {}).get("run")
    if t is None or not run:
        return "silent", [], None
    after = ((coin.get("event_hours") or {}).get(c.get("id")) or {})
    if after.get("patterns") is not None and after.get("rows"):
        pats, rows, hour = after.get("patterns") or [], after["rows"], "after"
    elif abs(t - run["start_t"]) <= MECH_REACH_S:
        m = coin.get("mechanics") or {}
        pats, rows, hour = m.get("patterns") or [], m.get("rows") or [], "onset"
    else:
        return "silent", [], None
    labels, _shut = _labels(pats, rows)
    across = any(l.endswith("across assets") for l in labels)
    if is_macro(c):
        fit = "agree" if across else "contradict" if "crypto only" in labels else "silent"
    elif "crypto only" in labels or "coin-specific" in labels:
        fit = "agree"
    else:
        fit = "contradict" if across else "silent"
    return fit, [l for l in labels if l], hour


# ---- the phrases -------------------------------------------------------------------------------------------

def _move(coin):
    pts = ((coin or {}).get("series") or {}).get("points") or []
    if len(pts) < 2 or not pts[0][1]:
        return None
    return (pts[-1][1] / pts[0][1] - 1.0) * 100.0


def _words(direction):
    return ("fall", "fell") if direction == "down" else ("rise", "rose")


def _ref(c, t, w1):
    """The candidate as a noun phrase with its time, from its own line."""
    we = _we()
    line = " ".join(str(c.get("line") or "").split()).rstrip(".")
    when = we.day_clock(t, w1) if t is not None else "an unknown time"
    k = c.get("kind")
    if k == "release":
        return f"the {line}, released at {when}"
    if k == "press" and not (BECAUSE.search(line) or GRADE_WORDS.search(line)):
        return f'"{line}", published at {when}'
    if k == "hack":
        return f"the {line}, at {when}"
    outlet = next((l.get("outlet") for l in c.get("links") or [] if l.get("outlet")), "the wire")
    if BECAUSE.search(line) or GRADE_WORDS.search(line):
        # a line that says "because" or carries a grade word is never quoted in the verdict (9.2's rule
        # for its section): the verdict's own grade decides those words, never a quoted line
        return f"a report from {outlet} at {when}"
    return f'the report "{line}" ({outlet}, {when})'


def _reported_phrase(c, n, ref):
    """The reported side of a Disputed verdict, in the report's own words. It never says which way
    the report said the price went: the report's direction is its own, not the window's."""
    if c.get("kind") in ("wire", "press"):
        if ref.startswith("the report "):
            return f"{_outlets(n or 1)} reported a cause: {ref[len('the report '):]}."
        return f"{_outlets(n or 1)} reported a cause: {ref}."
    return f"{_outlets(n or 1)} reported {ref} as a cause."


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _outlets(n):
    return {1: "One outlet", 2: "Two outlets", 3: "Three outlets"}.get(n, f"{n} outlets")


def _timing_phrase(path, r, c, fall):
    if path == "lead":
        if c.get("scheduled") and abs(r.get("lead_min") or 0) <= _we().SCHEDULED_TOL_MIN:
            return "The run began at its scheduled release time."
        return "It came within the hour before the run began."
    share = r.get("share_pct") or 0
    most = "Most" if share >= 50 else "A large share"
    return f"{most} of the {fall} came in the 60 minutes after it, and the price had not moved first."


def _against_phrase(r, name, fall):
    if r.get("moved_first"):
        return "The price moved first: most of the run was done before it."
    share = r.get("share_pct")
    if isinstance(share, (int, float)) and share < 0:
        return f"In the 60 minutes after it, {name} moved against the {fall}."
    if isinstance(share, (int, float)) and share < TIMING["share_min_pct"]:
        return f"Little of the {fall} came in the 60 minutes after it."
    return "It came well before the run began."


def _mech_phrase(coin, labels=None, hour="onset"):
    shut = False
    if labels is None:
        m = coin.get("mechanics") or {}
        labels, shut = _labels(m.get("patterns"), m.get("rows"))
    when = "In the hour after it" if hour == "after" else "In the hour the run began"
    if shut and not labels:
        return f"{when}, stock futures did not trade, so the market readings cannot tell a crypto move from a wider one."
    if labels:
        return f"{when}, the market readings show {' and '.join(labels)}."
    return f"{when}, the market readings show none of the four patterns the desk names."


# ---- the grade ------------------------------------------------------------------------------------------------

def grade(rec, sym):
    """The computed verdict for one coin of an evidence record: {sym, name, kind, grade, cand, dir,
    reasons, phrases, line, required}. `kind` is graded, flat, with_btc or none. Never raises for a
    record that lacks a coin; it returns kind none."""
    we = _we()
    name, word = NAMES.get(sym, (sym, sym.lower()))
    out = {"sym": sym, "name": name, "kind": "none", "grade": None, "cand": None, "dir": None,
           "reasons": [], "phrases": [], "line": [], "required": []}
    coins = (rec or {}).get("coins") or {}
    coin = coins.get(sym)
    mv = _move(coin)
    if mv is None:
        return out
    out["move_pct"] = round(mv, 3)
    if sym == "ETH":
        b = _move(coins.get("BTC"))
        if b is not None and abs(mv - b) < WITH_BTC_PTS:
            out.update(kind="with_btc", line=["Ether moved with Bitcoin."],
                       reasons=[f"its move was within {WITH_BTC_PTS:g} points of Bitcoin's over the window"])
            return out
    if abs(mv) <= FLAT_PCT:
        out.update(kind="flat", line=["Flat: nothing to explain."],
                   reasons=[f"the move was within {FLAT_PCT:g}% over the window"])
        return out
    run = coin.get("run")
    if not run:
        return out
    wend = _parse((rec.get("window") or {}).get("end_utc"))
    w1 = int(wend.timestamp()) if wend else coin["series"]["points"][-1][0]
    fall, fell = _words(run["dir"])
    out.update(kind="graded", dir=run["dir"])
    tests = {t["id"]: t for t in coin.get("tests") or []}
    graded = []
    for c in rec.get("candidates") or []:
        if c.get("secondary"):
            continue
        tst = tests.get(c["id"]) or {}
        r = tst.get("result")
        tu = _parse(tst.get("t_utc"))
        t = int(tu.timestamp()) if tu else None
        path = timing_pass(r)
        st, n, prim = stated(c, sym)
        fit, labels, hour = mech_fit(c, coin, t)
        measured = bool(r and r.get("in_window") and r.get("share_pct") is not None)
        g = None
        if st and path and fit == "agree" and (prim or n >= 2):
            g = "Confirmed"
        elif st and measured and (not path or fit == "contradict"):
            g = "Disputed"
        elif path and fit == "agree":
            g = "Likely"
        elif st and path and fit == "silent":
            g = "Likely"
        elif path:
            g = "timing"
        if g:
            graded.append({"g": g, "c": c, "r": r, "t": t, "path": path, "stated": st, "outlets": n,
                           "primary": prim, "fit": fit, "labels": labels, "hour": hour})
    real = [x for x in graded if x["g"] in RANK]
    if real:
        best = min(real, key=lambda x: (RANK[x["g"]], -(x["r"].get("share_pct") or 0), x["t"] or 0))
    else:
        best = next(iter(sorted([x for x in graded if x["g"] == "timing"],
                                key=lambda x: (-(x["r"].get("share_pct") or 0), x["t"] or 0))), None)
    mech = _mech_phrase(coin)
    if best is None or best["g"] == "timing":
        out["grade"] = "Unclear"
        if best is None:
            out["phrases"] = [NO_EVENT, mech]
            out["reasons"] = ["no candidate passes the timing test"]
        else:
            ref = _ref(best["c"], best["t"], w1)
            out["phrases"] = [f"{_cap(ref)} came in time with the {fall}, but no report names it as the cause "
                              f"and the market readings do not show it.", mech]
            out["reasons"] = ["a candidate passes the timing test, with no report stating it and no reading "
                              "behind it"]
            out["cand"] = _cand(best)
        out["line"] = list(out["phrases"])
        out["required"] = [0]
        return out
    c, r, t, ref = best["c"], best["r"], best["t"], _ref(best["c"], best["t"], w1)
    out["grade"], out["cand"] = best["g"], _cand(best)
    support = []
    if best["stated"]:
        support.append("A primary source states it as the cause." if best["primary"]
                       else f"{_outlets(best['outlets'] or 1)} reported it as the cause.")
    if best["fit"] == "agree":
        support.append(_mech_phrase(coin, best["labels"], best["hour"]))
    if best["g"] == "Confirmed":
        out["phrases"] = [f"{name} {fell} because of {ref}.", _timing_phrase(best["path"], r, c, fall)] + support
        out["reasons"] = ["a source states it", "the timing test passes", "the readings agree"]
    elif best["g"] == "Likely":
        out["phrases"] = [f"{name}'s {fall} lines up with {ref}.", _timing_phrase(best["path"], r, c, fall)] + support
        out["reasons"] = ["the timing test passes"] + (["the readings agree"] if best["fit"] == "agree"
                                                       else ["a report states it; the readings are silent"])
    else:
        side = (_against_phrase(r, name, fall) if not best["path"] else
                _mech_phrase(coin, best["labels"], best["hour"])[:-1] + ", which does not fit it.")
        out["phrases"] = [_reported_phrase(c, best["outlets"], ref), side]
        if mech not in side:
            out["phrases"].append(mech)
        out["reasons"] = ["a report states it", "the timing test fails" if not best["path"]
                          else "the readings contradict it"]
    out["line"] = out["phrases"][:2]
    out["required"] = [0, 1] if best["g"] == "Disputed" else [0]
    return out


def _cand(x):
    c = x["c"]
    return {"id": c["id"], "kind": c.get("kind"), "line": c.get("line"), "t_utc": _iso(x["t"]) if x["t"] else None,
            "timing": x["path"], "stated": x["stated"], "outlets": x["outlets"], "primary": x["primary"],
            "readings": x["fit"], "readings_hour": x["hour"], "patterns": x["labels"]}


# ---- the model: a draft from phrases, a check that states `stands` per claim -------------------------------------

DRAFT_SYSTEM = (
    "You write the two-sentence verdict for a crypto price move on a news site. The grade is computed "
    "elsewhere and printed separately; never write a grade word (Confirmed, Likely, Disputed, Unclear). "
    "Use ONLY the phrases you are given. Copy each phrase you use WHOLE, word for word, with its figures, "
    "times and quotation marks exactly as given. You may join two phrases into one sentence with \", and\" "
    "or \"; \" and you may lowercase a phrase's first letter after a join; you may not add, drop or change "
    "any other word. Never add a cause, a prediction or advice. Never use a dash. The phrases listed as "
    "REQUIRED must appear. Respond ONLY with JSON: {\"sentences\": [\"<sentence one>\", \"<sentence two>\"]}.")

CHECK_SYSTEM = (
    "You check a two-sentence market verdict against the ONLY facts it may use: the phrases it was written "
    "from. List every claim each sentence makes. For each claim write your reasoning FIRST, then decide. "
    "A claim stands only when the phrases carry it exactly: the same event, time, direction and figure, "
    "and nothing added. A claim does not stand when it adds a cause, a time, a figure, a direction, a "
    "prediction or advice that the phrases do not carry, or when it states a cause more strongly than the "
    "phrases do. Respond ONLY with JSON: {\"claims\": [{\"sentence\": <1 or 2>, \"claim\": \"<the words>\", "
    "\"why\": \"<your reasoning, 1 to 3 sentences, written first>\", \"stands\": <true|false, decided after "
    "writing why>}]}. Every sentence must have at least one claim.")


def draft_user(v):
    req = [v["phrases"][i] for i in v["required"]]
    return (f"COIN: {v['name']}\nGRADE (printed separately, never write it): {v['grade']}\n"
            f"PHRASES:\n{json.dumps(v['phrases'], ensure_ascii=False)}\n"
            f"REQUIRED:\n{json.dumps(req, ensure_ascii=False)}\n"
            "Write exactly two sentences from these phrases.")


def check_user(v, sents):
    return (f"PHRASES:\n{json.dumps(v['phrases'], ensure_ascii=False)}\n"
            f"SENTENCES:\n{json.dumps(sents, ensure_ascii=False)}\n")


_JOINS = (", and ", "; ", " and ")


def _covered(s, bodies):
    """True when sentence `s` is whole phrases joined by the allowed joins, ending in a period."""
    s = " ".join(s.split())
    if not s.endswith("."):
        return False
    s = s[:-1]

    def heads(b):
        return {b, b[:1].lower() + b[1:], b[:1].upper() + b[1:]}
    seen = set()
    stack = [0]
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        for b in bodies:
            for h in heads(b):
                if h and s.startswith(h, i):
                    j = i + len(h)
                    if j == len(s):
                        return True
                    for jn in _JOINS:
                        if s.startswith(jn, j):
                            stack.append(j + len(jn))
    return False


def belts(v, sents):
    """'' when the draft may go to the check, else why not. Deterministic, before any check."""
    if not isinstance(sents, list) or len(sents) != 2 or not all(isinstance(s, str) and s.strip() for s in sents):
        return "the draft is not exactly two sentences"
    bodies = [p.rstrip(".") for p in v["phrases"]]
    for s in sents:
        if DASH.search(s):
            return "a sentence carries a dash"
        if BECAUSE.search(s) and v["grade"] != "Confirmed":
            return "'because' on a verdict that is not Confirmed"
        if GRADE_WORDS.search(s):
            return "a sentence carries a grade word"
        if not _covered(s, bodies):
            return "a sentence is not built from whole phrases"
    joined = " ".join(sents).lower()
    for i in v["required"]:
        if bodies[i].lower()[1:] not in joined:
            return "a required phrase is missing"
    return ""


def _validate_draft(obj):
    import llm
    s = obj.get("sentences") if isinstance(obj, dict) else None
    if not isinstance(s, list) or not all(isinstance(x, str) for x in s):
        raise llm.LLMError("verdict_draft: no 'sentences' list of strings")
    return [" ".join(x.split()) for x in s]


def _validator_check(n):
    def ok(obj):
        import llm
        cl = obj.get("claims") if isinstance(obj, dict) else None
        if not isinstance(cl, list) or not cl:
            raise llm.LLMError("verdict_check: no 'claims' list")
        for c in cl:
            if (not isinstance(c, dict) or not isinstance(c.get("stands"), bool)
                    or not isinstance(c.get("sentence"), int) or not 1 <= c["sentence"] <= n):
                raise llm.LLMError("verdict_check: a claim item is out of contract")
        if {c["sentence"] for c in cl} != set(range(1, n + 1)):
            raise llm.LLMError("verdict_check: a sentence was left unjudged")
        return cl
    return ok


class Spend:
    """The run's spend through llm.Budget, and the day's before it, against the cap. A call is made
    only when its worst case (its prompt, and every output token it may take, at the 5.5 rates) still
    fits under the cap."""

    def __init__(self, day_before, cap):
        import llm
        self.day_before, self.cap = day_before, cap
        self.budget = llm.Budget(CFG["budget"]["max_tokens_per_run"], cap)

    def allows(self, stage, system, user):
        import llm
        mc = CFG["models"][stage]
        pin, pout = llm.PRICING.get(mc["model"], llm.DEFAULT_PRICE)
        worst = ((len(system) + len(user)) / 3.0 * pin + mc["max_tokens"] * pout) / 1_000_000
        return self.day_before + self.budget.usd + worst <= self.cap


def _model(v, client, spend, gate):
    """(sentences, None) when the model's two sentences pass every check; (None, why) otherwise."""
    import llm
    if client is None:
        return None, "no model client"
    if STOP["set"]:
        return None, f"the step's {DEADLINE_S}s budget is spent"
    du = draft_user(v)
    if not spend.allows("verdict_draft", DRAFT_SYSTEM, du):
        return None, f"the day's spend would pass the ${spend.cap:.2f} cap"
    try:
        sents = client.call_json("verdict_draft", DRAFT_SYSTEM, du, validate=_validate_draft, max_rungs=1)
    except llm.LLMError as e:
        return None, f"the draft failed ({str(e)[:120]})"
    why = belts(v, sents)
    if why:
        return None, f"the draft failed its belt: {why}"
    cu = check_user(v, sents)
    if STOP["set"]:
        return None, f"the step's {DEADLINE_S}s budget is spent"
    if not spend.allows("verdict_check", CHECK_SYSTEM, cu):
        return None, f"the check would take the day's spend past the ${spend.cap:.2f} cap"
    try:
        claims = client.call_json("verdict_check", CHECK_SYSTEM, cu, validate=_validator_check(len(sents)),
                                  max_rungs=1)
    except llm.LLMError as e:
        return None, f"the check failed ({str(e)[:120]})"
    v["check"] = claims
    down = [c for c in claims if c["stands"] is not True]
    if down:
        return None, f"the check withdrew {len(down)} claim(s): {str(down[0].get('claim'))[:80]!r}"
    if gate is not None:
        for s in sents:
            if gate.text(s, "the verdict", dollars=True).strip() != s.strip():
                return None, "the twins gate dropped a model sentence"
    return sents, None


# ---- the record ------------------------------------------------------------------------------------------------

def slug(date_et, sym):
    return f"{date_et}-{NAMES.get(sym, (sym, sym.lower()))[1]}"


def url(date_et, sym):
    return f"/why/{slug(date_et, sym)}"


def record_from(rec, date_et, slot, now=None, gate=None):
    """The verdict record for an evidence record, every coin on its graded line (no model)."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    out = {"what": "The verdict under 'Why it moved': the grade computed by code from the evidence record "
                   "(why_evidence.py), the graded line built from phrases, and the model's two checked "
                   "sentences when they passed every check.",
           "date_et": date_et, "slot": slot, "window": (rec or {}).get("window"),
           "evidence_made_utc": (rec or {}).get("made_utc"),
           "made_utc": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "timing_rule": dict(TIMING), "coins": {}}
    for sym in ("BTC", "ETH"):
        v = grade(rec, sym)
        if v["kind"] == "none":
            continue
        if gate is not None:
            v["line"] = [s for s in v["line"] if gate.text(s, "the verdict (phrases)", dollars=True).strip()]
        v.update(text=list(v["line"]), by="phrases", fail_reason=None, corrections=[],
                 url=url(date_et, sym) if v["grade"] else None)
        out["coins"][sym] = v
    return out


def _ledger_rows(path):
    try:
        rows = json.load(open(path, encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def day_spend(date_et, path=None):
    return round(sum(float(r.get("usd") or 0) for r in _ledger_rows(path or LEDGER) if r.get("date") == date_et), 6)


def write_run(rec, date_et, slot, gate=None, ledger_path=None, directory=None, save=True, cap=None,
              client=None, now=None):
    """Grade, write each graded coin's two sentences through the model and its check (failing open to
    the graded line), append the run's spend row to the ledger and print the day against the cap.
    Returns (verdict record, ledger row). The record is saved only when `save`."""
    import llm
    cap = CAP_USD if cap is None else cap
    ledger_path = ledger_path or LEDGER
    now = now or _dt.datetime.now(_dt.timezone.utc)
    out = record_from(rec, date_et, slot, now=now, gate=gate)
    before = day_spend(date_et, ledger_path)
    spend = Spend(before, cap)
    if client is None and os.environ.get("ANTHROPIC_API_KEY", "").strip():
        client = llm.Client(CFG, mode="live", budget=spend.budget)
    elif client is not None:
        client.budget = spend.budget
    for sym, v in out["coins"].items():
        if not v["grade"]:
            continue
        try:
            sents, why = _model(v, client, spend, gate)
        except _Late as e:                           # out of time: this coin, and any after it, fail open
            sents, why = None, str(e)
        except Exception as e:                       # never a gate on a slot: the graded line prints
            sents, why = None, f"the model path raised {type(e).__name__}: {str(e)[:100]}"
        if sents:
            v.update(text=sents, by="model", fail_reason=None)
        else:
            v.update(text=list(v["line"]), by="phrases",
                     fail_reason=why if client is not None else "no API key; no model call")
    s = spend.budget.summary()
    usd = round(spend.budget.usd, 6)
    row = {"date": date_et, "slot": slot, "t": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "calls": s["calls"], "tokens": s["tokens"], "usd": usd, "by_stage": s["by_stage"],
           "models": {k: m["model"] for k, m in CFG["models"].items()},
           "day_usd": round(before + usd, 6), "cap_usd": cap,
           "coins": {k: (f"{v['grade']} ({v['by']})" if v["grade"] else v["kind"]) for k, v in out["coins"].items()}}
    out["spend"] = row
    rows = _ledger_rows(ledger_path) + [row]
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    json.dump(rows[-400:], open(ledger_path, "w", encoding="utf-8"), indent=1)
    print(f"verdict: spend this run ${usd:.4f} ({s['calls']} call(s), {s['tokens']:,} tokens); "
          f"today ${row['day_usd']:.4f} of the ${cap:.2f} cap")
    for sym, v in out["coins"].items():
        print(f"verdict: {sym} {v['grade'] or v['kind']}" + (f" ({v['by']}" + (f": {v['fail_reason']}" if v.get(
            "fail_reason") else "") + ")" if v["grade"] else ""))
    if save:
        p = record_path(date_et, slot, directory)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
        print(f"verdict: wrote {p}")
    return out, row


def record_path(date_et, slot, directory=None):
    return os.path.join(directory or DIR, f"{date_et}-{slot}.json")


def load(date_et, slot, directory=None):
    try:
        r = json.load(open(record_path(date_et, slot, directory), encoding="utf-8"))
        return r if isinstance(r, dict) and isinstance(r.get("coins"), dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _names(directory=None):
    d = directory or DIR
    try:
        return sorted(n for n in os.listdir(d) if re.fullmatch(r"\d{4}-\d{2}-\d{2}-(morning|evening)\.json", n))
    except OSError:
        return []


def latest(directory=None):
    for n in sorted(_names(directory), key=lambda n: (n[:10], n.endswith("evening.json")), reverse=True):
        r = load(n[:10], n[11:-5], directory)
        if r:
            return r
    return None


def current(vrec, board_utc, max_gap_h=18):
    """The record when its window ended within `max_gap_h` hours of the Board reading a page carries
    (a morning verdict stands until the evening's, the evening's overnight); None otherwise. The card
    names its own window and carries its stamp for the stale state, so it is never shown as live."""
    if not vrec:
        return None
    a = _parse((vrec.get("window") or {}).get("end_utc"))
    b = _parse(board_utc)
    if a is None or b is None or abs((a - b).total_seconds()) > max_gap_h * 3600:
        return None
    return vrec


# ---- the card: one shape on the home, /today/, the coin pages and the verdict page --------------------------------

def card_html(vrec, sym, where="today", live=False, corrections=None, link=True):
    """The card for one coin, or '' (fail open). `where` is home, today, coin or page; the shape is
    the same everywhere. `corrections` are the page's own; the verdict's own always render."""
    try:
        return _card(vrec, sym, where, live, corrections, link)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::verdict: the card for {sym} was not drawn ({type(e).__name__}: {e})")
        return ""


def _card(vrec, sym, where, live, corrections, link):
    we = _we()
    v = ((vrec or {}).get("coins") or {}).get(sym)
    if not v or v.get("kind") not in ("graded", "flat", "with_btc"):
        return ""
    name = v.get("name") or sym
    wend = _parse(((vrec or {}).get("window") or {}).get("end_utc"))
    if wend is None:
        return ""
    w1 = int(wend.timestamp())
    asof = f' data-asof="{_e(_iso(w1))}"' if live else ""
    win = f'<p class="vd-win"{asof}>The 24 hours to {_e(we.clock(w1))}, {_e(we.long_day(w1))}</p>'
    if v["kind"] == "flat":
        body, cls = '<p class="vd-line vd-flat">Flat: nothing to explain.</p>', "flat"
    elif v["kind"] == "with_btc":
        body, cls = '<p class="vd-line vd-with">Ether moved with Bitcoin.</p>', "with"
    else:
        g = v["grade"]
        if g not in GRADES:
            return ""
        cls = g.lower()
        text = " ".join(v.get("text") or v.get("line") or [])
        body = (f'<p class="vd-grade"><span class="vd-badge vd-{cls}">Checked: <b>{_e(g)}</b></span> '
                f'<span class="vd-def">{_e(DEFINITIONS[g])}</span></p>'
                + (f'<p class="vd-line">{_e(text)}</p>' if text else ""))
    corr, seen = "", set()
    for c in list(v.get("corrections") or []) + list(corrections or []):
        t = str((c or {}).get("text") or "").strip()
        if t and t not in seen:
            seen.add(t)
            corr += f'<p class="vd-corr"><b>Correction, {_e(c.get("date"))}.</b> {_e(t)}</p>'
    more = ""
    if link and v.get("url") and where != "page":
        more = f'<p class="vd-more"><a href="{_e(v["url"])}">The verdict and its evidence</a></p>'
    return (f'<aside class="vd vd-{cls}" data-vd="{_e(sym)}" aria-label="Why {_e(name)} moved">'
            f'<h2 class="vd-h">Why {_e(name)} moved</h2>{win}{body}{corr}{more}</aside>')


# ---- the verdict pages: /why/<date>-<coin> ---------------------------------------------------------------------

SLOT_LABEL = {"morning": "Morning read", "evening": "Evening Edition"}


def build_pages(vdir=None, wdir=None, tdir=None, dateline=""):
    """[{rel, html, path, lastmod, published_utc, title}] for every graded verdict: one URL per day
    and coin, kept once it exists. The page shows the day's newest graded slot first and any earlier
    one under it, each with its card, and the evidence of the slot it leads with."""
    we = _we()
    by_day = {}
    for n in _names(vdir):
        r = load(n[:10], n[11:-5], vdir)
        if r:
            by_day.setdefault(n[:10], []).append(r)
    out = []
    for day, recs in sorted(by_day.items()):
        recs.sort(key=lambda r: r.get("slot") == "evening", reverse=True)
        for sym in ("BTC", "ETH"):
            graded = [r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade")]
            if not graded:
                continue
            try:
                out.append(_page(day, sym, recs, graded[0], vdir, wdir, tdir, dateline))
            except Exception as e:                               # noqa: BLE001
                print(f"::warning::verdict: /why/{slug(day, sym)} was not built ({type(e).__name__}: {e})")
    return out


def _today_corrections(day, slot, tdir):
    try:
        p = os.path.join(tdir or os.path.join(HERE, "site", "data", "today"), f"{day}-{slot}.json")
        return json.load(open(p, encoding="utf-8")).get("corrections") or []
    except (OSError, ValueError):
        return []


def _page(day, sym, recs, lead, vdir, wdir, tdir, dateline):
    import site_build as sb
    we = _we()
    name = NAMES[sym][0]
    d = _dt.date.fromisoformat(day)
    when = f"{d.strftime('%A, %B')} {d.day}, {d.year}"
    title = f"Why {name} moved: {when}"
    blocks = []
    for r in recs:
        corr = _today_corrections(day, r.get("slot"), tdir)
        card = card_html(r, sym, where="page", live=False, corrections=corr, link=False)
        if not card:
            continue
        label = SLOT_LABEL.get(r.get("slot"), r.get("slot") or "")
        head = ("" if r is lead else f'<h2 class="td-h3">Earlier, the {_e(label.lower())}</h2>')
        blocks.append(head + card)
    ev = we.load(day, lead.get("slot"), wdir)
    ev_html = we.section_html(ev, sym, live=False, corrections=_today_corrections(day, lead.get("slot"), tdir)) if ev else ""
    v = lead["coins"][sym]
    pub = lead.get("made_utc") or ""
    stamp = SLOT_LABEL.get(lead.get("slot"), "")
    body = f"""<main class="wrap"><section class="page td-page vd-page">
  <span class="kicker">Why it moved</span>
  <h1>{_e(title)}</h1>
  <p class="td-stamp">{_e(stamp)}</p>
  {"".join(blocks)}
  {ev_html}
  <p class="td-w">The day's answer, with what moved and what was reported, is at <a href="/today/{_e(day)}">/today/{_e(day)}</a>.</p>
</section></main>"""
    path = f"/why/{slug(day, sym)}.html"
    canon = sb.ORIGIN + url(day, sym)
    desc = " ".join(v.get("text") or v.get("line") or [])[:200]
    schema = json.dumps({"@context": "https://schema.org", "@graph": [{
        "@type": "NewsArticle", "headline": title, "url": canon, "mainEntityOfPage": canon,
        "description": desc, "datePublished": _et_iso(min(r.get("made_utc") or pub for r in recs)),
        "dateModified": _et_iso(pub),
        "author": {"@type": "Organization", "name": sb.NAME, "url": sb.ORIGIN + "/news.html"},
        "publisher": {"@type": "Organization", "@id": sb.ORIGIN + "/#publisher", "name": sb.FAMILY,
                      "url": sb.ORIGIN + "/",
                      "logo": {"@type": "ImageObject", "url": sb.ORIGIN + "/publisher-logo-512.png",
                               "width": 512, "height": 512}}}]}, ensure_ascii=False)
    html = sb.shell(f"{title} - {sb.NAME}", desc, "Today", body, dateline, path=path, og_type="article",
                    schema_extra=f'\n<script type="application/ld+json">{schema}</script>')
    return {"rel": f"why/{slug(day, sym)}.html", "html": html, "path": url(day, sym), "lastmod": pub,
            "published_utc": min(r.get("made_utc") or pub for r in recs), "title": title}


def _et_iso(utc):
    t = _parse(utc)
    return t.astimezone(_we().ET).isoformat() if t else ""


# ---- the run's step ----------------------------------------------------------------------------------------------

class _Late(BaseException):
    """The step's time budget is spent. A BaseException on purpose: llm.py's retry loop catches
    Exception, and a deadline it swallowed would be retried past the budget."""


STOP = {"set": False}          # set when the step's budget is spent: no further call starts


def main():
    if "--write" not in sys.argv[1:]:
        print(__doc__.split("\n\n")[-1])
        return 2
    try:
        import signal
        import why_evidence as we

        def late(*_a):
            STOP["set"] = True
            raise _Late(f"the step's {DEADLINE_S}s budget is spent")
        signal.signal(signal.SIGALRM, late)
        signal.signal(signal.SIGTERM, late)
        signal.alarm(DEADLINE_S)
        import site_build as sb
        import snapshot as _s
        import twins_gate
        now = _dt.datetime.now(_dt.timezone.utc)
        date, slot, _composed = we._slot_now(now)
        ev = we.load(date, slot)
        if not ev:
            print(f"verdict: no evidence record for {date}-{slot}; no verdict written")
            return 0
        if load(date, slot) and (load(date, slot).get("evidence_made_utc") or "") >= (ev.get("made_utc") or ""):
            print(f"verdict: {date}-{slot}.json already stored; a stored verdict is frozen")
            return 0
        pulse, flows = sb.load_pulse(), sb.load_flows()
        gate = twins_gate.Gate(_s.build(pulse, flows), log_path="", quiet=True)
        try:
            write_run(ev, date, slot, gate=gate, now=now)
        except _Late as e:
            # out of time mid-call: the graded lines, no model sentence, and the ledger says so
            print(f"::warning::verdict: {e}; writing the graded lines with no model sentence")
            signal.alarm(0)
            out = record_from(ev, date, slot, now=now, gate=gate)
            for v in out["coins"].values():
                if v["grade"]:
                    v["fail_reason"] = str(e)
            p = record_path(date, slot)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
            print(f"verdict: wrote {p} (graded lines only; any spend before the cut is in the API's own "
                  f"usage, not this run's ledger row)")
        signal.alarm(0)
    except Exception as e:                                       # never a gate on a slot
        print(f"::warning::verdict: no verdict written ({type(e).__name__}: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
