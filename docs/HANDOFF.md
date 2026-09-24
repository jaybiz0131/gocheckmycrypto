# Handoff, GoCheckMyCrypto

One session per sprint (U-1). Start by reading this file and this sprint's section
of `PROGRAM-4-2026-09-16.md`. Do not re-read the boards or repos to reconstruct
state this file carries (U-6). Where a board and a rule disagree, ask in one line
before inventing (V-15).

Public repo. No tokens, keys or secret values in this file, ever.

Last updated: 2026-09-16, end of the Program 4 throttle session.
This session ended at f7ea702.

The Sports handoff (`../gocheckmysports/docs/HANDOFF.md`) carries the shared laws,
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

---

# Standing rules, all desks

**U-1 to U-11, issued 24 September 2026, 12:50 PM ET. This is the one text.** Every desk
(Pet, Parents, Weather, Sports and Crypto) writes it into its HANDOFF.md as the
standing-rules section, replacing whatever set it holds, in one commit, and says so with
the hash in its next report. A rule is issued once by Jack, numbered next in the sequence,
and every desk records it the same day, unchanged. A desk that finds a rule missing from
its file says so in its report rather than cross-referencing a rule it cannot see. Three
entries name things that are not on every desk; keep the rule, substitute the particular.

## U-1. One session per sprint, one handoff file.

The desk's HANDOFF.md, outside the published tree, is the only handoff: a session begins by
reading it and the current program section, and everything the next session needs goes back
into it at the end of every sprint and after every report. Under 300 lines, no tokens or
keys of any kind, no second file, no parallel notes.

## U-2. Model by kind of work.

Sonnet subagents for the mechanical items: greps and replacements, deletions, screenshots,
harness runs, tallies and report assembly. Opus for design and engine work and for anything
read and matched by eye.

## U-3. Batch, never poll.

One harness run per sprint plus one re-measure when a change lands; screenshots once per
page per sprint; log and workflow checks once per report. Never wait on a Netlify build or a
workflow run inside the session: note the commit, move to the next item, read the result at
the next check.

## U-4. The key is for scheduled runs only.

A desk's model key is spent only by its scheduled runs: no local pipeline runs that call the
model, no test briefs, no dry runs that reach the API, and no manual dispatch of a workflow
that spends, other than the one agreed backstop where a desk has one. Every stage is tested
on fixtures on its no-model path; a stage without one gets one before it is tested. Every
model call appears in the desk's ledger; a spend that is not in the ledger is a leak and
goes in the next report with its cause.

## U-5. Report form.

One line per item, no narrative, no adjectives: what merged, with both hashes; what was read
live and the stamp it was read at; what the tests say, with each new test's break named; what
is open; what is Jack's. Counts are printed as recorded, nothing rounded, nothing estimated,
and a number that does not exist is said not to exist. When a decision is needed, one
paragraph with the two options and the desk's recommendation.

## U-6. No re-derivation.

Do not re-read boards, packages or repositories to reconstruct state the handoff carries;
open the file named for the item and the board named for it. Where a board and a rule
disagree, ask in one line before inventing.

## U-7. A headless browser is closed in a finally block and launched with a timeout.

Issued to the Pet desk, September 22, 2026, after fourteen headless Chromes from other
sessions were found alive on the machine. A harness that throws between spawn and kill
leaves the process alive, and a session that measures forty times leaves forty of them. The
kill goes in a finally, not on the happy path, and the launch carries a timeout, so nothing
outlives the read that started it. The shared harness is gcm-tools/harness/measure.mjs, in
the repository rather than in /tmp, because /tmp is cleared between sessions and the harness
was rewritten from memory three times before that file existed.

## U-8. A push is verified by hash, not by exit code.

September 22, 2026: a git push returned exit 0 while a rebase was still in progress; the
local branch sat on origin's own tip, so the push was a no-op and nothing of the desk's work
landed, and the exit code said it had. After every push, fetch and compare: git push origin
main; git fetch -q origin; git rev-parse --short HEAD; git rev-parse --short origin/main; git
rev-list --count origin/main..HEAD, which must be 0. A push is done when the two hashes match
and the count is zero, and both hashes go in the handoff and the report for every push of the
day, preview and merge.

## U-9. A new test is not trusted until it has been seen to fail.

September 22, 2026: the recurring failure of that session was checks that passed by not
running: a canary guarded on data it never loads, so its whole block was skipped in silence;
an assertion matching a string the script contains as well as the markup, so deleting the
markup left it green; a comparison that cannot be true because its own input is on both
sides; a fixture whose parts summed to exactly the total, so a test written to catch a summed
total passed; an assertion on a message's wording that failed when the message improved. Each
looked green and tested nothing. Before a test is committed: break the thing it guards on
purpose, watch the test go red, restore it, watch it go green, and name the break in the
report. A test that cannot be made to fail is deleted, not kept.

## U-10. A measurement counts only when the thing measured is the thing shipped.

Issued on the Weather desk, September 23, 2026, after its fit tests were found measuring the
system font instead of the shipped face: every number they produced was real and about the
wrong thing. A test that measures a font, a build or a file first proves it has the real one
and fails loudly on a stand-in rather than quietly measuring the substitute. For every desk:
a read of production names the stamp it read and fails if that is not the deploy it meant; a
screenshot comes from the preview or production URL named in the report, never from a local
build; a harness number is taken on the deployed page with its own fonts loaded; a suite run
after a new file is added regenerates the project first, so the binary under test is the tree
under test; a fixture run against a stubbed model says so beside its result and never stands
in for the live run the report asks for. This is U-9's other half: U-9 asks whether a test can
fail, U-10 asks whether it is looking at the shipped thing.

## U-11. A commit that changes nothing in the published tree does not build the site.

Issued September 24, 2026, after the Pet and Parents desks each found handoff and script
commits in their production deploy lists: three builds on Pet and three on Parents this week
with no site change behind them. A deploy changes what the site says; a number changing is
never a deploy. netlify.toml carries an ignore rule so a commit touching only HANDOFF.md,
docs/ or scripts outside the published tree does not build, proven once by pushing a handoff
update after a merge and showing no build followed. Every page carries the build's stamp, the
merge commit written by the build into one meta tag and /stamp.txt, and every live read
asserts it before measuring. The day's deploy count is read from the Netlify commit statuses
on GitHub through gh, never from a Netlify token, until the Worker's deploy counter is live,
when that becomes the count of record; the method is printed once in the handoff and the
count in every report.
