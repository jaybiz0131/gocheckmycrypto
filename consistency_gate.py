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
    "spot ETF flows": {
        "context": r"\betfs?\b", "span": 90,
        "pos": r"\binflows?\b",
        "neg": r"\boutflows?\b"},
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
    "whale exchange flows": {
        "context": r"\bwhales?\b", "span": 100,
        "pos": r"\b(off exchanges?|cold storage|self-custody|accumulat\w+)\b",
        "neg": r"\b(onto exchanges?|sell pressure)\b"},
}


def directions(text, m):
    """The set of directions ('pos'/'neg') this text asserts for one metric."""
    found = set()
    low = (text or "").lower()
    for c in re.finditer(m["context"], low):
        window = low[max(0, c.start() - m["span"]): c.end() + m["span"]]
        if re.search(m["pos"], window):
            found.add("pos")
        if re.search(m["neg"], window):
            found.add("neg")
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
            out.append(("whale-board", f"whales net {direction}"))
    except Exception:
        pass
    return out


def conflicts(surface_list=None):
    """Every (metric, surface A, dir, surface B, dir) pair where two single-direction
    surfaces disagree."""
    surf = surface_list if surface_list is not None else surfaces()
    found = []
    for name, m in METRICS.items():
        takes = [(sname, d) for sname, text in surf
                 for d in [directions(text, m)] if len(d) == 1]
        for i in range(len(takes)):
            for j in range(i + 1, len(takes)):
                if takes[i][1] != takes[j][1]:
                    found.append({"metric": name,
                                  "a": takes[i][0], "a_dir": next(iter(takes[i][1])),
                                  "b": takes[j][0], "b_dir": next(iter(takes[j][1]))})
    return found


def main():
    bad = conflicts()
    if not bad:
        print("consistency gate: homepage surfaces agree on every checked metric.")
        return 0
    for c in bad:
        print(f"::error::consistency gate: '{c['metric']}' contradiction: "
              f"{c['a']} says {c['a_dir']} but {c['b']} says {c['b_dir']}. "
              f"Two surfaces on one viewport may not assert opposite directions; "
              f"fix the wrong one before anything publishes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
