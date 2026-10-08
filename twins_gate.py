#!/usr/bin/env python3
"""
twins_gate.py: the newsroom's own text yields to the snapshot (Jack, 6 October 2026,
ruling 2d, and the two extensions of the October 6 Edition's read).

Three checks, each on OUR text only, each against the ONE snapshot at the run's stamp:

  1. A BITCOIN DOLLAR FIGURE in the narrative line, the checked note, a wire line or the
     Brief's lead line agrees with the snapshot's Bitcoin price within 1%, or the figure is
     dropped and the drop logged with both numbers.
  2. A WEEK OR MONTH FIGURE for a Board coin is the snapshot's own series figure (the stored
     daily closes, snapshot.series_windows), or it is dropped and logged the same way. The
     markets read's percentage fields are never a source for our text.
  3. A DIRECTION WORD (positive, negative, inflow, outflow, rising, falling) about a Board
     reading matches the snapshot's sign, or the sentence is dropped and logged.

What is dropped is the sentence that carries the figure or the word: the smallest unit that
leaves grammatical text behind (the part is not the whole). The Board is never touched, a
linked source keeps its own figure, and a board is never reverted to protect a sentence:
consistency_gate no longer withholds one.

Every drop is printed as one log line and appended to out/twins-gate.json for the run, so
the ledger and the close can name each one.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "out", "twins-gate.json")

TOLERANCE_PCT = 1.0

# ---- 1. the Bitcoin dollar figure -------------------------------------------------------
_BTC_USD = re.compile(
    r"\b(?:bitcoin|btc)\b([^.$]{0,60}?)\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,6}(?:\.\d+)?)"
    r"(\s?[kK]\b)?", re.I)
# A dollar figure named as something other than the price now: a high, a low, an average,
# a level the past held. Those are true of their own window and the gate does not read them.
_NOT_PRICE = re.compile(r"\b(high|low|peak|record|average|sma|moving|200-day|50-day|"
                        r"all-time|ath|since|from|target|level of|in 20\d\d|last year|"
                        r"a year ago|cap|capitali[sz]ation|inflows?|outflows?|worth of|"
                        r"million|billion)\b", re.I)

# ---- 2. week and month figures ------------------------------------------------------------
_COINS = [("BTC", r"bitcoin|btc"), ("ETH", r"ether(?:eum)?|eth"), ("SOL", r"solana|sol"),
          ("XRP", r"xrp"), ("BNB", r"bnb"), ("DOGE", r"dogecoin|doge"),
          ("ADA", r"cardano|ada")]
_COIN_RE = re.compile(r"\b(" + "|".join(p for _, p in _COINS) + r")\b", re.I)
_WINDOW = r"(week|seven days|7 days|7-day|seven-day|month|thirty days|30 days|30-day|thirty-day)"
_PCT_WINDOW = re.compile(
    r"\b(up|down|rose|fell|gained|lost|higher|lower|added|shed)?\s*([+\-−]?)\s*"
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:on|over|for|in|across|this)?\s*(?:the|a|its)?\s*"
    r"(?:past|last|latest)?\s*" + _WINDOW + r"\b", re.I)
_WINDOW_PCT = re.compile(
    r"\b(?:the\s+)?(week|weekly|7-day|seven-day|month|monthly|30-day|thirty-day)\s+"
    r"(?:gain|change|move|rise|decline|drop|loss|return)\s+(?:of|was|is|at|to)?\s*"
    r"([+\-−]?)(\d+(?:\.\d+)?)\s*(?:%|percent)", re.I)

# ---- 3. direction words --------------------------------------------------------------------
_DIR_WORDS = re.compile(r"\b(positive|negative|inflows?|outflows?|rising|falling)\b", re.I)
# Each Board reading the snapshot carries a sign for: its context words and what a positive
# value means. Whale net is measured off exchanges, so an "inflow" (onto exchanges) is the
# negative side, as the whale board prints it.
_READINGS = [
    ("whale net", r"\bwhales?\b|\bexchange (?:net)?flows?\b|\bexchange balances?\b",
     {"positive": 1, "negative": -1, "outflow": 1, "outflows": 1, "inflow": -1,
      "inflows": -1, "rising": 1, "falling": -1}),
    ("spot ETF net", r"\betfs?\b|\bexchange-traded\b",
     {"positive": 1, "negative": -1, "inflow": 1, "inflows": 1, "outflow": -1,
      "outflows": -1, "rising": 1, "falling": -1}),
    ("funding", r"\bfunding\b",
     {"positive": 1, "negative": -1, "rising": 1, "falling": -1}),
    ("stablecoin float", r"\bstablecoin (?:float|supply)\b|\bstablecoin\b",
     {"positive": 1, "negative": -1, "inflow": 1, "inflows": 1, "outflow": -1,
      "outflows": -1, "rising": 1, "falling": -1}),
    ("total market cap", r"\b(?:total )?market cap(?:itali[sz]ation)?\b",
     {"positive": 1, "negative": -1, "rising": 1, "falling": -1}),
    ("Bitcoin price", r"\bbitcoin\b|\bbtc\b",
     {"positive": 1, "negative": -1, "rising": 1, "falling": -1}),
]
_WEEK_WORDS = re.compile(r"\b(week|weekly|seven days|7 days|7-day|five sessions?)\b", re.I)
_MONTH_WORDS = re.compile(r"\b(month|monthly|30 days|30-day)\b", re.I)


def sentences(text):
    """Split prose into sentences, keeping each one's own terminal punctuation. A period
    inside a number ($85,456.00, 1.3%) is not a boundary."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", (text or "").strip())
    return [p for p in parts if p.strip()]


def _num(s):
    return float(str(s).replace(",", ""))


def _sign(v):
    return 1 if v > 0 else -1 if v < 0 else 0


def readings(snap):
    """{reading: (signed value, label)} from the snapshot at its stamp."""
    import snapshot as _s
    out = {}
    w = _s.value(snap, "whale_net") or {}
    if isinstance(w.get("net_usd"), (int, float)):
        out["whale net"] = (w["net_usd"], f"whale net {w['net_usd']:+,.0f} USD")
    e = (_s.value(snap, "etf_flows") or {}).get("btc") or {}
    if isinstance(e.get("latest_net_usd_m"), (int, float)):
        out["spot ETF net"] = (e["latest_net_usd_m"],
                               f"BTC spot ETF net {e['latest_net_usd_m']:+,.1f}M USD "
                               f"({e.get('latest_date')})")
    f = (_s.value(snap, "funding") or {}).get("BTC") or {}
    if isinstance(f.get("funding_8h_pct"), (int, float)):
        out["funding"] = (f["funding_8h_pct"], f"BTC funding {f['funding_8h_pct']:+.4f}% per 8h")
    st = _s.value(snap, "stablecoin_float") or {}
    if isinstance(st.get("change_30d_pct"), (int, float)):
        out["stablecoin float"] = (st["change_30d_pct"],
                                   f"stablecoin float {st['change_30d_pct']:+.2f}% over 30 days")
    cap = _s.value(snap, "total_cap") or {}
    if isinstance(cap.get("chg_24h_pct"), (int, float)):
        out["total market cap"] = (cap["chg_24h_pct"],
                                   f"total market cap {cap['chg_24h_pct']:+.2f}% 24h")
    b = _s.coin(snap, "BTC")
    if isinstance(b.get("chg_24h_pct"), (int, float)):
        out["Bitcoin price"] = (b["chg_24h_pct"], f"Bitcoin {b['chg_24h_pct']:+.2f}% 24h")
    return out


class Gate:
    """One run's gate. `snap` is the snapshot at the run's stamp; `log` collects drops."""

    def __init__(self, snap, log_path=None, quiet=False):
        import snapshot as _s
        self.snap = snap or {}
        self.stamp = self.snap.get("stamp_utc") or ""
        self.btc = _s.coin(self.snap, "BTC").get("price")
        self.read = readings(self.snap)
        self.drops = []
        self.log_path = log_path if log_path is not None else LOG_PATH
        self.quiet = quiet

    # -- the three checks on one sentence; each returns a reason or "" ------------------
    def _dollar(self, s):
        if not isinstance(self.btc, (int, float)) or not self.btc:
            return ""
        for m in _BTC_USD.finditer(s):
            if _NOT_PRICE.search(m.group(1) or ""):
                continue
            stated = _num(m.group(2)) * (1000 if m.group(3) else 1)
            if stated < 1000:
                continue
            pct = (stated - self.btc) / self.btc * 100.0
            if abs(pct) > TOLERANCE_PCT:
                return (f"Bitcoin ${stated:,.2f} in our text against the snapshot's "
                        f"${self.btc:,.2f} ({pct:+.2f}%, over {TOLERANCE_PCT:g}%)")
        return ""

    def _coin_before(self, s, pos):
        last = None
        for m in _COIN_RE.finditer(s[:pos]):
            last = m
        if not last:
            return None
        word = last.group(1).lower()
        for sym, pat in _COINS:
            if re.fullmatch(pat, word, re.I):
                return sym
        return None

    def _window(self, s):
        import snapshot as _s
        hits = []
        for m in _PCT_WINDOW.finditer(s):
            verb, sign, val, win = m.group(1), m.group(2), m.group(3), m.group(4)
            hits.append((m.start(), verb, sign, val, win))
        for m in _WINDOW_PCT.finditer(s):
            hits.append((m.start(), None, m.group(2), m.group(3), m.group(1)))
        for pos, verb, sign, val, win in hits:
            sym = self._coin_before(s, pos)
            if not sym:
                continue                 # a figure no Board coin owns is not this check's
            which = "30d" if re.search(r"month|30|thirty", win, re.I) else "7d"
            series = _s.series_window(self.snap, sym, which)
            stated = _num(val)
            neg = (sign in ("-", "−")) or (verb or "").lower() in (
                "down", "fell", "lost", "lower", "shed")
            stated = -stated if neg else stated
            label = "week" if which == "7d" else "month"
            if not isinstance(series, (int, float)):
                return (f"{sym} {stated:+.2f}% on the {label} in our text; the snapshot's "
                        f"series carries no {label} figure, so ours is not the series'")
            places = len(val.split(".")[1]) if "." in val else 0
            if abs(stated - series) > 0.5 * 10 ** (-places) + 1e-9:
                return (f"{sym} {stated:+.2f}% on the {label} in our text against the "
                        f"snapshot series' {series:+.2f}%")
        return ""

    def _direction(self, s):
        low = s.lower()
        ctx = []
        for name, pat, words in _READINGS:
            for m in re.finditer(pat, low):
                ctx.append((m.start(), m.end(), name, words))
        if not ctx:
            return ""
        for dm in _DIR_WORDS.finditer(low):
            word = dm.group(1).lower()
            near = [c for c in ctx if word in c[3]]
            if not near:
                continue
            c = min(near, key=lambda c: min(abs(dm.start() - c[1]), abs(c[0] - dm.end())))
            name, words = c[2], c[3]
            if name == "Bitcoin price" and (_WEEK_WORDS.search(low) or _MONTH_WORDS.search(low)):
                import snapshot as _s
                which = "30d" if _MONTH_WORDS.search(low) else "7d"
                v = _s.series_window(self.snap, "BTC", which)
                if not isinstance(v, (int, float)):
                    continue
                label = f"Bitcoin {v:+.2f}% series {'month' if which == '30d' else 'week'}"
            elif name == "spot ETF net" and _WEEK_WORDS.search(low):
                continue                 # the snapshot carries the day's net, not the week's
            elif name == "funding":
                # FUNDING IS PER COIN (7 October 2026): the first cut read every funding
                # sentence against Bitcoin's and dropped a true one about Ether. The coin
                # named nearest before the context word owns it; Bitcoin when none is.
                import snapshot as _s
                sym = self._coin_before(low, c[0]) or "BTC"
                f = (_s.value(self.snap, "funding") or {}).get(sym) or {}
                v = f.get("funding_8h_pct")
                if not isinstance(v, (int, float)):
                    continue
                label = f"{sym} funding {v:+.4f}% per 8h"
            else:
                if name not in self.read:
                    continue
                v, label = self.read[name]
            want = words[word]
            if _sign(v) and _sign(v) != want:
                return (f"'{dm.group(1)}' about {name} in our text while the snapshot "
                        f"reads {label}")
        return ""

    # -- apply ---------------------------------------------------------------------------
    def text(self, text, surface, dollars=True, pct=True, direction=True):
        """`text` with every failing sentence dropped. Returns the kept text ('' when
        every sentence failed)."""
        kept = []
        for s in sentences(text):
            why = ((dollars and self._dollar(s)) or (pct and self._window(s))
                   or (direction and self._direction(s)))
            if why:
                self._log(surface, s, why)
            else:
                kept.append(s)
        return " ".join(kept)

    def paragraphs(self, paras, surface, **kw):
        out = []
        for i, p in enumerate(paras or []):
            t = self.text(p, f"{surface} paragraph {i + 1}", **kw)
            if t.strip():
                out.append(t)
        return out

    def _log(self, surface, sentence, why):
        rec = {"surface": surface, "dropped": sentence, "why": why, "stamp_utc": self.stamp}
        self.drops.append(rec)
        if not self.quiet:
            print(f"twins gate: dropped from {surface}: {why}; at the snapshot's stamp "
                  f"{self.stamp}: \"{sentence[:140]}\"")

    def save(self):
        """Append this gate's drops to the run's log file (out/twins-gate.json)."""
        if not self.log_path:
            return
        try:
            prev = json.load(open(self.log_path, encoding="utf-8"))
        except Exception:
            prev = {"drops": []}
        prev.setdefault("drops", []).extend(self.drops)
        prev["stamp_utc"] = self.stamp
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        json.dump(prev, open(self.log_path, "w", encoding="utf-8"), indent=1)


def current_snapshot():
    """The snapshot of this run's own reads: the same function over the two files the
    run's market_pulse and whale_flows just wrote, never a file a previous build left."""
    import snapshot as _s
    d = os.path.join(HERE, "site", "data")

    def _j(n):
        p = os.path.join(d, n)
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None
    return _s.build(_j("pulse.json"), _j("flows.json"))
