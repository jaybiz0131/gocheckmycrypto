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

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")
DATA = os.path.join(HERE, "site", "data")

TOP_STORIES = 8  # how many newest stories share the homepage viewport

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
    "bitcoin price": {
        "context": r"\b(bitcoin|btc)\b", "span": 60,
        "pos": r"\b(rose|rises?|rallies|rallied|climbs?|climbed|gains?|gained|jumps?"
               r"|jumped|surges?|surged)\b",
        "neg": r"\b(fell|falls?|drops?|dropped|declines?|declined|slides?|slid|slumps?"
               r"|slumped|sinks?|sank|tumbles?|tumbled)\b"},
    "bitcoin dominance": {
        "context": r"\bdominance\b", "span": 50,
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
    for _, d in stories[:TOP_STORIES]:
        text = " ".join(str(d.get(k) or "") for k in ("title", "dek", "key_fact"))
        if (d.get("category") or "").lower() == "daily edition":
            text += " " + str(d.get("bottom_line") or "")
        out.append((f"story:{d.get('slug', '?')}", text))
    try:
        cm = json.load(open(os.path.join(DATA, "chartmaster.json"), encoding="utf-8"))
        out.append(("chart-master",
                    " ".join([str(cm.get("headline") or "")] +
                             [str(p) for p in cm.get("paragraphs") or []])))
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
            out.append(("whale-board", f"whales net {direction} {when}"))
    except Exception:
        pass
    return out


def conflicts(surface_list=None):
    """Every pair of surfaces asserting opposite single directions on the same metric at
    a colliding window. Same stated window collides; an unscoped claim ('') collides with
    every window; week-vs-day both stated do not collide (both can be true at once). A
    surface asserting both directions at one window is dual-grain phrasing and exempt."""
    surf = surface_list if surface_list is not None else surfaces()
    found = []
    for name, m in METRICS.items():
        takes = []  # (surface, scope, direction) for single-direction claims only
        for sname, text in surf:
            for scope, dirs in directions(text, m).items():
                if len(dirs) == 1:
                    takes.append((sname, scope, next(iter(dirs))))
        for i in range(len(takes)):
            for j in range(i + 1, len(takes)):
                (sa, ca, da), (sb, cb, db) = takes[i], takes[j]
                if sa == sb or da == db:
                    continue
                if ca == cb or ca == "" or cb == "":
                    found.append({"metric": name,
                                  "a": sa, "a_dir": da, "a_scope": ca or "unscoped",
                                  "b": sb, "b_dir": db, "b_scope": cb or "unscoped"})
    return found


def main():
    bad = conflicts()
    if not bad:
        print("consistency gate: homepage surfaces agree on every checked metric.")
        return 0
    for c in bad:
        print(f"::error::consistency gate: '{c['metric']}' contradiction: "
              f"{c['a']} says {c['a_dir']} ({c['a_scope']}) but {c['b']} says "
              f"{c['b_dir']} ({c['b_scope']}). Two surfaces on one viewport may not "
              f"assert opposite directions at a colliding window; name the window or "
              f"fix the wrong surface before anything publishes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
