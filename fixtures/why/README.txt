fixtures/why: real recorded data for Program 9, Sprint 9.2 (why_evidence.py, scripts/sprint92_test.py).

sources_2026-10-14T2343Z.json and sources_2026-10-15T2343Z.json
  Every answer the evidence's sources gave for the 24 hours ending at the Board's reading at the
  14 and 15 October Editions (pulse.json generated_utc at 7d9008b and 94dd6af: 2026-10-14T23:43:23Z
  and 2026-10-15T23:43:27Z). Recorded Sunday October 18 2026, about 12:50 PM EDT, by
  `python3 why_evidence.py --record END_UTC OUT`, through the same fetch code the run uses; each file
  carries its own recorded_utc and recorded_et. Keyed by URL, the answer as the source sent it.
  - Prices: Coinbase and OKX 5-minute candles. CoinGecko market_chart?days=1 reaches only the 24 hours
    before the moment it is read, and Kraken keeps its last 720 five-minute candles; neither reaches
    these days, so neither was asked, and each record names them as not read. The 5-minute data did
    reach these days (Coinbase, OKX), so no coarser granularity was needed.
  - OKX open interest is the hourly series (its 5-minute series reaches back about 48 hours).
  - OKX liquidations keep only the latest 100 orders (back to the morning of October 18 when read),
    so the onset hours of October 14 and 15 have no liquidation reading; the pages say so.
  - The SEC, CFTC and Fed press feeds were read on October 18, so they hold the items still in each
    feed then. All three still reached back past the start of both windows; a feed that does not
    is noted in the record with how far back it reaches.
  - Two long histories are trimmed to 7 days either side of the window to keep the files readable:
    DefiLlama's hack list and its total stablecoin series. The entries kept are the source's own,
    unchanged.

wire_2026-10-14T2343Z.json, wire_2026-10-15T2343Z.json
  site/data/wire.json as committed by the 14 and 15 October Editions (git show 7d9008b and 94dd6af).
  The 15 October file still carries the producer-price line Sprint 9.1 found unsupported by its own
  source; it is kept as the wire stood, and the tests use it only for its time (it was stamped
  04:25Z, before the 8:30 AM ET release, so it cannot be that release's first report).

pulse_2026-10-15T2343Z.json, flows_2026-10-15T2343Z.json
  site/data/pulse.json and flows.json as committed by the 15 October Edition (git show 94dd6af), for
  the Bitcoin and Ether page cases.

Cases in scripts/sprint92_test.py marked SYNTHETIC build a small series by hand to reach a rule
these two days do not reach; they are labeled as such (Jack, 13 October 2026) and use no figure from
these files.
