# Program 8, Sprint 8.1: the daily answer, plus the 7.x cleanup (report)

Status: **built and proved on the branch; NOT merged.** Jack's yes on the screenshots is the next step, and the merge must land outside 6:30 to 8:15 PM ET.

## Start
- `docs/RULES.md` body hash (from line 11): `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`. It matches.
- origin/main at the start: `15be76f` (ledger row, 23:17Z). It contains 7.3's merge `5bb4df7` and its close `c86fb1f`.
- Shell date, ET: Wednesday October 14, 2026, 7:37 PM at the start.
- Branch: the session was bound to `claude/zen-goodall-iaihrf`, so the work is there and not on a branch named `sprint-8-1`. Program 8 is its own documents-only commit, `01254e6`, taken verbatim from Section A.
- Nothing was pushed before 8:15 PM ET.

## The 7.3 live proof
The 7:08 PM Edition of Oct 14 has **not** produced an edition. The ops-ledger row for run `38652474134` (a `workflow_dispatch`, 23:17Z) reads `twins_drops: 0, twins_unparsed: 0`, no `twins_log`, `wrap: "failed"`, `stages_absent: [3.5-researcher, 4-writer, 4.5-approver, 5-digest]`, and there is no `site/content/2026-10-14-evening-brief.json`. So there are no dropped sentences to judge yet; the proof is still open, and the failed wrap is its own item to look at (the run log was not read here). The /today/ evening record is written by the Edition run, so it will not exist tonight unless the Edition publishes.

## Builds
Not read: this session has no Netlify access, so the before and after counts are not stated. The branch is not merged, so it has caused no production build.

## What was built
- **Item 0, /today/ and /today/YYYY-MM-DD** (`today.py`, `site_build._write_today`, workflows). One record per slot, no model call. The page: the dated answer paragraph, What moved, What was reported beside it, the Board, the stamp with the next update, the archive. Every sentence it writes goes through the twins gate. NewsArticle structured data carries ET offsets. The sitemap carries /today/ (priority tier) and each dated page (archive tier) with real lastmod. The home page links "Why crypto moved today →" under the Brief card.
  - Records are `site/data/today/YYYY-MM-DD-<slot>.json`, written by a new step in `morning-read.yml` and `crypto-news-brief.yml` (`python3 today.py --write`, never a gate) and committed with the slot's push. A stored record is frozen. A dated page links only earlier days, so a later day cannot change it. A build with no stored record composes one from the files in hand. **The two workflow files are edited: confirm the push token may update workflow files.**
  - The answer is the morning read's or the Edition's text only when it names Bitcoin, states the day's direction the way the sign says, carries a figure, has no cause word, and passes the gate sentence by sentence. Otherwise it is the fixed template. In practice the morning read quotes no change (7.1's rule), so the template answers most mornings.
- **Item 1, the morning wire stamp.** The cause was that `home.wire_top` printed `ranked_et` (the Edition's time) while `wire.refresh` stamps `refreshed_et`. It now prints "Re-ranked 8:18 AM ET on Oct 14" after a refresh. The re-rank itself was already running (`wire.py --refresh` in the workflow and in the Netlify build).
- **Item 2, small prices.** `_price_fmt` prints a price under $0.0001 as `$0.0₆3682`; `_price_label` gives "0.0000003682 dollars" as the Top 100 cell's and the coin page's `aria-label`. The 10 px tier is removed (CSS and `_price_class`). A price that rounds up to $0.0001 prints in full.
- **Item 3, Whale Watch at 1440.** **The brief's premise did not hold, and nothing was changed.** At 1440 no element is wider than its column; the two tables fill their grid cells (543 and 471 px in a 1036 px page). The 7.3 handoff wording was that they were narrower than the column, which is under-filling. At 375 the By exchange table scrolls inside its own box. I added `scripts/column_fit.mjs` as the guard (no element wider than its column, no table text under 12 px, at 1440 and 375) and ran it on /flows, /today/ and the home. **Jack: what did V-11 punch 6 ("full width") mean?** That decides whether there is anything to fix.
- **Cadence.** `NEWS_CADENCE_LINE` is "The Brief, every morning and evening."; the old line printed nowhere else; the pinning test in `verify_pipeline.py` is changed.
- Jack's three rulings and the program are recorded in `docs/HANDOFF.md` (section 3b, and the open-items table).

## The three fixture days (`scripts/sprint81_test.py`, section A)
| Bitcoin 24h | Title |
|---|---|
| -2.03% | Why is crypto down today? Wednesday, October 14, 2026 |
| +1.80% | Why is crypto up today? Wednesday, October 14, 2026 |
| -0.20% | Crypto today: flat. Wednesday, October 14, 2026 |

Plus or minus 0.5 is flat; 0.51 is not. No Bitcoin reading, or no slot read, makes no record.

## Tests: red on main, green on the branch
`scripts/sprint81_test.py` (unit, static, browser) runs inside the canary. Run against origin/main (`docs/sprint81-red-on-main.log`): 13 failing (the `today` module absent for sections A to E; the cadence line, the /today/ link, the morning stamp and the three compressed prices individually). On the branch: PASS. The cases: direction per sign, the dated page freezing byte for byte after the next morning's build, the gate seeing every answer sentence and every wire line (and dropping a wrong one), no cause word outside the reported items, a lifted read refused when it says "because" or states the wrong direction, structured data parsing with -04:00 offsets, canonical URLs, the archive, the BTT and $0.00009 prices, the 10 px tier gone, the column fit on three pages. `morning_test.py`, `color_truth_test.py` and `twins_gate_test.py` pass.

Canary on the branch: `LAYER 1 CANARY: PASS` (run twice: the first run failed K-1, "the news front does not open on the newest item", because a stale gitignored `site/publish` from my own local build was on disk; origin/main passes on a clean checkout and so did the branch once that directory was removed).

## Weights (375, bytes moved on a local build)
/today/ 181,406; /today/2026-10-14 181,411; home 194,192 (so /today/ is lighter); /pulse/prices 297,777; /flows 183,700.

## Screenshots for Jack
`shots/program8-8.1/`, 375 and 1440, light and dark: `today_-*` (/today/ as it builds from this morning's read), `today_2026_10_14-*` (the dated page), `home-*` (the new cadence line and the link), `pulse_prices-*` (the BTT row, $0.0₆3617 on today's data), `flows-*` (Whale Watch). The /today/ shots read "Morning read, 8:18 AM ET" beside "numbers as of 7:12 PM ET on Oct 14": the record was composed at 7:50 PM from this morning's read and the evening's numbers, because no stored record existed. A stored morning record, from tomorrow, will carry the morning's own numbers.

## Open, for Jack
1. Yes or no to merge (outside 6:30 to 8:15 PM ET), then: push the tip, merge, `git branch --contains` check, one build, read /today/ live and the count five minutes later.
2. Punch 6's meaning (Item 3).
3. A wire item on the page can carry a cause its source states ("sparking a crypto sell-off", CoinDesk, one source). It is shown with its source and under a heading and a line saying the desk does not say one caused the other. Say if you want single-source cause wording dropped.
4. The failed 7:17 PM wrap and the 7.3 live proof.
5. The live proof of the next morning's /today/ at about 8:20 AM ET is not read yet (hand to 8.2 if not read first).
