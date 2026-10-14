# Program 8, Sprint 8.1: the daily answer. Report (14 October 2026)

**Status: built and pushed on `sprint-8-1` (tip `c8289b4`). NOT merged: it waits for Jack's yes on the screenshots.**

## Start
- RULES hash: `4179b2ac...b3568d`, equal to the brief's. origin/main at start: `c86fb1f` (contains 7.3's merge `5bb4df7`).
- Program 8 committed verbatim as `docs/PROGRAM-8-2026-10-14.md`, its own documents-only commit (`c178cc8`). No trailers on any commit.
- 7.3 ledger proof: NOT YET READ. The 14 Oct 7:08 PM ET Edition had not run (shell time 4:2x PM ET). Read `twins_drops`, `twins_unparsed`, `twins_log` after it runs.

## What was built
- **Item 0, `today.py`.** `/today/` and `/today/YYYY-MM-DD`. Records `site/data/today/DATE.json` are written by the morning run and the Edition run (two new workflow steps, no model call, fail-open); the build only renders them. A dated page freezes when its evening record exists. Sitemap: `/today/` with the newest record's real lastmod, each dated page with its own. Home: "Why crypto moved today →" under the Brief card. First real record: 14 Oct morning (8:18 AM read, snapshot 8:17 AM).
- **Item 1.** Home "Moving the market" now prints "Re-ranked <morning time>; first ranked <Edition time>". `wire.py --refresh` already ran in the morning; the page just kept printing `ranked_et`.
- **Item 2.** `$0.0000003682` prints `$0.0₆3682`; label "0.0000003682 dollars"; the 10 px tier removed. Real Top 100 has PEPE and SHIB under $0.0001 today, so the row is proved on real data, not only the fixture.
- **Cadence line** changed in `NEWS_CADENCE_LINE` and its pin in `verify_pipeline.py`. (Program 5's historical doc still quotes the old line; left as history.)

## Things Jack should know
1. **Whale Watch (item 3): the stated defect does not reproduce.** At 1440 the tables are 543 and 471 px inside their grid columns (545 and 473), nothing overflows, and at 375 the exchange table scrolls inside its own box. 7.3's open item was that they are *narrower* than the 1080 px column (two-column layout), not wider. I changed nothing. The test (`scripts/sprint81_browser.mjs`) passes and goes red on a planted overflow (`--plant`). If "full width" is wanted, that is a layout ruling: say which.
2. **The twins gate does not read a coin's 24-hour change.** "Bitcoin is up 3%" passes it whatever the day did. The page's own numbers come from the snapshot, and lifted read sentences get an extra check (`today.day_claim_wrong`). Worth a decision whether the gate itself should learn it.
3. **Ambiguity in the zero count:** the brief's example `0.0000003682 -> $0.0₆3682` has the subscript equal to the total zeros after the point (6); its prose says "after 0.0" (that would be 5). I followed the example.
4. **The answer paragraph** is always the fixed template with numbers (the read rarely quotes a change, by the 7.1 law); a read sentence replaces it only if it itself states Bitcoin's move, the amount and the window. The read's sentences that pass appear as "From the morning read."
5. **Mixed day in the real data:** this morning's record says Bitcoin +0.75% and total market cap -2.98% (the Board's own figure), so the headline reads "up" over a down cap. Faithful to the snapshot; the cap figure may deserve a look.
6. Records are written at the workflow's snapshot time, so /today/ can be a few minutes older than the home tape (each figure carries its stamp).
7. The dated page keeps the morning's content if no evening record ever arrives; it never freezes on a breaking run (evening write needs an Edition published 6 PM to 5 AM ET).

## Tests (red, then green)
- `scripts/sprint81_test.py`: before the change (stash) 9 failures; after, 0. Items 1, 2, cadence.
- `scripts/today_test.py`: planted faults each fail it: `--plant sign|gate|because|freeze|order` (exit 1 each); clean run 0 failures. Covers the three fixture days, boundaries at plus or minus 0.5, page order, color truth, the gate on every sentence, no causal wording, freeze after two later days, structured data (ET offset -04:00 and -05:00), sitemap lastmod, home link, 7-day archive.
- `scripts/sprint81_browser.mjs`: Whale Watch and /today/ at 375 and 1440; no sideways scroll, no text under 12 px. Canary: `LAYER 1 CANARY: PASS` (exit 0) on the branch; the new `_sprint81_canary` runs both Python tests.

## Fixture days
-2.31% -> "Why is crypto down today? Wednesday, October 14, 2026"; +1.84% -> "...up today?..."; +0.31% -> "Crypto today: flat. Wednesday, October 14, 2026".

## Weights (375, no compression, local server)
/today/ 189,221 bytes against the home page's 201,346 (fonts dominate both). HTML: 21.5 KB against 33.6 KB.

## Screenshots (for Jack, light and dark, 375 and 1440)
`/tmp/claude-0/shots81/`: `today-*`, `today-dated-*`, `home-*`, `top100-*` (full page; the BTT-class rows are PEPE and SHIB), `whale-watch-*`.

## Not done yet (waits for Jack's yes)
Merge (outside 6:30 to 8:15 PM ET), production reads, count five minutes after the push, the live /today/ proof at about 8:20 AM ET tomorrow, the 7.3 ledger read, and the close.
