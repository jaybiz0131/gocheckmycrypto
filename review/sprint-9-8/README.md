# Sprint 9.8, the verdict record: the screenshots

Made Sunday, October 25, 2026, 5:37 PM EDT (the shell's date), on claude/awesome-mendel-m0sase, from a local build of the branch's working tree (`python3 site_build.py`), served from disk and drawn by headless Chromium (`scripts/sprint98_shots.mjs`). Every request to another host was refused.

## U-10 caveat

These are local builds, not the shipped site. No preview URL exists for this branch, so nothing here is a measurement of production.

## The records (real; nothing synthetic)

- The page reads the branch's committed site/data: the verdict records in site/data/verdict (October 19 evening, October 20 morning and evening) and site/data/movers (October 20 morning and evening). None of them holds a graded verdict (Bitcoin was flat or had no verdict; Ether moved with Bitcoin; no mover passed the gate), and site/data/verdict-record.json holds no later source. So the page prints zero in every count and says "No graded verdict is stored yet, so there is nothing to score." That is the record as stored, not a placeholder.
- The record's first day, Monday, October 19, 2026, is the first stored verdict record's date.

## Review 1 round

Recaptured Sunday, October 25, 2026, 6:58 PM EDT (the shell's date) after the review 1 fixes, at 375, 390 and 1440, light and dark, from a fresh local build of the branch's working tree. The grade table's headers now read "Confirmed later" and "Reversed later" (one name per count), and a narrow-width rule keeps all five columns inside the box at 375 and 390; the script checks the table's own box as well as the page.

## The files

- verdict-record-<width>-<scheme>.png: /verdict-record.html, the whole page, at 375, 390 and 1440, light and dark. In the 375 and 390 captures the fixed tab bar (Why it moved, Markets, Big movers, Whale Watch, Brief) is drawn once part way down the image: a full-page capture paints a fixed element where the first screen ends. On a phone it sits at the bottom of the screen.
- method-link-<width>-<scheme>.png: How we check, scrolled to its line linking the record.
- today-link-<width>-<scheme>.png: /today/, scrolled to its new line linking the record (review 1).
- No /why/ verdict page is captured: no graded verdict is stored, so the build writes none, and its new standing line ("Not yet revisited", or "Confirmed later by" or "Reversed later by" a named source, with a link to the record) is shown only by the test cases, on fixtures. Screenshots for approval come from real recorded data only.
- Document width equals the viewport in every capture (no sideways scroll), and the grade table fits its box, as the script printed.
