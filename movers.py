#!/usr/bin/env python3
"""
movers.py: Big movers, checked (Program 9, Sprint 9.4; AUDIT.md section 3.1, the row "Any top-100 coin",
and section 3.2).

THE GATE, the audit's line, held once in GATE below:
  a top-100 coin's 24-hour move of 10% or more, AND at least 2.5 times its own 30-day daily volatility,
  AND at least 6 points beyond what Bitcoin's move predicts for it (its 30-day beta). Stablecoins never;
  a rank over 100 never (9.1's rules, snapshot.MOVER_RANK_MAX and snapshot.is_stablecoin). Bitcoin and
  Ether are graded by their own cards (verdict.py) and are not read twice here. At most 8 a slot and 10
  an Eastern day, ranked by the volatility multiple.

THE HISTORY is the desk's own stored daily closes (data/history/<coin id>.json, history.py). The
volatility and the beta read the 31 stored closes before the window's Eastern day (30 daily returns), the
same days why_evidence._beta reads, so the beta the section prints is the gate's. A coin without those 31
consecutive closes is left out and said, never estimated. A coin past 10% that has no stored series is
bootstrapped through history.update (a real CoinGecko read, stored), at most BOOTSTRAPS_PER_RUN a run.

THE LOG: for two weeks from the gate's first run (through LOG_UNTIL), every coin that passes one leg of
the gate and fails another prints in the run log with its three figures, so Jack can move the line on
evidence.

THE EVIDENCE for each mover is 9.2's (why_evidence.coin_entry): its intraday series over the Board's 24
hours, the timing test, the onset hour's readings and the hour after each candidate. Its candidates are
the alt feeds and the wire items that NAME THE COIN (by its name, or its ticker when the ticker has three
or more letters); a market-wide event is Bitcoin's card's, and the gate already requires the move to be
6 points beyond what Bitcoin's move gives this coin.
  exchange listing and delisting notices  Binance, OKX, KuCoin, Bitget (their public announcement APIs)
                                          and Kraken (its blog feed, "is available for trading")
  token unlocks                           CoinMarketCap's token-unlock events (past events, with times)
  hacks and exploits                      DefiLlama's hack list (also 9.2's), matched to the coin by name
  the wire                                site/data/wire.json, the items that name the coin
A venue's series is kept only when its move over the window agrees with the Board's 24-hour figure
within AGREE_PTS: a ticker is a shallow key, and two coins can share one.

THE VERDICT is 9.3's (verdict.py), under the strategist's rulings of October 19: the grade in code, the
two sentences by Haiku 5.5 checked by Sonnet 5.5, every attempt reserved against the same $1.50 day cap in
data/verdict-ledger.json before it is made. A mover's window is the rolling 24 hours the gate measured
(basis rolling_24h, "over the last 24 hours"), named on its card.

THE PAGES: the card and the section on the coin's page while the record is current, the Big movers list
on /pulse/movers, and /why/<date>-<coin id> for each graded verdict, in the news and archive sitemaps.
A URL, once written, keeps its slug: the page carries the day's newest graded verdict for that coin.

    python3 movers.py --write        # the run's step, after verdict.py; exits 0 whatever happens
    python3 movers.py --record PULSE WIRE HISTORY_ANSWERS OUT   # record a real day's answers as a fixture
"""
import datetime as _dt
import html as _html
import json
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "site", "data", "movers")

# THE LINE, one versioned constant (AUDIT.md 3.1, "Any top-100 coin"; 3.2, "How many"). Jack moves it.
GATE = {"version": "2026-10-19", "source": "AUDIT.md section 3.1, the row 'Any top-100 coin', and section 3.2",
        "move_min_pct": 10.0, "vol_multiple_min": 2.5, "excess_min_pts": 6.0, "history_days": 30,
        "per_slot": 8, "per_day": 10}
LOG_UNTIL = "2026-11-02"        # two weeks from the gate's first live run, Monday October 19, 2026
OWN_CARD = ("BTC", "ETH")       # graded by verdict.py every slot
# A CRASH DAY, by the audit's own numbers (AUDIT.md 3.1, the row "Breaking": Bitcoin or the whole market 5% or more
# inside 24 hours; 3.2, "How many": crash days ran to 25 to 50 top-100 coins past 10%). On such a day, when most of
# the coins past 10% that the gate measured fail its beta leg (they moved within 6 points of what Bitcoin's move
# gives them), the Big movers section says once that they moved with the market, and points at Bitcoin's verdict.
CRASH = {"btc_or_market_pct": 5.0, "coins_past_move": 25}
BOOTSTRAPS_PER_RUN = 4          # history.py bootstraps a coin from a 365-day read; at most this many a run
AGREE_PTS = 3.0                 # a venue's window move within 3 points of the Board's 24-hour figure
HISTORY_BUDGET_S = 45           # the history reads for candidates that lack a stored series
DEADLINE_EVIDENCE_S = 150       # the reads; past it every source not yet read is skipped and named
DEADLINE_S = 300                # the whole step; the workflow's timeout is 360
CG_SPACING_S = 2.5              # keyless CoinGecko: calls this far apart

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-4))


def _we():
    import why_evidence
    return why_evidence


def _vd():
    import verdict
    return verdict


def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ---- the gate ----------------------------------------------------------------------------------------------

def stats(cid, before_day, root=None, days=None):
    """({vol_pct, beta, from, through, days}, None) from the stored closes, or (None, why). The 31 stored
    closes before `before_day` (the window's Eastern day) that the coin and Bitcoin both carry, which must be
    31 consecutive days ending no more than two days before it: 30 daily returns, their sample standard
    deviation in percent, and the beta by why_evidence._beta's own formula on the same days."""
    import history
    days = days or GATE["history_days"]
    a, b = history.load(cid, root), history.load("bitcoin", root)
    if not a:
        return None, "the desk holds no stored daily closes for it"
    if not b:
        return None, "Bitcoin's stored daily closes are missing"
    ca, cb = a["closes"], b["closes"]
    ds = sorted(d for d in ca if d in cb and d < before_day)[-(days + 1):]
    if len(ds) < days + 1:
        return None, f"{len(ds)} stored daily close(s) before {before_day}, under the {days + 1} the gate needs"
    d0 = _dt.date.fromisoformat(ds[0])
    if any(_dt.date.fromisoformat(d) != d0 + _dt.timedelta(days=i) for i, d in enumerate(ds)):
        return None, f"the stored closes from {ds[0]} to {ds[-1]} have a gap"
    if (_dt.date.fromisoformat(before_day) - _dt.date.fromisoformat(ds[-1])).days > 2:
        return None, f"the stored closes end {ds[-1]}, more than two days before {before_day}"
    if any(not _num(ca[d]) or ca[d] <= 0 or not _num(cb[d]) or cb[d] <= 0 for d in ds):
        return None, "a stored close is not a price"
    ra = [ca[ds[i]] / ca[ds[i - 1]] - 1 for i in range(1, len(ds))]
    rb = [cb[ds[i]] / cb[ds[i - 1]] - 1 for i in range(1, len(ds))]
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    var = sum((x - mb) ** 2 for x in rb)
    if not var:
        return None, "Bitcoin's stored closes did not move"
    beta = round(sum((x - mb) * (y - ma) for x, y in zip(rb, ra)) / var, 3)
    vol = statistics.stdev(ra) * 100.0
    if vol <= 0:
        return None, "the coin's stored closes did not move"
    return {"vol_pct": round(vol, 3), "beta": beta, "from": ds[0], "through": ds[-1], "days": days}, None


def eligible(rows):
    """The movers rules (9.1's, on the Board's own list): a row of the desk's Top 100, its place 100 or better in
    the Board's list as the Top 100 page and the coin page number it (review 1: one rank, from one source), never a
    stablecoin, a 24-hour figure the Board carries. Each row comes back with its place as `pos`."""
    import snapshot
    out = []
    for pos, r in enumerate(rows or [], 1):
        if pos <= snapshot.MOVER_RANK_MAX and _num(r.get("chg_24h_pct")) and not snapshot.is_stablecoin(r):
            out.append(dict(r, pos=pos))
    return out


def evaluate(row, btc24, st):
    """The three legs for one coin. Each figure is rounded once, here, and printed as stored."""
    mv = float(row["chg_24h_pct"])
    sign = 1 if mv >= 0 else -1
    mult = abs(mv) / st["vol_pct"]
    pred = st["beta"] * btc24
    excess = mv - pred
    legs = {"move": abs(mv) >= GATE["move_min_pct"],
            "multiple": mult >= GATE["vol_multiple_min"],
            "excess": excess * sign >= GATE["excess_min_pts"]}
    return {"sym": row["symbol"], "name": row.get("name") or row["symbol"], "gecko_id": row.get("gecko_id") or "",
            "rank": row.get("rank"), "pos": row["pos"], "move_pct": round(mv, 2), "vol_pct": round(st["vol_pct"], 2),
            "multiple": round(mult, 2), "beta": st["beta"], "btc_pct": round(btc24, 2),
            "predicted_pct": round(pred, 2), "excess_pts": round(excess, 2), "legs": legs,
            "pass": all(legs.values()), "history": {"from": st["from"], "through": st["through"]}}


def _fail_words(x):
    out = []
    if not x["legs"]["move"]:
        out.append(f"moved {abs(x['move_pct']):.2f}% (needs {GATE['move_min_pct']:g}%)")
    if not x["legs"]["multiple"]:
        out.append(f"{x['multiple']:.2f}x its 30-day daily volatility of {x['vol_pct']:.2f}% "
                   f"(needs {GATE['vol_multiple_min']:g}x)")
    if not x["legs"]["excess"]:
        out.append(f"{x['excess_pts']:+.2f} points beyond its Bitcoin beta of {x['beta']} "
                   f"(needs {GATE['excess_min_pts']:g} the way it moved)")
    return "; ".join(out)


def gate(board, before_day, root=None, used_today=0, now=None):
    """The gate on one Board read. {rule, board_utc, btc_24h_pct, passed, over_cap, failed, left_out,
    own_card, log}. `used_today` is the coin reads the day's earlier records already made."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    rows = ((board or {}).get("movers") or {}).get("top100") or []
    by = {r.get("symbol"): r for r in rows}
    btc = (by.get("BTC") or {}).get("chg_24h_pct")
    out = {"rule": dict(GATE), "board_utc": (board or {}).get("generated_utc"), "before_day": before_day,
           "btc_24h_pct": btc if _num(btc) else None, "passed": [], "over_cap": [], "failed": [],
           "left_out": [], "own_card": [], "log": []}
    log = out["log"]
    if not _num(btc):
        log.append("movers: the Board carries no Bitcoin 24-hour figure; no coin can be measured against its beta")
        return out
    measured = []
    for r in eligible(rows):
        if r["symbol"] in OWN_CARD:
            if abs(r["chg_24h_pct"]) >= GATE["move_min_pct"]:
                out["own_card"].append({"sym": r["symbol"], "move_pct": r["chg_24h_pct"]})
            continue
        st, why = stats(r.get("gecko_id") or "", before_day, root)
        if st is None:
            if abs(r["chg_24h_pct"]) >= GATE["move_min_pct"]:
                out["left_out"].append({"sym": r["symbol"], "name": r.get("name") or r["symbol"],
                                        "gecko_id": r.get("gecko_id") or "", "rank": r.get("rank"), "pos": r["pos"],
                                        "move_pct": r["chg_24h_pct"], "why": why})
            continue
        measured.append(evaluate(r, btc, st))
    passing = sorted([x for x in measured if x["pass"]], key=lambda x: (-x["multiple"], x["pos"]))
    out["crash"] = crash(rows, btc, measured, out["left_out"])
    room = max(0, min(GATE["per_slot"], GATE["per_day"] - int(used_today or 0)))
    out["passed"], out["over_cap"] = passing[:room], passing[room:]
    out["used_today"] = int(used_today or 0)
    out["failed"] = sorted([x for x in measured if not x["pass"] and any(x["legs"].values())],
                           key=lambda x: (-abs(x["move_pct"]), x["pos"]))
    for x in out["passed"]:
        log.append(f"movers: gate PASS {x['sym']} {x['move_pct']:+.2f}%, {x['multiple']:.2f}x its 30-day daily "
                   f"volatility of {x['vol_pct']:.2f}%, {x['excess_pts']:+.2f} points beyond its Bitcoin beta "
                   f"of {x['beta']} (Bitcoin {btc:+.2f}%)")
    for x in out["over_cap"]:
        log.append(f"movers: gate PASS, over the cap ({GATE['per_slot']} a slot, {GATE['per_day']} a day, "
                   f"{int(used_today or 0)} read earlier today): {x['sym']} {x['move_pct']:+.2f}%, "
                   f"{x['multiple']:.2f}x")
    c = out["crash"]
    if c["day"]:
        log.append(f"movers: a crash day by the audit's numbers ({', '.join(c['why'])}): {c['with_market']} of the "
                   f"{c['measured_past_move']} measured coins past {GATE['move_min_pct']:g}% moved with the market")
    for x in out["own_card"]:
        log.append(f"movers: {x['sym']} {x['move_pct']:+.2f}% is graded by its own card, not here")
    for x in out["left_out"]:
        log.append(f"movers: left out {x['sym']} {x['move_pct']:+.2f}%: {x['why']}; never estimated")
    if now.astimezone(ET).date().isoformat() <= LOG_UNTIL:
        for x in out["failed"]:
            log.append(f"movers: gate fail {x['sym']} {x['move_pct']:+.2f}%: {_fail_words(x)}")
    else:
        log.append(f"movers: {len(out['failed'])} coin(s) passed one leg and failed another (the per-coin "
                   f"log ran through {LOG_UNTIL})")
    if not passing:
        log.append(f"movers: no top-100 coin passed the gate ({len(measured)} measured, "
                   f"{len(out['left_out'])} left out for history)")
    return out


def crash(rows, btc24, measured, left_out):
    """{day, why, btc_pct, market_pct, past_move, measured_past_move, with_market}: whether the Board's reading is a
    crash day by CRASH, and how many of the measured coins past 10% moved with the market (failed the beta leg)."""
    import snapshot
    market = snapshot.top100_change({f"{r.get('symbol')}|{i}": r for i, r in enumerate(rows or [])})
    past = [x for x in measured if x["legs"]["move"]]
    n_past = len(past) + len(left_out or [])
    why = []
    if _num(btc24) and abs(btc24) >= CRASH["btc_or_market_pct"]:
        why.append(f"Bitcoin {btc24:+.2f}%")
    if _num(market) and abs(market) >= CRASH["btc_or_market_pct"]:
        why.append(f"the Top 100 {market:+.2f}%")
    if n_past >= CRASH["coins_past_move"]:
        why.append(f"{n_past} top-100 coins past {GATE['move_min_pct']:g}%")
    return {"day": bool(why), "why": why, "btc_pct": btc24 if _num(btc24) else None, "market_pct": market,
            "past_move": n_past, "measured_past_move": len(past),
            # review 2: "within 6 points of what Bitcoin's move gives them" is the absolute excess, either way; a coin
            # that moved far less than its beta gives fails the signed leg too, but is not within 6 points
            "with_market": sum(1 for x in past if abs(x["excess_pts"]) < GATE["excess_min_pts"])}


def bootstrap(board, before_day, fetch, now=None, root=None, limit=BOOTSTRAPS_PER_RUN, log=None,
              spacing=CG_SPACING_S):
    """Bring each coin past the move line up to yesterday in the desk's stored history, so the gate can
    measure it: history.update, a real read stored once (a coin with no file is bootstrapped from 365 days,
    at most `limit` a run). Returns [(sym, status, reason)]. Bitcoin's own series is the Board's to keep."""
    import history
    out, booted = [], 0
    rows = [r for r in eligible(((board or {}).get("movers") or {}).get("top100"))
            if r["symbol"] not in OWN_CARD and abs(r["chg_24h_pct"]) >= GATE["move_min_pct"] and r.get("gecko_id")]
    rows.sort(key=lambda r: -abs(r["chg_24h_pct"]))
    for r in rows:
        st, _why = stats(r["gecko_id"], before_day, root)
        if st is not None:
            continue
        s = history.load(r["gecko_id"], root)
        boot = history.needs_bootstrap(s, now)
        if out and spacing:
            time.sleep(spacing)                          # keyless CoinGecko, one call at a time
        series, status, why = history.update(r["gecko_id"], r["symbol"], fetch, now=now, root=root,
                                             allow_bootstrap=(not boot) or booted < limit)
        if status == "bootstrap":
            booted += 1
        out.append((r["symbol"], status, why))
        if log is not None:
            log.append(f"movers: history for {r['symbol']}: {status}" + (f" ({why})" if why else ""))
    return out


# ---- the alt feeds ----------------------------------------------------------------------------------------

DASHES = re.compile("\\s*[\\u2013\\u2014]\\s*")


def _clean(s):
    return DASHES.sub(", ", " ".join(str(s or "").split()))


def _ms(v):
    try:
        return int(float(v)) // 1000
    except (TypeError, ValueError):
        return None


LISTING_FEEDS = [
    ("Binance new listings", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20", "binance", "listing"),
    ("Binance delistings", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=20", "binance", "delisting"),
    ("OKX new listings", "https://www.okx.com/api/v5/support/announcements?annType=announcements-new-listings", "okx", "listing"),
    ("OKX delistings", "https://www.okx.com/api/v5/support/announcements?annType=announcements-delistings", "okx", "delisting"),
    ("KuCoin new listings", "https://api.kucoin.com/api/v3/announcements?annType=new-listings&pageSize=50", "kucoin", "listing"),
    ("KuCoin delistings", "https://api.kucoin.com/api/v3/announcements?annType=delistings&pageSize=50", "kucoin", "delisting"),
    ("Bitget listings", "https://api.bitget.com/api/v2/public/annoucements?language=en_US&annType=coin_listings", "bitget", "listing"),
    ("Kraken blog (listings)", "https://blog.kraken.com/feed", "kraken", "listing"),
    # review 1: Coinbase Exchange's status history carries its "Markets Open" and "Trading Suspension" notices, timed
    ("Coinbase status notices", "https://status.exchange.coinbase.com/history.rss", "coinbase", None),
]
# Read October 19, 2026 from the desk's reading host; each answered as below, so each is named, not read.
LISTING_UNREAD = [
    ("Upbit listing notices", "not read: its announcements API answered 403 to the desk on October 19, 2026"),
    ("Bybit listing notices", "not read: its announcements API answered 403 (blocked by country) to the desk on "
                              "October 19, 2026"),
    ("Protocol upgrades and governance votes", "not read: not wired in this step; Snapshot's public hub "
                                               "(hub.snapshot.org) answered the desk on October 19, 2026 with "
                                               "off-chain votes and is not read yet, and the desk has found no free "
                                               "feed for on-chain votes; a wire item that names the coin is read"),
]
OUTLET = {"binance": "Binance", "okx": "OKX", "kucoin": "KuCoin", "bitget": "Bitget", "kraken": "Kraken",
          "coinbase": "Coinbase"}
COINBASE_LISTING = re.compile(r"\bmarkets? (?:are )?open\b|\bnow (?:live|available)\b|\blaunch", re.I)
COINBASE_DELISTING = re.compile(r"\btrading suspension\b|\bdelist|\bsuspend(?:s|ed|ing)? trading\b", re.I)


def _announcements(kind, body):
    """[(epoch, title, url, what)] from one venue's answer; `what` is 'listing' or 'delisting' where the item
    itself says which (Coinbase's status feed), else None and the feed's own kind stands."""
    out = []
    if kind == "binance":
        for cat in (((body or {}).get("data") or {}).get("catalogs") or []):
            for a in cat.get("articles") or []:
                t = _ms(a.get("releaseDate"))
                if t and a.get("title"):
                    out.append((t, a["title"], f"https://www.binance.com/en/support/announcement/detail/{a.get('code')}", None))
    elif kind == "okx":
        for blk in (body or {}).get("data") or []:
            for a in blk.get("details") or []:
                t = _ms(a.get("pTime"))
                if t and a.get("title"):
                    out.append((t, a["title"], a.get("url") or "", None))
    elif kind == "kucoin":
        for a in (((body or {}).get("data") or {}).get("items") or []):
            t = _ms(a.get("cTime"))
            if t and a.get("annTitle"):
                out.append((t, a["annTitle"], a.get("annUrl") or "", None))
    elif kind == "bitget":
        for a in (body or {}).get("data") or []:
            t = _ms(a.get("cTime"))
            if t and a.get("annTitle"):
                out.append((t, a["annTitle"], a.get("annUrl") or "", None))
    elif kind in ("kraken", "coinbase"):
        import email.utils
        for item in re.findall(r"<item>(.*?)</item>", body or "", re.S):
            title = re.search(r"<title>(.*?)</title>", item, re.S)
            link = re.search(r"<link>(.*?)</link>", item, re.S)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
            if not (title and pub):
                continue
            ttl = _html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", title.group(1))).strip()
            what = None
            if kind == "coinbase":
                what = ("delisting" if COINBASE_DELISTING.search(ttl) else
                        "listing" if COINBASE_LISTING.search(ttl) else None)
                if not what:
                    continue                     # a delayed send or an outage is not a listing notice
            elif not re.search(r"available for trading|\blist(s|ing|ed)?\b", ttl, re.I):
                continue
            try:
                t = int(email.utils.parsedate_to_datetime(pub.group(1).strip()).timestamp())
            except (TypeError, ValueError):
                continue
            out.append((t, ttl, (link.group(1).strip() if link else ""), what))
    return out


def read_listings(start, end, fetch, ledger):
    """Every listing and delisting notice the venues published in the window and the hour before it."""
    out = []
    for label, url, kind, what in LISTING_FEEDS:
        try:
            body = fetch(url, "text" if kind in ("kraken", "coinbase") else "json")
            rows = _announcements(kind, body)
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(label, str(e) or type(e).__name__, url)
            continue
        ledger.ok(label, url, f"{len(rows)} notice(s) in its answer")
        for t, title, link, own in rows:
            if start - 3600 <= t <= end:
                out.append({"t": t, "title": _clean(title), "url": link, "venue": kind, "what": own or what,
                            "feed": label})
    for name, why in LISTING_UNREAD:
        ledger.miss(name, why)
    return out


def names_coin(text, sym, name):
    rx_name = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.I) if len(name or "") >= 4 else None
    rx_sym = (re.compile(r"(?<![A-Za-z0-9$])\$?" + re.escape(sym) + r"(?=(?:USDT|USDC|USD|BTC|ETH)?(?![A-Za-z0-9]))")
              if len(sym) >= 3 else None)
    t = str(text or "")
    return bool((rx_name and rx_name.search(t)) or (rx_sym and rx_sym.search(t)))


def listing_candidates(notices, sym, name):
    out = []
    for n in notices:
        if not names_coin(n["title"], sym, name):
            continue
        slugw = re.sub(r"[^a-z0-9]+", "-", n["title"].lower()).strip("-")[:60]
        out.append({"id": f"{n['what']}-{n['venue']}-{n['t']}-{slugw}", "kind": n["what"], "line": n["title"],
                    "event_utc": _we()._iso(n["t"]),
                    "event_basis": f"{OUTLET[n['venue']]}'s announcement time",
                    "scheduled": False, "report_utc": None, "source_count": 1, "primary": True,
                    "links": [{"outlet": OUTLET[n["venue"]], "url": n["url"]}] if n["url"] else
                             [{"outlet": OUTLET[n["venue"]], "url": ""}],
                    "secondary": False, "secondary_why": ""})
    return out


CMC = "https://api.coinmarketcap.com/data-api/v3"


def unlock_candidates(sym, name, gecko_id, start, end, fetch, ledger):
    """The coin's token unlocks in the window and the hour before it, from CoinMarketCap's token-unlock
    events (past events carry their time). The coin is found by its CoinGecko id as CoinMarketCap's slug,
    and only when CoinMarketCap gives the same ticker there."""
    label = f"CoinMarketCap token unlocks, {name}"
    url = f"{CMC}/cryptocurrency/detail/lite?slug={gecko_id}"
    try:
        d = (fetch(url, "json") or {}).get("data") or {}
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(label, str(e) or type(e).__name__, url)
        return []
    if str(d.get("symbol") or "").upper() != sym or not d.get("id"):
        ledger.miss(label, f"CoinMarketCap's page at the slug {gecko_id} does not carry the ticker {sym}", url)
        return []
    url = f"{CMC}/token-unlock/event?cryptoId={int(d['id'])}&type=past"
    try:
        body = fetch(url, "json") or {}
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(label, str(e) or type(e).__name__, url)
        return []
    data = body.get("data")
    if not isinstance(data, dict):
        ledger.miss(label, "CoinMarketCap's answer carries no unlock events for it", url)
        return []
    ledger.ok(label, url)
    out = []
    for ev in data.get("tokenEvent") or []:
        t = _we()._parse_utc(ev.get("time"))
        if t is None or not (start - 3600 <= int(t.timestamp()) <= end):
            continue
        pct = ev.get("percentage")
        line = f"{name} token unlock" + (f", {float(pct):.2f}% of its supply" if _num(pct) else "") + " (CoinMarketCap)"
        out.append({"id": f"unlock-{sym.lower()}-{int(t.timestamp())}", "kind": "unlock", "line": line,
                    "event_utc": _we()._iso(int(t.timestamp())), "event_basis": "the unlock time CoinMarketCap lists",
                    "scheduled": True, "report_utc": None, "source_count": 0, "primary": False,
                    "links": [{"outlet": "CoinMarketCap", "url": f"https://coinmarketcap.com/currencies/{gecko_id}/"}],
                    "secondary": False, "secondary_why": ""})
    return out


def read_hacks(start, end, fetch, ledger):
    """DefiLlama's hack list for the window (9.2's reader, read once a run)."""
    return _we()._hacks(start, end, fetch, ledger)


def coin_candidates(sym, name, coin_wires, notices, hacks, unlocks):
    """The candidates that name the coin: its wire items (build() keeps only the items that name it, once),
    the venues' notices and DefiLlama's hacks that name it, and the coin's unlocks."""
    out = list(coin_wires)
    out += listing_candidates(notices, sym, name)
    out += [h for h in hacks if names_coin(h.get("line"), sym, name)]
    out += unlocks
    return out


# ---- the evidence ----------------------------------------------------------------------------------------

def read_series_checked(sym, start, end, now, fetch, ledger, board_pct):
    """why_evidence.read_series, keeping a venue only when its move over the window is within AGREE_PTS of
    the Board's 24-hour figure for the coin. (series, others)."""
    we = _we()
    got = []
    want = (end - start) / 300.0
    for vname, url, parse, bar, skip in we.price_sources(sym, start, end, now):
        label = f"{we.COINS[sym]['name']} prices: {vname}"
        if skip:
            ledger.miss(label, skip)
            continue
        try:
            pts = we._clip(parse(fetch(url, "json"), bar), start, end)
        except Exception as e:                                   # noqa: BLE001
            ledger.miss(label, str(e) or type(e).__name__, url)
            continue
        if len(pts) < we.MIN_COVER * want:
            ledger.miss(label, f"{len(pts)} points for a window of {int(want)} five-minute bars", url)
            continue
        mv = we._pct(pts[0][1], pts[-1][1])
        if _num(board_pct) and abs(mv - board_pct) > AGREE_PTS:
            ledger.miss(label, f"moved {mv:+.2f}% over the window against the Board's {board_pct:+.2f}%: not taken "
                               f"as this coin's series (a ticker can name another coin)", url)
            continue
        ledger.ok(label, url)
        got.append({"source": vname, "url": url, "bar_min": 5, "points": [[t, round(p, 8)] for t, p in pts]})
    return (got[0] if got else None), got[1:]


def volume_vs_week(cid, volume_24h, end, fetch, ledger):
    """The coin's 24-hour volume against its 7-day average, from CoinGecko's daily volumes for the seven days
    before the window (market_chart, days=8, interval=daily). {ratio, avg_usd} or None (named)."""
    label = "CoinGecko daily volumes"
    url = f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency=usd&days=8&interval=daily"
    if not _num(volume_24h) or volume_24h <= 0:
        ledger.miss(label, "the Board carries no 24-hour volume for the coin")
        return None
    try:
        vols = (fetch(url, "json") or {}).get("total_volumes") or []
    except Exception as e:                                       # noqa: BLE001
        ledger.miss(label, str(e) or type(e).__name__, url)
        return None
    day0 = end - 24 * 3600
    prior = [v for t, v in ((int(p[0]) // 1000, p[1]) for p in vols if isinstance(p, list) and len(p) >= 2)
             if t <= day0 and _num(v) and v > 0][-7:]
    if len(prior) < 7:
        ledger.miss(label, f"{len(prior)} daily volume(s) before the window, under seven", url)
        return None
    ledger.ok(label, url)
    avg = sum(prior) / 7.0
    return {"ratio": round(volume_24h / avg, 2), "avg_usd": round(avg)}


STOP = {"set": False}
PHASE = {"verdict": False}      # once the verdicts start, the deadline interrupts a model call (verdict._Late)


def build(board, wire, before_day, used_today=0, fetch=None, now_utc=None, history_root=None, gate_text=None,
          deadline_s=DEADLINE_EVIDENCE_S, clock=None, log=None, cg_spacing=CG_SPACING_S):
    """The movers record for one Board read: the gate, and for each mover its evidence record (9.2's shape,
    with the coin's own candidates). Never raises for a source."""
    we = _we()
    fetch = fetch or we.live_fetch
    budget = we.Budget(deadline_s, clock=clock)
    core, bfetch = fetch, we.budgeted(fetch, budget)
    end_dt = we._parse_utc((board or {}).get("generated_utc"))
    if end_dt is None:
        raise ValueError("the Board carries no reading time")
    end = int(end_dt.timestamp())
    start = end - we.WINDOW_H * 3600
    now = int((we._parse_utc(now_utc) or _dt.datetime.now(_dt.timezone.utc)).timestamp())
    g = gate(board, before_day, history_root, used_today,
             now=_dt.datetime.fromtimestamp(now, _dt.timezone.utc))
    rec = {"what": "Big movers, checked: the gate on the Board's top 100 (AUDIT.md 3.1 and 3.2), and for each "
                   "coin past it the evidence by 9.2's rules with the coin's own candidates. Measured by code.",
           "window": {"start_utc": we._iso(start), "end_utc": we._iso(end), "hours": we.WINDOW_H},
           "made_utc": we._iso(now), "gate": g, "coins": {}, "shared": {}}
    if log is not None:
        log.extend(g["log"])
    if not g["passed"]:
        return rec
    led = we.Ledger()
    rows = {r["symbol"]: r for r in ((board.get("movers") or {}).get("top100") or [])}
    btc, _rest = we.read_series("BTC", start, end, now, core, led)
    if not btc:
        rec["shared"]["unread"] = led.unread
        if log is not None:
            log.append("movers: Bitcoin's series could not be read; no mover evidence written")
        return rec
    others = {"BTC": btc}
    notices = read_listings(start, end, bfetch, led)
    hacks = read_hacks(start, end, bfetch, led)
    wires = we._wire_candidates(wire, start, end)
    cross = we.cross_assets(start, end, bfetch, led)
    shared_read, shared_unread = list(led.read), list(led.unread)
    rec["shared"] = {"read": shared_read, "unread": shared_unread, "notices": len(notices), "hacks": len(hacks)}
    last_cg = [0.0]

    def cg_spaced(f):
        def inner(url, kind="json"):
            if "api.coingecko.com" in url and cg_spacing:
                wait = cg_spacing - (time.monotonic() - last_cg[0])
                if wait > 0:
                    time.sleep(wait)
                last_cg[0] = time.monotonic()
            return f(url, kind)
        return inner
    core_s, bfetch_s = cg_spaced(core), cg_spaced(bfetch)
    for x in g["passed"]:
        if STOP["set"]:
            break
        sym, name, cid = x["sym"], x["name"], x["gecko_id"]
        row = rows.get(sym) or {}
        we.register_coin(sym, cid, name)
        cl = we.Ledger()
        cl.read, cl.unread = list(shared_read), list(shared_unread)
        s, rest = read_series_checked(sym, start, end, now, core_s, cl, x["move_pct"])
        entry = {"gate": x, "gecko_id": cid, "name": name, "rank": x["rank"], "pos": x["pos"], "slug": cid}
        if not s:
            entry["evidence"] = None
            entry["unread"] = cl.unread
            rec["coins"][sym] = entry
            if log is not None:
                log.append(f"movers: {sym}: no venue's series agrees with the Board; no evidence, no verdict")
            continue
        cuts = []
        cw, cut = we._source_check([w for w in wires if names_coin(w.get("line"), sym, name)], bfetch, cl)
        cuts.extend(cut)
        if gate_text is not None:
            kept = []
            for c in cw:
                line = gate_text(c["line"])
                if not line:
                    cl.miss(f"Wire item {c.get('wire_id')}", "its line did not pass the twins gate")
                    continue
                kept.append(dict(c, line=line))
            cw = kept
        unl = unlock_candidates(sym, name, cid, start, end, bfetch, cl)
        cands = coin_candidates(sym, name, cw, notices, hacks, unl)
        ct = we._ct_val(bfetch, cl, (sym,))
        ce = we.coin_entry(sym, s, rest, cands, start, end, now, others, cross, bfetch, cl, ct, {},
                           history_root or we.HISTORY)
        vol = volume_vs_week(cid, row.get("volume_24h"), end, bfetch_s, cl)
        entry["volume_vs_7d"] = vol
        entry["evidence"] = {"what": "The evidence for a Big mover, by 9.2's rules (why_evidence.py): the coin's "
                                     "series, its own candidates (the wire items, listing and delisting notices, "
                                     "unlocks and hacks that name it), the timing test and the onset hour's "
                                     "readings. Measured by code; no model call; no grade.",
                             "window": rec["window"], "made_utc": rec["made_utc"], "candidates": cands,
                             "source_cuts": cuts, "coins": {sym: ce},
                             "subject": {"sym": sym, "name": name, "gecko_id": cid},
                             "day": {"stablecoins": None, "etf_btc": None},
                             "read": cl.read, "unread": cl.unread}
        rec["coins"][sym] = entry
        if log is not None:
            run = ce.get("run") or {}
            pats = ", ".join(p["label"] for p in (ce.get("mechanics") or {}).get("patterns") or []) or "none"
            log.append(f"movers: {sym} evidence: {len(cands)} candidate(s), run {run.get('dir')} {run.get('pct')}%, "
                       f"pattern {pats}, volume {('%.2fx its 7-day average' % vol['ratio']) if vol else 'not read'}")
    return rec


# ---- the verdicts -----------------------------------------------------------------------------------------

def register(sym, name, cid):
    """The mover's name, its /why/ slug (its CoinGecko id) and the words that make a line state its cause,
    in verdict.py's tables."""
    vd = _vd()
    if sym in OWN_CARD:
        return
    vd.NAMES[sym] = (name, cid)
    alt = [re.escape(name)] + ([re.escape(sym)] if len(sym) >= 3 else [])
    vd.SUBJECT[sym] = r"\b(" + "|".join(alt) + r")\b"


def day_of(entry, btc_pct):
    """The window the mover's card names: the rolling 24 hours the gate measured."""
    return {"basis": "rolling_24h", "BTC": btc_pct, entry["gate"]["sym"]: entry["gate"]["move_pct"]}


def verdicts(rec, date_et, slot, gate=None, ledger_path=None, cap=None, client=None, now=None, log=None):
    """Each mover's verdict through verdict.write_run: the grade in code, the model's two checked sentences,
    every attempt reserved against the day's cap. Fills entry['verdict']; returns the run rows."""
    vd = _vd()
    rows = []
    btc = (rec.get("gate") or {}).get("btc_24h_pct")
    for sym, entry in (rec.get("coins") or {}).items():
        if not entry.get("evidence"):
            continue
        if STOP["set"]:
            entry["verdict"] = vd.record_from(entry["evidence"], date_et, slot, now=now, gate=gate,
                                              day=day_of(entry, btc), syms=(sym,))
            for v in entry["verdict"]["coins"].values():
                if v.get("grade"):
                    v["fail_reason"] = f"the step's {DEADLINE_S}s budget is spent"
            continue
        register(sym, entry["name"], entry["gecko_id"])
        try:
            out, row = vd.write_run(entry["evidence"], date_et, slot, gate=gate, ledger_path=ledger_path, save=False,
                                    cap=cap, client=client, now=now, day=day_of(entry, btc), syms=(sym,))
        except vd._Late as e:
            out = vd.record_from(entry["evidence"], date_et, slot, now=now, gate=gate, day=day_of(entry, btc),
                                 syms=(sym,))
            for v in out["coins"].values():
                if v.get("grade"):
                    v["fail_reason"] = str(e)
            row = None
        entry["verdict"] = out
        if row:
            rows.append(row)
        v = (out.get("coins") or {}).get(sym) or {}
        if log is not None:
            log.append(f"movers: {sym} verdict {v.get('grade') or v.get('kind')}"
                       + (f" ({v.get('by')}: {v.get('fail_reason')})" if v.get("fail_reason") else
                          f" ({v.get('by')})" if v.get("grade") else ""))
    return rows


def reads_of(rec):
    """The coin reads a record made: each mover the gate passed (the per-day cap counts these)."""
    return len(((rec or {}).get("gate") or {}).get("passed") or [])


# ---- records on disk ---------------------------------------------------------------------------------------

NAME_RX = re.compile(r"(\d{4}-\d{2}-\d{2})-(morning|evening|breaking-\d{4})\.json")


def record_path(date_et, slot, directory=None):
    return os.path.join(directory or DIR, f"{date_et}-{slot}.json")


def load(date_et, slot, directory=None):
    try:
        r = json.load(open(record_path(date_et, slot, directory), encoding="utf-8"))
        return r if isinstance(r, dict) and isinstance(r.get("gate"), dict) else None
    except (OSError, ValueError, TypeError):
        return None


def names(directory=None):
    try:
        return sorted(n for n in os.listdir(directory or DIR) if NAME_RX.fullmatch(n))
    except OSError:
        return []


def records(directory=None):
    out = []
    for n in names(directory):
        m = NAME_RX.fullmatch(n)
        r = load(m.group(1), m.group(2), directory)
        if r:
            out.append(r)
    return out


def used_today(date_et, directory=None):
    return sum(reads_of(r) for r in records(directory) if r.get("date_et") == date_et)


def latest(directory=None):
    rs = records(directory)
    return max(rs, key=lambda r: ((r.get("window") or {}).get("end_utc") or "", r.get("made_utc") or "")) if rs else None


def current(rec, board_utc, max_gap_h=18):
    """The record when its window ended within `max_gap_h` hours of the Board reading a page carries."""
    we = _we()
    if not rec:
        return None
    a = we._parse_utc((rec.get("window") or {}).get("end_utc"))
    b = we._parse_utc(board_utc)
    if a is None or b is None or abs((a - b).total_seconds()) > max_gap_h * 3600:
        return None
    return rec


def prepare(rec):
    """Register every mover in a stored record with why_evidence and verdict, so a page can draw it."""
    for sym, e in ((rec or {}).get("coins") or {}).items():
        if sym in OWN_CARD:
            continue
        _we().register_coin(sym, e.get("gecko_id") or "", e.get("name") or sym)
        register(sym, e.get("name") or sym, e.get("gecko_id") or "")
    return rec


# ---- what the pages draw ------------------------------------------------------------------------------------

def coin_parts(rec, sym, board_utc):
    """(card html, section html) for a mover's coin page, or ('', ''). The section while the record's window
    ended within 3 hours of the page's Board reading (9.2's rule); the card, its section-page form, beside
    it; with no section, the card alone in its full form while the record is within 18 hours (9.3's rule).
    A card for another window than the section's never prints beside it."""
    try:
        we, vd = _we(), _vd()
        if not current(rec, board_utc):
            return "", ""
        e = (rec.get("coins") or {}).get(sym)
        if not e or not e.get("evidence") or not e.get("verdict"):
            return "", ""
        prepare(rec)
        ev, vrec = e["evidence"], e["verdict"]
        v = (vrec.get("coins") or {}).get(sym) or {}
        sec = ""
        if we.from_snapshot_coin(ev, sym, board_utc):
            sec = we.section_html(ev, sym, live=True, graded=v.get("grade"), marks=vd.marks(vrec, sym))
        card = vd.card_html(vrec, sym, where="coin", live=True, with_section=bool(sec))
        if not card and sec:
            sec = we.section_html(ev, sym, live=True)
        return card, sec
    except Exception as ex:                                       # noqa: BLE001 fail open
        print(f"::warning::movers: the coin page parts for {sym} were not drawn ({type(ex).__name__}: {ex})")
        return "", ""


def wire_urls(rec, sym):
    e = ((rec or {}).get("coins") or {}).get(sym) or {}
    return _we().wire_urls_shown(e.get("evidence")) if e.get("evidence") else set()


def _pct(v):
    return f"{v:+.2f}%" if _num(v) else ""


def coin_href(sym, name):
    """The coin page's URL by the site's own rule (site_build._coin_slug), never rebuilt here."""
    import site_build as sb
    slug = sb._coin_slug({"symbol": sym, "name": name})
    return f"/coins/{slug}.html" if slug else ""


def _btc_verdict_href(date_et):
    """Bitcoin's verdict for the day: its /why/ page when a graded one is stored, else its coin page, where the
    card is."""
    try:
        vd = _vd()
        for n in vd._names():
            if n.startswith(f"{date_et}-"):
                r = vd.load(n[:10], n[11:-5])
                if (((r or {}).get("coins") or {}).get("BTC") or {}).get("grade"):
                    return vd.url(date_et, "BTC")
    except Exception:                                             # noqa: BLE001
        pass
    return "/coins/btc.html"


def _reasons(left):
    """Each left-out coin under its own stored reason, the coins sharing a reason grouped: [(why, [rows])]."""
    out = {}
    for x in left:
        out.setdefault(x.get("why") or "no reason stored", []).append(x)
    return list(out.items())


def list_html(rec, board_utc, live=True):
    """THE BIG MOVERS LIST (AUDIT.md 3.2), the one movers list on /pulse/movers: every coin past the line, in order
    of its volatility multiple, with its place in the desk's Top 100, its 24-hour move, its excess over Bitcoin, its
    usual-day multiple, its volume against its 7-day average and its grade; the coins past the per-reading or the
    per-day cap listed ungraded, the cap named; each coin left out under its own reason; on a crash day, one line
    that most coins moved with the market, pointing at Bitcoin's verdict. Never padded. With no current record, the
    section says so."""
    try:
        we = _we()
        rule = (f'<p class="pc-note">The line: a 24-hour move of {GATE["move_min_pct"]:g}% or more, at least '
                f'{GATE["vol_multiple_min"]:g} times the coin\'s usual daily move over 30 days, and at least '
                f'{GATE["excess_min_pts"]:g} points beyond what Bitcoin\'s move gives it. Top 100 only, never a '
                f'stablecoin; at most {GATE["per_slot"]} checked a reading and {GATE["per_day"]} a day. '
                f'"Beyond Bitcoin" is the move minus what its 30-day beta to Bitcoin gives; "Its usual day" is the '
                f'move over its 30-day daily volatility. Bitcoin and Ether have their own checks on their pages.</p>')
        head = '<section class="bm" aria-label="Big movers"><div class="sec-head"><h2>Today\'s big movers, checked</h2><span class="bar"></span></div>'
        if not current(rec, board_utc):
            return (head + '<p class="pc-note">The desk has no current Big movers reading. It reads '
                           'the line with the Morning Brief and the Evening Brief; the list returns with the next.</p>'
                    + rule + '</section>')
        g = rec.get("gate") or {}
        w1 = we._parse_utc((rec.get("window") or {}).get("end_utc"))
        asof = f' data-asof="{_e(we._iso(int(w1.timestamp())))}"' if (live and w1) else ""
        when = f"the 24 hours to {we.clock(int(w1.timestamp()))}, {we.long_day(int(w1.timestamp()))}" if w1 else ""
        stamp = f"{we.clock(int(w1.timestamp()))}, {we.long_day(int(w1.timestamp()))}" if w1 else ""
        held = g.get("over_cap") or []
        rows = []
        for x in (g.get("passed") or []) + held:
            e = (rec.get("coins") or {}).get(x["sym"]) or {}
            v = (((e.get("verdict") or {}).get("coins") or {}).get(x["sym"]) or {})
            grade = v.get("grade")
            if x in held:
                gr = '<span class="bm-g">Past the cap</span>'
            elif grade and v.get("url"):
                gr = f'<a class="bm-g vd-badge vd-{_e(grade.lower())}" href="{_e(v["url"])}">Checked: <b>{_e(grade)}</b></a>'
            elif v.get("kind") == "withheld":
                gr = '<span class="bm-g">Not checked today</span>'
            elif v.get("kind") == "next_read":
                gr = '<span class="bm-g">Verdict at the next read</span>'
            else:
                gr = '<span class="bm-g">No grade</span>'
            vol = e.get("volume_vs_7d")
            volt = f"{vol['ratio']:.1f}x its 7-day average" if vol else ("not read" if x not in held else "")
            cls = "up" if x["move_pct"] >= 0 else "down"
            exc, mult = f"{x['excess_pts']:+.1f} pts", f"{x['multiple']:.1f}x"
            rows.append(
                f'<tr><td class="bm-rk">#{_e(x.get("pos"))}</td>'
                f'<th scope="row"><a href="{_e(coin_href(x["sym"], x["name"]))}">{_e(x["name"])}</a>'
                f'<span class="bm-sym">{_e(x["sym"])}</span></th>'
                f'<td class="bm-mv {cls}">{_e(_pct(x["move_pct"]))}</td>'
                f'<td class="xs-x">{_e(exc)}</td><td class="xs-x">{_e(mult)}</td><td class="xs-x">{_e(volt)}</td>'
                f'<td>{gr}</td></tr>')
        crash_html = ""
        c = g.get("crash") or {}
        if c.get("day") and c.get("measured_past_move") and c.get("with_market", 0) * 2 > c["measured_past_move"]:
            crash_html = (f'<p class="bm-crash">A market-wide move ({_e(", ".join(c["why"]))}): most coins moved with '
                          f'the market. {c["with_market"]} of the {c["measured_past_move"]} measured coins past '
                          f'{GATE["move_min_pct"]:g}% moved within {GATE["excess_min_pts"]:g} points of what Bitcoin\'s '
                          f'move gives them, so they are not checked one by one. '
                          f'<a href="{_e(_btc_verdict_href(rec.get("date_et") or ""))}">Bitcoin\'s verdict</a> covers '
                          f'the market\'s move.</p>')
        if rows:
            # AT 375 (Sprint 9.5): rank, coin, 24h and grade; the three measures wait behind "Show all columns"
            import site_build as _sb
            body = (_sb.fit_toggle("fit-bm") + '<div class="movetable fit-tbl" tabindex="0" role="region" aria-label="Big movers (scrollable)">'
                    '<table class="mv-tbl bm-tbl"><thead><tr><th scope="col">Rank</th><th scope="col">Coin</th>'
                    '<th scope="col">24h</th><th scope="col" class="xs-x">Beyond Bitcoin</th>'
                    '<th scope="col" class="xs-x">Its usual day</th>'
                    '<th scope="col" class="xs-x">Volume</th><th scope="col">Grade</th></tr></thead><tbody>'
                    + "".join(rows) + "</tbody></table></div>")
        else:
            body = ('<p class="pc-note">No top-100 coin moved past the line in this reading, so the list is '
                    'empty rather than padded.</p>')
        cap_html = ""
        if held:
            cap_html = (f'<p class="pc-note">The desk checks at most {GATE["per_slot"]} a reading and '
                        f'{GATE["per_day"]} a day ({int(g.get("used_today") or 0)} checked earlier today). Past that '
                        f'cap, these are listed and held back, not checked: '
                        + ", ".join(_e(x["name"]) for x in held) + '.</p>')
        left_html = "".join(
            f'<p class="pc-note">Moved {GATE["move_min_pct"]:g}% or more and not measured (the line needs 30 days of '
            f'stored daily closes); {_e(why)}: '
            + ", ".join(f'<a href="{_e(coin_href(x["sym"], x["name"]))}">{_e(x["name"])}</a> {_e(_pct(x["move_pct"]))}'
                        for x in xs) + '.</p>' for why, xs in _reasons(g.get("left_out") or []))
        rank = (f'<p class="pc-note">Rank: its place in the desk\'s Top 100 (CoinGecko market cap, screened, as the '
                f'Top 100 page and the coin pages number it), as of {_e(stamp)}.</p>') if rows else ""
        return (f'{head}<p class="live-stamp"{asof}>{_e(when)}</p>{crash_html}'
                f'{body}{cap_html}{left_html}{rank}{rule}</section>')
    except Exception as ex:                                       # noqa: BLE001 fail open
        print(f"::warning::movers: the Big movers list was not drawn ({type(ex).__name__}: {ex})")
        return ""


def listed(rec, board_utc):
    """The symbols the Big movers list prints (passed, past the cap and left out), so a page prints each move once."""
    if not current(rec, board_utc):
        return set()
    g = (rec or {}).get("gate") or {}
    return {x["sym"] for x in (g.get("passed") or []) + (g.get("over_cap") or []) + (g.get("left_out") or [])}


# ---- the Brief cites the movers it mentions (AUDIT.md 3.2, "Linked") -----------------------------------------------

_CITE_MEMO = {}


def day_list(date_et, directory=None):
    """{sym: (name, href)} for every coin on the day's Big movers lists (passed, past the cap, left out): its graded
    verdict's /why/ page when it has one that day, else its coin page."""
    d = directory or DIR
    stats_ = []
    for n in names(directory):
        try:
            st = os.stat(os.path.join(d, n))
            stats_.append((n, st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    key = (d, tuple(stats_), date_et)
    if key in _CITE_MEMO:
        return _CITE_MEMO[key]
    out = {}
    for r in records(directory):
        if r.get("date_et") != date_et:
            continue
        g = r.get("gate") or {}
        for x in (g.get("passed") or []) + (g.get("over_cap") or []) + (g.get("left_out") or []):
            v = (((((r.get("coins") or {}).get(x["sym"]) or {}).get("verdict") or {}).get("coins") or {})
                 .get(x["sym"]) or {})
            href = v.get("url") if v.get("grade") and v.get("url") else None
            have = out.get(x["sym"])
            if have and have[1].startswith("/why/"):
                continue
            out[x["sym"]] = (x.get("name") or x["sym"], href or coin_href(x["sym"], x.get("name") or x["sym"]))
    _CITE_MEMO.clear()
    _CITE_MEMO[key] = out
    return out


# THE WORDS A COIN CANNOT BE CITED BY ON ITS OWN (review 2): a coin whose name or ticker is an ordinary English word
# ("Story", "Flow", "Sonic", "NOT", "ONE", "Curve") links only beside a coin cue: its ticker or name in brackets, the
# word token or coin, a $ before it, or a $ or % figure right after it. Lower case; the one place this list lives.
COMMON_WORDS = frozenset("""
act ai ape ark beam core cosmos curve dash dot flow gas graph hype immutable jupiter kite link
maker magic mask max move near not one optimism plume polygon pump rain render sand sky sonic stable stellar story
sun trump wild world zero
""".split())
_CUE_AFTER = re.compile(r"\s*(?:\(\$?[A-Za-z0-9]+\)|tokens?\b|coins?\b|(?:\w+\s+){0,2}[-+]?\$?\d[\d.,]*\s?%?)")


def _cite_match(text, sym, name):
    """The first unambiguous mention of the coin in plain text: (start, end) or None. Its full name (four letters or
    more, as written) or its ticker (three letters or more, as written, a $ allowed before it); a name or ticker in
    COMMON_WORDS counts only beside a coin cue."""
    pats = []
    if len(name or "") >= 4:
        pats.append(r"(?<![A-Za-z0-9])" + re.escape(_e(name)) + r"(?![A-Za-z0-9])")
    if len(sym) >= 3:
        pats.append(r"(?<![A-Za-z0-9])\$?" + re.escape(sym) + r"(?![A-Za-z0-9])")
    if not pats:
        return None
    for m in re.finditer("|".join(pats), text):
        word = m.group(0).lstrip("$")
        if word.lower() not in COMMON_WORDS:
            return m.start(), m.end()
        if m.group(0).startswith("$") or text[max(0, m.start() - 1):m.start()] == "$" or _CUE_AFTER.match(text[m.end():]):
            return m.start(), m.end()
    return None


def cite(html_text, date_et, directory=None):
    """The Brief's text with each coin on the day's Big movers list linked at its first unambiguous mention: to its
    verdict, or to its coin page where it has no graded verdict. Deterministic, no model call. Text inside a tag or an
    existing link is never touched (_cite_match says what counts as a mention)."""
    try:
        lst = day_list(date_et, directory) if date_et else {}
        if not lst or not html_text:
            return html_text
        out = html_text
        for sym, (name, href) in lst.items():
            parts = re.split(r"(<[^>]+>)", out)
            depth = 0
            for i, part in enumerate(parts):
                if part.startswith("<"):
                    if re.match(r"<a[\s>]", part, re.I):
                        depth += 1
                    elif re.match(r"</a\s*>", part, re.I):
                        depth = max(0, depth - 1)
                    continue
                hit = None if depth else _cite_match(part, sym, name)
                if hit:
                    a0, a1 = hit
                    parts[i] = part[:a0] + f'<a class="bm-cite" href="{_e(href)}">{part[a0:a1]}</a>' + part[a1:]
                    break
            out = "".join(parts)
        return out
    except Exception as ex:                                       # noqa: BLE001 fail open: the text as it was
        print(f"::warning::movers: the Brief's citations were not drawn ({type(ex).__name__}: {ex})")
        return html_text


# ---- the /why/ pages ----------------------------------------------------------------------------------------

def build_pages(directory=None, dateline="", share=None):
    """[{rel, html, path, lastmod, published_utc, title}] for every graded mover verdict: one URL per day and
    coin, its slug the coin's CoinGecko id, kept once written. The page carries the day's newest graded
    verdict for the coin and its evidence."""
    by, evening = {}, set()
    for r in records(directory):
        prepare(r)
        if r.get("slot") == "evening":
            evening.add(r.get("date_et"))
        for sym, e in (r.get("coins") or {}).items():
            v = (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {})
            if v.get("grade") and e.get("evidence"):
                by.setdefault((r["date_et"], e.get("gecko_id") or sym.lower()), []).append((r, sym, e))
    out = []
    for (day, cid), items in sorted(by.items()):
        items.sort(key=lambda t: ((t[0].get("window") or {}).get("end_utc") or "", t[0].get("made_utc") or ""),
                   reverse=True)
        try:
            out.append(_page(day, cid, items, dateline, share, ["evening"] if day in evening else []))
        except Exception as ex:                                   # noqa: BLE001
            print(f"::warning::movers: /why/{day}-{cid} was not built ({type(ex).__name__}: {ex})")
    return out


def _page(day, cid, items, dateline, share=None, slots=()):
    import site_build as sb
    we, vd = _we(), _vd()
    rec, sym, e = items[0]
    name = e.get("name") or sym
    vrec, ev = e["verdict"], e["evidence"]
    v = vrec["coins"][sym]
    d = _dt.date.fromisoformat(day)
    when = f"{d.strftime('%A, %B')} {d.day}, {d.year}"
    title = f"Why {name} moved: {when}"
    sec = we.section_html(ev, sym, live=False, graded=v.get("grade"), marks=vd.marks(vrec, sym))
    card = vd.card_html(vrec, sym, where="page", live=False, link=False, with_section=bool(sec))
    path_rel = f"/why/{day}-{cid}"
    href = coin_href(sym, name)
    coin_link = (f'<p class="td-w">{_e(name)}\'s page, with its chart and readings, is at '
                 f'<a href="{_e(href)}">{_e(href[:-5])}</a>.</p>') if href else ""
    stamp = {"morning": "Morning Brief", "evening": "Evening Brief"}.get(rec.get("slot"), "Breaking read")
    body = f"""<main class="wrap"><section class="page td-page vd-page">
  <span class="kicker">Why it moved</span>
  <h1>{_e(title)}</h1>
  <p class="td-stamp">{_e(stamp)}, Big movers</p>
  {card}
  {sec}
  {coin_link}
</section></main>"""
    canon = sb.ORIGIN + path_rel
    desc = " ".join(v.get("text") or v.get("line") or [])[:200]
    pub_first = min(r.get("made_utc") or "" for r, _s, _e2 in items)
    pub = rec.get("made_utc") or ""
    schema = json.dumps({"@context": "https://schema.org", "@graph": [{
        "@type": "NewsArticle", "headline": title, "url": canon, "mainEntityOfPage": canon,
        "description": desc, "datePublished": vd._et_iso(pub_first), "dateModified": vd._et_iso(pub),
        "author": {"@type": "Organization", "name": sb.NAME, "url": sb.ORIGIN + "/news.html"},
        "publisher": {"@type": "Organization", "@id": sb.ORIGIN + "/#publisher", "name": sb.FAMILY,
                      "url": sb.ORIGIN + "/",
                      "logo": {"@type": "ImageObject", "url": sb.ORIGIN + "/publisher-logo-512.png",
                               "width": 512, "height": 512}}}]}, ensure_ascii=False)
    import share_cards
    og = share_cards.for_page(share, vrec, sym, ev, f"{day}-{cid}", day, slots)
    html = sb.shell(f"{title} - {sb.NAME}", desc, "Today", body, dateline, path=path_rel + ".html",
                    og_type="article", schema_extra=f'\n<script type="application/ld+json">{schema}</script>', **og)
    return {"rel": f"why/{day}-{cid}.html", "html": html, "path": path_rel, "lastmod": pub,
            "published_utc": pub_first, "title": title}


# ---- the run's step -----------------------------------------------------------------------------------------

def _slot(now):
    """(date_et, slot) this run writes for: a breaking run (BREAKING=1) writes its own record, named by its
    UTC clock; a slot's run writes the slot why_evidence wrote for."""
    if (os.environ.get("BREAKING") or "0") == "1":
        return now.astimezone(ET).date().isoformat(), f"breaking-{now.strftime('%H%M')}"
    d, slot, _c = _we()._slot_now(now)
    return d, slot


def run(board, wire, date_et, slot, fetch=None, now=None, directory=None, history_root=None, gate=None,
        ledger_path=None, cap=None, client=None, save=True, do_bootstrap=True, log=None, cg_spacing=CG_SPACING_S):
    """The whole step on one Board read: bootstrap the history a candidate lacks, gate, read the evidence,
    write each verdict, save the record. Returns the record."""
    we = _we()
    log = log if log is not None else []
    now = now or _dt.datetime.now(_dt.timezone.utc)
    end_dt = we._parse_utc((board or {}).get("generated_utc"))
    before_day = (end_dt - _dt.timedelta(hours=we.WINDOW_H)).astimezone(ET).date().isoformat()
    if do_bootstrap:
        # the history reads have their own budget: past it, a read is skipped and the coin is left out and said
        hfetch = we.budgeted(fetch or we.live_fetch, we.Budget(HISTORY_BUDGET_S))
        bootstrap(board, before_day, lambda u: hfetch(u, "json"), now=now, root=history_root, log=log,
                  spacing=cg_spacing)
    used = used_today(date_et, directory)
    gtext = (lambda s: gate.text(s, "the evidence (reported)", dollars=True).strip()) if gate is not None else None
    rec = build(board, wire, before_day, used_today=used, fetch=fetch, now_utc=we._iso(int(now.timestamp())),
                history_root=history_root, gate_text=gtext, log=log, cg_spacing=cg_spacing)
    rec.update(date_et=date_et, slot=slot)
    PHASE["verdict"] = True
    try:
        verdicts(rec, date_et, slot, gate=gate, ledger_path=ledger_path, cap=cap, client=client, now=now, log=log)
    finally:
        PHASE["verdict"] = False
    if save:
        p = record_path(date_et, slot, directory)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(rec, open(p, "w", encoding="utf-8"), indent=1)
        log.append(f"movers: wrote {p}")
    return rec


def main():
    args = sys.argv[1:]
    if args[:1] == ["--record"] and len(args) == 5:
        return _record(*args[1:])
    if "--write" not in args:
        print(__doc__.split("\n\n")[-1])
        return 2
    log = []
    try:
        import signal
        import home
        import site_build as sb
        import snapshot as _s
        import twins_gate
        we = _we()

        def late(*_a):
            # the reads stop at the next source and are named "not read in time"; a model call in flight is cut,
            # and its reservation stands (verdict.py's rule)
            STOP["set"] = True
            _vd().STOP["set"] = True
            we.STOP["set"] = True
            if PHASE["verdict"]:
                raise _vd()._Late(f"the step's {DEADLINE_S}s budget is spent")
        signal.signal(signal.SIGTERM, late)
        signal.signal(signal.SIGALRM, late)
        signal.alarm(DEADLINE_S)
        pulse, flows = sb.load_pulse(), sb.load_flows()
        end = (pulse or {}).get("generated_utc")
        now = _dt.datetime.now(_dt.timezone.utc)
        if not end or (now - we._parse_utc(end)).total_seconds() > 3 * 3600:
            print(f"::warning::movers: the Board's reading ({end}) is missing or over 3 hours old; no record written")
            return 0
        date, slot = _slot(now)
        have = load(date, slot)
        if have and ((have.get("gate") or {}).get("board_utc") or "") >= end:
            print(f"movers: {date}-{slot}.json already stored for this Board reading; a stored record is frozen")
            return 0
        gate = twins_gate.Gate(_s.build(pulse, flows), log_path="", quiet=True)
        run(pulse, home.load_json(sb.WIRE_JSON), date, slot, now=now, gate=gate, log=log)
        signal.alarm(0)
    except Exception as e:                                       # never a gate on a slot
        log.append(f"::warning::movers: no record written ({type(e).__name__}: {e})")
    for line in log:
        print(line)
    return 0


def _record(pulse_path, wire_path, hist_path, out_path):
    """Read a real day's sources for its recorded Board and save every answer, so the tests run on what
    the sources said. The Board, the wire and the history answers are the recorded files named; the venue
    answers are read now, for the Board's own window. Nothing is edited."""
    we = _we()
    import tempfile
    board = json.load(open(pulse_path, encoding="utf-8"))
    wire = json.load(open(wire_path, encoding="utf-8"))
    hist = json.load(open(hist_path, encoding="utf-8"))
    now = _dt.datetime.now(_dt.timezone.utc)
    rec = we.Recorder(we.live_fetch)
    with tempfile.TemporaryDirectory() as td:
        hroot = _history_root(hist, td)
        end_dt = we._parse_utc(board["generated_utc"])
        before_day = (end_dt - _dt.timedelta(hours=we.WINDOW_H)).astimezone(ET).date().isoformat()
        log = []
        # the clock is the read's own, as why_evidence's recorder keeps it: a venue whose public window cannot
        # reach this Board's window is not asked, and says so
        build(board, wire, before_day, fetch=rec, now_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"), history_root=hroot,
              log=log, deadline_s=600)
    json.dump({"what": "Every answer the movers step's sources gave for this Board's window, read at recorded_utc "
                       "by movers.py --record; the Board, the wire and the history answers are the recorded files "
                       "named in 'from'. Nothing is edited.",
               "from": {"board": os.path.basename(pulse_path), "wire": os.path.basename(wire_path),
                        "history": os.path.basename(hist_path)},
               "end_utc": board["generated_utc"], "recorded_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "recorded_et": now.astimezone(ET).strftime("%a %b %-d %Y, %-I:%M %p %Z"),
               "responses": rec.responses}, open(out_path, "w", encoding="utf-8"), separators=(",", ":"))
    for line in log:
        print(line)
    print(f"recorded {len(rec.responses)} answer(s) to {out_path}")
    return 0


def _history_root(hist_answers, directory):
    """A history directory built from recorded 365-day answers by history.py's own rules (plus Bitcoin's stored
    series), for a fixture: the closes are the source's, not edited."""
    import history
    import shutil
    for url, body in (hist_answers or {}).items():
        m = re.search(r"/coins/([a-z0-9-]+)/market_chart", url)
        if not m:
            continue
        s = {"coin": m.group(1), "symbol": "", "closes": {}}
        history.append(s, history.utc_day_closes((body or {}).get("prices")))
        history.save(s, directory)
    shutil.copy(os.path.join(history.HIST_DIR, "bitcoin.json"), os.path.join(directory, "bitcoin.json"))
    return directory


if __name__ == "__main__":
    sys.exit(main())
