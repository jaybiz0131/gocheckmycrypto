#!/usr/bin/env python3
"""Program 9, Sprint 9.5: names, the answer-first front and trust. Each case is named after what it guards.

  python3 scripts/sprint95_test.py                   # unit cases; exit 1 on any failure
  python3 scripts/sprint95_test.py --tree <dir>      # also the cases that read a built tree (and the browser half)
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote)

THE RECORDS ARE REAL: the home is drawn from the recorded 15 October Board (fixtures/why/) with the real verdict
that Board grades (Unclear: no reported event lines up), and from the same Board with no verdict; the corrections
log is drawn from the corrections the desk's own stories carry (site/content); the Brief archive from the real
Briefs. Cases marked SYNTHETIC change a real record by hand to reach a rule the real days do not, and say so
(Jack, 13 October 2026). NO MODEL CALL anywhere.

Jack's rulings of October 16 (3) and (4) are what this file holds the site to: the names as NAMES.md recommends
(Why it moved, Unclear, Big movers, and the recommended column of its section 4 in full), no AI disclosure
anywhere on the trust pages, the editor named Crypto Cronkite and nothing personal, and "How we check" saying only
what the process does.
"""
import contextlib
import copy
import datetime as dt
import html as _html
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
FX = os.path.join(HERE, "fixtures", "sprint95")
UTC = dt.timezone.utc
EM = re.compile("[\u2013\u2014]")


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


def visible(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h or "", flags=re.S | re.I)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def rendered(fn, *a, **k):
    """A renderer's page with the snapshot global the build sets, from the recorded 15 October Board."""
    import site_build as sb
    import snapshot
    t = s93()
    p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
    fl = t.s92().load(f"flows_{t.D15()}.json")
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, fl)
    try:
        return fn(p, fl, *a, **k)
    finally:
        sb.SNAP = old


def v15():
    import verdict
    t = s93()
    return verdict.record_from(t.rec(t.D15()), "2026-10-15", "evening", day=t.day15())


# ---- 1. the names, as Jack picked them -----------------------------------------------------------------------------

def name_cases(fails):
    import site_build as sb
    print("1. the names: NAMES.md as ruled on October 16 (3), the recommended column in full, one name per thing")
    want = {"why": "Why it moved", "markets": "Markets", "movers": "Big movers", "flows": "Whale Watch",
            "charts": "Charts", "news": "News", "brief": "The Brief", "record": "Storylines", "learn": "Learn"}
    guarded(fails, "the one table holds the nine names, and each has one name (no second, brand name)",
            lambda: {k: sb.NAMES[k][0] for k in sb.NAMES} == want and all(sb.NAMES[k][1] == "" for k in sb.NAMES))
    guarded(fails, "the URLs behind the names did not change (/today/, /pulse.html, /pulse/movers.html, /flows.html, "
                   "/chartmaster.html, /news.html, /bottom-line.html, /record.html, /learn.html)",
            lambda: [sb.NAMES[k][2] for k in want] == ["/today/", "/pulse.html", "/pulse/movers.html", "/flows.html",
                    "/chartmaster.html", "/news.html", "/bottom-line.html", "/record.html", "/learn.html"])
    guarded(fails, "the desktop nav: Home, Why it moved, Markets, Big movers, Whale Watch, Charts, News, The Brief, "
                   "Storylines, Learn, About",
            lambda: [t for _k, t, _b, _h in sb.NAV] == ["Home", "Why it moved", "Markets", "Big movers", "Whale Watch",
                                                      "Charts", "News", "The Brief", "Storylines", "Learn", "About"])
    guarded(fails, "the phone tab bar is exactly five: Why it moved, Markets, Big movers, Whale Watch, Brief, to /today/, /pulse.html, "
                   "/pulse/movers.html, /flows.html, /bottom-line.html, and the current page's tab is marked",
            lambda: [k for k, _d in sb.TAB_BAR] == ["why", "markets", "movers", "flows", "brief"]
            and re.findall(r'<a class="tb-item[^"]*" href="([^"]+)"[^>]*>.*?<span>([^<]+)</span></a>', sb.tab_bar("/pulse/movers.html"), re.S)
            == [("/today/", "Why it moved"), ("/pulse.html", "Markets"), ("/pulse/movers.html", "Big movers"),
                ("/flows.html", "Whale Watch"), ("/bottom-line.html", "Brief")]
            and sb.tab_bar("/pulse/movers.html").count('aria-current="page"') == 1
            and re.search(r'class="tb-item on" href="/pulse/movers.html" aria-current="page"', sb.tab_bar("/pulse/movers.html")))
    guarded(fails, "no nav entry carries a second (brand) name",
            lambda: all(b == "" for _k, _t, b, _h in sb.NAV))
    guarded(fails, "the title tag's lead is the one name", lambda: sb.name_title("markets") == "Markets"
            and sb.name_title("flows") == "Whale Watch" and sb.name_title("record") == "Storylines")
    guarded(fails, "the nav and the tab bar mark the same group: /today/ and /why/... are Why it moved, "
                   "/pulse/movers.html is Big movers, a month of the Brief is The Brief",
            lambda: sb.nav_group("/today/") == "why" and sb.nav_group("/why/2026-10-15-bitcoin") == "why"
            and sb.nav_group("/today/2026-10-15.html") == "why" and sb.nav_group("/pulse/movers.html") == "movers"
            and sb.nav_group("/bottom-line/2026-09.html") == "brief" and sb.nav_group("/pulse/prices.html") == "markets")

    import tile
    import wire
    rd = tile.READINGS
    guarded(fails, "the Markets tiles: ETF flows, Whale flows, Stablecoin supply, Bitcoin fees (section 4's rows)",
            lambda: rd["etf-net"].name == "ETF flows" and rd["whale-net"].name == "Whale flows"
            and rd["stablecoin-float"].name == "Stablecoin supply" and rd["network-fee"].name == "Bitcoin fees")
    guarded(fails, "the wire's reading names follow, and a stored wire file with the old names is read through the table",
            lambda: wire.TAG_READING["etfs-funds"] == "ETF flows" and wire.TAG_READING["stablecoins"] == "Stablecoin supply"
            and wire.TAG_READING["exchanges"] == "Whale flows" and wire.reading_label("Spot ETF net") == "ETF flows"
            and wire.reading_label("Stablecoin float") == "Stablecoin supply"
            and wire.reading_label("Whale net, exchange flows") == "Whale flows" and wire.reading_label("Fear & Greed") == "Fear & Greed")

    import home
    t = s93()
    wire_rec = t.s92().load(f"wire_{t.D15()}.json")
    old_wire = copy.deepcopy(wire_rec)
    for w in old_wire.get("items") or []:
        w["board_reading"] = "Spot ETF net"
    now = dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)
    pulse = t.s92().load(f"pulse_{t.D15()}.json")
    import snapshot
    snap = snapshot.build(pulse, t.s92().load(f"flows_{t.D15()}.json"))
    deltas = sb.board_deltas(pulse)
    fl = t.s92().load(f"flows_{t.D15()}.json")
    h = home.above_fold(snap, pulse, fl, deltas, old_wire, {}, {}, sb.NEWS_CADENCE_LINE, now=now)
    v = visible(h)
    guarded(fails, "the home: 'Top story, checked' heads the checked story (not 'The checked story')",
            lambda: "Top story, checked" in v and "The checked story" not in v)
    guarded(fails, "the home: the mood block is 'Sentiment' (not 'The mood')",
            lambda: 'data-block="mood"' in h and re.search(r'h-mood.*?Sentiment', h, re.S) is not None
            and "The mood" not in v and re.search(r'<h2 class="h-h">Sentiment</h2>', h) is not None)
    guarded(fails, "the home: the wire's mark is 'Reported' (not 'Wire') and a reading is 'Related data: ETF flows' "
                   "(not 'Reads with Spot ETF net'), from a stored wire written under the old name",
            lambda: 'class="h-wm">Reported<' in h and ">Wire<" not in h and "Related data: ETF flows" in v
            and "Reads with" not in v and "Spot ETF net" not in v)
    guarded(fails, "the home: the money cards read 'ETF flows', 'Whale flows', 'Stablecoin supply'",
            lambda: all(x in v for x in ("ETF flows", "Whale flows", "Stablecoin supply"))
            and not re.search(r'<h3 class="tl-l"><a[^>]*>Whales</a>', h) and "Stablecoin float" not in v)
    guarded(fails, "the home: the link to the daily answer reads 'Why it moved' (not 'Why crypto moved today')",
            lambda: ">Why it moved &rarr;<" in h and "Why crypto moved today" not in v)
    guarded(fails, "the home: no 'Board' as a place name (the Markets name is the only one)",
            lambda: not re.search(r"\b[Tt]he Board\b|\bBoard\b", v))
    guarded(fails, "the home: the Brief card is named 'Morning Brief' or 'Evening Brief' by slot, 'The Brief' when the slot is not named",
            lambda: home.brief_name({"slug": "evening-brief-2026-10-11", "date": "2026-10-11"}) == "EVENING BRIEF · SUNDAY"
            and home.brief_name({"morning": True, "date": "2026-10-12"}) == "MORNING BRIEF · MONDAY"
            and home.brief_name({"slug": "x", "date": "2026-10-11"}) == "THE BRIEF · SUNDAY"
            and home.brief_name(None) == "THE BRIEF")
    guarded(fails, "the funding card reads 'Funding rate, annualized' (not 'Leverage, funding annualized')",
            lambda: "Funding rate, annualized" in visible(rendered(lambda p, fl: "".join(
                [home.t_leverage(sb.SNAP, p) or ""]))) and "Leverage, funding annualized" not in visible(
                rendered(lambda p, fl: home.t_leverage(sb.SNAP, p) or "")))

    import today
    guarded(fails, "the daily answer's slots are 'Morning Brief' and 'Evening Brief'; no 'Edition', no 'Morning read'",
            lambda: today.SLOT_LABEL == {"morning": "Morning Brief", "evening": "Evening Brief"}
            and "Edition" not in today.stamp_line("evening", "2026-10-15T23:14:33Z", "2026-10-15T23:12:00Z", "7:12 PM ET",
                                                  dt.datetime(2026, 10, 16, 4, 0, tzinfo=UTC), fallback=True))
    guarded(fails, "a daily-answer record stored before the rename is read through the table (Evening Edition -> Evening Brief)",
            lambda: today.reader("Evening Edition, 7:14 PM ET") == "Evening Brief, 7:14 PM ET"
            and today.reader("Next update: Morning read, tomorrow at 8:15 AM ET") == "Next update: Morning Brief, tomorrow at 8:15 AM ET"
            and today.reader("Bitcoin spot ETF net") == "Bitcoin ETF flows")
    import verdict
    import movers
    guarded(fails, "the verdict pages and the movers' pages stamp the Brief names",
            lambda: verdict.SLOT_LABEL == {"morning": "Morning Brief", "evening": "Evening Brief"})
    guarded(fails, "the daily answer's kicker is 'Why it moved' (not 'Today')", lambda: re.search(
        r'<span class="kicker">Why it moved</span>', today.body_html(_today_rec(), [], "living")) is not None)

    guarded(fails, "the footer: News, Charts, Storylines, Learn, About, Archive, How we check, Corrections "
                   "(no 'How we work', no 'Standards & corrections')",
            lambda: all(f">{x}</a>" in sb.footer() for x in ("News", "Charts", "Storylines", "Learn", "About", "Archive",
                                                              "How we check", "Corrections"))
            and "How we work" not in sb.footer() and "Standards &amp; corrections" not in sb.footer()
            and "Standards & corrections" not in sb.footer() and "Worth keeping" not in sb.footer())
    guarded(fails, "the footer note names Markets, not the Board",
            lambda: "Whale Watch and Markets show" in sb.footer() and "the Board" not in sb.footer())


def _today_rec():
    return json.load(open(os.path.join(HERE, "site", "data", "today", "2026-10-15-evening.json"), encoding="utf-8"))


# ---- 2. the pages that carry the names -------------------------------------------------------------------------------

def page_name_cases(fails):
    import site_build as sb
    print("2. each page's H1, title tag, kicker and badges: one name, never a second one")
    items = sb.load_content()
    pulse, flows, cm = sb.load_pulse(), sb.load_flows(), sb.load_chartmaster()

    def h1(h):
        m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None

    def title(h):
        m = re.search(r"<title>(.*?)</title>", h, re.S)
        return _html.unescape(m.group(1)) if m else ""
    pages = {
        "Markets": lambda: rendered(lambda p, fl: sb.render_pulse_hub(p, fl, {}, "T")),
        "Whale Watch": lambda: rendered(lambda p, fl: sb.render_flows(fl, "T")),
        "Charts": lambda: rendered(lambda p, fl: sb.render_chartmaster({"date": "2026-10-15", "headline": "H",
                                                                         "paragraphs": ["Bitcoin holds."]}, "T", p)),
        "News": lambda: sb.render_news_hub(items, "T", pulse=pulse),
        "The Brief": lambda: sb.render_bottom_line_history(items, "T"),
        "Storylines": lambda: sb.render_record(items, "T"),
        "Learn": lambda: sb.render_learn("T"),
    }
    for name, fn in pages.items():
        h = fn()
        guarded(fails, f"{name}: the H1 is the name, the title tag opens with it, and no kicker or eyebrow prints a second name",
                lambda h=h, name=name: h1(h) == name and title(h).startswith(f"{name} - ")
                and not re.search(r'class="(?:kicker|bd-eyebrow)"[^>]*>\s*(The Board|Whale Watch|Chart Master|Checked|The Edition|'
                                  r'Worth keeping|The Board explained)\s*<', h))
    mk = pages["Markets"]()
    guarded(fails, "Markets: no 'The Board', no 'Markets: The Board', no 'Board' kicker in its title, crumbs or links",
            lambda: "The Board" not in visible(mk) and "Markets: The Board" not in mk and "The Board dashboard" not in mk
            and ">Board</a>" not in mk)
    cmh = pages["Charts"]()
    guarded(fails, "Charts: the dated read is 'The chart read, Sep 21', not \"Chart Master's read\"",
            lambda: "The chart read, Oct 15" in visible(cmh) and "Chart Master" not in visible(STORED_READS.sub("", cmh)))
    saved_now = sb._NOW_CACHE
    try:
        sb._NOW_CACHE = dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)
        card = visible(rendered(lambda p, fl: sb.render_pulse_hub(
            p, fl, {"date": "2026-10-15", "headline": "Majors hold above their averages", "paragraphs": ["x."]}, "T")))
    finally:
        sb._NOW_CACHE = saved_now
    guarded(fails, "the Markets page's chart card is 'The chart read, Oct 15' (not \"Chart Master's read\")",
            lambda: "The chart read, Oct 15" in card and "Chart Master" not in card)
    rec = pages["Storylines"]()
    guarded(fails, "Storylines: the record page's badges read Tracker, Ongoing story and Sources: (not Living table, Running story, Receipts:)",
            lambda: not re.search(r"Living table|Running story|Receipts", visible(rec)))
    nw = pages["News"]()
    guarded(fails, "News: nothing on it is called Checked as a brand, the Board, or Wire as a badge; the kind labels read Markets and Brief",
            lambda: "Checked</span>" not in nw and "The Board" not in visible(nw))
    lp = pages["Learn"]()
    guarded(fails, "Learn: no 'The Board explained'; the tiles are named as the Markets tiles are",
            lambda: "Board explained" not in visible(lp) and "Stablecoin dry powder" not in visible(lp)
            and "Spot ETF net" not in visible(lp) and "Whale net" not in visible(lp) and "Network fees" not in visible(lp))
    st = rendered(lambda p, fl: sb.render_pulse_stables(p, "T"))
    guarded(fails, "the stablecoin page is 'Stablecoin supply' (not 'Stablecoin dry powder' or 'float')",
            lambda: h1(st) == "Stablecoin supply" and "dry powder" not in visible(st).split("Dry powder")[0]
            and "Stablecoin float" not in visible(st) and "USD-pegged float" not in visible(st))
    fl = pages["Whale Watch"]()
    guarded(fails, "Whale Watch: the stablecoin flow is 'Stablecoins onto exchanges' (not 'Stablecoin buying power')",
            lambda: "Stablecoins onto exchanges" in visible(fl) and "Stablecoin buying power" not in visible(fl)
            and "buying power" not in visible(fl))


# ---- 3. the answer first -------------------------------------------------------------------------------------------

def _blocks(h):
    return re.findall(r'<(aside|section) class="([^"]*)"[^>]*?(?:data-block="([a-z]+)")?', h)


def front_cases(fails):
    import home
    import verdict
    t = s93()
    print("3. the answer first: the verdict card is the home's first object; Bitcoin is one line")
    v = v15()
    card = t._home_html(v)
    none = t._home_html(None)
    guarded(fails, "with a graded card: it is the first element of the home's first column, before the tape",
            lambda: re.search(r'<div class="h-l"><aside class="vd[^"]*" data-vd="BTC"', card) is not None
            and card.index("<aside") < card.index('data-block="tape"'))
    guarded(fails, "with a graded card: the ten blocks keep section 2's order after it",
            lambda: tuple(re.findall(r'data-block="([a-z]+)"', card)) == home.ABOVE_FOLD)
    tape = re.search(r'<section class="h-b h-tape" data-block="tape">.*?</section>', card, re.S).group(0)
    guarded(fails, "Bitcoin is one line: the tape block holds the price, the 24-hour change and the stamp, and no chart, no tile",
            lambda: "<svg" not in tape and "h-chart" not in tape and "h-coins" not in tape and 'class="h-bline' in tape
            and len(re.findall(r"\$[\d,]+", visible(tape))) == 1 and "24h" in visible(tape))
    since = re.search(r'<section class="h-b h-since" data-block="since">.*?</section>', card, re.S).group(0)
    guarded(fails, "the card Bitcoin used to have (the week's chart, the 24-hour range, the other coins) is under 'Where Bitcoin stands'",
            lambda: "h-chart" in since and "data-hl24" in since and "h-coins" in since and "Where Bitcoin stands" in since)
    guarded(fails, "the price and its change print once on the home: not in the tape and again in the chart card",
            lambda: len(re.findall(r'data-tape="bitcoin"', card)) == 1 and len(re.findall(r'data-tape-chg="bitcoin"', card)) == 1)
    guarded(fails, "with no graded card (the same Board, no verdict): no card, no empty slot; the tape's line is the first object, "
                   "the Brief card is next",
            lambda: "<aside" not in none and re.search(r'<div class="h-l"><section class="h-b h-tape"', none) is not None
            and tuple(re.findall(r'data-block="([a-z]+)"', none)) == home.ABOVE_FOLD
            and none.index('data-block="tape"') < none.index('data-block="narrative"'))
    withheld = copy.deepcopy(v)
    withheld["coins"]["BTC"] = {"kind": "withheld", "name": "Bitcoin", "window_words": "since midnight ET"}
    wh = t._home_html(withheld)
    guarded(fails, "SYNTHETIC (the day's cap reached): the notice follows the tape's line; it is not the answer and does not lead",
            lambda: "<aside" in wh and wh.index('data-block="tape"') < wh.index("<aside")
            and re.search(r'<div class="h-l"><section class="h-b h-tape"', wh) is not None)
    flat = copy.deepcopy(v)
    flat["coins"]["BTC"] = {"kind": "with_btc", "name": "Bitcoin"}
    guarded(fails, "SYNTHETIC (a kind that draws no card): nothing is drawn and nothing stands in for it",
            lambda: "<aside" not in t._home_html(flat))
    guarded(fails, "no em dash or en dash on the home", lambda: not EM.search(card) and not EM.search(none))


# ---- 4. How we check, the editor, no AI disclosure and no personal name -----------------------------------------

AI_WORDS = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bOpenAI\b|"
                      r"\bchatbot\b|\bbots?\b|\bmodels?\b|\bgenerat(?:ed|ive)\b|\bneural\b|algorithm|written by (?:a )?(?:person|human)|"
                      r"hand-?checked|hand-?written|personally|\bhuman\b|\bjournalists?\b|\breporters? on staff\b", re.I)
PERSON = re.compile(r"(?<!Crypto )\bCronkite\b|\bWalter\b|\bJack\b|\bBerno\b|\bGocheck\b|\bfounder\b|\bour (?:CEO|editor-in-chief)\b|"
                    r"\beditor-in-chief\b", re.I)


def trust_pages():
    import site_build as sb
    items = sb.load_content()
    return {"/method.html": sb.render_method(items, "T"), "/about.html": sb.render_about("T"),
            "/corrections.html": sb.render_corrections(items, "T"), "/standards.html": sb.render_standards("T")}


def trust_cases(fails):
    import site_build as sb
    print("4. How we check: the process as it runs, the editor named Crypto Cronkite, no AI disclosure, no personal name")
    pages = trust_pages()
    m = visible(pages["/method.html"])
    guarded(fails, "How we check names the editor 'Crypto Cronkite' and says the checks are automated and reviewed by the editor",
            lambda: "Crypto Cronkite" in m and "Source check" in m and "Number check" in m and "Timing check" in m
            and re.search(r"Automated", m) and "reviews what they produce" in m)
    guarded(fails, "How we check: the page's H1 is 'How we check' and the title tag opens with it",
            lambda: "<h1>How we check</h1>" in pages["/method.html"] and "<title>How we check - " in pages["/method.html"])
    guarded(fails, "How we check describes the four grades with the desk's own definitions (verdict.DEFINITIONS)",
            lambda: all(f"{g}." in m for g in ("Confirmed", "Likely", "Disputed", "Unclear"))
            and "A primary source states the cause" in m)
    for path, h in pages.items():
        v = visible(h)
        guarded(fails, f"{path}: no AI disclosure and no claim that a person wrote or hand-checked anything",
                lambda v=v: not AI_WORDS.search(v))
        guarded(fails, f"{path}: no personal name, and the editor is never named other than Crypto Cronkite",
                lambda v=v: not PERSON.search(v))
        guarded(fails, f"{path}: no em dash or en dash", lambda h=h: not EM.search(h))
    guarded(fails, "About names the editor and points to How we check; it does not say who wrote anything",
            lambda: "Crypto Cronkite" in visible(pages["/about.html"]) and 'href="/method.html"' in pages["/about.html"]
            and "human" not in visible(pages["/about.html"]).lower())
    guarded(fails, "/standards.html still resolves: it is a pointer to How we check and Corrections, canonical to /method.html",
            lambda: 'href="/method.html"' in pages["/standards.html"] and 'href="/corrections.html"' in pages["/standards.html"]
            and '<link rel="canonical" href="https://gocheckmycrypto.com/method"' in pages["/standards.html"].replace(".html", ""))
    guarded(fails, "a man's name never appears in the footer or the masthead either",
            lambda: not PERSON.search(visible(sb.footer())))


def corrections_cases(fails):
    import site_build as sb
    print("5. the corrections log: every correction the desk has made, from the data, with the story it belongs to")
    items = sb.load_content()
    rows = sb.corrections_log(items)
    stored = [i for i in items if (i.get("corrected") or "").strip() and not i.get("example")]
    guarded(fails, f"the log has one row for each story that carries a correction ({len(stored)})",
            lambda: len([r for r in rows if r["href"].startswith("/articles/")]) == len(stored) and len(stored) >= 1)
    page = sb.render_corrections(items, "T")
    v = visible(page)
    guarded(fails, "the page is 'Corrections', lists each story's title with a link to it and the correction's own words",
            lambda: "<h1>Corrections</h1>" in page and all(
                f'href="{r["href"]}"' in page and r["text"][:40].replace("&", "&amp;") in page.replace("&#x27;", "'").replace("&quot;", '"')
                or r["text"][:30] in v for r in rows))
    dated = [r for r in rows if re.match(r"^\d{4}-\d{2}-\d{2}$", r["when"] or "")]
    guarded(fails, "a correction's date is the date its own text carries; a correction with none says 'Correction date not recorded' "
                   "(the log never supplies a date)",
            lambda: ("Correction date not recorded" in v) == any(not r["when"] for r in rows)
            and all(f"Corrected {sb.fmt_date(r['when'])}" in v for r in dated))
    guarded(fails, "newest first", lambda: [r["sort"] for r in rows] == sorted((r["sort"] for r in rows), reverse=True))
    empty = sb.render_corrections([], "T", rows=[])
    guarded(fails, "SYNTHETIC (no corrections): the page says so and lists nothing",
            lambda: "has not published a correction yet" in visible(empty) and "co-l" not in empty)
    syn = [dict(i, corrected="2026-10-17: The headline said $5 million; the filing says $50 million.") for i in stored[:1]]
    guarded(fails, "SYNTHETIC (a dated correction): 'Corrected October 17, 2026.' and the story's link",
            lambda: "Corrected October 17, 2026." in visible(sb.render_corrections(syn, "T")))


def brief_cases(fails):
    import site_build as sb
    print("6. the Brief archive is a month to a page; /bottom-line.html stays the front of it")
    items = sb.load_content()
    months = sb._brief_months(items)
    keys = list(months)
    wraps = [i for i in items if sb._is_wrap(i) and i.get("bottom_line") and not i.get("example")]
    guarded(fails, f"the real Briefs fall in {len(keys)} months, newest first, and every Brief is in exactly one",
            lambda: len(keys) >= 3 and keys == sorted(keys, reverse=True)
            and sum(len(v) for v in months.values()) == len(wraps))
    front = sb.render_bottom_line_history(items, "T")
    older = sb.render_bottom_line_months(items, "T")
    guarded(fails, "/bottom-line.html holds the newest month only and links every month",
            lambda: front.count('class="bl-hist"') == len(months[keys[0]]) and front.count('class="bl-hist"') < len(wraps)
            and all((("/bottom-line.html" if k == keys[0] else f"/bottom-line/{k}.html") in front) for k in keys))
    guarded(fails, "each older month is its own page at /bottom-line/<YYYY-MM>.html, holding that month's Briefs",
            lambda: [p for _r, _h, p in older] == [f"/bottom-line/{k}.html" for k in keys[1:]]
            and all(h.count('class="bl-hist"') == len(months[k]) for (_r, h, _p), k in zip(older, keys[1:])))
    guarded(fails, "no month page carries a tenth of the old page's weight: the longest holds at most 70 Briefs",
            lambda: max(len(v) for v in months.values()) <= 70)
    guarded(fails, "the Brief page says 'The Brief', not 'daily reads', 'edition' or 'The Bottom Line'",
            lambda: "The Bottom Line" not in front and "daily reads" not in front
            and "edition" not in visible(front.split('class="bl-hist"')[0]).lower() and "<h1>The Brief</h1>" in front)


# ---- 7. the coin page: the Ledger card, the chart's box ------------------------------------------------------------

def coin_cases(fails):
    import site_build as sb
    import snapshot
    t = s93()
    print("7. the coin page: the Ledger card below the news and off a coin that moved past the mover line; the chart's box reserved")
    p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
    fl = t.s92().load(f"flows_{t.D15()}.json")
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, fl)
    try:
        def page(sym, mutate=None, movers=None, wire=None):
            q = copy.deepcopy(p)
            pos, c = next((i + 1, x) for i, x in enumerate(q["movers"]["top100"]) if x["symbol"] == sym)
            if mutate:
                mutate(c)
            return sb.render_coin_page(c, pos, q, [], "T", wire=wire or {"items": []}, cm={}, movers=movers or {})
        btc = page("BTC")
        guarded(fails, "an ordinary day: the Ledger card is on the page, after the coin's readings and stories, at the foot above the links",
                lambda: 'class="cn-cold"' in btc and btc.index('class="cn-cold"') > btc.index("Readings")
                and btc.index('class="cn-cold"') > (btc.index('class="cn-stories"') if 'class="cn-stories"' in btc else 0)
                and btc.index('class="cn-cold"') < btc.index('class="st-nav"'))
        xrp = page("XRP")
        guarded(fails, "the card is after 'Supply and trade' where the page has it",
                lambda: ("Supply and trade" not in xrp) or xrp.index('class="cn-cold"') > xrp.index("Supply and trade"))
        big = page("XRP", mutate=lambda c: c.__setitem__("chg_24h_pct", 31.0))
        guarded(fails, "SYNTHETIC (a coin up 31% in 24 hours, the audit's example): no Ledger card on its page",
                lambda: 'class="cn-cold"' not in big)
        down = page("XRP", mutate=lambda c: c.__setitem__("chg_24h_pct", -12.5))
        guarded(fails, "SYNTHETIC (a coin down 12.5%): no Ledger card either", lambda: 'class="cn-cold"' not in down)
        calm = page("XRP", mutate=lambda c: c.__setitem__("chg_24h_pct", 9.9))
        guarded(fails, "SYNTHETIC (a coin up 9.9%, under the line): the card stays", lambda: 'class="cn-cold"' in calm)
        # a coin on the Big movers record: the real 16 October record (movers fixtures), whose Board is that day's
        import sprint94_test as s94
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rec, _log = s94.record16(td)
        listed = {x["sym"] for x in (rec["gate"].get("passed") or [])}
        guarded(fails, f"the real 16 October record lists {sorted(listed)[:4]}...",
                lambda: len(listed) >= 1)
        sym = sorted(listed)[0]
        q = copy.deepcopy(s94.load(s94.BOARD16))
        pos, c = next((i + 1, x) for i, x in enumerate(q["movers"]["top100"]) if x["symbol"] == sym)
        sb.SNAP = snapshot.build(q, {})
        pg = sb.render_coin_page(c, pos, q, [], "T", wire={"items": []}, cm={}, movers=rec)
        guarded(fails, f"the real 16 October Big mover {sym}: no Ledger card on its page",
                lambda: 'class="cn-cold"' not in pg)
    finally:
        sb.SNAP = old
    css = open(os.path.join(HERE, "site", "assets", "system.css"), encoding="utf-8").read()
    guarded(fails, "the chart's box is reserved: the stage keeps its minimum height (308 px, 378 from 480 px) and the head keeps "
                   "the room its tabs take, so waking the tabs moves nothing",
            lambda: ".cc-stage{min-height:308px" in css and "min-height:378px" in css and re.search(r"\.cc-head\{[^}]*min-height:44px", css))


# ---- 8. charts that read on a phone -------------------------------------------------------------------------------

def chart_cases(fails):
    import why_evidence as we
    t = s93()
    print("8. charts that read on a phone: 12 px at 375 and 390, the 9.2 timing chart included")
    guarded(fails, "the timing chart's box is 340 units wide with 12.5-unit labels: 12.6 px in a 343 px column (375), 13.1 px at 390",
            lambda: we.CHART_W == 340 and we.LABEL_FS * 343 / we.CHART_W >= 12 and we.LABEL_FS * 358 / we.CHART_W >= 12)
    r = t.rec(t.D15())
    coin = r["coins"]["BTC"]
    cands = [(i + 1, c, c.get("test_t") or c.get("event_t") or c.get("report_t")) for i, c in enumerate(r["candidates"][:6])]
    svg = we.chart_svg(coin, cands, "Bitcoin", r["window"])
    sizes = [float(x) for x in re.findall(r'font-size="([\d.]+)"', svg)]
    guarded(fails, f"every label in the drawn chart is {min(sizes) if sizes else 0} units or more, and draws at 12 px or more in a 343 px column",
            lambda: sizes and min(s * 343 / we.CHART_W for s in sizes) >= 12)
    guarded(fails, "the chart's prices are whole dollars above $1,000 (no cents in an axis label)",
            lambda: not re.search(r">\$\d{1,3}(?:,\d{3})+\.\d\d<", svg))
    css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read()
    guarded(fails, "the chart is capped at 480 px so its labels never swell past 18 px on a wide column",
            lambda: ".ev-chart{display:block;width:100%;max-width:480px" in css)
    syst = open(os.path.join(HERE, "site", "assets", "system.css"), encoding="utf-8").read()
    guarded(fails, "the home chart's own labels (7D high close, the day names) are 12 px",
            lambda: re.search(r"body \.h-chart \.h-k\{font-size:12px\}", syst) and re.search(r"body \.h-days span\{font-size:12px\}", syst))
    tok = t._css_tokens()

    def lum(h):
        h = h.strip().lstrip("#")
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        f = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]

    def ratio(a, b):
        x, y = sorted((lum(a), lum(b)), reverse=True)
        return (x + 0.05) / (y + 0.05)
    d = tok["dark"]
    guarded(fails, "dark mode: the chart label inks (muted, faint) clear 4.5:1 on the paper and on the card",
            lambda: all(ratio(d[i], d[b]) >= 4.5 for i in ("--muted", "--faint") for b in ("--paper", "--card")))


def css_cases(fails):
    print("9. tables that fit 375: one shared rule in system.css")
    syst = open(os.path.join(HERE, "site", "assets", "system.css"), encoding="utf-8").read()
    guarded(fails, "system.css holds the shared rule: xs-x columns hide below 521 px and the toggle brings them back, no script",
            lambda: ".fit-cb+.fit-more+.fit-tbl .xs-x{display:none}" in syst and ".fit-cb:checked+.fit-more+.fit-tbl .xs-x{display:table-cell}" in syst
            and ".fit-more{display:none}" in syst and "@media (max-width:520px)" in syst)
    import site_build as sb
    t = s93()
    import tempfile
    import sprint94_test as s94
    import movers
    with tempfile.TemporaryDirectory() as td:
        rec, _ = s94.record16(td)
    bm = movers.list_html(rec, rec["gate"]["board_utc"])
    guarded(fails, "Big movers: rank, coin, 24h and grade stay; Beyond Bitcoin, Its usual day and Volume are xs-x, with the toggle before the table",
            lambda: bm.count('class="xs-x"') == 3 * (1 + len((rec["gate"].get("passed") or []) + (rec["gate"].get("over_cap") or [])))
            and 'class="fit-more"' in bm and 'class="movetable fit-tbl"' in bm
            and bm.index("fit-more") < bm.index("fit-tbl") and re.search(r'<th scope="col">Rank</th><th scope="col">Coin</th><th scope="col">24h</th>', bm)
            and re.search(r'<th scope="col">Grade</th>', bm))
    fl = rendered(lambda p, f: sb.render_flows(f, "T"))
    guarded(fails, "Whale Watch by exchange: net only at 375 (In and Out are xs-x), the toggle before the table",
            lambda: fl.count('class="pnum xs-x"') >= 2 and 'class="xs-x">In</th>' in fl and 'class="xs-x">Out</th>' in fl
            and "fit-more" in fl and fl.index("fit-more") < fl.index("fit-tbl"))
    guarded(fails, "the toggle's checkbox is a real, labelled control (a label for it, a 44 px target)",
            lambda: re.search(r'<input type="checkbox" class="fit-cb" id="(fit-[a-z]+)"><label class="fit-more" for="\1">', bm)
            and "min-height:44px" in syst[syst.index(".fit-more{display:inline-flex"):syst.index(".fit-more{display:inline-flex") + 120])


def stored_cases(fails):
    import why_evidence as we
    import wire
    print("10. a stored file written before the rename is read through the table when its page is drawn")
    guarded(fails, "why_evidence prints 'on Markets', not 'on the Board', for a stored reason",
            lambda: we._renamed("Farside spot ETF flows (daily; on the Board)") == "Farside spot ETF flows (daily; on Markets)"
            and we._renamed("the Board's reading was not handed to this build") == "the Markets reading was not handed to this build")
    t = s93()
    r = t.rec(t.D15())
    guarded(fails, "the evidence record the build writes now names Markets in its read-and-unread ledger",
            lambda: "the Board" not in json.dumps(r.get("read")) + json.dumps(r.get("unread")) + json.dumps(r.get("day")))
    import edition
    guarded(fails, "the composed Brief page is 'Evening Brief', not 'Evening Edition'",
            lambda: edition._edition_slot({"title": "The Evening Brief: x"}) == "Evening Brief"
            and edition._edition_slot({"title": "x"}) == "The Brief")


AI_PAGE_WORDS = re.compile(r"\bA\.?I\b|artificial intelligence|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|OpenAI|machine[- ]learn|"
                           r"drafted with software|written by software|software drafts|\bchatbot", re.I)
HUMAN_APPROVAL = re.compile(r"a human read|human read the queue|approve what publishes|without a person answering|a person answering|"
                            r"a person does|human editor|\bthe human\b|\ba human\b|\ba person (?:approves|reads|checks|writes)", re.I)


def _item(slug):
    import site_build as sb
    return next(i for i in sb.load_content() if i.get("slug") == slug)


def review1_cases(fails):
    import site_build as sb
    import narrative
    print("12. review 1: Record, spot ETF net, dry powder, the chart page's names, and no AI or human-approval claim on the trust path")
    items = sb.load_content()
    rec = visible(sb.render_record(items, "T"))
    guarded(fails, "Storylines: the lanes say 'N in Storylines', the index card 'Storylines, full index' and 'Open Storylines' (not the Record)",
            lambda: re.search(r"\d+ in Storylines", rec) and not re.search(r"in the Record|Record, full index|Open Record", rec))
    home_rec = visible(sb.record_sections(items, home=True))
    guarded(fails, "the home's Storylines lane links 'Storylines, in full' and says nothing is 'the Record'",
            lambda: "Storylines, in full" in home_rec and "the Record" not in home_rec)
    nw = visible(sb.render_news_hub(items, "T", pulse=sb.load_pulse()))
    guarded(fails, "News: the Storylines link reads 'Storylines: what stays true after the news moves on' (not 'Record:')",
            lambda: "Storylines: what stays true" in nw and "Record: what stays" not in nw)
    guarded(fails, "the table pages' breadcrumb is 'Storylines /' (not 'Record /')",
            lambda: '{esc(task_name("record"))}</a> /' in inspect_src("render_living_table_page") and 'href="/record.html">Record</a>' not in inspect_src("render_living_table_page"))
    names = narrative.band_names({"btc_24h_pct": 1, "etf_net_usd_m": 5, "fear_greed": 50, "funding_8h_pct": 0.01})
    guarded(fails, "the Brief card's small line names the readings as Markets does: ETF flows, Fear & Greed, Funding rate",
            lambda: names == "Written from Bitcoin's day, ETF flows, Fear & Greed and Funding rate" and "spot ETF net" not in names)
    st = visible(rendered(lambda p, fl: sb.render_pulse_stables(p, "T")))
    fl = visible(rendered(lambda p, f: sb.render_flows(f, "T")))
    guarded(fails, "the stablecoin page's explainer is 'Stablecoin supply 101' (not 'Dry powder 101'); 'dry powder' appears only as what traders call it",
            lambda: "Dry powder 101" not in st and "Stablecoin supply 101" in st
            and all("call" in x.lower() or "traders" in x.lower() for x in re.findall(r"[^.]*dry powder[^.]*\.", st + " " + fl, re.I)))
    lp = open(os.path.join(HERE, "learn", "06-stablecoin-dry-powder.md"), encoding="utf-8").read()
    guarded(fails, "the Learn stablecoin page (URL kept) does not say Markets calls it dry powder, and never uses it as a tile name",
            lambda: "Markets calls it dry powder" not in lp and "when dry powder is high" not in lp
            and not re.search(r"dry powder tile|The dry powder", lp))
    cmv = visible(rendered(lambda p, f: sb.render_chartmaster({"date": "2026-10-15", "headline": "H", "paragraphs": ["Bitcoin holds."]}, "T", p)))
    guarded(fails, "Charts: the chart section's eyebrow is 'Charts' and the read's tag is 'The chart read, Oct 15' (not 'The tape', not 'the read')",
            lambda: not re.search(r"\bThe tape\b", cmv) and not re.search(r"(?<![Tt]he chart )\bthe read\b", cmv.replace("The chart read", "")))
    cmh = rendered(lambda p, f: sb.render_chartmaster({"date": "2026-10-15", "headline": "H", "paragraphs": ["Bitcoin holds."]}, "T", p))
    guarded(fails, "Charts: no eyebrow 'The tape' and no tag 'the read' in the markup",
            lambda: 'bd-eyebrow">The tape<' not in cmh and 'class="tag">the read<' not in cmh)
    # ruling 4 on the trust path
    method = sb.render_method(items, "T")
    guarded(fails, "How we check does not render or link the example story",
            lambda: "Open the example story" not in method and "example-sec-enforcement" not in method and "What a finished story looks like" not in method)
    for slug in ("example-sec-enforcement", "why-crypto-cronkite"):
        art = visible(sb.render_article(_item(slug), items))
        guarded(fails, f"/articles/{slug}.html: no AI mention, no model named, no software drafting, no claim a person writes or approves",
                lambda art=art: not AI_PAGE_WORDS.search(art) and not HUMAN_APPROVAL.search(art))
    ex = sb.render_article(_item("example-sec-enforcement"), items)
    guarded(fails, "the example page keeps its URL, is noindex, and is not in the sitemaps",
            lambda: 'name="robots" content="noindex"' in ex and _item("example-sec-enforcement").get("example") is True)
    cr = sb.render_article(_item("why-crypto-cronkite"), items)
    guarded(fails, "the editorial describes the process as How we check does: automated checks, reviewed by the editor Crypto Cronkite",
            lambda: "Crypto Cronkite" in visible(cr) and "automated" in visible(cr))
    guarded(fails, "the editorial carries a visible correction in the site's format, dated, saying the process description was corrected to match How we check",
            lambda: 'class="callout corrected"' in cr and re.search(r"<b>Correction\.</b> 2026-10-\d\d: .*How we check", cr))
    log = sb.corrections_log(items)
    guarded(fails, "/corrections.html lists that correction, dated, with a link to the editorial",
            lambda: any(r["href"] == "/articles/why-crypto-cronkite.html" and re.match(r"^2026-10-\d\d$", r["when"]) for r in log)
            and "why-crypto-cronkite" in sb.render_corrections(items, "T"))


# ---- 13. the strategist's rulings of October 20 (J-8, J-9 item 3) and Jack's J-10 --------------------------------------

READINGS_LINE = "A reported event lines up in time, but the market readings do not match it."
OTHER_WAY_LINE = "A reported event lines up in time, but the move ran the other way."
NEXT_READ = "Verdict at the next read"
LIKELY_DEF = "The reported events that pass the timing test, with the market readings agreeing."
PROMPT_OLD_NAMES = re.compile(r"chart master|\bwhale net\b|spot etf net|etf net flows|stablecoin float|dry powder|"
                              r"buying power|\bthe board\b|\bthe edition\b|morning read|network fees", re.I)


def synth_events(specs, sym="BTC"):
    """SYNTHETIC, from the real 14 October record: its candidates and tests replaced by `specs`, each
    (id, kind, line, minutes before the run began, readings) with readings agree, silent or contradict. Every
    event is timed by hand so it passes the timing test by the lead path (it came within the hour before the
    run began, nothing of the run done); the readings of the hour after it are written to say what the spec
    asks. Returns the evidence record."""
    import why_evidence as we
    r = copy.deepcopy(s93().rec(s93().D14()))
    coin = r["coins"][sym]
    run = coin["run"]
    pts = [(t, p) for t, p in coin["series"]["points"]]
    r["candidates"], coin["tests"], coin["event_hours"] = [], [], {}
    for cid, kind, line, mins, fit in specs:
        t = run["start_t"] - mins * 60
        r["candidates"].append({"id": cid, "kind": kind, "line": line, "event_utc": we._iso(t),
                                "event_basis": "the outlet's announcement time", "scheduled": False,
                                "report_utc": None, "source_count": 1, "primary": False, "secondary": False,
                                "links": [{"outlet": "Binance" if kind in ("listing", "delisting") else "Example Wire",
                                           "url": f"https://example.invalid/{cid}"}]})
        coin["tests"].append({"id": cid, "t_utc": we._iso(t), "basis": "event",
                              "result": we.timing(pts, run, t, False)})
        pats = {"agree": [{"label": "coin-specific"}], "contradict": [{"label": "risk-on across assets"}],
                "silent": []}[fit]
        coin["event_hours"][cid] = {"patterns": pats, "hour_start_utc": we._iso(t), "hour_end_utc": we._iso(t + 3600),
                                    "rows": [{"key": "ES=F", "label": "S&P 500 futures", "value": 0.1, "unit": "pct"}]}
    return r


def rulings_cases(fails):
    import verdict
    import why_evidence as we
    t93 = s93()
    d14 = t93.day14()
    # --- J-10, option 1: the prompt carries NAMES.md's names -------------------------------------------------
    prompt = open(os.path.join(HERE, "prompts", "chartmaster.md"), encoding="utf-8").read()
    m = PROMPT_OLD_NAMES.search(prompt)
    guarded(fails, "J-10 (option 1): prompts/chartmaster.md carries no old name"
                   + (f" (found {m.group(0)!r})" if m else ""), lambda: not m)
    guarded(fails, "J-10: the prompt's flow names are NAMES.md's (ETF flows, Whale flows, Stablecoin supply)",
            lambda: "ETF flows" in prompt and "whale flows" in prompt.lower() and "stablecoin supply" in prompt.lower())
    # --- the merge-time canary failures on tonight's real data (October 20, 2026, 8:30 PM) ----------------------------
    import chartmaster as _cm
    import inspect as _ins
    src = _ins.getsource(_cm)
    guarded(fails, "chartmaster.py writes NAMES.md's names in the text it generates (the data card's headline, the model's "
                   "instruction): no 'Chart Master' in them",
            lambda: "Chart Master data card" not in src and 'return "Chart Master: levels' not in src
            and "write the Chart Master's read" not in src)
    guarded(fails, "the data card's headline names the chart read, not the Chart Master",
            lambda: _cm.headline_from_levels([]) == "Chart data card: levels, 50-day and 200-day lines, RSI"
            if hasattr(_cm, "headline_from_levels") else "Chart data card: levels, 50-day and 200-day lines, RSI" in src)
    import coin_pages_test as _cpt
    import tempfile as _tf
    import site_build as _sb
    real_pulse, real_rec = _sb.load_pulse, _sb._movers_rec
    try:
        _sb.load_pulse = lambda: {"generated_utc": "2026-10-20T23:00:00Z", "movers": {"top100": [
            {"symbol": "BIG", "chg_24h_pct": 12.0}, {"symbol": "CALM", "chg_24h_pct": 1.0}, {"symbol": "DROP", "chg_24h_pct": -10.0}]}}
        _sb._movers_rec = lambda m=None: {}
        guarded(fails, "SYNTHETIC: the coin pages check expects no Ledger card for a coin up or down 10% or more, and the card on every other",
                lambda: _cpt.no_ledger_symbols() == {"big", "drop"})
        page = lambda card: ('<script src="/assets/coinchart.js?v=1"></script>' + 'role="tab"' * 4
                             + '<div data-reading="coin-price"></div>' + ('<section class="cn-cold"></section>' if card else ""))
        nl = _cpt.no_ledger_symbols()
        ok = (_cpt.page_fails("big.html", page(False), nl) + _cpt.page_fails("calm.html", page(True), nl)
              + _cpt.page_fails("drop.html", page(False), nl))
        guarded(fails, "the coin pages check passes pages built under 9.5's rule (a 12% coin and a -10% coin without the card)", lambda: ok == [])
        bad = _cpt.page_fails("calm.html", page(False), nl) + _cpt.page_fails("big.html", page(True), nl)
        guarded(fails, "the coin pages check still fails a calm coin with no card, and a mover with one",
                lambda: any("calm.html lacks the cold-storage card" in f for f in bad)
                and any("big.html carries the cold-storage card" in f for f in bad))
    finally:
        _sb.load_pulse, _sb._movers_rec = real_pulse, real_rec
    # the chart page's headline and dated read are the renderer's own words: a stored read (J-10) in the archive cannot change them
    with _tf.TemporaryDirectory() as td:
        old_arch = _sb.CM_ARCHIVE
        _sb.CM_ARCHIVE = td
        try:
            json.dump({"date": "2026-10-20", "headline": "Chart Master data card: levels", "paragraphs": []},
                      open(os.path.join(td, "2026-10-20.json"), "w"))
            _sb.CM_ARCHIVE = tempfile_empty = _tf.mkdtemp()
            pg = visible(_sb.render_chartmaster({"date": "2026-10-15", "headline": "H", "paragraphs": ["Bitcoin holds."]}, "T", None))
            guarded(fails, "the chart page renders 'The chart read, Oct 15' with no old name when the archive holds no stored read",
                    lambda: "The chart read, Oct 15" in pg and "Chart Master" not in pg)
        finally:
            _sb.CM_ARCHIVE = old_arch
    # the data card (the stored read on a day the written read did not clear the checks) is a five-column table: it
    # scrolls inside its own wrapper on a phone and never widens the page (tonight's real data, /chartmaster.html +42 px at 375)
    css_all = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read() + open(
        os.path.join(HERE, "site", "assets", "system.css"), encoding="utf-8").read()
    guarded(fails, "the chart page's data card table has its own scroll wrapper and compact cells (.tbl-wrap, .tbl)",
            lambda: re.search(r"\.tbl-wrap\{[^}]*overflow-x:auto", css_all) and re.search(r"\.tbl-wrap \.tbl\{[^}]*width:100%", css_all)
            and re.search(r"\.tbl-wrap th,\.tbl-wrap td\{[^}]*padding", css_all))
    # the run writes no stray file into the repository's site/data
    here_cm = os.path.join(HERE, "site", "data", "chartmaster")
    guarded(fails, "unit() leaves site/data/chartmaster as it found it (the archive goes to a temp directory while the cases run)",
            lambda: sorted(os.listdir(here_cm)) == STRAY_BASE)
    # --- B4: the boundary --------------------------------------------------------------------------------------
    base = {"in_window": True, "before_onset": True, "share_pct": 80.0, "moved_first": False}
    guarded(fails, "J-8 boundary: 25 percent done exactly disqualifies the event (25 or more)",
            lambda: verdict.timing_pass(dict(base, done_pct=25.0)) is None)
    guarded(fails, "J-8 boundary: 24.9 percent done still passes",
            lambda: verdict.timing_pass(dict(base, done_pct=24.9)) == "lead")
    guarded(fails, "J-8 boundary: the printed reason for 25 percent done says a quarter or more",
            lambda: "quarter or more" in verdict._against_phrase(dict(base, done_pct=25.0), "Bitcoin"))
    guarded(fails, "J-8: TIMING_TEST is versioned 2026-10-20 and cites the October 20 ruling and the audit",
            lambda: we.TIMING_TEST["version"] == "2026-10-20" and "October 20" in we.TIMING_TEST["source"]
            and "3.1" in we.TIMING_TEST["source"] and we.TIMING_TEST["done_max_pct"] == 25.0)
    # --- B5: the clock -----------------------------------------------------------------------------------------
    ts = lambda s: int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    both = {"event_utc": "2026-10-14T10:00:00Z", "report_utc": "2026-10-14T10:40:00Z", "scheduled": False}
    guarded(fails, "J-8 clock: an event reported after it happened is measured from its first report (10:40, not 10:00)",
            lambda: we.test_time(both) == (ts("2026-10-14T10:40:00Z"), "first report"))
    guarded(fails, "J-8 clock: a scheduled release is measured from its release time (the report coincides)",
            lambda: we.test_time(dict(both, scheduled=True, event_utc="2026-10-14T12:30:00Z",
                                      report_utc="2026-10-14T12:33:56Z"))[0] == ts("2026-10-14T12:30:00Z"))
    guarded(fails, "J-8 clock: an event with only an event time keeps it; a report with only a report time keeps it",
            lambda: we.test_time({"event_utc": "2026-10-14T10:00:00Z", "report_utc": None})[0] == ts("2026-10-14T10:00:00Z")
            and we.test_time({"event_utc": None, "report_utc": "2026-10-14T10:40:00Z"})[0] == ts("2026-10-14T10:40:00Z"))
    # --- B6: Likely's definition and more than one passing event ----------------------------------------------
    guarded(fails, "J-8: Likely's printed definition is exactly the strategist's words",
            lambda: verdict.DEFINITIONS["Likely"] == LIKELY_DEF)
    g = verdict.grade(t93.rec(t93.D14()), "BTC", d14)
    guarded(fails, "J-8: 14 October (real), two 8:30 AM releases pass: one Likely naming both (CPI and Real Earnings)",
            lambda: g["grade"] == "Likely" and {r["id"] for r in g["refs"]} == {
                "bls-20261014-consumer-price-index", "bls-20261014-real-earnings"}
            and all(any(r["text"] in ph for ph in g["phrases"][:1]) for r in g["refs"]))
    vrec = verdict.record_from(t93.rec(t93.D14()), "2026-10-14", "evening", day=d14)
    card = verdict.card_html(vrec, "BTC", "today", with_section=True)
    guarded(fails, "J-8: 14 October on a page with the list: the card carries one pointer per named event, each to a different item",
            lambda: len(re.findall(r'data-vd-ref="', card)) == 2
            and len(set(re.findall(r'data-vd-ref="([^"]+)"', card))) == 2
            and sorted(verdict.marks(vrec, "BTC")) == ["bls-20261014-consumer-price-index", "bls-20261014-real-earnings"])
    r = synth_events([("syn-a", "wire", "Alpha Labs announced a partnership with Beta Corp", 30, "agree"),
                      ("syn-b", "wire", "Gamma Inc launched a custody service for institutions", 20, "agree")])
    g = verdict.grade(r, "BTC", d14)
    guarded(fails, "SYNTHETIC: two events pass the same way, both with the readings agreeing: one Likely naming each",
            lambda: g["grade"] == "Likely" and len(g["refs"]) == 2 and len(g["phrases"][0]) > 0
            and all(x["text"] in g["phrases"][0] for x in g["refs"]))
    r = synth_events([("syn-a", "listing", "Binance Will List Alpha (ALP)", 30, "agree"),
                      ("syn-b", "delisting", "Example Exchange will delist Beta (BET)", 20, "agree")])
    g = verdict.grade(r, "BTC", d14)
    guarded(fails, "SYNTHETIC: two events pass and point opposite ways (a listing up, a delisting down, against a fall): Disputed, both stated",
            lambda: g["grade"] == "Disputed" and len(g["refs"]) == 2 and all(any(x["text"] in ph for ph in g["phrases"][:1]) for x in g["refs"]))
    # --- B1: J-8(a) the readings do not match -----------------------------------------------------------------
    for fit in ("silent", "contradict"):
        r = synth_events([("syn-a", "wire", "Alpha Labs announced a partnership with Beta Corp", 30, fit)])
        g = verdict.grade(r, "BTC", d14)
        vrec = verdict.record_from(r, "2026-10-14", "evening", day=d14)
        card = verdict.card_html(vrec, "BTC", "home")
        guarded(fails, f"J-8(a) SYNTHETIC: an event passes the timing test, the readings are {fit}, no other named cause: "
                       "Unclear with its own line, the event named, a card drawn",
                lambda g=g, card=card: g["kind"] == "graded" and g["grade"] == "Unclear" and g["line"][0] == READINGS_LINE
                and g["refs"] and g["refs"][0]["text"] in g["line"][1] and READINGS_LINE in card
                and "<b>Unclear</b>" in card)
    r = synth_events([("syn-a", "wire", "Alpha Labs announced a partnership with Beta Corp", 30, "silent")])
    vrec = verdict.record_from(r, "2026-10-14", "evening", day=d14)
    v = vrec["coins"]["BTC"]
    card = verdict.card_html(vrec, "BTC", "today", with_section=True)
    guarded(fails, "J-8(a): on a page with the list the card names the event with one pointer to one marked item and "
                   "prints no clock time; the model's two sentences are built from whole phrases (the belt passes them)",
            lambda: len(re.findall(r'data-vd-ref="', card)) == 1 and verdict.marks(vrec, "BTC") == ["syn-a"]
            and READINGS_LINE in visible(card) and not re.search(r"\d:\d\d (AM|PM)", visible(card))
            and verdict.belts(v, v["line"]) == "")
    # --- B2: J-9(3) the move ran the other way ----------------------------------------------------------------
    r = synth_events([("syn-a", "listing", "Binance Will List Alpha (ALP)", 30, "agree")])
    g = verdict.grade(r, "BTC", d14)
    guarded(fails, "J-9(3) SYNTHETIC: a lone listing (up) lines up in time with a fall, for Bitcoin: Unclear, 'the move ran the other way', the event named",
            lambda: g["grade"] == "Unclear" and g["line"][0] == OTHER_WAY_LINE and g["refs"]
            and g["refs"][0]["text"] in g["line"][1])
    r = synth_events([("syn-a", "delisting", "Example Exchange will delist Beta (BET)", 30, "agree")])
    g2 = verdict.grade(r, "BTC", d14)
    guarded(fails, "J-9(3) SYNTHETIC: a lone delisting (down) with a fall is not against its direction: it is not the other-way case",
            lambda: g2["line"][0] != OTHER_WAY_LINE)
    r = synth_events([("syn-a", "listing", "Binance Will List Alpha (ALP)", 30, "agree")])
    r["coins"]["ETH"] = copy.deepcopy(r["coins"]["BTC"])
    g3 = verdict.grade(r, "ETH", {"basis": "rolling_24h", "BTC": d14["BTC"], "ETH": d14["BTC"] - 4.0})
    guarded(fails, "J-9(3) SYNTHETIC: the same rule for Ether",
            lambda: g3["grade"] == "Unclear" and g3["line"][0] == OTHER_WAY_LINE)
    # --- B7: a listing never Confirms ------------------------------------------------------------------------------
    r = synth_events([("syn-a", "listing", "Binance Will List Alpha (ALP)", 30, "agree")])
    r["coins"]["BTC"]["run"]["dir"] = "up"                 # a rise: the listing is with its direction
    r["candidates"][0]["primary"] = True
    g = verdict.grade(r, "BTC", {"basis": "rolling_24h", "BTC": 1.5, "ETH": 1.0})
    guarded(fails, "J-9(3): a listing, a primary notice, with a rise and the readings agreeing, is Likely, never Confirmed",
            lambda: g["grade"] in ("Likely", None) and g["grade"] != "Confirmed")
    # --- the printed definitions agree with every card they sit beside (coordinator, October 20) -------------------
    UNCLEAR_DEF = "No reported event passes the timing test with the market readings and the move's direction agreeing."
    DISPUTED_DEF = ("Outlets name different causes, or one named cause fails the timing test while another passes, or "
                    "the events that pass point opposite ways.")
    guarded(fails, "definitions: Unclear, Disputed, Likely carry the coordinator's wording; Confirmed is unchanged",
            lambda: verdict.DEFINITIONS["Unclear"] == UNCLEAR_DEF and verdict.DEFINITIONS["Disputed"] == DISPUTED_DEF
            and verdict.DEFINITIONS["Likely"] == LIKELY_DEF
            and verdict.DEFINITIONS["Confirmed"] == "A primary source states the cause, the timing test passes, and the market readings agree.")
    cases = [("14 Oct real", t93.rec(t93.D14()), d14), ("15 Oct real", t93.rec(t93.D15()), t93.day15()),
             ("readings silent", synth_events([("a", "wire", "Alpha Labs announced a partnership with Beta Corp", 30, "silent")]), d14),
             ("listing against a fall", synth_events([("a", "listing", "Binance Will List Alpha (ALP)", 30, "agree")]), d14),
             ("opposite ways", synth_events([("a", "listing", "Binance Will List Alpha (ALP)", 30, "agree"),
                                             ("b", "delisting", "Example Exchange will delist Beta (BET)", 20, "agree")]), d14)]
    for nm, r, dm in cases:
        vr = verdict.record_from(r, "2026-10-14", "evening", day=dm)
        card = verdict.card_html(vr, "BTC", "home")
        v = vr["coins"]["BTC"]
        shown = re.search(r'<span class="vd-def">(.*?)</span>', card)
        dtext = _html.unescape(shown.group(1)) if shown else ""
        line = " ".join(v.get("line") or [])
        # the card's own line and the definition beside it cannot both stand unless the definition is true: an
        # Unclear card that names an event lining up in time must not print a definition saying no event passes
        guarded(fails, f"definition beside the card ({nm}): the printed definition is the grade's, and an Unclear card naming an "
                       "event that lines up in time does not print a definition saying no event passes",
                lambda v=v, dtext=dtext, line=line: dtext == verdict.DEFINITIONS[v["grade"]]
                and not (v["grade"] == "Unclear" and "lines up in time" in line and "No reported event passes the timing test." in dtext + " "))
    # --- B3: J-8(b) the page's window ran the other way ------------------------------------------------------------
    rec14 = t93.rec(t93.D14())
    day_up = {"basis": "rolling_24h", "BTC": 1.4, "ETH": 1.0}
    g = verdict.grade(rec14, "BTC", day_up)
    guarded(fails, "J-8(b): the page's window rose while the measured run fell: no grade, kind next_read",
            lambda: g["kind"] == "next_read" and g["grade"] is None)
    vrec = verdict.record_from(rec14, "2026-10-14", "evening", day=day_up)
    for where in ("home", "today", "coin", "page"):
        card = verdict.card_html(vrec, "BTC", where)
        guarded(fails, f"J-8(b): on the {where} placement the card's place prints \"{NEXT_READ}\", with no badge and no grade word",
                lambda card=card: NEXT_READ in visible(card) and "vd-badge" not in card
                and not re.search(r"\b(Confirmed|Likely|Disputed|Unclear)\b", visible(card)))
    guarded(fails, "J-8(b): no marks, no verdict URL, and the model is never asked for it",
            lambda: verdict.marks(vrec, "BTC") == [] and vrec["coins"]["BTC"]["url"] is None)


def inspect_src(name):
    import inspect
    import site_build as sb
    return inspect.getsource(getattr(sb, name))


# Jack's J-10 exception (October 20): a stored read keeps the names it was written under, so the "Earlier reads" entries
# (stored headlines) are left out wherever a page's own words are checked for an old name.
STORED_READS = re.compile(r'<article class="bd-card cm-entry">.*?</article>', re.S)
STRAY_BASE = sorted(os.listdir(os.path.join(HERE, "site", "data", "chartmaster"))) if os.path.isdir(
    os.path.join(HERE, "site", "data", "chartmaster")) else []


def unit():
    fails = []
    import site_build as _sb0
    import tempfile as _tf0
    # load_chartmaster() keeps a dated copy of the live read in site/data/chartmaster; a test run must not leave one there
    _sb0.CM_ARCHIVE = _tf0.mkdtemp()
    for name, fn in (("names", name_cases), ("page names", page_name_cases), ("front", front_cases),
                     ("trust", trust_cases), ("corrections", corrections_cases), ("brief", brief_cases),
                     ("coin", coin_cases), ("charts", chart_cases), ("tables", css_cases), ("stored", stored_cases),
                     ("review 1", review1_cases), ("rulings of October 20", rulings_cases)):
        group(fails, name, fn)
    return fails


# ---- the cases that read a built tree ------------------------------------------------------------------------------

OLD_NAMES = [
    (r"\b[Tt]he Board\b", "the Board"), (r"Board explained", "The Board explained"), (r"Chart Master", "Chart Master"),
    (r"\bThe Edition\b|\bEvening Edition\b|\bMorning read\b", "Edition / Morning read"), (r"Worth keeping", "Worth keeping"),
    (r"Moving the market", "Moving the market"), (r"Living table|Running story|Receipts:", "Living table / Running story / Receipts"),
    (r"\bWhale net\b|\bSpot ETF net\b|Stablecoin float|Stablecoin dry powder|Stablecoin buying power|Network fees",
     "Whale net / Spot ETF net / Stablecoin float / dry powder / buying power / Network fees"),
    (r"\bin the Record\b|Record, full index|Open Record|Record: what stays|\bRecord /", "Record (Storylines is the name)"),
    (r"[Ss]pot ETF net(?! creations)", "spot ETF net"),
    (r"Dry powder|(?<!call )crypto's dry powder|calls it dry powder|when dry powder is high|dry powder tile", "dry powder as a name"),
    (r"Leverage, funding", "Leverage, funding annualized"), (r"\bThe mood\b", "The mood"), (r"How we work|Standards & corrections",
     "How we work / Standards & corrections"), (r"The checked story", "The checked story"), (r"Reads with", "Reads with"),
]
# Pages whose words are the desk's own stored prose (stories, the Chart Master's stored reads, the Briefs) keep
# whatever name they were written under; the scan covers every page the renames reach.
SCAN_SKIP = ("articles/", "og/", "edition/", "coverage/", "chartmaster/", "news/", "today/20", "why/")


def scan_names(root):
    hits = {}
    for dp, _d, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), root)
            if rel.startswith(SCAN_SKIP) or rel in ("archive.html", "wire.html", "cold-storage.html", "counterfeit-devices.html",
                                                    "crypto-tax.html", "corrections.html"):
                continue
            raw = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
            # THE ONE NAMED EXCEPTION (Jack, J-10, option 1, October 20, 2026; docs/RULINGS.md): a stored read keeps the
            # names it was written under (the October 19 read, and any read written before the prompt changed) until
            # it rolls off. Nothing already published is reworded. The scan therefore leaves out exactly the stored
            # read's text, wherever a page prints it: the read article on /chartmaster.html and the one-paragraph card
            # on /pulse.html and the coin pages. Every other word on those pages is scanned. Reads written from the
            # next run on use the new prompt (tested in group 13).
            if rel == "chartmaster.html":
                raw = re.sub(r'<article class="pulse-card cm-read">.*?</article>', "", raw, flags=re.S)
            raw = re.sub(r'<p class="cm-card-p">.*?</p>', "", raw, flags=re.S)
            t = visible(raw)
            for rx, label in OLD_NAMES:
                m = re.search(rx, t)
                if m:
                    hits.setdefault(label, []).append((rel, t[max(0, m.start() - 30):m.end() + 30]))
    return hits


def baseline_urls():
    return [ln.strip() for ln in open(os.path.join(FX, "urls_main.txt"), encoding="utf-8") if ln.strip()]


def tree(root):
    """The cases that read a built tree. Returns the failures."""
    fails = []
    print(f"11. the built tree {root}")
    pub = lambda rel: os.path.join(root, rel)
    rd = lambda rel: open(pub(rel), encoding="utf-8", errors="replace").read() if os.path.exists(pub(rel)) else ""
    missing = [u for u in baseline_urls() if not os.path.exists(pub(u))]
    guarded(fails, f"NO URL REMOVED OR CHANGED: all {len(baseline_urls())} pages main built (the structural set) are still built "
                   f"({'; '.join(missing[:6])})", lambda: not missing)
    guarded(fails, "the new pages are additions: /corrections.html is built, and the older Brief months are /bottom-line/<YYYY-MM>.html",
            lambda: os.path.exists(pub("corrections.html")) and any(re.match(r"\d{4}-\d{2}\.html$", f) for f in os.listdir(pub("bottom-line"))
                                                                    if os.path.isdir(pub("bottom-line"))))
    guarded(fails, "/today/ stays canonical: its canonical link is /today, and every page's nav links /today/",
            lambda: '<link rel="canonical" href="https://gocheckmycrypto.com/today/"' in rd("today/index.html")
            and 'href="/today/"' in rd("index.html"))
    sm = rd("sitemap-priority.xml") + rd("sitemap-archive.xml")
    months_built = sorted(f[:-5] for f in os.listdir(pub("bottom-line"))) if os.path.isdir(pub("bottom-line")) else []
    guarded(fails, "/standards.html and /method.html both resolve; the sitemap lists /corrections and every older Brief month",
            lambda: os.path.exists(pub("standards.html")) and os.path.exists(pub("method.html"))
            and "<loc>https://gocheckmycrypto.com/corrections</loc>" in sm and months_built
            and all(f"<loc>https://gocheckmycrypto.com/bottom-line/{m}</loc>" in sm for m in months_built))
    # every page's nav, tab bar and footer
    ix = rd("index.html")
    nav = re.findall(r'<a href="([^"]+)"[^>]*><span class="nv-task">([^<]+)</span>', ix)
    guarded(fails, "the nav on the built home: Home, Why it moved, Markets, Big movers, Whale Watch, Charts, News, The Brief, Storylines, Learn, About, in that order",
            lambda: [n for _h, n in nav] == ["Home", "Why it moved", "Markets", "Big movers", "Whale Watch", "Charts", "News", "The Brief",
                                             "Storylines", "Learn", "About"] and "nv-brand" not in ix)
    tabs = re.findall(r'<a class="tb-item[^"]*" href="([^"]+)"[^>]*>.*?<span>([^<]+)</span></a>', ix, re.S)
    guarded(fails, "the tab bar on the built home: exactly five, Why it moved, Markets, Big movers, Whale Watch, Brief, to the right addresses",
            lambda: tabs == [("/today/", "Why it moved"), ("/pulse.html", "Markets"), ("/pulse/movers.html", "Big movers"),
                             ("/flows.html", "Whale Watch"), ("/bottom-line.html", "Brief")])
    pages_with_bar = [f for f in ("index.html", "today/index.html", "pulse.html", "flows.html", "bottom-line.html", "about.html", "method.html")
                      if os.path.exists(pub(f))]
    guarded(fails, "every page carries the same five-tab bar",
            lambda: all(len(re.findall(r'class="tb-item', rd(f))) == 5 for f in pages_with_bar))
    # H1s and titles
    for key, (name, _b, href) in [("markets", ("Markets", "", "/pulse.html")), ("flows", ("Whale Watch", "", "/flows.html")),
                                  ("charts", ("Charts", "", "/chartmaster.html")), ("news", ("News", "", "/news.html")),
                                  ("brief", ("The Brief", "", "/bottom-line.html")), ("record", ("Storylines", "", "/record.html")),
                                  ("learn", ("Learn", "", "/learn.html"))]:
        h = rd(href.lstrip("/"))
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        guarded(fails, f"{href}: H1 '{name}', title tag opens '{name} - ', one name",
                lambda h=h, h1=h1, name=name: h1 and re.sub(r"<[^>]+>", "", h1.group(1)).strip() == name
                and f"<title>{name} - " in h and "nv-brand" not in h)
    hits = scan_names(root)
    for label, v in hits.items():
        guarded(fails, f"no built page prints the old name '{label}' ({len(v)} page(s), e.g. {v[0][0]}: ...{v[0][1]}...)", lambda: False)
    if not hits:
        guarded(fails, "no built page prints an old name (the Board, Chart Master, The Edition, Worth keeping, Wire, Living table, "
                       "Running story, Receipts, Whale net, Spot ETF net, Stablecoin float, dry powder, buying power, Network fees, "
                       "The mood, How we work, Standards & corrections)", lambda: True)
    # the trust pages as built
    for f in ("method.html", "about.html", "corrections.html", "standards.html"):
        v = visible(rd(f))
        guarded(fails, f"/{f} as built: no AI disclosure, no personal name",
                lambda v=v: v and not AI_WORDS.search(v) and not PERSON.search(v))
    trust_set = [f for f in ("about.html", "method.html", "standards.html", "corrections.html", "privacy.html", "terms.html", "accessibility.html",
                             "how-we-make-money.html", "learn.html", "flows.html", "onchain-flows.html", "pulse.html", "chartmaster.html",
                             "articles/why-crypto-cronkite.html", "articles/example-sec-enforcement.html")
                 if os.path.exists(pub(f))]
    trust_set += [os.path.join("learn", f) for f in sorted(os.listdir(pub("learn")))] if os.path.isdir(pub("learn")) else []
    trust_set += [os.path.join("pulse", f) for f in sorted(os.listdir(pub("pulse")))] if os.path.isdir(pub("pulse")) else []
    for f in trust_set:
        raw = rd(f)
        if f == "chartmaster.html":
            raw = re.sub(r'<article class="pulse-card cm-read">.*?</article>', "", raw, flags=re.S)
        guarded(fails, f"/{f} as built: no 'AI', no model named, no software drafting in its words",
                lambda raw=raw: not AI_PAGE_WORDS.search(visible(raw)))
    guarded(fails, "the example page is in neither sitemap and /method.html does not link it",
            lambda: "example-sec-enforcement" not in rd("sitemap-priority.xml") + rd("sitemap-archive.xml") + rd("news-sitemap.xml")
            and "example-sec-enforcement" not in rd("method.html"))
    guarded(fails, "/method.html as built names Crypto Cronkite; /about.html does too", lambda: "Crypto Cronkite" in visible(rd("method.html"))
            and "Crypto Cronkite" in visible(rd("about.html")))
    # the coin page: the ledger card position, the chart's box
    for coin in ("btc", "eth"):
        h = rd(f"coins/{coin}.html")
        if h:
            guarded(fails, f"/coins/{coin} as built: the Ledger card (if drawn) is after the coin's stories and above the links",
                    lambda h=h: 'class="cn-cold"' not in h or (h.index('class="cn-cold"') < h.index('class="st-nav"')
                    and ('class="cn-stories"' not in h or h.index('class="cn-cold"') > h.index('class="cn-stories"'))))
    guarded(fails, "/bottom-line.html as built holds one month and a month list", lambda: rd("bottom-line.html").count('class="bl-hist"') <= 70
            and 'class="bl-months"' in rd("bottom-line.html"))
    return fails


def fixture_pages(root):
    """Write the two home fixtures into a built tree so the browser half can read them: the home from the recorded 15
    October Board with its real verdict card, and the same Board with no verdict."""
    import site_build as sb
    import home
    import snapshot
    t = s93()
    p = t.s92().load(f"pulse_{t.D15()}.json")
    fl = t.s92().load(f"flows_{t.D15()}.json")
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, fl)
    try:
        now = dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)
        for name, v in (("card", v15()), ("nocard", None)):
            above = home.above_fold(sb.SNAP, p, {}, sb.board_deltas(p), t.s92().load(f"wire_{t.D15()}.json"), {}, {},
                                    sb.NEWS_CADENCE_LINE, now=now, verdict=v)
            body = (f'<main class="wrap h-page"><section class="page"><h1 class="sr-only">GoCheckMyCrypto: fixture</h1>'
                    f'{above}</section></main>')
            html = sb.shell("Home fixture - GoCheckMyCrypto", "fixture", "The Board", body, "T", body_class="h-home", path="/",
                            system_css=True, third_party=False)
            open(os.path.join(root, f"home-fixture-{name}.html"), "w", encoding="utf-8").write(html)
    finally:
        sb.SNAP = old
    # Big movers from the real 16 October Board and its movers record (the build's own pulse is of a later day, so
    # its page says there is no current reading), for the table at 375
    import sprint94_test as s94
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rec, _log = s94.record16(td)
    q = s94.load(s94.BOARD16)
    sb.SNAP = snapshot.build(q, {})
    try:
        open(os.path.join(root, "movers-fixture.html"), "w", encoding="utf-8").write(sb.render_pulse_movers(q, "T", movers_rec=rec))
    finally:
        sb.SNAP = old


def browser(root):
    """The browser half (scripts/sprint95_browser.mjs): the tab bar, the home's first object at 375 and 1440, CLS on the coin page,
    chart labels, tables at 375. Returns (failures, output). Skipped with a named reason when no node or playwright exists."""
    node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
    if not node:
        return ["no node on this machine: the browser half did not run"], ""
    fixture_pages(root)
    r = subprocess.run([node, os.path.join(HERE, "scripts", "sprint95_browser.mjs"), root], capture_output=True, text=True, timeout=3000)
    out = r.stdout + r.stderr
    fails = [ln[5:].strip() for ln in out.splitlines() if ln.startswith("FAIL ")]
    if r.returncode and not fails:
        fails = ["the browser run exited %d: %s" % (r.returncode, out[-300:])]
    return fails, out


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        root = args[args.index("--tree") + 1]
        fails += tree(root)
        bf, out = browser(root)
        print(out)
        fails += ["browser: " + f for f in bf]
    print(f"\nSPRINT 9.5: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
