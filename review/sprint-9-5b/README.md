# Sprint 9.5b, the desktop board: the designer's screenshots

Made October 20, 2026 on local branch local-sprint-9-5b (the builder's b3e2294 plus the designer's pass, and the builder's J-11 pass, which re-captured the 375 and added 768 and 900), in a worktree. Nothing pushed.

## U-10 caveat

These are local builds, not the shipped site. No Netlify preview exists for this branch, so nothing here is a measurement of production.
Each image is a throwaway copy of the branch's working tree, built with `python3 site_build.py`, served from disk and drawn by headless
Chromium (Playwright). Every request to another host was aborted, so the coin page's chart shows its own fallback line ("The live history
did not load, so this is the build's seven-day line") and the masthead's live stamps read their build-time values.

## The clock

SITE_BUILD_NOW=2026-10-20T07:20:00Z for every build, the same moment as the builder's tree and the 9.5b baselines.

## The records (all real, nothing synthetic)

- home-card, home-nocard: scripts/sprint95b_fixture.py, the builder's fixtures. The recorded October 15 Board (fixtures/why: pulse, flows
  and wire of 2026-10-15) with the verdict it really grades (Unclear), and the same Board with no verdict.
- coins-btc, today, pulse-movers, flows, method: the branch's committed site/data (the Board last read 7:12 PM ET, October 19).
- why-2026-10-19-bitcoin: the recorded October 19 morning record (site/data/why/2026-10-19-morning.json), turned into its verdict record
  by verdict.record_from (no model call) in the throwaway copy only; the branch's site/data is untouched.

## Names

`<page>-<width>-<theme>.png` is the full page. For the home, `-first-screen` is the viewport alone: 1280x800, 1440x800 and 1920x1000,
the screen a reader sees before scrolling; `-full` is the whole page at 1440. 375 is the phone, unchanged from Sprint 9.5.

## J-11 (the strategist's ruling of October 20, 3:35 PM ET): the two rules under 1280

9.5b carries exactly two rules below 1280, and these shots show them:
- Rule 1, the live stamp keeps three lines below 521 px: the home at 375 is two lines (36 px) taller, because the stamp under the Bitcoin line now
  holds three lines before the live price lands, so landing it moves nothing. Re-captured: home-card-375-{light,dark}.png and
  home-nocard-375-{light,dark}.png. No other 375 shot changes (no other page carries the stamp, and the nav is not drawn at 375).
- Rule 2, the nav wraps from 700 to 1019 px instead of scrolling the page sideways: the eleven items and their names are unchanged and wrap onto
  a second row. New: home-card-768-{light,dark}.png, home-card-900-{light,dark}.png (the home, the card fixture) and method-768-{light,dark}.png,
  method-900-{light,dark}.png (an inner page).
Same fixtures and builds as above (the builder's tree at the J-11 head, SITE_BUILD_NOW=2026-10-20T07:20:00Z, every other host aborted, the page
clock the sandbox's own: the home fixtures read "4 days ago").
