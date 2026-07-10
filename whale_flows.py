#!/usr/bin/env python3
"""
whale_flows.py: follow the money, not the feed.

A scrolling list of individual whale transfers is noise. The signal is the AGGREGATE: are
whales, on net, moving coins ONTO exchanges (which historically precedes selling) or OFF
exchanges into self-custody (accumulation)? This script classifies each large transfer by the
owner_type of its endpoints and rolls them up into a higher-perspective view per asset, plus
the biggest single moves onto exchanges.

CLASSIFICATION (Whale Alert marks known exchange wallets with owner_type == "exchange"):
  wallet/unknown -> exchange   = INFLOW  (money onto an exchange; potential sell pressure)
  exchange -> wallet/unknown   = OUTFLOW (money off an exchange; accumulation / self-custody)
  exchange -> exchange         = INTERNAL (ignored; not directional signal)
  wallet -> wallet             = WALLET  (ignored; no exchange involved)
  net_usd per asset = outflow - inflow   (positive = net leaving exchanges = accumulation)

This is a HEURISTIC and market data, not news and not advice. Exchange labels come from Whale
Alert; unlabeled wallets are treated as non-exchange. The site frames it as such.

OUTPUT
  out/whale_flows.json          full analysis (runtime)
  site/data/flows.json          the snapshot the site renders (a board, refreshed each run)

USAGE
  python3 whale_flows.py                      # live: Whale Alert API (needs WHALE_ALERT_API_KEY)
  python3 whale_flows.py --fixture F          # analyze a saved transactions file (tests)
  python3 whale_flows.py --window 24          # lookback hours (default from config)
  python3 whale_flows.py --example            # write the snapshot flagged example (illustrative)
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

import common

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "whale_flows.json")
SITE_DATA = os.path.join(HERE, "site", "data", "flows.json")
UA = "CryptoCronkite-WhaleFlows/1.0"


def classify(txn):
    ft = (txn.get("from", {}) or {}).get("owner_type", "")
    tt = (txn.get("to", {}) or {}).get("owner_type", "")
    f_ex, t_ex = ft == "exchange", tt == "exchange"
    if t_ex and not f_ex:
        return "inflow"
    if f_ex and not t_ex:
        return "outflow"
    if f_ex and t_ex:
        return "internal"
    return "wallet"


# Stablecoins invert the signal: a stablecoin moving ONTO an exchange is buying power arriving
# (dry powder), not sell pressure. So we score the sell-pressure/accumulation signal on volatile
# assets only, and report stablecoin exchange inflow separately as incoming buying power.
STABLES = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "GUSD"}


def analyze(txns, window_hours, top_assets=6, top_moves=6, example=False, date=None):
    assets = {}
    vol_in = vol_out = 0.0
    stable_in = stable_out = 0.0
    counted = 0
    inflow_moves = []
    for t in txns:
        kind = classify(t)
        sym = (t.get("symbol") or "?").upper()
        usd = float(t.get("amount_usd") or 0)
        if kind in ("internal", "wallet"):
            continue
        counted += 1
        is_stable = sym in STABLES
        if kind == "inflow":
            to = (t.get("to", {}) or {}).get("owner") or "unknown exchange"
            move = {"symbol": sym, "amount": float(t.get("amount") or 0), "usd": usd,
                    "to": to, "from": (t.get("from", {}) or {}).get("owner") or "unknown wallet",
                    "blockchain": t.get("blockchain", ""), "hash": t.get("hash", ""),
                    "stable": is_stable}
            inflow_moves.append(move)
        if is_stable:
            if kind == "inflow":
                stable_in += usd
            else:
                stable_out += usd
            continue
        # volatile asset: this is the directional sell-pressure / accumulation signal
        a = assets.setdefault(sym, {"symbol": sym, "inflow_usd": 0.0, "outflow_usd": 0.0})
        if kind == "inflow":
            a["inflow_usd"] += usd
            vol_in += usd
        else:
            a["outflow_usd"] += usd
            vol_out += usd

    by_asset = []
    for a in assets.values():
        a["net_usd"] = round(a["outflow_usd"] - a["inflow_usd"])  # + = net off exchanges
        a["inflow_usd"] = round(a["inflow_usd"])
        a["outflow_usd"] = round(a["outflow_usd"])
        by_asset.append(a)
    by_asset.sort(key=lambda x: abs(x["net_usd"]), reverse=True)
    by_asset = by_asset[:top_assets]

    inflow_moves.sort(key=lambda m: m["usd"], reverse=True)
    net = vol_out - vol_in  # positive = net off exchanges (accumulation)
    direction = "off exchanges" if net >= 0 else "onto exchanges"

    return {
        "example": example,
        "generated": date or "undated",
        "window_hours": window_hours,
        "txn_count": counted,
        "volatile": {
            "inflow_usd": round(vol_in), "outflow_usd": round(vol_out),
            "net_usd": round(net), "direction": direction,
        },
        "stablecoins": {
            "inflow_usd": round(stable_in), "outflow_usd": round(stable_out),
            "net_buying_power_usd": round(stable_in - stable_out),
        },
        "by_asset": by_asset,
        "top_inflows": inflow_moves[:top_moves],
        "note": ("Heuristic from Whale Alert exchange labels. For volatile assets, coins moving "
                 "onto exchanges can precede selling and coins moving off suggests accumulation "
                 "or self-custody. Stablecoins are the opposite: onto an exchange is buying power "
                 "arriving, so they are scored separately. Market data, not news, not advice."),
    }


def load_from_api(cfg, window_hours):
    wa = cfg["sources"].get("whale_alert", {})
    key = os.environ.get(wa.get("enabled_if_env", "WHALE_ALERT_API_KEY"), "")
    if not key:
        return None
    start = int((datetime.now(timezone.utc) - timedelta(hours=window_hours)).timestamp())
    params = {"api_key": key, "min_value": str(wa.get("min_value_usd", 5000000)), "start": str(start)}
    url = wa["url"] + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.load(resp)
    return data.get("transactions", []) or []


def run(fixture=None, window=None, example=False):
    cfg = common.load_config()
    window_hours = window or cfg.get("whale_flows", {}).get("window_hours", 24)
    top_assets = cfg.get("whale_flows", {}).get("top_assets", 6)
    top_moves = cfg.get("whale_flows", {}).get("top_moves", 6)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if fixture:
        txns = json.load(open(fixture, encoding="utf-8")).get("transactions", [])
        example = True  # a fixture-derived board is always illustrative
    else:
        txns = load_from_api(cfg, window_hours)
        if txns is None:
            common.gh("warning", "whale_flows: no WHALE_ALERT_API_KEY -> skipping (no board written). "
                                 "Set the key, or run with --fixture for a preview.")
            return 0

    result = analyze(txns, window_hours, top_assets, top_moves, example=example, date=date)
    common.write_out(os.path.basename(OUT), result)
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    json.dump(result, open(SITE_DATA, "w", encoding="utf-8"), indent=2)
    tag = " [EXAMPLE]" if result["example"] else ""
    v = result["volatile"]
    print(f"whale_flows{tag}: {result['txn_count']} exchange-relevant transfers, volatile net "
          f"${v['net_usd']:,} {v['direction']}, stablecoin buying power "
          f"${result['stablecoins']['net_buying_power_usd']:,} -> {os.path.relpath(SITE_DATA)}")
    return 0


def main():
    argv = sys.argv[1:]
    fixture = argv[argv.index("--fixture") + 1] if "--fixture" in argv else None
    window = int(argv[argv.index("--window") + 1]) if "--window" in argv else None
    example = "--example" in argv
    sys.exit(run(fixture=fixture, window=window, example=example))


if __name__ == "__main__":
    main()
