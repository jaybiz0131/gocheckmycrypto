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


EDITOR_MAX_CLUSTERS = 120


def build_user(items, top_n):
    pool = items["clusters"]
    if len(pool) > EDITOR_MAX_CLUSTERS:
        # Newest first, keep the cap: a 180-cluster day overwhelms the editor's output
        # budget and truncates its JSON (fail-closed catches it, but we would rather rank
        # the newest 120 than fail). Timestamps are ISO strings; empties sort last.
        pool = sorted(pool, key=lambda c: c.get("timestamp") or "0", reverse=True)
        print(f"editor: {len(items['clusters'])} clusters -> capped to newest {EDITOR_MAX_CLUSTERS}")
        pool = pool[:EDITOR_MAX_CLUSTERS]
    clusters = []
    for c in pool:
        clusters.append({
            "id": c["id"], "headline": c["headline"], "source": c["source"],
            "source_tier": c["source_tier"], "url": c["url"], "timestamp": c["timestamp"],
            "snippet": c["snippet"], "corroboration": c.get("corroboration", []),
            "shill_score": c["shill_score"], "shill_flags": c["shill_flags"],
            "shill_rejected": c["shill_rejected"],
        })
    import json
    # THE LIBRARIAN'S SHELF (charter, 2026-07-15): the editor ranks knowing what the desk
    # already ran, so a repeat only ranks as a genuine UPDATE (the deterministic rerun
    # guard remains the backstop at publish).
    import datetime as _dt
    import glob as _glob
    import os as _os
    recent = []
    cutoff = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=48)).isoformat()
    for p in _glob.glob(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                      "site", "content", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
            if (d.get("published_utc", "") >= cutoff and d.get("title")
                    and not d.get("id", "").startswith("wrap-")):
                recent.append(d["title"])
        except Exception:
            continue
    shelf = (("\n\nAlready published by this desk in the last 48 hours (a repeat of these "
              "ranks ONLY as a genuine update, and its why_it_matters must say what "
              "changed):\n" + "\n".join(f"- {t}" for t in sorted(recent)[:25]) + "\n\n")
             if recent else "\n\n")
    return (f"Here are {len(clusters)} deduplicated story clusters from the last "
            f"{items['_meta'].get('lookback_hours', '?')} hours. Rank the top {top_n} real "
            f"stories and reject the shill." + shelf + json.dumps(clusters, indent=2))


def validate(obj, top_n):
    if not isinstance(obj, dict) or "ranked" not in obj or "rejected" not in obj:
        import json as _json
        raise llmlib.LLMError("editor output missing 'ranked'/'rejected' -- got: "
                              + _json.dumps(obj)[:300])
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

    obj = client.call_json("editor", system, user,
                           validate=lambda o: validate(o, top_n))
    attach_corroboration(obj, items)

    obj["_meta"] = {"stage": "2-editor", "mode": client.mode,
                    "candidates": len(items["clusters"]),
                    "ranked": len(obj["ranked"]), "rejected": len(obj["rejected"]),
                    "budget": client.budget.summary()}
    path = common.write_out("editor.json", obj)
    print(f"editor: ranked {len(obj['ranked'])} / rejected {len(obj['rejected'])} "
          f"-> {path} [mode={client.mode}]")
    return obj



def attach_corroboration(obj, items):
    """Carry the cluster's real corroborating outlets onto each ranked story. DETERMINISTIC.

    source_urls was whatever the model chose to echo back, defaulting to []. The editor is
    handed each cluster's corroboration list and simply did not repeat it, so 76% of
    published stories carried exactly one source while the clusters behind them averaged 17
    corroborating outlets. The desk was doing the cross-outlet work and then throwing the
    evidence away at the first stage that could have kept it.

    Copied rather than requested, for the same reason the boundary fields are: a model asked
    to repeat a list of URLs will drop some, and there is no reason to ask. The model's own
    source_urls are kept and unioned in, in case it cited something outside the cluster.

    This is the input to a two-source rule, not the rule itself. Whether a story with one
    outlet may publish is an editorial decision; this makes the honest count available to
    whoever decides."""
    by_id = {c.get("id"): c for c in (items.get("clusters") or [])}
    for r in obj.get("ranked", []):
        c = by_id.get(r.get("id")) or {}
        urls, seen = [], set()
        for u in list(r.get("source_urls") or []) + [c.get("url")] + \
                [x.get("url") for x in (c.get("corroboration") or [])]:
            u = (u or "").strip()
            if u and u not in seen:
                seen.add(u); urls.append(u)
        r["source_urls"] = urls
        # Outlet names travel too, so a later stage can say WHO corroborated without
        # re-deriving it from a URL.
        names, nseen = [], set()
        for nm in [c.get("source")] + [x.get("name") for x in (c.get("corroboration") or [])]:
            nm = (nm or "").strip()
            if nm and nm not in nseen:
                nseen.add(nm); names.append(nm)
        r["source_outlets"] = names
        r["source_count"] = len(urls)

def main():
    try:
        run()
    except llmlib.LLMError as e:
        common.gh("error", f"editor: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
