fixtures/movers: real recorded data for Program 9, Sprint 9.4 (movers.py, the market-move trigger in
watcher.py, scripts/sprint94_test.py). Nothing here is edited. Every case in the tests that changes one of
these records by hand says SYNTHETIC beside it.

pulse_2026-10-16T1216Z.json and wire_2026-10-16T1216Z.json
  site/data/pulse.json and site/data/wire.json as committed at 9c8af54 ("morning: read 2026-10-16, boards
  and wire refreshed"), the Board generated 2026-10-16T12:16:53Z. Copied with `git show`, unchanged. Twelve
  rows of its Top 100 (its 100 places, as the Top 100 page and the coin pages number them) moved 10% or more
  over its 24 hours: TIA +30.60%, INJ +25.29%, ZRO +20.59%, ETHFI +15.53%, ARB, APT, WLD, NEAR, ZEC, FIL,
  PENDLE +11.20% (place 100) and SEI +10.10% (place 96), the day AUDIT.md section 1.2 cites.

history_answers_recorded_2026-10-19.json
  CoinGecko's /coins/{id}/market_chart?vs_currency=usd&days=365 answer for each of those twelve coins, keyed
  by URL, read Monday October 19 2026: nine between about 4:33 and 4:39 PM EDT, and aptos, sei-network and
  pendle at about 6:05 PM EDT (aptos had answered HTTP 429 five times at 4:39 PM; sei-network and pendle were
  added when review 1 moved the gate onto the Board's own Top 100 places). The tests build a history
  directory from these answers by history.py's own rules (movers._history_root) beside
  data/history/bitcoin.json as committed; the gate reads only the closes before the window's Eastern day
  (October 15), which the answers carry unchanged. On these, TIA, INJ, ZRO, ETHFI and PENDLE pass the gate and
  the other seven fail its volatility leg. A coin left out for history is reached only by a case marked
  SYNTHETIC that removes its stored closes.

sources_2026-10-16T1216Z.json
  Every answer the movers step's sources gave for that Board's window, recorded Monday October 19 2026,
  6:07 PM EDT (its recorded_utc) by
  `python3 movers.py --record PULSE WIRE HISTORY_ANSWERS OUT`, through the same fetch code the run uses.
  - Prices: CoinGecko market_chart?days=1 reaches only the last 24 hours and Kraken its last 720
    five-minute candles, so neither was asked for this window and each record says so; Coinbase, OKX and
    Binance's data-api mirror were asked, and a venue's series is kept only when its move agrees with
    the Board's within 3 points.
  - The listing feeds (Binance, OKX, KuCoin, Bitget, Kraken's blog, and Coinbase Exchange's status
    history, read since review 1) hold the notices still in each feed on October 19; none of them names
    any of the five movers inside the window.
  - CoinMarketCap's token-unlock events: TIA's list carries an unlock at 2026-10-16T00:00Z, inside the
    window. ETHFI's CoinGecko id (ether-fi) is CoinMarketCap's slug for another token (EETH), so its
    unlocks are not read, and the record says why.
  - CoinGecko's daily volumes (days=8, interval=daily): HTTP 429 for TIA, ZRO, ETHFI and PENDLE; INJ's
    answer reached only 4 days before this past window (a days=8 read made three days later), so the
    volume against the 7-day average reads "not read" in these records, each with its own reason.
  - Yahoo's 5-minute bars answered HTTP 429 for ES=F, DX-Y.NYB, ^TNX, ZT=F, ^VIX, IBIT and FBTC; the
    others answered.

board_raw.json
  A Board read Monday October 19 2026, 4:30 PM EDT (2026-10-19T20:30:40Z), by market_pulse.py's own
  section_movers() and section_market() (one CoinGecko /coins/markets read, coin_screen's cached verdicts
  applied), with CoinGecko's 365-day answers for the coins past 10% in it: PUMP +11.46% and VVV +13.74%,
  read at 4:30 PM, and CRV +10.13% (place 81 of the Board's Top 100, outside CoinGecko's top 100), read at
  6:20 PM EDT and stamped in added_utc after review 1 moved the gate onto the Board's own places. None
  passes the gate (each moved under 2.5 times its 30-day daily volatility): this is the recorded day with no
  coin past the line, and the tests read its log.

watcher_reads_recorded.json
  The watcher's two market reads, recorded Monday October 19 2026, 4:42 PM EDT: Bitcoin's
  market_chart?days=1 and the Top 100 /coins/markets with price_change_percentage=1h,24h.
