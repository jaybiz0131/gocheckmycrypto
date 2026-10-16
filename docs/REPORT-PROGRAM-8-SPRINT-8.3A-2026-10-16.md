# Program 8, Sprint 8.3 Part A: the fix list (report)

Status: **BUILT, NOT MERGED. Waiting for Jack's yes.** Branch `sprint-8-3a` on origin. Part B (the share loop) is held for the deep audit and was not started. "Part A" is read as the five fix items on the 8.3 list in `docs/HANDOFF.md` section 14 (items 1 to 5); if Part A meant something else, say so before the merge.

## Start
- Base: origin/main `6089eed`. Shell date, ET, at the start: Friday October 16, 2026, about 5:13 PM. Nothing was pushed to main.

## What was fixed (tests red on 6089eed first: `docs/sprint83a-red-on-main.log`, 14 FAIL; green on the branch)
1. **Coin chart to the current reading.** `snapshot.week_pair` is the one 7D pair (the chart's caption and its high/low labels). It was made of the seven COMPLETED daily closes only, so a price that had broken the range read outside it ("7D low $81,630" beside $80,896). It now includes the coin's current reading, and the build-time line (`coinpage.run_to_reading`) ends on that reading too. Today's BTC price ($82,216) sits inside its closes, so today's page prints the closes' own pair ($81,703.12 to $83,457.39); the break case is the test. The Oct 13 stop in the earlier screenshot was the local proof's recorded CoinGecko fixture, not the live fetch.
2. **Chart Master lifts whole sentences only.** `coinpage.whole_sentence`: begins with a capital or digit, ends in terminal punctuation, and does not open on a word that points back ("However", "But", "Meanwhile", "Also", "This", "It", "More ...", "Separately" and the like). A read whose only Bitcoin sentence is dependent lifts nothing and the levels card follows.
3. **Sources once per outlet.** "2 sources: Decrypt, Decrypt, Bitcoin Magazine" is now "2 sources: Decrypt, Bitcoin Magazine". The count is never fewer than the outlets listed.
4. **Twins gate.** A bare "stablecoin" followed by a flow word (movement, flow, transfer, withdrawal, deposit, buying power, inflow, outflow) names a movement, not the 30-day float; the 15 October 7:49 PM sentence (USDT off Bitfinex, "treats as an outflow") now stands, a real claim about the float against its sign is still dropped. The dropped sentence is logged whole (run log 400 characters, ops ledger 400; it was 140 and 70).
5. **The withheld Edition and the evening record.** `consistency_gate.edition_withheld_line`: when the gate withholds an Edition it prints one warning ("Edition withheld ...: the slot is still open, and the next dispatch for it will run") and appends it to the run summary. `today.storable`: after 5 PM ET a fallback record (the morning's, no read behind it) is not stored, so an evening run that finds no Edition freezes no morning record.
6. **Found by the canary, fixed with a test** (not on the list): the Top 100 row line for ALGO (+0.013% over seven days) was tagged "up" but drawn flat at one decimal, failing the hard-gate canary on today's data. A line whose first and last points draw at the same height is now tagged flat. This was latent in main; it needed only a coin with a tiny weekly change.

## Proof
- Canary on the final branch tree: see the last line of this report.
- Screenshots `shots/program8-8.3a/` (Bitcoin coin page, 375 and 1440). Today's data does not break the 7D range, so the false-label case is proved by test, not by a picture.
- Not exercised live: items 4 and 5 only fire in a live Edition (the first proof is the next Edition that withholds, or that writes a USDT-off-exchange sentence).

## Merge
Not done. After Jack's yes: outside 6:30 to 8:15 PM ET, one real merge commit, tip pushed first, `git branch --contains`, one build, production read by stamp, the count five minutes after. No Netlify access in this session, as before.

- Canary on the final branch tree (b7a7cbf plus the report): LAYER 1 CANARY: PASS. Shell date: Fri Oct 16 17:25:47 EDT 2026.
