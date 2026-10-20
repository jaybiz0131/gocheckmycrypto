#!/usr/bin/env python3
"""
watcher.py: the BREAKING-NEWS WATCHER (directive item 2, 2026-07-14). NO MODEL CALLS.

Runs every 30 minutes (watcher.yml). Three plain-threshold triggers, all configurable via
env (repo Variables in CI):
  1. PRICE: any major asset (BTC/ETH/SOL/XRP) moved more than WATCH_MOVE_PCT (default 5.0)
     percent in the last hour, per CoinGecko's keyless market_chart (no state needed:
     the 1h delta is computed from the chart itself).
  1b. GRIND: any major moved more than WATCH_MOVE_24H_PCT (default 4.0) percent over the
     same day chart's full span (first vs last point: zero extra requests, same
     fail-quiet posture). The Aug 27-29 BTC slide from ~$81.4K to sub-$78K was -4.2%
     total; the one-hour trigger was mathematically blind to it even in the degenerate
     all-in-one-hour case.
  2. NEWS: the desk's own RSS aggregation (aggregate.py, deterministic) shows a fresh
     cluster (last WATCH_FRESH_MIN minutes, default 90) carried by at least
     WATCH_MIN_SOURCES (default 4) INDEPENDENT sources.

On trigger it emits trigger=true to GITHUB_OUTPUT; watcher.yml then calls the full brief
workflow with breaking=true (Haiku pipeline + the additive two-source breaking gate).
COOLDOWN: if the desk already published within WATCH_COOLDOWN_MIN (default 120) minutes,
the watcher stays quiet: coverage is already fresh, and a 6-hour selloff must not buy 12
pipeline runs. Costs $0 in model tokens; the trigger pays for one Haiku run (~$0.20).

USAGE  python3 watcher.py     (exit 0 always; the signal is the trigger output line)
"""

import datetime
import glob
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MAJORS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP"}
UA = {"User-Agent": "CryptoCronkite-watcher/1.0"}

# `or` (not a get() default): unset repo Variables reach CI as EMPTY strings
MOVE_PCT = float(os.environ.get("WATCH_MOVE_PCT") or "5.0")
MOVE_24H_PCT = float(os.environ.get("WATCH_MOVE_24H_PCT") or "4.0")
MIN_SOURCES = int(os.environ.get("WATCH_MIN_SOURCES") or "5")   # T-1: raised from 4
FRESH_MIN = int(os.environ.get("WATCH_FRESH_MIN") or "90")
COOLDOWN_MIN = int(os.environ.get("WATCH_COOLDOWN_MIN") or "120")

# PROGRAM 4, T-1 (2026-09-16): THE CAGE.
#
# On 15 Sep this desk made 39 brief runs, a model run and a Netlify build each. The
# watcher is kept here (unlike the Sports desk, where it is off) because crypto
# breaking news is a product this desk actually sells, but it now fires only for a
# major event in the categories that earn, at most twice a day.
#
# Four changes, all reversible by the env vars below:
#   1. Earning categories only. A fresh multi-source cluster is no longer enough on its
#      own; it must be regulation, exchange security, ETFs and institutions, or a major
#      hack. The patterns follow site_build.TAG_RULES so the watcher and the site agree
#      on what a category is, plus a hack/exploit pattern the tag vocabulary has no
#      entry for.
#   2. Sources raised from 4 to 5.
#   3. A hard cap of two breaking runs a day.
#   4. The price triggers are off. A 5 percent hour and a 4 percent day are not events
#      in the categories above; they are volatility, and they fired on any moving day.
#      The Board already carries the move, and it carries it without a model run.
BREAKING_MAX_PER_DAY = int(os.environ.get("WATCH_MAX_BREAKING_PER_DAY") or "2")
PRICE_TRIGGERS = (os.environ.get("WATCH_PRICE_TRIGGERS") or "0") == "1"

# THE PATTERNS COME FROM THE SITE, NOT FROM A COPY HERE. site_build.TAG_RULES already
# carries regulation, exchanges, etfs-funds and security (hacks, exploits, breaches,
# theft, rug pulls) and the site tags every story with them. A second copy in this file
# would be correct on the day it was written and wrong the first time either one was
# edited: the watcher would fire on a category the site no longer recognises, or miss
# one it added. One definition, imported.
#
# The earning categories are named as site_build tags. "exchanges" earns because an
# exchange story that clears five independent sources inside 90 minutes is a halt, a
# delisting or an insolvency, not a listing announcement.
import re as _re

EARNING_TAGS = ["regulation", "exchanges", "etfs-funds", "security"]
# A few institutional words the site's etfs-funds rule does not carry, because on the
# site "institutional" would tag half the market stories and here it is one of four
# gates a story must already have cleared.
EXTRA = _re.compile(r"\b(institutional|sovereign wealth|pension fund|"
                    r"treasury (?:allocation|purchase))\b", _re.I)


def _earning_rules():
    """[(tag, compiled)] for the earning tags, read from site_build. Falls back to an
    empty list if site_build cannot be imported, and earning_category() treats that as
    'do not fire': a watcher that cannot tell what a category is must not spend."""
    try:
        import site_build
    except Exception as exc:
        print(f"watcher: site_build import failed ({exc}); no category can be resolved")
        return []
    want = set(EARNING_TAGS)
    return [(tag, _re.compile(pat, _re.I))
            for tag, pat in site_build.TAG_RULES if tag in want]


EARNING = _earning_rules()


def earning_category(text):
    """Which earning category this headline belongs to, or None. T-1.

    Order follows site_build.TAG_RULES, which is ordered most specific first, so a
    hacked-exchange story reads as security rather than exchanges."""
    text = text or ""
    for name, rx in EARNING:
        if rx.search(text):
            return name
    if EARNING and EXTRA.search(text):
        return "etfs-funds"
    return None


def breaking_runs_today():
    """How many breaking runs this desk has already made today, UTC, from the T-4
    ledger.

    The ledger is the right source: it records the RUN, so a breaking run that spent
    money and published nothing still counts against the day. Counting published
    stories instead would let a failed run retry all day, and would let the evening
    Edition's own stories eat the breaking allowance.

    Falls back to -1 (unknown) when the ledger is missing, and an unknown count does
    not block: the cap is a spend guard, not a publishing gate, and a watcher that
    silently stopped firing because a file was absent is the worse failure."""
    path = os.path.join(HERE, "ledger.json")
    try:
        rows = json.load(open(path, encoding="utf-8")).get("runs", [])
    except Exception:
        return -1
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    return sum(1 for r in rows
               if r.get("breaking") and (r.get("t") or "")[:10] == today)


def emit(trigger, reason="", breaking=True, slot=""):
    # `slot` names the edition slug a SLOT RECOVERY fire is FOR. It rides the outputs
    # into the fired brief run as SLOT_NAME so wrap.py regenerates THAT slot, instead of
    # resolving by wall clock and regenerating whichever slot the clock says (2026-08-12:
    # a morning recovery firing at 14:23 produced a midday edition, so the morning slot
    # was unrecoverable all day and the watcher re-fired it uselessly every tick).
    print(("WATCHER TRIGGER: " + reason) if trigger else f"watcher: quiet ({reason})")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        open(out, "a").write(f"trigger={'true' if trigger else 'false'}\n"
                             f"breaking={'true' if breaking else 'false'}\n"
                             f"slot={slot}\n"
                             f"reason={reason}\n")


# SLOT RECOVERY (2026-07-15): GitHub cron drift is real on this account (observed slots
# firing 3-7 hours late or never). Each slot's edition file is the proof-of-run; if a
# slot's deadline passed and its edition is absent, the watcher re-fires the full
# pipeline itself (breaking=false: a normal run; wrap's hour windows produce the right
# edition, the one-edition-per-slot skip and dedup guards make it rerun-safe). A slot
# that RAN but FAILED also leaves no edition, so transient failures self-retry too.
SLOT_DEADLINES = (  # (edition slug, deadline minutes-of-UTC-day, window end)
    # Each recovery window is CLAMPED to a boundary wrap.py resolves correctly (the
    # sports desk's rule: a recovery run past the boundary would write the NEXT
    # edition and re-fire until window end). The evening window CROSSES MIDNIGHT
    # (2026-08-31): the old 23:45-24:00 window, keyed on now.date(), made a missed
    # evening slot structurally unrecoverable once the clock passed 00:00, which is
    # why no evening brief published after Aug 22. wrap.py anchors a pre-05:00
    # evening fire to the previous day (SLOT_NAME outranks the clock), so the window
    # runs to 05:00 next day and no further: past 05:00 a recovery would date itself
    # onto the new day.
    # PROGRAM 4, T-1 (2026-09-16). MORNING AND AFTERNOON ARE OUT OF THIS TABLE.
    # The comment above is the rule and this is the case it warns about: a slot listed
    # here with no cron is re-fired daily by the recovery logic. With those two slots
    # disabled their editions are never written, so missed_slot() would report one on
    # every tick, for the rest of time, and each report spends a full model run.
    #
    # It is worse than the retry crons were. Slot recovery is checked BEFORE the
    # cooldown and before the cage, and it fires with breaking=False, so it does not
    # count against the two-a-day breaking cap either. Measured tonight on the sports
    # desk: a watcher tick at 22:21Z published the evening Edition an hour early by
    # exactly this path.
    ("evening-brief", 23 * 60 + 45, 29 * 60),        # cron 23:08; recover 23:45-05:00(+1d)
)


def missed_slot(now=None, content_dir=None):
    """Return the edition slug of a missed slot, or None. Pure function for the canary.

    The edition file is keyed to the SLOT'S OWN day, not now.date(): a window that
    crosses midnight (evening) checks the previous day's file, matching how wrap.py
    dates the recovered edition."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    content_dir = content_dir or os.path.join(HERE, "site", "content")
    minutes = now.hour * 60 + now.minute
    for slug, deadline, window_end in SLOT_DEADLINES:
        slot_day, m = now.date(), minutes
        if window_end > 24 * 60 and minutes < window_end - 24 * 60:
            # in the wrapped hours of a cross-midnight window, the slot's day is
            # yesterday and the clock reads as hour 24+
            slot_day, m = slot_day - datetime.timedelta(days=1), minutes + 24 * 60
        if deadline <= m < window_end and not os.path.exists(
                os.path.join(content_dir, f"{slot_day.isoformat()}-{slug}.json")):
            return slug
    return None


def desk_published_recently():
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=COOLDOWN_MIN))
    for p in glob.glob(os.path.join(HERE, "site", "content", "*.json")):
        try:
            ts = json.load(open(p, encoding="utf-8")).get("published_utc", "")
            when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if when >= cutoff:
                return True
        except Exception:
            continue
    return False


def hourly_move(assets=None, fetch=None, pause=3):
    """Largest 1h AND 24h moves among `assets` (the majors by default), from ONE CoinGecko keyless day
    chart per asset. The 24h read is the same chart's first point vs its last (zero extra
    requests, same fail-quiet posture): it exists because a grinding multi-hour
    drawdown never trips the 1-hour threshold (2026-08-31). `fetch(url)` returns the parsed answer
    (Sprint 9.4: the tests hand in recorded answers)."""
    fetch = fetch or _get_json
    worst = (0.0, "")
    worst24 = (0.0, "")
    for cid, sym in (assets or MAJORS).items():
        try:
            url = (f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
                   f"?vs_currency=usd&days=1")
            prices = (fetch(url) or {}).get("prices", [])
            if len(prices) < 3:
                continue
            now_ts, now_px = prices[-1]
            first_px = prices[0][1]
            if first_px:
                pct24 = (now_px - first_px) / first_px * 100
                if abs(pct24) > abs(worst24[0]):
                    worst24 = (pct24, sym)
            hour_ago = now_ts - 3600_000
            past_px = min(prices, key=lambda p: abs(p[0] - hour_ago))[1]
            if past_px:
                pct = (now_px - past_px) / past_px * 100
                if abs(pct) > abs(worst[0]):
                    worst = (pct, sym)
        except Exception:
            continue  # a flaky feed must never fake a trigger either way
        if pause:
            import time
            time.sleep(pause)  # keyless CoinGecko rate courtesy
    return worst, worst24


def _get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return json.load(r)


# PROGRAM 9, SPRINT 9.4: THE MARKET-MOVE TRIGGER, CRYPTO ONLY (Jack's ruling 6 of October 16, 2026: "the
# market-move breaking trigger on, crypto only, inside the two-a-day limit"; AUDIT.md section 3.1, the row
# "Breaking"; CLAUDE.md P4). On a crypto desk a large move is the reader's question. It fires when Bitcoin or
# the whole market moves 3% or more inside 60 minutes, or 5% or more inside 24 hours, between slots.
#   Bitcoin       hourly_move above, on Bitcoin alone (its day chart: the last hour, and the 24 hours).
#   The market    the Top 100's own change (snapshot.top100_change, the desk's whole-market figure since
#                 Sprint 9.1), from one /coins/markets read carrying the 1h and 24h changes.
#   Between slots never inside SLOT_QUIET_MIN minutes either side of a slot (the slot reports the move
#                 itself), and the 24-hour leg only when the Board the site last published did not already
#                 carry a 5% move the same way (that move is the slot's, not news since).
# INSIDE THE CAGE: it is checked after the PAUSE file, the cooldown and the two-a-day cap, so a capped day
# costs no read at all, and a fire is a breaking run that counts against the two like any other. The old
# price triggers (any major, 5% an hour, 4% a day) stay off: they are not this rule.
MARKET_TRIGGER = (os.environ.get("WATCH_MARKET_TRIGGER") or "1") == "1"
MARKET_1H_PCT = float(os.environ.get("WATCH_MARKET_1H_PCT") or "3.0")
MARKET_24H_PCT = float(os.environ.get("WATCH_MARKET_24H_PCT") or "5.0")
SLOTS_ET = (("the morning read", 8, 17), ("the Edition", 19, 8))   # the Worker's 8:17 AM read, the 7:08 PM cron
SLOT_QUIET_MIN = 60
MARKETS_URL = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
               "&per_page=100&page=1&price_change_percentage=1h,24h")


def near_slot(now=None):
    """The slot `now` falls within SLOT_QUIET_MIN minutes of, or None."""
    from zoneinfo import ZoneInfo
    now = now or datetime.datetime.now(datetime.timezone.utc)
    et = now.astimezone(ZoneInfo("America/New_York"))
    for name, h, m in SLOTS_ET:
        at = et.replace(hour=h, minute=m, second=0, microsecond=0)
        for day in (-1, 0, 1):
            if abs((et - (at + datetime.timedelta(days=day))).total_seconds()) <= SLOT_QUIET_MIN * 60:
                return name
    return None


def _top100(rows, key):
    """The Top 100's change over `key` from CoinGecko market rows, by snapshot.top100_change's rule."""
    import snapshot
    coins = {}
    for c in rows or []:
        if isinstance(c, dict) and c.get("symbol"):
            coins[str(c["symbol"]).upper() + "|" + str(c.get("id"))] = {
                "mcap_usd": c.get("market_cap"), "chg_24h_pct": c.get(key)}
    return snapshot.top100_change(coins)


def market_readings(fetch=None, pause=0):
    """{'BTC': (1h, 24h), 'market': (1h, 24h)}: Bitcoin from hourly_move, the market from one markets read.
    A reading that cannot be made is None, and None never fires."""
    fetch = fetch or _get_json
    out = {"BTC": (None, None), "market": (None, None)}
    (p1, s1), (p24, s24) = hourly_move({"bitcoin": "BTC"}, fetch=fetch, pause=pause)
    if s1 or s24:
        out["BTC"] = (p1 if s1 else None, p24 if s24 else None)
    try:
        rows = fetch(MARKETS_URL)
        out["market"] = (_top100(rows, "price_change_percentage_1h_in_currency"),
                         _top100(rows, "price_change_percentage_24h_in_currency"))
    except Exception:
        pass
    return out


def _carried(pulse):
    """{'BTC': 24h, 'market': 24h} the site's last published Board carried, when it is under 24 hours old."""
    import snapshot
    try:
        gen = datetime.datetime.fromisoformat(str(pulse.get("generated_utc")).replace("Z", "+00:00"))
    except Exception:
        return {}
    if (datetime.datetime.now(datetime.timezone.utc) - gen).total_seconds() > 24 * 3600:
        return {}
    rows = ((pulse.get("movers") or {}).get("top100")) or []
    btc = next((r.get("chg_24h_pct") for r in rows if r.get("symbol") == "BTC"), None)
    return {"BTC": btc, "market": snapshot.top100_change({str(r.get("symbol")) + "|" + str(r.get("gecko_id")): r
                                                          for r in rows})}


def market_trigger(readings, carried=None, now=None):
    """The reason to fire, or None. Pure: the readings, what the site last carried, the clock."""
    slot = near_slot(now)
    if slot:
        return None
    carried = carried or {}
    names = {"BTC": "Bitcoin", "market": "The whole market (the Top 100)"}
    for key in ("BTC", "market"):
        p1, _p24 = readings.get(key) or (None, None)
        if isinstance(p1, (int, float)) and abs(p1) >= MARKET_1H_PCT:
            return (f"MARKET MOVE: {names[key]} moved {p1:+.1f}% in the last hour "
                    f"(threshold {MARKET_1H_PCT:g}% inside 60 minutes)")
    for key in ("BTC", "market"):
        _p1, p24 = readings.get(key) or (None, None)
        if not (isinstance(p24, (int, float)) and abs(p24) >= MARKET_24H_PCT):
            continue
        had = carried.get(key)
        if isinstance(had, (int, float)) and abs(had) >= MARKET_24H_PCT and (had > 0) == (p24 > 0):
            continue                     # the slot already carried a 5% move this way: not news since
        return (f"MARKET MOVE: {names[key]} moved {p24:+.1f}% over the last 24 hours "
                f"(threshold {MARKET_24H_PCT:g}% inside 24 hours, not carried by the last published Board)")
    return None


def hot_cluster():
    """A fresh story carried by many independent sources = something real is breaking."""
    import aggregate
    out_path = os.path.join(HERE, "out", "watcher-items.json")
    try:
        rc = aggregate.run(out_path=out_path)
        if rc != 0:
            return None
    except Exception:
        return None
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=FRESH_MIN))
    for c in json.load(open(out_path, encoding="utf-8")).get("clusters", []):
        try:
            when = datetime.datetime.fromisoformat(
                (c.get("timestamp") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        if when < cutoff or c.get("shill_rejected"):
            continue
        names = {c.get("source", "").strip().lower()} | {
            (x.get("name") or "").strip().lower() for x in (c.get("corroboration") or [])}
        names.discard("")
        if len(names) < MIN_SOURCES:
            continue
        # T-1: several sources are necessary and no longer sufficient. The story has to
        # be in a category that earns.
        cat = earning_category(
            (c.get("headline") or "") + " " + (c.get("summary") or ""))
        if not cat:
            continue
        return f"{cat}: {len(names)} sources on: {c.get('headline','')[:80]}"
    return None


def main():
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        emit(False, "PAUSE file present")
        return 0
    # Slot recovery outranks the cooldown: a missed slot must run even if a breaking run
    # published an hour ago (the edition is the guaranteed product).
    slug = missed_slot()
    if slug:
        emit(True, f"SLOT RECOVERY: {slug} deadline passed with no edition published "
                   f"(cron drifted or the run failed); re-firing the pipeline",
             breaking=False, slot=slug)
        return 0
    if desk_published_recently():
        emit(False, f"desk published within the last {COOLDOWN_MIN}m; coverage is fresh")
        return 0
    # T-1: the day's allowance. Checked before any network call, so a capped day costs
    # nothing at all.
    already = breaking_runs_today()
    if already >= 0 and already >= BREAKING_MAX_PER_DAY:
        emit(False, f"breaking cap reached: {already} of {BREAKING_MAX_PER_DAY} "
                    f"run(s) today")
        return 0
    if PRICE_TRIGGERS:
        (pct, sym), (pct24, sym24) = hourly_move()
        if abs(pct) >= MOVE_PCT:
            emit(True, f"{sym} moved {pct:+.1f}% in the last hour (threshold {MOVE_PCT}%)")
            return 0
        # the grinding-drawdown trigger (2026-08-31): the Aug 27-29 BTC slide from
        # ~$81.4K to sub-$78K was -4.2% in total, so the 1-hour trigger provably could
        # not fire
        if abs(pct24) >= MOVE_24H_PCT:
            emit(True, f"{sym24} moved {pct24:+.1f}% over the last 24 hours "
                       f"(threshold {MOVE_24H_PCT}%)")
            return 0
    # SPRINT 9.4: the market-move trigger, crypto only, inside the cage (after the cap above)
    if MARKET_TRIGGER:
        try:
            pulse = json.load(open(os.path.join(HERE, "site", "data", "pulse.json"), encoding="utf-8"))
        except Exception:
            pulse = {}
        slot = near_slot()
        if slot:
            print(f"watcher: market-move trigger quiet within {SLOT_QUIET_MIN} minutes of {slot}")
        else:
            why = market_trigger(market_readings(), _carried(pulse))
            if why:
                emit(True, why + f" (run {already + 1} of {BREAKING_MAX_PER_DAY} today)")
                return 0
    hot = hot_cluster()
    if hot:
        emit(True, hot + f" (threshold {MIN_SOURCES} sources / {FRESH_MIN}m, "
                         f"run {already + 1} of {BREAKING_MAX_PER_DAY} today)")
        return 0
    emit(False, f"no {MIN_SOURCES}-source fresh cluster in an earning category "
                f"({already} of {BREAKING_MAX_PER_DAY} breaking run(s) used today; "
                f"price triggers {'on' if PRICE_TRIGGERS else 'off'}; market-move trigger "
                f"{'on' if MARKET_TRIGGER else 'off'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
