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
MIN_SOURCES = int(os.environ.get("WATCH_MIN_SOURCES") or "4")
FRESH_MIN = int(os.environ.get("WATCH_FRESH_MIN") or "90")
COOLDOWN_MIN = int(os.environ.get("WATCH_COOLDOWN_MIN") or "120")


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
    ("morning-brief", 12 * 60 + 10, 17 * 60),        # cron 10:40; recover 12:10-17:00
    ("afternoon-brief", 18 * 60 + 40, 23 * 60),      # cron 17:08; recover 18:40-23:00
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


def hourly_move():
    """Largest 1h AND 24h moves among the majors, from ONE CoinGecko keyless day chart
    per asset. The 24h read is the same chart's first point vs its last (zero extra
    requests, same fail-quiet posture): it exists because a grinding multi-hour
    drawdown never trips the 1-hour threshold (2026-08-31)."""
    worst = (0.0, "")
    worst24 = (0.0, "")
    for cid, sym in MAJORS.items():
        try:
            url = (f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
                   f"?vs_currency=usd&days=1")
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=25) as r:
                prices = json.load(r).get("prices", [])
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
        import time
        time.sleep(3)  # keyless CoinGecko rate courtesy
    return worst, worst24


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
        if len(names) >= MIN_SOURCES:
            return f"{len(names)} sources on: {c.get('headline','')[:80]}"
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
    (pct, sym), (pct24, sym24) = hourly_move()
    if abs(pct) >= MOVE_PCT:
        emit(True, f"{sym} moved {pct:+.1f}% in the last hour (threshold {MOVE_PCT}%)")
        return 0
    # the grinding-drawdown trigger (2026-08-31): the Aug 27-29 BTC slide from ~$81.4K
    # to sub-$78K was -4.2% in total, so the 1-hour trigger provably could not fire
    if abs(pct24) >= MOVE_24H_PCT:
        emit(True, f"{sym24} moved {pct24:+.1f}% over the last 24 hours "
                   f"(threshold {MOVE_24H_PCT}%)")
        return 0
    hot = hot_cluster()
    if hot:
        emit(True, hot + f" (threshold {MIN_SOURCES} sources / {FRESH_MIN}m)")
        return 0
    emit(False, f"max 1h move {sym} {pct:+.1f}%, max 24h move {sym24} {pct24:+.1f}%, "
                f"no {MIN_SOURCES}-source fresh cluster")
    return 0


if __name__ == "__main__":
    sys.exit(main())
