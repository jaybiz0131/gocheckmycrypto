#!/usr/bin/env python3
"""
editor.py: Stage 2, the managing-editor AI (rank + de-shill).

Reads out/items.json (Stage 1 clusters), sends the cleaned candidate set to the editor
model, and writes out/editor.json with the ranked top stories and the rejected-for-shill
list, each showing its work. Fail-closed: any parse/shape failure raises, and run.py catches
it and publishes nothing.

USAGE
  python3 editor.py                 # live (needs ANTHROPIC_API_KEY)
  CRYPTO_LLM_MODE=replay python3 editor.py   # offline replay (tests only)
"""

import sys

import common
import llm as llmlib


def build_user(items, top_n):
    clusters = []
    for c in items["clusters"]:
        clusters.append({
            "id": c["id"], "headline": c["headline"], "source": c["source"],
            "source_tier": c["source_tier"], "url": c["url"], "timestamp": c["timestamp"],
            "snippet": c["snippet"], "corroboration": c.get("corroboration", []),
            "shill_score": c["shill_score"], "shill_flags": c["shill_flags"],
            "shill_rejected": c["shill_rejected"],
        })
    import json
    return (f"Here are {len(clusters)} deduplicated story clusters from the last "
            f"{items['_meta'].get('lookback_hours', '?')} hours. Rank the top {top_n} real "
            f"stories and reject the shill.\n\n" + json.dumps(clusters, indent=2))


def validate(obj, top_n):
    if not isinstance(obj, dict) or "ranked" not in obj or "rejected" not in obj:
        raise llmlib.LLMError("editor output missing 'ranked'/'rejected'")
    if not isinstance(obj["ranked"], list) or not isinstance(obj["rejected"], list):
        raise llmlib.LLMError("editor 'ranked'/'rejected' must be lists")
    if len(obj["ranked"]) > top_n:
        obj["ranked"] = obj["ranked"][:top_n]
    for r in obj["ranked"]:
        for f in ("id", "headline", "why_it_matters"):
            if not r.get(f):
                raise llmlib.LLMError(f"editor ranked item missing '{f}': {r}")
        r.setdefault("source_urls", [])
        r.setdefault("confidence", "medium")
        r.setdefault("category", "other")
    return obj


def run(client=None):
    cfg = common.load_config()
    top_n = cfg["top_n"]
    items = common.read_out("items.json")
    client = client or llmlib.Client(cfg)
    system = common.load_prompt("editor.md", TOP_N=top_n)
    user = build_user(items, top_n)

    obj = client.call_json("editor", system, user)
    obj = validate(obj, top_n)

    obj["_meta"] = {"stage": "2-editor", "mode": client.mode,
                    "candidates": len(items["clusters"]),
                    "ranked": len(obj["ranked"]), "rejected": len(obj["rejected"]),
                    "budget": client.budget.summary()}
    path = common.write_out("editor.json", obj)
    print(f"editor: ranked {len(obj['ranked'])} / rejected {len(obj['rejected'])} "
          f"-> {path} [mode={client.mode}]")
    return obj


def main():
    try:
        run()
    except llmlib.LLMError as e:
        common.gh("error", f"editor: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
