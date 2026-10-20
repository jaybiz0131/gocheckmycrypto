# Sprint 9.5b, the desktop board: the designer's screenshots

Made October 20, 2026 on local branch local-sprint-9-5b (the builder's b3e2294 plus the designer's pass), in a worktree. Nothing pushed.

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
