#!/usr/bin/env python3
"""
verify_pipeline.py: self-verify the Crypto Cronkite pipeline. Same two-layer discipline as
the Pet recall verifier (_pipeline/verify_curated.py): an offline hard gate that blocks, and
a live notify-only check that never blocks a run.

  LAYER 1  offline canary (HARD FAIL, exit 1, blocks promotion). Proves the pipeline is wired
    and fails closed, with NO network and NO API key:
     - config.json, shill_rules.json well-formed; models carry no temperature/top_p/top_k
       (those 400 on the current model family).
     - prompts exist and carry their load-bearing guardrail tokens (editor: shill/rank;
       verifier: the three verdicts + adversarial; writer: DRAFT + not financial advice +
       human take).
     - shill canary: the deterministic belt scores a known shill headline as rejected and a
       primary-source real story as clean.
     - dedupe canary: two near-identical headlines collapse into one cluster.
     - full offline replay end-to-end (aggregate->editor->verifier->writer->digest) over the
       fixture: exact cluster count, exact editor split, all three verdicts present, only
       VERIFIED+REVIEW drafted, every draft DRAFT-tagged with an empty human_take + disclaimer.
     - fail-closed canaries: a missing API key fails the LLM call closed; a REJECT/hold story
       is never published; a replay-mode approval is refused by publish.
    Any deviation -> ::error:: + exit 1.

  LAYER 2  live source check (NOTIFY-ONLY, exit 3 on content mismatch, never blocks a run).
    Fetches each configured RSS feed and asserts HTTP 200 + looks-like-a-feed. A broken feed
    -> ::error:: + exit 3 (CI marks it failed / opens an issue) but never blocks. A network
    error -> ::warning:: only.

USAGE
  python3 verify_pipeline.py canary     # Layer 1 only (exit 0 pass / 1 fail)
  python3 verify_pipeline.py sources    # Layer 2 only (exit 0 pass / 3 mismatch)
  python3 verify_pipeline.py            # both; only Layer 1 affects the exit code
"""

import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common
import shill as shill_mod
import llm as llmlib

FIXTURE = os.path.join(HERE, "fixtures", "sample_feed.xml")


def gh(level, msg):
    print(f"::{level}::{msg}")


# ---- Layer 1 -----------------------------------------------------------------

def _check(cond, fails, msg):
    if not cond:
        fails.append(msg)


def layer1_canary():
    fails = []
    cfg = common.load_config()

    # config + models
    for stage in ("editor", "verifier", "writer"):
        mc = cfg["models"].get(stage, {})
        _check(mc.get("model"), fails, f"config: models.{stage}.model missing")
        for bad in ("temperature", "top_p", "top_k"):
            _check(bad not in mc, fails, f"config: models.{stage} sets '{bad}' (rejected by the model API)")
    _check(cfg["publish"]["require_human_approval"] is True, fails,
           "config: publish.require_human_approval must be true (the human gate is load-bearing)")
    _check("REJECT" in cfg["publish"]["never_publish_verdict"], fails,
           "config: REJECT must be in never_publish_verdict")

    # shill rules
    rules = shill_mod.load_rules()
    _check(rules.get("tells"), fails, "shill_rules: no tells")
    for t in rules.get("tells", []):
        for f in ("id", "pattern", "weight", "reason"):
            _check(f in t, fails, f"shill_rules: tell missing '{f}': {t.get('id','?')}")

    # prompts carry their guardrails
    guards = {
        "editor.md": ["shill", "rank", "JSON"],
        "verifier.md": ["VERIFIED", "NEEDS-HUMAN-REVIEW", "REJECT", "adversarial"],
        "writer.md": ["DRAFT", "financial advice", "human take", "human_take"],
    }
    for name, toks in guards.items():
        try:
            text = common.load_prompt(name)
        except Exception as e:
            fails.append(f"prompt {name}: cannot read ({e})")
            continue
        low = text.lower()
        for tk in toks:
            _check(tk.lower() in low, fails, f"prompt {name}: missing guardrail token '{tk}'")

    # shill belt canary: a moon post is rejected; a primary-source item is clean
    moon = {"headline": "PEPECOIN to $10 imminent, get in early", "snippet": "sponsored presale, 100x moon",
            "source": "x", "source_tier": "unknown", "url": "http://x"}
    real = {"headline": "SEC charges Acme Labs over unregistered securities offering", "snippet": "",
            "source": "SEC", "source_tier": "primary", "url": "http://sec"}
    shill_mod.annotate([moon, real], rules)
    _check(moon["shill_rejected"] is True, fails,
           f"shill canary: moon post not rejected (score={moon['shill_score']})")
    _check(real["shill_rejected"] is False and real["shill_score"] == 0, fails,
           f"shill canary: primary-source item wrongly flagged (score={real['shill_score']})")

    # dedupe canary: two near-identical headlines collapse
    import aggregate
    dup = [
        {"headline": "SEC charges Acme Labs over unregistered securities offering",
         "source": "A", "source_tier": "primary", "url": "u1", "timestamp": "", "snippet": ""},
        {"headline": "SEC charges Acme Labs over unregistered securities offering, seeks penalties",
         "source": "B", "source_tier": "major", "url": "u2", "timestamp": "", "snippet": ""},
        {"headline": "Ethereum core developers set date for next network upgrade",
         "source": "C", "source_tier": "major", "url": "u3", "timestamp": "", "snippet": ""},
    ]
    clusters = aggregate.dedupe(dup, cfg)
    _check(len(clusters) == 2, fails, f"dedupe canary: expected 2 clusters, got {len(clusters)}")

    # full offline replay end-to-end over the fixture
    e2e_fails = _replay_e2e()
    fails.extend(e2e_fails)

    # fail-closed canaries
    fails.extend(_failclosed_canaries(cfg))

    if fails:
        for f in fails:
            gh("error", "canary: " + f)
        print(f"\nLAYER 1 CANARY: FAIL ({len(fails)} problem(s)) -> promotion BLOCKED (exit 1)")
        return 1
    print("LAYER 1 CANARY: PASS -> pipeline wired, shill/dedupe belts work, offline replay "
          "end-to-end produces a DRAFT-tagged review queue, and every fail-closed gate holds.")
    return 0


def _replay_e2e():
    """Run the whole pipeline in replay mode over the fixture and assert the invariants."""
    fails = []
    os.environ["CRYPTO_LLM_MODE"] = "replay"
    cfg = common.load_config()
    client = llmlib.Client(cfg, mode="replay")
    import aggregate, editor, verifier, writer, digest
    try:
        rc = aggregate.run(fixture=FIXTURE, out_path=os.path.join(common.OUT_DIR, "items.json"))
        _check(rc == 0, fails, f"replay: aggregate exit {rc}")
        items = common.read_out("items.json")
        _check(items["_meta"]["clusters"] == 5, fails,
               f"replay: expected 5 fixture clusters, got {items['_meta']['clusters']}")

        ed = editor.run(client=client)
        _check(len(ed["ranked"]) == 3 and len(ed["rejected"]) == 2, fails,
               f"replay: editor split expected 3/2, got {len(ed['ranked'])}/{len(ed['rejected'])}")

        ve = verifier.run(client=client)
        verds = {v["verdict"] for v in ve["verdicts"]}
        _check(verds == {"VERIFIED", "NEEDS-HUMAN-REVIEW", "REJECT"}, fails,
               f"replay: expected all three verdicts, got {sorted(verds)}")

        wr = writer.run(client=client)
        drafted = {d["id"] for d in wr["drafts"]}
        rejected_ids = {v["id"] for v in ve["verdicts"] if v["verdict"] == "REJECT"}
        _check(drafted and drafted.isdisjoint(rejected_ids), fails,
               f"replay: writer drafted a REJECT story or drafted nothing (drafted={drafted})")
        for d in wr["drafts"]:
            art = d["article_draft"]
            _check(art["status"] == "DRAFT", fails, f"replay: draft {d['id']} not DRAFT-tagged")
            _check(art["human_take"] == "", fails, f"replay: draft {d['id']} human_take not empty")
            _check("financial advice" in art["not_financial_advice"].lower(), fails,
                   f"replay: draft {d['id']} missing not-financial-advice disclaimer")

        digest.run(date="canary")
        qmd = os.path.join(common.OUT_DIR, "review_queue", "canary.md")
        _check(os.path.exists(qmd), fails, "replay: digest did not write the review queue")
        tmpl = common.read_out("approval_template.json")
        _check(all(s["decision"] == "hold" for s in tmpl["stories"].values()), fails,
               "replay: approval template must default every story to 'hold'")
        _check(all(v["id"] not in tmpl["stories"] for v in ve["verdicts"] if v["verdict"] == "REJECT"),
               fails, "replay: a REJECT story leaked into the approval template")
    except Exception as e:
        fails.append(f"replay: end-to-end raised {type(e).__name__}: {e}")
    return fails


def _failclosed_canaries(cfg):
    fails = []
    # (a) missing key fails the LLM call closed
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        live = llmlib.Client(cfg, mode="live")
        try:
            live.call_json("editor", "sys", "user")
            fails.append("fail-closed: live call with no API key did NOT raise")
        except llmlib.LLMError:
            pass
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved

    # (b) budget cap trips
    tiny = llmlib.Budget(max_tokens=10, max_usd=100)
    try:
        tiny.record("claude-opus-4-8", {"input_tokens": 1000, "output_tokens": 1000})
        fails.append("fail-closed: budget cap did NOT trip on overspend")
    except llmlib.BudgetError:
        pass

    # (c) publish refuses a replay-mode approval and an unapproved/hold story
    import publish
    tmp = os.path.join(common.OUT_DIR, "approval_replay.json")
    common.write_out(os.path.basename(tmp), {"mode": "replay", "stories": {
        "c000": {"decision": "approve", "human_take": "x"}}})
    res = publish.run(approval_path=tmp)
    _check(res["published"] == [], fails, "fail-closed: publish accepted a replay-mode approval")

    common.write_out(os.path.basename(tmp), {"mode": "live", "stories": {
        "c000": {"decision": "hold", "human_take": ""}}})
    res2 = publish.run(approval_path=tmp)
    _check(res2["published"] == [], fails, "fail-closed: publish accepted a 'hold' story")
    return fails


# ---- Layer 2 -----------------------------------------------------------------

def layer2_sources():
    cfg = common.load_config()
    mismatch = False
    for f in cfg["sources"]["rss"]:
        name, url = f["name"], f["url"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": common.UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.getcode()
                head = r.read(2000).decode("utf-8", "replace").lower()
        except Exception as e:
            gh("warning", f"sources: '{name}' fetch failed ({url}): {e} -- soft warning only, NOT failing")
            continue
        if code != 200:
            gh("error", f"sources: '{name}' did not resolve 200 (got {code}): {url}")
            mismatch = True
            continue
        if not ("<rss" in head or "<feed" in head or "<rdf" in head or "<?xml" in head):
            gh("error", f"sources: '{name}' did not look like an RSS/Atom feed: {url}")
            mismatch = True
        else:
            print(f"LAYER 2 sources: OK '{name}' -> HTTP 200, feed-shaped.")
    if mismatch:
        print("\nLAYER 2 SOURCES: CONTENT MISMATCH -> notify (exit 3). Does NOT block a run.")
        return 3
    print("LAYER 2 SOURCES: PASS -> all configured feeds resolve 200 and look like feeds.")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "canary":
        sys.exit(layer1_canary())
    if cmd == "sources":
        sys.exit(layer2_sources())
    c = layer1_canary()
    s = layer2_sources()
    print(f"\n[gate] Layer1 canary = {'PASS' if c == 0 else 'FAIL'} | "
          f"Layer2 sources = {'PASS' if s == 0 else 'MISMATCH (notify, non-blocking)'}")
    sys.exit(c)  # ONLY Layer 1 blocks


if __name__ == "__main__":
    main()
