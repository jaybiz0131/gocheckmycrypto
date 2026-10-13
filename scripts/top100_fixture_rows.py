#!/usr/bin/env python3
"""
top100_fixture_rows.py: two SYNTHETIC Top 100 rows, rendered by the real row renderer, for
coin_pages_browser.mjs. Prints one JSON object {"price": <tr html>, "name": <tr html>}.

SYNTHETIC, and only for the layout test, never for a screenshot Jack approves:
  price  a coin priced $0.0000003682, the 13-character string a micro-cap carried on production
         on 13 October 2026 (7.2 px between price and 24h pill before Sprint 6.5). The Top 100's
         100 real rows in the build are tested as they are; this row adds the case the recorded
         data of the day does not contain.
  name   one word far wider than the coin column, so the ellipsis path is exercised on purpose.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def rows():
    import site_build as sb
    price = {"symbol": "FIXP", "name": "Micro Cap Fixture", "price": 0.0000003682, "chg_24h_pct": -12.34,
             "rank": 101, "spark7d": [3, 2, 3, 1, 2, 1, 1], "mcap_usd": 1.0e6, "volume_24h": 1.0e4}
    name = {"symbol": "FIXN", "name": "Supercalifragilisticexpialidocious Token", "price": 1.5, "chg_24h_pct": 1.0,
            "rank": 102, "spark7d": [1, 2, 3, 4, 5, 6, 7], "mcap_usd": 1.0e6, "volume_24h": 1.0e4}
    return {"price": sb._top100_rows([price]), "name": sb._top100_rows([name])}


if __name__ == "__main__":
    print(json.dumps(rows()))
