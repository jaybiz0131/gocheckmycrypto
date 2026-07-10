#!/usr/bin/env python3
"""
llm.py: the shared Anthropic client for the editor / verifier / writer stages.

FAIL-CLOSED by construction. This is the load-bearing safety property of the whole
pipeline (STAGE 0 of the blueprint): any error here raises, the orchestrator catches it,
writes a failed run report, and publishes NOTHING. There is no silent-success path.

  - No key            -> LLMError (the run flags a human; nothing publishes).
  - Budget exceeded   -> BudgetError before the offending call is made.
  - HTTP / parse error -> LLMError (the stage fails; the orchestrator fails closed).

RAW HTTP ON PURPOSE. This repo is deliberately dependency-free and offline-reproducible
(see build.sh: "deterministic and works offline"; every existing pipeline script uses only
the standard library). Adding the `anthropic` SDK would break that posture, so we call
https://api.anthropic.com/v1/messages directly with urllib and the documented headers. The
request shape follows the current model family: no temperature/top_p/top_k (those return
HTTP 400 on claude-opus-4-8 / sonnet-5), register and determinism are steered by the prompt.
See DEVIATIONS D-CRYPTO-1.

MODES
  live   (default)  real API call; requires ANTHROPIC_API_KEY.
  replay            reads fixtures/llm_replay.json keyed by stage; NO network, NO key, NO
                    spend. For the offline canary and the wiring test ONLY. A replay run is
                    stamped mode=replay everywhere downstream so it can never be mistaken for
                    a real editorial run (the human gate and publish refuse replay output).

Set the mode with the CRYPTO_LLM_MODE env var or the `mode` argument.
"""

import json
import os
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
REPLAY_PATH = os.path.join(HERE, "fixtures", "llm_replay.json")

# Approximate list price, USD per 1M tokens (input, output). Used only for the per-run cost
# cap; keep in sync with the model card. Overshooting the cap fails closed before the call.
# Cost is keyed by the REQUESTED model: if a refusal fallback serves a call, the output was
# produced by the (cheaper) fallback model but is counted at the requested model's rates, so
# the tracker only ever overestimates spend, never under.
PRICING = {
    "claude-opus-4-8":  (5.0, 25.0),
    "claude-opus-4-7":  (5.0, 25.0),
    "claude-sonnet-5":  (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5":   (10.0, 50.0),
}
DEFAULT_PRICE = (5.0, 25.0)


class LLMError(RuntimeError):
    """Any failure that must fail the stage closed (no key, HTTP error, unparseable output)."""


class BudgetError(LLMError):
    """The per-run token or dollar cap would be exceeded; refuse the call."""


class Budget:
    """Tracks cumulative spend across a run and refuses a call that would break the cap."""

    def __init__(self, max_tokens, max_usd):
        self.max_tokens = max_tokens
        self.max_usd = max_usd
        self.tokens = 0
        self.usd = 0.0
        self.calls = 0

    def record(self, model, usage):
        it = usage.get("input_tokens", 0) or 0
        ot = usage.get("output_tokens", 0) or 0
        it += (usage.get("cache_creation_input_tokens", 0) or 0)
        it += (usage.get("cache_read_input_tokens", 0) or 0)
        pin, pout = PRICING.get(model, DEFAULT_PRICE)
        self.tokens += it + ot
        self.usd += (it * pin + ot * pout) / 1_000_000
        self.calls += 1
        if self.tokens > self.max_tokens:
            raise BudgetError(f"token cap exceeded: {self.tokens} > {self.max_tokens} "
                              f"after {self.calls} call(s) -> failing closed")
        if self.usd > self.max_usd:
            raise BudgetError(f"USD cap exceeded: ${self.usd:.2f} > ${self.max_usd:.2f} "
                              f"after {self.calls} call(s) -> failing closed")

    def summary(self):
        return {"calls": self.calls, "tokens": self.tokens, "usd": round(self.usd, 4),
                "max_tokens": self.max_tokens, "max_usd": self.max_usd}


class Client:
    def __init__(self, cfg, mode=None, budget=None):
        self.cfg = cfg
        self.mode = mode or os.environ.get("CRYPTO_LLM_MODE", "live")
        b = cfg.get("budget", {})
        self.budget = budget or Budget(b.get("max_tokens_per_run", 200000),
                                       b.get("max_usd_per_run", 3.0))
        self._replay = None

    # ---- public --------------------------------------------------------------

    def call_json(self, stage, system, user):
        """Run one stage and return its parsed JSON object. Raises LLMError on any failure."""
        model_cfg = self.cfg["models"][stage]
        if self.mode == "replay":
            raw = self._replay_raw(stage)
        else:
            raw = self._live_raw(stage, model_cfg, system, user)
        obj = extract_json(raw)
        if obj is None:
            raise LLMError(f"{stage}: model output was not parseable JSON (first 200 chars: "
                           f"{raw[:200]!r})")
        return obj

    # ---- live ----------------------------------------------------------------

    def _live_raw(self, stage, model_cfg, system, user):
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise LLMError(f"{stage}: ANTHROPIC_API_KEY is not set -> failing closed "
                           f"(the pipeline never publishes on a missing key)")
        model = model_cfg["model"]
        body = {
            "model": model,
            "max_tokens": model_cfg.get("max_tokens", 4000),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        # claude-fable-5 runs cybersecurity safety classifiers, and hack/exploit coverage is
        # core news for this desk, so benign stories can occasionally be declined. The
        # server-side fallback re-runs a declined request on claude-opus-4-8 inside the same
        # call (a decline before output is not billed; the rescue bills at Opus rates). If the
        # whole chain still refuses, the stop_reason check below fails the stage closed.
        if model == "claude-fable-5":
            body["fallbacks"] = [{"model": "claude-opus-4-8"}]
            headers["anthropic-beta"] = "server-side-fallback-2026-06-01"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, method="POST", headers=headers)
        resp_json = self._post_with_retry(stage, req)
        if resp_json.get("stop_reason") == "refusal":
            raise LLMError(f"{stage}: model refused the request (whole fallback chain, if any) "
                           f"-> failing closed")
        self.budget.record(model, resp_json.get("usage", {}) or {})
        parts = [b.get("text", "") for b in resp_json.get("content", []) if b.get("type") == "text"]
        text = "".join(parts).strip()
        if not text:
            raise LLMError(f"{stage}: empty model response -> failing closed")
        return text

    def _post_with_retry(self, stage, req, attempts=4):
        delay = 2
        last = None
        for i in range(attempts):
            try:
                # claude-fable-5 thinks before answering (always on) and hard calls can run
                # minutes; a short timeout would fail perfectly healthy requests.
                with urllib.request.urlopen(req, timeout=600) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                code = e.code
                detail = e.read().decode("utf-8", "replace")[:300]
                # 4xx (except 429) are our fault: do not retry, fail closed immediately.
                if code != 429 and 400 <= code < 500:
                    raise LLMError(f"{stage}: HTTP {code} from Anthropic API -> failing closed: {detail}")
                last = LLMError(f"{stage}: HTTP {code} from Anthropic API: {detail}")
            except Exception as e:
                last = LLMError(f"{stage}: request failed: {e}")
            if i < attempts - 1:
                time.sleep(delay)
                delay *= 2
        raise last

    # ---- replay (offline test only) ------------------------------------------

    def _replay_raw(self, stage):
        if self._replay is None:
            if not os.path.exists(REPLAY_PATH):
                raise LLMError(f"replay mode: {os.path.relpath(REPLAY_PATH)} not found")
            self._replay = json.load(open(REPLAY_PATH, encoding="utf-8"))
        if stage not in self._replay:
            raise LLMError(f"replay mode: no recorded response for stage '{stage}'")
        # Charge a nominal replay cost so the budget path is exercised in tests too.
        self.budget.record(self.cfg["models"][stage]["model"],
                           {"input_tokens": 1000, "output_tokens": 500})
        val = self._replay[stage]
        return val if isinstance(val, str) else json.dumps(val)


def extract_json(text):
    """Return the first well-formed JSON object in text, or None. Models sometimes wrap JSON
    in prose or a ```json fence despite instructions; this recovers the object defensively."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except Exception:
                            break
        start = text.find("{", start + 1)
    return None
