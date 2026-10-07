#!/usr/bin/env python3
"""
narrative.py: the narrative line (program sections 3 and 8; Sprint 1b item 2).

One sentence of two clauses, in the serif's voice: which way the tape is drifting and on
what, and what kind of day the news is. It describes; it never predicts.

  THE EDITION (once a day): the Brief's own model call writes `narrative_line` from the
  Board's readings and the wire's top three, in the call the run already makes, so the line
  adds no model call. It is kept only if it is one sentence, carries no prediction, and
  passes the twins gate; otherwise the clause table below writes it. Either way it is
  stored with the readings it was written from (site/data/narrative.json, its own stamp).

  BETWEEN RUNS (`python3 narrative.py --refresh`, in the Netlify build): when a reading
  crosses a threshold since the line was written (a sign change on spot ETF net, Fear &
  Greed crossing a band, funding leaving calm), the build rewrites the line from the fixed
  clause table, never from a model, and records which crossing did it. No crossing leaves
  the line exactly as it is.

Nothing on the site renders the line yet; Sprint 2 draws the band. The build publishes
/data/narrative.json and the canary checks it exists.
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "site", "data", "narrative.json")

# FUNDING BANDS, per 8 hours, absolute value. PROPOSED 7 October 2026 for Jack's ruling: the
# Learn page says near-zero funding is calm and "tenths of a percent every 8 hours" is rich,
# and names no number between. 0.01% per 8h is the venues' own neutral rate. One table, so a
# ruling is a one-line change, and the Learn page prints these once Sprint 2 adds the anchor.
FUNDING_BANDS = ((0.010, "calm"), (0.030, "warm"), (float("inf"), "hot"))
# The tape's own dead band for "holding": under this 24-hour move either way.
FLAT_PCT = 0.5

_PREDICT = re.compile(r"\b(will|would|could|may|might|likely|expect\w*|forecast\w*|"
                      r"target\w*|poised|set to|on track|outlook|ahead of a)\b", re.I)


def funding_band(v):
    if not isinstance(v, (int, float)):
        return ""
    for top, word in FUNDING_BANDS:
        if abs(v) < top:
            return word
    return "hot"


def fng_band(v):
    if not isinstance(v, (int, float)):
        return ""
    from site_build import _fng_band
    return _fng_band(v)


def readings(snap):
    """The readings a line is written from, each named, from the snapshot at its stamp."""
    import snapshot as _s
    out = {"stamp_utc": (snap or {}).get("stamp_utc") or ""}
    b = _s.coin(snap, "BTC")
    if isinstance(b.get("chg_24h_pct"), (int, float)):
        out["btc_24h_pct"] = b["chg_24h_pct"]
    e = (_s.value(snap, "etf_flows") or {}).get("btc") or {}
    if isinstance(e.get("latest_net_usd_m"), (int, float)):
        out["etf_net_usd_m"] = e["latest_net_usd_m"]
        out["etf_date"] = e.get("latest_date")
    fg = _s.value(snap, "fear_greed") or {}
    if isinstance(fg.get("value"), (int, float)):
        out["fear_greed"] = fg["value"]
        out["fear_greed_band"] = fng_band(fg["value"])
    f = (_s.value(snap, "funding") or {}).get("BTC") or {}
    if isinstance(f.get("funding_8h_pct"), (int, float)):
        out["funding_8h_pct"] = f["funding_8h_pct"]
        out["funding_band"] = funding_band(f["funding_8h_pct"])
    return out


def named(r):
    """The band's small line: the readings the sentence was written from, by name."""
    bits = []
    if "btc_24h_pct" in r:
        bits.append(f"Bitcoin {r['btc_24h_pct']:+.2f}% on the day")
    if "etf_net_usd_m" in r:
        bits.append(f"spot ETF net {r['etf_net_usd_m']:+,.1f}M USD ({r.get('etf_date')})")
    if "fear_greed" in r:
        bits.append(f"Fear & Greed {r['fear_greed']:g} ({r.get('fear_greed_band', '').lower()})")
    if "funding_8h_pct" in r:
        bits.append(f"funding {r['funding_8h_pct']:+.4f}% per 8h ({r.get('funding_band')})")
    return "Written from " + ", ".join(bits) if bits else ""


# ---- the clause table --------------------------------------------------------------------

def _tape_clause(r, driver=None):
    p = r.get("btc_24h_pct")
    if not isinstance(p, (int, float)):
        head = "The tape has no Bitcoin reading"
    elif p >= FLAT_PCT:
        head = "Bitcoin is drifting higher"
    elif p <= -FLAT_PCT:
        head = "Bitcoin is drifting lower"
    else:
        head = "Bitcoin is holding flat"
    order = [driver] if driver else []
    order += [k for k in ("etf", "funding", "fear_greed") if k != driver]
    for k in order:
        if k == "etf" and isinstance(r.get("etf_net_usd_m"), (int, float)) and r["etf_net_usd_m"]:
            return head + (" on spot ETF inflows" if r["etf_net_usd_m"] > 0
                           else " on spot ETF outflows")
        if k == "funding" and r.get("funding_band"):
            if r["funding_8h_pct"] < 0 and r["funding_band"] != "calm":
                return head + " with funding below zero"
            return head + {"calm": " with funding calm", "warm": " with funding warming",
                           "hot": " with funding running hot"}[r["funding_band"]]
        if k == "fear_greed" and r.get("fear_greed_band"):
            return head + f" with sentiment in {r['fear_greed_band'].lower()}"
    return head


_NEWS_KIND = [("security", "security"), ("regulation", "regulation"), ("legal", "the courts"),
              ("etfs-funds", "funds and ETFs"), ("exchanges", "the exchanges"),
              ("stablecoins", "stablecoins"), ("macro", "the macro calendar"),
              ("markets", "the market itself"), ("bitcoin", "the market itself")]


def news_clause(wire_items):
    """What kind of day the news is, from the wire's top three by the tag rules."""
    top = (wire_items or [])[:3]
    if not top:
        return "the wire is quiet"
    from site_build import TAG_RULES
    words = dict(_NEWS_KIND)
    counts, first = {}, None
    for w in top:
        text = " ".join([w.get("line") or ""] + list(w.get("titles") or []))
        for tag, pat in TAG_RULES:
            if re.search(pat, text, re.I):
                counts[tag] = counts.get(tag, 0) + 1
                first = first or tag
                break
    for tag, word in _NEWS_KIND:
        if counts.get(tag, 0) >= 2:
            return f"the news is mostly {word}"
    # a mixed day is led by what the desk ranked first
    lead = words.get(first or "", "")
    return f"the news is mixed, led by {lead}" if lead else "the news is mixed"


def table_line(r, wire_items, driver=None):
    return f"{_tape_clause(r, driver)}; {news_clause(wire_items)}."


# ---- the Edition's line ------------------------------------------------------------------

def edition_line(model_line, r, wire_items, gate):
    """(line, by): the model's line when it is one sentence, predicts nothing and passes
    the twins gate; else the table's."""
    import twins_gate
    ln = " ".join(str(model_line or "").split())
    if ln:
        from site_build import destyle
        ln = destyle(ln)
        ok = (len(twins_gate.sentences(ln)) == 1 and not _PREDICT.search(ln)
              and len(ln) <= 220 and gate.text(ln, "the narrative line").strip() == ln.strip())
        if ok:
            return ln, "edition"
        print(f"narrative: the Edition's line did not hold ({ln[:120]!r}); the clause table "
              f"writes it")
    return table_line(r, wire_items), "table"


def record(line, by, r, wire_items, now_utc, crossed=None):
    return {"line": line, "by": by, "written_utc": now_utc, "written_et": _et(now_utc),
            "readings": r, "small_line": named(r),
            "wire_top3": [{"id": w.get("id"), "line": w.get("line")}
                          for w in (wire_items or [])[:3]],
            "crossed": crossed or []}


def _et(utc):
    try:
        from zoneinfo import ZoneInfo
        t = datetime.datetime.fromisoformat(str(utc).replace("Z", "+00:00"))
        return t.astimezone(ZoneInfo("America/New_York")).strftime("%-I:%M %p ET on %b %-d")
    except Exception:
        return ""


# ---- between runs ------------------------------------------------------------------------

def crossings(then, now):
    """The thresholds crossed between the readings a line was written from and now."""
    out = []
    a, b = then.get("etf_net_usd_m"), now.get("etf_net_usd_m")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a and b and \
            (a > 0) != (b > 0):
        out.append(("etf", f"spot ETF net changed sign, {a:+,.1f}M to {b:+,.1f}M USD"))
    fa, fb = then.get("fear_greed_band"), now.get("fear_greed_band")
    if fa and fb and fa != fb:
        out.append(("fear_greed", f"Fear & Greed crossed from {fa.lower()} into {fb.lower()} "
                                  f"({then.get('fear_greed')} to {now.get('fear_greed')})"))
    ua, ub = then.get("funding_band"), now.get("funding_band")
    if ua == "calm" and ub and ub != "calm":
        out.append(("funding", f"funding left calm, {then.get('funding_8h_pct'):+.4f}% to "
                               f"{now.get('funding_8h_pct'):+.4f}% per 8h"))
    return out


def refresh(rec, snap, wire_items, now_utc):
    """The stored line, rewritten from the table only when a threshold was crossed since
    it was written; otherwise the same object, untouched. Pure: no model, no network."""
    if not rec or not rec.get("line"):
        return rec, []
    now = readings(snap)
    crossed = crossings(rec.get("readings") or {}, now)
    if not crossed:
        return rec, []
    line = table_line(now, wire_items, driver=crossed[0][0])
    return record(line, "table", now, wire_items, now_utc,
                  crossed=[c[1] for c in crossed]), crossed


def load(path=None):
    try:
        return json.load(open(path or PATH, encoding="utf-8"))
    except Exception:
        return None


def write(rec, path=None):
    path = path or PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.write("\n")


def main():
    if "--refresh" not in sys.argv[1:]:
        print("usage: python3 narrative.py --refresh   (the Edition writes the line in wrap.py)")
        return 2
    rec = load()
    if not rec:
        print("narrative: no narrative.json to refresh; nothing changed")
        return 0
    import twins_gate
    import wire
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new, crossed = refresh(rec, twins_gate.current_snapshot(),
                           (wire.load() or {}).get("items") or [], now)
    if not crossed:
        print("narrative: no threshold crossed since the line was written; it stands")
        return 0
    write(new)
    print(f"narrative: rewritten from the clause table ({'; '.join(new['crossed'])}): "
          f"{new['line']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
