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

## The Worker and the deploy counter (24 September 2026)

**Deployed.** Jack ran `npx wrangler deploy` from `gcm-newsroom` main at `f75ce71` after a
fast-forward pull. Binding `env.COUNTS` (KV namespace `00dc8942e97043c8b18b611e14805465`),
schedule `*/5 * * * *` unchanged, version `f5bdae3d-77d9-48ce-ba07-fae8361c628f`. The webhook
secret was set once with `wrangler secret put` and appears in no file, handoff or report.

Read live at 5:46 PM ET: `/counts/today` answers `{"date":"2026-09-24","deploys":{},
"clicks":{},"note":"KV counters are not atomic; ..."}` and the status path answers
`token_ok: true`, `token_status: 200`, with both evening briefs in the schedule. Routes 2, 3
and 4 confirmed in production on their rejection paths, which count nothing: `GET /hit/<key>`
405, `POST /hit/other` 400 `unknown key`, `?sp=bird` 400 `bad species`, a foreign or absent
Origin 403, `GET /go/other` 404, and the counters unchanged after all six.

**The notification is called "HTTP POST request"** in Netlify's menu now, not "outgoing
webhook". Recorded so the next person does not hunt for it. Five sites post to
`/hooks/netlify-deploy` on **Deploy succeeded** and **Deploy failed**, JWS with the secret:
Sports, Pet, Parents, Weather and Crypto.

**The count of record** is the Worker's deploy counter from today (Jack's ruling, 1:55 PM),
replacing the `gh` commit-statuses method, which reads nothing on these repositories: Netlify
posts no status, no check and no deployment to GitHub here, so that method could not tell a
build that ran from one that was skipped. The corrected U-11 text has not reached this desk
yet and is not written in as a rule; this paragraph records the ruling, not the clause.

**U-11's proof for Sports, read by Jack in the Netlify UI on 24 September 2026**, not a read
of this desk's own: on the Deploys page, `028a973` (code) built at 4:51 PM, `75ecb4e` (the
documents-only push) shows **Canceled** at 4:52 PM, and `1c1eeea` (the stamp) published at
5:09 PM. So the ignore rule skipped the handoff push. **A skipped build appears as "Canceled"**,
which is worth knowing before someone reads it as an error.

**The stamp is live on both desks.** Every page carries the commit that built it and so does
`/stamp.txt`. Asserted, not eyeballed:

    python3 live_read.py https://gocheckmysports.com/ --expect-head

Sports `1c1eeeae7d79af221a4a7baca7947586291b85fc`, built 21:10:26Z, which matches the 5:09 PM
publish Jack read in the UI. Crypto `31880d817f8642e14f2147a5093d185908fab320`, built
21:15:59Z. Both matched `origin/main` on 40 characters. Any live read that does not match must
measure nothing.

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

**Addition, 24 September 2026, 6:10 PM ET.** Found on the Sports and Crypto desk while breaking
a test under U-9: on this machine Python's bytecode cache lives outside the project
(`sys.pycache_prefix` under `~/Library/Caches`), so deleting `__pycache__` clears nothing and
`python3 -B` only stops writing, not reading; a source file restored within the same second at
the same length leaves a stale `.pyc` that Python runs in place of the tree. Every Python test
run on every desk therefore sets a fresh `PYTHONPYCACHEPREFIX` for the run, or clears the prefix
it uses, so the bytecode under test is the tree under test. **A suite that goes red after a
restore is read as this before it is read as the code.**

## U-11. A commit that changes nothing in the published tree does not build the site.

Issued September 24, 2026, after the Pet and Parents desks each found handoff and script
commits in their production deploy lists: three builds on Pet and three on Parents this week
with no site change behind them. A deploy changes what the site says; a number changing is
never a deploy. netlify.toml carries an ignore rule so a commit touching only HANDOFF.md,
docs/ or scripts outside the published tree does not build, proven once by pushing a handoff
update after a merge and showing no build followed. Every page carries the build's stamp, the
merge commit written by the build into one meta tag and /stamp.txt, and every live read
asserts it before measuring. 

**The count clause, replaced 24 September 2026, 6:10 PM ET.** The count of record is the
Worker's deploy counter, fed by the Netlify deploy notifications Jack set on all five sites and
read at `/counts/today` on `gcm-slot-trigger.gocheckmybrands.workers.dev`. Until it answers for a
site, a desk prints the count it can read and names its source, and a desk that can read none
says it cannot read one rather than estimating. The clause naming Netlify commit statuses on
GitHub is withdrawn: Netlify posts no status, check or deployment to the Sports and Crypto
repositories, so that method reads nothing there. The rest of U-11 stands unchanged: the ignore
rule, its one-time proof, and the build stamp in one meta tag and `/stamp.txt` asserted by every
live read, which every desk that has not built it builds on its next branch.

### A log line with the `[36;1m` prefix is the command, not an error (2026-09-29)

**Verbatim, Jack's words:** a log line carrying the `[36;1m` prefix is GitHub
echoing the command, not a fired error; a finding from such a line is not a
finding.

Found in the failed-run audit. Three lines in the Inactives poller's log read as
fired errors and are not: "slot-trigger token is not accepted by GitHub", "push
failed after 3 attempts" and "rebase conflicted outside the snapshot". All three
are the shell script's own `echo` statements, logged before they run. Reported as
real, the first would have claimed the Worker's `ACTIONS_API` token was rejected
and sent someone to replace a working secret. The fired annotations are the
`##[error]` and `##[warning]` ones; the poller's real cause was two `##[error]`
lines from its H-6 canary and nothing else.

### The failed-run audit, 15 to 29 September 2026 (read-only, nothing re-run)

Logs were read, never re-run to see. **What was read, exactly:** the three runs
Jack named (9852c41, ce39579, 41ef7d7), one more Crypto brief, one Verify crypto
pipeline run, and one Sports Inactives poller run. Causes for the Sports daily
brief, watcher and verify groups are **not** read and are named as unverified
below rather than assumed to share a cause.

**A note on reading these logs.** Three lines in the poller's log looked like
fired errors and are not: "slot-trigger token is not accepted by GitHub",
"push failed after 3 attempts" and "rebase conflicted outside the snapshot" all
carry the `[36;1m` prefix, which is GitHub echoing the **command text** before
running it. The fired annotations are the `##[error]` ones. Had the first been
reported as real, this audit would have claimed the Worker's ACTIONS_API token
was rejected, which it was not. Read the prefix, not the words.
#### Cause A, Crypto: an empty `schedule:` key, so every push fails at startup

`.github/workflows/site-refresh.yml` has `on: schedule:` with **every cron line
commented out**, which parses to `schedule: None`. Actions requires at least one
`- cron:` under `schedule`, so the workflow does not load: GitHub creates a run
with **zero jobs**, names it by its path rather than its `name:`, and concludes
`failure` on every push. `total_count: 0, jobs: []` on run 36632138989.

- **14 failures**, first `e2f3dd1` 2026-09-21 20:23, last `9f9db56` 2026-09-29
  21:16. The last three are this desk's own documents pushes today.
- **The commit that caused it: `e2f3dd1`, 2026-09-21 16:20**, "Deploy budget:
  one scheduled daily refresh on this desk, not two", which retired the noon
  cron by commenting it out and left the key behind.
- **Nothing fixed it.** It has failed on every push for eight days.
- **The fix:** delete the empty `schedule:` key, keeping its comments, so only
  `workflow_dispatch` remains. **Its U-9 test:** a check that every workflow
  file loads, asserting `schedule` is absent or holds at least one `cron`, red
  against this file today and green after. It belongs in U-13's branch, which
  already has to parse every served script; a workflow that does not load is
  the same class of defect.

#### Cause B, Crypto: the canary asserts an artifact of a build that never runs

Every failing Crypto workflow that runs the offline canary stops on one line:

```
::error::canary: build stamp canary: /stamp.txt was not written by the build
::error::Offline canary FAILED (exit 1): the pipeline is mis-wired
```

`verify_pipeline.py._stamp_canary()` checks `site/publish/stamp.txt` exists.
Only `site_build.py` writes it, at its line 9415. The canary job runs
`checkout`, `setup-python`, `pip install Pillow`, **canary** and nothing else,
so in CI that file cannot exist. **The canary is right to stop and the gate is
working; the mis-wiring behind it is that the check was added before anything
in that job produced what it checks.**

- **66 failures** across the Breaking-news watcher, the Crypto Cronkite daily
  brief and Verify crypto pipeline. First `31880d8` 2026-09-24 21:13, last
  `46f4d3b` 2026-09-29 02:32.
- **The commit that caused it: `31880d8`, 2026-09-24 17:13**, "U-11's other
  half: every page names the deploy that built it".
- **Nothing fixed it.** A later commit on 26 September fixed a *different*
  aspect of the same function, comparing built pages against a HEAD that had
  moved, and the file says so; the missing artifact was untouched.
- **The fix:** the canary builds before it asserts. `_stamp_canary` renders into
  a temporary publish directory and asserts what U-11 actually asks, that the
  meta tag and `stamp.txt` name the same commit, rather than that a deploy has
  already happened in a job that never deploys. **Its U-9 test:** the two
  writers made to disagree, red; the stamp writer removed, red; restored,
  green. It lands with the stamp item on `build-stamp`, because **this failure
  IS the stamp item on this desk.**

#### Earlier and healed, Crypto

`Verify crypto pipeline` and the daily brief on `da5256f`, 2026-09-16, two runs,
before the stamp canary existed. Not read, healed without a commit naming it,
and listed for completeness rather than diagnosed.

#### Cancellations are not in the mail

`Breaking-news watcher` 1 and the daily brief 1 on 15 September, cancelled by
concurrency when the next tick superseded them. GitHub files those as
`cancelled`, not `failure`, and does not mail them, so they are not part of what
reaches Jack's inbox.

### The 26 twin pairs, read and classified (2026-09-29, nothing changed)

`twin_audit.py` calls all 26 "likely twin" and 0 "likely different". Read
headline beside headline, **22 are the same event published more than once and
4 are not.** The tool has no sense of a recurring column or of a story that
moves, so it cannot tell a duplicate from a sequel; that judgement is below and
the tool is left as the advisory it says it is.

**Two pairs share one URL**, which is the clearest case of all: `#2` and `#3`.
Two records point at one address, so one has already overwritten the other on
the page.

**The same event, published more than once (22).** Four clusters carry most of
them:

- **Revolut EURR**, 10 pairs (`#3 #4 #5 #8 #15 #17 #21 #22 #26` and `#3`'s twin
  URL): one launch, "EURR with Bridge as regulated issuer in three EU markets",
  filed from 28 August to 16 September under nine different headlines and eight
  different addresses.
- **SEC crypto custody**, 5 pairs (`#2 #11 #18 #23 #25`): one rule reaching
  White House review, filed 31 August, 7, 12 and 14 September.
- **Circle's Arc mainnet**, 2 pairs (`#9 #19`): the same 16 September launch,
  filed three times on 15 September.
- Singles: `#6` India tokenized bonds a day apart, `#7` Schwab adding the same
  three assets, `#10` Circle's OCC and New York charter on one day, `#16`
  BlackRock's tokenized money market funds two days apart, `#24` the S&P and
  Kaiko Series B a day apart.

**Not the same event (4), and the tool is wrong about these:**

- **`#1` The Week Ahead, 27 July against 14 September.** A recurring weekly
  column. The overlap is 1.0 because the column is formulaic, which is exactly
  what a template looks like to a token test. Two different weeks.
- **`#12` the CLARITY Act bill revised, 11 September, against the procedural
  vote being set, 14 September.** A bill moving is a sequence.
- **`#14` the vote being set against the vote failing.** Same.
- **`#20` the Banking minority staff's five loopholes, 5 August, against the
  Senate blocking the Act, 15 September.** Six weeks apart and different
  subjects.

**AND ONE PAIR IS WORSE THAN A TWIN.** `#13` and `#14` date the SAME cloture
vote to two different days: "Senate Fails Clarity Act Cloture Vote on September
15" and "...on September 16", published 15 and 16 September at
`/senate-blocks-crypto-clarity-act-in-49-50-v...` and
`/senate-fails-clarity-act-cloture-vote-on-se...`. One of those dates is wrong,
and a wrong date is not a duplicate to merge, it is a correction to make. It is
flagged here and not touched.

### The rule proposed for twins, link or retire (nothing applied)

1. **The URL never changes.** A retired twin keeps its address and points at the
   one that stays, as the desk's retired-URL mechanism already does in
   `site_build.py`: the surviving story takes the reporting and the retired slug
   301s to it. Never delete a published URL, because someone linked it.
2. **One event, one surviving story.** Where the pair is the same development,
   the EARLIEST address survives by default, because it is the one that has had
   the longest to be linked, and the latest reporting is merged into it. Where
   the later story is materially fuller, the later one survives and the earlier
   retires; the report names which and why, per pair.
3. **A sequence is linked, never retired.** A bill that moves, a launch that
   was announced then happened, a weekly column: each keeps its own address and
   gains a link to its neighbours. `#1 #12 #14 #20` take this path.
4. **A wrong fact is corrected before anything is merged.** `#13` and `#14`
   disagree on a date; that is settled first, because merging them would bury
   the error rather than fix it.
5. **The tool stays advisory and learns the exceptions.** `twin_audit.py`
   should carry a template list, so a recurring column stops being offered as a
   duplicate every run, and its warning line should say "22 likely twin, 4
   likely a sequence" rather than counting every candidate as a twin.

**Nothing in this section is applied.** It is the rule for Jack to accept or
change, and the retirements are per pair with their own report.

### The run-report rule (Jack, 2026-09-29, narrow; the 12 September execution rules stand)

**A run fails only when a person must act.** A step that stops on purpose, like
the canary, still fails, because a person must read it. **A step that finds
nothing to publish, or meets a rate limit it will retry on the next tick, exits
0, prints a warning annotation and one line in the run summary, and files
nothing under failed.**

Applied to this audit: **none of the failures found were of the second kind.**
All three causes below require a person, so the rule is recorded and there was
nothing to change under it. Saying so is the point; inventing a change to have
one would be the shape of thing U-9 exists to stop.

### The two stashes, listed before anything is cut (2026-09-29, Jack's order)

None applied. Each waits on a ruling from this list, and any that is applied
goes on a clean tree with its result read before anything is committed, which
is U-13's last sentence and the way Weather's markers got in.

| # | branch it was stashed on | date | what it holds |
|---|---|---|---|
| `stash@{0}` | `main`, "gcmc-pre-push-18410" | 2026-09-22 14:53 | `site/data/living-tables.json` alone, 97 lines each way. Generated data, no source. |
| `stash@{1}` | `main`, "local build artifacts before push" | 2026-09-21 10:53 | `site/data/living-tables.json` alone, 93 lines each way. Generated data, no source. |

**Neither holds source.** Both are the same generated file at two moments, so
neither carries anything that cannot be regenerated, and dropping both loses
nothing. The Sports desk's `stash@{1}` is the one on this desk pair that does
hold source, and it is listed in that handoff.

**The origin rule lives in one place for the family:**
`GoCheckMyParents/docs/monetization-subids.md`, 220 lines, tracked. The origin
goes in the network's second slot where it has one, is joined into a single-slot
sid only when it fits, and the page's own attribution is never shortened to make
room. **It does not apply on this desk**, because nothing here builds an
affiliate link; the pointer is here so the family has one text rather than four.

### The family.js name cleanup, applied and found to have nothing to act on (2026-09-29)

Jack's paste of 3:50 PM and its 4:00 PM addendum: delete `gcmSubidWithOrigin`
and `gcmOrigin` per name, **decided by the grep and nothing else**. A name with
any caller in the served tree stays and the report prints the callers; a name
with no caller goes, with a U-9 break and a guard that every served affiliate
link still carries the tracking it carried before.

**The grep on this desk found neither name, and no `family.js` at all.**

- `git ls-files | grep -E "(^|/)family\.js$"` answers nothing.
- `git grep "gcmSubidWithOrigin\|gcmOrigin"` over the tracked tree answers
  nothing.
- `find . -name family.js` outside `node_modules` answers nothing.

So there is nothing to delete, nothing to guard and no build. **No U-9 test was
written either:** a test asserting two names are absent from a file that does
not exist cannot be made to fail for the right reason, and U-9 says such a test
is deleted rather than kept.

**Why this desk differs.** The routing rail's `family.js` is copied into the
CONSUMER sites; this is a media desk, and the Newsroom's tool modules publish
into the six consumer sites rather than the media brands. The rail never landed
here.

**What the other desks found, for the record**, since the first paste described
the deletion as safe everywhere: on Pet and Parents both names have live callers
in `affiliates.js`, feeding the `clickref2` and `subId2` values on Awin and
Impact links and, on Parents, the LawDepot `sid`. On Weather the deletion is
genuinely done, and its only two remaining mentions are a comment recording it.
So the deletion was safe on exactly one repository, the one with no affiliate
builder.

## U-12. An exit status is captured from the command itself, never read through a pipe or inside a string.

Issued after the same trap bit the Weather desk three times in one day and the Sports and
Crypto desk once: "$?" inside an echo string reported the command substitution's status and
not the script's; "preflight.py | tail -1" discarded the script's status and a red preflight
read as clean, and a push went out on it. The form is: run the command to a file, capture its
status on the next line before anything else runs, and judge the output only after the status
is known. A harness prints the status it captured beside the output it judged, and a report
that says a suite was green names the status it read, not the last line it saw.

## U-13. A commit never carries a conflict marker, and preflight proves it.

Issued after the Weather site served its service worker with git conflict markers in it for
six days, from a stash applied on September 23: the file did not parse, so the offline shell
and web push were dead the whole time, a published page carried an empty conflict where a
reader could see it, and nothing looked broken because the site loads from the network
anyway; preflight read the version with a pattern that found the first of two values and
passed. Every desk's preflight therefore fails on <<<<<<<, ======= or >>>>>>> anywhere in the
tree it publishes or runs; parses every script the site serves, with node --check or the
language's own check, and fails on a file that does not parse; and asserts exactly one value
wherever a conflict leaves two. A stash is applied on a clean tree and its result is read
before anything is committed.
