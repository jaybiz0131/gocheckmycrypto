#!/usr/bin/env python3
"""
consistency.py: a deterministic cross-corpus figure-consistency belt (review feedback,
2026-07-23). The verifier checks each story against ITS OWN sources; it never checks a
story's numbers against the desk's other published numbers. So two stories could give
different figures for the same thing (the Ostium "$18M vs $24M" the review flagged) and
both pass. This belt catches that class before auto-publish and routes it to human review.

Scope, deliberately narrow to keep false positives near zero:
  - Only same PRIMARY ENTITY (a distinctive proper noun the two stories share).
  - Only figures of the SAME ORDER OF MAGNITUDE (max/min <= 3): $18M vs $24M is one
    quantity revised; $18M loss vs $50B market cap are different quantities, not a conflict.
  - Only a MATERIAL gap (> 15%).
  - Acknowledged updates are exempt: a story published as an update of the earlier one is
    SUPPOSED to revise the figure, so the caller passes update_of and that story is skipped.

A hit is a HOLD-for-human signal, not a silent drop: the human queue adjudicates. Reused by
autopilot before it auto-approves a non-update story.
"""

import datetime
import glob
import json
import os
import re

from autopilot import _signature, _OUTLETS

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")

_MULT = {"trillion": 1e12, "t": 1e12, "billion": 1e9, "bn": 1e9, "b": 1e9,
         "million": 1e6, "mn": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
_USD = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)\s?(trillion|billion|million|thousand|bn|mn|[tbmk])?\b", re.I)


def usd_figures(text):
    """Every dollar amount in the text, normalized to USD floats."""
    out = []
    for m in _USD.finditer(text or ""):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        out.append(v * _MULT.get((m.group(2) or "").lower(), 1))
    return out


def primary_entities(title, key_fact=""):
    """Distinctive named entities (proper nouns), dropping bare numbers and outlet names."""
    return {t for t in _signature(title, key_fact) if not t.replace(".", "").isdigit()} - _OUTLETS


# A RECURRING ACTOR IS NOT AN IDENTITY (2026-09-03, run 33768445949). The figure belts
# pair two stories on ONE shared headline entity, and "fbi" paired "FBI supervisory agent
# arrested for stealing $1 million" with "DOJ says FBI seized $560K in Hamas
# cryptocurrency": two unrelated events, one institution, and the gate blocked the whole
# publish. An institution, venue, issuer or state that headlines unrelated events every
# week names an ACTOR, not an event; a figure pair keyed on it alone says nothing. A
# subject entity (a protocol with one exploit, Avici) still pairs on its own, which is
# exactly the case the belt exists for, and two shared entities always pair. Grep-class
# by design, like the gate's own generic-market list; extend it when a new actor trips.
RECURRING_ACTORS = frozenset("""
fbi sec doj cftc treasury fed irs fincen ofac occ fdic congress senate house court
judge supreme federal state government police interpol europol
binance coinbase kraken okx bybit bitfinex gemini bitstamp robinhood paypal stripe
visa mastercard tether circle ripple blackrock fidelity grayscale vanguard microstrategy
strategy jpmorgan goldman citi citigroup hsbc barclays ubs morgan stanley wells fargo
sofi revolut nubank standard chartered
trump biden hamas iran russia china korea japan india brazil uk eu us usa america
american europe european london york hong kong dubai singapore
""".split())


def comparable_pair(shared, generic=frozenset()):
    """The entities on which two stories may be treated as the same subject: all of them
    when two or more are shared; a single shared entity only if it is neither a
    recurring actor nor generic market vocabulary. Empty means not comparable."""
    shared = {e for e in shared if e not in generic and not e.startswith("mag:")}
    if len(shared) >= 2:
        return shared
    return {e for e in shared if e not in RECURRING_ACTORS}


def figure_conflicts(headline, key_fact="", update_of=None, within_days=30):
    """Return a list of same-entity, same-magnitude, materially different figure conflicts
    between this candidate and recently published stories (excluding the update_of origin)."""
    cand_figs = usd_figures(f"{headline} {key_fact}")
    # the shared entity must be each story's SUBJECT (in the headline), not merely mentioned,
    # so a big entity with two unrelated same-magnitude figures (revenue vs an acquisition)
    # is not a false conflict.
    cand_ents = primary_entities(headline)
    if not cand_figs or not cand_ents:
        return []
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=within_days)).isoformat() if within_days else ""
    conflicts = []
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("id", "")).startswith("wrap-") or d.get("example"):
            continue
        if update_of and d.get("slug") == update_of:
            continue
        when = d.get("published_utc") or (d.get("date", "") + "T00:00:00Z")
        if cutoff and when < cutoff:
            continue
        shared = comparable_pair(cand_ents & primary_entities(d.get("title", "")))
        if not shared:
            continue
        pub_figs = usd_figures(f"{d.get('title','')} {d.get('key_fact','')}")
        for cf in cand_figs:
            for pf in pub_figs:
                hi, lo = max(cf, pf), min(cf, pf)
                if lo <= 0:
                    continue
                if hi / lo <= 3 and (hi - lo) / hi > 0.15:  # same quantity, materially revised
                    conflicts.append({"entity": sorted(shared)[0], "candidate_usd": cf,
                                      "published_usd": pf, "slug": d.get("slug", ""),
                                      "title": d.get("title", "")})
                    break
            else:
                continue
            break
    return conflicts
