#!/usr/bin/env python3
"""
Autopilot: full-auto release for the daily brief, on Jack's standing instruction (2026-07-11).

Policy (supersedes the launch-era always-human gate; recorded in DEVIATIONS):
  - VERIFIED stories publish automatically: the adversarial verifier IS the gate.
  - NEEDS-HUMAN-REVIEW stories are never auto-published; they stay in the review queue for a
    human take (publish.py still enforces that override rule independently).
  - REJECT never publishes. A failed run publishes nothing (fail-closed inheritance).

Three-role pipeline (2026-07-14): auto-publish now also requires the post-draft APPROVER's
sign-off (verdicts VERIFIED alone no longer suffice), and a DEPTH GATE holds any story whose
body ran under 120 words even though its research brief carried >=2000 chars of fetched
source text: the writer had material and did not use it, a quality failure. Thin-source
brevity stays legal (the honesty case): a short story from a thin brief publishes.

Runs after run.py in the daily workflow: writes an approval file that approves exactly the
VERIFIED+APPROVED set, runs Stage 6 (publish.py), then ingests approved payloads into site
content (site_build.py --ingest). The workflow then commits site/content and pushes, which
deploys.
"""

import datetime
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def _words(s):
    return set(re.findall(r"[a-z]{4,}", (s or "").lower()))


# Ubiquitous crypto vocabulary: shared between UNRELATED stories, so it is not an event
# fingerprint. Two stories both saying "Bitcoin"/"SEC"/"ETF" are not the same story.
_UBIQUITOUS = {
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "sec", "cftc", "etf",
    "token", "tokens", "blockchain", "defi", "stablecoin", "stablecoins", "market",
    "markets", "price", "prices", "exchange", "exchanges", "million", "billion", "billions",
    "trillion", "the", "and", "for", "with", "over", "into", "from", "u.s", "us", "new",
    "law", "bill", "act", "vote", "firm", "firms", "coin", "network", "protocol",
}


def _signature(*texts):
    """Event fingerprint: the DISTINCTIVE tokens that name a specific event. Proper nouns
    (Hut, IREN, Maruwa, Worldcoin, Grayscale, Parliament) and numbers/amounts (2,300,
    3,800, 1.65, 110), minus the ubiquitous crypto vocabulary two unrelated stories share.
    Two stories about the SAME event share these even when the headline words differ:
    'Amazon Japan supplier to pay 2,300 contractors' and 'AZ-COM Maruwa to pay 2,300
    partners' share {amazon, japan, 2300} though word-overlap is only 0.43."""
    blob = " ".join(t or "" for t in texts)
    proper = re.findall(r"\b([A-Z][A-Za-z0-9.\-]{2,}|[A-Z]{2,})\b", blob)
    nums = re.findall(r"\b\d[\d,\.]*\b", blob)
    sig = {p.lower().rstrip(".").replace(",", "") for p in proper}
    sig |= {n.replace(",", "").rstrip(".") for n in nums}
    return {t for t in sig if t and t not in _UBIQUITOUS and len(t) >= 2}


def same_event(a_title, a_kf, b_title, b_kf, word_thr=0.7, sig_thr=2):
    """True if two stories cover the same event: high headline-word overlap OR >= sig_thr
    shared distinctive fingerprint tokens (the news-dedup signal word overlap misses)."""
    wa, wb = _words(a_title), _words(b_title)
    if wa and wb and len(wa & wb) / min(len(wa), len(wb)) >= word_thr:
        return True
    return len(_signature(a_title, a_kf) & _signature(b_title, b_kf)) >= sig_thr


# Outlet / wire names: they appear as proper nouns in the signature but are not part of the
# EVENT, so a new outlet on the same story is not a new development.
_OUTLETS = {
    "coindesk", "cointelegraph", "decrypt", "theblock", "block", "defiant", "thedefiant",
    "blockworks", "blockonomi", "beacon", "reuters", "bloomberg", "forbes", "fortune",
    "cnbc", "messari", "nansen", "arkham", "lookonchain", "protos", "beincrypto",
    "cryptoslate", "dlnews", "axios", "wsj", "techcrunch", "coinshares",
}


def _headline_overlap(a_title, b_title):
    wa, wb = _words(a_title), _words(b_title)
    return len(wa & wb) / min(len(wa), len(wb)) if wa and wb else 0.0


def classify_published(headline, key_fact="", within_days=21):
    """Relate a candidate to the recently published corpus (widened from 5 to 21 days so
    multi-week running stories stay linked):
      ('rehash', title, slug)  near-duplicate to HOLD: same event, near-identical framing.
      ('update', title, slug)  a genuine development to publish AS AN UPDATE of the original.
      ('new', None, None)      unseen.
    Split rule: same event is matched as before; a near-identical HEADLINE (>=50% word
    overlap) is a rehash (the 5x-Kalshi case); the same event with a different angle plus
    >=2 new distinctive, non-outlet specifics (new actor/mechanism/number, e.g. the Ostium
    'Tornado Cash / 10,540 ETH' follow-up) is a development. The update links the EARLIEST
    matched story (the origin), so 'develops our earlier reporting' points at the first take."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=within_days)).isoformat() if within_days else ""
    matches = []
    for p in glob.glob(os.path.join(HERE, "site", "content", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("id", "")).startswith("wrap-") or d.get("example"):
            continue
        when = d.get("published_utc") or (d.get("date", "") + "T00:00:00Z")
        if cutoff and when < cutoff:
            continue
        if same_event(headline, key_fact, d.get("title", ""), d.get("key_fact", "")):
            matches.append((when, d.get("title", ""), d.get("slug", ""), d.get("key_fact", "")))
    if not matches:
        return ("new", None, None)
    # a near-identical headline against ANY match => rehash (hold)
    if any(_headline_overlap(headline, m[1]) >= 0.5 for m in matches):
        top = min(matches, key=lambda m: m[0])
        return ("rehash", top[1], top[2])
    origin = min(matches, key=lambda m: m[0])  # earliest = the story this one develops
    new = _signature(headline, key_fact) - _signature(origin[1], origin[3]) - _OUTLETS
    if len(new) >= 2:
        return ("update", origin[1], origin[2])
    return ("rehash", origin[1], origin[2])


def body_word_count(article_draft):
    body = article_draft.get("body", "")
    if isinstance(body, list):
        body = " ".join(str(p) for p in body)
    return len(str(body).split())


def depth_gate_holds(body_words, source_chars, min_words=120, min_source_chars=2000):
    """True when the story must be HELD: a short body despite substantial source material.
    A short body from thin sources passes (honest brevity is legal; padding is not)."""
    return body_words < min_words and source_chars >= min_source_chars


def breaking_two_source_holds(headline, source_names):
    """The BREAKING-path gate (additive, 2026-07-14 directive): a breaking piece publishes
    as fact only with >=2 independent sources; single-source may publish only when the
    headline itself carries the unconfirmed label; otherwise it HOLDS for the next
    scheduled slot. Deterministic, fail-closed."""
    distinct = {n.strip().lower() for n in source_names if n and n.strip()}
    if len(distinct) >= 2:
        return False
    return "unconfirmed" not in (headline or "").lower()


def already_published(headline, key_fact="", within_days=5):
    """A follow-up on yesterday's event should update the existing article, not publish a
    new one. This holds any story that covers the SAME EVENT as one already published in the
    last `within_days` (event fingerprint, not just headline words), so the desk stops
    re-running the UK inquiry / Hut 8-IREN / Amazon-Japan story as fresh coverage. Returns
    the matched (title, url) so the caller can log it, or None."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=within_days)).isoformat() if within_days else ""
    for p in glob.glob(os.path.join(HERE, "site", "content", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("id", "")).startswith("wrap-"):
            continue  # editions are not stories
        if cutoff and (d.get("published_utc") or d.get("date", "") + "T00:00:00Z") < cutoff:
            continue
        if same_event(headline, key_fact, d.get("title", ""), d.get("key_fact", "")):
            return (d.get("title", ""), f"/articles/{d.get('slug','')}.html")
    return None


def main():
    import consistency  # lazy: consistency imports from this module, so avoid an import cycle
    tpl_path = os.path.join(OUT, "approval_template.json")
    report_path = os.path.join(OUT, "run_report.json")
    if not (os.path.exists(tpl_path) and os.path.exists(report_path)):
        print("autopilot: no run outputs found -> nothing to publish (fail-closed)")
        return 1
    report = json.load(open(report_path, encoding="utf-8"))
    if report.get("mode") != "live" or report.get("status") not in ("ok", "OK", None) and not report.get("review_queue"):
        print(f"autopilot: run not live/ok -> nothing to publish (mode={report.get('mode')})")
        return 1

    # The approver's post-draft verdicts and the researcher's measured source volume: both
    # feed the publish decision. Missing files fail closed (everything holds).
    def _load(name):
        try:
            return json.load(open(os.path.join(OUT, name), encoding="utf-8"))
        except Exception:
            return {}
    approver = {a.get("id"): a for a in _load("approver.json").get("approvals", [])}
    briefs = {b.get("id"): b for b in _load("briefs.json").get("briefs", [])}
    drafts = {d.get("id"): d for d in _load("drafts.json").get("drafts", [])}
    clusters = {c.get("id"): c for c in _load("items.json").get("clusters", [])}
    breaking = os.environ.get("BREAKING") == "1"

    approval = json.load(open(tpl_path, encoding="utf-8"))
    approved = held = reruns = 0
    updates = {}  # cid -> slug of the earlier story this one develops (ingest writes update_of)
    approved_this_run = []  # (title, key_fact) of stories approved earlier in THIS run, so
    # two clusters about one event in a single run cannot both publish (neither is committed
    # yet, so the on-disk guard cannot see its sibling)
    for cid, story in approval.get("stories", {}).items():
        appr = approver.get(cid)
        words = body_word_count((drafts.get(cid, {}) or {}).get("article_draft", {}) or {})
        source_chars = (briefs.get(cid) or {}).get("source_chars", 0)
        c = clusters.get(cid) or {}
        kf = (drafts.get(cid, {}) or {}).get("article_draft", {}).get("key_fact", "") or c.get("snippet", "")
        headline = story.get("headline", "")
        src_names = [c.get("source", "")] + [x.get("name", "")
                                             for x in (c.get("corroboration") or [])]
        if story.get("verifier_verdict") != "VERIFIED":
            story["decision"] = "hold"
            held += 1
        elif breaking and breaking_two_source_holds(story.get("headline", ""), src_names):
            story["decision"] = "hold"
            held += 1
            print(f"autopilot: BREAKING two-source gate held "
                  f"'{story.get('headline','')[:60]}' (single-source, not labeled "
                  f"unconfirmed -> waits for the next scheduled slot)")
        elif not appr or appr.get("decision") != "APPROVE":
            story["decision"] = "hold"
            held += 1
            why = f"{appr.get('category')}: {'; '.join(appr.get('reasons', [])[:2])}" if appr else "no approver decision (fail-closed)"
            print(f"autopilot: approver held '{story.get('headline','')[:60]}' ({why})")
        elif depth_gate_holds(words, source_chars):
            story["decision"] = "hold"
            held += 1
            print(f"autopilot: depth gate held '{story.get('headline','')[:60]}' "
                  f"({words} words from {source_chars} chars of source material)")
        else:
            rel, mtitle, mslug = classify_published(headline, kf)  # against the committed corpus
            if rel == "rehash":
                story["decision"] = "hold"
                reruns += 1
                print(f"autopilot: HELD near-duplicate of a published story "
                      f"('{headline[:52]}' ~ '{(mtitle or '')[:42]}')")
            elif any(same_event(headline, kf, t, k) for t, k in approved_this_run):
                story["decision"] = "hold"
                reruns += 1
                print(f"autopilot: HELD same-run duplicate of an event already approved this "
                      f"run ('{headline[:60]}')")
            elif rel == "update":
                # a genuine development: publish it AS AN UPDATE of the origin story instead
                # of dropping the follow-up (the old guard's silent HOLD lost these, e.g. the
                # Ostium 'Tornado Cash' development of the $18M hack). Updates are meant to
                # revise figures, so the consistency belt below does not apply to them.
                story["update_of"] = mslug
                updates[cid] = mslug
                print(f"autopilot: APPROVED as an UPDATE of '{(mtitle or '')[:48]}' "
                      f"(update_of={mslug})")
                story["decision"] = "approve"
                approved += 1
                approved_this_run.append((headline, kf))
            else:
                # cross-corpus figure-consistency belt: a fresh story whose numbers contradict
                # a same-entity published figure (the Ostium $18M-vs-$24M class) is held for a
                # human, not silently auto-published.
                conflicts = consistency.figure_conflicts(headline, kf)
                if conflicts:
                    c = conflicts[0]
                    story["decision"] = "hold"
                    held += 1
                    print(f"autopilot: HELD figure conflict ('{headline[:44]}' cites "
                          f"${c['candidate_usd']:,.0f} vs published ${c['published_usd']:,.0f} "
                          f"for '{c['entity']}' in {c['slug']}) -> human review")
                else:
                    story["decision"] = "approve"
                    approved += 1
                    approved_this_run.append((headline, kf))
    json.dump(approval, open(os.path.join(OUT, "approval.json"), "w", encoding="utf-8"), indent=1)
    json.dump(updates, open(os.path.join(OUT, "updates.json"), "w", encoding="utf-8"), indent=1)
    print(f"autopilot: auto-approved {approved} VERIFIED, held {held} for human review")
    if approved == 0:
        print("autopilot: nothing VERIFIED today -> site publish skipped, queue kept for human")
        return 0

    r = subprocess.run([sys.executable, os.path.join(HERE, "publish.py")], cwd=HERE)
    if r.returncode != 0:
        print("autopilot: publish.py failed -> fail-closed")
        return 1
    r = subprocess.run([sys.executable, os.path.join(HERE, "site_build.py"), "--ingest"], cwd=HERE)
    if r.returncode != 0:
        print("autopilot: ingest/build failed -> fail-closed")
        return 1
    print("autopilot: published + ingested; workflow commit/push makes it live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
