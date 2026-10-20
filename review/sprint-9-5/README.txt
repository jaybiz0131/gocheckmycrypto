review/sprint-9-5: names, the answer-first front and trust (Program 9, Sprint 9.5), the designer's pass, at 390 and
1440 px, light and dark. Taken Tuesday October 20 2026, about 3:50 AM EDT.

THESE ARE LOCAL BUILDS, NOT THE PREVIEW OR PRODUCTION (U-10). No preview URL exists for this branch, so nothing here
was read from a deployed page; the merge's production read is still owed after the merge.

How they were built: a throwaway copy of the branch's tracked files with the designer's changes (the repository's
own site/data was never written), `python3 site_build.py` with SITE_BUILD_NOW=2026-10-20T07:20:00Z, then the
builder's fixture pages written into that tree by scripts/sprint95_test.py fixture_pages(). Captured by headless
Chromium (playwright, launched with a timeout and closed in a finally, U-7) from a local server, every other host
aborted except CoinGecko's market_chart route, answered from the recorded fixtures/coingecko files. The page clock
is fixed per page (below). A full-page shot is taken with the window as tall as the page, so the phone tab bar is
drawn where it sits at the end of a scroll, under the footer; nothing is hidden for the capture.

Records used, all real (Jack, October 13: screenshots for approval are drawn from real recorded data):
  - home-card, home-card-first-screen: home-fixture-card.html, the home's top (the verdict card, the Bitcoin line,
    the Brief card, Where Bitcoin stands and the blocks under it) rendered by home.above_fold from the recorded
    15 October Board (fixtures/why/pulse_2026-10-15T2343Z.json, with flows_ and wire_ of the same read) with the verdict that
    Board really grades, verdict.record_from on the 15 October evidence record: Unclear, "No reported event lines
    up with this move." No model call. Page clock 2026-10-15T23:50:00Z. It is the home's first screen and blocks,
    not the full home: the fixture carries no masthead data of that day and no footer content of its own.
  - home-nocard, home-nocard-first-screen, today, flows, coins-btc, pulse-movers, method, corrections,
    bottom-line, bottom-line-2026-09: today's real data as committed on the branch (the Board read
    2026-10-19T23:12:46Z, the 19 October evening verdict record, which grades no card on the home: Bitcoin was
    flat on the ET day). Page clock 2026-10-20T07:25:00Z, so the stale state reads "8 hours ago" as a reader
    would see it this morning. /pulse/movers today has no coin past the line, so it shows no table.
  - pulse-movers-oct16 (and -toggled): movers-fixture.html, Big movers rendered from the real 16 October Board
    (fixtures/movers/pulse_2026-10-16T1216Z.json, the read committed at 9c8af54) and its movers record built from fixtures/movers by scripts/sprint94_test.py record16(),
    graded with no model call. Page clock 2026-10-16T12:30:00Z. This is the table with the toggle.
  - coins-btc: the 7D chart is drawn from the recorded fixtures/coingecko file, which is an early-October week, so
    its date axis does not match the page's stamp. The page's own data is today's.
  - -toggled files: the same page at 390 after one tap on "Show all columns".

What the designer changed (CSS in system.css and site.css, and the month list's markup in site_build.py; no new
token, face, color, script or component, and no data, name, copy, grade or URL):
  - The phone tab bar is as the builder made it and measured sound: five tabs of 56 px at 375 and 390, every label
    inside its cell at 11 px (the widest, "Why it moved", 69 of 75 px; 12 px would not fit), the current tab marked
    by the bar across its top, a heavier label and aria-current as well as its ink, and the page keeps 60 px for
    the bar: on every page measured the footer ends 3 px above the bar.
  - The home: a gap under the Brief card, so "Where Bitcoin stands" no longer sits on its edge now that the Bitcoin
    card opens that block.
  - Tables that fit 375 (Big movers, Whale Watch by exchange): the head is the living table's head (mono caps,
    muted, left over its column, a rule under it), the coin's name sits left with the rule under it like every
    other cell. Before, the heads were centered over left-set figures and the name column broke every row's rule.
  - The coin page's foot: the Ledger card's text at its own sizes (the prose page's 17 px rule was reaching in) and
    the related links after it as 44 px targets with room above.
  - /today/ and the evidence section: the stamp line, the next-update line and the evidence window line at their
    own small mono sizes; the same prose rule had been setting them at 17 px.
  - Corrections: each entry is the card a corrected story carries (the rule edge on the left), the date small in
    the mono, the story's title in the serif, the correction in the serif.
  - The Brief's months: one target per month, styled as the coin chart's range tabs, the month shown filled; the
    count of Briefs inside the target (with " Briefs" for a screen reader).

Every page measured no horizontal overflow at 390 and 1440 (scrollWidth equal to the viewport).
