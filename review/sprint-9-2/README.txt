review/sprint-9-2: "What lined up with the move" (Program 9, Sprint 9.2), the section only, as element
screenshots of four pages at 390 and 1440 px, light and dark: /today/2026-10-14, /today/2026-10-15,
/coins/btc and /coins/eth. Taken Sunday October 18 2026, about 2:15 PM EDT.

THESE ARE LOCAL BUILDS, NOT THE PREVIEW OR PRODUCTION (U-10). No preview URL exists for this branch, so
nothing here was read from a deployed page; the merge's production read is still owed after the merge.
Sprint 9.1's screenshots were taken the same way, from local builds of real recorded data.

How they were built: a throwaway copy of the branch tree, `python3 site_build.py` with
SITE_BUILD_NOW=2026-10-15T23:50:00Z, then a headless Chromium (playwright, launched with a timeout and
closed in a finally, U-7) on a local server, every other host aborted.
  - Evidence records: site/data/why/2026-10-14-evening.json and 2026-10-15-evening.json, each built by
    why_evidence.build from the recorded fixtures fixtures/why/sources_2026-10-14T2343Z.json and
    sources_2026-10-15T2343Z.json with the wire and pulse the 14 and 15 October Editions committed
    (scripts/sprint92_test.py rec()). Real recorded data; no figure typed by hand.
  - The Board for the coin pages: pulse, flows and wire as the 15 October Edition committed them
    (94dd6af; fixtures/why/pulse_, flows_ and wire_2026-10-15T2343Z.json).
  - /today/2026-10-15 is the stored record site/data/today/2026-10-15-evening.json, with its two
    corrections. Its correction quotes the producer-price wire line, and the section does not print it.
  - /today/2026-10-14 has no stored daily-answer record (the stored records begin October 15). For
    these shots only, one was composed in the throwaway tree by the real today.compose from the files
    the 14 October Edition committed (7d9008b: pulse, flows, morning read, wire, and
    site/content/2026-10-14-evening-brief.json) at 7:50 PM ET October 14. It is not committed and does
    not exist on the site.

The fixed tab bar crosses some shots partway down: that is the capture of a fixed element, not the
page. The "N days ago" mark beside the window on the coin pages is asof.js reading the window's stamp
against today's clock, as it should.
