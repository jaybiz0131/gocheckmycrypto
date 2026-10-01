# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `PROGRAM-4-2026-09-16.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 1 October 2026, end of the merge-and-Cause-B session.
`main` ended at 021c116. `build-stamp` and `cause-b-stamp-proof` are MERGED and
DELETED. One local branch remains and is not this session's: `family-map-home-sections`.
Days before 23 September live in `HANDOFF-2026-08-17.md`; 23 September to
1 October live in `HANDOFF-2026-09-23-to-10-01.md` (U-1).

The Sports handoff (`../gocheckmysports/HANDOFF.md`, the file at that repo's root,
not the one in its `docs/`) carries the shared laws,
the shared traps and the command list. This file carries what is different here.

## 1. Where things live

Boards and packages in `../gcm-tools/`: `program-4-2026-09-16/` (Program 4,
ScoreboardC), `program-3-2026-09-15/` (Program 3, StyleTile, WhaleWatchPage and
ChartMasterPage on canvas row ten), `site-audit-2026-09-14/`. Worker in
`../gcm-newsroom/slot-trigger/`.

## 2. What is different on this desk

- **Crypto copy is frozen (V-13).** Jack has not reviewed this desk against the copy
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
| V-13 Crypto copy | **hold** |
| L-1 the Board on the Worker | open, Sprint I |
| R-1 desk reconfiguration | open, Sprint J |

Landed this session: A-14 (`/pulse` opens with the Board band at 646px against the
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

## Where this session ended (1 October 2026, evening)

- `main` is **`021c116`**, pushed and verified by hash, and live: the page's own `/stamp.txt`
  read `021c11677f6d` at 23:13:01Z. It carries the U-13 canaries, Cause A's workflow fix,
  Cause B's rebuilt stamp canary, the cleanup fix, the closes, and option two.
- **Cause A is live on `main`.** `site-refresh.yml` no longer carries an `on: schedule:` key
  with every cron line commented out, so it stops creating a zero-job run that fails on every
  push. `_workflow_canary` keeps it from coming back.
- **Cause B is fixed** at `c2b2d6b`. The stamp canary builds its own tree; see the history file
  for the four plants and the three traps it had to be careful about.
- The gate now takes about 145 seconds, up from about 60, because it builds the site once per
  run. That is the price of a canary that does not assume an output it did not make.
- Branches: **none open on this desk from this session.** `build-stamp` and
  `cause-b-stamp-proof` were merged and deleted after proving 0 commits outstanding.
  `family-map-home-sections` is older work and was left alone.
- Stashes: **none.**
- Deploys today, from `/counts/today`, the count of record: **5 production builds and 1
  skipped**, against an allowance of 5. The desk finished AT its allowance, not over it.
  Three of the five are this session's: `63557d0`, `c2b2d6b`, `021c116`. The skipped one is
  `da63d83`, the documents-only push, which is the ignore proof.
- **The ignore proof, measured three ways** on `da63d83` at 22:42:25Z: 322 seconds later
  `/stamp.txt` still read `c2b2d6b` built 22:39:48Z; `/counts/today` showed
  `gocheckmycrypto:production:canceled` = 1; and the Worker's `last` line named commit
  `da63d83d459a` with raw `state: "error"`, `"Canceled build due to no content change"`,
  `counted_as: "canceled"`. The closing docs push `e47ec81` skipped the same way, so this desk
  recorded TWO skips today. On Sports the first attempt built and the second skipped; a poller
  build in flight widens the range the ignore rule is given, and the day history says so.
- Open, with the last commit of each: the twins branch, link or retire, which is the FIRST
  order of the next session (`dc5d400`'s classification, no code yet); then S-2 on Sports; then
  the deep-URL register; then Cause C on Sports. A-17's font and poster work is shared with
  Sports and has nothing yet.

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
