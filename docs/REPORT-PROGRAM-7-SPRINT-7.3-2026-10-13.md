# Report: Program 7, Sprint 7.3, the writing tells the truth (Tuesday 13 October 2026)

Branch `sprint-7-3`. **Built and screenshotted today; NOT merged.** The merge waits for Wednesday 14 October after 8:30 AM ET and Jack's yes, because today's five builds are spent (below).

## Start

- RULES body sha256 `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`: **matched** (`tail -n +11 docs/RULES.md | sha256sum`).
- `origin/main` at the start: `07f5a831455ecf9624bb43af946cc54f31cac06f`, which contains Sprint 6.5's merge (`23c33e5`) and its close. Shell date 4:16 PM EDT, Tuesday 13 October 2026.
- Count of record, read 4:30 PM ET from the Worker (`https://gcm-slot-trigger.gocheckmybrands.workers.dev/counts/today`, which answered this session; the 6.5 report could not read it): crypto production **4 ready, 4 canceled** on 13 October. **One build remains today**, the 7:08 PM Edition. Nothing may be pushed 6:30 to 8:15 PM ET. This sprint's push of the branch builds nothing (branch deploys are off); its merge is 14 October's.

## Jack's rulings, Tuesday 13 October 2026 (recorded in HANDOFF.md section 13)

1. The site's promise is fact-based and no hype, so a true sentence must never be cut and a false pairing must never print. The gate's job is to catch wrong claims, not to thin out right ones.
2. A sentence the gate cannot parse is not dropped silently. It is logged in the ledger with the reason, and the drop is counted in the night's report.

How ruling 2 is built: a sentence with an odd number of quotation marks around a direction word, or one on which a check raises, is dropped with kind `unparsed`, a `::warning::` annotation, its reason in `out/twins-gate.json` (with a `counts` object), `gate.report()` in the run's log and the wrap status, and three fields on the ops-ledger row: `twins_drops` (wrong claims), `twins_unparsed`, `twins_log` (surface, kind, reason and opening words of up to six). Everything the gate cannot check because the snapshot does not carry the window (a five-session ETF net, a seven-day whale net) is **unverifiable and stands**; that is ruling 1, and it is not an unparsed drop.

## What was wrong, and where the seven sentences came from

The seven drops of 9 and 10 October were described in the handoff but not quoted. Their full text is in `wrap-status.json` (key `twins_gate`) inside the `crypto-review-queue` artifact of Actions runs 38003059379 and 38094093202; I read both. **Six fixtures are verbatim.** The seventh, the narrative line, is in no artifact (the table's line replaced it); the run log keeps its first 140 characters, so F7's tail is **reconstructed** and marked so in the test. The log's own drop reasons are reproduced exactly by main on every fixture (below), which is the check that the reconstruction is faithful where it matters.

## The fixtures, red then green

`python3 scripts/twins_gate_test.py`. On `origin/main` (clean worktree, test and fixtures copied in) 17 lines fail, among them:

| # | Date and place | Sentence (opening) | main | branch |
|---|---|---|---|---|
| F1 | 9 Oct bottom line | "The desk's ETF flow board shows bitcoin funds posted a net outflow of $244.1 million ..., and a net outflow of $510.1 million over the last five sessions, while the Whale Watch board shows ..." | DROP: 'outflow' about whale net | KEEP |
| F2 | 9 Oct body 1 | "... any single word like "rising" or "falling" for bitcoin today would be incomplete ..." | DROP: 'rising' about Bitcoin, series week -3.72% | KEEP |
| F3 | 9 Oct body 6 | "... a positive daily bitcoin print sitting alongside weekly ETF outflows and sustained onto-exchange bitcoin flows ..." | DROP: 'positive' vs series week -3.72% | KEEP |
| F4 | 10 Oct dek | "ETF flows remain split between the day's modest inflow and a five-session net outflow." | DROP: 'outflow' vs ETF net +21.1M | KEEP |
| F5 | 10 Oct bottom line | "Funding rates on OKX stayed negative for bitcoin and ethereum while Solana shorts took heavy liquidation hits." | DROP: 'negative' vs Bitcoin +0.53% 24h | KEEP |
| F6 | 10 Oct body 3 | "Bitcoin ETF flows showed an inflow of $21.1 million on October 9, but the five-session net stands at an outflow of $678.9 million." | DROP: 'outflow' vs ETF net +21.1M | KEEP |
| F7 | 10 Oct narrative line | "Bitcoin gained 0.53% on the day while falling 2.3% on the week as whale deposits to exchanges hit weekly highs; ..." (tail reconstructed) | DROP: +2.30% vs series -2.30% | KEEP |

The other red lines on main: the cause tests (hyphenated window, sign word, hyphen window must be checked, quoted word), the unparsed cases U1 to U3, the clause table's four sign cases, and the ledger and Whale-tag cases (those two die on main with an AttributeError and by the old tag pattern: `custody` and `shuts down` matched, shown directly). All 40 cases pass on the branch. The test is in the canary as `_sprint73_canary`.

**Each fixture checked against the data** (this is what "right" means in the replay table): F1 the 8 Oct ETF net is -244.1M and the five sessions 2, 5, 6, 7, 8 Oct sum to -510.1M (from `pulse.json` `etf_flows.recent` at `cbf7e80`); the whale board read -119,468,889 USD onto exchanges over 48 hours. F2 makes no claim about Bitcoin. F3 the day was +0.93% and the five sessions net out. F4 and F6 the 9 Oct net was +21.1M and the five sessions 5 to 9 Oct sum to -678.9M. F5 Bitcoin funding -0.0031% and Ether -0.0039% (Solana is not in the claim). F7 +0.53% on the day, series -2.30% on the week. **All seven were true; the new verdict (KEEP) is right on all seven.**

## Five true negatives (the gate must still drop them)

The record holds **no gate drop that was right**: every drop logged on 7, 9 and 10 October was judged wrong. So none of the negatives is a recorded drop. They are labeled in the test:

| # | Sentence | Basis |
|---|---|---|
| TN1 | "Bitcoin is up 1.3% on the week and up 8.3% on the month." | REAL: the 6 October Edition's wrong figures (the series said 2.75% and 7.45%) |
| TN2 | "Spot ETF flows were positive on the day." | SYNTHETIC text of the REAL 7 October class (the stale read said positive; the snapshot -66.9M) |
| TN3 | "Bitcoin is rising over seven days." | SYNTHETIC; series week -3.72% |
| TN4 | "Funding rates stayed negative for bitcoin and solana." | SYNTHETIC; Solana funding is positive |
| TN5 | "Bitcoin is falling 2.3% on the week." | SYNTHETIC; series +2.30% (so the sign word is checked, not skipped) |

Two more are in the file (TN6, a week claim against -2.30%; TN7, a four-word quote is still a claim) and "Bitcoin is rising on a seven-day basis" proves a hyphenated window is *checked* (main kept that wrong sentence; the branch drops it). TN1 to TN6 drop on main and on the branch; the sign-word case is one only the branch gets right.

## The replay

`python3 scripts/twins_replay.py` runs every recorded Edition through main's gate and the branch's, each against the snapshot rebuilt from that Edition's own committed `pulse.json` and `flows.json` (`fixtures/twins/`; stamps match the log's, e.g. 2026-10-09T23:11:49Z). Recorded Editions: **8, 9, 10 and 11 October** (7 October's Brief was withheld by the consistency gate, 12 October's run failed at the canary). Recorded morning reads: **none** (the morning run has not fired in production; the 7.2 fixture morning is a labeled fixture, not a record). Surfaces: title, dek, key fact, bottom line, every body paragraph, the narrative line, every wire line and the checked note.

| Set | Sentences | Old verdict | New verdict | Which is right |
|---|---|---|---|---|
| The seven recorded drops (F1 to F7) | 7 | DROP x7 | KEEP x7 | **new** x7, checked above |
| Published sentences, 8 to 11 Oct | 112 | KEEP | KEEP | same verdict on all 112 |
| Published sentences the two gates disagree on | 0 | | | |

**The replay caught a defect in my own first cut**: the 9 October dek, "...bitcoin up on the day while weekly ETF outflows and exchange inflows continue", was KEEP on main (by luck: a week word skipped it) and DROP on my first branch (it bound "exchange inflows" to the ETF net, -244.1M). It is true (the whale board read -119M onto exchanges). The whale reading now names "exchange inflows/outflows"; the sentence is test R1, and the replay shows no difference on any published sentence. Old gate 8 Oct to 11 Oct: none wrongly kept that the new gate would drop; no published sentence changed verdict.

## Item 1: direction and driver

`narrative._tape_clause` says "on spot ETF inflows/outflows" only when the ETF net's sign supports the direction (inflows with higher, outflows with lower); otherwise, and when the tape is flat, "while spot ETFs saw inflows/outflows". Tests I1 (all six sign cases, including the 9 October pairing "drifting higher while spot ETFs saw outflows") and `I1 gate` (the table's line passes the gate). The canary's own expected line for its fixture (lower on +212.4M inflows) changed accordingly: "Bitcoin is drifting lower while spot ETFs saw inflows". **Live today:** production prints "Bitcoin is holding flat on spot ETF outflows" (4:01 PM refresh, ETF net -65.4M, Bitcoin +0.49%); the branch's table writes "Bitcoin is holding flat while spot ETFs saw outflows" from the same readings (the home screenshot).

## Item 2

1. **`publish_narrative`**: the canary now reads the tree the real `build()` writes and requires `data/narrative.json` to hold the stored line. Seen red: with the call replaced by `pass`, the canary fails with `narrative canary: build() did not publish /data/narrative.json (published None ...); the build's call to publish_narrative is gone`; restored, green.
2. **Funding bands**: read live. `https://gocheckmycrypto.com/learn.html` prints calm "under 0.010%", warm "0.010% to under 0.030%", hot "0.030% or more", the same as `narrative.FUNDING_BANDS` `((0.010, calm), (0.030, warm), (inf, hot))` and `tile.funding_thresholds()`. The leverage page (`/pulse/leverage.html`) prints no band thresholds, only per-coin rates and prose with no numbers; the home Funding tile says "+0.0046% calm", consistent. **They do not differ, so no page change and no new check**; the existing tile canary already probes the Learn page's bands against `narrative.funding_band`.
3. **Whale tags**: `custody`, `shuts down` and `winds down` are out of the `exchanges` tag rule (the tag that maps to "Whale net, exchange flows"). Fixtures: an L2 shutdown and a bank custody approval read nothing; an exchange that pauses withdrawals or "Bitmex shuts down" still reads Whale net. Measured on the corpus: 34 of 561 stories lose the tag, those I scanned custody rules, protocol shutdowns and chain exits. `custodian` is untouched (not in the ruling).
4. **Unlocks (HYPE, WBT, RAIN)**: tried once each from this session. `hyperliquid.medium.com`, `whitebit.com/wbt` and `www.rain.one/get-rain` all answered **HTTP 403** (a Cloudflare block, a security check, a "Just a moment" page). Still unreadable; left to Jack. Confirmed each coin's page prints nothing for them (`coinpage.unlock_line` returns `''`; test N-HYPE, N-WBT, N-RAIN).

## Item 3: the open-items table, swept against the live site (13 October, production `23c33e5`)

| Row | Verdict | Where or plan |
|---|---|---|
| Twins gate cuts true sentences (5 causes) | **done on this branch** | this sprint; merge 14 Oct |
| Clause table pairs direction and driver | **done on this branch** | this sprint |
| No Brief for 7 October | history, removed | lost; the gate fix of 8 Oct and this sprint prevent the class |
| Unlocks HYPE, WBT, RAIN | **open** | Jack by hand; all three 403 again |
| Funding bands on the live leverage and Learn pages | **done** | Item 2.2: they agree |
| Wire stays in re-count order | closed (Jack, 7 Oct) | removed |
| Board reading from tag rules, "shut down" and "custody" | **done on this branch** | Item 2.3 |
| Home page cadence line | **done, revisit 14 Oct** | live home reads "...one checked, the Brief every evening"; true until the morning edition goes live, then reread |
| Coin pages print `/coins/markets` 7d/30d | **open** | the 7D tile is labeled "Rolling 7 days"; the Board's week is the stored series. Plan: one table of both values for the seven stored coins, then Jack decides |
| The week field (six closes in the 23:00 UTC hour) | **open, unverified since 7 Oct** | plan: one fixture on a coin outside the seven |
| `publish_narrative` has no failing test | **done on this branch** | Item 2.1 |
| Count 7 of 5 on 7 October | **superseded** | the Worker's `/counts/today` is the count of record and reads (above) |
| V-8 A-12 emblems (44x29 mark, masked watermark) | **superseded by Sprint 7.1** | the approved design ("A, front page in color, with glow") has a wordmark and neither; no `watermark` or `emblem` in the live home HTML or `system.css`. A new emblem would be a new design brief for Jack |
| V-9 N-3 module pages (Whale Watch, Chart Master, canvas row ten) | **done** | Programs 6.1 and 7.1: `/flows` and `/chartmaster` answer 200, no gradient, no overflow at 375. "Canvas row ten" lives on the Mac only and cannot be read from the cloud |
| V-10 N-1/N-2 nav (Home first, Chart Master in nav, 12th tile, read card) | **done / superseded** | nav reads Home, Markets, Flows, Charts (Chart Master), News, Brief, Record, Learn, About. The 12th tile and read card are superseded by 6.2 (home edited, 7 tiles) and 7.1 (the Brief card in the band's place) |
| V-11 punch 5, 6, 8 (label columns, full-width Whale Watch, Edition wordmark) | **5 superseded (6.1 tile law), 8 done, 6 open** | the Edition page carries the GoCheckMyCrypto wordmark. At 1440 `/flows`' tables are 471 to 543 px inside a 1080 px column, so if "full width" meant the tables spanning the column it is not done: ask Jack what punch 6 meant, or drop it |
| V-12 A-14/A-15/D-7 inner pages and phone, under 5,500 phone homepage | **done** | home 4,998 px tall at 375; all nine pages measured (`/`, `/pulse`, `/flows`, `/chartmaster`, `/bottom-line`, `/news`, `/record`, `/learn`, `/about`): no horizontal overflow, no gradient |
| V-13 Crypto copy | **superseded by Program 6.1** | no `technician`, `carved over his door` or `Cronkite` on the six live pages read |
| `top_n` 6 ranking check (3 of 7) | **open, ready to do** | seven Editions (4 to 10 Oct) exist; plan: read each one's `wire.json` rank of its VERIFIED item from git, one table, close or change `top_n` |
| Coin page chart (Jack, 5 Oct: on demand, default line, caption with no dollar figure) | **mostly done by 6.4 and 6.5; one part open** | chart, ranges 1D/7D/1M/1Y and honest averages are live. **But `/coins/btc`'s caption prints "High $85,526.87, low $81,763.06" while the home tape prints HIGH $85,597 LOW $81,630 for the same week**: two dollar figures from two reads, the twin the 5 Oct ruling retired. Plan: caption names range and read time only, or both read from one series |
| L-1 the Board on the Worker | **open** | plan: serve the snapshot from the Worker; `site-refresh.yml` has had no cron since 7.2, so builds are the only mover; needs Jack (touches the build count) |
| R-1 desk reconfiguration | **open** | Sprint J; no plan written; ask Jack for the brief |

The handoff's table now holds the open rows only, plus this sprint's, the morning proof, the tonight's-Edition proof (the Monday 12 October Brief never published: runs 399 to 402 failed at the canary step within a second; the live home still showed Sunday's Brief on Tuesday afternoon), 6.5's unread 13-character tier, and the V-13 line.

## Screenshots for Jack (`shots/program7-7.3/`)

`sheet-home-375-light.png`, `sheet-home-375-dark.png`, `sheet-edition-375-light.png`, `sheet-edition-375-dark.png`: before (production, read 4:01 PM ET today) beside after, at 375, light and dark. Real data throughout:

- **Home Brief card**: the live line beside the clause table's line for the same live readings (`/data/narrative.json`; the old table reproduces the live line exactly).
- **Edition**: the live 10 October Edition, and the same page with the three sentences the old gate cut put back, verbatim from that run's `wrap-status.json`, **each outlined in red** so nothing is hidden. **The paragraph is the gate's own; the place inside it is inferred** (the end of the dek and of the bottom line, the second sentence of body 3), because the artifact keeps the dropped sentence and not its position. The fourth cut that night (the narrative line) is not on the page.

## Other findings

- The canary overwrote the real `site/data/narrative.json` with the fixture morning's line on every run (`scripts/morning_test.py` called `morning.run` against the real path). Fixed: the test points `narrative.PATH` at its temp directory. This was already so on main; I restored the file by hand after the first two runs.
- A canary run takes minutes and imports site files: my first full run read three false reds (`inspect.getsource` of three site functions) because I edited files while it ran. The clean rerun was green. The handoff's trap line stands.
- The Worker's `/counts/today` is reachable from the cloud at the `gcm-slot-trigger.gocheckmybrands.workers.dev` host; 6.5 reported it was not.
- Not done, as instructed: no merge, no push of main, no production read after a push (nothing was pushed to main), no morning-edition proof.

## To do after Jack's yes (Wednesday 14 October, after 8:30 AM ET)

1. Jack's yes on `shots/program7-7.3/` and the replay table above: **pending, none received**.
2. Fetch, merge `sprint-7-3` into `origin/main` with one real merge commit; push; `git branch --contains` on the sprint tip to confirm the merge holds every sprint commit; canary green on the merged tree.
3. Read production by stamp; read `/counts/today` five minutes after the push; read the 8:15 AM ET morning run (the open 7.2 proof).
4. Live proof: the 14 Oct 7:08 PM ET Edition's ops-ledger row shows `twins_drops`, `twins_unparsed` and `twins_log` with their reasons. Hand to the next session if this one is closed.

Close: documents only. The merge hash, the production read and the count are not in this report because none has happened.

Sprint tip pushed to `origin/sprint-7-3` (`git ls-remote`: `f46c2fa`; the session's `claude/hopeful-mccarthy-yrskeh` holds the same commit). Shell date at the end of this session (ET): **Tuesday October 13, 2026, 4:44 PM EDT**.
