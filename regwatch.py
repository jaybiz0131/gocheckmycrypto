#!/usr/bin/env python3
"""
regwatch.py: the JURISDICTION TRACKER for regulation stories (2026-07-19).

A regulatory storyline moves in steps that are days or months apart: a Taiwan consultation
closes, the GENIUS Act hits a compliance deadline, a MiCA phase-in date arrives. Between
steps the desk's 36-hour story window forgets it, and the thread slips. This module keeps a
committed ledger of every regulatory storyline the desk has covered, keyed by jurisdiction
and named instrument, with the dates the reporting mentioned, and feeds the live ones back
into the daily edition so "what to watch" names them.

DETERMINISTIC AND FREE: no model call. It reads the desk's own published stories, matches
jurisdictions and named instruments from a config list, and pulls forward-looking dates out
of the same sentences. Facts only come from stories the desk already verified and published.

USAGE
  python3 regwatch.py            # update the ledger from published stories and print it
  python3 regwatch.py --show     # print the current ledger without updating
"""

import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")
LEDGER = os.path.join(HERE, "regwatch.json")

# Jurisdictions the desk covers. A story is regulatory-relevant when it names one of these
# AND a regulatory signal (below), or names an instrument outright.
JURISDICTIONS = [
    "United States", "U.S.", "US ", "Taiwan", "European Union", "EU ", "Europe",
    "United Kingdom", "U.K.", "Britain", "China", "Hong Kong", "Japan", "South Korea",
    "Singapore", "India", "Brazil", "Canada", "Australia", "Switzerland", "UAE",
    "Dubai", "Nigeria", "Turkey", "Argentina", "Mexico", "Thailand", "Vietnam",
]

# Named instruments: the things that actually carry deadlines. Extend freely.
INSTRUMENTS = [
    "GENIUS Act", "CLARITY Act", "Clarity Act", "MiCA", "Markets in Crypto-Assets",
    "FIT21", "Howey", "BSA", "Bank Secrecy Act", "Travel Rule", "AMLD", "AMLR",
    "Executive Order", "SAB 121", "Basel", "FATF", "DORA", "PSD2", "Stablecoin Act",
    "Digital Asset Market Structure", "CBDC ban", "BIP 110",
]

REG_SIGNAL = re.compile(
    r"\b(regulat\w+|legislat\w+|bill|act\b|rule\w*|ruling|law\b|statut\w+|consultation|"
    r"comment period|deadline|effective date|compliance date|enforce\w+|sanction\w*|"
    r"licens\w+|registrat\w+|framework|guidance|directive|mandate)\b", re.I)

# forward-looking dates the reporting states: "by March 3", "effective 2027-01-01",
# "deadline of July 28", "takes effect in January 2027". Month names are matched
# EXPLICITLY: an earlier version used [A-Z][a-z]+ under re.I, which made "by the 20" parse
# as a date. A tracker that invents deadlines is worse than no tracker.
_MONTHS = ("January|February|March|April|May|June|July|August|September|October|"
           "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
DATE_PAT = re.compile(
    r"\b(?:by|before|effective|deadline(?:\s+of)?|takes?\s+effect(?:\s+in|\s+on)?|due|"
    r"expires?|phase[-\s]in|no later than|on or before|starting|beginning)\s+"
    r"((?:\d{4}-\d{2}-\d{2})"
    rf"|(?:(?:{_MONTHS})\.?\s+\d{{1,2}}(?:,\s*\d{{4}})?)"
    rf"|(?:(?:{_MONTHS})\.?\s+\d{{4}}))", re.I)

# alias -> canonical, so one storyline does not fragment across EU/Europe/European Union
CANON = {
    "eu": "European Union", "europe": "European Union", "european union": "European Union",
    "u.s.": "United States", "us": "United States", "united states": "United States",
    "u.k.": "United Kingdom", "uk": "United Kingdom", "britain": "United Kingdom",
    "united kingdom": "United Kingdom", "uae": "UAE", "dubai": "UAE",
}

# instruments whose home jurisdiction is unambiguous, so a story that names the instrument
# without naming the country still files under the right jurisdiction
INSTRUMENT_HOME = {
    "genius act": "United States", "clarity act": "United States",
    "digital asset market structure": "United States", "fit21": "United States",
    "sab 121": "United States", "bank secrecy act": "United States", "bsa": "United States",
    "howey": "United States", "cbdc ban": "United States",
    "mica": "European Union", "markets in crypto-assets": "European Union",
    "dora": "European Union", "amld": "European Union", "amlr": "European Union",
    "psd2": "European Union",
}


def _story_text(d):
    body = d.get("body", [])
    body = body if isinstance(body, list) else [str(body)]
    return " ".join([d.get("title", ""), d.get("dek", ""), d.get("key_fact", ""),
                     d.get("bottom_line", "")] + [str(b) for b in body])


def load():
    if os.path.exists(LEDGER):
        try:
            return json.load(open(LEDGER, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def extract(text):
    """Return (canonical jurisdictions, instruments, stated_dates) found in one story."""
    found = set()
    for j in JURISDICTIONS:
        token = j.strip()
        pat = re.escape(token) if "." in token else r"\b" + re.escape(token) + r"\b"
        if re.search(pat, text):
            found.add(CANON.get(token.lower(), token))
    # canonical instrument casing, so "CLARITY Act" and "Clarity Act" are ONE storyline
    low = text.lower()
    canon_instr = {}
    for i in INSTRUMENTS:
        if i.lower() in low:
            canon_instr[i.lower()] = canon_instr.get(i.lower(), i)
    instr = sorted(canon_instr.values(), key=str.lower)
    # An instrument with an unambiguous home files under THAT jurisdiction only: a US story
    # that mentions MiCA is not an American MiCA storyline.
    homes = {INSTRUMENT_HOME[i.lower()] for i in instr if i.lower() in INSTRUMENT_HOME}
    if homes:
        found |= homes
    dates = sorted({m.group(1).strip().rstrip(",.") for m in DATE_PAT.finditer(text)})
    return sorted(found), instr, dates


def _pairs(juris, instr):
    """Jurisdiction/instrument pairs to file. An instrument with a known home pairs ONLY
    with that home; everything else pairs with each jurisdiction named in the story."""
    out = []
    for i in instr:
        home = INSTRUMENT_HOME.get(i.lower())
        if home:
            out.append((home, i))
        else:
            out += [(j, i) for j in (juris or ["Unspecified"])]
    if not instr:
        out += [(j, "(unnamed measure)") for j in (juris or ["Unspecified"])]
    return out


def update(days=45):
    """Fold the desk's recently published stories into the ledger. An entry is keyed by
    jurisdiction + instrument so a storyline accumulates instead of being re-created."""
    led = load()
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=days)).isoformat()
    for p in sorted(glob.glob(os.path.join(CONTENT, "*.json"))):
        if os.path.basename(p).startswith("example"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("id", "")).startswith("wrap-"):
            continue  # editions summarize stories; never track them as sources
        if (d.get("published_utc") or "") < cutoff:
            continue
        text = _story_text(d)
        if not REG_SIGNAL.search(text):
            continue
        juris, instr, dates = extract(text)
        # A trackable storyline needs something to track: a NAMED instrument, or a stated
        # date. "A country appeared in a regulation-flavoured story" is not a storyline and
        # would bury the real threads (Taiwan's consultation, the GENIUS Act deadline).
        if not instr and not dates:
            continue
        if not juris and not instr:
            continue
        for j, i in _pairs(juris, instr):
            key = f"{j} :: {i}"
            e = led.get(key, {"jurisdiction": j, "instrument": i, "dates": [],
                              "stories": [], "first_seen": d.get("date", "")})
            for dt in dates:
                if dt not in e["dates"]:
                    e["dates"].append(dt)
            url = f"/articles/{d.get('slug','')}.html"
            if url not in e["stories"]:
                e["stories"].append(url)
            e["stories"] = e["stories"][-5:]
            e["last_seen"] = d.get("date", "")
            e["last_title"] = d.get("title", "")
            led[key] = e
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), indent=1, sort_keys=True)
    return led


def active(led=None, stale_days=120):
    """Storylines worth carrying into an edition: seen recently enough to still be live."""
    led = led if led is not None else load()
    today = datetime.date.today()
    out = []
    for key, e in led.items():
        try:
            last = datetime.date.fromisoformat(e.get("last_seen") or e.get("first_seen") or "")
        except Exception:
            last = today
        if (today - last).days <= stale_days:
            out.append(e)
    out.sort(key=lambda e: e.get("last_seen") or "", reverse=True)
    return out


def for_edition(limit=8):
    """The compact block handed to the edition prompt: live regulatory storylines and any
    dates the desk's own reporting has stated for them, so a checkpoint never slips."""
    return [{"jurisdiction": e["jurisdiction"], "instrument": e["instrument"],
             "stated_dates": e.get("dates", [])[:4], "last_covered": e.get("last_seen", ""),
             "last_story": (e.get("stories") or [""])[-1]}
            for e in active()[:limit]]


def main():
    if "--show" in sys.argv[1:]:
        led = load()
    else:
        led = update()
    print(f"regwatch: {len(led)} storyline(s) tracked; {len(active(led))} live")
    for e in active(led)[:20]:
        dates = ", ".join(e.get("dates", [])) or "no date stated"
        print(f"  {e['jurisdiction']} :: {e['instrument']}  [{dates}]  last covered {e.get('last_seen','')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
