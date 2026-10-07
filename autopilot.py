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
# AUTOPILOT_OUT points a --dry-run at a fixture directory; nothing else sets it.
OUT = os.environ.get("AUTOPILOT_OUT") or os.path.join(HERE, "out")


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

def queue_origin_correction(origin_slug, conflict, update_headline):
    """A just-approved UPDATE materially revises a figure its origin story still asserts
    (the Avici >$1M vs $500,859 class, audit 2026-08-31). The update publishes anyway,
    revising figures is what updates are FOR, but the origin page now carries a stale
    number, so queue THAT story for the corrections loop. The flag rides in
    out/aging_report.json in the exact shape corrections.py reads: {"file": <content
    json basename>, "reason": ...}, and the reason becomes the visible correction note
    (capped at 160 chars there), so it is written for a reader."""
    fname = ""
    for p in glob.glob(os.path.join(HERE, "site", "content", "*.json")):
        try:
            if json.load(open(p, encoding="utf-8")).get("slug") == origin_slug:
                fname = os.path.basename(p)
                break
        except Exception:
            continue
    if not fname:
        return
    reason = (f"the desk's own update revised this story's "
              f"${conflict['published_usd']:,.0f} figure for '{conflict['entity']}' to "
              f"${conflict['candidate_usd']:,.0f}")
    try:
        report = common.read_out("aging_report.json")
    except Exception:
        report = {}
    flags = report.get("flags", [])
    if not any(f.get("file") == fname for f in flags):
        flags.append({"file": fname, "reason": reason})
    report["flags"] = flags
    common.write_out("aging_report.json", report)
    common.gh("warning", f"autopilot: update '{str(update_headline)[:60]}' revises a "
              f"figure the origin story still asserts; queued {fname} for the "
              f"corrections loop")


# ONE CHECKED STORY A DAY (Jack, 4 October 2026, under the 12 September law that he alone
# changes how the newsroom publishes). The evening Edition publishes at most one story: the
# top-ranked candidate that cleared every gate above AND rests on two independent sources
# or one primary source (standing.py). A story on one secondary outlet is never the day's
# story. The rest are held, not discarded: the ones that could have led are written to
# EDITION_HOLD and offered to the NEXT Edition only, as its story if nothing fresh clears
# and the held one is still current. The file is rewritten by every Edition, so a hold
# lives to the next Edition and no further. Breaking runs are untouched by all of this.
EDITION_HOLD = os.path.join(HERE, "site", "data", "edition_hold.json")
SECONDARY = "rests on one secondary outlet, so it is not the day's story"
ONE_A_DAY = "one story a day: held for the next Edition"


def choose_one(cands):
    """cands: [{"cid", "rank", "standing", ...}] for the stories that cleared every gate.
    Returns (chosen candidate or None, held list), each held entry carrying its "why".
    The lowest rank number that may lead wins; ties keep the order given."""
    chosen, held = None, []
    for c in sorted(cands, key=lambda c: c.get("rank") or 10 ** 6):
        if c.get("standing") not in ("corroborated", "primary"):
            held.append(dict(c, why=SECONDARY))
        elif chosen is None:
            chosen = c
        else:
            held.append(dict(c, why=ONE_A_DAY))
    return chosen, held


def et_date(utc_iso):
    from zoneinfo import ZoneInfo
    t = datetime.datetime.fromisoformat((utc_iso or "").replace("Z", "+00:00"))
    return t.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def carried_holds(today, path=None):
    """The holds the PREVIOUS Edition wrote, if it was yesterday's. Anything older is
    dropped: a hold lives to the next Edition and no further."""
    try:
        h = json.load(open(path or EDITION_HOLD, encoding="utf-8"))
    except Exception:
        return []
    prev = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat()
    if h.get("edition_date") != prev:
        return []
    return [s for s in h.get("held") or [] if s.get("why") == ONE_A_DAY and s.get("draft")]


def write_hold(path, today, run_utc, chosen, held, drafts):
    rec = {"edition_date": today, "run_utc": run_utc,
           "published": 1 if chosen else 0,
           "chosen": ({"cid": chosen["cid"], "headline": chosen.get("headline", ""),
                       "rank": chosen.get("rank"), "standing": chosen.get("standing")}
                      if chosen else None),
           "held": [{"cid": h["cid"], "headline": h.get("headline", ""), "rank": h.get("rank"),
                     "standing": h.get("standing"), "why": h["why"],
                     "key_fact": h.get("key_fact", ""), "verdict": "VERIFIED",
                     # the full draft rides along only for a story that could lead, so
                     # the next Edition can publish it without a model call
                     "draft": drafts.get(h["cid"]) if h["why"] == ONE_A_DAY else None}
                    for h in held]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    return rec


# already_published() lived here and was never called by anything. Its corpus scan and its
# is_coverage() preview filter are now inside classify_published(), which is the gate that
# actually runs. Keeping a second, unreachable copy is how the FOMC preview fix came to pass
# its canary while never executing in production.
def edition_choice(approval, drafts, clusters, dry=False):
    """Apply one-story-a-day to an approval set whose gates have already run. Mutates the
    approval decisions, writes EDITION_HOLD (not on a dry run), and returns how many
    stories will publish: 1 or 0."""
    import standing
    try:
        ranked = json.load(open(os.path.join(OUT, "editor.json"), encoding="utf-8"))["ranked"]
        rank = {r["id"]: i + 1 for i, r in enumerate(ranked)}
    except Exception:
        rank = {}
    try:
        run_utc = json.load(open(os.path.join(OUT, "items.json"), encoding="utf-8"))["_meta"]["generated"]
    except Exception:
        run_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = et_date(run_utc)
    stories = approval.get("stories", {})
    cands = []
    for cid, st in stories.items():
        if st.get("decision") != "approve":
            continue
        art = (drafts.get(cid) or {}).get("article_draft") or {}
        cands.append({"cid": cid, "rank": rank.get(cid), "headline": art.get("title") or st.get("headline", ""),
                      "key_fact": ((drafts.get(cid) or {}).get("script_skeleton") or {}).get("key_fact", ""),
                      "standing": standing.standing(art.get("sources") or [], art.get("also_reported_by") or [])})
    chosen, held = choose_one(cands)
    for h in held:
        stories[h["cid"]]["decision"] = "hold"
        stories[h["cid"]]["held_why"] = h["why"]
        print(f"autopilot: HELD #{h['rank']} '{h['headline'][:60]}' ({h['standing']}): {h['why']}")
    if chosen is None:
        chosen = carry_forward(approval, today, dry)
    if chosen:
        print(f"autopilot: THE DAY'S STORY #{chosen.get('rank')} '{chosen['headline'][:70]}' "
              f"({chosen['standing']})")
    else:
        print(f"autopilot: nothing cleared the bar for {today}; the Brief still runs")
    if not dry:
        write_hold(EDITION_HOLD, today, run_utc, chosen, held, drafts)
    return 1 if chosen else 0


def carry_forward(approval, today, dry=False):
    """Nothing fresh cleared. Yesterday's held story becomes today's when it is still
    current: it may lead, and nothing published since has told it already."""
    import standing
    for h in sorted(carried_holds(today), key=lambda h: h.get("rank") or 10 ** 6):
        art = h["draft"].get("article_draft") or {}
        title = art.get("title") or h.get("headline", "")
        kf = (h["draft"].get("script_skeleton") or {}).get("key_fact", "") or h.get("key_fact", "")
        if standing.standing(art.get("sources") or [], art.get("also_reported_by") or []) \
                not in ("corroborated", "primary"):
            continue
        rel, _t, _s = classify_published(title, kf)
        if rel in ("rehash", "update") or dedupe_nothing_new(title, kf)[0]:
            print(f"autopilot: yesterday's held '{title[:60]}' is no longer current ({rel})")
            continue
        new_id = "held-" + h["cid"]
        if not dry:
            d = common.read_out("drafts.json")
            d.setdefault("drafts", []).append(dict(h["draft"], id=new_id))
            common.write_out("drafts.json", d)
            v = common.read_out("verifier.json")
            v.setdefault("verdicts", []).append({"id": new_id, "verdict": "VERIFIED"})
            common.write_out("verifier.json", v)
        approval.setdefault("stories", {})[new_id] = {
            "headline": title, "verifier_verdict": "VERIFIED", "decision": "approve",
            "human_take": "", "carried_from": h["cid"]}
        print(f"autopilot: nothing fresh cleared; yesterday's held story leads: '{title[:60]}'")
        return {"cid": new_id, "rank": h.get("rank"), "headline": title,
                "standing": h.get("standing")}
    return None


def main():
    import consistency  # lazy: consistency imports from this module, so avoid an import cycle
    tpl_path = os.path.join(OUT, "approval_template.json")
    report_path = os.path.join(OUT, "run_report.json")
    # THE WIRE PATH WRITES NO STORY (Jack, 5 October 2026). The run ranked, verified and
    # wrote wire.json; there is no draft to approve and no hold to carry, so nothing here
    # runs and edition_hold.json is left as it stands.
    try:
        if json.load(open(report_path, encoding="utf-8")).get("path") == "wire":
            print("autopilot: the wire path writes no story (the daily written story "
                  "ended, 5 October); nothing to approve")
            return 0
    except Exception:
        pass
    if not (os.path.exists(tpl_path) and os.path.exists(report_path)):
        print("autopilot: no run outputs found -> nothing to publish (fail-closed)")
        return 1
    report = json.load(open(report_path, encoding="utf-8"))
    # --dry-run: every gate and the one-story choice run and print; nothing is written to
    # the hold file, nothing is published, nothing is ingested. Any mode is accepted, since
    # a dry run is how the no-model path is exercised (U-4).
    dry = "--dry-run" in sys.argv
    if not dry and (report.get("mode") != "live" or report.get("status") not in ("ok", "OK", None) and not report.get("review_queue")):
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
            # ADDS NOTHING = REHASH; ADDS ANYTHING = NEWS (owner directive 2026-08-20).
            # "rehash" is NOVELTY_MIN=2, so a follow-up carrying a single new fact was
            # held as a duplicate of the story it developed. Only an exact retelling is
            # held now; a development with anything new falls through to the update branch
            # below, which publishes it chained to its origin story.
            if rel == "rehash" and dedupe_nothing_new(headline, kf)[0]:
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
                # revise figures, so the consistency belt below does not HOLD them, but a
                # material revision leaves the ORIGIN page asserting the stale number (the
                # Avici class, audit 2026-08-31), so the belt still runs against just the
                # origin and a hit queues that story for the corrections loop.
                story["update_of"] = mslug
                updates[cid] = mslug
                revs = [x for x in consistency.figure_conflicts(headline, kf,
                                                                within_days=None)
                        if x.get("slug") == mslug]
                if revs:
                    queue_origin_correction(mslug, revs[0], headline)
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
    if not breaking:
        approved = edition_choice(approval, drafts, clusters, dry)
    if dry:
        print(f"autopilot: DRY RUN, {approved} chosen; nothing written, nothing published")
        return 0
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
