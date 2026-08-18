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

import datetime
import re
import sys

import common
import llm as llmlib
import calendar_check


EDITOR_MAX_CLUSTERS = 260  # was 120 (owner directive 2026-08-18, quality over quantity):
                           # a 212-cluster sports morning meant the editor never saw 92 of
                           # the day's stories, so the "best 8" were the best of a little
                           # over half the day. Choosing from the whole day is a selection
                           # improvement that costs input tokens only, and a full run bills
                           # 112k against a 400k cap.


# ---- the calendar duty (2026-08-02) --------------------------------------------------------
# The calendar was advisory and the desk missed two events it had PROMISED readers in the
# Week Ahead story: the FOMC decision died at the approver three runs straight with nobody
# noticing the pattern, and Strategy's Q2 never entered intake at all because no feed
# clustered it. calendar_check wrote out/calendar_gaps.json "for the editor", but nothing
# ever read it, and it ran after the pipeline in a workspace about to be discarded.
# Now the duty is structural: every due-uncovered event is handed to the editor as a
# MANDATORY decision (cover it, or pass with a stated reason), a synthetic cluster built
# from the event's own source URL guarantees there is always intake to cover from, and a
# deterministic check fails the run if any decision is missing. Covering stays a judgment
# call; silently not deciding is no longer possible.

def calendar_duties(mode):
    """Due-uncovered events, or [] outside live mode (replay fixtures predate the
    calendar; the enforcement logic itself is canaried in verify_pipeline). A broken
    calendar warns and skips rather than stopping the news: fail-closed protects what
    the desk SAYS, and a duty roster is not copy. The advisory workflow step still
    warns independently, so a dead calendar cannot go quiet."""
    if mode != "live":
        return []
    try:
        return calendar_check.gaps()
    except Exception as e:
        common.gh("warning", f"editor: calendar unreadable, duty roster skipped ({e})")
        return []


def ensure_duty_clusters(items, duties):
    """A decision to cover needs intake to cover FROM (brief-bound law: no fact outside
    sources). For each duty, find the clusters whose text already matches the event's
    AND-groups; an event no feed carried gets a synthetic single-source cluster built
    from the calendar entry's own source URL, which then rides the verifier, researcher
    and every downstream gate exactly like any other single-source cluster."""
    clusters = items["clusters"]

    def text(c):
        return (str(c.get("headline", "")) + " " + str(c.get("snippet", ""))).lower()

    for i, ev in enumerate(duties):
        groups = [[t.lower() for t in g if t] for g in (ev.get("match") or []) if g]
        ev["_cluster_ids"] = [c["id"] for c in clusters
                             if any(all(t in text(c) for t in g) for g in groups)]
        if not ev["_cluster_ids"]:
            slug = re.sub(r"[^a-z0-9]+", "-", str(ev.get("title", "")).lower())[:40]
            cid = f"cal-{i}-{slug}".strip("-")
            clusters.append({
                "id": cid,
                "headline": str(ev.get("title", "")),
                "source": str(ev.get("source_name") or "desk calendar"),
                "source_tier": 2,
                "url": str(ev.get("source", "")),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "snippet": str(ev.get("detail", ""))[:400],
                "corroboration": [],
                "shill_score": 0, "shill_flags": [], "shill_rejected": False,
            })
            ev["_cluster_ids"] = [cid]
    return items


def duty_section(duties):
    if not duties:
        return ""
    lines = []
    for ev in duties:
        lines.append(f"- \"{ev.get('title')}\" ({ev.get('kind')}, {ev.get('date')}): "
                     f"candidate cluster id(s): {', '.join(ev['_cluster_ids'])}")
    return ("\n\nMANDATORY CALENDAR DECISIONS. The desk's forward calendar (which the "
            "published Week Ahead story promised to readers) lists these events as due "
            "and not yet covered:\n" + "\n".join(lines) +
            "\nFor EACH event you MUST record a decision in the calendar_decisions "
            "output field: either cover it (rank one of its candidate clusters and cite "
            "that cluster_id) or pass with a concrete reason (a legitimate pass exists: "
            "a non-event, a story better held for confirmation). Silence is not an "
            "option; a missing decision fails this run.\n")


def enforce_duties(obj, duties):
    """Deterministic: every duty carries a decision; cover names a ranked cluster;
    pass states a reason. Raises LLMError so the contract ladder retries with the
    failure explained."""
    if not duties:
        return
    decisions = obj.get("calendar_decisions")
    if not isinstance(decisions, list):
        raise llmlib.LLMError(
            "calendar_decisions missing: every MANDATORY CALENDAR DECISION event needs "
            "an entry {title, decision: cover|pass, cluster_id (for cover), reason "
            "(for pass)}")
    by_title = {str(d.get("title", "")).strip().lower(): d for d in decisions}
    ranked_ids = {r.get("id") for r in obj.get("ranked", [])}
    for ev in duties:
        d = by_title.get(str(ev.get("title", "")).strip().lower())
        if not d:
            raise llmlib.LLMError(f"calendar_decisions has no entry for due event "
                                  f"'{ev.get('title')}'")
        if d.get("decision") == "cover":
            if d.get("cluster_id") not in ranked_ids:
                raise llmlib.LLMError(
                    f"decision covers '{ev.get('title')}' via cluster "
                    f"'{d.get('cluster_id')}' but no ranked story carries that id; "
                    f"rank it or pass with a reason")
        elif d.get("decision") == "pass":
            if not str(d.get("reason", "")).strip():
                raise llmlib.LLMError(f"pass on '{ev.get('title')}' needs a concrete "
                                      f"reason; an empty reason is a silent miss")
        else:
            raise llmlib.LLMError(f"decision for '{ev.get('title')}' must be "
                                  f"'cover' or 'pass', got {d.get('decision')!r}")


def build_user(items, top_n, duties=None):
    pool = items["clusters"]
    if len(pool) > EDITOR_MAX_CLUSTERS:
        # Newest first, keep the cap: a 180-cluster day overwhelms the editor's output
        # budget and truncates its JSON (fail-closed catches it, but we would rather rank
        # the newest 120 than fail). Timestamps are ISO strings; empties sort last.
        # CORROBORATION SURVIVES THE CAP (owner directive 2026-08-18). Sorting by recency
        # alone drops well-attested stories for fresher thin ones, which is backwards on a
        # desk whose promise is cross-outlet verification. The Lakers sale arrived in six
        # separate clusters and still missed the cut. Heavily corroborated clusters are
        # kept first, then the newest fill the rest.
        pool = sorted(pool, key=lambda c: (-len(c.get("corroboration") or []),
                                           c.get("timestamp") or "0"), reverse=False)
        pool = sorted(pool, key=lambda c: len(c.get("corroboration") or []), reverse=True)
        keep = pool[:EDITOR_MAX_CLUSTERS]
        print(f"editor: {len(items['clusters'])} clusters -> capped to "
              f"{EDITOR_MAX_CLUSTERS}, best-corroborated kept first")
        pool = sorted(keep, key=lambda c: c.get("timestamp") or "0", reverse=True)
        # a duty's candidate cluster must never be capped out of the editor's sight: the
        # mandate to decide is meaningless if the thing to decide about was dropped
        duty_ids = {cid for ev in (duties or []) for cid in ev.get("_cluster_ids", [])}
        have = {c["id"] for c in pool}
        pool += [c for c in items["clusters"] if c["id"] in duty_ids - have]
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
    # THE CORROBORATION FLOOR (owner directive 2026-08-18, quality over quantity). This
    # does not tell the editor to rank more stories; it tells it which ones it may not
    # ignore. A story independently carried by several outlets is the desk's strongest
    # available quality signal, computed for free at intake, and it is exactly the signal
    # that was present and unused when the Lakers sale (six clusters), Westbrook and the
    # Leavitt departure all missed the cut on the day competitors led with them.
    # Corroboration alone is NOT a quality signal, and testing this against real intake
    # proved it: "PEPECOIN to $10 imminent, get in early" carried thirteen outlets and
    # would have been protected by a naive count. Pump content is precisely what gets
    # republished widely. The floor therefore respects the desk's own shill belt, which
    # already scored that story 9 and rejected it, and takes only clusters the belt left
    # clean.
    floor = sorted((c for c in clusters
                    if len(c.get("corroboration") or []) >= 3
                    and not c.get("shill_rejected")
                    and not (c.get("shill_flags") or [])
                    and (c.get("shill_score") or 0) == 0),
                   key=lambda c: -len(c.get("corroboration") or []))[:5]
    floor_note = ""
    if floor:
        floor_note = ("\n\nINDEPENDENTLY CORROBORATED, RANK OR EXPLAIN: each of these is "
                      "carried by three or more independent outlets, the strongest signal "
                      "this desk has that a story is real and that readers will meet it "
                      "elsewhere. Rank it, or leave it out only for a reason you would "
                      "defend to the editor-in-chief (already covered, not this desk's "
                      "beat, thin despite the outlet count):\n"
                      + "\n".join(f"- {c['id']}: {c['headline'][:110]} "
                                  f"({len(c.get('corroboration') or [])} outlets)"
                                  for c in floor) + "\n")
    return (f"Here are {len(clusters)} deduplicated story clusters from the last "
            f"{items['_meta'].get('lookback_hours', '?')} hours. Rank the top {top_n} real "
            f"stories and reject the shill." + floor_note + shelf + duty_section(duties or [])
            + json.dumps(clusters, indent=2))


def validate(obj, top_n, duties=None):
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
    enforce_duties(obj, duties or [])
    return obj


def run(client=None):
    cfg = common.load_config()
    top_n = cfg["top_n"]
    items = common.read_out("items.json")
    client = client or llmlib.Client(cfg)
    duties = calendar_duties(client.mode)
    if duties:
        ensure_duty_clusters(items, duties)
        common.write_out("items.json", items)  # downstream stages see the same intake
        print(f"editor: {len(duties)} mandatory calendar decision(s) due: "
              + "; ".join(str(e.get("title")) for e in duties))
    system = common.load_prompt("editor.md", TOP_N=top_n)
    user = build_user(items, top_n, duties)

    obj = client.call_json("editor", system, user,
                           validate=lambda o: validate(o, top_n, duties))
    attach_corroboration(obj, items)
    for d in obj.get("calendar_decisions") or []:
        # a pass is legitimate but never quiet: it goes in the run log as an annotation
        # a human scans, and in editor.json where the record survives the run
        common.gh("notice", f"calendar decision: {d.get('decision')} "
                            f"'{d.get('title')}'"
                            + (f" ({d.get('reason')})" if d.get("reason") else ""))

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
