#!/usr/bin/env python3
"""
why_evidence.py: the evidence under "What lined up with the move" (Program 9, Sprint 9.2;
AUDIT.md section 3.1, layers 1 to 3). NO MODEL CALL, and no grade: this file measures and
shows; it never says which event moved the price.

THE FOUR PARTS, each from a named source, each source that cannot be read left out and named:

  the intraday series   Bitcoin and Ether over the 24 hours ending at the Board's reading.
                        CoinGecko market_chart?days=1 (5-minute points, the last 24 hours only)
                        first; Coinbase, OKX and Kraken 5-minute candles in that order after it.
                        The first that answers is the series; the next that answers is a second
                        read, kept to show whether the venues agree.
  the candidates        the wire's clusters (site/data/wire.json: outlets counted, primary flag,
                        links, first-report time) and the fixed primary feeds: the BLS monthly
                        release schedule, BEA's release_dates.json, the Fed's FOMC calendar (the
                        stored copy), the Fed, SEC and CFTC press feeds, DefiLlama's hack list and
                        the Federal Register. Each candidate carries an EVENT time (the release
                        time, the press stamp) and a FIRST-REPORT time (the earliest wire stamp
                        that names it). A cause stated only as commentary is kept and marked
                        secondary.
  the timing test       onset = the start of the largest same-direction run in the window (the
                        peak before the deepest fall on a down day, the trough before the
                        highest rise on an up day). Per candidate: did it come before the onset,
                        within 60 minutes, or at its scheduled release time; what share of the
                        window's move came in the 60 minutes after it; did the price move first.
  the mechanics         what each market did in the onset hour: Bitcoin, Ether, S&P 500 and
                        Nasdaq 100 futures, the dollar index, the 10-year yield, gold, oil and
                        the VIX (Yahoo's 5-minute bars), OKX open interest, liquidations and
                        funding; the pattern by rule: "risk-off across assets" (or risk-on on
                        an up move), "crypto only", "leverage flush", "coin-specific".

A RECORD is site/data/why/YYYY-MM-DD-<slot>.json, written by the workflows after the daily
answer's own record (`python3 why_evidence.py --write`) and frozen like it. The build reads the
record and renders the section on /today/ and the Bitcoin and Ether pages; a missing or broken
record renders the pages exactly as before (fail open).

    python3 why_evidence.py --write                  # the run's step; exits 0 whatever happens
    python3 why_evidence.py --record END_UTC OUT [WIRE]   # record a real window's answers as a fixture
"""
import datetime as _dt
import html as _html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "site", "data", "why")
HISTORY = os.path.join(HERE, "data", "history")
FOMC = os.path.join(HERE, "data", "calendar", "fomc-{year}.json")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-4))

WINDOW_H = 24
LEAD_MIN = 60                  # an event within 60 minutes before the onset lines up in time
AFTER_MIN = 60                 # the share of the move in the 60 minutes after a candidate
SCHEDULED_TOL_MIN = 10         # "at the scheduled release time": the onset within two bars of it
MOVED_FIRST_PCT = 50           # half of the run done before the news: the price moved first
MIN_COVER = 0.8                # a series with under 80% of its window's bars is not a series
# THE TIMING TEST'S THRESHOLDS, the one source of truth (the strategist's rulings of October 19 and October 20,
# 2026; AUDIT.md section 3.1, layer 2, "The timing test"): 25 percent or more of the move done before the
# event's first report disqualifies it (twenty-five exactly disqualifies: the October 20 ruling on J-8); 40
# percent of the move inside the hour after it is the bar for "lines up". The test measures from the first-report
# time (test_time below). The verdict (verdict.py) reads these and holds no copy. Revisited by the strategist after
# two weeks of 9.8's verdict record, not before and not by the desk. MOVED_FIRST_PCT above stays 9.2's printed
# wording only. The key is still called done_max_pct; the value is the first percentage that disqualifies.
TIMING_TEST = {"version": "2026-10-20",
               "source": "AUDIT.md section 3.1; strategist's rulings of October 19, 2026 and October 20, 2026 (J-8)",
               "lead_min": LEAD_MIN, "done_max_pct": 25.0, "share_min_pct": 40.0}
SECTION_TITLE = "What lined up with the move"

COINS = {
    "BTC": {"name": "Bitcoin", "gecko": "bitcoin", "coinbase": "BTC-USD", "okx": "BTC-USDT",
            "kraken": "XBTUSD", "binance": "BTCUSDT", "gate": "BTC_USDT", "swap": "BTC-USDT-SWAP", "ccy": "BTC", "history": "bitcoin"},
    "ETH": {"name": "Ether", "gecko": "ethereum", "coinbase": "ETH-USD", "okx": "ETH-USDT",
            "kraken": "ETHUSD", "binance": "ETHUSDT", "gate": "ETH_USDT", "swap": "ETH-USDT-SWAP", "ccy": "ETH", "history": "ethereum"},
}

# Yahoo symbol, the label the page prints, and how a change is stated (percent, or basis points
# for a yield)
CROSS = [("ES=F", "S&P 500 futures", "pct"), ("NQ=F", "Nasdaq 100 futures", "pct"),
         ("DX-Y.NYB", "Dollar index", "pct"), ("^TNX", "10-year Treasury yield", "bp"),
         ("ZT=F", "2-year Treasury note futures", "pct"),
         ("GC=F", "Gold futures", "pct"), ("CL=F", "Oil futures (WTI)", "pct"),
         ("^VIX", "VIX", "pct"),
         # the only intraday read of the spot ETFs: shares traded in the hour (AUDIT.md 3.1 layer 3)
         ("IBIT", "IBIT volume (iShares Bitcoin Trust)", "shares"),
         ("FBTC", "FBTC volume (Fidelity Wise Origin Bitcoin Fund)", "shares")]

# The grade labels belong to Sprint 9.3 and "because" to a Confirmed verdict: nothing this file
# prints may carry either. The labels are the capitalized words; "confirmed a ban" in a wire line
# is a verb, not a grade.
GRADE_WORDS = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b|\b[Bb][Ee][Cc][Aa][Uu][Ss][Ee]\b")

# A cause the line attributes to commentary, not to a report of an event (AUDIT.md 3.1 layer 1).
COMMENTARY = re.compile(
    r"\b(analysts?|traders?|strategists?|observers?|commentators?|market watchers?)\b[^.]{0,80}?"
    r"\b(said|say|says|believe\w*|suggest\w*|attribut\w*|point\w* to|blam\w*|cit\w*)\b"
    r"|\baccording to (analysts|traders|strategists)\b"
    r"|\b(may have|might have|could have|possibly|appears? to have)\b", re.I)

# A primary release and the words a wire line uses for it: the earliest wire item naming the
# release, stamped after it, is its first report.
RELEASE_WORDS = [
    (re.compile(r"consumer price index", re.I), r"\b(cpi|consumer[- ]price\w*|inflation)\b"),
    (re.compile(r"producer price index", re.I), r"\b(ppi|producer[- ]price\w*)\b"),
    (re.compile(r"employment situation", re.I), r"\b(jobs report|payrolls?|nonfarm|unemployment rate)\b"),
    (re.compile(r"gross domestic product|\bgdp\b", re.I), r"\b(gdp|gross domestic product)\b"),
    (re.compile(r"personal income", re.I), r"\b(pce|personal consumption|personal income)\b"),
    (re.compile(r"retail", re.I), r"\b(retail sales)\b"),
    (re.compile(r"fomc|federal open market", re.I), r"\b(fomc|fed (holds|cuts|raises|keeps)|rate decision|powell)\b"),
]
CRYPTO_WORDS = re.compile(r"\b(crypto\w*|bitcoin|ether(eum)?|digital asset\w*|stablecoin\w*|"
                          r"blockchain|token\w*|virtual currenc\w*|coinbase|binance|tether)\b", re.I)
FED_POLICY = re.compile(r"\b(fomc|federal open market|monetary policy|discount rate|minutes|"
                        r"interest rate\w*|beige book)\b", re.I)
HACK_MIN_USD = 5_000_000


# ---- time --------------------------------------------------------------------------------

def _parse_utc(s):
    try:
        return _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(_dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _iso(t):
    return _dt.datetime.fromtimestamp(t, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _et(t):
    return _dt.datetime.fromtimestamp(t, _dt.timezone.utc).astimezone(ET)


def clock(t):
    """'8:30 AM ET' for an epoch second."""
    return _et(t).strftime("%-I:%M %p ET")


def day_clock(t, ref=None):
    """'8:30 AM ET' when on the reference's ET day, else 'Wed 8:30 AM ET'."""
    e = _et(t)
    if ref is not None and _et(ref).date() == e.date():
        return e.strftime("%-I:%M %p ET")
    return e.strftime("%a %-I:%M %p ET")


def stamp(t):
    """'Oct 18, 10:30 AM ET'."""
    return f"{_et(t):%b} {_et(t).day}, {clock(t)}"


def long_day(t):
    e = _et(t)
    return f"{e.strftime('%A, %B')} {e.day}"


# ---- the fetch layer -----------------------------------------------------------------------

class Unread(Exception):
    """A source that did not answer with what the desk needs. Its message is printed as the
    reason the source is left out."""


FETCH_TIMEOUT = 12              # seconds per request: a slow source is a skipped source, never a stalled run
RETRY_AFTER_MAX = 3             # a 429's Retry-After is honored up to 3 seconds; past that the source is skipped
ARTICLE_CAP = 3_000_000


def retry_wait(retry_after):
    """Seconds to wait before the one retry of a 429 or a 5xx: the server's Retry-After, capped at
    RETRY_AFTER_MAX, or 2 when it names none. Never the 60-second wait market_pulse uses, which
    could carry the evidence step past its workflow timeout."""
    try:
        v = float(retry_after)
    except (TypeError, ValueError):
        return 2
    return max(0, min(RETRY_AFTER_MAX, int(v)))


def _http(url, cap=None, accept="application/json", tries=2):
    """One read with the desk's per-host spacing and user agent (common), a short timeout, and one
    retry on a 429, a 5xx or a timeout after retry_wait(). Raises Unread with the reason."""
    import time
    import urllib.error
    import urllib.request
    import common
    last = None
    for i in range(tries):
        common._polite_wait(url)
        wait = 2
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": common.ua_for(url), "Accept": accept, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
                return r.read(cap) if cap else r.read()
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in common.RETRY_STATUSES:
                break
            wait = retry_wait((e.headers or {}).get("Retry-After"))
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {str(e)[:80]}"
        if i < tries - 1:
            time.sleep(wait)
    raise Unread(last or "no answer")


def live_fetch(url, kind="json"):
    """The evidence step's reads: JSON, pages and feeds, and linked reports as article text, all
    through _http (short timeout, one capped retry). CoinGecko gets one try, so a throttled read
    falls to the next venue at once."""
    import common
    if kind == "json":
        body = _http(url, tries=1 if "coingecko.com" in url else 2)
        try:
            return json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            raise Unread("the answer was not JSON") from None
    if kind == "article":
        # a wire item's linked report, as the text the desk's own extractor takes from it. Read
        # whole: CoinDesk's pages run about 1.7MB with the article past the fetch layer's 600KB
        # cap, which leaves only the subheading.
        html = _http(url, cap=ARTICLE_CAP, accept="text/html,application/xhtml+xml,*/*;q=0.8")
        return common.extract_article_text(html.decode("utf-8", "replace"), cap=6000) or ""
    body = _http(url, cap=ARTICLE_CAP, accept="text/html,application/xml,*/*;q=0.8").decode("utf-8", "replace")
    if not body:
        raise Unread("an empty answer")
    return body


# ---- the run's budget ---------------------------------------------------------------------------

DEADLINE_S = 200                # the whole build; the workflow step's own timeout is 300
STOP = {"set": False}           # set by SIGTERM (the step's timeout): spend the budget, write what is in hand


class Budget:
    """The time the evidence step may spend. Past it (or once SIGTERM has arrived) every optional
    source is skipped and named; the price series and the timing test are the core and never wait
    on it."""

    def __init__(self, seconds=DEADLINE_S, clock=None):
        import time
        self.clock = clock or time.monotonic
        self.seconds, self.t0 = seconds, self.clock()

    def spent(self):
        return STOP["set"] or self.clock() - self.t0 > self.seconds

    def why(self):
        if STOP["set"]:
            return "not read in time: the step was stopped (SIGTERM) and wrote what it had"
        return f"not read in time: the evidence step's {self.seconds}-second budget was spent"


def budgeted(fetch, budget):
    """A fetch for the optional sources: past the budget it raises Unread with the reason, so each
    source's own handler names it in 'Not read' instead of reading."""
    def f(url, kind="json"):
        if budget.spent():
            raise Unread(budget.why())
        return fetch(url, kind)
    return f


def _why(e):
    code = getattr(e, "code", None)
    if code:
        return f"HTTP {code}"
    return f"{type(e).__name__}: {str(e)[:80]}"


def _key(url, kind):
    """A fixture's key for an answer: the URL, or 'article:' and the URL for a linked report read
    as article text."""
    return ("article:" + url) if kind == "article" else url


class Recorder:
    """Wraps a fetch and keeps every answer by URL, errors included, for a fixture."""

    def __init__(self, fetch=live_fetch):
        self.fetch, self.responses = fetch, {}

    def __call__(self, url, kind="json"):
        key = _key(url, kind)
        try:
            body = self.fetch(url, kind)
        except Exception as e:                                   # noqa: BLE001
            self.responses[key] = {"__error__": str(e) or type(e).__name__}
            raise
        self.responses[key] = body
        return body


class Replay:
    """Serves a recorded fixture's answers. A URL the fixture does not hold was not read."""

    def __init__(self, responses):
        self.responses = responses

    def __call__(self, url, kind="json"):
        key = _key(url, kind)
        if key not in self.responses:
            raise Unread("not in the recorded fixture")
        body = self.responses[key]
        if isinstance(body, dict) and "__error__" in body:
            raise Unread(body["__error__"])
        return body


class Ledger:
    """Which sources were read and which were not, with the reason, in the order tried."""

    def __init__(self):
        self.read, self.unread = [], []

    def ok(self, name, url, note=""):
        self.read.append({"name": name, "url": url, "note": note})

    def miss(self, name, why, url=""):
        self.unread.append({"name": name, "why": why, "url": url})


# ---- the intraday series --------------------------------------------------------------------

def _pts_coingecko(body, bar):
    return [(int(p[0]) // 1000, float(p[1])) for p in (body or {}).get("prices") or []
            if isinstance(p, list) and len(p) >= 2 and p[1] is not None]


def _pts_coinbase(body, bar):
    # [time (bucket open), low, high, open, close, volume]; the close stands at the bucket's end
    return [(int(r[0]) + bar, float(r[4])) for r in body or [] if isinstance(r, list) and len(r) >= 5]


def _pts_okx(body, bar):
    # [ts ms (bar open), open, high, low, close, ...]
    return [(int(r[0]) // 1000 + bar, float(r[4])) for r in (body or {}).get("data") or []
            if isinstance(r, list) and len(r) >= 5]


def _pts_binance(body, bar):
    # [open time ms, open, high, low, close, volume, close time ms, ...]
    return [(int(r[0]) // 1000 + bar, float(r[4])) for r in body or [] if isinstance(r, list) and len(r) >= 5]


def _pts_kraken(body, bar):
    res = (body or {}).get("result") or {}
    rows = next((v for k, v in res.items() if k != "last" and isinstance(v, list)), [])
    return [(int(r[0]) + bar, float(r[4])) for r in rows if isinstance(r, list) and len(r) >= 5]


def price_sources(sym, start, end, now):
    """(name, url, parser, bar seconds) in the order tried. A venue whose public window cannot
    reach `start` is not asked, and says so."""
    c = COINS[sym]
    out = []
    if abs(now - end) <= 15 * 60:
        out.append(("CoinGecko 5-minute prices",
                    f"https://api.coingecko.com/api/v3/coins/{c['gecko']}/market_chart"
                    f"?vs_currency=usd&days=1", _pts_coingecko, 0,
                    None))
    else:
        out.append(("CoinGecko 5-minute prices", "", None, 0,
                    "days=1 reaches only the 24 hours before now; this window ended earlier"))
    out.append(("Coinbase 5-minute candles",
                f"https://api.exchange.coinbase.com/products/{c['coinbase']}/candles?granularity=300"
                f"&start={_iso(start)}&end={_iso(end)}", _pts_coinbase, 300, None))
    out.append(("OKX 5-minute candles",
                f"https://www.okx.com/api/v5/market/history-candles?instId={c['okx']}&bar=5m"
                f"&after={end * 1000}&limit=300", _pts_okx, 300, None))
    out.append(("Binance 5-minute klines (data-api.binance.vision)",
                f"https://data-api.binance.vision/api/v3/klines?symbol={c['binance']}&interval=5m"
                f"&startTime={(start - 300) * 1000}&endTime={end * 1000}&limit=300", _pts_binance, 300, None))
    if now - start <= 59 * 3600:
        out.append(("Kraken 5-minute candles",
                    f"https://api.kraken.com/0/public/OHLC?pair={c['kraken']}&interval=5&since={start - 300}",
                    _pts_kraken, 300, None))
    else:
        out.append(("Kraken 5-minute candles", "", None, 0,
                    "keeps its last 720 five-minute candles, which end after this window began"))
    return out


def _clip(pts, start, end):
    seen, out = set(), []
    for t, p in sorted(pts):
        if start <= t <= end and t not in seen and p > 0:
            seen.add(t)
            out.append((t, p))
    return out


def read_series(sym, start, end, now, fetch, ledger):
    """(series, others): the first venue that answers is the series, every other venue that answers
    is kept beside it to show whether the venues agree. Each {source, url, bar_min, points}."""
    got = []
    want = (end - start) / 300.0
    for name, url, parse, bar, skip in price_sources(sym, start, end, now):
        label = f"{COINS[sym]['name']} prices: {name}"
        if skip:
            ledger.miss(label, skip)
            continue
        try:
            pts = _clip(parse(fetch(url, "json"), bar), start, end)
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(label, str(e) or type(e).__name__, url)
            continue
        if len(pts) < MIN_COVER * want:
            ledger.miss(label, f"{len(pts)} points for a window of {int(want)} five-minute bars", url)
            continue
        ledger.ok(label, url)
        got.append({"source": name, "url": url, "bar_min": 5,
                    "points": [[t, round(p, 6)] for t, p in pts]})
    return (got[0] if got else None), got[1:]


# ---- the timing test -------------------------------------------------------------------------

def _pct(a, b):
    return (b / a - 1.0) * 100.0 if a else None


def price_at(points, t):
    """The last price at or before t; None before the first point."""
    best = None
    for pt, p in points:
        if pt <= t:
            best = p
        else:
            break
    return best


def onset(points):
    """The largest same-direction run in the window, in the window's own direction: on a down
    window the highest point before the deepest fall below it, on an up window the lowest point
    before the highest rise above it. {dir, start_t, start_p, end_t, end_p, pct}; None under
    two points. The run's start is the onset."""
    if len(points) < 2:
        return None
    first, last = points[0][1], points[-1][1]
    down = last < first

    best = None
    ext_t, ext_p = points[0]
    for t, p in points[1:]:
        # a tie moves the extreme later: on a flat stretch the run starts where the move does
        if (down and p >= ext_p) or (not down and p <= ext_p):
            ext_t, ext_p = t, p
            continue
        size = (ext_p - p) if down else (p - ext_p)
        if size > 0 and (best is None or size > best[0]):
            best = (size, ext_t, ext_p, t, p)
    if best is None:
        return None
    _s, st, sp, et_, ep = best
    return {"dir": "down" if down else "up", "start_t": st, "start_p": sp, "end_t": et_,
            "end_p": ep, "pct": round(_pct(sp, ep), 3)}


def timing(points, run, t, scheduled=False):
    """The three questions of AUDIT.md 3.1 for one candidate at epoch `t`:
      lead_min      minutes from the candidate to the onset (positive: it came first)
      before_onset  it came within 60 minutes before the onset, or the onset fell at its
                    scheduled release time (within two five-minute bars either side)
      share_pct     the share of the window's move made in the 60 minutes after it (negative:
                    those 60 minutes ran against the move); None when it falls outside
      done_pct      how much of the run was already done when it came
      moved_first   the price made half or more of the run before it
    """
    if not points or not run:
        return None
    w0, w1 = points[0][0], points[-1][0]
    move = points[-1][1] - points[0][1]
    lead = (run["start_t"] - t) / 60.0
    before = (0 <= lead <= LEAD_MIN) or (scheduled and abs(lead) <= SCHEDULED_TOL_MIN)
    share = after = None
    partial = False
    if w0 <= t <= w1 and move:
        p0 = price_at(points, t)
        t1 = min(t + AFTER_MIN * 60, w1)
        partial = t1 < t + AFTER_MIN * 60
        p1 = price_at(points, t1)
        if p0 is not None and p1 is not None:
            share = round((p1 - p0) / move * 100.0, 1)
            after = round(_pct(p0, p1), 2)
    span = run["end_p"] - run["start_p"]
    if t <= run["start_t"] or not span:
        done = 0.0
    elif t >= run["end_t"]:
        done = 100.0
    else:
        pt = price_at(points, t)
        done = max(0.0, min(100.0, (pt - run["start_p"]) / span * 100.0)) if pt is not None else 0.0
    return {"lead_min": round(lead, 1), "before_onset": bool(before),
            "after_pct": after, "share_pct": share, "share_partial": partial, "in_window": w0 <= t <= w1,
            "done_pct": round(done, 1), "moved_first": done >= MOVED_FIRST_PCT}


# ---- the candidates ----------------------------------------------------------------------------

def _wire_candidates(wire, start, end):
    out = []
    for w in (wire or {}).get("items") or []:
        t = _parse_utc(w.get("reported_utc"))
        line = " ".join(str(w.get("line") or "").split())
        if t is None or not line:
            continue
        ts = int(t.timestamp())
        if not (start - LEAD_MIN * 60 <= ts <= end):
            continue
        links = [{"outlet": l.get("outlet") or "Source", "url": l.get("url")}
                 for l in (w.get("links") or []) if l.get("url")]
        sec = bool(COMMENTARY.search(line))
        out.append({"id": "wire-" + str(w.get("id") or len(out)), "kind": "wire", "line": line,
                    "titles": [t for t in w.get("titles") or [] if t],
                    "event_utc": None, "event_basis": None, "scheduled": False,
                    "report_utc": _iso(ts), "source_count": int(w.get("source_count") or len(links)),
                    "primary": bool(w.get("primary")), "links": links[:4],
                    "secondary": sec,
                    "secondary_why": "the cause it gives is commentary, not a reported event" if sec else "",
                    "wire_id": w.get("id")})
    return out


def _bls(start, end, fetch, ledger):
    """BLS releases from its monthly schedule pages: name, reference period, ET release time."""
    out = []
    months = sorted({(_et(t).year, _et(t).month) for t in (start, end)})
    for y, m in months:
        url = f"https://www.bls.gov/schedule/{y}/{m:02d}_sched.htm"
        try:
            page = fetch(url, "text")
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(f"BLS release schedule, {y}-{m:02d}", str(e), url)
            continue
        ledger.ok(f"BLS release schedule, {y}-{m:02d}", url)
        for cell in re.finditer(r'<td[^>]*id="d(\d\d)(\d\d)"[^>]*>(.*?)</td>', page, re.S):
            mm, dd, body = int(cell.group(1)), int(cell.group(2)), cell.group(3)
            yy = y - 1 if (m == 1 and mm == 12) else (y + 1 if (m == 12 and mm == 1) else y)
            for rel in re.finditer(r"<strong>(.*?)<br\s*/?>\s*</strong>(.*?)<br\s*/?>\s*(\d{1,2}):(\d\d)\s*([AP]M)",
                                   body, re.S):
                name = _html.unescape(re.sub(r"<[^>]+>", "", rel.group(1))).strip()
                ref = _html.unescape(re.sub(r"<[^>]+>", "", rel.group(2))).strip()
                hh, mi = int(rel.group(3)) % 12 + (12 if rel.group(5) == "PM" else 0), int(rel.group(4))
                try:
                    t = int(_dt.datetime(yy, mm, dd, hh, mi, tzinfo=ET).timestamp())
                except ValueError:
                    continue
                if start - LEAD_MIN * 60 <= t <= end:
                    out.append({"id": f"bls-{yy}{mm:02d}{dd:02d}-{re.sub(r'[^a-z]+', '-', name.lower()).strip('-')}",
                                "kind": "release", "line": f"{name}, {ref} (Bureau of Labor Statistics)",
                                "release_name": name, "event_utc": _iso(t), "event_basis": "BLS release schedule",
                                "scheduled": True, "report_utc": None, "source_count": 0, "primary": True,
                                "links": [{"outlet": "BLS", "url": url}], "secondary": False,
                                "secondary_why": ""})
    return out


def _bea(start, end, fetch, ledger):
    url = "https://apps.bea.gov/API/signup/release_dates.json"
    try:
        body = fetch(url, "json")
    except Exception as e:                                       # noqa: BLE001
        ledger.miss("BEA release dates", str(e), url)
        return []
    ledger.ok("BEA release dates", url)
    out = []
    for name, v in (body or {}).items():
        if not isinstance(v, dict):
            continue
        for s in v.get("release_dates") or []:
            t = _parse_utc(s)
            if t is None:
                continue
            ts = int(t.timestamp())
            if start - LEAD_MIN * 60 <= ts <= end:
                cid = f"bea-{_et(ts):%Y%m%d}-{re.sub(r'[^a-z]+', '-', name.lower()).strip('-')}"
                if any(c["id"] == cid for c in out):
                    continue
                out.append({"id": cid, "kind": "release", "line": f"{name} (Bureau of Economic Analysis)",
                            "release_name": name, "event_utc": _iso(ts), "event_basis": "BEA release dates",
                            "scheduled": True, "report_utc": None, "source_count": 0, "primary": True,
                            "links": [{"outlet": "BEA", "url": "https://www.bea.gov/news/schedule"}],
                            "secondary": False, "secondary_why": ""})
    return out


def _fomc(start, end, ledger, path=FOMC):
    """The stored copy of the Fed's meeting calendar gives dates, not times: a meeting that ends
    in the window is a candidate with no event time, and the timing test says it cannot run."""
    out = []
    years = sorted({_et(start).year, _et(end).year})
    for y in years:
        p = path.format(year=y)
        try:
            d = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError) as e:
            ledger.miss(f"FOMC calendar {y} (stored)", type(e).__name__)
            continue
        ledger.ok(f"FOMC calendar {y} (stored copy of the Fed's page, read {d.get('read_date')})",
                  d.get("source_url") or "")
        for m in d.get("meetings") or []:
            day = str(m.get("end") or "")
            if _et(start).date().isoformat() <= day <= _et(end).date().isoformat():
                out.append({"id": f"fomc-{day}", "kind": "release",
                            "line": f"FOMC meeting concludes, {m.get('as_printed') or day} (Federal Reserve)",
                            "release_name": "FOMC", "event_utc": None,
                            "event_basis": "the Fed's calendar gives the date, not the time",
                            "event_day": day, "scheduled": True, "report_utc": None, "source_count": 0,
                            "primary": True, "links": [{"outlet": "Federal Reserve", "url": d.get("source_url")}],
                            "secondary": False, "secondary_why": ""})
    return out


def _rss(name, url, start, end, fetch, ledger, keep, outlet):
    try:
        body = fetch(url, "text")
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(name, str(e), url)
        return []
    import email.utils as _eu
    out, oldest = [], None
    for item in re.findall(r"<item\b.*?</item>", body, re.S):
        title = re.search(r"<title>(.*?)</title>", item, re.S)
        link = re.search(r"<link>(.*?)</link>", item, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        if not (title and pub):
            continue
        clean = lambda s: _html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", s)).strip()
        try:
            ts = int(_eu.parsedate_to_datetime(clean(pub.group(1))).timestamp())
        except (TypeError, ValueError):
            continue
        oldest = ts if oldest is None else min(oldest, ts)
        t_txt = " ".join(clean(title.group(1)).split())
        if not (start - LEAD_MIN * 60 <= ts <= end) or not keep.search(t_txt):
            continue
        out.append({"id": f"{outlet.lower()}-{ts}", "kind": "press", "line": f"{t_txt} ({outlet})",
                    "event_utc": _iso(ts), "event_basis": f"{outlet}'s own feed stamp",
                    "scheduled": False, "report_utc": None, "source_count": 0, "primary": True,
                    "links": [{"outlet": outlet, "url": clean(link.group(1)) if link else url}],
                    "secondary": False, "secondary_why": ""})
    note = ""
    if oldest is not None and oldest > start:
        note = f"the feed reaches back only to {stamp(oldest)}"
    ledger.ok(name, url, note)
    return out


def _hacks(start, end, fetch, ledger):
    url = "https://api.llama.fi/hacks"
    try:
        body = fetch(url, "json")
    except Exception as e:                                       # noqa: BLE001
        ledger.miss("DefiLlama hacks", str(e), url)
        return []
    ledger.ok("DefiLlama hacks", url)
    out = []
    d0, d1 = _dt.datetime.fromtimestamp(start, _dt.timezone.utc).date(), _dt.datetime.fromtimestamp(end, _dt.timezone.utc).date()
    for h in body or []:
        try:
            day = _dt.datetime.fromtimestamp(int(h.get("date")), _dt.timezone.utc).date()
            amt = float(h.get("amount") or 0)
        except (TypeError, ValueError):
            continue
        if d0 <= day <= d1 and amt >= HACK_MIN_USD:
            out.append({"id": f"hack-{day.isoformat()}-{re.sub(r'[^a-z0-9]+', '-', str(h.get('name')).lower())}",
                        "kind": "hack", "line": f"{h.get('name')} exploit, {h.get('technique') or 'technique not given'} (DefiLlama)",
                        "amount_usd": amt, "event_utc": None,
                        "event_basis": "DefiLlama gives the day, not the time", "event_day": day.isoformat(),
                        "scheduled": False, "report_utc": None, "source_count": 0, "primary": False,
                        "links": [{"outlet": "DefiLlama", "url": "https://defillama.com/hacks"}],
                        "secondary": False, "secondary_why": ""})
    return out


def _fedreg(start, end, fetch, ledger):
    d0, d1 = _et(start).date().isoformat(), _et(end).date().isoformat()
    url = ("https://www.federalregister.gov/api/v1/documents.json?per_page=20"
           "&conditions%5Bterm%5D=crypto+OR+bitcoin+OR+%22digital+asset%22"
           f"&conditions%5Bpublication_date%5D%5Bgte%5D={d0}&conditions%5Bpublication_date%5D%5Blte%5D={d1}")
    try:
        body = fetch(url, "json")
    except Exception as e:                                       # noqa: BLE001
        ledger.miss("Federal Register", str(e), url)
        return []
    ledger.ok("Federal Register", url)
    out = []
    for r in (body or {}).get("results") or []:
        out.append({"id": f"fr-{r.get('document_number')}", "kind": "press",
                    "line": f"{' '.join(str(r.get('title') or '').split())} (Federal Register)",
                    "event_utc": None, "event_basis": "the Register gives the publication day, not a time",
                    "event_day": r.get("publication_date"), "scheduled": False, "report_utc": None,
                    "source_count": 0, "primary": True,
                    "links": [{"outlet": "Federal Register", "url": r.get("html_url")}],
                    "secondary": False, "secondary_why": ""})
    return out


FOREXFACTORY = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def _forexfactory(start, end, fetch, ledger, held):
    """US releases of medium and high impact from ForexFactory's calendar, which publishes the
    current week only. A release BLS or BEA already gives at the same time is not listed twice."""
    try:
        rows = fetch(FOREXFACTORY, "json") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss("ForexFactory calendar", str(e), FOREXFACTORY)
        return []
    stamps = [t for t in (_parse_utc(r.get("date")) for r in rows if isinstance(r, dict)) if t]
    if not stamps:
        ledger.miss("ForexFactory calendar", "its answer held no dated event", FOREXFACTORY)
        return []
    first = int(min(stamps).timestamp())
    if first > start:
        ledger.miss("ForexFactory calendar", f"it keeps only the current week, from {stamp(first)}, "
                    "which does not reach back to this window", FOREXFACTORY)
        return []
    ledger.ok("ForexFactory calendar", FOREXFACTORY)
    out = []
    for r in rows:
        t = _parse_utc(r.get("date"))
        if t is None or r.get("country") != "USD" or r.get("impact") not in ("High", "Medium"):
            continue
        ts = int(t.timestamp())
        if not (start - LEAD_MIN * 60 <= ts <= end):
            continue
        title = " ".join(str(r.get("title") or "").split())
        fam = next((w for _pat, w in RELEASE_WORDS if re.search(w, title, re.I)), None)
        if fam and any(abs(int(_parse_utc(h["event_utc"]).timestamp()) - ts) <= 300
                       and re.search(fam, h["line"], re.I) for h in held if h.get("event_utc")):
            continue
        cid = f"ff-{ts}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}"
        if any(c["id"] == cid for c in out):
            continue
        out.append({"id": cid, "kind": "release", "line": f"{title} (US, ForexFactory calendar)",
                    "release_name": title, "event_utc": _iso(ts), "event_basis": "ForexFactory calendar",
                    "scheduled": True, "report_utc": None, "source_count": 0, "primary": False,
                    "links": [{"outlet": "ForexFactory", "url": "https://www.forexfactory.com/calendar"}],
                    "secondary": False, "secondary_why": ""})
    return out


def _source_check(wires, fetch, ledger, links_per_item=2):
    """9.1's per-line source check (wire.source_check) on each wire candidate, against its titles
    and the text of its linked reports read now. A clause its sources do not carry is cut; a line
    with no subject left is dropped. (kept, cuts)."""
    import wire as _wire
    kept, cuts, read, missed = [], [], 0, []
    for w in wires:
        texts = list(w.get("titles") or [])
        for l in (w.get("links") or [])[:links_per_item]:
            try:
                texts.append(fetch(l["url"], "article"))
                read += 1
            except Exception as e:                               # noqa: BLE001
                missed.append(f"{l.get('outlet') or 'a report'} ({str(e) or type(e).__name__})")
        line, cut = _wire.source_check(w["line"], texts)
        for x in cut:
            cuts.append({"wire_id": w.get("wire_id"), "line": w["line"], **x})
        if not line:
            continue
        kept.append(dict(w, line=line) if line != w["line"] else w)
    if wires:
        ledger.ok("Wire sources (the linked reports, for 9.1's source check)", "",
                  f"{read} report(s) read")
    if missed:
        ledger.miss("Wire sources, some linked reports", "not read: " + "; ".join(missed[:6])
                    + (" and more" if len(missed) > 6 else ""))
    return kept, cuts


def candidates(start, end, wire, fetch, ledger, fomc_path=FOMC, cuts=None):
    """Every candidate in the window and the 60 minutes before it, primary releases first. A wire
    item that names a release and was stamped after it is that release's first report: it is
    folded into the release (printed once) and gives it its first-report time."""
    prim = (_bls(start, end, fetch, ledger) + _bea(start, end, fetch, ledger)
            + _fomc(start, end, ledger, fomc_path)
            + _rss("Federal Reserve press releases", "https://www.federalreserve.gov/feeds/press_all.xml",
                   start, end, fetch, ledger, FED_POLICY, "Federal Reserve")
            + _rss("SEC press releases", "https://www.sec.gov/news/pressreleases.rss",
                   start, end, fetch, ledger, CRYPTO_WORDS, "SEC")
            + _rss("CFTC press releases", "https://www.cftc.gov/RSS/RSSGP/rssgp.xml",
                   start, end, fetch, ledger, CRYPTO_WORDS, "CFTC")
            + _hacks(start, end, fetch, ledger) + _fedreg(start, end, fetch, ledger))
    prim += _forexfactory(start, end, fetch, ledger, prim)
    ledger.miss("Nasdaq economic calendar",
                "left out: read 18 October, its dates come back a day late (its answer for October 15 "
                "lists CPI, which BLS schedules for October 14, and its October 16 answer lists PPI, "
                "scheduled for October 15) and its time column is headed GMT while reading as Eastern, "
                "so no event can be stamped from it without guessing")
    wires = _wire_candidates(wire, start, end)
    ledger.ok("The wire (site/data/wire.json)", "/data/wire.json" if wire else "",
              f"{len(wires)} item(s) in the window")
    wires, cut = _source_check(wires, fetch, ledger)
    if cuts is not None:
        cuts.extend(cut)
    folded = set()
    for c in prim:
        words = next((w for pat, w in RELEASE_WORDS if pat.search(c.get("release_name") or c["line"])), None)
        ev = _parse_utc(c.get("event_utc"))
        if not words or ev is None:
            continue
        hits = [w for w in wires if w["id"] not in folded and re.search(words, w["line"], re.I)
                and _parse_utc(w["report_utc"]) >= ev]
        if hits:
            first = min(hits, key=lambda w: w["report_utc"])
            folded.add(first["id"])
            c.update(report_utc=first["report_utc"], report_line=first["line"],
                     report_links=first["links"], source_count=first["source_count"],
                     report_wire_id=first.get("wire_id"))
    rest = [w for w in wires if w["id"] not in folded]
    return prim + rest


def test_time(c):
    """(epoch, basis) the timing test uses: the first-report time, which is the moment the market could have
    reacted (the strategist's ruling of October 20, 2026, J-8). A scheduled release is measured from its release
    time, where the event and its report coincide. An event reported after it happened (a hack, a filing found
    later) is measured from its report: the move before it is not the event's. An event with only an event
    time keeps it (a source's own stamp is its first report); (None, why) when neither time exists."""
    ev = _parse_utc(c.get("event_utc"))
    rp = _parse_utc(c.get("report_utc"))
    if ev is not None and (c.get("scheduled") or rp is None):
        return int(ev.timestamp()), "event"
    if rp is not None:
        return int(rp.timestamp()), "first report"
    return None, c.get("event_basis") or "no time"


# ---- the mechanics -------------------------------------------------------------------------------

def _yahoo_url(sym, start, end):
    return (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym, safe='=')}"
            f"?interval=5m&period1={start}&period2={end}")


def _yahoo_pts(body):
    r = (((body or {}).get("chart") or {}).get("result") or [None])[0] or {}
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    # Yahoo stamps a 5-minute bar at its open; its close stands at the bar's end
    return [(int(t) + 300, float(c)) for t, c in zip(ts, closes) if c is not None]


def _yahoo_vol(body):
    r = (((body or {}).get("chart") or {}).get("result") or [None])[0] or {}
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    return [(int(t) + 300, int(v)) for t, v in zip(r.get("timestamp") or [], q.get("volume") or []) if v is not None]


def cross_assets(start, end, fetch, ledger):
    out = {}
    for sym, label, unit in CROSS:
        url = _yahoo_url(sym, start, end)
        try:
            body = fetch(url, "json")
            pts = _clip(_yahoo_pts(body), start, end)
            vol = [[t, v] for t, v in _yahoo_vol(body) if start <= t <= end]
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(f"Yahoo 5-minute bars, {label}", str(e), url)
            continue
        ledger.ok(f"Yahoo 5-minute bars, {label}", url)
        out[sym] = {"label": label, "unit": unit, "points": [[t, round(p, 4)] for t, p in pts]}
        if unit == "shares":
            out[sym]["volume"] = vol
    return out


def _okx_oi(sym, start, end, now, fetch, ledger):
    c = COINS[sym]
    period = "5m" if now - start <= 47 * 3600 else "1H"
    url = f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy={c['ccy']}&period={period}"
    try:
        rows = (fetch(url, "json") or {}).get("data") or []
        pts = _clip([(int(r[0]) // 1000, float(r[1])) for r in rows], start - 3600, end + 3600)
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(f"OKX open interest, {c['name']}", str(e), url)
        return None
    if not pts:
        ledger.miss(f"OKX open interest, {c['name']}", "no readings in this window", url)
        return None
    ledger.ok(f"OKX open interest, {c['name']} ({'5-minute' if period == '5m' else 'hourly'})", url)
    return {"period": period, "points": [[t, round(p)] for t, p in pts]}


def _okx_liq(sym, fetch, ledger, ct_val):
    c = COINS[sym]
    url = (f"https://www.okx.com/api/v5/public/liquidation-orders?instType=SWAP&state=filled"
           f"&uly={c['okx']}&limit=100")
    try:
        rows = (fetch(url, "json") or {}).get("data") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(f"OKX liquidations, {c['name']}", str(e), url)
        return None
    det = [d for r in rows for d in (r.get("details") or [])]
    cv = ct_val.get(c["swap"])
    if not det or not cv:
        ledger.miss(f"OKX liquidations, {c['name']}", "no orders or no contract size", url)
        return None
    ledger.ok(f"OKX liquidations, {c['name']}", url)
    return {"orders": [[int(d.get("ts") or 0) // 1000, d.get("posSide"),
                        round(float(d.get("sz") or 0) * cv * float(d.get("bkPx") or 0))] for d in det]}


def _okx_taker(sym, t0, fetch, ledger):
    """OKX taker buy and sell volume on the coin's USDT perpetual for the hour holding the onset,
    in USDT (rubik taker-volume-contract, unit 2; OKX's order is [ts, sellVol, buyVol])."""
    c = COINS[sym]
    h0 = t0 - t0 % 3600
    url = (f"https://www.okx.com/api/v5/rubik/stat/taker-volume-contract?instId={c['swap']}&period=1H"
           f"&unit=2&begin={(h0 - 3600) * 1000}&end={(h0 + 3600) * 1000}")
    try:
        rows = (fetch(url, "json") or {}).get("data") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(f"OKX taker flow, {c['name']}", str(e), url)
        return None
    row = next((r for r in rows if int(r[0]) // 1000 == h0), None)
    if not row:
        ledger.miss(f"OKX taker flow, {c['name']}", f"no reading for the hour from {stamp(h0)}", url)
        return None
    ledger.ok(f"OKX taker flow, {c['name']} (hourly)", url)
    return {"key": "taker", "label": f"Taker flow, OKX {c['swap']} (the hour from {clock(h0)}, in USDT)",
            "hour_utc": _iso(h0), "sell_usd": round(float(row[1])), "buy_usd": round(float(row[2]))}


def _gate_liq(sym, t0, fetch, ledger):
    """Gate's USDT-perpetual liquidations in the onset hour (its API serves any one-hour range).
    A positive size is a long position closed; the notional is size times the contract's quanto
    multiplier times the fill price."""
    c = COINS[sym]
    name = f"Gate liquidations, {c['name']}"
    curl = f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{c['gate']}"
    url = (f"https://api.gateio.ws/api/v4/futures/usdt/liq_orders?contract={c['gate']}"
           f"&from={t0}&to={t0 + 3600}&limit=1000")
    try:
        q = float((fetch(curl, "json") or {}).get("quanto_multiplier") or 0)
        rows = fetch(url, "json") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(name, str(e), url)
        return None
    if not q or not isinstance(rows, list):
        ledger.miss(name, "no contract multiplier or no list in its answer", url)
        return None
    ledger.ok(name, url, "1,000 orders, the most one answer holds" if len(rows) >= 1000 else "")
    usd = lambda o: abs(float(o["size"])) * q * float(o["fill_price"])
    return {"key": "liq-gate", "label": "Liquidations, Gate",
            "longs_usd": round(sum(usd(o) for o in rows if float(o["size"]) > 0)),
            "shorts_usd": round(sum(usd(o) for o in rows if float(o["size"]) < 0)),
            "orders": len(rows), "capped": len(rows) >= 1000}


KALSHI = "https://api.elections.kalshi.com/trade-api/v2"


def _lower1(t):
    return t[:1].lower() + t[1:]


KALSHI_MAX_STRIKES = 4          # strikes read per record: the four nearest the money when read


def _kalshi(onsets, end, fetch, ledger):
    """Kalshi's Fed markets (series KXFED) for the next meeting after the window, read ONCE per
    record for every coin's onset: 2 calls, then one hourly-candle call for each of the
    KALSHI_MAX_STRIKES strikes nearest the money (by their last price when read), covering all the
    onsets. For each onset, each strike priced between 5% and 95% gives its yes price (the bid-ask
    mid of its hourly candles) at the last close at or before the onset and the last close at or
    before an hour later; the row names both closes. {onset: [rows]}; {} with the reason in the
    ledger."""
    name = "Kalshi Fed markets (KXFED)"
    if not onsets:
        return {}
    try:
        evs = (fetch(f"{KALSHI}/events?series_ticker=KXFED&limit=200", "json") or {}).get("events") or []
        nxt = min((e for e in evs if (_parse_utc(e.get("strike_date")) or _dt.datetime.min.replace(
            tzinfo=_dt.timezone.utc)).timestamp() > end), key=lambda e: e["strike_date"], default=None)
        if not nxt:
            ledger.miss(name, "no meeting after this window in its answer")
            return {}
        mk = (fetch(f"{KALSHI}/markets?event_ticker={nxt['event_ticker']}&limit=100", "json") or {}).get("markets") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(name, str(e), f"{KALSHI}/events?series_ticker=KXFED")
        return {}

    def last_price(m):
        try:
            return float(m.get("last_price_dollars"))
        except (TypeError, ValueError):
            try:
                return float(m.get("last_price")) / 100.0
            except (TypeError, ValueError):
                return 0.0
    near = sorted(mk, key=lambda m: abs(last_price(m) - 0.5))[:KALSHI_MAX_STRIKES]

    def close_at(cands, t):
        c = [x for x in cands if int(x.get("end_period_ts") or 0) <= t]
        if not c:
            return None, None
        last = max(c, key=lambda x: int(x["end_period_ts"]))
        try:
            mid = round((float(last["yes_bid"]["close_dollars"]) + float(last["yes_ask"]["close_dollars"])) * 50, 1)
        except (KeyError, TypeError, ValueError):
            return None, None
        return int(last["end_period_ts"]), mid
    lo, hi = min(onsets) - 7200, max(onsets) + 7200
    meet = _parse_utc(nxt["strike_date"])
    when = f"{meet.astimezone(ET):%B} {meet.astimezone(ET).day}" if meet else nxt["event_ticker"]
    out, missed = {t0: [] for t0 in onsets}, []
    for m in sorted(near, key=lambda m: float(m.get("floor_strike") or 0)):
        url = (f"{KALSHI}/series/KXFED/markets/{m['ticker']}/candlesticks?start_ts={lo}"
               f"&end_ts={hi}&period_interval=60")
        try:
            cs = (fetch(url, "json") or {}).get("candlesticks") or []
        except Exception as e:                                   # noqa: BLE001
            missed.append(str(e) or type(e).__name__)
            continue
        for t0 in onsets:
            (ta, a), (tb, b) = close_at(cs, t0), close_at(cs, t0 + 3600)
            if a is None or b is None or not (5 <= a <= 95):
                continue
            out[t0].append({"key": f"kalshi-{m['ticker']}", "unit": "chance",
                            "label": f"Kalshi: Fed rate {_lower1(m.get('yes_sub_title') or m['ticker'])} after the "
                                     f"{when} meeting, yes price (bid-ask mid of hourly candles), "
                                     f"{clock(ta)} close to {clock(tb)} close",
                            "from_utc": _iso(ta), "to_utc": _iso(tb),
                            "from_pct": float(a), "to_pct": float(b)})
    if missed and len(missed) == len(near):
        ledger.miss(name, "its candles did not answer: " + missed[0], f"{KALSHI}/series/KXFED")
        return out
    ledger.ok(name, f"{KALSHI}/events?series_ticker=KXFED",
              (f"the {len(near)} strikes nearest the money read"
               + ("" if any(out.values()) else "; none was priced between 5% and 95% at the onset")
               + (f"; {len(missed)} strike(s) did not answer ({missed[0]})" if missed else "")))
    return out


def _okx_funding(sym, fetch, ledger):
    c = COINS[sym]
    url = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={c['swap']}&limit=100"
    try:
        rows = (fetch(url, "json") or {}).get("data") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(f"OKX funding, {c['name']}", str(e), url)
        return None
    ledger.ok(f"OKX funding, {c['name']}", url)
    return [[int(r["fundingTime"]) // 1000, round(float(r.get("realizedRate") or r.get("fundingRate")) * 100, 4)]
            for r in rows if r.get("fundingTime")]


def _ct_val(fetch, ledger, coins=("BTC", "ETH")):
    """Each swap's contract size, for liquidation notionals (sz is in contracts, not coins)."""
    out = {}
    for sym in coins:
        inst = COINS[sym]["swap"]
        url = f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={inst}"
        try:
            rows = (fetch(url, "json") or {}).get("data") or []
        except Exception as e:                                       # noqa: BLE001
            ledger.miss(f"OKX contract size, {inst}", str(e), url)
            continue
        out.update({r["instId"]: float(r.get("ctVal") or 0) for r in rows if r.get("instId") == inst})
    return out


def _stables(start, end, fetch, ledger):
    url = "https://stablecoins.llama.fi/stablecoincharts/all"
    try:
        rows = fetch(url, "json") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss("DefiLlama stablecoin supply", str(e), url)
        return None
    pts = []
    for r in rows:
        try:
            pts.append((int(r["date"]), float((r.get("totalCirculatingUSD") or {}).get("peggedUSD"))))
        except (KeyError, TypeError, ValueError):
            continue
    pts.sort()
    d_end = price_at(pts, end)
    d_start = price_at(pts, end - 86400)
    if d_end is None or d_start is None:
        ledger.miss("DefiLlama stablecoin supply", "no daily reading for this window", url)
        return None
    ledger.ok("DefiLlama stablecoin supply (daily)", url)
    return {"window": "daily", "change_usd": round(d_end - d_start), "total_usd": round(d_end)}


def _beta(sym, before_day, days=30, root=HISTORY):
    """The coin's 30-day beta to Bitcoin from the stored daily closes before `before_day`."""
    try:
        a = json.load(open(os.path.join(root, COINS[sym]["history"] + ".json"), encoding="utf-8"))["closes"]
        b = json.load(open(os.path.join(root, "bitcoin.json"), encoding="utf-8"))["closes"]
    except (OSError, ValueError, KeyError):
        return None
    days_ = sorted(d for d in a if d in b and d < before_day)[-(days + 1):]
    if len(days_) < days // 2:
        return None
    ra = [a[days_[i]] / a[days_[i - 1]] - 1 for i in range(1, len(days_))]
    rb = [b[days_[i]] / b[days_[i - 1]] - 1 for i in range(1, len(days_))]
    mb = sum(rb) / len(rb)
    ma = sum(ra) / len(ra)
    var = sum((x - mb) ** 2 for x in rb)
    if not var:
        return None
    return round(sum((x - mb) * (y - ma) for x, y in zip(rb, ra)) / var, 3)


def hour_change(points, t0, t1):
    a, b = price_at(points, t0), price_at(points, t1)
    if a is None or b is None:
        return None
    # a series with no bar inside the hour (a market shut) has no change for it
    if not any(t0 < t <= t1 for t, _p in points):
        return None
    return a, b


# Thresholds of the pattern rules. The audit names "open interest down 5% or more with
# liquidations mostly on one side"; the rest are this file's first setting, printed in the run
# log as the move happens so they can be moved on evidence.
CRYPTO_HOUR_MIN = 0.3          # crypto moved at least 0.3% in the onset hour
STOCKS_WITH_MIN = 0.2          # stock futures moved at least 0.2% the same way: across assets
STOCKS_QUIET_MAX = 0.1         # stock futures within 0.1% (or shut): crypto only
OI_FLUSH_PCT = -5.0
LIQ_ONE_SIDE = 0.7
EXCESS_MIN = 1.0               # coin-specific: 1 point or more beyond its Bitcoin beta, and over half its move


def mechanics(sym, run, series, others, cross, oi, liq, funding, beta, extra=None):
    """What each market did in the onset hour, and the pattern by the rules above."""
    if not run:
        return None
    t0, t1 = run["start_t"], run["start_t"] + 3600
    rows = []

    def add(key, label, pts, unit="pct"):
        hc = hour_change(pts, t0, t1)
        if hc is None:
            rows.append({"key": key, "label": label, "value": None, "unit": unit})
            return None
        a, b = hc
        v = round((b - a) * 100, 1) if unit == "bp" else round(_pct(a, b), 2)
        rows.append({"key": key, "label": label, "value": v, "unit": unit})
        return v

    own = add(sym, COINS[sym]["name"], series)
    btc = own if sym == "BTC" else add("BTC", "Bitcoin", (others.get("BTC") or {}).get("points") or [])
    if sym == "BTC" and others.get("ETH"):
        add("ETH", "Ether", others["ETH"]["points"])
    for ysym, label, unit in CROSS:
        if ysym not in cross:
            continue
        if unit == "shares":
            bars = [v for t, v in cross[ysym].get("volume") or [] if t0 < t <= t1]
            rows.append({"key": ysym, "label": label, "value": sum(bars) if bars else None, "unit": "shares"})
        else:
            add(ysym, label, cross[ysym]["points"], unit)
    oi_v = None
    if oi:
        p = oi["points"]
        if oi["period"] == "1H":
            h0 = t0 - t0 % 3600
            hc = hour_change(p, h0, h0 + 3600)
            label = f"Open interest, OKX (the hour from {clock(h0)})"
        else:
            hc = hour_change(p, t0, t1)
            label = "Open interest, OKX"
        oi_v = round(_pct(*hc), 2) if hc else None
        rows.append({"key": "oi", "label": label, "value": oi_v, "unit": "pct"})
    liq_row = None
    if liq and liq.get("orders"):
        oldest = min(o[0] for o in liq["orders"])
        if oldest <= t0:
            inside = [o for o in liq["orders"] if t0 <= o[0] <= t1]
            longs = sum(o[2] for o in inside if o[1] == "long")
            shorts = sum(o[2] for o in inside if o[1] == "short")
            liq_row = {"key": "liq", "label": "Liquidations, OKX", "longs_usd": longs, "shorts_usd": shorts}
            rows.append(liq_row)
        else:
            liq_row = {"key": "liq", "label": "Liquidations, OKX", "unread": True,
                       "why": f"OKX keeps its latest 100 orders, back to {stamp(oldest)}"}
            rows.append(liq_row)
    extra = extra or {}
    if extra.get("taker"):
        rows.append(extra["taker"])
    gate = extra.get("gate")
    if gate:
        rows.append(gate)
    rows.extend(extra.get("kalshi") or [])
    fund = None
    if funding:
        due = [f for f in funding if f[0] >= t0]
        if due:
            f = min(due, key=lambda r: r[0])
            fund = {"key": "funding", "label": "Funding, OKX (the 8-hour period that settled "
                    f"{day_clock(f[0], t0)})", "value": f[1], "unit": "rate"}
            rows.append(fund)

    pats = []
    d = 1 if run["dir"] == "up" else -1
    stocks = [r["value"] for r in rows if r["key"] in ("ES=F", "NQ=F") and r["value"] is not None]
    stocks_read = any(r["key"] in ("ES=F", "NQ=F") for r in rows)
    if btc is not None and btc * d >= CRYPTO_HOUR_MIN:
        if any(s * d >= STOCKS_WITH_MIN for s in stocks):
            pats.append({"label": "risk-off across assets" if d < 0 else "risk-on across assets",
                         "rule": f"crypto moved {CRYPTO_HOUR_MIN}% or more and stock futures "
                                 f"{STOCKS_WITH_MIN}% or more the same way in the onset hour"})
        elif stocks and all(abs(s) <= STOCKS_QUIET_MAX for s in stocks):
            # Sprint 9.3, review 1: a stock market that did not trade is not a reading, so "crypto only"
            # needs at least one futures bar in the hour (it was "within 0.1% or did not trade")
            pats.append({"label": "crypto only",
                         "rule": f"crypto moved {CRYPTO_HOUR_MIN}% or more while stock futures traded and "
                                 f"stayed within {STOCKS_QUIET_MAX}%"})
    venues = [r for r in (liq_row, gate) if r and not r.get("unread")]
    if oi_v is not None and venues:
        longs = sum(r["longs_usd"] or 0 for r in venues)
        shorts = sum(r["shorts_usd"] or 0 for r in venues)
        tot, side = longs + shorts, max(longs, shorts)
        if oi_v <= OI_FLUSH_PCT and tot and side / tot >= LIQ_ONE_SIDE:
            pats.append({"label": "leverage flush",
                         "rule": "open interest down 5% or more with 70% or more of liquidations on one side, "
                                 "at the venues read (" + ", ".join(r["label"].split(", ")[1] for r in venues) + ")"})
    excess = None
    if sym != "BTC" and own is not None and btc is not None and beta is not None:
        excess = round(own - beta * btc, 2)
        if abs(excess) >= EXCESS_MIN and abs(excess) > abs(own) / 2:
            pats.append({"label": "coin-specific",
                         "rule": f"{COINS[sym]['name']} moved {EXCESS_MIN} point or more beyond what its "
                                 f"30-day Bitcoin beta ({beta}) gives, and that is over half its move"})
    return {"hour_start_utc": _iso(t0), "hour_end_utc": _iso(t1), "rows": rows,
            "beta": beta, "excess_pts": excess, "patterns": pats}


# ---- the record -----------------------------------------------------------------------------------

def build(end_utc, wire, now_utc=None, fetch=None, pulse=None, gate=None, coins=("BTC", "ETH"),
          fomc_path=FOMC, history_root=HISTORY, deadline_s=DEADLINE_S, clock=None):
    """The evidence record for the 24 hours ending at `end_utc` (the Board's reading). Never
    raises for a source: a source that cannot be read is left out and named in `unread`.

    THE CORE AND THE REST (CLAUDE.md: the part is not the whole). The price series and the timing
    test are the core, read first with the plain fetch. Every other source reads through a budgeted
    fetch: past `deadline_s` (or after SIGTERM) it is skipped and named "not read in time", so the
    build returns, and the record is written, well inside the workflow step's timeout."""
    fetch = fetch or live_fetch
    budget = Budget(deadline_s, clock=clock)
    core_fetch, fetch = fetch, budgeted(fetch, budget)
    end_dt = _parse_utc(end_utc)
    if end_dt is None:
        raise ValueError(f"no window end: {end_utc!r}")
    end = int(end_dt.timestamp())
    start = end - WINDOW_H * 3600
    now = int((_parse_utc(now_utc) or _dt.datetime.now(_dt.timezone.utc)).timestamp())
    led = Ledger()
    series = {}
    for sym in coins:
        s, rest = read_series(sym, start, end, now, core_fetch, led)
        if s:
            series[sym] = (s, rest)
    cuts = []
    cands = candidates(start, end, wire, fetch, led, fomc_path, cuts)
    if gate is not None:
        kept = []
        for c in cands:
            if c["kind"] == "wire":
                line = gate.text(c["line"], "the evidence (reported)", dollars=True).strip()
                if not line:
                    led.miss(f"Wire item {c.get('wire_id')}", "its line did not pass the twins gate")
                    continue
                c["line"] = line
            kept.append(c)
        cands = kept
    cross = cross_assets(start, end, fetch, led)
    ct = _ct_val(fetch, led, coins)
    stables = _stables(start, end, fetch, led)
    led.miss("Hyperliquid liquidations", "not read: its public info API publishes no market-wide "
             "liquidation history; a liquidation shows only in the liquidated account's own fills")
    led.miss("Exchange listing notices", "not read for Bitcoin and Ether: a listing notice names a coin being "
             "added or removed, and the desk reads them for the Big movers")
    led.miss("EDGAR 8-K filings", "not read: the search gives the day, not the time")
    etf = (((pulse or {}).get("etf_flows") or {}).get("btc") or {})
    if isinstance(etf.get("latest_net_usd_m"), (int, float)):
        led.ok("Farside spot ETF flows (the daily read on Markets)", "https://farside.co.uk/btc/")
    else:
        led.miss("Farside spot ETF flows", "the Markets reading was not handed to this build")
    out = {"what": "The evidence under 'What lined up with the move': the intraday series, the "
                   "candidate events with their event and first-report times, the timing test and "
                   "the onset hour's mechanics. Measured by code; no model call; no grade.",
           "window": {"start_utc": _iso(start), "end_utc": _iso(end), "hours": WINDOW_H},
           "made_utc": _iso(now), "candidates": cands, "source_cuts": cuts, "coins": {},
           "day": {"stablecoins": stables,
                   "etf_btc": ({"date": etf.get("latest_date"), "net_usd_m": etf.get("latest_net_usd_m"),
                                "source": "Farside Investors (Markets)"}
                               if isinstance(etf.get("latest_net_usd_m"), (int, float)) else None)}}
    others = {k: v[0] for k, v in series.items()}
    runs = {sym: onset([(t, p) for t, p in series[sym][0]["points"]]) for sym in coins if sym in series}
    kalshi = _kalshi(sorted({r["start_t"] for r in runs.values() if r}), end, fetch, led)
    for sym in coins:
        if sym not in series:
            continue
        s, rest = series[sym]
        out["coins"][sym] = coin_entry(sym, s, rest, cands, start, end, now, others, cross, fetch, led, ct,
                                       kalshi, history_root)
    out["read"], out["unread"] = led.read, led.unread
    return out


def coin_entry(sym, s, rest, cands, start, end, now, others, cross, fetch, led, ct, kalshi, history_root=HISTORY):
    """One coin's part of a record: its series, the run, each candidate's timing test, the onset hour's
    mechanics and the hour after each candidate. build() calls it per coin; Sprint 9.4's movers step
    (movers.py) calls it for a Big mover with that coin's own candidates, so both read by the same rules."""
    pts = [(t, p) for t, p in s["points"]]
    run = onset(pts)
    mv = _pct(pts[0][1], pts[-1][1])
    seconds = [{"source": o["source"], "url": o["url"],
                "gap_pts": round(abs(_pct(o["points"][0][1], o["points"][-1][1]) - mv), 2)} for o in rest]
    sec = seconds[0] if seconds else None
    tests = []
    for c in cands:
        t, basis = test_time(c)
        r = timing(pts, run, t, c.get("scheduled")) if t is not None else None
        tests.append({"id": c["id"], "t_utc": _iso(t) if t is not None else None, "basis": basis,
                      "result": r})
    oi = _okx_oi(sym, start, end, now, fetch, led)
    liq = _okx_liq(sym, fetch, led, ct)
    fund = _okx_funding(sym, fetch, led)
    beta = _beta(sym, _et(start).date().isoformat(), root=history_root) if sym != "BTC" else None
    extra = {}
    if run:
        extra = {"taker": _okx_taker(sym, run["start_t"], fetch, led),
                 "gate": _gate_liq(sym, run["start_t"], fetch, led),
                 "kalshi": (kalshi or {}).get(run["start_t"]) or []}
    # SPRINT 9.3: the readings of the hour after each candidate, for the verdict's grade (verdict.py):
    # the onset hour cannot speak to an event that came after the onset. No new read: the series and
    # the cross-asset bars already in hand, by the same rules; open interest, liquidations and
    # funding stay the onset hour's only. Not printed by the section.
    evh = {}
    if run:
        for c, tst in zip(cands, tests):
            tu = _parse_utc(tst["t_utc"])
            if tu is None or not (start <= int(tu.timestamp()) <= end):
                continue
            m = mechanics(sym, dict(run, start_t=int(tu.timestamp())), pts, others, cross,
                          None, None, None, beta)
            if m:
                evh[c["id"]] = {"hour_start_utc": m["hour_start_utc"], "hour_end_utc": m["hour_end_utc"],
                                "rows": m["rows"], "patterns": m["patterns"]}
    return {"series": s, "second": sec, "seconds": seconds, "run": run, "tests": tests,
            "mechanics": mechanics(sym, run, pts, others, cross, oi, liq, fund, beta, extra),
            "event_hours": evh}


def register_coin(sym, gecko_id, name):
    """SPRINT 9.4: a Big mover's entry in COINS, so the series, the mechanics and the section read it by the
    same rules as Bitcoin and Ether. The venue tickers follow each venue's own pattern; a venue whose
    ticker names a different coin is caught by movers.py, which keeps a venue's series only when its move
    agrees with the Board's. Bitcoin and Ether keep their own entries."""
    if sym in ("BTC", "ETH"):
        return COINS[sym]
    COINS[sym] = {"name": name, "gecko": gecko_id, "coinbase": f"{sym}-USD", "okx": f"{sym}-USDT",
                  "kraken": f"{sym}USD", "binance": f"{sym}USDT", "gate": f"{sym}_USDT",
                  "swap": f"{sym}-USDT-SWAP", "ccy": sym, "history": gecko_id, "mover": True}
    return COINS[sym]


# ---- records on disk -------------------------------------------------------------------------------

def record_path(date_et, slot, directory=None):
    return os.path.join(directory or DIR, f"{date_et}-{slot}.json")


def load(date_et, slot, directory=None):
    """The stored record for a day's slot, or None. Never raises."""
    try:
        r = json.load(open(record_path(date_et, slot, directory), encoding="utf-8"))
        return r if isinstance(r, dict) and r.get("coins") else None
    except (OSError, ValueError):
        return None


def latest(directory=None):
    """The newest stored record, or None."""
    d = directory or DIR
    try:
        names = sorted(n for n in os.listdir(d) if re.fullmatch(r"\d{4}-\d{2}-\d{2}-(morning|evening)\.json", n))
    except OSError:
        return None
    for n in sorted(names, key=lambda n: (n[:10], n.endswith("evening.json")), reverse=True):
        date, slot = n[:10], n[11:-5]
        r = load(date, slot, d)
        if r:
            return r
    return None


def from_snapshot_coin(rec, sym, board_utc, max_gap_h=3):
    """The record's coin when its window ends within `max_gap_h` hours of the Board reading the
    page carries; None otherwise, so an old record is never shown as the page's current one."""
    if not rec or sym not in (rec.get("coins") or {}):
        return None
    a = _parse_utc((rec.get("window") or {}).get("end_utc"))
    b = _parse_utc(board_utc)
    if a is None or b is None or abs((a - b).total_seconds()) > max_gap_h * 3600:
        return None
    return rec["coins"][sym]


# ---- the page section --------------------------------------------------------------------------------

def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def _chg(v, unit="pct"):
    """A change with its own arrow and color (color truth); a rate prints signed, uncolored."""
    if v is None:
        return '<span class="ev-f">no trading in the hour</span>'
    if unit == "rate":
        return f'<span class="ev-f">{v:+.4f}% per 8 hours</span>'
    d = "up" if v > 0 else "down" if v < 0 else "flat"
    arrow = {"up": "▲ ", "down": "▼ "}.get(d, "")
    word = {"up": "up", "down": "down"}.get(d, "unchanged")
    txt = f"{abs(v):.1f} bp" if unit == "bp" else f"{abs(v):.2f}%"
    spoken = f"{abs(v):.1f} basis points" if unit == "bp" else f"{abs(v):.2f} percent"
    return f'<span class="chg {d}" aria-label="{word} {spoken}">{arrow}{txt}</span>'


def _usd(v):
    v = float(v)
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    if v >= 1e3:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.0f}"


def _price(v):
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}"


def _mins(m):
    m = int(round(abs(m)))
    h, mm = divmod(m, 60)
    if h and mm:
        return f"{h} hour{'' if h == 1 else 's'} {mm} minute{'' if mm == 1 else 's'}"
    if h:
        return f"{h} hour{'' if h == 1 else 's'}"
    return f"{mm} minute{'' if mm == 1 else 's'}"


def timing_words(r, c, name="the price", wdir="down", wname=None):
    """The timing test as plain sentences, from the numbers alone. Never a grade. `wname` (Sprint 9.9.1, Review 1) is the
    name of the window the figures are measured in ("since midnight ET", "in the 24 hours"); a page that names its window
    gets it beside every figure, and a caller that names none gets the sentences as they were."""
    if r is None:
        why = c.get("event_basis") or "no time is known for it"
        return [f"No time to test: {why}."]
    out = []
    lead = r["lead_min"]
    if c.get("scheduled") and abs(lead) <= SCHEDULED_TOL_MIN:
        out.append("The run began at its scheduled release time.")
    elif lead >= 0:
        out.append(f"It came {_mins(lead)} before the run began"
                   + ("." if lead <= LEAD_MIN else f", outside the {LEAD_MIN}-minute lead."))
    else:
        out.append(f"It came {_mins(lead)} after the run began.")
    fall = "fall" if wdir == "down" else "rise"
    if r.get("share_pct") is None or r.get("after_pct") is None:
        out.append("It falls outside the window, so the hour after it is not measured." if not wname else
                   f"It falls outside the {wname[3:]}, so the hour after it is not measured.")
    else:
        a, s = r["after_pct"], r["share_pct"]
        span = ("the rest of the window" if not wname else "the minutes left to the reading") if r.get("share_partial") else "the next 60 minutes"
        verb = "fell" if a < 0 else "rose" if a > 0 else "was unchanged"
        amt = f" {abs(a):.2f}%" if a else ""
        if s >= 0:
            out.append(f"In {span} {name} {verb}{amt}, {s:.0f}% of the " + (f"{fall} {wname}." if wname else f"window's {fall}."))
        else:
            out.append(f"In {span} {name} {verb}{amt}, against the " + (f"{fall} {wname}." if wname else f"window's {fall}."))
    if r["moved_first"]:
        out.append(f"The price moved first: {r['done_pct']:.0f}% of the run was done before it.")
    elif r["done_pct"] > 0:
        out.append(f"{r['done_pct']:.0f}% of the run was done before it.")
    return out


# The chart's box (Sprint 9.5, AUDIT.md 3.4 move 4: 12 px minimum on a phone). 340 units wide, so a 12.5-unit
# label reads at 12.6 px in the 343 px column of a 375 phone (13.1 px at 390), and at about 17.6 px at the
# 480 px the stylesheet caps it at. It was 420 wide with 11.5-unit labels: 9.4 px on a 375 phone.
CHART_W, CHART_H, CHART_X0, CHART_X1 = 340, 200, 62, 332
LABEL_FS = 12.5                 # every label's size in the box's own units; tests read it
PIN_R = 9.5


def _x(t, w0, w1, x0, x1):
    return x0 + (t - w0) / ((w1 - w0) or 1) * (x1 - x0)


# A record written before Sprint 9.5 carries "the Board" in its stored reasons; Markets is the name now.
_RENAMED = (("the Board's daily read", "the daily read on Markets"), ("the Board's reading", "the Markets reading"),
            ("on the Board", "on Markets"), ("(the Board)", "(Markets)"))


def _renamed(text):
    t = str(text or "")
    for a, b in _RENAMED:
        t = t.replace(a, b)
    return t


def chart_svg(coin, cands_numbered, name, window):
    """The timing chart: the price every five minutes over the window, its line colored by the
    window's own move (first point to last), the largest run shaded, the onset marked, each
    candidate inside the window pinned at its test time with its number from the list."""
    pts = (coin.get("series") or {}).get("points") or []
    run = coin.get("run")
    if len(pts) < 2:
        return ""
    W, H = CHART_W, CHART_H
    x0, x1, y0, y1 = CHART_X0, CHART_X1, 46, CHART_H - 30
    w0, w1 = pts[0][0], pts[-1][0]
    lo = min(p for _t, p in pts)
    hi = max(p for _t, p in pts)
    span = (hi - lo) or 1.0

    def y(p):
        return y1 - (p - lo) / span * (y1 - y0)

    up = pts[-1][1] >= pts[0][1]
    col = "var(--up-line)" if up else "var(--down-line)"
    line = " ".join(f"{_x(t, w0, w1, x0, x1):.1f},{y(p):.1f}" for t, p in pts)
    parts = [f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="var(--line)" stroke-width="1"></line>',
             f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="var(--line)" stroke-width="1"></line>',
             f'<text x="{x0 - 6}" y="{y0 + 4}" text-anchor="end" font-family="var(--mono)" font-size="{LABEL_FS}" '
             f'fill="var(--muted)">{_e(_price(hi))}</text>',
             f'<text x="{x0 - 6}" y="{y1 + 4}" text-anchor="end" font-family="var(--mono)" font-size="{LABEL_FS}" '
             f'fill="var(--muted)">{_e(_price(lo))}</text>']
    if run:
        rx0, rx1 = _x(run["start_t"], w0, w1, x0, x1), _x(run["end_t"], w0, w1, x0, x1)
        parts.append(f'<rect class="ev-run" x="{rx0:.1f}" y="{y0}" width="{max(1.0, rx1 - rx0):.1f}" '
                     f'height="{y1 - y0}" fill="{col}" fill-opacity="0.12"></rect>')
    # the time axis: every six hours on the ET clock
    first_tick = w0 - w0 % 3600 + 3600
    for t in range(first_tick, w1 + 1, 3600):
        if _et(t).hour % 6:
            continue
        x = _x(t, w0, w1, x0, x1)
        parts.append(f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y1 + 4}" stroke="var(--muted)"></line>'
                     f'<text x="{x:.1f}" y="{y1 + 17}" text-anchor="middle" font-family="var(--mono)" '
                     f'font-size="{LABEL_FS}" fill="var(--muted)">{_e(_et(t).strftime("%-I %p"))}</text>')
    parts.append(f'<polyline class="ev-line" fill="none" stroke="{col}" stroke-width="1.8" '
                 f'stroke-linejoin="round" points="{line}"></polyline>')
    last = {0: -99.0, 1: -99.0}
    for n, c, t in cands_numbered:
        if t is None or not (w0 <= t <= w1):
            continue
        x = _x(t, w0, w1, x0, x1)
        # two rows of markers, so two events minutes apart do not print one number over the other
        row = 0 if x - last[0] >= 21 else (1 if x - last[1] >= 21 else 0)
        last[row] = x
        cy = y0 - 14 - row * 21
        parts.append(f'<g class="ev-pin"><line x1="{x:.1f}" y1="{cy + PIN_R}" x2="{x:.1f}" y2="{y1}" '
                     f'stroke="var(--ink)" stroke-opacity="0.55" stroke-dasharray="3 3"></line>'
                     f'<circle cx="{x:.1f}" cy="{cy}" r="{PIN_R}" fill="var(--paper)" stroke="var(--ink)" '
                     f'stroke-width="1"></circle><text x="{x:.1f}" y="{cy + 4.4}" text-anchor="middle" '
                     f'font-family="var(--mono)" font-size="{LABEL_FS}" font-weight="700" fill="var(--ink)">{n}</text></g>')
    if run:
        ox = _x(run["start_t"], w0, w1, x0, x1)
        parts.append(f'<circle class="ev-onset" cx="{ox:.1f}" cy="{y(run["start_p"]):.1f}" r="4" '
                     f'fill="{col}" stroke="var(--paper)" stroke-width="1.5"></circle>')
    pinned = sum(1 for _n, _c, t in cands_numbered if t is not None and w0 <= t <= w1)
    wend = _parse_utc((window or {}).get("end_utc"))
    wend = int(wend.timestamp()) if wend else w1
    label = (f"{name} price every five minutes, the 24 hours to {clock(wend)} {long_day(wend)}, "
             f"between {_price(lo)} and {_price(hi)}; the largest run shaded"
             + (f", from {clock(run['start_t'])} to {clock(run['end_t'])}" if run else "")
             + f"; {pinned} event{'' if pinned == 1 else 's'} pinned at {'its' if pinned == 1 else 'their'} times.")
    return (f'<svg class="ev-chart" viewBox="0 0 {W} {H}" role="img" aria-label="{_e(label)}">'
            + "".join(parts) + "</svg>")


def _norm(t):
    return re.sub(r"[^a-z0-9$%]+", " ", str(t or "").lower()).strip()


def corrected_lines(corrections):
    """The lines a page's corrections quote, normalized: a correction that quotes a line says that
    line is wrong, so the section never prints it beside the correction."""
    out = []
    for c in corrections or []:
        for q in re.findall(r'["\u201c]([^"\u201d]{20,})["\u201d]', str((c or {}).get("text") or "")):
            out.append(_norm(q))
    return out


def _is_corrected(line, quoted):
    n = _norm(line)
    return bool(n) and any(n.startswith(q) or q.startswith(n) for q in quoted)


# ---- the page's window (Sprint 9.9.1) ---------------------------------------------------------------------------------------------
#
# THE LIST READS THE WINDOW THE GRADE WAS MADE ON (the strategist's ruling of October 26, entry 2026-10-26-C6, J-16 option 2). The stored
# record's run, its timing tests and its candidates are the 24 hours the verdict was graded on, and until sprint 9.9.3 moves the timing
# test, the grade and the list to the ET day together, a page draws that record as stored: it does not cut the series at midnight ET and
# does not re-measure anything. A page that names its window (`window` given) gets the window's name beside every figure of the list
# and the chart. How a stored verdict is graded (verdict.grade) is untouched.

WINDOW_NAME = "in the 24 hours"


def resolve_window(rec, window=None):
    """{basis, rec}: the record the page draws and the window's name. window None: the record as stored, the window unnamed (every page
    outside this item). Any named window draws the same stored record, named as the 24 hours it was graded on."""
    return {"basis": None if window is None else "rolling_24h", "rec": rec}


def section_html(rec, sym, live=True, skip_wire_ids=(), corrections=None, graded=None, marks=(), window=None, note=None):
    """The section for one coin, or '' (fail open) when the record has no series for it. `live`
    marks the window's stamp for the stale state (asof.js); a dated page passes False. Wire items
    the page already prints elsewhere are not passed here twice: the page drops them from its
    own list instead, so `skip_wire_ids` is for a caller that cannot. `corrections` are the
    page's own: a wire line one of them quotes is not printed (the record stays frozen; the
    correction applies when the page is drawn). `window` (Sprint 9.9.1): given, the window is named beside every figure (the 24 hours the
    record was graded on); None draws the section as every page outside that item has it (see resolve_window). `note` (Sprint 9.9.1)
    is one plain sentence the page adds under the section's head, naming the other window its card reads."""
    try:
        res = resolve_window(rec, window)
        return _section(res["rec"], sym, live, set(skip_wire_ids), corrected_lines(corrections), graded, set(marks or ()),
                        res if window is not None else None, note)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::why_evidence: the section for {sym} was not drawn ({type(e).__name__}: {e})")
        return ""


def _section(rec, sym, live, skip, quoted=(), graded=None, marks=frozenset(), res=None, note_text=None):
    coin = ((rec or {}).get("coins") or {}).get(sym)
    if not coin or not (coin.get("series") or {}).get("points"):
        return ""
    name = COINS[sym]["name"]
    pts = coin["series"]["points"]
    wend = _parse_utc((rec.get("window") or {}).get("end_utc"))
    # the window's own end (the Board's reading) labels it; the last close sits up to 5 minutes before
    w1 = int(wend.timestamp()) if wend else pts[-1][0]
    run = coin.get("run")
    by_id = {t["id"]: t for t in coin.get("tests") or []}
    cands = [c for c in rec.get("candidates") or [] if c.get("wire_id") not in skip or c["kind"] != "wire"]
    cands = [c for c in cands if not (c["kind"] == "wire" and _is_corrected(c["line"], quoted))]
    order = sorted(cands, key=lambda c: (by_id.get(c["id"], {}).get("t_utc") or "9999", c["id"]))
    numbered = []
    for i, c in enumerate(order, 1):
        tu = _parse_utc(by_id.get(c["id"], {}).get("t_utc"))
        numbered.append((i, c, int(tu.timestamp()) if tu else None))

    asof = f' data-asof="{_e(_iso(w1))}"' if live else ""
    # SPRINT 9.9.1: a page that names its window gets that window's name beside every figure (wname); None is the page as main has it
    wname = WINDOW_NAME if res else None
    wattr = f' data-ev-window="{res["basis"]}"' if res else ""
    win = f'the 24 hours to {clock(w1)}, {long_day(w1)}'
    seconds = coin.get("seconds") or ([coin["second"]] if coin.get("second") else [])
    src = f'{_e(coin["series"]["source"])}'
    for o in seconds:
        src += (f'; beside it, {_e(o["source"])} '
                + ("agrees within 0.1 point" if o["gap_pts"] <= 0.1
                   else f'differs by {o["gap_pts"]:.2f} points over the window'))
    head = (f'<p class="ev-win"{asof}>{_e(name)}, {_e(win)}. Prices: {src}.</p>')
    runp = ""
    if run:
        runp = (f'<p class="ev-run-l">The largest run {_e(wname) if wname else "in the window"}: {_chg(run["pct"])} from '
                f'{_e(_price(run["start_p"]))} at {_e(day_clock(run["start_t"], w1))} to '
                f'{_e(_price(run["end_p"]))} at {_e(day_clock(run["end_t"], w1))}. It is shaded on the chart; '
                f'its start is marked.</p>')
    chart = chart_svg(coin, numbered, name, rec.get("window"))
    note = f'<p class="ev-m ev-window-note">{_e(note_text)}</p>' if (res and note_text) else ""

    items = []
    for n, c, t in numbered:
        tst = by_id.get(c["id"], {})
        line = c["line"]
        if GRADE_WORDS.search(line):
            line = f'Report, {c["links"][0]["outlet"]}' if c.get("links") else "Report"
        links = c.get("report_links") or c.get("links") or []
        srcs = ", ".join(f'<a href="{_e(l["url"])}" rel="noopener">{_e(l["outlet"])}</a>'
                         for l in links if l.get("url"))
        meta = []
        ev = _parse_utc(c.get("event_utc"))
        if ev is not None:
            meta.append(f'Event {_e(day_clock(int(ev.timestamp()), w1))}'
                        + (" (scheduled)" if c.get("scheduled") else "")
                        + f', {_e(c.get("event_basis") or "")}')
        elif c.get("event_day"):
            meta.append(f'Event day {_e(c["event_day"])}, {_e(c.get("event_basis") or "")}')
        rp = _parse_utc(c.get("report_utc"))
        if rp is not None:
            k = int(c.get("source_count") or 0)
            meta.append(f'First reported {_e(day_clock(int(rp.timestamp()), w1))}'
                        + (f', {k} source{"" if k == 1 else "s"}' if k else ""))
        elif c["kind"] == "release":
            meta.append("No wire report of it found in the window")
        if c.get("primary"):
            meta.append("Primary source")
        if srcs:
            meta.append(srcs)
        tw = timing_words(tst.get("result"), c, name, (run or {}).get("dir") or "down", wname)
        sec = (f'<span class="ev-sec">Secondary: {_e(c["secondary_why"])}.</span>' if c.get("secondary") else "")
        rep = ""
        if (c.get("report_line") and not GRADE_WORDS.search(c["report_line"])
                and not _is_corrected(c["report_line"], quoted)):
            rep = f'<span class="ev-rep">First report: {_e(c["report_line"])}</span>'
        # Sprint 9.3, the pointer (Jack, J-7): every item carries its id; an item the verdict card names is
        # marked, so the card's name points at exactly one listed item
        mk = c["id"] in marks
        items.append(f'<li class="ev-c{" ev-graded" if mk else ""}" data-ev-id="{_e(c["id"])}">'
                     f'<span class="ev-n" aria-hidden="true">{n}</span>'
                     + ('<span class="ev-mark">Named in the verdict above</span>' if mk else "")
                     + f'<span class="ev-l">{_e(line)}</span>{rep}'
                     f'<span class="ev-m">{" &middot; ".join(meta)}</span>'
                     f'<span class="ev-t">{_e(" ".join(tw))}</span>{sec}</li>')
    cand_html = (f'<ol class="ev-cands">{"".join(items)}</ol>' if items else
                 (f'<p class="ev-m">The desk found no reported event or scheduled release {wname}.</p>' if wname else
                  '<p class="ev-m">The desk found no reported event or scheduled release in this window.</p>'))

    mech = coin.get("mechanics") or {}
    mrows = []
    for r in mech.get("rows") or []:
        if str(r.get("key")).startswith("kalshi"):
            fig = f'<span class="ev-f">{r["from_pct"]:.1f}% to {r["to_pct"]:.1f}%</span>'
        elif r.get("key") == "taker":
            fig = (f'<span class="ev-f">{_e(_usd(r["buy_usd"]))} bought, '
                   f'{_e(_usd(r["sell_usd"]))} sold</span>')
        elif r.get("unit") == "shares":
            fig = (f'<span class="ev-f">{r["value"] / 1e6:.2f}M shares</span>' if r.get("value")
                   else '<span class="ev-f">no trading in the hour</span>')
        elif str(r.get("key")).startswith("liq"):
            if r.get("unread"):
                fig = f'<span class="ev-f">not read for this hour: {_e(r["why"])}</span>'
            else:
                fig = (f'<span class="ev-f">{_e(_usd(r["longs_usd"]))} longs, '
                       f'{_e(_usd(r["shorts_usd"]))} shorts</span>')
        else:
            fig = _chg(r.get("value"), r.get("unit") or "pct")
        mrows.append(f'<li class="td-row"><span class="td-n">{_e(r["label"])}</span>{fig}</li>')
    mech_html = ""
    if mrows and run:
        h0, h1 = run["start_t"], run["start_t"] + 3600
        pat = mech.get("patterns") or []
        # a record written before 9.3 may label "crypto only" in an hour the futures did not trade; that is
        # not a reading, so the page says what happened instead (the verdict card reads it the same way)
        traded = any(r.get("key") in ("ES=F", "NQ=F") and r.get("value") is not None for r in mech.get("rows") or [])
        shut = any(p.get("label") == "crypto only" for p in pat) and not traded
        pat = [p for p in pat if not (shut and p.get("label") == "crypto only")]
        pat_html = ("".join(f'<p class="ev-pat">Pattern: <b>{_e(p["label"])}</b> ({_e(p["rule"])}).</p>'
                            for p in pat) if pat else
                    '<p class="ev-pat">Pattern: none of the four the desk names (risk-off or risk-on across '
                    'assets, crypto only, leverage flush, coin-specific) holds in this hour.</p>')
        if shut:
            pat_html += ('<p class="ev-pat">Stock futures did not trade in this hour, so the readings cannot tell '
                         'a crypto move from a wider one.</p>')
        beta = (f'<p class="ev-m">{_e(name)}\'s 30-day beta to Bitcoin, from the stored daily closes: '
                f'{mech["beta"]}.</p>' if mech.get("beta") is not None else "")
        mech_html = (f'<h3 class="td-h3">The hour the run began, {_e(day_clock(h0, w1))} to {_e(clock(h1))}</h3>'
                     f'<ul class="td-list ev-mech">{"".join(mrows)}</ul>{pat_html}{beta}')

    unread = rec.get("unread") or []
    seen, names = set(), []
    for u in unread:
        if u["name"] not in seen:
            seen.add(u["name"])
            names.append(_renamed(f'{u["name"]} ({u["why"]})'))
    srcs_html = (f'<p class="ev-src">Not read, so not shown: {_e("; ".join(names))}.</p>' if names else "")
    day = rec.get("day") or {}
    daily = [x for x, ok in (("Farside spot ETF flows (daily; on Markets)", day.get("etf_btc")),
                             ("DefiLlama stablecoin supply (daily)", day.get("stablecoins"))) if ok]
    if daily:
        srcs_html = f'<p class="ev-src">Read, not shown in this hour: {_e("; ".join(daily))}.</p>' + srcs_html
    return (f'<section class="td-sec ev" aria-label="{SECTION_TITLE}" data-ev="{_e(sym)}"{wattr}>'
            f'<h2>{SECTION_TITLE}</h2>{head}{note}{runp}'
            f'<figure class="ev-fig">{chart}<figcaption class="ev-m">Numbers on the chart match the list below. '
            f'Times are Eastern.</figcaption></figure>'
            f'{cand_html}{mech_html}'
            + (f'<p class="pc-note">These events and readings sit beside the move in time. The verdict on this '
               f'page grades them by fixed rules, the timing test and the market readings of the hour it names, '
               f'and says which, if any, lines up with the move.</p>' if graded else
               f'<p class="pc-note">These events and readings sit beside the move in time. The desk measured '
               f'when each came and what the price did around it; it does not say any of them moved the price.</p>')
            + f'{srcs_html}</section>')


def wire_ids_shown(rec):
    """The wire ids the section prints (as candidates or as a release's first report), so a page
    can leave them out of its own list and print each item once."""
    out = set()
    for c in (rec or {}).get("candidates") or []:
        if c.get("wire_id"):
            out.add(c["wire_id"])
        if c.get("report_wire_id"):
            out.add(c["report_wire_id"])
    return out


def wire_urls_shown(rec):
    """The source URLs of the wire items the section prints (for a page whose list carries no id)."""
    out = set()
    for c in (rec or {}).get("candidates") or []:
        if c["kind"] == "wire":
            out.update(l.get("url") for l in c.get("links") or [] if l.get("url"))
        out.update(l.get("url") for l in c.get("report_links") or [] if l.get("url"))
    return out


# ---- the run's step ----------------------------------------------------------------------------------

def _slot_now(now):
    """The slot this run writes for: the newest daily-answer record of today (ET), else the clock's."""
    import today as _today
    d = now.astimezone(ET).date().isoformat()
    recs = [r for r in _today.load_records() if r.get("date_et") == d]
    if recs:
        r = max(recs, key=lambda r: (r.get("composed_utc") or "", r["slot"] == "evening"))
        return d, r["slot"], r.get("composed_utc")
    return d, ("evening" if now >= _today._evening_et(now) else "morning"), None


def main():
    args = sys.argv[1:]
    if args[:1] == ["--record"] and len(args) in (3, 4):
        return _record(args[1], args[2], args[3] if len(args) == 4 else None)
    if "--write" not in args:
        print(__doc__.split("\n\n")[-1])
        return 2
    try:
        import home
        import site_build as sb
        import snapshot as _s
        import twins_gate
        pulse, flows = sb.load_pulse(), sb.load_flows()
        end = (pulse or {}).get("generated_utc")
        if not end:
            print("::warning::why_evidence: the Board carries no reading time; no record written")
            return 0
        now = _dt.datetime.now(_dt.timezone.utc)
        if (now - _parse_utc(end)).total_seconds() > 3 * 3600:
            print(f"::warning::why_evidence: the Board's reading ({end}) is over 3 hours old; no record written")
            return 0
        date, slot, composed = _slot_now(now)
        have = load(date, slot)
        if have and (have.get("today_composed_utc") or "") >= (composed or ""):
            print(f"why_evidence: {date}-{slot}.json already stored; a stored record is frozen")
            return 0
        snap = _s.build(pulse, flows)
        gate = twins_gate.Gate(snap, log_path="", quiet=True)
        # The step's `timeout 300` sends SIGTERM: the build then skips what it has not read, names it,
        # and returns, so the record below is still written with the core in it.
        import signal
        signal.signal(signal.SIGTERM, lambda *_a: STOP.update(set=True))
        import time
        t_start = time.monotonic()
        rec = build(end, home.load_json(sb.WIRE_JSON), fetch=live_fetch, pulse=pulse, gate=gate)
        print(f"why_evidence: built in {time.monotonic() - t_start:.0f}s (budget {DEADLINE_S}s)")
        rec.update(date_et=date, slot=slot, today_composed_utc=composed)
        os.makedirs(DIR, exist_ok=True)
        p = record_path(date, slot)
        json.dump(rec, open(p, "w", encoding="utf-8"), indent=1)
        for sym, c in rec["coins"].items():
            run = c.get("run") or {}
            pats = ", ".join(x["label"] for x in (c.get("mechanics") or {}).get("patterns") or []) or "none"
            print(f"why_evidence: {sym} run {run.get('dir')} {run.get('pct')}% from "
                  f"{run.get('start_t') and clock(run['start_t'])}; pattern {pats}")
        print(f"why_evidence: wrote {p} ({len(rec['candidates'])} candidate(s), "
              f"{len(rec['read'])} source(s) read, {len(rec['unread'])} not read)")
        for u in rec["unread"]:
            print(f"  not read: {u['name']}: {u['why']}")
    except Exception as e:                                       # never a gate on a slot
        print(f"::warning::why_evidence: no record written ({type(e).__name__}: {e})")
    return 0


# Long histories a fixture keeps only near its window, so a fixture stays a readable size. The
# entries kept are the source's own, unchanged; the README beside the fixtures says so.
_TRIM_DAYS = 7


def _trim(url, body, start, end):
    lo, hi = start - _TRIM_DAYS * 86400, end + _TRIM_DAYS * 86400
    if url.startswith("https://api.llama.fi/hacks") and isinstance(body, list):
        return [h for h in body if isinstance(h, dict) and lo <= int(h.get("date") or 0) <= hi]
    if url.startswith("https://stablecoins.llama.fi/") and isinstance(body, list):
        return [r for r in body if isinstance(r, dict) and lo <= int(r.get("date") or 0) <= hi]
    return body


def _record(end_utc, out_path, wire_path=None):
    """Read a real window's sources now and save every answer, so the tests run on what the
    sources said. The wire is not fetched: the fixture names the wire file it is tested with, and
    that file, when given, is what the linked reports are read for. When OUT already exists, its
    answers are kept as they were and only the answers it lacks are read now; each of those is
    stamped in `added_utc`, and the build keeps the fixture's first `recorded_utc` as its clock."""
    old = {}
    if os.path.exists(out_path):
        old = json.load(open(out_path, encoding="utf-8"))
    now = _dt.datetime.now(_dt.timezone.utc)
    now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    have = old.get("responses") or {}
    added = dict(old.get("added_utc") or {})

    def fetch(url, kind="json"):
        k = _key(url, kind)
        if k in have:
            return Replay(have)(url, kind)
        added[k] = now_s
        return live_fetch(url, kind)
    rec = Recorder(fetch)
    end = int(_parse_utc(end_utc).timestamp())
    wire = json.load(open(wire_path, encoding="utf-8")) if wire_path else None
    build(end_utc, wire, now_utc=old.get("recorded_utc") or now_s, fetch=rec)
    resp = {u: _trim(u, b, end - WINDOW_H * 3600, end) for u, b in rec.responses.items()}
    for k, v in have.items():
        resp.setdefault(k, v)
    json.dump({"what": "Every answer the evidence's sources gave for this window, read at "
                       "recorded_utc by why_evidence.py --record (answers added later carry their own "
                       "stamp in added_utc); long histories trimmed to 7 days either side of the window "
                       "(the entries kept are unchanged); a key 'article:<url>' is a linked report as "
                       "the text the desk's extractor took from it.",
               "end_utc": end_utc, "recorded_utc": old.get("recorded_utc") or now_s,
               "recorded_et": old.get("recorded_et") or now.astimezone(ET).strftime("%a %b %-d %Y, %-I:%M %p %Z"),
               "added_utc": {k: v for k, v in added.items() if k in resp},
               "responses": resp}, open(out_path, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"recorded {len(resp)} answer(s) to {out_path} ({sum(1 for k in added if k in resp)} added now)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
