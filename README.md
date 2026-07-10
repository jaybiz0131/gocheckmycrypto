# GoCheckMyCrypto: the Crypto Cronkite news desk

An AI-assisted crypto news desk (gocheckmycrypto.com): aggregate many sources, an editor AI
ranks importance and strips shill, an independent verifier AI audits the editor, a writer AI
drafts, a human approves every push, and only then does anything publish on a cadence. Plus
Whale Watch, the follow-the-money on-chain board.

Built on the same architecture as its GoCheckMy sibling's recall pipeline (GoCheckMyPet) and
the Storm NFIP pattern: scheduled ingest, AI processing, verified and gated output. Standard
library only, fail-closed everywhere, self-verifying. Migrated to its own repo with history
preserved (see DEVIATIONS.md D1).

## The one non-negotiable rule

**The AI is the newsroom staff. The human is the editor-in-chief and the on-air voice.**
Nothing publishes as reporting or as a "take" without human sign-off. The automation removes
the grunt work (reading, triage, fact-check, drafting), never the judgment or the voice. An
unsupervised crypto news bot that publishes a false hack or a wrong price is brand-ending and
a liability, so the human gate is load-bearing and cannot be removed to "scale faster".

## The stages

| Stage | Script | What it does | Output (in `out/`) |
|-------|--------|--------------|--------------------|
| 1 Aggregate | `aggregate.py` | Pull RSS (official/primary + major outlets; CryptoPanic if `CRYPTOPANIC_TOKEN` set), normalize, dedupe near-identical stories into clusters, run the deterministic shill pre-pass | `items.json` |
| 2 Editor | `editor.py` | Managing-editor AI ranks the top stories by genuine significance and strips shill, showing its work | `editor.json` |
| 3 Verifier | `verifier.py` | A SEPARATE, adversarial AI live-fetches each cited source and audits the editor: VERIFIED / NEEDS-HUMAN-REVIEW / REJECT, with reasons and editor-divergence | `verifier.json` |
| 4 Writer | `writer.py` | Drafts the surviving stories into a script skeleton + article draft, DRAFT-tagged, neutral on price, not-financial-advice, with an empty human-take slot | `drafts.json` |
| 5 Digest | `digest.py` | Builds the human review queue (Markdown + HTML) and an approval template | `review_queue/<date>.md`, `.html`, `approval_template.json` |
| 6 Publish | `publish.py` | Fail-closed, approval-gated auto-push. Publishes ONLY stories a human approved AND the verifier cleared. Push targets are dry-run adapters until an operator wires a real endpoint | `published/`, `publish_report.json` |

`run.py` orchestrates Stages 1-5 (fail-closed) and **never** publishes. Stage 6 is a separate,
deliberate, human step.

## Running it

```sh
# Full offline wiring test - no API key, no network for the AI stages, no spend:
python3 run.py --mode replay --fixture fixtures/sample_feed.xml

# Live daily brief (needs ANTHROPIC_API_KEY; optional CRYPTOPANIC_TOKEN):
export ANTHROPIC_API_KEY=sk-ant-...
python3 run.py --mode live
#  -> read out/review_queue/<date>.md
#  -> copy approval_template.json to approval.json, set stories you sign off to "approve",
#     add your take, then:
python3 publish.py
```

## Fail-closed posture (STAGE 0 of the blueprint)

- No `ANTHROPIC_API_KEY` -> the LLM call raises, the run reports failed, nothing publishes.
- Per-run token/USD budget cap (`config.json`) -> a call that would exceed it raises first.
- Any stage error -> `run.py` writes `status: failed` and exits non-zero (CI flags a human).
- A story publishes only if: a human set it to `approve`, the verifier said VERIFIED (or
  NEEDS-HUMAN-REVIEW **with** a human take as an override), and the run is `live` (a replay
  test run can never publish). REJECT is never publishable.
- Push targets ship as dry-run adapters; a real send requires an operator to add the endpoint,
  credential, and send implementation deliberately.

## Verify

`verify_pipeline.py` mirrors the GoCheckMyPet recall verifier's two layers:

```sh
python3 verify_pipeline.py canary    # Layer 1: offline HARD GATE (blocks)
python3 verify_pipeline.py sources   # Layer 2: live feed check (notify-only)
```

Layer 1 proves the pipeline is wired, the shill/dedupe belts work, the offline replay runs
end-to-end to a DRAFT-tagged review queue, and every fail-closed gate holds. Layer 2 checks
the configured RSS feeds still resolve. Wired to `.github/workflows/verify-crypto-pipeline.yml`.

## Configuration

- `config.json` - sources and tiers, cadence, top-N, budget cap, per-stage model, publish gates.
- `shill_rules.json` - deterministic shill tells and source reputation (the living tune-list).
- `prompts/` - the editor / verifier / writer system prompts (your editorial judgment, once).

## Cost control

The editor/verifier/writer calls are cheap per run but capped by `config.json -> budget`
(tokens and USD). No `temperature`/`top_p`/`top_k` is sent (rejected by the current model
family); register and determinism are steered by the prompts. Default model is
`claude-opus-4-8`; `claude-sonnet-5` is a cheaper per-run swap.

## The website

The public reader-facing site lives in `site/` and is generated by `site_build.py` into
`site/publish/` (a build artifact, gitignored, reproducible). It has its own editorial
"trusted newsroom" identity: masthead, serif headlines, verdict badges that reuse the
pipeline's vocabulary, a "how we work" trust strip, a Netlify-Forms newsletter signup, and
baked-in not-financial-advice. Pages: home, archive, how-we-work (`method.html`), about,
standards/corrections, per-story article pages, plus 404 and a subscribe thank-you.

```sh
python3 site_build.py            # build site/publish/ from committed content
python3 site_build.py --ingest   # promote approved payloads, then build
```

**Whale Watch (follow the money).** `whale_flows.py` turns Whale Alert's large-transfer feed
into a higher-perspective signal instead of a scrolling list: it classifies each transfer as
moving onto an exchange (potential sell pressure) or off an exchange (accumulation), scores
stablecoins separately as incoming buying power, and aggregates net flow per asset. It writes
`site/data/flows.json`, which the site renders as the "Whale Watch" page (a diverging bar chart
by asset + the biggest onto-exchange moves). Market data, not news, so it does not go through the
human gate, but it is clearly labelled as such. Refresh it with a Whale Alert key:
`python3 whale_flows.py` (or `--fixture fixtures/whale_sample.json` to preview).

Content flow: a story is published only after human approval (`publish.py`). `--ingest`
promotes those approved payloads (`out/published/*.json`) into committed content
(`site/content/*.json`), which the build renders. Committed seed content is an honest launch
editorial plus one clearly-labeled example story that shows the format. Deploy and cadence
steps are in `LAUNCH_CHECKLIST.md`.

## Not financial advice

Crypto Cronkite reports events. It never advises trades. Nothing it produces is financial
advice, and that disclaimer is baked into every draft and every published payload.
