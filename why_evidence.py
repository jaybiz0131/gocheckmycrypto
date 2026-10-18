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
    python3 why_evidence.py --record END_UTC OUT     # record a real window's answers as a fixture
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
SECTION_TITLE = "What lined up with the move"

COINS = {
    "BTC": {"name": "Bitcoin", "gecko": "bitcoin", "coinbase": "BTC-USD", "okx": "BTC-USDT",
            "kraken": "XBTUSD", "swap": "BTC-USDT-SWAP", "ccy": "BTC", "history": "bitcoin"},
    "ETH": {"name": "Ether", "gecko": "ethereum", "coinbase": "ETH-USD", "okx": "ETH-USDT",
            "kraken": "ETHUSD", "swap": "ETH-USDT-SWAP", "ccy": "ETH", "history": "ethereum"},
}

# Yahoo symbol, the label the page prints, and how a change is stated (percent, or basis points
# for a yield)
CROSS = [("ES=F", "S&P 500 futures", "pct"), ("NQ=F", "Nasdaq 100 futures", "pct"),
         ("DX-Y.NYB", "Dollar index", "pct"), ("^TNX", "10-year Treasury yield", "bp"),
         ("GC=F", "Gold futures", "pct"), ("CL=F", "Oil futures (WTI)", "pct"),
         ("^VIX", "VIX", "pct")]

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


def live_fetch(url, kind="json"):
    """The desk's own fetch layer: market_pulse.get_json for JSON (its 429 handling and the
    CoinGecko spacing; one try on CoinGecko so a throttled read falls to the next venue at
    once), common.fetch_page_meta for pages and feeds (per-host spacing, retry with
    Retry-After). Raises Unread with the reason."""
    import common
    import market_pulse
    if kind == "json":
        try:
            return market_pulse.get_json(url, timeout=25,
                                         attempts=1 if "coingecko.com" in url else 2)
        except Exception as e:                                   # noqa: BLE001
            raise Unread(_why(e)) from None
    m = common.fetch_page_meta(url, timeout=25, retries=1)
    if m.get("status") != 200 or not m.get("body"):
        raise Unread(m.get("error") or f"HTTP {m.get('status')}")
    return m["body"]


def _why(e):
    code = getattr(e, "code", None)
    if code:
        return f"HTTP {code}"
    return f"{type(e).__name__}: {str(e)[:80]}"


class Recorder:
    """Wraps a fetch and keeps every answer by URL, errors included, for a fixture."""

    def __init__(self, fetch=live_fetch):
        self.fetch, self.responses = fetch, {}

    def __call__(self, url, kind="json"):
        try:
            body = self.fetch(url, kind)
        except Exception as e:                                   # noqa: BLE001
            self.responses[url] = {"__error__": str(e) or type(e).__name__}
            raise
        self.responses[url] = body
        return body


class Replay:
    """Serves a recorded fixture's answers. A URL the fixture does not hold was not read."""

    def __init__(self, responses):
        self.responses = responses

    def __call__(self, url, kind="json"):
        if url not in self.responses:
            raise Unread("not in the recorded fixture")
        body = self.responses[url]
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
    """(series, second): each {source, url, bar_min, points [[t, price], ...]} or None."""
    got = []
    want = (end - start) / 300.0
    for name, url, parse, bar, skip in price_sources(sym, start, end, now):
        label = f"{COINS[sym]['name']} prices: {name}"
        if skip:
            ledger.miss(label, skip)
            continue
        if len(got) == 2:
            break
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
    return (got[0] if got else None), (got[1] if len(got) > 1 else None)


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


def candidates(start, end, wire, fetch, ledger, fomc_path=FOMC):
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
    wires = _wire_candidates(wire, start, end)
    ledger.ok("The wire (site/data/wire.json)", "/data/wire.json" if wire else "",
              f"{len(wires)} item(s) in the window")
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
    """(epoch, basis) the timing test uses: the event time when the source gives one, else the
    first-report time; (None, why) when neither exists."""
    ev = _parse_utc(c.get("event_utc"))
    if ev is not None:
        return int(ev.timestamp()), "event"
    rp = _parse_utc(c.get("report_utc"))
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


def cross_assets(start, end, fetch, ledger):
    out = {}
    for sym, label, unit in CROSS:
        url = _yahoo_url(sym, start, end)
        try:
            pts = _clip(_yahoo_pts(fetch(url, "json")), start, end)
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(f"Yahoo 5-minute bars, {label}", str(e), url)
            continue
        ledger.ok(f"Yahoo 5-minute bars, {label}", url)
        out[sym] = {"label": label, "unit": unit, "points": [[t, round(p, 4)] for t, p in pts]}
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


def mechanics(sym, run, series, others, cross, oi, liq, funding, beta):
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
        if ysym in cross:
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
        elif stocks_read and all(abs(s) <= STOCKS_QUIET_MAX for s in stocks):
            pats.append({"label": "crypto only",
                         "rule": f"crypto moved {CRYPTO_HOUR_MIN}% or more while stock futures stayed "
                                 f"within {STOCKS_QUIET_MAX}% or did not trade"})
    if oi_v is not None and liq_row and not liq_row.get("unread"):
        tot = (liq_row["longs_usd"] or 0) + (liq_row["shorts_usd"] or 0)
        side = max(liq_row["longs_usd"] or 0, liq_row["shorts_usd"] or 0)
        if oi_v <= OI_FLUSH_PCT and tot and side / tot >= LIQ_ONE_SIDE:
            pats.append({"label": "leverage flush",
                         "rule": "open interest down 5% or more with 70% or more of liquidations on one side"})
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
          fomc_path=FOMC, history_root=HISTORY):
    """The evidence record for the 24 hours ending at `end_utc` (the Board's reading). Never
    raises for a source: a source that cannot be read is left out and named in `unread`."""
    fetch = fetch or live_fetch
    end_dt = _parse_utc(end_utc)
    if end_dt is None:
        raise ValueError(f"no window end: {end_utc!r}")
    end = int(end_dt.timestamp())
    start = end - WINDOW_H * 3600
    now = int((_parse_utc(now_utc) or _dt.datetime.now(_dt.timezone.utc)).timestamp())
    led = Ledger()
    series = {}
    for sym in coins:
        s, second = read_series(sym, start, end, now, fetch, led)
        if s:
            series[sym] = (s, second)
    cands = candidates(start, end, wire, fetch, led, fomc_path)
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
    led.miss("OKX taker flow", "not read: the 5-minute series reaches back about three hours")
    led.miss("Kalshi Fed markets", "not read: not on the Board")
    led.miss("Exchange listing notices", "not read: no single feed")
    led.miss("EDGAR 8-K filings", "not read: the search gives the day, not the time")
    etf = (((pulse or {}).get("etf_flows") or {}).get("btc") or {})
    out = {"what": "The evidence under 'What lined up with the move': the intraday series, the "
                   "candidate events with their event and first-report times, the timing test and "
                   "the onset hour's mechanics. Measured by code; no model call; no grade.",
           "window": {"start_utc": _iso(start), "end_utc": _iso(end), "hours": WINDOW_H},
           "made_utc": _iso(now), "candidates": cands, "coins": {},
           "day": {"stablecoins": stables,
                   "etf_btc": ({"date": etf.get("latest_date"), "net_usd_m": etf.get("latest_net_usd_m"),
                                "source": "Farside Investors (the Board)"}
                               if isinstance(etf.get("latest_net_usd_m"), (int, float)) else None)}}
    others = {k: v[0] for k, v in series.items()}
    for sym in coins:
        if sym not in series:
            continue
        s, second = series[sym]
        pts = [(t, p) for t, p in s["points"]]
        run = onset(pts)
        sec = None
        if second:
            a, b = second["points"][0][1], second["points"][-1][1]
            mv = _pct(pts[0][1], pts[-1][1])
            sec = {"source": second["source"], "url": second["url"],
                   "gap_pts": round(abs(_pct(a, b) - mv), 2)}
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
        out["coins"][sym] = {"series": s, "second": sec, "run": run, "tests": tests,
                             "mechanics": mechanics(sym, run, pts, others, cross, oi, liq, fund, beta)}
    out["read"], out["unread"] = led.read, led.unread
    return out


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


def timing_words(r, c, name="the price", wdir="down"):
    """The timing test as plain sentences, from the numbers alone. Never a grade."""
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
        out.append("It falls outside the window, so the hour after it is not measured.")
    else:
        a, s = r["after_pct"], r["share_pct"]
        span = "the rest of the window" if r.get("share_partial") else "the next 60 minutes"
        verb = "fell" if a < 0 else "rose" if a > 0 else "was unchanged"
        amt = f" {abs(a):.2f}%" if a else ""
        if s >= 0:
            out.append(f"In {span} {name} {verb}{amt}, {s:.0f}% of the window's {fall}.")
        else:
            out.append(f"In {span} {name} {verb}{amt}, against the window's {fall}.")
    if r["moved_first"]:
        out.append(f"The price moved first: {r['done_pct']:.0f}% of the run was done before it.")
    elif r["done_pct"] > 0:
        out.append(f"{r['done_pct']:.0f}% of the run was done before it.")
    return out


# The chart's box. 420 units wide so its 11.5-unit labels read at about 9.4 px on a 375 phone
# (343 px of column) and about 16 px at the 600 px the stylesheet caps it at.
CHART_W, CHART_H, CHART_X0, CHART_X1 = 420, 216, 62, 410


def _x(t, w0, w1, x0, x1):
    return x0 + (t - w0) / ((w1 - w0) or 1) * (x1 - x0)


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
             f'<text x="{x0 - 6}" y="{y0 + 4}" text-anchor="end" font-family="var(--mono)" font-size="11.5" '
             f'fill="var(--muted)">{_e(_price(hi))}</text>',
             f'<text x="{x0 - 6}" y="{y1 + 4}" text-anchor="end" font-family="var(--mono)" font-size="11.5" '
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
                     f'font-size="11.5" fill="var(--muted)">{_e(_et(t).strftime("%-I %p"))}</text>')
    parts.append(f'<polyline class="ev-line" fill="none" stroke="{col}" stroke-width="1.8" '
                 f'stroke-linejoin="round" points="{line}"></polyline>')
    last = {0: -99.0, 1: -99.0}
    for n, c, t in cands_numbered:
        if t is None or not (w0 <= t <= w1):
            continue
        x = _x(t, w0, w1, x0, x1)
        # two rows of markers, so two events minutes apart do not print one number over the other
        row = 0 if x - last[0] >= 18 else (1 if x - last[1] >= 18 else 0)
        last[row] = x
        cy = y0 - 12 - row * 19
        parts.append(f'<g class="ev-pin"><line x1="{x:.1f}" y1="{cy + 8}" x2="{x:.1f}" y2="{y1}" '
                     f'stroke="var(--ink)" stroke-opacity="0.55" stroke-dasharray="3 3"></line>'
                     f'<circle cx="{x:.1f}" cy="{cy}" r="8" fill="var(--paper)" stroke="var(--ink)" '
                     f'stroke-width="1"></circle><text x="{x:.1f}" y="{cy + 3.5}" text-anchor="middle" '
                     f'font-family="var(--mono)" font-size="10" font-weight="700" fill="var(--ink)">{n}</text></g>')
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


def section_html(rec, sym, live=True, skip_wire_ids=()):
    """The section for one coin, or '' (fail open) when the record has no series for it. `live`
    marks the window's stamp for the stale state (asof.js); a dated page passes False. Wire items
    the page already prints elsewhere are not passed here twice: the page drops them from its
    own list instead, so `skip_wire_ids` is for a caller that cannot."""
    try:
        return _section(rec, sym, live, set(skip_wire_ids))
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::why_evidence: the section for {sym} was not drawn ({type(e).__name__}: {e})")
        return ""


def _section(rec, sym, live, skip):
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
    order = sorted(cands, key=lambda c: (by_id.get(c["id"], {}).get("t_utc") or "9999", c["id"]))
    numbered = []
    for i, c in enumerate(order, 1):
        tu = _parse_utc(by_id.get(c["id"], {}).get("t_utc"))
        numbered.append((i, c, int(tu.timestamp()) if tu else None))

    asof = f' data-asof="{_e(_iso(w1))}"' if live else ""
    win = f'the 24 hours to {clock(w1)}, {long_day(w1)}'
    second = coin.get("second")
    src = f'{_e(coin["series"]["source"])}'
    if second:
        src += (f'; second read, {_e(second["source"])}, '
                + ("agrees within 0.1 point" if second["gap_pts"] <= 0.1
                   else f'differs by {second["gap_pts"]:.2f} points over the window'))
    head = (f'<p class="ev-win"{asof}>{_e(name)}, {_e(win)}. Prices: {src}.</p>')
    runp = ""
    if run:
        runp = (f'<p class="ev-run-l">The largest run in the window: {_chg(run["pct"])} from '
                f'{_e(_price(run["start_p"]))} at {_e(day_clock(run["start_t"], w1))} to '
                f'{_e(_price(run["end_p"]))} at {_e(day_clock(run["end_t"], w1))}. It is shaded on the chart; '
                f'its start is marked.</p>')
    chart = chart_svg(coin, numbered, name, rec.get("window"))

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
        tw = timing_words(tst.get("result"), c, name, (run or {}).get("dir") or "down")
        sec = (f'<span class="ev-sec">Secondary: {_e(c["secondary_why"])}.</span>' if c.get("secondary") else "")
        rep = ""
        if c.get("report_line") and not GRADE_WORDS.search(c["report_line"]):
            rep = f'<span class="ev-rep">First report: {_e(c["report_line"])}</span>'
        items.append(f'<li class="ev-c"><span class="ev-n" aria-hidden="true">{n}</span>'
                     f'<span class="ev-l">{_e(line)}</span>{rep}'
                     f'<span class="ev-m">{" &middot; ".join(meta)}</span>'
                     f'<span class="ev-t">{_e(" ".join(tw))}</span>{sec}</li>')
    cand_html = (f'<ol class="ev-cands">{"".join(items)}</ol>' if items else
                 '<p class="ev-m">The desk found no reported event or scheduled release in this window.</p>')

    mech = coin.get("mechanics") or {}
    mrows = []
    for r in mech.get("rows") or []:
        if r.get("key") == "liq":
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
        pat_html = ("".join(f'<p class="ev-pat">Pattern: <b>{_e(p["label"])}</b> ({_e(p["rule"])}).</p>'
                            for p in pat) if pat else
                    '<p class="ev-pat">Pattern: none of the four the desk names (risk-off or risk-on across '
                    'assets, crypto only, leverage flush, coin-specific) holds in this hour.</p>')
        beta = (f'<p class="ev-m">{_e(name)}\'s 30-day beta to Bitcoin, from the stored daily closes: '
                f'{mech["beta"]}.</p>' if mech.get("beta") is not None else "")
        mech_html = (f'<h3 class="td-h3">The hour the run began, {_e(day_clock(h0, w1))} to {_e(clock(h1))}</h3>'
                     f'<ul class="td-list ev-mech">{"".join(mrows)}</ul>{pat_html}{beta}')

    unread = rec.get("unread") or []
    seen, names = set(), []
    for u in unread:
        if u["name"] not in seen:
            seen.add(u["name"])
            names.append(f'{u["name"]} ({u["why"]})')
    srcs_html = (f'<p class="ev-src">Not read, so not shown: {_e("; ".join(names))}.</p>' if names else "")
    return (f'<section class="td-sec ev" aria-label="{SECTION_TITLE}" data-ev="{_e(sym)}">'
            f'<h2>{SECTION_TITLE}</h2>{head}{runp}'
            f'<figure class="ev-fig">{chart}<figcaption class="ev-m">Numbers on the chart match the list below. '
            f'Times are Eastern.</figcaption></figure>'
            f'{cand_html}{mech_html}'
            f'<p class="pc-note">These events and readings sit beside the move in time. The desk measured '
            f'when each came and what the price did around it; it does not say any of them moved the price.</p>'
            f'{srcs_html}</section>')


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
    if args[:1] == ["--record"] and len(args) == 3:
        return _record(args[1], args[2])
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
        rec = build(end, home.load_json(sb.WIRE_JSON), fetch=live_fetch, pulse=pulse, gate=gate)
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


def _record(end_utc, out_path):
    """Read a real window's sources now and save every answer, so the tests run on what the
    sources said. The wire is not fetched: the fixture names the wire file it is tested with."""
    rec = Recorder()
    now = _dt.datetime.now(_dt.timezone.utc)
    end = int(_parse_utc(end_utc).timestamp())
    build(end_utc, None, now_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), fetch=rec)
    resp = {u: _trim(u, b, end - WINDOW_H * 3600, end) for u, b in rec.responses.items()}
    json.dump({"what": "Every answer the evidence's sources gave for this window, read at "
                       "recorded_utc by why_evidence.py --record; long histories trimmed to 7 days "
                       "either side of the window (the entries kept are unchanged).",
               "end_utc": end_utc, "recorded_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "recorded_et": now.astimezone(ET).strftime("%a %b %-d %Y, %-I:%M %p %Z"),
               "responses": resp}, open(out_path, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"recorded {len(resp)} answer(s) to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
