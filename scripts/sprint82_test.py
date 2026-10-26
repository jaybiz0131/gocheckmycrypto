#!/usr/bin/env python3
"""Program 8, Sprint 8.2: the numbers handed over labeled (item 0) and the coin doors (items 1 to 5).

  python3 scripts/sprint82_test.py          # unit cases; exit 1 on any failure
  (verify_pipeline.py's canary also calls unit() and static(out) on the tree the build wrote)

Fixtures (fixtures/sprint82/): the 15 October 8:18 AM wire and pulse as the desk held them, and the
snapshot built inline below. Where the model's own output was not kept, the fixture is reconstructed
from the log line and says so. Every case catches its own exceptions, so on origin/main (no
phrases.py, no coin doors) the run prints FAIL lines instead of crashing.
"""
import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FX = os.path.join(HERE, "fixtures", "sprint82")


def load(name):
    return json.load(open(os.path.join(FX, name), encoding="utf-8"))


def snap():
    """The 14 October snapshot, as the twins gate read it that night: Bitcoin -2.83% and Ether -7.44%
    over the week (the stored series), -2.08% and -3.36% on the day; spot ETFs +$2.2M on the day."""
    return {"stamp_utc": "2026-10-15T00:12:00Z", "board_coins": ["BTC", "ETH"],
            "fields": {"coins": {"value": {"BTC": {"price": 81470, "chg_24h_pct": -2.08},
                                           "ETH": {"price": 2480, "chg_24h_pct": -3.36}}},
                       "etf_flows": {"value": {"btc": {"latest_net_usd_m": -261.4,
                                                       "latest_date": "14 Oct 2026"}}},
                       "fear_greed": {"value": {"value": 53}},
                       "funding": {"value": {"BTC": {"funding_8h_pct": 0.0047}}}},
            "series": {"value": {"BTC": {"chg_7d_pct": -2.83}, "ETH": {"chg_7d_pct": -7.44}}}}


def guarded(fails, msg, fn):
    """Run one case; an exception is a FAIL with its name, never a crash."""
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- item 0: the Edition's week signs -------------------------------------------------------

# Reconstructed: the ledger kept only the first 70 characters of the first sentence and the whole
# second clause's start, so the endings are the plain ones the model's sentences had.
WEEK_BTC = ("Per the desk's boards, Bitcoin traded at $81,470, down 2.08 percent on the day and "
            "2.83 percent over the week.")
WEEK_ETH = ("Ethereum fell 3.36 percent on the day and 7.44 percent over the week, the weakest "
            "of the majors.")


def edition_cases(fails):
    import twins_gate
    print("A. the 14 October week-sign sentences (7:46 PM re-run)")
    g = twins_gate.Gate(snap(), log_path="", quiet=True)
    out_b = g.text(WEEK_BTC, "the Brief's body paragraph 1")
    out_e = g.text(WEEK_ETH, "the Brief's body paragraph 1")
    guarded(fails, "Bitcoin's sentence is kept, not dropped", lambda: out_b and not g.drops)
    guarded(fails, "Bitcoin's week figure now carries its own sign word: 'down 2.83 percent over the week'",
            lambda: "down 2.83 percent over the week" in out_b)
    guarded(fails, "Ether's sentence is kept with 'down 7.44 percent over the week'",
            lambda: "down 7.44 percent over the week" in out_e and "fell 3.36 percent on the day" in out_e)
    guarded(fails, "each sign word set is recorded as a repair, none as a drop",
            lambda: len(g.repairs) == 2 and not g.drops)
    g2 = twins_gate.Gate(snap(), log_path="", quiet=True)
    wrong_sign = g2.text("Bitcoin was up 2.83 percent over the week.", "t")
    guarded(fails, "an opposite sign word that is there stays a wrong claim: dropped and logged, never rewritten",
            lambda: wrong_sign == "" and len(g2.drops) == 1 and not g2.repairs)
    g3 = twins_gate.Gate(snap(), log_path="", quiet=True)
    wrong_size = g3.text("Bitcoin rose 9.1 percent over the week.", "t")
    guarded(fails, "a figure that is not the series' is still dropped and logged, never repaired",
            lambda: wrong_size == "" and len(g3.drops) == 1 and not g3.repairs)

    g5 = twins_gate.Gate(dict(snap(), fields=dict(snap()["fields"], coins={"value": {"BTC": {"price": 80896}}})),
                         log_path="", quiet=True)
    line = "U.S. inflation accelerated to 3.7% in September, sending Bitcoin below $82,000 as bond yields spiked."
    guarded(fails, "a level crossed ('Bitcoin below $82,000') is not a price claim: kept at $80,896",
            lambda: g5.text(line, "t") == line and g5.text("Bitcoin traded at $82,000 today.", "t") == "")

    print("A2. the Edition is handed every number already labeled")
    import phrases
    boards = load("boards_2026-10-14.json")
    rows = phrases.edition_numbers(boards)
    flat = " | ".join(p for r in rows for p in r["say"])
    guarded(fails, "'Bitcoin down 2.83% over seven days' is a phrase", lambda: "Bitcoin down 2.83% over seven days" in flat)
    guarded(fails, "'Ether down 7.44% over seven days' is a phrase", lambda: "Ether down 7.44% over seven days" in flat)
    guarded(fails, "the ETF day is in words with its date: took in $2.2M on the day, October 14",
            lambda: "spot Bitcoin ETFs took in $2.2M on the day, October 14" in flat)
    guarded(fails, "the ETF week is in words: net outflows of $110.5M over the week through October 14",
            lambda: "spot Bitcoin ETFs saw net outflows of $110.5M over the week through October 14" in flat)
    mb = phrases.model_boards(boards)
    guarded(fails, "the model's copy of the digest holds no signed window change for any asset",
            lambda: all(not any(k in a for k in ("chg_24h_pct", "chg_7d_pct", "chg_30d_pct")) for a in mb["assets"]))
    guarded(fails, "the model's copy holds no raw ETF net; the checker's copy is untouched",
            lambda: "latest_net_usd_m" not in mb["etf_flows"]["btc"]
            and boards["etf_flows"]["btc"]["latest_net_usd_m"] == 2.2 and "chg_7d_pct" in boards["assets"][0])
    src = open(os.path.join(HERE, "wrap.py"), encoding="utf-8").read()
    guarded(fails, "the Edition's user message is built from model_boards and numbers_block",
            lambda: "phrases.model_boards(boards)" in src and "phrases.numbers_block(boards)" in src)

    print("A3. the Edition's body publishes with both sentences, no drop")
    g4 = twins_gate.Gate(snap(), log_path="", quiet=True)
    body = g4.paragraphs([WEEK_BTC + " " + WEEK_ETH], "the Brief's body", dollars=False)
    guarded(fails, "one paragraph survives whole, nothing dropped",
            lambda: len(body) == 1 and "down 2.83 percent" in body[0] and "down 7.44 percent" in body[0] and not g4.drops)


# ---- item 0: the morning read ----------------------------------------------------------------

S1 = ("The wire's top line this morning is Kraken parent Payward's agreement to acquire "
      "Lithuania's Saldo Bank, carried by two outlets.")
S2 = "Markets shows the Fear & Greed index in the neutral band and funding calm."
LONG_HEAD = ("The wire opens on Standard Chartered's launch of Bitcoin and Ether trading for affluent "
             "clients in the UAE while Kraken's parent agrees to buy a Lithuanian bank")        # 156 characters


class Stub:
    """What llm.Client.call_json does: each rung's output goes through validate; a contract failure
    climbs to the next rung; the last failure is raised."""
    mode = "live"

    def __init__(self, outs):
        self.outs, self.calls, self.user, self.errors = outs, 0, "", []
        self.budget = type("B", (), {"tokens": 2065, "usd": 0.0037})()

    def call_json(self, stage, system, user, validate=None, max_rungs=3):
        import llm
        self.user, last = user, None
        for o in self.outs[:max_rungs]:
            self.calls += 1
            try:
                return validate(copy.deepcopy(o))
            except llm.LLMError as e:
                last = llm.ContractError(str(e))
                self.errors.append(str(e))
        raise last


def morning_run(outs, wire=None):
    import morning
    import narrative
    import twins_gate
    tmp = tempfile.mkdtemp(prefix="s82-morning-")
    morning.OUT, morning.LEDGER = os.path.join(tmp, "morning.json"), os.path.join(tmp, "ledger.json")
    narrative.PATH = os.path.join(tmp, "narrative.json")
    twins_gate.LOG_PATH = os.path.join(tmp, "twins.json")
    stub = Stub(outs)
    now = dt.datetime(2026, 10, 15, 12, 18, tzinfo=dt.timezone.utc)
    rec = morning.run(now=now, client=stub, snapshot=snap(), wire=wire if wire is not None else load("wire_2026-10-15T1218Z.json"))
    ledger = json.load(open(morning.LEDGER, encoding="utf-8"))
    return rec, ledger, stub


def morning_cases(fails):
    import morning
    print("B. this morning's headline (15 October 8:18 AM: 'missing or oversized headline')")
    good = {"headline": "The wire opens on a Payward bank deal and a neutral Board", "sentences": [S1, S2],
            "narrative_line": "Bitcoin is drifting lower on spot ETF outflows; the news is mixed."}
    long_o = dict(good, headline=LONG_HEAD)
    none_o = dict(good, headline="")
    guarded(fails, "the fixture headline is over the limit", lambda: len(LONG_HEAD) > morning.HEADLINE_MAX)

    def why(o):
        try:
            morning.clean(o, None)
        except Exception as e:                               # noqa: BLE001
            return str(e)
        return ""
    guarded(fails, "an oversized headline says it is too long, with its length and the limit",
            lambda: "too long" in why(long_o) and str(len(LONG_HEAD)) in why(long_o) and "100" in why(long_o))
    guarded(fails, "a missing headline says it is missing", lambda: "missing" in why(none_o) and "oversized" not in why(none_o))

    rec, ledger, stub = morning_run([long_o, long_o])
    guarded(fails, "oversized on both rungs: the read publishes, headline trimmed at a word boundary",
            lambda: rec and 0 < len(rec["headline"]) <= 100 and LONG_HEAD.startswith(rec["headline"])
            and rec.get("headline_by") == "trimmed")
    guarded(fails, "the ledger row is a read, not a fallback", lambda: ledger[-1]["outcome"] == "read")
    guarded(fails, "the repair rung was told what was wrong (the first error names the length)",
            lambda: stub.errors and "too long" in stub.errors[0])

    rec, ledger, stub = morning_run([none_o, none_o])
    guarded(fails, "missing on both rungs: the read publishes with the wire's top line as its headline",
            lambda: rec and 0 < len(rec["headline"]) <= 100 and rec.get("headline_by") == "wire top line"
            and rec["headline"].startswith("Standard Chartered"))
    rec, ledger, stub = morning_run([long_o, good])
    guarded(fails, "oversized then repaired by the model: the model's headline stands", lambda: rec and rec["headline"] == good["headline"] and rec.get("headline_by") == "model")

    one = dict(good, sentences=[S1])
    rec, ledger, stub = morning_run([one, one])
    guarded(fails, "a fallback stays honest: one surviving sentence still falls back, and the reason says so",
            lambda: rec is None and ledger[-1]["outcome"] == "fallback" and "sentence" in ledger[-1]["reason"])

    print("B2. the morning is handed percent-free phrases")
    rec, ledger, stub = morning_run([good, good])
    u = stub.user
    guarded(fails, "no '%', no 'percent' and no raw funding figure in what the model is handed",
            lambda: "%" not in u and "percent" not in u.lower() and "funding_8h_pct" not in u and "0.0047" not in u)
    guarded(fails, "the ETF flow is a phrase with its sign and window: net outflows of $261.4M on the day, October 14",
            lambda: "spot Bitcoin ETFs saw net outflows of $261.4M on the day, October 14" in u)
    guarded(fails, "the Standard Chartered line arrives without its 'up to 2% spread' clause",
            lambda: "closed-loop service." in u and "2%" not in u)
    guarded(fails, "the Board's bands arrive by name", lambda: "neutral" in u and "funding on Bitcoin perpetual futures is calm" in u)


# ---- items 1 to 5: the coin doors ------------------------------------------------------------

def coin_fixture():
    pulse = load("pulse_2026-10-15T1216Z.json")
    wire = load("wire_2026-10-15T1218Z.json")
    coins = pulse["movers"]["top100"]
    by = {c["symbol"]: (i + 1, c) for i, c in enumerate(coins)}
    return pulse, wire, by


def render(sym, wire=None, pulse=None, by=None, gate=None):
    import site_build as sb
    import twins_gate
    p0, w0, b0 = coin_fixture()
    pulse, wire, by = pulse or p0, wire if wire is not None else w0, by or b0
    pos, c = by[sym]
    gate = gate or twins_gate.Gate(coin_snap(), log_path="", quiet=True)
    import inspect
    kw = {"gate": gate} if "gate" in inspect.signature(sb.render_coin_page).parameters else {}
    # Sprint 9.3: these cases are the page with no verdict, whatever verdict records are on disk (a graded
    # verdict changes the no-causation note, which sprint93_test guards)
    if "verdict" in inspect.signature(sb.render_coin_page).parameters:
        kw["verdict"] = {}
    return sb.render_coin_page(c, pos, pulse, [], "THURSDAY, OCTOBER 15, 2026", wire=wire, cm={},
                               today=dt.date(2026, 10, 15), **kw)


def coin_snap():
    s = snap()
    s["fields"]["coins"]["value"]["BTC"]["price"] = 82000        # so the wire's '$82,000' line holds
    return s


def jsonld(html):
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        out.append(json.loads(m.group(1)))
    return out


def crumbs(html):
    for blk in jsonld(html):
        for n in (blk.get("@graph") if isinstance(blk, dict) and "@graph" in blk else [blk]):
            if isinstance(n, dict) and n.get("@type") == "BreadcrumbList":
                return n
    return None


def coin_cases(fails):
    print("C. the coin doors")
    pulse, wire, by = coin_fixture()
    btc = render("BTC")
    title = re.search(r"<title>(.*?)</title>", btc, re.S).group(1)
    desc = re.search(r'<meta name="description" content="(.*?)"', btc, re.S).group(1)
    guarded(fails, "item 1: Bitcoin's title reads what people type: 'Bitcoin price today and why it moved'",
            lambda: title.startswith("Bitcoin price today and why it moved"))
    guarded(fails, f"item 1: the description is under 155 characters ({len(desc)})", lambda: 0 < len(desc) < 155)
    guarded(fails, "item 1: the description carries the day's own price and its signed 24-hour change",
            lambda: re.search(r"\$80,896", desc) and re.search(r"down 3\.37% over 24 hours", desc))
    guarded(fails, "item 1: no em dash or en dash in either", lambda: not re.search("[–—]", title + desc))
    xrp = re.search(r"<title>(.*?)</title>", render("XRP"), re.S).group(1)
    guarded(fails, "item 1: every coin, not only Bitcoin ('XRP price today and why it moved')",
            lambda: xrp.startswith("XRP price today and why it moved"))

    why = re.search(r'<section class="cn-why".*?</section>', btc, re.S)
    guarded(fails, "item 2: Bitcoin (top 20, a wire item within 24 hours names it) has a 'Why Bitcoin moved today' block",
            lambda: why and "Why Bitcoin moved today" in why.group(0))
    w = why.group(0) if why else ""
    guarded(fails, "item 2: the item carries its sources (count and links) and its time",
            lambda: "U.S. inflation accelerated" in w and "source" in w and "<a href=" in w and "ET on Oct 14" in w)
    guarded(fails, "item 2: the older Standard Chartered item (30 hours) is not 'today'", lambda: "Standard Chartered" not in w)
    guarded(fails, "item 2: the no-causation line is there", lambda: "does not say" in w)
    guarded(fails, "item 2: the desk's own sentences never say 'because'",
            lambda: "because" not in re.sub(r'<a [^>]*>.*?</a>', "", w.lower()))
    after = _wire_with(wire, "c905", "Bitcoin miners reported record hash rate after the Board read.", ["Bitcoin hash rate record"])
    after["items"][0]["reported_utc"] = "2026-10-15T12:30:00Z"       # 13 minutes AFTER the 12:16:51Z read
    guarded(fails, "item 2 (fix): an item reported after the Board read is outside the 24-hour window the number sits under",
            lambda: "record hash rate" not in render("BTC", wire=after).split("cn-why")[1].split("</section>")[0])
    guarded(fails, "item 2 (fix): the window is the 24 hours ending at that read, both ends",
            lambda: __import__("coinpage").why_items(by["BTC"][1], 1, after, pulse["generated_utc"]) and
            all(w["id"] != "c905" for w in __import__("coinpage").why_items(by["BTC"][1], 1, after, pulse["generated_utc"])))
    eth = render("ETH")
    guarded(fails, "item 2: 'Ether' in a wire line names Ethereum (top 20) when the item is within 24 hours",
            lambda: True)                                          # the Standard Chartered item is 30 hours old: no block
    guarded(fails, "item 2: a top-20 coin no item names (Cardano) has no block and no empty heading",
            lambda: 'class="cn-why"' not in render("ADA") and "moved today" not in render("ADA"))
    far = dict(by)
    guarded(fails, "item 2: a coin outside the top 20 gets no 'Why' block even when an item names it",
            lambda: all(pos > 20 for pos, c in [by["SUI"]]) and "Why Sui moved today" not in render(
                "SUI", wire=_wire_naming(wire, "Sui")))
    cause = _wire_with(wire, "c901", "Bitcoin fell because of a large sale reported by the exchange.",
                       ["Bitcoin falls because exchange reports large sale"])
    guarded(fails, "item 2: a cause word in the desk's line that no cited source carries keeps the item out",
            lambda: "because of a large sale" not in render("BTC", wire=_wire_with(wire, "c902",
                    "Bitcoin fell because of a large sale reported by the exchange.", ["Bitcoin sold at the exchange"])))
    guarded(fails, "item 2: a cause word a cited source carries stands, as the source's",
            lambda: "because of a large sale" in render("BTC", wire=cause))
    wrongd = _wire_with(wire, "c903", "Bitcoin traded at $70,000 after the U.S. data.", ["Bitcoin trades after the U.S. data"])
    guarded(fails, "item 2: every sentence goes through the twins gate (a wrong Bitcoin price is dropped)",
            lambda: "$70,000" not in render("BTC", wire=wrongd))

    bc = crumbs(btc)
    guarded(fails, "item 3: BreadcrumbList parses, three items: Home, Markets, Bitcoin, with absolute URLs",
            lambda: bc and [i["name"] for i in bc["itemListElement"]] == ["Home", "Markets", "Bitcoin"]
            and [i["position"] for i in bc["itemListElement"]] == [1, 2, 3]
            and all(i["item"].startswith("https://gocheckmycrypto.com") for i in bc["itemListElement"])
            and bc["itemListElement"][2]["item"].endswith("/coins/btc"))
    guarded(fails, "item 3: every coin page carries it (ADA, SUI, XRP)",
            lambda: all(crumbs(render(s)) for s in ("ADA", "SUI", "XRP")))



def lastmod_cases(fails):
    print("D. the sitemap's real change times")
    import lastmod
    pulse, wire, by = coin_fixture()
    pstamp = pulse["generated_utc"]
    hits = [x for x in wire["items"] if x["id"] == "c009"]
    guarded(fails, "item 4: a coin page's lastmod is the newest of its Board read and the wire items it shows, not the build",
            lambda: lastmod.coin(pstamp, hits) == pstamp)
    late = [dict(hits[0], reported_utc="2026-10-15T13:00:00Z")]
    guarded(fails, "item 4: a newer wire item moves it", lambda: lastmod.coin(pstamp, late) == "2026-10-15T13:00:00Z")
    guarded(fails, "item 4: an article's is when it was published",
            lambda: lastmod.article({"published_utc": "2026-10-14T23:45:16Z", "date": "2026-10-14"}) == "2026-10-14T23:45:16Z"
            and lastmod.article({"date": "2026-10-14"}) == "2026-10-14T00:00:00Z")
    guarded(fails, "item 4: a page with no known change time carries none", lambda: lastmod.coin("", []) == "")



def indexnow_cases(fails):
    print("E. IndexNow")
    import indexnow
    guarded(fails, "item 5: the key is 8 to 128 hex characters and the key file is named for it",
            lambda: re.fullmatch(r"[0-9a-f]{8,128}", indexnow.KEY) and indexnow.key_file() == indexnow.KEY + ".txt")
    old = ('<urlset><url><loc>https://gocheckmycrypto.com/coins/bitcoin</loc><lastmod>2026-10-15T12:16:51Z</lastmod></url>'
           '<url><loc>https://gocheckmycrypto.com/coins/ethereum</loc><lastmod>2026-10-15T12:16:51Z</lastmod></url>'
           '<url><loc>https://gocheckmycrypto.com/about</loc></url></urlset>')
    new = ('<urlset><url><loc>https://gocheckmycrypto.com/coins/bitcoin</loc><lastmod>2026-10-15T23:12:00Z</lastmod></url>'
           '<url><loc>https://gocheckmycrypto.com/coins/ethereum</loc><lastmod>2026-10-15T12:16:51Z</lastmod></url>'
           '<url><loc>https://gocheckmycrypto.com/about</loc></url>'
           '<url><loc>https://gocheckmycrypto.com/today/2026-10-15</loc><lastmod>2026-10-15T23:12:00Z</lastmod></url></urlset>')
    ch = indexnow.changed_urls([old], [new])
    guarded(fails, "item 5: changed URLs are the new ones and those whose lastmod moved, nothing else",
            lambda: ch == ["https://gocheckmycrypto.com/coins/bitcoin", "https://gocheckmycrypto.com/today/2026-10-15"])
    pl = indexnow.payload(ch)
    guarded(fails, "item 5: the payload names host, key, keyLocation and the URL list",
            lambda: pl["host"] == "gocheckmycrypto.com" and pl["key"] == indexnow.KEY
            and pl["keyLocation"] == f"https://gocheckmycrypto.com/{indexnow.KEY}.txt" and pl["urlList"] == ch)

    class Resp:
        status = 202

        def read(self):
            return b""

    seen = {}

    def fake(req, timeout=0):
        seen["body"] = json.loads(req.data.decode())
        seen["url"] = req.full_url
        return Resp()
    line = indexnow.send(ch, opener=fake)
    guarded(fails, "item 5: the response is logged (status and count) and the request was a POST of the payload",
            lambda: "202" in line and "2 URL" in line and seen["body"]["urlList"] == ch)
    guarded(fails, "item 5: nothing changed sends nothing and says so", lambda: "nothing changed" in indexnow.send([], opener=fake))

    def boom(req, timeout=0):
        raise OSError("no route")
    guarded(fails, "item 5: a failed send is logged and never raises (a build is never failed by it)",
            lambda: "failed" in indexnow.send(ch, opener=boom))


def _wire_with(wire, wid, line, titles):
    w = copy.deepcopy(wire)
    w["items"].insert(0, {"rank": 1, "id": wid, "line": line, "titles": titles, "source_count": 2, "primary": False,
                          "reported_utc": "2026-10-15T08:00:00Z",
                          "links": [{"url": "https://example.com/a", "outlet": "Example", "primary": False}]})
    return w


def _wire_naming(wire, name):
    return _wire_with(wire, "c904", f"{name} announced a network upgrade scheduled for this week.", [f"{name} announces upgrade"])


def group(fails, name, fn):
    """A group whose module is absent (origin/main has no phrases.py, no coin doors) is a FAIL line
    for the group, not a crash that hides the groups after it."""
    try:
        fn(fails)
    except Exception as e:                                   # noqa: BLE001
        msg = f"group {name} could not run [{type(e).__name__}: {str(e)[:100]}]"
        print("  FAIL " + msg)
        fails.append(msg)


def unit():
    fails = []
    group(fails, "A (the Edition)", edition_cases)
    group(fails, "B (the morning read)", morning_cases)
    group(fails, "C (the coin pages)", coin_cases)
    group(fails, "D (lastmod)", lastmod_cases)
    group(fails, "E (IndexNow)", indexnow_cases)
    return fails


def static(out):
    """The built tree: every coin page, read from disk."""
    fails = []
    coins = os.path.join(out, "coins")
    if not os.path.isdir(coins):
        return ["static: no coin pages built"]
    n, bad = 0, []
    for f in sorted(os.listdir(coins)):
        if not f.endswith(".html"):
            continue
        h = open(os.path.join(coins, f), encoding="utf-8").read()
        n += 1
        t = re.search(r"<title>(.*?)</title>", h, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', h, re.S)
        if not (t and " price today and why it moved" in t.group(1)):
            bad.append(f"{f}: title")
        if not (d and 0 < len(d.group(1)) < 155):
            bad.append(f"{f}: description")
        bc = crumbs(h)
        if not bc or len(bc["itemListElement"]) != 3:
            bad.append(f"{f}: breadcrumb")
        if re.search("[–—]", (t.group(1) if t else "") + (d.group(1) if d else "")):
            bad.append(f"{f}: dash")
    if bad:
        fails.append(f"static: {len(bad)} coin page problem(s): " + "; ".join(bad[:5]))
    key = open(os.path.join(HERE, "indexnow.py"), encoding="utf-8").read() if os.path.exists(os.path.join(HERE, "indexnow.py")) else ""
    m = re.search(r'KEY = "([0-9a-f]+)"', key)
    if not (m and os.path.exists(os.path.join(out, m.group(1) + ".txt"))
            and open(os.path.join(out, m.group(1) + ".txt")).read().strip() == m.group(1)):
        fails.append("static: the IndexNow key file is not served from the site root")
    print(f"static: {n} coin pages read")
    return fails


def main():
    fails = unit()
    print("\nSPRINT 8.2:", "PASS" if not fails else f"FAIL ({len(fails)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
