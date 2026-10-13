# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `docs/PROGRAM-5-2026-10-05.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 13 October 2026, Program 6 Sprint 6.4 built, not merged (section 11). Before it, Program 7 Sprint 7.2 merged (section 10). Before it, Sprint 7.1 merged (section 9). Before it, Program 6 Sprint 6.3 merged (section 7e, moved). Before it, Sprint 6.2 (section 7d), Sprint 6.1 (section 7c, moved). Earlier that day, 9:20 AM EDT: Sprint 2's close (section 7b) and the band-ink merge `aa64f08`. Before that, the close of 8 October (section 7), written late: the 8 October
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
  **Amended 12 October 2026 (Jack, 5:30 PM): the noon refresh is retired as a schedule and kept only as the Worker's fallback** (it fires at noon ET only if no morning-read run is confirmed green or running that day, so a normal day has no noon build). The morning
  read's build (about 8:15 AM Eastern, dispatched by the Worker) replaces it, so the
  automatic builds are TWO a day, the morning read and the 7:08 PM Edition, and the
  merges' share is three. The allowance stays 5. `docs/RULES.md` does not name the noon
  refresh and is hash-protected, so it is unchanged.
- **K-8** waits on Jack's Worker deploy. The COUNTS namespace was created and bound on
  24 September; the deploy carries all four routes.
- **K-1 reads built output.** The canary compares the built `news.html` against the content
  directory, so a pull that brings in a story without a rebuild shows up as a red canary that
  is not a defect. Regenerate first, which is what U-10 asks (24 September: it came up red on
  the 2026-09-23 XRP story and went green on a rebuild with no code change).
---

## 6. The data contract and Program 5 Sprint 1a (6 October): moved whole to `docs/HANDOFF-2026-10-06.md` (U-1).

## 7. Sprint 1b (7 October) and the 8 October merges: moved whole to `docs/HANDOFF-2026-10-08.md` (U-1).

## 7b. Sprint 2's close (8 to 10 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

## 7c. Program 6, Sprint 6.1 (11 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

## 7d. Program 6, Sprint 6.2 (11 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

## 7e. Program 6, Sprint 6.3 (11 and 12 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

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


## 9. Program 7, Sprint 7.1: the new look, everywhere (12 October 2026)

**Jack's rulings, Monday 12 October 2026** (recorded in his words):
1. Sprint 6.3 is accepted: merged at 0ae8b0f, closed at f7cd67a.
2. Program 6's flat look read worse than the old site: "the layout improved, but the older one looked better visually." The layout stays. The look is replaced by the approved design, "A, the front page in color, with glow" (strategy desk canvas, October 12).
3. Sprint 6.4 (coin pages and the Top 100) waits until this sprint merges, so nothing new is built on the flat look.
4. A figure's color and arrow must always agree with the number printed beside it. The site never shows Bitcoin in green beside a line that says it is down.

**Jack's yes, 3:00 PM ET, with one fix, and its rulings:** each chart is colored by its own window (the week's line by the 7-day change, first close to last point, never the 24-hour badge); every line chart on the site the same. Accepted as built: the Brief card in the band's place (the Brief block below the fold is gone, nothing twice), the mood as the Fear & Greed gauge alone (funding in the money, open interest on the Board below), the masthead stamp that reads UPDATED and lights LIVE only after the live read answers, and 7:08 PM ET as the next-Brief time (the cron).

**Merged `4194c5b`** (real merge of `glow-look` `01a68f6` into `320a1e6`), pushed 3:17:20 PM EDT; production stamp `4194c5b` built 19:20:13Z; 32 production reads clean; count of record 4 ready, 1 canceled at 3:22:53 PM (the 7:08 PM Edition is the day's fifth). Report: `docs/REPORT-PROGRAM-7-SPRINT-7.1-2026-10-12.md`.

**The tokens** (`site/assets/system.css`, light / dark): ground #FFFFFF / #0B1422; card #FFFFFF / #13203A; ink #0F1B2D / #E8EEF7; muted #4A5568 / #A9B6CC; faint #6B7280 / #8E9BB3; line #E6EAF0 / #24314D; up text #0B6E3B / #4ADE80, up tint #EAF7EF / #123227, up line #12A05A / #4ADE80; down text #A51F15 / #FF6B5E, down tint #FDECEA / #3A1820, down line #E0301F / #FF6B5E; eyebrow red #C8261B / #FF7A6E; brand coral #FF6B5E; live green #7CFFB0; amber #F5A800, mood card #FFF6E5 / #2A2312, mood word #8A5A00 / #F5C75A; masthead band #0F1B2D / #060D19; Brief card #0F1B2D / #162A4D. Old names (`--paper`, `--rule`) are aliases. Type: Newsreader 700 (headlines, masthead; `newsreader-roman.woff2` now 400 to 700, plus a 2 KB `newsreader-italic-700.woff2` for "Crypto"), IBM Plex Mono 700 (every figure, stamp, eyebrow), IBM Plex Sans 400 to 600 (`plexsans.woff2`, replaces Inter, which is deleted).

**The glow rules:** glow only on data (chart lines and dots, the live dot, change badges, the gauge arc, the 200-day bar, the Brief card's edge), never on text, labels or navigation; never lowers contrast (every pair 4.5:1, 3:1 at 24 px and up or 19 px bold: the light up badge, white on #12A05A, is 3.39:1 at 19 px bold); static, no pulsing. One line style for every chart, `glow.py`: 3 px in the chart's own window's direction, gaussian blur stdDeviation 4 merged twice under the line, high and low as white dots ringed green and red, the last point a 6 px dot on a radius-16 halo. The shared filter's region is absolute user units (a percentage in user space resolves against the 0 by 0 defs SVG and erases the line).

**Color truth:** `tile.render(change=, since_change=)`; the figure's color is its same-window change, the since line has its own arrow and color. The narrative line never quotes a percentage (writer, prompt, render belt `home.band_line`, `_color_truth_canary`). `scripts/color_truth_test.py` is the fixture.

**Traps found:** the U-11 reads canary counts every module in `sys.modules` as a build read, so a canary that imports from `scripts/` must take the module out again. The home canary's fold regex is anchored on `<div class="h-below"`.

**Open:** the coin page chart product is 6.4's (only its line, dots and colors changed here). Sprint 7.2 gets its own session.

## 10. Program 7, Sprint 7.2: the morning edition, the Chart Master that publishes, the beacon (12 October 2026)

**Jack's rulings, Monday 12 October 2026, 3:29 PM ET:** (1) the Cloudflare Web Analytics beacon stays, on every page, the home page included; it is cookie-free, the page-weight rule names it, the privacy page says so in one plain line. (2) Crypto gets a morning edition; the site must never read as last night's in the morning.

**Jack approved 5:30 PM ET 12 October with four changes** (all made): the Chart Master substitution table is REMOVED (a flagged sentence is dropped, a flagged headline becomes a data headline built from the levels, fewer than two sentences left publishes the data-only card; nothing is ever reworded); the ledger date reads the night's own date; the noon refresh is retired; the Worker change is written on `gcm-newsroom`. Merge Tuesday 13 October, 6:00 to 8:00 AM ET, canary green first. (Earlier state text follows.) **MERGED Tuesday 13 October 2026, 6:14:27 AM ET: merge `c823b31`, main `35278fe` (the canary's clock-pin fix on top). Production stamp `35278fe` built 10:17:21Z; the count of record for 13 October read 1 ready at 6:19:47 AM (merge build); production reads clean (one beacon on home, /privacy, /chartmaster, /pulse; home 110.9 KB at 375 on the wire, LCP 1,096 ms). NOT YET LIVE: the morning run. At 8:34 AM ET no `morning-read.yml` run had happened: the Worker (`gcm-newsroom` `morning-dispatch`) was not deployed, and the 8:17 AM EDT cron backstop had not fired. Not dispatched by hand without Jack.** (Earlier state: built on `claude/laughing-rubin-j8g33g`, canary green.) Report: `docs/REPORT-PROGRAM-7-SPRINT-7.2-2026-10-12.md`. Count of record on 12 October: 4 ready, 2 canceled, the Edition is the fifth, so the merge waits for 13 October after midnight ET and must sit outside 6:30 to 8:15 PM ET. Jack approves on `shots/program7-7.2/`.

**Open for the next session:**
1. **The Worker change is written and tested** on `gcm-newsroom` branch `morning-dispatch` (`slot-trigger/src/worker.js`, `test/morning.test.mjs`); NOT deployed. The line that was here before: **(superseded)** Dispatch `morning-read.yml` (workflow_dispatch, ref main) at 8:15 AM in America/New_York computed with Intl, so it holds across 1 November; retire the Worker's noon refresh hook so the automatic builds stay at two. Check the Worker's real refresh time: `site-refresh.yml` says noon Eastern, the brief said 8:00 AM EDT.
2. After the merge: read production by stamp, the count five minutes after the push, then the next morning's 8:15 AM run on production, its tokens and dollars (none measured yet).
3. Jack's yes.

**What exists:** `morning.py` (`--guard`, `--message`, `--alarm`), `prompts/morning.md`, `morning-read.yml` (crons `17 12 * * *` EDT and `17 13 * * *` EST as backstops), `home.next_brief` read off the Eastern clock, `home.usable_morning`, `home.last_brief_note`; Chart Master `publish_path` (told retry, drop flagged sentences, `data_headline`, data-only card, `data/chartmaster-ledger.json`); `_beacon_canary`; `ops_ledger.is_empty_row`. Tests: `scripts/morning_test.py`, `scripts/chartmaster_publish_test.py`, both in the canary.

**Traps:** the Oct 10 refusal was a venue belt, not an advice word. Refused reads are not stored, so fixtures are reconstructions. A canary run takes several minutes and imports site files: do not edit them while it runs (inspect.getsource goes stale and reports false reds).

## 11. Program 6, Sprint 6.4: the coin pages and the Top 100, in the new look (13 October 2026)

**Jack's rulings, Tuesday 13 October 2026:** (1) Sprint 6.4 runs now, on Program 7's look: its tokens, type, glow rules and color truth (each chart colored by its own window; a figure's color matches the change printed beside it). (2) October 7 still stands: the wire stays in re-count order, and the checked item is never pinned to the top.

**Jack approved 12:45 PM ET with four fixes (all made, in the report): volume bars on 1M and 1Y only; the 50 and 200-day lines smooth, labeled in the right gutter; the Top 100 stamp read in production (it refreshes at every build, nothing to change); a clear gap between price and 24h pill at 375. Pages are at +9.0% after the fifth fix squeezed the script's operator spaces; stripping CSS comments at publish (40 KB) would give far more room and was not done unasked. Re-shot, waiting for his yes.**

**Jack approved again at 1:20 PM ET with a fifth fix (1M and 1Y fetch 565 days so both averages are daily curves across the whole window, never bridged; falls back to 365 if the public API refuses; unverified live, read the first 1Y after the merge) and permission to merge unattended; weights now +9.0%. Report has the merge facts.**

**State: BUILT, NOT MERGED.** Branch `claude/sweet-wright-s8j2we` (the brief named it `coin-pages`; the cloud session was bound to this branch name). Waits for Jack's yes on `shots/program7-6.4/`; one real merge commit after it, outside 6:30 to 8:15 PM ET. Report: `docs/REPORT-PROGRAM-6-SPRINT-6.4-2026-10-13.md`.

**What exists:** `site/assets/coinchart.js` (the chart, one shared file, comments squeezed at publish by `site_build.squeeze_js`), `coinpage.py` (row sparkline, readings tiles, Chart Master card, wire stories, unlock line), seven new `tile.READINGS` (`coin-price`, `coin-24h`, `coin-7d`, `coin-cap`, `coin-volume`, `coin-200d`, `rsi-14`), `COLD_*` constants (one copy, two looks), search and sort on the Top 100 (`TOP100_JS`), CSS in `system.css` (`.cc-*`, `.cn-*`, `.coin-*`). Tests: `scripts/coin_pages_test.py` (unit, static, browser) and `scripts/coin_pages_browser.mjs`, in the canary as `_coin_pages_canary`; `scripts/chart_closeups.mjs`; `fixtures/coingecko/` (recorded market_chart for bitcoin, ethereum, aptos).

**Traps:** CoinGecko's `total_volumes` is a trailing 24-hour figure at every point, so on 1D and 7D every bar is the same height: no bars there, bars on 1M and 1Y (daily volumes). The 50 and 200-day lines are averages of daily closes, so 1M and 1Y both read the 365-day series. The sort buttons on the Top 100 had no script since the live JS was removed; they work now. Playwright cannot click a cell whose row link overlays it: the row test taps by coordinates. The K-7 and data-contract canaries read the old coin-page markup and were rewritten to the new one, same invariants.

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
