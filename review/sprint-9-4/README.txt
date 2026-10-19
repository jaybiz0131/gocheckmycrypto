review/sprint-9-4: Big movers, checked (Program 9, Sprint 9.4), after review 1, on three pages at 390 and
1440 px, light and dark: a mover's coin page (/coins/tia), its verdict page (/why/2026-10-16-celestia) and
/pulse/movers, whose one list is now Big movers. Full pages. Recaptured Monday October 19 2026, about 6:20 PM
EDT, by the builder; the 4:15 PM captures are replaced under the same names.

THESE ARE LOCAL BUILDS, NOT THE PREVIEW OR PRODUCTION (U-10). No preview URL exists for this branch, so
nothing here was read from a deployed page; the production read is owed after the merge.

How they were built: a throwaway copy of the branch tree (the repository's own site/data was never written),
site/data/pulse.json replaced by the Board the morning read committed at 9c8af54 (generated
2026-10-16T12:16:53Z), and site/data/movers/2026-10-16-morning.json built by movers.build from the recorded
answers in fixtures/movers/ (README.txt there) and graded by verdict.record_from: the rules in code, no model
call, the graded line built from phrases, which is the exact path a run takes with no API key. Then
`python3 site_build.py` with SITE_BUILD_NOW=2026-10-16T12:30:00Z, and scripts/page_shots.mjs (headless
Chromium, every other host aborted, the browser closed in a finally, U-7).

What the real day gives: five rows of the Board's Top 100 passed the gate on October 16 (TIA, INJ, ZRO, ETHFI,
PENDLE), each listed with its place in the Top 100 (the number the coin page prints), and each grades Unclear:
the only candidate that names any of them is a CoinMarketCap token unlock for TIA at 00:00 UTC, which fails the
timing test (and, as new supply beside a rise, could not line up with it). So the card reads "No reported event
lines up with this move." No recorded day gives a mover a Likely, Disputed or Confirmed card, so none is
pictured; the tests reach a named card only through cases marked SYNTHETIC. The volume column reads "not read"
(CoinGecko answered 429, or for INJ reached only 4 days before this past window). October 16 is no crash day
by the audit's numbers (Bitcoin +1.48%, twelve coins past 10%), and no coin was past the cap or left out for
history, so those lines do not show here; the tests reach them, the crash day and the cap on the real Board
with one figure changed or 8 reads made earlier (SYNTHETIC and real respectively), the left-out reason with
stored closes removed (SYNTHETIC).

The pages read "3 days ago" because the build's clock is October 16 and the browser's is today's; the stale
state is the site's own, working as built. At 390 the list scrolls sideways inside its own box from the
"Its usual day" column on; the 24h column is the first after the name.

The recorded day with no coin past the line: the Board read October 19 at 4:30 PM EDT
(fixtures/movers/board_raw.json). PUMP +11.46%, VVV +13.74% and CRV +10.13% each moved under 2.5 times their
30-day daily volatility (1.51x, 2.23x and 2.10x), so no coin passed. Its gate log, as the test case prints it:
  movers: gate fail VVV +13.74%: 2.23x its 30-day daily volatility of 6.16% (needs 2.5x)
  movers: gate fail PUMP +11.46%: 1.51x its 30-day daily volatility of 7.57% (needs 2.5x)
  movers: gate fail CRV +10.13%: 2.10x its 30-day daily volatility of 4.82% (needs 2.5x)
  movers: no top-100 coin passed the gate (3 measured, 0 left out for history)
(Three measured because the fixture holds stored closes for those three coins and Bitcoin only.)
