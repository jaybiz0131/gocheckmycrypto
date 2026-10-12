# Program 7, Sprint 7.1: the new look, everywhere. Report, Monday 12 October 2026

## Start
- RULES body sha256 `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`: **matched** (`tail -n +11 docs/RULES.md | sha256sum`).
- `origin/main` at start `320a1e69a3e454a8a163983e69ef1b60c166a977` (contains `f7cd67a` and `0ae8b0f`). Shell: Mon Oct 12 12:48 PM EDT.
- `Main.dc.html` was not attached; the design was built from the opener's section 3 words.
- **Count of record at start (12:48 PM):** 3 ready, 1 canceled for crypto production, not 1 as the opener said. The third build is the automated coin-screen commit `320a1e6` (16:36Z). Builds left: 2.

## Builds used
- Before: 3 ready, 1 canceled. After the merge (read 3:22:53 PM EDT, push + 5 min 33 s, Worker `/counts/today`): **4 ready, 1 canceled**, last production `4194c5b` ready at 19:22:17Z. The 7:08 PM Edition is the day's fifth. The close below is documents only and must not build.

## Merge and production
- **Merge `4194c5b3b67133ea8ed936e08aff5b2ae5f5df14`**, a real merge of `glow-look` (`01a68f6`) into `origin/main` `320a1e6`. Canary on the merged tree from a fresh build: `LAYER 1 CANARY: PASS`, exit 0. Pushed **3:17:20 PM EDT**; local and `origin/main` both `4194c5b`, `rev-list --count` 0.
- **Production stamp:** `/stamp.txt` `commit 4194c5b...` `built 2026-10-12T19:20:13+00:00`, read 3:22:35 PM EDT.
- **Production reads, 375 and 1440, light and dark,** 8 pages (/, /pulse, /flows, /chartmaster, /news, /bottom-line, /record, /learn), 32 reads, all OK (`shots/program7-7.1/production/prod-read.json` and viewport shots): every page carries `build-commit` `4194c5b`; **the masthead reads `MON · OCT 12, 2026` on every read, equal to the shell's ET date**; no sideways scroll (scrollWidth = clientWidth); IBM Plex Sans loaded, Inter absent. Home: the masthead stamp lit `LIVE 3:23 PM ET` on 3 of 4 home reads after the live read answered; on the fourth (375 light) it stayed `UPDATED 3:20 PM ET` (the live read did not answer in that load; the page did not claim live). The week's line read `h-line down` with the 24-hour badge `down` at that moment.
- `scripts/color_truth.py` over production's `/` and `/pulse` HTML: 0 contradictions.

## Jack's yes
- **3:00 PM ET, Monday 12 October 2026**, on the contact sheets, with one fix: each chart colored by its own window. Fixed at `01a68f6`, Bitcoin card close-ups re-shot and sent before the merge. Other calls accepted (Brief card in the band's place, mood as the gauge, UPDATED/LIVE stamp, 7:08 PM).

## The token table as built (`site/assets/system.css`)
| Token | Light | Dark |
|---|---|---|
| ground | #FFFFFF | #0B1422 |
| card | #FFFFFF | #13203A |
| ink | #0F1B2D | #E8EEF7 |
| muted | #4A5568 | #A9B6CC |
| faint | #6B7280 | #8E9BB3 |
| line | #E6EAF0 | #24314D |
| up text / tint / line | #0B6E3B / #EAF7EF / #12A05A | #4ADE80 / #123227 / #4ADE80 |
| down text / tint / line | #A51F15 / #FDECEA / #E0301F | #FF6B5E / #3A1820 / #FF6B5E |
| eyebrow red | #C8261B | #FF7A6E |
| brand coral | #FF6B5E | #FF6B5E |
| live green | #7CFFB0 | #7CFFB0 |
| amber, mood card, mood word | #F5A800, #FFF6E5, #8A5A00 | #F5A800, #2A2312, #F5C75A |
| masthead band | #0F1B2D | #060D19 |
| Brief card, its eyebrow | #0F1B2D, #FF8A7F | #162A4D, #FF8A7F |

Type: Newsreader 700, IBM Plex Mono 700, IBM Plex Sans 400 to 600, self-hosted (Inter deleted). Fonts subset to the same 113 characters as before: `plexsans.woff2` 14,148 bytes (Inter was 14,216), `newsreader-roman.woff2` 24,564 (was 22,596; now runs to 700), `newsreader-italic-700.woff2` 2,180 (the masthead's "Crypto" only).

### Contrast pairs checked (WCAG relative luminance; need 4.5:1, or 3:1 at large text). 0 fail.
```
light ink                  #0F1B2D on ground          #FFFFFF  17.28:1  need 4.5  ok
light muted                #4A5568 on ground          #FFFFFF   7.53:1  need 4.5  ok
light faint                #6B7280 on ground          #FFFFFF   4.83:1  need 4.5  ok
light up text              #0B6E3B on ground          #FFFFFF   6.35:1  need 4.5  ok
light up text              #0B6E3B on up tint         #EAF7EF   5.76:1  need 4.5  ok
light down text            #A51F15 on ground          #FFFFFF   7.48:1  need 4.5  ok
light down text            #A51F15 on down tint       #FDECEA   6.54:1  need 4.5  ok
light ink                  #0F1B2D on up tint         #EAF7EF  15.68:1  need 4.5  ok
light ink                  #0F1B2D on down tint       #FDECEA  15.11:1  need 4.5  ok
light muted                #4A5568 on up tint         #EAF7EF   6.83:1  need 4.5  ok
light muted                #4A5568 on down tint       #FDECEA   6.58:1  need 4.5  ok
light eyebrow red          #C8261B on ground          #FFFFFF   5.60:1  need 4.5  ok
light link                 #123A5E on ground          #FFFFFF  11.72:1  need 4.5  ok
light mood word            #8A5A00 on mood card       #FFF6E5   5.52:1  need 4.5  ok
light ink                  #0F1B2D on mood card       #FFF6E5  16.10:1  need 4.5  ok
light white                #FFFFFF on masthead navy   #0F1B2D  17.28:1  need 4.5  ok
light brand coral          #FF6B5E on masthead navy   #0F1B2D   6.19:1  need 3.0  ok
light live green           #7CFFB0 on masthead navy   #0F1B2D  13.82:1  need 4.5  ok
light band muted           #B8C2D3 on masthead navy   #0F1B2D   9.63:1  need 4.5  ok
light white badge          #FFFFFF on up badge        #0B6E3B   6.35:1  need 4.5  ok
light white badge          #FFFFFF on down badge      #A51F15   7.48:1  need 4.5  ok
light Brief eyebrow coral  #FF8A7F on Brief navy      #0F1B2D   7.57:1  need 4.5  ok
dark  ink                  #E8EEF7 on ground          #0B1422  15.83:1  need 4.5  ok
dark  ink                  #E8EEF7 on card            #13203A  13.90:1  need 4.5  ok
dark  muted                #A9B6CC on ground          #0B1422   9.01:1  need 4.5  ok
dark  muted                #A9B6CC on card            #13203A   7.91:1  need 4.5  ok
dark  faint                #8E9BB3 on card            #13203A   5.78:1  need 4.5  ok
dark  faint                #8E9BB3 on ground          #0B1422   6.58:1  need 4.5  ok
dark  up text              #4ADE80 on card            #13203A   9.30:1  need 4.5  ok
dark  down text            #FF6B5E on card            #13203A   5.80:1  need 4.5  ok
dark  up text              #4ADE80 on ground          #0B1422  10.60:1  need 4.5  ok
dark  down text            #FF6B5E on ground          #0B1422   6.61:1  need 4.5  ok
dark  up text              #4ADE80 on up tint         #123227   7.97:1  need 4.5  ok
dark  down text            #FF6B5E on down tint       #3A1820   5.65:1  need 4.5  ok
dark  ink                  #E8EEF7 on up tint         #123227  11.91:1  need 4.5  ok
dark  ink                  #E8EEF7 on down tint       #3A1820  13.52:1  need 4.5  ok
dark  muted                #A9B6CC on up tint         #123227   6.78:1  need 4.5  ok
dark  muted                #A9B6CC on down tint       #3A1820   7.70:1  need 4.5  ok
dark  eyebrow red          #FF7A6E on ground          #0B1422   7.26:1  need 4.5  ok
dark  eyebrow red          #FF7A6E on card            #13203A   6.38:1  need 4.5  ok
dark  link                 #93BCE3 on card            #13203A   8.14:1  need 4.5  ok
dark  mood word            #F5C75A on mood card       #2A2312   9.79:1  need 4.5  ok
dark  ink                  #E8EEF7 on mood card       #2A2312  13.36:1  need 4.5  ok
dark  white                #FFFFFF on masthead band   #060D19  19.46:1  need 4.5  ok
dark  brand coral          #FF6B5E on masthead band   #060D19   6.96:1  need 3.0  ok
dark  live green           #7CFFB0 on masthead band   #060D19  15.55:1  need 4.5  ok
dark  band muted           #A9B6CC on masthead band   #060D19   9.50:1  need 4.5  ok
dark  ground badge         #0B1422 on up badge        #4ADE80  10.60:1  need 4.5  ok
dark  ground badge         #0B1422 on down badge      #FF6B5E   6.61:1  need 4.5  ok
dark  white                #FFFFFF on Brief card      #162A4D  14.26:1  need 4.5  ok
dark  Brief eyebrow coral  #FF8A7F on Brief card      #162A4D   6.24:1  need 4.5  ok
dark  band muted           #B8C2D3 on Brief card      #162A4D   7.94:1  need 4.5  ok
```
The one pair under 4.5:1, white on the light up badge #12A05A (3.39:1), is set at 19 px bold, large text under WCAG, so it needs and clears 3:1. Glows are box-shadow, text-shadow and SVG blur behind data; none sits under body text.

## The color-truth test, red then green
`scripts/color_truth_test.py` (renders the Markets tiles, the home tape and the band from a fixture; `scripts/color_truth.py` names each contradiction).
- **Red on 0ae8b0f's code** (this branch before any change, exit 1):
```
CONTRADICTION: tile 'Bitcoin': figure colored up beside 'Down 0.67%'
CONTRADICTION: tile 'Whole market': figure colored down beside 'Up 0.40%'
CONTRADICTION: the home band's sentence quotes a change ('up 0.79 percent')
color truth: FAIL, 3 contradiction(s)
```
- **Green after the fix:** `color truth: PASS, every color agrees with the number beside it`, exit 0.
- **Jack's 3:00 PM case** (24-hour up, the week down) added: red before the fix (`a chart line colored up runs down over its own window`, exit 1), green after, exit 0.
- **U-9 breaks of the canary check `_color_truth_canary`**, each red then green on restore from a saved copy: (1) the Bitcoin tile without its `since_change`; (2) `narrative.edition_line` without its `quotes_change` refusal (the writer kept "Bitcoin drifted up 0.79 percent on the day"); (3) the home band's render belt off; (4) the week chart's direction planted back to the 24-hour sign.

## Contact sheets (`shots/program7-7.1/`)
`sheet-home`, `-pulse`, `-coins-btc`, `-flows`, `-chartmaster`, `-news`, `-articles-evening-brief-2026-10-11` (story page), `-bottom-line`, `-record`, `-learn`, `-about`: 375 and 1440, light and dark, before beside after, local builds of the same data. Close-ups at 375, 2x: `closeup-bitcoin-card-375-{light,dark}` (re-shot after the 3:00 PM fix), `closeup-gauge-375-*`, `closeup-masthead-375-*`, `closeup-200day-375-*`.

## Weights (375, local copies served alike, every response body until quiet)
| Page | Before (bytes) | After (bytes) | Change |
|---|---:|---:|---:|
| / | 223,097 | 225,873 | +1.2% |
| /pulse | 211,830 | 212,288 | +0.2% |
| /coins/btc | 219,089 | 216,637 | -1.1% |
| /flows | 215,268 | 215,611 | +0.2% |
| /chartmaster | 221,956 | 222,880 | +0.4% |
| /news | 251,131 | 251,474 | +0.1% |
| /articles/evening-brief-2026-10-11 | 214,264 | 214,667 | +0.2% |
| /bottom-line | 354,511 | 354,854 | +0.1% |
| /record | 225,497 | 225,840 | +0.2% |
| /learn | 214,974 | 215,317 | +0.2% |
| /about | 202,179 | 202,542 | +0.2% |

No page grows more than 10 percent (largest +1.2 percent, the home page). **Home: 225,873 bytes, under 300 KB. LCP** (home_budget.mjs, Lighthouse mobile throttling, median of 3, local): 1,380 ms before, 1,444 ms after.

## Open
- The coin page's chart product is Sprint 6.4's; here only its line, dots and colors changed.
- Sprint 7.2 gets its own session.

Shell date at close: Mon Oct 12 2026, 3:25 PM EDT
