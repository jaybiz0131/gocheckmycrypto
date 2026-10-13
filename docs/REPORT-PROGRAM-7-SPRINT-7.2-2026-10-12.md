# Report: Program 7, Sprint 7.2, the morning edition, the Chart Master that publishes, the beacon

Written Monday 12 October 2026, 4:05 PM EDT, on branch `claude/laughing-rubin-j8g33g` (the session's designated branch; the brief named `morning-edition`). **Status: built and canary-green on the branch. NOT merged, NOT live.** Reasons below.

## Start
- RULES.md body sha256 `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`, matches. origin/main at start `0c42212e6c93845675286a8627438d42f4660a6c`, which contains the 7.1 merge (`4194c5b`) and its close.
- Count of record (Worker `/counts/today`, 3:40 PM EDT, Oct 12): crypto production **4 ready, 2 canceled**. One build remains, and the 7:08 PM Edition is it. **This sprint's merge cannot happen today.** It goes after midnight ET on 13 October, outside 6:30 to 8:15 PM ET. Builds before: 4 ready; after: unchanged, nothing was pushed to main.

## What the brief assumed that the repo does not say
1. The **Worker is not in this repository** (it lives in `gcm-newsroom`). Its source was not readable, so the Worker half of item 0 (dispatch at 8:15 AM America/New_York, retire the noon hook) is specified, not applied. See HANDOFF section 10.
2. `site-refresh.yml` says the Worker fires the refresh hook at **noon Eastern**, not 12:00 UTC. The brief says the noon refresh builds at 8:00 AM EDT. One of them is wrong; Jack should check the Worker's schedule.
3. The Oct 10 refusal was **not advice language**. It was the open-interest-names-no-venue belt. Only Oct 9 ('bleed') and Oct 11 ('bleeding') were advice words.
4. The refused texts were **never stored**, only commit messages. The three fixtures are reconstructions that use the flagged phrase the record names. They are labelled as such in each file.
5. No `ANTHROPIC_API_KEY` in this session: **no real morning run, no real cost.** Design cost: one Haiku call, about 1.5K tokens in and 0.3K out, an order of magnitude under the Edition's $0.06. That is an estimate, not a measurement. The first live run prints `tokens` and `usd` into `site/data/morning.json` and `data/morning-ledger.json`.

## Item 0, the morning edition
- `morning.py`, `prompts/morning.md`, `config.json` stage `morning`, `.github/workflows/morning-read.yml`, register entry in `desk.json`.
- Flow: Worker dispatches the workflow, which runs the canary, refreshes boards, `wire.py --refresh` (deterministic desk editor, no model), `morning.py`, then ONE push (the morning build). The hook is pinged only if nothing was pushed.
- Copy law: no percentage of any kind, no prediction words, bottom-line and unattributed-voice lints, no dashes, twins gate. The part is not the whole: a refused sentence is cut, the rest stand; fewer than two left means fallback.
- **Cron lines** (backstops only; the Worker computes ET itself): `17 12 * * *` = 8:17 AM EDT, `17 13 * * *` = 8:17 AM EST (from 1 November). The guard stands a backstop down outside 8 to 11 AM ET or once the read is written.
- Brief card: `THE BRIEF · TUESDAY MORNING`, headline, sentences, narrative line, `Next Brief tonight at 7:08 PM ET`; the next slot is read off the Eastern clock (after the EST change the Edition reads 6:08 PM, tested). "Moving the market" prints `Ranked <time>`.
- Failure: clean fallback, exit 0, card says `Last night's Brief, 7:16 PM ET`, no error email; `morning.py --alarm` fails the run only on the second consecutive fallback.
- Test `scripts/morning_test.py` (in the canary). **Red on main:** the card at 8:30 AM reads `THE BRIEF · MONDAY EVENING`, 7 failures. **Green on branch:** all pass.

## Item 1, the Chart Master
Flag, then one told retry (`llm.call_json(max_rungs=2)`), then a 14-entry substitution table, revalidated in full, then the data-only card (levels, 50-day, 200-day, RSI). Every path is a row in `data/chartmaster-ledger.json` with the words that tripped it.

Table: bleeding->falling, bleeds->falls, bleed->fall, bloodbath->steep decline, carnage->heavy losses, massacre(s)->steep decline, massacred->fell sharply, slaughter->steep decline, slaughtered->fell sharply, obliterate/annihilate (any form)->sharply cut, wrecked->hit, rekt->liquidated, pain trade->crowded position. Advice and prediction phrases have no entry: they go straight to the data card.

**Known weakness:** the table is blunt. "Longs bleed fees" became "Longs fall fees", which is ungrammatical, in the 9 October fixture (my reconstruction). It never publishes a flagged word, but it can publish an awkward sentence.

Red on main (`scripts/chartmaster_publish_test.py`):
```
== 2026-10-09: REFUSED  path=-  model calls=3  reason="chartmaster: advice/prediction language in the read ('bleed'); refusing to publish it"

== 2026-10-10: REFUSED  path=-  model calls=3  reason="chartmaster: an open-interest figure names no venue in its own sentence ('Open interest holds while the majors rest The regime reads as intact: the majors sit a"

== 2026-10-11: REFUSED  path=-  model calls=3  reason="chartmaster: advice/prediction language in the read ('bleeding'); refusing to publish it"

RESULT: at least one refused
```
Green on branch (published texts):
```

== 2026-10-09: PUBLISHED  path=reworded  model calls=2  reason='reworded'
   ledger: {"date": "2026-10-02", "path": "reworded", "tripped": ["bleed", "bleed"], "detail": "bleed->fall; bleed->fall", "t": "2026-10-12T19:41:22Z"}
   headline: Longs fall fees
   - The regime reads as intact: the majors sit above their 200-day lines and the crosses agree.
   - Momentum is resting while the trend holds, which is a finding rather than a signal.
   - Shorts fall when a trend line turns, a condition worth watching.

== 2026-10-10: PUBLISHED  path=data-only  model calls=2  reason='data-only'
   ledger: {"date": "2026-10-02", "path": "data-only", "tripped": ["chartmaster: an open-interest figure names no venue in its own sentence ('Open interest holds while the majors rest The "], "detail": "not an advice word; the table cannot help: chartmaster: an open-interest figure names no venue in its own sentence ('Open interest holds while the majors rest The ", "t": "2026-10-12T19:41:22Z"}
   headline: Chart Master data card: levels, 50-day and 200-day lines, RSI

== 2026-10-11: PUBLISHED  path=reworded  model calls=2  reason='reworded'
   ledger: {"date": "2026-10-02", "path": "reworded", "tripped": ["bleeding"], "detail": "bleeding->falling", "t": "2026-10-12T19:41:22Z"}
   headline: Shorts are falling as the majors hold their lines
   - The regime reads as intact: the majors sit above their 200-day lines and the crosses agree.
   - Momentum is resting while the trend holds, which is a finding rather than a signal.
   - Watch for the trend lines to cross, which would tell a reader the positioning picture changed.

RESULT: all three published```

## Item 2, the beacon
Every page now loads exactly one Cloudflare beacon, home included. Canary `_beacon_canary`: 803 of 803 built pages carry exactly one; on main's tree it failed `index.html=0`. Privacy page says it plainly. Home weight at 375 on its own host (local build, third hosts aborted): **before 225,565 bytes, after 225,740 bytes** (+175, the tag). The beacon itself is **31,679 bytes** (about 10.2 KB gzip) from `static.cloudflareinsights.com`, weighed against its own 40 KB allowance. The 300 KB ceiling stays on the own host. `home_budget.mjs` now names the beacon hosts instead of failing on them.

## Item 3, the ledger
`ops_ledger.is_empty_row`: a run with no model, no push, no ping and no Chart Master call is not committed; one line says so. **Breaking runs are never skipped**, because `watcher.py` counts the day's breaking runs from `ledger.json`. The issue-comment row still posts.

## Also fixed
`scripts/color_truth_test.py` read a gitignored `site/data/snapshot.json`, so the canary crashed on any fresh clone (it did here, on main too). It now builds the snapshot from the committed Board files. This may have been red in CI since 7.1.

## Proof status
- Canary on the branch tree, fresh clone: `LAYER 1 CANARY: PASS`, exit 0.
- Screenshots (fixture morning, Tuesday 8:30 AM, reworded Chart Master read): `shots/program7-7.2/` home and chartmaster at 375 and 1440, light and dark.
- **Jack's yes: not given. Merge: not done. Merge hash, production reads, counts after the merge, the live 8:15 AM proof: not done.** They need Jack, the Worker change, the 13 October build budget, and a real run.

TZ=America/New_York date at close: see the last line.
TZ end: Mon Oct 12 16:02:30 EDT 2026

## Addendum, after Jack's approval (5:30 PM ET, 12 October)
1. **Substitution table removed.** On a flag: one told retry, then each flagged sentence is DROPPED, a flagged headline is replaced by a data headline built from the levels ("Majors hold above their 200-day lines"), fewer than two sentences left publishes the data-only card. Never a reworded sentence. Per-sentence flags include the belts (so the Oct 10 open-interest sentence is cut, not the read).
2. **Ledger dates fixed:** the fixtures now carry their own night (2026-10-09, 10, 11); the earlier 2026-10-02 was the recorded digest's date leaking into the test.
3. **Noon refresh retired:** `CRYPTO_DAILY_ET` is empty in the Worker; HANDOFF's allowance line amended (automatic builds are two). `docs/RULES.md` does not name the noon refresh and is hash-protected, so it is unchanged.
4. **Worker change:** `jaybiz0131/gcm-newsroom`, branch `morning-dispatch`, `slot-trigger/`. Dispatches `morning-read.yml` at 8:15 AM America/New_York (12:15Z in EDT, 13:15Z in EST), one dispatch a day across 288 ticks on each side of 1 November; `node slot-trigger/test/morning.test.mjs` 14 passed (red on the old worker); counts tests still 95 passed. Not deployed.

Published texts, drop-not-reword (branch):
```

== 2026-10-09: PUBLISHED  path=cut  model calls=2  reason='cut'
   ledger: {"date": "2026-10-09", "path": "cut", "tripped": ["headline: advice: bleed", "advice: bleed"], "detail": "dropped 1 sentence(s): Shorts bleed when a trend line turns, a condition worth watching.; data headline used", "t": "2026-10-12T21:24:04Z"}
   headline: Majors hold above their 200-day lines
   - The regime reads as intact: the majors sit above their 200-day lines and the crosses agree.
   - Momentum is resting while the trend holds, which is a finding rather than a signal.

== 2026-10-10: PUBLISHED  path=cut  model calls=2  reason='cut'
   ledger: {"date": "2026-10-10", "path": "cut", "tripped": ["headline: belt: chartmaster: an open-interest figure names no venue in its own sentence ('Open interest holds while ", "belt: chartmaster: an open-interest figure names no venue in its own sentence ('Open interest is sizable ("], "detail": "dropped 1 sentence(s): Open interest is sizable (BTC near $2.49B, ETH near $1.1B), which measures how m; data headline used", "t": "2026-10-12T21:24:04Z"}
   headline: Majors hold above their 200-day lines
   - The regime reads as intact: the majors sit above their 200-day lines and the crosses agree.
   - Momentum is resting while the trend holds, which is a finding rather than a signal.

== 2026-10-11: PUBLISHED  path=cut  model calls=2  reason='cut'
   ledger: {"date": "2026-10-11", "path": "cut", "tripped": ["headline: advice: bleeding"], "detail": "dropped 0 sentence(s); data headline used", "t": "2026-10-12T21:24:04Z"}
   headline: Majors hold above their 200-day lines
   - The regime reads as intact: the majors sit above their 200-day lines and the crosses agree.
   - Momentum is resting while the trend holds, which is a finding rather than a signal.
   - Watch for the trend lines to cross, which would tell a reader the positioning picture changed.

== synthetic, every sentence flagged: data-only card published  ledger={"date": "2026-10-12", "path": "data-only", "tripped": ["headline: advice: bleed", "advice: bleeding", "advice: you should, buy now", "advice: will rise, price target"], "detail": "0 sentence(s) left after cutting 3", "t": "2026-10-12T21:24:04Z"}

RESULT: all three published
```
Red on main: all four fixtures refuse or fail (the synthetic all-flagged case has no data-only path on main).

## Addendum 2, the Worker's noon fallback (12 October, evening)
Safe to deploy before the workflow is on main: at noon ET the Worker asks GitHub whether a `morning-read.yml` run exists today (Eastern) and is green or still running; if not (404, refused dispatch, failed run, GitHub or token unreachable) it POSTs the old `CRYPTO_BUILD_HOOK`. A green morning fires nothing. `gcm-newsroom` `morning-dispatch` at `f78497f`: `morning.test.mjs` 31 passed (14 earlier plus the fallback in both offsets, the 404 case, a failed run, an unreachable GitHub, no token, and two end-to-end days); the fallback cases fail on the previous commit. Known edge: a morning run that pushes and then fails its second-day alarm reads as failed, so noon adds one build that day.
