#!/usr/bin/env python3
"""
coin_screen.py: keep coins without a real market off the Top 100 board.

WHY THIS EXISTS
  A market capitalization is a price multiplied by a supply. Our Top 100 board took both
  numbers from CoinGecko's markets endpoint and printed the product, which quietly assumes
  that the price came from a market and that the supply is the supply. For some coins
  neither holds, and the board ranked them against Bitcoin anyway.

  Two real examples, both found on the board and both verifiable from CoinGecko's own data:

    WhiteBIT Coin (WBT), which the board ranked #16 at $16.42B. 99.6% of its reported
    volume traded on WhiteBIT, the exchange that issues it, so the price was set where the
    issuer sets it. Worse, the cap was computed on 293,975,916 coins, roughly its TOTAL
    supply, while CoinGecko's own coin page reported 117,907,606 circulating. Same
    provider, two endpoints, 2.49x apart. On the circulating number the cap is $6.59B.

    Figure Heloc (FIGR_HELOC), ranked #9 at $20.60B, with 100% of volume on Figure
    Markets, the issuer's own venue.

WHAT DOES NOT WORK, tested and rejected
  CoinGecko's markets endpoint exposes no self-reported flag; the self_reported_* fields
  are simply absent for these coins, so there is nothing to switch on.

  A cap-to-volume ratio screen is the obvious idea and it is wrong. At >100x it removes 31
  of the top 100 including BNB, and it sweeps in tokenized treasuries and yield stablecoins
  that report no volume because they are REDEEMED rather than traded. Ratio alone cannot
  tell "nobody will buy this" from "this instrument does not trade by design".

WHAT THIS SCREEN ACTUALLY TESTS
  Whether an independent market exists, which is the thing a market cap claims.

    CAPTIVE      one venue accounts for >= 90% of reported volume. The price is whatever
                 that venue says. This separates cleanly on real data: BNB trades on 63
                 venues with its largest at 16.9%, CRO on 46 at 35.6%, Gate's own token on
                 8 at 48.3%, none of them their own exchange. WBT sits at 99.6% on its own.
    UNTRADED     no reported trading at all. Tokenized funds (BlackRock BUIDL, Invesco
                 USTB, the Janus Henderson trusts, Spiko, Circle USYC) are legitimate and
                 are not inflating anything, but their cap is an issuer's book value rather
                 than a traded price, and a Top 100 coins table implies the latter.
    SUPPLY       the markets endpoint's circulating supply exceeds the coin's own detail
                 endpoint by more than 20%. This is what caught WBT.
    ONCHAIN      the claimed circulating supply exceeds what actually exists on chain.
                 The SUPPLY test above compares an aggregator against ITSELF, so it catches
                 an inconsistent listing but not a supply figure that is wrong in a
                 self-consistent way, which is the self-reported cap this screen exists to
                 reject. On-chain total supply is a ceiling that cannot be argued with: a
                 token cannot circulate more than exists. Read keyless from Blockscout.

                 ONLY for tokens that live on Ethereum and nowhere else. A multi-chain
                 token's Ethereum supply is a fraction of its real total, so the comparison
                 would flag honest coins by the dozen; Chainlink alone lists 84 chains. The
                 guard is doing real work rather than being defensive: of Chainlink, Maker
                 and Shiba Inu, only SHIB qualifies for the check at all.

  STABLECOINS GET NO EXEMPTION (owner's ruling, 2026-07-29). The captive test catches some
  smaller stablecoins whose liquidity sits in one pool, USDS at 98.3% on a single Uniswap
  market being the live example. There is a reasonable argument for exempting them, since
  a stablecoin's cap is issuance rather than a discovered price, and the question was put
  and answered: no exemption. One test, applied the same way to everything, and a coin
  whose price only exists in one place is off the board whatever it is pegged to. USDT and
  USDC clear the test comfortably on their own trading, which is the point.

  Failing coins are dropped and the slots are backfilled from below, so the board always
  shows a full hundred that all pass.

COST CONTROL, and why screening is NOT part of the build
  Venue and supply checks need two calls per candidate against a keyless, rate-limited API.
  A full pass takes the better part of an hour, which is fine for a weekly job and absurd
  for a build that runs several times a day.

  So the two are separated. This module screens and writes site/data/coin_screen.json; the
  build only READS that file and applies it. A build never waits on CoinGecko for this, and
  a slow or rate-limited screen can never delay a publish. The refresh runs on its own
  schedule (.github/workflows/coin-screen.yml) and commits the result.

  That split is safe because the property being measured is slow. Whether a coin has an
  independent market is not something that changes between a Tuesday and a Wednesday.

FAIL-SAFE
  If screening cannot run, the previous cached verdicts still apply. A network problem
  must never silently return the board to publishing unscreened caps.

USAGE
  python3 coin_screen.py            # refresh the cache, print what changed
"""

import json
import os
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "site", "data", "coin_screen.json")

# Re-screen this often. Long, because whether a coin has an independent market is not a
# thing that changes between a Tuesday and a Wednesday.
CACHE_HOURS = 72

# Only coins above this cap-to-volume ratio are worth spending API calls on. Deliberately
# far below any exclusion threshold: this is a net, not a verdict, and it is cheap to check
# a coin that turns out to be fine.
#
# This started at 80x and that was too high. Figure Heloc, one of the two coins that
# prompted this whole screen, sits at 58x and sailed straight through the net without ever
# being checked, despite trading 100% on its issuer's own venue. A cap-to-volume ratio is a
# weak proxy for captivity, so the net has to be set well below where the real cases sit.
# 30x is under the top 100's median of about 44x and catches everything we have seen fail.
CANDIDATE_RATIO = 30

# Seconds to wait before each screened coin's calls. See the note in screen().
PACE_SECONDS = 3

# A single venue at or above this share of reported volume means the price is that venue's
# opinion rather than a market's.
CAPTIVE_SHARE = 0.90

# Below this much daily volume a coin is treated as not trading at all.
UNTRADED_USD = 25_000

# How far the markets endpoint's circulating supply may exceed the coin's own detail
# endpoint before the cap is considered built on unverified supply.
SUPPLY_TOLERANCE = 1.20

# THE INDEPENDENT CHECK. The tolerance above compares an aggregator against ITSELF, which
# catches an inconsistent listing (that is how WhiteBIT and FIGR_HELOC were caught) but
# cannot catch a supply figure that is simply wrong in a self-consistent way. That is
# exactly the self-reported market cap this screen exists to reject.
#
# On-chain total supply is a different kind of number: a ceiling that cannot be argued
# with, because a token cannot circulate more than exists. Blockscout serves it keyless and
# is already a dependency of this repo (whale_flows.py).
#
# Margin, not tolerance. The ceiling is hard, so this only absorbs read timing between two
# sources sampled seconds apart. Fabricated supply misses by multiples, not by 5%.
ONCHAIN_MARGIN = 1.05
BLOCKSCOUT_TOKEN = "https://eth.blockscout.com/api/v2/tokens/"

REASONS = {
    "captive": "one venue accounts for nearly all reported volume",
    "untraded": "no meaningful reported trading",
    "supply": "market cap computed on supply the coin's own listing does not confirm",
    "onchain": "market cap computed on more supply than exists on chain",
}


def _now():
    return datetime.now(timezone.utc)


def load_cache():
    """Cached verdicts, or an empty screen. Never raises: a missing or corrupt cache must
    not take the build down, it just means nothing is excluded yet."""
    try:
        with open(CACHE) as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("excluded"), dict):
            return d
    except Exception:
        pass
    return {"generated_utc": None, "excluded": {}, "checked": 0}


def is_stale(cache, hours=CACHE_HOURS):
    ts = (cache or {}).get("generated_utc")
    if not ts:
        return True
    try:
        age = _now() - datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return age.total_seconds() > hours * 3600
    except Exception:
        return True


def excluded_ids(cache=None):
    """The set of CoinGecko ids the board must not show."""
    return set((cache or load_cache()).get("excluded", {}))


def apply(coins, cache=None, limit=100):
    """Drop failing coins from a markets-endpoint list and backfill from below.

    Returns (kept, dropped). The caller is expected to have fetched more than `limit`
    coins so the backfill has somewhere to come from; if it did not, the board is simply
    shorter, which is the honest outcome and not an error.

    `dropped` is deliberately narrower than "everything excluded": it is only the coins
    that WOULD HAVE BEEN on the published board. Failures further down the fetched list
    were never going to be shown, so naming them to a reader would be noise dressed up as
    transparency."""
    bad = excluded_ids(cache)
    would_have_shown = {(c.get("id") or "") for c in coins[:limit]}
    kept, dropped = [], []
    for c in coins:
        if (c.get("id") or "") in bad:
            if (c.get("id") or "") in would_have_shown:
                dropped.append(c)
        else:
            kept.append(c)
    return kept[:limit], dropped


# ---- screening (the expensive half, run on a cache miss) ----------------------

def _venue_profile(get_json, coin_id):
    """Total reported volume, venue count, and the largest single venue's share."""
    d = get_json(f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers")
    by_venue = {}
    for t in (d.get("tickers") or []):
        v = ((t.get("converted_volume") or {}).get("usd")) or 0
        name = ((t.get("market") or {}).get("name")) or "?"
        by_venue[name] = by_venue.get(name, 0) + v
    total = sum(by_venue.values())
    if not by_venue or total <= 0:
        return {"total_usd": 0.0, "venues": len(by_venue), "top_share": None, "top": None}
    top, top_usd = max(by_venue.items(), key=lambda kv: kv[1])
    return {"total_usd": total, "venues": len(by_venue),
            "top_share": top_usd / total, "top": top}


def _detail(get_json, coin_id):
    """The coin's own listing: its stated circulating supply and the chains it lives on.

    One call for both. `platforms` is what makes the on-chain check safe: an Ethereum
    supply read is only a valid ceiling for a token that exists ONLY on Ethereum."""
    d = get_json(f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                 "?localization=false&tickers=false&market_data=true"
                 "&community_data=false&developer_data=false&sparkline=false")
    return {"circulating": (d.get("market_data") or {}).get("circulating_supply"),
            "platforms": {k: v for k, v in (d.get("platforms") or {}).items()
                          if k and v and str(v).strip()}}


def _detail_supply(get_json, coin_id):
    """Back-compat shim: the stated circulating supply alone."""
    return _detail(get_json, coin_id)["circulating"]


def _ethereum_only_contract(platforms):
    """The Ethereum contract address, but ONLY for a token that lives nowhere else.

    This guard is the whole reason the check is trustworthy. A multi-chain token's
    Ethereum supply is a fraction of its real total, so comparing a global circulating
    figure against it would flag honest coins by the dozen: Chainlink alone lists 84
    chains. When in doubt there is no check, which is this module's standing rule."""
    if len(platforms or {}) != 1:
        return None
    (chain, addr), = platforms.items()
    if chain.lower() != "ethereum" or not str(addr).startswith("0x"):
        return None
    return str(addr)


def _onchain_supply(get_json, contract):
    """Total supply from the chain itself, in whole tokens. None when unreadable."""
    d = get_json(BLOCKSCOUT_TOKEN + contract)
    raw, dec = d.get("total_supply"), d.get("decimals")
    if raw in (None, "") or dec in (None, ""):
        return None
    return int(raw) / (10 ** int(dec))


def judge(coin, get_json):
    """Screen one coin. Returns a verdict dict when it fails, or None when it passes.

    Order matters: untraded is checked before captive, because a coin with no trading has
    no venue share to speak of and the untraded reason is the more informative one."""
    cid = coin.get("id") or ""
    prof = _venue_profile(get_json, cid)

    if prof["total_usd"] < UNTRADED_USD:
        return {"reason": "untraded", "detail": prof}

    if prof["top_share"] is not None and prof["top_share"] >= CAPTIVE_SHARE:
        return {"reason": "captive", "detail": prof}

    listed = coin.get("circulating_supply")
    detail = _detail(get_json, cid)
    own = detail["circulating"]
    if listed and own and listed > own * SUPPLY_TOLERANCE:
        return {"reason": "supply",
                "detail": {"listed_supply": listed, "own_supply": own,
                           "ratio": round(listed / own, 2)}}

    # The independent read, last because it costs a second host. Only Ethereum-only tokens
    # qualify, and an unreadable contract is not evidence: this module excludes on evidence
    # and never on a failed request, so anything unclear falls through to a pass.
    contract = _ethereum_only_contract(detail["platforms"])
    if contract and listed:
        try:
            chain_supply = _onchain_supply(get_json, contract)
        except Exception:
            chain_supply = None
        if chain_supply and listed > chain_supply * ONCHAIN_MARGIN:
            return {"reason": "onchain",
                    "detail": {"listed_supply": listed, "chain_supply": chain_supply,
                               "contract": contract,
                               "ratio": round(listed / chain_supply, 2)}}
    return None


def screen(coins, get_json, verbose=True):
    """Screen a markets-endpoint list and return a fresh cache dict.

    Only coins that clear the cheap ratio pre-filter get paid API calls. A coin whose
    checks error out is left OUT of the excluded set: we exclude on evidence, never on a
    failed request."""
    cache = {"generated_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
             "excluded": {}, "checked": 0, "errors": 0}

    for c in coins:
        mc = c.get("market_cap") or 0
        vol = c.get("total_volume") or 0
        if mc <= 0:
            continue
        if vol > 0 and mc / vol < CANDIDATE_RATIO:
            continue                      # trades enough to be a market; not worth a call
        cache["checked"] += 1
        # Pace the calls. Keyless CoinGecko rate-limits bursts, and get_json's 429 backoff
        # starts at 20s, so it is far cheaper to wait a little before every call than to
        # trip the limiter and wait a lot after it.
        time.sleep(PACE_SECONDS)
        try:
            verdict = judge(c, get_json)
        except Exception as e:
            cache["errors"] += 1
            if verbose:
                print(f"::warning::coin screen could not check "
                      f"{c.get('symbol', '?').upper()}: {e}")
            continue
        if verdict:
            cache["excluded"][c["id"]] = {
                "symbol": (c.get("symbol") or "").upper(),
                "name": c.get("name") or "",
                "rank": c.get("market_cap_rank"),
                "market_cap": mc,
                "reason": verdict["reason"],
                "why": REASONS[verdict["reason"]],
                "detail": verdict["detail"],
            }
            if verbose:
                d = verdict["detail"]
                extra = (f"{d['top']} {d['top_share']:.1%}" if verdict["reason"] == "captive"
                         else f"{d['ratio']}x listed vs own" if verdict["reason"] == "supply"
                         else f"{d['ratio']}x listed vs on-chain" if verdict["reason"] == "onchain"
                         else f"${d['total_usd']:,.0f} volume")
                print(f"  drop #{c.get('market_cap_rank')} "
                      f"{(c.get('symbol') or '').upper():<12} {verdict['reason']:<9} {extra}")
    return cache


def refresh(coins, get_json, force=False, verbose=True):
    """Re-screen if the cache has aged out, otherwise keep what we have.

    On any failure the OLD cache is returned unchanged, so a network problem cannot put
    unscreened caps back on the board."""
    old = load_cache()
    if not force and not is_stale(old):
        return old
    try:
        fresh = screen(coins, get_json, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"::warning::coin screen failed, keeping previous verdicts: {e}")
        return old
    # A screen that checked nothing is a screen that did not run. Do not let it overwrite
    # real verdicts with an empty set.
    if not fresh["checked"] and old.get("excluded"):
        if verbose:
            print("::warning::coin screen checked nothing, keeping previous verdicts")
        return old
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(fresh, f, indent=1, sort_keys=True)
    return fresh


if __name__ == "__main__":
    from market_pulse import get_json as _get

    universe = json.loads(json.dumps(_get(
        "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
        "&order=market_cap_desc&per_page=160&page=1")))
    import sys
    print(f"screening {len(universe)} coins "
          f"(candidates: cap/volume >= {CANDIDATE_RATIO}x)")
    out = refresh(universe, _get, force=True)
    print(f"\nchecked {out['checked']}, excluded {len(out['excluded'])}, "
          f"errors {out.get('errors', 0)}")
    for cid, e in sorted(out["excluded"].items(), key=lambda kv: kv[1]["rank"] or 999):
        print(f"  #{e['rank']:>3} {e['symbol']:<12} ${e['market_cap'] / 1e9:7.2f}B  {e['why']}")
