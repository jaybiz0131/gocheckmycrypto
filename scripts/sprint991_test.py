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
REVIEW 1 (October 26, 2026, FAIL at d9db3cd) AND THIS ROUND'S CASES: the evidence list and chart of /today/ and the coin pages are cut to the
ET day (the page's window), the figures beside them name it, the notice names one window and its next read follows the build clock on a
living page, the window line prints only what the record states, and the /why/ pages stay as main wrote them. fixtures/sprint991/
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
FLIPPED_LINE = ("Verdict at the next read: the window flipped since the run (the move since midnight ET is up). "
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

    def home(self, verdict="real", now=None):
        import home
        v = self.v if verdict == "real" else verdict
        import inspect
        kw = {"evidence": self.ev} if "evidence" in inspect.signature(home.above_fold).parameters else {}
        return home.above_fold(self.snap, self.pulse, self.flows, self.sb.board_deltas(self.pulse), self.wire, {}, {},
                               self.sb.NEWS_CADENCE_LINE, now=now or self.now, verdict=v, **kw)

    def today(self, verdict="real", rec=None, here="living", evidence="real"):
        import today
        return today.body_html(rec or self.rec, [], here, evidence=self.ev if evidence == "real" else evidence,
                               verdict=self.v if verdict == "real" else verdict)

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
        guarded(fails, "the window line says the chart and the list read the same window, with no figure of its own and no second window",
                lambda: "same window" in line and "midnight ET to 8:17 AM ET" in line and "24 hours" not in line
                and "went down" not in line and not re.search(r"\d\.\d\d%", line))
        guarded(fails, "the window line sits under the stamp and above the answer",
                lambda: h.index('class="td-stamp"') < h.index('class="td-stamp td-win"') < h.index('class="td-answer"'))
        ev = re.search(r'<section class="td-sec ev".*?</section>', h, flags=re.S)
        evt = visible(ev.group(0)) if ev else ""
        guarded(fails, "the evidence section reads the ET day and says so in its own attribute (Review 1, failure 1)",
                lambda: 'data-ev-window="et_day"' in (ev.group(0) if ev else ""))
        guarded(fails, "the evidence's run figure carries its window's name beside it (since midnight ET), never 'the window' alone",
                lambda: re.search(r"The largest run since midnight ET: ▲ [\d.]+%", evt) and "in the window:" not in evt)
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
            guarded(fails, f"{name}: one notice, and it reads exactly the window-flipped line with the next read's time",
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
        guarded(fails, "the Ether page draws no notice for a verdict the desk never grades for Ether without Bitcoin's",
                lambda: not notice_texts(d.coin("ETH", verdict=None)))
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
        guarded(fails, "/today/ and /coins/btc name the same evidence window (since midnight ET to 8:17 AM ET)",
                lambda: e1 and e2 and visible(e1.group(1)) == visible(e2.group(1)) and "since midnight ET to 8:17 AM ET" in visible(e1.group(1)))
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


def window_cases(fails):
    print("8. Review 1, failures 1 and 2: the chart, the list and the headline read one window, and each figure names it")
    import verdict
    import why_evidence as we
    with Draw() as d:
        for name, h in (("/today/", d.today()), ("/coins/btc", d.coin("BTC"))):
            sec = section_of(h)
            st = visible(sec)
            guarded(fails, f"{name}: the evidence section reads the ET day (data-ev-window et_day), not the 24 hours",
                    lambda sec=sec: 'data-ev-window="et_day"' in sec)
            guarded(fails, f"{name}: the section's text names no 24-hour window at all (the headline's window is the only one)",
                    lambda st=st: st and "24 hours" not in st and "24-hour" not in st)
            guarded(fails, f"{name}: the largest run is read since midnight ET and went up, as the headline says (up 0.77%)",
                    lambda st=st: re.search(r"The largest run since midnight ET: ▲ [\d.]+%", st) is not None)
            guarded(fails, f"{name}: the chart is labeled with the window it draws (since midnight ET), not the 24 hours",
                    lambda sec=sec: re.search(r'<svg class="ev-chart"[^>]*aria-label="[^"]*since midnight ET', sec) is not None
                    and not re.search(r'<svg class="ev-chart"[^>]*aria-label="[^"]*24 hours', sec))
            guarded(fails, f"{name}: no figure is printed beside 'the window' (it would name neither window)",
                    lambda h=h: "of the window" not in visible(h) and "against the window" not in visible(h))
            guarded(fails, f"{name}: the events of the day before are not listed in a window that opened at midnight ET",
                    lambda sec=sec: 'class="ev-cands"' not in sec and "since midnight ET" in
                    (re.search(r'<p class="ev-m">The desk found no[^<]*</p>', sec).group(0) if re.search(r'<p class="ev-m">The desk found no[^<]*</p>', sec) else ""))
            guarded(fails, f"{name}: the readings of the run's hour are not drawn for another run than the window's largest, and the page says so",
                    lambda sec=sec, st=st: "The hour the run began" not in st and 'class="ev-mech"' not in sec
                    and "is not the largest run in this window" in st)
        today_h, coin_h = d.today(), d.coin("BTC")
        guarded(fails, "/today/: the notice names the page's window only (no 24-hour run beside the ET day)",
                lambda: all("24-hour" not in x and "24 hours" not in x for x in notice_texts(today_h)) and notice_texts(today_h))
        guarded(fails, "the home and /coins/btc: the same, one window in the notice",
                lambda: all("24-hour" not in x for x in notice_texts(d.home()) + notice_texts(coin_h)) and notice_texts(coin_h))
        guarded(fails, "the headline says up and the section's largest run went up: the page no longer reads up over a fall",
                lambda: d.rec["direction"] == "up" and "went down" not in visible(today_h)
                and re.search(r"▼ 1\.70%", visible(section_of(today_h))) is None)
        # the grade is the stored one: moving the display does not move how a stored verdict is graded (the rulings of October 19 and 20)
        with quiet():
            g = verdict.grade(d.ev, "BTC", verdict.day_moves(d.pulse, "2026-10-26"))
        st = d.v["coins"]["BTC"]
        guarded(fails, "grade() on the real record is the stored one (next_read, the flip's fields, the ET day basis)",
                lambda: g["kind"] == st["kind"] == "next_read" and g["line"] == st["line"] and g["basis"] == st["basis"] == "et_day"
                and g["reasons"] == st["reasons"] and g["move_pct"] == st["move_pct"])
        # the evidence record is read, never written: its own series and run are as stored
        ev0 = copy.deepcopy(d.ev)
        d.today()
        d.coin("BTC")
        guarded(fails, "drawing the pages leaves the stored evidence record as it was",
                lambda: d.ev == ev0 and d.ev["coins"]["BTC"]["run"]["dir"] == "down")
        # SYNTHETIC: one candidate moved into the ET day, so the list has an item whose figures need their window's name
        ev = copy.deepcopy(d.ev)
        ev["candidates"][1]["report_utc"] = "2026-10-26T04:30:00Z"
        for t in ev["coins"]["BTC"]["tests"]:
            if t["id"] == ev["candidates"][1]["id"]:
                t["t_utc"] = "2026-10-26T04:30:00Z"
        h = d.today(evidence=ev)
        sec = section_of(h)
        figs = re.findall(r'<span class="ev-t">([^<]*)</span>', sec)
        guarded(fails, "SYNTHETIC candidate in the ET day: the list prints it, its timing figure names the window",
                lambda: len(figs) == 1 and re.search(r"% of the (rise|fall) since midnight ET", figs[0]) is not None)
        guarded(fails, "SYNTHETIC: a candidate before the window opened (a day earlier) is not listed",
                lambda: sec.count('data-ev-id=') == 1)
    # the named fallback: a stored series that does not reach midnight ET cannot be cut honestly
    print("   the 24 hours only as the named fallback, with the window's name beside every figure")
    with Draw() as d:
        ev = copy.deepcopy(d.ev)
        ev["candidates"][1]["report_utc"] = "2026-10-26T04:30:00Z"
        for t in ev["coins"]["BTC"]["tests"]:
            if t["id"] == ev["candidates"][1]["id"]:
                t["t_utc"] = "2026-10-26T04:30:00Z"
        pts = ev["coins"]["BTC"]["series"]["points"]
        ev["coins"]["BTC"]["series"]["points"] = [p for p in pts if p[0] >= 1792987200 + 3600]     # SYNTHETIC: nothing before 1:00 AM ET
        h = d.today(evidence=ev)
        sec = section_of(h)
        st = visible(sec)
        guarded(fails, "SYNTHETIC series starting after midnight ET: the section names the 24 hours as the fallback in its attribute",
                lambda: 'data-ev-window="rolling_24h"' in sec)
        guarded(fails, "the fallback says why, from the stored prices",
                lambda: "read the 24 hours" in st and "do not reach midnight ET" in st)
        guarded(fails, "every figure of the fallback names the 24 hours (run, shares)",
                lambda: re.search(r"The largest run in the 24 hours: [▲▼] [\d.]+%", st) and
                all(re.search(r"(of the (rise|fall)|against the (rise|fall)) in the 24 hours", f) for f in re.findall(r'<span class="ev-t">([^<]*)</span>', sec)
                    if "next 60 minutes" in f or "rest of" in f))
        guarded(fails, "the fallback's window line on /today/ names the fallback and the reason, so the page never hides two windows",
                lambda: re.search(r"The chart and the list below read the 24 hours to 8:17 AM ET", visible(re.search(r'<p class="td-stamp td-win".*?</p>', h, flags=re.S).group(0))) is not None)
        # the direction check: the cut must run the way the page reads
        ok = we.section_html(d.ev, "BTC", live=True, window="et_day", want_dir="up")
        bad = we.section_html(d.ev, "BTC", live=True, window="et_day", want_dir="down")
        guarded(fails, "the cut must run the way the page's direction reads: the same day read as down falls back and says so",
                lambda: 'data-ev-window="et_day"' in ok and 'data-ev-window="rolling_24h"' in bad and "run the other way" in visible(bad))
        # a graded card is graded on the stored run: a cut that finds another run falls back, so card and list never grade apart
        diff = we.section_html(d.ev, "BTC", live=True, window="et_day", want_dir="up", graded="Likely")
        guarded(fails, "a graded verdict whose stored run is not the day's run: the list falls back to the 24 hours the grade was made on",
                lambda: 'data-ev-window="rolling_24h"' in diff and "the verdict is graded on" in visible(diff))


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

# The notice's reason names the window the page shows and the way the move ran in it, and no run the page does not draw.
NOT_GRADED_LINE = ("Verdict at the next read: the last read did not grade the move since midnight ET (it is up). "
                   "Next read: tonight at 7:08 PM ET.")
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
    print("12. Review 2, failure 1: /today/2026-10-25 reads one window, the one its record states (since midnight ET)")
    rec25 = json.load(open(os.path.join(FX25, "today.json"), encoding="utf-8"))
    ev25 = json.load(open(os.path.join(FX25, "why.json"), encoding="utf-8"))
    v25 = json.load(open(os.path.join(FX25, "verdict.json"), encoding="utf-8"))
    h = today.body_html(rec25, [], "dated", evidence=ev25, verdict=v25)
    sec, line = section_of(h), visible(re.search(r'<p class="td-stamp td-win".*?</p>', h, flags=re.S).group(0))
    guarded(fails, "the premise, from the real record: the headline reads down since midnight ET and the stored verdict is a graded "
                   "Unclear on the 24-hour run", lambda: rec25["direction"] == "down" and rec25["direction_basis"] == "et_day"
            and v25["coins"]["BTC"]["kind"] == "graded" and v25["coins"]["BTC"]["basis"] == "et_day")
    guarded(fails, "the evidence section is drawn on the ET day, not on the 24 hours as a fallback taken for another reason",
            lambda: 'data-ev-window="et_day"' in sec)
    guarded(fails, "no graded card stands over a list its run does not reach: the card is the notice, not 'Checked: Unclear'",
            lambda: "Checked:" not in visible(h) and len(notice_texts(h)) == 1)
    guarded(fails, "the page names no 24-hour window anywhere (line, notice, list, chart)",
            lambda: "24 hours" not in line and "24 hours" not in visible(sec) and "24 hours" not in " ".join(notice_texts(h))
            and not re.search(r'aria-label="[^"]*24 hours', sec))
    guarded(fails, "the list does not print the hour of a run that began before the window opened (Sat 11:20 PM ET)",
            lambda: "Sat 11:20 PM" not in visible(sec) and "The hour the run began" not in visible(sec))
    guarded(fails, "the notice names the window the list reads", lambda: "since midnight ET" in notice_texts(h)[0])
    print("   failure 2: the notice's reason names a window and a fact the page itself prints, and no run the page does not draw")
    with Draw() as d:
        dated = d.today(here="dated")
        for name, pg in (("home", d.home()), ("/today/", d.today()), ("/today/2026-10-26", dated), ("/coins/btc", d.coin("BTC"))):
            guarded(fails, f"{name}: the notice reads the ruled-out run no more, and says what the last read did not grade",
                    lambda pg=pg: notice_texts(pg) == [NOT_GRADED_LINE])
            guarded(fails, f"{name}: the notice does not say a window flipped since 'the run' (no run is drawn beside it)",
                    lambda pg=pg: all("flipped" not in x and "the run" not in x for x in notice_texts(pg)) and notice_texts(pg))
        for name, pg in (("/today/", d.today()), ("/coins/btc", d.coin("BTC"))):
            sec = section_of(pg)
            guarded(fails, f"{name}: the window the notice names is the one the list below it reads",
                    lambda sec=sec, pg=pg: 'data-ev-window="et_day"' in sec and "since midnight ET" in notice_texts(pg)[0])
    print("   failure 3 (SYNTHETIC probe): the card and the list never grade apart")
    ev, v, rec, g = probe()
    st = ev["coins"]["BTC"]["tests"][0]["result"]
    import why_evidence as we
    cut = we.resolve_window(ev, "BTC", "et_day", "up", None)
    ct = cut["rec"]["coins"]["BTC"]["tests"][0]["result"]
    guarded(fails, "SYNTHETIC premise: stored share 50.0 (passes by share), the cut's 33.3 (no pass), the same run, graded on the stored run",
            lambda: st["share_pct"] == 50.0 and vd.timing_pass(st) == "share" and ct["share_pct"] == 33.3
            and vd.timing_pass(ct) is None and cut["basis"] == "et_day" and cut["run_same"] and g["kind"] == "graded")
    h = today.body_html(rec, [], "dated", evidence=ev, verdict=v)
    guarded(fails, "SYNTHETIC: the card does not say a passing event while the list prints a figure under the bar for it",
            lambda: "Checked:" not in visible(h) and "passes the timing test" not in visible(h)
            and "Most of the move the timing test measures" not in visible(h) and len(notice_texts(h)) == 1)
    guarded(fails, "SYNTHETIC: the list is the ET day's (33% of the rise since midnight ET), beside a notice, not beside a grade",
            lambda: "33% of the rise since midnight ET" in visible(section_of(h)) and "Named in the verdict above" not in h)
    # the control: an event that comes before the run passes in both windows, so the card stands and the list is the cut
    ev2, v2, rec2, g2 = probe(event_utc="2026-10-26T09:40:00Z")
    r2 = ev2["coins"]["BTC"]["tests"][0]["result"]
    cut2 = we.resolve_window(ev2, "BTC", "et_day", "up", None)["rec"]["coins"]["BTC"]["tests"][0]["result"]
    h2 = today.body_html(rec2, [], "dated", evidence=ev2, verdict=v2)
    guarded(fails, "SYNTHETIC control: an event within the hour before the run passes in both windows: the graded card stands over the cut",
            lambda: vd.timing_pass(r2) == "lead" == vd.timing_pass(cut2) and "Checked:" in visible(h2)
            and 'data-ev-window="et_day"' in section_of(h2) and not notice_texts(h2))
    guarded(fails, "the SYNTHETIC probe on the Bitcoin page: the same outcome as /today/ (the three pages cannot grade apart)",
            lambda: coin_probe(fails, ev, v, rec))
    print("   failure 4: a thing left out is said (the second sources are not read for the cut window)")
    with Draw() as d:
        for name, pg in (("/today/", d.today()), ("/coins/btc", d.coin("BTC")), ("/coins/eth", d.coin("ETH"))):
            win = visible(re.search(r'<p class="ev-win"[^>]*>.*?</p>', pg, flags=re.S).group(0))
            guarded(fails, f"{name}: the section says the second sources (OKX, Binance, Kraken) are not read for this window",
                    lambda win=win: re.search(r"second price sources, OKX, Binance and Kraken, are not read for this window", win)
                    and "agrees" not in win)
        ev = copy.deepcopy(d.ev)
        ev["coins"]["BTC"]["series"]["points"] = [p for p in ev["coins"]["BTC"]["series"]["points"] if p[0] >= 1792987200 + 3600]
        win = visible(re.search(r'<p class="ev-win"[^>]*>.*?</p>', d.today(evidence=ev), flags=re.S).group(0))
        guarded(fails, "SYNTHETIC fallback (the series does not reach midnight): the 24 hours keep the second sources' agreement",
                lambda: "agrees within 0.1 point" in win and "are not read for this window" not in win)
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
        guarded(fails, "inside the day the Ether page keeps its own plain line (the rule applies past the day only)",
                lambda: "Ether moved with Bitcoin since midnight ET." in visible(d.coin("ETH")))


def coin_probe(fails, ev, v, rec):
    """The probe on /coins/btc: the build's coin page draws no graded card over the cut either."""
    with Draw() as d:
        h = d.coin("BTC", verdict=v, evidence=ev)
        return ("Checked:" not in visible(h) and "passes the timing test" not in visible(h) and len(notice_texts(h)) == 1
                and 'data-ev-window="et_day"' in section_of(h))



def scope_tree(root):
    fails = []
    print("   the tree: no /why/ page carries the window attributes of this item")
    pages = []
    for sub in ("why",):
        for dp, _d, fs in os.walk(os.path.join(root, sub)):
            pages += [os.path.join(dp, f) for f in fs if f.endswith(".html")]
    guarded(fails, "the built tree has /why/ pages to check", lambda: bool(pages))
    guarded(fails, "no /why/ page carries data-ev-window or data-vd-basis (they are outside 9.9.1's pages)",
            lambda: all("data-ev-window" not in open(p, encoding="utf-8", errors="replace").read()
                        and "data-vd-basis" not in open(p, encoding="utf-8", errors="replace").read() for p in pages))
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


def browser(fails):
    print("6. the home's first object at 375 and 1440, from a fixture page (Playwright)")
    tmp = tempfile.mkdtemp(prefix="s991-")
    try:
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
            lambda: fb and fb[0][0] == "aside" and "vd" in fb[0][1].split() and fb[1] == ("section", "h-b h-tape"))
    n = notice_texts(h)
    guarded(fails, "when the built home carries the notice, it is one line with a reason and a time of the next read",
            lambda: len(n) <= 1 and all(NEXT_READ + ": " in x and "Next read: " in x and x.endswith(".") for x in n))
    cp = os.path.join(root, "coins", "btc.html")
    c = open(cp, encoding="utf-8").read() if os.path.exists(cp) else ""
    guarded(fails, "the built Bitcoin page carries the verdict card or the notice, as the home does (the build hands the page its clock)",
            lambda: re.search(r'<aside class="vd[^"]*" data-vd="BTC"', c) is not None)
    fails += scope_tree(root)
    guarded(fails, "no built page that carries the bare words 'Verdict at the next read' lacks a reason and a time",
            lambda: all(_every_notice_full(os.path.join(dp, f)) for dp, _d, fs in os.walk(root) for f in fs if f.endswith(".html")))
    return fails


def _every_notice_full(path):
    h = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'<p class="vd-plain vd-next"[^>]*>(.*?)</p>', h, flags=re.S):
        t = visible(m.group(1))
        if not ("Next read: " in t and (": the window flipped since the run" in t or ": no read yet today" in t)):
            return False
    return True


def unit(only=()):
    fails = []
    for name, fn in (("today", today_cases), ("notice", notice_cases), ("agree", agree_cases), ("front", front_cases),
                     ("unchanged", unchanged_cases), ("window", window_cases), ("nextread", nextread_cases),
                     ("unsourced", unsourced_cases), ("scope", scope_cases), ("review2", review2_cases)):
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
