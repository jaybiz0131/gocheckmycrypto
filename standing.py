#!/usr/bin/env python3
"""
standing.py: what a story RESTS ON, decided once, read by the Edition and by the badge.

Jack's rule, 4 October 2026. The day's one story needs two independent sources, or one
primary source: the company's or the regulator's own notice, a filing, a court record, or
the chain itself. A story resting on one secondary outlet is not the day's story and is
held. Three badges, and only three:

  "Verified"                  checked against two or more independent sources
  "Verified, primary source"  rests on one source, and that source is primary
  "Unconfirmed, one report"   rests on one secondary outlet; never says Verified

Before this, a VERIFIED story whose cluster rested on one outlet wore "Verified, one source
so far" while the Standards page said a claim on a single weak source is labeled
unconfirmed or left out. A reader who checked both pages saw the site arguing with itself.
The selection in autopilot.py and verdict_badge() in site_build.py both call standing(), so
the story the Edition picks and the badge the reader sees cannot disagree.

The verifier's own logic does not change. This decides which story the day picks and what
the badge says, nothing else.
"""

from urllib.parse import urlparse

# Hosts whose own words ARE the event: regulators, courts, legislatures, filings, the
# chain, and a company's own notice. A suffix match, so www. and sub-sites count. Kept
# conservative on purpose: a host missing here costs a story the primary badge and holds
# it, which is the safe failure; a commentary site on this list would let one outlet's
# word pass as the record.
PRIMARY_HOSTS = (
    # US regulators, enforcement and legislature
    "sec.gov", "cftc.gov", "federalreserve.gov", "treasury.gov", "occ.gov",
    "occ.treas.gov", "fdic.gov", "fincen.gov", "irs.gov", "justice.gov", "ftc.gov",
    "consumerfinance.gov", "federalregister.gov", "congress.gov", "senate.gov",
    "house.gov", "whitehouse.gov", "finra.org", "dfs.ny.gov", "nasaa.org",
    # courts and court records
    "uscourts.gov", "supremecourt.gov", "courtlistener.com", "pacer.gov",
    # regulators abroad and standard setters
    "fca.org.uk", "bankofengland.co.uk", "esma.europa.eu", "eba.europa.eu",
    "ecb.europa.eu", "europa.eu", "mas.gov.sg", "sfc.hk", "hkma.gov.hk", "fsa.go.jp",
    "bis.org", "fsb.org", "imf.org", "fatf-gafi.org", "osc.ca", "asic.gov.au",
    # the chain itself
    "etherscan.io", "basescan.org", "arbiscan.io", "bscscan.com", "polygonscan.com",
    "solscan.io", "explorer.solana.com", "tronscan.org", "mempool.space",
    "blockstream.info", "blockchair.com",
    # company and protocol notices, and the wires companies file them on
    "blog.ethereum.org", "prnewswire.com", "businesswire.com", "globenewswire.com",
    "investor.coinbase.com", "coinbase.com", "binance.com", "kraken.com", "blog.kraken.com",
    "gemini.com", "circle.com", "tether.to", "paxos.com", "ripple.com", "blackrock.com",
    "ishares.com", "fidelity.com", "grayscale.com", "microstrategy.com", "strategy.com",
)


def host(url):
    h = (urlparse((url or "").strip()).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def is_primary(url):
    h = host(url)
    return bool(h) and any(h == p or h.endswith("." + p) for p in PRIMARY_HOSTS)


def _outlet(h):
    """The registrable-ish name of a host, so two URLs from one outlet count once."""
    parts = [p for p in h.split(".") if p]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "gov", "org", "ac") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _norm(name):
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def outlets(urls, also_reported_by=()):
    """The distinct outlets behind a story: one per source host, plus each corroborating
    outlet named by the desk that is not already one of those hosts."""
    seen = []
    for u in urls or []:
        h = host(u)
        if h:
            o = _outlet(h)
            if o not in seen:
                seen.append(o)
    stems = {_norm(o.split(".")[0]) for o in seen}
    for n in also_reported_by or []:
        if isinstance(n, dict):  # six stored stories carry {"outlet", "headline"}
            n = n.get("outlet") or n.get("name") or ""
        k = _norm(n)
        if k and k not in stems and not any(k.startswith(s) or s.startswith(k)
                                            for s in stems if s):
            stems.add(k)
            seen.append(k)
    return seen


def standing(urls, also_reported_by=()):
    """'corroborated' (two or more independent outlets), 'primary' (one, and it is
    primary), or 'single' (one secondary outlet, or nothing at all)."""
    if len(outlets(urls, also_reported_by)) >= 2:
        return "corroborated"
    if any(is_primary(u) for u in urls or []):
        return "primary"
    return "single"


def item_urls(item):
    """Source URLs from a published item (sources are {title, url}) or a draft (plain
    strings), whichever this is."""
    out = []
    for s in (item or {}).get("sources") or []:
        u = s.get("url") if isinstance(s, dict) else s
        if u:
            out.append(str(u))
    return out


def item_standing(item):
    return standing(item_urls(item), (item or {}).get("also_reported_by") or [])


def primary_first(sources):
    """The same list with primary sources moved to the front, order otherwise kept. A
    story wearing "Verified, primary source" shows that source first."""
    def _u(s):
        return s.get("url") if isinstance(s, dict) else s
    return ([s for s in sources or [] if is_primary(_u(s))]
            + [s for s in sources or [] if not is_primary(_u(s))])


def can_lead(item):
    """May this story be the day's one story? Two sources, or one primary."""
    return item_standing(item) in ("corroborated", "primary")
