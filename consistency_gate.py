#!/usr/bin/env python3
"""
consistency_gate.py: the cross-surface tripwire (audit item 1, 2026-07-27). A fact-checking
brand must never contradict itself within one viewport. The live homepage did: the lead
story reported a third straight week of spot ETF INFLOWS (true, Farside) while the Chart
Master blurb said "spot ETF outflows persist" (a two-day daily print stretched into a
regime). This gate makes that class of publish impossible.

DESIGN, deliberately grep-class (the audit's words: it needs a tripwire, not intelligence):
  - SURFACES that co-render on the homepage, read from the exact files about to ship:
    the newest story cards (title/dek/key_fact, plus bottom_line for Daily Editions),
    the Chart Master read (headline + paragraphs), and the whale-board teaser direction.
  - METRICS: a small high-collision set (spot ETF flows, bitcoin price direction,
    dominance, whale exchange flows). For each, a context regex and a positive/negative
    direction lexicon within a character window.
  - CONFLICT: two surfaces each assert exactly ONE direction on the same metric and they
    disagree. A surface that states BOTH directions is dual-grain phrasing ("two daily
    outflows cap a net-inflow week"): coherent, not a contradiction.
  - FAIL-CLOSED: any conflict exits non-zero. In the brief workflow this step runs before
    the commit/push step, so a contradicting run publishes nothing and goes red for a
    human, like every other gate.

USAGE  python3 consistency_gate.py          (exit 0 = coherent, 1 = contradiction)
"""

import datetime
import glob
import json
import os
import re
import sys

import consistency

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")
DATA = os.path.join(HERE, "site", "data")

TOP_STORIES = 8  # how many newest stories share the homepage viewport

# Shared window vocabulary. Defined once so four metrics cannot drift into four slightly
# different ideas of what "this week" means.
DAY_WINDOW = (r"\b(24\s*hours?|daily|today|yesterday|overnight|session|sessions"
              r"|last\s+day|intraday)\b")
WEEK_WINDOW = (r"\b(week(?:ly|s)?|7\s*days?|five\s+sessions?|5\s+sessions?"
               r"|last\s+\d\s+sessions?)\b")
MONTH_WINDOW = (r"\b(month(?:ly|s)?|30\s*days?|90\s*days?|quarter(?:ly)?|year"
                r"|12-month|ytd|year-to-date)\b")

METRICS = {
    # scoped=True: this metric's direction claims are bucketed by their stated window
    # (weekly vs daily), because both can be true at once (a net-inflow week ending in
    # outflow days, the state that recurred 2026-07-27). Claims at DIFFERENT stated
    # windows do not collide; an UNSCOPED direction claim ("outflows persist") collides
    # with every window, so lazy phrasing still blocks the publish. This makes the gate
    # enforce what the Chart Master and Edition prompts already demand: name the window.
    "spot ETF flows": {
        "context": r"\betfs?\b", "span": 90, "scoped": True,
        "week": r"\bweek(?:ly|s)?\b",
        "day": r"\b(?:daily|day|days|sessions?|today|yesterday|latest|on\s+"
               r"(?:january|february|march|april|may|june|july|august|september"
               r"|october|november|december)\b)",
        "pos": r"\binflows?\b|\b(?:ran|runs?|turn(?:s|ed)?|went|goes|stays?|stayed)\s+positive\b",
        "neg": r"\boutflows?\b|\b(?:ran|runs?|turn(?:s|ed)?|went|goes|stays?|stayed)\s+negative\b"},
    # Scoped for the same reason ETF and whale flows are. Found by audit on 2026-07-29
    # rather than by another blocked publish: "bitcoin fell today" and "bitcoin rose over
    # the week" are both routinely true, and unscoped these two metrics read that as a
    # contradiction and stop everything. Any metric whose underlying number is reported at
    # more than one window needs scoping; that is now all four.
    "bitcoin price": {
        "context": r"\b(bitcoin|btc)\b", "span": 60, "scoped": True,
        "scopes": ("month", "week", "day"),
        "day": DAY_WINDOW, "week": WEEK_WINDOW, "month": MONTH_WINDOW,
        "pos": r"\b(rose|rises?|rallies|rallied|climbs?|climbed|gains?|gained|jumps?"
               r"|jumped|surges?|surged)\b",
        "neg": r"\b(fell|falls?|drops?|dropped|declines?|declined|slides?|slid|slumps?"
               r"|slumped|sinks?|sank|tumbles?|tumbled)\b"},
    "bitcoin dominance": {
        "context": r"\bdominance\b", "span": 50, "scoped": True,
        "scopes": ("month", "week", "day"),
        "day": DAY_WINDOW, "week": WEEK_WINDOW, "month": MONTH_WINDOW,
        "pos": r"\b(rose|rising|climbs?|climbed|grew|growing|higher)\b",
        "neg": r"\b(fell|falling|drops?|dropped|shrank|shrinking|lower)\b"},
    # Scoped for the same reason ETF flows is, found the hard way on 2026-07-29: the
    # Whale Watch board widens its window to 48 hours when the 24-hour feed is quiet, and
    # then reports a 2-day net OFF exchanges while the Chart Master correctly reports the
    # 24-hour net ONTO them. Both true, different windows, and an unscoped metric read
    # them as a contradiction and blocked every publish. Scope names differ from ETF's
    # because these surfaces talk in hours and days, not weeks.
    "whale exchange flows": {
        "context": r"\bwhales?\b", "span": 100, "scoped": True,
        "scopes": ("multiday", "day"),
        "day": r"\b(24\s*hours?|last\s+day|today|overnight|latest\s+session)\b",
        "multiday": r"\b(\d+\s*days?|48\s*hours?|72\s*hours?|week(?:ly|s)?"
                    r"|multi-?day|13-week)\b",
        "pos": r"\b(off exchanges?|cold storage|self-custody|accumulat\w+)\b",
        "neg": r"\b(onto exchanges?|sell pressure)\b"},
}


def directions(text, m):
    """Directions this text asserts for one metric, keyed by stated window. Unscoped
    metrics use the single key ''; a scoped metric buckets each claim as 'week', 'day',
    or '' (no window named). One claim can land in both week and day buckets when the
    sentence names both, which is exactly the dual-grain phrasing that never collides."""
    found = {}
    low = (text or "").lower()
    for c in re.finditer(m["context"], low):
        window = low[max(0, c.start() - m["span"]): c.end() + m["span"]]
        dirs = set()
        if re.search(m["pos"], window):
            dirs.add("pos")
        if re.search(m["neg"], window):
            dirs.add("neg")
        if not dirs:
            continue
        scopes = [""]
        if m.get("scoped"):
            names = m.get("scopes", ("week", "day"))
            scopes = ([s for s in names if re.search(m[s], window)] or [""])
        for s in scopes:
            found.setdefault(s, set()).update(dirs)
    return found


def surfaces():
    """(name, text) for everything that co-renders on the homepage, from the files that
    are about to ship."""
    out = []
    stories = []
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("example"):
            continue
        when = d.get("published_utc") or (d.get("date", "") + "T00:00:00Z")
        stories.append((when, d))
    stories.sort(key=lambda t: t[0], reverse=True)
    for when, d in stories[:TOP_STORIES]:
        text = " ".join(str(d.get(k) or "") for k in ("title", "dek", "key_fact"))
        if (d.get("category") or "").lower() == "daily edition":
            text += " " + str(d.get("bottom_line") or "")
        out.append((f"story:{d.get('slug', '?')}", text, when))
    try:
        cm = json.load(open(os.path.join(DATA, "chartmaster.json"), encoding="utf-8"))
        out.append(("chart-master",
                    " ".join([str(cm.get("headline") or "")] +
                             [str(p) for p in cm.get("paragraphs") or []]), None))
    except Exception:
        pass
    try:
        fl = json.load(open(os.path.join(DATA, "flows.json"), encoding="utf-8"))
        direction = (fl.get("volatile") or {}).get("direction") or ""
        if direction and not fl.get("example"):
            # Name the window. The board widens to 48h on a quiet feed, and a bare
            # "whales net off exchanges" then collides with an honest 24-hour claim
            # somewhere else on the page. flows.json has always known the window; the
            # gate just was not being told.
            hours = fl.get("window_hours") or 24
            when = "over the last 24 hours" if hours <= 24 else \
                   f"over the last {round(hours / 24)} days"
            out.append(("whale-board", f"whales net {direction} {when}", None))
    except Exception:
        pass
    return out


def _stale(when, days=1):
    """True when a surface was frozen on an earlier calendar day than today (UTC).

    A published edition is a record of what the desk said at a moment; the boards are
    live and keep moving. Yesterday's edition saying whales moved onto exchanges is not a
    contradiction of today's board saying they moved off, it is the passage of time. This
    also removes a deadlock found on 2026-07-29: a frozen edition whose claim a later
    board refresh contradicted blocked EVERY subsequent publish, and the blocked publishes
    were the only thing that would have aged it out of the homepage window."""
    if not when:
        return False
    try:
        d = datetime.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except Exception:
        return False
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now.date() - d.date()).days >= days



def _day(when):
    """The UTC calendar day a surface was frozen on, or '' when it is live/unknown."""
    if not when:
        return ""
    try:
        return datetime.datetime.fromisoformat(str(when).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return ""

def conflicts(surface_list=None):
    """Every pair of surfaces asserting opposite single directions on the same metric at
    a colliding window. Same stated window collides; an unscoped claim ('') collides with
    every window; week-vs-day both stated do not collide (both can be true at once). A
    surface asserting both directions at one window is dual-grain phrasing and exempt.

    Claims frozen on an earlier day do not collide with live boards; see _stale. They
    still collide with each other, because two stories on one homepage contradicting each
    other is a reporting problem no matter when either was written."""
    surf = surface_list if surface_list is not None else surfaces()
    surf = [(t + (None,))[:3] if len(t) == 2 else t for t in surf]
    found = []
    for name, m in METRICS.items():
        takes = []  # (surface, scope, direction, stale?) single-direction claims only
        for sname, text, when in surf:
            for scope, dirs in directions(text, m).items():
                if len(dirs) == 1:
                    takes.append((sname, scope, next(iter(dirs)), _stale(when), _day(when)))
        for i in range(len(takes)):
            for j in range(i + 1, len(takes)):
                (sa, ca, da, xa, ya), (sb, cb, db, xb, yb) = takes[i], takes[j]
                if sa == sb or da == db:
                    continue
                # one side frozen on an earlier day, the other live: time, not conflict
                live = {"chart-master", "whale-board"}
                if (xa and sb in live) or (xb and sa in live):
                    continue
                # TWO EDITIONS FROM DIFFERENT DAYS ARE NOT IN CONFLICT (owner audit
                # 2026-08-25). Every metric this gate tracks is a market DIRECTION, and a
                # direction is a fact about a day: whales moved onto exchanges on Monday
                # and off them on Wednesday, and both editions were right when written.
                # Colliding them made the gate fail every run once the flow reversed,
                # which is alarm fatigue on a gate whose whole value is being believed.
                # Two surfaces from the SAME day still collide, because that is one
                # homepage contradicting itself, which is the reporting problem this gate
                # exists to catch.
                if sa not in live and sb not in live and ya and yb and ya != yb:
                    continue
                if ca == cb or ca == "" or cb == "":
                    found.append({"metric": name,
                                  "a": sa, "a_dir": da, "a_scope": ca or "unscoped",
                                  "b": sb, "b_dir": db, "b_scope": cb or "unscoped"})
    return found


# Asset-class and market-structure words shared across unrelated headlines; a pair must
# share a token beyond these before its figures are comparable.
_GENERIC_MARKET_TOKENS = {
    "etf", "etfs", "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "crypto", "cryptocurrency", "stablecoin", "stablecoins", "token", "tokens",
    "exchange", "exchanges", "blockchain", "defi",
}


def figure_conflicts_live(within_days=30):
    """Live-vs-live USD figure sweep (Avici audit 2026-08-31). The figure belt
    (consistency.figure_conflicts) only ever judges a NEW candidate at publish time, and
    autopilot exempts updates from it entirely, so two already-live stories carried >$1M
    and $500,859 for the same Avici drain and nothing ever compared them. This sweeps
    every live pair from the last within_days sharing a headline-level primary entity
    and flags same-magnitude (max/min <= 3), materially different (>15%) USD figures
    from title+key_fact, the same bar the belt uses. A pair is exempt only when the
    newer story's update_of names the older AND the older carries a non-empty
    'corrected' note: an acknowledged lineage whose origin still asserts the stale
    number is exactly the contradiction this exists to catch.

    Hits come back in the conflict-dict shape conflicts() uses, so main() routes them
    through the same scoping: block only what this run wrote, warn + flag issue for
    pre-existing pairs (never the 2026-07-28..30 deadlock class)."""
    recs = []
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("id", "")).startswith("wrap-") or d.get("example"):
            continue
        when = d.get("published_utc") or (d.get("date", "") + "T00:00:00Z")
        recs.append((when, d))
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=within_days)).isoformat()
    recs = sorted((r for r in recs if r[0] >= cutoff), key=lambda t: t[0])
    # RECURRING ACTORS DO NOT PAIR ALONE (2026-09-03, run 33768445949): "fbi" paired an
    # agent's $1M theft with a $560K Hamas seizure and blocked the publish. See
    # consistency.comparable_pair.
    found = []
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            older, newer = recs[i][1], recs[j][1]
            # mag: tokens are figure fingerprints, not names; pairing on one would
            # collide any two stories whose titles carry same-magnitude numbers. Broad
            # market vocabulary is likewise no identity: 'etfs' paired an $853M bitcoin
            # flow story with a $1.4B ethereum one on this sweep's first corpus run.
            # The desk's direction metrics already cover the big-asset surfaces.
            shared = {e for e in (consistency.primary_entities(older.get("title", ""))
                                  & consistency.primary_entities(newer.get("title", "")))
                      if not e.startswith("mag:")}
            shared = consistency.comparable_pair(shared, _GENERIC_MARKET_TOKENS)
            if not shared:
                continue
            if (newer.get("update_of") == older.get("slug")
                    and (older.get("corrected") or "").strip()):
                continue
            figs_a = consistency.usd_figures(
                f"{older.get('title', '')} {older.get('key_fact', '')}")
            figs_b = consistency.usd_figures(
                f"{newer.get('title', '')} {newer.get('key_fact', '')}")
            hit = None
            for fa in figs_a:
                for fb in figs_b:
                    hi, lo = max(fa, fb), min(fa, fb)
                    if lo <= 0:
                        continue
                    if hi / lo <= 3 and (hi - lo) / hi > 0.15:
                        hit = (fa, fb)
                        break
                if hit:
                    break
            if hit:
                found.append({"metric": f"USD figure: {sorted(shared)[0]}",
                              "a": f"story:{older.get('slug', '?')}",
                              "a_dir": f"${hit[0]:,.0f}", "a_scope": "title/key_fact",
                              "b": f"story:{newer.get('slug', '?')}",
                              "b_dir": f"${hit[1]:,.0f}", "b_scope": "title/key_fact"})
    return found


def _changed_paths():
    """Repo-relative paths this run has modified or created (uncommitted, so at gate
    time that is exactly the run's own output). None when git cannot answer, and the
    caller must then fail closed and treat every conflict as blocking."""
    import subprocess
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=HERE,
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None
        return {ln[3:].strip().strip('"') for ln in r.stdout.splitlines() if len(ln) > 3}
    except Exception:
        return None


def surface_paths():
    """surface name -> repo-relative source file, mirroring surfaces()."""
    out = {"chart-master": "site/data/chartmaster.json",
           "whale-board": "site/data/flows.json"}
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        out[f"story:{d.get('slug', '?')}"] = os.path.relpath(p, HERE)
    return out


def _flag_issue(lines):
    """Open ONE issue for live-vs-live contradictions (dedup by title). A pre-existing
    conflict must ping a human loudly, precisely because the gate no longer kills runs
    over it. No token -> the workflow log warning is the whole alarm."""
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        print("::notice::no GITHUB_TOKEN in env; live-vs-live contradiction reported in "
              "log only")
        return
    import urllib.request
    title = "Consistency: live surfaces contradict (human retire/correct needed)"
    hdrs = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues?state=open&labels=pipeline",
            headers=hdrs)
        if any(i["title"] == title for i in json.load(urllib.request.urlopen(req))):
            print("live-contradiction issue already open; not duplicating")
            return
        body = ("The consistency gate found contradictions between surfaces that are "
                "ALREADY live and that this run did not write. Publishing was allowed "
                "(blocking could not have removed them; it only starved the desk, the "
                "2026-07-28..30 deadlock class). A human needs to retire or correct the "
                "wrong surface.\n\n" + "\n".join(f"- {ln}" for ln in lines) +
                "\n\nClose after the surface is corrected or ages off the homepage.")
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues",
            data=json.dumps({"title": title, "body": body,
                             "labels": ["pipeline"]}).encode(),
            headers=hdrs, method="POST")
        urllib.request.urlopen(req)
        print("live-contradiction issue opened")
    except Exception as e:
        print(f"::warning::could not file the live-contradiction issue: {e}")


def main():
    bad = conflicts() + figure_conflicts_live()
    if not bad:
        print("consistency gate: homepage surfaces agree on every checked metric.")
        return 0
    # FAIL-CLOSED IS SCOPED TO WHAT THIS RUN WROTE (2026-08-02, from the failure
    # taxonomy): the gate's job is to stop THIS RUN from shipping a new contradiction.
    # AUTHORED text the run produced (a story, the Chart Master read) that collides with
    # anything still blocks, hard. But a contradiction between two surfaces the run did
    # not write is already on the live site whether or not we publish; blocking cannot
    # remove it, and through 2026-07-28..30 it only deadlocked the desk while the fix
    # (fresh coverage aging the stale claim off the homepage) was the very thing being
    # blocked. Those now warn + open a flag issue instead. A refreshed data board
    # (flows.json) is data, not authorship: the tape moving against an already-live
    # sentence is the passage of time, and holding back the tape is not an option.
    changed = _changed_paths()
    paths = surface_paths()
    authored = lambda s: s.startswith("story:") or s == "chart-master"

    def run_wrote(s):
        if changed is None:
            return True  # git unavailable: fail closed, everything blocks
        return authored(s) and paths.get(s) in changed

    blocking, preexisting = [], []
    for c in bad:
        (blocking if run_wrote(c["a"]) or run_wrote(c["b"]) else preexisting).append(c)

    def describe(c):
        return (f"'{c['metric']}' contradiction: {c['a']} says {c['a_dir']} "
                f"({c['a_scope']}) but {c['b']} says {c['b_dir']} ({c['b_scope']}).")

    for c in blocking:
        print(f"::error::consistency gate: {describe(c)} This run wrote one of these "
              f"surfaces. Two surfaces on one viewport may not assert opposite "
              f"directions at a colliding window; name the window or fix the wrong "
              f"surface before anything publishes.")
    if preexisting:
        lines = [describe(c) for c in preexisting]
        for ln in lines:
            print(f"::warning::consistency gate (pre-existing, not this run's writing): "
                  f"{ln} Publish allowed; a human must retire or correct the wrong "
                  f"surface.")
        _flag_issue(lines)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
