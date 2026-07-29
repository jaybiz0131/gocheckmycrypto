#!/usr/bin/env python3
"""
learn_pages.py: Learn-tier explainers that carry NO commercial layer.

WHY THIS FILE IS SEPARATE FROM explainers.py, which matters more than it looks.
  explainers.py opens by saying the money path lives there and only there, so an auditor
  can read the site's entire commercial surface in one screen. That property is worth
  keeping, and it would not survive nine link-free pieces being added around the three
  that carry links. So the money path stays in one file and everything that asks the
  reader for nothing lives here.

  The split is also the doctrine made structural. LEARN_QUEUE.md ranks ten approved
  topics and none of them carry a link; this is where they go. If a page in this file
  ever grows an affiliate link, it is in the wrong file and something has gone wrong with
  more than the imports.

SOURCING NOTE. The first page here documents our own Whale Watch board, so its "sources"
are whale_flows.py and the board itself rather than an outside authority. That makes
accuracy MORE fragile, not less: if the methodology changes and this page does not, we are
publishing a false description of our own work. Every number and rule stated below is
marked with the constant it comes from. Change one, change both.
"""

import whale_flows


def _whale_facts():
    """Read the live methodology constants rather than restating them from memory, so the
    page cannot drift out of true when whale_flows.py is tuned."""
    return {
        "floor_musd": int(whale_flows.FALLBACK_MIN_USD / 1_000_000),
        "history_weeks": whale_flows.HISTORY_WEEKS,
        "widen": whale_flows.WIDEN_HOURS,
        "stables": len(whale_flows.STABLES),
    }


def onchain_flows_body():
    """How to read on-chain flow data, which doubles as the manual for Whale Watch.

    MAINTENANCE: this page describes whale_flows.py. If the classification rules, the
    size floor, the widening ladder or the baseline window change there, they change here
    in the same commit. The numbers are read from the module at build time so a constant
    cannot silently disagree with the prose, but the PROSE describing the rules is not
    automatic and has to be checked by a human.

    NO COMMERCIAL LAYER. There is nothing to sell on this page and nothing should ever be
    added. See the module docstring.
    """
    f = _whale_facts()
    widen = ", ".join(f"{h} hours" for h in f["widen"][:-1]) + f" and then {f['widen'][-1] // 24} days"
    return f"""<main class="wrap narrow"><section class="page">
  <span class="kicker"><a href="/learn.html">Learn</a> &middot; explainer</span>
  <h1>How to read on-chain flow data</h1>
  <p class="lede">Every large crypto transfer is public, which is why you keep seeing
     headlines about whales moving coins. Almost none of those headlines tell you what the
     movement means. Here is what an exchange transfer actually indicates, what it does
     not, and how to read the board we build from it.</p>

  <h2>Why moving coins to an exchange means anything at all</h2>
  <p>To sell a large amount of crypto on an exchange, you first have to put it on that
     exchange. The transfer and the sale are separate events, and the transfer happens
     first and in public. That gap is the entire basis of flow watching: it is one of the
     few times the market shows its hand before it acts.</p>
  <p>The reverse move carries the opposite implication. Coins leaving an exchange for a
     private wallet are, at minimum, coins that are not for sale today, because selling
     them now means moving them back. Money going out is read as accumulation and money
     going in is read as potential sell pressure.</p>
  <p><strong>Potential is doing real work in that sentence.</strong> A deposit is a
     precondition for selling, not a sale. People move coins onto exchanges to post
     collateral, to earn yield, to convert between assets, to move between their own
     accounts, or because they changed their mind and moved it back out a day later. A
     transfer is evidence of intent to have the option, and nothing more.</p>

  <h2>Why the aggregate is the only part worth reading</h2>
  <p>A feed of individual transfers is noise dressed as information. One entity moving
     coins tells you about one entity, and there is no way to tell from the outside
     whether that entity is a fund unwinding, an exchange rearranging its own storage, or
     a custodian doing routine maintenance.</p>
  <p>The aggregate is different. When many large holders lean the same way across a
     window, the direction of the sum is a genuine measurement of what large holders did,
     even when every individual reason stays unknown. That is why our board reports one
     net figure per asset instead of a scrolling list, and why the sentence to take from
     it is about the net rather than any single move.</p>

  <h2>How our board actually computes it</h2>
  <p>The rules are simple enough to state completely, and stating them completely is the
     point. Each large transfer is classified by what sits at each end.</p>
  <ul class="rule-list">
    <li><strong>A private wallet sending to an exchange counts as an inflow.</strong>
        Money arriving where it could be sold.</li>
    <li><strong>An exchange sending to a private wallet counts as an outflow.</strong>
        Money leaving into self-custody.</li>
    <li><strong>Exchange to exchange is ignored.</strong> That is housekeeping between
        venues, not a directional signal, and counting it would double the noise.</li>
    <li><strong>Wallet to wallet is ignored.</strong> No exchange is involved, so there is
        nothing to read.</li>
  </ul>
  <p>The headline number is outflows minus inflows, so a positive net means more left
     exchanges than arrived. That is the figure the board leads with, and the word beside
     it, off or onto, is just the sign of that subtraction stated in English.</p>
  <p><strong>Stablecoins are scored separately, and this is the part most flow coverage
     gets backwards.</strong> A stablecoin moving onto an exchange is not sell pressure,
     it is buying power arriving: dollars staged where they can buy something. Folding
     stablecoins into the same net as bitcoin would make incoming purchasing power look
     identical to incoming supply. So our board scores the sell-pressure signal on
     volatile assets only and reports stablecoin inflow separately, as its own line.
     The board treats {f['stables']} stablecoins this way.</p>

  <h2>Reading the labels honestly</h2>
  <ul class="rule-list">
    <li><strong>"Unknown wallet" means unlabeled, not suspicious.</strong> Our data names
        an owner only when the source has identified one. Most addresses on any chain have
        no public label at all, so a transfer to an unknown wallet is the ordinary case,
        not a red flag.</li>
    <li><strong>"Exchange-size" means roughly ${f['floor_musd']} million and up.</strong>
        The public alert feed we read only carries transfers above about that value, so
        the board is a view of the very largest movements and not of all activity. There
        is a great deal of real money moving below that line that will never appear.</li>
    <li><strong>A quiet board is a quiet feed, not a quiet market.</strong> When no
        qualifying transfers land in the last day, the window widens, {widen}, until
        something does, and the board says which window it is showing. A widened window
        means the feed was quiet; it does not mean whales stopped moving.</li>
    <li><strong>The pace figure is a comparison, not a verdict.</strong> Running at about
        one times a typical week's pace means the current window's net, scaled for its
        length, is close to the median of the last {f['history_weeks']} weeks. It answers
        "is this a lot?" and nothing else.</li>
  </ul>

  <h2>What this does not tell you</h2>
  <p>The honest limits are worth more than the signal, because the signal is widely
     oversold.</p>
  <p><strong>Flows do not reliably predict price.</strong> This is the claim to be most
     careful with, including when we are the ones showing you the chart. Large deposits
     have preceded selloffs and they have preceded nothing at all; large withdrawals have
     preceded rallies and have preceded further declines. There is no dependable lead time
     and no threshold that reliably means anything. Read it as one description of what
     large holders did, alongside everything else, and treat any source presenting it as a
     forecast with suspicion.</p>
  <p><strong>The exchange labels are the weak link.</strong> Classification depends on
     recognizing an address as belonging to an exchange, from a list of about 30 known
     names. An exchange wallet nobody has labelled is counted as self-custody, which would
     read an internal transfer as accumulation. The direction of that error is knowable
     and its size is not.</p>
  <p><strong>It is a sample of a sample.</strong> Only the largest transfers, only where
     both ends can be classified, only on the chains the feed covers. A net figure is an
     accurate statement about what the board saw, not about the whole market.</p>

  <h2>How to use it in one sentence</h2>
  <p>Watch the direction of the net over several days rather than any single window, treat
     it as a description of what large holders did and never as a forecast, and remember
     that a deposit is an option to sell rather than a sale. If you want to see it, the
     board is <a href="/flows.html">Whale Watch</a>, and every figure on it is computed the
     way this page describes.</p>
  <p>The other half of the picture, what a private wallet actually is and why moving coins
     off an exchange changes who controls them, is
     <a href="/cold-storage.html">cold storage, explained</a>.</p>

  <h2>Sources</h2>
  <ul class="src-list">
    <li>The classification rules, size floor and baseline window above are read from this
        site's own <code>whale_flows.py</code>, which builds the board.</li>
    <li>Owner labels and the transfer feed come from Whale Alert's public alert archive,
        credited on the board itself.</li>
  </ul>

  <p class="nfa">This page is educational. It explains how a measurement is built and what
     it can support, and is not advice about your particular holdings, nor a
     recommendation to buy or sell any asset.</p>
</section></main>"""
