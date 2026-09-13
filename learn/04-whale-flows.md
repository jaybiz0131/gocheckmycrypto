---
title: Whale flows: what coins moving onto and off exchanges mean
slug: /learn/whale-flows
board_tile: whale_flows
meta_description: What Whale Watch measures, why coins moving onto exchanges usually mean selling pressure, why it is not always so, and how to read the 24-hour flow.
target_queries: bitcoin exchange inflows meaning; whale alert explained; crypto whale movements; exchange outflows bitcoin
related_tiles: etf_flows; stablecoins; leverage
read_time: 5 min
byline: The GoCheckMyCrypto desk
live_embed: board.whale_flows (net 24h flow, direction, largest single transfer, as-of stamp, source line). Template slot, filled at build.
build_note: RESOLVED 2026-09-13. Threshold confirmed against whale_flows.py FALLBACK_MIN_USD = 50_000_000; copy now says $50 million, per ruling 0.4.
---

# Whale flows: what coins moving onto and off exchanges mean

*Every large transfer on the blockchain is public. Whale Watch sorts the biggest ones into two piles, coins moving onto exchanges and coins moving off, and the Board shows the net. Here is why that direction matters and when it fools people.*

[LIVE FROM THE BOARD: net 24-hour flow, direction, largest single transfer, as-of stamp, source. Link: See it on the Board.]

## What it measures

A whale is anyone moving a large amount of coins at once. Whale Watch tracks transfers above $50 million and classifies each one by where it went.

Onto an exchange: the coins moved from a private wallet into an exchange wallet. An exchange is where coins are sold, so this is coins being positioned to sell.

Off an exchange: the coins moved from an exchange into a private wallet. Coins in private storage cannot be sold until they move again, so this is coins being positioned to hold.

The Board nets the two over the last 24 hours. A net figure "onto exchanges" means more coins arrived at exchanges than left. A net figure "off exchanges" means the reverse.

## Why it moves the market

Coins have to be on an exchange before they can be sold there. A wave of large deposits does not guarantee selling, but it makes selling possible, and it often precedes it by hours or days. A wave of withdrawals means the opposite: the coins are being taken out of reach, which shrinks the supply that could hit the market quickly.

Over weeks, the balance of coins held on exchanges is one of the cleaner supply signals in crypto. When it falls steadily during a rally, the rally has less stock available to sell into it. When it rises steadily during a rally, sellers are getting ready.

## How to read today's number

Direction and persistence matter more than any single transfer. One $200 million deposit is an event to note; three days of net deposits is a pattern to respect.

The most useful read is to put this tile beside the ETF flows tile. ETF inflows are large buyers arriving; whale deposits are large sellers arriving. When both are heavy on the same day, the market is absorbing real supply with real demand, and price often moves less than either number suggests. When ETF flows go quiet and whale deposits continue, there is less demand to meet the supply.

## What it does not tell you

Not every deposit is a sale. Exchanges shuffle coins between their own wallets, custodians move client holdings for operational reasons, and the funds behind the spot ETFs move coins to and from their custodians in size. Whale Watch filters the transfers it can identify as internal, but no filter is perfect, and a single very large transfer should be treated as unexplained until it repeats.

The other blind spot is trades that never touch the chain. Large holders often sell through over-the-counter desks that settle privately. Those sales are real, and they are invisible here.

## Where the data comes from

Transfers come from the Whale Alert public feed, which watches the major chains for large movements and labels known exchange and custodian addresses. The Board reads it at every site build. Whale Watch is labeled market data, not news, because it reports what moved and where, never why.

## Related on the Board

Spot ETF flows: the buyer side of the same day. Read the two together.

Stablecoin dry powder: the dollars sitting on exchanges that could meet incoming coins.

Leverage: heavy deposits into a highly leveraged market are the setup for sharp moves.

[Back to the Board]

*This page is education, not advice. Do your own research.*
