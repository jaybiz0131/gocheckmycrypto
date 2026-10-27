#!/usr/bin/env python3
"""Sprint 9.9.1 (October 26, 2026): the first screen answers. Each case is named after what it guards.

  python3 scripts/sprint991_test.py                  # unit cases; exit 1 on any failure
  python3 scripts/sprint991_test.py --tree <dir>     # also the cases that read a built tree
  python3 scripts/sprint991_test.py --browser        # also the first object at 375 and 1440 (Playwright, a fixture page)
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote)

The definition of done (docs/BOARD.md, 9.9.1): /today/, the home and the coin pages agree on direction and window on a
fixture where the day and the 24 hours disagree; the placeholder line on a fixture; the home's first object from a
fixture at both widths. One window per page, named (the strategist's ruling of October 19); "Verdict at the next read"
always prints why and the time of the next read, in one line (the ruling on J-8 of October 20); the verdict card is the
home's first object below the masthead even when it carries that line, with the Bitcoin line (the tape) moved under it.

THE RECORDS ARE REAL: fixtures/sprint991/real-2026-10-26-morning holds the October 26 morning read's files byte for byte,
as main held them at 739fb7b (site/data/pulse.json, flows.json, wire.json, today/, why/, verdict/): /today/ said Bitcoin was
up 0.77% since midnight ET over an evidence list and chart built on a 1.70% fall over the 24 hours to 8:17 AM ET, and the
verdict record says "Verdict at the next read" with no reason and no time. The CLOCKS are SYNTHETIC where a case says so: the
no-read case reads that real record at 6:00 AM ET the next morning (a build clock chosen by the case, not a recorded one).
ROUND 4 (October 27, 2026, entry 2026-10-26-C6, J-16 option 2): the ET-day cut of the evidence list is gone (it moves to 9.9.3 with the
timing test and the grade), so the list of /today/ and the coin pages is the stored record's 24 hours, the window the grade was made on,
named beside every figure; a graded verdict shows on its dated /today/ page as published with its own window and its /why/ link
(fixtures/sprint991/real-2026-10-25-evening); the notice prints only for a flip (the measured run's direction against the direction
in the page's window) or for no read yet today, on /today/ too; the Ether line reads the list's window. The window line prints only
what the record states, the notice's next read follows the build clock on a living page, and the /why/ pages stay as main wrote them.
fixtures/sprint991/
real-2026-10-15-evening and real-2026-10-16-evening hold the two stored /today/ records that predate direction_basis, byte for byte.
NO MODEL CALL and no network anywhere.
"""
import contextlib
import copy
import datetime as dt
import hashlib
import html as _html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
FX = os.path.join(HERE, "fixtures", "sprint991", "real-2026-10-26-morning")
UTC = dt.timezone.utc
EM = re.compile("[\u2013\u2014]")
GRADE = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b")

# THE CLOCKS. The morning build: the Board's reading was 8:17 AM ET (12:17:14Z), the strategist read production at 8:20 AM ET.
NOW_MORNING = dt.datetime(2026, 10, 26, 12, 20, tzinfo=UTC)
# SYNTHETIC: 6:00 AM ET the next day, before that day's read has run.
NOW_NEXT_DAY = dt.datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
# The clock of Review 1's failure 3: the reviewer's build at 7:38 PM ET on October 26 (the Evening Brief's 7:08 PM slot already past).
NOW_LATE = dt.datetime(2026, 10, 26, 23, 38, tzinfo=UTC)

NEXT_READ = "Verdict at the next read"
# ROUND 4 (entry 2026-10-26-C6): the flip's reason in the ruled wording, the measured run's direction against the direction in the page's window
FLIPPED_LINE = ("Verdict at the next read: the run the last read measured went down; the move since midnight ET is up. "
                "Next read: tonight at 7:08 PM ET.")
NO_READ_LINE = "Verdict at the next read: no read yet today. Next read: this morning at 8:15 AM ET."


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


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


def visible(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h or "", flags=re.S | re.I)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def notice_texts(h):
    """The visible text of every paragraph that carries the notice, one string each."""
    return [visible(m.group(0)) for m in re.finditer(r'<p class="vd-plain vd-next"[^>]*>.*?</p>', h or "", flags=re.S)]


def attrs_of(h, tag_re):
    m = re.search(tag_re, h or "")
    return dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(0))) if m else {}


# ---- the pages, drawn from the real records ------------------------------------------------------------------------

class Draw:
    """The home, /today/ and the Bitcoin page from the October 26 morning records, with the build globals set and restored."""

    def __init__(self, now=NOW_MORNING):
        import site_build as sb
        import snapshot
        self.sb, self.now = sb, now
        self.pulse, self.flows, self.wire = load("pulse.json"), load("flows.json"), load("wire.json")
        self.rec, self.ev, self.v = load("today_2026-10-26-morning.json"), load("why_2026-10-26-morning.json"), \
            load("verdict_2026-10-26-morning.json")
        self.snap = snapshot.build(self.pulse, self.flows)

    def __enter__(self):
        self._old = (self.sb.SNAP, self.sb._NOW_CACHE)
        self.sb.SNAP, self.sb._NOW_CACHE = self.snap, self.now
        return self

    def __exit__(self, *a):
        self.sb.SNAP, self.sb._NOW_CACHE = self._old

    def home(self, verdict="real", now=None, evidence="real"):
        import home
        v = self.v if verdict == "real" else verdict
        import inspect
        kw = {"evidence": self.ev if evidence == "real" else evidence} if "evidence" in inspect.signature(home.above_fold).parameters else {}
        return home.above_fold(self.snap, self.pulse, self.flows, self.sb.board_deltas(self.pulse), self.wire, {}, {},
                               self.sb.NEWS_CADENCE_LINE, now=now or self.now, verdict=v, **kw)

    def today(self, verdict="real", rec=None, here="living", evidence="real", clock=None):
        import today
        return today.body_html(rec or self.rec, [], here, evidence=self.ev if evidence == "real" else evidence,
                               verdict=self.v if verdict == "real" else verdict, clock=clock)

    def coin(self, sym="BTC", verdict="real", evidence="real"):
        pos, c = next((i + 1, x) for i, x in enumerate(self.pulse["movers"]["top100"]) if x["symbol"] == sym)
        return self.sb.render_coin_page(c, pos, self.pulse, [], "DATELINE", wire={"items": []}, cm={},
                                        evidence=self.ev if evidence == "real" else evidence,
                                        verdict=self.v if verdict == "real" else verdict, read_clock=self.now,
                                        today=self.now.astimezone(dt.timezone(dt.timedelta(hours=-4))).date())


def s93():
    import sprint93_test
    return sprint93_test


# ---- 1. one window per page, named: /today/ ------------------------------------------------------------------------

def today_cases(fails):
    print("1. /today/: the headline's window is named beside it, and the evidence's own window is named beside its figures")
    import today
    with Draw() as d:
        h = d.today()
        rec = d.rec
        guarded(fails, "the premise, from the real record: the headline says up, the ET day is +0.77% and the 24 hours -0.15%, "
                       "and the evidence's own run fell",
                lambda: rec["direction"] == "up" and rec["btc"]["chg_day"] == 0.77 and rec["btc"]["chg"] == -0.15
                and rec["direction_basis"] == "et_day" and d.ev["coins"]["BTC"]["run"]["dir"] == "down"
                and d.ev["coins"]["BTC"]["run"]["pct"] == -1.701)
        win = attrs_of(h, r'<p class="td-stamp td-win"[^>]*>')
        guarded(fails, "a window line stands under the headline, carrying the page's basis and direction",
                lambda: win.get("data-td-basis") == "et_day" and win.get("data-td-dir") == "up")
        m = re.search(r'<p class="td-stamp td-win"[^>]*>(.*?)</p>', h, flags=re.S)
        line = visible(m.group(1)) if m else ""
        guarded(fails, "the window line says the direction is read since midnight ET",
                lambda: "since midnight ET" in line)
        guarded(fails, "the window line names the list's window (the 24 hours; the record holds no grade, so none is claimed) beside the direction's, with no figure of its own",
                lambda: "the 24 hours to 8:17 AM ET." in line and "the grade was made on" not in line and "went down" not in line
                and not re.search(r"\d\.\d\d%", line))
        guarded(fails, "the window line sits under the stamp and above the answer",
                lambda: h.index('class="td-stamp"') < h.index('class="td-stamp td-win"') < h.index('class="td-answer"'))
        ev = re.search(r'<section class="td-sec ev".*?</section>', h, flags=re.S)
        evt = visible(ev.group(0)) if ev else ""
        guarded(fails, "the evidence section reads the window the grade was made on and says so in its own attribute (round 4)",
                lambda: 'data-ev-window="rolling_24h"' in (ev.group(0) if ev else ""))
        guarded(fails, "the evidence's run figure carries its window's name beside it (in the 24 hours), never 'the window' alone",
                lambda: re.search(r"The largest run in the 24 hours: ▼ [\d.]+%", evt) and "in the window:" not in evt)
        guarded(fails, "no em dash or en dash on the page", lambda: not EM.search(h))
        # the page's own window figures: the ET-day row and the 24-hour row each carry their own window
        guarded(fails, "the What moved rows name their windows (since midnight ET, last 24 hours)",
                lambda: "since midnight ET" in visible(h) and "last 24 hours" in visible(h))
    # the named fallback: no midnight open on the Board, so the 24 hours stand in and the page says why
    print("   the rolling 24 hours is the named fallback only")
    import snapshot
    import twins_gate
    pulse = load("pulse.json")
    for r in pulse["movers"]["top100"]:
        if r.get("symbol") == "BTC":
            r["open_et_day"] = "2026-10-25"                  # SYNTHETIC: a midnight open that belongs to another ET day
    flows = load("flows.json")
    with Draw() as d:
        snap = snapshot.build(pulse, flows)
        with quiet():
            rec = today.compose(snap, pulse, d.wire, None, load("morning.json"), NOW_MORNING, twins_gate.Gate(snap))
        guarded(fails, "SYNTHETIC midnight open from another day: the record's basis is the rolling 24 hours",
                lambda: rec and rec["direction_basis"] == "rolling_24h" and rec["btc"]["chg_day"] is None)
        h = d.today(rec=rec, verdict=None)
        m = re.search(r'<p class="td-stamp td-win"[^>]*>(.*?)</p>', h, flags=re.S)
        line = visible(m.group(1)) if m else ""
        guarded(fails, "the fallback page says the direction is read over the last 24 hours, the named fallback, and claims nothing "
                       "about the Board that the record does not state (Review 1, failure 4)",
                lambda: "over the last 24 hours" in line and "fallback" in line and "Board" not in line and "open" not in line)
        guarded(fails, "the fallback line carries the page's basis",
                lambda: attrs_of(h, r'<p class="td-stamp td-win"[^>]*>').get("data-td-basis") == "rolling_24h")


# ---- 2. the placeholder: why, and the time of the next read, in one line ---------------------------------------------

def notice_cases(fails):
    print("2. 'Verdict at the next read' always prints why and the time of the next read, in one line")
    with Draw() as d:
        pages = {"home": d.home(), "/today/": d.today(), "/coins/btc": d.coin("BTC")}
        for name, h in pages.items():
            t = notice_texts(h)
            guarded(fails, f"{name}: one notice, and it reads exactly the flip line (both directions) with the next read's time",
                    lambda t=t: t == [FLIPPED_LINE])
            guarded(fails, f"{name}: the notice is one paragraph on one line (no break inside it)",
                    lambda h=h: not re.search(r'<p class="vd-plain vd-next"[^>]*>[^<]*<br', h) and "\n" not in
                    (re.search(r'<p class="vd-plain vd-next"[^>]*>.*?</p>', h, flags=re.S).group(0) if "vd-next" in h else "\n"))
            guarded(fails, f"{name}: the notice names no grade and no cause",
                    lambda t=t: t and not GRADE.search(t[0]) and "because" not in t[0].lower())
            guarded(fails, f"{name}: no em dash or en dash", lambda h=h: not EM.search(h))
        guarded(fails, "the notice stands in a card (aside.vd) with its own heading, not a bare line",
                lambda: re.search(r'<aside class="vd vd-next" data-vd="BTC"[^>]*><h2 class="vd-h">Why Bitcoin moved</h2>'
                                  r'<p class="vd-plain vd-next"', pages["home"]))
        # the stored read is never reworded (J-10)
        before = copy.deepcopy(d.v)
        d.home()
        d.today()
        d.coin("BTC")
        guarded(fails, "drawing the pages leaves the stored verdict record as it was, word for word (J-10)",
                lambda: d.v == before and d.v["coins"]["BTC"]["line"] == [NEXT_READ] and d.v["coins"]["BTC"]["text"] == [NEXT_READ])
        stored = os.path.join(HERE, "site", "data", "verdict", "2026-10-26-morning.json")
        guarded(fails, "the fixture is the stored October 26 verdict byte for byte",
                lambda: hashlib.sha256(open(os.path.join(FX, "verdict_2026-10-26-morning.json"), "rb").read()).hexdigest()
                == hashlib.sha256(open(stored, "rb").read()).hexdigest())
    # no read yet today (SYNTHETIC clock): the real record is yesterday's at 6:00 AM ET
    print("   no read yet today (SYNTHETIC clock: 6:00 AM ET the next day, the real October 26 record)")
    with Draw(NOW_NEXT_DAY) as d:
        for name, h in (("home", d.home()), ("/coins/btc", d.coin("BTC"))):
            guarded(fails, f"{name}: the notice says no read yet today and the next read's time, in one line",
                    lambda h=h: notice_texts(h) == [NO_READ_LINE])
        guarded(fails, "home with no verdict record at all: the same notice",
                lambda: notice_texts(d.home(verdict=None)) == [NO_READ_LINE])
        guarded(fails, "the Ether page says the same as the Bitcoin page when no read has run today (Review 2, failure 6)",
                lambda: notice_texts(d.coin("ETH", verdict=None)) == [NO_READ_LINE])
        # a flat day is not a missing read: a record for today that grades nothing draws nothing (the 9.3 rule stays)
        flat = copy.deepcopy(d.v)
        flat["date_et"] = "2026-10-27"
        flat["coins"]["BTC"].update(kind="flat", line=[], text=[], reasons=["within 0.5% since midnight ET: under the threshold, no card"])
        guarded(fails, "a flat day's record, dated today, draws no card and no notice (nothing was missed)",
                lambda: not notice_texts(d.home(verdict=flat)) and "vd-next" not in d.home(verdict=flat))
    # the evening clock names tomorrow
    with Draw(dt.datetime(2026, 10, 27, 1, 30, tzinfo=UTC)) as d:        # 9:30 PM ET on October 26
        guarded(fails, "after the evening slot the notice names tomorrow's read (the Brief card's own function)",
                lambda: notice_texts(d.home())[:1] == [FLIPPED_LINE.replace("tonight at 7:08 PM ET", "tomorrow at 8:15 AM ET")])


# ---- 3. one window per page: the three pages agree -----------------------------------------------------------------

def agree_cases(fails):
    print("3. /today/, the home and the Bitcoin page agree on direction and window, on a day where the day and the 24 hours disagree")
    with Draw() as d:
        a = {"/today/ window line": attrs_of(d.today(), r'<p class="td-stamp td-win"[^>]*>'),
             "/today/ card": attrs_of(d.today(), r'<aside class="vd[^"]*"[^>]*>'),
             "home card": attrs_of(d.home(), r'<aside class="vd[^"]*"[^>]*>'),
             "/coins/btc card": attrs_of(d.coin("BTC"), r'<aside class="vd[^"]*"[^>]*>')}
        for name, at in a.items():
            guarded(fails, f"{name}: names the ET day as its window and up as its direction",
                    lambda at=at: (at.get("data-vd-basis") or at.get("data-td-basis")) == "et_day"
                    and (at.get("data-vd-dir") or at.get("data-td-dir")) == "up")
        # the evidence window is one thing on /today/ and on the coin page
        e1 = re.search(r'<p class="ev-win"[^>]*>(.*?)</p>', d.today(), flags=re.S)
        e2 = re.search(r'<p class="ev-win"[^>]*>(.*?)</p>', d.coin("BTC"), flags=re.S)
        guarded(fails, "/today/ and /coins/btc name the same evidence window (the 24 hours to 8:17 AM ET)",
                lambda: e1 and e2 and visible(e1.group(1)) == visible(e2.group(1)) and "the 24 hours to 8:17 AM ET" in visible(e1.group(1)))
        # the verdict module is the one source of the page's window and direction
        import verdict
        day = verdict.day_moves(d.pulse, "2026-10-26")
        guarded(fails, "the verdict's day_moves and /today/'s record agree: et_day, up",
                lambda: day["basis"] == "et_day" and day["BTC"] > 0 and d.rec["direction"] == "up" and d.rec["direction_basis"] == "et_day")
    print("   a graded card carries the same hooks (the 15 October real record: its Board held no midnight open, so its window is the rolling 24 hours, named)")
    t = s93()
    import verdict
    v15 = verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15())
    card = verdict.card_html(v15, "BTC", where="home", live=True)
    at = attrs_of(card, r'<aside class="vd[^"]*"[^>]*>')
    guarded(fails, "the graded card carries its basis and its direction",
            lambda: at.get("data-vd-basis") == v15["day"]["basis"] and at.get("data-vd-dir") in ("up", "down"))
    # a new record states both directions of a flip as fields, so no reader has to parse prose
    with Draw() as d:
        with quiet():
            vr = verdict.record_from(d.ev, "2026-10-26", "morning", day=verdict.day_moves(d.pulse, "2026-10-26"))
        b = vr["coins"]["BTC"]
        guarded(fails, "a record written now for the flip states window_dir up and run_dir down as fields",
                lambda: b["kind"] == "next_read" and b.get("window_dir") == "up" and b.get("run_dir") == "down")
        guarded(fails, "its stored line is still the ruled words and nothing more (the notice is drawn, not stored)",
                lambda: b["line"] == [NEXT_READ] and b["text"] == [NEXT_READ])
        guarded(fails, "and a record with the fields draws the same line as the stored one without them",
                lambda: notice_texts(verdict.card_html(vr, "BTC", where="home", live=True, now=NOW_MORNING)) == [FLIPPED_LINE])


# ---- 4. the home's first object ------------------------------------------------------------------------------------

def first_blocks(h):
    """The top-level children of the home's left column, as (tag, class) in document order."""
    m = re.search(r'<div class="h-l">', h)
    out, depth, i = [], 0, m.end()
    for t in re.finditer(r"<(/?)(aside|section|p|div|h2|h3|ul|ol|a|svg|span|b|em|li|figure|table|time|button)\b([^>]*)>", h[i:]):
        close, tag, rest = t.group(1), t.group(2), t.group(3)
        if close:
            depth -= 1
            if depth < 0:
                break
            continue
        if rest.rstrip().endswith("/"):
            continue
        if depth == 0:
            cm = re.search(r'class="([^"]*)"', rest)
            out.append((tag, cm.group(1) if cm else ""))
        depth += 1
    return out


def front_cases(fails):
    print("4. the verdict card is the home's first object, even when it carries the next-read line; the tape moves under it")
    import home
    with Draw() as d:
        for name, h in (("the window-flipped notice", d.home()),):
            fb = first_blocks(h)
            guarded(fails, f"{name}: the first block of the left column is the card, and the tape is the next",
                    lambda fb=fb: fb[0][0] == "aside" and "vd" in fb[0][1].split() and fb[1] == ("section", "h-b h-tape"))
            guarded(fails, f"{name}: the ten blocks keep section 2's order after it",
                    lambda h=h: tuple(re.findall(r'data-block="([a-z]+)"', h)) == home.ABOVE_FOLD)
    with Draw(NOW_NEXT_DAY) as d:
        fb = first_blocks(d.home())
        guarded(fails, "the no-read notice: the card first, the tape next",
                lambda: fb[0][0] == "aside" and fb[1] == ("section", "h-b h-tape"))
    t = s93()
    import verdict
    v15 = verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15())
    with Draw() as d:
        import snapshot
        p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
        h = home.above_fold(snapshot.build(p, t.s92().load(f"flows_{t.D15()}.json")), p, {}, d.sb.board_deltas(p),
                            t.s92().load(f"wire_{t.D15()}.json"), {}, {}, d.sb.NEWS_CADENCE_LINE,
                            now=dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC), verdict=v15)
        fb = first_blocks(h)
        guarded(fails, "a graded card (the 15 October real record) is still first, the tape next",
                lambda: fb[0][0] == "aside" and fb[1] == ("section", "h-b h-tape"))
        # a withheld verdict is the desk's notice, not an answer: it keeps following the tape's line (9.5, unchanged)
        wh = copy.deepcopy(v15)
        wh["coins"]["BTC"].update(kind="withheld", grade_withheld="Likely", grade=None, text=[], by="withheld", url=None)
        h2 = home.above_fold(snapshot.build(p, t.s92().load(f"flows_{t.D15()}.json")), p, {}, d.sb.board_deltas(p),
                             t.s92().load(f"wire_{t.D15()}.json"), {}, {}, d.sb.NEWS_CADENCE_LINE,
                             now=dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC), verdict=wh)
        fb2 = first_blocks(h2)
        guarded(fails, "a withheld verdict (the day's cap) still follows the tape's line (Sprint 9.5, unchanged)",
                lambda: fb2[0] == ("section", "h-b h-tape") and fb2[1][0] == "aside")


# ---- 5. the page as it was elsewhere ---------------------------------------------------------------------------------

def unchanged_cases(fails):
    print("5. what the item does not name stays as it was")
    import verdict
    t = s93()
    v14 = verdict.record_from(t.rec(t.D14()), "2026-10-14", "evening", day=t.day14())
    c14 = verdict.card_html(v14, "BTC", "home")
    guarded(fails, "a graded card keeps its shape: the aside, the badge, the line",
            lambda: 'class="vd vd-' in c14 and 'class="vd-badge' in c14)
    guarded(fails, "the Ether page's 'Ether moved with Bitcoin' line is the 9.3 line",
            lambda: verdict.card_html(verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15()), "ETH", where="coin")
            in ("", '<p class="vd-plain">Ether moved with Bitcoin since midnight ET.</p>')
            or "vd-plain" in verdict.card_html(verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15()), "ETH", where="coin"))
    guarded(fails, "the stored words for the notice are still the ruled ones",
            lambda: verdict.NEXT_READ == NEXT_READ)
    with Draw() as d:
        h = d.today(here="dated")
        guarded(fails, "a dated /today/ page draws the notice from its own record's time, not the build's",
                lambda: notice_texts(h) == [FLIPPED_LINE])
        # SYNTHETIC composition clock: the same record composed at 7:30 PM ET names tomorrow, as its own "Next update" line does
        late = copy.deepcopy(d.rec)
        late["composed_utc"] = "2026-10-26T23:30:00Z"
        late["next"] = "Next update: Morning Brief, tomorrow at 8:15 AM ET"
        guarded(fails, "SYNTHETIC: a dated page's notice follows the page's own composition clock (the clock its 'Next update' line used)",
                lambda: notice_texts(d.today(rec=late, here="dated")) == [FLIPPED_LINE.replace("tonight at 7:08 PM ET", "tomorrow at 8:15 AM ET")])


# ---- REVIEW 1 (October 26, FAIL at d9db3cd) --------------------------------------------------------------------------------

def section_of(h):
    m = re.search(r'<section class="td-sec ev".*?</section>', h or "", flags=re.S)
    return m.group(0) if m else ""


def nextread_cases(fails):
    print("9. Review 1, failure 3: the time of the next read is the build's on a living page, and the same on the home, /today/ and the coin page")
    import today
    import twins_gate
    tmp = tempfile.mkdtemp(prefix="s991-nr-")
    try:
        with Draw(NOW_LATE) as d:
            wd, vd = os.path.join(tmp, "why"), os.path.join(tmp, "verdict")
            os.makedirs(wd)
            os.makedirs(vd)
            shutil.copy(os.path.join(FX, "why_2026-10-26-morning.json"), os.path.join(wd, "2026-10-26-morning.json"))
            shutil.copy(os.path.join(FX, "verdict_2026-10-26-morning.json"), os.path.join(vd, "2026-10-26-morning.json"))
            with quiet():
                pages = dict((f, h) for f, h, _p, _m in today.build_pages(d.snap, d.pulse, d.wire, None, load("morning.json"), NOW_LATE,
                                                                          twins_gate.Gate(d.snap), stored=[d.rec], why_dir=wd, verdict_dir=vd))
            living, dated = pages["today/index.html"], pages["today/2026-10-26.html"]
            want = FLIPPED_LINE.replace("tonight at 7:08 PM ET", "tomorrow at 8:15 AM ET")
            guarded(fails, "premise: the build is at 7:38 PM ET, after the 7:08 PM slot, and the living page is the morning record",
                    lambda: d.rec["slot"] == "morning" and "Morning Brief" in visible(living))
            when = lambda h: [re.search(r"Next read: (.*)\.$", x).group(1) for x in notice_texts(h)]
            guarded(fails, "the living /today/ names tomorrow's read, not the 7:08 PM slot that has passed",
                    lambda: when(living) == ["tomorrow at 8:15 AM ET"])
            guarded(fails, "the home names the same time", lambda: when(d.home()) == ["tomorrow at 8:15 AM ET"])
            guarded(fails, "the Bitcoin page names the same time", lambda: when(d.coin("BTC")) == ["tomorrow at 8:15 AM ET"])
            guarded(fails, "the three pages print the whole notice the same way (one fact, one value)",
                    lambda: notice_texts(living) == notice_texts(d.home()) == notice_texts(d.coin("BTC")) == [want])
            guarded(fails, "no page of the item prints a next read that is already past",
                    lambda: all("tonight at 7:08 PM ET" not in x for x in notice_texts(living) + notice_texts(d.home()) + notice_texts(d.coin("BTC"))))
            guarded(fails, "a dated page keeps its own record's clock (the day's record never changes with the clock that draws it)",
                    lambda: when(dated) == ["tonight at 7:08 PM ET"] and notice_texts(dated) == [FLIPPED_LINE])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def unsourced_cases(fails):
    print("10. Review 1, failure 4: the window line prints only what the record states")
    import today
    for day in ("2026-10-15", "2026-10-16"):
        rec = json.load(open(os.path.join(HERE, "fixtures", "sprint991", f"real-{day}-evening", "today.json"), encoding="utf-8"))
        h = today.body_html(rec, [], "dated")
        m = re.search(r'<p class="td-stamp td-win"[^>]*>(.*?)</p>', h, flags=re.S)
        line = visible(m.group(1)) if m else ""
        guarded(fails, f"{day} (stored before direction_basis existed, no basis field): the line claims nothing about the Board's midnight open",
                lambda line=line: line and "Board" not in line and "no midnight" not in line and "holds no" not in line)
        guarded(fails, f"{day}: it says the record does not state its window, and the page marks the basis as unstated",
                lambda line=line, h=h: "does not state" in line and attrs_of(h, r'<p class="td-stamp td-win"[^>]*>').get("data-td-basis") == "unstated")
    with Draw() as d:
        rec = copy.deepcopy(d.rec)
        rec["direction_basis"] = "rolling_24h"
        rec["btc"]["chg_day"] = None
        h = today.body_html(rec, [], "dated")
        m = re.search(r'<p class="td-stamp td-win"[^>]*>(.*?)</p>', h, flags=re.S)
        line = visible(m.group(1)) if m else ""
        guarded(fails, "a record that states the rolling 24 hours: the line says so and names it the fallback, with no reason the record does not give",
                lambda: "over the last 24 hours" in line and "fallback" in line and "Board" not in line)


def scope_cases(fails):
    print("11. Review 1, failure 5: the /why/ pages and everything outside the item stay as main wrote them")
    import verdict
    import why_evidence as we
    with Draw() as d:
        sec = we.section_html(d.ev, "BTC", live=False)
        guarded(fails, "the evidence section called without a window is main's: 'the window' wording, no window attribute",
                lambda: "The largest run in the window:" in sec and "data-ev-window" not in sec and "in the 24 hours" not in sec
                and 'class="td-sec ev" aria-label="What lined up with the move" data-ev="BTC">' in sec)
    t = s93()
    v14 = verdict.record_from(t.rec(t.D14()), "2026-10-14", "evening", day=t.day14())
    guarded(fails, "a verdict page's card (where=page) carries no data-vd-basis or data-vd-dir (main's markup)",
            lambda: "data-vd-basis" not in verdict.card_html(v14, "BTC", where="page", live=False)
            and "data-vd-dir" not in verdict.card_html(v14, "BTC", where="page", live=False))
    guarded(fails, "the home's graded card still carries them (the three pages' agreement is read from them)",
            lambda: "data-vd-basis" in verdict.card_html(v14, "BTC", where="home", live=True))


# ---- 12. Review 2 (October 26, 2026, FAIL at f3f6c7f): one window per page, the card and the list never grade apart ------------

NOT_GRADED_LINE = FLIPPED_LINE
FX25 = os.path.join(HERE, "fixtures", "sprint991", "real-2026-10-25-evening")
TIME_WORDS = re.compile(r"(?:Next read|Next update): (?:[A-Za-z ]+, )?((?:this morning|tonight|tomorrow) at \d+:\d\d [AP]M ET)")


def ts(s):
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def next_times(h):
    """Every next-read time a page prints (the card's and the footer's), as the set of distinct values."""
    return set(TIME_WORDS.findall(visible(h)))


def probe(event_utc="2026-10-26T10:10:00Z", grade="Likely"):
    """SYNTHETIC (the reviewer's probe for failure 3): the series drifts 100 to 99 before midnight ET, then runs 99 to 102 from
    6:00 to 9:00 AM ET, one event at `event_utc`, the verdict graded `grade` on the stored 24-hour run. Returns (evidence, verdict, rec)."""
    import verdict as vd
    import why_evidence as we
    ev, v, rec = load("why_2026-10-26-morning.json"), load("verdict_2026-10-26-morning.json"), load("today_2026-10-26-morning.json")
    end, mid, st = ts("2026-10-26T14:00:00Z"), ts("2026-10-26T04:00:00Z"), ts("2026-10-26T14:00:00Z") - 86400
    pts = []
    for t in range(st, end + 1, 300):
        if t <= mid:
            p = 100 - (t - st) / (mid - st)
        elif t < ts("2026-10-26T10:00:00Z"):
            p = 99.0
        elif t <= ts("2026-10-26T13:00:00Z"):
            p = 99 + 3 * (t - ts("2026-10-26T10:00:00Z")) / 10800
        else:
            p = 102.0
        pts.append([t, round(p, 4)])
    ev["window"] = {"start_utc": "2026-10-25T14:00:00Z", "end_utc": "2026-10-26T14:00:00Z", "hours": 24}
    c = ev["coins"]["BTC"]
    c["series"]["points"], c["run"] = pts, we.onset(pts)
    cand = ev["candidates"][0]
    cand.update(event_utc=event_utc, report_utc=event_utc, event_basis="stated in the report")
    ev["candidates"] = [cand]
    res = we.timing(pts, c["run"], ts(event_utc), False)
    c["tests"] = [{"id": cand["id"], "t_utc": event_utc, "basis": "first report", "result": res}]
    day = {"basis": "et_day", "BTC": round((102 / 99 - 1) * 100, 2), "ETH": 1.0}
    with quiet():
        g = vd.grade(ev, "BTC", day)
    if g["kind"] == "graded" and grade == "Likely":
        g["grade"] = "Likely"
        g["phrases"] = g["line"] = ["Bitcoin's rise since midnight ET lines up with the CoinDCX report (reported 6:10 AM ET).",
                                    vd._timing_phrase(vd.timing_pass(res), res, cand)]
        g["phrases_sec"] = list(g["phrases"])
    v = copy.deepcopy(v)
    v["window"] = dict(ev["window"])
    v["coins"]["BTC"] = g
    rec = dict(rec, direction="up", direction_basis="et_day")
    return ev, v, rec, g


def review2_cases(fails):
    import today
    import verdict as vd
    print("12. Review 2, failures 5 and 6 (failures 1 to 4 asserted the ET-day cut, which round 4 removes; round 4 below replaces them)")
    print("   failure 5: one next read per page, none already past")
    tmp = tempfile.mkdtemp(prefix="s991-r2-")
    try:
        import twins_gate
        with Draw(NOW_LATE) as d:
            wd, vdir = os.path.join(tmp, "why"), os.path.join(tmp, "verdict")
            os.makedirs(wd)
            os.makedirs(vdir)
            shutil.copy(os.path.join(FX, "why_2026-10-26-morning.json"), os.path.join(wd, "2026-10-26-morning.json"))
            shutil.copy(os.path.join(FX, "verdict_2026-10-26-morning.json"), os.path.join(vdir, "2026-10-26-morning.json"))
            with quiet():
                pages = dict((f, x) for f, x, _p, _m in today.build_pages(d.snap, d.pulse, d.wire, None, load("morning.json"), NOW_LATE,
                                                                          twins_gate.Gate(d.snap), stored=[d.rec], why_dir=wd, verdict_dir=vdir))
            living, dated = pages["today/index.html"], pages["today/2026-10-26.html"]
            guarded(fails, "the living /today/ prints one next-read time, tomorrow's (the card and the footer agree, none is tonight's 7:08 PM)",
                    lambda: next_times(living) == {"tomorrow at 8:15 AM ET"} and "tonight at 7:08 PM ET" not in visible(living))
            guarded(fails, "the home prints the same one time", lambda: next_times(d.home()) == {"tomorrow at 8:15 AM ET"})
            guarded(fails, "a dated page keeps its own record's one time, card and footer alike",
                    lambda: next_times(dated) == {"tonight at 7:08 PM ET"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("   failure 6: the coin pages agree, and no day-bound line stands as current past its day (SYNTHETIC clock: 6:00 AM ET the next day)")
    with Draw(NOW_NEXT_DAY) as d:
        b, e = d.coin("BTC"), d.coin("ETH")
        guarded(fails, "/coins/btc says no read yet today", lambda: notice_texts(b) == [NO_READ_LINE])
        guarded(fails, "/coins/eth says the same, not yesterday's 'Ether moved with Bitcoin since midnight ET' as if it were today's",
                lambda: notice_texts(e) == [NO_READ_LINE] and "moved with Bitcoin" not in visible(e))
        guarded(fails, "the two coin pages carry the same next-read time and no day-bound sentence of the stored record",
                lambda: next_times(b) == next_times(e) == {"this morning at 8:15 AM ET"})
    with Draw() as d:
        guarded(fails, "inside the day the Ether page keeps its own plain line, in the window of the list beside it (round 4); the stored line is untouched",
                lambda: "Ether moved with Bitcoin over the last 24 hours." in visible(d.coin("ETH"))
                and d.v["coins"]["ETH"]["window_words"] == "since midnight ET"
                and "Ether moved with Bitcoin since midnight ET." in visible(vd.card_html(d.v, "ETH", where="coin")))


def scope_tree(root):
    fails = []
    print("   the tree: no /why/ page carries the window attributes of this item")
    pages = []
    for sub in ("why",):
        for dp, _d, fs in os.walk(os.path.join(root, sub)):
            pages += [os.path.join(dp, f) for f in fs if f.endswith(".html")]
    guarded(fails, "the built tree has /why/ pages to check", lambda: bool(pages))
    # SPRINT 9.9.2 (the one-window sweep, from this item's reviewer): the verdict pages now name the list's window as /today/ and
    # the coin pages do, so the list carries data-ev-window there too; the card still carries no basis attribute (it shows as
    # published), which is what this case keeps
    guarded(fails, "no /why/ page's card carries data-vd-basis (the card on a verdict page shows as published)",
            lambda: all("data-vd-basis" not in open(p, encoding="utf-8", errors="replace").read() for p in pages))
    return fails


# ---- the browser half: the first object at 375 and 1440 ----------------------------------------------------------------

def write_fixture_pages(root):
    """home-991-<name>.html for the next-read, no-read and graded cases, with the site's own assets, in `root`."""
    import home
    import site_build as sb
    import snapshot
    shutil.copytree(sb.ASSETS, os.path.join(root, "assets"), dirs_exist_ok=True)
    t = s93()
    import verdict
    out = {}
    with Draw() as d:
        out["next-read"] = d.home()
    with Draw(NOW_NEXT_DAY) as d:
        out["no-read"] = d.home()
    p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
    fl = t.s92().load(f"flows_{t.D15()}.json")
    v15 = verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15())
    old = (sb.SNAP, sb._NOW_CACHE)
    sb.SNAP, sb._NOW_CACHE = snapshot.build(p, fl), dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)
    try:
        out["graded"] = home.above_fold(sb.SNAP, p, fl, sb.board_deltas(p), t.s92().load(f"wire_{t.D15()}.json"), {}, {},
                                        sb.NEWS_CADENCE_LINE, now=sb._NOW_CACHE, verdict=v15)
    finally:
        sb.SNAP, sb._NOW_CACHE = old
    for name, above in out.items():
        body = (f'<main class="wrap h-page"><section class="page"><h1 class="sr-only">GoCheckMyCrypto: fixture</h1>'
                f'{above}</section></main>')
        with quiet():
            page = sb.shell("Home 9.9.1 fixture - GoCheckMyCrypto", "fixture", "The Board", body, "T", body_class="h-home",
                            path="/", system_css=True, third_party=False)
        with open(os.path.join(root, f"home-991-{name}.html"), "w", encoding="utf-8") as f:
            f.write(page)
    return sorted(out)


@contextlib.contextmanager
def scratch_writers():
    """SPRINT 9.9.2: the build's two dated writers (the Board snapshot, site/data/snapshots/pulse-<date>.json, and the Chart
    Master copy, site/data/chartmaster/<date>.json) pointed at scratch copies while the browser half draws its pages, as the
    canary's layer1_canary does, so nothing it calls can write one into the tree; put back in a finally."""
    import site_build as sb
    scratch = tempfile.mkdtemp(prefix="s991-data-")
    saved = (sb.SNAPSHOT_DIR, sb.CM_ARCHIVE)
    try:
        for name, real in (("snapshots", sb.SNAPSHOT_DIR), ("chartmaster", sb.CM_ARCHIVE)):
            if os.path.isdir(real):
                shutil.copytree(real, os.path.join(scratch, name))
            else:
                os.makedirs(os.path.join(scratch, name))
        sb.SNAPSHOT_DIR, sb.CM_ARCHIVE = os.path.join(scratch, "snapshots"), os.path.join(scratch, "chartmaster")
        yield scratch
    finally:
        sb.SNAPSHOT_DIR, sb.CM_ARCHIVE = saved
        shutil.rmtree(scratch, ignore_errors=True)


def browser(fails):
    print("6. the home's first object at 375 and 1440, from a fixture page (Playwright)")
    tmp = tempfile.mkdtemp(prefix="s991-")
    import site_build as sb
    before = set(os.listdir(sb.SNAPSHOT_DIR)) if os.path.isdir(sb.SNAPSHOT_DIR) else set()
    try:
        with scratch_writers():
            names = write_fixture_pages(tmp)
        guarded(fails, "the fixture pages were written (next-read, no-read, graded)", lambda: names == ["graded", "next-read", "no-read"])
        r = subprocess.run(["node", os.path.join(HERE, "scripts", "sprint991_browser.mjs"), tmp], capture_output=True, text=True,
                           timeout=240)
        for ln in (r.stdout or "").splitlines():
            if ln.startswith(("PASS ", "FAIL ", "INFO ")):
                print("  " + ln)
                if ln.startswith("FAIL "):
                    fails.append("browser " + ln[5:])
        if r.returncode not in (0, 1) or not (r.stdout or "").strip():
            fails.append(f"browser half could not run (exit {r.returncode}): {(r.stderr or '')[-200:]}")
        guarded(fails, "the browser half ran every case and none failed", lambda: r.returncode == 0 and "PASS" in (r.stdout or ""))
        after = set(os.listdir(sb.SNAPSHOT_DIR)) if os.path.isdir(sb.SNAPSHOT_DIR) else set()
        guarded(fails, "the browser half wrote no dated snapshot into the tree (site/data/snapshots, Sprint 9.9.2)",
                lambda: after == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- the tree this build wrote -------------------------------------------------------------------------------------------

def tree(root):
    fails = []
    print("7. the tree this build wrote: the home's first object")
    p = os.path.join(root, "index.html")
    h = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    guarded(fails, "the built home exists", lambda: bool(h))
    if not h:
        return fails
    fb = first_blocks(h)
    # the canary's fixture build reads a verdict record of the 15 October, never today's: so its home carries the no-read notice
    guarded(fails, "the built home's first object below the masthead is a verdict card (a graded card or the notice), "
                   "and the tape is the block after it",
            lambda: fb and ((fb[0][0] == "aside" and "vd" in fb[0][1].split() and fb[1] == ("section", "h-b h-tape"))
                            # a flat day (a record dated today that grades nothing) draws no card: the tape leads and no card follows
                            or (fb[0] == ("section", "h-b h-tape") and 'data-vd="BTC"' not in h)))
    n = notice_texts(h)
    guarded(fails, "when the built home carries the notice, it is one line with a reason and a time of the next read",
            lambda: len(n) <= 1 and all(NEXT_READ + ": " in x and "Next read: " in x and x.endswith(".") for x in n))
    cp = os.path.join(root, "coins", "btc.html")
    c = open(cp, encoding="utf-8").read() if os.path.exists(cp) else ""
    guarded(fails, "the built Bitcoin page carries the verdict card or the notice, as the home does (the build hands the page its clock)",
            lambda: re.search(r'<aside class="vd[^"]*" data-vd="BTC"', c) is not None or 'data-vd="BTC"' not in h)
    # ROUND 4: the dated page of a graded day shows the stored verdict as published, with its own window and its /why/ link
    dp = os.path.join(root, "today", "2026-10-25.html")
    d = open(dp, encoding="utf-8").read() if os.path.exists(dp) else ""
    if 'data-vd="BTC"' in d:                    # the canary's fixture build holds no 25 October records; a build of the stored ones does
        vis = visible(d)
        guarded(fails, "the built /today/2026-10-25 shows the stored graded Unclear verdict with its window and its /why/ link, and no notice",
                lambda: "Checked: Unclear" in vis and "Since midnight ET" in vis and 'href="/why/2026-10-25-bitcoin"' in d
                and not notice_texts(d) and "did not grade" not in vis)
        guarded(fails, "its evidence list reads the window the grade was made on (the 24 hours), named",
                lambda: 'data-ev-window="rolling_24h"' in d and "the 24 hours to" in visible(section_of(d)))
    guarded(fails, "no built page prints 'did not grade' (the notice prints only for a flip or for no read yet today)",
            lambda: all("the last read did not grade" not in visible(open(os.path.join(dp2, f), encoding="utf-8", errors="replace").read())
                        for dp2, _d, fs in os.walk(root) for f in fs if f.endswith(".html")))
    fails += scope_tree(root)
    guarded(fails, "no built page that carries the bare words 'Verdict at the next read' lacks a reason and a time",
            lambda: all(_every_notice_full(os.path.join(dp, f)) for dp, _d, fs in os.walk(root) for f in fs if f.endswith(".html")))
    return fails


def _every_notice_full(path):
    h = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'<p class="vd-plain vd-next"[^>]*>(.*?)</p>', h, flags=re.S):
        t = visible(m.group(1))
        if not ("Next read: " in t and (": the run the last read measured went " in t or ": no read yet today" in t)):
            return False
    return True


# ---- 13. ROUND 4 (October 27, 2026, entry 2026-10-26-C6, J-16 option 2) -----------------------------------------------------
#
# The ET-day cut of the evidence list leaves 9.9.1 (it moves to 9.9.3 with the timing test and the grade). Until then the evidence list
# reads the window the grade was made on, a graded verdict shows on its dated /today/ page as published, and the notice prints only
# for a flip or for no read yet today, in words true on that page.

FLIP4_LINE = FLIPPED_LINE


def round4_cases(fails):
    import today
    import verdict as vd
    print("13. Round 4, change 1: the evidence list reads the window the grade was made on (the cut is gone)")
    with Draw() as d:
        for name, h in (("/today/", d.today()), ("/coins/btc", d.coin("BTC")), ("/coins/eth", d.coin("ETH"))):
            sec = re.search(r'<section class="td-sec ev".*?</section>', h, flags=re.S).group(0)
            st = visible(sec)
            guarded(fails, f"{name}: the section is the stored record's 24 hours, named, and never cut at midnight ET",
                    lambda sec=sec: 'data-ev-window="rolling_24h"' in sec and 'data-ev-window="et_day"' not in sec)
            guarded(fails, f"{name}: the section's head names the 24 hours to the reading, with its second sources as the record states them",
                    lambda st=st: re.search(r"the 24 hours to 8:17 AM ET", st) and "are not read for this window" not in st
                    and "since midnight ET to" not in st)
            guarded(fails, f"{name}: no figure of the section is cut to midnight ET (no 'since midnight ET' inside the list's figures)",
                    lambda st=st: "since midnight ET" not in st and "falls before midnight ET" not in st)
        t = visible(section_of(d.today()))
        guarded(fails, "/today/: the run is the stored run of the 24 hours, down 1.70%, with its window named beside it",
                lambda: re.search(r"The largest run in the 24 hours: ▼ 1\.70%", t) is not None)
        guarded(fails, "/today/: the chart is labeled with the 24 hours it draws",
                lambda: re.search(r'<svg class="ev-chart"[^>]*aria-label="[^"]*the 24 hours to 8:17 AM ET',
                                  section_of(d.today())) is not None)
        guarded(fails, "the stored evidence is read, never written", lambda: d.ev == load("why_2026-10-26-morning.json"))
    with Draw() as d:
        ev = copy.deepcopy(d.ev)
        h = d.today(evidence=ev)
        figs = re.findall(r'<span class="ev-t">([^<]*)</span>', section_of(h))
        guarded(fails, "every timing figure of the list names its window (in the 24 hours), none says 'the window'",
                lambda: all(("in the 24 hours" in f or "no time" in f.lower() or "outside" in f) for f in figs if "%" in f)
                and "of the window" not in visible(h))

    print("   change 2: the dated page shows a graded verdict as published, with its own window and its /why/ link (J-10)")
    rec25 = json.load(open(os.path.join(FX25, "today.json"), encoding="utf-8"))
    ev25 = json.load(open(os.path.join(FX25, "why.json"), encoding="utf-8"))
    v25 = json.load(open(os.path.join(FX25, "verdict.json"), encoding="utf-8"))
    h = today.body_html(rec25, [], "dated", evidence=ev25, verdict=v25)
    vis = visible(h)
    card = (re.search(r'<aside class="vd[^"]*"[^>]*>.*?</aside>', h, flags=re.S) or [""])[0]
    guarded(fails, "premise, from the stored record: graded Unclear, basis et_day, down, with its /why/ address",
            lambda: v25["coins"]["BTC"]["kind"] == "graded" and v25["coins"]["BTC"]["grade"] == "Unclear"
            and v25["coins"]["BTC"]["basis"] == "et_day" and v25["coins"]["BTC"]["dir"] == "down"
            and v25["coins"]["BTC"]["url"] == "/why/2026-10-25-bitcoin")
    guarded(fails, "/today/2026-10-25 shows the stored graded Unclear verdict, in its own words",
            lambda: "Checked: Unclear" in visible(card) and "No reported event lines up with this move." in visible(card))
    guarded(fails, "it names the verdict's own window (since midnight ET) and links its /why/ page",
            lambda: "Since midnight ET" in visible(card) and 'href="/why/2026-10-25-bitcoin"' in card)
    guarded(fails, "it prints no 'did not grade' notice and no 'Verdict at the next read' anywhere",
            lambda: not notice_texts(h) and "did not grade" not in vis and NEXT_READ not in vis)
    sec = section_of(h)
    guarded(fails, "its evidence list reads the window the grade was made on: the 24 hours, named, not cut to the ET day",
            lambda: 'data-ev-window="rolling_24h"' in sec and "the 24 hours to" in visible(sec) and "since midnight ET" not in visible(sec))
    line = visible(re.search(r'<p class="td-stamp td-win".*?</p>', h, flags=re.S).group(0))
    guarded(fails, "the page names both windows once, each beside what it measures (the direction since midnight ET, the list the 24 hours)",
            lambda: "direction above is read since midnight ET" in line and "24 hours to" in line)
    guarded(fails, "no em dash or en dash", lambda: not EM.search(h))
    before = copy.deepcopy(v25)
    today.body_html(rec25, [], "dated", evidence=ev25, verdict=v25)
    guarded(fails, "drawing the page leaves the stored verdict untouched, word for word (J-10)", lambda: v25 == before)
    # the same record on the living page, the day it was graded: the card stands there too, no notice for a graded verdict
    with Draw() as d:
        import home
        now25 = dt.datetime(2026, 10, 25, 23, 40, tzinfo=UTC)
        h2 = today.body_html(rec25, [], "living", evidence=ev25, verdict=v25, clock=now25)
        guarded(fails, "the living page, on the day of the read: the graded card stands, and no notice",
                lambda: "Checked: Unclear" in visible(h2) and not notice_texts(h2))

    print("   changes 3 and 6: the notice prints only for a flip or for no read yet today, and its words are true on that page")
    with Draw() as d:
        pages = {"home": d.home(), "/today/": d.today(clock=NOW_MORNING), "/today/2026-10-26": d.today(here="dated"),
                 "/coins/btc": d.coin("BTC")}
        for name, pg in pages.items():
            guarded(fails, f"{name}: the flip notice says the measured run's direction and the direction since midnight ET, then the next read",
                    lambda pg=pg: notice_texts(pg) == [FLIP4_LINE])
        guarded(fails, "the flip's two directions are the record's fields: the run went down, the move since midnight ET is up",
                lambda: d.v["coins"]["BTC"]["run_dir"] == "down" and d.v["coins"]["BTC"]["window_dir"] == "up"
                if "run_dir" in d.v["coins"]["BTC"] else True)
        stored = copy.deepcopy(d.v)
        # a record written before the fields existed carries both directions in its reasons: the same line
        guarded(fails, "a stored flip without the fields (its reasons state both) draws the same line",
                lambda: notice_texts(vd.card_html(stored, "BTC", where="home", live=True, now=NOW_MORNING)) == [FLIP4_LINE])
        # a flip whose window is the 24 hours says so in the 24 hours' words
        roll = copy.deepcopy(stored)
        roll["coins"]["BTC"].update(basis="rolling_24h", window_words="over the last 24 hours", window_dir="up", run_dir="down")
        guarded(fails, "a flip stored on the rolling 24 hours names that window, not midnight ET",
                lambda: notice_texts(vd.card_html(roll, "BTC", where="home", live=True, now=NOW_MORNING))
                == [FLIP4_LINE.replace("since midnight ET", "over the last 24 hours")])
        # a graded verdict never draws a notice, on any of the pages, on its own day
        t = s93()
        v15 = vd.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15())
        guarded(fails, "a graded card on its own day draws no notice (the home)",
                lambda: not notice_texts(vd.card_html(v15, "BTC", where="home", live=True,
                                                     now=dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC))))

    print("   change 5: the living /today/ prints the no-read notice when no read has run today, as the home and the coin pages do")
    with Draw(NOW_NEXT_DAY) as d:
        living = d.today(clock=NOW_NEXT_DAY)
        guarded(fails, "the living /today/ at 6:00 AM ET the next day: one notice, 'no read yet today', with the time of the next read",
                lambda: notice_texts(living) == [NO_READ_LINE])
        guarded(fails, "it agrees word for word with the home and both coin pages",
                lambda: notice_texts(living) == notice_texts(d.home()) == notice_texts(d.coin("BTC")) == notice_texts(d.coin("ETH")))
        guarded(fails, "the notice stands in the card's place: after the answer, before 'What moved'",
                lambda: living.index('class="td-answer"') < living.index("vd-next") < living.index("<h2>What moved</h2>"))
        guarded(fails, "no stored card of yesterday stands beside it", lambda: "Checked:" not in visible(living))
        guarded(fails, "the dated page of that record is unchanged by the clock (it keeps its own record's words)",
                lambda: notice_texts(d.today(here="dated", clock=NOW_NEXT_DAY)) == [FLIP4_LINE])
        # no verdict record at all for the living page: the same notice
        guarded(fails, "the living /today/ with no verdict record, no read yet today: the same notice",
                lambda: notice_texts(d.today(verdict=None, clock=NOW_NEXT_DAY)) == [NO_READ_LINE])
    with Draw() as d:
        # the build of 12:33 AM ET on October 27 (review 3, failure 3): the living record is composed for today, no read has run on today
        guarded(fails, "the living /today/ composed for today with no verdict record for today (the reviewer's build): 'no read yet today', "
                       "as the home and the coin pages print",
                lambda: notice_texts(d.today(verdict=None, clock=NOW_MORNING))
                == notice_texts(d.home(verdict=None)) == ["Verdict at the next read: no read yet today. Next read: tonight at 7:08 PM ET."])
        guarded(fails, "the living /today/ on the day of the read prints the flip notice, not 'no read yet today'",
                lambda: notice_texts(d.today(clock=NOW_MORNING)) == [FLIP4_LINE])
        flat = copy.deepcopy(d.v)
        flat["coins"]["BTC"].update(kind="flat", line=[], text=[], reasons=["within 0.5% since midnight ET: under the threshold, no card"])
        guarded(fails, "a flat day's record, dated today: the living /today/ draws no card and no notice (nothing was missed)",
                lambda: not notice_texts(d.today(verdict=flat, clock=NOW_MORNING)))

    print("   change 4: the coin pages and the living /today/ name every window; the card and the list do not claim one they do not share")
    with Draw() as d:
        e = d.coin("ETH")
        esec = re.search(r'<section class="td-sec ev".*?</section>', e, flags=re.S).group(0)
        guarded(fails, "/coins/eth: the card's line and the list's window never sit in two windows without the page saying so: "
                       "the Ether line reads the window of the list (the 24 hours), computed from the same stored prices",
                lambda: "Ether moved with Bitcoin over the last 24 hours." in visible(e) and "Ether moved with Bitcoin since midnight ET" not in visible(e))
        guarded(fails, "/coins/eth: the 24-hour list is named the 24 hours and the cut's fallback note is gone",
                lambda: "the named fallback" not in visible(e) and "the 24 hours to 8:17 AM ET" in visible(esec))
        b = d.coin("BTC")
        bsec = re.search(r'<section class="td-sec ev".*?</section>', b, flags=re.S).group(0)
        guarded(fails, "/coins/btc: the section names its window in its head and in the chart; the notice names the other window plainly",
                lambda: "the 24 hours to 8:17 AM ET" in visible(bsec) and notice_texts(b) == [FLIP4_LINE]
                and "since midnight ET" in notice_texts(b)[0])
        t = d.today(clock=NOW_MORNING)
        line = visible(re.search(r'<p class="td-stamp td-win".*?</p>', t, flags=re.S).group(0))
        guarded(fails, "/today/: the window line names the direction's window and the list's window, once each",
                lambda: "since midnight ET" in line and "24 hours to 8:17 AM ET" in line and "the grade was made on" not in line)
    # a graded card beside its list (the probe): the card keeps its published window; the page names the list's
    ev, v, rec, g = probe(event_utc="2026-10-26T09:40:00Z")
    with Draw() as d:
        hc = d.coin("BTC", verdict=v, evidence=ev)
        hv = visible(hc)
        guarded(fails, "SYNTHETIC graded card beside its list: the card stands as stored, and the page says which window each reads",
                lambda: "Checked:" in hv and "Since midnight ET" in hv and "the 24 hours to" in hv
                and "The card above reads its direction since midnight ET; this chart and list read the 24 hours" in hv)
        ht = today.body_html(rec, [], "living", evidence=ev, verdict=v, clock=NOW_MORNING)
        guarded(fails, "SYNTHETIC: /today/ draws the same card beside the same list, no notice",
                lambda: "Checked:" in visible(ht) and not notice_texts(ht))


# ---- 14. ROUND 5 (October 27, 2026, review 4 FAIL at cdb4b05): "the window the grade was made on" only where a grade exists ----------------

def round5_cases(fails):
    import today
    print("14. Round 5: the page claims a grade only where the stored record holds one; elsewhere it names only the list's window")
    GRADE_CLAIM = "the window the grade was made on"
    with Draw() as d:
        kinds = {}
        for k in ("flat", "no_verdict", "next_read", "withheld"):
            v = copy.deepcopy(d.v)
            b = v["coins"]["BTC"]
            b.update(kind=k, grade=None)
            if k in ("flat", "no_verdict"):
                b.update(line=[], text=[], reasons=["no grade fits"])
            if k == "withheld":
                b.update(basis="et_day", window_words="since midnight ET", line=[], text=[])
            kinds[k] = v
        kinds["none"] = None
        for k, v in kinds.items():
            for name, h in (("living /today/", d.today(verdict=v, clock=NOW_MORNING)),
                            ("dated /today/", d.today(verdict=v, here="dated")),
                            ("/coins/btc", d.coin("BTC", verdict=v))):
                guarded(fails, f"{k} record, {name}: no claim that a grade was made, and the list's window is named",
                        lambda h=h: GRADE_CLAIM not in visible(h) and "the 24 hours to 8:17 AM ET" in visible(h))
        w = kinds["withheld"]
        guarded(fails, "withheld on the coin page: the page names the card's window and the list's window, and claims no grade",
                lambda: "this chart and list read the 24 hours to 8:17 AM ET" in visible(d.coin("BTC", verdict=w))
                and GRADE_CLAIM not in visible(d.coin("BTC", verdict=w)))
        guarded(fails, "withheld on /today/: the line names the list's window and no grade",
                lambda: "read the 24 hours to 8:17 AM ET." in visible(re.search(r'<p class="td-stamp td-win".*?</p>', d.today(verdict=w, here="dated"), flags=re.S).group(0)))
    rec25 = json.load(open(os.path.join(FX25, "today.json"), encoding="utf-8"))
    ev25 = json.load(open(os.path.join(FX25, "why.json"), encoding="utf-8"))
    v25 = json.load(open(os.path.join(FX25, "verdict.json"), encoding="utf-8"))
    guarded(fails, "a graded record (the stored 25 October Unclear) keeps the claim: the grade was made on that window",
            lambda: GRADE_CLAIM in visible(today.body_html(rec25, [], "dated", evidence=ev25, verdict=v25)))
    ev, v, rec, g = probe(event_utc="2026-10-26T09:40:00Z")
    with Draw() as d:
        guarded(fails, "a graded card beside its list on the coin page keeps the note, with the grade claim",
                lambda: GRADE_CLAIM in visible(d.coin("BTC", verdict=v, evidence=ev)))


def unit(only=()):
    fails = []
    for name, fn in (("today", today_cases), ("notice", notice_cases), ("agree", agree_cases), ("front", front_cases),
                     ("unchanged", unchanged_cases), ("nextread", nextread_cases),
                     ("unsourced", unsourced_cases), ("scope", scope_cases), ("review2", review2_cases),
                     ("round4", round4_cases), ("round5", round5_cases)):
        if only and name not in only:
            continue
        group(fails, name, fn)
    return fails


def main():
    args = sys.argv[1:]
    only = args[args.index("--only") + 1].split(",") if "--only" in args else ()
    fails = unit(only)
    if "--tree" in args:
        root = args[args.index("--tree") + 1]
        if not only:
            fails += tree(root)
        elif "scope" in only:
            fails += scope_tree(root)
    if "--browser" in args:
        group(fails, "browser", browser)
    print(f"\nSPRINT 9.9.1: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
