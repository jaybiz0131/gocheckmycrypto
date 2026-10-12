#!/usr/bin/env python3
"""The Chart Master's three refusals (9, 10, 11 October 2026) run through the stage.

Each fixture is fed to the live path as if the model returned it on every attempt, which
is what the model did on the real nights. Prints the outcome per fixture and the published
text. On main every night refuses; on the branch every night publishes.

  python3 scripts/chartmaster_publish_test.py          # exit 0 only if all three publish
  python3 scripts/chartmaster_publish_test.py --report # print, always exit 0
"""
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def run_night(day):
    import chartmaster as cm
    import llm
    fx = json.load(open(os.path.join(HERE, "fixtures", "chartmaster", f"{day}.json")))
    rec = {n: json.load(open(os.path.join(HERE, "fixtures", f"recorded_{n}_d6ec0f4.json")))
           for n in ("pulse", "flows")}
    tmp = tempfile.mkdtemp(prefix="cm-fx-")
    saved = (cm._load, llm.Client._live_raw, cm.STATUS, cm.SITE_DATA, os.environ.get("CRYPTO_LLM_MODE"),
             getattr(cm, "LEDGER", None))
    calls = []
    cm._load = lambda n: rec.get(n.split(".")[0], {})
    cm.STATUS = os.path.join(tmp, "status.json")
    cm.SITE_DATA = os.path.join(tmp, "chartmaster.json")
    if saved[5]:
        cm.LEDGER = os.path.join(tmp, "ledger.json")

    def fake(self, stage, mc, system, user, retried_empty=False):
        calls.append(mc.get("model"))
        return json.dumps({"headline": fx["headline"], "paragraphs": fx["paragraphs"]})
    llm.Client._live_raw = fake
    os.environ["CRYPTO_LLM_MODE"] = "live"
    os.environ.setdefault("ANTHROPIC_API_KEY", "test")
    cap = io.StringIO()
    code = None
    try:
        with contextlib.redirect_stdout(cap):
            try:
                cm.main()
            except SystemExit as e:
                code = e.code
        st = json.load(open(cm.STATUS))
        site = json.load(open(cm.SITE_DATA)) if os.path.exists(cm.SITE_DATA) else None
        led = json.load(open(cm.LEDGER)) if saved[5] and os.path.exists(cm.LEDGER) else None
    finally:
        cm._load, llm.Client._live_raw, cm.STATUS, cm.SITE_DATA = saved[:4]
        if saved[5]:
            cm.LEDGER = saved[5]
        if saved[4] is None:
            os.environ.pop("CRYPTO_LLM_MODE", None)
        else:
            os.environ["CRYPTO_LLM_MODE"] = saved[4]
    return {"day": day, "exit": code, "published": bool(st.get("published")), "reason": st.get("reason"),
            "calls": len(calls), "site": site, "ledger": led and led[-1]}


def flagged(site):
    import chartmaster as cm
    t = (site.get("headline", "") + " " + " ".join(site.get("paragraphs") or []))
    return cm.banned_hits(t) if hasattr(cm, "banned_hits") else cm.BANNED.findall(t)


def main():
    ok = True
    for day in ("2026-10-09", "2026-10-10", "2026-10-11"):
        r = run_night(day)
        pub = r["published"] and r["site"] is not None
        ok &= pub and not flagged(r["site"] or {})
        print(f"\n== {day}: {'PUBLISHED' if pub else 'REFUSED'}  path={(r['site'] or {}).get('path', '-')}"
              f"  model calls={r['calls']}  reason={r['reason']!r}")
        if pub:
            s = r["site"]
            print("   ledger:", json.dumps(r["ledger"]))
            print("   headline:", s["headline"])
            for p in s.get("paragraphs") or []:
                print("   -", p)
            if s.get("data_only"):
                for lv in s["levels"]:
                    print("   level:", lv)
    print("\nRESULT:", "all three published" if ok else "at least one refused")
    return 0 if ok or "--report" in sys.argv else 1


if __name__ == "__main__":
    sys.exit(main())
