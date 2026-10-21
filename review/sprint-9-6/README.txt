review/sprint-9-6: the share loop, re-aimed (Program 9, Sprint 9.6), for Jack's read after the fact.
Drawn Tuesday October 20, 2026, between 10:15 and 10:40 AM EDT, and the 14 October card and the two queue entries re-drawn after review 1
(this README's REVIEW 1 section). Local branch local-sprint-9-6 (built on Sprint 9.5's reviewed head 2453529, with 9.5b merged).

U-10 CAVEAT, FIRST: THESE ARE LOCAL DRAWINGS, NOT THE PREVIEW OR PRODUCTION. No preview URL exists for this branch and it is not pushed.
Every image here was drawn by share_cards.render() from a stored or recorded record on this machine, and the head-tags file is the
text verdict.build_pages wrote on this machine. Nothing was read from a deployed page. The merge's production read (the card's file
present at /og/why/<slug>.png on the deployed site, 1080 by 1080, named by the page's og:image) is still owed after the merge. The
fonts are the repo's own shipped faces (site/assets/fonts/IBMPlexMono-SemiBold.ttf, IBMPlexMono-Medium.ttf, Newsreader.ttf); the
renderer refuses to draw with a stand-in face (share_cards.fonts_ok), and a test proves it refuses.

THE RECORDS
  REAL   14 October evening: the evidence record built by why_evidence.build from the recorded fixture
         fixtures/why/sources_2026-10-14T2343Z.json (as scripts/sprint92_test.py rec() builds it), graded by verdict.record_from
         with no model call. Bitcoin grades Likely on the Consumer Price Index release and the Real Earnings release, both
         8:30 AM ET, both with the BLS release schedule as their source.
  REAL   15 October evening: the same, from fixtures/why/sources_2026-10-15T2343Z.json. Bitcoin grades Unclear.
  REAL   19 October evening: the stored verdict record site/data/verdict/2026-10-19-evening.json as the run committed it. Bitcoin was
         not graded (the page's window and the run the timing test measured went opposite ways) and Ether moved with Bitcoin.
  REAL   16 October morning Big movers record (fixtures/movers/, scripts/sprint94_test.py record16), Celestia, graded by code with the
         model mocked at the HTTP layer as in Sprint 9.4's tests, so its words are the graded line built from phrases.
  SYNTHETIC  card-SYNTHETIC-confirmed.png: the 14 October record with the Consumer Price Index release made a primary source's own
         line that states the cause. card-SYNTHETIC-disputed.png: the 14 October record with two outlets naming different causes (the
         release and the Kraken acquisition), the Kraken item made to pass the timing test. No recorded day gives Confirmed or
         Disputed; these two say SYNTHETIC in their names and exist to show those grades' shapes (Jack, 13 October 2026).

THE FILES
  card-2026-10-14-bitcoin-likely-REAL.png          the verdict card for /why/2026-10-14-bitcoin
  card-2026-10-15-bitcoin-unclear-REAL.png         the verdict card for /why/2026-10-15-bitcoin
  card-2026-10-16-celestia-mover-REAL-record.png   a Big mover's verdict card for /why/2026-10-16-celestia
  card-SYNTHETIC-confirmed.png, card-SYNTHETIC-disputed.png
  day-2026-10-14-REAL.png, day-2026-10-15-REAL.png the day cards for days with a graded verdict
  day-2026-10-19-no-verdict-REAL.png               the day card for a day with no graded verdict: it says so and invents none
  why-2026-10-14-bitcoin-head-tags.txt             the Open Graph and Twitter lines of that page's head, as built
  queue-2026-10-14-why-bitcoin.md, queue-2026-10-14-why-day.md   the two entries share_queue.py files for that day, as written
  plants.log                                       the U-9 plants: each guarded thing broken on purpose, the test seen red, restored, green

WHAT IS NOT HERE, AND WHY
  A card for "Verdict at the next read" and one for a verdict withheld at the cap: by design neither makes a card (tested).
  A flat day: no verdict record is graded and the day card says no verdict was graded; no recorded flat day with a /today/ page is in
  the stored data beyond 19 October's, which is shown.
  The queue's image lives at the build's og/why/<slug>.png once the build that carries the verdict has deployed; nothing per-card is
  committed to the repository (the repo's existing rule for share images, scripts/og_render.py).

REVIEW 1 (the six fixes; the cards and entries that changed are re-captured)
  card-2026-10-14-bitcoin-likely-REAL.png was re-drawn: the two 8:30 AM events share the hour after, so "The next 60 minutes after the
  Consumer Price Index release and the Real Earnings release: 1.45%" prints ONCE, naming both, instead of once under each. No other card's
  content changed (the Disputed card's two events are at different hours and keep their own figures; the Unclear cards print no figure).
  queue-2026-10-14-why-*.md were re-filed: they now open "# Share draft:" and are filed in share-queue/, a folder of its own (the desk
  does not post to LinkedIn; linkedin-queue/ and the publicist are untouched). The post line is unchanged.
  Pillow is optional: share_cards imports it only when a card is drawn. Without it no image is drawn, every /why/ page keeps the site card
  and its place in the sitemaps, and the canary passes; the drawing cases print named INFO lines and skip. plants-after-review-1.log is the
  plants log for this round (45 plants: the 38 earlier plus seven new); plants.log and plants-after-9.5b-merge.log are the earlier rounds.
  The queue window is the last 3 Eastern dates (today and the two before it), tested on its boundary. A Confirmed day gets its day card
  (a Confirmed verdict's own sentence may say "because", in its card or its day card, nowhere else). A day card's figures are checked against
  the pages that print its verdicts, not against its own words.
