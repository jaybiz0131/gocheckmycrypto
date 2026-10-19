fixtures/movers: real recorded data for Program 9, Sprint 9.4 (movers.py, the market-move trigger in
watcher.py, scripts/sprint94_test.py). Nothing here is edited. Every case in the tests that changes one of
these records by hand says SYNTHETIC beside it.

pulse_2026-10-16T1216Z.json and wire_2026-10-16T1216Z.json
  site/data/pulse.json and site/data/wire.json as committed at 9c8af54 ("morning: read 2026-10-16, boards
  and wire refreshed"), the Board generated 2026-10-16T12:16:53Z. Copied with `git show`, unchanged. Ten
  top-100 coins moved 10% or more over its 24 hours (TIA +30.60%, INJ +25.29%, ZRO +20.59%, ETHFI +15.53%,
  ARB, APT, WLD, NEAR, ZEC, FIL), the day AUDIT.md section 1.2 cites.

history_answers_recorded_2026-10-19.json
  CoinGecko's /coins/{id}/market_chart?vs_currency=usd&days=365 answer for each of those coins, read
  Monday October 19 2026 between about 4:33 and 4:39 PM EDT, keyed by URL. aptos answered HTTP 429 five
  times and is absent, so the gate leaves APT out and says so, as it would on a live run whose history
  read failed. The tests build a history directory from these answers by history.py's own rules
  (movers._history_root) beside data/history/bitcoin.json as committed; the gate reads only the closes
  before the window's Eastern day (October 15), which the answers carry unchanged.

sources_2026-10-16T1216Z.json
  Every answer the movers step's sources gave for that Board's window, recorded Monday October 19 2026,
  4:45 PM EDT (recorded_utc 2026-10-19T20:45:15Z) by
  `python3 movers.py --record PULSE WIRE HISTORY_ANSWERS OUT`, through the same fetch code the run uses.
  - Prices: CoinGecko market_chart?days=1 reaches only the last 24 hours and Kraken its last 720
    five-minute candles, so neither was asked for this window and each record says so; Coinbase, OKX and
    Binance's data-api mirror were asked, and a venue's series is kept only when its move agrees with
    the Board's within 3 points.
  - The listing feeds (Binance, OKX, KuCoin, Bitget, Kraken's blog) hold the notices still in each feed
    on October 19; none of them names TIA, INJ, ZRO or ETHFI inside the window.
  - CoinMarketCap's token-unlock events: TIA's list carries an unlock at 2026-10-16T00:00Z, inside the
    window. ETHFI's CoinGecko id (ether-fi) is CoinMarketCap's slug for another token (EETH), so its
    unlocks are not read, and the record says why.
  - CoinGecko's daily volumes (days=8, interval=daily) answered HTTP 429 for every coin when recorded,
    so the volume against the 7-day average reads "not read" in these records.
  - Yahoo's 5-minute bars answered for every cross-asset but FBTC (HTTP 429).

board_raw.json
  A Board read Monday October 19 2026, 4:30 PM EDT (2026-10-19T20:30:40Z), by market_pulse.py's own
  section_movers() and section_market() (one CoinGecko /coins/markets read, coin_screen's cached verdicts
  applied), with CoinGecko's 365-day answers for its two top-100 coins past 10% (PUMP +11.46%, VVV
  +13.74%). Neither passes the gate (each moved under 2.5 times its 30-day daily volatility): this is the
  recorded day with no coin past the line, and the tests read its log.

watcher_reads_recorded.json
  The watcher's two market reads, recorded Monday October 19 2026, 4:42 PM EDT: Bitcoin's
  market_chart?days=1 and the Top 100 /coins/markets with price_change_percentage=1h,24h.
