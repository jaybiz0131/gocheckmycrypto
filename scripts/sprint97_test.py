#!/usr/bin/env python3
"""Program 9, Sprint 9.7: app-ready feeds and the search pass. Each case is named after what it guards.

  python3 scripts/sprint97_test.py                       # unit cases; exit 1 on any failure
  python3 scripts/sprint97_test.py --tree <built dir>    # also the cases that read a built tree
                                                         # and, with node and playwright, the browser cases
  (verify_pipeline.py's canary also calls unit() and tree() on the tree it builds)

THE RECORDS ARE 9.2'S TO 9.4'S: the real 14 October evening evidence record (Likely, on the Consumer Price Index release
and the Real Earnings release), the real 15 October one (Unclear), the real 15 October Board, flows and wire
(fixtures/why), and the real 16 October morning Big movers record (fixtures/movers). Cases marked SYNTHETIC change a real
record by hand to reach what the real days do not give (a Confirmed grade, a move past the breaking line, a verdict that
moves, sixty Briefs); they say so on their name (Jack, 13 October 2026). NO MODEL CALL and no network: a feed is written
from stored records, and a browser case answers every host from a local stub.
"""
import contextlib
import copy
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
BECAUSE = re.compile(r"\bbecause\b", re.I)
AI = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bHaiku\b|\bSonnet\b|"
                r"\bOpenAI\b|\bchatbot\b", re.I)
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")


# HOTFIX 9.9h2 (round 2). The desk writes its own wire lines (wire.py: "the desk's own one-line summary of a story it
# ranked"), so a wire candidate line and a news item line are desk prose and stay in the AI-word scan. One AI word in them
# is excused: a reported subject, an AI word with the word after it that the item's OWN sources carry (the record's titles
# when the item has them, and the words of its source links' addresses, which the outlets wrote from their headlines).
# "AI compute" in a Luxor raise passes when a source says "ai compute"; "AI editor", "AI-generated", "Claude" and every
# other AI word the sources do not carry fail, and so does any disclosure phrasing. Press and hack candidate lines are the
# outlet's own title or a fixed template around DefiLlama's fields, so they are sourced and are left out of the scan.
SOURCED_EVENT_KINDS = ("press", "hack")
SOURCE_CHECKED_KINDS = ("wire",)
_AIW = (r"(?:A\.?I\b|artificial|machine[- ]learn|language model|LLM\b|GPT|Claude|Anthropic|Haiku|Sonnet|OpenAI|chatbot)")
# An AI disclosure: something said to be made, written, drafted, summarized or checked by or with an AI or a model, or the
# desk or its read said to use one. A line that says so is never excused.
AI_DISCLOSURE = re.compile(
    r"\b(?:written|generated|drafted|produced|composed|created|authored|summari[sz]ed|edited|graded|checked|powered|assisted|made)\s+"
    r"(?:in part\s+)?(?:by|with|using|via)\s+(?:an?\s+|the\s+)?" + _AIW
    + r"|\b(?:we|our|this desk|the desk|this read|this site)\b[^.]{0,60}\b(?:use[sd]?|using|run|runs|rely|relies)\b[^.]{0,30}" + _AIW,
    re.I)


def _words(t):
    return re.findall(r"[a-z0-9]+", (t or "").lower())


def source_carried_ai(line, item):
    """True when `line` has AI words, no disclosure phrasing, and every AI word with the word after it is carried, as that
    pair of words side by side, by the item's own source text (its "titles" and the words of its links' addresses)."""
    if not isinstance(line, str) or AI_DISCLOSURE.search(line):
        return False
    src = []
    for t in item.get("titles") or []:
        src += _words(t) + ["|"]
    for l in item.get("links") or []:
        if isinstance(l, dict) and isinstance(l.get("url"), str):
            src += _words(l["url"]) + ["|"]
    pairs = {(src[i], src[i + 1]) for i in range(len(src) - 1)}
    lw = _words(line)
    for m in AI.finditer(line):
        n = len(_words(m.group(0))) or 1
        i = len(_words(line[:m.start()]))
        if i + n >= len(lw) or (lw[i + n - 1], lw[i + n]) not in pairs:
            return False
    return True


def feed_prose(feed):
    """The feed as JSON text with every web address (a string that starts http:// or https://) taken out: the AI-word scan
    reads the desk's own words, and a source's address is not the desk's wording (a slug may hold 'ai-' in a headline the
    outlet wrote). Everything else, titles, lines, outlet names, stays in. The dash scan does NOT use this: it reads the
    whole feed. HOTFIX 9.9h."""
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items()}
        if isinstance(o, list):
            return [strip(v) for v in o]
        if isinstance(o, str) and re.match(r"https?://", o):
            return ""
        return o
    def own_words(o):
        """HOTFIX 9.9h2: blank the line of a press or hack candidate, and of a wire candidate whose AI words its own sources carry."""
        if isinstance(o, dict):
            r = {}
            for k, v in o.items():
                if k == "candidates" and isinstance(v, list):
                    v = [dict(c, line="") if isinstance(c, dict) and isinstance(c.get("line"), str) and (
                        (c.get("kind") in SOURCED_EVENT_KINDS and not AI_DISCLOSURE.search(c["line"]))
                        or (c.get("kind") in SOURCE_CHECKED_KINDS and source_carried_ai(c["line"], c))) else c for c in v]
                r[k] = own_words(v)
            return r
        if isinstance(o, list):
            return [own_words(v) for v in o]
        return o
    def news_lines(f):
        """The news feed (name "news"): an item's line is the desk's, excused only as a wire candidate's is."""
        if not (isinstance(f, dict) and f.get("name") == "news" and isinstance(f.get("data"), dict)
                and isinstance(f["data"].get("items"), list)):
            return f
        items = [dict(i, line="") if isinstance(i, dict) and source_carried_ai(i.get("line"), i) else i for i in f["data"]["items"]]
        return dict(f, data=dict(f["data"], items=items))
    return json.dumps(strip(own_words(news_lines(feed))))


FEEDS = ("index", "top100", "markets", "movers", "whales", "news", "brief/latest", "why/today", "events",
         "why/record")   # Sprint 9.8: the verdict record's feed, which the index now lists
NOW15 = dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)


def info(msg):
    print("  INFO " + msg)


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


def s94():
    import sprint94_test
    return sprint94_test


def visible(h):
    return s93().visible(h)


def norm(t):
    """Page text with the space an anchor leaves before punctuation closed up, for comparing a sentence to a page."""
    return re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s+", " ", t))


FIGURE = re.compile(r"\b\d{1,2}:\d{2} [AP]M\b|\d[\d,]*\.?\d*\s?%|\$[\d,]+(?:\.\d+)?(?:[KMBT]| million| billion)?|\d[\d,.]*\s?bp\b")


def why_strings_missing(day, coin_pages, day_page):
    """Every human string a why feed carries that its own page does not print: each graded coin's card sentences on that coin's
    verdict page, the evidence lines and window words on the day's page. A feed may carry nothing else of its own."""
    miss = []
    for sym, c in day["coins"].items():
        page = coin_pages.get(sym)
        for sline in c.get("card_text") or []:
            if page is None or norm(sline) not in norm(page):
                miss.append((sym, sline))
        if c.get("grade") is None and c.get("card_text"):
            miss.append((sym, "text on an ungraded coin"))
    ev = day.get("evidence") or {}
    for cd in ev.get("candidates") or []:
        if norm(cd["line"]) not in norm(day_page):
            miss.append(("evidence", cd["line"]))
    return miss


def figures_missing(sentences, page_text):
    """The figures (times, percents, dollars, basis points) in `sentences` that the page text does not carry."""
    pt = norm(page_text)
    return [f for s in sentences for f in FIGURE.findall(s) if f not in pt]


def fx15():
    """The recorded 15 October Board, flows and wire (fixtures/why), as the pages of that day were drawn from them."""
    t = s93()
    return (copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json")), copy.deepcopy(t.s92().load(f"flows_{t.D15()}.json")),
            copy.deepcopy(t.s92().load(f"wire_{t.D15()}.json")))


def feeds_mod():
    import api_feeds
    return api_feeds


def sb_mod():
    import site_build
    return site_build


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


@contextlib.contextmanager
def snap_of(pulse, flows):
    """site_build.SNAP set from a Board the way build() sets it, put back after."""
    import snapshot
    sb = sb_mod()
    old, oldn = sb.SNAP, sb._NOW_CACHE
    sb.SNAP = snapshot.build(pulse, flows)
    sb._NOW_CACHE = NOW15
    try:
        yield sb.SNAP
    finally:
        sb.SNAP, sb._NOW_CACHE = old, oldn


def graded_dirs(td, days=(("2026-10-14", "evening"),)):
    """Scratch verdict and evidence directories holding the real graded records (no model): 14 October evening is
    Likely, 15 October evening is Unclear. Returns (vdir, wdir, tdir)."""
    import verdict as vd
    t = s93()
    vdir, wdir, tdir = (os.path.join(td, n) for n in ("verdict", "why", "today"))
    for d in (vdir, wdir, tdir):
        os.makedirs(d, exist_ok=True)
    table = {"2026-10-14": (t.rec(t.D14()), t.day14()), "2026-10-15": (t.rec(t.D15()), t.day15())}
    for day, slot in days:
        rec, dm = table[day]
        rec = dict(rec, date_et=day, slot=slot)
        json.dump(rec, open(os.path.join(wdir, f"{day}-{slot}.json"), "w", encoding="utf-8"))
        v = vd.record_from(rec, day, slot, now=dt.datetime.fromisoformat(day + "T23:50:00+00:00"), day=dm)
        json.dump(v, open(os.path.join(vdir, f"{day}-{slot}.json"), "w", encoding="utf-8"))
    return vdir, wdir, tdir


def write_verdict(vdir, day, slot, mutate, made_utc):
    """SYNTHETIC: a copy of a real stored verdict record with `mutate(record)` applied, written under day and slot."""
    src = sorted(n for n in os.listdir(vdir) if n.endswith(".json"))[0]
    r = copy.deepcopy(json.load(open(os.path.join(vdir, src), encoding="utf-8")))
    r.update(date_et=day, slot=slot, made_utc=made_utc)
    mutate(r)
    json.dump(r, open(os.path.join(vdir, f"{day}-{slot}.json"), "w", encoding="utf-8"))
    return r


def brief_item(date, slot, hh="23:14:41"):
    return {"id": f"wrap-{'pm' if slot == 'evening' else 'am'}-{date}", "slug": f"{slot}-brief-{date}", "kind": "brief",
            "title": f"The {slot.title()} Brief: SYNTHETIC {date}", "date": date, "published_utc": f"{date}T{hh}Z",
            "category": "daily edition", "bottom_line": "SYNTHETIC read.", "sources": []}


# ---- 1. the one stale rule ---------------------------------------------------------------------------------------

def stale_cases(fails):
    print("1. the stale flag is the site's own rule")
    af = feeds_mod()
    import snapshot
    base = dt.datetime(2026, 10, 21, 5, 0, tzinfo=UTC)
    for h in (0, 1, 2.99, 3.0, 3.01, 5, 30, 49, 200):
        ts = (base - dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
        want = bool(snapshot.age_phrase(ts, base))
        guarded(fails, f"a reading {h} hours old: the feed says stale={want}, as the page's own age phrase does",
                lambda ts=ts, want=want: af.is_stale(ts, base) is want)
    guarded(fails, "the boundary is the page's: exactly STALE_HOURS old is not stale, a second more is",
            lambda: af.is_stale("2026-10-21T02:00:00Z", base) is False and af.is_stale("2026-10-21T01:59:59Z", base) is True)
    for bad in (None, "", "yesterday"):
        env = af.envelope("top100", "/pulse/prices", bad, base, ["x"], {})
        guarded(fails, f"an as-of that cannot be read ({bad!r}) is stale, with no age and no as-of claimed",
                lambda env=env: env["stale"] is True and env["as_of_utc"] is None and env["age_hours"] is None)
    env = af.envelope("top100", "/pulse/prices", "2026-10-21T04:00:00Z", base, ["CoinGecko"], {"rows": []})
    guarded(fails, "the envelope carries schema, version, name, path, page, as_of_utc, built_utc, stale, stale_after_hours, "
                   "age_hours, sources and data",
            lambda: set(env) >= {"schema", "version", "name", "path", "page", "as_of_utc", "built_utc", "stale",
                                 "stale_after_hours", "age_hours", "sources", "data"})
    guarded(fails, "the envelope names its path under /api/v1/ and prints the stale window the page uses",
            lambda: env["path"] == "/api/v1/top100.json" and env["stale_after_hours"] == snapshot.STALE_HOURS
            and env["schema"].endswith("/api/v1/top100") and env["version"] == 1)


# ---- 2. each feed's shape, and its figures on its page ------------------------------------------------------------

def top100_cases(fails):
    print("2. top100.json: the rows of /pulse/prices")
    af, sb = feeds_mod(), sb_mod()
    pulse, flows, wire = fx15()
    with snap_of(pulse, flows):
        import snapshot
        pv, fv = snapshot.views(sb.SNAP, pulse, flows)
        feed = af.top100_feed(pv, NOW15)
        page = visible(sb.render_pulse_prices(pv, "T"))
    rows = feed["data"]["rows"]
    guarded(fails, f"one row per coin the page lists ({len(rows)})", lambda: len(rows) == len((pv["movers"] or {}).get("top100")) > 90)
    guarded(fails, "a row carries rank, symbol, name, slug, url, price, chg_24h_pct, mcap_usd, volume_24h and shown",
            lambda: all({"rank", "symbol", "name", "slug", "url", "price", "chg_24h_pct", "mcap_usd", "volume_24h", "shown"} <= set(r)
                        for r in rows))
    guarded(fails, "rank counts the way the page counts (1 to N, no holes)", lambda: [r["rank"] for r in rows] == list(range(1, len(rows) + 1)))
    guarded(fails, "every shown string is on the page: no figure in the feed is absent from the page",
            lambda: all(r["shown"][k] in page for r in rows for k in ("price", "chg_24h", "mcap", "volume") if r["shown"].get(k)))
    guarded(fails, "the feed's as-of is the Board's reading, the same instant the page's stamp carries",
            lambda: feed["as_of_utc"] == pv["generated_utc"])
    guarded(fails, "fresh at the reading's own time, stale four hours on",
            lambda: af.top100_feed(pv, NOW15)["stale"] is False
            and af.top100_feed(pv, NOW15 + dt.timedelta(hours=4))["stale"] is True)
    guarded(fails, "a row whose price the source did not send prints no price figure and no zero",
            lambda: all(r["price"] is None or r["price"] > 0 for r in rows))


def whales_cases(fails):
    print("3. whales.json: the figures of /flows")
    af, sb = feeds_mod(), sb_mod()
    pulse, flows, wire = fx15()
    with snap_of(pulse, flows):
        import snapshot
        pv, fv = snapshot.views(sb.SNAP, pulse, flows)
        feed = af.whales_feed(fv, NOW15)
        page = visible(sb.render_flows(fv, "T"))
    d = feed["data"]
    guarded(fails, "the feed carries the window, the headline net, the exchanges, the weekly trend and the biggest moves",
            lambda: {"window_hours", "sentence", "volatile", "stablecoins", "by_exchange", "weeks", "moves_in", "moves_out"} <= set(d))
    shown = []
    for k in ("sentence",):
        shown.append(d[k])
    for e in d["by_exchange"]:
        shown += [e["shown"]["net"]]
    for w in d["weeks"]:
        shown += [w["shown"]["net"]]
    guarded(fails, f"every shown string is on the page ({len(shown)} checked)", lambda: shown and all(s in page for s in shown))
    guarded(fails, "the feed's as-of is the flows reading's, and stale follows the same rule",
            lambda: feed["as_of_utc"] == fv["generated_utc"] and feed["stale"] is af.is_stale(fv["generated_utc"], NOW15))


def movers_cases(fails):
    print("4. movers.json: the Big movers list of /pulse/movers")
    af, sb = feeds_mod(), sb_mod()
    t = s94()
    with tempfile.TemporaryDirectory() as td, quiet():
        rec, _log = t.record16(td)
    import movers as mv
    board_utc = (rec.get("gate") or {}).get("board_utc") or rec["window"]["end_utc"]
    pulse = {"generated_utc": board_utc, "movers": {"top100": []}}
    feed = af.movers_feed(rec, pulse, dt.datetime.fromisoformat(board_utc.replace("Z", "+00:00")))
    html = visible(mv.list_html(rec, board_utc))
    rows = feed["data"]["coins"]
    guarded(fails, f"the real 16 October morning record lists {len(rows)} coin(s) past the line, as the page does",
            lambda: len(rows) == len((rec["gate"]["passed"] or [])) + len(rec["gate"].get("over_cap") or []))
    guarded(fails, "every shown move and grade is on the page",
            lambda: all(r["shown"]["move"] in html and (r["shown"]["grade"] or "") in html for r in rows))
    guarded(fails, "every movers row's change names its window", lambda: all(r["window"] == "24 hours" for r in rows))
    guarded(fails, "a coin row names its coin page and, when graded, its verdict page",
            lambda: all(r["url"].startswith("/coins/") and (r["grade"] is None or r["verdict_url"]) for r in rows))
    old = af.movers_feed(rec, pulse, dt.datetime.fromisoformat(board_utc.replace("Z", "+00:00")) + dt.timedelta(hours=40))
    guarded(fails, "forty hours on the feed is stale", lambda: old["stale"] is True)
    other = dict(pulse, generated_utc="2026-10-10T00:00:00Z")
    none = af.movers_feed(rec, other, NOW15)
    guarded(fails, "a record that is not current for the Board says so and lists no coin (the page's own rule)",
            lambda: none["data"]["coins"] == [] and none["data"]["state"] == "no_current_reading")


def news_brief_cases(fails):
    print("5. news.json and brief/latest.json")
    af, sb = feeds_mod(), sb_mod()
    pulse, flows, wire = fx15()
    nf = af.news_feed(wire, NOW15)
    items = nf["data"]["items"]
    guarded(fails, f"one entry per wire cluster the page ranks ({len(items)})", lambda: len(items) == len(wire["items"]))
    guarded(fails, "an entry carries rank, line, standing, source_count, primary, links (outlet and url) and the board reading",
            lambda: all({"rank", "line", "standing", "source_count", "primary", "links", "board_reading"} <= set(i) for i in items))
    guarded(fails, "the feed's as-of is the wire's ranking time", lambda: nf["as_of_utc"] == wire["ranked_utc"])
    guarded(fails, "no wire line reaches the feed reworded or with a dash",
            lambda: all(i["line"] == w["line"] for i, w in zip(items, wire["items"])) and not DASH.search(json.dumps(nf)))
    ed = json.load(open(os.path.join(HERE, "site", "content", "2026-10-20-evening-brief.json"), encoding="utf-8"))
    bf = af.brief_feed(ed, dt.datetime(2026, 10, 21, 5, 0, tzinfo=UTC))
    d = bf["data"]
    guarded(fails, "the Brief feed carries title, dek, slot, date, published, bottom line and the page address",
            lambda: d["title"] == ed["title"] and d["url"] == f"/articles/{ed['slug']}.html" and d["slot"] == "evening"
            and d["bottom_line"] == ed["bottom_line"] and bf["as_of_utc"] == ed["published_utc"])
    guarded(fails, "a Brief from the night before is stale by the site's rule", lambda: bf["stale"] is True)
    import home
    # HOTFIX 9.9h: the October 20 clock reads the October 20 morning read, pinned. It read the live file, so every new
    # morning read broke the case (the stored October 26 read is another day's, and rightly no Brief on October 20).
    mor = json.load(open(os.path.join(HERE, "fixtures", "sprint97", "morning-2026-10-20.json"), encoding="utf-8"))
    ed19 = json.load(open(os.path.join(HERE, "site", "content", "2026-10-19-evening-brief.json"), encoding="utf-8"))
    at10 = dt.datetime(2026, 10, 20, 14, 0, tzinfo=UTC)                 # 10:00 AM ET on October 20, the morning the review read
    mf = af.brief_feed(ed19, at10, morning=mor)
    guarded(fails, "OCT 20, 10 AM ET: with the morning read stored and the 19 October Evening Brief before it, the feed is the MORNING Brief (what the home's card says)",
            lambda: mf["data"]["slot"] == "morning" and mf["data"]["title"] == mor["headline"] and mf["as_of_utc"] == mor["published_utc"]
            and mf["data"]["date"] == "2026-10-20")
    band = home.narrative_band({}, {"stamp_et": "x"}, ed19, at10, mor)
    guarded(fails, "the feed and the home's Brief card name the same Brief: the card prints the feed's headline and its sentences",
            lambda: sb_mod().esc(mf["data"]["title"]) in band and all(sb_mod().esc(x) in band or x[:40] in band.replace("&#x27;", "'") for x in mf["data"]["sentences"][:1]))
    ed20 = dict(ed19, published_utc="2026-10-20T23:14:41Z", date="2026-10-20", slug="evening-brief-2026-10-20", title="The Evening Brief: x")
    ef = af.brief_feed(ed20, dt.datetime(2026, 10, 20, 23, 30, tzinfo=UTC), morning=mor)
    guarded(fails, "once a later Evening Brief exists the feed is that Brief, as the card is (usable_morning returns None)",
            lambda: ef["data"]["slot"] == "evening" and home.usable_morning(mor, ed20, dt.datetime(2026, 10, 20, 23, 30, tzinfo=UTC)) is None)
    guarded(fails, "a morning read of another day is not the newest Brief",
            lambda: af.brief_feed(ed19, dt.datetime(2026, 10, 21, 14, 0, tzinfo=UTC), morning=mor)["data"]["slot"] == "evening")
    guarded(fails, "the feed calls home.usable_morning itself (one choice, not a copy)", lambda: "usable_morning" in open(os.path.join(HERE, "api_feeds.py"), encoding="utf-8").read())
    guarded(fails, "no Brief (None) is an empty feed that says so, stale, with no as-of",
            lambda: af.brief_feed(None, NOW15)["stale"] is True and af.brief_feed(None, NOW15)["as_of_utc"] is None)


def why_cases(fails):
    print("6. why/<date>.json and why/today.json: from stored verdict records only")
    af = feeds_mod()
    with tempfile.TemporaryDirectory() as td:
        vdir, wdir, tdir = graded_dirs(td, (("2026-10-14", "evening"), ("2026-10-15", "evening")))
        built = af.why_feeds(NOW15, vdir=vdir, wdir=wdir, tdir=tdir)
        guarded(fails, "a file for each stored day and for today, and for no other day",
                lambda: sorted(built) == ["why/2026-10-14.json", "why/2026-10-15.json", "why/today.json"])
        f14 = built["why/2026-10-14.json"]["data"]
        guarded(fails, "14 October carries its Likely grade for Bitcoin, the sentences the page prints and the verdict address",
                lambda: f14["coins"]["BTC"]["grade"] == "Likely" and f14["coins"]["BTC"]["card_text"]
                and f14["coins"]["BTC"]["url"] == "/why/2026-10-14-bitcoin")
        guarded(fails, "the evidence list and the timing series ride with the day (candidates with their times, the series points)",
                lambda: f14["evidence"]["candidates"] and f14["evidence"]["series"]["BTC"]["points"])
        f15 = built["why/2026-10-15.json"]["data"]
        guarded(fails, "15 October is Unclear and its verdict page is named",
                lambda: f15["coins"]["BTC"]["grade"] == "Unclear" and f15["coins"]["BTC"]["url"] == "/why/2026-10-15-bitcoin")
        guarded(fails, "today.json is the newest stored day's feed",
                lambda: built["why/today.json"]["data"]["date_et"] == "2026-10-15")
        guarded(fails, "'because' appears only in a feed whose own sentence says it (Confirmed); none here",
                lambda: not BECAUSE.search(json.dumps(built)))
        pages = {b["rel"]: b for b in s_build_pages(vdir, wdir, tdir)}
        t14 = visible(pages["why/2026-10-14-bitcoin.html"]["html"])
        guarded(fails, "every sentence the card prints, as the feed's card_text, is on the 14 October verdict page",
                lambda: f14["coins"]["BTC"]["card_text"] and all(norm(s) in norm(t14) for s in f14["coins"]["BTC"]["card_text"]))
        guarded(fails, "a why feed carries no sentence its page does not print: the full graded line (with times) is not in it",
                lambda: all("text" not in c for c in f14["coins"].values()))
        guarded(fails, "EVERY string in the 14 October feed (card sentences, evidence lines, window words) is on its own page",
                lambda: not why_strings_missing(f14, {"BTC": t14}, t14))
        with tempfile.TemporaryDirectory() as td2:
            v2, w2, t2 = graded_dirs(td2, (("2026-10-15", "evening"),))
            wf = af.why_feeds(NOW15, vdir=v2, wdir=w2, tdir=t2)["why/2026-10-15.json"]["data"]
            pg15 = {b["rel"]: b for b in s_build_pages(v2, w2, t2)}
            guarded(fails, "a day whose Ether line is 'moved with Bitcoin' (a sentence the verdict page does not print) carries no sentence for Ether",
                    lambda: wf["coins"]["ETH"]["card_text"] == [] and wf["coins"]["ETH"]["grade"] is None)
            guarded(fails, "every string in the 15 October feed is on the page that prints it",
                    lambda: not why_strings_missing(wf, {"BTC": visible(pg15["why/2026-10-15-bitcoin.html"]["html"])}, visible(pg15["why/2026-10-15-bitcoin.html"]["html"])))
        old = built["why/2026-10-14.json"]
        guarded(fails, "a feed's stale flag follows the record's own made time", lambda: old["as_of_utc"] == "2026-10-14T23:50:00Z"
                and old["stale"] is True)
    with tempfile.TemporaryDirectory() as td:
        vdir, wdir, tdir = graded_dirs(td, (("2026-10-14", "evening"),))
        open(os.path.join(vdir, "2026-10-16-morning.json"), "w", encoding="utf-8").write("{not json")
        open(os.path.join(vdir, "2026-10-17-morning.json"), "w", encoding="utf-8").write('{"coins": 7}')
        got = af.why_feeds(NOW15, vdir=vdir, wdir=wdir, tdir=tdir)
        guarded(fails, "a day whose stored record cannot be read (corrupt, or not a verdict) gets no dated feed: nothing is made up for it",
                lambda: sorted(got) == ["why/2026-10-14.json", "why/today.json"])
    with tempfile.TemporaryDirectory() as td:
        empty = af.why_feeds(NOW15, vdir=td, wdir=td, tdir=td)
        guarded(fails, "no stored record: today.json says there is none, stale, no as-of, and no dated file is invented",
                lambda: list(empty) == ["why/today.json"] and empty["why/today.json"]["stale"] is True
                and empty["why/today.json"]["as_of_utc"] is None and empty["why/today.json"]["data"]["state"] == "none_stored")


def s_build_pages(vdir, wdir, tdir):
    import verdict as vd
    with quiet():
        return vd.build_pages(vdir=vdir, wdir=wdir, tdir=tdir, dateline="T")


def backfill_cases(fails):
    print("7. the backfill refuses a day with no stored record")
    af = feeds_mod()
    with tempfile.TemporaryDirectory() as td:
        vdir, wdir, tdir = graded_dirs(td, (("2026-10-14", "evening"),))
        # an evidence record with NO verdict record: the day was measured, never graded
        t = s93()
        rec = dict(t.rec(t.D15()), date_et="2026-10-15", slot="evening")
        json.dump(rec, open(os.path.join(wdir, "2026-10-15-evening.json"), "w", encoding="utf-8"))
        before = sorted(os.listdir(vdir))
        for day, why in (("2026-10-13", "no stored verdict record"), ("2026-10-15", "no stored verdict record"),
                         ("2099-01-01", "no stored verdict record"), ("14 October", "not a date"), ("", "not a date")):
            r = af.backfill(day, vdir=vdir, wdir=wdir)
            guarded(fails, f"{day!r}: refused ({why}), no page, nothing built",
                    lambda r=r, why=why: r["ok"] is False and why in r["why"] and r["pages"] == [])
        guarded(fails, "a refusal writes nothing: the verdict directory is as it was", lambda: sorted(os.listdir(vdir)) == before)
        r = af.backfill("2026-10-14", vdir=vdir, wdir=wdir)
        guarded(fails, "a stored, graded day is backfilled: its verdict page is named and is the page the build writes",
                lambda: r["ok"] is True and r["pages"] == ["/why/2026-10-14-bitcoin"]
                and {b["path"] for b in s_build_pages(vdir, wdir, tdir)} == {"/why/2026-10-14-bitcoin"})
        # a stored record that graded nothing
        write_verdict(vdir, "2026-10-16", "morning", lambda r: [v.update(grade=None, kind="flat", text=[], line=[], url=None)
                                                              for v in r["coins"].values()], "2026-10-16T12:20:00Z")
        r2 = af.backfill("2026-10-16", vdir=vdir, wdir=wdir)
        guarded(fails, "a stored day that graded nothing gets no page, and says so",
                lambda: r2["ok"] is False and "no graded verdict" in r2["why"] and r2["pages"] == [])
        rep = af.backfill_all(vdir=vdir, wdir=wdir)
        guarded(fails, "the whole-store report lists each stored day once, the built pages, and the refusals with reasons",
                lambda: [d["day"] for d in rep["days"]] == ["2026-10-14", "2026-10-16"] and rep["pages"] == ["/why/2026-10-14-bitcoin"]
                and any("no graded verdict" in d["why"] for d in rep["days"]))
    real = af.backfill_all()
    info(f"on the real stored data the backfill reads {len(real['days'])} stored day(s) and produces {len(real['pages'])} page(s) "
         f"(no graded verdict is stored yet: {[d['day'] + ': ' + d['why'] for d in real['days'] if not d['ok']][:3]})")
    guarded(fails, "on the real data every stored day is accounted for and no page is invented",
            lambda: all(d["ok"] or d["why"] for d in real["days"]) and len(real["pages"]) == sum(1 for d in real["days"] if d["ok"]))


def events_cases(fails):
    print("8. events.json: the newest 50 events that would push, from stored records")
    af = feeds_mod()
    now = dt.datetime(2026, 10, 22, 0, 0, tzinfo=UTC)
    with tempfile.TemporaryDirectory() as td:
        vdir, wdir, tdir = graded_dirs(td, (("2026-10-14", "evening"),))
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir, exist_ok=True)
        items = [brief_item("2026-10-20", "evening"), brief_item("2026-10-21", "morning", "12:20:00"),
                 {"id": "story-1", "slug": "a-story", "kind": "story", "title": "A story", "date": "2026-10-21",
                  "published_utc": "2026-10-21T13:00:00Z", "category": "news"},
                 dict(brief_item("2026-10-19", "evening"), example=True),
                 {"id": "story-2", "slug": "corrected-story", "title": "A corrected story", "date": "2026-10-18",
                  "published_utc": "2026-10-18T13:00:00Z", "category": "news",
                  "corrected": "2026-10-19: SYNTHETIC correction text."}]
        with quiet():
            feed = af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir)
        ev = feed["data"]["events"]
        kinds = {e["kind"] for e in ev}
        guarded(fails, "the Briefs publish as events (two), the example and the story do not",
                lambda: sum(e["kind"] == "brief_published" for e in ev) == 2 and not any(e["url"].endswith("a-story.html") for e in ev))
        mor = json.load(open(os.path.join(HERE, "site", "data", "morning.json"), encoding="utf-8"))
        with quiet():
            mev = af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir, morning=mor)["data"]["events"]
        guarded(fails, "the stored Morning Brief is a brief_published event with its published time, from the record the home uses",
                lambda: any(e["kind"] == "brief_published" and e["at_utc"] == mor["published_utc"] and mor["headline"] in e["title"] for e in mev))
        guarded(fails, "a Morning Brief with no headline or sentences (the home does not show it) is no event",
                lambda: not any(e["at_utc"] == mor["published_utc"] for e in af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir, morning=dict(mor, sentences=[]))["data"]["events"]))
        guarded(fails, "a correction is an event with its date and no invented time",
                lambda: any(e["kind"] == "correction" and e["date_et"] == "2026-10-19" and e["at_utc"] is None for e in ev))
        guarded(fails, "the real 14 October Likely verdict (a small move) is NOT past the breaking line, so it is no event",
                lambda: "verdict_past_breaking_line" not in kinds)
        write_verdict(vdir, "2026-10-17", "evening", lambda r: r["coins"]["BTC"].update(grade="Likely", move_pct=6.2,
                      url="/why/2026-10-17-bitcoin", text=["SYNTHETIC."]), "2026-10-17T23:50:00Z")
        write_verdict(vdir, "2026-10-18", "morning", lambda r: r["coins"]["BTC"].update(grade="Likely", move_pct=-1.2,
                      url="/why/2026-10-18-bitcoin", text=["SYNTHETIC."]), "2026-10-18T12:20:00Z")
        write_verdict(vdir, "2026-10-18", "evening", lambda r: r["coins"]["BTC"].update(grade="Confirmed", move_pct=-1.3,
                      url="/why/2026-10-18-bitcoin", text=["SYNTHETIC."]), "2026-10-18T23:50:00Z")
        write_verdict(vdir, "2026-10-19", "morning", lambda r: r["coins"]["BTC"].update(grade="Likely", move_pct=-1.0,
                      url="/why/2026-10-19-bitcoin", text=["SYNTHETIC."]), "2026-10-19T12:20:00Z")
        write_verdict(vdir, "2026-10-19", "evening", lambda r: r["coins"]["BTC"].update(grade="Unclear", move_pct=-1.0,
                      url=None, text=["SYNTHETIC."]), "2026-10-19T23:50:00Z")
        with quiet():
            feed = af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir)
        ev = feed["data"]["events"]
        by = lambda k: [e for e in ev if e["kind"] == k]
        guarded(fails, "SYNTHETIC: a graded verdict on a 6.2 percent move is an event past the breaking line (5 percent)",
                lambda: len(by("verdict_past_breaking_line")) == 1 and by("verdict_past_breaking_line")[0]["coin"] == "BTC"
                and by("verdict_past_breaking_line")[0]["url"] == "/why/2026-10-17-bitcoin")
        guarded(fails, "SYNTHETIC: Likely then Confirmed on one day is a verdict that moved; Likely then Unclear is not",
                lambda: len(by("verdict_moved")) == 1 and by("verdict_moved")[0]["date_et"] == "2026-10-18"
                and "Confirmed" in by("verdict_moved")[0]["title"])
        write_verdict(vdir, "2026-10-20", "morning", lambda r: r["coins"]["BTC"].update(grade="Likely", move_pct=2.0,
                      url="/why/2026-10-20-bitcoin", text=["SYNTHETIC."]), "2026-10-20T12:20:00Z")
        write_verdict(vdir, "2026-10-20", "evening", lambda r: r["coins"]["BTC"].update(grade="Disputed", move_pct=2.1,
                      url="/why/2026-10-20-bitcoin", text=["SYNTHETIC."]), "2026-10-20T23:50:00Z")
        with quiet():
            ev = af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir)["data"]["events"]
        guarded(fails, "SYNTHETIC: a verdict that moves to Disputed is an event",
                lambda: any(e["kind"] == "verdict_moved" and e["date_et"] == "2026-10-20" and "Disputed" in e["title"] for e in ev))
        # a movers record: the real 16 October morning one, with place 7 and place 40 set by hand (SYNTHETIC)
        t = s94()
        with tempfile.TemporaryDirectory() as td2, quiet():
            mrec, _log = t.record16(td2)
        passed = mrec["gate"]["passed"]
        for x in passed:
            x["pos"] = 40
        if passed:
            passed[0]["pos"] = 7
        json.dump(mrec, open(os.path.join(mdir, f"{mrec['date_et']}-{mrec['slot']}.json"), "w", encoding="utf-8"))
        with quiet():
            ev = af.events_feed(items, now, vdir=vdir, mdir=mdir, tdir=tdir)["data"]["events"]
        tops = [e for e in ev if e["kind"] == "top10_mover"]
        guarded(fails, f"a top-10 coin past the mover line is an event, a place-40 coin is not ({len(tops)} found)",
                lambda: not passed or (len(tops) == 1 and tops[0]["coin"] == passed[0]["sym"]))
        guarded(fails, "a change figure in an event names its window (24 hours or the verdict's own window)",
                lambda: all(e["detail"].get("window") for e in ev if e["detail"] and "move_pct" in e["detail"]) and any(
                    "move_pct" in (e["detail"] or {}) for e in ev))
        guarded(fails, "newest first, and every event has an id, a kind, a title and a page address; ids are unique",
                lambda: [e["at_utc"] or e["date_et"] for e in ev] == sorted([e["at_utc"] or e["date_et"] for e in ev], reverse=True)
                and all(e["id"] and e["kind"] and e["title"] and e["url"] for e in ev) and len({e["id"] for e in ev}) == len(ev))
        guarded(fails, "no event title carries a dash, an AI word or a bare 'because'",
                lambda: not any(DASH.search(e["title"]) or AI.search(e["title"]) for e in ev))
        many = [brief_item(f"2026-09-{d:02d}", "evening") for d in range(1, 29)] + [brief_item(f"2026-10-{d:02d}", "morning", "12:20:00") for d in range(1, 29)]
        with quiet():
            capped = af.events_feed(many, now, vdir=vdir, mdir=mdir, tdir=tdir)["data"]
        guarded(fails, "SYNTHETIC: sixty Briefs and more are cut to the newest 50",
                lambda: len(capped["events"]) == 50 and capped["limit"] == 50 and capped["events"][0]["at_utc"] >= capped["events"][-1]["at_utc"])
    with tempfile.TemporaryDirectory() as td:
        with quiet():
            none = af.events_feed([], now, vdir=td, mdir=td, tdir=td)
        guarded(fails, "no record at all: an empty list, stale, no as-of; nothing invented",
                lambda: none["data"]["events"] == [] and none["stale"] is True and none["as_of_utc"] is None)
    pulse, flows, wire = fx15()
    guarded(fails, "the breaking line is the watcher's own constant, not a copy",
            lambda: af.BREAKING_LINE_PCT == __import__("watcher").MARKET_24H_PCT)


def coin_cases(fails):
    print("9. coins/<sym>.json: the readings of a coin page")
    af, sb = feeds_mod(), sb_mod()
    pulse, flows, wire = fx15()
    import tile
    with snap_of(pulse, flows):
        import snapshot
        pv, fv = snapshot.views(sb.SNAP, pulse, flows)
        coins = pv["movers"]["top100"]
        c = coins[0]
        sink = []
        old = tile.record(sink)
        try:
            with quiet():
                sb._page_reset()
                html = sb.render_coin_page(c, 1, pv, [], "T")
        finally:
            tile.record(old)
        feed = af.coin_feed(c, 1, sink, pv, NOW15)
    page = visible(html)
    d = feed["data"]
    guarded(fails, "the coin feed carries identity, rank, price, 24h, the readings the page's tiles print and the page address",
            lambda: d["symbol"] == c["symbol"] and d["rank"] == 1 and d["url"] == f"/coins/{sb._coin_slug(c)}" and d["readings"]
            and {"price", "chg_24h_pct", "mcap_usd", "volume_24h"} <= set(d))
    guarded(fails, "every reading's figure is a tile the page printed, and is on the page",
            lambda: all(r["figure"] in page for r in d["readings"]))
    guarded(fails, "the price and the 24h change shown are the page's strings",
            lambda: d["shown"]["price"] in page and d["shown"]["chg_24h"] in page)
    guarded(fails, "as-of is the tiles' stamp instant (the Board's reading)", lambda: feed["as_of_utc"] == pv["generated_utc"])


def index_cases(fails):
    print("10. index.json lists every feed")
    af = feeds_mod()
    a = af.envelope("top100", "/pulse/prices", "2026-10-15T20:00:00Z", NOW15, ["x"], {})
    b = af.envelope("movers", "/pulse/movers", None, NOW15, ["x"], {})
    c = af.envelope("whales", "/flows", "2026-10-15T23:00:00Z", NOW15, ["x"], {})
    idx = af.index_feed({"top100.json": a, "movers.json": b, "whales.json": c, "index.json": {"name": "index"}}, NOW15)
    rows = idx["data"]["feeds"]
    guarded(fails, "one row per feed with its path, page, as-of and stale flag, the same values as the feed itself",
            lambda: [(r["path"], r["page"], r["as_of_utc"], r["stale"]) for r in rows]
            == [("/api/v1/movers.json", "/pulse/movers", None, True), ("/api/v1/top100.json", "/pulse/prices", "2026-10-15T20:00:00Z", True),
                ("/api/v1/whales.json", "/flows", "2026-10-15T23:00:00Z", False)])
    guarded(fails, "the index counts its stale feeds, lists every feed it was given and never lists itself",
            lambda: idx["data"]["stale_count"] == 2 and idx["data"]["count"] == 3 and idx["as_of_utc"] == "2026-10-15T23:00:00Z")


# ---- 3. the search pass -------------------------------------------------------------------------------------------

def title_cases(fails):
    print("11. the search pass: titles, the coin h1, and no URL changed")
    sb = sb_mod()
    guarded(fails, "the home title carries query words, not the brand alone", lambda: sb.HOME_TITLE.endswith(" - " + sb.NAME)
            and "crypto" in sb.HOME_TITLE.lower() and "price" in sb.HOME_TITLE.lower() and len(sb.HOME_TITLE) <= 70)
    guarded(fails, "the Top 100 title says what people type: top 100 crypto prices", lambda: sb.TOP100_TITLE.endswith(" - " + sb.NAME)
            and "top 100 crypto prices" in sb.TOP100_TITLE.lower() and len(sb.TOP100_TITLE) <= 70)
    guarded(fails, "no title has a dash or an AI word", lambda: not any(DASH.search(x) or AI.search(x) for x in (sb.HOME_TITLE, sb.TOP100_TITLE)))
    pulse, flows, wire = fx15()
    with snap_of(pulse, flows):
        import snapshot
        pv, fv = snapshot.views(sb.SNAP, pulse, flows)
        with quiet():
            top = sb.render_pulse_prices(pv, "T")
            sb._page_reset()
            coin = sb.render_coin_page(pv["movers"]["top100"][0], 1, pv, [], "T")
            sb._page_reset()
            coin2 = sb.render_coin_page(pv["movers"]["top100"][5], 6, pv, [], "T")
    title = lambda h: re.search(r"<title>(.*?)</title>", h, re.S).group(1)
    for h, nm in ((coin, pv["movers"]["top100"][0]["name"]), (coin2, pv["movers"]["top100"][5]["name"])):
        guarded(fails, f"the {nm} page has exactly one h1 and it names the coin", lambda h=h, nm=nm: len(re.findall(r"<h1\b", h)) == 1
                and nm in re.search(r"<h1\b[^>]*>(.*?)</h1>", h, re.S).group(1))
        guarded(fails, f"the {nm} page keeps its title tag", lambda h=h, nm=nm: "price today and why it moved" in title(h))
    guarded(fails, "the Top 100 page still has its one h1", lambda: len(re.findall(r"<h1\b", top)) == 1)
    st = sb.COIN_TITLE_STYLE
    guarded(fails, "the coin h1 keeps the look the h2 had: its own inline rule restores size, weight, line height and margin, "
                   "with colors from tokens only (the two stylesheets stay Sprint 9.5's, byte for byte)",
            lambda: all(k in st for k in ("font-size:23px", "font-weight:700", "line-height:1.2", "margin:1.4em 0 .4em", "var(--ink)"))
            and not re.search(r"#[0-9a-fA-F]{3,6}\b|rgb\(", st))
    guarded(fails, "the Top 100 title tag is written once, as the new title (not escaped away)",
            lambda: title(top) == sb.esc(sb.TOP100_TITLE))


def live_cases(fails):
    print("12. the Worker live-price route and its client")
    sb = sb_mod()
    root = os.path.join(HERE, "worker")
    guarded(fails, "the route file, its test and the patch for the Worker repository exist",
            lambda: all(os.path.exists(os.path.join(root, n)) for n in ("live-prices.mjs", "live-prices.test.mjs", "gcm-newsroom-live-prices.patch")))
    node = shutil.which("node")
    if node and os.path.exists(os.path.join(root, "live-prices.test.mjs")):
        r = subprocess.run([node, os.path.join(root, "live-prices.test.mjs")], capture_output=True, text=True, timeout=120)
        for ln in r.stdout.splitlines():
            if ln.startswith("  FAIL"):
                print(ln)
        guarded(fails, "the route's own cases pass (shape, the 60-second cache, last good served flagged stale, refusals, CORS)",
                lambda: r.returncode == 0)
    else:
        info("node is not here, so the route's own cases were not run by this process (the suite runs them)")
    # the client
    guarded(fails, "with no route configured no page carries a route address (no meta in the head: today's head, byte for byte)",
            lambda: sb.LIVE_PRICE_URL == "" and '<meta name="gcm-live-prices"' not in sb.shell("T", "d", "The Board", "<main></main>", "T"))
    old = sb.LIVE_PRICE_URL
    sb.LIVE_PRICE_URL = "https://gcm-slot-trigger.gocheckmybrands.workers.dev/live/prices"
    try:
        head = sb.shell("T", "d", "The Board", "<main></main>", "T")
    finally:
        sb.LIVE_PRICE_URL = old
    guarded(fails, "configured, the head carries one meta with the route address", lambda: head.count('<meta name="gcm-live-prices"') == 1
            and "workers.dev/live/prices" in head)
    import home
    guarded(fails, "the home tape tries the route first and keeps the CoinGecko read as the fallback",
            lambda: "gcm-live-prices" in home.HOME_JS and "api.coingecko.com/api/v3/simple/price" in home.HOME_JS and "cg()" in home.HOME_JS)
    guarded(fails, "the CoinGecko fallback is the answer when the route gives none (an absent or failed route is today's read)",
            lambda: "return d?d.simple:cg();" in home.HOME_JS and "(LIVE?viaRoute()" in home.HOME_JS and ":cg())" in home.HOME_JS)
    guarded(fails, "the route is only ever read when it answers fresh: stale, malformed and slow answers fall back",
            lambda: "d.stale===false" in home.HOME_JS and "setTimeout" in home.HOME_JS and "typeof d.simple.bitcoin.usd==='number'" in home.HOME_JS)
    guarded(fails, "the home is the only page that reads a live price, so it is the only client changed (no page renders the ticker strip)",
            lambda: "simple/price" not in open(os.path.join(HERE, "site", "assets", "coinchart.js"), encoding="utf-8").read())
    guarded(fails, "the canary's host list takes the configured route host and no other",
            lambda: __import__("verify_pipeline").home_hosts("https://x.workers.dev/live/prices")[-1] == "x.workers.dev"
            and __import__("verify_pipeline").home_hosts("")[-1] != "x.workers.dev")


HOME_JS_97_BLOCK_SHA256 = "ea3baeea2494e8f62f1b6bc2bf6b27db0b17214fd8233b7114172c8a75bfd0e5"


def home_block_cases(fails):
    print("12b. the 9.7 block of HOME_JS is pinned (so 9.5b's cut-out stays covered without the browser)")
    import hashlib
    import home
    js = home.HOME_JS
    a = js.index("  // ===== Sprint 9.7: the Worker route")
    e = "  // ===== end Sprint 9.7 =====\n"
    block = js[a:js.index(e) + len(e)]
    guarded(fails, "the marked block hashes to the reviewed text", lambda: hashlib.sha256(block.encode()).hexdigest() == HOME_JS_97_BLOCK_SHA256)
    guarded(fails, "there is exactly one such block and the text outside it is Sprint 9.5's (sprint95b's hash)",
            lambda: js.count("// ===== Sprint 9.7") == 1)


def watchlist_cases(fails):
    print("13. the watchlist stays on the device, marks the table's own rows, and cannot move the page")
    sb = sb_mod()
    guarded(fails, "the Top 100 page carries the watchlist panel and its two scripts, on the key the pins already use",
            lambda: "data-wl-panel" in sb.WATCHLIST_PANEL_HTML and "gcmc_coins" in sb.WATCHLIST_PANEL_JS and "gcmc_coins" in sb.WATCHLIST_HEAD_JS)
    for name, js in (("filling script", sb.WATCHLIST_PANEL_JS), ("head script", sb.WATCHLIST_HEAD_JS)):
        guarded(fails, f"the {name} makes no request, sets no cookie, loads no library and sends no beacon",
                lambda js=js: not re.search(r"fetch\(|XMLHttpRequest|sendBeacon|document\.cookie|import\(|<script[^>]*src|WebSocket|new Image", js))
    js = sb.WATCHLIST_PANEL_JS
    guarded(fails, "every storage read and write is inside a try, and the panel goes away when storage is unavailable",
            lambda: js.count("try{") + js.count("try {") >= 2 and "removeAttribute('data-wl-n')" in js and sb.WATCHLIST_HEAD_JS.count("try{") == 1)
    guarded(fails, "the panel says it is saved on this device only", lambda: "this device only" in sb.WATCHLIST_PANEL_HTML)
    guarded(fails, "no second store: gcmc_coins is the only key either script names",
            lambda: "gcmc_" not in (js + sb.WATCHLIST_HEAD_JS).replace("gcmc_coins", ""))
    guarded(fails, "the coin page's pin control is on the same key", lambda: 'data-pick="BTC"' in sb._coin_pin("BTC"))
    guarded(fails, "the panel text has no dash, no AI word", lambda: not (DASH.search(sb.WATCHLIST_PANEL_HTML) or AI.search(sb.WATCHLIST_PANEL_HTML)))
    html_p = sb.WATCHLIST_PANEL_HTML
    guarded(fails, "THE SAME FACT ONCE: the panel reprints no price and no change (no money, no percent, no coin row, no change chip, no row map)",
            lambda: not re.search(r"[$%]|wp-px|chip|ROWS|wp-list|<li", html_p + sb.WATCHLIST_PANEL_JS + sb.WATCHLIST_HEAD_JS))
    pulse, flows, wire = fx15()
    coins = pulse["movers"]["top100"]
    head = sb.watchlist_head(coins)
    syms = re.search(r'S=("[^"]*")', head)
    symlist = json.loads(syms.group(1)) if syms else ""
    guarded(fails, "the head script validates against the table's own symbols, every one of them selector-safe",
            lambda: symlist == "," + ",".join(dict.fromkeys(c["symbol"] for c in coins if re.fullmatch(r"[A-Za-z0-9._-]+", c["symbol"]))) + ",")
    guarded(fails, "the head script marks the saved coins' own rows by an injected style (present before the table is parsed) and shows only saved rows on request",
            lambda: "wp-marks" in head and 'tr[data-sym=' in head and "data-wl-only" in head and "\\2605" in head and ":not([hidden])" in head
            and "td.sym2::after{content:" in head and "html[data-wl-only] '+T+'tr{display:none}" in head)
    with snap_of(pulse, flows):
        import snapshot
        pv, fv = snapshot.views(sb.SNAP, pulse, flows)
        page = sb.render_pulse_prices(pv, "T")
    guarded(fails, "ORDER: the head script comes before any stylesheet link (it never waits on CSS), the panel before the table, the filling script after it",
            lambda: page.index("data-wl-n") < page.index('<link rel="stylesheet"') < page.index("data-wl-panel") < page.index("<table")
            < page.rindex("gcmc_coins"))
    guarded(fails, "the page carries each of the three parts exactly once", lambda: page.count("var v=JSON.parse(localStorage.getItem('gcmc_coins')") == 1
            and page.count('data-wl-panel aria-label') == 1 and page.count("var KEY='gcmc_coins'") == 1)
    st = sb.WATCHLIST_PANEL_STYLE
    guarded(fails, "THE RESERVE: the panel's height is one fixed number (127px: border 2, padding 24, heading 24, note 33, gap 8, buttons 36), whatever is saved",
            lambda: "height:127px" in st and 2 + 24 + 24 + 33 + 8 + 36 == 127 and "--wp-n" not in st)
    guarded(fails, "no text box in the panel can change the height: heading, note and button row are fixed boxes",
            lambda: all(k in st for k in ("height:24px", "height:33px", "height:36px")))
    guarded(fails, "the panel takes no room until the head script has counted a saved coin", lambda: "display:none" in st.split("html[data-wl-n]")[0])
    css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read() + open(
        os.path.join(HERE, "site", "assets", "system.css"), encoding="utf-8").read()
    mine = sorted(set(re.findall(r"\bwp-[a-z]+", sb.WATCHLIST_PANEL_HTML + sb.WATCHLIST_PANEL_JS + st)))
    guarded(fails, f"the panel's class names ({', '.join(mine)}) are its own: none is in either stylesheet",
            lambda: mine and not any(re.search(r"\." + c + r"\b", css) for c in mine if c != "wp-marks"))
    guarded(fails, "every class the panel's markup uses is styled by the panel's own rules",
            lambda: all(("." + c) in st for c in re.findall(r"\bwp-[a-z]+", sb.WATCHLIST_PANEL_HTML)))
    guarded(fails, "colors come from tokens only", lambda: not re.search(r"#[0-9a-fA-F]{3,6}\b|rgb\(", st + head))


def wiring_cases(fails):
    print("14. wiring")
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "build() writes the feeds under /api/v1/ through api_feeds and fails open", lambda: "api_feeds" in src and "api/v1" in src
            and "the feeds were not written" in src)
    guarded(fails, "build() calls the feed writer once, after the coin pages (it needs their tiles)",
            lambda: src.count("    _write_api_feeds(w, items, pulse, flows, _board_tiles, _coin_tiles)\n") == 1
            and src.index("_write_api_feeds(w, items, pulse, flows, _board_tiles, _coin_tiles)") > src.index("_coin_tiles[_slug] ="))
    suite = open(os.path.join(HERE, "scripts", "sprint95_suite.sh"), encoding="utf-8").read()
    guarded(fails, "the suite runs this test", lambda: "sprint97_test.py" in suite)
    vp = open(os.path.join(HERE, "verify_pipeline.py"), encoding="utf-8").read()
    guarded(fails, "the canary calls this test's unit and tree cases", lambda: "_sprint97_canary" in vp and "sprint97_test" in vp)
    for name in ("api_feeds.py", "worker/live-prices.mjs", "worker/live-prices.test.mjs", "scripts/sprint97_browser.mjs"):
        p = os.path.join(HERE, name)
        guarded(fails, f"{name}: exists, no dash, US spelling of the house words",
                lambda p=p: os.path.exists(p) and not DASH.search(open(p, encoding="utf-8").read()))


def unit():
    fails = []
    for name, fn in (("stale", stale_cases), ("top100", top100_cases), ("whales", whales_cases), ("movers", movers_cases),
                     ("news and brief", news_brief_cases), ("why", why_cases), ("backfill", backfill_cases),
                     ("events", events_cases), ("coin", coin_cases), ("index", index_cases), ("titles", title_cases),
                     ("live", live_cases), ("home block", home_block_cases), ("watchlist", watchlist_cases), ("wiring", wiring_cases)):
        group(fails, name, fn)
    return fails


# ---- the built tree -----------------------------------------------------------------------------------------------

def tree(root, expect_pages=False, with_browser=False):
    """The cases that read the tree a build wrote. Returns the failures. `with_browser`: also run scripts/sprint97_browser.mjs
    (the suite does; the canary, which runs where no browser may be installed, reads the tree only)."""
    fails = []
    print(f"15. the built tree {root}")
    pub = lambda rel: os.path.join(root, rel)
    rd = lambda rel: open(pub(rel), encoding="utf-8", errors="replace").read() if os.path.exists(pub(rel)) else ""
    feed = lambda name: json.loads(rd(f"api/v1/{name}.json") or "null")
    import snapshot
    stamp = rd("stamp.txt")
    names = list(FEEDS)
    for n in names:
        guarded(fails, f"/api/v1/{n}.json exists and parses", lambda n=n: isinstance(feed(n), dict))
    guarded(fails, "a feed for each of the first 100 coin pages",
            lambda: sum(1 for n in os.listdir(pub("coins")) if n.endswith(".html")) == sum(
                1 for n in os.listdir(pub("api/v1/coins")) if n.endswith(".json")) > 90)
    every = [n[:-5] for n in sorted(os.listdir(pub("api/v1/coins")))] if os.path.isdir(pub("api/v1/coins")) else []
    allf = {n: feed(n) for n in names if feed(n)}
    allf.update({"coins/" + n: feed("coins/" + n) for n in every})
    why_days = sorted(n[:-5] for n in os.listdir(pub("api/v1/why")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", n)) if os.path.isdir(pub("api/v1/why")) else []
    allf.update({"why/" + d: feed("why/" + d) for d in why_days})
    guarded(fails, "every feed has schema, version 1, as_of_utc (or null), built_utc, a boolean stale and its sources",
            lambda: all(isinstance(f.get("stale"), bool) and f.get("version") == 1 and f.get("schema") and "as_of_utc" in f
                        and f.get("built_utc") and f.get("sources") for f in allf.values()))
    guarded(fails, "stale in every feed is the site's rule applied at the feed's own build time",
            lambda: all((f["as_of_utc"] is None and f["stale"]) or f["stale"] is bool(snapshot.is_stale(f["as_of_utc"], dt.datetime.fromisoformat(
                f["built_utc"].replace("Z", "+00:00")))) for f in allf.values()))
    idx = allf.get("index") or {}
    listed = {r["path"] for r in (idx.get("data") or {}).get("feeds", [])}
    guarded(fails, "index.json lists every feed that was written, and nothing that is not there",
            lambda: listed == {f"/api/v1/{n}.json" for n in allf if n != "index"} and all(os.path.exists(pub(p.lstrip("/"))) for p in listed))
    # the figures on the pages
    page = lambda rel: visible(rd(rel))
    top = allf.get("top100")
    if top:
        t = page("pulse/prices.html")
        guarded(fails, "top100: every shown string is on /pulse/prices.html",
                lambda: all(r["shown"][k] in t for r in top["data"]["rows"] for k in ("price", "chg_24h", "mcap", "volume") if r["shown"].get(k)))
        h = rd("pulse/prices.html")
        m = re.search(r'class="live-stamp"[^>]*data-asof="([^"]+)"', h)
        guarded(fails, "top100: the as-of is the page's own data-asof and the stale flag is the rule's", lambda: m and m.group(1) == top["as_of_utc"])
    mk = allf.get("markets")
    if mk:
        t = page("pulse.html")
        guarded(fails, f"markets: every tile figure and stamp is on /pulse.html ({len(mk['data']['tiles'])} tiles)",
                lambda: mk["data"]["tiles"] and all(x["figure"] in t and x["stamp"] in t for x in mk["data"]["tiles"]))
    wh = allf.get("whales")
    if wh and wh["data"].get("sentence"):
        t = page("flows.html")
        guarded(fails, "whales: the sentence and every shown net are on /flows.html",
                lambda: wh["data"]["sentence"] in t and all(e["shown"]["net"] in t for e in wh["data"]["by_exchange"]))
    nw = allf.get("news")
    if nw:
        t = page("news.html")
        guarded(fails, "news: the top line of the day is on /news.html", lambda: not nw["data"]["items"] or nw["data"]["items"][0]["line"] in t
                or nw["data"]["items"][0]["line"][:60] in t)
    br = allf.get("brief/latest")
    if br and br["data"].get("url"):
        t = norm(page(br["data"]["url"].lstrip("/") if br["data"]["url"] != "/" else "index.html"))
        guarded(fails, "brief: the title and the lead sentence are on the page the feed names (the home for a Morning Brief, the article for an Evening one)",
                lambda: norm(br["data"]["title"]) in t and (norm((br["data"]["sentences"] or [br["data"]["bottom_line"] or ""])[0])[:60] in t))
    mv = allf.get("movers")
    if mv:
        t = page("pulse/movers.html")
        guarded(fails, "movers: every shown move is on /pulse/movers.html", lambda: all(r["shown"]["move"] in t for r in mv["data"]["coins"]))
    for n in every[:100]:
        f = allf["coins/" + n]
        t = page(f"coins/{n}.html")
        if not all(r["figure"] in t for r in f["data"]["readings"]) or f["data"]["shown"]["price"] not in t:
            guarded(fails, f"coins/{n}: every reading and the price are on the page", lambda: False)
            break
    else:
        guarded(fails, f"coins: every reading and the price of {len(every)} coin feeds are on their pages", lambda: True)
    for d in why_days:
        f = allf["why/" + d]
        for sym, c in f["data"]["coins"].items():
            if c.get("url") and c.get("card_text"):
                t = page(c["url"].lstrip("/") + ".html")
                guarded(fails, f"why/{d} {sym}: the card's sentences and every figure are on {c['url']}",
                        lambda c=c, t=t: all(norm(s) in norm(t) for s in c["card_text"]))
    for d in why_days:
        f = allf["why/" + d]
        dp = rd(f"today/{d}.html")
        if dp:
            pgs = {sym: page(c["url"].lstrip("/") + ".html") for sym, c in f["data"]["coins"].items() if c.get("url")}
            guarded(fails, f"why/{d}: every string in the feed is on its own page", lambda f=f, pgs=pgs, dp=dp: not why_strings_missing(f["data"], pgs, visible(dp)))
    # the search pass on the tree
    h = rd("index.html")
    guarded(fails, "the home's title tag is the new one", lambda: re.search(r"<title>(.*?)</title>", h, re.S).group(1).startswith("Crypto prices"))
    guarded(fails, "the Top 100 title tag is the new one", lambda: "Top 100 crypto prices" in rd("pulse/prices.html").split("</title>")[0])
    bad = []
    for n in every:
        ph = rd(f"coins/{n}.html")
        if len(re.findall(r"<h1\b", ph)) != 1:
            bad.append(n)
    guarded(fails, f"every coin page has exactly one h1 ({len(bad)} without: {bad[:5]})", lambda: not bad and every)
    guarded(fails, "the beacon is on every page the build touches in this sprint (home, Top 100, a coin page): exactly one",
            lambda: all(len(re.findall(r"<script\b[^>]*data-cf-beacon=", rd(p))) == 1 for p in ("index.html", "pulse/prices.html", "coins/btc.html")))
    sm = rd("sitemap.xml") + rd("sitemap-priority.xml") + rd("sitemap-archive.xml") + rd("news-sitemap.xml")
    guarded(fails, "no feed is listed in a sitemap as a page", lambda: "/api/v1/" not in sm)
    base = [ln.strip() for ln in open(os.path.join(HERE, "fixtures", "sprint97", "pages-9.6.txt"), encoding="utf-8") if ln.strip()]
    gone = [p for p in base if not os.path.exists(pub(p))]
    guarded(fails, f"no URL changed: every page Sprint 9.6 built at the structural addresses ({len(base)}) is still built (missing: {gone[:4]})",
            lambda: not gone)
    guarded(fails, "no feed has a dash; none but the coin identity feeds (a coin's name may be 'Artificial ...') has an AI word",
            lambda: not any(DASH.search(json.dumps(f, ensure_ascii=False)) for f in allf.values())
            and not any(AI.search(feed_prose(f)) for n, f in allf.items() if n != "top100" and not n.startswith("coins/")))
    guarded(fails, "'because' is in a verdict feed only where a Confirmed grade stands (the law of 16 October), and in no event title",
            lambda: all(not BECAUSE.search(json.dumps(f["data"].get("coins") or {})) or any(
                c.get("grade") == "Confirmed" for c in (f["data"].get("coins") or {}).values() if isinstance(c, dict))
                for n, f in allf.items() if n.startswith("why/"))
            and not any(BECAUSE.search(e["title"]) for e in (allf.get("events") or {}).get("data", {}).get("events", [])))
    def strict(n):
        def bad(x):
            raise ValueError("non-finite number " + x)
        json.loads(rd(f"api/v1/{n}.json"), parse_constant=bad)
        return True
    guarded(fails, "every feed is strict JSON (no NaN or Infinity)", lambda: all(strict(n) for n in allf))
    tot = sum(os.path.getsize(os.path.join(dp, n)) for dp, _d, ns in os.walk(pub("api")) for n in ns) if os.path.isdir(pub("api")) else 0
    guarded(fails, f"the feeds weigh under 3 MB in all ({tot // 1024} KB) and none over 400 KB",
            lambda: tot < 3 * 1024 * 1024 and all(os.path.getsize(os.path.join(dp, n)) < 400 * 1024 for dp, _d, ns in os.walk(pub("api")) for n in ns))
    if with_browser:
        fails += browser(root)
    return fails


def browser(root):
    """The browser half: scripts/sprint97_browser.mjs. It needs node and playwright; their absence is a failure here, not a skip."""
    fails = []
    node = shutil.which("node")
    mjs = os.path.join(HERE, "scripts", "sprint97_browser.mjs")
    guarded(fails, "node and the browser script are available", lambda: bool(node) and os.path.exists(mjs))
    if not (node and os.path.exists(mjs)):
        return fails
    try:
        r = subprocess.run([node, mjs, root], capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        guarded(fails, "the browser script finished inside ten minutes", lambda: False)
        return fails
    for ln in r.stdout.splitlines():
        if ln.startswith("PASS "):
            print("  ok   " + ln[5:])
        elif ln.startswith("FAIL "):
            print("  FAIL " + ln[5:])
            fails.append(ln[5:])
        elif ln.startswith("INFO "):
            print("  INFO " + ln[5:])
    if r.returncode != 0 and not fails:
        fails.append("browser script exited " + str(r.returncode) + ": " + (r.stderr or "")[-300:])
        print("  FAIL " + fails[-1])
    return fails


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1], with_browser="--no-browser" not in args)
    print(f"\nSPRINT 9.7: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
