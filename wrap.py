#!/usr/bin/env python3
"""
wrap.py: the DAILY EDITION (The Morning Brief / The Closing Wrap), 2026-07-14.

Jack's product call: the desk is a full media outlet, and a media outlet never posts a
zero-content morning. This stage produces the flagship twice-daily synthesis: what is
really going on, why, and what to watch in the coming days: the voice of reason for a
market in constant panic. It runs AFTER autopilot in the brief workflow and can ALWAYS
publish, because its raw material is already gated: the desk's own published, verified
stories plus the desk's own boards. No new facts enter here.

Gates (fail-closed for the edition, fail-open for the brief: a wrap failure never blocks
story publishing):
  - the writer model is contract-bound to the provided inputs (prompts/wrap.md);
  - a separate checker call (stage "wrapcheck") verifies every specific fact traces to
    the inputs and nothing reads as advice or prediction; one retry with the reasons;
  - deterministic belts: destyle, no em dashes, advice-word lint, length bounds, NFA.

Editions: UTC hour < 14 -> morning (The Morning Brief), else closing (The Closing Wrap).
One edition file per slot per day (rerun-safe). The edition leads the site for its slot
via negative rank (load_content sorts rank ascending within the date; the day's #1 story
is rank 1, morning wrap -1, closing wrap -2 so the newest edition leads).

USAGE
  python3 wrap.py                          # live: write site/content/<date>-<edition>.json
  python3 wrap.py --dry-run                # write out/wrap-preview.json only
  python3 wrap.py --edition morning|closing  # override the clock (tests, replay)
"""

import datetime
import glob
import json
import os
import re
import sys

import common
import llm as llmlib

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "site", "content")
NFA = "Crypto Cronkite reports events. It never advises trades. Nothing here is financial advice."

EDITIONS = {
    "morning": {"name": "The Morning Brief", "slug": "morning-brief", "rank": -1,
                "id_prefix": "wrap-am"},
    "midday": {"name": "The Midday Update", "slug": "midday-update", "rank": -2,
               "id_prefix": "wrap-md"},
    "evening": {"name": "The Evening Wrap", "slug": "evening-wrap", "rank": -3,
                "id_prefix": "wrap-pm"},
    # legacy alias (pre-3-slot cadence); resolves to the evening edition
    "closing": {"name": "The Evening Wrap", "slug": "evening-wrap", "rank": -3,
                "id_prefix": "wrap-pm"},
}

ADVICE_LINT = [r"\byou should\b", r"\bbuy\b", r"\bsell\b", r"\bgood entry\b",
               r"\bwill (rally|crash|pump|dump|10x|moon)\b", r"\bguaranteed\b",
               r"\btime to (buy|sell|enter|exit)\b"]


def gather_stories(hours=36):
    """The desk's own published stories from the window: already verified + approved, so
    they are legal fact inputs. Editions themselves are excluded (no wrap-of-wraps)."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(hours=hours))
    out = []
    for p in sorted(glob.glob(os.path.join(CONTENT, "*.json"))):
        if os.path.basename(p).startswith("example"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("id", "").startswith("wrap-"):
            continue
        ts = d.get("published_utc") or (d.get("date", "") + "T00:00:00Z")
        try:
            when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        if when < cutoff:
            continue
        body = d.get("body", [])
        body = body if isinstance(body, list) else [str(body)]
        out.append({
            "title": d.get("title", ""), "summary": d.get("dek", ""),
            "key_fact": d.get("key_fact", ""),
            "first_paragraphs": body[:2],
            "bottom_line": d.get("bottom_line", ""),
            "date": d.get("date", ""),
            "url": f"/articles/{d.get('slug','')}.html",
        })
    return out


def belts(article_body, dek, watch):
    """Deterministic checks; returns a list of problems (empty = pass)."""
    problems = []
    text = " ".join([article_body, dek, watch])
    if "—" in text or "–" in text:
        problems.append("em/en dash in the edition")
    low = text.lower()
    for pat in ADVICE_LINT:
        if re.search(pat, low):
            problems.append(f"advice-lint hit: {pat}")
    words = len(article_body.split())
    if not 120 <= words <= 950:
        problems.append(f"body {words} words outside 120-950")
    return problems


def check(client, obj, stories, boards):
    """Independent trace check: every specific fact must come from the inputs."""
    user = ("Verify this daily edition against its ONLY permitted inputs. Rules: every "
            "specific number, name, date, and event in the edition must appear in the "
            "inputs; connecting/synthesizing them is allowed and expected; nothing may "
            "read as a price prediction, trade advice, or 'you should'; register must be "
            "calm (no hype, no panic language). Respond ONLY with JSON: "
            '{"decision": "APPROVE"|"REJECT", "reasons": ["<specific claim and why>"]}\n\n'
            "EDITION:\n" + json.dumps(obj, indent=1)
            + "\n\nINPUT STORIES:\n" + json.dumps(stories, indent=1)
            + "\n\nINPUT BOARDS:\n" + json.dumps(boards, indent=1))
    def check_shape(o):
        if o.get("decision") not in ("APPROVE", "REJECT"):
            raise llmlib.LLMError(f"wrapcheck: invalid decision {o.get('decision')!r}")
        return o
    v = client.call_json("wrapcheck",
                         "You are an adversarial fact-trace checker for a news desk. "
                         "Default to REJECT when uncertain.", user, validate=check_shape)
    return v.get("decision") == "APPROVE", v.get("reasons", [])


def build_item(edition, obj, stories, date, published_utc):
    ed = EDITIONS[edition]
    from site_build import destyle
    paras = [destyle(p.strip()) for p in str(obj.get("body", "")).split("\n") if p.strip()]
    return {
        "id": f"{ed['id_prefix']}-{date}",
        "slug": f"{ed['slug']}-{date}",
        "kind": "brief",
        "title": destyle(f"{ed['name']}: {obj.get('hook_title','').strip()}"),
        "dek": destyle(obj.get("dek", "")),
        "date": date, "published_utc": published_utc,
        "category": "daily edition",
        "rank": ed["rank"],
        "author": "Crypto Cronkite",
        "key_fact": destyle(obj.get("key_takeaway", "")),
        "bottom_line": destyle(obj.get("the_watch", "")),
        "human_take": "",
        "body": paras,
        "sources": [{"title": s["title"], "url": s["url"]} for s in stories],
    }


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    now = datetime.datetime.now(datetime.timezone.utc)
    # three slots (Eastern audience clock): 10:40 UTC morning, 17:00 UTC midday,
    # 23:00 UTC evening; the hour windows resolve whichever slot is running
    edition = (argv[argv.index("--edition") + 1] if "--edition" in argv
               else ("morning" if now.hour < 14 else "midday" if now.hour < 20 else "evening"))
    if edition not in EDITIONS:
        print(f"wrap: unknown edition '{edition}'"); return 1
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("wrap: PAUSE file present -> skipping"); return 0
    date = now.date().isoformat()
    # rerun-safe: one edition per slot per day
    final_path = os.path.join(CONTENT, f"{date}-{EDITIONS[edition]['slug']}.json")
    if not dry and os.path.exists(final_path):
        print(f"wrap: {EDITIONS[edition]['name']} already published today -> skip"); return 0

    stories = gather_stories()
    if not stories:
        print("wrap: no published stories in the window; a quiet-day edition needs at "
              "least the boards, but with zero stories the desk stays silent (honest).")
        return 0
    boards = None
    try:
        import chartmaster
        boards = chartmaster.digest()
    except Exception as e:
        common.gh("warning", f"wrap: desk boards unavailable ({e}); edition from stories only")

    # within-day continuity: later editions UPDATE and EXTEND the day's coverage rather
    # than repeating it; give the model what already ran today so it can move forward
    earlier = []
    for slug in ("morning-brief", "midday-update"):
        p = os.path.join(CONTENT, f"{date}-{slug}.json")
        if os.path.exists(p) and not p == final_path:
            try:
                e = json.load(open(p, encoding="utf-8"))
                earlier.append({"edition": e.get("title", ""), "dek": e.get("dek", ""),
                                "watch": e.get("bottom_line", "")})
            except Exception:
                pass

    cfg = common.load_config()
    client = llmlib.Client(cfg)
    system = common.load_prompt("wrap.md")
    user = (f"edition: {edition}\n\ntodays_stories:\n{json.dumps(stories, indent=1)}\n\n"
            + (f"desk_boards:\n{json.dumps(boards, indent=1)}\n\n" if boards else
               "desk_boards: (unavailable this run)\n\n")
            + (("earlier_editions_today (UPDATE and EXTEND, never repeat; lead with what "
                "changed since):\n" + json.dumps(earlier, indent=1) + "\n") if earlier else ""))

    def wrap_shape(o):
        for k in ("hook_title", "dek", "body", "the_watch"):
            if not str(o.get(k, "")).strip():
                raise llmlib.LLMError(f"wrap output missing '{k}'")
        return o

    obj = client.call_json("wrap", system, user, validate=wrap_shape)
    for attempt in (1, 2):
        probs = belts(str(obj.get("body", "")), str(obj.get("dek", "")),
                      str(obj.get("the_watch", "")))
        ok, reasons = (True, [])
        if not probs and client.mode == "live":
            ok, reasons = check(client, obj, stories, boards or {})
        if not probs and ok:
            break
        all_reasons = probs + reasons
        if attempt == 2:
            common.gh("error", f"wrap: edition failed its gates twice ({'; '.join(all_reasons[:4])}) "
                      f"-> NOT published (stories unaffected)")
            common.write_out("wrap-rejected.json", {"edition": edition, "obj": obj,
                                                    "reasons": all_reasons})
            return 1
        obj = client.call_json("wrap", system, user
                               + "\n\nYour previous attempt failed these checks; fix them "
                                 "and return the full JSON again:\n- "
                               + "\n- ".join(all_reasons), validate=wrap_shape)

    item = build_item(edition, obj, stories, date, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if dry:
        common.write_out("wrap-preview.json", item)
        print(f"wrap: DRY RUN {EDITIONS[edition]['name']} "
              f"({len(' '.join(item['body']).split())} words, {len(stories)} input stories) "
              f"-> out/wrap-preview.json")
        return 0
    json.dump(item, open(final_path, "w", encoding="utf-8"), indent=2)
    print(f"wrap: published {EDITIONS[edition]['name']} "
          f"({len(' '.join(item['body']).split())} words) -> {os.path.relpath(final_path)} "
          f"[budget {client.budget.summary()}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
