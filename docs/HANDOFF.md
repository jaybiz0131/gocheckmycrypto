# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `docs/PROGRAM-5-2026-10-05.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 11 October 2026, 5:10 PM EDT, Program 6 Sprint 6.2 (section 7d). Before it, Sprint 6.1 (section 7c). Earlier that day, 9:20 AM EDT: Sprint 2's close (section 7b) and the band-ink merge `aa64f08`. Before that, the close of 8 October (section 7), written late: the 8 October
evening wake-up reached the session on 11 October. `main` ends at the close commit on top of
`a5bea57`. Days before 23 September live in `HANDOFF-2026-08-17.md`; 23 September to 1 October
in `HANDOFF-2026-09-23-to-10-01.md`; 4 to 8 October in `HANDOFF-2026-10-04.md` to `-10-08.md`
(U-1).

**ITEM 0 OF THE NEXT SESSION (Sprint 3, its own opener), before anything new:** the twins
gate's direction and window checks cut true sentences (section 3, first row). Seven drops on
9 and 10 October, all wrong, the 10 October dek among them. Fix on a named branch, each cause
red first, before any Sprint 3 work merges.

**Sessions run in Claude Code cloud sessions** cloned from GitHub. The Mac's local state is
not there, nor `../gcm-tools` or `../gocheckmysports`: the program is
`docs/PROGRAM-5-2026-10-05.md`, the laws `docs/RULES.md` (hash in every opener).

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

- **The wire path (Jack, 5 October; live 7 October).** The daily written story ended. The
  Edition ranks and verifies, then writes `site/data/wire.json` (`wire.py`): the desk's one
  line per cluster (`wire_line`, from the editor's own call; never a source title verbatim),
  outlets counted, primary flag, links, the Board reading from the tag rules; the checked
  note (two sentences from the verifier's own call) on the top item that is VERIFIED and
  can lead (`standing.py`). Researcher, writer and approver are not called (code kept);
  autopilot stands down. The build's `wire.py --refresh` re-counts and re-orders, no
  model. Breaking runs keep the story path. `top_n` is 6.
- **The twins gate (`twins_gate.py`)**: our text yields to the snapshot. A Bitcoin dollar
  figure over 1% off, a week or month figure not the stored series' (`snapshot.series_windows`),
  a direction word against the snapshot's sign: the sentence drops, logged with both numbers
  (`out/twins-gate.json`). On wire lines, the note, the narrative line and the Brief.
- **The narrative line (`narrative.py`)**: written in the Brief's call, the clause table
  when it fails; `site/data/narrative.json`; rewritten between runs only on a crossing.
  Funding bands (Jack, 7 October): calm under 0.010% per 8h, warm under 0.030%, hot above.
- **Three badges, and only three:** "Verified" (two or more independent sources),
  "Verified, primary source" (one primary source, listed first), "Unconfirmed, one
  report" (one secondary outlet, whatever the verdict). Standards defines each. The back
  catalogue re-labeled with the rule.
- **The cadence line**: /news prints Jack's words (`NEWS_CADENCE_LINE`); the home page keeps
  the 4 October sentence until Sprint 2.
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
| **The twins gate cuts true sentences**: 9 and 10 Oct, seven drops, all wrong. Causes: "five-session" (hyphen) is not a window to `_WEEK_WORDS`; a direction word is pinned on the nearest context (a coin name beats "funding" or "ETF"); one window per sentence ("positive daily print ... weekly outflows" read as weekly); a quoted word ("a word like "rising"") read as a claim; "falling" missing from the sign words ("falling 2.3% on the week" read as +2.3%) | **item 0, Sprint 3's first branch** |
| The clause table pairs direction and driver without regard to sign ("drifting higher on spot ETF outflows", 9 Oct) | Sprint 3, with the gate |
| No Brief for 7 October | lost; the gate fix of 8 October prevents the class |
| Unlocks: HYPE, WBT, RAIN read "page not readable from the desk, October 6" | Jack, by hand in a browser |
| Learn page prints the funding bands: `tile.funding_thresholds()` reads `narrative.FUNDING_BANDS`; not confirmed on the live leverage page on 11 Oct | Sprint 3: read it live |
| The wire stays in re-count order; the checked item is never pinned | closed: Jack, 7 October (section 7b) |
| Board reading from the tag rules is coarse: "shut down" and "custody" map to exchanges, so an L2 shutdown and a bank custody approval read "Whale net" | Sprint 2, with the band |
| Home page cadence line: read with Sprint 2's home page live | Sprint 3: confirm |
| Coin pages print `/coins/markets` 7d/30d; the twins gate covers the newsroom's text only | P5 Sprint 3 |
| The week field: coins outside the seven stored series read six closes in the 23:00 UTC hour | note for Sprint 2/3 |
| The build's call to `publish_narrative` has no failing test (the unit test calls the function) | next branch |
| Count 7 of 5 on 7 October; two builds not nameable from `/counts/today` | Jack: read Netlify's deploy list |
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
- **d.** The twins check becomes a gate on the newsroom's own text, never on the Board.
  Landed in Sprint 1b with both October 6 extensions (series-only week and month; direction
  words yield to the snapshot's sign), section 7.

**The top_n 6 ranking check** (raise top_n if a chosen story would have ranked below 6, or a
day went dark with one below the cut): 4 Oct rank 6 of 6; 5 Oct rank 1 of 6; 6 Oct rank 3
of 6 (rank 1 held as single-source); 7 Oct (wire path) the checked note on rank 1 of 6.
Settle after 10 October.

## 7. Sprint 1b (7 October) and the 8 October merges (day files `-10-07.md`, `-10-08.md`)

Sprint 1b executed Jack's ruling of 5 October (the wire, the checked note, the twins gate, the
narrative line); merges `65b7a26`, `8e78f40`, `94c392b`. The first wire-path Edition cost
$0.0868 against $0.2718 the day before; its Brief was withheld by the consistency gate.

**Jack's rulings, 7 October 2026, 9:15 PM ET:** (1) the gate fix merges as 8 October's first
merge, in the morning; the 7 October Brief stays missing and nothing re-runs its slot; (2) the
funding thresholds are option 1 (calm under 0.010% per 8h, warm under 0.030%, hot above).

**8 October**, two merges, each canary exit 0 on its own rebuilt tree, local = origin:
- `fea18c0` 12:41:00Z (`cr-gate-fixes`): the gate yields to the snapshot; no fake zero from
  an empty volatile whale read (production showed "$0 net off exchanges"; now widened or the
  last good file stays; /pulse and /flows say what they wait for); funding per coin; the
  checked note names and links one outlet (the refresh re-resolves a stored note).
- `1a65e9d` 12:58:20Z (Sprint 2's stack `4c575a1` < `1804653` < `1e0e456`, one merge, plus the
  band's ETF date month first): home at 375, 111,985 bytes, LCP 1,212 ms; at 1440, 112,019
  bytes, LCP 1,180 ms; one stamp "8:58 AM ET on Oct 8"; since-yesterday lines nonzero and equal
  to the Board's tiles.
- Count read 13:04:43Z: 2 built. The day's final count was not read (the wake-up arrived late).

**Editions on the new path, each with a Brief:** 8 Oct $0.0915, 9 Oct $0.0852, 10 Oct $0.0677
(7 Oct $0.0868). The narrative line came from the table all three days.

## 7b. Sprint 2's close (the stack, the weight, the Editions of 8 to 10 October; day file `HANDOFF-2026-10-11.md`)

Written 11 October 2026, 9:20 AM EDT, documents only. The 8 October close named Sprint 2's merge
wrongly; git shows it as below.

- **The merges, from `git log --graph`.** `bc6d35d` 12:41:28Z merges `1e0e456` (home-below-fold,
  stacked on home-above-fold and tile-learn-anchors). `1a65e9d` 12:53:11Z merges `d618a44`, the
  last commit of `cr-gate-fixes` (its other work, `fea18c0` 12:35:58Z, merged first). Between
  them `6bf1849` (the band's small line, month first) sits on main.
- **The stack proof.** `git merge-base 4c575a1 1804653` = `4c575a1`; `git merge-base 1804653
  1e0e456` = `1804653`. Nine commits `94c392b..1e0e456`, from `506071e` to `1e0e456`.
- **Production weight, measured 9:16 to 9:17 AM EDT on `aa64f08`** with `scripts/home_budget.mjs`
  (three throttled phone loads each): 375 light 111,599 bytes, LCP median 1,116 ms; 375 dark
  109,983 bytes, 1,080 ms; 1440 light 110,068 bytes, 1,072 ms; 1440 dark 111,305 bytes, 1,060 ms.
  Hosts: the site and api.coingecko.com only; overflow 0. Budget 300 KB and 2,500 ms.
- **Editions, from the ledger** (all three published a Brief): 8 Oct run 37857914790 $0.0915; 9 Oct
  run 38003059379 $0.0852; 10 Oct run 38094093202 $0.0677. Chart Master: published 8 Oct
  (`b281882`, "Chart Master read 2026-10-08"); refused 9 Oct (`cbf7e80`): "chartmaster:
  advice/prediction language in the read ('bleed'); refusing to publish it"; refused 10 Oct
  (`8533a17`): "chartmaster: an open-interest figure names no venue in its own sentence ('Open
  interest is sizable (BTC near $2.49B, ETH" (the commit subject is cut there; the full reason is
  not kept).
- **Jack's rulings, as the strategy desk's order of 11 October states them.** 7 October: the wire
  stays in re-count order; the checked item is never pinned (this closes the open "keep or pin"
  item in section 3). 8 October: none for Crypto.

## 7c. Program 6, Sprint 6.1: one site, one look (11 October 2026; day file `HANDOFF-2026-10-11.md`)

Program 6 is `docs/PROGRAM-6-2026-10-11.md` (the pasted text; the attached file never reached the
session). **Jack's rulings, Sunday 11 October 2026, 10:49 AM ET, in the strategy desk's words:**
Jack agreed to all four decisions in Program 6, section 3:
1. The Chart Master's character voice is retired. The read stays as a plain card titled "The Chart
   Master's read, <date>".
2. The names are Program 5's: Markets (the Board), Flows (Whale Watch), Charts (Chart Master), News,
   Brief (the Edition), Record, Learn. URLs never change.
3. The order is 6.1, then 6.2, then 6.3, then 6.4.
4. Each sprint merges as one branch and one build, approved on screenshots first.

**6.1 shipped.** Jack approved the contact sheets on 11 October (the time was not stated to the
session). One merge, `325386b` (branch `one-look`, `7daaf4f` and `f63e00e`), pushed 2:39:44 PM EDT
(18:39:44Z), canary exit 0 on the rebuilt merged tree, production stamp `325386b` built
18:41:37Z, ready 18:43:47Z.
- **One name:** GoCheckMyCrypto everywhere a reader or a crawler sees a name. The sweep over the
  published tree (`scripts/one_look_sweep.py`): "Cronkite" 10,504 hits to 0, persona phrases 9 to 0,
  wash and decoration 820 to 0. One URL keeps the old name, `/articles/why-crypto-cronkite.html`.
  Stored stories still carry `author: Crypto Cronkite`; the renderer prints the one name.
- **One look:** `system.css` loads on every page, `site.css` takes the Program 5 tokens, no wash, no
  photo band, no section marks, no persona art, the Edition page drawn from the site's tokens. The home
  page is unchanged (311 elements, 14 computed properties, 0 differences).
- **The Board** is the home page's eight tiles (`tile.render`), a movers table and a list of the deep
  boards, under a dated Chart Master card that gives way to the Board's own line after one day.
  Deep-board cards and the coin page's cards keep their old components until 6.4.
- **Ride-alongs:** `data/week_calendar.json` retired (`calendar_check` and `week_ahead` read
  `site/data/calendar.json`; staleness reads its own `generated_utc`). The ETF read: Farside blocks
  this container (403) and 10 October 2026 was a Saturday, so the site's Friday 9 October read
  (+$21.1M) is the latest trading day; nothing changed.
- **Production reads (home_budget, 11 October 2:45 PM EDT onward, stamp asserted on each):** 15 pages
  (home, Board, Flows, Charts, News, Brief, Record, Learn, About, three coins, two stories, the 10
  October Edition) at 375 and 1440, light and dark: all stamped `325386b`, overflow 0, 104,327 to
  148,424 bytes each, home 108,333 to 110,019. Home LCP at 375 light 2,212 ms (one throttled run).
  The inner pages load Cloudflare's analytics beacon (a third host), so `home_budget.mjs` exits 1 on
  them by its own rule; the home page loads none. The band contrast test passes on production.
- **Counts of record:** crypto production 4 ready and 1 canceled for 11 October, read 2:45:00 PM EDT
  (5 min 16 s after the push). The merge was the fourth ready. If the canceled deploy counts against
  the allowance, today's five are spent and the evening Edition is the sixth; Jack's call.

**For 6.2: why the documents-only push `0c47b73` built.** `netlify_ignore.py` skips only paths under
`docs/`, `shots/`, `review-queue/`, markdown outside `site/`, the ledger and inactives snapshots.
`scripts/` is not on the list, though U-11's prose says scripts outside the published tree do not
build. The commit before it, `d2b8154`, changed `scripts/band_contrast.mjs` and carried
`[skip netlify]`, so Netlify never built it, and the ignore script diffs against the last BUILT
commit (`aa64f08`): that diff still held `scripts/band_contrast.mjs`, which forced a build.
Reproduced locally with `CACHED_COMMIT_REF=aa64f08 COMMIT_REF=0c47b73 python3 netlify_ignore.py`
(exit 1, "1 file(s) that change the site, e.g. scripts/band_contrast.mjs"). Options: add `scripts/`
to `DOC_PREFIXES` (no script is read by the build command), or never put `[skip netlify]` on a commit
that touches a path the ignore script would build for.

## 7d. Program 6, Sprint 6.2: the ignore rule, and the home page edited (11 October 2026)

Run on 11 October from the strategy desk's opener written for 12 October. RULES hash
`4179b2ac...b3568d`, the opener's; `origin/main` at start `f03f147`.
- **Item 0, the ignore rule, merge `dc4d8f5`** (branch `ignore-scripts`, `0f36bed`), pushed
  4:09:12 PM EDT. `scripts/` is on `DOC_PREFIXES` except `scripts/og_render.py`, which
  `site_build` imports (`BUILD_READS`). The new reads check found the opposite hole too:
  `learn/*.md` are rendered by the build but `DOC_SUFFIXES` skipped them, so they now always
  build (`BUILD_READ_PREFIXES`). `verify_pipeline.py` is on `DOC_FILES` (no build step reads
  it). Replay `CACHED_COMMIT_REF=aa64f08 COMMIT_REF=0c47b73`: old script exit 1, new exit 0.
  Canary `_ignore_reads_canary` records every path the stamp canary's build opens for reading
  and fails on a tool or document file the build never reads that would build, or one it reads
  that would be skipped. The push did not build: Netlify "Canceled build due to no content
  change" for `dc4d8f5`, production stayed `325386b`.
- **Item 1, the home page, merge `3c0665e`** (branch `home-edit`, `e2f3b4c`), Jack's yes on
  the contact sheets, pushed 4:53:57 PM EDT, production `3c0665e` built 20:56:49Z. The tape is
  the one place Bitcoin's day change prints. The band's small line names its readings with no
  figures (`narrative.band_names`); since yesterday is the 200-day line and Bitcoin's share of
  the market. Each reading prints once: the Board below the fold drops everything in
  `home.ABOVE_READINGS` (it shows Network fees only), the movers skip the tape's coins, and
  the tape shows Total cap at every width. The tape chart draws the week's daily closes across
  the tape (72 px phone, 96 px desktop), with a 12 percent fill, the low and high CLOSE marked
  with their figures, and a dot on the last point. It draws once and shows whole under reduced
  motion. The snapshot's hourly week low and high are no longer printed, because they are not
  on the line. Tile text was cut, and the explanations moved to `tile.READINGS` on Learn.
- **Counts of record, 11 October:** after item 0, 4 ready and 2 canceled (read 4:15:57 PM,
  push + 6 min 45 s). After item 1, 5 ready and 2 canceled (read 4:59:14 PM, push + 5 min
  17 s). Both canceled entries are ignore-script skips. Today's five builds are spent, so the
  evening Edition's push is the sixth. Jack's call.
- **Open:** "Since yesterday" no longer carries a since-yesterday change; its name is Sprint
  6.3's. Canaries leave `site/data/chartmaster/2026-10-08.json` and
  `site/data/snapshots/pulse-2026-10-11.json` untracked after every run (true before this
  sprint). This file is over U-1's 300 lines.

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

**7 October 2026.** A Claude Code cloud session, which clones this repository alone and cannot
read that path, reads `docs/RULES.md`, the verified copy of U-1 to U-16, before building anything.
**7 October 2026.** It checks that copy's hash against the opener's (`awk 'f{print} /^---$/ && !f {f=1}' docs/RULES.md | tail -n +2 | sha256sum`), and a different hash is said in the report and nothing is built until Jack restores the copy.

## U-14 to U-16, copied verbatim from the Weather handoff (`../gocheckmyweather/docs/HANDOFF.md`)

U-14, U-15 of 2026-10-05, 12:03 PM ET; U-16 of 2026-10-05, 9:28 PM ET.

**U-14. A push is gated on the preflight's exit status.** `preflight && push`, never chained with a semicolon or a newline; a red preflight means no push, under load or not, and a green rerun is a reason to push then, not a reason the first push was fine (the process error of 2026-10-05).

**U-15. The preflight runner prints the name of every failing case, never a count alone.** A red that cannot be named cannot be fixed. The load average is printed at each preflight (`scripts/preflight.py`, start and end) and reported: 48 to 88 is one desk, 300 to 970 is two desks at once, and Jack keeps that rule, not the desk.

**U-16. A suite's output goes to a file and is read after the suite exits.** It is never piped into head, tail, a pager or anything that can close the pipe early: a closed pipe kills the suite before its finally runs, and its server stays up as an orphan on its port (the two orphaned servers of 2026-10-05, both the desk's own). The preflight's red on an orphaned port is the rule working, not noise. (2026-10-05, 9:28 PM ET.)
