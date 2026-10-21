# Sprint 9.7, app-ready feeds and the search pass: the screenshots

Made Wednesday, October 21, 2026, about 4 AM ET (the shell's `date`), on claude/sleepy-sagan-xcfcw9 at the builder's working tree for Sprint 9.7. Nothing here is under review/, because review/ is not in netlify_ignore.py and a push of review/ files alone spends a build; docs/ is ignored.

## U-10 caveat

These are local builds, not the shipped site. No Netlify preview exists for this branch, so nothing here is a measurement of production.
Each image is a throwaway build of the branch's working tree (`python3 site_build.py`), served from disk and drawn by headless Chromium
(Playwright, `scripts/sprint97_shots.mjs`). Every request to another host was refused, so the coin page's chart shows its own fallback line
("The live history did not load, so this is the build's seven-day line") and nothing live is in any image.

## The clock

`SITE_BUILD_NOW=2026-10-21T05:00:00Z` for the build. The Board in the committed site/data was last read 7:12 PM ET on October 20, so the stamp line
under the Top 100's heading carries a red age ("8 hours ago" in these captures): that is the site's own stale state (a reading more than 3 hours old when it is read; asof.js measures against the clock at the moment the page is opened), and it is correct. The number depends on when a capture is taken.

## The records (real; nothing synthetic except the three saved coins)

- The Board, the Top 100 rows and the coin page are the branch's committed site/data (the Board read 7:12 PM ET, October 20).
- The three coins in the watchlist (BTC, ETH, SOL) are put in the capture browser's storage by the script, the way a reader's click on Pin would. A reader's list is theirs; these are a stand-in for one, and the rows shown are the Top 100 table's own strings.

## What each shows

- `coin-btc-<width>-<scheme>.png`: /coins/btc, first screen. The name is now an h1 (it was an h2). Its look is the h2's: the same size (23px), weight (700), line height, margin and color, so nothing moves. Compared against the same page built from Sprint 9.6's tree, the top 420 pixels at 375, 768 and 1440, light and dark, are identical byte for byte, and so are the heading's computed style and the boxes of the heading, the head row and the element after it (`h1-identity.log`).
- `watchlist-top100-<width>-<scheme>.png`: /pulse/prices with three saved coins. "Your watchlist" sits between the stamp and the search box: each saved coin's price and 24-hour change as the table below prints them, a link to its page ("Why it moved" opens the coin page, where its verdict card is), and Remove. "Saved on this device only. No account, no cookie, nothing logged." Its rows have fixed heights (78px under 600px wide, 49px from it) and the page reserves the panel's height from the saved count before anything below it is drawn, so it moves nothing.
- `watchlist-empty-top100-<width>-<scheme>.png`: the same page with nothing saved. The panel is hidden and takes no room, so a reader who never saves a coin sees the page Sprint 9.6 shipped.

Widths 375 and 1440; schemes light and dark.
