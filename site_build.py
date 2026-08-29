#!/usr/bin/env python3
"""
site_build.py: build the public Crypto Cronkite site from committed content.

Reproducible + lossless (the GoCheckMyPet lesson D2: everything the page needs is emitted
here from the templates, so rebuilding never strips the footer, disclaimer, or schema). Reads
site/content/*.json (one file per published item; _-prefixed files are ignored) and renders a
static deploy folder site/publish/: home, archive, one page per article, plus the static
editorial pages (about / how we work / standards) and a 404. No third-party dependency; no em
dashes; not-financial-advice baked into every article and the footer.

CONTENT FLOW
  A story is published only after a human approves it (publish.py, Stage 6). Promote approved
  payloads into committed site content with --ingest, then rebuild:

    python3 site_build.py --ingest      # out/published/*.json -> site/content/*.json, then build
    python3 site_build.py               # build site/publish/ from committed content

USAGE
  python3 site_build.py [--ingest]
"""

import glob
import hashlib
import json
import os
import re
import sys

import boundary
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
CONTENT = os.path.join(SITE, "content")
ASSETS = os.path.join(SITE, "assets")
PUBLISH = os.path.join(SITE, "publish")
PUBLISHED = os.path.join(HERE, "out", "published")

# Brand: Crypto Cronkite is the focal brand (the news desk, the masthead, the audience). This site
# stands on its own; the only thing it shares with the GoCheckMy family is the name/domain
# (gocheckmycrypto.com) plus the "A GoCheckMy site" footer tie. No family visual reskin, by design
# (see DEVIATIONS D-CRYPTO-2). Whale Watch is the on-chain tools sub-brand.
NAME = "Crypto Cronkite"
SLOGAN = "And that's the way it is."          # Walter Cronkite's sign-off; the brand tagline
DESK_LINE = "The honest voice in a shill-filled space."   # secondary descriptor
FAMILY = "GoCheckMyCrypto"                     # family/domain tie: gocheckmycrypto.com
FAMILY_HUB = "https://gocheckmy.com/"          # the GoCheckMy family hub (canonical footer link)
ORIGIN = "https://gocheckmycrypto.com"         # canonical origin for canonical/og:url/sitemap
SHORT_NAME = "GoCheckMyCrypto"                # home-screen label (manifest)
THEME_COLOR = "#B42318"                       # browser chrome + manifest
OG_IMAGE = ORIGIN + "/og-image.png"            # 1200x630 social card, generated at build time
CF_ANALYTICS_TOKEN = "ee5216c8411a41d78c7c4f679406ef4b"  # Cloudflare Web Analytics site token; empty renders no beacon
DESC = ("Crypto Cronkite is an independent crypto news desk built with one intention: get the "
        "stories right and keep the data honest. Plus the Whale Watch and Market Pulse data "
        "desks. We report events, we never advise trades.")
FAMILY_DESC = ("Independent crypto news with the shill stripped out, plus live whale flows and market dashboards the desk measures itself. Never financial advice.")
NFA = ("Not financial advice. Crypto Cronkite reports events and explains what they may mean. "
       "It never tells you to buy or sell anything. Do your own research.")
YEAR = "2026"
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

# ---- accessibility statement: the testing record the page reports --------------
# These are claims about testing that was actually run. Do not edit them to make the page
# read better. Edit them only when a new sweep has been run, in the same commit that
# records it. See render_accessibility().
ACCESSIBILITY_TESTED_ON = "28 July 2026"
ACCESSIBILITY_AXE_VERSION = "4.12.1"
ACCESSIBILITY_PAGE_COUNT = "30"       # 20 standalone + 8 Market Pulse boards + 2 article samples
ACCESSIBILITY_ARTICLE_COUNT = "141"

NAV = [("Home", "/index.html"), ("The Edition", "/news.html"),
       ("Whale Watch", "/flows.html"), ("Market Pulse", "/pulse.html"),
       ("Chart Master", "/chartmaster.html"), ("Learn", "/learn.html"),
       ("Archive", "/archive.html"), ("About", "/about.html")]


# ---- helpers -----------------------------------------------------------------

try:
    import family_modules as _fam
except ImportError:      # resolver absent: articles carry no module
    _fam = None

def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "story"


def fmt_date(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or ""))
    if not m:
        return str(iso or "")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{MONTHS[mo]} {d}, {y}"


def _parse_utc(item):
    """datetime for a story's publish moment: published_utc when stamped (new stories),
    else midnight of its date (legacy stories carry a date only)."""
    from datetime import datetime, timezone
    for fmt, val in (("%Y-%m-%dT%H:%M:%SZ", item.get("published_utc") or ""),
                     ("%Y-%m-%d", item.get("date") or "")):
        try:
            return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fmt_when(item):
    """Dateline with the publish time when we have one: 'July 12, 2026 · 07:41 UTC'.
    Crypto is a 24/7 market; an expert reader needs to know 2 hours old vs 20."""
    base = esc(fmt_date(item.get("date")))
    if item.get("published_utc"):
        dt = _parse_utc(item)
        if dt:
            return f"{base} &middot; {dt.strftime('%H:%M')} UTC"
    return base


def _rfc822(item):
    dt = _parse_utc(item)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000") if dt else ""


# Source attribution: outlet names read better (and more honestly) than raw feed URLs.
OUTLETS = {
    "coindesk.com": "CoinDesk", "theblock.co": "The Block",
    "cointelegraph.com": "Cointelegraph", "decrypt.co": "Decrypt",
    "bitcoinmagazine.com": "Bitcoin Magazine", "blockworks.co": "Blockworks",
    "dlnews.com": "DL News", "thedefiant.io": "The Defiant", "protos.com": "Protos",
    "reuters.com": "Reuters", "bloomberg.com": "Bloomberg", "cnbc.com": "CNBC",
    "wsj.com": "The Wall Street Journal", "ft.com": "Financial Times",
    "sec.gov": "SEC", "cftc.gov": "CFTC", "justice.gov": "U.S. Department of Justice",
    "federalreserve.gov": "Federal Reserve", "treasury.gov": "U.S. Treasury",
    "imf.org": "IMF", "whitehouse.gov": "The White House", "congress.gov": "Congress.gov",
    "ethereum.org": "Ethereum Foundation", "blog.ethereum.org": "Ethereum Foundation",
    "bitcoincore.org": "Bitcoin Core", "whale-alert.io": "Whale Alert",
}


def source_label(src):
    """'CoinDesk: lending protocol bonzo loses 77 of value locked' instead of a raw URL
    with utm cruft. A real title (anything that isn't just the URL) is kept as-is."""
    from urllib.parse import urlparse
    url = src.get("url") or ""
    title = (src.get("title") or "").strip()
    if title and title != url:
        return title
    p = urlparse(url)
    host = p.netloc.lower().removeprefix("www.")
    outlet = OUTLETS.get(host, host)
    slug = [s for s in p.path.split("/") if s]
    hint = re.sub(r"[-_]+", " ", re.sub(r"\.\w+$", "", slug[-1])) if slug else ""
    hint = re.sub(r"\b\d{5,}\b", "", hint).strip()
    if len(hint) > 80:
        hint = hint[:80].rsplit(" ", 1)[0] + "..."
    if hint and not hint.isdigit():
        return f"{outlet}: {hint}"
    return outlet


# RETIRED ARTICLES: retired slug -> the canonical slug that absorbed it.
#
# The desk published the same Treasury designation three times on 2026-07-30 (15:25 Protos,
# 18:40 and 18:55 both off one Defiant URL). The fullest of the three survives, the reporting
# only the others carried was folded into it, and these two 301 there. Deleting them would
# 404 anyone who linked or shared them, which turns our filing error into the reader's
# problem.
#
# This map is the audit trail as well as the mechanism: every entry is a URL the desk retired
# and where it went. Add here, never remove.
RETIRED_ARTICLES = {
    "39-u-s-banking-associations-form-bankchain-alliance-to-build-proprietary-blockchain-by-2027":
        "state-banking-associations-announce-bankchain-alliance-for-2027-launch",
    # owner audit 2026-08-29: one event told two or three times in 72 hours
    "coinbase-better-make-token-backed-mortgages-generally-available":
        "coinbase-and-better-take-bitcoin-backed-mortgages-from-waitlist-to-general-availability",
    "revolut-launches-euro-stablecoin-eurr-across-select-eu-markets":
        "revolut-starts-eurr-rollout-with-bridge-as-regulated-issuer",
    "revolut-rolls-out-eurr-stablecoin-across-three-eu-markets-with-bridge-as-issuer":
        "revolut-starts-eurr-rollout-with-bridge-as-regulated-issuer",
    "us-treasury-adds-digital-assets-to-iran-sanctions-authority":
        "u-s-treasury-brings-iran-s-crypto-sector-under-sanctions-authority",
    # cross-day audit 2026-08-25: the same anticipatory CoinDesk-sourced story told
    # twice three days apart, zero novel claims in the retelling
    "new-clarity-act-draft-may-drop-this-week-sources-tell-coindesk":
        "new-clarity-act-draft-may-arrive-as-soon-as-next-week-sources-say",
    "aave-approves-deprecation-of-50-assets-and-exit-from-six-chains":
        "aave-retires-50-assets-and-exits-six-chains-consolidating-away-from-low-value-markets",
    "ai-compute-stocks-bounce-as-hut-8-iren-land-billions-in-new-contracts":
        "hut-8-and-iren-announce-multi-billion-dollar-ai-data-center-contracts-mining-stocks-surge",
    "amazon-japan-logistics-firm-az-com-maruwa-to-pay-2-300-partners-with-regulated-yen-stablecoin-jpyc":
        "amazon-japan-supplier-to-pay-2-300-contractors-using-regulated-yen-stablecoin",
    "bitcoin-s-largest-holder-saylor-opposes-bip-110-spam-filter-on-neutrality-grounds":
        "michael-saylor-warns-bip-110-spam-filter-threatens-bitcoin-s-neutrality",
    "bitmex-sued-for-collateral-theft-and-insider-trading-as-shutdown-looms":
        "bitmex-faces-class-action-lawsuit-alleging-collateral-theft-and-insider-trading-as-exchange-announces-shutdown",
    "cftc-blocks-michigan-court-order-mandates-kalshiex-fulfill-trades":
        "cftc-overrides-michigan-court-order-mandates-kalshiex-fulfill-pending-trades",
    "cftc-orders-kalshiex-to-honor-trades-a-michigan-state-court-directed-it-to-cancel":
        "cftc-overrides-michigan-court-order-mandates-kalshiex-fulfill-pending-trades",
    "cftc-overrides-michigan-court-order-orders-kalshiex-to-fulfill-pending-trades":
        "cftc-overrides-michigan-court-order-mandates-kalshiex-fulfill-pending-trades",
    "cftc-overrides-michigan-court-orders-kalshiex-to-fulfill-prediction-market-trades":
        "cftc-overrides-michigan-court-order-mandates-kalshiex-fulfill-pending-trades",
    "cftc-overrides-michigan-court-orders-kalshiex-to-fulfill-trades":
        "cftc-overrides-michigan-court-order-mandates-kalshiex-fulfill-pending-trades",
    "coreum-bridge-loses-99-7-of-xrp-reserve-in-200k-exploit-via-fake-deposit-transactions":
        "xrp-bridge-drained-for-200-000-after-software-mistook-fake-deposits-for-real-ones",
    "ecb-picks-36-firms-including-deutsche-bank-and-revolut-for-digital-euro-pilot":
        "ecb-selects-36-firms-for-digital-euro-pilot-starting-in-2027",
    "ethereum-foundation-confirms-validator-crash-bug-surfaced-by-ai":
        "ethereum-foundation-discloses-validator-crash-bug-found-with-ai-help",
    "ostium-suffers-18-million-exploit-as-oracle-attack-wave-continues-to-hit-defi":
        "ostium-loses-18-million-to-oracle-manipulation-attack-via-priceupkeep-exploit",
    "solana-network-came-within-minutes-of-full-freeze-after-routing-glitch-knocked-out-28-of-stake":
        "solana-came-within-4-5-percentage-points-of-network-halt-after-teraswitch-routing-failure",
    "tether-posts-1-5-billion-operating-profit-in-q2-as-reserve-buffer-falls-by-half":
        "tether-q2-profit-falls-69-as-reserve-buffer-halves-to-4-1-billion",
    "trump-targets-brazil-s-pix-while-dollar-stablecoins-dominate-country-s-crypto-payments":
        "trump-tariffs-brazil-s-pix-while-dollar-stablecoins-already-own-90-of-crypto-payments",
    "u-s-sanctions-iran-linked-maritime-insurance-scheme-that-accepted-bitcoin":
        "us-sanctions-iranian-marine-insurers-accepting-bitcoin-for-strait-of-hormuz-passage",
    "u-s-treasury-sanctions-iran-linked-maritime-insurance-scheme-accepting-bitcoin":
        "us-sanctions-iranian-marine-insurers-accepting-bitcoin-for-strait-of-hormuz-passage",
    "uk-parliament-launches-formal-inquiry-into-banking-restrictions-on-crypto-firms":
        "u-k-parliament-launches-formal-inquiry-into-bank-restrictions-on-crypto-firms",
    "us-treasury-sanctions-iranian-firms-using-bitcoin-for-maritime-extortion":
        "us-sanctions-iranian-marine-insurers-accepting-bitcoin-for-strait-of-hormuz-passage",
    "us-treasury-sanctions-iranian-maritime-firms-behind-bitcoin-denominated-hormuz-insurance-scheme":
        "us-sanctions-iranian-marine-insurers-accepting-bitcoin-for-strait-of-hormuz-passage",
    "visa-launches-stablecoin-platform-with-open-usd-pressuring-circle-s-business-model":
        "visa-launches-stablecoin-platform-for-open-usd-upending-issuer-revenue-model",
    "visa-launches-visa-stablecoin-platform-for-open-usd-as-circle-s-competitive-moat-narrows":
        "visa-launches-stablecoin-platform-for-open-usd-upending-issuer-revenue-model",
}

# Topic tags: deterministic keyword rules over the story text, computed at build time so
# every story (old and new) gets them without touching the pipeline. Order = priority;
# a story keeps at most 3.
# TAG_RULES is in DISPLAY ORDER, most specific first, and that ordering is load-bearing:
# tags_for returns matches in this order and _hero_tag shows the first, so whatever sits at
# the top of this list is the label most of the site ends up wearing.
#
# It used to be "regulation", with the broadest pattern in the file, and the result was
# measurable: 111 of 156 published stories rendered "regulation" on the homepage, 71% of the
# site under one chip. "treasury" matched corporate treasury operations, "bill", "law",
# "approval" and "charge[sd]?" matched ordinary body prose, and a story could not be about
# litigation at all because there was no bucket for it. It also degraded related_stories,
# which scores on shared tags and so was matching almost everything to almost everything.
#
# Two changes. "regulation" now means an agency or a legislature ACTING, not any sentence
# that mentions a law; litigation moved to its own "legal" bucket where it belongs. And the
# list is ordered by how much the tag narrows the story down rather than by accident of
# authorship. "bitcoin" sits near the bottom on purpose: nearly every story on this desk
# mentions bitcoin, so it is the least informative thing the desk can say about one.
TAG_RULES = [
    ("security", r"\b(exploit\w*|hack\w*|stolen|theft|vulnerabilit\w*|drained|breach\w*|"
                 r"ponzi|fraud|scam\w*|phishing|attacker\w*|rug ?pull)\b"),
    ("etfs-funds", r"\b(etf\w*|grayscale|blackrock|ishares|fund flows)\b"),
    ("stablecoins", r"\b(stablecoin\w*|usdt|usdc|tether|dai)\b"),
    ("legal", r"\b(lawsuit\w*|sue[sd]?|suing|court|judge|judicial|indict\w*|prosecutor\w*|"
              r"plea|pleaded|guilty|settlement|subpoena\w*|sentenc\w*|litigation|"
              r"attorney general|class action)\b"),
    ("macro", r"\b(fomc|federal reserve|rate (?:decision|cut|hike)|interest rates?|"
              r"cpi|inflation|jobs report|treasury yield\w*|ecb|bank of england)\b"),
    ("regulation", r"\b(sec|cftc|occ|fincen|doj|finra|esma|fca|"
                   r"regulat\w*|rulemaking|congress|senate|parliament|lawmaker\w*|"
                   r"legislat\w*|cbdc|inquiry|executive order|sanction\w*|"
                   r"comment period|federal register)\b"),
    ("exchanges", r"\b(exchange\w*|binance|coinbase|kraken|okx|bitmex|bybit|bitfinex|"
                  r"gemini|custodian\w*|custody|delist\w*|shuts? down|wind(?:s|ing)? down)\b"),
    ("ethereum", r"\b(ethereum|eth|validator\w*|staking|vitalik)\b"),
    ("defi", r"\b(defi|tvl|oracle\w*|lending|dex|liquidity pool\w*|amm|"
             r"aave|uniswap|curve finance|compound|makerdao|tokeniz\w*)\b"),
    ("protocols", r"\b(cardano|solana|zcash|near|avalanche|polkadot|cosmos|chainlink|"
                  r"litecoin|monero|governance|hard ?fork|soft ?fork|mainnet|testnet|"
                  r"node software|upgrade\w*|shielded|privacy pool\w*)\b"),
    ("bitcoin", r"\b(bitcoin|btc|bip ?-?\d+|miner\w*|mining|halving)\b"),
    ("markets", r"\b(price\w*|rally|selloff|sell-off|surge\w*|plunge\w*|all-time high|"
                r"market cap|liquidation\w*|volume\w*|institutional|trading)\b"),
]
_TAG_RES = [(tag, re.compile(pat, re.I)) for tag, pat in TAG_RULES]


def tags_for(item):
    """Up to three topic tags, most specific first. See TAG_RULES for why the order matters.

    Matched against the headline, dek and key fact ONLY, never the body. A tag is a claim
    about what the story IS about, and a 600-word body mentions enough to match most rules
    in the list: that is how "regulation" ended up on 71% of the site."""
    text = " ".join([item.get("title") or "", item.get("dek") or "",
                     item.get("key_fact") or ""])
    return [tag for tag, rx in _TAG_RES if rx.search(text)][:3]



_STORY_STOP = {"the","a","an","and","or","of","to","for","in","on","with","from","as","at",
               "its","it","that","this","after","over","amid","says","said","new","first",
               "crypto","bitcoin","btc","report","reports"}


def _content_words(*texts):
    out = set()
    for t in texts:
        out |= {w for w in re.findall(r"[a-z][a-z0-9.]{2,}", (t or "").lower())
                if w not in _STORY_STOP}
    return out


def _proper_nouns(*texts):
    out = set()
    for t in texts:
        out |= {w.lower() for w in re.findall(r"\b[A-Z][A-Za-z0-9&.-]{2,}", t or "")
                if w.lower() not in _STORY_STOP}
    return out


def _same_storyline(a, b, names_floor=0.22):
    """True when two stories visibly share a subject, by their own words.

    THE BAR MATCHES THE CLAIM (owner SEO audit 2026-08-25). Measured on the 58 declared
    update edges, vocabulary overlap runs a median of 0.10 and the band from 0.14 to 0.22
    is a coin flip: "Russia passes crypto law" over "Russia's parliament passes crypto
    law" is the same story, but "Storj files Chapter 11" over "Movement Labs files
    Chapter 11" is two different bankruptcies that merely share the words. So the DEFAULT
    is strict, because the Update callout asserts a lineage in the desk's own voice and a
    false assertion is worse than a missing link. A "read next" link claims far less, so
    the related picker passes a lower floor deliberately."""
    at, bt = a.get("title") or "", b.get("title") or ""
    ak, bk = a.get("key_fact") or "", b.get("key_fact") or ""
    aw, bw = _content_words(at, ak), _content_words(bt, bk)
    if not aw or not bw:
        return False
    overlap = len(aw & bw) / min(len(aw), len(bw))
    shared_names = _proper_nouns(at, ak) & _proper_nouns(bt, bk)
    return overlap >= 0.55 or (bool(shared_names) and overlap >= names_floor)


def _watchlist_rx():
    """The editor-in-chief's narrative watchlist, compiled once: name -> regex."""
    global _WATCH_RX
    try:
        return _WATCH_RX
    except NameError:
        pass
    out = []
    try:
        wl = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8")) \
            .get("narratives", {}).get("watchlist", [])
        for n in wl:
            kws = n.get("keywords") or []
            if kws:
                out.append((n.get("name", ""), re.compile(
                    r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", re.I)))
    except Exception:
        out = []
    _WATCH_RX = out
    return out


def _narratives_of(item):
    """Which tracked storylines this story belongs to, from its own title and key fact.

    The watchlist tag lives on the intake cluster and never reaches the published item,
    so it is recomputed here from the same fields tracking_match trusts. Title and
    key_fact only: a 600-word body mentions enough to match almost anything."""
    text = " ".join([item.get("title") or "", item.get("key_fact") or ""])
    return {name for name, rx in _watchlist_rx() if rx.search(text)}


def storyline_for(item, all_items, cap=6):
    """The desk's OWN prior and subsequent coverage of this story, oldest first.

    THE ONE THING NO SOURCE ARTICLE HAS (owner directive 2026-08-25). Every outlet can
    report today's event; only this desk knows what it published about the same
    development three weeks ago, because it is the desk's own archive. Rendering that as
    a dated timeline gives a reader the shape of a story instead of one more isolated
    page, and gives a crawler a reason this page is not a rewrite of somebody else's.

    Three signals, strongest first: the declared update chain walked in BOTH directions
    transitively, then the editor-in-chief's narrative watchlist, then a shared subject
    by the same test the Update callout uses. Editions and the example page are never
    part of a storyline; near-duplicates are excluded so a timeline never lists the same
    event twice.
    """
    slug = item.get("slug")
    pool = [i for i in (all_items or [])
            if not i.get("example") and not _is_wrap(i)
            and i.get("category") != "daily edition" and i.get("slug")]
    by = {i["slug"]: i for i in pool}
    if slug not in by:
        return []

    # 1. transitive update_of component
    kids = {}
    for i in pool:
        p = i.get("update_of")
        if p and p in by and _same_storyline(i, by[p]):
            kids.setdefault(p, []).append(i["slug"])
    parent = {i["slug"]: i.get("update_of") for i in pool
              if i.get("update_of") in by and _same_storyline(i, by[i["update_of"]])}
    comp, stack = set(), [slug]
    while stack:
        cur = stack.pop()
        if cur in comp:
            continue
        comp.add(cur)
        if parent.get(cur):
            stack.append(parent[cur])
        stack.extend(kids.get(cur, []))
    comp.discard(slug)

    # 2. THE SAME DEVELOPMENT, NOT THE SAME BEAT (owner check 2026-08-25). The first
    # build grouped "Storj files Chapter 11" with "SummerFi winds down" and "BitMEX
    # shuts down" because all three matched the "Crypto failures" watchlist entry and
    # cleared a loose word-overlap floor. Those are three different companies, not one
    # story developing, and a timeline that says "how this story developed" must not
    # claim otherwise. A watchlist entry is a BEAT; the beat sections on /news are where
    # that belongs. So membership beyond the declared chain now requires a shared
    # distinctive SUBJECT and a strong overlap, which is the same bar the Update callout
    # passes: the same actor doing the same thing, not two firms failing in one quarter.
    # 2. NOTHING ELSE. Word overlap cannot tell one development from one THEME, and every
    # loosening tried on the live corpus produced a timeline that was confidently wrong:
    # at 0.20 it presented Storj, SummerFi and BitMEX as one story because three separate
    # companies failed the same month; tightened to 0.26 with a shared subject it still
    # strung a BitClub prosecution, a Goliath Ventures suit and a Las Vegas conviction
    # into one thread because all three are Ponzi cases. "How this story developed" is a
    # claim about causation between chapters, and only the desk's own declared update
    # chain actually carries it. So the timeline renders on few stories and is right on
    # all of them, and More-on below carries the breadth with a claim it can support.

    chain = [by[s] for s in comp if not dedupe_same_event(item, by[s])]
    chain.sort(key=lambda i: (i.get("date") or "", i.get("published_utc") or ""))
    if len(chain) > cap:  # keep the earliest chapters and the most recent ones
        chain = chain[:2] + chain[-(cap - 2):]
    return chain


def render_timeline(item, all_items):
    """The storyline timeline module: the desk's own coverage, dated, in order."""
    chain = storyline_for(item, all_items)
    if len(chain) < 2:
        return ""   # two chapters is a link, not a timeline; related-stories covers that
    rows = []
    placed = False
    for c in chain:
        if not placed and (c.get("date") or "") > (item.get("date") or ""):
            rows.append(f'<li class="tl-now"><span class="tl-date">'
                        f'{esc(fmt_date(item.get("date")))}</span>'
                        f'<span class="tl-title">{esc(item.get("title"))} '
                        f'<em>(this story)</em></span></li>')
            placed = True
        rows.append(f'<li><span class="tl-date">{esc(fmt_date(c.get("date")))}</span>'
                    f'<span class="tl-title"><a href="/articles/{esc(c["slug"])}">'
                    f'{esc(c.get("title"))}</a></span></li>')
    if not placed:
        rows.append(f'<li class="tl-now"><span class="tl-date">'
                    f'{esc(fmt_date(item.get("date")))}</span>'
                    f'<span class="tl-title">{esc(item.get("title"))} '
                    f'<em>(this story)</em></span></li>')
    return (f'<section class="timeline"><h2>How this story developed</h2>'
            f'<p class="mut">The desk\'s own reporting on this development, in order. '
            f'{len(chain)} earlier and later stories.</p>'
            f'<ol class="tl">{"".join(rows)}</ol></section>')


_ENT_CACHE = {}
_ENT_MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august",
               "september", "october", "november", "december"}
_ENT_STOP = {"the", "this", "that", "with", "from", "after", "before", "new", "its", "and",
             "but", "for", "million", "billion", "percent", "first", "second", "report",
             "reports", "update", "breaking",
             # A CORPORATE SUFFIX IS NOT A SUBJECT (owner check 2026-08-25): the first
             # build produced "More on LABS", grouping Storj with Movement Labs because
             # both companies end in the same word. Readers of one care nothing for the
             # other, and a module that says otherwise is worse than no module.
             "labs", "inc", "corp", "group", "capital", "ventures", "holdings", "partners",
             "foundation", "protocol", "network", "networks", "finance", "financial",
             "technologies", "systems", "global", "digital", "markets", "exchange",
             "chain", "chains", "coin", "token", "tokens", "fund", "funds", "bank",
             "act", "bill", "rule", "rules", "law", "court", "committee", "department",
             # too broad to be a subject: nearly every story on this desk touches these
             "u.s", "us", "u.k", "btc", "eth", "usd", "etf", "etfs", "defi", "nft"}


def _entity_stats(all_items):
    """Corpus-wide capitalised vs lowercase counts, computed once per build."""
    key = len(all_items or ())
    if key in _ENT_CACHE:
        return _ENT_CACHE[key]
    cap, low = {}, {}
    for i in (all_items or []):
        b = i.get("body")
        t = " ".join(x for x in b if isinstance(x, str)) if isinstance(b, list) else str(b or "")
        for w in re.findall(r"\b[A-Z][A-Za-z0-9&.]{2,}", t):
            k = w.lower().rstrip(".")
            cap[k] = cap.get(k, 0) + 1
        for w in re.findall(r"\b[a-z][a-z0-9&.]{2,}\b", t):
            k = w.rstrip(".")
            low[k] = low.get(k, 0) + 1
    _ENT_CACHE.clear()
    _ENT_CACHE[key] = (cap, low)
    return cap, low


def entities_of(item, all_items):
    """The subjects a story is about: companies, agencies, protocols, people, places.

    A PROPER NOUN IS ONE THE CORPUS RARELY LOWERCASES. "Coinbase" and "CFTC" are almost
    always capitalised; "act", "million" and "market" are not, even though every one of
    them appears capitalised at the start of a sentence. Measuring the ratio across the
    desk's own 225-article body text separates them without a hand-maintained list, and
    outlet names are dropped because who reported a story is not what it is about."""
    cap, low = _entity_stats(all_items)
    try:
        import dedupe
        outlets = dedupe._OUTLETS
    except Exception:
        outlets = set()
    out = set()
    txt = " ".join([item.get("title") or "", item.get("key_fact") or ""])
    for w in re.findall(r"\b[A-Z][A-Za-z0-9&.]{2,}", txt):
        k = w.lower().rstrip(".")
        if k in _ENT_MONTHS or k in _ENT_STOP or k in outlets or len(k) < 3:
            continue
        if w.isupper() and len(w) <= 6:
            out.add(k)
            continue
        c, l = cap.get(k, 0), low.get(k, 0)
        if c + l >= 3 and c / (c + l) >= 0.65:
            out.add(k)
    return out


def render_more_on(item, all_items, per=4):
    """"More on <subject>": the desk's other coverage of the same company, agency or
    protocol.

    Distinct from the timeline, and labelled as what it is. The timeline says these
    stories are chapters of ONE development; this says only that the desk has covered
    this subject before, which is true far more often and is exactly what a reader who
    cares about that subject wants next. Together they reach most of the archive without
    either one overstating what it knows."""
    mine = entities_of(item, all_items)
    if not mine:
        return ""
    pool = [i for i in (all_items or [])
            if not i.get("example") and not _is_wrap(i)
            and i.get("category") != "daily edition"
            and i.get("slug") and i.get("slug") != item.get("slug")]
    chain = {c.get("slug") for c in storyline_for(item, all_items)}
    best = None
    for ent in sorted(mine):
        hits = [i for i in pool
                if ent in entities_of(i, all_items)
                and i.get("slug") not in chain
                and not dedupe_same_event(item, i)]
        if len(hits) >= 2 and (best is None or len(hits) > len(best[1])):
            best = (ent, hits)
    if not best:
        return ""
    ent, hits = best
    hits.sort(key=lambda i: i.get("published_utc") or i.get("date") or "", reverse=True)
    label = ent.upper() if len(ent) <= 5 else ent.title()
    lis = "".join(f'<li><a href="/articles/{esc(i["slug"])}">{esc(i.get("title"))}</a>'
                  f'<span class="mut"> &middot; {fmt_when(i)}</span></li>'
                  for i in hits[:per])
    return (f'<section class="more-on"><h2>More on {esc(label)}</h2>'
            f'<p class="mut">Other reporting from this desk on {esc(label)}.</p>'
            f'<ul class="link-list">{lis}</ul></section>')

def related_stories(item, items, n=3):
    """The stories a reader of this one should read next, best first.

    REBUILT (owner SEO audit 2026-08-25). The old picker scored on shared topic tags
    alone and was measured actively harmful on the live corpus: 8% of its picks were
    good, 46% of the 849 internal links it emitted pointed at DAILY EDITIONS rather than
    stories, 38 article pages carried a related block that was 100% editions, and 64% of
    real stories received no inbound related link at all while two pages absorbed 55 and
    54 each. A funnelling link graph where most of the corpus is an internal orphan is a
    mechanical cause of "crawled, currently not indexed".

    Now, in order: the article's own storyline (its update chain, both directions, which
    the old picker hit 0.1% of the time and is the single most useful link there is),
    then same-subject stories by the shared-proper-noun test, then shared tags as a
    fallback. Editions are never linked from a story: they are summaries OF stories and
    linking them dilutes the story graph. A near-duplicate of this story is never linked
    either, because that teaches a crawler the two pages are interchangeable.
    """
    slug = item.get("slug")
    pool = [o for o in items
            if o is not item and not o.get("example")
            and o.get("slug") != slug
            and not _is_wrap(o) and o.get("category") != "daily edition"
            and not o.get("superseded_by")]
    if not pool:
        return []
    chain = set()
    if item.get("update_of"):
        chain.add(item["update_of"])
    chain |= {o.get("slug") for o in pool if o.get("update_of") == slug}
    mine = set(tags_for(item))
    scored = []
    for o in pool:
        if dedupe_same_event(item, o):
            continue  # a near-duplicate is not a "read next"
        if o.get("slug") in chain:
            rank = 3
        elif _same_storyline(item, o, names_floor=0.16):
            rank = 2
        elif mine and (mine & set(tags_for(o))):
            rank = 1
        else:
            continue
        scored.append((rank, o, abs(_date_gap(item, o))))
    # WITHIN A RANK, NEAREST IN TIME (owner SEO audit 2026-08-25). Sorting the tag
    # fallback by recency alone funnelled the whole corpus into a handful of hub pages:
    # the first rebuild left 75% of stories with no inbound link while two pages absorbed
    # 130 and 87. Coverage is the point of this module, so neighbours in time win, which
    # spreads inbound links across the archive instead of stacking them on the newest
    # broadly-tagged story.
    scored.sort(key=lambda t: (-t[0], t[2]))
    return [o for _, o, _ in scored[:n]]


def _date_gap(a, b):
    """Days between two items, large when either date is unusable."""
    import datetime as _dt
    try:
        da = _dt.date.fromisoformat(str(a.get("date"))[:10])
        db = _dt.date.fromisoformat(str(b.get("date"))[:10])
        return (da - db).days
    except Exception:
        return 9999


def dedupe_same_event(a, b):
    """dedupe.same_event on two published items, fail-open."""
    try:
        import dedupe
        return dedupe.same_event(a.get("title", ""), a.get("key_fact", ""),
                                 b.get("title", ""), b.get("key_fact", ""))
    except Exception:
        return False


def _w3c_dt(raw):
    """A valid W3C datetime for sitemaps: full ISO 8601 with timezone when a time is
    present, else a bare YYYY-MM-DD date. A time WITHOUT a timezone (e.g.
    '2026-07-19T15:32:39') is NOT valid W3C datetime, which is what Search Console flags as
    'Invalid date' on <lastmod>. Returns UTC times with a trailing 'Z'."""
    import datetime as _dt
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        dt = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return raw[:10]  # last resort: keep just the date part (still valid W3C)
    if "T" not in raw:
        return dt.strftime("%Y-%m-%d")           # date-only input stays date-only
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)  # a naive time gets an explicit UTC zone
    return dt.isoformat().replace("+00:00", "Z")  # e.g. 2026-07-19T15:32:39Z


def render_news_sitemap(items, window_hours=48):
    """Google News sitemap: articles published within window_hours of the NEWEST item
    (relative, so the build is reproducible and never reads a wall clock). Every published
    story and daily edition qualifies as news. Regenerated on every deploy."""
    import datetime as _dt

    def _ts(it):
        raw = (it.get("published_utc") or (it.get("date", "") + "T00:00:00Z"))
        try:
            return _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None

    live = [it for it in items if not it.get("example") and _ts(it)]
    if not live:
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset '
                'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n</urlset>\n')
    newest = max(_ts(it) for it in live)
    cutoff = newest - _dt.timedelta(hours=window_hours)
    rows = []
    for it in sorted(live, key=_ts, reverse=True):
        if _ts(it) < cutoff:
            continue
        pub = _w3c_dt(it.get("published_utc") or it.get("date"))
        rows.append(
            f"  <url><loc>{ORIGIN}/articles/{esc(it['slug'])}</loc>\n"
            f"    <news:news><news:publication><news:name>{esc(NAME)}</news:name>"
            f"<news:language>en</news:language></news:publication>\n"
            f"    <news:publication_date>{esc(pub)}</news:publication_date>\n"
            f"    <news:title>{esc(it.get('title',''))}</news:title></news:news></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset '
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def render_feed(items):
    """RSS 2.0 feed of the published stories. The desk consumes RSS; now it emits it."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           "<channel>",
           f"<title>{esc(NAME)} &#8212; {esc(FAMILY)}</title>",
           f"<link>{ORIGIN}/news.html</link>",
           f"<description>{esc(DESC)}</description>",
           "<language>en-us</language>",
           f'<atom:link href="{ORIGIN}/feed.xml" rel="self" type="application/rss+xml"/>']
    for it in [i for i in items if not i.get("example")][:30]:
        url = f"{ORIGIN}/articles/{it['slug']}.html"
        pd = _rfc822(it)
        cats = "".join(f"<category>{esc(t)}</category>" for t in tags_for(it))
        out += ["<item>",
                f"<title>{esc(it.get('title') or '')}</title>",
                f"<link>{url}</link>",
                f'<guid isPermaLink="true">{url}</guid>',
                (f"<pubDate>{pd}</pubDate>" if pd else ""),
                f"<description>{esc(it.get('dek') or '')}</description>",
                cats,
                "</item>"]
    out += ["</channel>", "</rss>", ""]
    return "\n".join(x for x in out if x)


def fmt_usd(n):
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    a = abs(n)
    if a >= 1e12:
        return f"{sign}${a/1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}${a/1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}${a/1e6:.1f}M"
    if a >= 1e3:
        return f"{sign}${a/1e3:.0f}K"
    return f"{sign}${a:.0f}"


def load_flows():
    path = os.path.join(SITE, "data", "flows.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None


def load_chartmaster():
    path = os.path.join(SITE, "data", "chartmaster.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None


def load_pulse():
    path = os.path.join(SITE, "data", "pulse.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None



def tracking_match(story, rx):
    """True when a story is genuinely ABOUT a tracked storyline, not merely mentioning
    it. A title hit qualifies alone; otherwise two or more hits across title+key_fact.
    The dek and body never qualify: the dek is where comparative asides live and the
    body mentions everything, which is how one GENIUS Act article wore three chips.
    Module level so the canary can pin the regression (ported from sports/news)."""
    title = story.get("title") or ""
    if rx.search(title):
        return True
    text = " ".join([title, story.get("key_fact") or ""])
    return len(rx.findall(text)) >= 2

def destyle(text):
    """House style: no em/en dashes in site copy (model drafts sometimes use them).

    ENTITIES COUNT. This handled the literal characters only, and the gap was not
    theoretical: three em dashes shipped on a sister site written as &mdash;, including one
    in an H2, and a lint that counted literal characters reported zero. A dash a reader sees
    is a dash whatever it is spelled as in the source, so the numeric and named entity forms
    are normalised here too, before the literal pass runs on whatever they decode to.

        NEVER PUNCTUATE TWICE, AND NEVER REWRITE A QUOTATION (owner audit 2026-08-25).
    The old pass replaced every em dash with ", " unconditionally, so a dash that
    already followed punctuation produced the published string "government. , and",
    and a dash INSIDE a verbatim quotation was silently repunctuated, which changes
    what a named person is quoted as saying. House style still bans the desk's own
    dashes; a source's own words inside quotation marks are left exactly as spoken.
    """
    import re as _re
    s = str(text or "")
    for ent in ("&mdash;", "&#8212;", "&#x2014;", "&#X2014;"):
        s = s.replace(ent, "\u2014")
    for ent in ("&ndash;", "&#8211;", "&#x2013;", "&#X2013;"):
        s = s.replace(ent, "\u2013")

    def _clean(seg):
        # en dash between digits is a numeric range and stays a hyphen
        seg = _re.sub(r"(?<=\d)\s*\u2013\s*(?=\d)", "-", seg)
        seg = seg.replace("\u2013", "-")
        # an em dash following punctuation needs no comma of its own
        seg = _re.sub(r"(?<=[.,;:!?])\s*\u2014\s*", " ", seg)
        # ...nor does one immediately before punctuation or at the end
        seg = _re.sub(r"\s*\u2014\s*(?=[.,;:!?])", "", seg)
        seg = _re.sub(r"\s*\u2014\s*$", "", seg)
        seg = _re.sub(r"\s*\u2014\s*", ", ", seg)
        return _re.sub(r",\s*,", ",", seg)

    # split on double-quoted spans; odd indexes are quotations and are preserved
    parts = _re.split(r'("[^"]*"|\u201c[^\u201d]*\u201d)', s)
    return "".join(p if i % 2 else _clean(p) for i, p in enumerate(parts))



def resolve_retired(url):
    """Point a link at the canonical when it names a slug that has since been merged away.

    The daily editions cite the desk's OWN stories by URL, and those URLs are frozen in the
    edition's data the day it publishes. Merge a duplicate later and every edition that cited
    it is left pointing at a page that no longer builds. The redirect catches the reader, so
    nothing is broken, but a site that links to its own redirects has quietly decided the
    link check will always have a little noise in it, and a link check with acceptable noise
    stops being a link check.

    Resolving at render time rather than migrating the stored data is the point: the next
    merge fixes its own back-references, with no data migration to remember and no second
    place for the mapping to live."""
    m = re.match(r"^(?:https?://[^/]+)?/articles/(.+?)(?:\.html)?$", str(url or ""))
    if not m:
        return url
    canon = RETIRED_ARTICLES.get(m.group(1))
    return f"/articles/{canon}.html" if canon else url


def load_content():
    items = []
    if os.path.isdir(CONTENT):
        for fn in sorted(os.listdir(CONTENT)):
            if fn.startswith("_") or not fn.endswith(".json"):
                continue
            c = json.load(open(os.path.join(CONTENT, fn), encoding="utf-8"))
            c.setdefault("slug", slugify(c.get("title", "")))
            # Derived, not stored, so the 103 stories published before the flag existed are
            # labelled too. Editions are excluded: a daily wrap cites the day's stories and
            # is not a single-outlet claim.
            if "developing" not in c:
                c["developing"] = ((not _is_wrap(c)) and len(c.get("sources") or []) < 2
                                   and not c.get("also_reported_by"))
            items.append(c)
    # newest first by date then id
    # newest date first; within a date, the editor's rank (1 = lead); unranked (intro,
    # example) after the day's ranked stories
    items.sort(key=lambda c: (c.get("date", ""), -(c.get("rank") or 999), c.get("id", "")),
               reverse=True)
    return items


# ---- shared chrome -----------------------------------------------------------

def masthead(active, dateline, brand="site"):
    """Each page leads with its own identity: GoCheckMyCrypto (the site) everywhere by
    default; Crypto Cronkite (the anchor) on his news desk pages. The other identity always
    appears exactly once, small, so nothing repeats."""
    nav = "".join(
        f'<a href="{esc(href)}"{" class=active" if label == active else ""}>{esc(label)}</a>'
        for label, href in NAV)
    if brand == "cronkite":
        fam = (f'<span class="mh-family"><img class="mh-fam-mark" src="/assets/logo.svg" '
               f'alt="">{esc(FAMILY)}.com</span>')
        brand_row = f"""<a class="mh-brand" href="/news.html" style="margin-top:8px">
    <span class="badge-anim mh-badge"><img class="mh-mark coin" src="/assets/cronkite-coin.png" alt=""></span>
    <span class="mh-word">{esc(NAME)}</span>
    <span class="mh-slogan">{esc(SLOGAN)}</span>
  </a>"""
    else:
        fam = f'<a class="mh-family" href="{FAMILY_HUB}">A GoCheckMy site</a>'
        brand_row = f"""<a class="mh-brand" href="/index.html" style="margin-top:8px">
    <img class="mh-mark" src="/assets/logo.svg" alt="">
    <span class="mh-word">GoCheckMy<em class="mh-accent">Crypto</em></span>
    <span class="mh-slogan">Crypto, checked.</span>
  </a>"""
    # Motion pause/play control (WCAG 2.2.2). Lives in the masthead so it is present on
    # every page that carries motion (hero video, section videos, looping decorations).
    # Starts in the "playing" state; the script flips it and remembers the choice.
    motion_toggle = ('<button type="button" class="motion-toggle" data-motion '
                     'aria-pressed="false" aria-label="Pause motion">'
                     '<span class="mt-ico" aria-hidden="true"></span>'
                     '<span class="mt-txt">Motion</span></button>')
    return f"""<div class="top-rule"></div>
<header class="masthead"><div class="wrap">
  <div class="mh-top">
    {fam}
    <span class="mh-meta"><span class="mh-dateline">{esc(dateline)} &middot; Independent &middot; No hype</span>{motion_toggle}</span>
  </div>
  {brand_row}
</div></header>
<nav class="mh-nav" aria-label="Primary"><div class="wrap">{nav}</div></nav>"""


def _ticker_built(pulse):
    """What the ticker says BEFORE any live price arrives: the vintage of the numbers the
    build actually shipped. Marked stale when that vintage has outrun the refresh promise,
    so a blocked live fetch can never leave old numbers wearing a live label."""
    import datetime as _dt
    ts = ((pulse or {}).get("generated_utc") or "").strip()
    if not ts:
        return '<span class="stale">vintage unknown</span>'
    try:
        gen = _dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return "as of build"
    age_h = (_dt.datetime.now(_dt.timezone.utc) - gen).total_seconds() / 3600
    label = f"as of {gen.strftime('%H:%M UTC')}"
    return f'<span class="stale">{label}, stale</span>' if age_h > BOARD_FRESH_HOURS else label


def market_strip(pulse=None):
    """A live markets ticker, pre-filled server-side from the build's own pulse snapshot so the
    first paint is NEVER dashes; the reader's browser then overwrites with live CoinGecko data.
    Clearly labelled and separate from the verified news: a price is live factual data, not a
    story that went through the human gate. A failed client fetch quietly leaves the built
    values standing."""
    assets = {a.get("symbol"): a for a in ((pulse or {}).get("assets") or [])}

    def tick(cid, sym):
        a = assets.get(sym) or {}
        px = _price_fmt(a.get("price")) if a.get("price") else "--"
        chg = a.get("chg_24h_pct")
        chg_html = (f'<span class="chg {"up" if chg >= 0 else "down"}">{chg:+.1f}%</span>'
                    if chg is not None else '<span class="chg"></span>')
        return (f'<span class="tick" data-id="{cid}"><span class="sym">{sym}</span>'
                f'<span class="px">{esc(px)}</span>{chg_html}</span>')

    ticks = (tick("bitcoin", "BTC") + tick("ethereum", "ETH") +
             tick("solana", "SOL") + tick("ripple", "XRP"))
    mkt = (pulse or {}).get("market") or {}
    cap = mkt.get("total_mcap_usd")
    cap_px = fmt_tick(cap) if cap else "--"
    cap_chg = mkt.get("mcap_change_24h_pct")
    cap_chg_html = (f'<span class="chg {"up" if cap_chg >= 0 else "down"}">{cap_chg:+.1f}%</span>'
                    if cap_chg is not None else '<span class="chg"></span>')
    extras = ""
    if mkt.get("btc_dominance_pct"):
        extras += (f'<span class="tick"><span class="sym">BTC dom</span>'
                   f'<span class="px">{mkt["btc_dominance_pct"]:.1f}%</span>'
                   f'<span class="chg"></span></span>')
    fng = (pulse or {}).get("fng") or {}
    if fng.get("value") is not None:
        extras += (f'<span class="tick"><span class="sym">Fear &amp; Greed</span>'
                   f'<span class="px" data-fng>{fng["value"]} {esc((fng.get("label") or "").lower())}</span>'
                   f'<span class="chg"></span></span>')
    lev = ((pulse or {}).get("leverage") or {}).get("assets") or []
    btcl = next((a for a in lev if a.get("symbol") == "BTC"), None)
    if btcl and btcl.get("funding_8h_pct") is not None:
        f8 = btcl["funding_8h_pct"]
        extras += (f'<span class="tick"><span class="sym">BTC funding</span>'
                   f'<span class="px">{f8:+.4f}%/8h</span>'
                   f'<span class="chg"></span></span>')
    return f"""<section class="markets" id="markets"><div class="wrap" tabindex="0" role="region" aria-label="Live crypto markets ticker (scrollable)">
  <span class="lab">Markets &middot; <span class="mkt-asof" id="mktAsOf">{_ticker_built(pulse)}</span></span>
  {ticks}
  <span class="tick" id="mcap"><span class="sym">Total cap</span><span class="px">{esc(cap_px)}</span>{cap_chg_html}</span>
  {extras}
  <span class="note">Market data, not news. Not financial advice.</span>
</div>""" + """
<script>
(function(){
  var CG="https://api.coingecko.com/api/v3";
  function money(n){ if(n>=1e12)return "$"+(n/1e12).toFixed(2)+"T"; if(n>=1e9)return "$"+(n/1e9).toFixed(1)+"B";
    if(n>=1000)return "$"+Math.round(n).toLocaleString(); return "$"+n.toFixed(2); }
  function chg(el,p){ if(p==null){return;} var s=(p>=0?"+":"")+p.toFixed(1)+"%";
    el.textContent=s; el.className="chg "+(p>=0?"up":"down"); }
  fetch(CG+"/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd&include_24hr_change=true")
    .then(function(r){return r.json();}).then(function(d){
      document.querySelectorAll(".markets .tick[data-id]").forEach(function(t){
        var k=t.getAttribute("data-id"), v=d[k]; if(!v)return;
        var px=t.querySelector(".px");
        if(px.textContent!==money(v.usd)){
          px.textContent=money(v.usd);
          px.classList.remove("flash","flash-dn");void px.offsetWidth;
          px.classList.add((v.usd_24h_change||0)<0?"flash-dn":"flash");
          if(px.animate&&!matchMedia("(prefers-reduced-motion: reduce)").matches)
            px.animate([{transform:"translateY(-5px)",opacity:.2},{transform:"translateY(0)",opacity:1}],{duration:160,easing:"ease-out"});
        }
        chg(t.querySelector(".chg"), v.usd_24h_change);
      });
      // honest-data promise: the label ships as build-time data and is UPGRADED to live
      // only here, once real prices have actually arrived. A failed or blocked fetch
      // therefore leaves the build stamp standing instead of dressing old numbers as live.
      var as=document.getElementById("mktAsOf");
      if(as){var t=new Date();as.textContent="live, as of "+("0"+t.getHours()).slice(-2)+":"+("0"+t.getMinutes()).slice(-2);as.classList.remove("stale");}
    }).catch(function(){});
  fetch(CG+"/global").then(function(r){return r.json();}).then(function(d){
      var g=d.data||{}, m=document.getElementById("mcap"); if(!m)return;
      if(g.total_market_cap&&g.total_market_cap.usd) m.querySelector(".px").textContent=money(g.total_market_cap.usd);
      chg(m.querySelector(".chg"), g.market_cap_change_percentage_24h_usd);
    }).catch(function(){});
  // Fear & Greed refreshes once a day (alternative.me, keyless, CORS-open). Refresh it in
  // the browser like the prices above so the ticker is never a build behind the index.
  fetch("https://api.alternative.me/fng/?limit=1").then(function(r){return r.json();}).then(function(d){
      var f=(d.data||[])[0], el=document.querySelector(".markets [data-fng]"); if(!f||!el)return;
      el.textContent=f.value+" "+(f.value_classification||"").toLowerCase();
    }).catch(function(){});
})();
</script>
</section>"""


def newsletter():
    return f"""<section class="news" aria-label="Get the brief"><div class="wrap">
  <h2>Get the brief</h2>
  <p>The day's real crypto news, de-shilled and fact-checked, with the honest take. No hype,
     no moon calls. One email, on a cadence we can actually keep.</p>
  <form name="newsletter" method="POST" data-netlify="true" netlify-honeypot="company" action="/thanks.html">
    <input type="hidden" name="form-name" value="newsletter">
    <input class="hp" type="text" name="company" tabindex="-1" autocomplete="off" aria-hidden="true">
    <input type="email" name="email" placeholder="you@email.com" required aria-label="Email address">
    <button type="submit">Subscribe</button>
  </form>
  <p class="fine">Emails are stored by Netlify Forms, delivered to our company inbox, and used
     only to send the newsletter. Never sold, never shared. Unsubscribe anytime. See our
     <a href="/privacy.html">privacy policy</a>. Not financial advice.</p>
</div></section>"""


def trust_block():
    return f"""<section class="trust"><div class="wrap">
  <div class="sec-head"><h2>The desk's promise</h2><span class="bar"></span></div>
  <p class="trust-line">We aggregate stories from a wide range of primary and major sources,
  audit every one for credibility, and surface only what genuinely matters, with the shill
  and the hype stripped out. Sources are linked on every story, and nothing here is ever
  financial advice.</p>
</div></section>"""


def footer(brand="site"):
    """Brand-aware, matching the masthead doctrine: one identity per page. Site pages close
    as GoCheckMyCrypto (Cronkite named as the news desk); Cronkite's own pages close as the
    desk."""
    links = "".join(f'<a href="{esc(h)}">{esc(l)}</a>' for l, h in
                    [("About", "/about.html"), ("How we work", "/method.html"),
                     ("Standards & corrections", "/standards.html"), ("Archive", "/archive.html"),
                     ("Explainers", "/learn.html"),
                     ("How we make money", "/how-we-make-money.html"),
                     ("Accessibility", "/accessibility.html"),
                     ("Privacy", "/privacy.html"), ("Terms", "/terms.html"),
                     ("Contact", "mailto:desk@gocheckmycrypto.com"),
                     ("RSS", "/feed.xml")])
    if brand == "cronkite":
        who = f"{esc(NAME)}"
        note = ("Crypto Cronkite is GoCheckMyCrypto's independent news desk, built with one "
                "intention: get the stories right and keep the data honest. Whale Watch and "
                "Market Pulse show market data, not news. Sources are linked on every story.")
    else:
        who = f"{esc(FAMILY)}"
        note = ("GoCheckMyCrypto is an independent crypto site, built with one intention: get "
                "the stories right and keep the data honest. Crypto Cronkite is its news desk; "
                "Whale Watch and Market Pulse show market data, not news. Sources are linked "
                "on every story.")
    return f"""<footer class="site"><div class="wrap">
  <div class="frow">
    <div class="fbrand">{who}</div>
    <div class="flinks">{links}</div>
  </div>
  <p class="fnote"><b>{esc(NFA)}</b> {note}
    {who}<br>&copy; {YEAR} Go Check My Brands LLC.</p>
</div></footer>"""


_ASSET_VER = {}


def _fingerprint_assets(html):
    """Version every /assets/ URL with a content hash (site.css?v=ab12cd34ef). netlify.toml
    caches assets in the browser for 7 days; without this, a changed stylesheet leaves
    returning visitors on week-old CSS. The HTML itself always revalidates, so a new hash
    reaches every browser on the next page load."""
    import hashlib

    def ver(path):
        if path not in _ASSET_VER:
            f = os.path.join(HERE, "site", path.lstrip("/"))
            try:
                _ASSET_VER[path] = hashlib.md5(open(f, "rb").read()).hexdigest()[:10]
            except OSError:
                _ASSET_VER[path] = "0"
        return _ASSET_VER[path]

    return re.sub(r'((?:src|href)=")(/assets/[^"?#]+)(")',
                  lambda m: f'{m.group(1)}{m.group(2)}?v={ver(m.group(2))}{m.group(3)}', html)


# The motion layer's shared guard: reduced-motion strips every video to its poster and
# freezes the micro-details; otherwise videos play only while on screen and story cards
# fade up once. Inline (one request), transform/opacity only, no layout shift.
MOTION_JS = (
    '<script>(function(){var rm=matchMedia("(prefers-reduced-motion: reduce)").matches;'
    'var vids=[].slice.call(document.querySelectorAll(".motion-video"));'
    'var toggles=[].slice.call(document.querySelectorAll("[data-motion]"));'
    # Reduced-motion users: strip every video (zero bytes, zero decode); the toggle is
    # hidden by CSS, and the animation-kill media block freezes the decorative layer.
    'if(rm){vids.forEach(function(v){v.parentNode.removeChild(v)});return;}'
    'document.documentElement.classList.add("mjs");'
    # Manual pause state (WCAG 2.2.2), remembered across pages. Paused => freeze the CSS
    # motion layer (html.motion-off) and hold every video; the scroll observer will not
    # resume a video while paused.
    'var root=document.documentElement,KEY="cc_motion",paused=false;'
    'try{paused=localStorage.getItem(KEY)==="off"}catch(e){}'
    'function inView(v){var r=v.getBoundingClientRect();'
    'return r.bottom>0&&r.top<(window.innerHeight||0)&&r.right>0&&r.left<(window.innerWidth||0)}'
    'function sync(){toggles.forEach(function(b){b.setAttribute("aria-pressed",paused?"true":"false");'
    'b.setAttribute("aria-label",paused?"Play motion":"Pause motion")})}'
    'function apply(){if(paused){root.classList.add("motion-off");'
    'vids.forEach(function(v){if(!v.paused)v.pause()})}'
    'else{root.classList.remove("motion-off");'
    'vids.forEach(function(v){if(inView(v)&&v.paused)v.play().catch(function(){})})}sync()}'
    'toggles.forEach(function(b){b.addEventListener("click",function(){paused=!paused;'
    'try{localStorage.setItem(KEY,paused?"off":"on")}catch(e){}apply()})});'
    'if("IntersectionObserver" in window){'
    'var vo=new IntersectionObserver(function(es){es.forEach(function(e){var v=e.target;'
    'if(!paused&&e.isIntersecting&&e.intersectionRatio>=.12){if(v.paused)v.play().catch(function(){})}'
    'else if(!v.paused)v.pause()})},{threshold:.12});'
    'vids.forEach(function(v){if(!v.classList.contains("motion-lazy"))vo.observe(v)});'
    'var lz=vids.filter(function(v){return v.classList.contains("motion-lazy")});'
    'if(lz.length){var arm=function(){lz.forEach(function(v){vo.observe(v)});'
    'removeEventListener("scroll",arm)};addEventListener("scroll",arm,{passive:true})}'
    'var ro=new IntersectionObserver(function(es){es.forEach(function(e){'
    'if(e.isIntersecting){e.target.classList.add("in");ro.unobserve(e.target)}})},'
    '{rootMargin:"0px 0px -5% 0px"});'
    '[].slice.call(document.querySelectorAll(".reveal")).forEach(function(el){ro.observe(el)})}'
    'else{[].slice.call(document.querySelectorAll(".reveal")).forEach(function(el){el.classList.add("in")})}'
    'apply();'
    '})()</script>')


def shell(title, desc, active, body, dateline, body_class="", path="/", noindex=False,
          live_js=False, brand="site", og_type="website", schema_extra="", og_image=None,
          canonical_path=None):
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&family=Mrs+Saint+Delafield&display=swap" rel="stylesheet">')
    # ONE URL PER PAGE (2026-08-17, ported from news/sports). Netlify's Pretty URLs serve
    # every page at both /articles/foo and /articles/foo.html and rewrite internal links to
    # the extensionless form. A .html canonical meant Google crawled the linked URL, read a
    # canonical pointing elsewhere, and filed every story as "Alternate page with proper
    # canonical tag"; the same mismatch made og:url disagree with the URL people share, so
    # scrapers cached previews under a URL nobody sends. If Pretty URLs is ever disabled
    # this must revert with it, or every canonical points at a 404.
    # CANONICAL MAY POINT ELSEWHERE (owner SEO audit 2026-08-25): a composite page whose
    # unique content already lives on its own URL should name that URL as canonical
    # rather than compete with it. Everything else keeps the self-referential canonical.
    _cp = canonical_path or path
    url = ORIGIN + (_cp[:-5] if _cp.endswith(".html") else _cp)
    # one identity per page: site-brand pages carry the umbrella in the title tail and
    # social tags; Cronkite's own pages keep the desk name
    site_name = NAME if brand == "cronkite" else FAMILY
    if brand != "cronkite" and title.endswith(f"- {NAME}"):
        title = title[: -len(NAME)] + FAMILY
    robots = '<meta name="robots" content="noindex">\n' if noindex else f'<link rel="canonical" href="{esc(url)}">\n'
    beacon = ""
    if CF_ANALYTICS_TOKEN:
        beacon = ('\n<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                  f'data-cf-beacon=\'{{"token": "{CF_ANALYTICS_TOKEN}"}}\'></script>')
    livejs = ('\n<script defer src="/assets/pulse-live.js"></script>' if live_js else "")
    # accessibility: id the page's first <main> landmark as the skip-link target, and emit
    # the skip-link ONLY when such a target exists (list pages built from bare <section>s
    # get no dangling link). tabindex=-1 lets the non-interactive <main> receive focus so
    # the skip link actually moves keyboard focus (WCAG 2.4.1). The .skip-link CSS is in
    # site.css.
    skip = ""
    if re.search(r'<main(\s|>)', body):
        body = re.sub(r'<main(\s|>)', r'<main id="main" tabindex="-1"\1', body, count=1)
        skip = '<a class="skip-link" href="#main">Skip to main content</a>\n'
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}<link rel="alternate" type="application/rss+xml" title="{esc(NAME)} feed" href="/feed.xml">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{esc(og_type)}">{schema_extra}
<meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="{esc(site_name)}">
<meta property="og:image" content="{og_image or OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og_image or OG_IMAGE}">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="{THEME_COLOR}">
{fonts}
<link rel="stylesheet" href="/assets/site.css">
</head>
<body class="{esc(body_class)}">
{skip}{masthead(active, dateline, brand)}
{body}
{footer(brand)}{beacon}{livejs}
{MOTION_JS}
</body>
</html>"""
    return _fingerprint_assets(page)


# ---- article ----------------------------------------------------------------

# When a story cites the desk's own boards ("the desk's Whale Watch board showed..."),
# the mention becomes a link to that board. Escape-then-link, longest names first.
BOARD_LINKS = [("Whale Watch", "/flows.html"), ("Market Pulse", "/pulse.html"),
               ("Leverage board", "/pulse/leverage.html"),
               ("ETF flows board", "/pulse/etf.html"), ("ETF Flows board", "/pulse/etf.html")]


def _link_boards(escaped_text):
    for name, href in BOARD_LINKS:
        escaped_text = escaped_text.replace(esc(name), f'<a href="{href}">{esc(name)}</a>', 1)
    return escaped_text


def render_body(body):
    out = []
    for b in body or []:
        if isinstance(b, dict) and "h2" in b:
            out.append(f"<h2>{esc(b['h2'])}</h2>")
        else:
            out.append(f"<p>{_link_boards(esc(b))}</p>")
    return "\n".join(out)


def verdict_badge(verdict, item=None):
    """The verdict, plus a developing flag when the story rests on a single outlet.

    The two say different things and both matter. "Verified" means the verifier checked the
    claims against the sources that existed; "Developing" means only one outlet has carried
    it yet. A story can honestly be both, and showing only the first is the part that
    oversells."""
    out = ""
    if verdict == "VERIFIED":
        out = '<span class="badge verified">Verified</span>'
    elif verdict in ("NEEDS-HUMAN-REVIEW", "REVIEW"):
        out = '<span class="badge review">Editor reviewed</span>'
    if item is not None and item.get("developing"):
        out += ('<span class="badge developing" title="Only one outlet has carried this so '
                'far. The desk publishes it as developing rather than corroborated.">'
                'Developing, single source</span>')
    return out


def sig_block():
    """The desk's closing mark. It states what was DONE to the story, not how the desk is
    built: ranked, source-checked, independently reviewed. Owner's call, 2026-07-30, to drop
    the "automated newsroom" caption and the "passed our automated editorial review" framing.

    The claim stays literally true, which is the only thing that matters here. The method
    link is kept on "independent review pass" so a reader can still see what the phrase
    means, and the stamp's visible and accessible text match the caption rather than saying
    something the caption no longer says.

    Stamp reads SOURCES VERIFIED / ON THE RECORD (owner's pick, 2026-07-30). Both halves
    describe what was done to the story and neither describes how the desk is built, which
    is the whole point: nothing here should help anyone reproduce the process."""
    return """<div class="sigrow">
  <div class="sig">
    <span class="sig-script">Crypto Cronkite</span>
    <span class="sig-cap">The Crypto Cronkite Desk</span>
    <span class="sig-attest">Ranked, source-checked, and verified by the desk's
      <a href="/method.html">independent review pass</a>.</span>
  </div>
  <div class="stamp" role="img" aria-label="Sources verified, on the record stamp">
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" stroke-width="2"/>
      <!-- Stamp J (owner's pick, 2026-07-30): a solid accent disc fills the ring and the
           GoCheckMy check is knocked out of it, so the mark IS the seal rather than a small
           device sitting inside one. The knockout uses --card so it inverts with the theme;
           a hardcoded white would vanish into the dark-mode disc. This replaces the dashed
           inner ring, which the disc now occupies. -->
      <circle cx="60" cy="60" r="45" fill="currentColor"/>
      <defs><path id="stamparc" d="M60,60 m-51,0 a51,51 0 1,1 102,0 a51,51 0 1,1 -102,0"/></defs>
      <text font-size="9.4" letter-spacing="2.2" fill="currentColor"
        font-family="IBM Plex Mono,monospace" font-weight="600">
        <textPath href="#stamparc" startOffset="2%">SOURCES VERIFIED</textPath>
        <textPath href="#stamparc" startOffset="55%">ON THE RECORD</textPath>
      </text>
      <path d="M27 62 L49 85 L93 32" fill="none" stroke="var(--card)" stroke-width="11"
        stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
</div>"""


def share_row(url, title):
    """Share buttons for growing the audience: LinkedIn and X get the story with one click,
    copy-link covers everything else. Plain links, no tracking scripts."""
    u, t = quote(url, safe=""), quote(title, safe="")
    return f"""<div class="sharerow">
  <span class="share-lab">Share this story</span>
  <a class="share-btn" href="https://www.linkedin.com/sharing/share-offsite/?url={u}"
     target="_blank" rel="noopener">LinkedIn</a>
  <a class="share-btn" href="https://twitter.com/intent/tweet?text={t}&amp;url={u}"
     target="_blank" rel="noopener">X</a>
  <button class="share-btn" type="button" data-url="{esc(url)}">Copy link</button>
</div>
<script>
(function(){{
  var b=document.querySelector('.sharerow button');if(!b)return;
  b.addEventListener('click',function(){{
    var u=b.getAttribute('data-url');
    function ok(){{b.textContent='Copied';setTimeout(function(){{b.textContent='Copy link';}},1600);}}
    function fb(){{var t=document.createElement('textarea');t.value=u;t.style.position='fixed';t.style.opacity='0';
      document.body.appendChild(t);t.select();try{{document.execCommand('copy');ok();}}catch(e){{}}
      document.body.removeChild(t);}}
    if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText(u).then(ok,fb);}}else{{fb();}}
  }});
}})();
</script>"""


def render_article(item, all_items=None):
    dateline = fmt_date(item.get("date"))
    badge = verdict_badge(item.get("verdict"), item)
    tag = f'<span class="tag">{esc(item.get("category","news"))}</span>' if item.get("category") else ""
    topic_chips = "".join(f'<span class="tag topic">{esc(t)}</span>' for t in tags_for(item))
    ribbon = ""
    if item.get("example"):
        ribbon = ('<div class="callout"><b>Example, not a real story.</b> This page shows the '
                  'format Crypto Cronkite publishes in. The content is illustrative only.</div>')
    if item.get("update_of"):
        prev = next((i for i in (all_items or []) if i.get("slug") == item["update_of"]), None)
        # ONLY CLAIM A LINEAGE THE PAGES ACTUALLY SHARE (owner SEO audit 2026-08-25). This
        # callout tells the reader, in the desk's own voice, that the piece develops an
        # earlier story, and autopilot writes update_of automatically from a fuzzy
        # matcher. An audit of the 58 live edges found roughly 30 that share no proper
        # noun and under 0.50 headline overlap: a Trezor shipping breach "developing" a
        # BitMEX shutdown, a UK tax-letter story "developing" a New York lawsuit against
        # Kalshi. Each one is a false statement to the reader and an internal link that
        # teaches a crawler the wrong thing. The edge still rides in the data (nothing is
        # deleted); it simply is not ASSERTED unless the two pages visibly share the
        # story, which is a deterministic check, not a judgement call.
        if prev and _same_storyline(item, prev):
            ribbon += (f'<div class="callout"><b>Update.</b> This story develops our earlier '
                       f'reporting: <a href="/articles/{esc(item["update_of"])}">'
                       f'{esc(prev.get("title"))}</a>.</div>')
    # A correction is a feature of an honest desk (standards page): show it plainly. The
    # aging loop (corrections.py) and manual reconciliations both write item["corrected"].
    if (item.get("corrected") or "").strip():
        ribbon += (f'<div class="callout corrected"><b>Correction.</b> '
                   f'{esc(destyle(item["corrected"]))}</div>')
    # A CONSOLIDATION is a structural error, not a factual one: the desk published the same
    # development more than once and merged them. It gets its own label rather than reusing
    # Correction, because "Correction" has to keep meaning "we got a fact wrong" or it stops
    # meaning anything. Same instinct as the corrections policy, applied one level up.
    if (item.get("consolidated") or "").strip():
        ribbon += (f'<div class="callout"><b>Editor\'s note.</b> '
                   f'{esc(destyle(item["consolidated"]))}</div>')
    # THE BOUNDARY PANEL sits ABOVE the prose, unlike every other panel on the page, because
    # it answers the only question a reader of a security advisory has before they will read
    # anything else: am I affected. Values are the vendor's own words, copied through the
    # pipeline by assignment (writer._carry_boundary) and never restated in prose, so there
    # is no sentence here that can come back inverted. See boundary.py.
    bnd = ""
    brows = boundary.rows(item.get("boundary") or {})
    if brows:
        lis = ""
        for label, value in brows:
            cell = (f'<a href="{esc(value)}" rel="nofollow noopener">{esc(value)}</a>'
                    if label == "Advisory" else esc(value))
            lis += f'<div class="brow"><dt>{esc(label)}</dt><dd>{cell}</dd></div>'
        bnd = (f'<section class="boundary" aria-labelledby="bnd-h">'
               f'<h2 id="bnd-h">Who this affects</h2>'
               f'<p class="mut">Quoted from the advisory linked below. The desk does not '
               f'restate it.</p><dl>{lis}</dl></section>')
    key = ""
    if item.get("key_fact"):
        key = (f'<div class="keyfact"><span class="lab">The key fact</span>'
               f'<p>{esc(item["key_fact"])}</p></div>')
    bottom = ""
    if (item.get("bottom_line") or "").strip():
        bottom = (f'<div class="bottomline"><span class="lab">The Bottom Line</span>'
                  f'<p>{esc(item["bottom_line"])}</p></div>')
    take = ""
    if (item.get("human_take") or "").strip():
        take = (f'<div class="take"><span class="lab">The take</span>'
                f'<p>{esc(item["human_take"])}</p></div>')
    srcs = item.get("sources") or []
    src_html = ""
    if srcs:
        def _src_li(s):
            url = resolve_retired(s.get("url", ""))
            # THE DESK'S OWN INSTRUMENT IS NOT A LINK (owner audit 2026-08-25). A
            # board-verified market story cites desk://market-boards, which rendered in
            # the Sources block as a dead anchor reading "market-boards". It is a real
            # source and it should say what it is, in plain words, and point at the
            # boards the reader can actually see.
            if url.startswith("desk://"):
                return ('<li>The desk\'s own market boards, measured this run '
                        '(<a href="/">see the live boards</a>)</li>')
            return (f'<li><a href="{esc(url)}" rel="nofollow">'
                    f'{esc(source_label(s))}</a></li>')
        lis = "".join(_src_li(s) for s in srcs)
        src_html = f'<div class="sources"><h2>Sources</h2><ol>{lis}</ol></div>'
    also = [str(x) for x in (item.get("also_reported_by") or []) if str(x).strip()]
    if also:
        src_html += (f'<p class="also-reported">Also reported by '
                     f'{esc(", ".join(also[:8]))}. The desk cites only the pages it drew '
                     f'facts from; these outlets independently carried the same development.</p>')
    rel_html = ""
    for rel in related_stories(item, all_items or []):
        rel_html += (f'<li><a href="/articles/{esc(rel["slug"])}">{esc(rel.get("title"))}</a>'
                     f'<span class="mut"> &middot; {fmt_when(rel)}</span></li>')
    if rel_html:
        rel_html = f'<div class="related"><h2>Related stories</h2><ul>{rel_html}</ul></div>'
    # THE DESK'S OWN ARCHIVE, RENDERED (owner directive 2026-08-25). Every outlet can
    # report today's event; only this desk can show what it published about the same
    # development earlier, and which other stories it has run on this subject. Both
    # modules derive at render time from items already on disk: no fetching, no model
    # call, no change to wrap or ingest, and the whole archive gains them on the next
    # build. Measured coverage on the live corpus: timeline 14% of articles (the strict
    # claim), More-on 76% (the honest weaker one).
    if not (item.get("example") or _is_wrap(item)
            or item.get("category") == "daily edition"):
        # editions summarise stories; they are not chapters of one, and the example page
        # is a format demo. Neither gets an archive module (owner check 2026-08-25).
        rel_html = (render_board_panel(item)
                    + render_timeline(item, all_items or [])
                    + render_more_on(item, all_items or [])
                    + rel_html)
    # consistent desk attribution (the byline is the desk, never a person): aggregators and
    # Google News check for a stable byline, and this reads honestly as a newsroom, not a
    # named human author
    # ONE tool module, only when the headline says the story is about it. Here
    # the destination is usually this site's own cold-storage explainer, so it
    # is an internal route rather than a cross-site one, but it still carries
    # attribution so the family rollup counts it the same way.
    tool_html = ""
    if _fam is not None:
        _m = _fam.tool_module("crypto", item.get("slug", ""), _fam.story_text(item))
        if _m:
            tool_html = (f'<aside class="tool-module"><p class="tm-k">Practical next step</p>'
                         f'<p><a href="{esc(_m["url"])}" rel="noopener">{esc(_m["text"])}</a>'
                         f'. Free, no account.</p></aside>')
    author = esc(item.get("author", "Crypto Cronkite"))
    if author in ("Crypto Cronkite", "Crypto Cronkite Desk"):
        author = "the Crypto Cronkite Desk"
    body = f"""<main class="wrap narrow">
  <article class="article">
    <div class="ey">{badge}{tag}{topic_chips}<span class="dateline">{fmt_when(item)}</span></div>
    <h1>{esc(item.get("title"))}</h1>
    {f'<p class="dek">{esc(item["dek"])}</p>' if item.get("dek") else ""}
    <div class="byline">By {author}</div>
    {ribbon}
    {bnd}
    <div class="prose">{render_body(item.get("body"))}</div>
    {key}
    {take}
    {bottom}
    <p class="signoff">{esc(SLOGAN)}</p>
    {sig_block()}
    {share_row(ORIGIN + f"/articles/{item['slug']}", item.get("title") or "")}
    {tool_html}
    {src_html}
    {rel_html}
    <p class="nfa">{esc(NFA)}</p>
  </article>
</main>"""
    title = f'{item.get("title")} - {NAME}'
    desc = item.get("dek") or (item.get("body", [""])[0] if item.get("body") else DESC)
    url = f"{ORIGIN}/articles/{item['slug']}.html"
    # per-article OG card: rendered into the publish output at build time by
    # _render_og_card (pure-Python Pillow, so it runs on Netlify). og:image points at it
    # when the render succeeded; a failed render fell back to the site-wide card already.
    card_out = os.path.join(PUBLISH, "og", f"{item['slug']}.png")
    og_image = f"{ORIGIN}/og/{item['slug']}.png" if os.path.exists(card_out) else OG_IMAGE
    schema = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "NewsArticle", "headline": item.get("title"),
         "description": item.get("dek") or "", "url": url, "mainEntityOfPage": url,
         "image": og_image,
         "datePublished": item.get("published_utc") or item.get("date"),
         "dateModified": item.get("published_utc") or item.get("date"),
         "author": {"@type": "Organization", "name": NAME, "url": ORIGIN + "/news.html"},
         # ONE PUBLISHER IDENTITY (crawl audit 2026-08-25): the @id is the same node the
         # homepage Organization block defines, so a crawler resolves both to one entity.
         # The full object stays because Google News wants a sized publisher logo here.
         "publisher": {"@type": "Organization", "@id": ORIGIN + "/#publisher",
                       "name": FAMILY, "url": ORIGIN + "/",
                       "logo": {"@type": "ImageObject", "url": ORIGIN + "/publisher-logo-512.png",
                                "width": 512, "height": 512}}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Latest", "item": ORIGIN + "/news.html"},
            {"@type": "ListItem", "position": 2, "name": item.get("title"), "item": url}]}
    ]}, ensure_ascii=False)
    return shell(title, desc if isinstance(desc, str) else DESC, "Latest", body, dateline.upper(),
                 path=f"/articles/{item['slug']}.html", noindex=bool(item.get("example")),
                 brand="cronkite", og_type="article", og_image=og_image,
                 schema_extra=f'\n<script type="application/ld+json">{schema}</script>')


# ---- cards / index / archive -------------------------------------------------

def card(item):
    badge = verdict_badge(item.get("verdict"), item)
    tag = f'<span class="tag">{esc(item.get("category","news"))}</span>' if item.get("category") else ""
    tag += "".join(f'<span class="tag topic">{esc(t)}</span>' for t in tags_for(item)[:2])
    href = f'/articles/{esc(item["slug"])}.html'
    summ = item.get("dek") or (item.get("body", [""])[0] if item.get("body") else "")
    if isinstance(summ, dict):
        summ = summ.get("h2", "")
    nsrc = len(item.get("sources") or [])
    return f"""<article class="card reveal">
  <div class="row">{badge}{tag}</div>
  <h3><a href="{href}">{esc(item.get("title"))}</a></h3>
  <p class="summary">{esc(summ[:180])}</p>
  <div class="foot"><span class="dateline">{fmt_when(item)}</span>
    <span class="src">{nsrc} source{"s" if nsrc != 1 else ""}</span></div>
</article>"""


def desk_strip():
    # Home-only anchor-desk strip: the Crypto Cronkite portrait coin (the YouTube channel
    # face) beside the desk line. The masthead checkmark badge stays the site mark; this is
    # the anchor's face at the top of the front page. No link yet (channel tie post-launch).
    return f"""<section class="desk" aria-label="The news desk"><div class="wrap">
  <video class="desk-coin motion-video" autoplay muted loop playsinline preload="none"
    poster="/assets/cronkite-coin.png" aria-hidden="true" tabindex="-1" width="132" height="132">
    <source src="/assets/hero/coin-loop.webm" type="video/webm">
    <source src="/assets/hero/coin-loop.mp4" type="video/mp4"></video>
  <div class="desk-copy">
    <span class="kicker">From the desk</span>
    <p>{esc(DESK_LINE)}</p>
  </div>
</div></section>"""


_NOW_CACHE = None


def _build_now():
    """Build-time 'now' for the editions staleness rule, ported from the sports desk.
    SITE_BUILD_NOW (ISO timestamp) overrides the wall clock so a build stays
    reproducible when it has to be."""
    import datetime as _dt
    global _NOW_CACHE
    if _NOW_CACHE is None:
        env = os.environ.get("SITE_BUILD_NOW", "")
        try:
            _NOW_CACHE = _dt.datetime.fromisoformat(env.replace("Z", "+00:00"))
        except ValueError:
            _NOW_CACHE = _dt.datetime.now(_dt.timezone.utc)
    return _NOW_CACHE


def _fresh_hours(item, now):
    import datetime as _dt
    try:
        ts = (item.get("published_utc") or "").replace("Z", "+00:00")
        return (now - _dt.datetime.fromisoformat(ts)).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return 1e9


def _blink_when(item):
    """Edition timestamp with a clock-style blinking colon (CSS animates .tick-colon)."""
    t = fmt_when(item)
    if ":" in t:
        head, rest = t.split(":", 1)
        return f'{head}<span class="tick-colon">:</span>{rest}'
    return t


def _is_wrap(item):
    return str(item.get("id", "")).startswith("wrap-")


BL_FRESH_HOURS = 24  # an edition's read is a read of THAT day; see current_bottom_line


def current_bottom_line(items, max_age_hours=BL_FRESH_HOURS):
    """The newest edition read, or None when it has aged out. ONE selector, two callers.

    There was no staleness rule at all here, and the cost was visible on the front page: on
    2026-07-31 the hero still carried the July 28 Evening Brief telling readers to watch an
    FOMC decision that had happened two days before the build. Both call sites took wraps[0]
    unconditionally, and the only edition-recency rule in the file is relative (the archive's
    sorted({dates})[:2]) so it can never expire and governs a different surface anyway.

    AGED AGAINST THE NEWEST CONTENT, NOT A WALL CLOCK. Every reader-facing date in this build
    is derived from the content (see build(): "never a wall clock"), because a build has to be
    reproducible: reading the clock would make two builds of the same commit differ. The
    newest item is the right reference regardless. What makes a Bottom Line stale is not the
    passage of time as such, it is the desk having published things since that the read does
    not account for. If the desk went completely silent the wrap IS the newest item, its age
    is zero, and it stands, which is correct: it remains the last thing the desk said, and
    there is no newer reporting for it to be out of step with.

    An empty slot beats a three-day-old brief framing a past decision as upcoming."""
    wraps = [i for i in items if _is_wrap(i) and i.get("bottom_line") and not i.get("example")]
    if not wraps:
        return None
    ed = wraps[0]  # load_content sorts newest-first; wraps outrank stories within a date
    ref = max((d for d in (_parse_utc(i) for i in items if not i.get("example")) if d),
              default=None)
    when = _parse_utc(ed)
    if ref and when and (ref - when).total_seconds() / 3600 > max_age_hours:
        return None
    return ed


def bottom_line_card(items):
    """THE BOTTOM LINE (owner directive 2026-07-15): the desk's signature element, the
    newest edition's 3-5 sentence read, refreshed every slot (and by breaking runs).
    Rendered as the compact card that rides beside the lead story (owner directive
    2026-07-17: lead first, Bottom Line to its right, same arrangement as the front
    page), reusing the home hero's card styling."""
    ed = current_bottom_line(items)
    if not ed:
        return ""
    name = esc((ed.get("title") or "").split(":")[0].strip() or "The Daily Edition")
    return (f'<a class="hero-bl news-bl" href="/articles/{esc(ed["slug"])}.html">'
            f'<span class="hero-kick"><span class="kicker">The Bottom Line</span></span>'
            f'<span class="hero-bl-src">{name} &middot; {_blink_when(ed)}</span>'
            f'<span class="hero-bl-read">{esc(ed["bottom_line"])}</span>'
            f'<span class="hero-bl-more">Read the full edition &rarr;</span></a>')


def render_bottom_line_history(items, dateline):
    """/bottom-line.html: the browsable history of the daily reads, one entry per
    edition, newest first. Each edition's read is preserved with its edition forever."""
    wraps = [i for i in items if _is_wrap(i) and i.get("bottom_line") and not i.get("example")]
    rows = []
    for ed in wraps:
        name = esc((ed.get("title") or "").split(":")[0].strip())
        rows.append(f"""<div class="bl-hist">
      <div class="bl-head"><span class="bl-label">{name}</span>
        <span class="dateline">{fmt_when(ed)}</span></div>
      <p class="bl-read">{esc(ed["bottom_line"])}</p>
      <p style="margin:6px 0 0"><a href="/articles/{esc(ed['slug'])}.html">The full edition &rarr;</a></p>
    </div>""")
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">The Bottom Line</span>
  <h1>The daily reads</h1>
  <p class="lede">Three times a day the desk closes its edition with The Bottom Line: what
     happened, why it mattered, and what the calendar says comes next. Synthesis of the
     desk's verified reporting, never a prediction and never advice. Every read is kept.</p>
  {"".join(rows) if rows else '<p class="lede">The first edition lands soon.</p>'}
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"The Bottom Line - {NAME}", "The desk's daily reads: what happened, why it "
                 "mattered, and what comes next. Synthesis, never advice.",
                 "The Bottom Line", body, dateline, path="/bottom-line.html", brand="cronkite")



# The beats the desk actually covers, with a standing description. A hub page whose only
# content is links is a page with nothing of its own to say, which is what Google reports
# as "crawled, currently not indexed" (owner SEO audit 2026-08-25).
NEWS_BEATS = [
    ("Regulation and enforcement", ("regulation", "enforcement", "policy", "legal", "sec", "cftc"),
     "Rulemaking, enforcement actions and court decisions, from the agencies' own filings "
     "wherever the desk can read them. The desk reports what a regulator did, not what it "
     "is rumoured to be considering."),
    ("Market structure", ("markets", "etf", "etfs", "flows", "derivatives", "liquidity", "price"),
     "Prices, ETF flows, leverage and liquidations, measured on the desk's own boards as "
     "well as reported. Where a number comes from the desk's instruments, the story says so."),
    ("Protocol and infrastructure", ("protocol", "upgrade", "ethereum", "bitcoin", "layer2",
                                     "network", "mining"),
     "Upgrades, forks, client releases and the plumbing beneath them, sourced to the "
     "protocol teams' own announcements where they exist."),
    ("Security and exploits", ("security", "hack", "exploit", "breach", "scam", "fraud"),
     "Exploits, breaches and the money that moved, cross-checked against an independent "
     "exploit ledger so a missed incident shows up as a gap, not silence."),
    ("Business and institutions", ("business", "company", "exchange", "institutional",
                                  "funding", "adoption", "stablecoin"),
     "Exchanges, issuers, banks and the institutions moving into the asset class: what was "
     "announced, by whom, and what was actually signed."),
]


def _beat_of(item):
    t = set(tags_for(item)) | {(item.get("category") or "").lower()}
    text = " ".join([item.get("title") or "", item.get("key_fact") or ""]).lower()
    for name, keys, _desc in NEWS_BEATS:
        if t & set(keys) or any(k in text for k in keys):
            return name
    return None


def _news_beats(live, per=6):
    """The corpus grouped by beat, each with a standing description of what it covers."""
    buckets = {}
    for i in sorted(live, key=lambda x: x.get("published_utc") or x.get("date") or "",
                    reverse=True):
        b = _beat_of(i)
        if b:
            buckets.setdefault(b, []).append(i)
    secs = []
    for name, _keys, desc in NEWS_BEATS:
        rows = buckets.get(name) or []
        if len(rows) < 3:
            continue
        lis = "".join(
            f'<li><a href="/articles/{esc(i["slug"])}">{esc(i.get("title"))}</a>'
            f'<span class="mut"> &middot; {fmt_when(i)}</span></li>' for i in rows[:per])
        secs.append(f'<section class="sec"><div class="wrap">'
                    f'<div class="sec-head"><h2>{esc(name)}</h2><span class="bar"></span></div>'
                    f'<p class="lede">{esc(desc)}</p>'
                    f'<p class="mut">{len(rows)} stories on this beat.</p>'
                    f'<ul class="link-list">{lis}</ul></div></section>')
    return "".join(secs)


def _news_threads(live, max_threads=6):
    """Ongoing storylines, built from the desk's OWN declared update chains.

    This is the part no aggregator can copy: the desk knows which of its stories develop
    which, so a reader can follow a thread from its origin instead of meeting each chapter
    as an unconnected page."""
    by_slug = {i.get("slug"): i for i in live}
    kids = {}
    for i in live:
        p = i.get("update_of")
        if p and p in by_slug and _same_storyline(i, by_slug[p]):
            kids.setdefault(p, []).append(i)
    threads = sorted(kids.items(), key=lambda kv: -len(kv[1]))[:max_threads]
    if not threads:
        return ""
    out = []
    for root, children in threads:
        chain = [by_slug[root]] + sorted(children, key=lambda x: x.get("date") or "")
        lis = "".join(f'<li><a href="/articles/{esc(c["slug"])}">{esc(c.get("title"))}</a>'
                      f'<span class="mut"> &middot; {fmt_when(c)}</span></li>' for c in chain)
        out.append(f'<div class="thread"><h3>{esc(by_slug[root].get("title"))}</h3>'
                   f'<ol class="link-list">{lis}</ol></div>')
    return ('<section class="sec"><div class="wrap">'
            '<div class="sec-head"><h2>Storylines the desk is following</h2>'
            '<span class="bar"></span></div>'
            '<p class="lede">Developments the desk has covered more than once, in order. '
            'Each thread is the desk\'s own reporting on one story as it moved.</p>'
            + "".join(out) + '</div></section>')


def _news_collection_schema(live):
    """CollectionPage + ItemList so the hub declares what it is."""
    newest = sorted(live, key=lambda x: x.get("published_utc") or "", reverse=True)[:10]
    data = {"@context": "https://schema.org", "@type": "CollectionPage",
            "name": f"Crypto news by beat and storyline - {NAME}",
            "url": ORIGIN + "/news",
            "mainEntity": {"@type": "ItemList", "itemListElement": [
                {"@type": "ListItem", "position": n + 1,
                 "url": f"{ORIGIN}/articles/{i.get('slug')}",
                 "name": i.get("title")} for n, i in enumerate(newest)]}}
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'

def render_news(items, dateline, pulse=None):
    live = [i for i in items if not i.get("example")]
    bl = bottom_line_card(live)
    live = [i for i in live if not _is_wrap(i)]  # editions speak through the Bottom Line card
    if live:
        lead = live[0]
        rest = live[1:]
        badge = verdict_badge(lead.get("verdict"), lead)
        lead_tags = tags_for(lead)
        tag = (f'<span class="tag topic">{esc(lead_tags[0])}</span>' if lead_tags
               else f'<span class="tag">{esc(lead.get("category", "news"))}</span>')
        lead_inner = f"""<span class="kicker">Lead story</span> {tag}
    <h1><a href="/articles/{esc(lead["slug"])}.html" style="color:inherit">{esc(lead.get("title"))}</a></h1>
    {f'<p class="dek">{esc(lead["dek"])}</p>' if lead.get("dek") else ""}
    <div class="meta">{badge}<span class="dateline">{fmt_when(lead)}</span>
      <a href="/articles/{esc(lead["slug"])}.html">Read the story &rarr;</a></div>"""
        # Lead first, The Bottom Line beside it (front-page arrangement); without an
        # edition the lead simply spans the row.
        lead_html = (f"""<section class="lead"><div class="wrap"><div class="news-grid">
    <div class="news-lead">{lead_inner}</div>
    {bl}
  </div></div></section>""" if bl else f"""<section class="lead"><div class="wrap">
    {lead_inner}
  </div></section>""")
        grid = ""
        if rest:
            grid = (f'<section class="sec"><div class="wrap"><div class="sec-head" id="latest">'
                    f'<h2>More from the desk</h2><span class="bar"></span></div>'
                    f'<div class="grid">{"".join(card(i) for i in rest)}</div></div></section>')
    else:
        lead_html = f"""<section class="lead"><div class="wrap">
    <span class="kicker">The desk is live</span>
    <h1>Honest crypto news, on a cadence we can keep.</h1>
    <p class="dek">{esc(DESK_LINE)} The first published brief lands here. In the meantime, read how
       the desk works and why you can trust the byline.</p>
    <div class="meta"><a href="/method.html">How we work &rarr;</a>
      <a href="/about.html">Why this exists &rarr;</a></div>
  </div></section>"""
        grid = ('<section class="sec"><div class="wrap"><div class="empty">'
                '<span class="k">No brief published yet</span>'
                '<p style="margin:.6em 0 0">Every story here will have been ranked by an AI editor, '
                'checked against its sources by an independent AI verifier, and approved by a human. '
                'That gate is the whole point, so we would rather publish nothing than publish junk.</p>'
                '</div></div></section>')
    # news first: lead story (Bottom Line beside it), then the rest of the day's stories;
    # the promise strip and the whale teaser read as the footer beats, never above the
    # journalism
    # the ticker and desk strip are secondary chrome; the news itself is the main landmark
    body = (market_strip(pulse) + desk_strip() + '<main class="news-main">' + lead_html + grid
            + _news_beats(live) + _news_threads(live)
            + trust_block() + flow_teaser() + newsletter() + '</main>')
    return shell(f"Crypto news by beat and storyline - {NAME}",
                 "Every story the desk has published, grouped by beat and by the "
                 "storylines it follows, with what each beat covers and how the desk "
                 "verifies it.",
                 "Latest", body, dateline, path="/news.html", brand="cronkite",
                 schema_extra=_news_collection_schema(live))



def home_schema():
    """Organization + WebSite for the homepage.

    Article pages have carried NewsArticle and BreadcrumbList since launch and /news now
    carries CollectionPage, but the HOMEPAGE, the page a crawler reaches first and the one
    that should establish who publishes everything else, emitted no structured data at all
    (crawl audit 2026-08-25). The publisher block here is the same identity the article
    schema names, so the two agree."""
    org = {"@type": "NewsMediaOrganization", "@id": ORIGIN + "/#publisher",
           "name": FAMILY, "url": ORIGIN + "/",
           "logo": {"@type": "ImageObject", "url": ORIGIN + "/publisher-logo-512.png",
                    "width": 512, "height": 512},
           "description": FAMILY_DESC}
    site = {"@type": "WebSite", "@id": ORIGIN + "/#website", "url": ORIGIN + "/",
            "name": FAMILY, "publisher": {"@id": ORIGIN + "/#publisher"}}
    return ('<script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@graph": [org, site]},
                         ensure_ascii=False) + "</script>")

def render_home(items, flows, pulse, cm, dateline):
    """The GoCheckMyCrypto front door, built for the RETURNING reader: live markets strip,
    today's headlines, the storylines the desk is tracking, then the four desks. The brand
    pitch lives below the information, not above it."""
    live = [i for i in (items or []) if not i.get("example") and not _is_wrap(i)]
    desk_stat = f"{len(live)} verified stories on the desk" if live else "The first brief lands soon"
    cards = []
    cards.append(f"""<a class="dash-card home-card" href="/news.html">
      <img class="dash-hero-img" src="/assets/crypto-cronkite-banner.png" alt="Crypto Cronkite: market news and on-chain insights" loading="lazy">
      <span class="lab">Latest news</span>
      <span class="dash-stat" style="font-size:19px">{esc(desk_stat)}</span>
      <p class="pc-note">The day's real crypto stories with the paid promotion stripped out,
      every source linked. And that's the way it is.</p>
      <span class="dash-open">Read the latest &rarr;</span></a>""")
    ww_line = "Follow the money on-chain."
    if flows and not flows.get("example") and flows.get("volatile"):
        wnet = flows["volatile"].get("net_usd", 0)
        # Show the magnitude, not a signed value: the direction word carries the sign, so a
        # bare "-$434.5M net onto exchanges" reads ambiguously. Magnitude + word is unambiguous.
        ww_line = (f"{fmt_usd(abs(wnet))} net {'off' if wnet >= 0 else 'onto'} exchanges in the "
                   f"last {_win_phrase(flows.get('window_hours', 24))}.")
    cards.append(f"""<a class="dash-card home-card" href="/flows.html">
      <img class="dash-hero-img" src="/assets/whale-watch-banner.png" alt="Whale Watch: market pulse, on-chain insights" loading="lazy">
      <span class="lab">Whale Watch</span>
      <span class="dash-stat" style="font-size:19px">{esc(ww_line)}</span>
      <p class="pc-note">Where the whales are moving money: onto exchanges or into cold
      storage, aggregated so the signal beats the noise.</p>
      <span class="dash-open">Follow the money &rarr;</span></a>""")
    fng = (pulse or {}).get("fng") or {}
    mp_line = "Seven dashboards, explained in plain language."
    if fng:
        mp_line = f"Fear &amp; Greed today: {fng.get('value', '?')}, {esc((fng.get('label') or '').lower())}."
    cards.append(f"""<a class="dash-card home-card" href="/pulse.html">
      <img class="dash-hero-img" src="/assets/market-pulse-banner.png" alt="Market Pulse: live dashboards" loading="lazy">
      <span class="lab">Market Pulse</span>
      <span class="dash-stat" style="font-size:19px">{mp_line}</span>
      <p class="pc-note">Sentiment, price posture, top movers, the top 100, stablecoin dry
      powder, and network vitals. Live data, honest charts, every term taught.</p>
      <span class="dash-open">See the dashboards &rarr;</span></a>""")
    cm_line = (cm or {}).get("headline") or "The wizard reads the tape."
    cards.append(f"""<a class="dash-card home-card" href="/chartmaster.html">
      <img class="dash-hero-img" src="/assets/chart-master-banner.png" alt="The Chart Master, crypto wizard" loading="lazy">
      <span class="lab">The Chart Master</span>
      <span class="dash-stat" style="font-size:19px">&ldquo;{esc(cm_line)}&rdquo;</span>
      <p class="pc-note">The resident wizard's plain-language read of the boards, plus the
      Oracle Challenge and the Wizard's Exam. Learn the charts by playing them.</p>
      <span class="dash-open">Enter the tower &rarr;</span></a>""")

    # The front page (owner directive 2026-07-16): a network-style hero mosaic. Several
    # lead stories visible at once with explicit hierarchy (the editor's rank orders them),
    # editions in their own strip below. No carousel: every ranked story is on screen.
    stories = [i for i in items if not i.get("example") and not _is_wrap(i)]

    def _hero_tag(item):
        tags = tags_for(item)
        return f'<span class="tag topic">{esc(tags[0])}</span>' if tags else ""

    desk_html = ""
    if stories:
        lead = stories[0]
        dek_html = f'<p class="hero-dek">{esc(lead["dek"])}</p>' if lead.get("dek") else ""
        # The desk set: an ambient video loop behind the lead card. It is scenery for
        # WHATEVER story leads, never an illustration of it (no caption, no linkage), and
        # the scrim guarantees the headline always beats the motion. Reduced-motion
        # readers get the poster still only (script below removes the video pre-load).
        hero_video = (
            '<video class="hero-video motion-video" autoplay muted loop playsinline preload="none" '
            'poster="/assets/hero/hero-poster.jpg" aria-hidden="true" tabindex="-1">'
            '<source src="/assets/hero/hero-loop.webm" type="video/webm">'
            '<source src="/assets/hero/hero-loop.mp4" type="video/mp4"></video>'
            '<span class="hero-scrim" aria-hidden="true"></span>')
        lead_html = (f'<a class="hero-lead" href="/articles/{esc(lead["slug"])}.html">'
                     f'<span class="hero-kick"><span class="kicker">Lead story</span>{_hero_tag(lead)}</span>'
                     f'<h3>{esc(lead.get("title"))}</h3>{dek_html}'
                     f'<span class="hl-meta">{verdict_badge(lead.get("verdict"), lead)}'
                     f'<span class="dateline">{fmt_when(lead)}</span></span></a>')
        # The Bottom Line rides shotgun: the day's summary as the hero square beside the
        # lead, replacing the standalone band lower on the page.
        bl_card = ""
        ed = current_bottom_line(items)
        if ed:
            ed_name = esc((ed.get("title") or "").split(":")[0].strip() or "The Daily Edition")
            bl_card = (f'<a class="hero-bl" href="/articles/{esc(ed["slug"])}.html">'
                       f'<span class="hero-kick"><span class="kicker">The Bottom Line</span></span>'
                       f'<span class="hero-bl-src">{ed_name} &middot; {_blink_when(ed)}</span>'
                       f'<span class="hero-bl-read">{esc(ed["bottom_line"])}</span>'
                       f'<span class="hero-bl-more">Read the full edition &rarr;</span></a>')
        more = "".join(
            f'<a class="hero-item" href="/articles/{esc(i["slug"])}.html">'
            f'<span class="hero-num">{n:02d}</span><span class="hero-body">'
            f'<span class="hero-kick">{_hero_tag(i)}</span>'
            f'<span class="hl-title">{esc(i.get("title"))}</span>'
            f'<span class="dateline">{fmt_when(i)}</span></span></a>'
            for n, i in enumerate(stories[1:6], start=2))
        more += ('<a class="hero-item more" href="/news.html">'
                 '<span class="hero-body"><span class="hl-title">All stories &rarr;</span></span></a>')
        desk_html = f"""<div class="sec-head"><h2>Today at the desk</h2><span class="bar"></span></div>
  <div class="hero-band">{hero_video}<div class="hero-band-inner">
    <div class="hero-grid{"" if bl_card else " solo"}">{lead_html}{bl_card}</div>
    <div class="hero-more-lab">More from the desk</div>
    <div class="hero-more">{more}</div>
  </div></div>"""

    # The Editions: the desk's daily synthesis as its own strip, one card per slot
    # (morning / midday / evening), newest first, never older than the current news cycle.
    # EDITIONS STALENESS (owner directive 2026-07-27, ported from sports/news 2026-08-18;
    # this desk never received the port): a card older than 24 hours never renders and
    # the strip collapses entirely when nothing fresh exists; the live-dot only ever
    # sits on a fresh card. A stale brief wearing a live-dot reads as a sync failure.
    _now = _build_now()
    wraps = [i for i in items if _is_wrap(i) and not i.get("example")
             and _fresh_hours(i, _now) <= 24]
    ed_cards, seen_slots = [], set()
    if wraps:
        recent = sorted({w.get("date", "") for w in wraps}, reverse=True)[:2]
        for w in wraps:
            if len(ed_cards) >= 3:
                break
            if (w.get("date") or "") not in recent:
                continue
            title = w.get("title") or ""
            kick, _, hook = title.partition(":")
            if not hook:
                kick, hook = "The Daily Edition", title
            if kick in seen_slots:
                continue
            seen_slots.add(kick)
            fact = w.get("key_fact") or w.get("dek") or ""
            dot = '<span class="live-dot"></span>' if not ed_cards else ''
            ed_cards.append(
                f'<a class="edition-card reveal" href="/articles/{esc(w["slug"])}.html">'
                f'<span class="ed-kick">{esc(kick)}{dot}</span>'
                f'<span class="ed-title">{esc(hook.strip())}</span>'
                f'<span class="ed-fact">{esc(fact)}</span>'
                f'<span class="dateline">{_blink_when(w)}</span></a>')
    editions_html = ""
    if ed_cards:
        editions_html = (f'<div class="sec-head" style="margin-top:26px"><h2>The Editions</h2>'
                         f'<span class="bar"></span></div>'
                         f'<p class="pc-note" style="margin:0 0 10px">The desk\'s daily synthesis: '
                         f'morning, midday, and evening reads over everything published.</p>'
                         f'<div class="edition-strip">{"".join(ed_cards)}</div>')

    # Tracking: the narratives watchlist, each chip linking to its latest published chapter.
    track_html = ""
    chips = []
    try:
        watch = json.load(open(os.path.join(HERE, "config.json"),
                               encoding="utf-8")).get("narratives", {}).get("watchlist", [])
    except Exception:
        watch = []
    # TAG INTEGRITY, PORTED (2026-08-25; sports/news had it since 2026-07-27, this desk
    # never did): the old rule matched a SINGLE keyword hit anywhere INCLUDING THE BODY,
    # so "CLARITY Act" and "Stablecoin law" both landed on one GENIUS Act article whose
    # body mentioned both, and "Sovereign adoption" landed on a tokenized-securities
    # pilot. A chip's story must be ABOUT the storyline: a title hit qualifies alone,
    # otherwise two hits across title+key_fact (never the dek, never the body). And one
    # article carries at most one chip: the first storyline to claim it keeps it.
    _chip_slugs_used = set()
    for n in watch:
        kws = n.get("keywords") or []
        if not kws:
            continue
        rx = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", re.I)
        cands = [i for i in live if not i.get("superseded_by") and tracking_match(i, rx)]
        cands.sort(key=lambda i: i.get("published_utc") or "", reverse=True)
        hit = cands[0] if cands else None
        if hit and hit.get("slug") in _chip_slugs_used:
            print(f"tracking: chip {n.get('name')!r} skipped; its newest match "
                  f"{hit.get('slug')!r} already carries another chip")
            hit = None
        if hit:
            _chip_slugs_used.add(hit.get("slug"))
            chips.append(f'<a class="chip" href="/articles/{esc(hit["slug"])}.html">'
                         f'{esc(n.get("name", ""))}</a>')
    if chips:
        track_html = (f'<div class="tracking"><span class="lab">Tracking</span>{"".join(chips)}'
                      f'<span class="mut">the storylines the desk is following</span></div>')

    # The Bottom Line lives in the hero square beside the lead (owner call 2026-07-16);
    # the standalone band below is retired on home. /bottom-line.html keeps the history.
    body = market_strip(pulse) + f"""<main class="wrap"><section class="page">
  <h1 class="sr-only">{esc(FAMILY)}: crypto news and market data, checked</h1>
  {desk_html}
  {editions_html}
  {track_html}
  <div class="dash-grid home-grid">{"".join(cards)}</div>
  <p class="lede home-lede" style="margin-top:22px">Built with one intention: get the stories
     right and keep the data honest. Real news with the shill stripped out, on-chain money
     flows, live dashboards that teach you what they mean, and a wizard who reads the tape.
     No hype, no paid promotion, and never financial advice. Everything here is free; every
     number comes with an explanation in plain language.</p>
</section></main>""" + newsletter()
    return shell(f"{FAMILY} - Crypto, checked.", FAMILY_DESC, "Home", body, dateline, path="/", schema_extra=home_schema())


def flow_teaser():
    flows = load_flows()
    if not flows or not flows.get("by_asset"):
        summ = "Track where whales are moving large amounts on net: onto exchanges or off into self-custody."
    else:
        v = flows.get("volatile", {})
        s = flows.get("stablecoins", {})
        pre = "Example: " if flows.get("example") else ""
        summ = (f"{pre}Volatile whales net {fmt_usd(abs(v.get('net_usd',0)))} {v.get('direction','')} over "
                f"{_win_phrase(flows.get('window_hours', 24))}; {fmt_usd(s.get('net_buying_power_usd',0))} "
                f"stablecoin buying power arriving.")
    return (f'<section class="sec"><div class="wrap">'
            f'<a class="flow-teaser" href="/flows.html">'
            f'<div><div class="t">Whale Watch &middot; follow the money</div>'
            f'<div class="d">{esc(summ)}</div></div>'
            f'<span style="font-family:var(--mono);font-size:11px;letter-spacing:.06em;'
            f'text-transform:uppercase;white-space:nowrap">Open the board &rarr;</span></a>'
            f'</div></section>')


def render_archive(items, dateline):
    live = [i for i in items if not i.get("example")]
    if live:
        # group by day, newest first (items are already sorted): a researcher scans by date
        days = []
        for i in live:
            if not days or days[-1][0] != i.get("date"):
                days.append((i.get("date"), []))
            days[-1][1].append(i)
        inner = "".join(
            f'<div class="sec-head" style="margin-top:22px"><h2>{esc(fmt_date(d))}</h2>'
            f'<span class="bar"></span></div><div class="grid">'
            + "".join(card(i) for i in group) + "</div>"
            for d, group in days)
    else:
        inner = ('<div class="empty"><span class="k">Archive is empty</span>'
                 '<p style="margin:.6em 0 0">No stories have been approved and published yet.</p></div>')
    body = f"""<main class="wrap"><section class="sec">
    <div class="sec-head"><h1>Archive</h1><span class="bar"></span></div>
    {inner}
  </section></main>"""
    return shell(f"Archive - {NAME}", "Every published Crypto Cronkite story.", "Archive", body, dateline,
                 path="/archive.html", brand="cronkite")


# ---- static editorial pages --------------------------------------------------

def render_method(items, dateline):
    example = next((i for i in items if i.get("example")), None)
    ex_html = ""
    if example:
        ex_html = (f'<h2>What a finished story looks like</h2>'
                   f'<p>Here is the format, using an illustrative example (not a real story):</p>'
                   f'<div style="margin:18px 0">{card(example)}</div>'
                   f'<p><a href="/articles/{esc(example["slug"])}.html">Open the example story &rarr;</a></p>')
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Method</span>
  <h1>How we work</h1>
  <p class="lede">The standards this desk holds itself to, and the things it does not do.</p>

  <h2>What we aim for</h2>
  <ul>
    <li><b>Sources you can check.</b> Stories link the material they draw on, and primary
        sources such as regulators, exchange and protocol notices and company filings carry
        more weight here than commentary about them.</li>
    <li><b>A second look before publication.</b> Stories are checked against the sources they
        cite, by a pass separate from the one that assembled them. Work that does not hold up
        is held back or dropped rather than smoothed over.</li>
    <li><b>Labels on unsettled news.</b> Where something is reported rather than confirmed, we
        try to say so plainly and name who reported it.</li>
    <li><b>One event, one story.</b> The same news carried by many outlets is treated as one
        story, so a loud story does not look like ten of them.</li>
    <li><b>Human oversight.</b> A human editor-in-chief oversees the desk, can hold or remove
        anything, and owns the opinion and analysis published here.</li>
  </ul>

  {ex_html}

  <h2>What we do not do</h2>
  <ul>
    <li>We do not tell you to buy or sell anything.</li>
    <li>We do not run paid coverage as news.</li>
    <li>We do not put an opinion in a voice that did not hold it.</li>
    <li>We do not attach a commercial link to coverage of a failure or a loss. How this site
        earns money is set out on <a href="/how-we-make-money.html">how we make money</a>.</li>
  </ul>

  <p>Stories on this site are produced with AI assistance and reviewed before publication,
     under the human editor-in-chief described above. We say so because you should know what
     you are reading.</p>

  <p>When we get something wrong we aim to fix it and say so on the story itself. Our sourcing
     and corrections policy is on <a href="/standards.html">standards and corrections</a>.</p>

  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"How we work - {NAME}", "How Crypto Cronkite ranks, verifies, and approves every story.",
                 "How we work", body, dateline, path="/method.html")


def render_about(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">About</span>
  <h1>Why Crypto Cronkite exists</h1>
  <p class="lede">Crypto media is drowning in shilling. The scarce thing is an honest voice. That
     is the entire product.</p>

  <p>Most crypto "news" is paid promotion wearing a press badge: price predictions with nothing
     behind them, "partnerships" that are really self-issued press releases, and listicles of coins
     to buy that are affiliate bait. It is exhausting, and it is how people get hurt.</p>

  <p>Crypto Cronkite is built on one idea: report the real news, strip the shill, and never tell you
     what to do with your money. The name is a promise. Walter Cronkite was trusted because he was
     straight with people. That is the register we hold ourselves to, right down to the sign-off:
     and that's the way it is.</p>

  <p>Alongside the news, <b>Whale Watch</b> follows the money on-chain, the large exchange flows most
     coverage ignores. It is market data, clearly labelled, never dressed up as news.</p>

  <h2>The machine does the grind. A human owns the judgment.</h2>
  <p>An AI newsroom does the reading, the triage, the fact-checking, and the first draft, every day,
     without getting tired. But the machine is the staff, not the editor. A story runs only when an
     independent verification pass confirms it against its sources; anything flagged waits for the
     human editor-in-chief, who oversees the desk, overrides the machine where judgment differs, and
     owns every take: no opinion ever goes out in a human voice unless a human wrote it. If that
     standard ever slips, we drop the cadence before we drop the standard.</p>

  <h2>Our bias</h2>
  <p>We are biased toward the reader and against the shill. We weight official and primary sources
     most, we link every source, and we would rather publish nothing on a given day than publish
     something we cannot stand behind.</p>

  <h2>What we are not</h2>
  <p>We are not your financial advisor, and this is not investment advice. We report what happened
     and, carefully, what it may mean. What you do with that is yours.</p>

  <h2>Contact the desk</h2>
  <p>Tips, corrections, and questions: <a href="mailto:desk@gocheckmycrypto.com">desk@gocheckmycrypto.com</a>.</p>
  <p>Sponsorship inquiries: <a href="mailto:desk@gocheckmycrypto.com">desk@gocheckmycrypto.com</a>.
     Sponsorship never buys coverage; see <a href="/method.html">how we work</a>.</p>
  <p>This website is operated by Go Check My Brands LLC, a South Carolina limited liability company.
     Contact: <a href="mailto:hello@gocheckmycrypto.com">hello@gocheckmycrypto.com</a>.</p>

  <div class="callout"><b>Read next:</b> <a href="/method.html">How a story gets to you</a>, the
    step-by-step of how we rank, verify, and approve. Or <a href="/standards.html">our standards and
    corrections policy</a>.</div>
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"About - {NAME}", "Why Crypto Cronkite exists: an honest crypto news desk plus on-chain analytics.",
                 "About", body, dateline, path="/about.html")


def render_how_we_make_money(dateline):
    """The published commercial policy. Renders from explainers.PARTNERS, so a new
    relationship is disclosed by adding it there and nowhere else."""
    import explainers
    return shell(f"How we make money - {NAME}",
                 "The complete list of what this desk earns affiliate commission from, "
                 "and the rules about where those links may and may not appear.",
                 "", explainers.how_we_make_money_body(), dateline,
                 path="/how-we-make-money.html")


def render_crypto_tax(dateline):
    """Evergreen tax explainer. Every factual claim is tied to IRS primary material; see
    explainers.TAX_SOURCES. Review each January when filing season opens."""
    import explainers
    return shell(f"Crypto and tax, explained - {NAME}",
                 "What the IRS treats as a taxable event, what it does not, and why cost "
                 "basis is the hard part. United States federal tax only.",
                 "", explainers.crypto_tax_body(), dateline, path="/crypto-tax.html")


def render_onchain_flows(dateline):
    """Learn-tier explainer with NO commercial layer; the copy lives in learn_pages.py so
    explainers.py stays exactly the money path. This page documents our own Whale Watch
    methodology, so it must be revisited whenever whale_flows.py changes."""
    import learn_pages
    return shell(f"How to read on-chain flow data - {NAME}",
                 "What an exchange transfer indicates, what it does not, and how the "
                 "Whale Watch board classifies and nets large on-chain moves.",
                 "", learn_pages.onchain_flows_body(), dateline,
                 path="/onchain-flows.html")


def render_counterfeit_devices(dateline):
    """Evergreen device-verification explainer. Copy and affiliate config live in
    explainers.py. Every claim about tampering signs and verification is sourced to
    manufacturer documentation; see explainers.COUNTERFEIT_SOURCES and the note there
    about which conclusion is ours rather than theirs."""
    import explainers
    return shell(f"Counterfeit hardware wallets - {NAME}",
                 "How tampered devices and pre-filled recovery cards reach buyers, what a "
                 "prepared device looks like, and how to verify the one you received.",
                 "", explainers.counterfeit_devices_body(), dateline,
                 path="/counterfeit-devices.html")


def render_learn(dateline):
    """The Learn tier index. Renders from explainers.EXPLAINERS, so a new entry there is
    the only edit an added explainer needs."""
    import explainers
    return shell(f"Learn crypto: explainers, boards, and glossary - {NAME}",
                 "Evergreen explainers, how the desk verifies stories, how to read its "
                 "market boards, and a glossary of the terms its reporting uses.",
                 "", explainers.learn_index_body(), dateline, path="/learn.html")


def render_cold_storage(dateline):
    """Evergreen custody explainer. The copy and the affiliate config live in
    explainers.py so the entire commercial surface of the site is one auditable file."""
    import explainers
    return shell(f"Cold storage, explained - {NAME}",
                 "Exchange, hot wallet, or cold storage: who holds the keys in each, what "
                 "each is for, and when a hardware wallet is worth buying.",
                 "", explainers.cold_storage_body(), dateline,
                 path="/cold-storage.html")


def render_standards(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Standards</span>
  <h1>Standards and corrections</h1>
  <p class="lede">What you can hold us to.</p>

  <h2>Sourcing</h2>
  <p>Stories link the sources they draw on. We give more weight to official and primary sources
     such as regulators and exchange or protocol notices than to commentary about them, and a
     claim resting on a single weak source is labelled as unconfirmed or left out.</p>

  <h2>Verification</h2>
  <p>Stories are checked against the sources they cite by a pass separate from the one that
     assembled them. Work that does not hold up is labelled clearly for the reader or held
     back. We would rather be slow than wrong.</p>

  <h2>Oversight</h2>
  <p>A human editor-in-chief oversees the desk, can hold or remove anything, and owns the
     opinion and analysis published here.</p>

  <h2>Not financial advice</h2>
  <p>We report events and explain what they may mean. We never advise buying or selling any asset.
     Nothing on this site is financial, investment, legal, or tax advice.</p>

  <h2>Corrections</h2>
  <p>When we get something wrong, we aim to fix it and say so on the story. If you spot an
     error, tell us and we will check it against the source. A correction is a feature of an
     honest desk, not a failure.</p>

  <h2>AI disclosure</h2>
  <p>Stories on this site are produced with AI assistance and reviewed before publication,
     under a human editor-in-chief who oversees the desk. Opinion, analysis and corrections
     are human work. We say so because you should know what you are reading.</p>
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"Standards - {NAME}", "Crypto Cronkite standards, verification, and corrections policy.",
                 "Standards", body, dateline, path="/standards.html")


def render_accessibility(dateline):
    """Accessibility conformance statement.

    MAINTENANCE, and this matters more than most pages: every factual claim below is a
    claim about testing that was actually run. TESTED_ON, the page counts, the widths, the
    themes and the axe version are the record of one specific sweep. If you change what is
    tested, change this page in the same commit. If a claim here stops being true, the page
    is worse than no page at all. Never add the words certified or compliant, and never
    imply a third party checked any of this.
    """
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Accessibility</span>
  <h1>Accessibility statement</h1>
  <p class="lede">What we test, how we test it, what we have not tested, and how to tell us
     when something is in your way.</p>

  <h2>Where we stand</h2>
  <p>We aim to meet <strong>WCAG 2.1 Level AA</strong>. This is a
     <strong>self-assessment</strong>. We ran the testing described below ourselves and are
     reporting what it found. No outside party has audited or verified this site, and
     nothing on this page is a certification or a claim of legal compliance.</p>

  <h2>What was tested, and when</h2>
  <p>Last full review: <strong>{ACCESSIBILITY_TESTED_ON}</strong>.</p>
  <p>The review covered <strong>{ACCESSIBILITY_PAGE_COUNT} pages</strong>: every standalone
     page on the site, including the home page, Latest, Whale Watch, Market Pulse and each
     of its eight boards, Chart Master, the Learn explainers, Archive, and the trust and
     policy pages. Articles are generated from a single shared template, so two article
     pages were tested as samples of it rather than all {ACCESSIBILITY_ARTICLE_COUNT} of
     them. Each page was tested in <strong>both the light and dark themes</strong>, at
     <strong>1280px and 375px wide</strong>.</p>
  <p>That is the whole scope. Pages, themes and widths outside that list were not part of
     this review.</p>

  <h2>How it was tested</h2>
  <p>Automated testing used <strong>axe-core {ACCESSIBILITY_AXE_VERSION}</strong> against
     the rendered pages in a real browser, running the WCAG 2.0 A/AA, WCAG 2.1 A/AA and
     best-practice rule sets. That automated pass currently reports
     <strong>no violations</strong> across the pages, themes and widths listed above.</p>
  <p>Automated tools catch a minority of accessibility problems, so the following checks
     were also performed by hand:</p>
  <ul class="rule-list">
    <li><strong>Keyboard.</strong> Every control reached and operated by keyboard alone,
        with a visible focus indicator, a working skip-to-content link, and no traps.</li>
    <li><strong>Contrast.</strong> Text and interface colors measured against AA ratios in
        all three theme scopes, including the dark data boards.</li>
    <li><strong>Structure.</strong> Heading order, one h1 per page, landmark regions, list
        semantics, and scoped table headers.</li>
    <li><strong>Forms and controls.</strong> Labels, grouping, and error handling on every
        input on the site.</li>
    <li><strong>Motion and media.</strong> A pause control for moving content, and the
        browser's reduced-motion setting honored independently of it.</li>
    <li><strong>Dynamic content.</strong> Live regions and focus movement where the page
        updates without a reload.</li>
    <li><strong>Reflow and zoom.</strong> Readable and operable at 320px and at 200% zoom,
        with wide data tables scrolling inside their own containers.</li>
    <li><strong>Target size.</strong> Interactive controls checked for adequate hit area.</li>
  </ul>

  <h2>What we have not tested</h2>
  <p><strong>We have not tested this site with a screen reader or any other assistive
     technology.</strong> No testing with NVDA, JAWS, VoiceOver, TalkBack, voice control,
     or switch access has been performed. Passing automated checks and our manual checks
     is not the same as being usable with those tools, and we are not going to imply
     otherwise. This is the largest known gap in the review.</p>
  <p>We have also not conducted usability testing with disabled users, which is the only
     method that reliably finds the problems the rest of this page misses.</p>

  <h2>Known limitations</h2>
  <p><strong>This site publishes new content automatically, on a schedule, without a human
     reviewing each page before it goes out.</strong> Stories are generated and published
     several times a day. A new story can introduce an accessibility problem that did not
     exist at the last review, and it can be live for hours or days before anyone notices.
     The statement above describes the state of the site at the review date. It is not a
     guarantee about a page published after it.</p>
  <p>The same applies to the data boards, which redraw charts and tables from live market
     feeds on every build.</p>
  <p>Some content is outside our control: embedded material from third parties, and source
     documents we link to on other organizations' sites, are not covered by this review.</p>

  <h2>Tell us if something is in your way</h2>
  <p>If any part of this site is difficult or impossible for you to use, please tell us. You
     do not need to know why it is broken or what the standard says. Describing what you
     were trying to do and what happened is enough, and telling us which browser or
     assistive technology you were using helps us reproduce it.</p>
  <p><strong>Email <a href="mailto:desk@gocheckmycrypto.com">desk@gocheckmycrypto.com</a>.</strong>
     We read every message and aim to reply within five business days. If we can fix the
     problem we will, and if we cannot fix it quickly we will tell you where it stands and
     what the alternative is in the meantime.</p>
  <p>Reports of specific barriers are the most useful accessibility information we get,
     more useful than any scan, and they are why this page has an address on it.</p>

  <p class="nfa">This statement was last reviewed on {ACCESSIBILITY_TESTED_ON} and is
     updated when the site is retested.</p>
</section></main>"""
    return shell(f"Accessibility statement - {NAME}",
                 "Our WCAG 2.1 AA self-assessment: what was tested, how, what has not been "
                 "tested, known limitations, and how to report a barrier.",
                 "Accessibility", body, dateline, path="/accessibility.html")


def render_privacy(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Privacy</span>
  <h1>Privacy policy</h1>
  <p class="lede">What this site actually collects, which is very little, and where the little
     goes. No accounts, no ads, no cookies set by us.</p>

  <h2>The newsletter</h2>
  <p>If you sign up for the daily brief, the email address you submit is stored by Netlify Forms,
     the form service of our hosting provider, and delivered to our company inbox. We use it only
     to send the newsletter. We do not sell your email address, and we do not share it with anyone
     else. Every issue includes an unsubscribe option, and unsubscribing removes you from the
     list. The signup form is the only place this site asks you for anything.</p>

  <h2>Analytics</h2>
  <p>We measure traffic with Cloudflare Web Analytics. It is a cookieless beacon: it counts page
     views and referrers in aggregate and does not build profiles or track you across other
     sites. Cloudflare processes those requests under its own privacy policy.</p>

  <h2>Hosting and server logs</h2>
  <p>The site is served by Netlify. Like any web host, Netlify's infrastructure sees standard
     request data (your IP address and browser user agent) and keeps its own server logs under
     its own privacy policy. We do not receive or store that data ourselves.</p>

  <h2>Live prices</h2>
  <p>Pages with live prices fetch them directly from your browser to CoinGecko's public API
     (api.coingecko.com). That request comes from you, so CoinGecko sees your IP address,
     governed by CoinGecko's own privacy policy. No identifier from this site is attached.</p>

  <h2>Fonts</h2>
  <p>Pages load their typefaces from Google Fonts (fonts.googleapis.com and fonts.gstatic.com),
     so your browser makes a request to Google when a page loads. Google processes font requests
     under its own privacy policy.</p>

  <h2>Links out</h2>
  <p>Stories link their sources, and dashboards link the services behind their data. Once you
     leave this site, the site you land on operates under its own privacy policy.</p>

  <h2>Contact</h2>
  <p>This website is operated by Go Check My Brands LLC, a South Carolina limited liability company.
     Contact: <a href="mailto:hello@gocheckmycrypto.com">hello@gocheckmycrypto.com</a>.</p>
  <p>Questions about this policy, your data, or the newsletter, including unsubscribe requests:
     <a href="mailto:desk@gocheckmycrypto.com">desk@gocheckmycrypto.com</a>. A human reads it.</p>

  <h2>Changes</h2>
  <p>This policy changes only when the site's behavior changes, and the date below moves when it
     does. Last updated July 14, 2026.</p>
</section></main>"""
    return shell(f"Privacy - {NAME}",
                 "What GoCheckMyCrypto collects and where it goes: newsletter emails via Netlify Forms, "
                 "cookieless Cloudflare analytics, and nothing else.",
                 "Privacy", body, dateline, path="/privacy.html")


def render_terms(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Terms</span>
  <h1>Terms of use</h1>
  <p>This website is operated by Go Check My Brands LLC, a South Carolina limited liability company.
     Contact: <a href="mailto:hello@gocheckmycrypto.com">hello@gocheckmycrypto.com</a>.</p>

  <h2>Not financial advice</h2>
  <p>GoCheckMyCrypto publishes market news, on-chain data, and plain-language analysis for
     education and information only. Nothing on this site is financial, investment, legal, or tax
     advice, and nothing here is a recommendation to buy, sell, or hold any asset. Crypto assets
     are volatile and you can lose money. Decisions about your money are yours alone; if you need
     advice, get it from a licensed professional who knows your situation.</p>

  <h2>Informational purposes only</h2>
  <p>Stories, dashboards, and commentary are assembled from public third-party sources (exchanges,
     public APIs, news outlets, on-chain data). Data can be delayed, revised, or wrong at the
     source. Verify anything that matters against primary sources before you act on it.</p>

  <h2>No warranty</h2>
  <p>The site and its data are provided "as is" and "as available," without warranties of any
     kind, express or implied, to the maximum extent permitted by law. We do not warrant that the
     site is accurate, complete, current, or uninterrupted.</p>

  <h2>Limitation of liability</h2>
  <p>To the fullest extent permitted by law, GoCheckMyCrypto and its operators are not liable for
     any loss or damage arising from your use of this site or reliance on its content, including
     trading losses and indirect, incidental, or consequential damages.</p>

  <h2>Governing law</h2>
  <p>These terms are governed by the laws of the State of South Carolina, without regard to
     conflict-of-law rules. If you do not agree with these terms, please do not use the site.</p>

  <p class="nfa">Last updated July 14, 2026.</p>
</section></main>"""
    return shell(f"Terms of Use - {NAME}",
                 "What GoCheckMyCrypto is and is not: market news and data for education, "
                 "not financial advice, with no warranty.",
                 "Terms", body, dateline, path="/terms.html")


def flows_chart_svg(by_asset):
    """Diverging horizontal bar chart of net whale exchange flow per volatile asset. Inline SVG,
    offline, theme-aware (fills use the site's CSS variables). Polarity is encoded three ways so
    it never relies on red/green alone: side of the zero line, the sign in the label, and color.
    Left/red = net onto exchanges (sell pressure); right/green = net off exchanges (accumulation)."""
    if not by_asset:
        return '<div class="empty"><span class="k">No exchange-relevant whale moves in window</span></div>'
    W, cx, half = 720, 360, 250
    row_h, bar_h = 46, 20
    top = 44
    H = top + len(by_asset) * row_h + 16
    max_abs = max((abs(a.get("net_usd", 0)) for a in by_asset), default=1) or 1
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
             f'aria-label="Net whale exchange flow by asset" style="max-width:100%;height:auto">']
    # axis labels + zero line
    parts.append(f'<text x="{cx-12}" y="20" text-anchor="end" class="ax">&#8592; onto exchanges (sell pressure)</text>')
    parts.append(f'<text x="{cx+12}" y="20" text-anchor="start" class="ax">off exchanges (accumulation) &#8594;</text>')
    parts.append(f'<line x1="{cx}" y1="30" x2="{cx}" y2="{H-8}" class="zero"/>')
    for i, a in enumerate(by_asset):
        y = top + i * row_h
        net = a.get("net_usd", 0)
        length = (abs(net) / max_abs) * half
        cy = y + row_h / 2
        by = cy - bar_h / 2
        parts.append(f'<text x="8" y="{cy+5:.0f}" class="sym">{esc(a.get("symbol",""))}</text>')
        if net < 0:  # onto exchanges, extend left, red
            parts.append(f'<rect x="{cx-length:.1f}" y="{by:.0f}" width="{length:.1f}" height="{bar_h}" '
                         f'rx="4" fill="var(--down)"/>')
            parts.append(f'<text x="{cx-length-8:.1f}" y="{cy+5:.0f}" text-anchor="end" class="val">'
                         f'{esc(fmt_usd(net))}</text>')
        else:  # off exchanges, extend right, green
            parts.append(f'<rect x="{cx:.1f}" y="{by:.0f}" width="{length:.1f}" height="{bar_h}" '
                         f'rx="4" fill="var(--up)"/>')
            parts.append(f'<text x="{cx+length+8:.1f}" y="{cy+5:.0f}" text-anchor="start" class="val">'
                         f'+{esc(fmt_usd(net))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def ww_hero():
    # The whale loop is contained section dressing (never a trade signal): strictly lazy
    # (no autoplay attribute, motion-lazy pool arms on first scroll), poster as first
    # paint, and the section identity rides the scrim in light text.
    return ('<section class="ww-hero" aria-label="Whale Watch"><div class="ww-heroinner"><div class="ww-panel">'
            '<video class="ww-vid motion-video motion-lazy" muted loop playsinline preload="none" '
            'poster="/assets/whale/whale-poster.jpg" aria-hidden="true" tabindex="-1">'
            '<source src="/assets/whale/whale-loop.webm" type="video/webm">'
            '<source src="/assets/whale/whale-loop.mp4" type="video/mp4"></video>'
            '<span class="ww-scrim" aria-hidden="true"></span>'
            '<span class="ww-panel-fg"><span class="kicker">Follow the money</span>'
            '<span class="ww-title">Whale Watch</span></span>'
            '</div></div></section>')


def _win_phrase(hours):
    """Human window label: '24 hours', '48 hours', '7 days'."""
    hours = int(hours or 24)
    if hours >= 48 and hours % 24 == 0:
        return f"{hours // 24} days"
    return f"{hours} hours"


def render_flows(flows, dateline):
    if not flows or (not flows.get("by_asset") and not flows.get("top_inflows")):
        body = ww_hero() + """<main class="wrap"><section class="page">
  <h1>Where the whales are moving</h1>
  <p class="lede">This board tracks where whales are moving large amounts of crypto: onto
     exchanges (which can precede selling) or off exchanges into self-custody (accumulation).</p>
  <div class="empty"><span class="k">A quiet stretch</span>
    <p style="margin:.6em 0 0">Whale Alert's public feed only carries the very largest
    transfers (roughly $50M and up), and none touched an exchange recently. The board
    refreshes with every site build; check back soon.</p></div>
</section></main>"""
        return shell(f"Whale Watch - {NAME}", "Follow the money: whale exchange flows.",
                     "Whale Watch", body, dateline, body_class="ww-dark", path="/flows.html")

    v = flows.get("volatile", {})
    s = flows.get("stablecoins", {})
    net = v.get("net_usd", 0)
    dir_word = v.get("direction", "")
    dir_cls = "up" if net >= 0 else "down"
    ribbon = ""
    if flows.get("example"):
        ribbon = ('<div class="callout"><b>Example board.</b> These are illustrative figures from '
                  'sample data, shown so you can see the format. Live flows arrive with the next site build.</div>')
    if flows.get("window_widened_from"):
        ribbon += (f'<div class="callout"><b>Quiet stretch.</b> No exchange-size whale moves hit '
                   f'the public feed in the last {_win_phrase(flows["window_widened_from"])}, so '
                   f'this board shows the last {_win_phrase(flows.get("window_hours"))} instead.</div>')
    # the "what it cannot tell you" explainer names the source that actually produced this
    # snapshot (whale_flows falls back to Blockscout when Whale Alert's feed is down)
    src_line = ('Only the very largest Ethereum ERC-20 transfers visible on the '
                '<a href="https://eth.blockscout.com/" rel="nofollow">Blockscout</a> public '
                'explorer ($50M and up) appear here'
                if flows.get("source") == "blockscout" else
                'Only moves large enough for <a href="https://whale-alert.io/" '
                'rel="nofollow">Whale Alert</a> to post publicly (roughly $50M and up) '
                'appear here')
    # deterministic 'now' anchor for move ages: the newest transfer in the window
    all_moves = flows.get("top_inflows", []) + flows.get("top_outflows", [])
    now_ts = max((m.get("ts") or 0 for m in all_moves), default=0)

    def _move_rows(moves):
        rows = ""
        for m in moves:
            usd = fmt_usd(m.get("usd", 0))
            # the receipt: the transfer itself, on the source that actually saw it (a move
            # from the Blockscout fallback carries its own explorer url; Whale Alert moves
            # keep the classic link)
            url = m.get("url") or (
                f'https://whale-alert.io/transaction/{m["blockchain"]}/{m["hash"]}'
                if m.get("hash") and m.get("blockchain") else "")
            usd_html = f'<a href="{esc(url)}" rel="nofollow">{esc(usd)}</a>' if url else esc(usd)
            age = ""
            if m.get("ts") and now_ts:
                h = max(0, round((now_ts - m["ts"]) / 3600))
                age = f'<span class="mut"> &middot; {h}h ago</span>' if h else '<span class="mut"> &middot; latest</span>'
            rows += (f'<tr><td class="sym2">{esc(m.get("symbol",""))}{" &middot; stable" if m.get("stable") else ""}</td>'
                     f'<td class="num">{usd_html}</td>'
                     f'<td style="white-space:normal">&rarr; {esc(m.get("to",""))}{age}'
                     f'<br><span class="mut">from {esc(m.get("from",""))}</span></td></tr>')
        return rows

    move_rows = _move_rows(flows.get("top_inflows", []))
    out_rows = _move_rows(flows.get("top_outflows", []))
    ex_rows = "".join(
        f'<tr><td class="sym2" style="text-transform:none">{esc(e.get("exchange",""))}</td>'
        f'<td class="pnum" style="color:var(--down)">{esc(fmt_usd(e.get("inflow_usd",0)))}</td>'
        f'<td class="pnum" style="color:var(--up)">{esc(fmt_usd(e.get("outflow_usd",0)))}</td>'
        f'<td class="pnum">{"+" if e.get("net_usd",0) >= 0 else ""}{esc(fmt_usd(e.get("net_usd",0)))}</td></tr>'
        for e in flows.get("by_exchange", []))
    winp = _win_phrase(flows.get("window_hours", 24))
    # pace vs the last quarter: |net| in this window against the median week's |net|,
    # scaled to the window length, so the headline number arrives with a judgment
    pace_html = ""
    med = flows.get("weekly_median_abs_usd") or 0
    win_h = flows.get("window_hours", 24) or 24
    if med and net is not None:
        pace = abs(net) / (med * win_h / 168)
        pace_html = f' &middot; about {pace:.1f}x a typical week&rsquo;s pace'
    biggest = max(flows.get("top_inflows", []) + flows.get("top_outflows", []),
                  key=lambda m: m.get("usd", 0), default=None)
    big_html = ""
    if biggest:
        big_html = f"""<div class="stat">
      <span class="lab">Biggest single move</span>
      <span class="big">{esc(fmt_usd(biggest.get("usd", 0)))}</span>
      <span class="sub">{esc(biggest.get("symbol", ""))} &rarr; {esc(biggest.get("to", ""))}</span>
    </div>"""
    body = ww_hero() + f"""<main class="wrap"><section class="page">
  <div class="ey" style="margin:14px 0 0">
    <span class="daily-badge">refreshed through the day</span></div>
  <h1 style="margin-top:6px">Where the whales are moving</h1>
  <p class="lede" style="margin-bottom:10px">The aggregate, not the feed: whale money onto
     exchanges (can precede selling) vs off into self-custody (accumulation), last {winp}.</p>
  {ribbon}

  <div class="stats">
    <div class="stat">
      <span class="lab">Volatile assets, net ({esc(winp)})</span>
      <span class="big {dir_cls}">{esc(fmt_usd(abs(net)))}</span>
      <span class="sub">net {esc(dir_word)} &middot; gross {esc(fmt_usd(v.get("inflow_usd", 0)))} on /
        {esc(fmt_usd(v.get("outflow_usd", 0)))} off{pace_html}</span>
    </div>
    <div class="stat">
      <span class="lab">Stablecoin buying power</span>
      <span class="big">{esc(fmt_usd(s.get("net_buying_power_usd",0)))}</span>
      <span class="sub">net stablecoins onto exchanges</span>
    </div>
    {big_html}
    <div class="stat">
      <span class="lab">Exchange-size moves</span>
      <span class="big">{flows.get("txn_count", 0)}</span>
      <span class="sub">$50M+ transfers in {esc(winp)}</span>
    </div>
  </div>

  <div class="board-grid">
    <div>
      <div class="sec-head"><h2>Net flow by asset</h2><span class="bar"></span></div>
      <div class="chartcard">{flows_chart_svg(flows.get("by_asset", []))}</div>
      {f'''<div class="sec-head" style="margin-top:18px"><h2>The 13-week trend</h2><span class="bar"></span></div>
      <div class="chartcard">{flow_ledger(
          [(w.get("week_ending", ""), w.get("net_usd", 0),
            f'{w.get("moves", 0)} exchange-size moves') for w in flows.get("history", [])],
          aria="Weekly net exchange flow, last 13 weeks", compact=True)}</div>
      <p class="pc-note" style="margin-top:8px">Weekly net flow for volatile assets, newest
      first: green right = net withdrawals (accumulation), red left = net deposits.</p>''' if flows.get("history") else ""}
    </div>
    <div class="stack">
      <div class="sec-head"><h2>Biggest moves onto exchanges</h2><span class="bar"></span></div>
      <div class="movetable" tabindex="0" role="region" aria-label="Biggest moves onto exchanges (scrollable)"><table><tbody>{move_rows or '<tr><td class=mut>None in window.</td></tr>'}</tbody></table></div>
      <div class="sec-head"><h2>Biggest moves off exchanges</h2><span class="bar"></span></div>
      <div class="movetable" tabindex="0" role="region" aria-label="Biggest moves off exchanges (scrollable)"><table><tbody>{out_rows or '<tr><td class=mut>None in window.</td></tr>'}</tbody></table></div>
      {f'''<div class="sec-head"><h2>By exchange</h2><span class="bar"></span></div>
      <div class="movetable" tabindex="0" role="region" aria-label="Net flow by exchange (scrollable)"><table>
        <thead><tr><th><span class="sr-only">Exchange</span></th><th>In</th><th>Out</th><th>Net</th></tr></thead>
        <tbody>{ex_rows}</tbody></table></div>
      <p class="pc-note" style="margin-top:6px">Window totals per named exchange; net + = more
      left than arrived. Amounts in the move tables link to the transfer itself on Whale Alert.</p>''' if ex_rows else ""}
    </div>
  </div>

  <div class="sec-head" style="margin-top:30px"><h2>Whale watching 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab sell">Onto exchanges</span>
      <p>To sell a large amount of crypto, a whale usually has to move it onto an exchange first.
      So when BTC or ETH flows heavily <b>onto</b> exchanges on net, it can mean big holders are
      getting into position to sell. That is the sell-pressure side of the chart. For how this
      board classifies a transfer, and what a net figure can and cannot support, see
      <a href="/onchain-flows.html">how to read on-chain flow data</a>.</p></div>
    <div class="learn"><span class="lab buy">Off exchanges</span>
      <p>Coins withdrawn from an exchange usually head to self-custody: wallets the holder
      controls directly, often cold storage. Money tends to go there to sit, so net
      <b>outflow</b> historically reads as accumulation. That is the other side.
      If you want the mechanics of how that custody actually works, we explain it in
      <a href="/cold-storage.html">cold storage, explained</a>.</p></div>
    <div class="learn"><span class="lab">Stablecoins flip the logic</span>
      <p>Stablecoins like USDT and USDC are crypto's dry powder. When they flood <b>onto</b>
      exchanges, buyers may be staging money for purchases; when they leave, that buying power
      is stepping out of the arena. That is why we score them separately from volatile assets.</p></div>
    <div class="learn"><span class="lab">What it cannot tell you</span>
      <p>Whales move money for many reasons: custody rotations, transfers between their own
      wallets, over-the-counter deals. {src_line}, and exchanges are identified by name.
      Treat this board as context for the news above it, never as a trade signal on its
      own.</p></div>
  </div>
  {data_stamp(flows, what="This whale board")}
  <p class="nfa">{esc(flows.get("note",""))} {esc(NFA)}</p>
</section></main>"""
    return shell(f"Whale Watch - {NAME}", "Follow the money: net whale exchange flows by asset.",
                 "Whale Watch", body, dateline, body_class="ww-dark", path="/flows.html")


# ---- market pulse -------------------------------------------------------------

def spark_svg(values, w=230, h=44, cls="spark"):
    """Tiny inline sparkline; server-rendered, no JS."""
    vals = [float(v) for v in (values or []) if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(vals):
        x = 3 + i * (w - 6) / (len(vals) - 1)
        y = 3 + (h - 6) * (1 - (v - lo) / rng)
        pts.append(f"{x:.1f},{y:.1f}")
    last = pts[-1].split(",")
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="none" role="img" aria-hidden="true">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linejoin="round"/>'
            f'<circle cx="{last[0]}" cy="{last[1]}" r="2.6" fill="currentColor"/></svg>')


FNG_BANDS = [(0, 25, "#C0392B", "Extreme fear"), (25, 45, "#D9822B", "Fear"),
             (45, 55, "#9AA0A6", "Neutral"), (55, 75, "#6FA26B", "Greed"),
             (75, 100, "#2E7D4F", "Extreme greed")]

# chart data colors: the main series is always direction-coded on the market scale
# (green ended higher than it started, red ended lower); overlays are neutral references.
C_UP = "var(--up)"
C_DOWN = "var(--down)"
C_SMA50 = "#8F6BD6"   # violet, the 50-day average overlay
C_SMA200 = "#8A93A0"  # slate, the 200-day average overlay


def trend_color(series):
    """The market color for a series: green if it ended at or above where it started."""
    vals = [float(v) for v in (series or []) if v is not None]
    return C_UP if len(vals) < 2 or vals[-1] >= vals[0] else C_DOWN



def spark_widget(values, period, dollars=True):
    """A spark that MEASURES: colored by its period direction (green ended higher, red
    ended lower), end dot, and the period + high/low range printed beneath - a mini chart
    with scale, not a decorative squiggle."""
    vals = [float(v) for v in (values or []) if v is not None]
    if len(vals) < 2:
        return ""
    color = "var(--up)" if vals[-1] >= vals[0] else "var(--down)"
    lo, hi = fmt_tick(min(vals), dollars), fmt_tick(max(vals), dollars)
    return (f'<span style="color:{color}">{spark_svg(vals)}</span>'
            f'<span class="w-range">{esc(period)} range {lo} &ndash; {hi}</span>')

def fmt_tick(n, dollars=True):
    """Compact axis label: $82K / $310B / 45. Whole numbers below 1000."""
    n = float(n)
    sign = "-" if n < 0 else ""
    a = abs(n)
    p = "$" if dollars else ""
    if a >= 1e12:
        return f"{sign}{p}{a/1e12:.4g}T"
    if a >= 1e9:
        return f"{sign}{p}{a/1e9:.4g}B"
    if a >= 1e6:
        return f"{sign}{p}{a/1e6:.4g}M"
    if a >= 1e3:
        return f"{sign}{p}{a/1e3:.4g}K"
    return f"{sign}{p}{a:.4g}"


def _nice_step(rough):
    """Round a rough step up to a 'nice' 1/2/2.5/5 x 10^n value."""
    import math
    mag = 10 ** math.floor(math.log10(rough)) if rough > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if rough <= m * mag:
            return m * mag
    return 10 * mag


def _ticks(lo, hi, target=4):
    if hi <= lo:
        hi = lo + 1
    step = _nice_step((hi - lo) / target)
    import math
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + step * 1e-9:
        out.append(round(t, 10))
        t += step
    return out or [lo, hi]


def line_chart_svg(series, *, w=680, h=260, dollars=True, x_labels=None, overlays=None,
                   bands=None, color=None, area=True, y_min=None, y_max=None,
                   value_label=None, aria="", pill_attr=""):
    """A real chart: gridlines, labeled y-axis, dated x-axis, area fill, current-value pill,
    optional dashed overlay series and tinted horizontal bands. Pure server-rendered SVG.
    color=None direction-codes the main line on the market scale (green up, red down)."""
    vals = [float(v) for v in (series or []) if v is not None]
    if len(vals) < 2:
        return ""
    if color is None:
        color = C_UP if vals[-1] >= vals[0] else C_DOWN
    all_vals = list(vals)
    for ov in (overlays or []):
        all_vals += [float(v) for v in ov.get("series", []) if v is not None]
    lo = y_min if y_min is not None else min(all_vals)
    hi = y_max if y_max is not None else max(all_vals)
    pad = (hi - lo) * 0.06 or abs(hi) * 0.02 or 1
    if y_min is None:
        lo -= pad
    if y_max is None:
        hi += pad
    ml, mr, mt, mb = 62, 20, 12, 26  # margins: left labels, right, top, bottom dates
    pw, ph = w - ml - mr, h - mt - mb

    def X(i, n):
        return ml + i * pw / (n - 1)

    def Y(v):
        return mt + ph * (1 - (float(v) - lo) / (hi - lo))

    # A stable digest, not hash(). Python salts hash() of a str per process
    # (PYTHONHASHSEED), so this id changed on every build and four pulse pages differed run
    # to run, which quietly defeated the rebuild-identical gate on this repo.
    uid = "g" + hashlib.sha1(
        f"{round(lo, 2)}|{round(hi, 2)}|{len(vals)}|{color}".encode()).hexdigest()[:8]
    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
             f'role="img" aria-label="{esc(aria)}" preserveAspectRatio="xMidYMid meet">']
    # tinted horizontal bands (e.g. fear/greed zones)
    for b in (bands or []):
        y1, y0 = Y(b["from"]), Y(b["to"])
        parts.append(f'<rect x="{ml}" y="{min(y0, y1):.1f}" width="{pw}" '
                     f'height="{abs(y1 - y0):.1f}" fill="{b["color"]}" opacity="0.10"/>')
        if b.get("label"):
            parts.append(f'<text x="{ml + pw - 6}" y="{(y0 + y1) / 2 + 3:.1f}" text-anchor="end" '
                         f'class="band-lab" fill="{b["color"]}">{esc(b["label"])}</text>')
    # y gridlines + labels
    for t in _ticks(lo, hi):
        y = Y(t)
        if y < mt - 1 or y > mt + ph + 1:
            continue
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + pw}" y2="{y:.1f}" '
                     f'stroke="var(--line)" stroke-width="1"/>')
        parts.append(f'<text x="{ml - 8}" y="{y + 3.5:.1f}" text-anchor="end" class="ctick">'
                     f'{esc(fmt_tick(t, dollars))}</text>')
    # x labels: start / middle / end
    if x_labels:
        n = len(x_labels)
        for j, lab in enumerate(x_labels):
            xx = ml if j == 0 else (ml + pw if j == n - 1 else ml + pw * j / (n - 1))
            anchor = "start" if j == 0 else ("end" if j == n - 1 else "middle")
            parts.append(f'<text x="{xx:.1f}" y="{h - 8}" text-anchor="{anchor}" class="ctick">'
                         f'{esc(lab)}</text>')
    # area fill under the main line
    n = len(vals)
    pts = " ".join(f"{X(i, n):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    if area:
        parts.append(f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
                     f'<stop offset="0%" stop-color="{color}" stop-opacity="0.22"/>'
                     f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
                     f'</linearGradient></defs>')
        parts.append(f'<polygon points="{ml},{mt + ph} {pts} {ml + pw},{mt + ph}" '
                     f'fill="url(#{uid})"/>')
    # overlay series (dashed)
    for ov in (overlays or []):
        ovals = [float(v) for v in ov.get("series", []) if v is not None]
        if len(ovals) < 2:
            continue
        on = len(ovals)
        opts = " ".join(f"{X(i, on):.1f},{Y(v):.1f}" for i, v in enumerate(ovals))
        parts.append(f'<polyline points="{opts}" fill="none" stroke="{ov["color"]}" '
                     f'stroke-width="1.6" stroke-dasharray="5 4"/>')
    # main line + end dot + value pill
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
    ex, ey = X(n - 1, n), Y(vals[-1])
    parts.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.4" fill="{color}"/>')
    if value_label:
        tw = 8.2 * len(value_label) + 14
        py = max(mt + 2, min(ey - 11, mt + ph - 24))
        px = ex - tw - 8 if ex + 6 + tw > w else ex + 6
        parts.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{tw:.1f}" height="21" rx="10.5" '
                     f'fill="var(--card)" stroke="{color}" stroke-width="1"/>')
        pill_extra = f' {pill_attr}' if pill_attr else ""
        parts.append(f'<text x="{px + tw / 2:.1f}" y="{py + 14.5:.1f}" text-anchor="middle" '
                     f'class="cpill" fill="{color}"{pill_extra}>{esc(value_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def chart_legend(entries):
    items = "".join(f'<span class="lgd"><span class="lgd-swatch" style="background:{c}'
                    f'{";height:2px" if dash else ""}"></span>{esc(t)}</span>'
                    for t, c, dash in entries)
    return f'<div class="chart-legend">{items}</div>'


def fng_gauge_svg(value):
    """Semicircular sentiment gauge, 0 (extreme fear) to 100 (extreme greed)."""
    import math
    cx, cy, r = 130, 122, 96

    def pt(v, radius):
        theta = math.pi * (1 - v / 100.0)
        return cx + radius * math.cos(theta), cy - radius * math.sin(theta)

    parts = [f'<svg class="gauge" viewBox="0 0 260 150" xmlns="http://www.w3.org/2000/svg" '
             f'role="img" aria-label="Fear and greed gauge reading {value}">']
    for a, b, color, _ in FNG_BANDS:
        x0, y0 = pt(a + 0.6, r)
        x1, y1 = pt(b - 0.6, r)
        parts.append(f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 1 {x1:.1f} {y1:.1f}" '
                     f'fill="none" stroke="{color}" stroke-width="15" stroke-linecap="butt"/>')
    nx, ny = pt(max(2, min(98, value)), r - 22)
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" '
                 f'stroke="currentColor" stroke-width="3" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="5.5" fill="currentColor"/>')
    parts.append(f'<text x="{cx}" y="{cy - 26}" text-anchor="middle" class="gauge-num">{value}</text>')
    parts.append("</svg>")
    return "".join(parts)


def flow_ledger(rows, aria="", compact=False):
    """Signed flows as LEDGER ROWS instead of a bar chart: date, a horizontal bar diverging
    from a center line (green right = in/accumulation, red left = out/sell side), and the
    dollar value at full text size. SVG bar charts scale their labels below legibility on
    phones; HTML rows never shrink, and the exact numbers are the point.
    rows: [(label, value_usd, tooltip_or_None), ...] oldest->newest (rendered newest first)."""
    if not rows:
        return ""
    max_abs = max((abs(v) for _, v, _ in rows), default=0) or 1
    out = [f'<div class="ledger{" compact" if compact else ""}" role="img" aria-label="{esc(aria)}">']
    for label, val, tip in reversed(rows):
        pct = abs(val) / max_abs * 50
        side = "pos" if val >= 0 else "neg"
        style = (f"left:50%;width:{pct:.1f}%" if val >= 0 else
                 f"right:50%;width:{pct:.1f}%")
        tip_attr = f' title="{esc(tip)}"' if tip else ""
        out.append(
            f'<div class="lrow"{tip_attr}><span class="ldate">{esc(label)}</span>'
            f'<span class="ltrack"><span class="lbar {side}" style="{style}"></span></span>'
            f'<span class="lval {"up" if val >= 0 else "down"}">'
            f'{"+" if val >= 0 else ""}{esc(fmt_usd(val))}</span></div>')
    out.append("</div>")
    return "".join(out)


def _chip(text, cls="", learn=""):
    """A posture chip; pass learn="#anchor" to make it a tap-link to its 101 lesson."""
    if learn:
        return f'<a class="chip {cls}" href="{learn}" title="tap for the plain-language explanation">{esc(text)}</a>'
    return f'<span class="chip {cls}">{esc(text)}</span>'


def _posture_card(a):
    win = a.get("window") or {}
    sym = a.get("symbol", "")
    overlays = []
    if a.get("spark_sma50"):
        overlays.append({"series": a["spark_sma50"], "color": C_SMA50})
    if a.get("spark_sma200"):
        overlays.append({"series": a["spark_sma200"], "color": C_SMA200})
    chart = line_chart_svg(
        a.get("spark"), overlays=overlays,
        x_labels=[win.get("start", ""), win.get("end", "")],
        value_label=_price_fmt(a.get("price")),
        aria=f"{sym} price over 90 days with 50 and 200 day averages, "
             f"currently {_price_fmt(a.get('price'))}",
        pill_attr=f'data-live="pill:{sym}"')
    legend = chart_legend([("price", trend_color(a.get("spark")), False),
                           ("50-day avg", C_SMA50, True),
                           ("200-day avg", C_SMA200, True)])
    rsi = a.get("rsi14")
    if rsi is None:
        rsi_chip = ""
    elif rsi >= 70:
        rsi_chip = _chip(f"RSI {rsi:.0f} hot", "chip-down", learn="#rsi101")
    elif rsi <= 30:
        rsi_chip = _chip(f"RSI {rsi:.0f} cold", "chip-cool", learn="#rsi101")
    else:
        rsi_chip = _chip(f"RSI {rsi:.0f} neutral", learn="#rsi101")
    mom = (_chip("Momentum building", "chip-up", learn="#momentum101") if a.get("macd_above_signal")
           else _chip("Momentum fading", "chip-down", learn="#momentum101"))
    trend = (_chip("Above 200-day", "chip-up", learn="#trend101") if a.get("above_sma200")
             else _chip("Below 200-day", "chip-down", learn="#trend101"))
    cross = (_chip("Golden cross", "chip-up", learn="#trend101") if a.get("golden_cross")
             else _chip("Death cross", "chip-down", learn="#trend101"))
    chg = a.get("chg_24h_pct")
    chg_html = ""
    if chg is not None:
        chg_html = (f'<span class="pc-chg {"up" if chg >= 0 else "down"}" '
                    f'data-live="chg:{esc(sym)}">{chg:+.2f}% (24h)</span>')
    stats = "".join(
        f'<div><dt>{esc(lab)}</dt><dd>{esc(_price_fmt(a.get(key)))}</dd></div>'
        for lab, key in (("50-day avg", "sma50"), ("200-day avg", "sma200"),
                         ("90-day high", "spark_high"), ("90-day low", "spark_low")))
    return f"""<div class="pulse-card">
  <div class="pc-head"><span class="pc-sym">{esc(sym)}<span class="live-dot"></span></span>
    <span class="pc-quote"><span class="pc-price" data-live="price:{esc(sym)}">{esc(_price_fmt(a.get("price")))}</span>{chg_html}</span></div>
  {chart}
  {legend}
  <dl class="pc-stats">{stats}</dl>
  <div class="pc-chips">{rsi_chip}{mom}{trend}{cross}
    {_chip(f'{a.get("pct_from_high_12m", 0):+.0f}% vs 12-mo high', learn="#chips101")}
    {_chip(f'volatility {a.get("vol30_pct", 0):.0f}%/yr', learn="#chips101")}</div>
</div>"""


def _fng_band_color(value):
    return next((c for a, b, c, _ in FNG_BANDS
                 if a <= value < b or (b == 100 and value == 100)), "#9AA0A6")


PULSE_DESKS = [
    ("sentiment", "Crowd sentiment", "The Fear & Greed gauge: what the crowd is feeling and how to read it."),
    ("posture", "Price posture", "RSI, momentum, and trend for the majors, in plain language."),
    ("stablecoins", "Stablecoin dry powder", "The market's fuel gauge: dollars staged inside crypto."),
    ("network", "Bitcoin network", "Fees and mining difficulty: how busy and how confident the chain is."),
]


def _dash_crumb():
    return '<span class="kicker"><a href="/pulse.html">Market Pulse</a> &middot; dashboard</span>'


def mp_hero():
    # The pulse loop is header atmosphere only (never adjacent to live numbers: the whole
    # board renders below on the plain background). Strictly lazy like the other section
    # videos: no autoplay attribute, motion-lazy pool, poster first paint.
    return ('<section class="ww-hero mp-hero" aria-label="Market Pulse"><div class="ww-heroinner"><div class="ww-panel">'
            '<video class="ww-vid motion-video motion-lazy" muted loop playsinline preload="none" '
            'poster="/assets/pulse/pulse-poster.jpg" aria-hidden="true" tabindex="-1">'
            '<source src="/assets/pulse/pulse-loop.webm" type="video/webm">'
            '<source src="/assets/pulse/pulse-loop.mp4" type="video/mp4"></video>'
            '<span class="ww-scrim" aria-hidden="true"></span>'
            '<span class="ww-panel-fg"><span class="kicker">Market Pulse</span>'
            '<span class="ww-title">The Board</span></span>'
            '</div></div></section>')


# DATA-AGE TRIPWIRE (audit 2026-07-28). A board is only as fresh as the deploy that built
# it, and the desk publishes market data as "live". If a refresh is missed, old numbers keep
# rendering under a live label: the exact dishonesty this desk exists to avoid. So every
# board states the instant its snapshot was generated, and when that instant is older than
# the refresh promise the board says so in its own voice instead of presenting stale numbers
# as current. Age is measured at BUILD time (the moment of publication), which is also when
# the generators run, so a healthy deploy stamps an age of roughly zero.
BOARD_FRESH_HOURS = 12  # the promise: three daily briefs plus the noon rebuild


def data_stamp(data, promise_hours=BOARD_FRESH_HOURS, what="This board"):
    """Visible provenance line for a data board: when the snapshot was generated and, when
    it has outrun the refresh promise, an explicit stale label."""
    import datetime as _dt
    d = data or {}
    ts = (d.get("generated_utc") or "").strip()
    if not ts:
        dated = (d.get("generated") or "").strip()
        when = f" The snapshot is dated {esc(dated)}." if dated else ""
        return (f'<p class="data-stamp stale"><b>{esc(what)} may be out of date.</b> '
                f'It carries no generation timestamp, so its age cannot be verified.{when}</p>')
    try:
        gen = _dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return f'<p class="data-stamp">Data as of {esc(ts)}.</p>'
    stamp = gen.strftime("%H:%M UTC on %d %b %Y").replace(" 0", " ")
    age_h = (_dt.datetime.now(_dt.timezone.utc) - gen).total_seconds() / 3600
    if age_h > promise_hours:
        hrs = int(age_h)
        older = f"{hrs} hours" if hrs < 48 else f"{hrs // 24} days"
        return (f'<p class="data-stamp stale"><b>Stale data.</b> {esc(what)} last refreshed '
                f'at {stamp}, about {older} ago, and the desk refreshes it several times a '
                f'day. Read these numbers as history, not as the current market.</p>')
    return f'<p class="data-stamp">Data as of {stamp}. Refreshed at every site build.</p>'


def _dash_shell(slug, title, desc, body_inner, dateline, live=False, data=None):
    stamp = data_stamp(data) if data is not None else ""
    body = (f'<main class="wrap"><section class="page">\n{body_inner}\n{stamp}\n'
            f'</section></main>')
    return shell(f"{title} - Market Pulse - {NAME}", desc, "Market Pulse", body, dateline,
                 body_class="ww-dark", path=f"/pulse/{slug}.html", live_js=live)


def _no_data(cmd="python3 market_pulse.py"):
    return (f'<div class="empty"><span class="k">No data yet</span>'
            f'<p style="margin:.6em 0 0">This dashboard refreshes from free public data at each '
            f'site build. Generate it locally with <code>{esc(cmd)}</code>.</p></div>')


def render_pulse_hub(pulse, flows, cm, dateline):
    """THE BOARD: the master dashboard. The Chart Master's read full-width on top, then
    NINE even cards in rows of three, importance descending by the house reading doctrine
    (price, flows, positioning, then the day and the chain as the supporting row). The
    doctrine group rides in each card's label; the 101 teaching lives on the deep boards."""
    desc = ("The Board: every market desk at a glance - price posture, ETF and whale flows, "
            "leverage, sentiment, and the Bitcoin network, ordered the way a desk reads a "
            "market. Market data, not advice.")
    pulse = pulse or {}
    W = []

    def widget(href, lab, stat, sub="", mini="", stat_color="", cls=""):
        color = f' style="color:{stat_color}"' if stat_color else ""
        W.append(f'''<a class="dash-card widget{cls}" href="{href}">
      <span class="lab">{lab}</span>
      <span class="dash-stat"{color}>{stat}</span>
      {f'<span class="w-sub">{sub}</span>' if sub else ""}
      {f'<div class="pc-spark">{mini}</div>' if mini else ""}</a>''')

    # The read: the desk's synthesis of everything below, full width (not a card)
    if (cm or {}).get("headline"):
        W.append(f'''<a class="dash-card widget wide" href="/chartmaster.html">
      <span class="lab">The Chart Master&rsquo;s read &middot; {esc(fmt_date(cm.get("date")))}</span>
      <span class="w-read">&ldquo;{esc(cm["headline"])}&rdquo;</span></a>''')

    # Row 1 - what the market is doing
    assets = pulse.get("assets") or []
    if assets:
        btc = assets[0]
        chg = btc.get("chg_24h_pct")
        chg_s = f' <span class="w-delta {"up" if chg >= 0 else "down"}">{chg:+.1f}%</span>' if chg is not None else ""
        widget("/pulse/posture.html", "Price &middot; BTC posture",
               f'<span data-live="price:BTC">{esc(_price_fmt(btc.get("price")))}</span>{chg_s}',
               f'RSI {btc.get("rsi14", 0):.0f} &middot; '
               f'{"above" if btc.get("above_sma200") else "below"} 200-day',
               spark_widget((btc.get("spark") or [])[-30:], "30d"))
    mkt = pulse.get("market") or {}
    if mkt.get("total_mcap_usd"):
        mchg = mkt.get("mcap_change_24h_pct")
        mchg_s = (f' <span class="w-delta {"up" if mchg >= 0 else "down"}">{mchg:+.1f}%</span>'
                  if mchg is not None else "")
        dom = mkt.get("btc_dominance_pct", 0)
        dom_bar = (f'<span class="dom-bar"><span style="width:{dom:.1f}%"></span></span>'
                   f'<span class="w-range">BTC is {dom:.1f}% of the whole crypto market</span>')
        widget("/pulse/prices.html", "Price &middot; Whole market",
               f'{esc(fmt_tick(mkt["total_mcap_usd"]))}{mchg_s}',
               'total crypto market cap &middot; 24h change', dom_bar)
    etf = (pulse.get("etf_flows") or {}).get("btc") or {}
    if etf.get("latest_net_usd_m") is not None:
        latest = etf["latest_net_usd_m"]
        mini = flow_ledger([(d.get("date", "")[:6], (d.get("net_usd_m") or 0) * 1e6, None)
                            for d in etf.get("recent", [])[-4:]],
                           aria="BTC ETF flows, last 4 trading days", compact=True)
        widget("/pulse/etf.html", "Flows &middot; ETF flows",
               f'{"+" if latest >= 0 else ""}{esc(fmt_usd(latest * 1e6))}',
               f'BTC spot ETFs, {esc(etf.get("latest_date", ""))}', mini,
               stat_color="var(--up)" if latest >= 0 else "var(--down)")

    # Row 2 - where the money is moving, and how leveraged the bets are
    if flows and flows.get("volatile"):
        wnet = flows["volatile"].get("net_usd", 0)
        wmini = flow_ledger(
            [(f'wk {w.get("week_ending", "")}', w.get("net_usd", 0), None)
             for w in (flows.get("history") or [])[-4:]],
            aria="Weekly whale net flow, last 4 weeks", compact=True)
        widget("/flows.html", "Flows &middot; Whale Watch",
               f'{esc(fmt_usd(abs(wnet)))}',
               f'net {"off" if wnet >= 0 else "onto"} exchanges, '
               f'{esc(_win_phrase(flows.get("window_hours", 24)))}', wmini,
               stat_color="var(--up)" if wnet >= 0 else "var(--down)")
    lev = (pulse.get("leverage") or {}).get("assets") or []
    btcl = next((a for a in lev if a.get("symbol") == "BTC"), None)
    if btcl:
        ls = btcl.get("long_short_ratio")
        sub = (f'BTC funding &middot; {esc(fmt_usd(btcl.get("open_interest_usd", 0)))} OI'
               + (f' &middot; {ls:.2f} L/S' if ls is not None else ""))
        q = btcl.get("liquidations") or {}
        if q.get("count"):
            longs, shorts = q.get("longs_usd", 0), q.get("shorts_usd", 0)
            side = "longs" if longs >= shorts else "shorts"
            sub += (f'<br>liqs {esc(fmt_usd(longs + shorts))} last '
                    f'{q.get("window_hours", "?")}h &middot; mostly {side}')
        widget("/pulse/leverage.html", "Positioning &middot; Leverage",
               f'{btcl.get("funding_8h_pct", 0):+.4f}% <span class="w-unit">/8h</span>', sub,
               spark_widget(btcl.get("oi_history_usd") or [], "30d open interest"))
    stables = pulse.get("stables") or {}
    if stables.get("total_usd"):
        chg = stables.get("change_30d_pct", 0)
        widget("/pulse/stablecoins.html", "Flows &middot; Stablecoin dry powder",
               esc(fmt_usd(stables["total_usd"])),
               f'<span class="w-delta {"up" if chg >= 0 else "down"}">{chg:+.1f}%</span> in 30 days',
               spark_widget((stables.get("spark") or [])[-60:], "60d"))

    # Row 3 - the supporting desks: the day's action, the mood, the chain
    movers = pulse.get("movers") or {}
    if movers.get("gainers"):
        g = movers["gainers"][0]
        l = (movers.get("losers") or [{}])[0]
        g_line = " &middot; ".join(f'{esc(x.get("symbol", ""))} {x.get("chg_24h_pct", 0):+.1f}%'
                                   for x in movers.get("gainers", [])[:3])
        l_line = " &middot; ".join(f'{esc(x.get("symbol", ""))} {x.get("chg_24h_pct", 0):+.1f}%'
                                   for x in movers.get("losers", [])[:3])
        mv_mini = (f'<span class="w-range" style="color:var(--up)">up&nbsp; {g_line}</span>'
                   f'<span class="w-range" style="color:var(--down)">down&nbsp; {l_line}</span>')
        widget("/pulse/movers.html", "The day &middot; Top movers",
               f'{esc(g.get("symbol", ""))} <span class="w-delta up">{g.get("chg_24h_pct", 0):+.1f}%</span>',
               "the day&rsquo;s biggest big-cap moves, both directions", mv_mini)
    fng = pulse.get("fng") or {}
    if fng.get("value") is not None:
        v = fng["value"]
        widget("/pulse/sentiment.html", "The day &middot; Crowd sentiment",
               f'{v} &middot; {esc((fng.get("label") or "").lower())}',
               "the foil: what the crowd feels, not what the money does",
               spark_widget((fng.get("history") or [])[-30:], "30d", dollars=False),
               stat_color=_fng_band_color(v))
    network = pulse.get("network") or {}
    if network.get("fastest_fee") is not None:
        fee = network.get("fastest_fee", 0) or 0
        busy = "a quiet chain" if fee <= 5 else ("normal traffic" if fee <= 30 else "a crowded chain")
        net_mini = (f'<span class="w-range">1-hour fee {network.get("hour_fee", "?")} sat/vB &middot; '
                    f'difficulty {network.get("difficulty_change_pct", 0):+.1f}% &middot; '
                    f'retarget in {network.get("retarget_blocks", "?")} blocks</span>'
                    f'<span class="w-range">sat/vB = satoshis per virtual byte, the bid for block space</span>')
        widget("/pulse/network.html", "Chain &middot; Bitcoin network",
               f'{network.get("fastest_fee", "?")} <span class="w-unit">sat/vB</span>',
               f'next-block fee: {busy}', net_mini, cls=" mspan")

    body = mp_hero() + f'''<main class="wrap"><section class="page">
  <div class="ey" style="margin:14px 0 0">
    <span class="daily-badge">refreshed through the day</span></div>
  <h1 style="margin-top:6px">The Board</h1>
  <p class="lede" style="margin-bottom:10px">Every desk at a glance, in the order a desk
     reads a market: price, flows, positioning, then the day and the chain. Tap any card
     for the full board, where every number is taught in plain language.
     <span class="live-stamp"><span class="live-dot"></span>prices update in your browser
     <span data-live="stamp"></span></span></p>
  <div class="dash-grid widget-grid">{"".join(W)}</div>
  {data_stamp(pulse, what="The market boards")}
  <p class="nfa">{esc(pulse.get("note", ""))} {esc(NFA)}</p>
</section></main>'''
    return shell(f"The Board - Market Pulse - {NAME}", desc, "Market Pulse", body, dateline,
                 body_class="ww-dark", path="/pulse.html", live_js=True)

def render_pulse_sentiment(pulse, dateline):
    desc = ("The crypto Fear & Greed Index explained: what feeds the gauge, what extremes "
            "have historically meant, and why it measures mood, not value.")
    fng = (pulse or {}).get("fng") or {}
    if not fng:
        inner = f"{_dash_crumb()}\n  <h1>Crowd sentiment</h1>\n  {_no_data()}"
        return _dash_shell("sentiment", "Crowd sentiment", desc, inner, dateline, data=pulse)
    v = fng.get("value", 50)
    win = fng.get("window") or {}
    hist = fng.get("history") or []
    zone_bands = [{"from": a, "to": b, "color": c, "label": lab.lower()}
                  for a, b, c, lab in FNG_BANDS]
    chart = line_chart_svg(
        hist, dollars=False, y_min=0, y_max=100, bands=zone_bands,
        x_labels=[win.get("start", ""), win.get("end", "")],
        value_label=f"{v} today",
        aria=f"Fear and greed index over the last 90 days, currently {v}")
    inner = f"""{_dash_crumb()}
  <h1>Crowd sentiment</h1>
  <p class="lede">One number for the market's mood, from 0 (extreme fear) to 100 (extreme
     greed). Today: {v}, {esc(fng.get("label", "").lower())}.</p>
  <div class="pulse-grid2">
    <div class="pulse-card center">{fng_gauge_svg(v)}
      <div class="gauge-label" style="color:{_fng_band_color(v)}">{esc(fng.get("label",""))}</div>
      <p class="pc-note">Fear &amp; Greed Index, via alternative.me
      <span class="daily-badge">daily data</span></p></div>
    <div class="pulse-card"><span class="lab">How to read it</span>
      <p class="pc-note" style="font-size:14.5px">Reading the trend matters more than any
      single day: a mood that has been dark for weeks tells you more than one nervous
      afternoon. The zones on the chart below are the same ones the gauge uses, so you can
      see exactly how long the crowd has been sitting in fear or greed.</p></div>
  </div>

  <div class="sec-head" style="margin-top:26px"><h2>90 days of crowd mood</h2><span class="bar"></span></div>
  <div class="chartcard">{chart}</div>

  <div class="sec-head" style="margin-top:30px"><h2>Sentiment 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">What feeds it</span>
      <p>The index blends measurable proxies for emotion: price volatility, trading volume,
      social media chatter, and Bitcoin dominance. When those run hot the score climbs toward
      greed; when they freeze up it sinks toward fear.</p></div>
    <div class="learn"><span class="lab">What extremes have meant</span>
      <p>Historically, <b>extreme fear</b> has often appeared near local bottoms and
      <b>extreme greed</b> near local tops, because crowds overreact in both directions. That
      is a tendency, not a law: fear can stay extreme for months in a real bear market.</p></div>
    <div class="learn"><span class="lab">Mood, not value</span>
      <p>The gauge says nothing about what anything is worth. It measures how people feel
      about prices, which is exactly why it is useful and exactly why it should never be a
      buy or sell signal on its own.</p></div>
  </div>
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("sentiment", "Crowd sentiment", desc, inner, dateline, data=pulse)


def render_pulse_posture(pulse, dateline):
    desc = ("Major-asset price posture: RSI, MACD momentum, 50/200-day trend, distance "
            "from the 12-month high, and volatility, each explained in plain language.")
    assets = (pulse or {}).get("assets") or []
    if not assets:
        inner = f"{_dash_crumb()}\n  <h1>Price posture</h1>\n  {_no_data()}"
        return _dash_shell("posture", "Price posture", desc, inner, dateline, live=True, data=pulse)
    cards = "".join(_posture_card(a) for a in assets)
    inner = f"""{_dash_crumb()}
  <h1>Price posture</h1>
  <p class="lede">Where the majors stand, measured with fixed, standard formulas on daily
     closes: RSI-14, MACD 12/26/9, the 50- and 200-day averages, distance from the 12-month
     high, and 30-day realized volatility.</p>
  <p class="live-stamp"><span class="live-dot"></span>prices update in your browser
     <span data-live="stamp"></span></p>
  <div class="pulse-stack">{cards}</div>
  <p class="pc-note" style="margin-top:8px">Solid line is price over 90 days; the dashed
  lines are the 50- and 200-day averages the trend chips refer to. Every chip is defined
  below; we publish the formulas, never a recommendation.</p>

  <div class="sec-head" style="margin-top:30px"><h2>Posture 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn" id="rsi101"><span class="lab">RSI</span>
      <p>The Relative Strength Index compares recent gains to recent losses on a 0-100 scale.
      Above 70 reads as <b>hot</b> (overbought), below 30 as <b>cold</b> (oversold). Extremes
      often cool off, but a strong trend can stay hot for weeks.</p></div>
    <div class="learn" id="momentum101"><span class="lab">Momentum (MACD)</span>
      <p>MACD compares a fast moving average to a slow one. When the fast line sits above its
      signal line, momentum is <b>building</b>; below it, momentum is <b>fading</b>. It shows
      which way the wind is blowing, not how long it will blow.</p></div>
    <div class="learn" id="trend101"><span class="lab">Trend (moving averages)</span>
      <p>The 200-day average is the classic bull/bear line: price above it reads as an uptrend.
      When the 50-day crosses above the 200-day, that is a <b>golden cross</b> and trend
      followers take notice. Crossing below is the bearish twin, the <b>death cross</b>.</p></div>
    <div class="learn" id="chips101"><span class="lab">The other two chips</span>
      <p>Distance from the <b>12-month high</b> says how deep the drawdown is; annualized
      <b>volatility</b> says how violently price has been moving lately. High volatility cuts
      both ways: bigger rallies, bigger drops, worse sleep.</p></div>
    <div class="learn"><span class="lab">Reading them together</span>
      <p>No single chip is a verdict. Fear plus a death cross plus building momentum, for
      example, is a market arguing with itself. The honest read is the full picture, which is
      why every card shows all of it.</p></div>
    <div class="learn"><span class="lab">What this page is not</span>
      <p>Indicators describe the recent past; none of them predict. We publish them with fixed,
      standard formulas so you can learn to read them yourself, and we will never turn them
      into a buy or sell call. That is the deal.</p></div>
  </div>
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("posture", "Price posture", desc, inner, dateline, live=True, data=pulse)


def render_pulse_stables(pulse, dateline):
    desc = ("Total stablecoin float explained: why the dollars parked in USDT, USDC and "
            "friends are the market's fuel gauge, with a one-year trend.")
    stables = (pulse or {}).get("stables") or {}
    if not stables:
        inner = f"{_dash_crumb()}\n  <h1>Stablecoin dry powder</h1>\n  {_no_data()}"
        return _dash_shell("stablecoins", "Stablecoin dry powder", desc, inner, dateline, data=pulse)
    chg = stables.get("change_30d_pct", 0)
    chg_chip = _chip(f"{chg:+.1f}% in 30 days", "chip-up" if chg >= 0 else "chip-down")
    win = stables.get("window") or {}
    chart = line_chart_svg(
        stables.get("spark"), x_labels=[win.get("start", ""), win.get("end", "")],
        value_label=fmt_tick(stables.get("total_usd", 0)),
        aria=f"Total stablecoin float over one year, currently "
             f"{fmt_usd(stables.get('total_usd', 0))}")
    inner = f"""{_dash_crumb()}
  <h1>Stablecoin dry powder</h1>
  <p class="lede">Stablecoins are dollars that already made the jump into crypto. The size of
     that float is the market's fuel gauge: money staged to buy, or money heading for the exit.</p>
  <div class="pulse-grid2">
    <div class="pulse-card"><span class="lab">Total USD-pegged float</span>
      <span class="pc-big">{esc(fmt_usd(stables.get("total_usd", 0)))}</span>
      <div class="pc-chips">{chg_chip}</div>
      <p class="pc-note">All dollars parked in stablecoins across chains, per DefiLlama.
      <span class="daily-badge">daily data</span></p></div>
    <div class="pulse-card"><span class="lab">How to read it</span>
      <p class="pc-note" style="font-size:14.5px">The direction of the line is the story:
      a growing float means money is staying in the arena, staged to buy; a shrinking float
      means money is leaving crypto entirely. The 30-day change chip gives you the recent
      lean at a glance.</p></div>
  </div>

  <div class="sec-head" style="margin-top:26px"><h2>One-year float</h2><span class="bar"></span></div>
  <div class="chartcard">{chart}</div>

  <div class="sec-head" style="margin-top:30px"><h2>Dry powder 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Why it matters</span>
      <p>Before anyone can buy crypto at scale, dollars have to enter the system, and they
      usually arrive as stablecoins. A growing float is potential demand parked at the door.
      It does not say when, or whether, that money will actually buy.</p></div>
    <div class="learn"><span class="lab">Mints and burns</span>
      <p>Issuers create (mint) stablecoins when money comes in and destroy (burn) them when it
      leaves. The biggest mints and burns show up as news in our daily brief, because a
      billion-dollar mint is a story, not just a statistic.</p></div>
    <div class="learn"><span class="lab">Read it with Whale Watch</span>
      <p>This page shows the SIZE of the float; <a href="/flows.html">Whale Watch</a> shows
      where big chunks of it are MOVING, onto or off exchanges. Size is the fuel level, flows
      are the throttle.</p></div>
  </div>
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("stablecoins", "Stablecoin dry powder", desc, inner, dateline, data=pulse)


def _mover_rows(movers):
    rows = []
    for m in movers:
        chg = m.get("chg_24h_pct", 0)
        chip = _chip(f"{chg:+.1f}%", "chip-up" if chg >= 0 else "chip-down")
        price = m.get("price")
        if not price:
            price_s = "?"
        elif price >= 100:
            price_s = f"${price:,.0f}"
        elif price >= 1:
            price_s = f"${price:,.2f}"
        else:
            price_s = "$" + f"{price:.6f}".rstrip("0").rstrip(".")
        rows.append(
            f'<tr><td class="mut">#{m.get("rank", "?")}</td>'
            f'<td class="sym2">{esc(m.get("symbol", ""))}<span class="mut"> &middot; '
            f'{esc((m.get("name") or "")[:14])}</span></td>'
            f'<td class="pnum">{esc(price_s)}</td>'
            f'<td>{chip}</td>'
            f'<td class="mut">{esc(fmt_usd(m.get("mcap_usd", 0)))} cap</td></tr>')
    return "".join(rows)


def render_pulse_movers(pulse, dateline):
    desc = ("Top 5 gainers and losers over 24 hours, drawn only from the top 100 coins by "
            "market cap, with plain-language guidance on how to read big moves.")
    movers = (pulse or {}).get("movers") or {}
    if not movers:
        inner = f"{_dash_crumb()}\n  <h1>Top movers</h1>\n  {_no_data()}"
        return _dash_shell("movers", "Top movers", desc, inner, dateline, live=True, data=pulse)
    inner = f"""{_dash_crumb()}
  <h1>Top movers</h1>
  <p class="lede">The five biggest gainers and losers of the last 24 hours, drawn only from
     the top {movers.get("universe", 100)} coins by market cap, so micro-cap pump coins never
     make this board.</p>
  <p class="live-stamp"><span class="live-dot"></span>tables update in your browser
     <span data-live="stamp"></span></p>
  <div class="pulse-grid2">
    <div class="pulse-card"><span class="lab" style="color:var(--up)">Top 5 gainers (24h)<span class="live-dot"></span></span>
      <div class="movetable" tabindex="0" role="region" aria-label="Top gainers (scrollable)"><table><tbody data-live="movers:gainers">{_mover_rows(movers.get("gainers", []))}</tbody></table></div></div>
    <div class="pulse-card"><span class="lab" style="color:var(--down)">Top 5 losers (24h)<span class="live-dot"></span></span>
      <div class="movetable" tabindex="0" role="region" aria-label="Top losers (scrollable)"><table><tbody data-live="movers:losers">{_mover_rows(movers.get("losers", []))}</tbody></table></div></div>
  </div>

  <div class="sec-head" style="margin-top:30px"><h2>Movers 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Why coins move this much</span>
      <p>Double-digit daily moves usually have a cause: a listing, a protocol launch, an
      unlock, a hack, or a big holder buying or selling into thin liquidity. Smaller coins
      move more because less money is needed to push them.</p></div>
    <div class="learn"><span class="lab">Why top-100 only</span>
      <p>Outside the biggest names, "top gainer" lists get taken over by micro-cap coins that
      pump 300% on a few thousand dollars of volume, exactly the shill we exist to strip out.
      Limiting to the top 100 keeps every mover here a coin with real money behind it.</p></div>
    <div class="learn"><span class="lab">Check the news before you believe it</span>
      <p>A big move WITH a verified story behind it is information. A big move with no story
      is usually noise, or worse, someone's exit. Cross-check the <a href="/index.html">front
      page</a>: if a mover matters, the desk will have covered why.</p></div>
    <div class="learn"><span class="lab">What this page is not</span>
      <p>Yesterday's winner is not a prediction about tomorrow, and chasing a move that
      already happened is how crowds get hurt. This board is a snapshot of where the action
      was, never a list of things to buy.</p></div>
  </div>
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("movers", "Top movers", desc, inner, dateline, live=True, data=pulse)


def _price_fmt(price):
    if not price:
        return "?"
    if price >= 100:
        return f"${price:,.0f}"
    if price >= 1:
        return f"${price:,.2f}"
    return "$" + f"{price:.6f}".rstrip("0").rstrip(".")


def _top100_rows(coins):
    rows = []
    for c in coins:
        chg = c.get("chg_24h_pct")
        chg_html = (f'<span class="chip {"chip-up" if chg >= 0 else "chip-down"}">{chg:+.1f}%</span>'
                    if chg is not None else '<span class="chip">?</span>')
        spark = c.get("spark7d") or []
        up = len(spark) >= 2 and spark[-1] >= spark[0]
        spark_html = (f'<span class="row-spark" style="color:{"var(--up)" if up else "var(--down)"}">'
                      f'{spark_svg(spark, w=110, h=26)}</span>') if spark else ""
        rows.append(
            f'<tr data-sym="{esc(c.get("symbol", ""))}">'
            f'<td class="mut" data-cell="rank" data-val="{c.get("rank") or 999}">#{c.get("rank", "?")}</td>'
            f'<td class="sym2">{esc(c.get("symbol", ""))}<span class="mut"> &middot; '
            f'{esc((c.get("name") or "")[:18])}</span></td>'
            f'<td>{spark_html}</td>'
            f'<td class="pnum" data-cell="price" data-val="{c.get("price") or 0}">{esc(_price_fmt(c.get("price")))}</td>'
            f'<td data-cell="chg" data-val="{chg if chg is not None else 0}">{chg_html}</td>'
            f'<td class="mut" data-cell="mcap" data-val="{c.get("mcap_usd") or 0}">{esc(fmt_usd(c.get("mcap_usd", 0)))}</td></tr>')
    return "".join(rows)


def render_pulse_prices(pulse, dateline):
    desc = ("Live prices, 7-day trend, 24-hour change, and market cap for the top 100 "
            "cryptocurrencies by market cap. Sortable, updated in your browser.")
    movers = (pulse or {}).get("movers") or {}
    coins = movers.get("top100") or []
    if not coins:
        inner = f"{_dash_crumb()}\n  <h1>Top 100</h1>\n  {_no_data()}"
        return _dash_shell("prices", "Top 100", desc, inner, dateline, data=pulse)
    total_mcap = sum(c.get("mcap_usd") or 0 for c in coins)
    # Name what the screen removed. A filtered board that does not say it filtered is just
    # a board with a secret. See coin_screen.py for the tests behind each reason.
    out = (movers or {}).get("screened_out") or []
    if out:
        WHY = {"captive": "traded almost entirely on the venue that issues it",
               "untraded": "no reported trading",
               "supply": "cap rests on unconfirmed supply"}
        bits = ", ".join(f'{esc(o["symbol"])} ({esc(WHY.get(o["reason"], o["reason"]))})'
                         for o in out)
        screened = (f'\n  <p class="screen-note">Screened out of this board today: {bits}. '
                    f'Places filled from below.</p>')
    else:
        screened = ""
    inner = f"""{_dash_crumb()}
  <h1>Top 100</h1>
  <p class="lede">Every coin in the top 100 by market cap: price, 7-day trend, 24-hour
     change. {esc(fmt_usd(total_mcap))} of market tracked. Click a column header to sort.</p>
  <p class="live-stamp"><span class="live-dot"></span>prices update in your browser
     <span data-live="stamp"></span></p>
  <div class="movetable prices-table"><table>
    <thead><tr>
      <th scope="col" data-sort="rank" aria-sort="ascending"><button type="button" class="th-sort">#</button></th>
      <th scope="col">Coin</th><th scope="col">7d</th>
      <th scope="col" data-sort="price" aria-sort="none"><button type="button" class="th-sort">Price</button></th>
      <th scope="col" data-sort="chg" aria-sort="none"><button type="button" class="th-sort">24h</button></th>
      <th scope="col" data-sort="mcap" aria-sort="none"><button type="button" class="th-sort">Market cap</button></th>
    </tr></thead>
    <tbody data-live="top100">{_top100_rows(coins)}</tbody>
  </table></div>

  <div class="sec-head" style="margin-top:30px"><h2>Prices 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">What market cap means</span>
      <p>Price times circulating supply. It is the market's total bet on a coin, and the only
      fair way to compare a $60,000 coin to a $0.60 one. Rank is just market cap in order.</p></div>
    <div class="learn"><span class="lab">Why ranks shift</span>
      <p>A coin climbing the table means money is flowing in faster than into its neighbors.
      Watching WHO is climbing over weeks tells you more than any single day's prices.</p></div>
    <div class="learn"><span class="lab">Not a menu</span>
      <p>Being big is not being good: rank measures size, not quality, and plenty of coins
      have ridden this table down as well as up. This is a reference page, never a buy list.</p></div>
    <div class="learn"><span class="lab">What we leave out</span>
      <p>A market cap is only real if the price came from a market. We drop coins whose
      volume is almost entirely on the venue that issues them, coins with no reported
      trading at all, and coins whose cap rests on more supply than their own listing
      confirms. Freed places are filled from further down, so this is still a full
      hundred.</p></div>
  </div>{screened}
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("prices", "Top 100", desc, inner, dateline, live=True, data=pulse)


def render_pulse_leverage(pulse, dateline):
    desc = ("The derivatives tape for the majors: funding, open interest trend, the "
            "long/short ratio, and recent liquidations, in plain language.")
    lev = (pulse or {}).get("leverage") or {}
    assets = lev.get("assets") or []
    if not assets:
        inner = f"{_dash_crumb()}\n  <h1>Leverage</h1>\n  {_no_data()}"
        return _dash_shell("leverage", "Leverage", desc, inner, dateline, data=pulse)
    rows = ""
    for a in assets:
        f8 = a.get("funding_8h_pct", 0)
        cls = "chip-down" if f8 > 0.01 else ("chip-cool" if f8 < 0 else "")
        ls = a.get("long_short_ratio")
        ls_html = (f'<span class="chip {"chip-down" if ls >= 1.5 else ""}">{ls:.2f} L/S</span>'
                   if ls is not None else '<span class="mut">&mdash;</span>')
        rows += (f'<tr><td class="sym2">{esc(a.get("symbol",""))}</td>'
                 f'<td class="pnum"><span class="chip {cls}">{f8:+.4f}% / 8h</span></td>'
                 f'<td class="pnum">{a.get("funding_annual_pct", 0):+.1f}%/yr</td>'
                 f'<td class="pnum">{esc(fmt_usd(a.get("open_interest_usd", 0)))}</td>'
                 f'<td class="pnum">{ls_html}</td>'
                 f'<td class="mut">{esc(a.get("venue",""))}</td></tr>')
    # liquidations: forced closes by side, per asset (recent window, single venue)
    liq_rows = ""
    for a in assets:
        q = a.get("liquidations") or {}
        if not q.get("count"):
            continue
        liq_rows += (f'<tr><td class="sym2">{esc(a.get("symbol",""))}</td>'
                     f'<td class="pnum">{q["count"]}</td>'
                     f'<td class="pnum" style="color:var(--down)">{esc(fmt_usd(q.get("longs_usd", 0)))}</td>'
                     f'<td class="pnum" style="color:var(--up)">{esc(fmt_usd(q.get("shorts_usd", 0)))}</td>'
                     f'<td class="mut">last {q.get("window_hours", "?")}h</td></tr>')
    liq_html = ""
    if liq_rows:
        liq_html = f"""<div class="sec-head" style="margin-top:26px"><h2>Recent liquidations</h2><span class="bar"></span></div>
  <div class="movetable" tabindex="0" role="region" aria-label="Recent liquidations (scrollable)"><table>
    <thead><tr><th><span class="sr-only">Asset</span></th><th>Forced closes</th><th>Longs liquidated</th><th>Shorts liquidated</th><th>Window</th></tr></thead>
    <tbody>{liq_rows}</tbody></table></div>
  <p class="pc-note" style="margin-top:8px">Forced position closes on one venue's public feed,
  by which side got caught. Lopsided liquidations show which crowd was leaning wrong.</p>"""
    # trend charts for the deepest market: funding history + OI trend
    charts_html = ""
    btc = assets[0]
    if btc.get("funding_history_pct") and len(btc["funding_history_pct"]) > 2:
        fh = btc["funding_history_pct"]
        chart = line_chart_svg(fh, dollars=False, x_labels=["21 funding intervals ago", "now"],
                               value_label=f"{fh[-1]:+.4f}%",
                               aria=f"{btc.get('symbol','BTC')} funding rate history")
        charts_html += (f'<div class="sec-head" style="margin-top:26px"><h2>BTC funding, last 21 intervals</h2>'
                        f'<span class="bar"></span></div><div class="chartcard">{chart}</div>'
                        f'<p class="pc-note" style="margin-top:8px">Each point is one 8-hour funding interval (%). '
                        f'Above zero, longs pay shorts; the further from zero, the more crowded the trade.</p>')
    if btc.get("oi_history_usd") and len(btc["oi_history_usd"]) > 2:
        oi = btc["oi_history_usd"]
        chart = line_chart_svg(oi, x_labels=["30 days ago", "now"],
                               value_label=fmt_tick(oi[-1]),
                               aria=f"{btc.get('symbol','BTC')} open interest, 30 days")
        charts_html += (f'<div class="sec-head" style="margin-top:26px"><h2>BTC open interest, 30 days</h2>'
                        f'<span class="bar"></span></div><div class="chartcard">{chart}</div>'
                        f'<p class="pc-note" style="margin-top:8px">Total money in open contracts on the venue. '
                        f'Rising OI with rising price is new money chasing; falling OI into a move is positions closing out.</p>')
    inner = f"""{_dash_crumb()}
  <h1>Leverage</h1>
  <p class="lede">The derivatives tape: what leveraged traders are paying to hold their bets
     (funding), how much money is in those bets (open interest), which way the crowd leans
     (long/short), and who just got carried out (liquidations). This is where crowding
     shows up before it shows up in price.</p>
  <div class="movetable" tabindex="0" role="region" aria-label="Funding and open interest (scrollable)"><table>
    <thead><tr><th><span class="sr-only">Asset</span></th><th>Funding</th><th>Annualized</th><th>Open interest</th><th>Long/short</th><th>Venue</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
  <p class="pc-note" style="margin-top:8px">Single-venue snapshots from public exchange data,
  refreshed with each site build; they move with the market but are not market-wide totals.</p>
  {charts_html}
  {liq_html}

  <div class="sec-head" style="margin-top:30px"><h2>Leverage 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Funding is the cost of conviction</span>
      <p>A perpetual swap has no expiry, so exchanges keep its price pinned to the real market
      with funding: every eight hours, one side pays the other. <b>Positive funding means longs
      are paying shorts</b>, the crowd is leaning bullish and paying for the privilege. Negative
      funding means shorts are paying, the crowd leans bearish.</p></div>
    <div class="learn"><span class="lab">Extremes are the tell</span>
      <p>Near-zero funding is a calm market. Persistently rich funding (think tenths of a
      percent every 8 hours, double-digit annualized) means a crowded, expensive trade that
      often unwinds violently when price stops cooperating. It is a crowd gauge, not a
      direction signal.</p></div>
    <div class="learn"><span class="lab">Open interest is the fuel</span>
      <p>Open interest is the total money sitting in open contracts. Rising OI with rising
      price = new money chasing the move. High OI is also fuel for liquidation cascades:
      when price moves fast against the crowd, forced closes accelerate it.</p></div>
    <div class="learn"><span class="lab">Long/short is the lean</span>
      <p>The long/short ratio counts accounts positioned each way. At 1.00 the crowd is
      balanced; well above it, longs are crowded. A heavily crowded side is the side that
      gets squeezed hardest when price goes the other way.</p></div>
    <div class="learn"><span class="lab">Liquidations are the receipts</span>
      <p>A liquidation is a leveraged position the exchange force-closed because the margin
      ran out. Lopsided liquidations tell you which crowd was wrong today, and clusters of
      them can accelerate the very move that caused them.</p></div>
    <div class="learn"><span class="lab">What it cannot tell you</span>
      <p>These are snapshots from one venue's public data, not the whole market, and funding
      flips fast. Treat this as context for how stretched the boat is, never as a trade
      signal on its own.</p></div>
  </div>
  <p class="nfa">{esc(lev.get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("leverage", "Leverage", desc, inner, dateline, data=pulse)


def render_pulse_etf(pulse, dateline):
    desc = ("Daily US spot Bitcoin and Ethereum ETF net flows: the traditional-finance "
            "bid, in plain language. Market data, not advice.")
    etf = (pulse or {}).get("etf_flows") or {}
    if not etf.get("btc") and not etf.get("eth"):
        inner = f"{_dash_crumb()}\n  <h1>ETF flows</h1>\n  {_no_data()}"
        return _dash_shell("etf", "ETF flows", desc, inner, dateline, data=pulse)
    boards = ""
    for key, name in (("btc", "Bitcoin"), ("eth", "Ethereum")):
        b = etf.get(key)
        if not b:
            continue
        latest = b.get("latest_net_usd_m") or 0
        cls = "up" if latest >= 0 else "down"
        word = "into" if latest >= 0 else "out of"
        cum = b.get("cumulative_usd_m")
        cum_html = (f'<span class="sub">{esc(fmt_usd(cum * 1e6))} cumulative since launch</span>'
                    if cum is not None else "")
        boards += f"""<div class="sec-head" style="margin-top:26px"><h2>{esc(name)} spot ETFs</h2><span class="bar"></span></div>
  <div class="stats"><div class="stat">
    <span class="lab">Latest day ({esc(b.get("latest_date", ""))})</span>
    <span class="big {cls}">{esc(fmt_usd(latest * 1e6))}</span>
    <span class="sub">net {word} the funds</span>
  </div><div class="stat">
    <span class="lab">Since launch</span>
    <span class="big">{esc(fmt_usd(cum * 1e6)) if cum is not None else "&mdash;"}</span>
    <span class="sub">cumulative net flow</span>
  </div></div>
  <div class="chartcard" style="margin-top:14px">{flow_ledger(
      [(d.get("date", "")[:6], (d.get("net_usd_m") or 0) * 1e6, None) for d in b.get("recent", [])],
      aria=f"{name} ETF daily net flows")}</div>"""
    inner = f"""{_dash_crumb()}
  <h1>ETF flows</h1>
  <p class="lede">The traditional-finance bid: how much money moved into or out of the US
     spot ETFs each trading day. This is the regulated world's demand for crypto, measured
     in actual dollars, published by the funds themselves.</p>
  {boards}
  <div class="sec-head" style="margin-top:30px"><h2>ETF flows 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">What a flow is</span>
      <p>When investors buy more ETF shares than they sell, the fund must go buy the real
      asset to back them: a <b>net creation</b>, money into crypto. Selling pressure works
      in reverse (a redemption). Flows are the cleanest window into institutional and
      retirement-account demand.</p></div>
    <div class="learn"><span class="lab">Why it moves markets</span>
      <p>ETF buying is spot buying: the fund takes real coins off the market, every trading
      day, at any price. A long streak of inflows or outflows is a supply/demand story that
      compounds, which is why desks watch the streak more than any single day.</p></div>
    <div class="learn"><span class="lab">The rhythm</span>
      <p>Flows publish once per trading day, a day behind, and pause on weekends and market
      holidays, so this board moves slower than the rest of the pulse. That is not staleness;
      that is the market it measures.</p></div>
    <div class="learn"><span class="lab">What it cannot tell you</span>
      <p>Flows say what regulated funds did, not why, and not what tomorrow brings. One fund
      family's quirks (fees, conversions) can dominate a quiet day. Context for the news,
      never a trade signal.</p></div>
  </div>
  <p class="nfa">{esc(etf.get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("etf", "ETF flows", desc, inner, dateline, data=pulse)


def render_pulse_network(pulse, dateline):
    desc = ("Bitcoin network vitals explained: what transaction fees and mining difficulty "
            "say about demand for the chain and miner confidence.")
    network = (pulse or {}).get("network") or {}
    if not network:
        inner = f"{_dash_crumb()}\n  <h1>Bitcoin network</h1>\n  {_no_data()}"
        return _dash_shell("network", "Bitcoin network", desc, inner, dateline, live=True, data=pulse)
    diff = network.get("difficulty_change_pct", 0)
    inner = f"""{_dash_crumb()}
  <h1>Bitcoin network</h1>
  <p class="lede">The chain's own vital signs: what it costs to transact right now, and
     whether miners are adding or removing machines.</p>
  <div class="pulse-card"><div class="pc-chips" style="margin-top:2px">
    <span class="chip" data-live="fee:fastest" data-prefix="next-block fee " data-suffix=" sat/vB">next-block fee {network.get("fastest_fee", "?")} sat/vB</span>
    <span class="chip" data-live="fee:hour" data-prefix="1-hour fee " data-suffix=" sat/vB">1-hour fee {network.get("hour_fee", "?")} sat/vB</span>
    {_chip(f'difficulty est. {diff:+.1f}%', "chip-up" if diff >= 0 else "chip-down")}
    {_chip(f'{network.get("retarget_blocks", "?")} blocks to retarget')}</div>
  <p class="pc-note"><span class="live-dot"></span>Fees update live in your browser via
  mempool.space; difficulty refreshes with each build. <span data-live="stamp"></span></p></div>

  <div class="sec-head" style="margin-top:30px"><h2>Network 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Fees are demand</span>
      <p>Every Bitcoin transaction bids for limited block space. High fees mean the chain is
      crowded with activity; fees of a few sat/vB mean it is quiet. Quiet is not automatically
      bearish, but it does mean nobody is rushing.</p></div>
    <div class="learn"><span class="lab">Difficulty is confidence</span>
      <p>Mining difficulty adjusts about every two weeks so blocks keep arriving on schedule.
      Rising difficulty means miners are plugging in more machines, a long-term bet with real
      electricity bills behind it. Falling difficulty means some are switching off.</p></div>
    <div class="learn"><span class="lab">Slow signals</span>
      <p>Network vitals move slowly and that is their value: they are hard to fake and hard to
      spin. They tell you about the health of the system, not tomorrow's price.</p></div>
  </div>
  <p class="nfa">{esc((pulse or {}).get("note", ""))} {esc(NFA)}</p>"""
    return _dash_shell("network", "Bitcoin network", desc, inner, dateline, live=True, data=pulse)




def cm_hero():
    # The wizard loop is the column's satirical mascot, a character and never an
    # authority claim: it appears exactly once, as the page-top panel (same slot the
    # Whale Watch and Market Pulse headers use), with no predictive framing anywhere
    # in this markup. Strictly lazy: no autoplay attribute, preload="none", the
    # motion-lazy pool arms on first scroll, poster paints first.
    return ('<section class="ww-hero cm-hero" aria-label="The Chart Master"><div class="ww-heroinner"><div class="ww-panel">'
            '<video class="ww-vid motion-video motion-lazy" muted loop playsinline preload="none" '
            'poster="/assets/wizard/wizard-poster.jpg" aria-hidden="true" tabindex="-1">'
            '<source src="/assets/wizard/wizard-loop.webm" type="video/webm">'
            '<source src="/assets/wizard/wizard-loop.mp4" type="video/mp4"></video>'
            '<span class="ww-scrim" aria-hidden="true"></span>'
            '<span class="ww-panel-fg"><span class="kicker">The resident wizard</span>'
            '<span class="ww-title">The Chart Master</span></span>'
            '</div></div></section>')


def render_chartmaster(read, dateline):
    desc = ("The Chart Master reads the boards: a plain-language take on sentiment, "
            "whale flows, and price posture. Plus the Oracle Challenge and the Wizard's "
            "Exam. Never financial advice.")
    read = read or {}
    paras = "".join(f"<p>{esc(destyle(p))}</p>" for p in read.get("paragraphs", []))
    # A read older than the current dateline quotes numbers the live boards have moved past;
    # say so rather than let it read as today's.
    stale_note = ""
    if read.get("date") and fmt_date(read["date"]).upper() != (dateline or "").upper():
        stale_note = (f'<p class="pc-note"><b>From the Master\'s ledger, {esc(fmt_date(read["date"]))}.</b> '
                      f'The boards below are live; the figures in this read are from its date.</p>')
    # The read is a clean text card: the wizard lives in the page-top panel (cm_hero)
    # and appears nowhere else on the page. The describe-not-predict disclaimer stays
    # in its usual spot below the prose, unobscured.
    head_html = (
        '<div class="ey"><span class="tag">the read</span>'
        f'<span class="dateline">{esc(fmt_date(read.get("date")))}</span></div>'
        f'<h3 class="cm-headline">{esc(destyle(read.get("headline", "")))}</h3>')
    read_html = (f"""<div class="sec-head" style="margin-top:8px"><h2>The Chart Master's read</h2><span class="bar"></span></div>
  <article class="pulse-card cm-read">
    {head_html}
    {stale_note}
    <div class="prose">{paras}</div>
    <p class="pc-note">The Chart Master reads the day's <a href="/pulse.html">Market
    Pulse</a> and <a href="/flows.html">Whale Watch</a> boards. He describes the tape;
    he does not predict it.</p>
  </article>""" if read.get("paragraphs") else "")

    body = cm_hero() + f"""<main class="wrap"><section class="page">
  <h1 style="margin-top:6px">The Chart Master</h1>
  <p class="lede">The desk's technician reads the boards so you learn to read them too:
     what the charts show, in plain language, with the receipts linked. He has one rule,
     carved over his door: <b>describe the tape, never predict it.</b></p>
  {read_html}

  <div class="sec-head" style="margin-top:30px"><h2>The Oracle Challenge</h2><span class="bar"></span></div>
  <div class="pulse-card" id="oracle">
    <p style="margin:0 0 10px">The Chart Master refuses to predict. Think you can do better?
    Call Bitcoin <b>higher or lower</b> than right now by this time tomorrow. Your record
    lives in your browser, and it IS the lesson.</p>
    <div class="pc-chips" id="oracle-buttons">
      <button class="cm-btn" data-guess="up">Higher &uarr;</button>
      <button class="cm-btn" data-guess="down">Lower &darr;</button>
    </div>
    <p class="pc-note" id="oracle-status" aria-live="polite" role="status">Loading the tape...</p>
    <p class="pc-note" id="oracle-record" aria-live="polite"></p>
  </div>

  <div class="sec-head" style="margin-top:30px"><h2>The Wizard's Exam</h2><span class="bar"></span></div>
  <div class="pulse-card" id="exam">
    <p style="margin:0 0 10px">Eight questions, straight from the desks. Pass, and you may
    call yourself a reader of charts. Fail, and the Master suggests the
    <a href="/pulse.html">101 sections</a>.</p>
    <div id="exam-body"><button class="cm-btn" id="exam-start">Take the exam</button></div>
  </div>

  <div class="sec-head" style="margin-top:30px"><h2>The Spellbook</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Golden cross / death cross</span>
      <p>The 50-day average crossing above the 200-day is a <b>golden cross</b> (trend
      turning up); crossing below is a <b>death cross</b>. See them drawn live on
      <a href="/pulse/posture.html">Price posture</a>.</p></div>
    <div class="learn"><span class="lab">Dry powder</span>
      <p>Stablecoins are dollars staged inside crypto, ready to buy. The
      <a href="/pulse/stablecoins.html">float</a> is the market's fuel gauge.</p></div>
    <div class="learn"><span class="lab">Whale flows</span>
      <p>Coins moving onto exchanges can precede selling; coins withdrawn to cold storage
      read as accumulation. <a href="/flows.html">Follow the money.</a></p></div>
    <div class="learn"><span class="lab">Fear &amp; Greed</span>
      <p>A 0-100 crowd-mood gauge. Extremes mark crowded emotions, not value.
      <a href="/pulse/sentiment.html">Today's reading.</a></p></div>
    <div class="learn" id="rsi101"><span class="lab">RSI</span>
      <p>Momentum on a 0-100 scale: above 70 runs hot, below 30 runs cold, and strong trends
      can stay hot for weeks. <a href="/pulse/posture.html">Current readings.</a></p></div>
    <div class="learn"><span class="lab">Exit liquidity</span>
      <p>What you become when you chase a pump with no story behind it. The
      <a href="/pulse/movers.html">movers board</a> exists so you check before you chase.</p></div>
  </div>
  <p class="nfa">{esc(NFA)} The Chart Master is a character of this desk, and nothing on
  this page is a recommendation of any kind.</p>
</section></main>
<script defer src="/assets/chart-master.js"></script>"""
    return shell(f"The Chart Master - {NAME}", desc, "Chart Master", body, dateline,
                 body_class="ww-dark", path="/chartmaster.html")




def render_404(dateline):
    body = """<main class="wrap narrow"><section class="page" style="text-align:center;padding-top:60px">
  <span class="kicker">404</span>
  <h1>That page moved on.</h1>
  <p class="lede" style="margin-left:auto;margin-right:auto">The story you were looking for is not
     here. Try the <a href="/index.html">front page</a> or the <a href="/archive.html">archive</a>.</p>
</section></main>"""
    return shell(f"Not found - {NAME}", "Page not found.", None, body, dateline,
                 path="/404.html", noindex=True)


def render_thanks(dateline):
    body = """<main class="wrap narrow"><section class="page" style="text-align:center;padding-top:60px">
  <span class="kicker">Subscribed</span>
  <h1>You are on the list.</h1>
  <p class="lede" style="margin-left:auto;margin-right:auto">Thanks for subscribing to the brief.
     We will not sell your email, and you can unsubscribe anytime. Back to the
     <a href="/index.html">front page</a>.</p>
</section></main>"""
    return shell(f"Subscribed - {NAME}", "Thanks for subscribing.", None, body, dateline,
                 path="/thanks.html", noindex=True)


# ---- ingest approved payloads -----------------------------------------------

DEDUPE_WINDOW_H = 24  # the owner's spec: entity + event-date overlap inside 24 hours


def same_event_on_disk(item, window_h=DEDUPE_WINDOW_H, content=None):
    """(path, story) of an already-published story covering this same event, or (None, None).

    THE LAST GATE, and it exists because the one before it can be raced. autopilot's guard
    reads the corpus committed on disk, which is correct until two runs overlap: the 18:41
    run had not pushed when the 18:47 run checked out, so the second run's disk did not
    contain the first run's story and the guard had nothing to match against. Two Tether
    earnings stories published thirteen minutes apart carrying the SAME cluster id, which is
    only possible across runs, because within one run the id is a dict key.

    Ingest is the right place for the backstop. It is the moment content actually enters the
    site, it runs after publish.py in the same job, and by then the day's other stories are
    on disk whatever route they arrived by. A guard here also catches content that reaches
    site/content without passing autopilot at all.

    Matching is dedupe.same_event (entity and signature overlap), bounded to a window,
    because two unrelated stories about one company weeks apart are not one event."""
    from datetime import timedelta
    import dedupe
    when = _parse_utc(item)
    if not when:
        return None, None
    for path in sorted(glob.glob(os.path.join(content or CONTENT, "*.json"))):
        if os.path.basename(path).startswith("_"):
            continue
        try:
            other = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if other.get("example") or other.get("slug") == item.get("slug"):
            continue
        # An edition summarises the day; it is not a duplicate of the stories in it.
        if _is_wrap(other) or _is_wrap(item):
            continue
        other_when = _parse_utc(other)
        if not other_when or abs((when - other_when).total_seconds()) > window_h * 3600:
            continue
        if not dedupe.same_event(other.get("title", ""), other.get("key_fact", ""),
                                 item.get("title", ""), item.get("key_fact", "")):
            continue
        # same_event is the CANDIDATE filter, never the verdict, and merging on it alone is
        # destructive in a way the publish gate's version is not: holding a story loses a
        # duplicate, merging the wrong pair loses a real one. Tested against live content it
        # matched a Kalshi gambling lawsuit to a Tether earnings report.
        #
        # So the same second test the gate applies: how much did the newcomer actually add,
        # measured against everything the published story already covered. Below the gate's
        # own NOVELTY_MIN means it said nothing new, which is the definition of a duplicate
        # this desk already enforces at publish time.
        # BETTER SOURCING OUTRANKS NOVELTY (owner-approved, 2026-08-13 audit). The novelty
        # test asks "did this add anything?", and a corroborated retelling usually adds
        # plenty: new outlets, sharper numbers, a corrected framing. That is exactly why it
        # sailed past this gate and published alongside the weaker original. The desk ran a
        # single-source piece saying Solana came "within minutes of full freeze" and, three
        # hours later, a three-source piece putting it 4.5 points from a halt. Two live
        # articles, one of them overstated, and nothing reconciling them.
        #
        # So a same-event story with STRICTLY more sources is a merge candidate whatever its
        # novelty score, and merge_into_existing replaces the prose for that case alone.
        # SAME EVENT IS NOT ENOUGH TO TOUCH A PUBLISHED STORY (owner report 2026-08-28).
        # The comment above says same_event is a candidate filter and then both branches
        # below treat it as the verdict anyway. It cost exactly what was predicted: a
        # BankChain alliance story and a Roman Storm retrial story matched (they share
        # little beyond the year 2027), the retrial had more sources, and it overwrote the
        # BankChain article in place. The published page then carried a Roman Storm body
        # under a BankChain URL with both stories' citations beneath a SOURCES VERIFIED
        # badge. So the candidate must now also be the same STORYLINE, by the same test
        # the Update callout uses: real content overlap on a shared subject. The two
        # stories above fail it outright.
        #
        # This is _same_storyline ALONE. entities_of was tried alongside it and dropped:
        # it scores a token by how often the CORPUS lowercases it, and a two-document
        # comparison has no corpus, so it reported "no shared subject" for a genuine
        # Solana-halt upgrade exactly as readily as for the false pair. The storyline
        # test separates both correctly by itself.
        if not _same_storyline(item, other, 0.22):
            continue
        if len(item.get("sources") or []) > len(other.get("sources") or []):
            return path, other
        novel = (dedupe._claim_signature(item)
                 - dedupe._covered_signature(other) - dedupe._OUTLETS)
        if len(novel) < dedupe.NOVELTY_MIN:
            return path, other
    return None, None


def merge_into_existing(path, prior, incoming):
    """Fold a duplicate into the story already published, and keep the published URL.

    UPDATES rather than replaces, deliberately. The existing story owns a URL that may
    already be indexed and linked, so its slug, title and body stand. What the second copy
    genuinely adds is sourcing, so its sources are unioned in, and the fact that an update
    landed is stamped so the page can say when it was last touched.

    The prose is NOT rewritten from the incoming copy. A later retelling of the same event is
    usually not better reporting, it is the same reporting again, and silently swapping the
    body of a published story is a bigger risk than the duplicate it would fix. Anything the
    second copy really adds is a job for a human, and merged_from records what to look at."""
    # THE ONE CASE THE PROSE IS REPLACED (owner-approved, 2026-08-13). The rule above
    # holds for equal or weaker retellings and is right: the same reporting again is not
    # better reporting. But when the newcomer carries strictly more sources it IS better
    # reporting, and leaving the thinner telling standing is how an overstatement outlived
    # its own correction for a day. The URL, slug and original publication time survive;
    # the words and the sourcing become the better ones, and the page says so.
    upgraded = len(incoming.get("sources") or []) > len(prior.get("sources") or [])
    if upgraded:
        old_title = prior.get("title", "")
        for f in ("title", "dek", "key_fact", "body", "bottom_line", "boundary",
                  "also_reported_by", "developing"):
            if f in incoming:
                prior[f] = incoming[f]
        prior["consolidated"] = (
            "This story was updated in place with a better-sourced account of the same "
            "event, carrying "
            f"{len(incoming.get('sources') or [])} sources against the original "
            f"{len(prior.get('sources') or [])}. The earlier version was headlined "
            f"\u201c{old_title}\u201d. The URL and publication time are unchanged.")
    if upgraded:
        # CITATIONS BELONG TO THE PROSE THEY SUPPORT (owner report 2026-08-28). Unioning
        # was right while the body always stood: two tellings of one event, both sets of
        # sources genuinely underwrite it. It is wrong on this branch, the one that swaps
        # the words, because the previous story's citations were verified against text
        # that no longer exists on the page. The desk shipped a Roman Storm retrial
        # article citing BankChain coverage under a SOURCES VERIFIED badge. On an upgrade
        # the incoming sources REPLACE; the displaced ones stay in merged_from as the
        # record of what was there.
        prior["superseded_sources"] = prior.get("sources") or []
        prior["sources"] = incoming.get("sources") or []
    else:
        seen = {(s.get("url") or "").strip() for s in (prior.get("sources") or [])}
        for s in (incoming.get("sources") or []):
            u = (s.get("url") or "").strip()
            if u and u not in seen:
                prior.setdefault("sources", []).append(s)
                seen.add(u)
    prior["updated_utc"] = incoming.get("published_utc") or prior.get("published_utc")
    prior.setdefault("merged_from", []).append({
        "id": incoming.get("id"), "title": incoming.get("title"),
        "published_utc": incoming.get("published_utc")})
    json.dump(prior, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)



def _board_snapshot_for(published_utc):
    """A compact, honest snapshot of the desk's boards, or None if it would lie."""
    try:
        pulse = json.load(open(os.path.join(HERE, "site", "data", "pulse.json"),
                               encoding="utf-8"))
        flows = json.load(open(os.path.join(HERE, "site", "data", "flows.json"),
                               encoding="utf-8"))
        if pulse.get("example") or flows.get("example"):
            return None
        as_of = pulse.get("generated_utc") or ""
        # staleness guard: boards older than 6 hours are the previous session's market
        if published_utc and as_of:
            from datetime import datetime, timezone
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            try:
                age = (datetime.strptime(published_utc[:19] + "Z", fmt)
                       - datetime.strptime(as_of[:19] + "Z", fmt)).total_seconds()
                if age > 6 * 3600 or age < -3600:
                    return None
            except ValueError:
                return None
        want = {"BTC", "ETH"}
        assets = [{"symbol": a["symbol"], "price": a.get("price"),
                   "chg_24h_pct": a.get("chg_24h_pct")}
                  for a in (pulse.get("assets") or [])
                  if isinstance(a, dict) and a.get("symbol") in want]
        fng = pulse.get("fng") or {}
        lev = {}
        for a in ((pulse.get("leverage") or {}).get("assets") or []):
            if isinstance(a, dict) and a.get("symbol") == "BTC":
                lev = {"funding_annual_pct": a.get("funding_annual_pct"),
                       "open_interest_usd": a.get("open_interest_usd")}
                break
        vol = flows.get("volatile") or {}
        snap = {"as_of": as_of, "assets": assets,
                "fng": {"value": fng.get("value"), "label": fng.get("label")},
                "leverage": lev,
                "flows": {"window_hours": flows.get("window_hours"),
                          "net_usd": vol.get("net_usd"),
                          "direction": vol.get("direction")}}
        return snap if assets else None
    except Exception:
        return None


def render_board_panel(item):
    """The market, as this desk measured it, when this story published.

    Renders only from the snapshot stamped at ingest, never from live data: showing
    today's prices on last month's story would be a lie in the desk's own voice. Only
    market-facing beats get the panel; a court ruling does not need a BTC price."""
    snap = item.get("board_snapshot")
    if not snap or not snap.get("assets"):
        return ""
    # MARKET-FACING = NAMES AN ASSET AND A MOVEMENT, the same test the verifier's
    # board-check uses to decide a story makes a market claim. The beat classifier is
    # the wrong gate here: it routes "Bitcoin slides as leverage unwinds" to Protocol
    # because the word Bitcoin outweighs the price verbs (measured 2026-08-25).
    try:
        import verifier as _v
        txt = f"{item.get('title') or ''} {item.get('key_fact') or ''}"
        if not (_v._BOARD_ASSET.search(txt) and _v._BOARD_MOVE.search(txt)):
            return ""
    except Exception:
        return ""
    rows = ""
    for a in snap["assets"]:
        try:
            chg = float(a.get("chg_24h_pct") or 0)
            cls = "up" if chg >= 0 else "down"
            rows += (f'<div class="bp-row"><span class="bp-k">{esc(a["symbol"])}</span>'
                     f'<span class="bp-v">${a["price"]:,.0f}</span>'
                     f'<span class="bp-d {cls}">{chg:+.1f}% 24h</span></div>')
        except (TypeError, ValueError, KeyError):
            continue
    fng = snap.get("fng") or {}
    if fng.get("value") is not None:
        rows += (f'<div class="bp-row"><span class="bp-k">Fear &amp; Greed</span>'
                 f'<span class="bp-v">{esc(str(fng["value"]))}</span>'
                 f'<span class="bp-d">{esc(str(fng.get("label") or ""))}</span></div>')
    fl = snap.get("flows") or {}
    if fl.get("net_usd") is not None:
        try:
            rows += (f'<div class="bp-row"><span class="bp-k">Whale flow '
                     f'{int(fl.get("window_hours") or 24)}h</span>'
                     f'<span class="bp-v">${abs(float(fl["net_usd"]))/1e6:,.0f}M</span>'
                     f'<span class="bp-d">{esc(str(fl.get("direction") or ""))}</span></div>')
        except (TypeError, ValueError):
            pass
    lev = snap.get("leverage") or {}
    if lev.get("funding_annual_pct") is not None:
        rows += (f'<div class="bp-row"><span class="bp-k">BTC funding</span>'
                 f'<span class="bp-v">{float(lev["funding_annual_pct"]):+.1f}%/yr</span>'
                 f'<span class="bp-d">perp lean</span></div>')
    if not rows:
        return ""
    when = esc((snap.get("as_of") or "")[:16].replace("T", " ") + " UTC")
    return (f'<aside class="board-panel"><h2>The market when this story published</h2>'
            f'<p class="mut">Measured by this desk\'s own boards at {when}, the run '
            f'this story shipped in. Not live numbers: the '
            f'<a href="/">front page</a> has those.</p>'
            f'<div class="bp-grid">{rows}</div></aside>')

def ingest():
    """Promote approved payloads (out/published/*.json from publish.py) into committed content."""
    if not os.path.isdir(PUBLISHED):
        print("ingest: no out/published/ (nothing approved yet); building from committed content only.")
        return 0
    # date/time from the run, not a wall clock, so builds stay reproducible
    date, published_utc = "undated", ""
    try:
        published_utc = json.load(open(os.path.join(HERE, "out", "items.json"),
                                       encoding="utf-8"))["_meta"]["generated"]
        date = published_utc[:10]
    except Exception:
        pass
    os.makedirs(CONTENT, exist_ok=True)
    # editor rank (1 = lead) so the day's page keeps the desk's editorial order
    rank_map = {}
    try:
        ranked = json.load(open(os.path.join(HERE, "out", "editor.json"), encoding="utf-8"))["ranked"]
        rank_map = {r["id"]: i + 1 for i, r in enumerate(ranked)}
    except Exception:
        pass
    # autopilot flags developments of an earlier story (out/updates.json: id -> origin slug);
    # carry that onto the published item so the article renders the "Update" callout.
    updates_map = {}
    try:
        updates_map = json.load(open(os.path.join(HERE, "out", "updates.json"), encoding="utf-8"))
    except Exception:
        pass
    n, merged = 0, 0
    for fn in sorted(os.listdir(PUBLISHED)):
        if not fn.endswith(".json"):
            continue
        rec = json.load(open(os.path.join(PUBLISHED, fn), encoding="utf-8"))
        payload = rec.get("payload", {})
        art = payload.get("article", {})
        title = art.get("title") or "Untitled"
        slug = slugify(title)
        body = art.get("body", "")
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()] or [body]
        srcs = [{"title": u, "url": u} for u in art.get("sources", [])]
        title = destyle(title)
        # the writer model sometimes slips a process note about the review status into the
        # copy ("Note: flagged for human review."); the article is the finished story only,
        # so any such sentence is stripped from every published field at the door
        note = re.compile(r"(?:Note:\s*)?[^.!?]*(?:flagged for|pending)\s+human\s+review[^.!?]*[.!?]?\s*"
                          r"|[^.!?]*human review before publication[^.!?]*[.!?]?\s*", re.I)
        def scrub(text):
            return note.sub("", destyle(text)).strip()
        paras = [scrub(p) for p in paras]
        paras = [p for p in paras if p]
        item = {
            "id": rec.get("id"), "slug": slug, "kind": "brief",
            "title": title, "dek": scrub((payload.get("script", {}) or {}).get("summary", "")),
            "date": date, "published_utc": published_utc,
            "category": "news", "verdict": rec.get("verdict"),
            "rank": rank_map.get(rec.get("id")),
            "author": "Crypto Cronkite",
            "key_fact": scrub((payload.get("script", {}) or {}).get("key_fact", "")),
            "bottom_line": scrub(art.get("bottom_line", "")),
            "human_take": destyle(art.get("human_take", "")), "body": paras, "sources": srcs,
        }
        if updates_map.get(rec.get("id")):
            item["update_of"] = updates_map[rec.get("id")]
        # THE DESK'S OWN MEASUREMENTS, AT THE MOMENT OF PUBLISH (owner directive
        # 2026-08-25: every article should carry something no source article has). The
        # boards are refreshed earlier in the same workflow run, so at ingest they are
        # the desk's measurement of the market this story shipped into. Stamped once,
        # never updated: an old story showing TODAY'S prices would be dishonest, which
        # is also why the guard refuses a stamp when the board data is stale or the
        # fixture. Old items simply lack the field and render no panel.
        snap = _board_snapshot_for(published_utc)
        if snap:
            item["board_snapshot"] = snap
        # The boundary block passes through UNSCRUBBED and UNDESTYLED, alone among the
        # fields here. Every other value is the desk's own prose and gets house style; these
        # four are the vendor's words, checked character-for-character against the advisory
        # upstream (boundary.check_against_sources) and labeled on the page as quoted. Running
        # destyle over a quotation would edit a version range the desk promised not to touch,
        # for a house-style rule that has never applied to quoted material anyway.
        if boundary.is_complete(art.get("boundary")):
            item["boundary"] = {f: str(art["boundary"][f]) for f in boundary.FIELDS}
        # SINGLE SOURCE IS A DISCLOSURE, NOT A DETAIL. The homepage sells verification
        # "against outlets deliberately spread across the political spectrum", and a story
        # resting on one outlet cannot deliver that whatever its verdict says. 76% of
        # published stories carried one source while their clusters averaged 17 corroborating
        # outlets, so most of this is now fixed upstream (editor.attach_corroboration). What
        # genuinely has one outlet gets labelled rather than quietly presented as verified.
        item["also_reported_by"] = [str(x) for x in (art.get("also_reported_by") or []) if x]
        # Corroborated by other outlets is not "developing", whatever the citation count:
        # the badge exists to disclose a story resting on one outlet's word, and this one is
        # resting on several. Sources stay honest (what the desk actually drew on) and the
        # corroboration renders as its own labelled line.
        item["developing"] = len(srcs) < 2 and not item["also_reported_by"]
        prior_path, prior = same_event_on_disk(item)
        if prior_path:
            merge_into_existing(prior_path, prior, item)
            print(f"  MERGED {rec.get('id')} into {os.path.basename(prior_path)} "
                  f"(same event within {DEDUPE_WINDOW_H}h; no second story created)")
            merged += 1
            continue
        out = os.path.join(CONTENT, f"{date}-{slug}.json")
        json.dump(item, open(out, "w", encoding="utf-8"), indent=2)
        print(f"  ingested {rec.get('id')} -> {os.path.relpath(out)}")
        n += 1
    print(f"ingest: promoted {n} approved item(s) into site content"
          + (f", merged {merged} duplicate(s) into an existing story." if merged else "."))
    return n


# ---- build -------------------------------------------------------------------

def _copytree(src, dst):
    os.makedirs(dst, exist_ok=True)
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target, exist_ok=True)
        for f in files:
            data = open(os.path.join(root, f), "rb").read()
            open(os.path.join(target, f), "wb").write(data)


def _render_og_card(item):
    """Render this article's OG card into PUBLISH/og/<slug>.png at build time. FAIL-OPEN:
    any problem (Pillow missing, font issue, bad headline) is swallowed so the card simply
    does not exist and the article falls back to the site-wide og-image. A card is a
    nice-to-have; it must never break the site build."""
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(HERE, "scripts"))
        import og_render
        cat = (item.get("category") or "").strip().lower()
        kicker = ("Crypto News" if cat in ("", "news")
                  else "Daily Edition" if cat == "daily edition" else item["category"].title())
        og_render.render_card(item.get("title", ""), kicker,
                              os.path.join(PUBLISH, "og", f"{item['slug']}.png"))
        return True
    except Exception as e:
        print(f"::warning::og card skipped for {item.get('slug','?')}: {e}")
        return False


def build():
    items = load_content()
    # dateline reflects the newest content (or a neutral standing line), never a wall clock
    newest = next((i.get("date") for i in items if not i.get("example") and i.get("date")), None)
    dateline = fmt_date(newest).upper() if newest else "AN HONEST CRYPTO NEWS DESK"

    import shutil
    if os.path.isdir(PUBLISH):
        shutil.rmtree(PUBLISH)
    os.makedirs(os.path.join(PUBLISH, "articles"), exist_ok=True)
    _copytree(ASSETS, os.path.join(PUBLISH, "assets"))

    def w(rel, html):
        path = os.path.join(PUBLISH, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(html)

    flows = load_flows()
    pulse = load_pulse()
    cm = load_chartmaster()
    w("index.html", render_home(items, flows, pulse, cm, dateline))
    w("news.html", render_news(items, dateline, pulse=pulse))
    w("flows.html", render_flows(flows, dateline))
    w("pulse.html", render_pulse_hub(pulse, flows, cm, dateline))
    w("chartmaster.html", render_chartmaster(cm, dateline))
    w(os.path.join("pulse", "sentiment.html"), render_pulse_sentiment(pulse, dateline))
    w(os.path.join("pulse", "posture.html"), render_pulse_posture(pulse, dateline))
    w(os.path.join("pulse", "movers.html"), render_pulse_movers(pulse, dateline))
    w(os.path.join("pulse", "prices.html"), render_pulse_prices(pulse, dateline))
    w(os.path.join("pulse", "stablecoins.html"), render_pulse_stables(pulse, dateline))
    w(os.path.join("pulse", "leverage.html"), render_pulse_leverage(pulse, dateline))
    w(os.path.join("pulse", "etf.html"), render_pulse_etf(pulse, dateline))
    w(os.path.join("pulse", "network.html"), render_pulse_network(pulse, dateline))
    w("archive.html", render_archive(items, dateline))
    w("method.html", render_method(items, dateline))
    w("about.html", render_about(dateline))
    w("standards.html", render_standards(dateline))
    w("learn.html", render_learn(dateline))
    w("how-we-make-money.html", render_how_we_make_money(dateline))
    w("cold-storage.html", render_cold_storage(dateline))
    w("crypto-tax.html", render_crypto_tax(dateline))
    w("counterfeit-devices.html", render_counterfeit_devices(dateline))
    w("onchain-flows.html", render_onchain_flows(dateline))
    w("accessibility.html", render_accessibility(dateline))
    w("privacy.html", render_privacy(dateline))
    w("terms.html", render_terms(dateline))
    w("404.html", render_404(dateline))
    w("thanks.html", render_thanks(dateline))
    for it in items:
        _render_og_card(it)  # build-time per-article share card (fail-open) -> PUBLISH/og/
        w(os.path.join("articles", f"{it['slug']}.html"), render_article(it, all_items=items))
    w("bottom-line.html", render_bottom_line_history(items, dateline))
    w("feed.xml", render_feed(items))

    # The site card and the home-screen icon are GENERATED here, not copied from assets.
    # They used to be copied, and all three desks shipped the same committed file: News and
    # Sports were serving the Crypto card, so the one surface a stranger sees carried the
    # wrong brand. Generating removes the class of bug rather than the instance.
    # Fail-open, and fall back to the committed asset, because a missing og:image is worse
    # than a stale one.
    _share_generated = False
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(HERE, "scripts"))
        import og_render
        og_render.render_site_card(os.path.join(PUBLISH, "og-image.png"))
        og_render.render_icon(os.path.join(PUBLISH, "apple-touch-icon.png"), 180)
        _share_generated = True
    except Exception as e:
        print(f"::warning::share surfaces not generated, falling back to committed: {e}")
    if not _share_generated:
        for _name in ("apple-touch-icon.png", "og-image.png"):
            _src = os.path.join(ASSETS, _name)
            if os.path.exists(_src):
                open(os.path.join(PUBLISH, _name), "wb").write(open(_src, "rb").read())
    # A web app manifest, so saving to a home screen picks up the desk's own name and colour
    # instead of the page title and a browser default.
    with open(os.path.join(PUBLISH, "site.webmanifest"), "w", encoding="utf-8") as _mf:
        # FAMILY, not NAME. NAME is the byline persona on this desk (Crypto Cronkite), and
        # a home-screen label is a brand surface: the wordmark is the hero there too.
        json.dump({"name": FAMILY, "short_name": SHORT_NAME, "start_url": "/",
                   "display": "standalone", "background_color": "#FBFAF6",
                   "theme_color": THEME_COLOR,
                   "icons": [{"src": "/apple-touch-icon.png", "sizes": "180x180",
                              "type": "image/png"}]}, _mf, ensure_ascii=False, indent=1)
    # the square publisher logo at the site root (schema publisher.logo, Publisher Center):
    # 512px+ square, referenced by NewsArticle JSON-LD and available to aggregators
    for lg in ("publisher-logo-512.png", "publisher-logo-1024.png"):
        src = os.path.join(ASSETS, lg)
        if os.path.exists(src):
            open(os.path.join(PUBLISH, lg), "wb").write(open(src, "rb").read())

    # sitemap (indexable pages only; 404/thanks are noindex), robots, netlify 404 redirect
    locs = ["/", "/news.html", "/flows.html", "/pulse.html", "/chartmaster.html",
            "/pulse/sentiment.html", "/pulse/posture.html",
            "/pulse/movers.html", "/pulse/prices.html", "/pulse/stablecoins.html",
            "/pulse/leverage.html", "/pulse/etf.html", "/pulse/network.html",
            "/archive.html", "/bottom-line.html", "/method.html", "/about.html", "/standards.html",
            "/learn.html", "/cold-storage.html", "/crypto-tax.html", "/counterfeit-devices.html",
            "/onchain-flows.html",
            "/how-we-make-money.html",
            "/accessibility.html", "/privacy.html", "/terms.html"]
    # standard sitemap: static pages (no lastmod) + article URLs WITH lastmod from the
    # story's own publish timestamp, so Google sees freshness on every deploy
    # static pages name the same extensionless form the canonical does (2026-08-17)
    static_urls = "".join(
        f"  <url><loc>{ORIGIN}{esc(p[:-5] if p.endswith('.html') else p)}</loc></url>\n"
        for p in locs)
    art_urls = ""
    for it in items:
        if it.get("example"):
            continue
        lm = _w3c_dt(it.get("published_utc") or it.get("date") or "")
        lmtag = f"<lastmod>{esc(lm)}</lastmod>" if lm else ""
        art_urls += f"  <url><loc>{ORIGIN}/articles/{esc(it['slug'])}</loc>{lmtag}</url>\n"
    w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + static_urls + art_urls + "</urlset>\n")

    # NEWS SITEMAP (Google News format): only articles from the last 48 hours, relative to
    # the newest published item so the build stays reproducible (no wall clock). Regenerated
    # every deploy. Google ignores entries older than ~2 days, which is the point.
    w("news-sitemap.xml", render_news_sitemap(items))
    w("robots.txt", f"User-agent: *\nAllow: /\n\n"
      f"Sitemap: {ORIGIN}/sitemap.xml\nSitemap: {ORIGIN}/news-sitemap.xml\n")
    # RETIRED URLS keep working. When the desk publishes the same development more than once
    # and the duplicates are merged, the surviving story takes the reporting and the retired
    # slugs 301 here. Never delete a published URL: someone linked it, and a 404 punishes the
    # reader for our filing error. Order matters, Netlify takes the first match, so these
    # must precede the catch-all.
    # /rss.xml is the address readers and aggregators try first; the desk publishes at
    # /feed.xml, so alias rather than leave a 404 (2026-08-13 audit).
    rss_alias = "/rss.xml  /feed.xml  301\n"
    # A REDIRECT TO A 404 IS WORSE THAN NO REDIRECT (owner audit 2026-08-29). Every
    # survivor in RETIRED_ARTICLES must actually render, or the retired URL sends a
    # reader and a crawler into a dead end. This shipped once: a survivor slug was
    # transcribed from a truncated console listing ("...next-week-source" for
    # "...next-week-sources-say") and the 301 pointed at nothing for a day. Build-time
    # assertion, loud, because the failure is invisible from the map alone.
    _rendered = {i.get("slug") for i in items if i.get("slug")}
    _dangling = sorted(v for v in set(RETIRED_ARTICLES.values()) if v not in _rendered)
    if _dangling:
        for v in _dangling:
            print(f"::error::RETIRED_ARTICLES points at a survivor that does not exist: "
                  f"{v} (the retired URLs mapped to it would 301 into a 404)")
        raise SystemExit(f"site: {len(_dangling)} dangling redirect target(s); fix "
                         f"RETIRED_ARTICLES before shipping")
    redirects = "".join(f"/articles/{old}.html  /articles/{new}.html  301\n"
                        f"/articles/{old}  /articles/{new}  301\n"
                        for old, new in sorted(RETIRED_ARTICLES.items()))
    w("_redirects", rss_alias + redirects + "/*  /404.html  404\n")
    # THE EDITION (owner spec 2026-08-03): the composed front replaces the Latest tab
    # at its own URL, and every edition day is preserved as a back issue under
    # /edition/. Rendering layer only; ranking and content come from the items as
    # published. Written LAST so the composed front wins the /news.html route.
    import edition as _edition
    n_ed = _edition.build(items, w, shell=shell)
    if n_ed:
        print(f"site: The Edition composed for {n_ed} day(s) -> news.html + /edition/")

    n_live = sum(1 for i in items if not i.get("example"))
    print(f"site: built {PUBLISH} - {n_live} published stor{'y' if n_live == 1 else 'ies'} "
          f"+ {len(items) - n_live} example, plus home/archive/method/about/standards/404.")
    return 0


def main():
    if "--ingest" in sys.argv:
        ingest()
    build()


if __name__ == "__main__":
    main()
