review/sprint-9-4: Big movers, checked (Program 9, Sprint 9.4), on three pages at 390 and 1440 px, light and
dark: a mover's coin page (/coins/tia), its verdict page (/why/2026-10-16-celestia) and /pulse/movers with
the Big movers list. Full pages. Taken Monday October 19 2026, about 5:15 PM EDT, by the builder.

THESE ARE LOCAL BUILDS, NOT THE PREVIEW OR PRODUCTION (U-10). No preview URL exists for this branch, so
nothing here was read from a deployed page; the production read is owed after the merge.

How they were built: a throwaway copy of the branch tree (the repository's own site/data was never written),
site/data/pulse.json replaced by the Board the morning read committed at 9c8af54 (generated
2026-10-16T12:16:53Z), and site/data/movers/2026-10-16-morning.json built by movers.build from the recorded
answers in fixtures/movers/ (README.txt there) and graded by verdict.record_from: the rules in code, no model
call, the graded line built from phrases, which is the exact path a run takes with no API key. Then
`python3 site_build.py` with SITE_BUILD_NOW=2026-10-16T12:30:00Z, and scripts/page_shots.mjs (headless
Chromium, every other host aborted, the browser closed in a finally, U-7).

What the real day gives: four top-100 coins passed the gate on October 16 (TIA, INJ, ZRO, ETHFI), and each
grades Unclear: the only candidate that names any of them is a CoinMarketCap token unlock for TIA at
00:00 UTC, which fails the timing test. So the card reads "No reported event lines up with this move."
No recorded day gives a mover a Likely, Disputed or Confirmed card, so none is shown; the tests reach a
named card only through a case marked SYNTHETIC, which is not pictured. APT moved 14.03% that day but the
fixture holds no stored closes for it (its history read answered 429), so the list names it as not
measured. The volume column reads "not read" because CoinGecko's daily volumes answered 429 when recorded.

The pages read "3 days ago" because the build's clock is October 16 and the browser's is today's; the
stale state is the site's own, working as built.

The recorded day with no coin past the line: the Board read October 19 at 4:30 PM EDT
(fixtures/movers/board_raw.json). PUMP +11.46% and VVV +13.74% each moved under 2.5 times their 30-day daily
volatility (1.51x and 2.23x), so no coin passed. Its gate log, as the test case prints it:
  movers: gate fail VVV +13.74%: 2.23x its 30-day daily volatility of 6.16% (needs 2.5x)
  movers: gate fail PUMP +11.46%: 1.51x its 30-day daily volatility of 7.57% (needs 2.5x)
  movers: no top-100 coin passed the gate (2 measured, 0 left out for history)
(Two measured because the fixture holds stored closes for those two coins and Bitcoin only.)
