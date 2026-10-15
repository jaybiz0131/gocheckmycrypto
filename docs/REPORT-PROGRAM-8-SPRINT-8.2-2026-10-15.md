# Program 8, Sprint 8.2: the coin doors, plus the numbers handed over labeled (report)

Status: **BUILT, NOT MERGED. Waiting for Jack's yes.** Branch `sprint-8-2` on origin. Nothing was merged or pushed to main.

## Start
- `docs/RULES.md` body hash (from line 11): `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`. It matches.
- origin/main at the start: `f64f5bf` (contains Sprint 8.1's merge `3675e45`).
- Shell date, ET, at the start: Thursday October 15, 2026, 9:17 AM.

## Item 0: the three failures, diagnosed from the logs
1. **Oct 14, 7:46 PM re-run, "+2.83% on the week" for -2.83% (and Ether +7.44%).** The ops-ledger twins log has both drops. The cause is not a wrong sign the model computed: it wrote one direction word in front of two figures ("fell 3.36 percent on the day and 7.44 percent over the week"). The twins gate reads a figure with no sign word as positive, so a true sentence was dropped as "+7.44% against -7.44%". The model-written sentences were not kept, so the test fixtures are reconstructed from the 70 characters the ledger kept plus the plain ending (stated in the test).
2. **Oct 15, 8:18 AM morning read, "missing or oversized headline".** Read from run 38733331764's log. That message was the LAST error, not the cause. Rung 1 failed because every sentence was cut by the copy law: one sentence copied the wire line "...with up to 2% spread" (a percent), the other wrote the funding reading as "0.0047 percent". Rung 2 then came back with a headline that was missing or over 100 characters; the code raised one message for both and the ledger said nothing more. The log also did not name the rule that cut a sentence.
3. **Oct 14, 7:17 PM Edition, the ETF window.** Floored in 8.1; not touched.

## Item 0: what was built (no new model calls)
- `phrases.py`: every number a model is handed is a finished phrase with sign, unit and window ("Bitcoin down 2.83% over seven days", "spot Bitcoin ETFs saw net outflows of $261.4M on the day, October 14"). The Edition's user message carries a `labeled_numbers` block and a copy of the digest with the signed window changes and ETF nets removed (`wrap.py`); the trace checker and belts keep the raw digest. The morning read is handed percent-free `board_phrases` and wire lines with the percent clause cut (or the line left out when the figure is mid-line).
- Twins gate: a week or month figure that is the series' own size but carries NO sign word gets the series' word, logged as a repair. A sign word that is there and wrong ("falling 2.3%" against +2.30, TN5) is still a wrong claim and is dropped; so is a figure of the wrong size. Nothing turns a wrong claim into a right one.
- Morning headline: the error now says "too long (N characters; the limit is 100)" or "is missing", the repair rung is told exactly that, and on the last rung a long headline is trimmed at a clause or word boundary and a missing one is the wire's top line (`headline_by` is recorded in the read). A read with fewer than two surviving sentences still falls back, with its reason. The copy-law log line now names the rule that cut a sentence.
- Gate false positive found by the coin page: "sending Bitcoin below $82,000" was read as a price claim and dropped (BTC $80,896), which cost Bitcoin's page its only wire item. "below, above, under, beneath, over, past" now mark a level, not a price (twins gate test 43 of 43; a case in sprint82_test).

## Items 1 to 5
1. Title "<Coin> price today and why it moved - GoCheckMyCrypto" on every coin page; description from the day's own price and signed 24-hour change plus the Board's stamp, under 155 characters (Bitcoin: 120).
2. "Why <coin> moved today" for the top 20: wire items that name the coin ("Ether" counts for Ethereum), reported within 24 hours of the Board read the page carries, each with its sources, time and primary mark, under "The desk does not say any of them moved its price". Nothing when no item names it. A desk line with a cause word none of its cited sources carries is left out; every line and the move line go through the twins gate; items shown there are not repeated under "Stories about". The same cause and gate rules now apply to the stories list.
3. BreadcrumbList (Home, Markets, the coin) on every coin page; parsed in the test and on all 100 built pages.
4. Sitemap lastmod is the page's real change time (`lastmod.py`): an article's publish time, a coin page's Board read or newest wire item shown, the board pages' read. Pages with no known change time carry none. On the local build 142 entries carry one, 110 of them the Board's 12:16:51Z stamp, not the build time.
5. IndexNow: key file `a44f710d9349e5f84a1c0bbae18b03c5.txt` served from the site root; the build compares its sitemaps with the live ones and keeps the changed URLs; a Netlify plugin (`plugins/indexnow`, onSuccess, production only) sends them to api.indexnow.org and logs the response. It never fails a build. **Not exercised live**: no Netlify here. The first production build after the merge will log it; the first one only writes the key (and sends changes only if the live sitemaps can be read).

## Tests: red on main, green on the branch
`scripts/sprint82_test.py` (runs in the canary). On origin/main `f64f5bf`: 31 FAIL (`docs/sprint82-red-on-main.log`), including the exact live message "fell back (morning: missing or oversized headline)". On the branch: PASS. `twins_gate_test` 43 of 43, `morning_test`, `etf_floor_test`, `color_truth_test` pass.

## Weights (375, bytes moved, local build, same data)
| page | main | branch | change |
|---|---|---|---|
| /coins/btc (title, description, breadcrumb, Why block) | 217,875 | 218,780 | +905 |
| /coins/ada (top 20, no wire item) | 215,065 | 215,509 | +444 |
| /coins/sui (outside the top 20) | 213,424 | 213,864 | +440 |
All under the 5 KB limit.

## Screenshots
`shots/program8-8.2/`, 375 and 1440, light and dark: `coins_btc-*` (title, description, the Why block), `coins_ada-*` (top 20, no block), `coins_sui-*` (outside the top 20).

## Open
- Jack's yes: not given. Merge not done. A merge must be outside 6:30 to 8:15 PM ET, one real merge commit, push the tip first, `git branch --contains`, production read by stamp, the count five minutes after.
- Live proof after the merge: the next morning read and Edition publish with no sign or window drop, or the drop is logged and right.
- Canary: see the line at the end of this report.
