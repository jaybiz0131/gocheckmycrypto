#!/usr/bin/env python3
"""
venues.py: ONE name table for the exchanges this desk prints (4 October 2026).

Whale Alert names OKX by its old name, "okex", and the desk printed it three ways:
OKX on the Board, "Okex" on Whale Watch, and whatever the model echoed in an Edition.
Every surface now spells an exchange from this table: whale_flows writes the table's
name into flows.json, site_build renders through it, and the house-style pass rewrites
the old spelling in stored copy. "Okex" is never printed.
"""

import re

VENUE_NAMES = {
    "binance": "Binance", "binance us": "Binance.US", "bitfinex": "Bitfinex",
    "bitget": "Bitget", "bitmex": "BitMEX", "bitstamp": "Bitstamp",
    "bithumb": "Bithumb", "bybit": "Bybit", "coinbase": "Coinbase",
    "coinbase institutional": "Coinbase Institutional", "crypto.com": "Crypto.com",
    "deribit": "Deribit", "gate.io": "Gate.io", "gemini": "Gemini", "htx": "HTX",
    "huobi": "Huobi", "kraken": "Kraken", "kucoin": "KuCoin", "mexc": "MEXC",
    "okx": "OKX", "okex": "OKX", "upbit": "Upbit", "tether treasury": "Tether Treasury",
    "unknown wallet": "Unknown wallet", "unknown": "Unknown",
}

# Old names that must not survive in prose, whatever their case.
_RENAMED = re.compile(r"\bok-?ex\b", re.IGNORECASE)


def fix_names(text):
    """Rewrite retired exchange names in a piece of copy. Strings only."""
    if not isinstance(text, str) or not text:
        return text
    return _RENAMED.sub("OKX", text)


def canonical(owner):
    """The table's name for a feed owner string, or the string unchanged."""
    t = " ".join(str(owner or "").split())
    return VENUE_NAMES.get(t.lower(), t)
