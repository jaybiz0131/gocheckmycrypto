# Program 9, Sprint 9.2: the evidence (report)

Status: **MERGED 18 October 2026, pushed 9:58 PM ET, merge `66ba069`**, on the reviewer's PASS (third review) under Jack's October 18 ruling, with the user's yes in the session. No model call anywhere in this sprint.

## Start
- `docs/RULES.md` body hash (from line 11): `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`. It matches.
- main at the start: `2d54bdf`. Shell date, ET, at the start: Sun Oct 18 2026, 12:37 PM.
- Branch: built on `claude/sleepy-sagan-xcfcw9`, not `sprint-9-2`, by a session constraint on which branches may be pushed. One branch, one merge build, as the board requires.

## Commits
- `0ed9b60` the evidence: `why_evidence.py` and "What lined up with the move".
- `31ddf0e` review fix 1: every named source read or named, corrections reach the section, screenshots.
- `3d9d4d7` review fix 2: the Kalshi row names its closes; the run step has a deadline.
- `66ba069` the merge into main at `649f535` (the 18 October Edition and its ledger had landed; nothing else).

## What shipped
- `why_evidence.py`: the 5-minute series (CoinGecko, then Coinbase, OKX, Kraken and Binance's data-api mirror, a second venue kept for agreement); candidates with an event time and a first-report time (the wire after 9.1's source check, BLS and BEA schedules, the FOMC file, Fed, SEC and CFTC feeds, DefiLlama hacks, the Federal Register); commentary-only causes marked secondary; the timing test (onset at the start of the largest same-direction run, lead within 60 minutes or at the scheduled release, share of the move in the hour after, price moved first); the onset hour's mechanics (Yahoo 5-minute cross-asset including ZT=F and IBIT and FBTC volume, OKX open interest, taker flow and funding, Gate liquidations, Kalshi KXFED) and the pattern label.
- Records at `site/data/why/<date>-<slot>.json`, frozen once written. Both workflows run `timeout 300 python3 why_evidence.py --write || true` after `today.py --write`. `build()` holds a 200 second budget: the series and the timing test are read first, every other source is skipped and named "not read in time" past the deadline or on SIGTERM, and the record is still written.
- `/today/` and the Bitcoin and Ether pages render the section and the timing chart, with no grade word and no "because". A wire line that a page's correction quotes is dropped from the section. Coin pages show it only when the record's window ended within 3 hours of the Board reading. No record, no section: the page renders as before.
- Every audit source is read or named with its reason: Hyperliquid (no public market-wide liquidation history), Nasdaq's calendar (dates a day late), ForexFactory for past windows (current week only), EDGAR 8-K (day only), exchange listing notices (no single feed; 9.4 owns them). OKX liquidations reach the latest 100 orders; Gate covers the onset hour.

## Tests
- `scripts/sprint92_test.py`, 117 cases in 11 groups, run inside the canary. Red logs: `docs/sprint92-red-on-main.log`, `docs/sprint92-fix1-red.log`, `docs/sprint92-fix2-red.log`. Each fix's plants were seen red, then green.
- Fixtures under `fixtures/why/` are real answers recorded 18 October; the canary builds from the 15 October fixture record and fails if it meets no section.
- On the merged tree: `LAYER 1 CANARY: PASS` (exit 0) and `SPRINT 9.2: PASS`.

## Review
- Review 1 FAIL: readable sources left out or unnamed; a retracted wire line printing beside its own correction on `/today/2026-10-15`; no screenshots under `review/`.
- Review 2 FAIL: the Kalshi row's window was not the one its heading named; the run step could pass `timeout 300` (live 155 s, Kalshi 126 s) and lose the slot's whole record.
- Review 3 PASS at `3d9d4d7`: live `build()` 39.8 s for 52 reads; worst case every host hanging gives a coinless record that reads as absent, so the pages fail open; SIGTERM writes a well-formed partial record.
- Screenshots: `review/sprint-9-2/`, 16 local captures (4 pages, 390 and 1440, light and dark) of real recorded data. No preview URL exists, so U-10's preview rule is not met; the README says so, on 9.1's precedent.

## Production read
- Worker count of record, read 2026-10-19T02:0xZ: `last:gocheckmycrypto:production` `66ba069`, state ready, at 2026-10-19T02:03:57Z. Crypto built 3 of 5 for 18 October (the morning read, the Edition, this merge).
- `https://gocheckmycrypto.com/assets/site.css` carries the `.ev-` styles. The section is not live yet: no record is committed, and the first workflow run after the merge writes one.

## Not done
- No section live until the 19 October morning read writes the first record; that read is the sprint's first real proof.
- The scorecard re-score after the merge is the strategist's.

## Proposals (proposals only)
1. **The onset, before 9.3 grades on it.** The onset is the start of the largest run measured from the window's own peak. On 14 October that is 4:10 AM ET, so CPI at 8:30 AM reads "after the run began" although the hour after it carried 71% of the fall. Every number on the page is true, but 9.3's grade would read CPI as not before the onset. The strategist should rule on the onset rule (for example, where the price first leaves a band around the pre-run level) or 9.3 should weigh the share after the event.
2. Pattern thresholds (0.3%, 0.2%, 0.1% hour moves, 1 point excess) are first settings; log misses for two weeks.
3. Records written after the budget is spent or on SIGTERM are frozen thin; consider letting the next run replace them.
4. When every feed is skipped and the wire is empty, the fallback "The desk found no reported event or scheduled release in this window" should say the feeds were not read.
5. Group 8's source catalog is hand-kept; build it from the audit's table instead.
6. Nasdaq's calendar could be used once its day offset is confirmed against BLS over a few weeks.
7. 9.1's Edition source check reads headlines and snippets; it may gain from reading CoinDesk pages whole, as this step does.
8. At 390 the chart's labels render at about 9.5 px, under section 3.4's 12 px; that belongs to 9.5.
