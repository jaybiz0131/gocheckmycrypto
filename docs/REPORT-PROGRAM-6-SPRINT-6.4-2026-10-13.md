# Report: Program 6, Sprint 6.4, the coin pages and the Top 100 (13 October 2026)

**Status: MERGED 13 October 2026, 1:43:37 PM EDT, merge `60ac24e`. Two open items from the live reads, both below under "Merge, production reads, count": the live API refuses the 565-day request, and one Top 100 row has a 7.2 px gap.** Everything below that needs a yes or a production read says so.

## Start
- RULES body sha256 `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`: **matched** (`tail -n +11 docs/RULES.md | sha256sum`).
- origin/main at start: `135138e`, which contains Sprint 7.2's merge `c823b31`.
- Shell date at start: Tue Oct 13 2026, 11:58 AM EDT.
- Branch: `claude/sweet-wright-s8j2we` (the brief says `coin-pages`; this session is bound to the former).
- Rulings recorded in `docs/HANDOFF.md` section 11.

## Builds
- Count of record: the Worker's `/counts/today` could not be read from this session (no URL in the repository's documents, no network route). From the documents: 1 ready at 6:19:47 AM (the 7.2 merge build). Still to come today: the noon fallback refresh (it fires only if no morning run happened; none had) and the 7:08 PM Edition. Worst case at merge time: 3 used, this sprint's merge is the 4th, inside the five.
- Before this sprint: 1 ready (documents). After: unchanged, nothing was pushed to main. Not read live; **the merge session must read `/counts/today` first.**

## Data sources and point spacing
| Window | Request | Points | Spacing |
|---|---|---|---|
| 1D | CoinGecko `market_chart?days=1` | 289 | 5 minutes, the finest the source gives |
| 7D | `days=7` | 169 | hourly |
| 1M | the 365-day request, last 30 days | 31 | daily |
| 1Y | `days=365` | 366 | daily |
Volume bars are drawn on 1M and 1Y only, where each is a day's volume; on 1D and 7D the source's volume is a trailing 24-hour figure at every point, so none are drawn. The 50-day and 200-day lines are averages of daily closes from the 366-day series, drawn on 1M and 1Y only. The chosen window lives in the script's closure: no storage, no cookie (reload returns to 7D).

## What was built
- Chart: 1D/7D/1M/1Y tabs (44 px), Program 7 line (3 px, glow, area, glowing high and low with mono labels, halo on the last point) colored by the window's own change, the printed change beside it from the same series; dashed averages (smooth, named in the right gutter, 1M and 1Y only); muted volume bars on their own scale, up/down by close (1M and 1Y only); price labels right in Plex Mono 12 px; four date labels at 375; crosshair readout (price, date, volume) for touch, hover and keyboard (arrows, Shift, Home, End, Esc) that stays inside the box; draws once, whole at once under reduced motion. Built as one shared file.
- Coin page order under the chart: readings grid (seven tiles via `tile.render`; 200-day distance and RSI only for the Board's seven coins, absent elsewhere), Chart Master card (coin's own sentences when the read names it; levels otherwise; dated; says how old past one day), the coin's wire items newest first with sources (published stories follow as "Checked by the desk"), cold-storage card (same copy as the Board's, shared constants), unlock line (only where `data/calendar/unlocks.json` has a future dated entry with source and read date), then the supply rows the page already had.
- Top 100: search (no network), "No coin matches" with a clear button, plain 7-day line per row colored by its own seven days (no glow), columns at 375 rank/coin/price/24h/line, cap and volume at 768+, whole row is the link (stretched anchor), and the sort buttons now work (they had no script).

## Tests, red then green
Red on the before tree (`/tmp` copy of origin/main's build): 19 of 20 browser checks failed (selectors absent); the sideways-scroll check passed there, so it was proven red by a plant. Mutation plants on the new tree, each went red: chart direction fixed to up (own-window, two checks); averages on every window; a 900 px element planted on `/coins/xrp` (`+547px`); the search match broken (both search checks); sparkline direction fixed (two unit checks).
Green: 20 of 20 browser checks (101 pages at 375 without sideways scroll), unit and static layers pass, and `python3 verify_pipeline.py canary` prints `LAYER 1 CANARY: PASS` (exit 0) with the new `_coin_pages_canary` inside it. The K-7 and data-contract canaries were rewritten to the new markup (same invariants: own history fetch, ranges, crosshair, averages from the series shown, price from the snapshot, high never below price, fallback says it is the fallback).
**Canary on the merged tree is still to run after the merge.**

## Weights at 375 (uncompressed bytes, local, chart data blocked)
| Page | Before | After | Change |
|---|---|---|---|
| /coins/btc | 216,638 | 237,428 | +9.6% (limit 10%) |
| /coins/eth | 216,727 | 237,561 | +9.6% |
| /coins/apt | 215,014 | 235,270 | +9.4% |
| /pulse/prices | 403,800 | 325,382 | -19.4% (limit +15%; no lazy-draw needed) |
To get inside 10%: the script's comments and indentation are stripped at publish (-4.3 KB) and the dead K-7 and stat-grid CSS was removed (-1.7 KB). The BTC margin is thin. Chart data is fetched on top: 7D 17 KB, 1D 30 KB, 1Y/1M 38 KB raw from CoinGecko (the old chart fetched 17 KB too).

## Contact sheets (for Jack)
`shots/program7-6.4/`: `contact-coins_btc.jpg`, `contact-coins_eth.jpg`, `contact-coins_apt.jpg` (Aptos, rank 76, the bottom-half small coin), `contact-pulse_prices.jpg`: before beside after, 375 and 1440, light and dark. `contact-btc-chart-closeups.jpg` and the four `btc-chart-{1d,1y}-375-{light,dark}.png`: crosshair shown once. Charts drew from recorded CoinGecko fixtures (`fixtures/coingecko/`).
Known visual limits: the Chart Master card in the repo is the Oct 8 read, so it shows its age note until tonight's read.

## gcm-newsroom
- `morning-dispatch` (two commits, `a36716a`, `f78497f`) was a straight descendant of main `00d7123`. Tests passed first: both slot-trigger node tests, `test_citations`, `test_claims`, `test_gates`, `test_parents_chrome`.
- Merged as a real merge commit **`25e53ef`**, pushed to main. Nothing deployed (no workflow deploys the Worker).
- **Could not confirm the deployed version against a README version note: the README carries none (no `d3d4f43d` anywhere in the branch).** The branch tip was committed Oct 12 9:28 PM UTC, before the 11:52 AM ET deploy, and the worker source reads as the morning dispatch plus the noon fallback the notes describe, so it is consistent with the deploy, but that is not a confirmation. Jack can compare `wrangler deployments` with `f78497f`.

## Jack's yes
**Not given yet.** Merge, production reads by stamp and the count five minutes after the push are all pending: merge only after his yes and outside 6:30 to 8:15 PM ET; then read production by stamp, the count of record, and run the canary on the merged tree.

## Merge hash, production reads, counts
(Superseded by the section "Merge, production reads, count" at the end of this report.)

## Jack's four fixes, 13 October 2026 (approved 12:45 PM ET, four changes before the merge)
1. **Volume bars only on 1M and 1Y.** `coinchart.js` draws them only where each bar is a day's volume (`DAILY`). 1D and 7D have no bars and no volume strip, the crosshair readout shows no volume there, and the caption says nothing of volume there (on 1M and 1Y it says "each day's volume"). Without the strip the low label would have landed on the date row, so those windows keep a 16 px gap above the dates.
2. **The averages.** Each is one smooth curve (a monotone cubic through the daily averages, so it never overshoots a turn), not a polyline. The labels, "50D" and "200D", are in the right gutter beside the price axis, in their own column to the right of the price labels, kept 15 px apart, inside the chart box, and never on a line. The gutter is 100 px on 1M and 1Y (64 px elsewhere); at 375 those two windows show three date labels where the others show four. The latest values of both averages are in the caption. Nothing is clipped at 375 (checked: every label inside the svg).
3. **The Top 100's stamp.** Read, not assumed. `netlify.toml`'s build command runs `market_pulse.py` before `site_build.py`; `movers` (the Top 100) is one of its six core sections, and the page's "As of" is `generated_utc`, the oldest core section, so a Top 100 that failed to refresh would pull the stamp back and mark it stale instead of passing as current. Production read at 12:43 PM ET: `/pulse/prices` carries build `135138e` and reads "As of 12:11 PM ET on Oct 13." (the noon fallback's build), with no stale mark. So production refreshes the Top 100 at every build and no change was needed. The Oct 11 in my shots was the committed `pulse.json` (23:12Z Oct 11): this sandbox cannot reach CoinGecko, so the local build had nothing newer to fall back to. The shots of this round carry that same stamp for the same reason.
4. **Price and 24h pill at 375.** The cause was width: the price (13 px) overflowed its 74 px cell by up to 20 px into the pill's cell (the widest, a $0.00000549 coin, is 94 px). The price cell is now 90 px, right-aligned, 12 px font (11 px for a price of 11 characters or more, class `pn-long`), with 12 px kept clear on its right; the pill's cell is 66 px, wider than its widest pill (60 px). Measured on all 100 rows at 375: the least gap between the end of the price and the start of the pill is at least 12 px (test `top100-gap`). The coin column lost 4 px.

**Tests, red then green.** The five new or changed checks ran first against the tree before the fixes: red on all of them (averages as polylines, labels on the plot, volume on 1D and 7D, readout volume on 7D, a gap of -9.6 px). Green after: `coin_pages_test.py` passes (every browser check, 101 pages at 375 without sideways scroll). New checks: `chart-averages` (curve, gutter), `chart-volume`, `top100-gap`; `chart-readout` now asks for volume on 1Y and none on 7D.
**Weight.** The fixes first pushed the BTC page to +10.3%, over the limit. Cut: unused code in `coinchart.js` (the trillions branch, PageUp and PageDown, which Shift-arrows already cover), a tighter `smooth`, and `squeeze_js` now also drops a newline where none can matter (after `{`, `,`, `(`, `;` and before `}`; `node --check` clean). Now, uncompressed at 375 against the baselines above: `/coins/btc` 238,178 (+9.94%), `/coins/eth` 238,311 (+9.96%), `/coins/apt` 236,020 (+9.77%), `/pulse/prices` 325,491. **The margin is 124, 89 and 495 bytes; the next addition to a coin page breaks the rule.** The real fix is stripping CSS comments at publish: `site.css` carries 35 KB of comments and `system.css` 5 KB, all served. That changes every page, so it was not done unasked.
**Shots.** `shots/program7-6.4/`: `btc-chart-{1d,1y}-375-{light,dark}.png`, `contact-btc-chart-closeups.jpg`, `top100-375-{light,dark}.png`, `contact-pulse_prices.jpg`. The three `contact-coins_*.jpg` sheets are from before these fixes (their 7D chart still shows bars) and were not redone.
**Not changed, seen:** long coin names wrap inside the coin column at 375 ("Hyperliqui d" on HYPE), as they did before.

## Jack's fifth fix, 13 October 2026, 1:20 PM ET: the averages are daily curves on 1Y
Approved with one more fix, and permission to merge without waiting if the new test is green and the page stays under the weight rule. Both held.
- **Cause.** 1M and 1Y fetched 365 days, so the 200-day average had no value for the first 199 days shown and its line began a third of the way across (167 points of 366). The 50-day began 49 days in.
- **Fix.** 1M and 1Y now fetch 565 days (one request serves both); the average is computed over all of it and the window shows the last 365 (1Y) or 30 (1M) days, so both averages have a value for every day shown, one point per day. A line starts where its data starts and is split, never bridged, across a gap of more than two days. **Unverified against the live API:** CoinGecko's keyless endpoint was rate-limited from this sandbox (429), and its public tier may cap history at 365 days. If it refuses 565, the chart retries at 365 days and draws as before (200-day line starting where its data does), so the charts cannot go blank; that fallback has its own test. Read the first live 1Y after the merge to see which one production got.
- **Tests.** `chart-averages-daily`, red first on the tree before the fix (200-day line 167 points, starting 127 px in), green after: on 1Y each average is at least 300 points, no segment spans more than 2 days, and each begins at the first day shown; and with the long request refused (401), the chart still draws, each line starts where its data starts, and none bridges a gap. Whole browser suite 26 of 26.
- **Fixtures.** `fixtures/coingecko/*-565.json` are the recorded 365 days with 200 synthetic days prepended (the sandbox could not record a 565-day answer); see its README. The shots' 200-day line therefore rests on 200 invented days at its left end; the last 365 days of every price are recorded.
- **Weight.** The long request does not count (the page ships no chart data), but the code did, so `squeeze_js` now also drops the spaces around operators and punctuation (strings and regexes left exactly as written; `node --check` clean; the whole browser suite runs the squeezed file). `coinchart.js` 16.5 KB to 14.0 KB. At 375: `/coins/btc` 236,150 (+9.0%), `/coins/eth` 236,283 (+9.0%), `/coins/apt` 233,992 (+8.8%), against baselines 216,638, 216,727 and 215,014. The margin is about 2 KB, replacing the 89 to 495 bytes of the previous round.
- **Shots.** `shots/program7-6.4/btc-chart-1y-375-{light,dark}.png` and `contact-btc-chart-closeups.jpg` re-shot (1D unchanged).

## Merge, production reads, count (13 October 2026)
**Authority.** Jack, 1:20 PM ET: merge without waiting if the new test is green and the page stays under 10%. Both held (26 of 26 browser checks; +9.0%).
**Merge.** One real merge commit `60ac24e` (parents `135138e`, the 7.2 close, and `6b78340`, the sprint tip), no attribution trailer, pushed 1:43:37 PM EDT. Canary on the merged tree: `LAYER 1 CANARY: PASS`, exit 0. One slip, caught before anything reached main: the first merge was made before the sprint tip was pushed, so it held `b2de41a` and lacked the fifth fix; it was discarded unpushed, the tip was pushed, the merge redone, and the canary run again on the second one. `/counts/today` before the push (1:37 PM): crypto 2 ready, 1 canceled. Merged at 1:43 PM, outside 6:30 to 8:15 PM ET.
**Production by stamp.** `/stamp.txt` read `commit 60ac24e`, built 17:47:29Z (1:47 PM ET). `live_read.mjs --expect 60ac24e` at 375 and at 1440 on `/coins/btc`, `/coins/eth` and `/pulse/prices`: commit matched, no sideways overflow, on all six. The Top 100 reads "As of 1:43 PM ET on Oct 13" (refreshed by this build).
**Count of record, 1:50:49 PM ET (seven minutes after the push):** crypto **3 ready, 1 canceled** for 13 October; the last ready build is `60ac24e` at 17:49:43Z, so the merge was counted once. The 7:08 PM Edition is the day's 4th of 5.
**Open 1: the live API refuses the 565-day request, so the fifth fix does not deliver on production.** A probe from production's own page (at 375, 1Y tab): `market_chart?days=565` answered 429 and then 401, the same refusal the public tier gives for history beyond 365 days. The chart's fallback then asked for 365 (both tries 429 from this sandbox, which is rate-limited, so the probe never saw a drawn 1Y). By the fallback's design, on production the 1Y shows both averages as daily curves starting where their data starts: the 50-day about 49 days in, the 200-day about 199 days in, no bridging. What Jack asked, a value for every day shown, needs history this free endpoint will not give. Each 1M or 1Y visit also spends one extra request on the refused 565 before the 365. Decisions for Jack: (a) accept the late start; (b) a keyed CoinGecko plan; (c) another keyless source (not evaluated); (d) drop the 565 attempt and keep the late start without the wasted request. Not changed: the brief closes with documents only.
**Open 2: one Top 100 row misses the 12 px gap.** On production at 375 the least gap between a price and its 24h pill is **7.2 px**, on a micro-cap priced `$0.0000003682` (13 characters, wider than any price in the local data, so the local test passed at 12 px or more). It is a visible gap, not touching, and the next widest rows are 13.8 px. Fix, one line each: a third size tier in `site.css` for prices of 13 characters or more (10 px), set where `pn-long` is set in `_top100_rows`, and the same live probe as the test.
**Not read.** The 7:08 PM Edition's build and the next morning run are still to come; the count after the Edition is not read. `gcm-newsroom` was not touched this round.

Shell date at close: see the last line.
Shell date at close: Tue Oct 13 2026, 12:30 PM ET
