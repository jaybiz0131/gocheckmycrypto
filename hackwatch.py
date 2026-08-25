#!/usr/bin/env python3
"""
hackwatch.py: the desk should never learn about a major exploit from a reader.

Companion to calendar_check.py, same shape and same discipline. That module asks "did we
cover the events we already knew were coming?"; this one asks "did we cover the exploits
that actually happened?". Exploits are the one beat where the desk cannot pre-curate a
calendar, because nobody schedules a hack, so the only way to be sure is to check an
independent ledger after the fact.

SOURCE  DefiLlama's hacks dataset (api.llama.fi/hacks). Free, keyless, no quota. Each record
carries a date, a USD amount, the protocol, the technique and a source link, so a gap report
can say what was missed and how big it was rather than just naming it.

WHY A LEDGER AND NOT A FEED. The desk already aggregates crypto news feeds, and a big
exploit usually shows up in them. "Usually" is the problem: aggregation is reactive and a
quiet news cycle, a feed outage, or a story that breaks at 3am between slots all produce the
same result, which is silence that looks identical to nothing having happened. A ledger is
checkable. It answers the question directly.

THE FLOOR is $1,000,000, and it is a judgment, not a law. Measured against the live dataset
over the trailing 90 days: everything = 7.0 exploits/week, $500k = 4.0/week, $1M = 2.8/week,
$5M = 1.3/week. The alarm only fires for exploits with NO coverage, so the real rate is lower
than that. $1M is set where a miss would embarrass the desk and a hit is worth a story.
Raise it if the flag gets noisy; that is a one-constant change.

ADVISORY, NEVER A GATE. Whether an exploit is worth covering is a judgment for a human, so
this warns, writes out/hack_gaps.json for the workflow to raise a flag from, and always
exits 0. Network failure is a warning, not a failure: a check that cannot run must never
stop the desk publishing.

USAGE  python3 hackwatch.py [--days-back N] [--floor USD]
"""

import datetime
import glob
import json
import os
import re
import sys
import urllib.request

import common

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")

HACKS_URL = "https://api.llama.fi/hacks"
DAYS_BACK = 4          # an exploit stays "due" for a few slots, like a calendar event
FLOOR_USD = 1_000_000  # see the module docstring; measured, not guessed
UA = "GoCheckMyCrypto/1.0 (+https://gocheckmycrypto.com)"

# A story counts as coverage only if it reads like coverage OF AN EXPLOIT. Without this a
# routine story that happens to name the protocol would mark the hack covered, which is the
# failure mode that matters here: a false "covered" is silent, a false "uncovered" is just a
# flag someone closes.
EXPLOIT_WORD = re.compile(
    r"\b(hack\w*|exploit\w*|drain\w*|stolen|steal\w*|theft|breach\w*|attack\w*|"
    r"compromis\w*|siphon\w*|rug\s?pull|malicious)\b", re.I)


def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _corpus(within_days=14):
    """(publication date, lowercased text) for the desk's recent stories."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=within_days)).isoformat()
    out = []
    for p in glob.glob(os.path.join(CONTENT, "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("example") or (d.get("date", "") < cutoff):
            continue
        body = d.get("body") or []
        body = body if isinstance(body, list) else [str(body)]
        out.append((d.get("date", ""),
                    " ".join([str(d.get("title", "")), str(d.get("dek", "")),
                              str(d.get("key_fact", ""))] + [str(b) for b in body]).lower()))
    return out


def _name_terms(name):
    """Match terms for a protocol name.

    The full name first. Also its first word when the name is multi-word, because the desk
    writes "the Ostium exploit" for "Ostium Protocol", but only when that word is long
    enough to be distinctive: a three-letter fragment would match half the corpus."""
    name = (name or "").strip()
    terms = [name.lower()] if name else []
    head = name.split()[0].lower() if name.split() else ""
    if head and head != name.lower() and len(head) >= 5:
        terms.append(head)
    return terms


def gaps(days_back=DAYS_BACK, floor=FLOOR_USD, today=None, hacks=None):
    """Exploits above the floor, inside the window, with no matching story on the desk."""
    today = today or datetime.date.today()
    if hacks is None:
        try:
            hacks = _fetch(HACKS_URL)
        except Exception as e:
            common.gh("warning", f"hackwatch: hacks ledger unreachable ({e}); no check ran")
            return None
    corpus = _corpus()
    lo = today - datetime.timedelta(days=days_back)
    out = []
    for h in hacks or []:
        ts, amount = h.get("date"), h.get("amount") or 0
        if not ts or amount < floor:
            continue
        try:
            when = datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).date()
        except Exception:
            continue
        if not (lo <= when <= today):
            continue
        terms = _name_terms(h.get("name"))
        if not terms:
            continue
        # Covered when a story dated on or after the exploit names the protocol AND reads
        # like exploit coverage. The date rule is calendar_check's, for the same reason:
        # naming a protocol before it was hacked is not coverage of the hack.
        if any(any(t in story for t in terms) and EXPLOIT_WORD.search(story)
               for date, story in corpus if date >= when.isoformat()):
            continue
        out.append({
            "date": when.isoformat(),
            "kind": "exploit",
            "title": f"{h.get('name')} exploit, ${amount:,.0f}",
            "detail": f"{h.get('technique') or 'technique not stated'}"
                      f"{' on ' + ', '.join(h['chain']) if h.get('chain') else ''}",
            "match": terms,
            "amount_usd": amount,
            "source": h.get("source") or "https://defillama.com/hacks",
            "source_name": "DefiLlama hacks ledger",
        })
    out.sort(key=lambda e: -e["amount_usd"])
    return out


def main():
    argv = sys.argv[1:]

    def opt(name, default):
        return int(argv[argv.index(name) + 1]) if name in argv else default

    missed = gaps(opt("--days-back", DAYS_BACK), opt("--floor", FLOOR_USD))
    if missed is None:
        return 0  # unreachable source: warned already, and never a reason to fail a run
    common.write_out("hack_gaps.json",
                     {"checked_utc": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "uncovered": missed})
    if not missed:
        print("hackwatch: every exploit above the floor in the window has coverage.")
        return 0
    for e in missed:
        common.gh("warning",
                  f"hackwatch: UNCOVERED EXPLOIT {e['date']}: {e['title']}. "
                  f"{e['detail']}. The desk has published nothing matching {e['match']}. "
                  f"Source: {e['source']}")
    print(f"hackwatch: {len(missed)} exploit(s) above ${FLOOR_USD:,} with no coverage "
          f"-> out/hack_gaps.json (advisory; the editor decides)")
    # AN UNCOVERED EIGHT-FIGURE EXPLOIT MUST RING A BELL, NOT SCROLL A LOG (owner
    # directive 2026-08-25, after TAC $7.5M and TermFinance $8.5M both passed as
    # warning lines). One deduplicated issue per open state, same pattern as
    # edition_check: no token means the annotations above stay the whole alarm.
    _flag_issue(missed)
    return 0


def _flag_issue(missed):
    import urllib.request
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not (tok and repo and missed):
        return
    title = "Hackwatch: uncovered exploit above $1M"
    hdrs = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    body_lines = ["The exploit ledger lists these and the desk has published nothing on them:", ""]
    for e in missed:
        body_lines.append(f"- {e['date']}: {e['title']} ({e['detail']}) - {e['source']}")
    body_lines += ["", "Close after coverage publishes or after ruling the exploit out of scope."]
    body = "\n".join(body_lines)
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues?state=open&labels=pipeline",
            headers=hdrs)
        openi = json.load(urllib.request.urlopen(req, timeout=20))
        hit = next((i for i in openi if i["title"] == title), None)
        if hit:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/issues/{hit['number']}/comments",
                data=json.dumps({"body": body}).encode(), headers=hdrs, method="POST")
        else:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/issues",
                data=json.dumps({"title": title, "body": body,
                                 "labels": ["pipeline"]}).encode(),
                headers=hdrs, method="POST")
        urllib.request.urlopen(req, timeout=20)
        print("hackwatch: flag issue filed/updated")
    except Exception as e:
        print(f"hackwatch: flag issue failed ({e}); the warnings above are the alarm")


if __name__ == "__main__":
    sys.exit(main())
