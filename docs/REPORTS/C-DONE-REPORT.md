# C-DONE: the running scorecard

Session opened Tuesday, November 24, 2026; working from Wednesday, November 25, 4:00 AM ET. One Claude Code cloud
session on gocheckmycrypto with gcm-newsroom attached (push access). `docs/RULES.md` body hash
`4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, verified at the opener. No trailer on any commit.
Updated after every merge. A point is green only with its evidence named; "open" means not yet scored. Jack's word of
November 25: continue with all fixes and items; the target is above 8 of 10, pushing toward 9.

## Scorecard

| # | Point | State | Evidence or reason |
|---|---|---|---|
| 1 | Fresh | built, 1 of 3 reads | Merge 3. Production stamp `3d286ab`, read Nov 25 5:06 AM ET: /pulse "As of 4:39 AM ET on Nov 25, 2026.", every tile one instant (`2026-11-25T09:39:45Z`), no stale banner, "several times a day" in 0 of 4 pages read. Reads 2 and 3 are due Nov 26 and Nov 27, with the run logs. No carried section has occurred on production since the merge, so the older-section line is proven on a local build only (below). |
| 2 | Published | 4 of 7 days | Evening Briefs on main: Nov 21 (watcher run 44971801349), Nov 22 (run 45081776201), Nov 23 (45286438006), Nov 24 (45507657192). Nov 18 to 20: none (the canary lock N-1 fixed). Days 5 to 7 are Nov 25 to 27. Gap issues #130 and #131 were closed by `close_edition_flags` after a Brief, not by hand. The stored-wire class is closed for good by merge 4 (below). Canary warnings of the Nov 24 run: 18, listed below. |
| 3 | Readable in five minutes | open | Findings 2 to 5 below. |
| 4 | Clean | open | Production crawl running (background), counts to follow. |
| 5 | Whole | open | Same crawl. |
| 6 | Fast | open | Lighthouse not run yet. |
| 7 | Taught | open | Not read yet. |
| 8 | Quiet | built, reads pending | Run sweep Nov 18 to Nov 25 09:26 UTC: 287 runs, 63 failures, all 63 the offline canary's stored-wire case, the last at 2026-11-22T01:00:48Z; 0 failures since N-1's merge. Health gate: 3 full runs (Nov 22, 23, 24), all "Healthy". Ignore rule: merge 2, proven twice (merges 2 and 4 were canceled by Netlify, count below). Publish-time gate: merge 4. Gap finding a warning, week's spend, health gate's prices line: merge 5. Spend Nov 18 to 24: 11 runs, 581,208 tokens, $0.8590 (`C-DONE-logs/week-spend-2026-11-18-to-24.txt`). Open: the health gate runs 6 to 11 hours late (Jack's, below). |
| 9 | Found | open | Not read yet. |
| 10 | Beautiful enough | open | The home's lead paragraph placed at 1280 and up (merge 1). Before: `C-DONE-shots/home-1440-before-production-4750aca-jack-0401ET.webp`. |

## Merges, in order

| # | Repo | Merge | Tip | Onto | What | Gate |
|---|---|---|---|---|---|---|
| 0 | gcm-newsroom | `b5c0806` | `bab0253` | `2f1f538` | The family newsroom is off: `newsroom.yml` has no schedule, `workflow_dispatch` kept, one line in `docs/HEALTH.md`. | Five Python suites and three Worker tests exit 0, every workflow parsed. |
| 1 | crypto | `96ca8aa` | `d18b90c` | `9e799fa` | Why Bitcoin moved has its own cell in the desktop grid, under the Brief card. `system.css` sha256 `1dafda16013688d7a9851fffa2a13e7bc455cfb2aee0c2c8f1c3aa9d4f4affe8` to `2d034b8ab496d2a20d9625ef1ab972686ea135d5523dbf8050f87ada49f1fb87`; the 9.5b pin holds. | Canary exit 0 on tree `d4866675` (`lead-place-gate.log`). Built: stamp `96ca8aa`, 09:20:14Z. |
| 2 | crypto | `96edf6e` | `75a68ad` | `96ca8aa` | review/ and .github/ never build the site; the reads canary walks both trees. The scorecard starts. | Canary exit 0 (`ignore-rule-gate.log`). No build: Netlify canceled it. |
| 3 | crypto | `3d286ab` | `00f97ff` | `96edf6e` | Point 1: the Board's stamp is its fresh read; an older section prints its own time on its tile, on the Board's stamp line and on the home's Board line; a section's page takes its own read; the ticker and Why Bitcoin moved take the prices' read; the banner's window and cadence are read from the schedule; Retry-After capped at 90 s. | Canary exit 0 on tree `7046ebee` (`fresh-gate.log`). Built: stamp `3d286ab`, 09:42:23Z. |
| 4 | crypto | `ec99dba` | `cf2f264` | `3d286ab` | The publish-time gate (`scripts/canary_gate.py`): a red canary stops a run only when the code is red; red from data stored since the last code commit is a named warning and the run goes on. The Wire test's run-from-git half retired (below). | Real canary, exit 0, on `eb6f04c` in a fresh worktree (`publish-gate-real-canary-proof.log`). No build (workflows and scripts only). |
| 5 | crypto | this merge | | `ec99dba` | Point 8: the edition gap finding is a warning; `ops_ledger.py --week`; the markets feed carries `prices_as_of_utc` and the health gate reads it. Merged with `[skip netlify]`: it rides the 8:15 AM read's build. | Canary exit 0 (`quiet-gate.log`). |

Every push verified by hash (U-8): local equals origin, 0 ahead, each time.

## Tests new this session, each seen red, each planted

`scripts/cdone_test.py`, in the canary as `_cdone_canary`. Plants restored from saved copies, never `git checkout`.

| Group | Cases | Red on main | Plants (all caught) |
|---|---|---|---|
| 1 lead placement | 9 | 2 FAIL (`lead-place-red-on-main.log`) | 3: rule removed; lead in the Brief card's row; chart span cut |
| 2 ignore rule | 20 | 4 FAIL (`ignore-rule-red-on-main.log`) | 2: review/ off the list; site/ on it |
| 3 fresh | 20 | 5 FAIL then TypeError, no `now` (`fresh-red-on-main.log`) | 14 (`fresh-plants.log`) |
| 4 publish gate | 18 | 1 FAIL, no script (`publish-gate-red-on-main.log`) | 7 (`publish-gate-plants.log`); one plant was not caught on the first pass, a case was added, rerun caught all |
| 5 quiet | 10 | 5 FAIL, then 2 FAIL (`quiet-red-on-main.log`, `-2.log`) | 8 (`quiet-plants.log`) |
| gcm-newsroom `test_newsroom_off.py` | 3 | 2 FAIL | 2 |

Group 4 runs a stand-in canary in a throwaway repository, said beside each case (U-10). The real proof: a worktree of
the branch with one stored wire line given a dash, the real canary: red on the tree (`sprint 9.7: no feed has a dash`),
green on the code commit, verdict data, exit 0, the case named in the warning and the step summary.

## Found while proving, fixed

- `scripts/sprint96w_test.py` ran main's `render_wire` from git (`3be7684`) when the clone held that commit and skipped
  the case when it did not. Every CI checkout is one commit deep, so it never ran there; on a deep clone it has been red
  since Sprint A took the site-name line out of the footer on November 7 (`d762a89`). Seen red here once the clone was
  deepened (`publish-gate-96w-red-on-deep-clone.log`). The run-from-git half is retired; the stored copy of main's
  output, re-pinned by Sprint A, is the pin. A machine with full history (the Mac) has had a red canary on main since
  November 7 for this reason alone.

## Production reads

| Read at (ET, Nov 25) | Stamp | What was read |
|---|---|---|
| 4:20 AM | `4750aca`, built 2026-11-24T23:18:18Z | `/stamp.txt` only; merge 1's build had not landed. |
| 4:24 AM | `96ca8aa`, built 09:20:14Z | Served `system.css` carries `[data-block="lead"]{grid-column:1;grid-row:4}` (1 match). IndexNow by hand: 1 URL, response 200. |
| 5:06 AM | `3d286ab`, built 09:42:23Z | Point 1, read 1 (scorecard row 1). IndexNow by hand: 2 URLs, response 200. |

Count of record (Worker `/counts/today`, Nov 25, read 5:06 AM ET): production ready 2, canceled 1. Merge 4 pushed after
that read; its count is in the next read.

## Point 1 on a carried build (local build, not production, U-10)

`site/data/pulse.json` with prices and the whole market carried from 13:16 UTC, built at the Nov 24 evening clock:
/pulse reads "As of 6:12 PM ET on Nov 24, 2026." and on its own line "Prices and whole market as of 8:16 AM ET on Nov
24."; the two carried tiles carry `2026-11-24T13:16:00Z`, the other six `23:12:59Z`; /pulse/sentiment reads 6:12 PM,
/pulse/prices reads 8:16 AM; no stale banner. The stored file was restored from a saved copy.

## The canary's warnings, Nov 24 evening run 45507657192 (18, all inside the quiet block)

morning fell back (1 sentence survived the copy law); flows stablecoin tile -201100000 against rows 201100000;
posture DOGE averages identical; consistency gate fixture (Oct 15 Edition withheld); why_evidence BTC section not drawn
(TypeError: 'str' object cannot be interpreted as an integer); share queue and share card refusals for 2026-10-14-bitcoin
(7 lines); researcher c011 boundary; editor contract retries (5 lines). All are the canary's own fixtures and negative
tests except two worth a look: the flows sign mismatch and the why_evidence TypeError. Both open.

## Findings from Jack's screenshot of the home, Nov 25, 4:01 AM ET, 1440 wide (stamp `4750aca`)

1. The lead paragraph sat alone in the top-left cell with an empty cell beside it. Fixed, merge 1.
2. Two Bitcoin prices an inch apart: the paragraph's $59,968 and -2.31% over 24 hours (6:17 PM) against the live
   line's $59,348 and -1.14% (4:01 AM). Open, point 3.
3. The paragraph restates the tiles beside it; HYPE's -5.50% printed three times on one screen. Open, points 3 and 4.
4. At 4:01 AM Wednesday the masthead reads Tuesday, and "Next Brief tomorrow at 8:15 AM ET" means today. Open, point 4.
5. "Today: Nothing scheduled." and "Mine: Pins come from any coin page." are empty sections; the All crypto tile reads
   "no 24h figure". Open, points 3 and 4.
6. XRP at six decimals beside Solana at two; middle dots as separators; "Written from Bitcoin's day, ETF flows..."
   on the Brief card; the masthead's age prints red inside the schedule. Open, points 4 and 10.

## From the run sweep, open

- Run 565 (Nov 23, 00:42 UTC) closed gap issue #131 from a stand-down of the evening slot while naming the morning slot.
- The janitor closed "Desk run failed" #128 on Nov 20 while the canary was still red; #129 reopened nine minutes later.

## The family newsroom, once

Done in gcm-newsroom, merge `b5c0806`. Only `newsroom.yml` lost its schedule: it is the pipeline that publishes. Left as
they were, named: `research.yml` (Sundays, the topic sweep that feeds the pipeline, still spends its weekly model call),
`audit.yml`, `compliance.yml`, `deskeditor.yml`, `govscout.yml`. The DeskEditor liveness check ran inside the newsroom
run, so it no longer runs on a schedule.

## Jack's

1. **The health gate runs late.** Its crons are 7:03 AM ET; GitHub started the six runs of Nov 22 to 24 between 1:14 PM
   and 6:46 PM ET. The gate is a GitHub cron on purpose (it must mail on the day the Worker fails), so the cron stays;
   the Worker can dispatch it on time as well, and the gate already stands a second run down. The diff for
   `gcm-newsroom/slot-trigger/src/worker.js` follows in this report before exit; the command is `cd slot-trigger && npx
   wrangler deploy`. Not deployed by this desk.
