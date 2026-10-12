# Program 6, Sprint 6.3: navigation and names. Report, Sunday 11 October 2026

**Status: built and proved locally. NOT merged, NOTHING pushed.** The session ran 6:12 to about 7:15 PM
ET, inside the 6:30 to 8:15 PM no-push window, and the merge needs Jack's yes on the contact sheets.
Production is untouched, so there are no production reads and no count change from this sprint.

## Start
- RULES body sha256 `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`: **matched**
  (`tail -n +11 docs/RULES.md | sha256sum`).
- `origin/main` at start `9fe3f7ed000e303885f59b1d2b54685c538d4d84`, contains `3c0665e`.
- `Nav.dc.html` is not in this repository; the picture was taken from Program 5 section 6's words.
- Jack's two rulings are recorded in `docs/HANDOFF.md` section 7e.

## Branches (all local)
- `nav-names` `f358afc`: items 0 to 2 (site_build.py, home.py, explainers.py, site.css, canary names).
- `nav-names-close`: item 3, item 4, this report, the contact sheets. Documents and scripts only
  except that its `verify_pipeline.py` and `scripts/` are both on the ignore list, so it does not build.

## Item 0: the names, before and after
One table, `site_build.NAMES`, read by every surface below, plus `verify_pipeline` canary checks.

| Surface | Before | After |
|---|---|---|
| Desktop nav (all 801 pages) | Home, Whale Watch, Chart Master, News, The Edition, The Record, Learn, About | Home, **Markets** The Board, **Flows** Whale Watch, **Charts** Chart Master, **News** Checked, **Brief** The Edition, **Record** Worth keeping, **Learn** The Board explained, About (task name leads, brand small under it from 900 px up) |
| /pulse.html | title "The Board", H1 "The Board", eyebrow "The Board" | title "Markets: The Board", H1 "Markets", eyebrow "The Board" |
| /pulse/*.html, /coins/* titles | "... - The Board - ..." | "... - Markets - ..." |
| Dashboard eyebrow | "The Board . dashboard" | "Markets . The Board dashboard" |
| /flows.html (both renders) | title "Whale Watch", H1 "Where the whales are moving" | title "Flows: Whale Watch", H1 "Flows", eyebrow "Whale Watch"; old H1 is the lede's first sentence |
| /chartmaster.html | title and H1 "The Chart Master", no eyebrow | title "Charts: Chart Master", H1 "Charts", eyebrow "Chart Master" |
| "The Chart Master's read" (card, aria, Learn card, page descriptions, Chart Master archive title) | The Chart Master's read | Chart Master's read |
| /news.html | title "Crypto news by storyline", H1 "News", no eyebrow | title "News: Checked", H1 "News", eyebrow "Checked" |
| News lanes and months | "News desk" in breadcrumb, crumb JSON-LD, active label | "News" (26 pages) |
| Article JSON-LD breadcrumb | "Latest" | "News" |
| /bottom-line.html | title "The Bottom Line", eyebrow "The Bottom Line", H1 "The daily reads", meta "daily reads" | title "Brief: The Edition", eyebrow "The Edition", H1 "Brief", lede and meta reworded |
| /record.html | title "The Record", H1 "The Record", eyebrow "The Record", dek and h2 said the same sentence twice | title "Record: Worth keeping", eyebrow "Worth keeping", H1 "Record", one dek; the section head now belongs to the home page only (double heading fixed) |
| Record links | "The full Record", "Open the Record", "The Record, full index", "The Record" crumb (3 tables) | "Record, in full", "Open Record", "Record, full index", "Record" |
| /learn.html | title "Learn the Board: every crypto number explained", H1 "Learn the Board" | title "Learn: The Board explained", H1 "Learn", eyebrow "The Board explained" |
| Learn explainer pages (8) | eyebrow "Learn the Board" | "The Board explained" |
| Learn page section and links | "The Chart Master", "Open the Chart Master", "Open the Board" | "Chart Master", "Open Charts", "Open Markets" |
| Footer | The Record, Archive, ... | **Record, Learn, About**, Archive, ... (these are also the phone's route to Record and Learn) |
| Home block headings | The Board, The Brief, The Record, "The Board in full", "The full Record", "Whale Watch" link | Markets, Brief, Record, "Markets, in full", "Record, in full", "Flows" |
| Coin page related links | The Board, How to read the Board | Markets, Learn |
| How we make money (policy copy) | "Latest", "Market Pulse and The Chart Master" | "News", "The Board and Chart Master" |
| Phone tab bar | Board, Whales, News, Edition, Learn | Markets, Flows, Charts, News, Brief |

URLs: none changed. Verified: all 801 built pages carry the same nav, the same footer lead links and
the same five tabs; the active mark follows the URL group on every page.

**Left alone, on purpose, for Jack:** (a) "The Bottom Line" still labels the card that carries an
edition's read (the news page card, article pages, 546 pages). It is a content element, not the
Brief page's chrome. (b) Prose uses the brand names ("the Board", "Whale Watch"), and the home band's
"How to read the Board" link is a law from Sprint 6.1. (c) Home and About stay in the desktop row,
with no brand line. (d) The K-1 canary's rule "The Board is not in the nav" is retired, replaced by the
rule that Markets is.

## Item 1: the phone tab bar, proofs (375 x 800 viewport, light and dark, all 20 pages of 11 groups)
- Below 700 px (699.98): top row hidden, bar shown. At 700 and 701 the row is back and the bar gone.
  Row has no sideways scroll at 700, 701, 768, 899, 900, 1024, 1100, 1280.
- **Targets:** five tabs, each 56 px tall, 75 px wide at 375. Footer links 44 px tall below 700.
- **Safe area:** `viewport-fit=cover` added to the viewport meta; the bar's bottom padding is
  `env(safe-area-inset-bottom)` and the body reserves `60px + env(safe-area-inset-bottom)`. Headless
  Chromium has no inset, so the inset value itself is not exercised; the CSS is.
- **Last content never hidden:** at scroll end the footer's bottom is 740 px against the bar's top
  at 743 px on every page measured (first cut was 1 px short, caught by the measurement, fixed).
- **Current tab:** a 3 px bar across its top edge, weight 800, a thicker icon stroke, and
  `aria-current="page"`. Not colour alone. Nothing depends on hover.
- **No sideways scroll at 375:** `documentElement.scrollWidth` and `body.scrollWidth` equal 375 on every
  page group, both modes (also 1440): home, markets (Board, Top 100, sentiment, coin), flows, charts,
  news (hub, lane, article), brief (history, edition), record, learn (hub, explainer), tables,
  coverage, about, method, 404. Measured before the change too: no regressions.
- Record and Learn: **footer only**. Search does not exist yet, so nothing is behind search.
- Not built: header search (waits for Sprint 4).
- Side effect seen, not mine: /bottom-line.html is about 98,000 px tall at 375 (every edition listed).

## Item 2: "Since yesterday"
**Not renamed.** The block has two lines, not three: Bitcoin against its 200-day average, and Bitcoin's
share of the whole market. "Against the trend" is true of the first and not of the second, so it fails
the test. Proposals, Jack picks: **"Where Bitcoin stands"** (fits both lines; my recommendation),
"The long view", or "Against the trend" if the second line is dropped. The heading is unchanged and
the 6.2 home canary still pins it, so the rename is a one-line change plus that canary line.

## Item 3: the canary's leftovers
- Cause: `_live_layer_canary` renders the home page, and that render keeps a dated Chart Master copy
  (`site_build.load_chartmaster`) and a dated Board snapshot (`snapshot_pulse`) in the real data
  directories. The stamp canary's cleanup never saw them because they are written outside its build.
- Fix: `layer1_canary` runs with `CM_ARCHIVE` and `SNAPSHOT_DIR` on a scratch copy of the real
  directories (reads unchanged, writes elsewhere), restored in a finally. Documents and scripts only.
- Test `scripts/canary_clean_test.py`: **red** on main (`left ?? site/data/chartmaster/2026-10-08.json`,
  `left ?? site/data/snapshots/pulse-2026-10-11.json`, exit 1), **green** after (`PASS, git status is the
  same after the canary as before it`, exit 0). Canary itself: `LAYER 1 CANARY: PASS` on both branches.

## Item 4: the handoff
`docs/HANDOFF.md`: **403 lines before, 287 after** (U-1: 300). Sections 6, 7, 7b and 7c moved whole and
unedited (a one-line moved-from note above each) into HANDOFF-2026-10-06.md, -10-08.md and -10-11.md;
one pointer line left for each. Section 7e added for this sprint.

## Contact sheets (for Jack, before any merge)
`shots/program6-6.3/`, one per page group, each showing before and after, light and dark, at 375 and
1440: `sheet-home`, `-markets`, `-flows`, `-charts`, `-news`, `-brief`, `-record`, `-learn`, `-tables`,
`-coverage`, `-static` (all .jpg). `sheet-phone-tab-bar.jpg` shows the fixed bar on Markets, News and
Brief, top and end of page, both modes. They exist on this machine and on `nav-names-close`; nothing
has been pushed.

## Jack's rulings after the contact sheets (11 October) and the merge (12 October)
- Rulings applied: "Since yesterday" is now **"Where Bitcoin stands"**; the edition card is now **"The Brief"**
  (news hub and article pages; story prose that opens "The Bottom Line:" is story text and was left);
  Home and About stay as built. Re-shoots: `shots/program6-6.3/reshoot/`.
- Both branches were pushed Sunday 7:47 PM ET (`nav-names` `7d73e21`, `nav-names-close` `e167e23`), no force,
  no trailer, canary PASS on each. The push fell inside the 6:30 to 8:15 window; Jack named it explicitly.

## Merge hash, production reads, counts
- **Merge `0ae8b0f`** (real merge commit, `nav-names` into `origin/main` `357170a`), pushed **Mon 12 Oct 8:30:55 AM ET**
  (12:30:55Z). Canary PASS first (the first run was red only because my local built tree predated Sunday's Evening
  Brief, the K-1 trap in the handoff; rebuilt locally, then PASS). Nothing had built that day before it: production
  stamp was `7d8971b` (11 Oct 23:17Z) and every commit since was `[skip netlify]`.
- **Production by stamp:** `/stamp.txt` read `commit 0ae8b0ff...` `built 2026-10-12T12:34:55+00:00` (push + 4 min 0 s).
  Every page carries `build-commit` `0ae8b0f`.
- **Production reads, 375 and 1440, light and dark** (8 pages: /, /pulse, /flows, /chartmaster, /news, /bottom-line,
  /record, /learn; 32 reads, `shots/program6-6.3/production/prod-read.json` and viewport shots): H1 is the task name
  on every page (Markets, Flows, Charts, News, Brief, Record, Learn); `aria-current` names task and brand
  ("Markets The Board" and so on); at 375 the top row is hidden and the bar is shown with five tabs of 56 px; at
  1440 the row is shown and the bar hidden; `scrollWidth` equals `clientWidth` on all 32 reads (no sideways scroll).
- **Count:** I have no Netlify access from this container, so the dashboard count was **not read**. What the stamp
  shows: today's first build is `0ae8b0f`, and the close below was checked against the ignore script before pushing.
  Jack to read the dashboard: expected 1 ready for 12 October, plus 1 canceled for the close.
- **Close:** `nav-names-close` merged after, items 3 and 4, report, sheets (documents and scripts only). Pushed with
  the results below; see the handoff's section 7e for the hash.
