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

## D3 - Default model `claude-opus-4-8` over the blueprint's cost emphasis

The blueprint stresses cheap-per-run calls and a spend cap. The model default is
`claude-opus-4-8` (quality, per the owner's explicit call), with a hard per-run token/USD
budget cap in `config.json` and a documented `claude-sonnet-5` swap for a cheaper run. The
cost discipline is met by the cap, not by silently downgrading the model.

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

## D5 - Whale Alert and X source adapters are wired but not live-tested

Both are keyless-skip sources (absence is a documented skip, never a failure) and could not be
exercised here without paid/gated API keys. The Whale Alert flow classification is locked by an
offline canary over fixture transactions, and the Whale Watch board ships an EXAMPLE snapshot
(clearly ribboned) until a key is connected. Treat the first keyed run of each as a smoke test
and check the intake log.
