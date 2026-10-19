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
        guarded(fails, f"16 October: TIA, INJ, ZRO and ETHFI pass, ranked by their volatility multiple ({passed})",
                lambda: passed == ["TIA", "INJ", "ZRO", "ETHFI"])
        tia = next(x for x in g["passed"] if x["sym"] == "TIA")
        guarded(fails, "TIA's three legs: +30.60%, 3.67x its 30-day daily volatility of 8.33%, +28.15 points beyond "
                       "its Bitcoin beta of 1.653 with Bitcoin +1.48%",
                lambda: (tia["move_pct"], tia["multiple"], tia["vol_pct"], tia["excess_pts"], tia["beta"],
                         tia["btc_pct"]) == (30.6, 3.67, 8.33, 28.15, 1.653, 1.48))
        failed = {x["sym"]: x for x in g["failed"]}
        guarded(fails, "ARB, WLD, NEAR, ZEC and FIL fail on the volatility leg alone (they moved 10% or more and "
                       "6 points beyond their beta, under 2.5 times their usual day)",
                lambda: set(failed) == {"ARB", "WLD", "NEAR", "ZEC", "FIL"} and all(
                    x["legs"] == {"move": True, "multiple": False, "excess": True} for x in failed.values()))
        guarded(fails, "APT (+14.03%) has no stored closes: left out and said, never estimated",
                lambda: [(x["sym"], x["move_pct"]) for x in g["left_out"]] == [("APT", 14.03)]
                and "no stored daily closes" in g["left_out"][0]["why"])
        guarded(fails, "the beta the gate uses is the one the section prints (why_evidence._beta on the same days)",
                lambda: __import__("why_evidence")._beta("TIA", BEFORE16, root=os.path.join(td, "history"))
                == tia["beta"] if __import__("why_evidence").register_coin("TIA", "celestia", "Celestia") else False)
        rows = load(BOARD16)["movers"]["top100"]
        outside = [r["symbol"] for r in rows if isinstance(r.get("rank"), int) and r["rank"] > 100]
        stables = [r["symbol"] for r in rows if snapshot.is_stablecoin(r)]
        every = {x["sym"] for k in ("passed", "over_cap", "failed", "left_out") for x in g[k]}
        guarded(fails, f"no stablecoin ({len(stables)} on the Board) and no rank over 100 ({len(outside)} on the "
                       f"Board) is ever measured", lambda: stables and outside and not (every & (set(stables) | set(outside))))
        guarded(fails, "Bitcoin and Ether are never measured here: their own cards grade them",
                lambda: not (every & {"BTC", "ETH"}))
        guarded(fails, "the line is the audit's, held once: 10%, 2.5x, 6 points, 30 days, 8 a slot, 10 a day",
                lambda: (movers.GATE["move_min_pct"], movers.GATE["vol_multiple_min"], movers.GATE["excess_min_pts"],
                         movers.GATE["history_days"], movers.GATE["per_slot"], movers.GATE["per_day"])
                == (10.0, 2.5, 6.0, 30, 8, 10))
        g8 = gate16(td, used=8)
        guarded(fails, "the day's cap: with 8 reads made earlier today, 2 pass and 2 wait over the cap",
                lambda: [x["sym"] for x in g8["passed"]] == ["TIA", "INJ"]
                and [x["sym"] for x in g8["over_cap"]] == ["ZRO", "ETHFI"])
        g10 = gate16(td, used=10)
        guarded(fails, "the day's cap: at 10 reads, none passes and all four are named over the cap",
                lambda: not g10["passed"] and len(g10["over_cap"]) == 4)
        # SYNTHETIC: twelve coins past every leg, made by copying the real TIA row under twelve names
        b = copy.deepcopy(load(BOARD16))
        tia_row = next(r for r in b["movers"]["top100"] if r["symbol"] == "TIA")
        hdir = os.path.join(td, "history")
        src = json.load(open(os.path.join(hdir, "celestia.json")))
        for i in range(12):
            b["movers"]["top100"].append(dict(tia_row, symbol=f"SYN{i}", name=f"Synthetic {i}", gecko_id=f"syn-{i}",
                                              rank=100))
            json.dump(dict(src, coin=f"syn-{i}"), open(os.path.join(hdir, f"syn-{i}.json"), "w"))
        gs = movers.gate(b, BEFORE16, hdir, 0, now=dt.datetime(2026, 10, 16, 12, 30, tzinfo=UTC))
        guarded(fails, "SYNTHETIC (sixteen coins past the line): at most 8 a slot, the rest over the cap",
                lambda: len(gs["passed"]) == 8 and len(gs["over_cap"]) == 8)
        log = "\n".join(g["log"])
        guarded(fails, "for two weeks every coin that fails the gate prints in the run log with its figures",
                lambda: all(re.search(rf"gate fail {s} \+\d+\.\d\d%: \d\.\d\dx its 30-day daily volatility", log)
                            for s in ("ARB", "WLD", "NEAR", "ZEC", "FIL")))
        late = gate16(td, now=dt.datetime(2026, 11, 3, 12, 30, tzinfo=UTC))
        guarded(fails, "after November 2 the failing coins are counted, not listed",
                lambda: not any("gate fail" in l for l in late["log"]) and any("5 coin(s) passed one leg" in l
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
        guarded(fails, "19 October 4:30 PM ET (real): PUMP +11.46% and VVV +13.74% fail the volatility leg, and no "
                       "coin passes: the record says so",
                lambda: not g19["passed"] and sorted(x["sym"] for x in g19["failed"] if x["legs"]["move"])
                == ["PUMP", "VVV"] and any("no top-100 coin passed the gate" in l for l in g19["log"]))


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
            lambda: rows == [(1792146611, "PNT is available for trading!", "https://x")])
    with tempfile.TemporaryDirectory() as td:
        r, log = record16(td)
        coins = r["coins"]
        guarded(fails, "16 October: the four movers each carry an evidence record", lambda: sorted(coins) ==
                ["ETHFI", "INJ", "TIA", "ZRO"] and all(coins[s].get("evidence") for s in coins))
        unread = " ".join(u["name"] + ": " + u["why"] for u in coins["TIA"]["evidence"]["unread"])
        read = " ".join(x["name"] for x in coins["TIA"]["evidence"]["read"])
        guarded(fails, "the listing feeds read are named as read: Binance, OKX, KuCoin, Bitget, Kraken",
                lambda: all(n in read for n in ("Binance new listings", "OKX new listings", "KuCoin new listings",
                                                "Bitget listings", "Kraken blog")))
        guarded(fails, "the feeds not read are named with their reason: Coinbase, Upbit, Bybit, governance votes",
                lambda: all(n in unread for n in ("Coinbase listing notices", "Upbit listing notices: not read: its "
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
        guarded(fails, f"three runs on one day make 4, 4 and 2 coin reads: ten, the day's cap ({reads})",
                lambda: reads == [4, 4, 2] and movers.used_today(DAY16, mdir) == 10)
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


def synthetic_named(td):
    """SYNTHETIC (the real 16 October days grade every mover Unclear, so no card names an event): the real TIA
    record with its real CoinMarketCap unlock moved to 30 minutes before the run began, and two listing notices
    added (two from Binance, so the outlet alone cannot tell them apart, and one from OKX), each timed by hand.
    Every other part of the record is the recorded day's."""
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
    unl["event_utc"] = we._iso(t0)

    def notice(i, venue, outlet, title, t):
        return {"id": f"listing-{venue}-{t}-synthetic-{i}", "kind": "listing", "line": title,
                "event_utc": we._iso(t), "event_basis": f"{outlet}'s announcement time", "scheduled": False,
                "report_utc": None, "source_count": 1, "primary": True,
                "links": [{"outlet": outlet, "url": f"https://example.invalid/{venue}/{i}"}],
                "secondary": False, "secondary_why": ""}
    ev["candidates"] += [notice(1, "binance", "Binance", "Binance Will List Celestia (TIA) perpetual", t0 - 7200),
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
        for sym in ("ARB", "WLD", "NEAR", "APT"):
            h = _coin_page(sym, r)
            guarded(fails, f"16 October {sym} (failed or left out): its page carries no card, no section, no grade word",
                    lambda: 'class="vd' not in h and 'class="td-sec ev"' not in h and not GRADE.search(s93().visible(h)))
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir)
        json.dump(r, open(os.path.join(mdir, f"{DAY16}-morning.json"), "w"))
        paths = {b["path"] for b in movers.build_pages(mdir)}
        guarded(fails, f"only the graded movers have /why/ pages ({sorted(paths)})",
                lambda: paths == {f"/why/{DAY16}-{c}" for c in ("celestia", "injective-protocol", "layerzero",
                                                               "ether-fi")})
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
        for sym in ("TIA", "INJ", "ZRO", "ETHFI"):
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
        guarded(fails, f"SYNTHETIC TIA, the unlock 30 minutes before the run: graded in code ({vn.get('grade')}) "
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
                and all("Evening Edition" in b["html"] for b in again))
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
        guarded(fails, f"Big movers lists the four in order of the volatility multiple ({order})",
                lambda: order == ["TIA", "INJ", "ZRO", "ETHFI"])
        guarded(fails, "each row carries its 24h move, its excess over Bitcoin, its usual-day multiple, its volume "
                       "against its 7-day average (or 'not read') and its grade linked to its /why/ page",
                lambda: "+30.60%" in bm and "+28.1 pts" in bm and "3.7x" in bm and f'href="/why/{DAY16}-celestia"' in bm)
        guarded(fails, "the 24h column is the first after the name", lambda: re.search(
            r'<th scope="col">Coin</th><th scope="col">24h</th>', bm))
        guarded(fails, "APT is named as left out for history, with its move, and is not graded",
                lambda: "under 30 days of its daily closes" in bm and "+14.03%" in bm)
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


def unit():
    fails = []
    for name, fn in (("gate", gate_cases), ("evidence", evidence_cases), ("trigger", trigger_cases),
                     ("spend", spend_cases), ("no card", no_card_cases), ("pages", page_cases),
                     ("budget", budget_cases), ("wiring", wiring_cases)):
        group(fails, name, fn)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.4: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
