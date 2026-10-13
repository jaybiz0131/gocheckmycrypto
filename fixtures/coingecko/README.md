# Recorded CoinGecko market_chart answers (Sprint 6.4 chart tests)

`<id>-1.json`, `-7.json` and `-365.json` are recorded answers. `<id>-565.json` is the 365-day recording with 200
SYNTHETIC days (a mean-reverting walk around the first close) prepended, because the sandbox these were made in was
rate-limited by CoinGecko and could not record a 565-day answer. The last 365 days are the recording; the 200
synthetic days exist only so both moving averages have a value for every day the 1Y window shows. Never read a
price off the first 200 days of a `-565` file.
