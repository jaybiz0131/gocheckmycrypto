#!/usr/bin/env python3
"""
morning.py: the morning read (Program 7, Sprint 7.2, Jack's ruling of 12 October 2026).

The site must never read as last night's in the morning. At about 8:15 AM Eastern the Worker
dispatches morning-read.yml, which re-ranks the wire with the deterministic desk editor
(wire.py --refresh, no model), then runs this: one model call writes a headline, two or three
sentences and the narrative line, under the Edition's copy law and the twins gate, and the
run builds ONCE (the push, or the hook ping when nothing was pushed).

  python3 morning.py            # write site/data/morning.json (or fall back, exit 0)
  python3 morning.py --alarm    # exit 1 only if this is the second morning in a row to fall back

THE FALLBACK IS CLEAN. A missing key, an API error, a read the gate emptied: morning.json is
left as it was (home.usable_morning ignores any read that is not today's), the build still
goes out with fresh numbers, the Brief card says "Last night's Brief" with its time, and the
run exits 0. No error email for that. The alarm is for two mornings in a row.
"""
import datetime as _dt
import json
import os
import re
import sys

import common
import llm as llmlib
import phrases

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "data", "morning.json")
LEDGER = os.path.join(HERE, "data", "morning-ledger.json")
STATUS = os.path.join(HERE, "out", "morning-status.json")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-4))

SENTENCES = (2, 3)
HEADLINE_MAX = 100


def et_stamp(now):
    return now.astimezone(ET).strftime("%-I:%M %p ET on %b %-d")


def inputs(snapshot=None, wire=None):
    import narrative
    import twins_gate
    import wire as wiremod
    snap = snapshot if snapshot is not None else twins_gate.current_snapshot()
    w = wire if wire is not None else (wiremod.load() or {})
    items, top = [], []
    for i in (w.get("items") or []):
        if not i.get("line"):
            continue
        # the copy law quotes no change: a wire line holding "up to 2% spread" is handed over
        # with that clause cut, or left out (15 Oct: every sentence built on it was cut)
        line = phrases.percent_free(i["line"])
        if not line:
            continue
        items.append(i)
        top.append({"id": i.get("id"), "line": line, "sources": i.get("source_count")})
        if len(items) == 5:
            break
    return narrative.readings(snap), top, items


def clean(obj, gate, final=False, top=None, info=None):
    """(headline, sentences, narrative_line) after the copy law, or raises LLMError.

    The part is not the whole: a sentence the law refuses is cut, the others stand; only a read
    left with fewer than two sentences is refused. The same for the headline (15 Oct: "missing or
    oversized headline" fell the whole morning back and never said which). A headline that is
    missing or too long says so, in words the repair rung can act on; on the last rung it is fixed
    here instead of failing the read: too long is trimmed at a word boundary, missing is the
    wire's top line (phrases.derive_headline). `info["headline_by"]` records which."""
    import narrative
    import wrap
    from site_build import destyle
    info = info if info is not None else {}
    if not isinstance(obj, dict):
        raise llmlib.LLMError("morning: output is not an object")
    head = destyle(str(obj.get("headline") or "").strip())
    sents = [destyle(str(s).strip()) for s in obj.get("sentences") or [] if str(s).strip()]
    line = destyle(" ".join(str(obj.get("narrative_line") or "").split()))
    info["headline_by"] = "model"
    why = phrases.headline_problem(head, HEADLINE_MAX)
    if why:
        if not final:
            raise llmlib.LLMError(f"morning: the headline {why}")
        if head:
            head, info["headline_by"] = phrases.trim_headline(head, HEADLINE_MAX), "trimmed"
        else:
            head = destyle(phrases.derive_headline([t.get("line") for t in top or []], HEADLINE_MAX))
            info["headline_by"] = "wire top line" if top else "fixed line"
        print(f"morning: the headline {why.split(';')[0]}; fixed deterministically ({info['headline_by']}): {head!r}")

    def bad(t):
        # a change quoted (7.1's color-truth rule), a prediction, advice, desk-opinion voice;
        # the rule is named so the run log says what cut a sentence
        if narrative.quotes_change(t):
            return "quotes a change"
        if narrative._PREDICT.search(t):
            return "predicts"
        if wrap.bottom_line_lint(t):
            return "bottom-line lane"
        if wrap.unattributed_lint(t):
            return "unattributed voice"
        if re.search(r"[\u2013\u2014]", t):
            return "carries a dash"
        return ""
    r = bad(head)
    if r:
        raise llmlib.LLMError(f"morning: the headline breaks the copy law ({r}): {head!r}")
    kept = []
    for s in sents:
        r = bad(s)
        if r:
            print(f"morning: cut a sentence under the copy law ({r}): {s[:100]!r}")
            continue
        if gate is not None and gate.text(s, "the morning read", dollars=True).strip() != s:
            print(f"morning: the twins gate cut: {s[:100]!r}")
            continue
        kept.append(s)
    if len(kept) < SENTENCES[0]:
        raise llmlib.LLMError(f"morning: {len(kept)} sentence(s) survived the copy law; "
                              f"{SENTENCES[0]} needed")
    return head, kept[:SENTENCES[1]], line


def record(date_et, outcome, reason="", tokens=0, usd=0.0, path=None):
    path = path or LEDGER
    try:
        rows = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get("date") != date_et]      # one row a morning
    rows.append({"date": date_et, "outcome": outcome, "reason": reason[:160],
                 "tokens": tokens, "usd": round(usd, 4)})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(rows[-120:], open(path, "w", encoding="utf-8"), indent=1)


def second_fallback(path=None, today=None):
    path = path or LEDGER
    """True when the last two mornings on record are consecutive days and both fell back."""
    try:
        rows = sorted(json.load(open(path, encoding="utf-8")), key=lambda r: r["date"])
    except (OSError, ValueError, KeyError):
        return False
    if len(rows) < 2:
        return False
    a, b = rows[-2], rows[-1]
    try:
        gap = (_dt.date.fromisoformat(b["date"]) - _dt.date.fromisoformat(a["date"])).days
    except ValueError:
        return False
    return gap == 1 and a["outcome"] == "fallback" and b["outcome"] == "fallback"


def run(now=None, client=None, snapshot=None, wire=None):
    now = now or _dt.datetime.now(_dt.timezone.utc)
    date_et = now.astimezone(ET).date().isoformat()
    tokens, usd = 0, 0.0
    try:
        cfg = common.load_config()
        client = client or llmlib.Client(cfg)
        if client.mode == "replay":
            raise llmlib.LLMError("morning: replay mode, no live model")
        readings, top, items = inputs(snapshot, wire)
        system = common.load_prompt("morning.md")
        user = "Write this morning's read.\n\n" + json.dumps(
            {"board_phrases": phrases.morning_phrases(readings), "wire_top": top}, indent=1)
        import twins_gate
        gate = twins_gate.Gate(snapshot if snapshot is not None else twins_gate.current_snapshot())
        box, info, calls = {}, {}, {"n": 0}
        rungs = 2

        def shape(o):
            calls["n"] += 1
            box["obj"] = o
            # the last rung fixes a bad headline itself; the first one tells the model exactly
            # what was wrong and gets the one repair
            box["r"] = clean(o, gate, final=calls["n"] >= rungs, top=top, info=info)
            return o
        try:
            client.call_json("morning", system, user, validate=shape, max_rungs=rungs)
        except llmlib.BudgetError:
            raise
        except llmlib.LLMError as e:
            # a headline-only failure on a rung count the ladder did not reach (a parse miss
            # on the first rung): the headline is fixed here, the sentences still must stand
            if "morning: the headline" in str(e) and "copy law" not in str(e) and box.get("obj"):
                box["r"] = clean(box["obj"], gate, final=True, top=top, info=info)
            else:
                raise
        head, sents, line = box["r"]
        b = client.budget
        tokens, usd = b.tokens, b.usd
        import narrative
        ln, by = narrative.edition_line(line, readings, items[:3], gate)
        gate.save()
        rec = {"date_et": date_et, "slot": "morning", "published_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "published_et": et_stamp(now), "headline": head, "headline_by": info.get("headline_by", "model"), "sentences": sents, "line": ln,
               "line_by": by, "tokens": tokens, "usd": round(usd, 4),
               "generated_by": "morning.py (one model call; copy law and twins gate)"}
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(rec, open(OUT, "w", encoding="utf-8"), indent=1)
        # the narrative line is the band's sentence too: store it with its readings
        try:
            narrative.write(narrative.record(ln, by, readings, items[:3],
                                             now.strftime("%Y-%m-%dT%H:%M:%SZ")))
        except Exception as e:
            print(f"morning: narrative.json not written ({e})")
        record(date_et, "read", tokens=tokens, usd=usd)
        print(f"morning: read written; {tokens} tokens, ${usd:.4f}")
        return rec
    except llmlib.BudgetError:
        raise
    except Exception as e:
        b = getattr(client, "budget", None)
        tokens, usd = (b.tokens, b.usd) if b else (0, 0.0)
        record(date_et, "fallback", reason=f"{type(e).__name__}: {e}", tokens=tokens, usd=usd)
        print(f"::warning::morning: fell back ({e}); the build goes out with fresh numbers and "
              f"the card says Last night's Brief")
        return None


def guard(event, now=None, path=None):
    """(serve, why). A dispatch serves unless today's read is already written; a backstop cron
    also stands down outside 8:00 to 11:00 AM Eastern (the Worker is the real trigger)."""
    now = (now or _dt.datetime.now(_dt.timezone.utc)).astimezone(ET)
    try:
        rows = json.load(open(path or LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    today = [r for r in rows if r.get("date") == now.date().isoformat()]
    if any(r.get("outcome") == "read" for r in today):
        return False, "today's morning read is already written"
    if event == "schedule" and today:
        # a backstop never retries a morning that already fell back: that would be a second build
        return False, "this morning already ran and fell back; a backstop does not buy a second build"
    if event == "schedule" and not 8 <= now.hour < 11:
        return False, f"a backstop cron at {now:%-I:%M %p} ET is outside 8 to 11 AM"
    return True, ""


def message(path=None, today=None):
    """The commit subject: names the read written today, or says it fell back."""
    today = today or _dt.datetime.now(_dt.timezone.utc).astimezone(ET).date().isoformat()
    try:
        rows = json.load(open(path or LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    row = next((r for r in rows if r.get("date") == today), None)
    if row and row.get("outcome") == "read":
        return f"read {today}, boards and wire refreshed"
    return f"fell back {today} (Last night's Brief stands), boards and wire refreshed"


def main():
    if "--guard" in sys.argv[1:]:
        serve, why = guard(os.environ.get("EV", "workflow_dispatch"))
        print(f"morning guard: {'serve' if serve else 'stand down: ' + why}")
        if os.environ.get("GITHUB_OUTPUT"):
            open(os.environ["GITHUB_OUTPUT"], "a").write(f"serve={'true' if serve else 'false'}\n")
        return 0
    if "--message" in sys.argv[1:]:
        print(message())
        return 0
    if "--alarm" in sys.argv[1:]:
        if second_fallback():
            print("::error::morning: the second morning in a row to fall back; "
                  "the morning read has not run for two days")
            return 1
        return 0
    try:
        run()
    except llmlib.BudgetError as e:
        print(f"::warning::morning: budget stop ({e}); falling back")
        record(_dt.datetime.now(_dt.timezone.utc).astimezone(ET).date().isoformat(), "fallback", str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
