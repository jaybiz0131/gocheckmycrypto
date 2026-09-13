# gocheckmycrypto

Source for the daily crypto news desk and market boards at
[gocheckmycrypto.com](https://gocheckmycrypto.com). Python 3, standard library only, no
third-party runtime dependencies.

How the desk works editorially is documented on the site itself, at
`/method.html` and `/standards.html`. This file is setup and operation.

Contact: desk@gocheckmycrypto.com

## Requirements

- Python 3.11 or newer. No packages to install.
- `ANTHROPIC_API_KEY` in the environment for a live run. Not needed for a replay run.
- `CRYPTOPANIC_TOKEN` optional; one extra intake lane when set.
- Node and Google Chrome only if you want screenshots (`gcm-tools/fullpage-shot.mjs`).

## Running it

```sh
# Offline wiring test. No API key, no network, no spend.
python3 run.py --mode replay --fixture fixtures/sample_feed.xml

# Live run.
export ANTHROPIC_API_KEY=sk-ant-...
python3 run.py --mode live

# Refresh the market boards, then build the static site into site/publish/
python3 market_pulse.py
python3 whale_flows.py
python3 site_build.py

# Ingest finished output into site/content/ and rebuild
python3 site_build.py --ingest
```

`run.py --mode live` writes its output under `out/`, including a queue file at
`out/review_queue/<date>.md`. `publish.py` promotes approved output; it reads
`approval.json`, which you create by copying `approval_template.json` and marking
entries.

## Stages

`run.py` drives these in order. Each writes a JSON artifact under `out/` and the next
stage reads it, so any stage can be inspected or re-run on its own.

| # | Stage | File | Output |
|---|---|---|---|
| 1 | Aggregate | `aggregate.py` | `items.json` |
| 2 | Editor | `editor.py` | `editor.json` |
| 3 | Verifier | `verifier.py` | `verifier.json` |
| 4 | Researcher | `researcher.py` | `research.json` |
| 5 | Writer | `writer.py` | `drafts.json` |
| 6 | Approver | `approver.py` | `approved.json` |
| 7 | Digest | `digest.py` | the queue file |
| 8 | Autopilot | `autopilot.py` | `approval.json` |
| 9 | Publish | `publish.py` | `site/content/*.json` |
| 10 | Wrap | `wrap.py` | the day's edition |

Data collectors run alongside the stages and write into `site/data/`:

| Script | Writes | Notes |
|---|---|---|
| `market_pulse.py` | `pulse.json` | the eight Board readings |
| `whale_flows.py` | `flows.json` | exchange flows, $50M floor |
| `chartmaster.py` | `chartmaster.json` | the daily board read |
| `coin_screen.py` | screen output | scheduled separately |
| `source_health.py` | `source_health.json` | advisory, always exits 0 |

`site_build.py` keeps a dated copy of `pulse.json` under
`site/data/snapshots/pulse-YYYY-MM-DD.json` at the first build after 00:00 UTC. The
Board's since-yesterday deltas are computed against that snapshot. A tile with no prior
value renders no delta, and a section carried forward from an earlier fetch produces no
delta at all.

## Configuration

Everything tunable is in `config.json`: `sources`, `budget`, `cadence`, `publish`,
`dedupe`, `edition`, `narratives`, `models`, `top_n`, `lookback_hours`.

A per-run budget cap lives under `budget`. A call that would exceed it raises before it
is made rather than after.

## Verifying a change

```sh
# Hard gate. Must print PASS before anything is pushed.
python3 verify_pipeline.py canary

# The site must build clean, exit 0, no traceback.
python3 site_build.py

# Advisory checks. These warn; they never fail a run.
python3 source_health.py --check
python3 twin_audit.py --quiet
```

`verify_pipeline.py canary` runs an offline replay end to end and asserts that every
fail-closed gate holds. It is fast and it is the gate: never push on a red canary.

Its deliberate negative tests print inside `::stop-commands::` so they do not post as
annotations on a green run.

## Fail-closed posture

- A stage that cannot complete stops the run rather than passing partial output on.
- A source that cannot be fetched is dropped, not guessed at.
- A gate that fires withholds the affected item, not the whole run.
- A data surface with no reading renders nothing rather than a zero. An empty
  `by_asset` with zeroed totals is an absent reading, not a measured one.
- A Board older than its refresh promise renders a stale stamp and a banner.

## Scheduled workflows

| Workflow | What it runs |
|---|---|
| `crypto-news-brief.yml` | the daily run and the edition slot |
| `watcher.yml` | breaking-news threshold checks |
| `site-refresh.yml` | rebuild on the board cadence |
| `crypto-aging.yml` | archive and aging passes |
| `coin-screen.yml` | the coin screen |
| `depth-backfill.yml` | backfill pass |
| `verify-crypto-pipeline.yml` | the canary on a schedule |
| `janitor.yml` | housekeeping |
| `publicist.yml` | disabled; schedule removed, manual dispatch kept, code kept |

## The site

`site_build.py` renders `site/publish/` from `site/content/` plus `site/data/`.
`site/publish/` is generated and is not committed. Netlify builds from `main`.

Explainer copy for `/learn/<slug>` lives in `learn/*.md`, one file per Board tile, with
front matter naming the tile it binds to. The page's live block reads the same
`pulse.json` the Board reads, so a page and a tile cannot disagree.

House rules the build enforces: no em dashes in desk copy, and a source's own words
inside a quotation are never repunctuated.
