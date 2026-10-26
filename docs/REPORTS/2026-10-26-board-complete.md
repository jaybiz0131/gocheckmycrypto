# Program 9 board: complete (report)

Written October 26, 2026, 1:12 AM ET by the pod shift. Documents only; nothing built, nothing merged, no production build spent.

## Start
- Pod inbox: Crypto read (README first); its three entries, 2026-10-20-C2, 2026-10-21-C3 and 2026-10-25-C4, are already in docs/RULINGS.md by id. Nothing applied.
- `docs/RULES.md` body hash `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d` (the HANDOFF.md method), matches docs/BOARD.md.
- main at the start: `7079f35`. No item at building.

## Why the board is complete
- The board's last item, 9.8, is merged (`a874558`, October 26 12:00 AM ET; report docs/REPORTS/2026-10-26-9.8.md). The only item not merged is 8.4, marked jack.

## Item states
- Merged: 9.2 (`66ba069`), 9.3 (`d977c04`), 9.4 (`308669b`), 9.5 (`ca7ff70`), 9.5b (`c1a9c88`), 9.6 (`a5bff98`), 9.6h (`39449aa`), 9.6w (`64271a6`), 9.7 (`f8e40ec`), 9.8 (`a874558`).
- Jack: 8.4 (documents only, first meaningful read November 9).

## For Jack and the strategist
- The strategist writes docs/REVIEW.md and the next board; docs/REVIEW.md does not exist yet. Sprint 9.9 (corrections from review, named in the October 20 rulings and in entry 2026-10-21-C3) is not on this board.
- Entry 2026-10-20-C2 says the allowance goes back to five when the board is complete. The board header still states eight; this shift did not change the board.
- Open from the 9.8 report: the sprint95b throttled CLS red at 1440 exists on main before 9.8; no later-source path past the ET day; the BLS and ForexFactory ids of one release not folded into one identity.

## Gate
- `python3 verify_pipeline.py canary` with python3 resolving to 3.12 (the workflows' version; this sandbox's default 3.11 cannot parse site_build.py, and the coin pages canary shells out to python3), on the tree with this report: `LAYER 1 CANARY: PASS`, exit 0. Run with the 3.11 default first, it printed `LAYER 1 CANARY: FAIL (3 problem(s))`, all three in the coin pages canary from scripts/top100_fixture_rows.py failing under 3.11.
