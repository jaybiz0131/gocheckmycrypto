# Recorded CoinGecko market_chart answers (coin chart tests)

All of these are recorded answers from CoinGecko's public API. None is synthetic. Nothing Jack approves
rests on invented data (his ruling of Tuesday 13 October 2026).

| File | Request | Recorded |
|---|---|---|
| `bitcoin-365.json` | `/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily` | Tue 13 Oct 2026, 3:18 PM EDT (19:18Z), sprint 6.5 session |
| `ethereum-365.json` | same, `ethereum` | Tue 13 Oct 2026, 3:20 PM EDT (19:20Z) |
| `aptos-365.json` | same, `aptos` | Tue 13 Oct 2026, 3:21 PM EDT (19:21Z) |
| `<id>-1.json`, `<id>-7.json` | `days=1`, `days=7` | Sprint 6.4 (13 Oct 2026), recorded from the same API |

Each 365 file has 366 daily points, 14 Oct 2025 to 13 Oct 2026, no gap longer than one day, with `prices`,
`market_caps` and `total_volumes`. They are what the page's one history request returns for 1M and 1Y.

Sprint 6.4's `<id>-565.json` files (the 365-day recording with 200 SYNTHETIC days prepended) are deleted. The
page no longer asks for 565 days. A 50-day or 200-day average begins on the first day it has a full window of
real history, so the 200-day line on 1Y begins about 199 days in, and the page says so under the chart.

Synthetic series that remain are in `scripts/coin_pages_browser.mjs` (`shaped`, for the Aptos "windows run in
different directions" color test) and in `scripts/coin_pages_test.py`'s math checks. They are labeled synthetic
where they are defined and never appear in a screenshot for approval.
