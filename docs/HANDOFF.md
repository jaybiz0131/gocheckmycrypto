# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `docs/PROGRAM-5-2026-10-05.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 14 October 2026, Program 7 Sprint 7.3 MERGED `5bb4df7`, 8:44 AM ET (section 13). Before it, Sprints 6.5, 6.4, 7.2 and 7.1 merged (sections 9 to 12, moved). Before it, Sprint 7.1 merged (section 9). Before it, Program 6 Sprint 6.3 merged (section 7e, moved). Before it, Sprint 6.2 (section 7d), Sprint 6.1 (section 7c, moved). Earlier that day, 9:20 AM EDT: Sprint 2's close (section 7b) and the band-ink merge `aa64f08`. Before that, the close of 8 October (section 7), written late: the 8 October
evening wake-up reached the session on 11 October. `main` ends at the close commit on top of
`a5bea57`. Days before 23 September live in `HANDOFF-2026-08-17.md`; 23 September to 1 October
in `HANDOFF-2026-09-23-to-10-01.md`; 4 to 8 October in `HANDOFF-2026-10-04.md` to `-10-08.md`
(U-1).

**ITEM 0 IS DONE AND MERGED (section 13):** the twins gate fix, the clause table's sign rule, the ledger's drops, the Whale tags and the funding-band read are merged 14 October at `5bb4df7`; its live proof is the 14 October 7:08 PM Edition's ledger row.

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
- **Crypto copy (V-13) was frozen until Program 6.1** replaced the persona copy with plain copy under the copy law, at Jack's direction; no persona text remains on any live page (read 13 October). Chrome copy still changes only by a Jack ruling.
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

Swept 13 October 2026 (Sprint 7.3, item 3): every row read against the live site; the done and superseded rows are in `docs/REPORT-PROGRAM-7-SPRINT-7.3-2026-10-13.md`, this table holds only what is live.

| Item | Status |
|---|---|
| The twins gate's live proof: the 14 Oct Edition (re-run 7:46 PM ET, run 38655570796) carries `twins_drops: 2`, `twins_unparsed: 0` and a `twins_log` naming two week-sign drops (BTC and ETH), both correct | **read, closed for 14 Oct.** Still open: the first live ETF floor drop, and the first stored `/today/` records (tonight's Edition, tomorrow's 8:15 AM read) |
| The home cadence line still reads "the Brief every evening" now that the morning edition is live | **Done in 8.1 on the branch, pending Jack's yes to merge:** the line is "The Brief, every morning and evening." (Jack, 14 Oct) |
| Unlocks HYPE, WBT, RAIN: all three vesting pages answer 403 to the session (13 Oct); their coin pages print no unlock line | Jack, by hand in a browser |
| `top_n` 6 ranking check, 7 Editions (4 to 10 Oct) now exist | plan: read each Edition's `wire.json` rank of its VERIFIED item from git, write one table, close or change `top_n` |
| Coin pages' 7d tile prints `/coins/markets`' rolling 7 days (labeled so); the Board's week is the stored series' close to close; the two can differ | plan: show both values for the seven stored coins in one table, then Jack decides whether to unify |
| The week field: a coin outside the seven stored series reads six closes in the 23:00 UTC hour | unverified since 7 Oct; plan: one fixture on a coin outside the seven |
| 6.5: the 13-character price tier | **Closed in 8.1, merged 15 Oct:** a price under $0.0001 prints compressed ($0.0₆3682) at normal size, the 10 px tier is removed |
| L-1 the Board on the Worker (`site-refresh.yml` has no cron since 7.2, so builds are the only mover) | open; plan: serve the snapshot from the Worker; needs Jack, it touches the build count |
| R-1 desk reconfiguration | open (Sprint J); no plan written, ask Jack for the brief |
| Whale Watch (`/flows`) at 1440, V-11 punch 6 ("full width") | **Closed (Jack, 14 Oct): punch 6 is superseded by Program 6.** 8.1 measured it: nothing is wider than its column at 1440 (tables 543 and 471 px in a 1036 px page; the By exchange table scrolls in its own box at 375). `scripts/column_fit.mjs` stays as the guard |
| V-13 Crypto copy hold | superseded by Program 6.1 (plain copy under the copy law; no persona text on any live page, read 13 Oct); section 2's bullet updated |

Landed 4 October: A-14 (`/pulse` opens with the Board band at 646px against the
homepage band's 1027, 63%), A-5's ornament (Bitcoin's 30-day closes as a filled area
in #FF6A4D, omitted under 720px), the watermark fetch fix, and the mono-500 font
weight removal.

## 3b. Program 8, Sprint 8.1: the daily answer (14 October 2026)

Jack's rulings, Wednesday 14 October 2026, 10:42 AM ET: (1) Program 8 is approved (`docs/PROGRAM-8-2026-10-14.md`). (2) The home cadence line reads exactly "The Brief, every morning and evening." (`NEWS_CADENCE_LINE`, and the test in `verify_pipeline.py` that pins it). (3) The daily answer makes no new model call and never says "because" unless a cited source does.

What 8.1 built (MERGED 15 October 2026, `3675e45`; production read, see the report): `today.py` composes a record per slot (`site/data/today/YYYY-MM-DD-<slot>.json`, written by `python3 today.py --write` in the morning and Edition workflows); `site_build._write_today` renders /today/ (newest record) and /today/YYYY-MM-DD (the evening record once it exists, else the morning one; a stored record is frozen and a dated page links only earlier days, so a later day cannot change it). Cases: `scripts/sprint81_test.py`, run by the canary. The morning wire block now prints "Re-ranked <time>" from `refreshed_et` (it printed `ranked_et`, the Edition's time). Corrections: a record's `corrections` list renders under the answer.

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


## 9 to 12. Program 7 Sprints 7.1 and 7.2, Program 6 Sprints 6.4 and 6.5 (12 and 13 October): moved whole to `docs/HANDOFF-2026-10-13.md` (U-1).

Standing facts from them: the look is `site/assets/system.css` (tokens in that file), the glow rules and color truth hold on every chart and figure, the narrative line never quotes a percentage, the Cloudflare beacon stays on every page, the morning edition exists (`morning.py`, `morning-read.yml`) and its live proof is Wednesday 14 October after the 8:15 AM ET run, the 50 and 200-day lines start where their history starts, and a canary run takes minutes and imports site files, so no site file is edited while it runs (inspect.getsource goes stale and reports false reds; it did again on 13 October).

## 13. Program 7, Sprint 7.3: the writing tells the truth (13 October 2026)

**Jack's rulings, Tuesday 13 October 2026:** (1) The site's promise is fact-based and no hype, so a true sentence must never be cut and a false pairing must never print. The gate's job is to catch wrong claims, not to thin out right ones. (2) A sentence the gate cannot parse is not dropped silently. It is logged in the ledger with the reason, and the drop is counted in the night's report.

**State: MERGED Wednesday 14 October 2026, 8:44:07 AM ET: merge `5bb4df7` (parents `a90286f` and `f99b624`, one real merge commit, no conflicts), pushed to `main`. Canary green on the merged tree (exit 0). Production stamp `5bb4df7`, built 12:44:41Z, read at 8:47 AM ET at 375 and 1440: the tape's "24h high $84,025 · low $82,919" and "7D HIGH $83,457 / LOW $81,630" equal the `/coins/btc` data attributes, caption and the labels the chart draws on 1D and 7D; no overflow. The morning edition (run 3, 8:16 AM ET dispatch) published a read: 1,090 tokens, $0.0019, no fallback. OPEN FOR THE NEXT SESSION: the 14 Oct 7:08 PM ET Edition's ledger row (`twins_drops`, `twins_unparsed`, `twins_log`).** Jack approved 13 Oct 9:25 PM ET on `shots/program7-7.3/` and the replay table. Report: `docs/REPORT-PROGRAM-7-SPRINT-7.3-2026-10-13.md`.

**What changed:** `twins_gate.py` reads a sentence by clause. A window is any phrase `WINDOW_RE` names (hyphenated and numbered forms included); each direction word gets its own window, bound to the nearest one in its clause; a direction word binds to the subject it modifies (an adjective takes what follows, a predicate takes a Board reading before it, a coin name is the weakest subject, and a clause with none takes the nearest subject before it); funding is read for every coin the clause names; a short quoted word is not a claim; `falling` and kin are sign words. A claim in a window the snapshot does not carry is unverifiable and stands. Unparsed sentences (odd quotation marks, a check that raises) are dropped with kind `unparsed`, a `::warning::`, and counted: `gate.report()`, `out/twins-gate.json` `counts`, and the ops-ledger row's `twins_drops`, `twins_unparsed`, `twins_log`. `narrative._tape_clause` says "on" only when the ETF net's sign supports the direction, else "while spot ETFs saw inflows/outflows". The `exchanges` tag no longer matches `custody` or `shuts down`/`winds down` (34 of 561 stories lost it). The canary now fails if `build()` stops calling `publish_narrative`. `scripts/morning_test.py` no longer overwrites `site/data/narrative.json`.

**Tests:** `scripts/twins_gate_test.py` (43 cases: the eight recorded drops, seven true negatives, the replay's find, the five causes alone, unparsed, the clause table's six sign cases, the ledger fields, the Whale tags, the three unlock pages), in the canary as `_sprint73_canary`; `scripts/twins_replay.py` prints the replay table; `scripts/gate_shots.mjs` made the screenshots.

**Follow-up, the evening of 13 October:** (1) Runs 399 to 402 (Monday's Edition, its two retries and the late cron) all died in the canary within a second: `scripts/color_truth_test.py` opened the gitignored `site/data/snapshot.json`, absent on a fresh CI checkout; fixed on main by 7.2's `95b14a1` (merged after them); tonight's run 403 passed that canary on CI, published (`8aea846`) and the day's count is 5 ready, 4 canceled. (2) Bitcoin's high and low are one figure per window: the tape's HIGH/LOW are the 7D closes pair and now say "7D"; `high_24h`/`low_24h` are a snapshot field (`snapshot.day_pair`), printed on the tape and on `/coins/btc`'s 1D chart; 1M and 1Y say their window; `scripts/btc_hilo_test.py` fails when the pages differ (`--fast` is in the canary). (3) The old gate cut an eighth true sentence at 7:17 PM (an Ether ETF sentence read against Bitcoin's ETF net); fixed, fixture F8. Whale Watch's 1440 width is logged in the table.

**Traps:** the old gate's "week" test fired on any week word anywhere in the sentence, even "multi-week"; a direction word's nearest coin name is not its subject; a first cut of this fix bound "exchange inflows" to the ETF net and would have cut the 9 October dek, which the replay caught; the reconstruction of F7 (the narrative line) is the only fixture text not verbatim, and a narrative line with a percentage is refused by `narrative.quotes_change` anyway since 6.2. The full text of every gate drop is in `wrap-status.json` inside the run's `crypto-review-queue` artifact (90 days).


---

## 14. Program 8, Sprint 8.2: the coin doors, the numbers handed over labeled (15 October 2026)
**MERGED 15 October 2026, pushed 8:24:36 PM ET, merge `97fe676`** (Jack's yes; canary PASS on the merged tree). Report: `docs/REPORT-PROGRAM-8-SPRINT-8.2-2026-10-15.md`. Production stamp `commit 97fe676, built 2026-10-16T00:27:31+00:00`.
- Numbers reach a model only as finished phrases (`phrases.py`); the twins gate sets a missing sign word on a figure that is the series' own (never on a wrong one); the morning headline says why it failed and is repaired on the last rung; "below/above/under/over/past $N" is a level, not a price claim.
- Coin pages: "<Coin> price today and why it moved" title, description from the day's numbers, BreadcrumbList, "Why <coin> moved today" (top 20, items inside the 24 hours ending at the Board read, cause and gate rules), real-change-time sitemap lastmod (`lastmod.py`), IndexNow (`indexnow.py`, `plugins/indexnow`, key `a44f710d9349e5f84a1c0bbae18b03c5`).

**8.3 list, top first (Jack, 15 October):**
1. The coin chart's series stops at Oct 13 while the price reads Oct 15, so "7D low $81,630" is false beside $80,896. The chart must run to the current reading and its high and low labels must match it.
2. Chart Master's read on the coin page opens mid-sentence with "However,". Lift whole sentences only.
3. Seen on production: the Why block's "2 sources: Decrypt, Decrypt, Bitcoin Magazine" lists an outlet twice and counts two (stories_html).
4. Twins gate: a direction word in a clause about an exchange or whale movement must not bind to the stablecoin float reading (the 7:49 PM drop, tail logged at 140 characters, the ledger at 70: log the whole sentence).
5. Consistency-gate withhold of the Edition: one visible line on the run, and `today.py` must not store a morning record from an evening run (see the report, the two Editions of 15 October).
6. Then the share loop as Program 8 states.

## 15. The deep audit, 16 October 2026 (documents only)
`docs/audit-2026-10/AUDIT.md` (scores, the competition, the plan, Program 9's proposed sequence), `NAMES.md` (renames for Jack to pick), `shots/` (production `9c8af54`, 375 and 1440, light and dark). Overall 4.4 of 10. Nothing built; Program 9 waits on Jack's eight decisions (AUDIT.md section 4). Found live and open, beyond the 8.3 list:
- The whole-market 24h change (`market_pulse.py:564`, CoinGecko `/global`) contradicts Bitcoin and Ether on 15 and 16 October.
- Whale Watch prints net stablecoins "onto exchanges" for transfers that left them.
- The 15 October PPI wire line carries a cause and figures its linked CoinDesk source does not.
- `/today/` dated pages can freeze the wrong direction.
- `llm.py:231` would 400 every `claude-sonnet-5-5` call, and `PRICING` lacks the 5.5 models.

If Jack approves, 8.3's items 1 to 5 fold into Sprint 9.1.

## 16. Program 9: Jack's rulings (16 October 2026)
Jack adopted the deep audit's plan (`docs/audit-2026-10/AUDIT.md`, commit `18a156e`) on 16 October 2026 and ruled on its decisions. Sprint 9.1 replaces Sprint 8.3: 8.3's fix list folds into 9.1 and its share loop moves to 9.6. No new model calls in 9.1.
1. The desk may print "Likely" when its own timing test and mechanics agree. "because" stays for Confirmed.
2. New model spend of about $0.60 to $1.30 a day for the why, capped at $1.50 a day.
3. Names as `docs/audit-2026-10/NAMES.md` recommends: "Why it moved", "Unclear" with "No reported event lines up with this move", "Big movers", and the recommended column of its section 4 in full.
4. No AI disclosure on the site. The editor is "Crypto Cronkite"; no personal name or details anywhere. The site never claims a human wrote or hand-checked what it did not. "How we check" describes the process truthfully: automated source and timing checks, reviewed by the editor. Keep the corrections log. (This overrules AUDIT.md decision 4's AI-disclosure half.)
5. Graded verdict pages become the desk's articles.
6. Market-move breaking trigger on, crypto only, inside the two-a-day limit.
7. The Worker live-price route in 9.7.
8. Order: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, with 8.4 on its Monday schedule.

## 17. Program 9, Sprint 9.1: numbers that agree (16 October 2026)
**MERGED 16 October 2026, pushed 9:37:49 PM ET, merge `8d955d7`** (Jack's yes; branch tip `ff52578` pushed first, `git branch -r --contains` shows `origin/main`; canary PASS on the merged tree). Production stamp `commit 8d955d7, built 2026-10-17T01:43:28+00:00`; a data correction `df30e8f` followed (stamp built 01:51:17Z). Builds on the 16 October ET date by stamp: 9c8af54, 7cb577f, 8d955d7, df30e8f (four). Report: `docs/REPORT-PROGRAM-9-SPRINT-9.1-2026-10-16.md`. Red-on-main log: `docs/sprint91-red-on-main.log` (53 FAIL on `18a156e`, PASS on the branch); the cases are `scripts/sprint91_test.py`, wired into the canary.
- Whole-market change checked against the Top 100's own figure, Bitcoin and Ether, else withheld as "unchecked" (`snapshot.check_market_change`); stablecoin sign (`stable_flow_words`); one 7-day figure per coin page; movers rules (`snapshot.mover_rows`); no false "live"; the stale state (`data-asof`, `/assets/asof.js`); `/today/`'s direction is the ET day's (`market_pulse.et_open`, `chg_et_day_pct`); "What was reported"; the wire source check (`wire.source_check`); 8.3 items 1 to 5; `llm.thinking_param` and 5.5 prices.
- **The brief's premise that 15 October was a down day did not hold** (Kraken: +1.48% midnight ET to midnight ET). No direction correction was made; the page's unsupported wire line and contradicting whole-market figure were corrected with visible correction lines, and the same figure was removed from the 16 October morning record.
- The brief was cut off at item 9; scope past it was taken from AUDIT.md row 9.1.
- Found: origin/main's canary was red on `top100-sparkline` (ALGO); fixed in `row_spark`.
- **One Edition per evening** (Jack's added item): `slot_guard.py`, wired into the slot guard in `crypto-news-brief.yml`; ledger rows now carry `slot`, `slot_day` and `edition_published`. Red on main: `docs/slotguard-red-on-main.log` (19 FAIL), `scripts/slot_guard_test.py`, in the canary. The 15 October pair: run 38822001905 (workflow_dispatch, 7:10 PM ET, ledger 160c657) and run 38825025985 (workflow_dispatch, 7:40 PM, ledger 00a405e), both the Worker's dispatches under Jack's token, not the schedule (its own tick fired at 01:11 UTC on the 16th) and not the catch-up cron. The first was withheld at the consistency gate (no Edition file), so the old guard, which asked only whether the Edition was on origin/main, let the second spend a full run.
- Open for Jack (was): the merge (outside 6:30 to 8:15 PM ET, one real merge commit, push the tip first, `git branch --contains`, count five minutes after); after it, the first run writes `open_et` and the ET-day direction goes live (until then the rolling-24-hour fallback, said in `direction_basis`).

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
