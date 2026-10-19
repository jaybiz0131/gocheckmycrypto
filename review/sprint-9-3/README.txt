review/sprint-9-3: the verdict card (Program 9, Sprint 9.3), its look by the designer, on seven pages at
390 and 1440 px, light and dark: the home (/), /today/, /today/2026-10-15, /coins/btc, /coins/eth,
/why/2026-10-14-bitcoin and /why/2026-10-19-bitcoin. Each shot is a slice of the full page from just
above the card to the section under it, so what sits beside the card shows. Taken Monday October 19 2026,
about 10:10 AM EDT.

THESE ARE LOCAL BUILDS, NOT THE PREVIEW OR PRODUCTION (U-10). No preview URL exists for this branch, so
nothing here was read from a deployed page; the merge's production read is still owed after the merge.

How they were built: a throwaway copy of the branch tree (the repository's own site/data was never
written), `python3 site_build.py` with SITE_BUILD_NOW=2026-10-19T12:30:00Z, then a headless Chromium
(playwright, closed in a finally, U-7) on a local server, every other host aborted, the page clock fixed
at 2026-10-19T12:30:00Z and the fixed tab bar hidden for the capture.

Records used, all graded by verdict.record_from (the rules in code, no model call, the graded line built
from phrases: the exact path a run takes with no API key):
  - 19 October, morning: the real evidence record site/data/why/2026-10-19-morning.json, as the morning
    run committed it. Bitcoin grades Unclear; Ether "moved with Bitcoin". This is the card on the home,
    /today/, /coins/btc, /coins/eth and /why/2026-10-19-bitcoin.
  - 14 October, evening: the evidence record built by why_evidence.build from the recorded fixture
    fixtures/why/sources_2026-10-14T2343Z.json (scripts/sprint92_test.py rec()). Bitcoin grades Likely
    (the CPI release). This is /why/2026-10-14-bitcoin.
  - 15 October, evening: the same, from fixtures/why/sources_2026-10-15T2343Z.json. Bitcoin grades
    Unclear; Ether "moved with Bitcoin". With the stored daily record site/data/today/2026-10-15-evening.json
    (its corrections) this is /today/2026-10-15.
The real data gives Likely, Unclear and "moved with Bitcoin". No recorded day gives Confirmed, Disputed or
a flat day, so those shapes are not shown here; their styles are in site.css with the rest.

The grade is told apart without color three ways: its word, its dot (Confirmed full, Likely half,
Disputed hollow, Unclear none) and its chip's edge (Confirmed filled, Likely solid outline, Disputed
dashed, Unclear dotted).

Every page measured scrollWidth equal to the viewport at 390 and 1440 (no horizontal scroll).
