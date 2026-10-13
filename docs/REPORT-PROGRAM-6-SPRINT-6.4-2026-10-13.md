# Report: Program 6, Sprint 6.4, the coin pages and the Top 100 (13 October 2026)

**Status: built and proven on the local tree, NOT merged. Jack's yes is not in this session.** Everything below that needs a yes or a production read says so.

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
Volume is the source's trailing 24-hour volume at each point (not per interval); the caption says so. The 50-day and 200-day lines are averages of daily closes from the 366-day series, drawn on 1M and 1Y only. The chosen window lives in the script's closure: no storage, no cookie (reload returns to 7D).

## What was built
- Chart: 1D/7D/1M/1Y tabs (44 px), Program 7 line (3 px, glow, area, glowing high and low with mono labels, halo on the last point) colored by the window's own change, the printed change beside it from the same series; dashed labeled averages; muted volume bars on their own scale, up/down by close; price labels right in Plex Mono 12 px; four date labels at 375; crosshair readout (price, date, volume) for touch, hover and keyboard (arrows, Shift, Home, End, Esc) that stays inside the box; draws once, whole at once under reduced motion. Built as one shared file.
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
Known visual limits: on 1Y the average labels can sit across the price line; the Chart Master card in the repo is the Oct 8 read, so it shows its age note until tonight's read.

## gcm-newsroom
- `morning-dispatch` (two commits, `a36716a`, `f78497f`) was a straight descendant of main `00d7123`. Tests passed first: both slot-trigger node tests, `test_citations`, `test_claims`, `test_gates`, `test_parents_chrome`.
- Merged as a real merge commit **`25e53ef`**, pushed to main. Nothing deployed (no workflow deploys the Worker).
- **Could not confirm the deployed version against a README version note: the README carries none (no `d3d4f43d` anywhere in the branch).** The branch tip was committed Oct 12 9:28 PM UTC, before the 11:52 AM ET deploy, and the worker source reads as the morning dispatch plus the noon fallback the notes describe, so it is consistent with the deploy, but that is not a confirmation. Jack can compare `wrangler deployments` with `f78497f`.

## Jack's yes
**Not given yet.** Merge, production reads by stamp and the count five minutes after the push are all pending: merge only after his yes and outside 6:30 to 8:15 PM ET; then read production by stamp, the count of record, and run the canary on the merged tree.

## Merge hash, production reads, counts
None: not merged.

Shell date at close: see the last line.
Shell date at close: Tue Oct 13 2026, 12:30 PM ET
