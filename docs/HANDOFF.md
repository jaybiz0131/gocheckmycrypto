# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `PROGRAM-4-2026-09-16.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 5 October 2026, end of the data-contract session.
`main` ends at the close commit on top of `10f70f6` (section 7). `canary-own-writes`,
`snapshot-contract` and `live-ticker-only` are MERGED and DELETED. One local branch remains
and is not this session's: `family-map-home-sections`. Days before 23 September live in
`HANDOFF-2026-08-17.md`; 23 September to 1 October in `HANDOFF-2026-09-23-to-10-01.md`;
4 October in `HANDOFF-2026-10-04.md`; 5 October in `HANDOFF-2026-10-05.md` (U-1).

**No AI attribution on any commit or PR** (family rule): `.claude/settings.json` sets
`attribution.commit` and `.pr` to "" and `includeCoAuthoredBy` false (Claude Code 2.1.289).

The Sports handoff (`../gocheckmysports/HANDOFF.md`, the file at that repo's root,
not the one in its `docs/`) carries the shared laws,
the shared traps and the command list. This file carries what is different here.

## 1. Where things live

Boards and packages in `../gcm-tools/`: `program-4-2026-09-16/` (Program 4,
ScoreboardC), `program-3-2026-09-15/` (Program 3, StyleTile, WhaleWatchPage and
ChartMasterPage on canvas row ten), `site-audit-2026-09-14/`. Worker in
`../gcm-newsroom/slot-trigger/`.

## 2. What is different on this desk

- **One checked story a day (Jack, 4 October 2026).** The evening Edition publishes at
  most one story: the top-ranked one that clears every gate AND rests on two independent
  sources or one primary source (`standing.py`, the one rule the Edition and the badge
  both read). The rest are held; only holds that could have led carry their draft, in
  `site/data/edition_hold.json`, offered to the NEXT day's Edition only, as its story if
  nothing fresh clears and the held one is still current. Breaking runs are untouched
  (two a day, five sources, four categories). `top_n` is 6. `python3 autopilot.py
  --dry-run` with `AUTOPILOT_OUT=<fixture dir>` runs the decision and writes nothing.
- **Three badges, and only three:** "Verified" (two or more independent sources),
  "Verified, primary source" (one primary source, listed first), "Unconfirmed, one
  report" (one secondary outlet, whatever the verdict). Standards defines each. The back
  catalogue re-labeled with the rule.
- **The cadence line** sits under the News title and over the home story slot. "Nothing
  cleared the bar today." prints only once the hold file carries today's Eastern date and
  nothing published today.
- **Exchange names come from `venues.py`.** OKX is the only spelling; `destyle` rewrites
  the old one in stored copy. Whale Watch's sentence and tables come from one function,
  `whale_window()`, and every label names the window the data carries.
- **Crypto copy is frozen (V-13)**, lifted on 4 October for the cadence, badge, Standards
  and whale lines only. Jack has not reviewed this desk against the copy
  law. Do not change chrome copy here. The Sports law will apply in the same shape
  once he has. Structural duplication introduced by new work may still be removed.
- **The watcher is caged, not disabled.** Sports turned its watcher off; this desk
  sells crypto breaking news, so it is kept under four constraints in `watcher.py`:
  1. Earning categories only, imported from `site_build.TAG_RULES` so the watcher and
     the site cannot drift: `regulation`, `exchanges`, `etfs-funds`, `security`.
     `security` already existed as the first and most specific tag rule.
  2. Five independent sources, raised from four.
  3. Two breaking runs a day, counted from `ledger.json`. The ledger counts the RUN,
     so a run that spent and published nothing uses the allowance. A missing ledger
     reads as unknown and does not block.
  4. Price triggers off. A 5% hour and a 4% day are volatility, not events in those
     categories. Re-enable with `WATCH_PRICE_TRIGGERS=1`.
  Its cron is `17 12-23 * * *` as a backstop; the Worker ticks it on the half hour
  during US hours.
- **`SLOT_DEADLINES` holds evening-brief only.** A slot left there with no cron is
  re-fired on every tick forever, before the cooldown and before the cage, and each
  fire spends a run. The canary guards this now.
- **`site-refresh.yml` stays** at 12:00 UTC until the Board is served by the Worker
  (L-1, Sprint I). Until then it is the only thing that moves the Board between
  midnight and the 23:08 Edition: one build, no model run. It retires with R-1.
- Brief cron: `8 23 * * *` only. Morning, midday and their retries are disabled.
- **The slot guard (X-2, X-2b)** applies to every run, not only crons: a served slot,
  a dispatch with no slot, and a dispatch naming a slot this desk no longer serves all
  stand down at zero before any model call. `breaking=true` is the only bypass. Ten
  cases in the canary.
- `ledger.json` carries `since` (2026-09-16T16:27Z); every tally prints it.

The cage's behaviour, on the record. Fires: an SEC/BlackRock ETF headline
(`etfs-funds`), Binance halting withdrawals (`exchanges`), a bridge drain
(`security`), a Senate cloture vote (`regulation`). Stays quiet: a 6% Bitcoin rally,
a Solana client upgrade, a celebrity-driven Dogecoin surge.

## 3. Open items

| Item | Status |
|---|---|
| V-8 A-12 emblems: 44x29 mark and masked watermark | open, Sprint I |
| V-9 N-3 module pages (WhaleWatchPage, ChartMasterPage, canvas row ten) | open |
| V-10 N-1/N-2 nav: Home first, Chart Master in nav, 12th tile, read card | open |
| V-11 punch 5, 6, 8: label columns, full-width Whale Watch, Edition wordmark | open |
| V-12 A-14/A-15/D-7 inner pages and phone, under 5,500 phone homepage | part done |
| V-13 Crypto copy | **hold** (lifted 4 Oct for named lines only) |
| top_n 6 ranking check, after seven Editions, 4 to 10 Oct (section 6) | open, 2 of 7 |
| Twins check (`twin_audit.figure_twins`): warns only; whether it gates is Sprint 1's call | open, P5 S1 |
| Coin page chart: stays on demand (Jack, 5 Oct). P5 Sprint 3 rebuilds it: default line from the snapshot's sparkline field once Sprint 1 adds it, longer ranges on demand, caption with range and read time and NO dollar figure (a second price from a second endpoint is the twin the contract retires) | open, P5 S3 |
| Ticker label hidden at 375 (`site.css` `.markets .lab .mkt-asof{display:none}`), so a phone reader never sees "live" on the one live surface; the rule's reason (the tile said it) left with branch two | open |
| `assets` (`/coins/{id}/market_chart`) carried since 2 Oct 23:12Z in every committed `pulse.json`; the Board sparkline, RSI line and Chart Master charts draw from it | open |
| `chartmaster.json` dated 2026-09-21 while Edition commits say "Chart Master read" each day | open |
| L-1 the Board on the Worker | open, Sprint I |
| R-1 desk reconfiguration | open, Sprint J |

Landed 4 October: A-14 (`/pulse` opens with the Board band at 646px against the
homepage band's 1027, 63%), A-5's ornament (Bitcoin's 30-day closes as a filled area
in #FF6A4D, omitted under 720px), the watermark fetch fix, and the mono-500 font
weight removal.

## 4. Notes carried forward

- The stale-data tripwire is the honesty mechanism on this desk. C-18's phone rule was
  hiding it along with the routine stamp; the routine stamp stays hidden on phone, the
  warning does not. It is the only phone height change and appears only when stale.
- `/flows` and `/chartmaster` keep no band. C-2's ruling that data pages are tables
  and charts stands; A-14 gives the band only to `/pulse`.
- The reduced `/pulse` band omits the Chart Master slot: that page carries the read
  full width 300px below it.
- `board_tile_grid(..., cm_slot=False)` is how a caller drops that tile.
- A-17: Crypto LCP 4,540 ms live on phone, median of three. Absolute budget is under
  3,000 ms by the end of Sprint I, via the five self-hosted font files and the
  390-wide poster variant. Same work as the Sports desk; do both together.

## 5. Commands

Same as the Sports handoff. Serve on 8802. The canary here is
`python3 verify_pipeline.py canary; echo "exit=$?"` and its exit code must be read,
not piped into `tail` and assumed.

## Live as of 24 September 2026

- **The deploy count method (U-11 as corrected).** Read `/counts/today` on the Worker, the
  count of record. The `gh` commit-statuses method is withdrawn: Netlify posts no status,
  check or deployment to this repository.

- **The ignore rule (U-11).** `netlify_ignore.py` carries a path list: `docs/`, `shots/`,
  `review-queue/`, any markdown outside `site/`, and the ignore file itself never build the
  site. `site_build.py` and `chartmaster.py` are not on it and the canary asserts they still
  build.
- **This desk is not under the Sports freeze.** It may push outside the Edition quiet hour,
  6:30 to 8:15 PM ET. The Sports window is Sundays 12:30 to 8:30 PM ET and no other day.
- **The allowance** is 5 production deploys a day on this desk.
- **K-8** waits on Jack's Worker deploy. The COUNTS namespace was created and bound on
  24 September; the deploy carries all four routes.
- **K-1 reads built output.** The canary compares the built `news.html` against the content
  directory, so a pull that brings in a story without a rebuild shows up as a red canary that
  is not a defect. Regenerate first, which is what U-10 asks (24 September: it came up red on
  the 2026-09-23 XRP story and went green on a rebuild with no code change).
---

## 6. The data contract (live 5 October 2026, `0ab4472` and `10f70f6`)

**One snapshot.** `snapshot.py` builds one object at build time from `pulse.json` and
`flows.json`, written to `site/data/snapshot.json` (ignored) and published at
`/data/snapshot.json`. One endpoint per field, named beside it with its read time: `coins`
(price and 24h for all 100, CoinGecko `/coins/markets`), `dominance` and `total_cap`
(`/global`), `etf_flows` (Farside), `whale_net` with window and "all coins" (Whale Alert),
`funding` and `open_interest` (OKX), `stablecoin_float` (DefiLlama), `fear_greed`
(alternative.me), `network_fee` (mempool.space). Its stamp is the oldest read, written with
its zone, "8:29 PM ET on Oct 5". Changing a source is changing `SOURCES` in that file.

**Every surface reads it.** Renderers are handed `snapshot.views()`, never the raw files: the
ticker's server fill, the Board, coin pages, Top 100, the Brief's lead line, the article board
panel and `chartmaster.digest()`, which the Edition writes from. A field the snapshot lacks is
removed from the view, so it is omitted rather than printed from another endpoint.

**The ticker is the only live surface.** In the browser it refreshes coin prices and 24h
change, the total cap and BTC dominance (one `/global` call), and says "live · 8:34 PM ET"
only after an OK answer that carried a price; otherwise it keeps the build's stamp. No Fear &
Greed, no funding: those are the snapshot's, on the Board. Nothing else refreshes in the
browser; `pulse-live.js` is retired. The one exception is the coin page chart's range buttons,
a reader's action, on demand by Jack's ruling.

**Chart Master**: boards first, then "The Chart Master's read, <date>", and one line under it
when the read is older than the Board: "The boards above are newer than this read; they are as
of <stamp>."

**The twins check** (`twin_audit.figure_twins`) compares a story's Bitcoin price with the
Board's, both from the snapshot it is handed; 3%, same-day stories; warning only.

**Guarded by** `_data_contract_canary` (snapshot moved to numbers no endpoint returns; every
surface must print them) and `_live_layer_canary`. Tomorrow's Edition is the first to read
the snapshot; 5 October's read the raw file.

**The top_n 6 ranking check.** top_n 6 assumes the editor ranks the same way when asked for
six as it did for twelve. Settle it after seven Editions under the cadence (4 to 10 October)
from `ledger.json` and the hold files: if any day's chosen story would have ranked below 6
under the old count, or a day went dark with a story that could have led below the cut,
raise top_n and say to what. Data points: 4 October rank 6 of 6; 5 October rank 1 of 6.

**The next session** is Program 5 Sprint 1, with its own opener. Queued behind it from the
5 October order, in this order unless the opener says otherwise: S-2 on Sports, then the
deep-URL register, then Cause C on Sports.

## 7. Where this session ended (5 October 2026, evening)

- Item 0 (`88751d9`) and branch one (`3378807`) merged at `0ab4472`, pushed 00:16:29Z (6 Oct),
  local = origin, 0 outstanding; live by `/stamp.txt` at 00:20:48Z, built 00:18:35Z.
- Branch two (`cced2fc`, `101c6ac`) merged at `10f70f6`, pushed 00:29:28Z, local = origin, 0
  outstanding; live by `/stamp.txt` at 00:33:57Z, built 00:31:35Z.
- Board, `/coins/btc` and the Top 100 BTC row all $85,829.00 under "8:29 PM ET on Oct 5";
  ticker "live · 8:34 PM ET" at 1440 and 375.
- The 5 October Edition (run 37386951225) chose rank 1 of 6, "OKX and NYSE Parent ICE File
  for 24/7 Tokenized U.S. Stock Trading" (`d6ec0f4`); held rank 4, the CFTC perpetuals story,
  corroborated, draft carried to 6 October. Ledger 149,861 tokens, $0.2512.
- Deploys 5 October (`/counts/today`): 5 production builds against 5: site-refresh,
  `24ab0c2`, `d6ec0f4`, `0ab4472`, `10f70f6`. The close commit is documents only.
- Stashes: none. Two `zsh` loops from 4 October (PIDs 2862, 2386) wait on a `pgrep` that
  matches itself; Jack kills them from his own Terminal.

## 8. Traps

- **The canary cleans only what the build wrote** (rule since 5 October, `88751d9`). Its
  cleanup acts on the paths the build process opened for writing and leaves everything else
  as found, printing "left X as found". The stray-writer plant runs on every canary: a second
  process writes `fixtures/.stamp-canary-stray.txt` and appends to `fixtures/sample_feed.xml`
  during the build, and both must survive. Editing while the canary runs is safe again; a
  build that writes through a subprocess would not be recorded, so its file would be left.
- **A ledger row lands mid-canary.** The watcher pushes `ledger.json` rows on the half hour;
  twice now (4 and 5 October) one landed between the canary and the push. Re-merge on origin's
  tip and push; the shipped tree differs by that row only. Fetch before pushing, every time.

---

# Standing rules, all desks: not here, by Jack's ruling

**Option two, 1 October 2026.** U-1 to U-13 and the dated rules beside them live in ONE file,
`../gocheckmysports/HANDOFF.md`, the file at that repo's root and not the one in its `docs/`.
This handoff used to carry its own copy of the full text; the copy was removed the same day,
because a law copied into five files is five chances to drift and a law in one file is none.

Read that file before building anything here. It carries U-1 to U-13 verbatim, the three rules
added on 1 October (a plant's restore comes from a saved copy and never from `git checkout` on
the file under test; nothing is staged with `git add -A` and a documents-only message is
checked against `git diff --cached --stat`; a push's exit status is read from the push and
never from a pipe), and the traps the two desks share.

If that path does not resolve, say so in the report rather than working without the laws or
reciting a rule from memory. The two repos sit side by side in `~/Berno Projects`.
