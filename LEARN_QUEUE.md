# The Learn tier: publishing queue

Approved by the owner 2026-07-29. The governing rule is in CHARTER.md under LEARN TOPIC
SELECTION: topics are chosen by reader need first, and only then do we ask whether a
product is honestly part of the answer. Most of the time it is not.

**Zero of the ten pieces below carry an affiliate link, and that is ratified, not an
oversight.** Three of them could carry one. All three were refused. With the three
published explainers that puts the tier at 3 link-carrying pieces out of 13, which is the
ratio the doctrine is aiming at: the pieces that ask for nothing are what make the ones
that ask believable.

## How each topic was chosen

Two sources, weighted toward the first.

**Our own surfaces**, because that is demand we can actually see. Every board's rendered
copy was read for terms used without explanation. Several boards already teach themselves
well (Sentiment 101, Network 101, Dry powder 101 are genuinely good). The real gaps are
Whale Watch, which assumes the reader knows what on-chain flow data is and why a transfer
to an exchange means anything, and the stablecoins board, which explains the fuel-gauge
metaphor and never says what backs the dollar.

**Primary sources on recurring loss patterns**, for the safety pieces: FBI/IC3 on address
poisoning and drainer contracts, the Uniform Law Commission and ABA on fiduciary access to
digital assets.

Discarded: general "beginner crypto questions" search results, which are near-worthless
affiliate listicles recycling each other. One claimed seed phrases are being replaced in
2026 by MPC and passkeys. That is a vendor talking point, not a durable fact, and a good
illustration of what search-demand data drags in.

Excluded as news, not Learn: privacy-coin moves, ETF flow direction, the status of any
specific bill, whether a death cross is bearish. Anything tied to a price move, a bill's
progress, or one company's news belongs to the desk.

---

## 1. How to read on-chain flow data (BUILD FIRST)

**Reader question.** "Everyone says whales are moving coins to exchanges. So what?"
**Durability.** The mechanic of an exchange deposit versus a self-custody withdrawal does
not change when the price does.
**Link.** No. Nothing to sell. This is our own board's manual.
**Home.** Whale Watch, contextual sentence under the net-flow chart.
**Sourcing.** Mostly our own methodology, which is the honest version anyway: what
"exchange-size" means, why "unknown wallet" appears, what the 13-week baseline is. Any
claim that flows predict price needs care, because the evidence is weak and the page
should say so.
**Why first.** Biggest gap between what our best board shows and what a new reader can get
from it, and it carries no link, which is the doctrine working as intended.

## 2. Seed phrases and passphrases, properly explained

**Reader question.** "Where am I supposed to put these twelve words?"
**Durability.** Deterministic key derivation is a standard, not a product cycle.
**Link.** No, and this is a deliberate refusal. Metal backup plates are a real category and
both partners sell them. This piece has to say never enter your phrase anywhere, never
photograph it, never put it in a password manager. A page that tells you to trust nothing
and then sells you something has spent its own credibility inside one scroll.
**Home.** Cold storage, where the seed is first mentioned. Also counterfeit devices.
**Sourcing.** BIP-39 for wordlist and checksum. The passphrase section needs care: a
passphrase creates a genuinely separate wallet, and getting that wrong loses funds.

## 3. How to verify a receiving address before sending

**Reader question.** "How do I know this is really the right address?"
**Durability.** Address poisoning works because wallets truncate. A UI fact, not a market
fact.
**Link.** No.
**Home.** Whale Watch, next to the "unknown wallet" label. Counterfeit devices, in the
verification section.
**Sourcing.** Strong and primary. IC3 documents the mechanic precisely: attackers use an
address whose first and last characters match one you have used, because the middle is
hidden. Rare case where the check is simple and the source is a federal agency.

## 4. What stablecoins are and what actually backs them

**Reader question.** "Is my USDT actually a dollar?"
**Durability.** The categories (fiat-reserved, overcollateralised crypto, algorithmic)
outlive any issuer.
**Link.** No.
**Home.** The stablecoins board, which says "USD-pegged float" and never says pegged to
what, by whom, backed how.
**Sourcing.** Issuer attestations, plus the statutory framework where it is settled.
**Durability flag.** The US stablecoin regulatory picture is the likeliest thing here to
date. Write the mechanics as the spine and quarantine the regulatory paragraph so it can
be updated without rewriting the piece.

## 5. Custody versus ownership on an exchange

**Reader question.** "It's in my exchange account, so it's mine, right?"
**Durability.** "Not your keys, not your coins" is a claim about creditor status, and
bankruptcy law moves slowly.
**Link.** No. This is the refusal most open to challenge, and it was put to the owner
explicitly and upheld. The obvious move is a hardware-wallet link, and cold storage
already does that job properly. Two pages making the same recommendation with the same
links reads as a funnel rather than two answers. Cross-link to cold storage instead.
**Home.** Whale Watch off-exchanges card, alongside cold storage. Exchange coverage.
**Sourcing.** Celsius and FTX customer-property rulings, which are genuinely instructive.

## 6. Gas fees and why transactions cost what they do

**Reader question.** "Why did it cost forty dollars to move a hundred?"
**Durability.** Block space is a scarce good sold at auction. Permanent.
**Link.** No.
**Home.** The Bitcoin network board, which shows sat/vB and assumes you know what that is.
**Sourcing.** EIP-1559 for the base-fee mechanic, mempool data for Bitcoin. No current fee
levels in the copy.

## 7. Crypto and inheritance

**Reader question.** "If I die, can my family get to this?"
**Durability.** Estate planning is the slowest-moving area on this list.
**Link.** No, absolutely not, and this is the strongest refusal in the queue. There is an
industry of inheritance-vault products that would pay for placement here, and taking it
would be the failure rule in a different costume: monetising someone thinking about their
own death and their family's loss. Not at any rate.
**Home.** Cold storage, in the self-custody-failure-mode section, which already says lost
seeds destroy more crypto than exchange failures do.
**Sourcing.** RUFADAA, adopted in most states, plus the gap it does not close: a fiduciary
can be legally authorised and still unable to open a wallet, because authorisation is not
a key. That distinction is the whole piece.

## 8. Who regulates what in US crypto (HOLD)

**Reader question.** "Who do I even complain to?"
**Durability.** Weakest on the list and the reason to hold it. The agency perimeter has
been actively contested; a plain-language map written today could be materially wrong in a
year, which fails our own durability filter.
**Link.** No.
**Home.** Method or Standards.
**Sourcing.** Agency primary material only. If built, structure it around the durable spine
(what each agency's jurisdiction is *for*) and keep current allocations in a small, clearly
dated section.

## 9. What a bridge is and why they get exploited

**Reader question.** "How do I move this to another chain, and is that safe?"
**Durability.** The custody model that makes bridges fragile is architectural.
**Link.** No, and note the failure rule applies independently: this piece is largely about
exploits and losses, so no money path attaches regardless of what else were true.
**Home.** Bridge-exploit coverage, contextual.
**Sourcing.** Post-mortems from the major bridge exploits, which are public and technical.

## 10. A plain-language glossary (BUILD LAST)

**Reader question.** "What does any of this mean?"
**Durability.** Yes, but it is infrastructure rather than an article.
**Link.** No.
**Home.** Every board.
**Note.** Build it last, from vocabulary the first nine actually used. Built first it is a
list of guesses; built last it is an index that can deep-link to the pieces that explain
each term properly.

---

## Build order

**1, 3, 2** first. Flows because it closes the biggest gap between our best board and a new
reader, and makes Whale Watch worth returning to. Address verification next because the
check is simple, the source is federal, and it is the piece most likely to prevent an
actual loss. Seed phrases third because it completes the custody trilogy with cold storage
and counterfeit devices, which currently cross-link into a gap.

Then 4 and 5, then 6 and 7, then 9, then 10. Number 8 only if the regulatory perimeter
settles.
