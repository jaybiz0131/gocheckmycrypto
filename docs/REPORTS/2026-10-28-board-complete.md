# Program 9 board: complete again after hotfix 9.9h2 went to jack (report)

Written October 28, 2026, 5:20 AM ET by the pod shift fired at 5:09 AM ET (routine "Crypto Pod Shift 1"), session branch claude/vigilant-pasteur-e1ixfj. Documents only; nothing built, nothing merged, no production build spent, no subagent dispatched.

## Start
- Pod inbox: Crypto read (README first); its eight entries, 2026-10-20-C2, 2026-10-21-C3, 2026-10-25-C4, 2026-10-26-C5, 2026-10-26-C6, 2026-10-27-C7, 2026-10-27-C8 and 2026-10-27-C9, are already in docs/RULINGS.md on main by id. Nothing applied. No entry answers J-21.
- `docs/RULES.md` body hash `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d` (everything below the header's `---` line), matches docs/BOARD.md.
- main at the start: `f55490e`. No item at building.

## Why the board is complete
- Every item not merged is marked jack or blocked by an item marked jack: 9.9h2 is jack (October 27, 11:51 PM ET, three reviewer FAILs at 14120fd, 5039e0a and 339c9a9, J-21); 9.9.2 is at review with its round 4 held behind 9.9h2 by its board line ("waiting behind hotfix 9.9h2", resuming after it merges), a hold that counts as a dependency; 9.9.3 depends on 9.9.2 merged, 9.9.4 on 9.9.3 merged; 8.4 is jack (documents only, first meaningful read November 9).

## Item states
- Merged: 9.2 (`66ba069`), 9.3 (`d977c04`), 9.4 (`308669b`), 9.5 (`ca7ff70`), 9.5b (`c1a9c88`), 9.6 (`a5bff98`), 9.6h (`39449aa`), 9.6w (`64271a6`), 9.7 (`f8e40ec`), 9.8 (`a874558`), 9.9h (`c0cb8c0`), 9.9.1 (`f9de9c2`).
- Jack: 8.4; 9.9h2 (build on claude/vigilant-pasteur-adseyy, head `339c9a9`).
- Blocked by jack: 9.9.2 (status review, build of record claude/awesome-mendel-7mb5ar at `421f08e`, round 4 not started), 9.9.3, 9.9.4 (status todo).

## For Jack and the strategist
- J-21 waits on a ruling: (1) one more narrow round on 339c9a9 with the reviewer's three-word run and the five probes as plants red first, then review 4 (the shift's recommendation in J-21); (2) merge 339c9a9 as is on the reviewer's gate evidence; (3) keep the check and accept missed slots until the Luxor line leaves the stored data. Any of them reaches the pod through an inbox entry.
- Consequence while it waits: main's gate is red on J-20's feed check (below), so the October 28 8:15 AM ET morning read fails its hard gate and misses its slot, and every later run does the same until a fix merges or the Luxor line leaves site/data/why/2026-10-27-evening.json and the wire.
- The allowance stays at eight per Eastern date until 9.9 is complete, as the board header states.

## Gate
- `python3 verify_pipeline.py canary` with python3 resolving to 3.12 (the workflows' version), on the tree with this report: `LAYER 1 CANARY: FAIL (1 problem(s))`, exit 1. The one problem is J-20's: sprint 9.7, "no feed has a dash; none but the coin identity feeds (a coin's name may be 'Artificial ...') has an AI word", the same red recorded by the October 27 11:51 PM ET shift on f55490e. This push changes one file under docs/REPORTS/ and no code, data or feed, so it neither causes nor clears that red.
- Under python3 3.11 the run also fails three Top 100 row checks, because scripts/top100_fixture_rows.py is run as `python3` and site_build.py uses 3.12 f-string syntax; that is the sandbox's interpreter, not the tree.
