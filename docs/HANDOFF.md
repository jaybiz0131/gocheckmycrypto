# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `PROGRAM-4-2026-09-16.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 4 October 2026, end of the one-story-a-day session.
`main` ends at the close commit on top of `c2a2d46` (section 7). `one-story-a-day` and
`whale-sentence` are MERGED and DELETED. One local branch remains and is not this
session's: `family-map-home-sections`. Days before 23 September live in
`HANDOFF-2026-08-17.md`; 23 September to 1 October in `HANDOFF-2026-09-23-to-10-01.md`;
4 October in `HANDOFF-2026-10-04.md` (U-1).

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
| **Data contract: the NEXT session's first order**, named, not started (section 6) | open |
| top_n 6 ranking check, after seven Editions, 4 to 10 Oct (section 6) | open |
| Stamp canary cleanup reverts edits made during its run (section 8) | open |
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

## 6. The next session's first order and the open check

**The data contract (named 4 October, not started).** One snapshot object for price,
dominance, ETF flows, whale net, funding, stablecoin float and Fear & Greed that every
surface reads: ticker, Board, coin page, Top 100 and Brief. The client-side refresh either
refreshes every surface from that one payload and re-stamps them together, or touches only
the ticker, which then says so. Every stamp carries its zone. Chart Master's read carries its
date in its headline and never sits above a live figure it contradicts. The twins check
reads the story's number and the Board's from the same snapshot, which is how it stops being
advisory. After it: S-2 on Sports, then the deep-URL register, then Cause C on Sports.

**The top_n 6 ranking check.** top_n 6 assumes the editor ranks the same way when asked for
six as it did for twelve. Settle it after seven Editions under the cadence (4 to 10 October)
from `ledger.json` and the hold files: if any day's chosen story would have ranked below 6
under the old count, or a day went dark with a story that could have led below the cut,
raise top_n and say to what. First data point, 4 October: chosen at rank 6 of 6, the last
slot.

## 7. Where this session ended (4 October 2026, evening)

- Items 1 to 3 merged at `f733356` (branch `1c5fced`), live by `/stamp.txt` at 16:03:21Z.
- The first Edition under the cadence (run 37242770317, items 23:14:34Z) chose rank 6,
  "Japan sanctions Garantex...", corroborated (`e130708`); held rank 5, the ETF flows story,
  as resting on one secondary outlet, no draft carried, so the 5 October Edition has no held
  story to fall back on. Ledger: 114,399 tokens, $0.1889 (twelve-story runs: $0.3287 to
  $0.6822).
- Item 4 merged at `c2a2d46` (branch `2da8fde`), local = origin, 0 outstanding, pushed
  02:00:33Z after a first push was rejected by a mid-canary ledger row; live by `/stamp.txt`
  at 02:02:40Z. /flows: count 2 = rows 2 = stat 2, ages 29h and 36h, OKX only; home tile
  "2 days net, all coins".
- Deploys 4 October (`/counts/today`, the count of record): 4 production builds before the
  close, against 5: site-refresh, `f733356`, the Edition's `e130708`, `c2a2d46`.
- Stashes: none.

## 8. Traps

- **Two writers.** Everything the build writes is stamped and agrees with itself; the
  client-side refresh then moves some numbers after load and leaves the rest at build time,
  so one page shows two moments under one stamp. The Board and the coin page also read price
  from two endpoints under the one stamp. The data contract retires this.
- **A hardcoded window over a widened reading.** The Board's whale tile said "24h net" while
  `flows.json` had widened to 48 hours, and Whale Watch said nothing moved in 24 hours above
  a 48-hour table aged from its newest move. The same finding as the two writers in a smaller
  coat: a label written in one place about data chosen in another. Fixed 4 October.
- **The stamp canary reverts what you edit while it runs.** Its cleanup diffs the working
  tree before and after and restores or removes every difference, so a file written during
  the run is treated as the build's and erased (4 October: the day history and the handoff).
  Until it records the build's own writes, edit nothing in the repo while the canary runs.

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
