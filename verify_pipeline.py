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

import inspect
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
        "researcher.md": ["brief", "confidence", "bear_case", "unconfirmed", "thin"],
        "writer.md": ["DRAFT", "financial advice", "human take", "human_take", "brief",
                      "never pad", "what to watch"],
        "approver.md": ["APPROVE", "REJECT", "accuracy", "balance", "clarity", "compliance",
                        "smuggled"],
        "wrap.md": ["voice of reason", "what to watch", "never what to do", "no em dashes",
                    "todays_stories", "desk_boards"],
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

    # whale-flow classification canary (offline, deterministic over the sample transactions)
    fails.extend(_whale_flow_canary())
    fails.extend(_window_belt_canary())
    fails.extend(_coin_screen_canary())
    fails.extend(_regwatch_canary())
    fails.extend(_hackwatch_canary())
    fails.extend(_fedreg_canary())
    fails.extend(_dedupe_guard_canary())
    fails.extend(_boundary_canary())
    fails.extend(_front_page_canary())
    fails.extend(_preview_suppression_canary())
    fails.extend(_consistency_gate_canary())
    fails.extend(_merge_state_canary())

    # full offline replay end-to-end over the fixture
    e2e_fails = _replay_e2e()
    fails.extend(e2e_fails)

    # fail-closed canaries
    fails.extend(_failclosed_canaries(cfg))

    # contract ladder + slot recovery (the 2026-07-15 self-healing layer)
    fails.extend(_contract_ladder_canary(cfg))

    if fails:
        for f in fails:
            gh("error", "canary: " + f)
        print(f"\nLAYER 1 CANARY: FAIL ({len(fails)} problem(s)) -> promotion BLOCKED (exit 1)")
        return 1
    print("LAYER 1 CANARY: PASS -> pipeline wired, shill/dedupe belts work, offline replay "
          "end-to-end produces a DRAFT-tagged review queue, and every fail-closed gate holds.")
    return 0


def _fedreg_canary():
    """Federal rulemaking onto the calendar, offline against fixture documents.

    The desk's regulatory awareness ran entirely off its own published stories via
    regwatch, so it could not know about a rule until someone else wrote about it. This
    closes that, and these cases pin the two things that make it trustworthy."""
    fails = []
    import datetime as _dt
    import fedreg as fr

    doc = {"title": "Permitted Payment Stablecoin Issuer Customer Identification Programs",
           "abstract": "FinCEN is proposing requirements for stablecoin issuers.",
           "publication_date": "2026-06-22", "type": "Proposed Rule",
           "comments_close_on": "2026-08-21", "document_number": "2026-1",
           "agencies": [{"name": "Financial Crimes Enforcement Network"}],
           "html_url": "http://fr/1", "docket_ids": ["FINCEN-2026-0001"]}
    ev = fr.events(docs=[doc], today=_dt.date(2026, 7, 31))
    kinds = {e["kind"] for e in ev}
    _check("proposed rule" in kinds, fails,
           "fedreg: the rule's publication is no longer an event")
    _check("comment deadline" in kinds, fails,
           "fedreg: the comment deadline is no longer an event; that deadline is the "
           "forward-looking thing this module exists to surface")
    dl = next((e for e in ev if e["kind"] == "comment deadline"), None)
    _check(dl and dl["date"] == "2026-08-21", fails,
           "fedreg: the deadline event is not dated on the closing date")
    _check(dl and ["fincen", "stablecoin"] in dl["match"], fails,
           "fedreg: match groups lost the agency+topic pairing, so coverage of the rule "
           "cannot be recognised")

    # a passed deadline is history, not a forthcoming event
    _check(not [e for e in fr.events(docs=[doc], today=_dt.date(2026, 9, 30))
                if e["kind"] == "comment deadline"], fails,
           "fedreg: a closed comment period is still being carried as a deadline")

    # an off-topic rule from a covered agency must not reach the calendar
    off = dict(doc, title="Submarine Cable Landing Licence Rules",
               abstract="Review of licensing procedures.", comments_close_on=None,
               document_number="2026-2")
    _check(fr.events(docs=[off], today=_dt.date(2026, 7, 31)) == [], fails,
           "fedreg: an off-topic rule reached the calendar; the term filter is what keeps "
           "this from burying the real ones")

    # THE QUIET FAILURE. The API returns zero for a quoted OR term the moment a date filter
    # is added, which looks exactly like "no crypto rulemaking" and is undetectable
    # downstream. One query per term is the fix; a single combined term must not come back.
    _check(isinstance(fr.TERMS, (list, tuple)) and len(fr.TERMS) >= 4, fails,
           "fedreg: TERMS collapsed to a combined query; the API silently returns zero for "
           "a quoted OR expression once a date filter is applied, which reads as clean")
    _check(not any(" OR " in t for t in fr.TERMS), fails,
           "fedreg: a term contains an OR expression, which the API drops to zero when "
           "combined with a date filter")

    # the reader-facing Week Ahead must keep running off the CURATED calendar only
    import inspect
    import week_ahead
    _check("fedreg" not in inspect.getsource(week_ahead), fails,
           "fedreg: week_ahead now reads the generated calendar; machine-selected entries "
           "would reach readers in a published story without review")
    return fails

def _hackwatch_canary():
    """The exploit coverage check, offline against a fixture ledger.

    Nobody schedules a hack, so the curated calendar cannot cover this beat and an
    independent ledger is the only way to answer "did we miss one?". Run against the live
    dataset over 30 days this found five uncovered exploits above $1M, including a $21.3M
    one, so the check earns its place; these cases keep it honest.

    The asymmetry matters: a false "uncovered" is a flag someone closes, a false "covered"
    is silence. So coverage requires BOTH the protocol name and exploit language, and the
    story must not predate the hack."""
    fails = []
    import datetime as _dt
    import hackwatch as hw

    today = _dt.date(2026, 7, 30)
    ts = int(_dt.datetime(2026, 7, 29, tzinfo=_dt.timezone.utc).timestamp())
    ledger = [
        {"date": ts, "amount": 21_300_000, "name": "BonkDAO", "technique": "Governance",
         "chain": ["Solana"], "source": "http://x"},
        {"date": ts, "amount": 5_000, "name": "Dustcoin", "technique": "Rug"},
    ]

    def run(stories):
        hw._corpus = lambda within_days=14: stories
        return hw.gaps(days_back=4, today=today, hacks=ledger)

    _check([e["title"] for e in run([])] == ["BonkDAO exploit, $21,300,000"], fails,
           "hackwatch: missed an uncovered exploit, or flagged one below the floor")

    _check(run([("2026-07-29", "bonkdao drained in a governance exploit")]) == [], fails,
           "hackwatch: real coverage was not recognised, which turns the flag into noise")

    _check(len(run([("2026-07-29", "bonkdao announces a new staking program")])) == 1, fails,
           "hackwatch: a story that merely names the protocol counted as exploit coverage; "
           "a false 'covered' is silent and is the failure that matters")

    _check(len(run([("2026-07-28", "bonkdao hit by an exploit")])) == 1, fails,
           "hackwatch: a story published BEFORE the exploit counted as coverage of it")

    _check(hw.gaps(days_back=4, today=_dt.date(2026, 8, 20), hacks=ledger) == [], fails,
           "hackwatch: an exploit outside the window is still being flagged")

    # an unreachable ledger must return None, which main() treats as "no check ran"
    hw._fetch = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))
    _check(hw.gaps(days_back=4, today=today) is None, fails,
           "hackwatch: an unreachable source no longer fails open; a check that cannot run "
           "must never look like a clean result")

    _check(hw._name_terms("AFX Bridge") == ["afx bridge", "bridge"] or
           hw._name_terms("AFX Bridge") == ["afx bridge"], fails,
           "hackwatch: name terms changed shape unexpectedly")
    _check("the" not in hw._name_terms("The Pool"), fails,
           "hackwatch: a short leading word became a match term and will match everything")
    return fails

def _regwatch_canary():
    """A tracked storyline must belong to the jurisdiction whose measure it is.

    The tracker paired an unhomed instrument with every country named ANYWHERE in a story,
    so a US Treasury sanctions piece citing Executive Order 13902, which also noted that
    the sanctioned shipping companies were based in China and Hong Kong, filed
    "China :: Executive Order" and "Hong Kong :: Executive Order". Those are not
    imprecise, they are false: neither country issued it.

    Jurisdictions now come from the headline and lede. The canary pins that the rule holds
    AND that it did not over-correct, because a tracker that files nothing is as useless as
    one that files nonsense."""
    fails = []
    import regwatch as rw

    story = {"title": "US Treasury sanctions Iranian firms using Bitcoin for maritime extortion",
             "dek": "OFAC designated two insurers under a US executive order.",
             "key_fact": "Both firms now fall under Executive Order 13902.",
             "body": ["The Treasury also designated eight shipping companies based in "
                      "China, Hong Kong and the Marshall Islands in the same action."]}
    full = rw._story_text(story)
    _, instr, _ = rw.extract(full)
    juris, _, _ = rw.extract(rw.subject_text(story))
    keys = {f"{a} :: {b}" for a, b in rw._pairs(juris, instr)}
    for bogus in ("China :: Executive Order", "Hong Kong :: Executive Order"):
        _check(bogus not in keys, fails,
               f"regwatch: filed {bogus!r}; a country mentioned in the body is not the "
               f"issuer of the measure")
    _check("United States :: Executive Order" in keys, fails,
           "regwatch: the story's actual jurisdiction stopped being filed, which is the "
           "over-correction that makes the tracker useless")

    # a jurisdiction named only in the body is a mention, not a storyline
    only_body = {"title": "Russia's parliament passes crypto market law",
                 "dek": "A transition period runs to 2027.",
                 "key_fact": "Retail investors face an annual cap.",
                 "body": ["EU countermeasures may tighten as reliance on crypto grows."]}
    j2, _, _ = rw.extract(rw.subject_text(only_body))
    _check("Russia" in j2, fails,
           "regwatch: Russia is invisible again; six regulatory headlines named it and the "
           "tracker filed them under the European Union instead")
    _check("European Union" not in j2, fails,
           "regwatch: a body-only mention is being tracked as that jurisdiction's own "
           "storyline")

    # The WIRING, not just the helpers. The first version of this canary tested _pairs and
    # subject_text underneath update(), so a regression that reverted update() to body-wide
    # jurisdictions passed clean. story_pairs is the real filing decision; exercise it.
    keys2 = {f"{a} :: {b}" for a, b in rw.story_pairs(story)[0]}
    _check("United States :: Executive Order" in keys2
           and "China :: Executive Order" not in keys2, fails,
           "regwatch: story_pairs files the wrong jurisdiction; the rule is not wired into "
           "the path update() actually takes")

    # Replay must not touch committed state. wrap.py calls update() on every edition,
    # including the replay this verifier runs, so without the guard a TEST RUN writes the
    # ledger. Sabotage-testing this very canary did exactly that: it wrote five false
    # storylines into regwatch.json that survived restoring the code, because update only
    # ever adds.
    import os as _os
    _before = _os.environ.get("CRYPTO_LLM_MODE")
    try:
        _os.environ["CRYPTO_LLM_MODE"] = "replay"
        _stat = _os.stat(rw.LEDGER).st_mtime_ns if _os.path.exists(rw.LEDGER) else None
        rw.update()
        _after = _os.stat(rw.LEDGER).st_mtime_ns if _os.path.exists(rw.LEDGER) else None
        _check(_stat == _after, fails,
               "regwatch: update() wrote the committed ledger during a replay run; a "
               "verification must never mutate committed state")
    finally:
        if _before is None:
            _os.environ.pop("CRYPTO_LLM_MODE", None)
        else:
            _os.environ["CRYPTO_LLM_MODE"] = _before
    return fails

def _coin_screen_canary():
    """Lock the on-chain supply check, offline.

    The board's whole claim is that a market cap is a price times a supply and that both
    are real. The other supply test compares CoinGecko against CoinGecko, so it can only
    catch a listing that disagrees with itself. This one is the independent read.

    Two properties, and the second matters more than the first. It must catch a cap built
    on more supply than exists; and it must NEVER fire on a multi-chain token, whose
    Ethereum supply is a fraction of its real total. A false positive here silently deletes
    a legitimate coin from the Top 100, which nobody would notice."""
    fails = []
    import coin_screen as cs

    eth_only = {"ethereum": "0xabc0000000000000000000000000000000000001"}
    _check(cs._ethereum_only_contract(eth_only) == eth_only["ethereum"], fails,
           "coin screen: an Ethereum-only token no longer qualifies for the on-chain check")
    for label, platforms in (
            ("multi-chain", {"ethereum": "0xabc", "solana": "So111"}),
            ("non-Ethereum only", {"solana": "So111"}),
            ("no platform at all (a native coin like BTC)", {}),
            ("a blank address", {"ethereum": ""})):
        _check(cs._ethereum_only_contract(platforms) is None, fails,
               f"coin screen: {label} would be checked against an Ethereum supply ceiling, "
               f"which is not its ceiling; that drops legitimate coins")

    # the arithmetic of the verdict itself
    over = 1_000 > 500 * cs.ONCHAIN_MARGIN      # claims twice what exists
    under = 400 > 500 * cs.ONCHAIN_MARGIN       # circulating below total, the normal case
    edge = 505 > 500 * cs.ONCHAIN_MARGIN        # inside the read-timing margin
    _check(over and not under and not edge, fails,
           "coin screen: the on-chain margin no longer separates fabricated supply from "
           "ordinary read timing")
    _check(1.0 < cs.ONCHAIN_MARGIN <= 1.10, fails,
           "coin screen: ONCHAIN_MARGIN left its band; it absorbs seconds of read timing "
           "against a hard ceiling, not a supply disagreement")
    _check("onchain" in cs.REASONS, fails,
           "coin screen: the onchain verdict has no reader-facing reason, so the board "
           "would drop a coin without saying why")
    return fails

def _dedupe_guard_canary():
    """The three-in-one-day failure, pinned as fixtures.

    On 2026-07-30 the desk published one Treasury designation three times. same_event() was
    never the problem: it matched all three pairs. These cases lock the four things that were
    wrong downstream, and the one case that must still get through, because a guard that
    holds everything is just a slower way to publish nothing."""
    fails = []
    import autopilot as ap
    import dedupe

    # CHASSIS SYNC. dedupe.py is one file copied into three repositories, so the only thing
    # keeping them honest is this hash plus the shared fixtures below. Editing the guard in
    # one desk and not the others reds every desk that was not updated.
    _sha = __import__("hashlib").sha256(
        open(dedupe.__file__, "rb").read()).hexdigest()[:16]
    _check(_sha == "d4753cc9a2fd90a3", fails,
           f"dedupe: this desk's dedupe.py is {_sha}, the chassis copy is d4753cc9a2fd90a3. "
           f"The guard was changed in one repo and not the others; re-sync all three.")

    # (4) Title Case is not evidence. A headline yields capitalised tokens for ordinary
    # words, so novelty must be read from sentence-cased prose.
    title_sig = dedupe._signature(
        "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of Hormuz Passage")
    _check({"accepting", "insurers", "passage"} <= title_sig, fails,
           "dedupe: this fixture assumed Title Case pollutes _signature and it no longer "
           "does; re-check whether _claim_signature still needs to avoid headlines")
    # The fixture MUST carry a title, or pulling the headline back into the claim signature
    # changes nothing and this assertion tests nothing.
    claim = dedupe._claim_signature(
        {"title": "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of "
                  "Hormuz Passage",
         "key_fact": "HormuzSafe, an Iranian state-linked firm, accepts Bitcoin to collect "
                     "mandatory insurance fees from vessels transiting the Strait of Hormuz."})
    _check(not ({"accepting", "insurers", "passage"} & claim), fails,
           "dedupe: _claim_signature is reading the headline again; a reworded headline will "
           "look like new reporting and the same event will publish twice")

    # (1)(2) A retelling that adds nothing is a rehash, even when the wording differs enough
    # to beat a word-overlap threshold, and even when an older unrelated story also matched.
    pub = {"title": "US Treasury Sanctions Iranian Firms Using Bitcoin for Maritime Extortion",
           "key_fact": "US Treasury sanctioned two Iranian firms accepting Bitcoin to fund "
                       "IRGC operations via a coercive maritime insurance extortion scheme.",
           # Verbatim from the story that actually published at 18:40, not a paraphrase.
           # A shortened body made this fixture pass for the wrong reason on first run:
           # the retelling looked novel only because the excerpt omitted the Strait.
           "body": ["HormuzSafe Marine Services Authority and Persian Gulf Marine Insurance "
                    "Company were designated under Executive Order 13902.",
                    "HormuzSafe advertises itself as offering digital insurance, traffic "
                    "control, security and emergency response to vessels transiting the "
                    "Strait of Hormuz."]}
    retell = {"key_fact": "HormuzSafe, an Iranian state-linked firm, accepts Bitcoin and "
                          "digital assets to collect mandatory insurance fees from vessels "
                          "transiting the Strait of Hormuz, generating revenue for the IRGC."}
    covered = dedupe._covered_signature(pub)
    _check(len(dedupe._claim_signature(retell) - covered - dedupe._OUTLETS)
           < dedupe.NOVELTY_MIN, fails,
           "dedupe: a retelling that adds no new fact scores as novel; this is the shape "
           "that published one Treasury designation three times")

    # the case that MUST still pass: a real development adds a new actor and a new amount
    # Verbatim from the two stories the desk actually published on 2026-07-16. A paraphrase
    # here failed to trip same_event at all, so the follow-up came back "new" and the
    # assertion tested nothing.
    followup = {"key_fact": "The Ostium OLP vault lost approximately $24M USDC via oracle "
                            "manipulation; the exploiter converted stolen stablecoins to "
                            "12,086 ETH total and routed 10,540 ETH through Tornado Cash."}
    origin = {"title": "Ostium Suffers $18 Million Exploit as Oracle Attack Wave Continues "
                       "to Hit DeFi",
              "key_fact": "An attacker drained $18 million in USDC from Ostium's vault by "
                          "submitting oracle reports with future-dated timestamps, exposing "
                          "a critical gap in price-feed validation.",
              "body": ["The attack targeted Ostium's price-feed validation."]}
    _check(len(dedupe._claim_signature(followup) - dedupe._covered_signature(origin)
               - dedupe._OUTLETS) >= dedupe.NOVELTY_MIN, fails,
           "dedupe: a genuine follow-up with a new actor and a new amount is being held as a "
           "rehash; the guard has become a publish-nothing gate")

    # (2) NOVELTY AGAINST ALL PRIOR COVERAGE, exercised end to end against a controlled
    # corpus rather than inspected in source. An earlier version of this check only grepped
    # classify_published for "min(matches" and a revert to the oldest-match rule passed it
    # clean, which is the same weakness that let a canary sit over dead code for two days.
    stale = {"id": "c001", "slug": "iran-strikes",
             "title": "Crypto Little Changed as U.S. Launches Fresh Iran Strikes",
             "date": "2026-07-12",
             "key_fact": "Markets held steady after a reported Strait of Hormuz closure.",
             "body": ["Traders shrugged off the escalation."]}
    first = dict(pub, id="c112", slug="iran-sanctions-first", date="2026-07-30",
                 published_utc="2026-07-30T15:25:01Z")
    corpus = [stale, first]
    verdict, _t, _s = dedupe.classify_published(
        "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of Hormuz Passage",
        retell["key_fact"], corpus=corpus)
    _check(verdict == "rehash", fails,
           f"dedupe: a same-day retelling classified as {verdict!r} with an unrelated older "
           f"story in the corpus; that older story is exactly what made all three Iran "
           f"duplicates look novel on 2026-07-30")

    # and the same corpus must still let a real development through
    verdict2, _t2, _s2 = dedupe.classify_published(
        "Ostium Vault Exploiter Routes 10,540 ETH to Tornado Cash",
        followup["key_fact"], corpus=[dict(origin, id="c900", slug="ostium-origin",
                                           date="2026-07-16",
                                           published_utc="2026-07-16T07:33:18Z")])
    _check(verdict2 == "update", fails,
           f"dedupe: a genuine follow-up classified as {verdict2!r}; the guard has become a "
           f"publish-nothing gate")

    # (3) the guard must judge the shipped title
    _check('article_draft' in inspect.getsource(ap.main)
           and '.get("title")' in inspect.getsource(ap.main), fails,
           "dedupe: main() is judging the editor's headline again rather than the writer's "
           "title; the string checked must be the string shipped")
    return fails

def _boundary_canary():
    """The inverted-advisory failure, pinned as fixtures.

    On 2026-07-30 the desk drafted a hardware-wallet firmware advisory twice and the approver
    rejected it twice on accuracy, correctly: the second draft implied users on the PATCHED
    version were the ones at risk. These cases lock the four properties that stop that draft
    ever existing, plus the one case that must still publish, because a gate that holds every
    security story is just a slower way to leave readers uninformed."""
    fails = []
    import boundary as bnd
    import publish as pubmod
    import researcher
    import writer

    # CHASSIS SYNC, same discipline as dedupe.py: one file, three repositories, one hash.
    _sha = __import__("hashlib").sha256(open(bnd.__file__, "rb").read()).hexdigest()[:16]
    _check(_sha == "0cf27e0f447f1031", fails,
           f"boundary: this desk's boundary.py is {_sha}, the chassis copy is 0cf27e0f447f1031. "
           f"The module was changed in one repo and not the others; re-sync all three.")

    # (1) CLASSIFICATION. A firmware advisory with a version in it is boundary-class; a
    # security story with no boundary in it is not, or every story becomes a held story.
    _check(bnd.is_boundary_story(
        "Coldcard Mk4 firmware vulnerability lets an attacker extract the seed",
        "Coinkite patched the flaw in firmware 4.0.1."), fails,
        "boundary: a firmware advisory naming a version is not classified boundary-class; "
        "the fields that stop an inverted range would never be required")
    # Both negatives fire exactly ONE half of the classifier. That is deliberate: an earlier
    # pair fired neither, so relaxing the rule from AND to OR left them passing and the
    # sabotage run went clean. A negative fixture that no plausible break can flip is not a
    # test, and this is the second time on this desk a canary has passed over nothing.
    _check(not bnd.is_boundary_story(
        "Bitcoin falls below $60,000 before the Fed decision",
        "BTC traded down on the day, after a run above $62,000 earlier in the week."), fails,
        "boundary: an ordinary market story is classified boundary-class on its numbers "
        "alone; the gate will hold stories that have no boundary to confirm")
    _check(not bnd.is_boundary_story(
        "Coinkite discloses a firmware flaw and says a patch is coming",
        "The company said an advisory would follow and gave no further detail."), fails,
        "boundary: a security story with no version, date or threshold anywhere in it is "
        "classified boundary-class, so it can never satisfy fields that do not exist for it")

    # (2) VERBATIM, NOT PARAPHRASE. This is the whole point: "4.0.1 and earlier" tidied into
    # "up to 4.0.1" means the same thing to a reader and means the check has stopped running.
    advisory = [{"url": "https://blog.coinkite.com/advisory-2026-07",
                 "source_text": "Affected: Mk4 firmware 4.0.0 and earlier. Fixed in firmware "
                                "4.0.1. Users should update to 4.0.1 immediately."}]
    good = {"affected": "Mk4 firmware 4.0.0 and earlier", "fixed": "firmware 4.0.1",
            "user_action": "update to 4.0.1 immediately",
            "advisory_url": "https://blog.coinkite.com/advisory-2026-07"}
    ok, why = bnd.check_against_sources(good, advisory)
    _check(ok, fails, f"boundary: a block quoted verbatim from the advisory failed the "
                      f"check ({why}); the gate would hold every advisory story")

    tidied = dict(good, affected="versions up to 4.0.0")
    ok2, _ = bnd.check_against_sources(tidied, advisory)
    _check(not ok2, fails,
           "boundary: a paraphrased affected-versions string passed as verbatim; paraphrase "
           "is the exact step that inverted the Coldcard draft")

    inverted = dict(good, affected="Mk4 firmware 4.0.1 and later")
    ok3, _ = bnd.check_against_sources(inverted, advisory)
    _check(not ok3, fails,
           "boundary: an INVERTED range passed the advisory check; this is the published "
           "claim the whole change exists to prevent")

    # (3) SECOND-HAND IS NOT PRIMARY. A field quoted out of a news write-up of the advisory
    # is where the direction flips, so only text fetched from the advisory URL counts.
    ok4, why4 = bnd.check_against_sources(
        good, [{"url": "https://example.test/news-story",
                "source_text": "Affected: Mk4 firmware 4.0.0 and earlier. Fixed in firmware "
                               "4.0.1."}])
    _check(not ok4 and any("primary" in r for r in why4), fails,
           "boundary: the check accepted a news write-up as the advisory; second-hand "
           "sourcing is where a version range gets restated and inverted")

    for f in ("affected", "fixed", "user_action", "advisory_url"):
        ok5, _ = bnd.check_against_sources({k: v for k, v in good.items() if k != f}, advisory)
        _check(not ok5, fails, f"boundary: a block missing {f!r} passed as complete")

    # (4) THE WRITER GETS NO SAY. writer.py COPIES the block; if it ever starts trusting the
    # model's rendering of it, a paraphrase is back in the pipeline.
    art = {"title": "T", "body": "b", "boundary": {"affected": "WHATEVER THE MODEL SAID",
                                                   "fixed": "x", "user_action": "y",
                                                   "advisory_url": "z"}}
    writer._carry_boundary(art, {"brief": {"boundary": good, "boundary_required": True,
                                           "boundary_ok": True}})
    _check(art.get("boundary") == good, fails,
           "boundary: writer._carry_boundary did not overwrite the model's block with the "
           "brief's; the writer is restating the version range again")
    _check("_carry_boundary" in inspect.getsource(writer.validate), fails,
           "boundary: writer.validate no longer calls _carry_boundary, so nothing copies the "
           "fields and the draft carries whatever the model wrote")

    # (5) THE GATE IS FAIL-CLOSED AND READS THE DRAFT. An unconfirmed boundary holds, with no
    # retry path: retrying cannot make a vendor advisory fetchable.
    # Built fresh, NOT from art: _carry_boundary stamped boundary_ok=True onto art above, so
    # reusing it made the never-checked case inherit that True and pass for the wrong reason.
    # The absent-key case is the one that matters most here, so it has to be genuinely absent.
    base = {"title": "T", "body": "b", "boundary": dict(good)}
    _check(pubmod.boundary_block({"article_draft": dict(base, boundary_required=True,
                                                        boundary_ok=True)}) == "", fails,
           "boundary: publish is holding a story whose boundary IS confirmed")
    for bad in ({"boundary_required": True, "boundary_ok": False},
                {"boundary_required": True, "boundary_ok": None},
                {"boundary_required": True}):
        _check(pubmod.boundary_block({"article_draft": dict(base, **bad)}) != "", fails,
               f"boundary: publish let a boundary-class story through with {bad}; an "
               f"unconfirmed who-is-affected claim reached a reader")
    _check(pubmod.boundary_block({"article_draft": {"boundary_required": True,
                                                    "boundary_ok": True}}) != "", fails,
           "boundary: publish let through a story marked confirmed that carries no block to "
           "render; the panel would be absent and the prose says nothing about it, by design")
    _check(pubmod.boundary_block({"article_draft": {"title": "ordinary story"}}) == "", fails,
           "boundary: publish is holding an ordinary story that has no boundary at all")
    _check("boundary_block(" in inspect.getsource(pubmod.run), fails,
           "boundary: publish.run no longer calls boundary_block; the gate is unreachable "
           "and this canary is testing dead code")

    # (6) THE RESEARCHER STAMPS BOTH DIRECTIONS. A missing key and a negative answer look
    # identical downstream, and only one of them means the check ran.
    brief = {"id": "c011", "core_claim": "Coinkite patched a firmware flaw in 4.0.1."}
    researcher._stamp_boundary(brief, {"headline": "Coldcard firmware vulnerability lets an "
                                                   "attacker extract the seed",
                                       "source_texts": advisory})
    _check(brief.get("boundary_required") is True and brief.get("boundary_ok") is False, fails,
           f"boundary: a boundary-class brief with no block was stamped "
           f"required={brief.get('boundary_required')!r} ok={brief.get('boundary_ok')!r}; "
           f"the publish gate reads these and would let it through")
    plain = {"id": "c020", "core_claim": "Bitcoin traded near flat."}
    researcher._stamp_boundary(plain, {"headline": "Bitcoin holds steady", "source_texts": []})
    _check(plain.get("boundary_required") is False, fails,
           "boundary: an ordinary story was stamped boundary_required; every story would "
           "need a vendor advisory to publish")
    _check("_stamp_boundary" in inspect.getsource(researcher.validate), fails,
           "boundary: researcher.validate no longer calls _stamp_boundary, so no brief is "
           "ever classified and the gate never fires")

    # (7) RENDERING. Nothing is composed into a sentence, and an incomplete block renders
    # nothing at all rather than a panel with a blank row where the fix version goes.
    _check([lab for lab, _ in bnd.rows(good)] == ["Affected", "Fixed in", "What to do",
                                                  "Advisory"], fails,
           "boundary: the rendered panel changed shape; a reader scanning for the fix version "
           "should find it in the same place on every advisory story")
    _check(bnd.rows({"affected": "x"}) == [], fails,
           "boundary: an incomplete block still renders; a panel missing the fixed version "
           "answers the question wrong by omission")
    return fails


def _preview_suppression_canary():
    """A preview must never suppress coverage of the thing it previewed.

    This is the bug that cost the desk the FOMC decision on 2026-07-29. The Week Ahead
    published two days earlier listed "Wednesday, July 29: FOMC rate decision", and
    already_published() scanned it like any other story. When the Fed actually decided, the
    real story was ranked #1, VERIFIED against federalreserve.gov and APPROVED, then held
    as already-published. Every event the Week Ahead flags was pre-suppressed for the next
    five days, so the better the preview, the worse the blackout.

    The two assertions have to hold together: previews and editions must not suppress, and
    real coverage still must. Fixing the first by weakening the second would just trade a
    missed story for a duplicate."""
    fails = []
    import autopilot as ap

    # REACHABILITY FIRST. The previous version of this canary tested is_coverage() and
    # already_published() directly, and BOTH were dead: nothing in production called them, so
    # the FOMC preview fix passed its canary for two days without ever executing. Assert the
    # filter runs inside the gate that actually decides, and that the gate is the one
    # main() calls.
    import inspect
    import dedupe
    _gate_src = inspect.getsource(dedupe.classify_published)
    _check("is_coverage(" in _gate_src, fails,
           "preview suppression: classify_published no longer filters with is_coverage, so "
           "previews and editions can suppress or anchor a real story again")
    _check("classify_published(" in inspect.getsource(ap.main), fails,
           "preview suppression: main() no longer calls classify_published; the guard being "
           "asserted here is not the guard that runs")

    for label, doc in (
            ("a Week Ahead preview (by id)", {"id": "week-ahead-2026-07-27"}),
            ("a Week Ahead preview (by category)",
             {"id": "x", "category": "Week Ahead"}),
            ("a daily edition", {"id": "wrap-am-2026-07-30"})):
        _check(not ap.is_coverage(doc), fails,
               f"preview suppression: {label} counts as coverage and can suppress a "
               f"real story about the same event")
    _check(ap.is_coverage({"id": "c150", "category": "policy"}), fails,
           "preview suppression: a normal story stopped counting as coverage, which "
           "disables duplicate suppression entirely")

    # the fingerprint itself must still see the two as the same event; the fix is the
    # exclusion, not a weaker matcher
    # Verbatim from the 2026-07-27 Week Ahead and the story it suppressed. A paraphrase
    # here does NOT match, which this canary caught on its first run: shortened, the pair
    # fails same_event and the whole check would have passed for the wrong reason.
    _check(ap.same_event(
        "Federal Reserve issues FOMC statement",
        "The Federal Open Market Committee held rates steady in a 9-3 vote.",
        "The Week Ahead: FOMC rate decision; Coinbase second-quarter results; "
        "Strategy second-quarter results",
        "Wednesday, July 29: FOMC rate decision. The Federal Open Market Committee meets "
        "Tuesday and Wednesday; the rate decision lands Wednesday at 2:00 p.m. Eastern "
        "with a press conference at 2:30."), fails,
        "preview suppression: same_event no longer matches the preview to the event, so "
        "this canary would pass for the wrong reason")

    # The post-approval hold annotation. Formatting only, but the three call sites feed it
    # and a silent regression here re-hides exactly what the FOMC miss needed surfaced.
    notes = ap.held_after_approval_notes([
        {"headline": "Federal Reserve issues FOMC statement",
         "gate": "near-duplicate of a published story",
         "matched": "The Week Ahead: FOMC rate decision"},
        {"headline": "X", "gate": "figure conflicts with a published story", "matched": ""}])
    _check(len(notes) == 2 and "VERIFIED and APPROVED, then held" in notes[0]
           and "The Week Ahead" in notes[0], fails,
           "held-after-approval: the annotation stopped naming the story or the gate")
    _check(ap.held_after_approval_notes([]) == [] and ap.held_after_approval_notes(None) == [],
           fails, "held-after-approval: an empty run no longer annotates nothing")
    return fails


def _front_page_canary():
    """Two front-page defects found in the 2026-07-31 review, pinned so they cannot return.

    Both were the same kind of bug: a rule that looked like it governed something and did
    not. Neither failed a build, neither showed up in a link check, and both were visible to
    any reader who opened the homepage."""
    fails = []
    import datetime as _d
    import site_build as sb

    # (1) THE BOTTOM LINE HAD NO STALENESS RULE AT ALL. On 2026-07-31 the hero still carried
    # the July 28 Evening Brief, telling readers to watch an FOMC decision that had happened
    # two days before the build.
    def _it(slug, wrap, hours_old, bl=None):
        when = (_d.datetime(2026, 7, 31, 12, tzinfo=_d.timezone.utc)
                - _d.timedelta(hours=hours_old))
        out = {"slug": slug, "id": ("wrap-" + slug if wrap else "c1"), "kind": "brief",
               "title": "The Evening Brief: the day in crypto",
               "date": when.strftime("%Y-%m-%d"),
               "published_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if bl:
            out["bottom_line"] = bl
        return out

    for label, items, want in (
        ("a fresh edition", [_it("w", 1, 0, "read")], True),
        ("an edition 3h old with a story since", [_it("s", 0, 0), _it("w", 1, 3, "read")], True),
        # the exact 2026-07-31 shape: an old edition with newer reporting on the site
        ("a 25h-old edition with a story since", [_it("s", 0, 0), _it("w", 1, 25, "read")], False),
        # the desk going quiet is NOT staleness: nothing newer exists to contradict the read
        ("a 72h-old edition with nothing since", [_it("w", 1, 72, "read")], True),
    ):
        got = sb.current_bottom_line(items) is not None
        _check(got == want, fails,
               f"front page: {label} is {'shown' if got else 'retired'} and should be "
               f"{'shown' if want else 'retired'}; the Bottom Line staleness rule changed")
    _check("current_bottom_line(" in inspect.getsource(sb.render_home)
           and "current_bottom_line(" in inspect.getsource(sb.bottom_line_card), fails,
           "front page: a Bottom Line surface stopped going through current_bottom_line and "
           "is taking wraps[0] unconditionally again, which is how the July 28 brief held the "
           "hero on a July 31 build")

    # (2) TAG COLLAPSE. "regulation" was declared first with the broadest pattern in the file
    # and _hero_tag shows tags[0], so 111 of 156 published stories rendered "regulation".
    _check(sb.tags_for({"title": "Company reports record corporate treasury operations",
                        "dek": "", "key_fact": ""}) != ["regulation"], fails,
           "front page: 'regulation' matches corporate treasury again; that one word is much "
           "of how the tag reached 71% of the site")
    litig = sb.tags_for({"title": "Judge dismisses class action lawsuit against the exchange",
                         "dek": "", "key_fact": ""})
    # ORDER IS THE MECHANISM, so it needs a fixture that can see it. The litigation case
    # below cannot: "regulation" no longer matches a lawsuit at all, so moving it back to the
    # top of TAG_RULES left that assertion green and the sabotage run went clean. This story
    # matches legal AND regulation AND exchanges, so only the ordering decides what shows.
    both = sb.tags_for({"title": "SEC sues Coinbase over its unregistered exchange",
                        "dek": "", "key_fact": ""})
    _check(both and both[0] == "legal", fails,
           f"front page: a story matching legal, regulation and exchanges displays "
           f"{(both or [None])[0]!r}; TAG_RULES is ordered most-specific-first and _hero_tag "
           f"shows tags[0], so that ordering is the entire mechanism")
    _check(litig and litig[0] == "legal", fails,
           f"front page: a litigation story tags {litig} rather than leading with 'legal'; "
           f"the legal bucket exists because litigation is not rulemaking")
    # A tag claims what the story IS about, so it never reads the body: a 600-word body
    # mentions enough to match most of the rules in the list.
    _check(not sb.tags_for({"title": "Quiet day on the desk", "dek": "", "key_fact": "",
                            "body": ["The SEC, the CFTC and Congress were all mentioned here, "
                                     "alongside an exploit, a stablecoin and an ETF."]}), fails,
           "front page: tags_for is reading the body again; that is how one story came to "
           "match nearly every rule in the list")
    # ...and the live corpus must stay spread. Deliberately loose: this fires on collapse,
    # not on a news cycle that happens to run heavy on one topic for a week.
    try:
        items = [i for i in sb.load_content() if not i.get("example")]
    except Exception:
        items = []
    if len(items) >= 40:
        lead = {}
        for i in items:
            t = sb.tags_for(i)
            if t:
                lead[t[0]] = lead.get(t[0], 0) + 1
        top, n = max(lead.items(), key=lambda kv: kv[1]) if lead else ("", 0)
        _check(n / len(items) <= 0.40, fails,
               f"front page: {n/len(items):.0%} of published stories display {top!r}; the "
               f"taxonomy has collapsed to one chip again (it was 71% 'regulation')")
        untagged = sum(1 for i in items if not sb.tags_for(i))
        _check(untagged / len(items) <= 0.15, fails,
               f"front page: {untagged}/{len(items)} published stories carry no tag at all; "
               f"narrowing the rules has left a hole rather than a taxonomy")
    return fails


def _merge_state_canary():
    """Lock the resolution rules for the files two overlapping publishes always collide on.

    The brief's retry rebases when main moves mid-run. site/content/ is additive and never
    conflicts, but editorial-log.json, regwatch.json and chartmaster.json are rewritten by
    every run, so overlapping runs always conflict there and the run died. These assertions
    pin what each merge must preserve, because getting editorial-log wrong silently deletes
    another run's editorial record and nothing would notice."""
    fails = []
    import merge_state as ms

    up = [{"date": "2026-07-29", "approved": 3, "rejected": [{"id": "other"}]}]
    mine = [{"date": "2026-07-29", "approved": 5, "rejected": [{"id": "mine"}]}]
    got = ms.merge_editorial_log(up, mine)
    ids = [r["id"] for e in got for r in e.get("rejected", [])]
    _check("other" in ids and "mine" in ids, fails,
           "merge_state: editorial-log merge dropped a run's record")
    _check(ms.merge_editorial_log(up, up) == up, fails,
           "merge_state: editorial-log merge duplicated an identical record")

    up_r = {"US :: A": {"dates": ["Jul 29"], "first_seen": "2026-07-01",
                        "last_seen": "2026-07-29"}}
    my_r = {"US :: A": {"dates": ["Jul 15"], "first_seen": "2026-07-01",
                        "last_seen": "2026-07-15"},
            "UK :: B": {"dates": ["Jul 28"], "first_seen": "2026-07-28",
                        "last_seen": "2026-07-28"}}
    got_r = ms.merge_regwatch(up_r, my_r)
    _check("UK :: B" in got_r, fails, "merge_state: regwatch merge dropped a measure")
    _check(got_r["US :: A"]["last_seen"] == "2026-07-29", fails,
           "merge_state: regwatch merge kept the older sighting")
    _check(set(got_r["US :: A"]["dates"]) == {"Jul 29", "Jul 15"}, fails,
           "merge_state: regwatch merge lost sighting dates")

    # snapshot, not a record: later date wins, tie goes to upstream (see merge_state)
    _check(ms.merge_chartmaster({"date": "2026-07-29", "headline": "up"},
                                {"date": "2026-07-29", "headline": "mine"})["headline"] == "up",
           fails, "merge_state: chartmaster tie did not go to upstream")
    _check(ms.merge_chartmaster({"date": "2026-07-28", "headline": "up"},
                                {"date": "2026-07-29", "headline": "mine"})["headline"] == "mine",
           fails, "merge_state: chartmaster ignored the later date")

    _check(set(ms.KNOWN) == {"editorial-log.json", "regwatch.json",
                             "site/data/chartmaster.json"}, fails,
           "merge_state: the auto-resolve allowlist changed; anything added here can "
           "silently overwrite real work during a rebase")
    return fails


def _consistency_gate_canary():
    """Lock the window/date semantics of the cross-surface gate, offline.

    This exists because the gate blocked four production runs in three days, and every
    one of them was the same shape: two surfaces stating something TRUE at two different
    windows, which an unscoped metric could not tell apart from a contradiction. Three
    metrics were scoped one at a time, each after it had already cost a publish. These
    cases pin the behaviour so the fourth is not discovered the same way.

    Every metric whose number is reported at more than one window must be scoped; the
    audit assertion below fails if a new unscoped one is ever added."""
    fails = []
    import datetime as _dt
    import consistency_gate as cg

    for name, m in cg.METRICS.items():
        _check(m.get("scoped"), fails,
               f"consistency gate: metric '{name}' is unscoped; two true claims at "
               f"different windows would read as a contradiction and block a publish")

    def blocks(surf):
        return bool(cg.conflicts(surf))

    now = _dt.datetime.now(_dt.timezone.utc)
    today = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    older = (now - _dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # true at different windows: must NOT block
    for label, a, b in (
            ("btc day vs week", "bitcoin fell today", "bitcoin rose over the week"),
            ("dominance day vs month", "dominance fell in the last 24 hours",
             "dominance climbed over 30 days"),
            ("whale 2d vs 24h", "whales net off exchanges over the last 2 days",
             "whale flows onto exchanges over the last 24 hours"),
            ("etf week vs session", "etfs posted a weekly inflow",
             "etfs saw outflows in the latest session")):
        _check(not blocks([("story:a", a, None), ("chart-master", b, None)]), fails,
               f"consistency gate: false positive on {label} (both can be true)")

    # genuine contradictions: must block
    for label, a, b in (
            ("btc same day", "bitcoin rose today", "bitcoin fell today"),
            ("dominance same week", "dominance rose this week", "dominance fell this week"),
            ("btc unscoped", "bitcoin rallied", "bitcoin tumbled"),
            ("btc unscoped vs scoped", "bitcoin rallied", "bitcoin fell today"),
            ("etf unscoped vs week", "etf outflows persist", "etfs posted a weekly inflow")):
        _check(blocks([("story:a", a, None), ("chart-master", b, None)]), fails,
               f"consistency gate: missed a real contradiction on {label}")

    # a claim frozen on an earlier day is history, not a contradiction of a live board;
    # a same-day one still collides
    _check(not blocks([("story:a", "bitcoin rose today", older),
                       ("chart-master", "bitcoin fell today", None)]), fails,
           "consistency gate: stale story still colliding with a live board (deadlock)")
    _check(blocks([("story:a", "bitcoin rose today", today),
                   ("chart-master", "bitcoin fell today", None)]), fails,
           "consistency gate: same-day contradiction with a live board was not caught")
    return fails


def _window_belt_canary():
    """Lock the window belts, offline.

    WHY. The consistency gate is the LAST step before the publish and it has no retry, so
    a single loose sentence in the Chart Master or the edition discards a whole run of
    verified stories. The belts exist so that failure is caught earlier, inside the retry
    ladder, where the model gets another attempt and the stories still ship. ETF flows got
    a belt after it cost a publish; whale flows had the identical exposure, no belt, and
    cost run 30577704932 the same way on 2026-07-30.

    These cases pin the two properties that make a belt worth having: it fires on the
    phrasing the gate would have blocked, and it stays silent on phrasing the gate would
    have passed. A belt that fires on harmless prose burns the retry ladder and ends in
    the same place, with the previous read standing and nothing gained."""
    fails = []
    import chartmaster as cm

    day = {"direction": "onto exchanges", "window_hours": 24}
    multi = {"direction": "off exchanges", "window_hours": 48}

    # fires: exactly the shapes the gate treats as a collision
    for label, board, text in (
            ("unscoped contradiction (the 2026-07-30 failure)", day,
             "whales continued moving coins off exchanges into cold storage"),
            ("same-window contradiction", day,
             "over the last 24 hours whales moved off exchanges"),
            ("multiday board, multiday contradiction", multi,
             "over the last 2 days whales moved onto exchanges")):
        _check(bool(cm.whale_flow_problems(text, board)), fails,
               f"whale window belt: missed {label}")

    # silent: the gate would pass these, so the belt must not spend a retry on them
    for label, board, text in (
            ("agreement, unscoped", day,
             "whales pushed coins onto exchanges, adding sell pressure"),
            ("agreement, scoped", day,
             "in the last 24 hours whales moved onto exchanges"),
            ("a different window, both true at once", day,
             "whales have moved off exchanges over the last 7 days"),
            ("dual-grain phrasing naming both directions", day,
             "whales moved onto exchanges in the last 24 hours even as the 7 day trend "
             "stayed off exchanges into self-custody"),
            ("no whale claim", day, "bitcoin held its range and etf flows stayed positive"),
            ("day-scoped claim against a multiday board", multi,
             "in the last 24 hours whales moved onto exchanges")):
        _check(not cm.whale_flow_problems(text, board), fails,
               f"whale window belt: false positive on {label}")

    # no board direction means nothing to check against, never a blocked publish
    _check(cm.whale_flow_problems("whales moved off exchanges", {}) == [], fails,
           "whale window belt: fired with no board direction to compare against")

    # --- price belt: the third metric, added by audit rather than after a lost run ---
    down = [{"symbol": "BTC", "chg_24h_pct": -0.34, "chg_7d_pct": -1.59, "chg_30d_pct": -2.97}]
    mixed = [{"symbol": "BTC", "chg_24h_pct": 1.2, "chg_7d_pct": -3.0, "chg_30d_pct": -5.0}]
    for label, assets, text in (
            ("a day claim against a down day", down, "bitcoin rallied today"),
            ("a week claim against a down week", mixed, "bitcoin gained over the week"),
            ("an unscoped claim against an all-down tape", down,
             "bitcoin climbed as buyers stepped in"),
            ("an unscoped claim while the windows disagree", mixed, "bitcoin rose")):
        _check(bool(cm.price_problems(text, assets)), fails,
               f"price window belt: missed {label}")
    for label, assets, text in (
            ("an unscoped claim agreeing with every window", down,
             "bitcoin slid as sellers pressed"),
            ("a correct day claim", down, "bitcoin fell today"),
            ("dual-grain phrasing naming both", mixed,
             "bitcoin rose today even as it fell over the week"),
            ("no bitcoin claim", down, "ether led the majors higher")):
        _check(not cm.price_problems(text, assets), fails,
               f"price window belt: false positive on {label}")
    _check(cm.price_problems("bitcoin rallied today", []) == [], fails,
           "price window belt: fired with no asset numbers to compare against")
    # a window with no number must not be judged; silence beats a guess in a publish gate
    _check(not cm.price_problems("bitcoin gained over the week",
                                 [{"symbol": "BTC", "chg_24h_pct": -1.0}]), fails,
           "price window belt: judged a week claim with no week number")

    # --- THE INVARIANT, and the reason this canary exists ---
    # Every metric the consistency gate can block a publish on must be belted upstream, or
    # be listed as a deliberate exemption with a reason. The gate is the last step before
    # the push and has no retry, so an unbelted metric is a live run waiting to be thrown
    # away: that is exactly how ETF flows, then whale flows, each cost a publish. Adding a
    # metric to the gate without a belt now fails here instead of in production.
    import consistency_gate as cg
    BELTED = {"spot ETF flows": cm.etf_flow_problems,
              "whale exchange flows": cm.whale_flow_problems,
              "bitcoin price": cm.price_problems}
    for metric in cg.METRICS:
        _check(metric in BELTED or metric in cm.UNBELTED_METRICS, fails,
               f"window belt: the gate can block on '{metric}' and nothing belts it "
               f"upstream; add a belt or an explicit UNBELTED_METRICS reason")
    for metric in cm.UNBELTED_METRICS:
        _check(metric in cg.METRICS, fails,
               f"window belt: '{metric}' is exempted but the gate no longer checks it; "
               f"drop the stale exemption")

    # both surfaces that co-render must share the belts, or the unbelted one reintroduces
    # the failure. wrap.py calls into chartmaster for exactly this reason.
    import inspect
    import wrap
    src = inspect.getsource(wrap)
    for fn in ("etf_flow_problems", "whale_flow_problems", "price_problems"):
        _check(fn in src, fails,
               f"window belt: the edition no longer calls {fn}; it is a gate surface too")
    return fails

def _whale_flow_canary():
    """Lock the follow-the-money classification: stablecoins are scored separately from the
    volatile sell-pressure/accumulation signal, and direction follows net sign."""
    fails = []
    import whale_flows
    whale_sample = os.path.join(HERE, "fixtures", "whale_sample.json")
    txns = json.load(open(whale_sample, encoding="utf-8")).get("transactions", [])
    r = whale_flows.analyze(txns, 24)
    # exchange->exchange and wallet->wallet are excluded; 10 of the 12 sample txns count
    _check(r["txn_count"] == 10, fails, f"whale canary: expected 10 exchange-relevant txns, got {r['txn_count']}")
    _check(r["volatile"]["net_usd"] == 35000000, fails,
           f"whale canary: volatile net expected 35000000, got {r['volatile']['net_usd']}")
    _check(r["volatile"]["direction"] == "off exchanges", fails,
           f"whale canary: direction expected 'off exchanges', got {r['volatile']['direction']}")
    _check(r["stablecoins"]["net_buying_power_usd"] == 200000000, fails,
           f"whale canary: stablecoin buying power expected 200000000, got {r['stablecoins']['net_buying_power_usd']}")
    btc = next((a for a in r["by_asset"] if a["symbol"] == "BTC"), None)
    _check(btc and btc["net_usd"] < 0, fails, "whale canary: BTC should be net onto exchanges (negative)")
    _check(all(a["symbol"] not in whale_flows.STABLES for a in r["by_asset"]), fails,
           "whale canary: a stablecoin leaked into the volatile by_asset chart")
    return fails


def _replay_e2e():
    """Run the whole pipeline in replay mode over the fixture and assert the invariants."""
    fails = []
    os.environ["CRYPTO_LLM_MODE"] = "replay"
    cfg = common.load_config()
    client = llmlib.Client(cfg, mode="replay")
    import aggregate, editor, verifier, researcher, writer, approver, digest
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

        # Researcher: every draftable story gets a brief with a measured source_chars, and
        # REJECT stories are never briefed (no tokens spent on the dead).
        re_ = researcher.run(client=client)
        briefed = {b["id"] for b in re_["briefs"]}
        draftable = {v["id"] for v in ve["verdicts"] if v["verdict"] != "REJECT"}
        _check(briefed == draftable, fails,
               f"replay: researcher briefed {sorted(briefed)}, expected {sorted(draftable)}")
        _check(all("source_chars" in b for b in re_["briefs"]), fails,
               "replay: a brief is missing its measured source_chars")

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

        # Approver: one categorized decision per draft; an unjudged draft would REJECT
        # (fail-closed coverage is exercised by the validate path itself).
        ap = approver.run(client=client)
        judged = {a["id"] for a in ap["approvals"]}
        _check(judged == drafted, fails,
               f"replay: approver judged {sorted(judged)}, expected {sorted(drafted)}")
        _check(all(a.get("category") in approver.CATEGORIES
                   for a in ap["approvals"] if a["decision"] == "REJECT"), fails,
               "replay: an approver REJECT is missing its category")

        # Depth gate (deterministic): short body + rich sources holds; short body + thin
        # sources passes (honest brevity); long body always passes.
        import autopilot
        _check(autopilot.depth_gate_holds(40, 5000) is True, fails,
               "depth gate: 40 words from 5000 chars of source material was NOT held")
        _check(autopilot.depth_gate_holds(40, 0) is False, fails,
               "depth gate: honest-thin story (40 words, no sources) was wrongly held")
        _check(autopilot.depth_gate_holds(450, 5000) is False, fails,
               "depth gate: full-length story was wrongly held")

        # BREAKING two-source gate (deterministic, fail-closed): a single-source breaking
        # story HOLDS unless its headline carries the unconfirmed label; two independent
        # sources publish; duplicate source names do not count as independence.
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk"]) is True, fails,
               "breaking gate: single-source story published as fact was NOT held")
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk", "The Block"]) is False, fails,
               "breaking gate: two-source story was wrongly held")
        _check(autopilot.breaking_two_source_holds(
                   "Unconfirmed: Exchange X may have halted withdrawals", ["CoinDesk"]) is False,
               fails, "breaking gate: labeled-unconfirmed single-source was wrongly held")
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk", "coindesk", ""]) is True, fails,
               "breaking gate: duplicate source names wrongly counted as independent")

        # EVENT-FINGERPRINT DEDUP (2026-07-22): same-event-different-words duplicates that
        # headline-word overlap misses must be caught; genuinely distinct stories spared.
        _check(autopilot.same_event(
                   "Amazon Japan supplier to pay 2,300 contractors using regulated yen stablecoin", "",
                   "Amazon Japan logistics firm AZ-COM Maruwa to pay 2,300 partners with regulated yen", ""),
               fails, "dedup: same event with different words (Amazon Japan) was NOT caught")
        _check(autopilot.same_event(
                   "Hut 8 and IREN land billions in AI contracts", "",
                   "AI compute stocks bounce as Hut 8, IREN book AI capacity", ""),
               fails, "dedup: Hut 8/IREN same event was NOT caught")
        _check(not autopilot.same_event(
                   "Grayscale Files S-1 for Spot Worldcoin ETF", "",
                   "Movement Labs files for Chapter 11 bankruptcy", ""),
               fails, "dedup: two distinct stories were wrongly merged")
        _check(not autopilot.same_event(
                   "Russia Parliament passes crypto market law with $3,800 cap", "",
                   "UK Parliament launches inquiry into banking restrictions", ""),
               fails, "dedup: two different Parliament stories wrongly merged")

        # Daily edition (wrap): replay dry-run must produce a belts-clean edition item
        # that leads the page (negative rank) and carries the desk's stories as sources.
        import subprocess
        env = dict(os.environ, CRYPTO_LLM_MODE="replay")
        r = subprocess.run([sys.executable, os.path.join(HERE, "wrap.py"),
                            "--dry-run", "--edition", "morning"],
                           capture_output=True, text=True, env=env)
        _check(r.returncode == 0, fails, f"wrap dry-run failed: {(r.stdout + r.stderr)[-200:]}")
        if r.returncode == 0:
            wp = common.read_out("wrap-preview.json")
            _check(wp.get("rank", 0) < 0, fails, "wrap: edition rank must be negative (leads the page)")
            _check(wp.get("human_take") == "", fails, "wrap: human_take must be empty")
            _check("—" not in json.dumps(wp), fails, "wrap: em dash leaked into the edition")
            _check(wp.get("sources"), fails, "wrap: edition must cite the desk's own stories")

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


def _contract_ladder_canary(cfg):
    """The recovery layer (2026-07-15): a contract violation retries on the same model,
    then escalates ONE call to the rescue model, and replay mode never escalates."""
    fails = []

    class StubClient(llmlib.Client):
        def __init__(self, cfg, answers):
            super().__init__(cfg, mode="live")
            self.answers = list(answers)
            self.models_used = []

        def _live_raw(self, stage, model_cfg, system, user):
            self.models_used.append(model_cfg["model"])
            return self.answers.pop(0)

    def need_ranked(o):
        if "ranked" not in o:
            raise llmlib.LLMError("editor output missing 'ranked'")
        return o

    # (a) bad shape then good on rung 2: recovered, no escalation
    c = StubClient(cfg, ['{"id": "c000"}', '{"ranked": [], "rejected": []}'])
    try:
        obj = c.call_json("editor", "sys", "user", validate=need_ranked)
        _check("ranked" in obj and len(c.models_used) == 2, fails,
               f"ladder: retry did not recover (calls={c.models_used})")
        _check(c.models_used[0] == c.models_used[1], fails,
               "ladder: rung 2 must reuse the configured model")
    except llmlib.LLMError as e:
        fails.append(f"ladder: recoverable violation wrongly failed: {e}")

    # (b) two bad answers: rung 3 runs on the rescue model
    c2 = StubClient(cfg, ['nonsense', '{"wrong": 1}', '{"ranked": [], "rejected": []}'])
    try:
        c2.call_json("editor", "sys", "user", validate=need_ranked)
        _check(len(c2.models_used) == 3 and c2.models_used[2] == llmlib.RESCUE_MODEL, fails,
               f"ladder: third rung was not the rescue model (calls={c2.models_used})")
    except llmlib.LLMError as e:
        fails.append(f"ladder: rescue rung wrongly failed: {e}")

    # (c) three bad answers: fails closed
    c3 = StubClient(cfg, ['x', 'y', 'z'])
    try:
        c3.call_json("editor", "sys", "user", validate=need_ranked)
        fails.append("ladder: triple violation did NOT fail closed")
    except llmlib.LLMError:
        pass

    # (d) replay never retries/escalates: a fixture that fails validation fails the canary
    rc = llmlib.Client(cfg, mode="replay")
    try:
        rc.call_json("editor", "sys", "user",
                     validate=lambda o: (_ for _ in ()).throw(llmlib.LLMError("fixture bad")))
        fails.append("ladder: replay validation failure did NOT raise")
    except llmlib.LLMError:
        _check(rc.budget.calls == 1, fails,
               f"ladder: replay made {rc.budget.calls} calls (must be exactly 1, no ladder)")

    # (e) watcher slot recovery: past deadline + missing edition -> that slot; edition
    # present -> quiet; before deadline -> quiet
    import datetime as _dt
    import tempfile
    import watcher
    with tempfile.TemporaryDirectory() as td:
        noon = _dt.datetime(2026, 7, 15, 13, 0, tzinfo=_dt.timezone.utc)
        _check(watcher.missed_slot(noon, td) == "morning-brief", fails,
               "watcher recovery: missed morning slot not detected")
        open(os.path.join(td, "2026-07-15-morning-brief.json"), "w").write("{}")
        _check(watcher.missed_slot(noon, td) is None, fails,
               "watcher recovery: fired despite the edition existing")
        early = _dt.datetime(2026, 7, 15, 11, 0, tzinfo=_dt.timezone.utc)
        _check(watcher.missed_slot(early, td) is None, fails,
               "watcher recovery: fired before the deadline")
        evening = _dt.datetime(2026, 7, 15, 23, 50, tzinfo=_dt.timezone.utc)
        _check(watcher.missed_slot(evening, td) == "evening-brief", fails,
               "watcher recovery: missed evening slot not detected")

    # THE BOTTOM LINE lane gate (owner directive 2026-07-15): the signature element's
    # own guardrail must block directional/predictive language and pass clean synthesis.
    import wrap as wrapmod
    clean = ("The day's theme was regulation outpacing the market: two agencies moved and "
             "the tape barely noticed. The honest read is that positioning stayed calm "
             "while the headlines ran hot. The coming checkpoints are Thursday's committee "
             "vote and the exchange's incident report.")
    _check(wrapmod.bottom_line_lint(clean) == [], fails,
           f"Bottom Line lane: clean synthesis wrongly flagged: {wrapmod.bottom_line_lint(clean)}")
    dirty = "Today's flush sets up for a move higher into the CPI print."
    _check(len(wrapmod.bottom_line_lint(dirty)) >= 1, fails,
           "Bottom Line lane: 'sets up for a move higher' was NOT blocked")
    _check(len(wrapmod.bottom_line_lint("Bitcoin looks poised to rally, brace for volatility.")) >= 2,
           fails, "Bottom Line lane: poised-to/brace-for was NOT blocked")

    # ATTRIBUTED OBSERVATIONS (2026-07-19): the desk reports what a source shows, it does
    # not assert a house opinion. Attributed phrasing passes; unattributed voice is blocked.
    attributed = ("Per CoinDesk's reporting the vote slipped to next week, and the desk's "
                  "Whale Watch board shows $162M moving onto exchanges.")
    _check(wrapmod.unattributed_lint(attributed) == [], fails,
           f"attribution: sourced phrasing wrongly flagged: {wrapmod.unattributed_lint(attributed)}")
    _check(len(wrapmod.unattributed_lint("The honest read is that nobody cares.")) >= 1, fails,
           "attribution: 'the honest read is' was NOT blocked")
    _check(len(wrapmod.unattributed_lint("Make no mistake, the real story is elsewhere.")) >= 2,
           fails, "attribution: 'make no mistake' / 'the real story is' were NOT blocked")

    # JURISDICTION TRACKER: real stated dates parse, prose numbers do not (a tracker that
    # invents a deadline is worse than no tracker).
    import regwatch
    _check(bool(regwatch.DATE_PAT.search("compliance deadline of January 20, 2027")), fails,
           "regwatch: a real stated deadline was NOT parsed")
    _check(not regwatch.DATE_PAT.search("rose by the 20 percent"), fails,
           "regwatch: prose number 'by the 20 percent' was wrongly parsed as a date")
    _check(not regwatch.DATE_PAT.search("due over 90 days"), fails,
           "regwatch: 'over 90 days' was wrongly parsed as a date")
    j, i, dts = regwatch.extract("The GENIUS Act compliance deadline of January 20, 2027 applies.")
    _check("United States" in j and "GENIUS Act" in i and dts, fails,
           f"regwatch: GENIUS Act storyline not filed correctly (j={j} i={i} d={dts})")
    j2, i2, _ = regwatch.extract("A US official commented on the EU's MiCA regime.")
    _check(i2 == ["MiCA"] and "European Union" in j2, fails,
           f"regwatch: MiCA should file under the EU only (j={j2} i={i2})")
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
