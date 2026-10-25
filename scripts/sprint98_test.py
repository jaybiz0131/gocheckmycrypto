#!/usr/bin/env python3
"""Program 9, Sprint 9.8: the verdict record. Each case is named after what it guards.

  python3 scripts/sprint98_test.py                       # unit cases; exit 1 on any failure
  python3 scripts/sprint98_test.py --tree <built dir>    # also the cases that read a built tree
  (verify_pipeline.py's canary also calls unit() and tree() on the tree it builds)

THE VERDICTS ARE 9.3'S AND 9.4'S: the real 14 October evening evidence record graded by code (Likely), the real 15 October
one (Unclear), and the real 16 October morning Big movers record graded through a stubbed model (sprint94_test.graded16; the
grade is code's, the stub only answers the sentence step). Every LATER SOURCE in these cases is SYNTHETIC: no later primary
source has been stored for any real verdict, so the sources here are made up, named "SYNTHETIC" in their own text, and point at
example.gov. A verdict record copied to another day is SYNTHETIC too and says so on its case. NO MODEL CALL and no network.
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
UTC = dt.timezone.utc
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
BECAUSE = re.compile(r"\bbecause\b", re.I)
AI = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bHaiku\b|\bSonnet\b|"
                r"\bOpenAI\b|\bchatbot\b", re.I)
PERSON = re.compile(r"\bJack\b")
PAGE = "/verdict-record.html"
# the static pages the sitemap listed before this sprint (main fe2fe53): every one must still be there, unchanged
OLD_LOCS = ["/", "/news.html", "/flows.html", "/pulse.html", "/chartmaster.html", "/pulse/sentiment.html", "/pulse/posture.html",
            "/pulse/movers.html", "/pulse/prices.html", "/pulse/stablecoins.html", "/pulse/leverage.html", "/pulse/etf.html",
            "/pulse/network.html", "/archive.html", "/bottom-line.html", "/record.html", "/method.html", "/about.html",
            "/corrections.html", "/learn.html", "/cold-storage.html", "/crypto-tax.html", "/counterfeit-devices.html",
            "/onchain-flows.html", "/how-we-make-money.html", "/accessibility.html", "/privacy.html", "/terms.html"]


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


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def s97():
    import sprint97_test
    return sprint97_test


def s94():
    import sprint94_test
    return sprint94_test


def vr():
    import verdict_record
    return verdict_record


def visible(h):
    return s97().visible(h)


def later(verdict, finding, published, primary=True, name="SYNTHETIC primary source", says=None, url=None):
    """SYNTHETIC: one later source as the store holds it."""
    return {"verdict": verdict, "source": name, "url": url or "https://example.gov/synthetic/" + verdict.rsplit("/", 1)[-1],
            "published_utc": published, "primary": primary, "finding": finding,
            "says": says if says is not None else f"SYNTHETIC: the source's statement on {verdict}.",
            "recorded_utc": "2026-10-25T21:00:00Z"}


def fixture(td):
    """The verdict fixture: real 14 October (Likely) and 15 October (Unclear) evening records, and two SYNTHETIC copies of the
    14 October record on 16 and 17 October (each Likely, made at 23:50 UTC that day). Returns (vdir, mdir)."""
    t = s97()
    with quiet():
        vdir, _wdir, _tdir = t.graded_dirs(td, (("2026-10-14", "evening"), ("2026-10-15", "evening")))
        src = json.load(open(os.path.join(vdir, "2026-10-14-evening.json"), encoding="utf-8"))
        for day in ("2026-10-16", "2026-10-17"):
            r = copy.deepcopy(src)
            r.update(date_et=day, slot="evening", made_utc=day + "T23:50:00Z")
            for v in r["coins"].values():
                if v.get("url"):
                    v["url"] = v["url"].replace("2026-10-14", day)
            json.dump(r, open(os.path.join(vdir, f"{day}-evening.json"), "w", encoding="utf-8"))
    mdir = os.path.join(td, "movers")
    os.makedirs(mdir, exist_ok=True)
    return vdir, mdir


LATER = [later("/why/2026-10-14-bitcoin", "confirms", "2026-10-15T14:00:00Z"),
         later("/why/2026-10-16-bitcoin", "reverses", "2026-10-18T15:00:00Z")]


# ---- 1. the tally from a fixture of verdicts and later sources --------------------------------------------------------

def tally_cases(fails):
    print("1. the tally from a fixture of verdicts and later sources")
    m = vr()
    with tempfile.TemporaryDirectory() as td:
        vdir, mdir = fixture(td)
        vs = m.graded(vdir=vdir, mdir=mdir)
        urls = {v["url"]: v for v in vs}
        guarded(fails, "every stored graded Bitcoin verdict is on the record, once, with its own URL and grade",
                lambda: {u: urls[u]["grade"] for u in urls if u.endswith("-bitcoin")} == {
                    "/why/2026-10-14-bitcoin": "Likely", "/why/2026-10-15-bitcoin": "Unclear",
                    "/why/2026-10-16-bitcoin": "Likely", "/why/2026-10-17-bitcoin": "Likely"})
        t = m.tally(vs, LATER)
        lk = t["by_grade"]["Likely"]
        n_likely = sum(1 for v in vs if v["grade"] == "Likely")
        guarded(fails, f"Likely: {n_likely} graded, 1 confirmed by a later primary source, 1 reversed, the rest open",
                lambda: lk == {"graded": n_likely, "confirmed": 1, "reversed": 1, "open": n_likely - 2})
        guarded(fails, "the Unclear verdict is graded and open (no later source names it)",
                lambda: t["by_grade"]["Unclear"]["graded"] >= 1 and t["by_grade"]["Unclear"]["confirmed"] == 0
                and t["by_grade"]["Unclear"]["reversed"] == 0)
        guarded(fails, "the totals add up: graded = confirmed + reversed + open in every grade",
                lambda: all(g["graded"] == g["confirmed"] + g["reversed"] + g["open"] for g in t["by_grade"].values()))
        guarded(fails, "the total is every graded verdict stored", lambda: t["total"]["graded"] == len(vs))
        rows = {r["url"]: r for r in t["rows"]}
        guarded(fails, "14 October's Likely is confirmed, with the source that confirmed it",
                lambda: rows["/why/2026-10-14-bitcoin"]["status"] == "confirmed"
                and rows["/why/2026-10-14-bitcoin"]["source"]["url"] == LATER[0]["url"])
        guarded(fails, "17 October's Likely, with no later source, is open", lambda: rows["/why/2026-10-17-bitcoin"]["status"] == "open")
        guarded(fails, "the record runs newest first", lambda: [r["day"] for r in t["rows"]] == sorted((r["day"] for r in t["rows"]), reverse=True))
        guarded(fails, "the record starts at the first stored verdict record (9.3's first verdict on)",
                lambda: m.first_day(vdir=vdir, mdir=mdir) == "2026-10-14")
        # one verdict per URL: a day with a graded morning and a graded evening is the page's verdict, the newest
        r = json.load(open(os.path.join(vdir, "2026-10-17-evening.json"), encoding="utf-8"))
        r2 = copy.deepcopy(r)
        r2.update(slot="morning", made_utc="2026-10-17T12:20:00Z")
        r2["coins"]["BTC"]["grade"] = "Disputed"                      # SYNTHETIC: the morning graded it otherwise
        json.dump(r2, open(os.path.join(vdir, "2026-10-17-morning.json"), "w", encoding="utf-8"))
        vs2 = m.graded(vdir=vdir, mdir=mdir)
        guarded(fails, "SYNTHETIC: a day graded at both slots is one verdict, the evening's (the one its page shows)",
                lambda: [v["grade"] for v in vs2 if v["url"] == "/why/2026-10-17-bitcoin"] == ["Likely"])
        # a withheld verdict (the cap) is no grade and is not counted
        r3 = copy.deepcopy(r)
        r3.update(date_et="2026-10-18", made_utc="2026-10-18T23:50:00Z")
        for v in r3["coins"].values():
            v.update(kind="withheld", grade_withheld=v.get("grade"), grade=None, url=None)
        json.dump(r3, open(os.path.join(vdir, "2026-10-18-evening.json"), "w", encoding="utf-8"))
        guarded(fails, "SYNTHETIC: a verdict withheld at the cap is not on the record (no grade was printed)",
                lambda: not any(v["day"] == "2026-10-18" for v in m.graded(vdir=vdir, mdir=mdir)))


# ---- 2. a reversed verdict counted as reversed --------------------------------------------------------------------------

def reversed_cases(fails):
    print("2. a reversed verdict is counted as reversed")
    m = vr()
    with tempfile.TemporaryDirectory() as td:
        vdir, mdir = fixture(td)
        vs = m.graded(vdir=vdir, mdir=mdir)
        t = m.tally(vs, LATER)
        rows = {r["url"]: r for r in t["rows"]}
        guarded(fails, "16 October's Likely, reversed by a later primary source, is counted reversed and not confirmed",
                lambda: rows["/why/2026-10-16-bitcoin"]["status"] == "reversed"
                and t["by_grade"]["Likely"]["reversed"] == 1 and t["by_grade"]["Likely"]["confirmed"] == 1)
        both = LATER + [later("/why/2026-10-16-bitcoin", "confirms", "2026-10-19T15:00:00Z", name="SYNTHETIC second source")]
        t2 = m.tally(vs, both)
        guarded(fails, "a verdict one primary source reverses stays reversed when another confirms it",
                lambda: {r["url"]: r for r in t2["rows"]}["/why/2026-10-16-bitcoin"]["status"] == "reversed"
                and t2["by_grade"]["Likely"]["reversed"] == 1 and t2["by_grade"]["Likely"]["confirmed"] == 1)
        early = [later("/why/2026-10-17-bitcoin", "reverses", "2026-10-17T20:00:00Z")]
        t3 = m.tally(vs, early)
        guarded(fails, "a source published before the verdict was made is not a later source: the verdict stays open",
                lambda: {r["url"]: r for r in t3["rows"]}["/why/2026-10-17-bitcoin"]["status"] == "open"
                and t3["ignored"] and "before the verdict" in " ".join(t3["ignored"][0]["why"]))
        weak = [later("/why/2026-10-17-bitcoin", "reverses", "2026-10-19T20:00:00Z", primary=False)]
        t4 = m.tally(vs, weak)
        guarded(fails, "a source that is not primary does not reverse a verdict",
                lambda: {r["url"]: r for r in t4["rows"]}["/why/2026-10-17-bitcoin"]["status"] == "open" and t4["ignored"])
        lost = [later("/why/2026-09-01-bitcoin", "reverses", "2026-10-19T20:00:00Z")]
        t5 = m.tally(vs, lost)
        guarded(fails, "a later source for a verdict that is not stored is counted nowhere and named as ignored",
                lambda: t5["by_grade"]["Likely"]["reversed"] == 0 and "no stored graded verdict" in " ".join(t5["ignored"][0]["why"]))
        odd = [dict(later("/why/2026-10-17-bitcoin", "reverses", "2026-10-19T20:00:00Z"), finding="weakens")]
        t6 = m.tally(vs, odd)
        guarded(fails, "a finding other than confirms or reverses is counted nowhere",
                lambda: t6["by_grade"]["Likely"]["reversed"] == 0 and t6["ignored"])
        nolink = [dict(later("/why/2026-10-17-bitcoin", "reverses", "2026-10-19T20:00:00Z"), url="")]
        guarded(fails, "a source with no link is counted nowhere (the reader must be able to read it)",
                lambda: m.tally(vs, nolink)["by_grade"]["Likely"]["reversed"] == 0)
        page = visible(m.page_html(t, "T"))
        guarded(fails, "the page names the reversed verdict as reversed, with its source",
                lambda: "Why Bitcoin moved, Friday, October 16, 2026" in page
                and "Reversed by SYNTHETIC primary source" in page)


# ---- 3. Big movers are on the record too ---------------------------------------------------------------------------------

def movers_cases(fails):
    print("3. a graded Big mover's verdict is on the record under its own /why/ address")
    m = vr()
    t94 = s94()
    with tempfile.TemporaryDirectory() as td:
        vdir, mdir = fixture(td)
        r = t94.graded16(td)
        json.dump(r, open(os.path.join(mdir, "2026-10-16-morning.json"), "w", encoding="utf-8"))
        graded = {sym: e for sym, e in (r.get("coins") or {}).items()
                  if (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {}).get("grade")}
        vs = m.graded(vdir=vdir, mdir=mdir)
        mine = {v["url"]: v for v in vs if v.get("kind") == "mover"}
        guarded(fails, f"each of the {len(graded)} graded movers of 16 October is on the record at /why/2026-10-16-<coin id>",
                lambda: graded and set(mine) == {f"/why/2026-10-16-{e['gecko_id']}" for e in graded.values()})
        guarded(fails, "each mover keeps the grade its card printed",
                lambda: all(mine[f"/why/2026-10-16-{e['gecko_id']}"]["grade"] == e["verdict"]["coins"][s]["grade"]
                            for s, e in graded.items()))


# ---- 4. the page --------------------------------------------------------------------------------------------------------

def page_cases(fails):
    print("4. the page: the counts as tallied, honest when empty, the house rules")
    m = vr()
    with tempfile.TemporaryDirectory() as td:
        vdir, mdir = fixture(td)
        vs = m.graded(vdir=vdir, mdir=mdir)
        t = m.tally(vs, LATER, first=m.first_day(vdir=vdir, mdir=mdir))
        h = m.page_html(t, "T")
        txt = visible(h)
        lk = t["by_grade"]["Likely"]
        guarded(fails, "the headline counts are the tally's: Likely verdicts, confirmed later, reversed, not yet revisited",
                lambda: re.search(rf"\b{lk['graded']}\b\s*Likely verdicts", txt) and re.search(r"\b1\b\s*confirmed by a later primary source", txt)
                and re.search(r"\b1\b\s*reversed", txt) and re.search(rf"\b{lk['open']}\b\s*not yet revisited", txt))
        guarded(fails, "every graded verdict is listed with a link to its own page",
                lambda: all(f'href="{v["url"]}"' in h for v in vs))
        guarded(fails, "the record names its first day", lambda: "October 14, 2026" in txt)
        guarded(fails, "each listed row carries its verdict's address, grade and status (as the tree cases read them)",
                lambda: sorted((u, g, st) for st, u, g in page_rows(h)) == sorted((r["url"], r["grade"], r["status"]) for r in t["rows"]))
        guarded(fails, "one h1, 'The verdict record'", lambda: h.count("<h1") == 1 and re.search(r"<h1[^>]*>The verdict record</h1>", h))
        guarded(fails, "its canonical address is /verdict-record", lambda: 'rel="canonical" href="https://gocheckmycrypto.com/verdict-record"' in h)
        guarded(fails, "it links How we check for the grades' definitions", lambda: 'href="/method.html"' in h)
        for name, tt in (("fixture", t), ("empty", m.tally([], []))):
            page, body = m.page_html(tt, "T"), m.page_body(tt)
            vt = visible(page)
            guarded(fails, f"{name}: no 'because' on the page (it belongs to a Confirmed verdict's own sentence)", lambda: not BECAUSE.search(vt))
            # the body as the record writes it, before the shell's own dash belt (which would hide a dash written here)
            guarded(fails, f"{name}: no en or em dash in the record's own markup", lambda: not DASH.search(body))
            guarded(fails, f"{name}: no AI word and no personal name on the page", lambda: not AI.search(vt) and not PERSON.search(page))
        empty = visible(m.page_html(m.tally([], []), "T"))
        guarded(fails, "with no graded verdict stored, the page says so and prints zero counts, nothing invented",
                lambda: "No graded verdict" in empty and re.search(r"\b0\b\s*Likely verdicts", empty)
                and re.search(r"\b0\b\s*reversed", empty))
        open_only = visible(m.page_html(m.tally(vs, []), "T"))
        guarded(fails, "with graded verdicts but no later source, the page says none has been revisited yet",
                lambda: "No verdict has been revisited yet" in open_only and re.search(r"\b0\b\s*reversed", open_only))


# ---- 5. adding a later source ----------------------------------------------------------------------------------------

def add_cases(fails):
    print("5. a later source is stored only when it can count")
    m = vr()
    with tempfile.TemporaryDirectory() as td:
        vdir, mdir = fixture(td)
        store = os.path.join(td, "verdict-record.json")
        ok, why = m.add_later(later("/why/2026-10-14-bitcoin", "confirms", "2026-10-15T14:00:00Z"), path=store, vdir=vdir, mdir=mdir)
        guarded(fails, "a primary source published after a stored verdict is stored", lambda: ok and len(m.load_later(store)) == 1)
        ok2, why2 = m.add_later(later("/why/2026-10-14-bitcoin", "reverses", "2026-10-14T20:00:00Z"), path=store, vdir=vdir, mdir=mdir)
        guarded(fails, "one published before the verdict is refused, with the reason", lambda: not ok2 and why2 and len(m.load_later(store)) == 1)
        ok3, _ = m.add_later(later("/why/2026-10-20-bitcoin", "reverses", "2026-10-21T20:00:00Z"), path=store, vdir=vdir, mdir=mdir)
        guarded(fails, "one for a verdict that is not stored is refused", lambda: not ok3)
        ok4, _ = m.add_later(later("/why/2026-10-16-bitcoin", "reverses", "2026-10-18T20:00:00Z",
                                   says="It fell " + chr(0x2014) + " SYNTHETIC."), path=store, vdir=vdir, mdir=mdir)
        guarded(fails, "a statement with a dash is refused", lambda: not ok4)
        ok5, _ = m.add_later(later("/why/2026-10-16-bitcoin", "reverses", "2026-10-18T20:00:00Z",
                                   says="SYNTHETIC: it fell because of a rate decision."), path=store, vdir=vdir, mdir=mdir)
        guarded(fails, "a statement with 'because' is refused (the record's own words never say it)", lambda: not ok5)
        guarded(fails, "the store carries only the one source that can count", lambda: len(m.load_later(store)) == 1)


# ---- 6. the real store -----------------------------------------------------------------------------------------------------

def real_cases(fails):
    print("6. the real stored records: the record counts only what is stored")
    m = vr()
    import verdict as vd
    import movers as mv
    urls = set()
    for name in vd._names():
        r = vd.load(name[:10], name[11:-5]) or {}
        for sym, v in (r.get("coins") or {}).items():
            if v.get("grade"):
                urls.add(vd.url(name[:10], sym))
    for r in mv.records():
        for sym, e in (r.get("coins") or {}).items():
            if (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {}).get("grade") and e.get("evidence"):
                urls.add(f"/why/{r['date_et']}-{e.get('gecko_id') or sym.lower()}")
    vs = m.graded()
    info(f"stored graded verdicts: {len(urls)}; later sources stored: {len(m.load_later())}")
    guarded(fails, f"the record holds exactly the {len(urls)} graded verdict(s) stored, by URL", lambda: {v['url'] for v in vs} == urls)
    guarded(fails, "the store of later sources exists and parses", lambda: os.path.exists(m.STORE) and isinstance(m.load_later(), list))
    guarded(fails, "every stored later source can count (nothing in the store is ignored)",
            lambda: not m.tally(vs, m.load_later())["ignored"])
    guarded(fails, "the record's first day is the first stored verdict record's (October 19, 2026, the Evening Brief)",
            lambda: m.first_day() == sorted(n[:10] for n in vd._names())[0])


# ---- 7. the wiring -------------------------------------------------------------------------------------------------------

def wiring_cases(fails):
    print("7. the wiring: the build writes the page, How we check links it, the sitemap lists it, no URL changed")
    import site_build as sb
    src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "the build writes verdict-record.html from verdict_record", lambda: re.search(r'w\("verdict-record\.html"', src))
    guarded(fails, "the sitemap lists /verdict-record.html", lambda: '"/verdict-record.html"' in src.split("# sitemap (indexable pages only")[1][:1500])
    guarded(fails, "every static page the sitemap listed before is still listed",
            lambda: all(f'"{p}"' in src.split("# sitemap (indexable pages only")[1][:1500] for p in OLD_LOCS))
    with quiet():
        h = sb.render_method([], "T")
    guarded(fails, "How we check links the verdict record", lambda: 'href="/verdict-record.html"' in h)
    guarded(fails, "its address is new: no page the site built before is at /verdict-record.html and nothing else moved",
            lambda: PAGE not in OLD_LOCS and not os.path.exists(os.path.join(HERE, "site", "verdict-record.html")))


# ---- the built tree -------------------------------------------------------------------------------------------------------

def info(msg):
    print("  INFO " + msg)


def page_rows(h):
    """[(url, grade, status)] as the built record lists them."""
    return re.findall(r'<li class="vr-r vr-(\w+)"><p><a href="(/why/[^"]+)">.*?</a></p><p class="vr-s">Graded (\w+)\.', h)


def tree_grades(root):
    """{url: grade} of every graded verdict page the build wrote: the grade its own card prints (U-10: the record is read
    against the pages it shipped beside, whatever records the build was given)."""
    out = {}
    d = os.path.join(root, "why")
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if n.endswith(".html"):
            g = re.search(r'class="vd-badge vd-\w+">Checked: <b>(\w+)</b>', open(os.path.join(d, n), encoding="utf-8").read())
            if g:
                out["/why/" + n[:-5]] = g.group(1)
    return out


def tree(root):
    fails = []
    print(f"8. the built tree {root}")
    p = os.path.join(root, "verdict-record.html")
    h = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    guarded(fails, "the build wrote verdict-record.html", lambda: bool(h))
    txt = visible(h)
    rows = [(u, g, st) for st, u, g in page_rows(h)]
    want = tree_grades(root)
    info(f"graded verdict pages in the tree: {len(want)}; rows on the record: {len(rows)}")
    guarded(fails, "the record lists every graded /why/ page the build wrote, once, with the grade that page prints, and nothing else",
            lambda: sorted((u, g) for u, g, _s in rows) == sorted(want.items()))
    lk = [r for r in rows if r[1] == "Likely"]
    n = {k: sum(1 for r in lk if r[2] == k) for k in ("confirmed", "reversed", "open")}
    guarded(fails, f"its headline counts are its own rows' ({len(lk)} Likely, {n['confirmed']} confirmed, {n['reversed']} reversed, {n['open']} open)",
            lambda: re.search(rf"\b{len(lk)}\b\s*Likely verdicts", txt) and re.search(rf"\b{n['reversed']}\b\s*reversed", txt)
            and re.search(rf"\b{n['confirmed']}\b\s*confirmed by a later primary source", txt)
            and re.search(rf"\b{n['open']}\b\s*not yet revisited", txt))
    guarded(fails, "with no graded page in the tree it says so; with no later source it says none has been revisited",
            lambda: ("No graded verdict is stored yet" in txt) if not rows else
            (("No verdict has been revisited yet" in txt) == all(r[2] == "open" for r in rows)))
    guarded(fails, "no 'because', no dash, no AI word, no personal name",
            lambda: not BECAUSE.search(txt) and not DASH.search(h) and not AI.search(txt) and not PERSON.search(h))
    sm = open(os.path.join(root, "sitemap-priority.xml"), encoding="utf-8").read() if os.path.exists(os.path.join(root, "sitemap-priority.xml")) else ""
    guarded(fails, "sitemap-priority.xml lists https://gocheckmycrypto.com/verdict-record", lambda: "<loc>https://gocheckmycrypto.com/verdict-record</loc>" in sm)
    mh = open(os.path.join(root, "method.html"), encoding="utf-8").read() if os.path.exists(os.path.join(root, "method.html")) else ""
    guarded(fails, "the built How we check links it", lambda: 'href="/verdict-record.html"' in mh)
    return fails


def unit():
    fails = []
    for name, fn in (("tally", tally_cases), ("reversed", reversed_cases), ("movers", movers_cases), ("page", page_cases),
                     ("add", add_cases), ("real", real_cases), ("wiring", wiring_cases)):
        group(fails, name, fn)
    return fails


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1])
    print(f"\nSPRINT 9.8: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
