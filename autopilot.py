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

import common
# The dedupe guard is chassis-level: one module, identical across the three desks. See
# dedupe.py for why it was extracted and what each rule is defending against. Re-exported
# here because callers and canaries have always reached for these through autopilot.
from dedupe import (NOVELTY_MIN, classify_published, is_coverage, same_event,
                    adds_nothing_new as dedupe_nothing_new,  # noqa: F401
                    _claim_signature, _covered_signature, _headline_overlap,   # noqa: F401
                    _OUTLETS, _signature, _words)                              # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


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


def held_after_approval_notes(held):
    """The annotation lines for stories the desk VERIFIED and APPROVED and then held.

    Warnings, never errors. These holds are usually CORRECT (a real rerun of a real story),
    so this must not fail a run or email anyone. It exists because every hold used to be a
    bare print() into a log nobody reads, which is how the 2026-07-29 FOMC miss sat
    unnoticed for two days: the desk had verified the story against federalreserve.gov,
    approved it, and dropped it, and nothing said so.

    Earlier gates (not VERIFIED, approver held, depth) are deliberately not included. Those
    fire several times a run and are the gates working; including them would bury this."""
    out = []
    for h in held or []:
        line = (f"autopilot: VERIFIED and APPROVED, then held: "
                f"'{str(h.get('headline', ''))[:70]}' -> {h.get('gate', 'unknown gate')}")
        if h.get("matched"):
            line += f" ({str(h['matched'])[:50]})"
        out.append(line)
    return out

# already_published() lived here and was never called by anything. Its corpus scan and its
# is_coverage() preview filter are now inside classify_published(), which is the gate that
# actually runs. Keeping a second, unreachable copy is how the FOMC preview fix came to pass
# its canary while never executing in production.
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
    # Stories the desk VERIFIED and APPROVED and then held anyway. This is the highest
    # signal the pipeline produces: the desk did the whole job and threw the result
    # away. Every hold used to be a bare print(), which is why the FOMC miss on
    # 2026-07-29 sat unnoticed for two days. Earlier gates (not VERIFIED, approver
    # held, depth) are deliberately NOT collected: those fire several times a run and
    # are the gates working, so alarming on them would bury this.
    held_after_approval = []
    approved_this_run = []  # (title, key_fact) of stories approved earlier in THIS run, so
    # two clusters about one event in a single run cannot both publish (neither is committed
    # yet, so the on-disk guard cannot see its sibling)
    for cid, story in approval.get("stories", {}).items():
        appr = approver.get(cid)
        words = body_word_count((drafts.get(cid, {}) or {}).get("article_draft", {}) or {})
        source_chars = (briefs.get(cid) or {}).get("source_chars", 0)
        c = clusters.get(cid) or {}
        _d = drafts.get(cid, {}) or {}
        _draft = _d.get("article_draft", {}) or {}
        # THE CLAIM THE READER GETS, and it does NOT live on article_draft. That object's
        # schema (prompts/writer.md) is title/body/bottom_line/human_take/sources/status/
        # not_financial_advice, with no key_fact at all, so `_draft.get("key_fact", "")`
        # could only ever return "" and fall through to the raw aggregate snippet. Since
        # dedupe._claim_signature() reads key_fact exclusively, the guard was judging the
        # shipped TITLE against a feed blurb, and a thin blurb yields a claim signature too
        # small to match anything. That is how a fourth copy of the same OFAC sanctions
        # story published at 15:09 on 2026-07-31, hours after this guard went live and in
        # the same run where it correctly held three other near-duplicates.
        # key_fact belongs to script_skeleton. Ordered richest-first.
        kf = ((_d.get("script_skeleton") or {}).get("key_fact")
              or _draft.get("key_fact")
              or c.get("snippet", ""))
        # THE HEADLINE THE READER GETS. story["headline"] is the EDITOR's ranked headline;
        # what ships is the writer's rewrite (site_build ingest publishes
        # payload["article"]["title"]). Judging the wrong one is not academic: on 2026-07-30
        # the 18:40 duplicate scored 0.44 word-overlap as the editor wrote it and 0.75 as it
        # actually shipped, and 0.75 would have held it.
        headline = _draft.get("title") or story.get("headline", "")
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
                held_after_approval.append(
                    {"headline": headline, "gate": "near-duplicate of a published story",
                     "matched": mtitle or "", "matched_slug": mslug or ""})
                print(f"autopilot: HELD near-duplicate of a published story "
                      f"('{headline[:52]}' ~ '{(mtitle or '')[:42]}')")
            elif any(same_event(headline, kf, t, k) for t, k in approved_this_run):
                story["decision"] = "hold"
                reruns += 1
                held_after_approval.append(
                    {"headline": headline, "gate": "duplicate of an event approved earlier "
                                                   "in this same run", "matched": "", "matched_slug": ""})
                print(f"autopilot: HELD same-run duplicate of an event already approved this "
                      f"run ('{headline[:60]}')")
            elif dedupe_nothing_new(headline, kf)[0]:
                _rep_t, _rep_s = dedupe_nothing_new(headline, kf)
                story["decision"] = "hold"
                reruns += 1
                held_after_approval.append(
                    {"headline": headline, "gate": "adds nothing the desk already published",
                     "matched": _rep_t or "", "matched_slug": _rep_s or ""})
                print(f"autopilot: HELD zero-novelty retelling of "
                      f"'{(_rep_t or '')[:52]}' ('{headline[:44]}')")
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
                    held_after_approval.append(
                        {"headline": headline, "gate": "figure conflicts with a published story",
                         "matched": c["entity"], "matched_slug": c["slug"]})
                    print(f"autopilot: HELD figure conflict ('{headline[:44]}' cites "
                          f"${c['candidate_usd']:,.0f} vs published ${c['published_usd']:,.0f} "
                          f"for '{c['entity']}' in {c['slug']}) -> human review")
                else:
                    story["decision"] = "approve"
                    approved += 1
                    approved_this_run.append((headline, kf))
    json.dump(approval, open(os.path.join(OUT, "approval.json"), "w", encoding="utf-8"), indent=1)
    json.dump(updates, open(os.path.join(OUT, "updates.json"), "w", encoding="utf-8"), indent=1)
    json.dump(held_after_approval,
              open(os.path.join(OUT, "held_after_approval.json"), "w", encoding="utf-8"), indent=1)
    for line in held_after_approval_notes(held_after_approval):
        common.gh("warning", line)
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
