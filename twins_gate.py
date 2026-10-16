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

SPRINT 7.3 (13 October 2026; Jack's two rulings). The gate's promise is fact-based and no hype,
so a true sentence is never cut and a false pairing never prints: the gate catches wrong claims,
it does not thin out right ones. Seven sentences of 9 and 10 October were cut and all seven were
true. The five causes, fixed here:
  1. a hyphenated window ("five-session", "seven-day", "24-hour") is a window (WINDOW_RE);
  2. a direction word binds to the subject it modifies, not the nearest coin name: a clause is
     read as a unit, "funding" or "ETF flows" beats a coin named beside them, and the coin names
     in the clause are each checked for funding (bind_reading);
  3. a sentence may carry several windows, each bound to its own direction word (the nearest one
     in its clause) and each claim checked against its own window only;
  4. a short quoted word ("a word like "rising"") is mentioned, not claimed;
  5. "falling" and its kin are sign words, so "falling 2.3% on the week" is -2.3%.
A claim in a window the snapshot does not carry (a five-session ETF net, a seven-day whale
net) is UNVERIFIABLE, not wrong, and stands. A sentence the gate cannot parse (an odd number of
quotation marks around a direction word, or a check that raises) is dropped LOUDLY: kind
"unparsed", its reason in the log, and the count in the night's report (Jack, ruling 2).
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
# a level the past held, a line crossed ("below $82,000", 15 Oct: it cost Bitcoin's coin page its
# only wire item). Those are true of their own window and the gate does not read them.
_NOT_PRICE = re.compile(r"\b(high|low|peak|record|average|sma|moving|200-day|50-day|"
                        r"all-time|ath|since|from|target|level of|in 20\d\d|last year|"
                        r"a year ago|cap|capitali[sz]ation|inflows?|outflows?|worth of|"
                        r"million|billion|below|above|under|beneath|over|past)\b", re.I)

# ---- 2. week and month figures ------------------------------------------------------------
_COINS = [("BTC", r"bitcoin|btc"), ("ETH", r"ether(?:eum)?|eth"), ("SOL", r"solana|sol"),
          ("XRP", r"xrp"), ("BNB", r"bnb"), ("DOGE", r"dogecoin|doge"),
          ("ADA", r"cardano|ada")]
_COIN_RE = re.compile(r"\b(" + "|".join(p for _, p in _COINS) + r")\b", re.I)
_WINDOW = r"(week|seven days|7 days|7-day|seven-day|month|thirty days|30 days|30-day|thirty-day)"
# SIGN WORDS (Sprint 7.3): the verb or participle just before a figure gives it its sign.
# "falling 2.3% on the week" is -2.3, not +2.3 (10 October).
_NEG_VERBS = ("down", "fell", "falling", "lost", "losing", "lower", "shed", "shedding", "dropped",
              "dropping", "declined", "declining", "slid", "sliding", "slipped", "slipping",
              "sank", "sinking", "retreated", "retreating", "sagged", "slumped", "tumbled",
              "dipped", "dipping", "eased", "easing", "off")
_POS_VERBS = ("up", "rose", "rising", "gained", "gaining", "higher", "added", "adding",
              "climbed", "climbing", "advanced", "advancing", "jumped", "rallied", "surged",
              "risen")
_SIGN_VERB = "|".join(_NEG_VERBS + _POS_VERBS)
_PCT_WINDOW = re.compile(
    r"\b(" + _SIGN_VERB + r")?\s*([+\-−]?)\s*"
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
    ("whale net", r"\bwhales?\b|\bexchange[- ](?:net|in|out)?flows?\b|\bexchange balances?\b",
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
# ---- windows -----------------------------------------------------------------------------------
_NUMWORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fourteen": 14, "twenty four": 24,
            "twenty-four": 24, "thirty": 30, "sixty": 60, "ninety": 90}
_NUM = r"\d+|twenty[- ]four|" + "|".join(k for k in _NUMWORD if " " not in k and "-" not in k)
# One scan over the (lower-cased) sentence; the alternatives are tried left to right so the
# hyphenated and numbered forms win over the bare word inside them ("seven-day" is one window,
# not "day"; "multi-week" is not "week").
WINDOW_RE = re.compile(
    r"(?P<multi>\bmulti[- ](?:day|week|month|session)s?\b)"
    r"|\b(?P<n>" + _NUM + r")[- ](?P<unit>sessions?|days?|weeks?|months?|hours?|hrs?)\b"
    r"|(?P<long>\bytd\b|\byear[- ]to[- ]date\b|\bcumulative\b|\b(?:this|last) year\b)"
    r"|(?P<week>\bweek(?:ly|s)?\b|\bweek['’]s\b)"
    r"|(?P<month>\bmonth(?:ly|s)?\b)"
    r"|(?P<day>\bdaily\b|\bday['’]s\b|\bday\b|\btoday\b|\bintraday\b|\bovernight\b"
    r"|\byesterday\b|\bsession\b)"
    r"|(?P<plural>\bsessions\b|\bdays\b)")


def _winnum(s):
    s = str(s).lower().replace(",", "")
    return float(_NUMWORD[s] if s in _NUMWORD else _NUMWORD.get(s.replace(" ", "-"), s))


def _win_class(n, unit):
    u = unit.rstrip("s")
    if u in ("hour", "hr"):
        return "day" if n <= 24 else "other"
    if u == "day":
        return "day" if n == 1 else "week" if n == 7 else "month" if n in (30, 31) else "other"
    if u == "week":
        return "week" if n == 1 else "other"
    if u == "month":
        return "month" if n == 1 else "other"
    return "day" if n == 1 else "other"            # session(s)


def windows(text):
    """[(start, end, class)] for every window phrase in `text`; class is day, week, month or
    other (a window the snapshot does not carry: five sessions, multi-week, year to date)."""
    out = []
    for m in WINDOW_RE.finditer(text):
        if m.group("n"):
            out.append((m.start(), m.end(), _win_class(_winnum(m.group("n")), m.group("unit"))))
        elif m.group("day"):
            out.append((m.start(), m.end(), "day"))
        elif m.group("week"):
            out.append((m.start(), m.end(), "week"))
        elif m.group("month"):
            out.append((m.start(), m.end(), "month"))
        else:
            out.append((m.start(), m.end(), "other"))
    return out


# What window each Board reading is in. A claim in another window cannot be checked against it.
_NATIVE = {"whale net": {"day"}, "spot ETF net": {"day"}, "funding": {"day"},
           "stablecoin float": {"day", "month"}, "total market cap": {"day"},
           "Bitcoin price": {"day", "week", "month"}}

# ---- clauses, quotes, binding ----------------------------------------------------------------
_BREAK = re.compile(r"[;:\u2014\u2013]|,\s|\s-\s|\b(?:while|whereas|although|though|but|as|yet|with|"
                    r"alongside|against|versus|despite)\b")
_QUOTE_SHORT = re.compile(r'"([^"]{1,40})"|“([^”]{1,40})”')
# a verb that makes the direction word a predicate ("funding stayed negative"), so its subject
# is BEFORE it; otherwise "positive"/"rising" is an adjective and modifies what FOLLOWS it
_COPULA = re.compile(r"\b(?:is|are|was|were|be|been|being|stay(?:s|ed)?|remain(?:s|ed)?|"
                     r"turn(?:s|ed)?|stand(?:s)?|stood|sit(?:s)?|sat|read(?:s)?|ran|runs?|"
                     r"look(?:s|ed)?|became|becomes?|got|went|held|holds?|flipp?ed|printed|"
                     r"prints|came|comes|show(?:s|ed)?|print)\s+(?:\w+\s+)?$")
_COIN_READING = "Bitcoin price"


class Unparsed(Exception):
    """A sentence the gate cannot read: it is dropped, loudly (kind "unparsed")."""


def _blank_quoted(low):
    """`low` with every SHORT quoted span (three words or fewer: a word mentioned, not a claim)
    blanked to spaces, so positions stay. An odd number of quotation marks cannot be read."""
    straight = low.count('"')
    if straight % 2 or low.count("“") != low.count("”"):
        raise Unparsed("an odd number of quotation marks around a direction word")

    def blank(m):
        inner = m.group(1) or m.group(2) or ""
        return " " * len(m.group(0)) if len(inner.split()) <= 3 else m.group(0)
    return _QUOTE_SHORT.sub(blank, low)


def _clauses(low):
    """[(start, end)] of the clause spans between the breaks."""
    out, pos = [], 0
    for m in _BREAK.finditer(low):
        out.append((pos, m.start()))
        pos = m.end()
    out.append((pos, len(low)))
    return out


def _clause_of(clauses, pos):
    for i, (a, b) in enumerate(clauses):
        if a <= pos <= b:
            return i
    return len(clauses) - 1


def _tokens_between(low, a_end, b_start):
    lo, hi = (a_end, b_start) if a_end <= b_start else (b_start, a_end)
    return len(low[lo:hi].split())


def bind_reading(low, dm, ctx, clauses):
    """The context entry a direction word modifies, or None. `ctx` is [(start, end, name,
    words)] for the contexts that can take this word. In order:
      1. an adjective ("a positive daily bitcoin print", "rising funding"), when no linking verb
         stands before it, takes the context that FOLLOWS it in its clause, within four tokens;
      2. a predicate or noun takes a Board reading (whale, ETF, funding, stablecoin, total cap)
         in its own clause, before it first, then after it;
      3. a bare coin name in its own clause is the weakest subject: before, then after;
      4. no subject in its own clause (", and a net outflow of $510.1 million"): the nearest
         subject in the clauses before, a Board reading ahead of a coin name."""
    p, e = dm.start(), dm.end()
    ci = _clause_of(clauses, p)
    ca, cb = clauses[ci]
    adj = dm.group(1).lower() in ("positive", "negative", "rising", "falling")
    if adj and not _COPULA.search(low[max(0, p - 28):p]):
        after = [c for c in ctx if c[0] >= e and c[0] <= cb and
                 len(low[e:c[0]].split()) <= 4 and not re.search(r"[,;.]", low[e:c[0]])]
        if after:
            return min(after, key=lambda c: c[0])
    own = [c for c in ctx if ca <= c[0] <= cb]
    reading = [c for c in own if c[2] != _COIN_READING]
    coin = [c for c in own if c[2] == _COIN_READING]
    for pool in (reading, coin):
        before = [c for c in pool if c[0] < p]
        if before:
            return max(before, key=lambda c: c[0])
        after = [c for c in pool if c[0] >= e]
        if after:
            return min(after, key=lambda c: c[0])
    for pi in range(ci - 1, -1, -1):
        pa, pb = clauses[pi]
        prev = [c for c in ctx if pa <= c[0] <= pb]
        if prev:
            r = [c for c in prev if c[2] != _COIN_READING]
            return max(r or prev, key=lambda c: c[0])
    return None


def _owner(low, clauses, dirs, ws, we):
    """The direction word (its start) that the window [ws, we) belongs to: the nearest one in the
    window's own clause by tokens between, a tie going to the word after the window. None when
    the window's clause has no direction word."""
    wc = _clause_of(clauses, ws)
    cands = [d for d in dirs if _clause_of(clauses, d[0]) == wc]
    if not cands:
        return None
    return min(cands, key=lambda d: (_tokens_between(low, we, d[0]) if d[0] >= we
                                     else _tokens_between(low, d[1], ws),
                                     0 if d[0] >= we else 1))[0]


def window_for(low, dpos, dend, dirs, clauses, wins):
    """The class of the window bound to the direction word at [dpos, dend); `dirs` is every
    direction word's (start, end). A window belongs to the nearest direction word in its own
    clause; a window in a clause with no direction word ("over the week," / ", over five
    sessions") goes to the nearest direction word that has none of its own. No window means the
    day. Two windows in one sentence are each bound to their own word, so each claim is checked
    against its own window only."""
    owner = {ws: _owner(low, clauses, dirs, ws, we) for ws, we, _c in wins}
    owned = {o for o in owner.values() if o is not None}
    mine = [w for w in wins if owner[w[0]] == dpos]
    if not mine and dpos not in owned:
        for ws, we, cls in wins:
            if owner[ws] is None:
                free = [d for d in dirs if d[0] not in owned]
                if free and min(free, key=lambda d: abs(d[0] - ws))[0] == dpos:
                    mine.append((ws, we, cls))
    if not mine:
        return "day"
    near = min(mine, key=lambda w: _tokens_between(low, w[1], dpos) if dpos >= w[1]
               else _tokens_between(low, dend, w[0]))
    return near[2]


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
    e2 = (_s.value(snap, "etf_flows") or {}).get("eth") or {}
    if isinstance(e2.get("latest_net_usd_m"), (int, float)):
        out["spot ETF net (ETH)"] = (e2["latest_net_usd_m"],
                                     f"ETH spot ETF net {e2['latest_net_usd_m']:+,.1f}M USD "
                                     f"({e2.get('latest_date')})")
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
        self.repairs = []
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
            neg = (sign in ("-", "−")) or (verb or "").lower() in _NEG_VERBS
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
        import snapshot as _s
        low = s.lower()
        if not _DIR_WORDS.search(low):
            return ""
        mask = _blank_quoted(low)             # raises Unparsed on an odd number of quotes
        dms = list(_DIR_WORDS.finditer(mask))
        if not dms:
            return ""                         # the only direction words were quoted words
        ctx = []
        for name, pat, words in _READINGS:
            for m in re.finditer(pat, mask):
                ctx.append((m.start(), m.end(), name, words))
        if not ctx:
            return ""
        clauses = _clauses(mask)
        wins = windows(mask)
        dirs = [(m.start(), m.end()) for m in dms]
        for dm in dms:
            word = dm.group(1).lower()
            c = bind_reading(mask, dm, [c for c in ctx if word in c[3]], clauses)
            if c is None:
                continue                      # no reading it modifies: not this check's
            name, words = c[2], c[3]
            win = window_for(mask, dm.start(), dm.end(), dirs, clauses, wins)
            if name == _COIN_READING and win in ("week", "month"):
                v = _s.series_window(self.snap, "BTC", "30d" if win == "month" else "7d")
                if not isinstance(v, (int, float)):
                    continue
                label = f"Bitcoin {v:+.2f}% series {'month' if win == 'month' else 'week'}"
            elif win not in _NATIVE.get(name, {"day"}):
                continue          # a window the snapshot does not carry: unverifiable, not wrong
            elif name == "funding":
                # FUNDING IS PER COIN (7 October 2026), and every coin the clause names owns
                # the word (13 October): "negative for bitcoin and ethereum" is read against
                # both. A coin named before the word owns it, as before; Bitcoin when none is.
                ca, cb = clauses[_clause_of(clauses, c[0])]
                syms = []
                for m in _COIN_RE.finditer(mask[c[1]:cb]):
                    syms.append(self._sym(m.group(1)))
                pre = self._coin_before(mask, c[0])
                if pre:
                    syms.insert(0, pre)
                syms = list(dict.fromkeys(x for x in syms if x)) or ["BTC"]
                for sym in syms:
                    f = (_s.value(self.snap, "funding") or {}).get(sym) or {}
                    v = f.get("funding_8h_pct")
                    if not isinstance(v, (int, float)):
                        continue
                    label = f"{sym} funding {v:+.4f}% per 8h"
                    want = words[word]
                    if _sign(v) and _sign(v) != want:
                        return (f"'{dm.group(1)}' about {name} in our text while the "
                                f"snapshot reads {label}")
                continue
            else:
                # AN ETF SENTENCE IS ABOUT ONE ASSET'S FUNDS (13 October 2026): the clause that
                # names the ETFs says whose. "Ethereum ETFs show ... a $16.7 million net inflow"
                # is read against the ETH net, never Bitcoin's; both named is not one sign,
                # so it stands unverified.
                if name == "spot ETF net":
                    ca, cb = clauses[_clause_of(clauses, c[0])]
                    seg = mask[ca:cb]
                    eth = re.search(r"\b(?:ether(?:eum)?|eth)\b", seg)
                    btc = re.search(r"\b(?:bitcoin|btc)\b", seg)
                    if eth and btc:
                        continue
                    if eth:
                        name = "spot ETF net (ETH)"
                if name not in self.read:
                    continue
                v, label = self.read[name]
            want = words[word]
            if _sign(v) and _sign(v) != want:
                return (f"'{dm.group(1)}' about {name} in our text while the snapshot "
                        f"reads {label}")
        return ""

    @staticmethod
    def _sym(word):
        for sym, pat in _COINS:
            if re.fullmatch(pat, word.lower(), re.I):
                return sym
        return None

    def _fix_window_signs(self, s):
        """(text, notes): a week or month figure that IS the snapshot series' figure in size but
        stands without any sign word of its own gets the series' word.

        14 October, 7:46 PM: "Ethereum fell 3.36 percent on the day and 7.44 percent over the
        week" put one direction word in front of two figures; the gate read the second as +7.44
        against the series' -7.44 and dropped the sentence, which was true. The figure is the
        snapshot's own to the digit, so only its word is missing, and the word is a fact the
        snapshot already holds. A word that is there and wrong ("falling 2.3%" against +2.30,
        TN5) is a wrong claim, and a figure whose size is not the series' is one too: the check
        below drops both, logged. Nothing here turns a wrong claim into a right one."""
        import snapshot as _s
        notes, edits = [], []
        for m in _PCT_WINDOW.finditer(s):
            verb, sign, val, win = m.group(1), m.group(2), m.group(3), m.group(4)
            sym = self._coin_before(s, m.start())
            if not sym:
                continue
            which = "30d" if re.search(r"month|30|thirty", win, re.I) else "7d"
            series = _s.series_window(self.snap, sym, which)
            if not isinstance(series, (int, float)) or not series:
                continue
            places = len(val.split(".")[1]) if "." in val else 0
            if abs(abs(series) - _num(val)) > 0.5 * 10 ** (-places) + 1e-9:
                continue
            if verb or sign:
                continue          # a sign word that is there and wrong is a wrong claim: dropped, logged
            word = "down" if series < 0 else "up"
            edits.append((m.start(3), m.start(3), word + " "))
            notes.append(f"{sym} {val}% on the {'week' if which == '7d' else 'month'}: "
                         f"no sign word, so '{word}' (the snapshot series' {series:+.2f}%)")
        for a, b, w in sorted(edits, reverse=True):
            s = s[:a] + w + s[b:]
        return s, notes

    # -- apply ---------------------------------------------------------------------------
    def text(self, text, surface, dollars=True, pct=True, direction=True):
        """`text` with every failing sentence dropped. Returns the kept text ('' when
        every sentence failed). A sentence the gate cannot read is dropped as kind
        "unparsed" with its reason, never silently (Jack, 13 October 2026, ruling 2)."""
        kept = []
        for s in sentences(text):
            kind = "wrong"
            if pct:
                try:
                    s, notes = self._fix_window_signs(s)
                except Exception:
                    notes = []
                for n in notes:
                    self._repair(surface, s, n)
            try:
                why = ((dollars and self._dollar(s)) or (pct and self._window(s))
                       or (direction and self._direction(s)))
            except Unparsed as e:
                why, kind = f"unparsed: {e}", "unparsed"
            except Exception as e:
                why, kind = f"unparsed: {type(e).__name__}: {e}", "unparsed"
            if why:
                self._log(surface, s, why, kind)
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

    @property
    def unparsed(self):
        return sum(1 for d in self.drops if d.get("kind") == "unparsed")

    def report(self):
        """The night's one-line count: wrong claims dropped and unparsed sentences dropped."""
        n = len(self.drops)
        return (f"twins gate: {n} sentence(s) dropped, {n - self.unparsed} wrong claim(s) and "
                f"{self.unparsed} unparsed")

    def _repair(self, surface, sentence, note):
        """A sign word set to the snapshot's own: counted, printed, kept in the run's log."""
        self.repairs.append({"surface": surface, "kept": sentence, "repair": note,
                             "stamp_utc": self.stamp})
        if not self.quiet:
            print(f"twins gate: set a sign word in {surface}: {note}")

    def _log(self, surface, sentence, why, kind="wrong"):
        rec = {"surface": surface, "dropped": sentence, "why": why, "kind": kind,
               "stamp_utc": self.stamp}
        self.drops.append(rec)
        if not self.quiet:
            tag = " [UNPARSED, dropped loudly]" if kind == "unparsed" else ""
            print(f"twins gate: dropped from {surface}{tag}: {why}; at the snapshot's stamp "
                  f"{self.stamp}: \"{sentence[:140]}\"")
            if kind == "unparsed":
                print(f"::warning::twins gate: could not parse a sentence in {surface} "
                      f"({why[:120]}); dropped and counted")

    def save(self):
        """Append this gate's drops to the run's log file (out/twins-gate.json)."""
        if not self.log_path:
            return
        try:
            prev = json.load(open(self.log_path, encoding="utf-8"))
        except Exception:
            prev = {"drops": []}
        prev.setdefault("drops", []).extend(self.drops)
        if self.repairs:
            prev.setdefault("repairs", []).extend(self.repairs)
        prev["stamp_utc"] = self.stamp
        prev["counts"] = counts(prev["drops"])
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        json.dump(prev, open(self.log_path, "w", encoding="utf-8"), indent=1)


def log_drop(surface, sentence, why, stamp="", kind="wrong", path=None):
    """Append one drop made OUTSIDE a Gate (the Edition's ETF floor, Sprint 8.1) to the run's log
    file, in the same shape a Gate writes, so the ops ledger counts and names it."""
    path = path if path is not None else LOG_PATH
    rec = {"surface": surface, "dropped": sentence, "why": why, "kind": kind, "stamp_utc": stamp}
    try:
        prev = json.load(open(path, encoding="utf-8"))
    except Exception:
        prev = {"drops": []}
    prev.setdefault("drops", []).append(rec)
    prev["counts"] = counts(prev["drops"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(prev, open(path, "w", encoding="utf-8"), indent=1)
    print(f"twins gate: dropped from {surface}: {why}: \"{sentence[:140]}\"")
    return rec


def counts(drops):
    """{"wrong": n, "unparsed": n} over a log's drops (a drop with no kind is a wrong claim)."""
    u = sum(1 for d in drops if d.get("kind") == "unparsed")
    return {"wrong": len(drops) - u, "unparsed": u}


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
