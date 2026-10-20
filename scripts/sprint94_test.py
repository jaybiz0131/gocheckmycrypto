#!/usr/bin/env python3
"""Program 9, Sprint 9.4: Big movers, checked. Each case is named after what it guards.

  python3 scripts/sprint94_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() on the tree)

THE RECORDS ARE REAL (fixtures/movers/README.txt):
  - the Board the morning read published at 2026-10-16T12:16:53Z (site/data/pulse.json at 9c8af54), the
    wire of that commit, and CoinGecko's 365-day answers for every top-100 coin past 10% in it, read
    October 19 (aptos answered 429 five times, so the fixture holds no closes for it); the movers step's
    source answers for that Board's window, recorded by `movers.py --record`;
  - a Board read October 19 at 20:30Z by market_pulse's own section_movers, with the 365-day answers for
    its two coins past 10% (neither passes the gate);
  - the watcher's two reads (Bitcoin's day chart, the Top 100 markets) recorded October 19.
Bitcoin's stored closes are data/history/bitcoin.json as committed. Cases marked SYNTHETIC change a real
record by hand to reach a rule the real days do not, and say so (Jack, 13 October 2026). NO LIVE MODEL
CALL: the API is mocked at the HTTP layer (llm.urllib.request.urlopen), as in Sprint 9.3's tests.
"""
import contextlib
import copy
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
FX = os.path.join(HERE, "fixtures", "movers")
GRADE = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b")
UTC = dt.timezone.utc


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def group(fails, name, fn):
    try:
        fn(fails)
    except Exception as e:                                   # noqa: BLE001
        msg = f"group {name} could not run [{type(e).__name__}: {str(e)[:100]}]"
        print("  FAIL " + msg)
        fails.append(msg)


def s93():
    import sprint93_test
    return sprint93_test


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


BOARD16 = "pulse_2026-10-16T1216Z.json"
WIRE16 = "wire_2026-10-16T1216Z.json"
HIST16 = "history_answers_recorded_2026-10-19.json"
SRC16 = "sources_2026-10-16T1216Z.json"
BOARD19 = "board_raw.json"
DAY16 = "2026-10-16"
BEFORE16 = "2026-10-15"          # the window's Eastern day: it starts 2026-10-15 08:16 AM ET


def hist_root(td, answers):
    import movers
    d = os.path.join(td, "history")
    os.makedirs(d, exist_ok=True)
    return movers._history_root(answers, d)


def gate16(td, used=0, now=None):
    import movers
    return movers.gate(load(BOARD16), BEFORE16, hist_root(td, load(HIST16)), used,
                       now=now or dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))


def replay16():
    import why_evidence as we
    f = load(SRC16)
    return we.Replay(f["responses"]), f["recorded_utc"]


def record16(td, used=0):
    """The movers record for 16 October's morning Board, built from the recorded answers (no network)."""
    import movers
    fetch, rec_utc = replay16()
    log = []
    r = movers.build(load(BOARD16), load(WIRE16), BEFORE16, used_today=used, fetch=fetch, now_utc=rec_utc,
                     history_root=hist_root(td, load(HIST16)), log=log, cg_spacing=0)
    r.update(date_et=DAY16, slot="morning")
    return r, log


@contextlib.contextmanager
def mocked_api(api=None):
    t = s93()
    api = api or t.MockAPI(draft=t.copy_two, check=t.stands_all)
    with t.mocked(api):
        yield api


def graded16(td, ledger=None, cap=None, slot="morning", used=0, rec=None):
    import movers
    r = rec or record16(td, used)[0]
    r.update(slot=slot)
    out = io.StringIO()
    with mocked_api(), contextlib.redirect_stdout(out):
        movers.verdicts(r, DAY16, slot, ledger_path=ledger or os.path.join(td, "ledger.json"), cap=cap,
                        now=dt.datetime(2026, 10, 16, 12, 40, tzinfo=UTC))
    return r


# ---- 1. the gate -------------------------------------------------------------------------------------------

def gate_cases(fails):
    import movers
    import snapshot
    print("1. the gate, from the real 16 October Board and the stored closes")
    with tempfile.TemporaryDirectory() as td:
        g = gate16(td)
        passed = [x["sym"] for x in g["passed"]]
        guarded(fails, f"16 October: TIA, INJ, ZRO, ETHFI and PENDLE pass, ranked by their volatility multiple "
                       f"({passed})", lambda: passed == ["TIA", "INJ", "ZRO", "ETHFI", "PENDLE"])
        tia = next(x for x in g["passed"] if x["sym"] == "TIA")
        guarded(fails, "TIA's three legs: +30.60%, 3.67x its 30-day daily volatility of 8.33%, +28.15 points beyond "
                       "its Bitcoin beta of 1.653 with Bitcoin +1.48%",
                lambda: (tia["move_pct"], tia["multiple"], tia["vol_pct"], tia["excess_pts"], tia["beta"],
                         tia["btc_pct"]) == (30.6, 3.67, 8.33, 28.15, 1.653, 1.48))
        failed = {x["sym"]: x for x in g["failed"]}
        guarded(fails, "ARB, APT, WLD, NEAR, ZEC, FIL and SEI fail on the volatility leg alone (they moved 10% or more "
                       "and 6 points beyond their beta, under 2.5 times their usual day)",
                lambda: set(failed) == {"ARB", "APT", "WLD", "NEAR", "ZEC", "FIL", "SEI"} and all(
                    x["legs"] == {"move": True, "multiple": False, "excess": True} for x in failed.values()))
        os.rename(os.path.join(td, "history", "aptos.json"), os.path.join(td, "aptos.hold"))
        gl = movers.gate(load(BOARD16), BEFORE16, os.path.join(td, "history"), 0,
                         now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        os.rename(os.path.join(td, "aptos.hold"), os.path.join(td, "history", "aptos.json"))
        guarded(fails, "SYNTHETIC (APT's stored closes removed): APT +14.03% is left out and said, never estimated",
                lambda: [(x["sym"], x["move_pct"]) for x in gl["left_out"]] == [("APT", 14.03)]
                and "no stored daily closes" in gl["left_out"][0]["why"] and not g["left_out"])
        guarded(fails, "the beta the gate uses is the one the section prints (why_evidence._beta on the same days)",
                lambda: __import__("why_evidence")._beta("TIA", BEFORE16, root=os.path.join(td, "history"))
                == tia["beta"] if __import__("why_evidence").register_coin("TIA", "celestia", "Celestia") else False)
        rows = load(BOARD16)["movers"]["top100"]
        stables = [r["symbol"] for r in rows if snapshot.is_stablecoin(r)]
        every = {x["sym"] for k in ("passed", "over_cap", "failed", "left_out") for x in g[k]}
        guarded(fails, f"no stablecoin ({len(stables)} on the Board) is ever measured",
                lambda: stables and not (every & set(stables)))
        guarded(fails, "Bitcoin and Ether are never measured here: their own cards grade them",
                lambda: not (every & {"BTC", "ETH"}))
        guarded(fails, "the line is the audit's, held once: 10%, 2.5x, 6 points, 30 days, 8 a slot, 10 a day",
                lambda: (movers.GATE["move_min_pct"], movers.GATE["vol_multiple_min"], movers.GATE["excess_min_pts"],
                         movers.GATE["history_days"], movers.GATE["per_slot"], movers.GATE["per_day"])
                == (10.0, 2.5, 6.0, 30, 8, 10))
        g8 = gate16(td, used=8)
        guarded(fails, "the day's cap: with 8 reads made earlier today, 2 pass and 3 wait over the cap",
                lambda: [x["sym"] for x in g8["passed"]] == ["TIA", "INJ"]
                and [x["sym"] for x in g8["over_cap"]] == ["ZRO", "ETHFI", "PENDLE"])
        g10 = gate16(td, used=10)
        guarded(fails, "the day's cap: at 10 reads, none passes and all five are named over the cap",
                lambda: not g10["passed"] and len(g10["over_cap"]) == 5)
        # SYNTHETIC: twelve coins past every leg, made by copying the real TIA row under twelve names, placed after
        # Bitcoin, so twelve real rows fall past the 100th place (PENDLE among them)
        b = copy.deepcopy(load(BOARD16))
        tia_row = next(r for r in b["movers"]["top100"] if r["symbol"] == "TIA")
        hdir = os.path.join(td, "history")
        src = json.load(open(os.path.join(hdir, "celestia.json")))
        for i in range(12):
            b["movers"]["top100"].insert(1, dict(tia_row, symbol=f"SYN{i}", name=f"Synthetic {i}", gecko_id=f"syn-{i}",
                                                 rank=2))
            json.dump(dict(src, coin=f"syn-{i}"), open(os.path.join(hdir, f"syn-{i}.json"), "w"))
        gs = movers.gate(b, BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        guarded(fails, "SYNTHETIC (sixteen coins past the line): at most 8 a slot, the rest over the cap",
                lambda: len(gs["passed"]) == 8 and len(gs["over_cap"]) == 8)
        log = "\n".join(g["log"])
        guarded(fails, "for two weeks every coin that fails the gate prints in the run log with its figures",
                lambda: all(re.search(rf"gate fail {s} \+\d+\.\d\d%: \d\.\d\dx its 30-day daily volatility", log)
                            for s in ("ARB", "APT", "WLD", "NEAR", "ZEC", "FIL", "SEI")))
        late = gate16(td, now=dt.datetime(2026, 11, 3, 12, 30, tzinfo=UTC))
        guarded(fails, "after November 2 the failing coins are counted, not listed",
                lambda: not any("gate fail" in l for l in late["log"]) and any("7 coin(s) passed one leg" in l
                                                                              for l in late["log"]))
        # SYNTHETIC: a gap in TIA's stored closes
        s2 = json.load(open(os.path.join(hdir, "celestia.json")))
        del s2["closes"]["2026-10-01"]
        json.dump(s2, open(os.path.join(hdir, "celestia.json"), "w"))
        gg = movers.gate(load(BOARD16), BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        guarded(fails, "SYNTHETIC (one stored close removed): a gap leaves the coin out and says so, never fills it",
                lambda: any(x["sym"] == "TIA" and "gap" in x["why"] for x in gg["left_out"])
                and "TIA" not in [x["sym"] for x in gg["passed"]])
    with tempfile.TemporaryDirectory() as td:
        f = load(BOARD19)
        g19 = movers.gate(f["board"], "2026-10-18", hist_root(td, f["responses"]), 0,
                          now=dt.datetime(2026, 10, 19, 20, 35, tzinfo=UTC))
        guarded(fails, "19 October 4:30 PM ET (real): PUMP +11.46%, VVV +13.74% and CRV +10.13% fail the volatility "
                       "leg, and no coin passes: the record says so",
                lambda: not g19["passed"] and sorted(x["sym"] for x in g19["failed"] if x["legs"]["move"])
                == ["CRV", "PUMP", "VVV"] and any("no top-100 coin passed the gate" in l for l in g19["log"]))


# ---- 2. the alt feeds and the evidence -----------------------------------------------------------------------

def evidence_cases(fails):
    import movers
    import why_evidence as we
    print("2. the alt feeds and each mover's evidence, from the recorded answers")
    guarded(fails, "a coin is named by its name or a ticker of three letters or more, also before a quote currency",
            lambda: movers.names_coin("Binance Will List Celestia (TIA)", "TIA", "Celestia")
            and movers.names_coin("OKX to list TIAUSDT perpetual", "TIA", "Celestia")
            and not movers.names_coin("the TIARA token", "TIA", "Celestia")
            and not movers.names_coin("M is up", "M", "MemeCore") and movers.names_coin("MemeCore jumps", "M", "MemeCore"))
    rows = movers._announcements("kraken", "<item><title>PNT is available for trading!</title><link>https://x</link>"
                                           "<pubDate>Fri, 16 Oct 2026 10:30:11 +0000</pubDate></item>")
    guarded(fails, "Kraken's blog item 'is available for trading' is a listing notice with its time",
            lambda: rows == [(1792146611, "PNT is available for trading!", "https://x", None)])
    with tempfile.TemporaryDirectory() as td:
        r, log = record16(td)
        coins = r["coins"]
        guarded(fails, "16 October: the five movers each carry an evidence record", lambda: sorted(coins) ==
                ["ETHFI", "INJ", "PENDLE", "TIA", "ZRO"] and all(coins[s].get("evidence") for s in coins))
        unread = " ".join(u["name"] + ": " + u["why"] for u in coins["TIA"]["evidence"]["unread"])
        read = " ".join(x["name"] for x in coins["TIA"]["evidence"]["read"])
        guarded(fails, "the listing feeds read are named as read: Binance, OKX, KuCoin, Bitget, Kraken, Coinbase",
                lambda: all(n in read for n in ("Binance new listings", "OKX new listings", "KuCoin new listings",
                                                "Bitget listings", "Kraken blog", "Coinbase status notices")))
        guarded(fails, "the feeds not read are named with their reason: Upbit, Bybit, governance votes",
                lambda: all(n in unread for n in ("Upbit listing notices: not read: its "
                                                  "announcements API answered 403", "Bybit listing notices",
                                                  "Protocol upgrades and governance votes")))
        guarded(fails, "token unlocks read from CoinMarketCap for TIA (its slug carries the ticker)",
                lambda: "CoinMarketCap token unlocks, Celestia" in read)
        e_unread = " ".join(u["name"] + ": " + u["why"] for u in coins["ETHFI"]["evidence"]["unread"])
        guarded(fails, "ETHFI: CoinMarketCap's page at its CoinGecko slug is another token (EETH), so its unlocks "
                       "are not read, and the reason says so", lambda: "does not carry the ticker ETHFI" in e_unread)
        for sym, e in coins.items():
            name = e["name"]
            others = [c["line"] for c in e["evidence"]["candidates"] if not movers.names_coin(c["line"], sym, name)
                      and c["kind"] not in ("unlock",)]
            guarded(fails, f"{sym}: every candidate names the coin (a market-wide event is Bitcoin's card's)",
                    lambda: not others)
        tia = coins["TIA"]["evidence"]["coins"]["TIA"]
        guarded(fails, "TIA's series is a venue's, and its move agrees with the Board's within 3 points",
                lambda: tia["series"]["points"] and abs(we._pct(tia["series"]["points"][0][1],
                                                        tia["series"]["points"][-1][1]) - 30.6) <= 3.0)
        guarded(fails, "TIA's beta prints in its readings and is the gate's", lambda: tia["mechanics"]["beta"] == 1.653)
        # SYNTHETIC: a venue whose ticker is another coin (its move 27 points off the Board's)
        led = we.Ledger()
        we.register_coin("TIA", "celestia", "Celestia")
        start, end = 1792066613, 1792153013

        def f(url, kind="json"):
            if "binance" in url:
                return [[(start + i * 300 - 300) * 1000, 1, 1, 1, 1 + i * 0.002] for i in range(289)]
            raise we.Unread("not in this case")
        s, rest = movers.read_series_checked("TIA", start, end, end + 3600 * 80, f, led, 30.6)
        guarded(fails, "SYNTHETIC (a venue moving +57.6% against the Board's +30.6%): its series is not taken, and "
                       "the reason is named", lambda: s is None and any("not taken as this coin's series" in u["why"]
                                                                       for u in led.unread))


# ---- 3. the trigger and the cage -----------------------------------------------------------------------------

def trigger_cases(fails):
    import watcher
    print("3. the market-move trigger, crypto only, at section 3.1's thresholds, inside the two-a-day cage")
    calm = dt.datetime(2026, 10, 19, 15, 0, tzinfo=UTC)          # 11:00 AM ET, between the slots
    mt = lambda r, c=None, now=calm: watcher.market_trigger(r, c, now)
    guarded(fails, "on by default on this desk, at 3% inside 60 minutes and 5% inside 24 hours",
            lambda: watcher.MARKET_TRIGGER and watcher.MARKET_1H_PCT == 3.0 and watcher.MARKET_24H_PCT == 5.0)
    # the readings below are set by hand at each threshold's boundary: SYNTHETIC
    guarded(fails, "SYNTHETIC Bitcoin +2.99% in the hour: quiet", lambda: mt({"BTC": (2.99, 1.0)}) is None)
    guarded(fails, "SYNTHETIC Bitcoin +3.00% in the hour: fires", lambda: "Bitcoin moved +3.0% in the last hour" in
            (mt({"BTC": (3.0, 1.0)}) or ""))
    guarded(fails, "SYNTHETIC Bitcoin -3.20% in the hour: fires", lambda: mt({"BTC": (-3.2, -1.0)}))
    guarded(fails, "SYNTHETIC the whole market -3.1% in the hour, Bitcoin -2.0%: fires on the market",
            lambda: "The whole market" in (mt({"BTC": (-2.0, -2.0), "market": (-3.1, -3.0)}) or ""))
    guarded(fails, "SYNTHETIC Bitcoin -4.99% over 24 hours: quiet", lambda: mt({"BTC": (0.5, -4.99)}) is None)
    guarded(fails, "SYNTHETIC Bitcoin -5.00% over 24 hours, not carried by the last Board: fires",
            lambda: "over the last 24 hours" in (mt({"BTC": (0.5, -5.0)}, {"BTC": -1.0}) or ""))
    guarded(fails, "SYNTHETIC Bitcoin -6% over 24 hours that the last published Board already carried (-5.5%): quiet",
            lambda: mt({"BTC": (0.5, -6.0)}, {"BTC": -5.5}) is None)
    guarded(fails, "SYNTHETIC the market +5.4% over 24 hours after a Board that carried -5.2%: fires (a new move)",
            lambda: mt({"market": (0.2, 5.4)}, {"market": -5.2}))
    guarded(fails, "SYNTHETIC an unreadable reading never fires", lambda: mt({"BTC": (None, None), "market": (None, None)})
            is None)
    for label, when in (("7:30 PM ET, the Edition", dt.datetime(2026, 10, 19, 23, 30, tzinfo=UTC)),
                        ("8:00 AM ET, the morning read", dt.datetime(2026, 10, 19, 12, 0, tzinfo=UTC))):
        guarded(fails, f"SYNTHETIC between slots only: a 4% hour at {label} stays quiet (the slot reports it)",
                lambda: mt({"BTC": (4.0, 4.0)}, now=when) is None)
    f = load("watcher_reads_recorded.json")["responses"]
    rd = watcher.market_readings(fetch=lambda u: f[u])
    guarded(fails, f"the recorded reads give Bitcoin's hour and day and the Top 100's ({rd})",
            lambda: all(isinstance(v, float) for v in rd["BTC"]) and all(isinstance(v, float) for v in rd["market"]))
    guarded(fails, "the old price triggers (any major, 5% an hour, 4% a day) stay off", lambda: not watcher.PRICE_TRIGGERS)

    def run_main(already, readings, slot=None):
        calls = {"read": 0}
        out = tempfile.NamedTemporaryFile("w+", delete=False)
        out.close()
        saved = {k: getattr(watcher, k) for k in ("missed_slot", "desk_published_recently", "breaking_runs_today",
                                                  "market_readings", "near_slot", "hot_cluster")}
        old_env = os.environ.get("GITHUB_OUTPUT")
        try:
            watcher.missed_slot = lambda *a, **k: None
            watcher.desk_published_recently = lambda: False
            watcher.breaking_runs_today = lambda: already

            def reads(*a, **k):
                calls["read"] += 1
                return readings
            watcher.market_readings = reads
            watcher.near_slot = lambda now=None: slot
            watcher.hot_cluster = lambda: None
            os.environ["GITHUB_OUTPUT"] = out.name
            with contextlib.redirect_stdout(io.StringIO()):
                watcher.main()
            text = open(out.name).read()
        finally:
            for k, v in saved.items():
                setattr(watcher, k, v)
            if old_env is None:
                os.environ.pop("GITHUB_OUTPUT", None)
            else:
                os.environ["GITHUB_OUTPUT"] = old_env
            os.unlink(out.name)
        return text, calls["read"]
    big = {"BTC": (-3.4, -4.0), "market": (-3.0, -3.5)}
    t0, n0 = run_main(0, big)
    guarded(fails, "the cage: with no breaking run today, a 3.4% hour fires a breaking run, run 1 of 2",
            lambda: "trigger=true" in t0 and "breaking=true" in t0 and "run 1 of 2" in t0)
    t1, n1 = run_main(1, big)
    guarded(fails, "the cage: with one breaking run today, it fires as run 2 of 2", lambda: "run 2 of 2" in t1)
    t2, n2 = run_main(2, big)
    guarded(fails, "the cage: at two breaking runs today it stays quiet and makes no read at all",
            lambda: "trigger=false" in t2 and "breaking cap reached" in t2 and n2 == 0)
    t3, n3 = run_main(0, big, slot="the Edition")
    guarded(fails, "inside a slot's span the trigger makes no read and fires nothing",
            lambda: "trigger=false" in t3 and n3 == 0)


# ---- 4. the verdicts, the spend and the cap ------------------------------------------------------------------

def spend_cases(fails):
    import movers
    import verdict
    import why_evidence as we
    print("4. the verdicts and the spend against the $1.50 cap at ten coin reads (9.3's reservation, API mocked)")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "ledger.json")
        mdir = os.path.join(td, "movers")
        fetch, rec_utc = replay16()
        hroot = hist_root(td, load(HIST16))
        api = s93().MockAPI(draft=s93().copy_two, check=s93().stands_all)
        recs = []
        with s93().mocked(api), contextlib.redirect_stdout(io.StringIO()):
            for slot in ("morning", "evening", "breaking-1700"):
                recs.append(movers.run(load(BOARD16), load(WIRE16), DAY16, slot, fetch=fetch,
                                       now=dt.datetime(2026, 10, 16, 12, 40, tzinfo=UTC), directory=mdir,
                                       history_root=hroot, ledger_path=led, do_bootstrap=False, cg_spacing=0))
        reads = [len(r["gate"]["passed"]) for r in recs]
        guarded(fails, f"three runs on one day make 5, 5 and 0 coin reads: ten, the day's cap ({reads})",
                lambda: reads == [5, 5, 0] and movers.used_today(DAY16, mdir) == 10
                and len(recs[2]["gate"]["over_cap"]) == 5)
        rows = verdict._ledger_rows(led)
        calls = [r for r in rows if r.get("kind") == "call"]
        guarded(fails, f"every model attempt was reserved before it was made and settled after ({len(calls)} calls)",
                lambda: len(calls) == 20 and all(r["status"] == "settled" and r["est_usd"] > 0 for r in calls))
        day = verdict.day_spend(DAY16, led)
        worst = round(sum(r["est_usd"] for r in calls), 4)
        print(f"     ten coin reads: settled ${day:.4f} at the mocked usage (1,200 in, 300 out a call); "
              f"reserved worst case ${worst:.4f}; cap ${verdict.CAP_USD:.2f}")
        guarded(fails, "ten coin reads stay inside the $1.50 day cap even at every call's worst case",
                lambda: day <= verdict.CAP_USD and worst <= verdict.CAP_USD)
        guarded(fails, "the movers' calls go to the same ledger and the same models as Bitcoin's (Haiku 5.5 drafts, "
                       "Sonnet 5.5 checks)", lambda: {b["model"] for b in api.bodies} == {"claude-haiku-5-5",
                                                                                         "claude-sonnet-5-5"})
        v = recs[0]["coins"]["TIA"]["verdict"]["coins"]["TIA"]
        guarded(fails, f"TIA's verdict is graded in code and its two checked sentences print ({v.get('grade')}, "
                       f"{v.get('by')})", lambda: v.get("grade") in verdict.GRADES and v.get("by") == "model")
        guarded(fails, "a mover's card names its window as the gate measured it: over the last 24 hours",
                lambda: v.get("window_words") == "over the last 24 hours")
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "ledger.json")
        # SYNTHETIC: the day already at $1.45 from Bitcoin's and Ether's reads
        json.dump([{"kind": "call", "date": DAY16, "slot": "morning", "stage": "verdict_check", "status": "settled",
                    "usd": 1.45, "est_usd": 1.45, "model": "claude-sonnet-5-5"}], open(led, "w"))
        r = graded16(td, ledger=led)
        ks = {s: (e["verdict"]["coins"][s].get("kind"), e["verdict"]["coins"][s].get("grade"),
                  e["verdict"]["coins"][s].get("url")) for s, e in r["coins"].items()}
        guarded(fails, f"SYNTHETIC (the day at $1.45): no mover's check is made past the cap; each verdict is "
                       f"withheld, no grade, no URL ({ks})",
                lambda: all(k == ("withheld", None, None) for k in ks.values())
                and verdict.day_spend(DAY16, led) <= verdict.CAP_USD)
        we.register_coin("TIA", "celestia", "Celestia")
        movers.register("TIA", "Celestia", "celestia")
        card = verdict.card_html(r["coins"]["TIA"]["verdict"], "TIA", where="coin")
        guarded(fails, "the withheld card says the desk's check did not run, never a guess",
                lambda: verdict.CAP_LINE in s93().visible(card) and not GRADE.search(s93().visible(card)))
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "ledger.json")
        r, _ = record16(td)
        import llm
        n = {"i": 0}

        def flaky(user):
            n["i"] += 1
            if n["i"] == 1:                 # the first draft attempt answers HTTP 500; llm.py retries it
                return llm.urllib.error.HTTPError("https://api.anthropic.com/v1/messages", 500, "boom", {},
                                                  io.BytesIO(b"{}"))
            return s93().copy_two(user)
        api = s93().MockAPI(draft=flaky, check=s93().stands_all)
        with s93().mocked(api), contextlib.redirect_stdout(io.StringIO()):
            movers.verdicts(r, DAY16, "morning", ledger_path=led, now=dt.datetime(2026, 10, 16, 12, 40, tzinfo=UTC))
        calls = [x for x in verdict._ledger_rows(led) if x.get("kind") == "call"]
        guarded(fails, "an automatic retry is reserved before it is made: the failed attempt is a row of its own "
                       "(unbilled), then the retry's", lambda: calls and calls[0]["status"] == "unbilled"
                and calls[1]["status"] == "settled" and calls[0]["stage"] == calls[1]["stage"] == "verdict_draft")


def synthetic_named(td, which="listing"):
    """SYNTHETIC (the real 16 October days grade every mover Unclear, so no card names an event): the real TIA
    record with three listing notices added (two from Binance, so the outlet alone cannot tell them apart, and one
    from OKX), each timed by hand; with which='listing' the first Binance notice comes 30 minutes before the run
    began, with which='unlock' the record's real CoinMarketCap unlock is moved there instead. Every other part of
    the record is the recorded day's."""
    import why_evidence as we
    r, _ = record16(td)
    for k in [k for k in r["coins"] if k != "TIA"]:
        del r["coins"][k]
    r["gate"]["passed"] = [x for x in r["gate"]["passed"] if x["sym"] == "TIA"]
    ev = r["coins"]["TIA"]["evidence"]
    coin = ev["coins"]["TIA"]
    run = coin["run"]
    pts = [(t, p) for t, p in coin["series"]["points"]]
    t0 = run["start_t"] - 1800
    unl = next(c for c in ev["candidates"] if c["kind"] == "unlock")
    if which == "unlock":
        unl["event_utc"] = we._iso(t0)

    def notice(i, venue, outlet, title, t):
        return {"id": f"listing-{venue}-{t}-synthetic-{i}", "kind": "listing", "line": title,
                "event_utc": we._iso(t), "event_basis": f"{outlet}'s announcement time", "scheduled": False,
                "report_utc": None, "source_count": 1, "primary": True,
                "links": [{"outlet": outlet, "url": f"https://example.invalid/{venue}/{i}"}],
                "secondary": False, "secondary_why": ""}
    ev["candidates"] += [notice(1, "binance", "Binance", "Binance Will List Celestia (TIA) perpetual",
                                t0 if which == "listing" else t0 - 7200),
                         notice(2, "binance", "Binance", "Binance Adds TIA to Margin", t0 - 5400),
                         notice(3, "okx", "OKX", "OKX will launch TIA/USD for spot trading", t0 - 3 * 3600)]
    coin["tests"] = []
    for c in ev["candidates"]:
        t, basis = we.test_time(c)
        coin["tests"].append({"id": c["id"], "t_utc": we._iso(t), "basis": basis,
                              "result": we.timing(pts, run, t, c.get("scheduled"))})
    coin["event_hours"] = {}
    return r


# ---- 5. no card below the gate ----------------------------------------------------------------------------------

def _coin_page(sym, rec, board=None):
    import site_build as sb
    import snapshot
    p = copy.deepcopy(board or load(BOARD16))
    pos, c = next((i + 1, x) for i, x in enumerate(p["movers"]["top100"]) if x["symbol"] == sym)
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, json.load(open(os.path.join(HERE, "fixtures", "why", "flows_2026-10-15T2343Z.json"))))
    try:
        return sb.render_coin_page(c, pos, p, [], "DATELINE", wire={"items": []}, cm={}, movers=rec,
                                   evidence={}, verdict={})
    finally:
        sb.SNAP = old


def no_card_cases(fails):
    import movers
    print("5. no card below the gate: a coin that did not pass gets no card, no grade and no URL")
    with tempfile.TemporaryDirectory() as td:
        r = graded16(td)
        for sym in ("ARB", "WLD", "NEAR", "APT", "SEI"):
            h = _coin_page(sym, r)
            guarded(fails, f"16 October {sym} (failed or left out): its page carries no card, no section, no grade word",
                    lambda: 'class="vd' not in h and 'class="td-sec ev"' not in h and not GRADE.search(s93().visible(h)))
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir)
        json.dump(r, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        paths = {b["path"] for b in movers.build_pages(mdir)}
        guarded(fails, f"only the graded movers have /why/ pages ({sorted(paths)})",
                lambda: paths == {f"/why/{DAY16}-{c}" for c in ("celestia", "injective-protocol", "layerzero",
                                                               "ether-fi", "pendle")})
        f = load(BOARD19)
        with tempfile.TemporaryDirectory() as td2:
            g19 = movers.gate(f["board"], "2026-10-18", hist_root(td2, f["responses"]), 0,
                              now=dt.datetime(2026, 10, 19, 20, 35, tzinfo=UTC))
        rec19 = {"window": {"end_utc": f["board"]["generated_utc"]}, "gate": g19, "coins": {}, "date_et": "2026-10-19",
                 "slot": "evening", "made_utc": f["board"]["generated_utc"]}
        h = _coin_page("VVV", rec19, f["board"])
        guarded(fails, "19 October (real): VVV, +13.74% but under 2.5 times its usual day, gets no card",
                lambda: 'class="vd' not in h and not GRADE.search(s93().visible(h)))


# ---- 6. the pages: the card and the section, one fact once, one pointer per name; the URLs and the sitemaps ------

def page_cases(fails):
    import movers
    import site_build as sb
    t = s93()
    print("6. the coin page and the /why/ page of a mover: no fact twice, every name points at one listed item")
    with tempfile.TemporaryDirectory() as td:
        r = graded16(td)
        for sym in ("TIA", "INJ", "ZRO", "ETHFI", "PENDLE"):
            for variant, rr in (("graded line", None), ("model text", True)):
                rec = copy.deepcopy(r)
                if not variant.startswith("model"):
                    v = rec["coins"][sym]["verdict"]["coins"][sym]
                    v.update(text=list(v["line"]), by="phrases")
                h = _coin_page(sym, rec)
                card, sec, ctext, crow, srow = t._parts(h)
                guarded(fails, f"{sym}, {variant}: its page carries the card above the readings and the section",
                        lambda: card and sec and h.index('class="vd') < h.index("Readings</h2>") < h.index('class="td-sec ev"'))
                both = sorted((t._facts(ctext) & t._facts(t.visible(sec))) | (crow & srow))
                guarded(fails, f"{sym}, {variant}, coin page: no fact in both ({'; '.join(both) or 'none'})", lambda: not both)
                if "No reported event lines up" not in ctext:
                    probs = t.pointer_problems(card, sec)
                    guarded(fails, f"{sym}, {variant}, coin page: the event is named and points at exactly one listed "
                                   f"item ({'; '.join(probs) or 'one'})", lambda: not probs and 'data-vd-ref="' in card)
        # SYNTHETIC (see synthetic_named): a mover's card that names its event, on its coin page and its /why/ page
        sn = synthetic_named(td)
        with mocked_api(), contextlib.redirect_stdout(io.StringIO()):
            movers.verdicts(sn, DAY16, "morning", ledger_path=os.path.join(td, "ln.json"),
                            now=dt.datetime(2026, 10, 16, 12, 40, tzinfo=UTC))
        vn = sn["coins"]["TIA"]["verdict"]["coins"]["TIA"]
        guarded(fails, f"SYNTHETIC TIA, a Binance listing 30 minutes before the run: graded in code ({vn.get('grade')}) "
                       f"and named by subject ({[x.get('text') for x in vn.get('refs') or []]})",
                lambda: vn.get("grade") in ("Likely", "Disputed") and vn.get("refs"))
        sdir = os.path.join(td, "named")
        os.makedirs(sdir)
        json.dump(sn, open(os.path.join(sdir, f"{DAY16}-morning.json"), "w"))
        named_pages = {"/coins/tia": _coin_page("TIA", sn)}
        named_pages.update({"/" + b["rel"][:-5]: b["html"] for b in movers.build_pages(sdir)})
        for pname, html in named_pages.items():
            card, sec, ctext, crow, srow = t._parts(html)
            both = sorted((t._facts(ctext) & t._facts(t.visible(sec))) | (crow & srow))
            probs = t.pointer_problems(card, sec)
            guarded(fails, f"SYNTHETIC {pname}: no fact in both ({'; '.join(both) or 'none'}), and each named event "
                           f"points at exactly one listed item ({'; '.join(probs) or 'one'})",
                    lambda: card and sec and not both and not probs and 'data-vd-ref="' in card)
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir)
        json.dump(r, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        pages = movers.build_pages(mdir)
        for b in pages:
            card, sec, ctext, crow, srow = t._parts(b["html"])
            both = sorted((t._facts(ctext) & t._facts(t.visible(sec))) | (crow & srow))
            guarded(fails, f"/{b['rel'][:-5]}: the card and the section, no fact in both ({'; '.join(both) or 'none'})",
                    lambda: card and sec and not both)
            if "No reported event lines up" not in ctext:
                probs = t.pointer_problems(card, sec)
                guarded(fails, f"/{b['rel'][:-5]}: the pointer names exactly one listed item ({'; '.join(probs) or 'one'})",
                        lambda: not probs)
            guarded(fails, f"/{b['rel'][:-5]}: canonical at its own URL, linked to the coin page",
                    lambda: f'<link rel="canonical" href="{sb.ORIGIN}{b["path"]}"' in b["html"]
                    and 'href="/coins/' in b["html"])
        # URLs stable: a later record the same day for the same coin keeps the URL. SYNTHETIC: the real record
        # copied as the evening's, stamped one second after the real one's own stamp
        r2 = copy.deepcopy(r)
        later = (dt.datetime.fromisoformat(r["made_utc"].replace("Z", "+00:00")) + dt.timedelta(seconds=1))
        r2.update(slot="evening", made_utc=later.strftime("%Y-%m-%dT%H:%M:%SZ"))
        json.dump(r2, open(os.path.join(mdir, f"{DAY16}-evening.json"), "w"))
        again = movers.build_pages(mdir)
        guarded(fails, "a second record the same day keeps every URL; the page carries the day's newest verdict",
                lambda: {b["path"] for b in again} == {b["path"] for b in pages}
                and all("Evening Brief" in b["html"] for b in again))
        # the sitemaps: every /why/ URL the build writes is in the archive sitemap and, inside its 48 hours, the news one
        built, written = [], {}
        old_dir = movers.DIR
        movers.DIR = mdir
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                built = sb._write_verdicts(lambda rel, html: written.__setitem__(rel, html), "DATELINE")
        finally:
            movers.DIR = old_dir
        mv_paths = {b["path"] for b in built if b["path"] in {p["path"] for p in pages}}
        guarded(fails, "the build writes the movers' /why/ pages beside Bitcoin's and hands them to the sitemaps",
                lambda: mv_paths == {p["path"] for p in pages} and all(p["rel"] in written for p in pages))
        news = sb.render_news_sitemap([{"published_utc": "2026-10-16T23:20:00Z", "date": DAY16, "slug": "x",
                                        "title": "x", "category": "news"}],
                                      extra=[{"loc": b["path"], "published_utc": b["published_utc"], "title": b["title"]}
                                             for b in built])
        guarded(fails, "every mover's /why/ URL is in the news sitemap inside its 48 hours",
                lambda: all(f"{sb.ORIGIN}{p}<" in news for p in mv_paths))
        # the Big movers list
        h = sb.render_pulse_movers(dict(load(BOARD16)), "DATELINE", movers_rec=r)
        bm = (re.search(r'<section class="bm".*?</section>', h, re.S) or re.match("", "")).group(0)
        order = re.findall(r'<span class="bm-sym">(\w+)</span>', bm)
        guarded(fails, f"Big movers lists the five in order of the volatility multiple ({order})",
                lambda: order == ["TIA", "INJ", "ZRO", "ETHFI", "PENDLE"])
        guarded(fails, "each row carries its 24h move, its excess over Bitcoin, its usual-day multiple, its volume "
                       "against its 7-day average (or 'not read') and its grade linked to its /why/ page",
                lambda: "+30.60%" in bm and "+28.1 pts" in bm and "3.7x" in bm and f'href="/why/{DAY16}-celestia"' in bm)
        guarded(fails, "the 24h column is the first after the name", lambda: re.search(
            r'<th scope="col">Coin</th><th scope="col">24h</th>', bm))
        guarded(fails, "APT and SEI, which failed the gate, are not in Big movers",
                lambda: "APT" not in order and "SEI" not in order and "+14.03%" not in bm)
        rest = h.replace(bm, "")
        guarded(fails, "a coin in Big movers is not listed again in the gainers below (one fact, printed once)",
                lambda: not re.search(r"\+30\.6|\+25\.29|\+20\.59", rest))
        f = load(BOARD19)
        with tempfile.TemporaryDirectory() as td2:
            g19 = movers.gate(f["board"], "2026-10-18", hist_root(td2, f["responses"]), 0,
                              now=dt.datetime(2026, 10, 19, 20, 35, tzinfo=UTC))
        rec19 = {"window": {"end_utc": f["board"]["generated_utc"]}, "gate": g19, "coins": {}}
        h19 = sb.render_pulse_movers(f["board"], "DATELINE", movers_rec=rec19)
        guarded(fails, "19 October (real): no coin passed, so the list says so rather than padding",
                lambda: "empty rather than padded" in h19 and 'class="bm-tbl' not in h19)


# ---- 7. the time budget ------------------------------------------------------------------------------------------

def budget_cases(fails):
    import movers
    import why_evidence as we
    print("7. the step keeps a time budget and fails open")
    with tempfile.TemporaryDirectory() as td:
        fetch, rec_utc = replay16()
        ticks = {"t": 0.0}

        def clock():
            ticks["t"] += 10.0
            return ticks["t"]
        r = movers.build(load(BOARD16), load(WIRE16), BEFORE16, fetch=fetch, now_utc=rec_utc,
                         history_root=hist_root(td, load(HIST16)), deadline_s=movers.DEADLINE_EVIDENCE_S, clock=clock,
                         cg_spacing=0)
        late = [u for e in r["coins"].values() for u in (e.get("evidence") or {}).get("unread") or []
                if "not read in time" in u["why"]]
        guarded(fails, "past the evidence budget every source not yet read is skipped and named 'not read in time', "
                       "and the record is still written", lambda: late and r["coins"])
        rr, _ = record16(td)
        movers.STOP["set"] = True
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                movers.verdicts(rr, DAY16, "morning", ledger_path=os.path.join(td, "l.json"),
                                now=dt.datetime(2026, 10, 16, 12, 40, tzinfo=UTC))
        finally:
            movers.STOP["set"] = False
            we.STOP["set"] = False
        v = rr["coins"]["TIA"]["verdict"]["coins"]["TIA"]
        guarded(fails, "with the step's budget spent, each mover keeps its graded line and no model call is made",
                lambda: v.get("grade") and v.get("by") == "phrases" and not os.path.exists(os.path.join(td, "l.json")))
    guarded(fails, "the budgets: 45 seconds for history reads, 150 for evidence, 300 for the step inside the "
                   "workflow's 360", lambda: (movers.HISTORY_BUDGET_S, movers.DEADLINE_EVIDENCE_S, movers.DEADLINE_S)
            == (45, 150, 300))


# ---- 8. wiring ---------------------------------------------------------------------------------------------------

def wiring_cases(fails):
    print("8. wired into both workflows after verdict.py, with a timeout, never a gate; the trigger's settings")
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: runs movers.py --write after verdict.py, with a timeout, never as a gate",
                lambda: re.search(r"verdict\.py --write \|\| true.*?timeout 360 python3 movers\.py --write \|\| true",
                                  y, re.S))
        guarded(fails, f"{wf}: commits the movers records", lambda: "git add site/data/movers" in y)
    y = open(os.path.join(HERE, ".github", "workflows", "crypto-news-brief.yml"), encoding="utf-8").read()
    step = re.search(r"- name: Big movers[^\n]*\n(.*?)(?=\n      - name:)", y, re.S)
    guarded(fails, "the Edition's step tells a breaking run so, which writes its own record",
            lambda: step and "BREAKING: ${{ inputs.breaking == true && '1' || '0' }}" in step.group(1))
    w = open(os.path.join(HERE, ".github", "workflows", "watcher.yml"), encoding="utf-8").read()
    guarded(fails, "watcher.yml passes the market trigger's three settings",
            lambda: all(k in w for k in ("WATCH_MARKET_TRIGGER", "WATCH_MARKET_1H_PCT", "WATCH_MARKET_24H_PCT")))
    for f in ("movers.py", "watcher.py", "why_evidence.py", "verdict.py", "scripts/sprint94_test.py"):
        src = open(os.path.join(HERE, f), encoding="utf-8").read()
        guarded(fails, f"{f} carries no em or en dash", lambda: not re.search("[\u2013\u2014]", src))


# ---- 9. review 1 (Monday October 19, 2026): the reviewer's seven failures and the page's two standing laws ----------

def _bm(h):
    return (re.search(r'<section class="bm".*?</section>', h, re.S) or re.match("", "")).group(0)


def review1_cases(fails):
    import movers
    import site_build as sb
    import verdict
    import why_evidence as we
    t = s93()
    print("9. review 1: one list, the Brief's citations, the crash-day line, the cap said, true reasons, direction")
    with tempfile.TemporaryDirectory() as td:
        r = graded16(td)
        board = load(BOARD16)
        h = sb.render_pulse_movers(dict(board), "DATELINE", movers_rec=r)
        guarded(fails, "ONE LIST: /pulse/movers prints Big movers and no 'Biggest gainers' or 'Biggest losers' list",
                lambda: 'class="bm"' in h and "Biggest gainers" not in h and "Biggest losers" not in h)
        h0 = sb.render_pulse_movers(dict(board), "DATELINE", movers_rec={})
        guarded(fails, "ONE LIST: with no current movers record the page says so, and still prints no old list",
                lambda: "Biggest gainers" not in h0 and "no current Big movers reading" in t.visible(h0))
        guarded(fails, "How to read Big movers never says 'because' (only a Confirmed verdict may)",
                lambda: not re.search(r"\bbecause\b", t.visible(h), re.I))
        # one rank, from one named source, with its stamp: the Board's Top 100 position the coin page prints
        bm = _bm(h)
        cp = _coin_page("TIA", r)
        guarded(fails, "ONE RANK: Big movers prints TIA at #80, its place in the Board's Top 100, as /coins/tia does, "
                       "with the source and the Board's stamp named",
                lambda: re.search(r'<td class="bm-rk">#80</td>', bm) and "Rank 80 of the Top 100" in cp
                and "#99" not in t.visible(h) and "place in the desk's Top 100" in t.visible(bm))
        b101 = copy.deepcopy(board)
        tia_row = next(x for x in b101["movers"]["top100"] if x["symbol"] == "TIA")
        b101["movers"]["top100"].append(dict(tia_row, symbol="SYN101", name="Synthetic 101", gecko_id="celestia",
                                             rank=60))
        g101 = movers.gate(b101, BEFORE16, os.path.join(td, "history"), 0,
                           now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        every = {x["sym"] for k in ("passed", "over_cap", "failed", "left_out") for x in g101[k]}
        guarded(fails, "SYNTHETIC (a 101st row with TIA's figures and a source rank of 60): outside the Board's 100 "
                       "positions, never measured", lambda: "SYN101" not in every)

        # 4. the cap said
        r8, _ = record16(td, used=8)
        h8 = _bm(sb.render_pulse_movers(dict(board), "DATELINE", movers_rec=r8))
        v8 = t.visible(h8)
        guarded(fails, "PAST THE CAP: after 8 reads today, ZRO +20.59%, ETHFI +15.53% and PENDLE +11.20% are still "
                       "listed, ungraded",
                lambda: re.findall(r'<span class="bm-sym">(\w+)</span>', h8) == ["TIA", "INJ", "ZRO", "ETHFI", "PENDLE"]
                and "+20.59%" in v8 and "+15.53%" in v8 and "+11.20%" in v8 and v8.count("Past the cap") == 3)
        guarded(fails, "PAST THE CAP: a line names both caps (8 a reading, 10 a day) and the coins held back",
                lambda: re.search(r"8 a reading and 10 a day", v8) and re.search(r"held back[^.]*LayerZero, Ether\.fi, Pendle\.", v8))
        guarded(fails, "PAST THE CAP: listed() carries the coins past the cap",
                lambda: {"ZRO", "ETHFI", "PENDLE"} <= movers.listed(r8, board["generated_utc"]))

        # 7. the left-out reason is the coin's own
        hdir = os.path.join(td, "history")
        s2 = json.load(open(os.path.join(hdir, "celestia.json")))
        keep = copy.deepcopy(s2)
        del s2["closes"]["2026-10-01"]
        json.dump(s2, open(os.path.join(hdir, "celestia.json"), "w"))
        os.rename(os.path.join(hdir, "aptos.json"), os.path.join(td, "aptos.hold"))
        gg = movers.gate(board, BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        os.rename(os.path.join(td, "aptos.hold"), os.path.join(hdir, "aptos.json"))
        json.dump(keep, open(os.path.join(hdir, "celestia.json"), "w"))
        rg = {"window": r["window"], "gate": gg, "coins": {}, "date_et": DAY16, "slot": "morning"}
        vg = t.visible(_bm(sb.render_pulse_movers(dict(board), "DATELINE", movers_rec=rg)))
        guarded(fails, "LEFT OUT: SYNTHETIC (a gap in TIA's closes, APT's closes removed) the list prints TIA's own reason (a gap) and APT's "
                       "own (no stored closes), not one fixed sentence",
                lambda: "have a gap" in vg and "no stored daily closes" in vg and "under 30 days of its daily closes" not in vg)

        # 3. the crash day
        guarded(fails, "CRASH DAY: 16 October (real, Bitcoin +1.48%, ten coins past 10%) is no crash day: no line",
                lambda: "moved with the market" not in t.visible(bm))
        bc = copy.deepcopy(board)
        next(x for x in bc["movers"]["top100"] if x["symbol"] == "BTC")["chg_24h_pct"] = 9.0
        gc = movers.gate(bc, BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        rc = {"window": r["window"], "gate": gc, "coins": {}, "date_et": DAY16, "slot": "morning"}
        vc = sb.render_pulse_movers(dict(bc), "DATELINE", movers_rec=rc)
        bmc = _bm(vc)
        guarded(fails, "CRASH DAY: SYNTHETIC (Bitcoin set to +9.0% on the real Board) the section says once that most "
                       "coins moved with the market, with the count, and points at Bitcoin's verdict",
                lambda: t.visible(bmc).count("moved with the market") == 1 and re.search(
                    r'href="/(coins/btc\.html|why/2026-10-16-bitcoin)"', bmc) and gc["crash"]["day"])
        guarded(fails, "CRASH DAY: the definition is held once, by the audit's numbers (Bitcoin or the market 5% in 24 "
                       "hours, or 25 or more top-100 coins past 10%)",
                lambda: movers.CRASH == {"btc_or_market_pct": 5.0, "coins_past_move": 25})

        # 2. the Brief cites the movers it mentions (SYNTHETIC: the real 16 October Edition with one sentence added)
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir, exist_ok=True)
        json.dump(r, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        ed = json.load(open(os.path.join(HERE, "site", "content", "2026-10-16-evening-brief.json")))
        ed = copy.deepcopy(ed)
        ed["body"] = list(ed.get("body") or []) + [
            "Celestia rose and Celestia led; Pendle and Arbitrum also moved, and Injective held its gain."]
        old_dir = movers.DIR
        movers.DIR = mdir
        try:
            art = sb.render_article(ed, [ed])
            import edition as _ed
            front = _ed.render_front(_ed.DESK, [ed], DAY16, [DAY16])
        finally:
            movers.DIR = old_dir
        prose = (re.search(r'<div class="prose">.*?</div>', art, re.S) or re.match("", "")).group(0)
        guarded(fails, "THE BRIEF CITES: on the Edition's page, Celestia links to its verdict, once",
                lambda: prose.count(f'<a class="bm-cite" href="/why/{DAY16}-celestia">Celestia</a>') == 1)
        guarded(fails, "THE BRIEF CITES: Injective and Pendle link to their verdicts; Arbitrum (not on the list) is not "
                       "linked", lambda: f'href="/why/{DAY16}-injective-protocol">Injective</a>' in prose
                and f'href="/why/{DAY16}-pendle">Pendle</a>' in prose and ">Arbitrum</a>" not in prose)
        r8b = copy.deepcopy(r8)
        json.dump(r8b, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        movers.DIR = mdir
        try:
            art8 = sb.render_article(ed, [ed])
        finally:
            movers.DIR = old_dir
        guarded(fails, "THE BRIEF CITES: a coin on the list past the cap (no graded verdict) links to its coin page",
                lambda: 'class="bm-cite" href="/coins/pendle.html">Pendle</a>' in art8)
        guarded(fails, "THE BRIEF CITES: the Edition's front page cites the same way",
                lambda: f'href="/why/{DAY16}-celestia">Celestia</a>' in front)
        nxt = copy.deepcopy(ed)
        nxt.update(date="2026-10-17", slug="evening-brief-2026-10-17")
        movers.DIR = mdir
        try:
            art17 = sb.render_article(nxt, [nxt])
        finally:
            movers.DIR = old_dir
        guarded(fails, "THE BRIEF CITES: a Brief of another day (no Big movers record) links no coin",
                lambda: 'class="bm-cite"' not in art17)

    # 5. every 'not read' reason is true: Coinbase's status feed is read
    with tempfile.TemporaryDirectory() as td:
        rr, _ = record16(td)
        ev = rr["coins"]["TIA"]["evidence"]
        read = " ".join(x["name"] for x in ev["read"])
        unread = " ".join(u["name"] + ": " + u["why"] for u in ev["unread"])
        guarded(fails, "COINBASE: its status feed (status.exchange.coinbase.com/history.rss) is read as a listing feed",
                lambda: "Coinbase status notices" in read and "Coinbase publishes no listing" not in unread)
        guarded(fails, "TRUE REASONS: governance is named as not wired, with Snapshot's hub said to answer",
                lambda: "Snapshot" in unread and "no single feed covers them" not in unread)
    rows = movers._announcements("coinbase", '<item><title>DATA-USD Markets Open</title><link>https://s/x</link>'
                                             '<pubDate>Fri, 09 Oct 2026 11:08:46 -0700</pubDate></item>'
                                             '<item><title>Celestia - Delayed Sends and Receives</title>'
                                             '<pubDate>Fri, 16 Oct 2026 23:49:00 -0700</pubDate></item>'
                                             '<item><title>Upcoming Trading Suspension: NEON-USD AND SYND-USD</title>'
                                             '<pubDate>Fri, 16 Oct 2026 10:00:00 -0700</pubDate></item>')
    guarded(fails, "COINBASE: 'Markets Open' is a listing, 'Trading Suspension' a delisting, a delayed send neither",
            lambda: [(x[1], x[3]) for x in rows] == [("DATA-USD Markets Open", "listing"),
                                                    ("Upcoming Trading Suspension: NEON-USD AND SYND-USD", "delisting")])
    src = open(os.path.join(HERE, "why_evidence.py"), encoding="utf-8").read()
    guarded(fails, "TRUE REASONS: Bitcoin's and Ether's records no longer say listing notices have no single feed",
            lambda: '"Exchange listing notices", "not read: no single feed"' not in src)

    # 6. direction by event type, every type crossed with each direction
    print("9b. the readings agree by direction: a listing with a rise; a delisting, an unlock or a hack with a fall")
    expect = {"listing": "up", "delisting": "down", "unlock": "down", "hack": "down"}
    for kind, good in expect.items():
        for d in ("up", "down"):
            coin = {"run": {"dir": d, "start_t": 1000}, "mechanics": {"patterns": [{"label": "coin-specific"}],
                                                                   "rows": [{"key": "ES=F", "value": 0.0}]},
                    "event_hours": {}}
            c = {"id": "x", "kind": kind, "line": "Example line", "links": []}
            fit = verdict.mech_fit(c, coin, 1000, sym="TIA")[0]
            want = "agree" if d == good else "contradict"
            guarded(fails, f"{kind} on a move {d}: the readings {want}", lambda: fit == want)
    with tempfile.TemporaryDirectory() as td:
        sn = synthetic_named(td, "unlock")
        e = sn["coins"]["TIA"]
        movers.register("TIA", "Celestia", "celestia")
        v = verdict.grade(e["evidence"], "TIA", movers.day_of(e, sn["gate"]["btc_24h_pct"]))
        guarded(fails, f"SYNTHETIC TIA +30.6% with an unlock in time and no other cause: no Likely; the rulings give no "
                       f"grade, so no card ({v.get('kind')}, {v.get('grade')})",
                lambda: v.get("grade") is None and v.get("kind") == "no_verdict")
        lst = next(c for c in e["evidence"]["candidates"] if c["id"].endswith("synthetic-1"))
        unl = next(c for c in e["evidence"]["candidates"] if c["kind"] == "unlock")
        guarded(fails, "WORDS: an unlock is 'scheduled', as CoinMarketCap lists it; a listing is 'announced'; neither "
                       "is 'reported'",
                lambda: "scheduled" in verdict._ref_full(unl, 1792100000, 1792153013, verdict.named(unl, [unl]))
                and "reported" not in verdict._ref_full(unl, 1792100000, 1792153013, verdict.named(unl, [unl]))
                and "announced" in verdict._ref_full(lst, 1792100000, 1792153013, verdict.named(lst, [lst])))


# ---- 10. review 2 (Monday October 19, 2026, 8:36 PM): the crash count, the citations, no internals on pages ------

def _crash_board(td, inj=None, offset=-1.0):
    """SYNTHETIC (the reviewer's probe, /tmp/claude-0/runs/r94b/crash.py, on the real 16 October Board and stored
    closes): Bitcoin set to -9.0%; each measured coin's move set to what its own beta gives plus `offset`; INJ set to
    `inj` when given."""
    import movers
    root = hist_root(td, load(HIST16))
    b = copy.deepcopy(load(BOARD16))
    rows = b["movers"]["top100"]
    for r in rows:
        if r["symbol"] == "BTC":
            r["chg_24h_pct"] = -9.0
    for r in rows:
        if r["symbol"] in ("BTC", "ETH"):
            continue
        st, _ = movers.stats(r.get("gecko_id") or "", BEFORE16, root)
        if not st:
            continue
        r["chg_24h_pct"] = inj if (r["symbol"] == "INJ" and inj is not None) else round(st["beta"] * -9.0 + offset, 2)
    return b, root


def review2_cases(fails):
    import movers
    import site_build as sb
    import why_evidence as we
    t = s93()
    print("10. review 2: the crash count says what it measures; citations never link a common word; no internals")
    with tempfile.TemporaryDirectory() as td:
        b, root = _crash_board(td, inj=-10.5)
        g = movers.gate(b, BEFORE16, root, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        inj = next(x for x in g["failed"] + g["passed"] if x["sym"] == "INJ")
        rec = {"gate": g, "window": {"end_utc": b["generated_utc"]}, "coins": {}, "date_et": DAY16}
        line = t.visible(" ".join(re.findall(r'<p class="bm-crash">.*?</p>', movers.list_html(rec, b["generated_utc"]),
                                             re.S)))
        within = [x for x in g["failed"] + g["passed"] if x["legs"]["move"] and abs(x["excess_pts"]) < 6]
        m = re.search(r"(\d+) of the (\d+) measured coins", line)
        guarded(fails, f"CRASH COUNT: SYNTHETIC (the reviewer's probe: Bitcoin -9.0%, INJ -10.5% against a predicted "
                       f"{inj['predicted_pct']}%, excess {inj['excess_pts']:+.2f}) the count is the coins within 6 points "
                       f"either way ({len(within)}), INJ not among them ({line[:120]!r})",
                lambda: m and int(m.group(1)) == len(within) and abs(inj["excess_pts"]) >= 6
                and "INJ" not in [x["sym"] for x in within])
        b2, root2 = _crash_board(td, offset=-7.0)
        g2 = movers.gate(b2, BEFORE16, root2, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        rec2 = {"gate": g2, "window": {"end_utc": b2["generated_utc"]}, "coins": {}, "date_et": DAY16}
        h2 = movers.list_html(rec2, b2["generated_utc"])
        guarded(fails, "CRASH COUNT: SYNTHETIC (every coin 7 points past what its beta gives, a crash day): no coin is "
                       "within 6 points, so the line that most moved with the market does not print",
                lambda: g2["crash"]["day"] and 'class="bm-crash"' not in h2)

    print("10b. citations: an unambiguous match only; a coin whose name or ticker is a common word needs a coin cue")
    with tempfile.TemporaryDirectory() as td:
        # SYNTHETIC day lists: names and tickers that are English words, handed to cite() as its day list
        lst = {"IP": ("Story", "/why/x-story"), "FLOW": ("Flow", "/coins/flow.html"), "S": ("Sonic", "/coins/s.html"),
               "NOT": ("Notcoin", "/coins/not.html"), "ONE": ("Harmony", "/coins/one.html"),
               "TIA": ("Celestia", "/why/x-celestia")}
        old = movers.day_list
        movers.day_list = lambda d, directory=None: lst
        try:
            cases = {
                "Story continues tonight: markets were calm.": False,
                "The Flow of funds turned. Sonic speed, analysts said.": False,
                "It is NOT clear, and ONE fund sold.": False,
                "Story (IP) rose 20%.": True,
                "The Story token rose.": True,
                "$NOT jumped 15% after the listing.": True,
                "$NOT led the day, by the desk's count.": True,
                "Celestia rose 30%.": True,
            }
            for text, linked in cases.items():
                out = movers.cite(text, DAY16)
                guarded(fails, f"cite: {text!r} {'links' if linked else 'links nothing'}",
                        lambda: ('class="bm-cite"' in out) == linked)
        finally:
            movers.day_list = old
        guarded(fails, "the common-word list is held in one named place", lambda: "story" in movers.COMMON_WORDS
                and "not" in movers.COMMON_WORDS)

    print("10c. no code or file path in the text a reader sees, on the pages this sprint touches")
    with tempfile.TemporaryDirectory() as td:
        r = graded16(td)
        board = load(BOARD16)
        hdir = os.path.join(td, "history")
        os.rename(os.path.join(hdir, "aptos.json"), os.path.join(td, "aptos.hold"))
        gl = movers.gate(board, BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        os.rename(os.path.join(td, "aptos.hold"), os.path.join(hdir, "aptos.json"))
        rl = dict(r, gate=dict(r["gate"], left_out=gl["left_out"]))
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir)
        json.dump(r, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        pages = {"/pulse/movers (APT left out)": sb.render_pulse_movers(dict(board), "D", movers_rec=rl),
                 "/coins/tia": _coin_page("TIA", r)}
        pages.update({"/" + x["rel"][:-5]: x["html"] for x in movers.build_pages(mdir)})
        btc = s93().rec(s93().D15())
        pages["Bitcoin's section (15 October)"] = we.section_html(btc, "BTC", live=False)
        for name, html in pages.items():
            v = t.visible(re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S))
            hits = re.findall(r"\S*(?:\.py\b|data/)\S*", v)
            guarded(fails, f"{name}: no code or file path in the visible text ({hits[:3] or 'none'})", lambda: not hits)


def unit():
    fails = []
    for name, fn in (("gate", gate_cases), ("evidence", evidence_cases), ("trigger", trigger_cases),
                     ("spend", spend_cases), ("no card", no_card_cases), ("pages", page_cases),
                     ("budget", budget_cases), ("wiring", wiring_cases), ("review 1", review1_cases),
                     ("review 2", review2_cases)):
        group(fails, name, fn)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.4: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
