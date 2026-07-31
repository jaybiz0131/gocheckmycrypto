#!/usr/bin/env python3
"""
chartmaster.py: the Chart Master's read, regenerated from the live boards.

The resident technician's plain-language analysis of the day's tape. Reads the two data
desks the site already publishes (site/data/pulse.json and site/data/flows.json), digests
them into one factual document, and asks the model to read it like a professional market
technician: regime, momentum, positioning, flows, sentiment, and what to watch. The house
rule is enforced twice (prompt and a deterministic output belt): DESCRIBE the tape, never
predict it, never advise.

MARKET COMMENTARY, NOT NEWS: like Whale Watch and Market Pulse it does not pass the
editorial gate, and like them it is FAIL-OPEN: any failure (missing key, network, refusal,
a read that trips the no-advice belt) keeps the previous committed read rather than
breaking the brief. A replay run writes only the out/ test artifact, never site data.

USAGE
  python3 chartmaster.py                       # live: needs ANTHROPIC_API_KEY
  CRYPTO_LLM_MODE=replay python3 chartmaster.py  # offline wiring test (out/ only)

Wired into crypto-news-brief.yml after the data-desk refresh, so each brief ships a read
of the same boards the site deploys. Cost: one call, cents per day.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import common
import llm as llmlib

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DATA = os.path.join(HERE, "site", "data", "chartmaster.json")


def _load(name):
    try:
        return json.load(open(os.path.join(HERE, "site", "data", name), encoding="utf-8"))
    except Exception:
        return {}


def _etf_digest(v):
    """Latest day PLUS multi-day context. Shipping only the latest daily print taught the
    model to call two negative days a regime ('outflows persist') inside a net-inflow week
    (homepage contradiction, audit 2026-07-26). The model now sees both grains and cannot
    honestly collapse them."""
    v = v or {}
    rec = v.get("recent") or []

    def _sign(x):
        return (x > 0) - (x < 0)

    streak = 0
    if rec:
        s = _sign(rec[-1].get("net_usd_m") or 0)
        while streak < len(rec) and s != 0 and \
                _sign(rec[-1 - streak].get("net_usd_m") or 0) == s:
            streak += 1
    return {"latest_date": v.get("latest_date"),
            "latest_net_usd_m": v.get("latest_net_usd_m"),
            "last5_sessions_net_usd_m": round(sum((r.get("net_usd_m") or 0)
                                                  for r in rec[-5:]), 1),
            "same_direction_days": streak,
            "cumulative_usd_m": v.get("cumulative_usd_m")}


def _window_changes(a):
    """Percent change at the week and month windows, derived from the daily spark series.

    The digest used to ship chg_24h_pct and nothing else per window, while the prompt asks
    for regime and momentum, which are week-and-month ideas. The model was being asked to
    describe windows it had no number for, and inferring them from spark_high/spark_low.
    That is a standing invitation to write an unscoped or mis-scoped direction claim, which
    is precisely what the consistency gate blocks the publish over.

    So this is half of the whale/ETF fix rather than a separate feature: the belts catch a
    bad window claim, and these numbers remove the reason to make one. They also give the
    price belt something to check against."""
    out = {}
    s = [v for v in (a.get("spark") or []) if isinstance(v, (int, float))]
    for key, back in (("chg_7d_pct", 7), ("chg_30d_pct", 30)):
        if len(s) > back and s[-1 - back]:
            out[key] = round((s[-1] - s[-1 - back]) / s[-1 - back] * 100, 2)
    return out


def digest():
    """One compact, factual document: every number the boards publish, nothing else.
    This is the model's entire world, so completeness here IS the quality of the read."""
    pulse = _load("pulse.json")
    flows = _load("flows.json")
    if not pulse.get("assets"):
        raise ValueError("no pulse snapshot (site/data/pulse.json); run market_pulse.py first")

    fng = pulse.get("fng") or {}
    hist30 = (fng.get("history") or [])[-30:]
    d = {
        "data_date": pulse.get("generated") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fear_greed": {"value": fng.get("value"), "label": fng.get("label"),
                       "range_30d": [min(hist30), max(hist30)] if hist30 else None},
        "assets": [dict({k: a.get(k) for k in
                         ("symbol", "price", "chg_24h_pct", "rsi14", "macd_above_signal",
                          "above_sma200", "golden_cross", "pct_from_high_12m",
                          # high_12m_usd travels WITH pct_from_high_12m, always. spark_high
                          # is the 90-day high; pairing it with the 12-month percentage is
                          # the mistake the 2026-07-28 edition made. See market_pulse.py.
                          "high_12m_usd", "vol30_pct",
                          "spark_high", "spark_low")}, **_window_changes(a))
                   for a in pulse.get("assets", [])],
        "leverage": [{k: a.get(k) for k in
                      ("symbol", "venue", "funding_8h_pct", "funding_annual_pct",
                       "open_interest_usd", "long_short_ratio", "liquidations")}
                     for a in (pulse.get("leverage") or {}).get("assets") or []],
        "market": pulse.get("market"),
        "etf_flows": {k: _etf_digest(v)
                      for k, v in (pulse.get("etf_flows") or {}).items()
                      if k in ("btc", "eth")} or None,
        "stablecoins": {k: (pulse.get("stables") or {}).get(k)
                        for k in ("total_usd", "change_30d_pct")},
        "network": pulse.get("network"),
        "movers": {side: [{k: m.get(k) for k in ("symbol", "chg_24h_pct")}
                          for m in (pulse.get("movers") or {}).get(side, [])[:3]]
                   for side in ("gainers", "losers")},
    }
    if flows.get("volatile"):
        vol = flows["volatile"]
        d["whale_flows"] = {
            "window_hours": flows.get("window_hours"),
            "volatile_net_usd": vol.get("net_usd"),
            "direction": vol.get("direction"),
            # THE SIGN CONVENTION, STATED. It was not, and it cost the desk the daily
            # edition: the trace check read volatile_net_usd of -112,735,021 next to
            # direction "onto exchanges", assumed net meant inflow minus outflow, computed
            # +112.8M from the same board's own asset rows, and killed the edition as
            # internally contradictory. The board was right; nothing told the reader which
            # way the sign ran. A signed number whose convention is implicit is a number
            # every consumer has to guess at, and one of them guessed wrong every slot for
            # three days while the workflow swallowed the failure.
            #
            # net_plain is the belt-and-braces version: an unambiguous English sentence, so
            # a consumer never has to do sign arithmetic to say what happened at all.
            "net_convention": "volatile_net_usd = outflow_usd - inflow_usd. POSITIVE means "
                              "net value LEAVING exchanges; NEGATIVE means net value moving "
                              "ONTO exchanges. The 'direction' field states the same thing "
                              "in words and is authoritative.",
            "net_plain": _net_plain(vol.get("net_usd"), vol.get("direction")),
            "stablecoin_buying_power_usd": (flows.get("stablecoins") or {}).get("net_buying_power_usd"),
            # Same treatment per asset row: the trace check also tried to reconcile
            # these against the aggregate and reported a "magnitude mismatch".
            "by_asset": [dict(a, net_plain=_net_plain(
                a.get("net_usd"),
                "off exchanges" if (a.get("net_usd") or 0) >= 0 else "onto exchanges"))
                for a in (flows.get("by_asset") or [])],
            "biggest_onto_exchanges": [{k: m.get(k) for k in ("symbol", "usd", "to")}
                                       for m in flows.get("top_inflows", [])[:3]],
            "biggest_off_exchanges": [{k: m.get(k) for k in ("symbol", "usd", "from")}
                                      for m in flows.get("top_outflows", [])[:3]],
            "weekly_net_usd_recent": [w.get("net_usd") for w in (flows.get("history") or [])[-4:]],
        }
    return d



def _net_plain(net, direction):
    """One unambiguous sentence for the net whale flow, magnitude and direction together.

    Deliberately drops the sign rather than reporting it. The magnitude and the direction
    are the two facts; the sign is an encoding of the direction, and carrying both invites a
    consumer to reconcile them and get it wrong. That is exactly what happened."""
    try:
        mag = abs(float(net or 0))
    except (TypeError, ValueError):
        return ""
    return f"${mag:,.0f} net moving {direction or 'unknown direction'}"


# The no-advice/no-prediction belt: deterministic, runs on whatever the model returns.
# The prompt already forbids these; the belt makes the rule survivable under model drift.
BANNED = re.compile(
    r"\b(you should|buy now|sell now|time to (buy|sell)|price target|take profits?|"
    r"load up|going to (rise|fall|pump|dump|moon)|will (rise|fall|hit|reach|break)|"
    r"expect(ed)? to (rise|fall|hit|reach)|likely to (rise|fall)|guaranteed)\b", re.I)


def _dedash(s):
    # House style: no em/en dashes. Same substitutions as destyle() in site_build.py,
    # applied here too so the committed read is clean even before the renderer runs.
    return s.replace(" — ", ", ").replace("—", ", ").replace("–", "-")


def _sign(x):
    return (x > 0) - (x < 0)


def etf_flow_problems(text, etf, who="chartmaster"):
    """Deterministic honesty check on ETF flow direction claims, against the same digest
    the model was handed. Returns a list of problems; empty means the text is honest about
    which window it is describing.

    The prompt's window rule did not survive model drift (runs 55-56 wrote a week-negative
    claim over a positive five-session net, and the consistency gate rightly blocked the
    whole publish); this belt makes the rule hold. Claims are read with the consistency
    gate's own lexicon so the desk has exactly one definition of "a direction claim at a
    window".

    SHARED ON PURPOSE. This lived only on the Chart Master until the 2026-07-28 edition
    made the identical mistake in prose ("third straight weekly inflow" beside "$402.6
    million in net outflows" over five sessions) and only the slower, model-based trace
    check caught it. Two surfaces reading the same numbers need the same belt, so wrap.py
    calls this too. Do not fork it."""
    import consistency_gate as cg
    problems = []
    m = cg.METRICS["spot ETF flows"]
    btc = (etf or {}).get("btc") or {}
    signs = {"day": _sign(btc.get("latest_net_usd_m") or 0),
             "week": _sign(btc.get("last5_sessions_net_usd_m") or 0)}
    want = {1: "pos", -1: "neg"}
    for scope, dirs in cg.directions(text, m).items():
        if len(dirs) != 1:
            continue  # dual-grain phrasing names both directions; nothing to contradict
        d = next(iter(dirs))
        if scope in signs:
            if signs[scope] and d != want[signs[scope]]:
                problems.append(
                    f"{who}: ETF flow claim says {d} at the {scope} window but the "
                    f"digest's {scope} number points the other way; state what the data "
                    f"says")
        else:
            ok = {want[s] for s in signs.values() if s}
            if ok and (len(ok) > 1 or d not in ok):
                problems.append(
                    f"{who}: unscoped ETF flow direction while the daily and "
                    "five-session numbers disagree; name the window")
    return problems


def _etf_flow_belt(text, etf):
    """Raising wrapper, so the Chart Master's retry ladder keeps its existing behaviour:
    a violation raises, the ladder gets another attempt, and if the model never phrases it
    honestly the previous read stands (fail-open in main)."""
    for p in etf_flow_problems(text, etf):
        raise llmlib.LLMError(p)


# The whale board states its direction as prose, so map it onto the gate's own lexicon
# rather than inventing a second vocabulary for the same idea.
_BOARD_DIRECTION = {"onto exchanges": "neg", "off exchanges": "pos"}


def whale_flow_problems(text, whale, who="chartmaster"):
    """The same belt as ETF flows, for whale exchange flows. Returns a list of problems.

    WHY THIS EXISTS. ETF flows got a window belt because model drift kept writing a
    direction claim without naming the window, and the consistency gate then, correctly,
    blocked the whole publish. Whale flows had the identical exposure and no belt, so the
    identical thing happened on run 30577704932 (2026-07-30 20:06Z): the Chart Master
    wrote an unscoped whale direction while the board reported the opposite over 24 hours,
    the gate fired, and the run's verified stories went nowhere.

    The difference between the two failures is only where they were caught. An unbelted
    violation reaches the gate, which has no retry and is the last step before publishing,
    so one loose sentence discards a whole run. A belted violation raises inside the retry
    ladder, the model gets another attempt, and if it never complies the previous read
    stands and the stories still publish. Same rule, survivable failure.

    Only DISAGREEMENT is a problem. An unscoped claim that happens to match the board
    cannot collide (the gate compares directions before windows), so flagging it would
    burn retries on prose that was never going to fail. This mirrors the ETF belt, which
    likewise only flags an unscoped claim when the numbers behind it disagree."""
    import consistency_gate as cg
    problems = []
    board = _BOARD_DIRECTION.get(str((whale or {}).get("direction") or "").strip().lower())
    if not board:
        return problems
    hours = (whale or {}).get("window_hours") or 24
    board_scope = "day" if hours <= 24 else "multiday"
    said = str(whale.get("direction")).strip().lower()
    window_text = ("the last 24 hours" if hours <= 24
                   else f"the last {round(hours / 24)} days")
    for scope, dirs in cg.directions(text, cg.METRICS["whale exchange flows"]).items():
        if len(dirs) != 1:
            continue  # dual-grain phrasing names both directions; nothing to contradict
        if next(iter(dirs)) == board:
            continue
        if scope == "":
            problems.append(
                f"{who}: unscoped whale flow direction while the board reports {said} "
                f"over {window_text}; name the window or state what the board says")
        elif scope == board_scope:
            problems.append(
                f"{who}: whale flow claim contradicts the board, which reports {said} "
                f"over {window_text}; state what the data says")
    return problems


def _whale_flow_belt(text, whale):
    """Raising wrapper, same contract as _etf_flow_belt."""
    for p in whale_flow_problems(text, whale):
        raise llmlib.LLMError(p)


def price_problems(text, assets, who="chartmaster"):
    """Window belt for bitcoin price direction, the third of the gate's four metrics.

    Added by audit rather than after another lost run. The gate can block a publish on any
    of its metrics, and after whale flows two were still unbelted. This one is the higher
    risk of the two by a distance: the Chart Master writes about bitcoin's direction in
    essentially every read, and "bitcoin fell" beside "bitcoin rallied" at two different
    windows is the exact shape that has now cost three publishes on other metrics.

    Windows come from _window_changes plus the 24-hour print, so the belt checks the same
    numbers the model was handed. A window with no number is not judged: silence beats a
    guess in something that can block publishing."""
    import consistency_gate as cg
    problems = []
    btc = next((a for a in (assets or []) if str(a.get("symbol", "")).upper() == "BTC"), None)
    if not btc:
        return problems
    signs = {}
    for scope, key in (("day", "chg_24h_pct"), ("week", "chg_7d_pct"), ("month", "chg_30d_pct")):
        v = btc.get(key)
        if isinstance(v, (int, float)):
            signs[scope] = _sign(v)
    if not signs:
        return problems
    want = {1: "pos", -1: "neg"}
    for scope, dirs in cg.directions(text, cg.METRICS["bitcoin price"]).items():
        if len(dirs) != 1:
            continue  # dual-grain phrasing names both directions; nothing to contradict
        d = next(iter(dirs))
        if scope in signs:
            if signs[scope] and d != want[signs[scope]]:
                problems.append(
                    f"{who}: bitcoin price claim says {d} at the {scope} window but the "
                    f"digest's {scope} number ({btc.get({'day': 'chg_24h_pct', 'week': 'chg_7d_pct', 'month': 'chg_30d_pct'}[scope])}%) "
                    f"points the other way; state what the data says")
        elif scope == "":
            ok = {want[s] for s in signs.values() if s}
            if ok and (len(ok) > 1 or d not in ok):
                named = ", ".join(f"{k} {btc.get({'day': 'chg_24h_pct', 'week': 'chg_7d_pct', 'month': 'chg_30d_pct'}[k])}%"
                                  for k in ("day", "week", "month") if k in signs)
                problems.append(
                    f"{who}: unscoped bitcoin price direction while the windows disagree "
                    f"({named}); name the window")
    return problems


def _price_belt(text, assets):
    """Raising wrapper, same contract as the other two."""
    for p in price_problems(text, assets):
        raise llmlib.LLMError(p)


# Bitcoin dominance is the gate's fourth metric and is deliberately UNBELTED, because
# pulse.json publishes btc_dominance_pct as a single live reading with no history, so there
# is no week or month number to check a direction claim against. A belt that guessed would
# be worse than none: it would raise inside the retry ladder on claims that may be true.
#
# It is also the lowest-risk of the four. The whale board and the ETF digest each assert a
# direction of their own, so those metrics collide chart-master against a live board every
# run; nothing on the page asserts a dominance direction except prose, so a collision needs
# a story and the Chart Master to disagree, which is rare.
#
# To belt it, market_pulse.py would need to keep a dominance history the way it already
# keeps 90 days of fear-and-greed. The canary below asserts this exemption stays explicit,
# so adding history without adding the belt cannot pass silently.
UNBELTED_METRICS = {"bitcoin dominance": "pulse.json carries no dominance history"}


def validate(obj, etf=None, whale=None, assets=None):
    if not isinstance(obj, dict):
        raise llmlib.LLMError("chartmaster: output is not an object")
    headline = _dedash((obj.get("headline") or "").strip())
    paras = [_dedash(p.strip()) for p in obj.get("paragraphs") or []
             if isinstance(p, str) and p.strip()]
    if not headline or len(headline) > 160:
        raise llmlib.LLMError("chartmaster: missing/oversized headline")
    if not 3 <= len(paras) <= 7:
        raise llmlib.LLMError(f"chartmaster: expected 3-7 paragraphs, got {len(paras)}")
    text = headline + " " + " ".join(paras)
    hit = BANNED.search(text)
    if hit:
        raise llmlib.LLMError(f"chartmaster: advice/prediction language in the read ({hit.group(0)!r}); "
                              "refusing to publish it")
    if etf:
        _etf_flow_belt(text.lower(), etf)
    if whale:
        _whale_flow_belt(text.lower(), whale)
    if assets:
        _price_belt(text.lower(), assets)
    return {"headline": headline, "paragraphs": paras}


def run():
    cfg = common.load_config()
    data = digest()
    client = llmlib.Client(cfg)
    system = common.load_prompt("chartmaster.md")
    user = ("Read today's tape and write the Chart Master's read.\n\n"
            + json.dumps(data, indent=1))
    obj = client.call_json("chartmaster", system, user,
                           validate=lambda o: validate(o, data.get("etf_flows"),
                                                       data.get("whale_flows"),
                                                       data.get("assets")))
    out = {
        "date": data["data_date"],
        "headline": obj["headline"],
        "paragraphs": obj["paragraphs"],
        "generated_by": "chartmaster.py (auto, from the live boards)",
        "mode": client.mode,
    }
    common.write_out("chartmaster.json", out)
    if client.mode == "replay":
        print("chartmaster [REPLAY]: wiring test only -> out/chartmaster.json (site data untouched)")
        return 0
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    json.dump(out, open(SITE_DATA, "w", encoding="utf-8"), indent=2)
    print(f"chartmaster: \"{obj['headline']}\" ({len(obj['paragraphs'])} paragraphs) "
          f"-> {os.path.relpath(SITE_DATA)}")
    return 0


def main():
    try:
        sys.exit(run())
    except Exception as e:
        # Fail-open: commentary must never break the brief. The previous read stands.
        common.gh("warning", f"chartmaster: read not refreshed ({e}) -> previous read stands.")
        sys.exit(0)


if __name__ == "__main__":
    main()
