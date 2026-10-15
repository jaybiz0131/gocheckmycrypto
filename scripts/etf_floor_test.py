#!/usr/bin/env python3
"""Sprint 8.1 fix 4: the Edition's ETF floor, with tonight's real digest (14 October 2026) as the fixture.

The 7:08 PM Edition failed three times on the ETF window belt and published nothing. Here the model is
handed both ETF numbers with their windows, and when the ETF belt is the ONLY belt still failing after the
last repair, the ETF sentences are dropped (logged like a twins drop) and the Edition publishes. Any other
belt failure still fails the wrap. On origin/main there is no floor, so the same drafts fail the slot.

  python3 scripts/etf_floor_test.py
"""
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FX = json.load(open(os.path.join(HERE, "fixtures", "etf_floor", "tonight_2026-10-14.json"), encoding="utf-8"))


def check(cond, fails, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def draft(etf_sentences, extra=""):
    paras = list(FX["clean_paras"])
    body = "\n".join(paras[:2] + [" ".join(etf_sentences)] + paras[2:]) if etf_sentences else "\n".join(paras)
    return {"hook_title": "The Evening Brief: a quiet day on the wire", "dek": paras[0],
            "key_takeaway": "", "body": body + extra, "bottom_line": paras[-1]}


class Ladder:
    """What llm.Client.call_json does with validate: each rung's draft goes through it; the last
    failure is raised when every rung fails."""
    def __init__(self, drafts):
        self.drafts, self.calls = drafts, 0

    def call_json(self, stage, system, user, validate=None, max_rungs=3):
        last = None
        import llm
        for d in self.drafts:
            self.calls += 1
            try:
                return validate(copy.deepcopy(d))
            except llm.LLMError as e:
                last = e
        raise last


def run(drafts, boards=None):
    import llm
    import wrap
    boards = boards or FX["boards"]
    hold, status = {}, {"repairs": []}

    def belts_fn(o):
        return wrap.belts(str(o.get("body", "")), str(o.get("dek", "")), str(o.get("bottom_line", "")), boards)

    def validate(o):
        probs = belts_fn(o)
        if hasattr(wrap, "finish_shape"):
            return wrap.finish_shape(o, probs, hold)
        if probs:
            raise llm.LLMError("edition failed deterministic belts: " + "; ".join(probs))
        return o
    client = Ladder(drafts)
    if hasattr(wrap, "call_with_etf_floor"):
        out = wrap.call_with_etf_floor(client, "wrap", "", "", validate, hold, belts_fn, status)
    else:
        out = client.call_json("wrap", "", "", validate=validate)        # main: no floor
    return out, status, belts_fn


def main():
    import llm
    import twins_gate
    import wrap
    fails = []
    tmp = tempfile.mkdtemp(prefix="etf-floor-")
    twins_gate.LOG_PATH = os.path.join(tmp, "twins-gate.json")

    print("A. tonight's digest: three drafts fail the ETF belt, the Edition still publishes")
    w, wk, w3 = FX["etf_wrong"]
    drafts = [draft([w]), draft([wk]), draft([w3])]
    try:
        out, status, bf = run(drafts)
        ok = True
    except llm.LLMError as e:
        out, status, bf, ok = None, {"repairs": []}, None, False
        print("   raised:", str(e)[:160])
    check(ok, fails, "the Edition is published instead of failing the wrap")
    if ok:
        text = " ".join([out["body"], out["dek"], out["bottom_line"]])
        check("ETF" not in text and "etf" not in text.lower(), fails, "no sentence naming the ETFs is left")
        check(not bf(out) and len(out["body"].split()) >= 120, fails, "every belt passes on what is left, and the body is long enough")
        check(any("etf floor" in r for r in status["repairs"]), fails, "the repair is recorded in the wrap status")
        log = json.load(open(twins_gate.LOG_PATH, encoding="utf-8")) if os.path.exists(twins_gate.LOG_PATH) else {"drops": []}
        check(len(log["drops"]) >= 1 and "ETF" in log["drops"][0]["dropped"] and log["counts"]["wrong"] >= 1, fails,
              "each dropped sentence is logged in the twins gate's file and counted")

    print("B. any other belt failure still fails the wrap")
    bad = draft([w], extra="\nThe desk's view is that you should buy the dip in Bitcoin now.")
    try:
        run([bad, bad, bad])
        check(False, fails, "an advice-lint failure beside the ETF one raises")
    except llm.LLMError:
        check(True, fails, "an advice-lint failure beside the ETF one raises")

    print("C. a correct ETF sentence is never touched")
    good = draft(["Bitcoin spot ETF flows were a net outflow over the week and a small inflow on the day, per Farside."])
    out, status, bf = run([good])
    check("ETF" in out["body"] and not status["repairs"], fails, "a sentence that names both windows stands, no drop, no repair")

    print("D. too little left after the drop fails closed")
    allp = {"hook_title": "x", "dek": "ETF flows were negative on the day.", "key_takeaway": "",
            "body": " ".join([w] * 40), "bottom_line": w}
    try:
        run([allp, allp, allp])
        check(False, fails, "an Edition that is all ETF sentences does not publish")
    except llm.LLMError:
        check(True, fails, "an Edition that is all ETF sentences does not publish")

    print("E. the model is handed both numbers with their windows")
    note = wrap.etf_window_note(FX["boards"]) if hasattr(wrap, "etf_window_note") else ""
    check("on the day" in note and "+$2.2M" in note and "14 Oct 2026" in note
          and "over the week" in note and "-$110.5M" in note and "disagree" in note, fails,
          "the note carries '+$2.2M' on the day, '-$110.5M' over the week, the date and the sign warning")
    check(wrap.etf_window_note({}) == "", fails, "no ETF read, no note") if hasattr(wrap, "etf_window_note") else check(False, fails, "etf_window_note exists")
    print("\nETF FLOOR:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
