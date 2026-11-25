# C-DONE: the running scorecard

Session opened Tuesday, November 24, 2026; working from Wednesday, November 25, 4:00 AM ET. One Claude Code cloud
session on gocheckmycrypto with gcm-newsroom attached (push access). `docs/RULES.md` body hash
`4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, verified at the opener. No trailer on any commit.
Updated after every merge. A point is green only with its evidence named; "open" means not yet scored. Jack's word of
November 25: continue with all fixes and items; the target is above 8 of 10, pushing toward 9.

## Scorecard

| # | Point | State | Evidence or reason |
|---|---|---|---|
| 1 | Fresh | built, 1 of 3 reads | Merge 3. Production stamp `3d286ab`, read Nov 25 5:06 AM ET: /pulse "As of 4:39 AM ET on Nov 25, 2026.", every tile one instant, no stale banner, "several times a day" on 0 of 4 pages read. Reads 2 and 3 are due Nov 26 and 27, with the run logs. No section has been carried on production since the merge, so the older-section line is proven on a local build only (below). |
| 2 | Published | 4 of 7 days | Evening Briefs on main: Nov 21 (watcher run 44971801349), Nov 22 (45081776201), Nov 23 (45286438006), Nov 24 (45507657192). Nov 18 to 20: none (the canary lock N-1 fixed). Days 5 to 7 are Nov 25 to 27. Gap issues #130 and #131 were closed by `close_edition_flags` after a Brief, not by hand. The stored-data class is closed by merge 4. |
| 3 | Readable in five minutes | green on production, one state | Merge 6. Production stamp `a0153db`, read Nov 25 7:05 AM ET at 375 by 812 (fold 755 px above the tab bar), before the morning read: tape 105 to 207, the day's line to 254, the Brief card to 353, the movers and standouts to 550, Today's first event title ending at 638. Screenshot `C-DONE-shots/home-375-production-a0153db.png`. The state with the day's Brief on the card was measured on a local build only (next event's title at 734); its production read is after the 8:15 AM read. |
| 4 | Clean | fixes merged, count of record pending | Crawl of stamp `3d286ab` (table below); fixes in merges 7, 9, 11. The count of record is the same crawl on the build that carries them. |
| 5 | Whole | green but for one page, fixed in merge 11 | Stamp `a0153db`: all 368 sitemap pages at 375: tab bar present with five tabs on 368 of 368, each tab's target answers; horizontal overflow on 1 page (273 px, a long address in /articles/senate-fails-clarity-act-cloture-vote..., fixed in merge 11). Watchlist from a fresh device: hidden when empty; SOL pinned on /coins/sol; the home shows "SOL $67.74 -3.90%"; still there after a reload. Titles, descriptions and canonicals on 915 of 915 pages; /market-pulse 301 to /pulse; 368 sitemap URLs all 200; 12 dead internal links fixed in merge 7. |
| 6 | Fast | green | Lighthouse 13.6.0 mobile on production stamp `a0153db`: home performance 97, accessibility 100; Board 100 and 100; a Brief 100 and 100 (`C-DONE-logs/lighthouse-production-a0153db.txt`). |
| 7 | Taught | green | Merge 9. All twelve explainers read in full on Nov 25; 23 lines corrected (list in the merge's commit); each prints "Last reviewed November 25, 2026" from its own record; every tile's definition is on /learn and each Board reading's definition links its full explainer; Learn is in the nav. Production stamp `22f4c70`, read 7:58 AM ET: /learn/bitcoin-posture, /learn/leverage, /cold-storage and /crypto-tax print "Last reviewed November 25, 2026"; the live cards read "as of 7:51 AM ET on Nov 25, CoinGecko" and "..., OKX"; no "site build", no "last build", no "line 8z". |
| 8 | Quiet | built, reads pending | Run sweep Nov 18 to Nov 25 09:26 UTC: 287 runs, 63 failures, all 63 the offline canary's stored-wire case, the last at 2026-11-22T01:00:48Z; 0 since. Health gate: 3 full runs (Nov 22, 23, 24), all "Healthy". Ignore rule: merge 2, proven (merges 2 and 4 canceled by Netlify). Publish-time gate: merge 4. Gap finding a warning, the week's spend, the gate's prices line: merge 5. Spend Nov 18 to 24: 11 runs, 581,208 tokens, $0.8590. The push-time canary on CI passed on every merge of this session (runs 458 to 465). Open: the first publishing run through the new gate (the 8:15 AM read), and the health gate's lateness (Jack's, below). |
| 9 | Found | green | Merge 8. "By Crypto Cronkite" and a NewsArticle author of that name with the story's own published time; home title "Why crypto moved today: prices and big movers - GoCheckMyCrypto"; description names the Board, the big movers and "No hype"; About names Go Check My Brands LLC and nothing about method; Edition titles carry their date. Production stamp `22f4c70`, read 7:58 AM ET: the home's title and description as merged; the Nov 24 Brief reads "By Crypto Cronkite", its NewsArticle author is Crypto Cronkite, datePublished `2026-11-24T23:15:43Z`; About has the LLC and the byline and none of the method words; /edition/2026-11-24 is titled "Evening Brief, November 24, 2026 - GoCheckMyCrypto". |
| 10 | Beautiful enough | in progress, two elements are Jack's | Merges 1, 6, 11 and 13. Before and after of production at 375 and 1440 under `C-DONE-shots/` (home, Board, a Brief). The red and white holds (light theme, read at both widths). **There is no hero photo and no scrim on production:** the poster files are in `site/assets/hero/` and nothing references them (open ruling J-2, "the board's default is none"). **The Chart Master and Whale Watch marks are not drawn anywhere** (`site/assets/marks/` is unreferenced), so they are not misused, and not used. Neither was added: no redesign. |

## Merges, in order

| # | Repo | Merge | Tip | Onto | What | Gate and build |
|---|---|---|---|---|---|---|
| 0 | gcm-newsroom | `b5c0806` | `bab0253` | `2f1f538` | The family newsroom is off: `newsroom.yml` has no schedule, `workflow_dispatch` kept, one line in `docs/HEALTH.md`. | Five Python suites and three Worker tests exit 0. |
| 1 | crypto | `96ca8aa` | `d18b90c` | `9e799fa` | Why Bitcoin moved has its own cell in the desktop grid. | Canary exit 0. Built, stamp `96ca8aa`, 09:20:14Z. |
| 2 | crypto | `96edf6e` | `75a68ad` | `96ca8aa` | review/ and .github/ never build the site; the scorecard starts. | Canary exit 0. Canceled by Netlify (no build). |
| 3 | crypto | `3d286ab` | `00f97ff` | `96edf6e` | Point 1: the Board's stamp is its fresh read; older sections carry their own time; the banner reads the schedule; Retry-After capped at 90 s. | Canary exit 0. Built, stamp `3d286ab`, 09:42:23Z. |
| 4 | crypto | `ec99dba` | `cf2f264` | `3d286ab` | The publish-time gate (`scripts/canary_gate.py`); the Wire test's run-from-git half retired. | Real canary exit 0 on `eb6f04c` in a fresh worktree. Canceled by Netlify. |
| 5 | crypto | `b187fce` | `0475497` | `ec99dba` | Point 8: gap finding a warning; `ops_ledger.py --week`; `prices_as_of_utc` in the markets feed, read by the health gate. | Canary exit 0. `[skip netlify]`; carried by merge 6's build. |
| 6 | crypto | `a0153db` | `0ac3124` | `b187fce` | Point 3: the Board leads the home; one line for Bitcoin since midnight ET; the long paragraph stays on /today/; the phone order; "Next date"; an empty watchlist draws no block. | Canary exit 0 on tree `50e56710`. Built, stamp `a0153db`, 10:41:44Z. |
| 7 | crypto | `d499c72` | `5ab560b` | `a0153db` | Points 4 and 5: dead internal links drawn as text; Edition pages in Eastern time with no place; no empty rail; outlets by name; a price under a cent; US spelling. | Canary exit 0. `[skip netlify]`. |
| 8 | crypto | `767d3c2` | `18305df` | `d499c72` | Point 9: the Crypto Cronkite byline and schema; the home's title and description; About; dated Edition titles. | Canary exit 0. `[skip netlify]`. |
| 9 | crypto | `70dcf4f` | `09865a7` | `767d3c2` | Point 7: every explainer read and corrected; "Last reviewed"; the Fear and Greed tile's band from the site's one table; the live card's own source. | Canary exit 0. `[skip netlify]`. |
| 10 | crypto | `a63b2bd` | `a14449b` | `70dcf4f` | The story-lane ruling: 14 quiet days takes a lane off the home and the lane lists; its page says since when. | Canary exit 0. `[skip netlify]`. |
| 11 | crypto | `01f4697` | `078a0e8` | `a63b2bd` | Points 4 and 10: nothing twice in the movers; four decimals under a dollar; the age in its stamp's ink; the empty Brief card; long addresses wrap. | Canary exit 0. `[skip netlify]`. |
| 12 | crypto | `22f4c70` | `002399c` | `01f4697` | The scorecard after eleven merges, the handoff section (documents only). | Canary exit 0. **Built** (see the note below), stamp `22f4c70`, 12:54:11Z: it carried merges 7 to 11 to production. |
| 13 | crypto | `28fe518` | `6dea1ea` | `22f4c70` | Points 3 and 4: /today/'s answer one short sentence per fact; no story line where there is no story. | Canary exit 0 on tree `d54cba1`. `[skip netlify]`. |

Every push verified by hash (U-8): local equals origin, 0 ahead, each time.

**One build over the allowance on November 25, the desk's error.** Merges 7 to 11 carried `[skip netlify]` to ride the
8:15 AM read's build. Merge 12, documents only, was pushed without the marker; Netlify's ignore rule compares against the
last BUILT commit (`a0153db`), that diff held the five skipped merges' site files, and it built, correctly. So the day
has four merge builds (1, 3, 6, 12) against a share of three, and with the morning read and the evening Brief it ends at
six of five. The same trap as October 11 (`0c47b73`). From merge 13 on, every merge pushed while a skipped site commit
is unbuilt carries the marker. Count of record (Worker `/counts/today`, Nov 25, read 7:57 AM ET): production ready 4,
canceled 2.

## Re-pins, old to new

- `site/assets/system.css`: `1dafda16013688d7a9851fffa2a13e7bc455cfb2aee0c2c8f1c3aa9d4f4affe8` (main at the opener) to
  `2d034b8ab496d2a20d9625ef1ab972686ea135d5523dbf8050f87ada49f1fb87` (merge 1) to
  `fe1f7d2ace3920f3988eb612f1e490fbf1c51525acfc00341b56a0bd0bed1f53` (merge 6).
- `fixtures/sprint95b/system.95.css`: `3d4f145bd88b004b32a15d73ec161a538a490871c7278996bb88137c86027b2b` to
  `8afa1fcf6c8a930f5ce65d6de50661ad061c42266ce274f712c9e10c6c09382d` (merge 6: the same marked C-DONE block, so "the
  9.5b block cut out leaves this file" still holds).
- `deadlinks-baseline.json`: 6 excused targets to 0 (merge 7).
- `site/assets/site.css`: `3b90de50fdf0021cdcb2aef4739cae7b69430fe090ce283df4a426ccd3b357f6` to
  `88654b059e214934362750dc0dbe4e22c17a2eb1cda39bab708d93a686b4dc3b`; `system.css` to
  `01dc4981649abd865bb96b274167ba1221c0171d380c2e2b3f8ef677dafee90c`; the two 9.5b stylesheet fixtures take the same
  lines (merge 11).
- `HOME_JS_SHA256` (the 9.5 text of the home's script): `4df64baaee46fe975e1d2e2bf832e6f6eb270fe3c053628e460c8cf02a4995e4`
  to `b46841673ba000785c3b3e9d0c9a0f1ff3914e8253a28fb6ae15de885fc097f2` (merge 11: the price formatter).

## Older checks brought to Jack's rulings of November 24 and 25, each with a C-DONE note beside it

- The home canary's "a day with no events says nothing scheduled": now the next dated event, or no block (merge 6).
- "The ten blocks keep section 2's order" in sprint 9.3, 9.5 and 9.9.1: the dated block is drawn only when a date is
  ahead (merge 6). Their "card first" cases still pass on markup; on the page the tape now leads, by the ruling.
- Sprint 9.5b's 375 markup: the empty-day block is masked on both sides (merge 6).
- `scripts/column_fit.mjs` measures against the nearest ancestor that draws a box (merge 6).
- The canary's "article page renders the also-reported line": the line is drawn by `sb.also_reported` (merge 7).
- `scripts/sprint96w_test.py`: the run-from-git half retired, red on any deep clone since November 7 (merge 4).
- The canary's two "one name" byline checks and sprint 9.7's home title tag (merge 8).
- The home canary's lane cases and sprint 9.5's two Storylines cases, which read the day's content (merge 10).
- Sprint 9.5b's markup pin masks the standouts line on both sides (merge 11).

## Tests new this session, each seen red, each planted

`scripts/cdone_test.py`, in the canary as `_cdone_canary`. Plants restored from saved copies, never `git checkout`.

| Group | Cases | Red on main | Plants (all caught) |
|---|---|---|---|
| 1 lead placement | 9 | 2 FAIL | 3 |
| 2 ignore rule | 20 | 4 FAIL | 2 |
| 3 fresh | 21 | 5 FAIL then TypeError | 14 |
| 4 publish gate | 18 | 1 FAIL, no script | 7 (one missed on the first pass, a case added, rerun caught all) |
| 5 quiet | 12 | 5 FAIL, then 2 FAIL | 8 |
| 6 the answer first | 14 | 9 FAIL | 13 |
| 7 clean and whole | 10 | 10 FAIL | 12 |
| 8 found | 13 | 11 FAIL | 10 |
| 9 taught | 39 | red, no review dates | 11 |
| 10 story lanes | 9 | 7 FAIL | 8 |
| 11 polish | 6 | 5 FAIL | 5 |
| gcm-newsroom `test_newsroom_off.py` | 3 | 2 FAIL | 2 |

Logs: `docs/REPORTS/C-DONE-logs/<item>-red-on-main.log`, `-plants.log`, `-gate.log`. Group 4's real proof
(`publish-gate-real-canary-proof.log`): one stored wire line given a dash, the real canary red on the tree and green on
the code commit, verdict data, exit 0, the case named.

## Points 4 and 5: the crawl of production, Nov 25, stamp `3d286ab` (start and end), 915 HTML pages, 941 link targets

Pages and extracted text are kept in the session's scratchpad; the counts below are pages affected / occurrences.

| Pattern | Count | What it is | State |
|---|---|---|---|
| "undefined" | 5 / 5 | English prose ("custody rules remain undefined"), no script leak | 0 leaks |
| "NaN", "null" | 0, 0 | | green |
| "None" | 25 / 26 | English ("None of these") | 0 leaks |
| a bare $0 | 22 real | /why/2026-11-12-pepe "$0.00" five times (fixed, merge 7); stored Brief and Edition text "flat at $0", "$0 longs" on two dated /today/ pages (stored records, not rewritten) | 5 fixed, 17 in stored copy |
| "0 pieces", "1 pieces" | 0, 0 | | green |
| a middle dot shown as an unrendered escape | 0 | | green |
| the middle dot as a separator | 915 / 15,795 | the site's separator in the masthead, tiles, footer and link lists | read as designed, not removed; if "literal ·" in the brief means every dot, that is a site-wide change and Jack's to call |
| a UTC stamp of the site's own | 88 Edition pages | "The Evening Brief 11:15 PM UTC" | fixed, merge 7 (Eastern time) |
| "UTC" in reported text | 29 pages | an event's own time in a stored story ("at 01:30 UTC") | stored copy, not rewritten |
| em dash, en dash | 0, 0 | | green |
| "the last build" | 1 | /learn/bitcoin-posture | open, point 7 |
| other build notes, TODO, placeholder | 0 | | green |
| "Stale data" | 0 | | green |
| AI as the site's maker | 0 | 6 pages name AI companies as the news subject | green |
| empty section or card | 24 | 23 empty Edition rails (fixed, merge 7); 1 hidden pinned-coins holder on /pulse | 23 fixed |
| lowercased source headlines shown | 84 article pages | "CoinDesk: u s sec maps out crypto custody..." under "Also reported by" | fixed, merge 7 |
| British spelling in site copy | 2 | About, the on-chain explainer ("labelled") | fixed, merge 7 |
| a place in the Edition's dateline | 88 Edition pages | "Charleston, S.C." | removed, merge 7 (ruling 4 of October 16: no personal details) |
| title, description, canonical missing | 0, 0, 0 | | green |
| duplicate titles | 7 groups | 70 Evening, 13 Afternoon, 5 Morning Brief articles with no date in the title; paginated hubs; /today/ and its dated twin | open, point 9 |
| internal 404s | 12 | 10 links to stories the desk never published, /coins/sei and /coins/strk from two dated pages | fixed, merge 7: drawn as text (15 anchors on the local build), `deadlinks.py` PASS with 0 excused |
| /market-pulse | 301 to /pulse | | green |
| sitemap URLs | 368, all 200 | | green |

Still to count after merge 7 is live: the same crawl again, and a story older than 48 hours presented as today's.

## Production reads

| Read at (ET, Nov 25) | Stamp | What was read |
|---|---|---|
| 4:20 AM | `4750aca`, built Nov 24 23:18:18Z | `/stamp.txt` only. |
| 4:24 AM | `96ca8aa`, built 09:20:14Z | Served `system.css` carries merge 1's rule. IndexNow by hand: 1 URL, response 200. |
| 5:06 AM | `3d286ab`, built 09:42:23Z | Point 1, read 1. IndexNow by hand: 2 URLs, response 200. |
| 5:40 AM to 6:00 AM | `3d286ab` (start and end) | The crawl. |
| 6:55 AM | `a0153db`, built 10:41:44Z | `/stamp.txt` and the count of record. The page read at 375 is next. |

## Point 1 on a carried build (local build, not production, U-10)

`site/data/pulse.json` with prices and the whole market carried from 13:16 UTC, built at the Nov 24 evening clock:
/pulse reads "As of 6:12 PM ET on Nov 24, 2026." and on its own line "Prices and whole market as of 8:16 AM ET on Nov
24."; the two carried tiles carry `2026-11-24T13:16:00Z`, the other six `23:12:59Z`; /pulse/sentiment reads 6:12 PM,
/pulse/prices reads 8:16 AM; no stale banner. The stored file was restored from a saved copy.

## Judgment calls made without asking, each easy to reverse

1. The long Why Bitcoin moved paragraph is off the home and stays on /today/; the home keeps one line (Bitcoin since
   midnight ET). Reason: the home's own rule that nothing prints twice, and Jack's reading of the screenshot.
2. At 375 the verdict card follows the movers and the next date; the Brief card is the "why". Reason: the order in
   point 3 as written.
3. "Next Brief ..." is hidden inside the Brief card on phones when the card carries the day's line. Reason: the fold.
4. The Edition's dateline no longer prints a city. Reason: ruling 4 of October 16.
5. A red canary from stored data no longer stops a run. Reason: four lock-ups in thirty days; the code is still gated
   at every push and merge.

## Findings from Jack's screenshot of the home, Nov 25, 4:01 AM ET, 1440 wide (stamp `4750aca`)

1. The lead paragraph alone in the top-left cell. Fixed, merge 1, then replaced by one line, merge 6.
2. Two Bitcoin prices an inch apart. Fixed, merge 6: the home prints the price once, on the tape.
3. The paragraph restated the tiles; HYPE's figure three times. Fixed in part, merge 6: the paragraph is gone; HYPE
   still prints in the top 20 row and in the standouts line. Open.
4. At 4:01 AM the masthead reads the build's day and "Next Brief tomorrow" means today. Open, point 4.
5. "Today: Nothing scheduled." and the empty "Mine" block. Fixed, merge 6. "no 24h figure" on the All crypto tile: open.
6. XRP at six decimals in the live price beside the build's four; the masthead's age in red inside the schedule; "Written
   from Bitcoin's day..." on the Brief card. Open, points 4 and 10.

## The canary's warnings, Nov 24 evening run 45507657192 (18, all inside the quiet block)

All are the canary's own fixtures and negative tests except two worth a look: `flows: stablecoin tile -201100000 !=
by-exchange stablecoin rows 201100000` and `why_evidence: the section for BTC was not drawn (TypeError: 'str' object
cannot be interpreted as an integer)`. Both open.

## From the run sweep, open

- Run 565 (Nov 23, 00:42 UTC) closed gap issue #131 from a stand-down of the evening slot while naming the morning slot.
- The janitor closed "Desk run failed" #128 on Nov 20 while the canary was still red; #129 opened nine minutes later.

## The family newsroom, once

Done in gcm-newsroom, merge `b5c0806`. Only `newsroom.yml` lost its schedule: it is the pipeline that publishes. Left as
they were, named: `research.yml` (Sundays, the topic sweep that feeds the pipeline, still spends its weekly model call),
`audit.yml`, `compliance.yml`, `deskeditor.yml`, `govscout.yml`. The DeskEditor liveness check ran inside the newsroom
run, so it no longer runs on a schedule.

## Rulings checked against the code, no change needed

- The cold storage module is Ledger-only: `explainers.py` has two store links, both `_cta(LEDGER_STORE, "Ledger", ...)`
  (cold storage and counterfeit devices); Trezor was removed September 9 and appears only as a cited manufacturer.
  CoinLedger is the tax tool on /crypto-tax, a separate module.
- The Brief at one a day and the watcher's cage of two runs a day: untouched.

## Still open, in the order to take them

1. "Next Brief tomorrow at 8:15 AM ET" is true when built and wrong after midnight (Jack's, below: it is ruled wording).
2. Run 565's flag closure and the janitor closing a live alarm (from the run sweep). Neither stops a run or a page.
3. /today/ and its dated twin share a title on the day; paginated hubs share theirs.
4. On November 23 and 24 a breaking run also published an Afternoon Brief, so those days carry two Briefs. Not touched
   (the Brief and the watcher's cage are not this session's to change); named because the ruling says one a day.

Closed since the last scorecard: both canary warnings that looked real are the canary's own negative tests ("a broken
record draws no section and raises nothing"; "a tile that disagrees with its rows is caught"), so all 18 warnings of the
Nov 24 run are fixtures and negative tests. The "no 24h figure" line on the All crypto tile is Sprint A's ruled wording
for a withheld figure and stays.

## Jack's

1. **The health gate runs late.** Its crons are 7:03 AM ET; GitHub started the six runs of Nov 22 to 24 between 1:14 PM
   and 6:46 PM ET. The gate is a GitHub cron on purpose (it must mail on the day the Worker fails), so the cron stays;
   the Worker can dispatch it on time as well, and the gate already stands a second run down. The diff for
   `gcm-newsroom/slot-trigger/src/worker.js` is `docs/REPORTS/C-DONE-worker-health-dispatch.patch` (80 lines: one
   dispatch at 7:05 AM Eastern, and its test; the Worker's four test files pass with it). Apply and deploy:
   `cd gcm-newsroom && git apply ../gocheckmycrypto/docs/REPORTS/C-DONE-worker-health-dispatch.patch && cd slot-trigger
   && npx wrangler deploy`. Not applied to gcm-newsroom and not deployed by this desk.
4. **"Next Brief tomorrow at 8:15 AM ET."** The line is right when the page is built and wrong after midnight, because
   the page is static (you read it at 4:01 AM). One function writes it for the Brief card, /today/ and the verdict
   notice, and its wording was ruled on October 20 (29 test cases pin it). Two options: (a) leave it; (b) name the day
   instead of "tonight" and "tomorrow" ("Next Brief Thursday at 8:15 AM ET"), which stays true until the slot passes.
   The desk recommends (b); it is one function and the 29 cases.
5. **The hero photo and the section marks** (point 10): neither is on the site today (J-2 is still open at its default
   of none). Say if either should come back; it is a design change, not a fix.
6. **Section ledes under the copy law.** Whale Watch and The Brief each open with a paragraph that explains the section.
   Chrome copy changes only by your ruling, so they were left.
3. **The CoinLedger affiliate link** carries an id that reads as a first name; it shows on hover. Changing it changes
   who is paid, so it is yours.
2. **The middle dot.** If the brief's "literal ·" means the separator itself and not an unrendered escape, say so: it is
   on every page (15,795 times) and replacing it is one site-wide change.
