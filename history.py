#!/usr/bin/env python3
"""history.py: the stored daily closes (Jack, 6 October 2026).

The Board's history used to be a 365-day read of CoinGecko's `/coins/{id}/market_chart`
on every run, seven coins in a row. On 2 October that read started meeting a 429, and the
section was carried forward from the 2 October file under a log line nobody reads, four
days running. The history is now a series the site owns:

  data/history/<coin id>.json   {"coin", "symbol", "source", "through", "closes": {date: close}}

One file per coin the Board covers, daily closes keyed by UTC date, committed by the run.
`through` is the last UTC day the file holds a close for, and it is the series' stamp.

- A run APPENDS and never refetches. When the file's through date is within seven days,
  the run reads `market_chart` for the few days it is missing (two at least), takes the
  close of each completed UTC day after `through`, and stores each date once; a date
  already present is never written again. A file already through yesterday costs no call.
- A missing file, or one more than seven days behind, is BOOTSTRAPPED from a 365-day
  read, and only one coin per run, so a bootstrap never bursts the free tier.
- A failed append leaves the file at its through date. The tiles computed from the
  series print "closes through <date>" and the stale mark once the through date is 48
  hours or more behind the run. A series is not a reading: it never sets the page stamp.

The close of UTC day D is the last price CoinGecko gives with a timestamp after D 00:00
and at or before D+1 00:00 UTC. Daily points are stamped at 00:00, so the point stamped
D+1 00:00 is D's close; hourly points give the last hour of D.
"""
import datetime as _dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HIST_DIR = os.path.join(HERE, "data", "history")
ENDPOINT = "CoinGecko /coins/{id}/market_chart"
URL = ("https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
       "?vs_currency=usd&days={days}")
APPEND_WITHIN_DAYS = 7
BOOTSTRAP_DAYS = 365
STALE_HOURS = 48


def _today(now):
    return (now or _dt.datetime.now(_dt.timezone.utc)).astimezone(_dt.timezone.utc).date()


def path(cid, root=None):
    return os.path.join(root or HIST_DIR, f"{cid}.json")


def load(cid, root=None):
    try:
        s = json.load(open(path(cid, root), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(s, dict) or not isinstance(s.get("closes"), dict):
        return None
    return s


def save(series, root=None):
    p = path(series["coin"], root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    closes = series["closes"]
    series["through"] = max(closes) if closes else ""
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"coin": series["coin"], "symbol": series.get("symbol", ""),
                   "source": ENDPOINT.replace("{id}", series["coin"]),
                   "through": series["through"],
                   "closes": {d: closes[d] for d in sorted(closes)}}, fh, indent=0)
        fh.write("\n")
    os.replace(tmp, p)


def utc_day_closes(points):
    """{date: close} from CoinGecko's [[ms, price], ...]. Every day that has a point is
    returned, the current one included; `completed()` drops the days not yet over."""
    out, at = {}, {}
    for p in points or []:
        if not p or len(p) < 2 or not isinstance(p[1], (int, float)) or not p[1]:
            continue
        t = _dt.datetime.fromtimestamp(p[0] / 1000, tz=_dt.timezone.utc)
        # a point exactly at midnight closes the day before it
        d = (t - _dt.timedelta(microseconds=1)).date().isoformat()
        if d not in at or t >= at[d]:
            at[d], out[d] = t, p[1]
    return out


def completed(closes, now=None):
    """Only the UTC days that have ended by `now`."""
    today = _today(now).isoformat()
    return {d: v for d, v in closes.items() if d < today}


def append(series, new_closes):
    """Store each new date once. A date already in the series is never overwritten.
    Returns the dates stored."""
    have = series.setdefault("closes", {})
    added = []
    for d in sorted(new_closes):
        if d in have:
            continue
        have[d] = new_closes[d]
        added.append(d)
    return added


def gap_days(series, now=None):
    """Days between the series' through date and yesterday; None with no series."""
    if not series or not series.get("closes"):
        return None
    through = _dt.date.fromisoformat(max(series["closes"]))
    return ((_today(now) - _dt.timedelta(days=1)) - through).days


def needs_bootstrap(series, now=None):
    g = gap_days(series, now)
    return g is None or g > APPEND_WITHIN_DAYS


def update(cid, sym, fetch, now=None, root=None, allow_bootstrap=True):
    """Bring one coin's series up to yesterday. `fetch(url)` returns the parsed JSON or
    raises. Returns (series or None, status, reason):

      status "current"    already through yesterday, no call made
              "appended"   the missing completed days stored
              "bootstrap"  built from a 365-day read
              "failed"     the read failed; the file is unchanged (reason names it)
              "waiting"    needs a bootstrap and this run's one bootstrap is spent
    """
    series = load(cid, root)
    if needs_bootstrap(series, now):
        if not allow_bootstrap:
            return series, "waiting", (f"{sym}: no stored series within "
                                       f"{APPEND_WITHIN_DAYS} days; bootstraps on a later "
                                       f"run (one per run)")
        url = URL.format(cid=cid, days=BOOTSTRAP_DAYS)
        try:
            d = fetch(url)
        except Exception as e:
            return series, "failed", (f"{sym}: {ENDPOINT.replace('{id}', cid)} "
                                      f"days={BOOTSTRAP_DAYS} failed ({e})")
        fresh = {"coin": cid, "symbol": sym, "closes": {}}
        if series:                         # keep what the old file holds, add the rest
            fresh["closes"] = dict(series["closes"])
        append(fresh, completed(utc_day_closes((d or {}).get("prices")), now))
        save(fresh, root)
        return fresh, "bootstrap", ""
    g = gap_days(series, now)
    if g <= 0:
        return series, "current", ""
    days = max(2, g + 1)
    url = URL.format(cid=cid, days=days)
    try:
        d = fetch(url)
    except Exception as e:
        return series, "failed", (f"{sym}: {ENDPOINT.replace('{id}', cid)} days={days} "
                                  f"failed ({e}); series stays through "
                                  f"{series.get('through') or max(series['closes'])}")
    through = max(series["closes"])
    new = {k: v for k, v in completed(utc_day_closes((d or {}).get("prices")), now).items()
           if k > through}
    append(series, new)
    series.setdefault("coin", cid)
    series.setdefault("symbol", sym)
    save(series, root)
    return series, "appended", ""


def closes(series):
    """(dates, values) in date order."""
    c = (series or {}).get("closes") or {}
    ds = sorted(c)
    return ds, [c[d] for d in ds]


def is_stale(through, now=None):
    """The stale mark: the through date is 48 hours or more behind the run, measured from
    the through date's own 00:00 UTC. Through yesterday is never stale; through the day
    before yesterday always is."""
    try:
        t = _dt.datetime.fromisoformat(str(through)).replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return True
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return (now - t).total_seconds() >= STALE_HOURS * 3600


def through_label(through):
    """'closes through Oct 5'."""
    try:
        d = _dt.date.fromisoformat(str(through))
    except ValueError:
        return ""
    return f"closes through {d.strftime('%b')} {d.day}"
