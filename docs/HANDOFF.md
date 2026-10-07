# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `docs/PROGRAM-5-2026-10-05.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 6 October 2026, end of Program 5 Sprint 1a (section 7). `main` ends at the
close commit on top of `747724e`. Days before 23 September live in `HANDOFF-2026-08-17.md`;
23 September to 1 October in `HANDOFF-2026-09-23-to-10-01.md`; 4, 5 and 6 October in
`HANDOFF-2026-10-04.md`, `-10-05.md` and `-10-06.md` (U-1).

**ITEM 0 OF THE NEXT SESSION, before anything new:** merge `calendar-ledger-followups`
(`d51d056`, already on origin; Jack pushed it 6 October; branch pushes build nothing here).
Read it, run the canary on the merged tree, push on exit 0, read it live, then start Sprint
1b. It is its own merge and rides with nothing else (section 3, first row).

**The next session runs in a Claude Code cloud session** cloned from GitHub. The held branch
is on origin; this Mac's local state (stashes, untracked files such as
`site/data/snapshots/pulse-*.json`, the local branch `family-map-home-sections`) is not.
`../gcm-tools` and `../gocheckmysports` are not there either: the program is
`docs/PROGRAM-5-2026-10-05.md`; the U-rules gap this leaves is in section 3.

**No AI attribution on any commit or PR** (family rule): `.claude/settings.json` sets
`attribution.commit` and `.pr` to "" and `includeCoAuthoredBy` false (Claude Code 2.1.289).

The Sports handoff (`../gocheckmysports/HANDOFF.md`, the file at that repo's root,
not the one in its `docs/`) carries the shared laws,
the shared traps and the command list. This file carries what is different here.

## 1. Where things live

Program 5 (governs the build): `docs/PROGRAM-5-2026-10-05.md`. On the Mac only, boards and
packages in `../gcm-tools/`: `program-4-2026-09-16/` (Program 4,
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
| **`calendar-ledger-followups` `d51d056` (on origin): mixed filings stay in, the unlocks file's lines, the ledger row's Chart Master calls/tokens/cost** | **next session's item 0, its own merge** |
| Unlocks: HYPE, WBT, RAIN read "page not readable from the desk, October 6" | Jack, by hand in a browser |
| Twins gate (ruling 2d below): a Bitcoin dollar figure in our own text within 1% of the snapshot or dropped and logged; never the Board | P5 Sprint 1b |
| The newsroom's half (program section 9): wire, checked note, narrative line and clause table, cadence line, Edition cost before and after | P5 Sprint 1b |
| The Brief's week and month come from the stored series (`_window_changes`), the coin pages' 7d/30d from `/coins/markets`: 6 Oct Brief "up 1.3% on the week, up 8.3% on the month", markets read +2.47% and +7.01%. Two sources for one window | for 1b's twins gate |
| The week field gives 6 closes when the read lands in a UTC 23:00 hour (168 points start after 00:00 six days back); 7 otherwise. No second request fixes it; Sprint 2 draws what is there | note for Sprint 2 |
| `_chartmaster_crash_canary` prints its planted crash as a `::warning::` annotation on a green run (6 Oct run, 23:11:45Z); belongs inside `::stop-commands::` | small, next branch |
| U-1 to U-13 live only in `../gocheckmysports/HANDOFF.md`, which a cloud session cannot read; U-14 to U-16 are copied below | Jack's call (close report) |
| V-8 A-12 emblems: 44x29 mark and masked watermark | open, Sprint I |
| V-9 N-3 module pages (WhaleWatchPage, ChartMasterPage, canvas row ten) | open |
| V-10 N-1/N-2 nav: Home first, Chart Master in nav, 12th tile, read card | open |
| V-11 punch 5, 6, 8: label columns, full-width Whale Watch, Edition wordmark | open |
| V-12 A-14/A-15/D-7 inner pages and phone, under 5,500 phone homepage | part done |
| V-13 Crypto copy | **hold** (lifted 4 Oct for named lines only) |
| top_n 6 ranking check, after seven Editions, 4 to 10 Oct (section 6) | open, 3 of 7 |
| Coin page chart: stays on demand (Jack, 5 Oct). P5 Sprint 3 rebuilds it: default line from the snapshot's sparkline field once Sprint 1 adds it, longer ranges on demand, caption with range and read time and NO dollar figure (a second price from a second endpoint is the twin the contract retires) | open, P5 S3 |
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
- **The allowance** is 5 production deploys a day on this desk. **Standing line (Jack, 6
  October 2026): five builds a day are the Worker's noon refresh, the Edition, and THREE
  merges; a fourth merge waits for the next Eastern date; a day's plan names its three
  before the first push.** 6 October ran 6 of 5 for missing this (section 7).
- **K-8** waits on Jack's Worker deploy. The COUNTS namespace was created and bound on
  24 September; the deploy carries all four routes.
- **K-1 reads built output.** The canary compares the built `news.html` against the content
  directory, so a pull that brings in a story without a rebuild shows up as a red canary that
  is not a defect. Regenerate first, which is what U-10 asks (24 September: it came up red on
  the 2026-09-23 XRP story and went green on a rebuild with no code change).
---

## 6. The data contract and Program 5 Sprint 1a (live 6 October 2026)

**One snapshot** (`snapshot.py`, 5 October, `0ab4472`, `10f70f6`): one object per build at
`/data/snapshot.json`, one endpoint per field named beside it, stamp = the oldest READING with
its zone. Renderers get `snapshot.views()`, never the raw files. The ticker is the only live
surface and says "live · 8:21 PM ET" only after an OK answer with a landed price. Details in
`HANDOFF-2026-10-05.md`.

**Sprint 1a, the data assets** (6 October, all four live; day file `HANDOFF-2026-10-06.md`):
- Item 0 `4d8a23d`: the live mark shows at 375 (10px mono, the label's existing line).
  `scripts/ticker_mark_375.mjs <url> [--width N] [--expect-live]` reads it in headless Chrome.
- Items 1 and 2 `35e3922`: **the stored series** (`history.py`): `data/history/<coin>.json`,
  daily closes by UTC date for the seven Board coins, committed by the Edition. A run appends
  the completed days it lacks and never refetches; a missing file or one more than seven days
  behind bootstraps from 365 days, one coin per run. 429s wait Retry-After or 60s, three
  tries; CoinGecko calls spaced 12s and counted (`out/coingecko-calls.json`). A failed append
  leaves the file; tiles print "closes through <date>", stale at 48h behind the run. The
  series is not a reading: it sits in the snapshot as `series`, outside the stamp. Through
  date tonight: **2026-10-05** for all seven. **The Chart Master**: `_belt_inputs` hands the
  leverage belt the pipeline's shape; a belt crash is one refused read, never retried; the
  commit message reads the file's date and the night's state.
- Item 3 `9eb41fa`: the snapshot's `week` (seven daily closes, low, high, from
  `/coins/markets` sparkline=true) and `movers` (CoinGecko ranks 1 to 20: three rises and the
  fall; top 100: more than 5% either way, or "none today"; stablecoins from
  `data/stablecoins.json`, DefiLlama, refreshed monthly). Written compact; 33,056 bytes in
  tonight's run against 60 KB.
- Item 4 `fddf690`: `desk_calendar.py` writes `site/data/calendar.json` (FRED with
  `FRED_API_KEY` in the Edition's calendar step only; FOMC and NYSE yearly files in
  `data/calendar/`; Deribit; mempool.space; Federal Register; `unlocks.json`). The Edition
  commits it; the build publishes it at `/data/calendar.json`.

**The four rulings, as they ended** (Jack, 6 October):
- **a.** The live mark: shown at every width, never hidden. Done, item 0.
- **b.** Replaced at 6:54 AM ET: the record wins; assets is a stored series the site owns,
  appended per run, never carried forward silently, its through date on the tiles that use it
  and never in the page stamp. Done, items 1 and 2.
- **c.** The commit message and the file agree, and the file is the truth. The stage had run
  every Edition from 22 September and every read was refused; three crashed (1, 3, 4 October)
  on K-4 `6cab8b6`. Crash fixed by Jack's 7:30 AM ET ruling with four conditions, all met.
  Cadence unchanged.
- **d.** The twins check becomes a gate on the newsroom's own text, never on the Board: any
  Bitcoin dollar figure in the narrative line, the checked note, a wire line or the Brief's
  lead line must agree with the snapshot's price within 1% at the run's stamp, or it is dropped
  from our text and the drop logged with both numbers; a linked source keeps its own figure.
  Sprint 1b.

**The top_n 6 ranking check** (raise top_n if a chosen story would have ranked below 6, or a
day went dark with one below the cut): 4 Oct rank 6 of 6; 5 Oct rank 1 of 6; 6 Oct rank 3
of 6 (rank 1 held as single-source). Settle after 10 October.

## 7. Where this session ended (6 October 2026, evening)

- Merges, each canary exit 0, each push local = origin, 0 outstanding: `4d8a23d` 11:13:40Z,
  `35e3922` 11:40:59Z, `9eb41fa` 11:49:10Z, `fddf690` 12:02:39Z. All read on production by
  stamp at 375 and 1440.
- The Edition (run 37545030660, commit `4ce5537`, built 23:19:54Z): rank 3 of 6 published,
  "Conduit sues Tether over $2.76 million freeze"; ledger 163,794 tokens, $0.2718 (5 Oct:
  149,861, $0.2512). Chart Master: 3 model calls, $0.0634, refused on content (the ETF flow
  window belt), no crash; figures from the run log, since the ledger's per-stage fields land
  with item 0. CoinGecko calls: 2 (series current, no append). Calendar: 31 entries, FRED
  verified, 14 macro entries (CPI Oct 14 first). The consistency gate withheld the whale board
  (the Brief said positive, the board negative), so the committed `flows.json` stayed at
  5 October; production rebuilt it: "7:19 PM ET on Oct 6", BTC $85,456.00.
- **Count of record: 6 of 5 on October 6**: four Sprint 1a merges before 8:10 AM ET, the
  noon refresh, the Edition; the plan had counted three scheduled-plus-merge slots wrong,
  corrected in the standing line (section "Live as of 24 September"). The close is documents
  only.

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

## U-14 to U-16, copied verbatim from the Weather handoff (`../gocheckmyweather/docs/HANDOFF.md`)

U-14, U-15 of 2026-10-05, 12:03 PM ET; U-16 of 2026-10-05, 9:28 PM ET.

**U-14. A push is gated on the preflight's exit status.** `preflight && push`, never chained with a semicolon or a newline; a red preflight means no push, under load or not, and a green rerun is a reason to push then, not a reason the first push was fine (the process error of 2026-10-05).

**U-15. The preflight runner prints the name of every failing case, never a count alone.** A red that cannot be named cannot be fixed. The load average is printed at each preflight (`scripts/preflight.py`, start and end) and reported: 48 to 88 is one desk, 300 to 970 is two desks at once, and Jack keeps that rule, not the desk.

**U-16. A suite's output goes to a file and is read after the suite exits.** It is never piped into head, tail, a pager or anything that can close the pipe early: a closed pipe kills the suite before its finally runs, and its server stays up as an orphan on its port (the two orphaned servers of 2026-10-05, both the desk's own). The preflight's red on an orphaned port is the rule working, not noise. (2026-10-05, 9:28 PM ET.)
