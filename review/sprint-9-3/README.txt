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

RECAPTURED AFTER REVIEW 1, Monday October 19 2026, about 11:01 AM EDT, by the builder, all 28 files replaced
under the same names, the same way: a throwaway copy of the branch tree, SITE_BUILD_NOW=2026-10-19T12:30:00Z,
the same three records graded by verdict.record_from with no model call, headless Chromium (the global
playwright, closed in a finally, U-7) on a local server, every other host aborted, the page clock fixed at
2026-10-19T12:30:00Z, the fixed tab bar hidden. Each slice now runs from just above the card to the end of
"What lined up with the move" when the page has that section (else to the block under the card), so the
changed notes at the section's end show; 390 slices run 4,509 to 5,611 px tall. Every page measured no
horizontal overflow at 390 and 1440.

What changed on every page with a card, and why (the reviewer's four failures and four items):
  - The grade chip is neutral: Confirmed and Likely take --ink (Confirmed on --tag-bg), never --verified-fg
    or --verified-bg, which system.css sets to the up green. Disputed keeps the review tokens, Unclear the tag
    tokens. Word, dot and edge are the designer's, unchanged.
  - The card shows the readings its grade rests on, under a hairline, named with their own hour: "the hour
    after it" with its figures (the hour after the release; the coin's own figure is left out because the
    evidence list prints it), or "the hour the run began" with no figures (the section below prints them).
  - The direction word names its window: "Bitcoin's fall over the 24 hours to 7:43 PM ET", "the 24-hour fall".
  - The definitions: Likely needs the readings to agree; no definition says "silent".
  - A page with a graded card no longer denies a cause: the evidence note, /today/'s reported note and the
    coin page's wire note point at the verdict instead. Pages with no grade keep 9.2's words.
  - 19 October: stock futures did not trade in the hour the run began, so the section no longer labels it
    "crypto only"; it says the futures did not trade, as the card does.
  - /why/2026-10-14-bitcoin no longer links /today/2026-10-14, which does not exist.
