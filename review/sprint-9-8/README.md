review/sprint-9-8: the verdict record, /why/record/ (Program 9, Sprint 9.8), for Jack's read after the fact.
Drawn Sunday October 25, 2026, about 1:52 PM EDT, on local branch local-9-8 (from origin/main 7f04343).

U-10 CAVEAT, FIRST: THESE ARE LOCAL CAPTURES, NOT THE PREVIEW OR PRODUCTION. The branch is not pushed and no preview exists.
Every image is a full-page capture by scripts/sprint98_shots.mjs (Playwright, Chromium) of a tree built on this machine by
`python3 site_build.py` from the branch's code and the stored records committed on main, served locally, every other host refused.
The fonts are the site's own shipped faces. The production read (the page at /why/record/ on the deployed site) is owed after merge.

THE RECORDS
  REAL       record-REAL-*: the page as the build draws it from the stored records: site/data/verdict/ (2026-10-19 evening,
             2026-10-20 morning and evening) and site/data/movers/ (2026-10-20 morning and evening). None of those reads graded a
             move (the next read, flat, Ether with Bitcoin, no grade fits; no mover past the gate), so the honest state is the one
             shown: every count zero, "No move has been graded since the record began", the window from the first verdict record
             (7:16 PM ET on Oct 19, 2026) through the newest read (7:15 PM ET on Oct 20, 2026), marked stale ("4 days ago") by
             snapshot.is_stale at the build's moment, and the reads that ran counted (3 of Bitcoin and Ether, 2 of Big movers).
  SYNTHETIC  record-FIXTURE-SYNTHETIC-*: the page drawn from scripts/sprint98_test.py's fixture by scripts/sprint98_fixture_page.py,
             written into a copy of the built tree at /why/record-fixture/ (a capture path only; nothing ships there). The fixture is
             the real 14 October Likely verdict (CPI and Real Earnings releases), the real 15 October Unclear verdict and the real
             16 October morning Big movers record (five Unclear, model mocked as in 9.4's tests), restamped and regraded by hand to make
             later reads of the same move, which no recorded day gives (Jack, 13 October 2026): 14 October morning Likely confirmed
             later by the evening's Confirmed on the CPI release; 15 October morning Likely REVERSED by the real 15 October evening
             Unclear; 16 October evening Likely awaiting; one Confirmed, one Disputed, six Unclear. Its window ends 7:16 PM ET on
             Oct 17, 2026, so the browser's stale script marks it "7 days ago" when read on October 25; that is the stale rule
             working on an old fixture, not a fault.

THE FILES (each full page)
  record-REAL-390-light.png  record-REAL-390-dark.png  record-REAL-1440-light.png  record-REAL-1440-dark.png
  record-FIXTURE-SYNTHETIC-390-light.png  record-FIXTURE-SYNTHETIC-390-dark.png
  record-FIXTURE-SYNTHETIC-1440-light.png  record-FIXTURE-SYNTHETIC-1440-dark.png
  No capture scrolls sideways (the script read the page width at each viewport: 390 at 390, 1440 at 1440).

WHAT WAS CHOSEN, AND WHY
  The page sits in the site's narrow reading column (the corrections log's and How we check's), under the "Why it moved" kicker,
  with the Why it moved tab marked. The tally is one card in the verdict card's frame: the window line first in the mono stamp style
  (the one place the counts are dated, with data-asof for the stale script), then the Likely verdicts as three cells (confirmed later
  edged in ink, reversed edged in the site's rule red, awaiting plain) and the other grades as three cells, and the reads counted
  last. Each count prints once, there and nowhere else. The list below is the corrections log's card per entry: the read and its time
  in the mono, the /why/ page's title in the serif, the grade in the verdict card's own badge shapes, and for a Likely its outcome in
  one plain sentence. Green and red are not used: on this site they mean up and down. Tokens only; no new font, script or color.
