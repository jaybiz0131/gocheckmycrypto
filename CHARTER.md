# Crypto Cronkite: the News Desk charter

This desk is Desk 1 of the GoCheckMy two-desk charter (2026-07-15). The family master
charter, including the reference desk and the six per-site mission briefs, lives in the
gcm-newsroom repo's CHARTER.md; this file is this desk's operating half.

Mission: report what actually happened in crypto, stripped of shill, for a reader who is
lied to all day. Speed matters; accuracy outranks it. A held story costs a slot, a wrong
one costs the brand. Fail-closed everywhere: nothing wrong ships to make a deadline.

THE FOUR STAGES
1. RESEARCHER: feed aggregation (16 tiered RSS sources, deduplicated into clusters) plus
   the breaking-news watcher (deterministic thresholds, no model). Draftable stories get
   a structured research brief built from the FULL fetched source pages: data points
   with per-claim confidence labels (verified-on-chain / reported / announced-not-
   verified / unconfirmed), a deliberately-pulled bear case, open questions.
2. VERIFIER-EDITOR: the editor ranks and de-shills over the deterministic shill belt,
   with the desk's last-48h published titles in view (the librarian's shelf: repeats
   rank only as genuine updates). An independent adversarial verifier live-fetches
   every cited source and issues VERIFIED / NEEDS-HUMAN-REVIEW / REJECT. BREAKING-AS-
   FACT needs two INDEPENDENT sources; wire rewrites are not independence;
   single-source breaking publishes only labeled unconfirmed, or holds a slot.
3. WRITER: the Cronkite voice: straight, sourced, no hype, no advice, epistemics in the
   prose, the take slot always empty for a human. Brief-bound: no fact outside the
   brief. Across the day's three slots, update and extend, never repeat.
4. GATE: ten deterministic classes (source liveness, dedup/rerun, compliance lint,
   persona/credential, em-dash, depth, template completeness, NFA, approver sign-off,
   breaking two-source), the post-draft approver tracing every fact to its brief, and
   the categorized editorial log.

CADENCE: The Morning Brief 10:40 UTC, The Afternoon Brief 17:08, The Evening Brief 23:08 (Eastern
audience clock); watcher-triggered breaking runs; slot recovery on cron drift; contract
ladder on small-model output; monthly aging review WITH the correction loop
(corrections.py: premise-flagged stories re-run through research -> write -> approve and
update in place only with the approver's signature, stamped with a correction note).

THE BOTTOM LINE (2026-07-15): each edition closes with the desk's signature 3-5
sentence read: synthesis of what happened and why it mattered, never price
direction, never setup language, never advice, never causation beyond sources.
It renders in its own band at the top of the homepage and the news desk, refreshed
every slot (breaking runs regenerate the current slot's edition), archived forever
at /bottom-line.html, and guarded by its own deterministic directional-language
gate on top of the prompt lane.

COMMERCIAL DOCTRINE (owner's ruling, 2026-07-28, ratified as family law across the
Crypto, News and Sports desks). Affiliate revenue is allowed, and where it may appear is
fixed by tier:

- NEWS surfaces never carry affiliate anything. The homepage lead, Latest, articles, the
  Editions, the RSS feed and the Google News sitemap stay clean. This is the credibility
  that makes every other surface worth something.
- BOARDS (Whale Watch, Market Pulse, Chart Master) may carry a contextual link to an
  explainer where it genuinely helps a reader, and nothing more: no calls to action, no
  commission language, no affiliate URL on a data board.
- EVERGREEN explainers carry the disclosed commercial layer. Disclosure sits above the
  first link, the commission sentence stays separate from any editorial rationale, links
  are store-wide and carry rel="sponsored noopener", and recommendations follow fit and
  never commission rate (the routing rule is written down in explainers.py).

THE FAILURE RULE, standing and absolute: no money path ever attaches to coverage of a
failure, collapse, or loss. Exchange bankruptcies, hacks, depegs and wind-downs are the
highest-converting pages a crypto desk will ever publish, and they are permanently
off limits to the commercial layer. A desk that monetizes fear has stopped being a desk.

THE SEVERABILITY TEST: delete the commercial layer from any page carrying one. If the
piece no longer stands as an article, it was an advertisement and it does not ship.

CATEGORY FIRST, NAME SECOND, the construction rule that makes severability pass. Describe
what the category of thing does and what problem it solves, thoroughly enough that a reader
could go find one unaided. Only then name a specific option, in its own sentence, as an
instance of that category. A brand name must never do the work a description should be
doing. Built that way, cutting the name still leaves the reader knowing what to look for.
Measure it rather than assuming it: strip the commercial section and every sentence naming
a partner, then read what survives. The tax explainer keeps 94 percent of its words under
that cut, with no dangling reference left behind.

LEARN TOPIC SELECTION (owner's ruling, 2026-07-28). Learn topics are chosen by reader need
first. Only after a topic is chosen do we ask whether a product is honestly part of the
answer, and most of the time it will not be. Pieces that carry no affiliate link get
written anyway, at the same quality and the same length. A Learn tier where three of twelve
pieces carry links is more credible, and probably converts better, than one where all
twelve do, because the nine that ask for nothing are what make the three believable.
Monetization never ranks the queue. The severability test stays absolute above all of this:
if a piece collapses when the commercial layer is deleted, it does not ship.

READER DATA (owner's correction, 2026-07-28). An earlier handoff described this desk as
collecting no email, which was wrong. This desk does collect email, and the actual policy
is: addresses are collected through the newsletter signup form and for the newsletter only,
they are stored in Netlify Forms and delivered to the company inbox, they are never sold
and never shared with anyone else, and every issue carries an unsubscribe that removes the
address from the list. Nothing else about a reader is collected by us. The reader-facing
statement of this is the privacy page, and the signup form's fine print must agree with it.

The reader-facing version of this charter is the site's method page.
