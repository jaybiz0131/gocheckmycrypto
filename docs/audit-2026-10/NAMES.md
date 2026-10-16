# GoCheckMyCrypto: the naming system (for Jack to pick)

Written Friday 16 October 2026 by the strategy desk's audit session, from a read of production (build `9c8af54`, built 12:19 UTC) and of `site_build.NAMES`, `home.py` and the live pages. Companion to `AUDIT.md`. Nothing here is built; every row waits for Jack's pick.

## 1. What is wrong today, in one table

The site gives most things two or three names, and some names promise what the page will not do.

| Thing | Names a reader meets today | Where |
|---|---|---|
| The market dashboard | "Markets", "The Board", "Markets: The Board" | nav, `/pulse` title, home "Everything below is the Board" |
| Exchange transfer tracking | "Flows", "Whale Watch", "Whale net", "whale flows", "on-chain flow data" | nav, `/flows`, the Board tile, Learn, `/onchain-flows` |
| The chart page and its daily read | "Charts", "Chart Master", "Chart Master's read", "The tape", "the read" | nav, `/chartmaster`, coin pages, `/pulse` |
| The news list | "News", "Checked", "Ranked by the desk", "The day's stories", "Wire" | nav, `/news` |
| The twice-daily summary | "Brief", "The Edition", "The Brief · Friday morning", "Morning read", "The Evening Brief", "Evening Edition", "the edition", "the daily reads" | nav, `/bottom-line`, home card, `/today/` stamp, article titles, next-update line |
| Lasting pieces | "Record", "Worth keeping", "Running story", "Living table", "Receipts" | nav, `/record` |
| Explainers | "Learn", "The Board explained", "what this means", "Movers 101" | nav, every tile, `/pulse/movers` |
| Stablecoins | "Stablecoin float", "Stablecoin buying power", "Stablecoin dry powder" | the Board tile, `/flows`, the Learn page titled "Stablecoin dry powder: why sidelined dollars matter" |
| The wire list on home | "Moving the market" | home, directly above the line "It is not a story the desk wrote or checked" |
| The why page | "Why crypto moved today" (home link), "Why is crypto up today?" (title), "Today" (eyebrow) | `/today/`; not in the nav or the tab bar |

Three names do active harm:
1. **"Moving the market"** heads a list the desk says, two lines later and again on `/today/`, it does not claim moved the market. The label makes the causal claim the copy law forbids.
2. **"Brief" / "The Edition" / "Morning read" / "Evening Brief"**: one product, four names; the `/bottom-line` lede still says "Once a day the desk closes its edition" under the cadence line "The Brief, every morning and evening."
3. **"<Coin> price today and why it moved"** (the 8.2 coin-page title) promises a why; the block under it says "The desk does not say any of them moved its price." The title is right for search and right for the reader; the page has to earn it (AUDIT.md section 3.1).

## 2. The rules the proposal follows

1. **One name per thing, everywhere**: nav, H1, title tag, card, link text, share card, app tab. `site_build.NAMES` already holds one table, so a rename is one edit plus the strings that bypass it (listed in section 5).
2. **The plain word leads.** A first-time reader should know what is behind a link before tapping it. A brand name survives only where it is already plain (Whale Watch is; Chart Master and The Edition are not).
3. **"Checked" is the brand's verb**, so it goes on the thing that is actually checked: the graded verdict and the verified stories. It is not spent on a nav label.
4. **No name claims a cause** the page does not grade.
5. **URLs never change** (Program 6.3's rule). Renames move labels; old paths stay, new paths are added only for new features.

## 3. The two new features

### 3.1 The evidence-graded why (AUDIT.md section 3.1)

| Option | Page and nav label | A verdict reads | For | Against |
|---|---|---|---|---|
| **A. "Why it moved" (recommended)** | nav "Why it moved"; H1 "Why is crypto down today?" (the 8.1 search title, unchanged); coin block "Why Bitcoin moved" | "Checked: **Likely**. US CPI came in hot at 8:30 AM ET; Bitcoin fell 1.9% in the next 40 minutes." | The reader's own words; matches the queries `/today/` and the coin doors already target; works as an app tab | Plain, so the brand lives in the verdict line, not the name |
| B. "The Why Check" | nav "Why Check" | "Why Check: Likely" | Carries the brand verb in the name | A coined phrase a reader has to learn; reads as a product, not an answer |
| C. "Move check" | nav "Move check" | "Move check: Likely" | Short; fits a tab bar | "Move" is vague out of context (moving house, a chess move) |

The four verdict grades, as briefed, with the one-line definitions that print beside them:
- **Confirmed**: a primary source states the cause, the timing test passes, and the mechanics agree.
- **Likely**: the timing test passes and the mechanics agree, but no primary source states the cause.
- **Disputed**: credible evidence points two ways (the timing fails, or the mechanics contradict the reported cause).
- **Unclear**: nothing passes the timing test. The page says so: "No reported event lines up with this move."

Alternative wording for the fourth grade, if Jack prefers it to read as a finding rather than a shrug: **"No clear cause"**. Recommended: keep "Unclear" in the badge and print "No reported event lines up with this move" as its sentence.

### 3.2 Big movers

| Option | Label | For | Against |
|---|---|---|---|
| **A. "Big movers" (recommended)** | nav (inside Markets) "Big movers"; block "Today's big movers, checked" | What traders and newcomers both say; one word less than "gainers and losers" | Needs the threshold printed so "big" is defined (it is: section 3.2 of AUDIT.md) |
| B. "Gainers and losers" | "Top gainers and losers" | The CoinGecko/CMC term; strong search phrase | Generic; says nothing about the why, which is the point of difference |
| C. "Movers, checked" | "Movers, checked" | Brand verb, short | "Movers" alone is jargon to a first-time reader |

Recommended: A for the label, and keep "top gainers" and "top losers" in the page title for search ("Crypto top gainers and losers today, with why they moved").

## 4. Every existing section

Recommended option first in each row. "Keep" is a real option and is chosen where the current name already works.

| Today | Option 1 (recommended) | Option 2 | Option 3 | Why the recommendation |
|---|---|---|---|---|
| Markets / The Board (`/pulse`) | **Markets** | Market dashboard | The Board (alone) | "The Board" is the desk's word, not the reader's; "Markets" is what every competitor's reader expects |
| Flows / Whale Watch (`/flows`) | **Whale Watch** | Exchange flows | Big transfers | The brand name is the plain one here: "whale" is common crypto usage; "Flows" is vaguer than the name it labels |
| Charts / Chart Master (`/chartmaster`) | **Charts**; the dated card becomes "**The chart read, Oct 15**" | Technical read | Chart Master (keep) | "Chart Master" is a persona remnant (Program 6 dropped the voice); the read is a description of chart levels and should say so |
| News / Checked (`/news`) | **News** | Checked news | Latest | The brand verb belongs on the badges, which already say "Verified" |
| Brief / The Edition (`/bottom-line`) | **The Brief**, with "**Morning Brief**" and "**Evening Brief**" for the two editions | Daily Brief | The Edition | Matches Jack's cadence line ("The Brief, every morning and evening") and the article titles ("The Evening Brief"); retires "Edition" and "Morning read" from reader copy (internal names may stay) |
| Record / Worth keeping (`/record`) | **Storylines** | Reference | The Record (keep) | The page holds running stories, trackers and lasting pieces; "Storylines" says that, "Worth keeping" does not |
| Learn / The Board explained (`/learn`) | **Learn** | Crypto, explained | Explainers | Fine as is once "The Board" is gone from the subtitle |
| `/today/` "Why crypto moved today" | **Why it moved** (the why feature's front page) | Today | Why crypto moved | Becomes the feature in 3.1; earns a nav slot and a tab |
| `/pulse/movers` "Movers" | **Big movers** | Gainers and losers | Movers | Section 3.2 |
| Home "Moving the market" | **What was reported** | Today's news | The wire | Removes the causal claim (section 1, harm 1) |
| Home "The checked story" | **Top story, checked** | Checked today | The day's checked story | Keeps the verb; says it is one story |
| Home "Where Bitcoin stands" | **Where Bitcoin stands** (keep) | Bitcoin's trend | Bitcoin's position | Already plain |
| Home "The mood" | **Sentiment** | Fear & Greed | Market mood | One gauge, one word readers search |
| "Wire" badge on news items | **Reported** | News wire | Wire (keep) | Pairs with "Verified": a reader sees reported versus verified at a glance |
| "Reads with Stablecoin float" chip | **Related data: Stablecoin supply** | See also | Board reading | Says what the link is |
| "Receipts:" (Record) | **Sources:** | Checked against | Receipts (keep) | One word for sources across the site |
| "Running story" | **Ongoing story** | Developing | Running story (keep) | "Running" is newsroom jargon |
| "Living table" | **Tracker** | Data table | Living table (keep) | Plain and short |
| Board tile "Spot ETF net" | **ETF flows** (subline "spot Bitcoin ETFs, net") | Spot ETF net (keep) | ETF net flow | Matches the Learn page and the query people type |
| Board tile "Whale net" | **Whale flows** | Whale net (keep) | Exchange net flow | Matches Whale Watch |
| Board tile "Leverage, funding annualized" | **Funding rate** | Leverage | Funding | The figure is a funding rate; the label should say so |
| Board tile "Stablecoin float" / `/flows` "Stablecoin buying power" / Learn "stablecoin dry powder" | **Stablecoin supply** (the total) and **Stablecoins onto exchanges** (the flow) | Stablecoin float (keep, and rename the other two to it) | Dry powder | Three names for two different numbers; one name each |
| Board tile "Fear & Greed" | **Fear & Greed** (keep) | Sentiment index | Mood | The index's own name; what readers search |
| Board tile "Network fees" | **Bitcoin fees** | Network fees (keep) | Fees | Says which network |
| Footer "How we work" (`/method`) and "Standards & corrections" (`/standards`) | **How we check** (one page, both merged; `/standards` redirects) | Keep both | Methods and standards | Two pages say nearly the same thing (478 and 433 words); one page, named for the brand's verb |
| "Cold storage" card "Keep it off the exchange" | Keep | Store it safely | Self-custody | Plain already |
| Masthead "Crypto, checked." | Keep | Crypto, checked daily | The why, checked | The tagline is the brand; keep it |
| Home cadence line "The Brief, every morning and evening." | Keep (Jack's words, 14 Oct) | | | Unchanged by this proposal |

## 5. What a rename touches (for the build session, not this one)

- `site_build.NAMES` and `NAV` (one table) and the tab bar list.
- Strings that bypass the table: `home.py` section heads ("The checked story", "Moving the market", "Reads with"), `site_build.py` badges ("Living table", "Running story", "Receipts:"), the Board tile labels in `tile.READINGS`, the `/bottom-line` lede ("Once a day the desk closes its edition"), the morning card eyebrow and `today.stamp_line` ("Morning read", "Evening Edition"), Learn slugs' titles (the slugs stay).
- Canary checks that pin names (`verify_pipeline.py` names checks from 6.3) move with them; each one is seen to fail on the old name first (U-9).
- No URL changes. New paths only for new features: `/why/` may alias `/today/` (recommended: keep `/today/` as the canonical URL, since 8.1's search work points at it).

## 6. The app's names (for the later program)

- App Store name: **GoCheckMy Crypto**; subtitle: **Why crypto moved, checked**.
- Tabs: **Why it moved**, **Markets**, **Big movers**, **Whale Watch**, **Brief**. Watchlist lives inside Markets.
- Push titles lead with the coin and the grade: "Bitcoin down 4.1%: Likely, US CPI at 8:30 AM ET".

## 7. Jack's picks

1. The why feature: A "Why it moved" (recommended), B "The Why Check", or C "Move check".
2. The fourth grade: "Unclear" (recommended) or "No clear cause".
3. Movers: A "Big movers" (recommended), B "Gainers and losers", or C "Movers, checked".
4. Section 4's table: accept the recommended column whole, or mark the rows to change.
