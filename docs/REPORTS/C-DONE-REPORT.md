# C-DONE: the running scorecard

Session opened Tuesday, November 24, 2026; working from Wednesday, November 25, 4:00 AM ET. One Claude Code cloud
session on gocheckmycrypto with gcm-newsroom attached (push access). `docs/RULES.md` body hash
`4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, verified at the opener. No trailer on any commit.
Updated after every merge. A point is green only with its evidence named; "open" means not yet scored. Jack's word of
November 25: continue with all fixes and items; the target is above 8 of 10, pushing toward 9.

## Scorecard

| # | Point | State | Evidence or reason |
|---|---|---|---|
| 1 | Fresh | green: three reads a day apart, with one part proven only on a local build | Merge 3. Production stamp `3d286ab`, read Nov 25 5:06 AM ET: /pulse "As of 4:39 AM ET on Nov 25, 2026.", every tile one instant, no stale banner, "several times a day" on 0 of 4 pages read. Reads 2 and 3 are due Nov 26 and 27, with the run logs. No section has been carried on production since the merge, so the older-section line is proven on a local build only (below). The 8:15 AM read of Nov 25 (run 45621734470): `market_pulse` 8 of 8 sections fresh, 0 of 9 CoinGecko calls answered 429; production stamp `b86cf1d`, built 13:20:01Z, the home and /pulse read "As of 8:19 AM ET on Nov 25, 2026." (read 8:23 AM and again 9:10 AM ET). **Read 2, Nov 26 8:45 AM ET, stamp `3a30285` (the morning read's build, 13:20:00Z):** /pulse "As of 8:19 AM ET on Nov 26, 2026.", nine tiles at one instant, no stale banner, "several times a day" nowhere; the stored board has all seven sections at 13:16:52Z and nothing carried; the evening Brief's run of Nov 25 made 2 CoinGecko calls, 0 refused. **Read 3, Nov 27 8:45 AM ET, stamp `706277c` (the morning read's build, 13:21:28Z):** /pulse "As of 8:21 AM ET on Nov 27, 2026.", nine tiles at one instant, no stale banner; the stored board has every section at 13:16:55Z, nothing carried. Run logs for the three days: 0 CoinGecko refusals in every ledger row (Nov 25 evening; Nov 26 breaking and evening, 2 calls each). "Several times a day" is on none of the three. **Not seen on production:** a carried section printing its own older time, because no section was carried in the three days; that line is proven on a local build only (below). |
| 2 | Published | 6 of 7 days | Evening Briefs on main: Nov 21 (watcher run 44971801349), Nov 22 (45081776201), Nov 23 (45286438006), Nov 24 (45507657192), Nov 25 (45719264052, every step green, published 6:16 PM ET, `65cb560`), Nov 26 (45909331425, published 6:15 PM ET, `3af829e`, 66,073 tokens, $0.0810). Nov 18 to 20: none (the canary lock N-1 fixed). Day 7 is Nov 27. Nov 26 carried one Brief: the breaking run at 9:39 AM ET (45839706683) wrote a movers record and no story. The morning read of Nov 27 published (`706277c`). Nov 25 carried one Brief and no breaking Afternoon Brief. The morning read of Nov 26 published at 8:18 AM ET (`3a30285`). No Edition gap issue is open: since Nov 25 12:00 UTC the only issue touched is the ops ledger. Gap issues #130 and #131 were closed by `close_edition_flags` after a Brief, not by hand. The stored-data class is closed by merge 4, and the Brief feed's own sentences about an AI story the wire carries by merge 14. Nov 23 and 24 each also carried an Afternoon Brief from a breaking run (named under Still open). |
| 3 | Readable in five minutes | green before the morning read; the morning state failed on production and is fixed in merge 16, production read pending | Merge 6. Production stamp `a0153db`, read Nov 25 7:05 AM ET at 375 by 812 (fold 755 px above the tab bar), before the morning read: tape 105 to 207, the day's line to 254, the Brief card to 353, the movers and standouts to 550, Today's first event title ending at 638 (`C-DONE-shots/home-375-production-a0153db.png`). **With the Morning Brief on the card it failed:** stamp `b86cf1d`, read 8:23 AM ET: the card ran 256 to 760 (504 px), the movers began at 774 and the next event's title ended at 1002 (`C-DONE-logs/morning-card-fold-production-b86cf1d.txt`, `C-DONE-shots/home-375-morning-before-production-b86cf1d.png`). Merge 16: the card opens on the read's one line; on a phone the long read is behind "The full read" (a checkbox and its label, no script, keyboard reachable); at 700 px and wider the read prints in full. Local build of the merged tree with the same morning read: card 256 to 510, movers 524 to 663, the next event's title ending at 752 (`morning-card-fold-after-local.txt`, `home-375-morning-after-local.png`, `-open.png`). **The margin is 3 px** with a two-line headline and a three-line one line; a longer headline puts the event's title under the fold again. A one-row layout for the toggle and the stamp was tried and dropped (it wraps at 360). The first production read of the morning state on the fixed card is Nov 26, after the 8:15 AM read. **The evening state failed on production the same night:** stamp `65cb560`, read Nov 25 7:26 PM ET at 375 by 812: the order is right (tape, the day's line, the Brief card, the movers, the next date) but the card ran 256 to 558 (a three-line headline, a four-line line, a three-line "Written from..." line), the movers 572 to 799 (four in the top 20) and the next event's title ended at 887, 132 px under the fold (`C-DONE-logs/fold-production-65cb560-evening.txt`, `C-DONE-shots/home-375-evening-production-65cb560.png`). On Nov 24's data the same state measured 734. **So the fit depends on the day:** the headline's length, the source line's length and how many of the top 20 moved. No rule in the stylesheet can hold all four above 755 px on a busy day without hiding an answer (the movers past the second, or the card's sentence); that is a change to what the phone home shows, so it is Jack's (below, item 8). **The morning state on the fixed card, production stamp `3a30285`, Nov 26 8:45 AM ET, a day Bitcoin was up 3.69%:** the card works as built (the one line, then "The full read", which opens the long read on a tap; checked on production) and stands 256 to 555 with a three-line headline; the movers ran 569 to 967 because the standouts line listed 34 coins; the next event's title ended at 1055. Merge 20 names the six biggest standouts and counts the rest: on stamp `54d9d9d` the movers end at 796 and the next event's title at 885 (`C-DONE-logs/fold-production-54d9d9d-morning.txt`, `C-DONE-shots/home-375-morning-production-54d9d9d.png`). 130 px under the fold on a big day. Nov 27 8:45 AM ET, stamp `706277c`, a quieter morning: the movers end at 742 and the next event's title at 857 (`C-DONE-logs/fold-production-706277c-morning.txt`). Red until ruled. |
| 4 | Clean | green on the count of record (crawl 3), but for stored copy and the separator question | Crawl 1 of stamp `3d286ab` and crawl 2 of stamp `22f4c70` (both below; crawl 2 is the count of record so far, `C-DONE-logs/crawl-production-22f4c70.txt`). Fixes in merges 7, 9, 11, 13, 15 and 17. Crawl 2 found what merge 7 missed: every story's Sources list printed a headline made from the link's address, lowercased and cut with three dots, on about 570 story pages; merge 17 prints the outlet's name. **Crawl 3, the count of record, stamp `54d9d9d` (carries merges 1 to 20), Nov 26 9:05 AM ET, 919 pages, 933 link targets (`C-DONE-logs/crawl-production-54d9d9d.txt`):** NaN, null, "0 pieces", em dash, en dash, every build-note phrase, TODO, placeholder, "Stale data", the site's own UTC stamps: 0 each; "undefined" 5 and "None" 27, all English prose; text cut with three dots after a letter: 1 (a story's summary on /archive, cut at a word; was 159); empty sections: 1 hidden holder; missing title, description or canonical: 0; duplicate titles: 1 group (/today/ and its dated twin; was 4); internal links that do not answer: 0 (the 2 counted are script strings the crawler read as links). What remains is stored story text ("UTC" inside 36 stories' own sentences, 13 British spellings in names and one story) and the separator dot on every page (Jack's item 2). Read on production stamp `65cb560`, Nov 25 7:30 PM ET: the story page that printed the clipped headline lists "Decrypt, The Defiant, Bitcoin Magazine, CoinDesk"; the three lanes' second pages are titled "..., page 2"; /today/ reads one short sentence per fact. |
| 5 | Whole | green but for one page, fixed in merge 11 | Stamp `a0153db`: all 368 sitemap pages at 375: tab bar present with five tabs on 368 of 368, each tab's target answers; horizontal overflow on 1 page (273 px, a long address in /articles/senate-fails-clarity-act-cloture-vote..., fixed in merge 11). Watchlist from a fresh device: hidden when empty; SOL pinned on /coins/sol; the home shows "SOL $67.74 -3.90%"; still there after a reload. Titles, descriptions and canonicals on 915 of 915 pages; /market-pulse 301 to /pulse; 368 sitemap URLs all 200; 12 dead internal links fixed in merge 7. |
| 6 | Fast | green | Lighthouse 13.6.0 mobile on production stamp `a0153db`: home performance 97, accessibility 100; Board 100 and 100; a Brief 100 and 100 (`C-DONE-logs/lighthouse-production-a0153db.txt`). |
| 7 | Taught | green | Merge 9. All twelve explainers read in full on Nov 25; 23 lines corrected (list in the merge's commit); each prints "Last reviewed November 25, 2026" from its own record; every tile's definition is on /learn and each Board reading's definition links its full explainer; Learn is in the nav. Production stamp `22f4c70`, read 7:58 AM ET: /learn/bitcoin-posture, /learn/leverage, /cold-storage and /crypto-tax print "Last reviewed November 25, 2026"; the live cards read "as of 7:51 AM ET on Nov 25, CoinGecko" and "..., OKX"; no "site build", no "last build", no "line 8z". |
| 8 | Quiet | built, reads pending | Run sweep Nov 18 to Nov 25 09:26 UTC: 287 runs, 63 failures, all 63 the offline canary's stored-wire case, the last at 2026-11-22T01:00:48Z; 0 since. Health gate: 3 full runs (Nov 22, 23, 24), all "Healthy". Ignore rule: merge 2, proven (merges 2 and 4 canceled by Netlify). Publish-time gate: merge 4. Gap finding a warning, the week's spend, the gate's prices line: merge 5. Spend Nov 18 to 24: 11 runs, 581,208 tokens, $0.8590. The push-time canary on CI passed on every merge of this session (runs 458 to 465). **The first publishing run through the new gate:** the 8:15 AM read, run 45621734470 (#123) on head `28fe518`: the canary step ran through `canary_gate.py` and printed LAYER 1 CANARY: PASS at 13:17:02Z; the read was written (1,055 tokens, $0.0019) and pushed as `b86cf1d`; Netlify built it. Merging onto that commit then turned the canary red on two cases, both from the day's stored data (the Brief feed's sentence about an AI story on the wire; this session's own fold-list case, which did not allow the day's line); both were fixed at the cause in merge 14 before anything was merged over them. The evening Brief of Nov 25 (run 45719264052) went through the same gate on `620cce8`: the canary step green in 2 minutes 5 seconds, every step that ran green (three failure-only steps skipped), 133,993 tokens, $0.1565 (the editor stage $0.1406; Nov 24's Brief was $0.0936), 0 of 2 CoinGecko calls refused; the push-time canary on the same commit is CI run 473, success. A second dispatch at 23:40 UTC (run 573) concluded success and pushed nothing. The health gate ran twice on Nov 25, at 3:23 PM and 4:35 PM ET (runs 7 and 8, both success): late again by eight hours and more. Nov 26 and the morning of Nov 27: the health gate ran at 2:59 PM and 4:23 PM ET on Nov 26 (runs 9 and 10, both success, both late); no "Desk run failed", "Edition gap" or "Missed edition" issue was opened or touched since Nov 25 12:00 UTC (the two issues touched are the ops ledger and the advisory calendar-coverage flag #124); every ledger row since the publish-time gate merged reads "ran". The week by `ops_ledger.py --week` (ET days Nov 20 to 26): 16 runs, 952,044 tokens, $1.3712 (`C-DONE-logs/week-spend-2026-11-20-to-26.txt`). Open: the seven days end Dec 1, and the health gate's lateness (Jack's, below). |
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
| 13 | crypto | `28fe518` | `6dea1ea` | `22f4c70` | Points 3 and 4: /today/'s answer one short sentence per fact; no story line where there is no story. | Canary exit 0 on tree `d54cba1`. `[skip netlify]`. Built by the 8:15 AM read's push, stamp `b86cf1d`. |
| 14 | crypto | `c517eb8` | `85ae244` | `b86cf1d` | Points 2 and 8: the morning's stored data turned main's gate red twice; the Brief feed may report an AI story the wire carries (three shared subject words, never a disclosure); the fold list allows the day's line. Tests and scripts only. | Canary exit 0. Pushed 13:33:45Z; canceled by Netlify (no build). |
| 15 | crypto | `3a19921` | `9e3778d` | `c517eb8` | Point 9: a lane's later pages carry their page number in the title; the crawl of record filed. | Canary exit 0 on the merged tree. `[skip netlify]`. |
| 16 | crypto | `e9ec721` | `68d5fed` | `3a19921` | Point 3: the Morning Brief card opens on its one line; on a phone the long read is behind "The full read". | Canary exit 0 (`morning-card-gate.log`); the merged tree equals the gated tree. `[skip netlify]`. |
| 17 | crypto | `74bab9d` | `9bed8c6` | `e9ec721` | Point 4: a story's Sources list names the outlet; no headline made from a link's address. | Canary exit 0 (`sources-gate.log`); the merged tree equals the gated tree. `[skip netlify]`. |
| 18 | crypto | `620cce8` | `5f6968d` | `74bab9d` | The scorecard after seventeen merges (documents only). | The canary passed on `74bab9d`'s tree minutes before and this merge changes one document; the push-time canary on CI is run 473. `[skip netlify]`. |
| 19 | crypto | `834dc17` | `f9f47e7` | `356f7f5` | The scorecard for the evening of Nov 25 (documents only). | Canary exit 0 (`docs-5-gate.log`). `[skip netlify]`. |
| 20 | crypto | `54d9d9d` | `67ebc26` | `3a30285` | Points 3 and 4: on a big day the home names the six biggest standouts and counts the rest, linked to the Big movers page. | Canary exit 0 (`standouts-gate.log`); the merged tree equals the gated tree. **Built**, stamp `54d9d9d`, 13:56:57Z, the first of Nov 26's three merge builds. IndexNow by hand for the home, response 200. |
| 21 | crypto | `b3306fd` | `7c25317` | `54d9d9d` | The scorecard for the morning of Nov 26, crawl 3 (documents only). | Canary exit 0 (`docs-6-gate.log`). `[skip netlify]`. |

Every push verified by hash (U-8): local equals origin, 0 ahead, each time.

**One build over the allowance on November 25, the desk's error.** Merges 7 to 11 carried `[skip netlify]` to ride the
8:15 AM read's build. Merge 12, documents only, was pushed without the marker; Netlify's ignore rule compares against the
last BUILT commit (`a0153db`), that diff held the five skipped merges' site files, and it built, correctly. So the day
has four merge builds (1, 3, 6, 12) against a share of three, and with the morning read and the evening Brief it ends at
six of five. The same trap as October 11 (`0c47b73`). From merge 13 on, every merge pushed while a skipped site commit
is unbuilt carries the marker. Count of record (Worker `/counts/today`, Nov 25, read 7:57 AM ET): production ready 4,
canceled 2; read again 8:59 AM ET: ready 5 (merges 1, 3, 6, 12 and the morning read), canceled 3 (merges 2, 4, 14).
Merges 13 and 15 to 17 carried the marker and made no deploy. Merges 15 to 18 rode the evening
Brief's build, the day's sixth: stamp `65cb560`, built 23:18:12Z. Count of record for Nov 25, final, read 7:25 PM ET:
ready 6, canceled 3. Six of five, the one overrun named above. Nov 26, final (Worker `/counts/2026-11-26`): ready 4 (the morning read,
merge 20, the breaking run, the evening Brief), inside the allowance of five. Nov 27, read 8:45 AM ET: ready 1.

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
- Merge 16, the toggle's rules inside the marked C-DONE block of both files: `site/assets/system.css`
  `01dc4981649abd865bb96b274167ba1221c0171d380c2e2b3f8ef677dafee90c` to
  `e8bbe51babf0b45a9e9ab689e65d9ae001462c3b42de2c6ea59dd3ad7f4068c9`; `fixtures/sprint95b/system.95.css`
  `9d91988d4450d480c2f5d021446d88567fc52cfe5c6d7a3c2f77388e5437e076` to
  `6742b36bcf0134742f4e90b4edbdfb8b9dff96df14a69dc4e3bd1d063906c7ff`.

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
| 12 read well (/today/'s sentences, no story line without a story) | 5 | red (`read-well-red-on-main.log`) | 5 |
| 10, lane page titles | 2 more | 2 FAIL | 1 |
| 13 live data (the Brief feed and the wire; the fold list) | 10 | the canary itself, 2 problems on `b86cf1d` | 8 |
| 14 the Morning Brief on a phone | 7 | 4 FAIL | 11 (two missed on the first pass, the desktop cases tightened, rerun caught all) |
| 15 the Sources list | 6 | 5 FAIL | 9 |
| 16 the standouts on a big day | 8 | 4 FAIL | 10, and one against the rewritten home canary check |
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

### Crawl 3 is the count of record (row 4 above); crawl 2 is kept for the comparison

### Crawl 2: stamp `22f4c70` (carries merges 1 to 12), 913 HTML pages, 929 link targets

`C-DONE-logs/crawl-production-22f4c70.txt`. Against the table above:

- NaN, null, "0 pieces", em dash, en dash, build notes ("the last build" and seven other phrases), TODO, placeholder,
  "Stale data": 0 each. "undefined" 5 and "None" 26, all English prose.
- The site's own UTC stamps: 0 (was 88 Edition pages). "UTC" remains on 36 pages inside reported text (an event's own
  time in a stored story). ISO timestamps: only inside schema.org data, where they belong.
- Title, description, one canonical: 913 of 913. Internal links: no real 404. The 4 non-200 targets are 2 fetches the
  connection dropped (/pulse/prices and /method, both answer 200 when read again, 9:10 AM ET) and 2 script strings the crawler read as
  links.
- Empty section or card: 1, the hidden pinned-coins holder on /pulse (was 24).
- Duplicate titles: 4 groups (was 7). Three were a lane's later pages, fixed in merge 15; /today/ and its dated twin
  remain (still open).
- A bare $0: the sub-cent prices are real prices; the stored-copy lines ("shows $0 million so far") are stored records.
- **Text cut with three dots: 159 nodes on 150 pages.** One on /archive is a story's summary cut at a word. The rest
  were the Sources list under every story ("CoinDesk: u s sec maps out crypto custody in new proposal that furthers
  its digital..."), which merge 7 had left standing one element above the line it fixed. Fixed in merge 17: local
  build, 585 story pages with a Sources list, 0 with a label made from an address.
- British spelling: 13, all in stored story text: proper names ("Cyber Crime Coordination Centre", "Astana
  International Financial Centre") and "catalogued" in one story. Stored copy, not rewritten.
- The middle dot as the separator: every page, 15,552 (Jack's, below).
- A story older than 48 hours presented as today's: 0. Counted on stamp `b86cf1d` at 9:10 AM ET: the home links one
  story (the Week Ahead of Nov 23, under Storylines, as the week's piece) and /today/ links none.

## Production reads

| Read at (ET, Nov 25) | Stamp | What was read |
|---|---|---|
| 4:20 AM | `4750aca`, built Nov 24 23:18:18Z | `/stamp.txt` only. |
| 4:24 AM | `96ca8aa`, built 09:20:14Z | Served `system.css` carries merge 1's rule. IndexNow by hand: 1 URL, response 200. |
| 5:06 AM | `3d286ab`, built 09:42:23Z | Point 1, read 1. IndexNow by hand: 2 URLs, response 200. |
| 5:40 AM to 6:00 AM | `3d286ab` (start and end) | The crawl. |
| 6:55 AM | `a0153db`, built 10:41:44Z | `/stamp.txt` and the count of record. |
| 7:05 AM | `a0153db` | Point 3 at 375 before the morning read; the 368-page sweep at 375; the watchlist from a fresh device; Lighthouse. |
| 7:58 AM | `22f4c70`, built 12:54:11Z | Points 7 and 9 (rows above); crawl 2. |
| Nov 27, 8:45 AM | `706277c`, built 13:21:28Z | Point 1 read 3; point 3 at 375 (857 px); the Nov 26 Evening Brief and the count of record. |
| Nov 26, 8:45 AM | `3a30285`, built 13:20:00Z | Point 1 read 2; point 3, the morning state on the fixed card (a big day: 1055 px). |
| Nov 26, 9:00 AM | `54d9d9d`, built 13:56:57Z | Merge 20 on production: the standouts line reads six names and "31 more" linked to /pulse/movers; the next event's title at 885; the toggle tapped; crawl 3. |
| 7:26 PM | `65cb560`, built 23:18:12Z | The evening Brief's build, carrying merges 13 to 18: the home at 375 and 1440 (point 3, evening state: red by 132 px), the Sources list, the lane page titles, /today/. IndexNow by hand: 371 URLs from the production sitemap in three batches (172 pages, 99 stories and why pages, 100 coin pages), response 200 each (`C-DONE-logs/indexnow-production-65cb560.txt`). |
| 8:23 AM | `b86cf1d`, built 13:20:01Z | The morning read's build: point 3 with the Morning Brief on the card (failed, fixed in merge 16); the live stamp reads "price live, 8:42 AM ET, range and chart as of 8:19 AM ET on Nov 25" in two lines of the three reserved. |

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
6. On a phone the morning read's long paragraph is behind "The full read"; the card shows the one line. Reason: the
   fold. Nothing is removed from the page.
7. A story's Sources list prints the outlet's name, not a headline made from the link's address. Reason: point 4.
8. The home names the six biggest standouts of the top 100 and counts the rest with a link; an older check that held
   every standout on the home was brought to it. Reason: 34 names was eleven lines on a phone. The number is one
   constant, `home.HOME_STANDOUTS`.
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
2. Closed as read, no change: the janitor closes any auto-alarm older than seven days by design, and a live condition
   opens a fresh issue (it did, nine minutes later, #129). Run 565's closing comment named the wrong slot; the flag it
   closed had been answered by that evening's Brief. Neither stops a run or a page.
3. /today/ and its dated twin share a title on the day (the lanes' later pages were fixed in merge 15).
4. On November 23 and 24 a breaking run also published an Afternoon Brief, so those days carry two Briefs. Not touched
   (the Brief and the watcher's cage are not this session's to change); named because the ruling says one a day.

Closed since the last scorecard: both canary warnings that looked real are the canary's own negative tests ("a broken
record draws no section and raises nothing"; "a tile that disagrees with its rows is caught"), so all 18 warnings of the
Nov 24 run are fixtures and negative tests. The "no 24h figure" line on the All crypto tile is Sprint A's ruled wording
for a withheld figure and stays.


## Jack's

8. **Point 3 on a busy day.** At 375 by 812 the four answers are in order on every build read, and all four clear the
   fold only on a light day (638 px before the morning read, 752 px in the morning state on a local build, 887 px
   tonight). Three ways to rule it: (a) the point is the order, and the next date may sit a short scroll down on a busy
   day; (b) on a phone the home shows the top two movers and the card's headline, with the rest one tap away (the desk
   can build it in one item, and it hides answers, which is why it was not done unasked); (c) item 7's third stamp line,
   which gives back 18 px and does not close a 132 px gap by itself. The desk recommends (a) with (c).
7. **The live stamp's third line** (point 3's margin). Under the tape the stamp keeps three lines below 521 px (J-11
   rule 1, ruled October 20, so the live price landing moves nothing). At 375 the longest text it carries ("price live,
   10:42 AM ET, range and chart as of 10:19 AM ET on Nov 25") takes two, so 18 px above the fold are blank and point 3
   clears the fold by 3 px in the morning state. Two lines at 375 and wider, three under 360, would make that 21 px.
   It is a ruled rule and a byte pin, so it was left; say the word and it is one line of CSS and its test.

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
