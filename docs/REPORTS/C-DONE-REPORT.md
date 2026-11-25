# C-DONE: the running scorecard

Session opened Tuesday, November 24, 2026; working from Wednesday, November 25, 4:00 AM ET. One Claude Code cloud
session on gocheckmycrypto with gcm-newsroom attached (push access). `docs/RULES.md` body hash
`4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, verified at the opener. No trailer on any commit.
Updated after every merge. A point is green only with its evidence named; "open" means not yet scored.

## Scorecard

| # | Point | State | Evidence or reason |
|---|---|---|---|
| 1 | Fresh | open | Not built yet. Read so far: the Board stamps its oldest core section (`market_pulse.main`, `snapshot.build`), the stale banner's "several times a day" is at `site_build.py` `data_stamp`. |
| 2 | Published | open | Evening Briefs on main: Nov 21, 22, 23, 24 (`site/content/*-evening-brief.json`, ledger rows `edition_published: true`). Seven days need Nov 25 to Dec 1. |
| 3 | Readable in five minutes | open | Jack's Nov 25 4:01 AM ET screenshot read: five findings, listed below. |
| 4 | Clean | open | Crawl not run yet. |
| 5 | Whole | open | Crawl not run yet. |
| 6 | Fast | open | Lighthouse not run yet. |
| 7 | Taught | open | Not read yet. |
| 8 | Quiet | open | Ignore rule: review/ and .github/ added (this merge). Seven-day run sweep in progress. |
| 9 | Found | open | Not read yet. |
| 10 | Beautiful enough | open | The home's lead paragraph placed at 1280 and up (merge 1). |

## Merges, in order

| # | Repo | Merge | Branch tip | Onto | What | Gate |
|---|---|---|---|---|---|---|
| 0 | gcm-newsroom | `b5c0806` | `bab0253` | `2f1f538` | The family newsroom is off: `newsroom.yml` has no schedule, `workflow_dispatch` kept, one line in `docs/HEALTH.md`. Test `test_newsroom_off.py`, red first (2 FAIL), plants: cron put back (red), health line removed (red). | Five Python suites and three Worker tests exit 0, every workflow parsed. Pushed, local equals origin, 0 ahead. |
| 1 | gocheckmycrypto | `96ca8aa` | `d18b90c` | `9e799fa` | Why Bitcoin moved has its own cell in the desktop grid, under the Brief card (it took the first free cell, above the price line, with an empty cell beside it). `system.css` sha256 `1dafda16013688d7a9851fffa2a13e7bc455cfb2aee0c2c8f1c3aa9d4f4affe8` to `2d034b8ab496d2a20d9625ef1ab972686ea135d5523dbf8050f87ada49f1fb87`; the 9.5b pin holds (the block cut out leaves Sprint 9.5's file). | `verify_pipeline.py canary` exit 0 on tree `d4866675` (`C-DONE-logs/lead-place-gate.log`); the merged tree is the same tree. Pushed 4:18 AM ET Nov 25, local equals origin, 0 ahead. |

Tests new in merge 1: `scripts/cdone_test.py` group 1, in the canary as `_cdone_canary`. Red on main: 2 FAIL
(`C-DONE-logs/lead-place-red-on-main.log`). Plants, each restored from a saved copy: the lead's rule removed (red, 2
cases); the lead put in the Brief card's row (red, 1 case); the chart column's span cut to 3 (red, 1 case).

Main's canary before any change, tree `9e799fa`: exit 0, PASS (`C-DONE-logs/canary-main-9e799fa.log`). One warning in
it: `share queue: 2026-10-14-bitcoin failed the publicist's gates: FAIL banned pattern absent [\bhuge\b]`.

## Production reads

| Read at (ET) | Stamp | What was read |
|---|---|---|
| Nov 25, 4:20 AM | `commit 4750aca`, built 2026-11-24T23:18:18+00:00 | `/stamp.txt` only: the merge 1 build had not landed two minutes after the push. Not waited on (U-3). |

## Findings from Jack's screenshot of the home, Nov 25, 4:01 AM ET, 1440 wide (stamp `4750aca`)

1. The lead paragraph sat alone in the top-left cell with an empty cell beside it. Fixed in merge 1.
2. Two Bitcoin prices an inch apart: the paragraph's $59,968 and -2.31% over 24 hours (6:17 PM) against the live
   line's $59,348 and -1.14% (4:01 AM). Open, point 3.
3. The paragraph restates the tiles beside it (ETF, whale, funding, Fear and Greed, movers); HYPE's -5.50% printed
   three times on one screen. Open, points 3 and 4.
4. At 4:01 AM Wednesday the masthead reads Tuesday, and "Next Brief tomorrow at 8:15 AM ET" means today. Open, point 4.
5. "Today: Nothing scheduled." and "Mine: Pins come from any coin page." are empty sections; the All crypto tile reads
   "no 24h figure". Open, points 3 and 4.
6. XRP at six decimals beside Solana at two; middle dots as separators; "Written from Bitcoin's day, ETF flows..."
   on the Brief card. Open, point 4.

## The family newsroom, once

Done in gcm-newsroom, merge `b5c0806` (row 0 above). Only `newsroom.yml` lost its schedule: it is the pipeline that
publishes. Left as they were, named: `research.yml` (Sundays, the topic sweep that feeds the pipeline, still spends its
weekly model call), `audit.yml`, `compliance.yml`, `deskeditor.yml`, `govscout.yml`. The DeskEditor liveness check ran
inside the newsroom run, so it no longer runs on a schedule.

## Jack's

Nothing yet.
