#!/usr/bin/env python3
"""
explainers.py: evergreen explainers that carry a commercial layer.

THE MONEY PATH LIVES HERE AND ONLY HERE. Affiliate URLs are declared once, at the top of
this file, and referenced by name in the copy below. They are never pasted into body text,
so an auditor can read the whole commercial surface of the site in one screen.

RULES THIS FILE IS BUILT TO KEEP
  - The page must read correctly with the commercial layer removed. The argument is the
    product; the links are a convenience at the end of it. If deleting the buy section
    broke the piece, the piece would be an advertisement and would not ship.
  - Store-wide links only. Commission is on the cart rather than a SKU, and product URLs
    rot every time a lineup refreshes. No product links, and no prices anywhere:
    manufacturer pricing rotates and a stale price is a credibility hit.
  - Recommend by fit, never by commission. See ROUTING RULE below.
  - Educational only. Nothing here is advice about any particular person's holdings.
  - No email capture, no personal data collected, no interaction layer (no selector, quiz,
    or filter). The reader reads prose and decides.

ROUTING RULE (written down deliberately, per directive):
  Trezor pays a higher commission than Ledger. That fact must never influence which device
  the copy points a reader toward. The routing is by FIT ONLY:
    - Reader is Bitcoin focused, or wants source code they or others can audit
      -> Trezor is the better fit.
    - Reader holds many chains, or wants phone access to the device
      -> Ledger is the better fit.
  If those two sentences ever stop matching the products, change the copy, not the logic.
  Both devices are legitimate and well regarded, and the page says so plainly.
"""

# ---- AFFILIATE CONFIG: the only place these URLs exist ------------------------
LEDGER_STORE = "https://shop.ledger.com/?r=c1480b445e30"
TREZOR_STORE = "https://affil.trezor.io/aff_c?offer_id=133&aff_id=846461"

# every outbound commercial link carries these, without exception
LINK_REL = "sponsored noopener"
LINK_TARGET = "_blank"

# sources for every factual claim on the page, cited inline at the bottom
SOURCES = [
    ("FDIC, What the public needs to know about deposit insurance and crypto",
     "https://www.fdic.gov/news/fact-sheets/crypto-fact-sheet-7-28-22.pdf"),
    ("SIPC, What SIPC protects",
     "https://www.sipc.org/for-investors/what-sipc-protects"),
    ("Ledger, Best practices to securely buy your Ledger device",
     "https://www.ledger.com/academy/topics/ledgersolutions/best-practices-to-securely-buy-ledger-signer"),
    ("Trezor, Is my device safe to use?",
     "https://trezor.io/support/troubleshooting/device-issues/is-my-device-safe-to-use"),
]


def _cta(href, brand, line, store):
    """One primary call to action per brand. The link names its destination so the reader
    (and a screen reader) knows it goes to the manufacturer's own store before clicking,
    which is also the point being made two sections above."""
    return (f'<a class="cta-buy" href="{href}" rel="{LINK_REL}" target="{LINK_TARGET}">'
            f'<span class="cta-brand">{brand}</span>'
            f'<span class="cta-line">{line}</span>'
            f'<span class="cta-go">Shop the official {store} store</span></a>')


def cold_storage_body():
    """The page. Sections 1 to 5 are the article and stand alone; section 6 is the
    commercial layer and is deliberately severable."""
    sources = "".join(
        f'<li><a href="{url}" rel="noopener" target="_blank">{name}</a></li>'
        for name, url in SOURCES)
    return f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Explainer</span>
  <h1>Cold storage, explained</h1>
  <p class="lede">Crypto can sit in three different places, and the difference between them
     comes down to one question: who holds the keys. Here is what each option is actually
     for, what you give up in each, and when a hardware wallet is worth buying.</p>

  <h2>The three places crypto lives</h2>
  <p>These are not competitors and there is no winner among them. They are different tools
     for different jobs.</p>

  <h3>On an exchange</h3>
  <p>The platform holds the keys. You hold an account balance, and the exchange moves coins
     on your instruction. This is what makes an exchange convenient: you can trade in
     seconds, recover a lost password through customer support, and never think about
     seed phrases. It suits active trading and the working balance you are actually
     trading with. The tradeoff is the custody mechanic described in the next section.</p>

  <h3>In a hot wallet</h3>
  <p>A hot wallet is self-custody software, the category that includes wallets like
     MetaMask and Exodus. You hold the keys, but they live on an internet-connected
     device: a phone, a laptop, a browser extension. That is what makes a hot wallet the
     right tool for actually using crypto, connecting to applications, swapping tokens,
     paying for things, moving day-to-day amounts. The tradeoff is that the keys sit on a
     machine that also opens email and runs software, which exposes them to malware,
     phishing, and anything that compromises the device.</p>

  <h3>In cold storage</h3>
  <p>Cold storage means the keys are held offline on a dedicated device that signs
     transactions without ever exposing the keys to your computer. It suits long-term
     holdings you are not moving often. The tradeoff is that it costs money, adds a little
     setup friction, and puts the recovery phrase entirely in your hands.</p>

  <div class="callout"><b>The honest conclusion.</b> Most people who know what they are
     doing use more than one. A trading balance on an exchange, spending money in a hot
     wallet, long-term holdings in cold storage. The question is not which tool is best,
     it is which job you are doing right now.</div>

  <h2>What it means when the exchange holds the keys</h2>
  <p>This is the part most people have never had explained, and it is mechanical rather
     than dramatic. When your crypto sits on an exchange, the exchange controls the keys
     to the coins. Your balance is a claim against that company, an entry in its records
     saying it owes you a certain amount, rather than coins you hold directly. In normal
     operation the distinction never comes up: you withdraw, the exchange sends, the
     system works exactly as advertised.</p>
  <p>Where the distinction does matter is in what backs that claim. Dollars in an insured
     bank account are covered by federal deposit insurance, and securities at a failed
     brokerage are covered by SIPC. Crypto is covered by neither. The FDIC states plainly
     that deposit insurance does not apply to crypto assets and does not protect against
     the failure of a non-bank company, including exchanges and custodians. SIPC does not
     protect digital assets that are not securities. Many people assume a safety net is
     there because it is there for every other financial account they hold. For crypto on
     an exchange, it is not.</p>
  <p>None of that makes exchanges unsafe or means you should not use one. It means the
     sensible rule is to match custody to use. Active trading on a reputable exchange is
     completely reasonable, and so is leaving there what you are actively trading with.
     Holdings you intend to keep for years are a different job, and that job belongs in
     cold storage. Most people end up doing both.</p>

  <h2>Self-custody has its own failure mode</h2>
  <p>Being honest about this cuts the other way too: lost seed phrases and forgotten
     passphrases have permanently destroyed more crypto than exchange failures have, and
     there is no support line that can recover them. If you take the keys, you take the
     responsibility for backing them up properly.</p>

  <h2>Buy from the manufacturer's store</h2>
  <p>If you do buy a hardware wallet, where you buy it matters more than most people
     expect. A hardware wallet is a security device, and a device that passed through
     unknown hands before reaching you cannot be assumed to be untouched. The specific
     risks are tampered hardware and, more commonly, a recovery card that arrives already
     filled in, which is not a backup but somebody else's keys. Both manufacturers give
     the same guidance: buy from their own store or a reseller they list as authorized,
     and treat marketplace listings on general retail sites as unverified. That means no
     Amazon, no eBay, no third-party marketplace seller, however convenient.</p>

  <h2>Ledger and Trezor</h2>
  <p>These are the two established names, both legitimate and both well regarded. They are
     built on different philosophies, which is what should decide between them.</p>
  <p><b>Ledger</b> builds around a certified secure element, the same class of tamper
     resistant chip used in passports and bank cards, and supports a broad range of chains
     and tokens. Its devices pair with a phone, and the premium model adds Bluetooth and a
     larger screen for checking transactions on the device itself. The lineup runs from an
     entry model with a small screen to a premium model with a larger display.</p>
  <p><b>Trezor</b> builds around open source: the firmware and much of the hardware design
     are published, so the security claims can be audited by anyone rather than taken on
     trust. Its roots and its focus are Bitcoin, and its entry model is the cheaper way
     into hardware storage. The lineup runs from a straightforward entry model to a
     premium model with a colour touchscreen.</p>
  <p>Choosing between them is mostly one question. If you hold Bitcoin above all and want
     security you or anyone else can inspect in the source code, Trezor fits better. If
     you hold assets across many chains and want to manage them from a phone, Ledger fits
     better. Either device does the core job, which is keeping keys off an
     internet-connected machine.</p>

  <h2>Where to buy</h2>
  <p class="affil-note">We earn a commission if you buy through the links below. It costs
     you nothing extra and it does not change what we recommend. Separately, and for
     reasons that have nothing to do with us, both links go to the manufacturers' own
     stores, because that is where the supply chain is verifiable.</p>
  <div class="cta-row">
    {_cta(LEDGER_STORE, "Ledger", "Multi-chain and mobile access", "ledger.com")}
    {_cta(TREZOR_STORE, "Trezor", "Bitcoin focus and open source", "trezor.io")}
  </div>

  <h2>Sources</h2>
  <ul class="src-list">{sources}</ul>

  <p class="nfa">This page is educational. It explains how custody works and is not advice
     about your particular holdings, nor a recommendation to buy or sell any asset.</p>
</section></main>"""
