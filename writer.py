#!/usr/bin/env python3
"""
writer.py: Stage 4, the writer AI (drafts).

Drafts the stories that SURVIVED verification (VERIFIED, plus NEEDS-HUMAN-REVIEW which the
human may promote) into a script skeleton and an article draft, in the Crypto Cronkite voice:
factual, sourced, neutral on price, with a not-financial-advice disclaimer and an explicit,
empty human-take slot. REJECT stories are never drafted. Everything is tagged DRAFT. Fail-closed.

USAGE
  python3 writer.py
  CRYPTO_LLM_MODE=replay python3 writer.py
"""

import json
import sys

import common
import llm as llmlib

DRAFTABLE = {"VERIFIED", "NEEDS-HUMAN-REVIEW"}
NFA = "Crypto Cronkite reports events. It never advises trades. Nothing here is financial advice."


def select(editor, verifier):
    by_verdict = {v["id"]: v for v in verifier["verdicts"]}
    # The aggregate clusters carry the actual reporting (snippet + who corroborated it).
    # Without them the writer sees only a headline and a two-line significance note, which
    # is why early articles ran thin: give it the source material the desk already has.
    clusters = {}
    try:
        for c in common.read_out("items.json").get("clusters", []):
            clusters[c.get("id")] = c
    except Exception:
        pass
    out = []
    for s in editor["ranked"]:
        v = by_verdict.get(s["id"])
        if not v or v["verdict"] not in DRAFTABLE:
            continue
        story = {**s, "verdict": v["verdict"]}
        c = clusters.get(s["id"])
        if c:
            story["source_material"] = {
                "summary": (c.get("snippet") or "")[:600],
                "first_seen": c.get("timestamp", ""),
                "reported_by": [c.get("source", "")] + [
                    x.get("name", "") for x in (c.get("corroboration") or [])[:6]],
            }
        out.append(story)
    return out


def validate(obj, stories):
    if not isinstance(obj, dict) or not isinstance(obj.get("drafts"), list):
        raise llmlib.LLMError("writer output missing 'drafts' list")
    ids = {s["id"] for s in stories}
    by_id = {s["id"]: s for s in stories}
    for d in obj["drafts"]:
        if d.get("id") not in ids:
            raise llmlib.LLMError(f"writer drafted an unexpected/unverified id: {d.get('id')}")
        art = d.get("article_draft") or {}
        skel = d.get("script_skeleton") or {}
        if not art or not skel:
            raise llmlib.LLMError(f"writer draft {d.get('id')} missing article_draft or script_skeleton")
        # Enforce the guardrails regardless of what the model returned.
        # If the model skipped The Bottom Line closer, fall back to the editor's
        # why_it_matters line rather than publishing without one.
        if not (art.get("bottom_line") or "").strip():
            art["bottom_line"] = by_id[d["id"]].get("why_it_matters", "")
        art["status"] = "DRAFT"
        art["not_financial_advice"] = NFA
        art.setdefault("human_take", "")
        art["human_take"] = ""  # never let the model fabricate the take
        skel.setdefault("human_take", "")
        skel["human_take"] = ""
        d["article_draft"], d["script_skeleton"] = art, skel
    return obj


def run(client=None):
    cfg = common.load_config()
    editor = common.read_out("editor.json")
    verifier = common.read_out("verifier.json")
    stories = select(editor, verifier)
    client = client or llmlib.Client(cfg)

    if not stories:
        # Nothing survived verification. That is a valid, fail-closed outcome: write an empty
        # draft set (the digest will show an empty queue) without spending an API call.
        obj = {"drafts": [], "_meta": {"stage": "4-writer", "mode": client.mode,
               "draftable": 0, "note": "no VERIFIED or REVIEW stories to draft",
               "budget": client.budget.summary()}}
        common.write_out("drafts.json", obj)
        print("writer: 0 draftable stories (nothing survived verification) -> out/drafts.json")
        return obj

    system = common.load_prompt("writer.md")
    user = ("Draft these verified stories. Two formats each, DRAFT-tagged, human_take left "
            "empty.\n\n" + json.dumps(stories, indent=2))
    obj = client.call_json("writer", system, user)
    obj = validate(obj, stories)

    obj["_meta"] = {"stage": "4-writer", "mode": client.mode,
                    "draftable": len(stories), "drafted": len(obj["drafts"]),
                    "budget": client.budget.summary()}
    path = common.write_out("drafts.json", obj)
    print(f"writer: drafted {len(obj['drafts'])}/{len(stories)} -> {path} [mode={client.mode}]")
    return obj


def main():
    try:
        run()
    except llmlib.LLMError as e:
        common.gh("error", f"writer: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
