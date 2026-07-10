#!/usr/bin/env python3
"""
verifier.py: Stage 3, the INDEPENDENT verifier AI (audits the editor).

A separate call with an adversarial prompt (the builder never verifies their own work). For
each ranked story it live-fetches the cited source_urls and hands the model the actual page
text, so it can confirm the claim's facts are really present (the same live-source discipline
as the Pet curated-recall verifier). Emits a per-story verdict VERIFIED / NEEDS-HUMAN-REVIEW
/ REJECT and computes divergence from the editor. Fail-closed.

Note: in replay mode the live source fetch is skipped (offline), and every source_check is
recorded as skipped so the model routes unconfirmed items to NEEDS-HUMAN-REVIEW, which is the
correct fail-closed direction for a test run.

USAGE
  python3 verifier.py
  CRYPTO_LLM_MODE=replay python3 verifier.py
"""

import json
import sys

import common
import llm as llmlib

VALID = {"VERIFIED", "NEEDS-HUMAN-REVIEW", "REJECT"}


def gather_sources(story, mode):
    checks = []
    if mode == "replay":
        for url in story.get("source_urls", []) or []:
            checks.append({"url": url, "http_status": None, "text_excerpt": "(skipped: replay mode is offline)"})
        return checks
    for url in (story.get("source_urls", []) or [])[:3]:
        code, text = common.fetch_text(url)
        checks.append({"url": url, "http_status": code,
                       "text_excerpt": (text[:1500] if code == 200 else text)})
    return checks


def build_user(ranked, mode):
    enriched = []
    for s in ranked:
        enriched.append({
            "id": s["id"], "headline": s["headline"], "why_it_matters": s["why_it_matters"],
            "category": s.get("category", "other"), "confidence": s.get("confidence", "medium"),
            "source_urls": s.get("source_urls", []),
            "source_checks": gather_sources(s, mode),
        })
    return ("Audit these ranked stories. For each, use the fetched source_checks to confirm or "
            "refute the claim, then return a verdict.\n\n" + json.dumps(enriched, indent=2))


def validate(obj, ranked):
    if not isinstance(obj, dict) or "verdicts" not in obj or not isinstance(obj["verdicts"], list):
        raise llmlib.LLMError("verifier output missing 'verdicts' list")
    ids = {s["id"] for s in ranked}
    by_id = {}
    for v in obj["verdicts"]:
        vid = v.get("id")
        verdict = v.get("verdict")
        if verdict not in VALID:
            raise llmlib.LLMError(f"verifier: invalid verdict '{verdict}' for id {vid}")
        v.setdefault("reasons", [])
        by_id[vid] = v
    # Fail-closed on coverage: any story the verifier did not judge is treated as REVIEW,
    # never silently promoted.
    for sid in ids:
        if sid not in by_id:
            by_id[sid] = {"id": sid, "verdict": "NEEDS-HUMAN-REVIEW",
                          "reasons": ["verifier returned no verdict for this story"],
                          "source_supported": False, "shill_missed_by_editor": False}
    obj["verdicts"] = [by_id[s["id"]] for s in ranked]
    return obj


def run(client=None):
    cfg = common.load_config()
    editor = common.read_out("editor.json")
    ranked = editor["ranked"]
    client = client or llmlib.Client(cfg)
    system = common.load_prompt("verifier.md")
    user = build_user(ranked, client.mode)

    obj = client.call_json("verifier", system, user)
    obj = validate(obj, ranked)

    counts = {"VERIFIED": 0, "NEEDS-HUMAN-REVIEW": 0, "REJECT": 0}
    for v in obj["verdicts"]:
        counts[v["verdict"]] += 1
    obj["_meta"] = {"stage": "3-verifier", "mode": client.mode,
                    "audited": len(ranked), "counts": counts,
                    "budget": client.budget.summary()}
    path = common.write_out("verifier.json", obj)
    print(f"verifier: {counts} across {len(ranked)} stories -> {path} [mode={client.mode}]")
    return obj


def main():
    try:
        run()
    except llmlib.LLMError as e:
        common.gh("error", f"verifier: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
