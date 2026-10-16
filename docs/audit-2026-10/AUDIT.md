# GoCheckMyCrypto: the deep audit, and the road to 9 out of 10

Strategy desk audit session, Friday 16 October 2026. Documents only: no site code, no build, nothing merged. Companion files: `NAMES.md` (the naming options) and `shots/` (every screenshot cited, 375 and 1440, light and dark).

## 0. Start, and how this was measured

- `docs/RULES.md` body sha256 (`tail -n +11 docs/RULES.md | sha256sum`): `4179b2ac06d0dc7fb9de9987dc077884df6f4e1b5ebabe1b6ff1bb2de8b3568d`. **Matches.**
- `origin/main` at the start: `6089eed` ("Documents only: report close time"). Shell date at the start: Friday October 16, 2026, 5:12 PM EDT.
- Production read: `/stamp.txt` `commit 9c8af54`, built 2026-10-16T12:19:17Z (the 8:15 AM morning read's build). Every page read carried that build. Screenshots taken 5:14 to 5:20 PM ET; Lighthouse 5:20 to 5:21 PM ET; text reads 5:12 to 5:30 PM ET. The page stamps therefore read about nine hours old; that is the cadence, and it is part of what is scored.
- Read in full: `docs/RULES.md`, `docs/HANDOFF.md`, `docs/PROGRAM-8-2026-10-14.md`, `docs/PROGRAM-6-2026-10-11.md`, the 8.1 and 8.2 reports, and the 12 to 13 October handoff day file. **There is no standalone Program 7 document in the repository**; Program 7 exists as the 7.1, 7.2 and 7.3 reports and `docs/HANDOFF-2026-10-13.md` sections 9 and 10, which were read (the 6.3, 6.4, 6.5, 7.1 and 7.2 reports in their opening sections).
- Method: production pages read with Playwright (Chromium, `colorScheme` emulation for dark; the site has no theme toggle) and curl; the 14-day rhythm from `ledger.json`, `data/morning-ledger.json`, `site/content/`, git history and the GitHub Actions run list; data sources probed from this sandbox; the model prices from the Claude API reference as cached on 6 October 2026.
- **Process note (U-2):** the four measurement subagents (screenshots, ledger tallies, source probes, competitor reads) ran on the session's model, not on Sonnet as U-2 asks for mechanical work. Recorded here rather than redone.
- **Process note (U-4):** no model call was made against the desk's key. Nothing here was dry-run.
- Live sites not reachable from this sandbox: The Block (403 on the home page), CoinGecko's website (403; its API answers), Messari (429), Farside (403; it answers from the GitHub runners), Binance (451), Bybit (403). Section 2 says where this limits the comparison.

## Summary for Jack

**The overall score today is 4.4 out of 10.** The machinery under the site is unusually honest and the pages are fast and handsome. But the site does not answer the one question it was built to answer. Every page that promises "why" ends with "The desk does not say one caused the other." Meanwhile its own numbers disagree with each other in ways a reader can see.

The finding that matters most is on the 15 October dated "why" page (`03-today-2026-10-15-375-light.jpg`):
- It froze with the title "Why is crypto up today?" on a day the same page read "down" at 9:03 AM.
- The one causal item it lists is the desk's own wire line, credited to CoinDesk at 12:25 AM ET: "Hot US producer-price data triggered nearly $940 million in crypto liquidations as Fed rate-hike bets spiked to 50%."
- The linked CoinDesk piece (published 04:25 UTC, never modified) says nothing about producer prices, $940 million or 50%. It reports $483 million in Bitcoin and Ether liquidations "as uncertainty about the Federal Reserve's next interest-rate decision weighed".

The desk's strictest rule forbids it to say why. Meanwhile its own one-line summary had invented a cause that its only source does not carry.

The path to 9 is not looser rules. It is a graded verdict on each move that earns its claim with a timing test and the market's mechanics, and shows the test. That same test would have caught this line.

---

## 1. The audit, scored

| # | Area | Today | What a 9 looks like |
|---|---|---|---|
| 1 | The answer | **3** | In ten seconds: what moved, by how much, and the graded why, with the evidence one tap away |
| 2 | Big movers | **2** | Every top-100 coin past a real threshold is listed, graded and explained the same day |
| 3 | Truth machinery | **5** | Text checked against numbers (done) **and** numbers checked against each other, one causal policy everywhere, nothing stale shown as live |
| 4 | Information architecture and naming | **4** | One plain name per thing; the why is a destination, not a link under a card |
| 5 | Design and feel | **6** | Answer-first hierarchy, tables that fit at 375, charts legible on a phone |
| 6 | Speed and weight | **8** | Lighthouse 90+ mobile on every template, no layout shift |
| 7 | Search and discovery | **4** | A URL per graded move, titles people type, a news sitemap that carries the day |
| 8 | Trust | **5** | Named editor, AI disclosure, a corrections log, a public record of how the verdicts held up |
| 9 | Daily rhythm | **5** | Every slot fresh and on time; a market move between slots gets a read within the hour |
| 10 | App readiness | **2** | A versioned JSON feed per screen, a push event log, a watchlist |
| | **Overall (mean)** | **4.4** | |

### 1.1 The answer: 3

**What a 9 looks like.** A reader who lands from "why is crypto down today" gets, in the first screen: Bitcoin and the whole market with the move and the window; one or two sentences on the cause, graded; the evidence one tap away.

**What the site does.**
- `/today/` answers *what moved* well, and fast. The first screen at 375 is the date, the direction, and four plain sentences with figures and windows (`02-today-375-fold.jpg`). That part is good.
- It does not answer *why*, by design. Program 8 ruled "no new model call" and "never says because unless a source says so". The page lists wire items "beside" the move and closes with "These are separate reports. The desk does not say one caused the other."
- On the live page at 5:15 PM the "beside" list is empty: "No wire item reported today has cleared the desk yet." The home page at the same moment lists five wire items. The two disagree because `/today/` takes only items stamped since midnight ET.
- **The title contradicts its own second sentence.** It reads "Why is crypto up today?". The next sentence says "The whole market's value was down 0.62%" (`02-today-375-fold.jpg`). Direction comes from Bitcoin's 24h change alone.
- **The dated page can freeze the wrong direction for the day.** At 9:03 AM on 15 October, production read "Why is crypto down today? Thursday" (Bitcoin -2.60%; 8.1 report). The frozen page now reads "Why is crypto up today? Thursday, October 15, 2026" (Bitcoin +0.80% at 7:45 PM). A reader who searched "why is crypto down today" that morning now lands on "up".
- **The one causal line the page did carry was not in its source.** The 15 October dated page lists, fifth of five, "Hot US producer-price data triggered nearly $940 million in crypto liquidations as Fed rate-hike bets spiked to 50%", with 12:25 AM and one source, CoinDesk.
  - The linked piece gives $483 million and "uncertainty about the Federal Reserve's next interest-rate decision".
  - The stored morning record for the same item carries a different line: "Nearly $1 billion ... as hot US inflation data (PPI +1.3%) revived rate-hike bets" (`site/data/today/2026-10-15-*.json`).
  - On Kraken's hourly candles, Bitcoin drifted from $81,729 (20:00 UTC on 14 October) to $80,115 (13:00 UTC on 15 October), then rose to $82,336 by 15:00 UTC.
  - The competitor read found the PPI release at 8:30 AM ET on 15 October, and CoinMarketCap's write-up says "Bitcoin moved less than 1% on the producer price release itself" (release time not checked against BLS by this session).
  - The line names a cause stamped about eight hours before the data it cites, and its own source gives a different one. It also sits under "Stories about Bitcoin" on `/coins/btc`, so 8.2's rule did not catch it. That rule drops a line whose cause word none of its sources carries; the cited headline says only "liquidated as bitcoin, ether and XRP slide".
- **The coin doors promise a why the page refuses.**
  - The title is "Bitcoin price today and why it moved". The block under it says "The desk does not say any of them moved its price".
  - Its only item on 16 October is "Russia's Central Bank confirmed ban on direct P2P crypto trades effective July 1, 2027". That is unrelated to a 1.57% day.
  - The same page's "Stories about Bitcoin" carries the 15 October PPI line above, whose cause its own source does not support (`04-coin-btc-1440-light.jpg`).
- **The two surfaces apply two causal policies.**
  - The Evening Brief archive asserts cause freely, under the "Brief" name: "Wednesday's selloff was driven by U.S. inflation data and rising rate-hike odds" (14 Oct); "suggesting institutional rotation toward self-custody" (September).
  - `/today/` refuses even when a source states the cause.
  - So the reader gets the strict policy where they asked the question and the loose one where they did not.
- **The morning headline implies a cause the numbers cannot carry.** "Bitcoin higher as spot ETFs draw inflows" stands on a $5.1M ETF day against $32.2B of Bitcoin volume (`01-home-375-fold.jpg`). "As" is the copy law's loophole: it reads as "because".

**Score 3.** The what is right and quick. The why is absent where asked for, loose where not asked for, and sometimes wrong in direction.

### 1.2 Big movers: 2

**What a 9 looks like.** Every top-100 coin past a defined threshold is on one list with its move, its excess over the market, and a graded reason; the list is never padded.

**What the site does.**
- `/pulse/movers` and `/today/` list the top and bottom of the Top 100 by 24h change, with no explanation of any of them.
  - On 16 October Celestia (TIA) was up 30.60%, Injective 25.29% and LayerZero 20.59%. Nothing on the site says why.
  - TIA's coin page (`/coins/tia`) shows +31.04%, the readings, and a "Buy direct from Ledger" affiliate card. There is no wire item and no "why" block, because TIA is outside the top 20.
- The movers page tells the reader "if a mover matters, the desk will have covered why." The desk had not. The same box says "A big move with no story is usually noise, or worse, someone's exit." That is itself an unsourced claim about cause (`15-pulse-movers-375-light.jpg`).
- **The list is padded and leaks:**
  - The "Top 5 losers" include #107 Starknet (outside the stated top 100) and PayPal USD at 0.0%, a stablecoin.
  - The heading promises losers on a morning when only three top-100 coins fell more than 1%.
  - Canton is #29 here and #25 on the Top 100.
- **At 375 the table hides the number that matters.** The 24h change column is off the right edge and the price is clipped to "$0." (`15-pulse-movers-375-light.jpg`).
- The home's "Moving today, top 20" shows three coins, and two of them repeat in the "beyond 5%" line under it (`01-home-1440-fold.jpg`).

**Score 2.** Movers are surfaced in two places, with no explanation and a list that leaks.

### 1.3 Truth machinery: 5

**Where it protects the reader (keep all of it).**
- The twins gate drops a sentence whose figure or direction disagrees with the snapshot; 7.3 made it read by clause.
- Color truth: a figure's color always matches its own window's sign.
- The copy law: no prediction, no advice, no percentage in the narrative line.
- The three badges ("Verified", "Verified, primary source", "Unconfirmed, one report").
- The ETF window floor, and the stale-data tripwire.
- On 16 October the morning read published with no drop and no repair (8.2 report).
- This is rare in crypto media and is the base the why feature needs.

**Where it fails: numbers are checked against text, never against each other.**
1. **The whole-market figure is wrong three days running, and nothing catches it.**
   - `market_pulse.py:564` prints CoinGecko `/global`'s `market_cap_change_percentage_24h_usd` unchecked.
   - On 16 October: whole market -0.62%, Bitcoin +1.48% at 59.2% of the market, Ether +4.13%, worst top-100 coin -3.81%. Bitcoin alone contributes about +0.88 points, so the other 40.8% would have to fall about 3.7% while Ether rose 4% and nothing fell 4%.
   - On 15 October: Bitcoin +0.80%, Ether +0.96%, whole market -2.13%.
   - The 8.1 read of 15 October morning: Bitcoin -2.60%, whole market -6.29%.
   - The `/pulse` tile prints "▼ 0.62%" over "▲ Up 0.24% since yesterday's close" (`14-pulse-1440-light.jpg`).
   - The same line's `or 0` would print a fake 0.00% when the field is missing (CLAUDE.md P3's class).
   - The top 250 summed by this session at 5:20 PM gave -0.88% against Bitcoin -0.56%: plausible. **The desk can compute this number itself and should.**
2. **Whale Watch's stablecoin sign is inverted.**
   - The card reads "-$233.2M net stablecoins onto exchanges".
   - The only two stablecoin transfers listed (Bitfinex to Tether Treasury, $131.3M; Binance to Ceffu, $101.9M) both left exchanges, and they sum to exactly $233.2M (`07-flows-1440-dark.jpg`).
3. **Three seven-day figures for Bitcoin on one page.** The chart says "-1.05% over 7 days" (live, read 5:15 PM), the readings tile "+0.08%", and the Chart Master read "down 2.0% over the week" (`04-coin-btc-1440-light.jpg`). On `/coins/aave` the chart's own figure differs between loads (-4.28% vs -7.25%) against a tile of -0.89% (`05-coin-aave-375-fold.jpg`, `05-coin-aave-1440-light.jpg`).
4. **The week's low sits above today's low.** The home card prints "24h high $82,816 · low $79,806" over a chart labeled "7D LOW $81,703" (closes). Each is correct for its own definition; a reader sees a contradiction (`01-home-375-fold.jpg`).
5. **Stale presented as live.**
   - The Top 100's meta description says "Live prices... updated in your browser". The page makes no fetch and reads "As of 8:18 AM ET" nine hours later.
   - The home masthead switches to "LIVE 5:14 PM ET" and recolors Bitcoin red when CoinGecko answers (1 load in 4; 429 in the other 3). The Brief directly under it still says "Bitcoin higher" (`01-home-1440-dark.jpg`).
   - Whale Watch's "22h ago" stamps were frozen at build time, so those transfers were about 31 hours old by 5 PM, outside the window the page claims.
6. **The Chart Master read contradicts itself.** "All seven major assets sit above their 200-day" sits beside "Doge, alone among the majors, sits below its 200-day average". It also says shorts were "shaken out even as the asset has fallen sharply" (`08-chartmaster-1440-light.jpg`).
7. **The gate cuts true sentences** (four times in the window, three fixed; the 15 October USDT sentence is open on the 8.3 list).
8. **The wire line, the one sentence the desk owns on every item, is checked by nothing.**
   - The 15 October PPI line (1.1) carries a cause and two figures ($940 million, 50%) that its only linked source does not.
   - The gates check the desk's sentences against the snapshot, never against the source the line cites.
   - CLAUDE.md P6 already names the cheapest version of the fix: a figure the source does not carry is smuggled. Applied to wire lines, it fails this one.

**Where it costs clarity.**
- The law forbids the desk's own voice from naming a cause, so the reader gets the disclaimer instead of the answer.
- Internal vocabulary leaks into reader copy: "a divergence the desk's own window-sign table flags explicitly" (the 15 October Edition), "Reads with Stablecoin float", "the desk's own boards".

**Score 5.** The text-against-number half is excellent. The number-against-number half and the line-against-source half do not exist, and that is where today's visible errors live.

### 1.4 Information architecture and naming: 4

- **Every nav item carries two names.** MARKETS/The Board, FLOWS/Whale Watch, CHARTS/Chart Master, NEWS/Checked, BRIEF/The Edition, RECORD/Worth keeping, LEARN/The Board explained (`01-home-1440-fold.jpg`). The 375 tab bar keeps only the first word of each.
- **One product has four names.** "The Brief · Friday morning" (home card), "Morning read" (`/today/` stamp), "The Evening Brief" (article titles), "Evening Edition" (next-update line). The nav says "Brief / The Edition" at `/bottom-line`. That page's lede says "Once a day the desk closes its edition" under the cadence line "The Brief, every morning and evening."
- **Two different numbers carry three names.** The stablecoin total is "Stablecoin float" on the Board and "Stablecoin dry powder" in Learn. The exchange flow is "Stablecoin buying power" on Whale Watch.
- **"Moving the market"** heads the home wire list two lines above "It is not a story the desk wrote or checked".
- **The why has no slot in the navigation.** It is reached by a 15 px "Why crypto moved today →" link under the Brief card, and it is not in the 375 tab bar.
- `/bottom-line` holds every Brief ever written on one page: 102,353 px tall at 375, no h2, 126 tap targets under 24 px.
- Coin pages have no h1.
- Full proposal: `NAMES.md`.

**Score 4.** Program 6.3 made one table (`site_build.NAMES`), which makes the fix cheap. The names in it still make a reader guess.

### 1.5 Design and feel: 6

**What works.**
- The 7.1 look is premium: Newsreader headlines, Plex Mono figures, a navy masthead, the Brief card, and the glow kept to data.
- Dark mode is clean and every page fits 375 with no sideways scroll.
- The Bitcoin card at 375 is a strong object (`01-home-375-fold.jpg`, `01-home-375-dark.jpg`).

**What holds it at 6.**
- **Hierarchy answers the wrong question first.** The first phone screen is almost entirely the Bitcoin price card; the Brief headline starts at y 619 of 812. A reader who came for "why" sees a price.
- **The front is two columns of tiles at 1440.** THE MONEY, THE MOOD, MOVING TODAY, then a paragraph of 30 tickers with percentages (`01-home-1440-fold.jpg`). It reads as a terminal, not an answer.
- **Charts are illegible on a phone.** Chart Master's axis labels render about 5 px with cents ("$86,596.74"), with weak dark-mode contrast (`08-chartmaster-375-dark.jpg`). Whale Watch's by-asset labels are unreadable at 375.
- **Tables clip at 375.** Movers hide the 24h change; the Whale Watch exchange table cuts its Out and Net columns (`07-flows-375-light.jpg`).
- **Small type is everywhere.** 10 px minimum (the "Wire" badge, chart labels), much metadata at 10.5 to 12 px mono capitals, inline links about 15 px tall.
- **Desktop reading pages leave the right third empty at 1440** (`02-today-1440-dark.jpg`).
- **Sub-cent sparklines break.** SHIB shows one spike, PEPE a flat line (`06-top100-pulse-prices-1440-dark.jpg`).
- **A shopping card on a moving coin.** The Ledger affiliate card sits mid-page on every coin page, including one up 31% with no explanation.

**Score 6.** It looks like a trusted product until a reader tries to read a chart or a table on a phone.

### 1.6 Speed and weight: 8

- Every page at 375 transfers 81 to 120 KB in 11 to 14 requests: 2 CSS (about 20 KB), 1 or 2 JS (10 to 16 KB), 5 fonts (about 50 KB), and no images.
- Lighthouse, mobile, simulated throttling:

  | Page | Score | FCP | LCP | TBT | CLS |
  |---|---|---|---|---|---|
  | Home | **87** | 1.1 s | 2.3 s | 420 ms | 0.001 |
  | `/coins/btc` | **94** | 1.2 s | 3.0 s | 50 ms | 0 |

- Unthrottled LCP was 304 to 848 ms on every page.
- A-17's 3,000 ms budget is met on home and at the line on the coin page.
- **What costs points:**
  - Home's inline script does about 2.65 s of main-thread work under throttling (the TBT).
  - Coin pages shift layout by **0.276 CLS** at 1440, because the chart box is inserted after load (`P.cc-chg`, `DIV.cc-box`).
  - `/bottom-line` ships 38 KB of HTML because every Brief lives on one page.

**Score 8.** Three fixes (reserve the chart box, trim the home script, paginate the Brief archive) make it 9.

### 1.7 Search and discovery: 4

- **The doors from Program 8 are right.**
  - `/today/` titles match the query ("Why is crypto up today? Friday, October 16, 2026").
  - Coin pages read "<Coin> price today and why it moved", with a numeric description, BreadcrumbList, real lastmod and IndexNow.
- **What undercuts them:**
  - Home's title is "GoCheckMyCrypto - Crypto, checked.", the brand alone, with no query words. `/pulse/prices` is "Top 100 - Markets"; people type "top 100 crypto prices".
  - **No new article since 6 October.** The wire path (7 October) stopped written stories: 192 in August, 210 in September, 13 in October, none after the 6th.
  - The news sitemap carries two URLs, both Evening Briefs. Wire lines have no URLs of their own; the "checked story" on home links out to CoinDesk.
  - For Google News and for long-tail search, the site has gone quiet while still publishing every day.
  - Dated `/today/` pages exist for 15 and 16 October only; 2 to 14 October return 404 (not backfilled).
  - Coin pages have no h1, and the Brief archive has no h2.
  - Structured data: home carries NewsMediaOrganization and WebSite, `/today/` NewsArticle, coin pages BreadcrumbList, articles NewsArticle with author "GoCheckMyCrypto" (Organization). The board pages carry none.
- **What the target queries need.** "Why is crypto down today" is answered on the day by a page whose first sentence states the cause; a page that disclaims the cause loses that query to one that names it. "Why is <coin> up" is a long tail of hundreds of coins; only a per-move graded page wins it. Section 3.6 puts a URL on every graded verdict.
- The kill test in Program 8 (no impressions growth by 7 December freezes `/today/`) stands, and the first meaningful read is 9 November.

**Score 4.**

### 1.8 Trust: 5

**Strong.**
- Sources are linked on every item and outlets are counted.
- Every figure carries its source and stamp ("CoinGecko · 8:18 AM ET on Oct 16").
- The three badges are defined on `/standards`.
- "Not financial advice" is plain.
- How we make money (affiliate) is disclosed beside each card.

**Weak.**
- **No page says the stories, Briefs and reads are drafted and checked by AI models.** `/about`, `/method` and `/standards` say "an independent verification pass" and "a human editor-in-chief oversees the desk". The editor is not named anywhere. Articles are bylined "By GoCheckMyCrypto".
- A site whose promise is "checked" and whose text is model-written carries a disclosure risk that a competitor or a regulator can turn into the story.
- **Corrections:** `/standards` promises them, and 0 of 564 content files carry one. There is no corrections log page.
- "How we work" (478 words) and "Standards and corrections" (433 words) overlap almost entirely.

**Score 5.**

### 1.9 Daily rhythm: 5

The window: 2 to 16 October, 18 scheduled slots. Fourteen Editions at 7:08 PM, and four morning reads from 13 October when the slot began.

| | Scheduled | Fresh within 60 min | Late over 60 min | Fallback | Missed |
|---|---|---|---|---|---|
| Edition | 14 | 12 (10 first try, 2 on the +37 min retry) | 0 | 0 | 2 (7 Oct withheld by the consistency gate; 12 Oct canary crash) |
| Morning read | 4 | 2 | 0 | 1 (15 Oct) | 1 (13 Oct, launch day, Worker not yet deployed) |
| **All** | **18** | **14 (77.8%)** | **0** | **1** | **3** |

- First attempt on time: 12 of 18 (66.7%).
- **A fresh answer is not a correct one.** Of the two `/today/` pages that exist, the 15 October page froze the wrong direction (1.1) and both print the wrong whole-market change (1.3).
- Runs in the window: the daily brief failed 20 of 56, but 12 of those are the Edition-gap gate going red on retries after the slot was served (an advisory check erroring, against CLAUDE.md's rule). The watcher failed 16 of 478; the morning read 0 of 11.
- GitHub's crons fired 2.7 to 4.4 hours late every evening; only the Worker's dispatches keep the slots on time.
- **Between slots the site is static for 11 to 13 hours.** A reader at 5 PM sees "UPDATED 8:19 AM ET" on every page with no staleness warning. On 16 October the market reversed after the morning read (Bitcoin +1.57% at 8:18 AM, -0.56% at 5:20 PM). No page said so except the home tape, on the one load in four when CoinGecko answered.
- Incidents, with causes and fixes, are in the handoffs and the 7.x and 8.x reports.

**Score 5.** On time most days; often not correct; silent all afternoon.

### 1.10 App readiness: 2

- **What exists.**
  - A web manifest, which still carries the old paper color `#FBFAF6` as background.
  - A service worker (`/sw.js`, 1.4 KB).
  - Three JSON files served as a side effect of the build: `/data/snapshot.json` (40.8 KB), `/data/wire.json` and `/data/narrative.json`.
  - "Pin BTC" on coin pages.
  - The Worker (`gcm-slot-trigger`), which could serve a live price route and push.
- **What an app needs that does not exist.**
  - A versioned JSON feed per screen with a stale flag. `/data/pulse.json` and the `/today/` records answer 404.
  - A defined list of push moments.
  - A watchlist.
  - A widget-sized summary.
  - A live price source that is not each client calling CoinGecko's free API. That call fails 3 times in 4 from one browser today.

**Score 2.**

---

## 2. The competition

The same reader question was read across seven outlets on Friday 16 October, between 5:15 and 5:45 PM ET. By then the day had turned. Bitcoin peaked near $82,550 about 8 AM ET and slid to about $81,040 by 3 PM ET as the Nasdaq fell about 2% and oil jumped. So the live question was "why is crypto down today", and the site's `/today/` still said "up".

| Outlet | Reachable | What they answered today | Speed | Evidence | Where they guess |
|---|---|---|---|---|---|
| **CoinDesk** | 200 | Morning: "Altcoins outpace bitcoin as celestia jumps 16%, Warsh silent on interest-rate plans". Afternoon live blog, 14 entries, 5:48 AM to 4:25 PM ET: "Bitcoin dips to $81,000 as stocks slide, VIX soars", citing the AI-stock selloff, then "WTI crude now up more than 3%" on reports of a Saudi pipeline attack | Best of the set: an 11:28 AM entry ("dipped about 1% over the 30 minutes") matches the hourly prices | Strong: open interest against price to infer short covering, ETF flows by asset, implied volatility, funding, CME FedWatch odds, the 10-year yield; links Celestia's own post for TIA | A headline "Nearly $1 billion in crypto bets liquidated" over a body that supports $483 million; "suggests the forced selling has run its course"; quotes an exchange executive's view as context. TIA's linked catalyst post is dated 1 October, so it is background, which CoinDesk's "coinciding" correctly hedges |
| **CoinMarketCap** | 200 (AI widgets need a browser) | An AI button, "Why is the market down today?" ("Generated 17 minutes ago"): "a macro-driven selloff led by Bitcoin... strong correlation (92%) with the S&P 500". A written analysis as of 9:40 AM ET that missed the afternoon turn | AI: minutes. Articles: one a day | Its written pieces are well sourced: FedWatch 14.9% vs 27.7%, CoinGlass, Farside, Glassnode. The best timing sentence of the day: "Bitcoin moved less than 1% on the producer price release itself" | The AI asserts with no evidence and gets mechanics backwards: "dominance rose... confirming it led the downturn" (rising dominance in a fall means Bitcoin fell less); falling ETF AUM read as outflows (Farside shows an inflow); for TIA, "a broad rotation of capital into altcoins". The gainers page is a bare table |
| **Decrypt** | 200 | "Bitcoin Bounces, But Where Does It Go Next?", chart levels with no cause for the bounce | Late: published 38 minutes after CoinDesk reported the turn lower | Its 15 October piece is good: CPI and PPI against forecasts, liquidations with the long share | Puts the 15 October fall on CPI and PPI although most of it came before the PPI release |
| **The Block** | Home 403; RSS and data pages 200 | No "why today" piece on 16 October; the last explainer was 15 October at 12:38 AM ET | n/a | Company news only | Its ticker shows two different Bitcoin changes on one page with no stamp |
| **CoinGecko** | Web 403 by curl, 200 in a browser; API 200 | Template: "Celestia (TIA) price has increased today... 13.84%". The AI answer needs a sign-in | n/a | None on cause | Trending led by an unexplained +63% micro-cap; its own Fear & Greed reads 32 where alternative.me reads 63 and CoinMarketCap 50 |
| **CryptoPanic** | 200 (JS) | An aggregator with a "Panic Score"; no cause | n/a | None | Sponsored items in the news feed |
| **Messari** | 429 and 502 on every path, by curl, browser and fetch | Not evaluated | | | |

**Search.** The search tool available here is not Google, so this is not a ranking measurement. For "why is bitcoin up today" and "why is the crypto market down today" it returned dated syndications (finanzen.at, Benzinga's "Why Is Crypto Up Today? June 16, 2025", Yahoo) and spam on hijacked subdomains. None of the seven appeared, and neither did GoCheckMyCrypto. The query space looks held by stale or junk pages, which is an opening. The 9 November Search Console read (8.4) is the real measurement.

**What GoCheckMyCrypto can do that none of them do.**
1. **Publish the timing test as the answer.** Put the primary-source time on the price line and measure the reaction, for every claimed cause, every day. CoinMarketCap wrote one such sentence on 16 October; nobody makes it the standard. It would also have caught the desk's own 15 October wire line.
2. **Grade the cause, including "Disputed" and "Unclear", and grade other outlets' causes too.** CoinDesk says "no obvious, overriding narrative" when it is true. CoinMarketCap's AI always names a "primary reason". A public record of graded verdicts would have marked CoinMarketCap's AUM-as-outflows claim Disputed against Farside's +$5.1M. No competitor keeps score of its own explanations; the verdict record (Sprint 9.8) is the moat.
3. **Reconcile the numbers and re-answer when the direction flips.**
   - Four outlets gave four liquidation totals for one event ($483M, "nearly $1B", $939.53M, $948M).
   - Three indices called "Fear & Greed" read 32, 50 and 63.
   - The desk already prints a source and window on every figure. It can be the place that says which number is right, and it can re-issue the why when the market's sign flips between slots instead of holding a morning "up" until 7:08 PM.

**What to learn from them.**
- From CoinDesk: inferring short covering from open interest against price; flagging rumors as unconfirmed; saying "no obvious narrative" out loud.
- From CoinMarketCap: the "Watch for" line of falsifiers.
- From Decrypt: plain definitions inline.

---

## 3. The plan to 9

### 3.1 The why, done honestly: "Why it moved"

**The idea in one line.** The desk already refuses to guess; the step to a 9 is to stop refusing to answer: test each candidate cause against the clock and against the market's own mechanics, grade it in code, and show the test. The copy law stays as strict as it is. What changes is that a cause can pass it on evidence the desk measured, not only on a sentence an outlet wrote.

**What it explains, and when.**

| Subject | Explained when | Runs in |
|---|---|---|
| Bitcoin | Every slot. A flat day (within 0.5%, Program 8's rule) reads "Flat: nothing to explain" and gets no grade | morning read, Edition |
| The whole market | Every slot, using a change the desk computes (top 250 by cap, summed) and cross-checks against `/global`; when the two differ by more than 0.5 points the desk's figure prints and the gap is logged | same |
| Ether | Every slot when its move differs from Bitcoin's by 2 points or more; otherwise one line, "moved with Bitcoin" | same |
| Any top-100 coin | 24h move of 10% or more, AND at least 2.5 times its own 30-day daily volatility, AND at least 6 points beyond what Bitcoin's move predicts for it (30-day beta). Stablecoins excluded. At most 8 a slot and 10 a day, ranked by the volatility multiple | same, plus breaking |
| Breaking | Bitcoin or the whole market moves 3% or more inside 60 minutes, or 5% inside 24 hours, between slots | the watcher's existing `hourly_move` trigger, switched on for this desk only (CLAUDE.md P4), inside the cage's two-a-day limit |

The coin threshold is sized against the desk's own history (section 3.2): it gives about 5 to 8 reads on a typical day and is capped on crash days. For two weeks every candidate that fails the gate prints in the run log, so Jack can move the line on evidence.

**The four layers.**

1. **What is reported, with primary sources checked.**
   - Candidates come from the wire the desk already clusters and ranks (`wire.json`: outlets counted, primary flag, links).
   - Fixed primary feeds that explain most moves are added. All are free and reachable from here or from the runners:
     - US release times (BEA's `release_dates.json` carries times; the BLS schedule; Nasdaq's and ForexFactory's economic calendars with ET times);
     - the Fed's FOMC calendar and statements;
     - SEC press releases and EDGAR 8-K and full-text search (needs a contact User-Agent);
     - CFTC press releases;
     - the Federal Register (blocked here, works from the runners);
     - exchange listing and delisting notices;
     - DefiLlama for hacks and stablecoin supply.
   - Each candidate carries two times: the **event time** (release time, filing stamp, block time) and the **first-report time** (the earliest outlet stamp).
   - A cause that appears only in commentary ("analysts said") is kept and marked secondary.
2. **The timing test.**
   - Intraday prices at 5 minutes for the last 24 hours, for any coin, from CoinGecko `market_chart?days=1` (already used by the coin chart). Kraken, Coinbase, OKX 1-minute candles and Binance's public `data-api.binance.vision` mirror second it; together they cover 70 to 76 of the top 100.
   - Code finds the move's onset (the start of the largest same-direction run in the window) and asks three questions of each candidate:
     1. Did the event come before the onset: within 60 minutes, or at the scheduled release time?
     2. What share of the day's move happened in the 60 minutes after it?
     3. Did the price move before the news? If so, the news cannot be the cause, and the page says so.
   - It prints with its numbers, for example: "Released 8:30 AM ET; Bitcoin fell 1.9% in the next 40 minutes, 71% of the day's fall." (Illustrative wording; no figure in this example was measured.)
3. **The market mechanics in the same window.** Each source, its venue, and whether it is new:

   | Mechanic | Source | Notes |
   |---|---|---|
   | Liquidations | OKX `liquidation-orders` (on the Board now), Gate and Hyperliquid as second and third venues | No free market-wide total exists, so the page names the venues |
   | Open interest and taker flow | OKX `rubik` 5-minute series | New |
   | Funding | OKX | On the Board now |
   | Spot ETF flows | Farside, daily | On the Board now. Daily only, so it can support a day's verdict and never an hour's |
   | Stablecoin supply | DefiLlama, daily per-coin | Gives a mint and burn proxy |
   | Cross-asset prices | Yahoo's chart API, 5-minute bars, reachable: S&P 500 and Nasdaq futures, the dollar index, the 10-year yield and the 2-year note future, gold, oil, VIX, and IBIT and FBTC volume | IBIT and FBTC volume is the only intraday ETF proxy |
   | Rate expectations | Kalshi's Fed markets | Public and free |

   Code computes what each did in the onset hour and labels the pattern: "risk-off across assets", "crypto only", "leverage flush" (open interest down 5% or more with liquidations mostly on one side), or "coin-specific" (the coin's excess move over its Bitcoin beta).
4. **The graded verdict.** The grade is computed by code from layers 1 to 3, never chosen by a model:
   - **Confirmed**: a primary source, or two independent outlets, state the cause; the timing test passes; the mechanics agree.
   - **Likely**: the timing test passes and the mechanics agree, with no source stating the cause; or a source states it and the timing passes but the mechanics are silent.
   - **Disputed**: a reported cause fails the timing test (the price moved first), or the mechanics contradict it.
   - **Unclear**: no candidate passes the timing test. The page says "No reported event lines up with this move" and still shows the mechanics.

   How the sentence is written and checked:
   - A model writes only the two-sentence verdict, from finished phrases (8.2's `phrases.py` rule).
   - A second, stronger pass states `stands` per claim, the `wrap.check` rule, before anything prints.
   - The twins gate checks every figure.
   - "Because" prints only on Confirmed. Likely says "lines up with". Disputed shows both sides.
   - Nothing predicts and nothing advises.

**What the reader sees.** One card, the same shape on home, `/today/`, each coin page and the app.

The worked example below is the 15 October line from section 1.1, graded the way the engine would grade it. The Bitcoin prices are Kraken's hourly closes. The release time comes from the competitor read and was not checked against BLS by this session. The wording is illustrative.

> **Bitcoin down 2.0% overnight, then back up. Checked: Disputed.**
> Reports blamed hot US producer-price data. Most of the fall came before that release: Bitcoin slid from $81,729 at 4 PM ET Wednesday to $80,115 by 9 AM ET Thursday, and rose 2.1% in the hour after 10 AM. CoinDesk's own report gave uncertainty about the Fed's next rate decision, and $483 million in Bitcoin and Ether liquidations.
> [the timing chart: the overnight slide, the 8:30 AM release pinned on it, the rebound shaded]
> Evidence: CoinDesk (04:25 UTC) · Kraken hourly prices · BLS release time · OKX liquidations · how we grade

The timing chart is the product's signature. It shows the reader the test, not only the verdict. A "Disputed" that says so plainly is worth more to a reader than a fluent "because". Of the seven competitors read, only CoinMarketCap's write-up made this check, in one sentence (section 2).

**What it fixes on the way.** The dated page's direction becomes the ET calendar day's move (midnight ET to the slot's reading, and midnight to midnight once the day is over), not a 24-hour snapshot at publish time. A day that fell then cannot freeze as "up". The whole-market figure is the desk's own (1.3).

**Model cost per day.** Prices per million tokens, input and output, as cached on 6 October 2026: Haiku 5.5 $0.10/$0.50, Haiku 4.5 $1/$5, Sonnet 5.5 $2/$10, Opus 5.5 $4/$20.

Assumptions: 6 market and Bitcoin reads a day at 15k tokens in; coin reads at 8k tokens in; about 800 visible output tokens plus about 1.5k of thinking per call; the grader reads the draft call's input plus the draft; 30% added for repair rungs.

| Draft model and grade model | 5 coin reads | 10 coin reads | 20 coin reads |
|---|---|---|---|
| **Haiku 5.5 draft, Sonnet 5.5 grade (recommended)** | $0.62 a day | $0.84 a day (about $25 a month) | $1.30 a day |
| Haiku 4.5 draft, Sonnet 5.5 grade | $0.81 | $1.10 | $1.70 |
| Sonnet 5.5 draft, Opus 5.5 grade | $1.97 | $2.72 | $4.20 |

- Today's whole-desk spend is about $0.10 to $0.23 a day (`ledger.json`, 7 to 15 October), so the recommended pairing is roughly five to eight times today.
- The grader is 90% or more of the cost.
- These are estimates from token budgets, not measurements (U-5): the first live week's ledger replaces them.
- **This reverses Program 8's "no new model call" ruling for the daily answer, and is Jack's decision (section 4).**

**Two `llm.py` defects must be fixed before any 5.5 model is used.**
- `llm.py:231` disables thinking with `model.startswith("claude-sonnet-5")`. That also matches `claude-sonnet-5-5`, which rejects `{type: "disabled"}` with a 400, so every Sonnet 5.5 call would fail.
- `PRICING` (`llm.py:47`) has no 5.5 entries. Those models fall back to the default price, which would overstate Haiku 5.5 spend about 50 times and trip the $1.50 run cap early.

### 3.2 Big movers

- **Surfacing.**
  - One list, "Big movers", replaces the padded top 5 and bottom 5.
  - Every top-100 coin past the 3.1 threshold, in order of its volatility multiple, each with its 24h move, its excess over Bitcoin, its volume against its 7-day average, and its grade.
  - Stablecoins never appear. A rank over 100 never appears.
  - When no coin falls past the line, the page says "No top-100 coin fell more than 4%" instead of padding.
  - The 24h column is the first column after the name at 375.
- **How many.** By the desk's own history, from 190 versions of `pulse.json` across 44 days (28 July to 16 October), per day:

  | Threshold | Last snapshot of the day (mean / median / max) | Unique coins over all the day's snapshots (mean / median / max) |
  |---|---|---|
  | ≥ 10% | 4.5 / 3 / 24 | 7.4 / 5 / 27 |
  | ≥ 15% | 1.6 / 1 / 8 | 2.5 / 2 / 8 |

  - From 168 days of close-to-close data for 75 of today's top 100, "2.5 times own volatility" fires on a median of 1 coin a day, with a p90 of 6.
  - The proposed AND-gate gives about 5 to 8 reads on a typical day. On a market-wide crash day, which ran to 25 to 50 coins on 18 September, 21 September and 12 October, it gives a cap of 10.
  - On a crash day most alts are "moving with the market". The page says that once, with Bitcoin's verdict, and grades only the coins whose excess move needs its own cause.
- **Explaining.**
  - Each mover gets the same four layers. Its layer-1 feeds are the alt-specific causes: exchange listings and delistings, token unlocks (where the calendar can be read; three vesting pages answer 403 today), hacks and exploits (DefiLlama), protocol upgrades and governance votes, and the wire.
  - Layer 3 adds the coin's own perp funding and open interest where a venue lists it (Hyperliquid covers 65 of the top 100).
  - The verdict sits on the movers list, at the top of the coin's own page (above the readings, and above the Ledger card), and in the coin's "Why <coin> moved" block. That block extends from the top 20 to any coin that crossed the line.
- **Linked.** A mover links to its coin page. The coin page links to the dated verdict page. The Brief cites the movers it mentions.

### 3.3 A naming system

All options are in `NAMES.md`. The recommendations:
- **"Why it moved"** for the why feature, with **Confirmed / Likely / Disputed / Unclear** as the grades and "Checked:" as the lead word.
- **"Big movers"** for the movers feature.
- One name per section: Markets, Whale Watch, Charts (with "The chart read" for the daily card), News, The Brief (Morning Brief and Evening Brief), Storylines, Learn.
- "What was reported" in place of "Moving the market".
- "Stablecoin supply" and "Stablecoins onto exchanges" for the two stablecoin numbers.
- "How we check" for the merged method and standards page.

Jack picks.

### 3.4 Design moves, ranked by score lift per hour of build

| # | Move | Hours | Lifts |
|---|---|---|---|
| 1 | **Answer first.** The verdict card is the home page's first object at 375 and 1440, above the Bitcoin card, which shrinks to one line of price and change. `/today/` opens with the card | 4 to 6 (after 3.1) | Answer, Design |
| 2 | **A visible stale state.** When a page's Board stamp is more than 3 hours old at the moment of reading, the masthead says "Prices as of 8:18 AM ET, 9 hours ago" in the warning color, computed in the browser from the stamp. The "LIVE" swap happens only when every figure in that card is live | 2 | Truth, Rhythm |
| 3 | **Tables that fit 375.** Movers: rank, coin, 24h, price; market cap behind a tap. Whale Watch by-exchange: net only at 375. One shared rule in `system.css` | 3 | Design, Movers |
| 4 | **Charts that read on a phone.** 12 px minimum axis labels, prices rounded to the dollar above $1,000, contrast 4.5:1 in dark | 3 | Design |
| 5 | **One name per thing** (NAMES.md), and the why in the nav and the 375 tab bar (Why, Markets, Movers, Whale Watch, Brief) | 3 | IA |
| 6 | **Reserve the coin chart's box** (CLS 0.276 to 0) and **paginate the Brief archive** (one page per month) | 2 | Speed, Design |
| 7 | **Move the Ledger card** below the coin's news on every coin page, and off any page whose coin moved past the mover line that day | 1 | Trust, Design |
| 8 | **Fill the 1440 reading pages' right column** with the evidence list and the timing chart | 2 (after 3.1) | Design |

### 3.5 The iOS path

**Build into the site now, so the app is cheap later.**
1. **One JSON file per screen, written by the build that writes the HTML, from the same records.**
   - The HTML is rendered from the file the app reads, so the two cannot disagree.
   - Paths under `/api/v1/`, each file with `schema`, `as_of_utc` and `stale`: `why/today.json` (verdict, grade, evidence list, the timing series), `why/<date>.json`, `movers.json`, `markets.json`, `top100.json`, `coins/<sym>.json`, `whales.json`, `brief/latest.json`, `news.json`.
   - The three files served today (`/data/snapshot.json`, `wire.json`, `narrative.json`) are the start. They have no version and are shaped for the build, not for a screen.
2. **A push event log before any phone buzzes.** `/api/v1/events.json` holds the newest 50 events that *would* push:
   - a graded verdict on a market move past the breaking line;
   - a top-10 coin past its mover line;
   - a verdict that moves (Likely to Confirmed, or to Disputed);
   - the Morning and Evening Brief published;
   - a correction.

   Two weeks of this log is how Jack sets the push volume.
3. **A watchlist on the site first**, kept in the browser as a convenience (the existing "Pin BTC" is the start). The per-coin why logic is then written once. No account and no email capture (Jack's standing rule).
4. **Live prices through the Worker.** A cached `/live/prices` route (60-second cache) on the existing `gcm-slot-trigger` Worker serves the home tape now and the app and widgets later. Each browser stops hitting CoinGecko's free tier, which refuses 3 loads in 4 today. The Worker lives in `gcm-newsroom`, so this needs Jack.

**The app, for a later program (rough scope).**
- SwiftUI and read-only. Five tabs: Why it moved, Markets (with the watchlist), Big movers, Whale Watch, Brief.
- One home-screen widget: Bitcoin price, 24h change, the latest grade.
- Push through APNs, sent by the Worker from `events.json`.
- No login, no trading, no ads.
- Needs an Apple Developer Program membership ($99 a year).
- Size: about three to four sessions to a TestFlight build once the feeds exist, plus App Review. Without the feeds the app would scrape its own site and cost about double.

### 3.6 The sequence: Program 9

Each sprint is one session, one branch, one merge build (one of the day's three merge slots). Score lifts are the audit's own estimate of each area after the sprint lands; the overall is the mean of the ten.

| Sprint | What | Model, effort (U-2) | Builds | New model spend | Lifts | Overall after |
|---|---|---|---|---|---|---|
| **9.1 Numbers that agree** | Whole-market change computed and cross-checked; Whale Watch stablecoin sign; one seven-day figure per page, each window labeled; movers list rules (no stablecoins, rank ≤ 100, no padding, 24h visible at 375); Top 100 "live" claim removed; the stale state (3.4 #2); `/today/` direction by ET day; "Moving the market" retired; `/bottom-line` lede; "last 1 hours"; the `llm.py` thinking and pricing defects; **Program 8.3's list items 1 to 5** (coin chart to the current reading, the "However," lift, an outlet counted twice, the stablecoin binding, the Edition-withheld line, and `today.py`'s slot taken from the read); **a source check on every wire line**: a figure or cause word in the line that its linked sources do not carry drops the clause, logged (CLAUDE.md P6 applied to the wire) | Sonnet 5.5, medium | 1 | none | Truth 5→6, Answer 3→4, Movers 2→3, Rhythm 5→6 | 4.8 |
| **9.2 The evidence** | `why_evidence.py`: intraday series, candidate events with event and report times, the timing test, the mechanics pattern; fixtures recorded from real days (14 to 15 October first); `/today/` and the Bitcoin and Ether pages show "What lined up with the move" and the timing chart, with no grade yet | Opus 5.5, high | 1 | none (no model) | Answer 4→6, Truth 6→8 | 5.2 |
| **9.3 The verdict** | Grade rules in code; the two-sentence verdict (Haiku 5.5) and its check (Sonnet 5.5); the card on home, `/today/`, Bitcoin and Ether; **a URL per graded verdict** (`/why/2026-10-14-bitcoin`) in the news sitemap; corrections render on the verdict | Opus 5.5, high | 1 | about $0.35 to $0.45 a day (6 reads) | Answer 6→8, Search 4→6 | 5.6 |
| **9.4 Big movers, checked** | The mover gate; alt feeds (listings, unlocks, hacks); verdicts on movers and coin pages; the market-move breaking trigger on (crypto only, inside the cage) | Opus 5.5, medium | 1 | rising to about $0.84 a day at 10 coin reads | Movers 3→8, Rhythm 6→7 | 6.2 |
| **9.5 Names, the answer-first front, and trust** | Jack's NAMES.md picks; the verdict card first on home; the why in the nav and tab bar; design moves 3 to 7; AI disclosure and the named editor on About; "How we check" merges method and standards; a corrections log page | Sonnet 5.5, medium | 1 | none | IA 4→8, Design 6→8, Trust 5→7 | 7.0 |
| **9.6 The share loop, re-aimed** | Program 8.3's share loop, built on the verdict card instead of the Brief: a square card per verdict and per day, Open Graph per verdict URL, the queue Jack posts from | Sonnet 5.5, medium | 1 | none | Search 6→7 | 7.1 |
| **9.7 App-ready feeds and the search pass** | `/api/v1/` per screen with stale flags; `events.json`; the browser watchlist; the Worker live-price route (needs Jack: `gcm-newsroom`); home and Top 100 titles; h1 on coin pages; backfill of dated why pages from stored records only (never invented) | Sonnet 5.5, medium | 1 | none | App 2→6, Search 7→8, Speed 8→9 | 7.7 |
| **8.4 The first read** (kept as Program 8 wrote it) | Search Console baseline and the first Monday read; now also reads the verdict URLs | Sonnet 5.5, low, documents only | 0 | none | measurement only | |
| **9.8 The verdict record** | A public page scoring the desk's own grades after the fact: how many Likely verdicts a later primary source confirmed, how many were reversed. The trust feature no competitor can copy without the grading underneath | Opus 5.5, medium | 1 | none | Trust 7→9, Answer 8→9 | 8.0 |

**Where the remaining points come from.** About 8 by the end of 9.8 is what the build can buy. The last point is earned over time:
- the verdict record has to accumulate weeks of graded moves that held up (Trust 9, Search 9);
- the rhythm has to run a month with no missed slot and no wrong direction (Rhythm 9);
- the app has to ship (App 9).

A 9 is realistic in about eight weeks of the sequence above plus the app program. That is not a promise; the ledger and the 8.4 reads decide it.

**Program 8's remaining sprints.**
- 8.3's list items 1 to 5 are truth fixes and go first, inside 9.1.
- 8.3's share loop moves to 9.6, aimed at the verdict, which is the thing worth sharing.
- 8.4 stays as written, documents only, on its own Monday schedule; its first meaningful read is 9 November.
- The 7 December kill test stands, now applied to `/today/` and the verdict URLs together.

---

## 4. Decisions for Jack

1. **Let the desk grade a cause.** Program 8 ruled the daily answer says "because" only when a source does, and `/today/` prints "The desk does not say one caused the other." The plan keeps "because" for Confirmed only, but lets the desk print **Likely** ("lines up with") when its own timing test and mechanics agree. **Recommended: yes.** Without it the site cannot answer its own title.
2. **New model spend for the why.** About $0.62 to $1.30 a day (recommended pairing, 5 to 20 coin reads), against about $0.10 to $0.23 today, which reverses "the daily answer makes no new model call." **Recommended: yes, capped at $1.50 a day** by the existing run cap.
3. **The names.** `NAMES.md`, section 7 (four picks).
4. **Disclose the models and name the editor** on About and in "How we check", and keep a corrections log. **Recommended: yes**, before the verdict ships, because a graded "Checked: Likely" from an unnamed, undisclosed process is the weakest point a critic can find.
5. **Written stories.** The wire path ended them on 7 October. **Recommended: the graded verdict pages become the desk's articles** (one URL per graded move), rather than restoring the old story pipeline.
6. **A market-move breaking trigger on this desk.** The cage keeps price triggers off ("volatility, not events"). On a crypto desk a large move is the reader's question. **Recommended: on, crypto only, at the 3.1 thresholds, inside the two-a-day limit.**
7. **The Worker live-price route** (`gcm-newsroom`). **Recommended: yes in 9.7**; it fixes today's 3-in-4 refusals and is the app's price source.
8. **Order.** **Recommended: 9.1 first** (truth fixes, no model, one build), then 9.2 to 9.4 back to back, then names and the front together in 9.5. The share loop waits for the verdict.

## 5. Evidence index

| Claim | Where |
|---|---|
| `/today/` title "up" beside "whole market down 0.62%" | `02-today-375-fold.jpg`, `02-today-1440-dark.jpg`, `site/data/today/2026-10-16-morning.json` |
| 15 October frozen as "up"; the PPI item listed fifth of five | `03-today-2026-10-15-375-light.jpg`, `03-today-2026-10-15-1440-light.jpg`, `site/data/today/2026-10-15-evening.json` |
| The PPI wire line against its source | the line: `site/data/today/2026-10-15-evening.json` and `-morning.json`; the source: coindesk.com/markets/2026/10/15/nearly-usd1-billion-in-crypto-bets-liquidated-as-bitcoin-ether-and-xrp-slide (datePublished and dateModified 2026-10-15T04:25Z, read 5:50 PM ET); prices: Kraken `OHLC?pair=XBTUSD&interval=60` |
| Home first screen: price card, Brief at y 619, "as spot ETFs draw inflows" | `01-home-375-fold.jpg` |
| Home LIVE tape red under a "Bitcoin higher" Brief | `01-home-1440-dark.jpg` |
| Home at 1440: two names per nav item, tiles, ticker paragraph | `01-home-1440-fold.jpg` |
| Bitcoin page: three seven-day figures; Russia P2P as "why"; PPI under "Stories" | `04-coin-btc-1440-light.jpg`, `04-coin-btc-375-light.jpg` |
| Coin chart figure differs between loads | `05-coin-aave-375-fold.jpg`, `05-coin-aave-1440-light.jpg` |
| Top 100 static "As of 8:18 AM" under a "live" description; sub-cent sparklines | `06-top100-pulse-prices-375-fold.jpg`, `06-top100-pulse-prices-1440-dark.jpg` |
| Whale Watch stablecoin sign; tables clipped at 375 | `07-flows-1440-dark.jpg`, `07-flows-375-light.jpg` |
| Chart Master contradictions; 5 px axis labels | `08-chartmaster-1440-light.jpg`, `08-chartmaster-375-dark.jpg` |
| Brief archive: "Once a day", one page of every Brief | `09-bottom-line-1440-dark.jpg`, `09-bottom-line-1440-light-full.jpg` |
| Trust pages: no AI disclosure, unnamed editor | `11-about-375-light.jpg`, `12-method-375-light.jpg`, `12-standards-375-light.jpg` |
| Newest article 6 October; "By GoCheckMyCrypto" | `13-article-375-light.jpg` |
| `/pulse` whole market ▼0.62% over ▲0.24% | `14-pulse-1440-light.jpg` |
| Movers: #107 and a stablecoin among losers; 24h hidden at 375 | `15-pulse-movers-375-light.jpg`, `15-pulse-movers-1440-dark.jpg` |
| Record lanes and dates | `16-record-1440-light.jpg` |
| Learn | `10-learn-375-light.jpg`, `10-learn-1440-light.jpg` |

Every page in `shots/` exists at 375 and 1440, light and dark, plus a fold shot at each width: `NN-slug-{375,1440}-{light,dark,fold}.jpg`. The 375 shots of `/bottom-line` are clipped at 9,000 px (the page is 102,353 px). In the 375 full-page shots the fixed tab bar appears partway down the image; that is the capture, not the site.

Shell date, ET, at the close: see the final line of the session's report.
