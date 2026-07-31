#!/usr/bin/env python3
"""
fedreg.py: put federal rulemaking on the desk's calendar BEFORE the news does.

WHY THIS EXISTS
  regwatch.py tracks regulatory storylines by reading the desk's OWN published stories, so
  it can only ever know about a measure the desk already covered. The desk's regulatory
  awareness is therefore entirely downstream of news feeds, which is the same shape as the
  FOMC miss: awareness arrives with, or after, the coverage.

  The Federal Register is upstream of all of it. A proposed rule is published there on the
  day it exists, and the comment period it opens is a real, dated, checkable deadline. A
  rule often gets no press release at all, which is precisely the gap the desk's existing
  SEC and CFTC feeds cannot close.

WHAT IT PRODUCES
  data/fedreg_calendar.json, in the SAME event schema as the curated data/week_calendar.json:
  the publication date of a crypto-relevant rule, and, separately, the date its comment
  period closes, which is the forward-looking event worth knowing about.

WHO READS IT, AND WHO DELIBERATELY DOES NOT
  calendar_check.py reads it, so an uncovered rule raises the same internal flag as an
  uncovered calendar event. That is an editor-facing signal and carries no risk.

  week_ahead.py does NOT read it. That module renders a PUBLISHED story, and it is
  deterministic from a curated file on purpose, so nothing machine-selected reaches a reader
  unreviewed. Auto-generated entries appearing in reader-facing copy is a different decision
  from auto-generated entries appearing on an internal checklist, and it is the owner's to
  make after seeing what this actually collects.

SCOPE, and why it is narrow
  Agency-filtered and type-filtered. A bare term search for "digital asset" returns 3,183
  documents including asylum referrals and submarine cable licences, because the phrase
  appears in unrelated rules. Filtered to the financial regulators and to RULE/PRORULE,
  six months of sweeps return 34 unique documents, which reduce to 13 calendar events after
  the topic filter, carrying 2 live comment deadlines. That is the right order of magnitude:
  frequent enough to be worth checking every run, rare enough that a flag means something.
  NOTICE is excluded: SEC self-regulatory organisation filings are routine, numerous, and
  not the desk's beat.

KEYLESS, ADVISORY, FAIL-OPEN. No key, no quota. A fetch failure warns and writes nothing,
so calendar_check simply falls back to the curated calendar; it never blocks a publish.

The output is NOT committed (see .gitignore). It is regenerated immediately before
calendar_check reads it, in the same job, so a committed copy would churn on every run for
a file nothing reads between runs.

USAGE  python3 fedreg.py [--days-back N]
"""

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import common

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(HERE, "data", "fedreg_calendar.json")

API = "https://www.federalregister.gov/api/v1/documents.json"
UA = "GoCheckMyCrypto/1.0 (+https://gocheckmycrypto.com)"

# The financial regulators whose rules move this market. Anything outside these is noise for
# this desk, whatever words the rule happens to use.
AGENCIES = [
    "securities-and-exchange-commission",
    "commodity-futures-trading-commission",
    "financial-crimes-enforcement-network",
    "comptroller-of-the-currency",
    "federal-reserve-system",
    "treasury-department",
]

# ONE QUERY PER TERM, merged on document number. This is not a style choice: the API's term
# parser silently returns ZERO for a quoted OR expression as soon as a publication_date
# filter is added. Measured: '"digital asset" OR cryptocurrency OR ...' alone returns 48
# documents; the same string with a date filter returns 0, while the single term
# "digital asset" with the same date filter returns 97. A combined query looks like a clean
# "no crypto rulemaking this month" and is indistinguishable from the truth, which is the
# worst failure mode a coverage check can have. Six cheap queries cannot lie that way.
TERMS = ("digital asset", "stablecoin", "cryptocurrency", "virtual currency",
         "bitcoin", "tokenized")

DAYS_BACK = 180     # rulemaking is slow, and a comment period opened months ago
                    # can still be open, which is the event worth knowing about
LOOKAHEAD_DAYS = 90  # how far forward a comment deadline is still worth carrying

# Words that make a workable match group with the agency. A rule's title is long and formal;
# the desk writes about it in shorter words, so match on the topic word plus the agency
# rather than on the title.
TOPIC_WORDS = ("stablecoin", "digital asset", "cryptocurrency", "virtual currency",
               "bitcoin", "custody", "anti-money laundering", "tokenized")

AGENCY_SHORT = {
    "securities and exchange commission": "sec",
    "commodity futures trading commission": "cftc",
    "financial crimes enforcement network": "fincen",
    "comptroller of the currency": "occ",
    "federal reserve system": "federal reserve",
    "treasury department": "treasury",
}


def _query(term, since, timeout=30):
    q = [("per_page", "40"), ("order", "newest"),
         ("conditions[term]", term),
         ("conditions[publication_date][gte]", since)]
    q += [("conditions[agencies][]", a) for a in AGENCIES]
    q += [("conditions[type][]", t) for t in ("RULE", "PRORULE")]
    q += [("fields[]", f) for f in ("title", "publication_date", "agencies", "type",
                                    "comments_close_on", "html_url", "docket_ids",
                                    "abstract", "document_number")]
    url = API + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return (json.load(r) or {}).get("results") or []


def _fetch(days_back=DAYS_BACK, timeout=30):
    """One query per term, merged on document number. See the TERMS note.

    A term that errors is skipped rather than failing the sweep: five terms' worth of
    coverage beats none. All six failing is a real outage and raises, which the caller
    turns into "no check ran"."""
    since = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()
    merged, errors = {}, 0
    for term in TERMS:
        try:
            for doc in _query(term, since, timeout):
                key = doc.get("document_number") or doc.get("html_url") or json.dumps(doc)
                merged.setdefault(key, doc)
        except Exception as e:
            errors += 1
            common.gh("warning", f"fedreg: term {term!r} failed ({e}); continuing")
    if errors == len(TERMS):
        raise RuntimeError("every Federal Register query failed")
    return sorted(merged.values(), key=lambda d: str(d.get("publication_date")), reverse=True)


def _agency_terms(doc):
    """Short agency names the desk would actually write, e.g. 'sec', not the full title."""
    out = []
    for a in doc.get("agencies") or []:
        name = str(a.get("name") or "").strip().lower()
        short = AGENCY_SHORT.get(name)
        if short and short not in out:
            out.append(short)
    return out


def _match_groups(doc):
    """AND-groups in week_calendar.json's format: agency + topic word.

    Deliberately not the rule's title. Titles are formal and long ("Permitted Payment
    Stablecoin Issuer Customer Identification Programs"); the desk writes "FinCEN's
    stablecoin rule". Requiring the agency AND a topic word is specific enough not to match
    unrelated coverage and loose enough to match how the story would actually be written."""
    hay = " ".join([str(doc.get("title") or ""), str(doc.get("abstract") or "")]).lower()
    topics = [t for t in TOPIC_WORDS if t in hay]
    agencies = _agency_terms(doc)
    if not topics or not agencies:
        return []
    return [[a, t] for a in agencies for t in topics[:2]]


def events(docs=None, today=None, days_back=DAYS_BACK, lookahead=LOOKAHEAD_DAYS):
    """Calendar events from federal rulemaking, in week_calendar.json's schema.

    Two kinds per rule, and the second is the point: the rule's publication (something
    happened) and its comment deadline (something is going to happen, on a known date)."""
    today = today or datetime.date.today()
    if docs is None:
        try:
            docs = _fetch(days_back) or []
        except Exception as e:
            common.gh("warning", f"fedreg: Federal Register unreachable ({e}); "
                                 f"previous calendar stands")
            return None
    lo = (today - datetime.timedelta(days=days_back)).isoformat()
    hi = (today + datetime.timedelta(days=lookahead)).isoformat()
    out = []
    for d in docs:
        groups = _match_groups(d)
        if not groups:
            continue
        agency = ", ".join(a.get("name", "") for a in (d.get("agencies") or [])) or "an agency"
        docket = ", ".join(d.get("docket_ids") or [])
        title = re.sub(r"\s+", " ", str(d.get("title") or "")).strip()
        pub = str(d.get("publication_date") or "")
        kind = "rule" if str(d.get("type", "")).lower().startswith("rule") else "proposed rule"
        if lo <= pub <= hi:
            out.append({
                "date": pub, "kind": kind,
                "title": f"{agency}: {title}"[:180],
                "detail": (str(d.get("abstract") or "").strip()[:400]
                           or f"{kind} published in the Federal Register."
                           ) + (f" Docket {docket}." if docket else ""),
                "match": groups,
                "source": d.get("html_url") or "https://www.federalregister.gov/",
                "source_name": "Federal Register",
            })
        close = str(d.get("comments_close_on") or "")
        if close and today.isoformat() <= close <= hi:
            out.append({
                "date": close, "kind": "comment deadline",
                "title": f"Comments close: {title}"[:180],
                "detail": f"The comment period on {agency}'s {kind} closes."
                          + (f" Docket {docket}." if docket else ""),
                "match": groups,
                "source": d.get("html_url") or "https://www.federalregister.gov/",
                "source_name": "Federal Register",
            })
    out.sort(key=lambda e: e["date"])
    return out


def main():
    argv = sys.argv[1:]
    days = int(argv[argv.index("--days-back") + 1]) if "--days-back" in argv else DAYS_BACK
    ev = events(days_back=days)
    if ev is None:
        return 0  # unreachable: warned, and never a reason to fail a run
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    payload = {"note": "Generated by fedreg.py from the Federal Register API. Read by "
                       "calendar_check.py only; week_ahead.py reads the CURATED calendar, "
                       "so nothing here reaches a reader unreviewed.",
               "generated_utc": datetime.datetime.now(datetime.timezone.utc)
               .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "events": ev}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
        f.write("\n")
    deadlines = sum(1 for e in ev if e["kind"] == "comment deadline")
    print(f"fedreg: {len(ev)} event(s) ({deadlines} comment deadline(s)) "
          f"-> {os.path.relpath(OUT_FILE)}")
    for e in ev[:8]:
        print(f"  {e['date']}  {e['kind']:17} {e['title'][:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
