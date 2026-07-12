# GoCheckMyCrypto (Crypto Cronkite): DEVIATIONS.md

Places where the build diverged from, or must flag a tension in, its instructions.
House rule (inherited from the GoCheckMy family): surface tensions, do not resolve them silently.

---

## D1 - Migrated out of the GoCheckMyPet repo (2026-07-10; resolves the original D-CRYPTO-1 tension 1)

Crypto Cronkite was originally built inside the GoCheckMyPet repo under `crypto_pipeline/`
(branch `claude/crypto-cronkite-pipeline-i9zgjh`, PR #1, never merged into that repo's main),
because it reused that repo's proven pattern: scheduled ingest, AI processing, verified and
human-gated output, and the two-layer self-verification discipline. The "different product,
same repo" tension was recorded from day one with the note "if it graduates to its own home,
the directory lifts out whole."

It graduated: this repo was created via `git subtree split --prefix=crypto_pipeline`, so the
full crypto commit history is preserved with the pipeline at the repo root. Only the CI
workflows, the Netlify config (now a zero-setting root `netlify.toml`), and doc paths were
adapted; no Python changed (every script resolves paths from its own location by design).
GoCheckMyPet's main was never touched by any of this work.

## D2 - Raw HTTP, not the Anthropic SDK

The Claude API guidance prefers the official SDK. This project is deliberately dependency-free
and offline-reproducible (standard library only, like its GoCheckMy siblings), so the LLM
client calls `https://api.anthropic.com/v1/messages` directly with `urllib` and the documented
headers. The request shape follows the current model family: no `temperature`/`top_p`/`top_k`
(those return HTTP 400 on `claude-opus-4-8` / `claude-sonnet-5`); register and determinism are
steered by the prompts.

## D3 - Quality-first models over the blueprint's cost emphasis (updated 2026-07-10)

The blueprint stresses cheap-per-run calls and a spend cap. Per the owner's explicit call
("the right man for the job; I will pay more for better quality"), the two JUDGMENT stages
run `claude-fable-5` (Anthropic's most capable model, $10/$50 per MTok): the editor, whose
job is filtering shill, and the verifier, whose job is accuracy against live sources. The
writer stays on `claude-opus-4-8` (strong news prose, human-reviewed anyway, and a second
model family after two Fable stages). Two Fable-specific accommodations in `llm.py`: a
600s HTTP timeout (its always-on thinking can run minutes) and a server-side refusal
fallback to `claude-opus-4-8` (hack/exploit coverage, core content for a crypto desk, can
trip Fable's cybersecurity safety classifiers; the fallback re-serves declined calls in the
same request, and a full-chain refusal still fails the stage closed). The cost discipline is
met by the hard cap (raised to $5/run for thinking-token headroom; typical runs land well
under $1.50), not by silently downgrading the model. Note: `claude-fable-5` requires 30-day
data retention on the Anthropic org; a zero-data-retention org would 400 on every call.

## D4 - Standalone brand; name-only GoCheckMy family tie

Two deliberate divergences from the GoCheckMy family conventions, decided with the owner:

1. **No family visual reskin.** GoCheckMy siblings share a teal/gold palette, Fraunces
   wordmark, and a shared disclosure-bar header. This site keeps its own trusted-newsroom
   identity (Newsreader serif, red masthead rule) because the owner has an existing Crypto
   Cronkite channel, logo, and audience; continuity there outweighs family visual consistency.
   The family tie is the NAME only: the domain `gocheckmycrypto.com`, a small
   "GoCheckMyCrypto.com" marker in the masthead top row, and the canonical
   `<a href="https://gocheckmy.com/">A GoCheckMy site</a>` hub link in the footer. Crypto
   Cronkite is the focal brand (masthead + tagline "And that's the way it is."); the Cronkite
   name is used as a brand/homage, never as the domain or company (the riskier play).

2. **Email newsletter kept, diverging from the family "no email capture" rule.** The crypto
   blueprint explicitly makes the newsletter the highest-value channel ("the owned audience,
   build this first"), and the owner confirmed this site stands on its own apart from the
   family. The signup stays (Netlify Forms; no selling of emails; unsubscribe-anytime copy
   baked in).

## D6 - The Netlify build fetches Whale Alert data (build is no longer purely deterministic)

The repo's stated posture is a deterministic site build from committed content. The Whale
Watch board needs fresh data without a human committing JSON every day, so the Netlify build
command runs `whale_flows.py` (network call to Whale Alert, keyed by a Netlify env var)
before `site_build.py`, and the daily-brief workflow pings a Netlify build hook so the board
refreshes every morning. The tension is contained: the fetch is fail-open (`|| true`; a
missing key or API error falls back to the committed `site/data/flows.json` snapshot, never
fails a deploy), everything else in the build stays deterministic from the commit, and a
local `python3 site_build.py` still reproduces the site from committed content exactly.

## D7 - Whale Alert: free public archive instead of the retired keyed API (2026-07-10)

Whale Alert retired the keyed v1 REST API this pipeline was built against. The replacements
(a $29.95/mo personal-use-only WebSocket needing a 24/7 listener, and a $699/mo Enterprise
REST API) fit neither the budget nor the static/serverless posture. Instead, both consumers
(the Whale Watch board and the brief's on-chain items) now read Whale Alert's FREE public
archive of every alert they post (`https://whale-alert.io/whale-alerts-archive.json.gzip`),
which Whale Alert explicitly offers for models/algorithms/research and which refreshes
continuously. Trade-offs, stated honestly on the site: (1) the archive names owners but has
no owner_type, so exchanges are identified by a curated name list in common.py (a heuristic);
(2) only transfers large enough for Whale Alert to post publicly (roughly $50M+) appear, so
the board reflects the very largest moves, not all whale activity. The loader streams the
newest-first gzip and stops at the window boundary, reading tens of KB, not the ~600MB file.
The board is fail-open (fetch failure keeps the previous snapshot); the news pipeline treats
a fetch failure as a documented skip. Attribution and links to Whale Alert are on the board.
Live-tested 2026-07-10: 21 archive alerts in 24h -> 11 exchange-relevant transfers, real
board committed. This resolves and replaces the old D5 concern for Whale Alert.

Addendum 2026-07-12: because only ~$50M+ moves appear, a quiet day can leave the configured
24h window with zero exchange-relevant transfers, and the build was overwriting a good board
with an empty one ("no board yet" in production). `whale_flows.py` now widens the lookback
(48h -> 72h -> 7d) until something exchange-relevant appears and labels the board with the
window it actually shows (the page explains the widening to the reader). If even a week is
empty it keeps the previous snapshot, the same fail-open as a fetch error.

## D8 - Market Pulse: third-party market data fetched at build time (2026-07-10)

The Market Pulse page (sentiment gauge, RSI/MACD/moving-average posture, stablecoin float,
Bitcoin network vitals) extends the D6 posture: `market_pulse.py` fetches four keyless
public sources at Netlify build time (alternative.me, CoinGecko, DefiLlama, mempool.space)
and computes the indicators with standard formulas in the standard library. Each section is
independently fail-open: a failed source is warned and omitted, a fully failed run keeps the
committed snapshot, and a deploy never fails on market data. The same honesty rules as Whale
Watch apply: sources are named on the page, every indicator gets a plain-language education
card, and none of it ever becomes a buy or sell call. The Whale Watch board also gained a
13-week net-flow history computed from the same public archive read (D7). Market data never
touches the editorial pipeline or the human gate.

## D5 - X source adapter is wired but not live-tested

X/Twitter remains a keyless-skip source (absence is a documented skip, never a failure) and
could not be exercised without a paid API key (~$100/mo). Treat the first keyed run as a
smoke test and check the intake log. (Whale Alert, formerly also in this entry, is now
live-tested via the public archive -- see D7.)
