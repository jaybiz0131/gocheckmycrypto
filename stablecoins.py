#!/usr/bin/env python3
"""stablecoins.py: which coins are stablecoins (6 October 2026).

A stablecoin does not move, so it is never a mover; the Top 100 shows it and marks it.
The list is DefiLlama's (stablecoins.llama.fi/stablecoins, keyless), the source the desk
already reads for the stablecoin float, kept in data/stablecoins.json by CoinGecko id with
the endpoint and the date it was read. It costs the build no request: the desk refreshes
it monthly, at the first session of the month, with the unlocks file.

    python3 stablecoins.py --refresh     # read DefiLlama now and rewrite the file
"""
import datetime as _dt
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "stablecoins.json")
ENDPOINT = "DefiLlama stablecoins.llama.fi/stablecoins"
URL = "https://stablecoins.llama.fi/stablecoins?includePrices=false"


def load(path=PATH):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {"source": ENDPOINT, "read_utc": "", "gecko_ids": []}
    return d


def ids(path=PATH):
    return set(load(path).get("gecko_ids") or [])


def from_answer(answer, read_utc):
    pa = (answer or {}).get("peggedAssets") or []
    return {"source": ENDPOINT, "read_utc": read_utc,
            "note": "Every pegged asset DefiLlama lists with a CoinGecko id. Refreshed "
                    "monthly by the desk.",
            "gecko_ids": sorted({a["gecko_id"] for a in pa if a.get("gecko_id")})}


def refresh(path=PATH):
    req = urllib.request.Request(URL, headers={"User-Agent": "GoCheckMyCrypto/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        answer = json.load(r)
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = from_answer(answer, now)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=0)
        fh.write("\n")
    print(f"stablecoins: {len(d['gecko_ids'])} ids from {ENDPOINT}, read {now}")


if __name__ == "__main__":
    if "--refresh" in sys.argv[1:]:
        refresh()
    else:
        d = load()
        print(f"{len(d.get('gecko_ids') or [])} ids, {d.get('source')}, read {d.get('read_utc')}")
