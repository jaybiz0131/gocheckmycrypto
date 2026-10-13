# Program 6, Sprint 6.5: honest averages, the Top 100 polish, the lighter stylesheet

Branch `sprint-6-5`, tip `e0872b4`. **MERGED Tuesday 13 October 2026, merge `23c33e5` (real merge commit, pushed 3:57:40 PM ET).** Built Tuesday 13 October 2026, 3:18 to 3:40 PM ET, on Jack's 3:18 PM ET ruling to start today.

## Start
- **RULES hash:** `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, matches.
- **origin/main at the start:** `ae37bc21b1ef9773899698a7ef4d04f28fe65984` (contains 6.4's merge `60ac24e` and its close).

## The morning edition's live proof (7.2 item 5): OPEN
To be read after the Oct 14 8:15 AM ET run. At 2:42 PM ET on Oct 13 production still read "THE BRIEF · SUNDAY EVENING" (build `60ac24e`). Jack's note: the Worker `gcm-slot-trigger` was deployed at 11:52 AM ET Oct 13 (version `d3d4f43d`). Tokens, dollars and fallback status come from the ledger after that run; nothing is claimed here.

## Builds
Count of record last read at 1:50 PM ET Oct 13: 3 ready, 1 canceled, the 7:08 PM Edition the 4th. This sprint's merge is the day's **4th ready build** by the documents (3 ready + this merge, 1 canceled), so the 7:08 PM Edition is the fifth and the morning's run, if it builds, is on Oct 14's count. **The count was NOT read after the push**: the Worker's `/counts/today` has no URL in the repository's documents and the site's own `/counts/today` answers 404, so this session cannot read it (the same blocker 6.4 reported). Read it from the Worker and correct this line. Production built `23c33e5` between 3:57:44 and 4:03:55 PM ET (about 6 minutes after the push, from the stamp). Nothing else was pushed to `main` today by this sprint except this close (documents only, ignored by the build).

## Averages (item 0)
- One 365-day request serves 1M and 1Y; the 565 request and its fallback are gone.
- **Real starts, BTC and ETH alike** (366 daily points, 14 Oct 2025 to 13 Oct 2026): the 50-day average starts **Dec 2, 2025** (point 50), the 200-day average starts **May 1, 2026** (point 200). The 1Y caption reads "50-day average from Dec 2 (needs 50 days of history) · 200-day average from May 1 (needs 200 days of history)". It shows on 1Y only.
- Fixtures: real 365-day recordings of bitcoin, ethereum and aptos, 3:18, 3:20 and 3:21 PM ET Oct 13 (CoinGecko answered 200 for BTC, then 429 twice, then 200 after a wait). The `-565` files and every synthetic day are gone; the README says so.
- Honest note on the "red against 6.4's code" ask: with a real 365-day fixture, 6.4's code already drew the right number of points, on the right days, with no long segment (its 365 fallback was sound). What 6.4's code fails is the request (it asks for 565 days, then 365: `[7,565,365]`) and the missing start-date caption.

## Tests, red then green
| Test | Red | Green |
|---|---|---|
| chart-averages-daily, both coins: one 365-day request and none above; exactly N-period+1 points (317 and 167 of 366); first point on day 50 and day 200; one run, no segment over 2 days; caption on 1Y only | against 6.4's tree: 4 of 10 failed (request `[7,565,365]`, no caption, for BTC and ETH) | 13 of 13 |
| the caption is muted, 12 px, Plex Mono | 17 px, ink colour (a more specific rule won) | fixed with `body .cc-start` |
| top100-rows: 13+ char price leaves 12 px; steps 12/11/10 px; no word broken; ellipsis plus full name in title and label | 5 of 7 failed on 6.4's tree: fixture gap 7.2 px (the production case), and six mid-word breaks (Hyperliquid, PancakeSwap, Superintelligence, (BinanceLife), (ex-MATIC), the synthetic long word) | 7 of 7, all 100 real rows plus the two labeled synthetic rows |
| CSS comments: published has no `/*`, source keeps them | 2 failures against the 6.4 tree | pass |
| masthead (3 clocks, a day after the newest story) | mutated to the UTC day: fails at 10:30 PM ET; mutated one day behind: fails | pass, no code change |
Browser suite: 43 of 43. Canary on the branch tree: `LAYER 1 CANARY: PASS`.

## Top 100 rows (item 1)
- 13+ characters: 10 px; 11 to 12: 11 px; the rest 12 px. Worst gap now at least 12 px on all 100 real rows plus the $0.0000003682 fixture.
- Names wrap only at a space; a word too wide ends in an ellipsis; the row link carries `title` and `aria-label` ("Name (SYM)"). To make Hyperliquid and PancakeSwap fit in full, the coin cell's padding is trimmed and the "·" before the name (which sat alone on a line) is hidden below 768; only "Superintelligence" and "(BinanceLife)" ellipsize.
- Ticker stays on its own line, above the name as it was (the brief said "under"; the layout has not changed).

## Weights at 375 (uncompressed bytes, local, chart data blocked)
| Page | Before | After | Change |
|---|---|---|---|
| / | 231,398 | 191,075 | -17.4% |
| /coins/btc | 236,150 | 196,288 | -16.9% |
| /pulse/prices | 325,491 | 296,110 | -9.0% |
| one article | 219,775 | 179,452 | -18.3% |
Comments stripped from `site.css` (110,427 to 74,967 B) and `system.css` (37,312 to 32,449 B) at publish; the source keeps them. Against the pre-6.4 BTC baseline (216,638) the page is **-9.4%**, so the 10 percent rule (ceiling 238,302) has **42,014 bytes** of margin, 19.4 points; 6.4 had 0.1 points.

## Masthead (item 3)
Crypto already printed the build clock's ET day (Sprint 7.1, `masthead()`), and no script rewrites it (the home script only sets the clock time on the "UPDATED" stamp). It had no test. Added `scripts/masthead_test.py` (in the canary): 12:35 PM, 10:30 PM and 12:05 AM ET a day after the newest story, shell and article pages, the article's own dateline kept, and the built tree. No code change.

## Contact sheets
`shots/program6-6.5/`: `contact-btc-averages.jpg`, `contact-top100-first.jpg`, `contact-top100-rows.jpg`. Before beside after, 375, light and dark. Data: BTC from the 3:18 PM ET recording; the Top 100 rows are production's own recorded rows (stamp `60ac24e`), BTT's $0.0000003682 is the real row. "Before" is 6.4's code and CSS on the same real data.

## Jack's yes, merge, production reads, counts
- **Jack's yes:** 3:55 PM ET Oct 13 (before the 6:00 PM cutoff), merge of tip `e0872b4`.
- **Merge:** `23c33e5` on `main`, from `ae37bc2`. `git branch --contains` confirmed `cb5469b` and `e0872b4` were on `origin/sprint-6-5`, and `merge-base --is-ancestor` confirmed both are in `23c33e5`. Tip pushed before the merge (pushed earlier at 3:40 PM). Canary on the merged tree: `LAYER 1 CANARY: PASS` (3:57 PM). Pushed 3:57:40 PM ET, 2 h 32 min before the 6:30 PM bar.
- **Production by stamp** (`/` stamp `23c33e5` from 4:03:55 PM ET; the previous read was `60ac24e` until 4:03:34), read 4:04 PM ET at 375 and 1440: `/`, `/coins/btc`, `/coins/eth`, `/pulse/prices` all stamp `23c33e5`, no sideways overflow at either width, masthead "TUE · OCT 13, 2026". Published `site.css` (74,982 B) and `system.css` (32,455 B) carry no `/*`.
- **BTC 1Y caption, live, both widths:** "50-day average from Dec 2 (needs 50 days of history) · 200-day average from May 1 (needs 200 days of history)", 12 px, two average lines drawn, and the page made exactly one history request, `days=365`.
- **The BTT row on the live Top 100: NOT READABLE.** BTT left the Top 100 at the 3:57 PM ET refresh (the live page, "As of 3:57 PM ET", has 100 rows and no BTT). The 13-character case was proved before the merge on production's own recorded BTT row (contact sheet) and on the labeled fixture. Live at 375, all 100 rows: longest prices are SHIB and PEPE (12 characters, 11 px), the smallest gap between price and 24h pill is **13.8 px**; at 1440 the smallest gap is 43.8 px and the prices are 13.5 px. Names at 375: Hyperliquid whole; only "(BinanceLife)" and "Superintelligence" ellipsize, and the rows carry `aria-label`/`title`. The 10 px tier is in the served CSS (`pn-xlong`) but no live row is 13 characters long right now.
- **Count five minutes after the push:** not readable from here (see Builds).

## Still open
- The morning edition's live proof (7.2 item 5): to be read after the Oct 14 8:15 AM ET run.
- The count of record for Oct 13 after this merge: read from the Worker.

Closed Tuesday 13 October 2026, 4:08 PM ET.
