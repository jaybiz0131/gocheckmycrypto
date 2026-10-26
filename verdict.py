#!/usr/bin/env python3
"""
verdict.py: the verdict under "Why it moved" (Program 9, Sprint 9.3; AUDIT.md section 3.1, layer 4).

THE GRADE IS COMPUTED HERE, NEVER CHOSEN BY A MODEL. It reads one evidence record (why_evidence.py,
9.2) and grades each coin by the rules below. A model only writes the two sentences that say it, from
finished phrases this file builds (8.2's phrases.py rule: the model copies phrases whole), and a stronger
model checks them, stating `stands` per claim (the wrap.check rule). A failure prints the graded line built
from the same phrases; an unchecked sentence never prints.

THE RULES (the strategist's rulings of October 19, 2026, docs/RULINGS.md):
  The window  the one /today/ uses: the ET day, midnight ET to the reading, from the Board's open_et
              (basis et_day); the rolling 24 hours only when open_et is absent (basis rolling_24h). The
              card's direction words name that window ("since midnight ET", "over the last 24 hours").
  No card     a move under the threshold: Bitcoin flat (within 0.5%) on that window; Ether within 2
              points of Bitcoin (one plain line, "Ether moved with Bitcoin", on the Ether page). When the
              window moved the other way from the run the timing test measured there is no card either, and
              the page prints "Verdict at the next read" in its place (October 20, J-8 b).
  Unclear     printed definition: "No reported event passes the timing test with the market readings and the
              move's direction agreeing." Card: no candidate passes, "No reported event lines up with this move."
              Also (October 20, J-8 a and J-9 item 3) an event that lines up in time with nothing to support
              it: "A reported event lines up in time, but the market readings do not match it." or, for an event
              with a direction of its own that the move ran against, "A reported event lines up in time, but
              the move ran the other way." Each names the event.
  Disputed    outlets name different causes, or a named cause fails the timing test while another event
              passes it. The card names both.
  Likely      the reported events that pass the timing test, with the market readings agreeing: one card
              naming each of them (the 14 October pair of 8:30 AM releases). Events that point opposite ways
              are Disputed and the card states both.
  Confirmed   a primary source states the cause, the timing test passes and the readings agree. The only
              grade whose line says "because".
  On the ET day, only events from an hour before midnight ET onward are graded.

THE TIMING TEST reads its thresholds from why_evidence.TIMING_TEST (one versioned constant): 25% or more of the
run done before the event's first report disqualifies it; it passes when it came within the hour before the run began, or when
40% of the move came in the hour after it. 9.2's onset and printed figures are unchanged.

THE READINGS: the hour after the event when the record stores it, else the hour the run began (which
speaks only to an event within 60 minutes of it). A macro event agrees with "risk-off/on across assets"; a
crypto event with "crypto only" or "coin-specific". A shut stock market is no reading.

THE EVENT IS NAMED, NEVER QUOTED: by its subject ("the CFTC proposal"), built in code from its line. On a
page that also prints the evidence list, the name carries a pointer to the one listed item it means, and
that item is marked; the time, figures and wording stay in the list only.

THE SPEND (rulings 2 of October 16 and 4 of October 19): every model attempt, retries included, is reserved
in data/verdict-ledger.json at its worst-case cost before it is made and settled to its actual cost after,
so a call cut off by the deadline still counts. An attempt that would take the day past $1.50 is not made,
and the verdict is withheld: the card says the desk's check did not run today, never a guess.

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

# ---- the rules, in one place (the timing thresholds are why_evidence.TIMING_TEST's, never copied here) -----

FLAT_PCT = 0.5                 # Program 8: Bitcoin within plus or minus 0.5% is flat
WITH_BTC_PTS = 2.0             # Ether within 2 points of Bitcoin's move "moved with Bitcoin"
MECH_REACH_S = 3600            # the onset hour's readings speak to a candidate within 60 minutes of it
CAP_USD = 1.50                 # ruling 2 of October 16: new model spend for the why, capped at $1.50 a day
DEADLINE_S = 100               # the run step's own budget; the workflow's timeout is 150
MODEL_DRAFT = "claude-haiku-5-5"
MODEL_CHECK = "claude-sonnet-5-5"
CFG = {"models": {"verdict_draft": {"model": MODEL_DRAFT, "max_tokens": 3000},
                  "verdict_check": {"model": MODEL_CHECK, "max_tokens": 6000}},
       "budget": {"max_tokens_per_run": 120000, "max_usd_per_run": CAP_USD}}
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")
DEFINITIONS = {
    "Confirmed": "A primary source states the cause, the timing test passes, and the market readings agree.",
    "Likely": "The reported events that pass the timing test, with the market readings agreeing.",
    "Disputed": "Outlets name different causes, or one named cause fails the timing test while another passes, or "
                "the events that pass point opposite ways.",
    "Unclear": "No reported event passes the timing test with the market readings and the move's direction agreeing.",
}
NAMES = {"BTC": ("Bitcoin", "bitcoin"), "ETH": ("Ether", "ether")}
NO_EVENT = "No reported event lines up with this move."
# The strategist's rulings of October 20, 2026 (J-8, J-9 item 3): the two cards an event that lines up in time can
# still get when nothing else supports it, and the notice that stands where no card can be drawn.
READINGS_MISMATCH = "A reported event lines up in time, but the market readings do not match it."
OTHER_WAY = "A reported event lines up in time, but the move ran the other way."
NEXT_READ = "Verdict at the next read"
# SPRINT 9.9.1 (the strategist's ruling on J-8 of October 20 and Review 1): the notice always prints why and the time of the next
# read, in one line. The two reasons: the window flipped since the run, or no read yet today. The words are drawn, never stored: a
# stored record keeps its ruled line (J-10).
WHY_FLIPPED = "the window flipped since the run"
WHY_NO_READ = "no read yet today"
CAP_LINE = "The desk's check of this move did not run today."
WINDOW_WORDS = {"et_day": "since midnight ET", "rolling_24h": "over the last 24 hours"}
GRADE_WORDS = re.compile(r"\b(confirmed|likely|disputed|unclear)\b", re.I)
BECAUSE = re.compile(r"\bbecause\b", re.I)
DASH = re.compile("[\\u2013\\u2014]")

# "A source states the cause": the line names the coin (or crypto), a price move, and a link between
# the event and the move. Grep-class, and in code: no model decides it.
SUBJECT = {"BTC": r"\b(bitcoin|btc|crypto\w*|digital assets?)\b",
           "ETH": r"\b(ether|eth|ethereum|crypto\w*|digital assets?)\b"}
MOVE = re.compile(r"\b(fell|falls?|falling|dropp\w*|drops?|slid|slides?|sliding|slump\w*|tumbl\w*|plung\w*|"
                  r"sank|sinks?|rose|rises?|rising|rall(?:y|ied|ies|ying)|jump\w*|surg\w*|climb\w*|soar\w*|"
                  r"liquidat\w*|sell-?offs?|selloffs?|lower|higher)\b|\b(?:below|above|under|past) \$", re.I)
LINK = re.compile(r"\b(because|due to|driven by|caused by|owing to|after|amid|following|on the back of|as|"
                  r"send\w*|sent|trigger\w*|spark\w*|push\w*|drag\w*|lift\w*|knock\w*|weigh\w*|hit|fuel\w*|"
                  r"prompt\w*|led to)\b", re.I)
MACRO = re.compile(r"\b(inflation|cpi|consumer price|producer[- ]price|ppi|payrolls?|jobs report|unemployment|"
                   r"gdp|fed|federal reserve|fomc|rate[- ](?:hike|cut)s?|interest rates?|treasury yields?|"
                   r"bond yields?|tariffs?)\b", re.I)

# THE SUBJECT OF AN EVENT, by code: a macro report by its kind, else the line's leading name and the noun of
# its first action. No figure, no time, no quotation.
MACRO_SUBJ = [(r"producer[- ]price", "the producer-price data"),
              (r"consumer price|\bcpi\b|\binflation\b", "the inflation data"),
              (r"\bpayrolls?\b|jobs report", "the jobs report"),
              (r"\bfomc\b|rate decision|federal reserve", "the Fed decision"),
              (r"\btariffs?\b", "the tariff news")]
ACTIONS = [("agreed to acquire", "acquisition"), ("to acquire", "acquisition"), ("acquired", "acquisition"),
           ("proposed", "proposal"), ("halted", "halt"), ("launched", "launch"), ("authorized", "authorization"),
           ("classified", "classification"), ("confirmed", "confirmation"), ("dismantled", "takedown"),
           ("approved", "approval"), ("filed", "filing"), ("sued", "lawsuit"), ("charged", "charges"),
           ("announced", "announcement"), ("delisted", "delisting"), ("listed", "listing"), ("hacked", "hack"),
           ("exploited", "exploit"), ("drained", "drain"), ("froze", "freeze"), ("seized", "seizure"),
           ("banned", "ban"), ("partnered", "partnership"), ("integrated", "integration"),
           ("upgraded", "upgrade"), ("released", "release"), ("settled", "settlement"), ("fined", "fine")]
GENERIC_KEYS = {"bitcoin", "ether", "btc", "eth", "crypto", "et"}

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
    """'lead' (it came within the hour before the run began), 'share' (40% or more of the move in the hour
    after it), or None. 25% or more of the run done before it disqualifies it (twenty-five exactly does:
    the strategist's ruling of October 20, 2026). The thresholds are
    why_evidence.TIMING_TEST's. `r` is a 9.2 timing result."""
    tt = _we().TIMING_TEST
    if not r or not r.get("in_window", True):
        return None
    done, share = r.get("done_pct"), r.get("share_pct")
    if r.get("moved_first") or (isinstance(done, (int, float)) and done >= tt["done_max_pct"]):
        return None
    if r.get("before_onset"):
        return "lead"
    if isinstance(share, (int, float)) and isinstance(done, (int, float)) and share >= tt["share_min_pct"]:
        return "share"
    return None


def day_moves(pulse, date_et):
    """The window /today/ uses, from the Board: {basis, date, BTC, ETH}. The ET day (price over open_et,
    rounded as the snapshot rounds it) when the Board carries Bitcoin's open_et for `date_et`; else the
    rolling 24 hours (basis rolling_24h). Ether is read on the same basis or not at all. None with no
    Bitcoin reading."""
    rows = {c.get("symbol"): c for c in (((pulse or {}).get("movers") or {}).get("top100") or [])}

    def et(sym):
        r = rows.get(sym) or {}
        if (isinstance(r.get("open_et"), (int, float)) and r["open_et"] > 0 and r.get("open_et_day") == date_et
                and isinstance(r.get("price"), (int, float))):
            return round((r["price"] / r["open_et"] - 1.0) * 100.0, 2)
        return None

    def h24(sym):
        v = (rows.get(sym) or {}).get("chg_24h_pct")
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    if et("BTC") is not None:
        return {"basis": "et_day", "date": date_et, "BTC": et("BTC"), "ETH": et("ETH")}
    if h24("BTC") is None:
        return None
    return {"basis": "rolling_24h", "date": date_et, "BTC": h24("BTC"), "ETH": h24("ETH")}


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


# SPRINT 9.4, review 1: AN EVENT'S OWN DIRECTION. A listing is new demand and lines up only with a rise; a
# delisting, an unlock (new supply) or a hack on the coin itself lines up only with a fall. The other way it
# contradicts, whatever the readings show. A hack is directional only for a Big mover, whose candidates name
# the coin; a DeFi exploit beside Bitcoin or Ether is not Bitcoin's or Ether's own, and their grading is 9.3's.
DIRECTION = {"listing": "up", "delisting": "down", "unlock": "down", "hack": "down"}


def own_direction(c, sym=None):
    """The direction an event carries of its own ('up' or 'down'), or None. A hack is directional only for a
    Big mover, never beside Bitcoin or Ether."""
    want = DIRECTION.get(c.get("kind"))
    if want and c.get("kind") == "hack" and sym in ("BTC", "ETH", None):
        want = None
    return want


def mech_fit(c, coin, t, sym=None):
    """(fit, labels, hour): what the market readings say of this candidate. fit is 'agree',
    'contradict' or 'silent'; hour is 'after' (the readings of the hour after the candidate, stored by
    the evidence record since 9.3) or 'onset' (the hour the run began, which speaks only to a
    candidate within 60 minutes of it). A record written before 9.3 has only the onset hour. An event
    with a direction of its own (DIRECTION) contradicts a run the other way, and agrees only with a run
    its way that the readings call coin-specific or crypto only."""
    run = (coin or {}).get("run")
    if t is None or not run:
        return "silent", [], None
    want = own_direction(c, sym)
    if want and run.get("dir") != want:
        return "contradict", [], None
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
    if want:
        fit = "agree" if ("crypto only" in labels or "coin-specific" in labels) else "silent"
    elif is_macro(c):
        fit = "agree" if across else "contradict" if "crypto only" in labels else "silent"
    elif "crypto only" in labels or "coin-specific" in labels:
        fit = "agree"
    else:
        fit = "contradict" if across else "silent"
    return fit, [l for l in labels if l], hour


# ---- the phrases ----------------------------------------------------------------------------------------------

def _move(coin):
    pts = ((coin or {}).get("series") or {}).get("points") or []
    if len(pts) < 2 or not pts[0][1]:
        return None
    return (pts[-1][1] / pts[0][1] - 1.0) * 100.0


def _words(direction):
    return ("fall", "fell") if direction == "down" else ("rise", "rose")


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _list(items):
    """'A', 'A and B', 'A, B and C'."""
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _outlets(n):
    return {1: "One outlet", 2: "Two outlets", 3: "Three outlets"}.get(n, f"{n} outlets")


def _shown_outlet(c):
    """The outlet the evidence list prints beside the item (its first report's when it has one)."""
    return next((l.get("outlet") for l in (c.get("report_links") or c.get("links") or []) if l.get("outlet")),
                "the wire")


def _entity(line):
    out = []
    for tok in line.split():
        w = tok.strip(",.;:()")
        if w and (w[0].isupper() or w == "&"):
            out.append(w)
            if len(out) == 3:
                break
        else:
            break
    return " ".join(out)


def subject(c):
    """(name, key) for a candidate: its subject in words and the words that find it in the list. Built
    from its own line by code; no time, no figure, no quotation."""
    line = " ".join(str(c.get("line") or "").split()).rstrip(".")
    k = c.get("kind")
    if k == "release":
        name = re.split(r"[,(]", line)[0].strip()
        if name and not re.search(r"\d", name) and not (BECAUSE.search(name) or GRADE_WORDS.search(name)):
            return f"the {name} release", [name]
    if k == "hack":
        name = line.split(" exploit")[0].strip()
        if name and not re.search(r"\d", name):
            return f"the {name} exploit", [name]
    # SPRINT 9.4: a Big mover's own candidates, named by what they are and whose notice it is
    if k in ("listing", "delisting"):
        outlet = _shown_outlet(c)
        return f"the {outlet} {k} notice", [outlet]
    if k == "unlock":
        return "the token unlock", ["token unlock"]
    for rx, subj in MACRO_SUBJ:
        m = re.search(rx, line, re.I)
        if m and k != "release":
            return subj, [m.group(0)]
    ent = _entity(line)
    if not ent or re.search(r"\d", ent) or BECAUSE.search(ent) or GRADE_WORDS.search(ent):
        outlet = _shown_outlet(c)
        return f"the {outlet} report", [outlet]
    rest = " " + re.sub(r"[,;:]", " ", line[len(ent):].lower()) + " "
    hits = sorted((rest.find(" " + a + " "), noun) for a, noun in ACTIONS if (" " + a + " ") in rest)
    noun = hits[0][1] if hits else None
    key = [ent.split("'s ")[-1] if "'s " in ent else ent]
    if "'s" in ent:
        return f"the {noun or 'report'} by {ent}", key
    return f"the {ent} {noun or 'report'}", key


def _listed_text(c):
    return " ".join([str(c.get("line") or ""), str(c.get("report_line") or "")]
                    + [l.get("outlet") or "" for l in (c.get("report_links") or c.get("links") or [])])


def named(c, cands):
    """{id, text, key}: the subject, made to find one listed item. When its words also find another
    listed candidate, the outlet the list prints beside it is added; when that still finds two, the key is
    left empty and the item's marker alone identifies it."""
    text, key = subject(c)

    def finds(cc, toks):
        t = _listed_text(cc).lower()
        return all(tk.lower() in t for tk in toks)
    others = [o for o in cands if o.get("id") != c.get("id")]
    generic = any(tk.lower() in GENERIC_KEYS for tk in key)
    if generic or any(finds(o, key) for o in others):
        outlet = _shown_outlet(c)
        text, key = f"{text}, as {outlet} reported it", key + [outlet]
        if generic or any(finds(o, key) for o in others):
            key = []
    return {"id": c.get("id"), "text": text, "key": key}


def _ref_full(c, t, w1, nm):
    """The event with its time, for a page with no evidence list beside the card (the home)."""
    if t is None:
        return nm["text"]
    when = _we().day_clock(t, w1)
    k = c.get("kind")
    if k == "release":
        return f"{nm['text']} ({when})"
    # Sprint 9.4, review 1: "reported" only where an outlet reported it
    if k == "unlock":
        return f"{nm['text']} (scheduled for {when}, as CoinMarketCap lists it)"
    if k in ("listing", "delisting"):
        return f"{nm['text']} (announced {when})"
    return f"{nm['text']} (reported {when})"


def _timing_phrase(path, r, c):
    if path == "lead":
        if c.get("scheduled") and abs(r.get("lead_min") or 0) <= _we().SCHEDULED_TOL_MIN:
            return "The run began at its scheduled release time."
        return "It came within the hour before the run began."
    share = r.get("share_pct") or 0
    most = "Most" if share >= 50 else "A large share"
    return f"{most} of the move the timing test measures came in the 60 minutes after it, and the price had not moved first."


def _against_phrase(r, name):
    tt = _we().TIMING_TEST
    done, share = r.get("done_pct"), r.get("share_pct")
    if r.get("moved_first") or (isinstance(done, (int, float)) and done >= tt["done_max_pct"]):
        return "A quarter or more of the run was done before it."
    if isinstance(share, (int, float)) and share < 0:
        return f"In the 60 minutes after it, {name} moved against the run."
    if isinstance(share, (int, float)) and share < tt["share_min_pct"]:
        return "Less of the move than the timing test needs came in the 60 minutes after it."
    return "It came too long before the run began."


def _mech_sec(coin, labels, hour, shut=False):
    """The readings phrase on a page that prints the section: the onset hour's reading is the section's
    to print, so it is dropped (''); the hour after an event stays, unless it reads as the onset hour
    did, which the section already says."""
    if hour != "after":
        return ""
    m = coin.get("mechanics") or {}
    on = _labels(m.get("patterns"), m.get("rows"))
    if (sorted(labels or []), bool(shut)) == (sorted(on[0]), bool(on[1])):
        return "In the hour after it, the market readings read as they did in the hour the run began."
    return _mech_phrase(coin, labels, hour)


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

def grade(rec, sym, day=None):
    """The computed verdict for one coin: {sym, name, kind, grade, basis, window_words, cand, refs, dir,
    reasons, phrases, phrases_sec, line, required, readings}. kind is graded, flat, with_btc, no_verdict or
    none; only graded draws a card. `day` is day_moves(); without it the record's own series stands in, as
    the rolling 24 hours. Never raises for a record that lacks a coin."""
    we = _we()
    name, _w = NAMES.get(sym, (sym, sym.lower()))
    out = {"sym": sym, "name": name, "kind": "none", "grade": None, "cand": None, "refs": [], "dir": None,
           "reasons": [], "phrases": [], "phrases_sec": [], "line": [], "required": [], "readings": None}
    coins = (rec or {}).get("coins") or {}
    coin = coins.get(sym)
    series_mv = _move(coin)
    if series_mv is None:
        return out
    if not day or not isinstance(day.get("BTC"), (int, float)):
        day = {"basis": "rolling_24h", "BTC": _move(coins.get("BTC")), "ETH": _move(coins.get("ETH"))}
    basis = day.get("basis") if day.get("basis") in WINDOW_WORDS else "rolling_24h"
    mv = day.get(sym)
    out.update(basis=basis, window_words=WINDOW_WORDS[basis])
    if sym == "ETH":
        b = day.get("BTC")
        if not isinstance(mv, (int, float)):
            out.update(kind="no_verdict", reasons=["Ether has no reading on the page's window"])
            return out
        if isinstance(b, (int, float)) and abs(mv - b) < WITH_BTC_PTS:
            out.update(kind="with_btc", line=["Ether moved with Bitcoin."],
                       reasons=[f"within {WITH_BTC_PTS:g} points of Bitcoin {WINDOW_WORDS[basis]}"])
            return out
    if not isinstance(mv, (int, float)):
        return out
    out["move_pct"] = mv
    if abs(mv) <= FLAT_PCT:
        out.update(kind="flat", reasons=[f"within {FLAT_PCT:g}% {WINDOW_WORDS[basis]}: under the threshold, no card"])
        return out
    run = coin.get("run")
    if not run:
        return out
    ddir = "down" if mv < 0 else "up"
    if ddir != run["dir"]:
        # October 20, J-8 (b): no card, and the page prints NEXT_READ where the card would stand
        out.update(kind="next_read", line=[NEXT_READ], window_dir=ddir, run_dir=run["dir"],
                   reasons=[f"the page's window moved {ddir} while the run the timing test measured went "
                            f"{run['dir']}: the next slot's run grades the move as it then stands"])
        return out
    wend = _parse((rec.get("window") or {}).get("end_utc"))
    w1 = int(wend.timestamp()) if wend else coin["series"]["points"][-1][0]
    since = None
    if basis == "et_day":
        e = we._et(w1)
        since = int(_dt.datetime(e.year, e.month, e.day, tzinfo=we.ET).timestamp()) - we.TIMING_TEST["lead_min"] * 60
    fall, fell = _words(run["dir"])
    ww = WINDOW_WORDS[basis]
    out.update(dir=run["dir"])
    tests = {t["id"]: t for t in coin.get("tests") or []}
    cands = [c for c in rec.get("candidates") or [] if not c.get("secondary")]
    xs = []
    for i, c in enumerate(cands):
        tst = tests.get(c["id"]) or {}
        r = tst.get("result")
        tu = _parse(tst.get("t_utc"))
        t = int(tu.timestamp()) if tu else None
        if since is not None and (t is None or t < since):
            continue                        # outside the page's window: not this window's verdict
        st, n, prim = stated(c, sym)
        fit, labels, hour = mech_fit(c, coin, t, sym)
        xs.append({"i": i, "c": c, "r": r or {}, "t": t, "path": timing_pass(r), "stated": st, "outlets": n,
                   "primary": prim, "fit": fit, "labels": labels, "hour": hour,
                   "measured": bool(r and r.get("in_window") and r.get("share_pct") is not None)})
    order = lambda x: (-(x["r"].get("share_pct") or 0), x["t"] or 0, x["i"])
    passing = sorted([x for x in xs if x["path"]], key=order)
    mech = _mech_phrase(coin)
    if not passing:
        out.update(kind="graded", grade="Unclear", readings=_readings(coin, None, None, sym),
                   phrases=[NO_EVENT, mech], phrases_sec=[NO_EVENT, ""], required=[0],
                   reasons=["no candidate passes the timing test"])
        out["line"] = list(out["phrases"])
        return out
    named_xs = [x for x in xs if x["stated"]]
    named_fail = sorted([x for x in named_xs if not x["path"] and x["measured"]], key=lambda x: (x["t"] or 0, x["i"]))
    nm = {x["c"]["id"]: named(x["c"], cands) for x in xs}
    full = lambda x: _ref_full(x["c"], x["t"], w1, nm[x["c"]["id"]])
    sec = lambda x: nm[x["c"]["id"]]["text"]
    if named_fail and any(p is not named_fail[0] for p in passing):
        a = named_fail[0]
        b = next(p for p in sorted(passing, key=lambda p: (p["fit"] != "agree",) + order(p)) if p is not a)
        p0 = lambda ref: f"{_outlets(a['outlets'] or 1)} named {ref} as the cause, but it fails the timing test."
        p1 = lambda ref: f"{_cap(ref)} passes the timing test."
        out.update(grade="Disputed", cand=_cand(b), readings=_readings(coin, b["c"], b["t"], sym),
                   phrases=[p0(full(a)), p1(full(b)), _against_phrase(a["r"], name)],
                   phrases_sec=[p0(sec(a)), p1(sec(b)), _against_phrase(a["r"], name)],
                   refs=[nm[a["c"]["id"]], nm[b["c"]["id"]]],
                   reasons=["a named cause fails the timing test while another event passes it"])
    elif len(named_xs) >= 2:
        a, b = sorted(named_xs, key=lambda x: (not x["path"],) + order(x))[:2]
        both = a["path"] and b["path"]
        p0 = lambda ra, rb: f"Outlets named different causes: {ra} and {rb}."
        p1s = (lambda ra, rb: "Both pass the timing test.") if both else (
            lambda ra, rb: f"{_cap(ra)} passes the timing test; {rb} does not.")
        out.update(grade="Disputed", cand=_cand(a), readings=_readings(coin, a["c"], a["t"], sym),
                   phrases=[p0(full(a), full(b)), p1s(full(a), full(b))],
                   phrases_sec=[p0(sec(a), sec(b)), p1s(sec(a), sec(b))],
                   refs=[nm[a["c"]["id"]], nm[b["c"]["id"]]], reasons=["outlets name different causes"])
    else:
        agree = [p for p in passing if p["fit"] == "agree"]
        # an event with a direction of its own (DIRECTION) that the move ran against, and that lines up in time
        against = [p for p in passing if p["fit"] == "contradict" and own_direction(p["c"], sym)
                   and own_direction(p["c"], sym) != run["dir"]]
        prim = [p for p in agree if p["primary"]]
        if agree and against:
            # October 20, J-8: events that pass and point opposite ways are Disputed, the card stating both
            p0 = lambda f: (f"Reported events that line up in time point opposite ways: "
                            f"{_list([f(x) for x in agree])} with the move, {_list([f(x) for x in against])} against it.")
            p1 = "Each passes the timing test."
            x = agree[0]
            out.update(grade="Disputed", cand=_cand(x), readings=_readings(coin, x["c"], x["t"], sym),
                       phrases=[p0(full), p1], phrases_sec=[p0(sec), p1],
                       refs=[nm[p["c"]["id"]] for p in agree + against],
                       reasons=["events that pass the timing test point opposite ways"])
        elif agree:
            # Confirmed names the one event a primary source states; Likely names every event that passes
            # with the readings agreeing (October 20, J-8: the 14 October pair of 8:30 AM releases)
            g, grp = ("Confirmed", [prim[0]]) if prim else ("Likely", agree)
            x = grp[0]
            out["readings"] = _readings(coin, x["c"], x["t"], sym)
            shut_b = (out["readings"] or {}).get("shut", False)
            support, support_s = [], []
            if len(grp) == 1 and x["stated"]:
                sp = ("A primary source states it as the cause." if x["primary"]
                      else f"{_outlets(x['outlets'] or 1)} reported it as the cause.")
                support.append(sp)
                support_s.append(sp)
            support.append(_mech_phrase(coin, x["labels"], x["hour"]))
            support_s.append(_mech_sec(coin, x["labels"], x["hour"], shut_b))
            tps = []
            for p in grp:
                tp = _timing_phrase(p["path"], p["r"], p["c"])
                if tp not in tps:
                    tps.append(tp)
            if g == "Confirmed":
                lead = lambda ref: f"{name} {fell} {ww} because of {ref}."
                out["reasons"] = ["a primary source states it", "the timing test passes", "the readings agree"]
            else:
                lead = lambda ref: f"{name}'s {fall} {ww} lines up with {ref}."
                out["reasons"] = ["the timing test passes", "the readings agree", "no primary source"]
            out.update(grade=g, cand=_cand(x), refs=[nm[p["c"]["id"]] for p in grp],
                       phrases=[lead(_list([full(p) for p in grp]))] + tps + support,
                       phrases_sec=[lead(_list([sec(p) for p in grp]))] + tps + support_s)
        else:
            # October 20, J-8 (a) and J-9 item 3: an event lines up in time and nothing supports it. Unclear, with
            # its own line, and the event named: no cause is claimed, and the page is not silent on a move it
            # has evidence on.
            x = passing[0]
            other_way = all(p in against for p in passing)
            top = OTHER_WAY if other_way else READINGS_MISMATCH
            lab = "The event" if len(passing) == 1 else "The events"
            ph = [top, f"{lab}: {_list([full(p) for p in passing])}."]
            ph_s = [top, f"{lab}: {_list([sec(p) for p in passing])}."]
            out["readings"] = _readings(coin, x["c"], x["t"], sym)
            if x["hour"]:
                shut_b = (out["readings"] or {}).get("shut", False)
                ph.append(_mech_phrase(coin, x["labels"], x["hour"]))
                ph_s.append(_mech_sec(coin, x["labels"], x["hour"], shut_b))
            out.update(grade="Unclear", cand=_cand(x), refs=[nm[p["c"]["id"]] for p in passing], phrases=ph,
                       phrases_sec=ph_s, required=[0, 1],
                       reasons=["an event passes the timing test, but the move ran against its own direction"
                                if other_way else
                                "an event passes the timing test, but the market readings do not agree with it"])
    out["kind"] = "graded"
    out["line"] = out["phrases"][:2]
    out["required"] = out["required"] or ([0, 1] if out["grade"] == "Disputed" else [0])
    return out


def marks(vrec, sym):
    """The listed items a graded card names, for the evidence list to mark: [candidate id]."""
    v = ((vrec or {}).get("coins") or {}).get(sym) or {}
    return [r.get("id") for r in v.get("refs") or [] if r.get("id")] if v.get("kind") == "graded" else []


def _readings(coin, c, t, sym):
    """The readings the grade rests on, for the card: the hour after the candidate when the record
    stores it, else the hour the run began. {hour, start_utc, end_utc, rows, patterns, shut}. The
    coin's own row is left out: the evidence list prints its hour figure."""
    after = ((coin.get("event_hours") or {}).get((c or {}).get("id")) or {}) if c else {}
    if after.get("rows"):
        m, hour = after, "after"
    else:
        m, hour = coin.get("mechanics") or {}, "onset"
    if not m.get("hour_start_utc"):
        return None
    labels, shut = _labels(m.get("patterns"), m.get("rows"))
    rows = [r for r in m.get("rows") or [] if r.get("key") != sym
            and r.get("unit") in ("pct", "bp") and not str(r.get("key")).startswith(("liq", "kalshi", "oi"))]
    on = coin.get("mechanics") or {}
    on_labels, on_shut = _labels(on.get("patterns"), on.get("rows"))
    return {"hour": hour, "start_utc": m.get("hour_start_utc"), "end_utc": m.get("hour_end_utc"),
            "rows": rows, "patterns": labels, "shut": shut,
            "onset_rows": [[r.get("key"), r.get("value")] for r in on.get("rows") or []],
            "onset_patterns": on_labels, "onset_shut": on_shut}


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


def _pieces(s, bodies):
    """[(join, index, raw)] when sentence `s` is whole phrases joined by the allowed joins (the belt's
    rule), else None: the phrases a sentence was built from, in order."""
    s = " ".join(s.split())
    if not s.endswith("."):
        return None
    s = s[:-1]

    def go(i, join):
        for k, b in enumerate(bodies):
            for h in {b, b[:1].lower() + b[1:], b[:1].upper() + b[1:]}:
                if h and s.startswith(h, i):
                    j = i + len(h)
                    if j == len(s):
                        return [(join, k, h)]
                    for jn in _JOINS:
                        if s.startswith(jn, j):
                            rest = go(j + len(jn), jn)
                            if rest:
                                return [(join, k, h)] + rest
        return None
    return go(0, "")


def text_sec(v):
    """The card's sentences on a page that prints the section: each sentence rebuilt from the section forms
    of the whole phrases it was built from; a phrase whose section form is '' (the section's to print, or
    dropped by the twins gate) drops out. A sentence that cannot be traced to whole phrases prints nothing.
    None when the record carries no section forms."""
    sec, ph = v.get("phrases_sec"), v.get("phrases") or []
    if sec is None or len(sec) != len(ph):
        return None
    bodies = [p.rstrip(".") for p in ph]
    out = []
    for snt in v.get("text") or v.get("line") or []:
        pcs = _pieces(snt, bodies)
        if pcs is None:
            continue                        # never an untraced or unchecked sentence
        parts = [(j, sec[k].rstrip("."), raw) for j, k, raw in pcs if sec[k]]
        if not parts:
            continue
        txt = ""
        for n, (j, body, raw) in enumerate(parts):
            if n == 0:
                txt = body[:1].upper() + body[1:]
            else:
                txt += j + (body[:1].lower() + body[1:] if raw[:1].islower() else body)
        out.append(txt + ".")
    return out


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


def estimate(stage, system, user):
    """A call's worst case at the 5.5 rates: its prompt (about three characters a token) and every output
    token it may take."""
    import llm
    mc = CFG["models"][stage]
    pin, pout = llm.PRICING.get(mc["model"], llm.DEFAULT_PRICE)
    return round(((len(system) + len(user)) / 3.0 * pin + mc["max_tokens"] * pout) / 1_000_000, 6)


def _row_usd(r):
    """What a ledger call row counts against the day: its actual cost once settled, its reservation while
    reserved or lost (a call cut off or failed in transit may have been billed), nothing when unbilled."""
    st = r.get("status")
    if st == "settled":
        return float(r.get("usd") or 0)
    if st in ("reserved", "lost"):
        return float(r.get("est_usd") or 0)
    return 0.0


def _ledger_rows(path):
    try:
        rows = json.load(open(path, encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def day_spend(date_et, path=None):
    return round(sum(_row_usd(r) for r in _ledger_rows(path or LEDGER)
                     if r.get("kind") == "call" and r.get("date") == date_et), 6)


class Spend:
    """THE DAY'S SPEND, reserved before every attempt and settled after (ruling 4 of October 19). llm.py
    calls guard() before each HTTP attempt (retries and the empty-response retry included) and after it.
    "before" reserves the call's worst case in the ledger, on disk at once, or refuses with BudgetError
    when that would take the day past the cap; "done" settles it to the actual usage; "unbilled" (an HTTP
    error answer) clears it; "lost" (a transport failure) keeps it. A call the deadline cuts off is never
    settled, so its reservation stands and counts."""

    def __init__(self, path, date_et, slot, cap, now=None):
        self.path, self.date, self.slot, self.cap = path, date_et, slot, cap
        self.now = now or _dt.datetime.now(_dt.timezone.utc)
        self.rows = _ledger_rows(path)
        self.mine, self.est, self.open, self.refused = [], {}, None, False

    def total(self):
        return round(sum(_row_usd(r) for r in self.rows if r.get("kind") == "call" and r.get("date") == self.date), 6)

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        json.dump(self.rows[-800:], open(self.path, "w", encoding="utf-8"), indent=1)

    def prepare(self, stage, system, user):
        self.est[stage] = estimate(stage, system, user)

    def guard(self, phase, stage, usage=None):
        import llm
        if phase == "before":
            est = self.est.get(stage) or estimate(stage, "", "")
            if self.total() + est > self.cap + 1e-12:
                self.refused = True
                raise llm.BudgetError(f"{stage}: the day's spend would pass the ${self.cap:.2f} cap; no attempt made")
            row = {"kind": "call", "date": self.date, "slot": self.slot,
                   "t": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "stage": stage,
                   "model": CFG["models"][stage]["model"], "est_usd": est, "usd": None, "tokens": None,
                   "status": "reserved"}
            self.rows.append(row)
            self.mine.append(row)
            self.open = row
            self.save()
            return
        if self.open is None:
            return
        if phase == "unbilled":
            self.open.update(status="unbilled", usd=0.0)
        elif phase == "lost":
            self.open.update(status="lost")
        elif phase == "done":
            u = usage or {}
            it = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            ot = int(u.get("output_tokens") or 0)
            pin, pout = llm.PRICING.get(self.open["model"], llm.DEFAULT_PRICE)
            self.open.update(status="settled", usd=round((it * pin + ot * pout) / 1_000_000, 6), tokens=it + ot)
        self.open = None
        self.save()


def _model(v, client, spend, gate):
    """(sentences, None) when the model's two sentences pass every check; (None, why) otherwise. Every
    attempt goes through spend.guard; a refusal there leaves spend.refused set."""
    import llm
    if client is None:
        return None, "no model client"
    if STOP["set"]:
        return None, f"the step's {DEADLINE_S}s budget is spent"
    du = draft_user(v)
    spend.prepare("verdict_draft", DRAFT_SYSTEM, du)
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
    spend.prepare("verdict_check", CHECK_SYSTEM, cu)
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


def record_from(rec, date_et, slot, now=None, gate=None, day=None, syms=("BTC", "ETH")):
    """The verdict record for an evidence record, every graded coin on its graded line (no model). The
    twins gate reads the graded line and every section form; a sentence it drops does not print. `syms` is
    the coins graded: Bitcoin and Ether for a slot's record, one Big mover for movers.py (Sprint 9.4)."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    out = {"what": "The verdict under 'Why it moved': the grade computed by code from the evidence record "
                   "(why_evidence.py) on the page's window, the graded line built from phrases, and the model's "
                   "two checked sentences when they passed every check.",
           "date_et": date_et, "slot": slot, "window": (rec or {}).get("window"),
           "evidence_made_utc": (rec or {}).get("made_utc"),
           "made_utc": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "timing_rule": dict(_we().TIMING_TEST), "day": day, "coins": {}}
    for sym in syms:
        v = grade(rec, sym, day)
        if v["kind"] == "none":
            continue
        if gate is not None:
            keep = lambda s: bool(s) and gate.text(s, "the verdict (phrases)", dollars=True).strip() == s.strip()
            v["line"] = [s for s in v["line"] if keep(s)]
            v["phrases_sec"] = [s if keep(s) else "" for s in v.get("phrases_sec") or []]
        v.update(text=list(v["line"]), by="phrases", fail_reason=None, corrections=[],
                 url=url(date_et, sym) if v["grade"] else None)
        out["coins"][sym] = v
    return out


def write_run(rec, date_et, slot, gate=None, ledger_path=None, directory=None, save=True, cap=None,
              client=None, now=None, day=None, syms=("BTC", "ETH")):
    """Grade on the page's window, write each graded coin's two sentences through the model and its
    check, every attempt reserved against the day's cap and settled after. A model failure prints the
    graded line; a refusal at the cap withholds the verdict (CAP_LINE, no grade). Appends the run's row,
    prints the day against the cap, returns (verdict record, run row)."""
    import llm
    cap = CAP_USD if cap is None else cap
    ledger_path = ledger_path or LEDGER
    now = now or _dt.datetime.now(_dt.timezone.utc)
    out = record_from(rec, date_et, slot, now=now, gate=gate, day=day, syms=syms)
    spend = Spend(ledger_path, date_et, slot, cap, now)
    budget = llm.Budget(CFG["budget"]["max_tokens_per_run"], 1e9)     # the cap is the ledger's to keep
    if client is None and os.environ.get("ANTHROPIC_API_KEY", "").strip():
        client = llm.Client(CFG, mode="live", budget=budget)
    if client is not None:
        client.budget = budget
        client.attempt_guard = spend.guard
    for sym, v in out["coins"].items():
        if not v["grade"]:
            continue
        spend.refused = False
        try:
            sents, why = _model(v, client, spend, gate)
        except _Late as e:                           # out of time: the graded line; the cut call stays reserved
            sents, why = None, str(e)
        except Exception as e:                       # never a gate on a slot: the graded line prints
            sents, why = None, f"the model path raised {type(e).__name__}: {str(e)[:100]}"
        if spend.refused:
            # AT THE CAP THE VERDICT IS WITHHELD, never a guess (ruling 4): no grade, no line, no URL
            v.update(kind="withheld", grade_withheld=v["grade"], grade=None, text=[], by="withheld",
                     url=None, fail_reason=why)
        elif sents:
            v.update(text=sents, by="model", fail_reason=None)
        else:
            v.update(text=list(v["line"]), by="phrases",
                     fail_reason=why if client is not None else "no API key; no model call")
    mine = spend.mine
    row = {"kind": "run", "date": date_et, "slot": slot, "t": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "calls": len(mine), "tokens": sum(int(r.get("tokens") or 0) for r in mine),
           "usd": round(sum(_row_usd(r) for r in mine), 6),
           "by_stage": {s: round(sum(_row_usd(r) for r in mine if r["stage"] == s), 6) for s in CFG["models"]
                        if any(r["stage"] == s for r in mine)},
           "models": {k: m["model"] for k, m in CFG["models"].items()},
           "day_usd": spend.total(), "cap_usd": cap,
           "coins": {k: (f"{v['grade']} ({v['by']})" if v["grade"] else v["kind"]) for k, v in out["coins"].items()}}
    out["spend"] = row
    spend.rows.append(row)
    spend.save()
    print(f"verdict: spend this run ${row['usd']:.4f} ({row['calls']} call(s), {row['tokens']:,} tokens); "
          f"today ${row['day_usd']:.4f} of the ${cap:.2f} cap")
    for sym, v in out["coins"].items():
        print(f"verdict: {sym} {v['grade'] or v['kind']}"
              + (f" ({v['by']}: {v['fail_reason']})" if v.get("fail_reason") else f" ({v['by']})" if v["grade"] else ""))
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


# ---- the notice: why there is no card yet, and when the next read is ---------------------------------------------------

_FLIP_REASON = re.compile(r"moved (up|down) while the run .*? went (up|down)")


def _flip_dirs(v, vrec, sym):
    """(window direction, run direction) of a flipped record. A record written since 9.9.1 states both as fields; one
    stored before it states them in its reasons (code-written words), and the window's own move is in `day`."""
    wd, rd = v.get("window_dir"), v.get("run_dir")
    if wd in ("up", "down") and rd in ("up", "down"):
        return wd, rd
    m = _FLIP_REASON.search(" ".join(v.get("reasons") or []))
    if m:
        return m.group(1), m.group(2)
    mv = ((vrec or {}).get("day") or {}).get(sym)
    if isinstance(mv, (int, float)) and mv:
        return ("up" if mv > 0 else "down"), None
    return None, None


def _next_read_when(now, vrec):
    """'tonight at 7:08 PM ET': the next slot off the clock, by the one function the Brief card and the daily answer use
    (home.next_slot). `now` is the build's on a live page; without it the record's own time stands, so a dated page and
    a stored record never change with the clock that draws them."""
    import home
    t = now or _parse((vrec or {}).get("made_utc")) or _parse(((vrec or {}).get("window") or {}).get("end_utc"))
    return home.next_slot(t)[1]


def notice_line(why, when, detail=""):
    """The one line: the ruled words, why, and the time of the next read."""
    return f"{NEXT_READ}: {why}{f' ({detail})' if detail else ''}. Next read: {when}."


def _notice_card(sym, name, kind, line, basis=None, direction=None):
    at = (f' data-vd-basis="{_e(basis)}"' if basis else "") + (f' data-vd-dir="{_e(direction)}"' if direction else "")
    return (f'<aside class="vd vd-next" data-vd="{_e(sym)}" data-vd-kind="{_e(kind)}"{at} aria-label="Why {_e(name)} moved">'
            f'<h2 class="vd-h">Why {_e(name)} moved</h2>'
            f'<p class="vd-plain vd-next" data-vd-next="{_e(kind)}">{_e(line)}</p></aside>')


def no_read_html(now, sym="BTC"):
    """The card's place when no read has run on the ET day of `now`: the notice, with the time of the next read."""
    name = NAMES.get(sym, (sym, sym.lower()))[0]
    return _notice_card(sym, name, "no_read", notice_line(WHY_NO_READ, _next_read_when(now, None)))


def is_today(vrec, now):
    """True when the record is the ET day of `now`'s own (its date_et)."""
    if not vrec or now is None:
        return False
    return str(vrec.get("date_et") or "") == now.astimezone(_we().ET).date().isoformat()


# ---- the card: one shape on the home, /today/, the Bitcoin page and the verdict page ------------------------------

def card_html(vrec, sym, where="today", live=False, corrections=None, link=True, with_section=False, now=None):
    """The card for one coin, or '' (fail open). `where` is home, today, coin or page. Only a graded verdict
    draws a card, and a withheld one (the cap) draws the desk's line in its place, and a move whose page
    window ran the other way from the measured run draws "Verdict at the next read"; Ether moving with Bitcoin
    is one plain line on the Ether page. `with_section`: the page also prints the evidence list, so the card
    names the event with a pointer to its item and leaves times, figures and wording to the list."""
    try:
        return _card(vrec, sym, where, live, corrections, link, with_section, now)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::verdict: the card for {sym} was not drawn ({type(e).__name__}: {e})")
        return ""


def _card(vrec, sym, where, live, corrections, link, with_section=False, now=None):
    we = _we()
    v = ((vrec or {}).get("coins") or {}).get(sym)
    if not v:
        return ""
    if v.get("kind") == "with_btc":
        ww = v.get("window_words") or WINDOW_WORDS["rolling_24h"]
        return f'<p class="vd-plain">Ether moved with Bitcoin {_e(ww)}.</p>' if where == "coin" else ""
    if v.get("kind") == "next_read":
        # October 20, J-8 (b): no grade, and the notice stands in the card's place on every page that draws it. SPRINT 9.9.1: it
        # says why (the window flipped since the run, both directions named, no figure) and when the next read is, in one line,
        # inside a card of its own so it is the home's first object like any verdict.
        wd, rd = _flip_dirs(v, vrec, sym)
        ww = v.get("window_words") or WINDOW_WORDS["rolling_24h"]
        detail = f"the 24-hour run went {rd}; the move {ww} is {wd}" if wd and rd else ""
        return _notice_card(sym, v.get("name") or sym, "next_read",
                            notice_line(WHY_FLIPPED, _next_read_when(now, vrec), detail), v.get("basis"), wd)
    if v.get("kind") not in ("graded", "withheld"):
        return ""
    name = v.get("name") or sym
    wend = _parse(((vrec or {}).get("window") or {}).get("end_utc"))
    if wend is None:
        return ""
    w1 = int(wend.timestamp())
    asof = f' data-asof="{_e(_iso(w1))}"' if live else ""
    ww = v.get("window_words") or WINDOW_WORDS["rolling_24h"]
    # the window the card's words use is the page's (ruling 1); its end time is the section's to print
    win = (f'<p class="vd-win"{asof}>{_e(_cap(ww))}</p>' if with_section else
           f'<p class="vd-win"{asof}>{_e(_cap(ww))}, to {_e(we.clock(w1))}, {_e(we.long_day(w1))}</p>')
    if v["kind"] == "withheld":
        body, cls = f'<p class="vd-line">{_e(CAP_LINE)}</p>', "withheld"
    else:
        g = v["grade"]
        if g not in GRADES:
            return ""
        cls = g.lower()
        sents = (text_sec(v) if with_section else None)
        if with_section and sents is None:
            sents = []                      # a record with no section forms: the grade only, beside the list
        text = " ".join(sents if sents is not None else (v.get("text") or v.get("line") or []))
        line_html = _e(text)
        if with_section:
            # THE POINTER (Jack, J-7): each named event carries the id of the one listed item it means, and the
            # words that find it there; the list marks that item
            for ref in v.get("refs") or []:
                for form in (ref.get("text") or "", _cap(ref.get("text") or "")):
                    if form and _e(form) in line_html:
                        tag = (f'<b class="vd-ref" data-vd-ref="{_e(ref.get("id"))}" '
                               f'data-vd-key="{_e("|".join(ref.get("key") or []))}">{_e(form)}</b>')
                        line_html = line_html.replace(_e(form), tag, 1)
                        break
        body = (f'<p class="vd-grade"><span class="vd-badge vd-{cls}">Checked: <b>{_e(g)}</b></span> '
                f'<span class="vd-def">{_e(DEFINITIONS[g])}</span></p>'
                + (f'<p class="vd-line">{line_html}</p>' if text else "")
                + _readings_html(v.get("readings"), text, rows=(where != "home"), with_section=with_section))
    corr, seen = "", set()
    for c in list(v.get("corrections") or []) + list(corrections or []):
        t = str((c or {}).get("text") or "").strip()
        if t and t not in seen:
            seen.add(t)
            corr += f'<p class="vd-corr"><b>Correction, {_e(c.get("date"))}.</b> {_e(t)}</p>'
    more = ""
    if link and v.get("url") and where != "page":
        more = f'<p class="vd-more"><a href="{_e(v["url"])}">The verdict and its evidence</a></p>'
    at = (f' data-vd-basis="{_e(v.get("basis"))}"' if v.get("basis") else "") + (
        f' data-vd-dir="{_e(v.get("dir"))}"' if v.get("dir") in ("up", "down") else "")
    return (f'<aside class="vd vd-{cls}" data-vd="{_e(sym)}"{at} aria-label="Why {_e(name)} moved">'
            f'<h2 class="vd-h">Why {_e(name)} moved</h2>{win}{body}{corr}{more}</aside>')


def _readings_html(rd, text, rows=True, with_section=False):
    """THE READINGS BEHIND THE GRADE (review 1; AUDIT.md 3.1: the page shows the reader the test). The
    hour the grade read, named with its own times, its figures (off the home), and its pattern unless
    the card's sentences already say it. The coin's own hour figure is not repeated here."""
    if not rd or not rd.get("start_utc"):
        return ""
    we = _we()
    a, b = _parse(rd["start_utc"]), _parse(rd.get("end_utc"))
    if a is None or b is None:
        return ""
    label = "the hour after it" if rd.get("hour") == "after" else "the hour the run began"
    if with_section and "onset_rows" not in rd:
        return f'<div class="vd-read"><p class="vd-rh">The readings behind this grade: {_e(label)}.</p></div>'
    if with_section and rd.get("hour") != "after":
        return ('<div class="vd-read"><p class="vd-rh">The readings behind this grade: the hour the run began, '
                'in the evidence below.</p></div>')
    if with_section:
        out = '<p class="vd-rh">The readings behind this grade: the hour after it, from its time in the list below.</p>'
    else:
        out = (f'<p class="vd-rh">The readings behind this grade: {_e(label)}, '
               f'{_e(we.clock(int(a.timestamp())))} to {_e(we.clock(int(b.timestamp())))}.</p>')
    shown = rd.get("rows") or []
    if with_section:
        # a row the section's onset hour prints with the same figure is the section's to print
        on = {(k, v) for k, v in rd.get("onset_rows") or []}
        shown = [r for r in shown if (r.get("key"), r.get("value")) not in on]
    if rows and rd.get("hour") == "after" and shown:
        out += '<ul class="vd-rows">' + "".join(
            f'<li><span class="vd-rn">{_e(r["label"])}</span>{we._chg(r.get("value"), r.get("unit") or "pct")}</li>'
            for r in shown) + "</ul>"
    if with_section and (sorted(rd.get("patterns") or []), bool(rd.get("shut"))) == (
            sorted(rd.get("onset_patterns") or []), bool(rd.get("onset_shut"))):
        if "read as they did" not in (text or ""):
            out += '<p class="vd-rp">Pattern: as in the hour the run began, in the evidence below.</p>'
        return f'<div class="vd-read">{out}</div>'
    pats = rd.get("patterns") or []
    if pats:
        said = " and ".join(pats)
        if said not in (text or ""):
            out += f'<p class="vd-rp">Pattern: {_e(said)}.</p>'
    elif rd.get("shut"):
        if "did not trade" not in (text or ""):
            out += ('<p class="vd-rp">Stock futures did not trade in this hour, so the readings cannot tell a '
                    'crypto move from a wider one.</p>')
    elif "none of the four" not in (text or ""):
        out += '<p class="vd-rp">Pattern: none of the four the desk names.</p>'
    return f'<div class="vd-read">{out}</div>'


# ---- the verdict pages: /why/<date>-<coin> ---------------------------------------------------------------------

SLOT_LABEL = {"morning": "Morning Brief", "evening": "Evening Brief"}


def build_pages(vdir=None, wdir=None, tdir=None, dateline="", share=None, record=None):
    """[{rel, html, path, lastmod, published_utc, title}] for every graded verdict: one URL per day and
    coin, kept once it exists. The page carries the day's newest graded verdict and its evidence.
    `share` (share_cards.Ctx, Sprint 9.6): when it names a directory the page's own square image is drawn there and
    the page's Open Graph and Twitter tags name it; without it the page is the page it was.
    `record` (Sprint 9.8, round 4): verdict_record.standings(), each page's standing line; drawn here when not given."""
    import verdict_record
    if record is None:
        record = verdict_record.standings(vdir=vdir, wdir=wdir)
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
                out.append(_page(day, sym, recs, graded[0], vdir, wdir, tdir, dateline, share, record))
            except Exception as e:                               # noqa: BLE001
                print(f"::warning::verdict: /why/{slug(day, sym)} was not built ({type(e).__name__}: {e})")
    return out


def _page(day, sym, recs, lead, vdir, wdir, tdir, dateline, share=None, record=None):
    import site_build as sb
    we = _we()
    name = NAMES[sym][0]
    d = _dt.date.fromisoformat(day)
    when = f"{d.strftime('%A, %B')} {d.day}, {d.year}"
    title = f"Why {name} moved: {when}"
    corr = _today_corrections(day, lead.get("slot"), tdir)
    ev = we.load(day, lead.get("slot"), wdir)
    ev_html = (we.section_html(ev, sym, live=False, corrections=corr, graded=lead["coins"][sym].get("grade"),
                               marks=marks(lead, sym)) if ev else "")
    card = card_html(lead, sym, where="page", live=False, corrections=corr, link=False, with_section=bool(ev_html))
    v = lead["coins"][sym]
    pub = lead.get("made_utc") or ""
    stamp = SLOT_LABEL.get(lead.get("slot"), "")
    import verdict_record                    # SPRINT 9.8, round 4: the move's standing on the record, linked
    standing = verdict_record.standing_html(url(day, sym), record)
    tdd = tdir or os.path.join(HERE, "site", "data", "today")
    today_link = ""
    if any(os.path.exists(os.path.join(tdd, f"{day}-{sl}.json")) for sl in ("morning", "evening")):
        today_link = (f'<p class="td-w">The day\'s answer, with what moved and what was reported, is at '
                      f'<a href="/today/{_e(day)}">/today/{_e(day)}</a>.</p>')
    body = f"""<main class="wrap"><section class="page td-page vd-page">
  <span class="kicker">Why it moved</span>
  <h1>{_e(title)}</h1>
  <p class="td-stamp">{_e(stamp)}</p>
  {card}
  {ev_html}
  {today_link}
  {standing}
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
    import share_cards
    og = share_cards.for_page(share, lead, sym, ev, slug(day, sym), day, [r.get("slot") for r in recs], corr)
    html = sb.shell(f"{title} - {sb.NAME}", desc, "Today", body, dateline, path=path, og_type="article",
                    schema_extra=f'\n<script type="application/ld+json">{schema}</script>', **og)
    return {"rel": f"why/{slug(day, sym)}.html", "html": html, "path": url(day, sym), "lastmod": pub,
            "published_utc": min(r.get("made_utc") or pub for r in recs), "title": title}


def _today_corrections(day, slot, tdir):
    try:
        p = os.path.join(tdir or os.path.join(HERE, "site", "data", "today"), f"{day}-{slot}.json")
        return json.load(open(p, encoding="utf-8")).get("corrections") or []
    except (OSError, ValueError):
        return []


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
        day = day_moves(pulse, date)
        print(f"verdict: the page's window is {(day or {}).get('basis') or 'the series'}")
        gate = twins_gate.Gate(_s.build(pulse, flows), log_path="", quiet=True)
        try:
            write_run(ev, date, slot, gate=gate, now=now, day=day)
        except _Late as e:
            # out of time outside a call: the graded lines, no model sentence; any reservation stands
            print(f"::warning::verdict: {e}; writing the graded lines with no model sentence")
            signal.alarm(0)
            out = record_from(ev, date, slot, now=now, gate=gate, day=day)
            for v in out["coins"].values():
                if v["grade"]:
                    v["fail_reason"] = str(e)
            p = record_path(date, slot)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
            print(f"verdict: wrote {p} (graded lines only)")
        signal.alarm(0)
    except Exception as e:                                       # never a gate on a slot
        print(f"::warning::verdict: no verdict written ({type(e).__name__}: {e})")
    _sync_record()
    return 0


def _sync_record():
    """SPRINT 9.8: store every new graded verdict and every newly resolved Likely in the verdict record (verdict_record.py),
    append-only, in site/data/verdict/record/, which the run's commit stages with site/data/verdict. Never a gate."""
    try:
        # the step's alarm and its SIGTERM handler are disarmed first (review 1): neither may fire inside the store's write
        import signal
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        import verdict_record
        verdict_record.sync(save=True)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::verdict record: not stored this run ({type(e).__name__}: {e})")


if __name__ == "__main__":
    sys.exit(main())
