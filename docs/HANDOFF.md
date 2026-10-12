# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `docs/PROGRAM-5-2026-10-05.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 12 October 2026, Program 6 Sprint 6.3 merged (section 7e). Before it, Sprint 6.2 (section 7d), Sprint 6.1 (section 7c, moved). Earlier that day, 9:20 AM EDT: Sprint 2's close (section 7b) and the band-ink merge `aa64f08`. Before that, the close of 8 October (section 7), written late: the 8 October
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

## 6. The data contract and Program 5 Sprint 1a (6 October): moved whole to `docs/HANDOFF-2026-10-06.md` (U-1).

## 7. Sprint 1b (7 October) and the 8 October merges: moved whole to `docs/HANDOFF-2026-10-08.md` (U-1).

## 7b. Sprint 2's close (8 to 10 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

## 7c. Program 6, Sprint 6.1 (11 October): moved whole to `docs/HANDOFF-2026-10-11.md` (U-1).

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

## 7e. Program 6, Sprint 6.3: navigation and names (11 October 2026, 7:05 PM EDT; written Monday's session)

**Jack's rulings, Sunday 11 October 2026:** (1) Sprint 6.2 is accepted: the ignore rule `dc4d8f5`
and the home edit `3c0665e`, closed at `9fe3f7e`. (2) On a day when the five builds are used up,
the evening Edition still runs. The Edition outranks the allowance, and the report notes the
overage.

RULES hash `4179b2ac...b3568d`, matched. `origin/main` at start `9fe3f7e`. Nothing was pushed:
the session ran inside the 6:30 to 8:15 PM ET window, and the merge waits for Jack's yes on the
contact sheets (`shots/program6-6.3/`).
- **Items 0 to 2, branch `nav-names`, local commit `f358afc`, NOT merged.** `site_build.NAMES` is
  the one table (task name, brand name, URL); nav, tab bar, footer, H1, eyebrow, title tag all
  read it. Markets (The Board), Flows (Whale Watch), Charts (Chart Master), News (Checked), Brief
  (The Edition), Record (Worth keeping), Learn (The Board explained). Below 700 px the top row is
  hidden and a five-tab bar shows (56 px targets, `env(safe-area-inset-bottom)`, `viewport-fit=cover`,
  a bar across the top of the current tab plus `aria-current`). Record and Learn are in the footer,
  search does not exist yet. Home and About stay in the desktop row. The active mark comes from
  the URL (`nav_group`), not from the label each caller passed. Item 2 is not applied: see the report.
- **Item 3, branch `nav-names-close`, done.** `layer1_canary` runs with `CM_ARCHIVE` and
  `SNAPSHOT_DIR` on a scratch copy (the live-layer canary's home render wrote the two files);
  `scripts/canary_clean_test.py` was red on main (two files left), green after.
- **Item 4, branch `nav-names-close`, done:** sections 6, 7, 7b and 7c moved whole to the day files.
- **Jack's yes and rulings (11 October, 7:2x PM):** "Since yesterday" is "Where Bitcoin stands"; the edition
  card is "The Brief"; Home and About as built.
- **Merged 12 October, 8:30:55 AM EDT: `0ae8b0f`**, production stamp read `0ae8b0f` built 12:34:55Z; 32 reads at
  375 and 1440 in both modes clean (report). Netlify count not readable from the container: Jack reads it.
- **Close merged after (documents and scripts only, ignore rule).** Sprint 6.4 gets its own session.

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
