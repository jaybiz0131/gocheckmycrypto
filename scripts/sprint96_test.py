#!/usr/bin/env python3
"""Program 9, Sprint 9.6: the share loop, re-aimed. Each case is named after what it guards.

  python3 scripts/sprint96_test.py          # unit cases; exit 1 on any failure
  python3 scripts/sprint96_test.py --tree <built publish dir>   # also the cases that read a built tree
  (verify_pipeline.py's canary also calls unit() and tree() on the tree it builds)

THE RECORDS ARE 9.2'S AND 9.3'S (scripts/sprint93_test.py): the real 14 October evening record (Likely, on the
Consumer Price Index release and the Real Earnings release, both 8:30 AM ET), the real 15 October evening record
(Unclear), the real 19 October evening verdict record (no verdict graded: the page's window and the measured run
went opposite ways), and the real 16 October morning Big movers record (scripts/sprint94_test.py). Cases marked
SYNTHETIC change a real record by hand to reach a grade the real days do not give (Confirmed, Disputed); they say
so on their name (Jack, 13 October 2026). NO MODEL CALL and no network: the cards are drawn from stored records.
"""
import contextlib
import copy
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
GRADE = re.compile(r"\b(Confirmed|Likely|Disputed|Unclear)\b")
BECAUSE = re.compile(r"\bbecause\b", re.I)
DASH = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
AI = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bHaiku\b|\bSonnet\b|"
                r"\bOpenAI\b|\bchatbot\b|algorithm|\bautomated\b|\bgenerated\b", re.I)
PERSON = re.compile(r"(?<!Crypto )\bCronkite\b|\bWalter\b|\bJack\b|\bBerno\b|\bfounder\b|\beditor-in-chief\b", re.I)
FIG = re.compile(r"\b\d{1,2}:\d{2} [AP]M\b|\d[\d,]*\.?\d*\s?%|\$[\d,]+(?:\.\d+)?(?:[KMB]| million| billion)?|\d[\d,.]*\s?bp\b")
UTC = dt.timezone.utc
ORIGIN = "https://gocheckmycrypto.com"


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


def sc():
    import share_cards
    return share_cards


# ---- the records: real, and SYNTHETIC where a grade is out of the real days' reach -------------------------------

_CACHE = {}


def vrec(name):
    """(verdict record, evidence record, day, slot) for a named fixture."""
    if name in _CACHE:
        return _CACHE[name]
    import verdict
    t = s93()
    table = {"likely": (t.rec(t.D14()), "2026-10-14", t.day14()),
             "unclear": (t.rec(t.D15()), "2026-10-15", t.day15()),
             "confirmed": (t.synthetic_confirmed(), "2026-10-14", t.day14()),
             "disputed": (t.synthetic_disputed_two(), "2026-10-14", t.day14())}
    ev, day, mv = table[name]
    v = verdict.record_from(ev, day, "evening", day=mv)
    _CACHE[name] = (v, ev, day, "evening")
    return _CACHE[name]


def spec_of(name, sym="BTC"):
    import verdict
    v, ev, day, _slot = vrec(name)
    return sc().verdict_spec(v, sym, ev, slug=verdict.slug(day, sym), day=day)


def page_text(name, sym="BTC"):
    """The verdict page's visible text, as built by verdict.build_pages for the fixture."""
    import verdict
    v, ev, day, slot = vrec(name)
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
        json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
        built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))
    return visible(next(b["html"] for b in built if b["path"].endswith(verdict.NAMES[sym][1])))


def words_of(spec):
    return " ".join(spec["words"])


# ---- 1. the card from a fixture -------------------------------------------------------------------------------------

def card_cases(fails):
    print("1. the card, from the real 14 and 15 October records and two SYNTHETIC grades")
    s = spec_of("likely")
    guarded(fails, "14 October Bitcoin (real): the card exists and carries the verdict's own grade, Likely",
            lambda: s and s["grade"] == "Likely" and "Checked: Likely" in words_of(s))
    guarded(fails, "14 October (real): the card names BOTH 8:30 AM releases, the Consumer Price Index and the Real Earnings "
                   "release, each with its time and its source (the BLS release schedule)",
            lambda: len(s["events"]) == 2 and "Consumer Price Index release" in words_of(s)
            and "Real Earnings release" in words_of(s)
            and all("8:30 AM ET" in " ".join(e["facts"]) and "BLS release schedule" in " ".join(e["facts"]) for e in s["events"]))
    guarded(fails, "14 October (real): the window is named on the card, 'Over the last 24 hours', to its time and day",
            lambda: "Over the last 24 hours" in words_of(s) and "Wednesday, October 14, 2026" in words_of(s)
            and "7:43 PM ET" in words_of(s))
    guarded(fails, "14 October (real): the heading is 'Why Bitcoin moved' and the card is the verdict's, not the Brief's "
                   "(no Brief, no Evening Edition, no morning read on it)",
            lambda: s["heading"] == "Why Bitcoin moved" and not re.search(r"\bBrief\b|Edition|morning read", words_of(s)))
    guarded(fails, "14 October (real): one figure per event, the next 60 minutes, with the price source named once "
                   "('Prices: Coinbase 5-minute candles')",
            lambda: [f["text"] for f in s["figures"]] == ["1.45%", "1.45%"]
            and sum(1 for w in s["words"] if w.startswith("Prices: Coinbase 5-minute candles")) == 1)
    u = spec_of("unclear")
    guarded(fails, "15 October Bitcoin (real): the card exists, grade Unclear, and says exactly "
                   "'No reported event lines up with this move.'",
            lambda: u and u["grade"] == "Unclear" and "No reported event lines up with this move." in u["words"])
    guarded(fails, "15 October (real): Unclear names no event and prints no figure (so no price source is claimed)",
            lambda: not u["events"] and not u["figures"] and not any(w.startswith("Prices:") for w in u["words"]))
    c = spec_of("confirmed")
    guarded(fails, "SYNTHETIC Confirmed (14 October's record with a primary source stating the cause): grade Confirmed, "
                   "the event is named, the timing and readings are the real ones",
            lambda: c and c["grade"] == "Confirmed" and c["events"])
    d = spec_of("disputed")
    guarded(fails, "SYNTHETIC Disputed (two outlets name different causes): grade Disputed and the card names both "
                   "events, with the reported cause stated in the card's own sentences",
            lambda: d and d["grade"] == "Disputed" and len(d["events"]) == 2)
    for nm in ("likely", "unclear", "confirmed", "disputed"):
        guarded(fails, f"{nm}: the grade on the card is the verdict record's own grade, not recomputed",
                lambda nm=nm: spec_of(nm)["grade"] == vrec(nm)[0]["coins"]["BTC"]["grade"])
    ether = vrec("likely")[0]
    guarded(fails, "Ether moved with Bitcoin (real, 14 October): the plain 'moved with Bitcoin' line is not a graded "
                   "verdict, so it gets no card of its own",
            lambda: sc().verdict_spec(ether, "ETH", vrec("likely")[1], slug="2026-10-14-ether", day="2026-10-14") is None)


# ---- 2. the tags on a verdict URL ----------------------------------------------------------------------------------

def _meta(html, key, attr="property"):
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', html)
    return m.group(1) if m else None


def _pages(name, sym="BTC", slot="evening"):
    """The built page for a fixture, with the share context the build passes (the PNG written to a temp dir)."""
    import verdict
    v, ev, day, _s = vrec(name)
    td = tempfile.mkdtemp(prefix="s96-")
    vd, wd, og = os.path.join(td, "verdict"), os.path.join(td, "why"), os.path.join(td, "og")
    os.makedirs(vd)
    os.makedirs(wd)
    json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
    json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
    ctx = sc().Ctx(directory=og, today=dt.date(2026, 10, 20))
    built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"), share=ctx)
    return built, ctx, og


def tag_cases(fails):
    print("2. Open Graph and Twitter tags on a verdict URL, pointing at that verdict's square image")
    built, ctx, og = _pages("likely")
    b = next(x for x in built if x["path"] == "/why/2026-10-14-bitcoin")
    h = b["html"]
    img = f"{ORIGIN}/og/why/2026-10-14-bitcoin.png"
    guarded(fails, "og:image is the verdict's own square image, an absolute https URL",
            lambda: _meta(h, "og:image") == img)
    guarded(fails, "twitter:image is the same absolute URL", lambda: _meta(h, "twitter:image", "name") == img)
    guarded(fails, "og:image:width and og:image:height are 1080 and 1080",
            lambda: (_meta(h, "og:image:width"), _meta(h, "og:image:height")) == ("1080", "1080"))
    alt = _meta(h, "og:image:alt")
    guarded(fails, "og:image:alt and twitter:image:alt are the same non-empty sentence that opens with the heading and names the "
                   "grade", lambda: alt and alt == _meta(h, "twitter:image:alt", "name") and alt.startswith("Why Bitcoin moved")
            and "Likely" in alt)
    guarded(fails, "twitter:card is 'summary' (a square image is shown whole; summary_large_image would crop it to two to one)",
            lambda: _meta(h, "twitter:card", "name") == "summary")
    guarded(fails, "og:url and the canonical are still the verdict's own URL, og:image:type is image/png",
            lambda: _meta(h, "og:url") == f"{ORIGIN}/why/2026-10-14-bitcoin" and _meta(h, "og:image:type") == "image/png")
    guarded(fails, "the image the tag names was written, at /og/why/<slug>.png, and is a PNG of 1080 by 1080",
            lambda: _png_size(os.path.join(og, "2026-10-14-bitcoin.png")) == (1080, 1080))
    guarded(fails, "the page's tags name no second image (one og:image, one twitter:image)",
            lambda: h.count('property="og:image"') == 1 and h.count('name="twitter:image"') == 1)
    plain, _c, _o = _pages("likely")[0], None, None
    import verdict
    v, ev, day, slot = vrec("likely")
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
        json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
        old = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))[0]
    guarded(fails, "a build that is given no share context writes the page it wrote before: the site card, 1200 by 630, "
                   "summary_large_image", lambda: _meta(old["html"], "og:image") == f"{ORIGIN}/og-image.png"
            and _meta(old["html"], "og:image:width") == "1200" and _meta(old["html"], "twitter:card", "name") == "summary_large_image")
    import site_build as sb
    other = sb.shell("T - GoCheckMyCrypto", "d", "Home", "<main>x</main>", "D", path="/x.html")
    guarded(fails, "every other page's tags are unchanged: the site card at 1200 by 630 and summary_large_image",
            lambda: _meta(other, "og:image") == f"{ORIGIN}/og-image.png" and _meta(other, "og:image:width") == "1200"
            and _meta(other, "twitter:card", "name") == "summary_large_image")
    # a render that fails leaves the page with the site card, never a tag naming a missing file
    ctx2 = sc().Ctx(directory="/proc/definitely/not/writable", today=dt.date(2026, 10, 20))
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
        json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
        with contextlib.redirect_stdout(io.StringIO()):
            failed = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"), share=ctx2)[0]
    guarded(fails, "an image that cannot be written leaves the page on the site card and the page still builds",
            lambda: _meta(failed["html"], "og:image") == f"{ORIGIN}/og-image.png")
    # Big movers' verdict pages carry the same tags
    t = s94()
    with tempfile.TemporaryDirectory() as td:
        r = t.graded16(td)
        mdir = os.path.join(td, "movers")
        os.makedirs(mdir)
        json.dump(r, open(os.path.join(mdir, f"{t.DAY16}-morning.json"), "w"))
        import movers
        ctx3 = sc().Ctx(directory=os.path.join(td, "og"), today=dt.date(2026, 10, 20))
        pages = movers.build_pages(mdir, share=ctx3)
        guarded(fails, "every Big movers verdict page carries its own square image tags (absolute URL, 1080 by 1080, alt)",
                lambda: pages and all(_meta(p["html"], "og:image") == f"{ORIGIN}/og/why/{p['path'].split('/')[-1]}.png"
                                      and _meta(p["html"], "og:image:height") == "1080" and _meta(p["html"], "og:image:alt")
                                      for p in pages))


def _png_size(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size


# ---- 3. the queue entry --------------------------------------------------------------------------------------------

def queue_cases(fails):
    print("3. the queue Jack posts from: a file per card, the existing linkedin-queue shape, nothing posted")
    import publicist
    s = spec_of("likely")
    name, text = sc().queue_entry(s)
    guarded(fails, "the entry's file is linkedin-queue/<date>-why-<coin>.md, beside the publicist's drafts",
            lambda: name == "2026-10-14-why-bitcoin.md")
    guarded(fails, "the entry lists the page URL, the image URL and the image path, all absolute where they are URLs",
            lambda: f"Story: {ORIGIN}/why/2026-10-14-bitcoin" in text
            and f"Image: {ORIGIN}/og/why/2026-10-14-bitcoin.png" in text and "Image path: /og/why/2026-10-14-bitcoin.png" in text)
    guarded(fails, "the entry keeps the publicist's shape: a heading, the story line, the framing box, then the "
                   "ready-to-paste draft",
            lambda: text.startswith("# LinkedIn draft: ") and "YOUR FRAMING" in text
            and "---- READY-TO-PASTE DRAFT (passed all " in text)
    post = text.split("----\n\n", 1)[1].strip()
    ok, rep = publicist.run_gates(post, f"{ORIGIN}/why/2026-10-14-bitcoin")
    guarded(fails, f"the suggested post line passes the publicist's own gates ({'; '.join(r for r in rep if r.startswith('FAIL')) or 'all'})",
            lambda: ok)
    left = post.replace(f"{ORIGIN}/why/2026-10-14-bitcoin", "")
    for w in sorted(set(s["words"]), key=len, reverse=True):
        left = left.replace(w, "")
    guarded(fails, f"the post line is built only from the card's own words: take away every string the card prints and the "
                   f"page address, and nothing is left ({left.strip()[:60] or 'nothing'})", lambda: not left.strip())
    guarded(fails, "the post line names the grade, no other grade word, no 'because', no AI, no person, no dash",
            lambda: set(GRADE.findall(post)) == {"Likely"} and not BECAUSE.search(post) and not AI.search(post)
            and not PERSON.search(post) and not DASH.search(post))
    # nothing posts, nothing needs a credential
    import urllib.request
    import share_queue
    posted = []
    real_open = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: posted.append(a) or (_ for _ in ()).throw(AssertionError("network"))
    env = {k: os.environ.pop(k, None) for k in ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN", "ANTHROPIC_API_KEY")}
    try:
        with tempfile.TemporaryDirectory() as td:
            vd, wd, qd = os.path.join(td, "verdict"), os.path.join(td, "why"), os.path.join(td, "q")
            os.makedirs(vd)
            os.makedirs(wd)
            v, ev, day, slot = vrec("likely")
            json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
            json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
            kw = dict(vdir=vd, wdir=wd, tdir=os.path.join(td, "none"), mdir=os.path.join(td, "nomovers"), qdir=qd,
                      today=dt.date(2026, 10, 20), days=30)
            with contextlib.redirect_stdout(io.StringIO()):
                wrote = share_queue.run(**kw)
                again = share_queue.run(**kw)
            guarded(fails, "the run writes one file for the verdict and one for the day, with no credential in the environment "
                           "and no network call", lambda: sorted(os.path.basename(p) for p in wrote)
                    == ["2026-10-14-why-bitcoin.md", "2026-10-14-why-day.md"] and not posted)
            guarded(fails, "a second run writes nothing: an entry that exists is never rewritten (Jack's framing stays)",
                    lambda: again == [])
            open(os.path.join(qd, "2026-10-14-why-bitcoin.md"), "a").write("MY FRAMING\n")
            with contextlib.redirect_stdout(io.StringIO()):
                share_queue.run(**kw)
            guarded(fails, "an edited entry is left as Jack left it",
                    lambda: open(os.path.join(qd, "2026-10-14-why-bitcoin.md")).read().endswith("MY FRAMING\n"))
            with tempfile.TemporaryDirectory() as td3:
                same_day = dict(kw, qdir=os.path.join(td3, "q"), today=dt.date(2026, 10, 14), days=3)
                vm = copy.deepcopy(v)
                vm["slot"] = "morning"
                os.remove(os.path.join(vd, f"{day}-{slot}.json"))
                json.dump(vm, open(os.path.join(vd, f"{day}-morning.json"), "w"))
                json.dump(ev, open(os.path.join(wd, f"{day}-morning.json"), "w"))
                with contextlib.redirect_stdout(io.StringIO()):
                    early = share_queue.run(**same_day)
                    late = share_queue.run(**dict(same_day, today=dt.date(2026, 10, 15)))
                guarded(fails, "a morning-only verdict is not queued on its own day (the card is not final), and is queued once "
                               "the day is over", lambda: early == [] and sorted(os.path.basename(p) for p in late)
                        == ["2026-10-14-why-bitcoin.md", "2026-10-14-why-day.md"])
            old = dict(kw, today=dt.date(2026, 12, 25), days=3)
            with contextlib.redirect_stdout(io.StringIO()):
                old_wrote = share_queue.run(**dict(old, qdir=os.path.join(td, "q2")))
            guarded(fails, "an old day is not queued (only the last few days are new)", lambda: old_wrote == [])
    finally:
        urllib.request.urlopen = real_open
        for k, v2 in env.items():
            if v2 is not None:
                os.environ[k] = v2
    bad = copy.deepcopy(s)
    bad["post_lines"] = bad["post_lines"] + ["A huge move for crypto."]
    guarded(fails, "SYNTHETIC: a post line the publicist's gates refuse (a banned word) files no entry",
            lambda: sc().queue_entry(bad) is None)
    src = open(os.path.join(HERE, "share_queue.py"), encoding="utf-8").read()
    guarded(fails, "share_queue.py imports no HTTP client and reads no credential",
            lambda: not re.search(r"urllib|requests|http\.client|LINKEDIN|ANTHROPIC|os\.environ", src))


# ---- 4. a withheld or deferred verdict makes no card ---------------------------------------------------------------

def nocard_cases(fails):
    print("4. 'Verdict at the next read' and a verdict withheld at the cap make no share card")
    import verdict
    v, ev, day, slot = vrec("likely")
    nr = copy.deepcopy(v)
    nr["coins"]["BTC"].update(kind="next_read", grade=None, text=[verdict.NEXT_READ], line=[verdict.NEXT_READ], url=None)
    wh = copy.deepcopy(v)
    wh["coins"]["BTC"].update(kind="withheld", grade_withheld="Likely", grade=None, text=[], by="withheld", url=None)
    for nm, rec in (("Verdict at the next read", nr), ("withheld at the cap", wh)):
        guarded(fails, f"{nm}: no spec, so no image and no tags", lambda rec=rec: sc().verdict_spec(rec, "BTC", ev,
                slug="2026-10-14-bitcoin", day=day) is None)
        with tempfile.TemporaryDirectory() as td:
            vd, wd, og = os.path.join(td, "verdict"), os.path.join(td, "why"), os.path.join(td, "og")
            os.makedirs(vd)
            os.makedirs(wd)
            json.dump(rec, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
            json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
            tdd = os.path.join(td, "today")
            os.makedirs(tdd)
            json.dump({"date_et": day, "slot": slot}, open(os.path.join(tdd, f"{day}-{slot}.json"), "w"))
            ctx = sc().Ctx(directory=og, today=dt.date(2026, 10, 20))
            built = verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"), share=ctx)
            guarded(fails, f"{nm}: the build makes no /why/ page, no PNG and no queue spec for the verdict",
                    lambda: not built and not os.path.isdir(og) and not [s for s in ctx.specs if s["kind"] == "verdict"])
            days = sc().day_specs(vd, wd, tdd, today=dt.date(2026, 10, 20))
            d = days[0] if days else None
            guarded(fails, f"{nm}: the day's card says exactly that no verdict was graded, and names no grade",
                    lambda: d and d["graded"] == [] and "No verdict was graded for Bitcoin or Ether." in d["words"]
                    and not GRADE.search(words_of(d)))
    real = verdict.load("2026-10-19", "evening", os.path.join(HERE, "site", "data", "verdict"))
    with tempfile.TemporaryDirectory() as td:
        vd = os.path.join(td, "verdict")
        os.makedirs(vd)
        json.dump(real, open(os.path.join(vd, "2026-10-19-evening.json"), "w"))
        days = sc().day_specs(vd, os.path.join(td, "why"), os.path.join(HERE, "site", "data", "today"), today=dt.date(2026, 10, 20))
        d = days[0]
        guarded(fails, "19 October (real record, no verdict graded): a day card that says so, links the day's answer, "
                       "invents no verdict",
                lambda: d["graded"] == [] and "No verdict was graded for Bitcoin or Ether." in d["words"]
                and d["page"] == "/today/2026-10-19" and not GRADE.search(words_of(d)) and not d["figures"])


# ---- 5. the day card -----------------------------------------------------------------------------------------------

def day_cases(fails):
    print("5. a square card per day: the day's graded verdicts, or the truthful no-verdict card")
    import verdict
    v, ev, day, slot = vrec("likely")
    u, ev15, day15, _s = vrec("unclear")
    with tempfile.TemporaryDirectory() as td:
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        for rec, e, d in ((v, ev, day), (u, ev15, day15)):
            json.dump(rec, open(os.path.join(vd, f"{d}-evening.json"), "w"))
            json.dump(e, open(os.path.join(wd, f"{d}-evening.json"), "w"))
        days = {x["day"]: x for x in sc().day_specs(vd, wd, os.path.join(td, "none"), today=dt.date(2026, 10, 20))}
    d14, d15 = days["2026-10-14"], days["2026-10-15"]
    guarded(fails, "14 October: the day card lists Bitcoin's graded verdict (Likely) and links its /why/ page; Ether, which only "
                   "moved with Bitcoin, is not listed as graded",
            lambda: [(g["name"], g["grade"], g["page"]) for g in d14["graded"]] == [("Bitcoin", "Likely", "/why/2026-10-14-bitcoin")])
    guarded(fails, "15 October: the day card lists Bitcoin Unclear with the exact line 'No reported event lines up with this move.'",
            lambda: [(g["name"], g["grade"]) for g in d15["graded"]] == [("Bitcoin", "Unclear")]
            and "No reported event lines up with this move." in d15["words"])
    guarded(fails, "the day card's grade is the verdict's own, and its date is the day's, written out",
            lambda: "Wednesday, October 14, 2026" in words_of(d14) and "Checked: Likely" in words_of(d14))
    guarded(fails, "a day card prints no figure (so none can lack its source)", lambda: not FIG.search(words_of(d14)) and not d14["figures"])
    guarded(fails, "the day card's page is the day's answer when it exists, else the day's first verdict page",
            lambda: d14["page"] == "/why/2026-10-14-bitcoin")


# ---- 6. no grade word, no 'because', no figure on a card that is not on its page ----------------------------------

def words_cases(fails):
    print("6. every card's words: its own grade only, 'because' only on Confirmed, no figure the page lacks, no AI, no name, no dash")
    for nm in ("likely", "unclear", "confirmed", "disputed"):
        s = spec_of(nm)
        txt = words_of(s)
        page = page_text(nm)
        guarded(fails, f"{nm}: the only grade word on the card is its own ({sorted(set(GRADE.findall(txt)))})",
                lambda s=s, txt=txt: set(GRADE.findall(txt)) == {s["grade"]})
        guarded(fails, f"{nm}: 'because' is on the card only if the grade is Confirmed",
                lambda s=s, txt=txt: (not BECAUSE.search(txt)) or s["grade"] == "Confirmed")
        miss = sorted({f for f in FIG.findall(txt)} - {f for f in FIG.findall(page)})
        guarded(fails, f"{nm}: every figure on the card is on the verdict page ({miss or 'all'})", lambda miss=miss: not miss)
        guarded(fails, f"{nm}: no AI mention, no personal name, no em dash or en dash on the card",
                lambda txt=txt: not AI.search(txt) and not PERSON.search(txt) and not DASH.search(txt))
        guarded(fails, f"{nm}: every figure on the card has its source on the card (a time names the BLS schedule or a report's outlet; "
                       f"a price move names the price source)",
                lambda s=s: all(_sourced(s, f) for f in s["figures"]) and all(_sourced_time(e) for e in s["events"]))
    # the build refuses a card whose figure the page does not carry: SYNTHETIC, a figure added to the sentences
    import verdict
    v, ev, day, _s = vrec("likely")
    first = list(v["coins"]["BTC"]["text"])

    def mutated(sents, rec=v):
        m = copy.deepcopy(rec)
        m["coins"]["BTC"]["text"] = sents
        return m
    ctl = _forced_spec(v, ev, day)
    guarded(fails, "control: the verdict's own text, put through the same path the synthetic cases use, draws the card",
            lambda: ctl and ctl["grade"] == "Likely" and ctl["sentences"] == first)
    for what, sents in (("'because' on a Likely card", ["Bitcoin fell because of the Consumer Price Index release.", first[1]]),
                        ("a second grade word (Disputed)", [first[0], first[1] + " It was a Disputed matter."]),
                        ("an AI mention", ["Bitcoin fell after an AI model flagged the Consumer Price Index release.", first[1]]),
                        ("a personal name", ["Jack says Bitcoin fell after the Consumer Price Index release.", first[1]]),
                        ("a dash", ["Bitcoin fell after the Consumer Price Index release \u2014 on the day.", first[1]])):
        guarded(fails, f"SYNTHETIC: {what} in the verdict's words makes no card (fail closed)",
                lambda sents=sents: _forced_spec(mutated(sents), ev, day) is None)
    # the page loses the figures its card carries (the drift the check guards against): SYNTHETIC, the page's text read back empty
    cmod = sc()
    real_visible = cmod.visible
    cmod.visible = lambda h: ""
    try:
        guarded(fails, "SYNTHETIC: a page that does not print the card's figures (its times, the 1.45%) leaves the card undrawn "
                       "(fail closed)", lambda: cmod.verdict_spec(v, "BTC", ev, slug="2026-10-14-bitcoin", day=day) is None)
    finally:
        cmod.visible = real_visible
    cv, cev, cday, _cs = vrec("confirmed")
    guarded(fails, "SYNTHETIC: 'because' on a Confirmed card is allowed (the one grade that may say it)",
            lambda: (_forced_spec(mutated(["Bitcoin fell because of the Consumer Price Index release.", first[1]], cv), cev, cday) or {}).get("grade") == "Confirmed")
    corr = copy.deepcopy(v)
    corr["coins"]["BTC"]["corrections"] = [{"date": "October 16, 2026", "text": "This verdict named the wrong hour."}]
    guarded(fails, "SYNTHETIC: a verdict with a standing correction is not passed around (no card)",
            lambda: sc().verdict_spec(corr, "BTC", ev, slug="2026-10-14-bitcoin", day=day) is None)
    badw = copy.deepcopy(v)
    badw["coins"]["BTC"]["text"] = ["Bitcoin fell because of the Consumer Price Index release.", "It was a Disputed matter."]
    r = sc().verdict_spec(badw, "BTC", ev, slug="2026-10-14-bitcoin", day=day)
    guarded(fails, "SYNTHETIC: 'because' on a Likely card, or a second grade word, makes no card (fail closed)", lambda: r is None)


def _forced_spec(vrec, ev, day):
    """verdict_spec with text_sec bypassed, so the synthetic sentence reaches the card as the card's own words."""
    import verdict
    old = verdict.text_sec
    verdict.text_sec = lambda v: list(v.get("text") or [])
    try:
        return sc().verdict_spec(vrec, "BTC", ev, slug="2026-10-14-bitcoin", day=day)
    finally:
        verdict.text_sec = old


def _sourced(spec, fig):
    return fig.get("source") and any(fig["source"] in w for w in spec["words"])


def _sourced_time(e):
    return bool(e["facts"]) and any(("schedule" in f) or re.search(r"First reported .*·|First reported .*, \d+ source", f) or "Federal Register" in f
                                    or "reported" in f for f in e["facts"])


# ---- 7. color truth ------------------------------------------------------------------------------------------------

def color_cases(fails):
    print("7. color truth: no up or down color beside a figure of the other sign; the grade mark is never up or down colored")
    cs = sc()
    for nm in ("likely", "unclear", "confirmed", "disputed"):
        s = spec_of(nm)
        ops = cs.layout(s)
        figs = [o for o in ops if o.get("role") == "figure"]
        guarded(fails, f"{nm}: every figure's color role agrees with its sign (up green with a plus or up arrow, down with a down arrow)",
                lambda s=s, figs=figs: len(figs) == len(s["figures"]) and all(_agrees(o) for o in figs))
        coloured = [o for o in ops if tuple(o.get("fill", ())) in (cs.UP, cs.DOWN)]
        guarded(fails, f"{nm}: nothing but a figure is drawn in the up or the down color (the grade chip, the dot, the words are neutral)",
                lambda coloured=coloured: all(o.get("role") == "figure" for o in coloured))
        chip = [o for o in ops if o.get("role") in ("chip", "chip-mark")]
        guarded(fails, f"{nm}: the grade chip and its mark are neutral ink (never green, never red)",
                lambda chip=chip: chip and all(tuple(o["fill"]) in cs.NEUTRALS for o in chip))
    # in the pixels: the down card has the down color and not one up-colored pixel; a SYNTHETIC rise has the reverse
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "a.png")
        cs.render(spec_of("likely"), p)
        im = Image.open(p).convert("RGB")
        px = im.getdata()
        down = sum(1 for q in px if _near(q, cs.DOWN, 40))
        up = sum(1 for q in px if _near(q, cs.UP, 40))
        guarded(fails, f"14 October (a fall): the image holds the down color ({down} px) and no up color ({up} px)", lambda: down > 150 and up == 0)
        rise = copy.deepcopy(spec_of("likely"))
        for f in rise["figures"]:
            f["value"], f["text"] = abs(f["value"]), f["text"]
        rise["events"][0]["figure"]["value"] = abs(rise["events"][0]["figure"]["value"])
        rise["events"][1]["figure"]["value"] = abs(rise["events"][1]["figure"]["value"])
        cs.render(rise, p)
        px = Image.open(p).convert("RGB").getdata()
        down2 = sum(1 for q in px if _near(q, cs.DOWN, 40))
        up2 = sum(1 for q in px if _near(q, cs.UP, 40))
        guarded(fails, f"SYNTHETIC rise (the same card with the sign turned): green figures ({up2} px), no red ({down2} px)",
                lambda: up2 > 150 and down2 == 0)


def _near(a, b, tol):
    return all(abs(a[i] - b[i]) <= tol for i in range(3))


def _agrees(o):
    sign = o["sign"]
    col = tuple(o["fill"])
    import share_cards as cs
    arrow_up, arrow_down = "▲" in o["text"], "▼" in o["text"]
    if sign > 0:
        return col == cs.UP and arrow_up and not arrow_down
    if sign < 0:
        return col == cs.DOWN and arrow_down and not arrow_up
    return col in cs.NEUTRALS


# ---- 8. the image: dimensions, weight, determinism -----------------------------------------------------------------

def image_cases(fails):
    print("8. the image: 1080 by 1080, light, drawn the same every time, from the repo's own fonts")
    cs = sc()
    with tempfile.TemporaryDirectory() as td:
        outs = {}
        for nm in ("likely", "unclear", "confirmed", "disputed"):
            p = os.path.join(td, nm + ".png")
            cs.render(spec_of(nm), p)
            outs[nm] = p
        for nm, p in outs.items():
            guarded(fails, f"{nm}: a PNG of exactly 1080 by 1080", lambda p=p: _png_size(p) == (1080, 1080))
            guarded(fails, f"{nm}: under 100 KB ({os.path.getsize(p) // 1024} KB)", lambda p=p: os.path.getsize(p) < 100 * 1024)
        p2 = os.path.join(td, "again.png")
        cs.render(spec_of("likely"), p2)
        guarded(fails, "drawn twice, the same bytes (deterministic: no stamp, no randomness)",
                lambda: hashlib.sha256(open(outs["likely"], "rb").read()).hexdigest() == hashlib.sha256(open(p2, "rb").read()).hexdigest())
        guarded(fails, "the four cards are four different images",
                lambda: len({hashlib.sha256(open(p, "rb").read()).hexdigest() for p in outs.values()}) == 4)
        for fn in ("IBMPlexMono-SemiBold.ttf", "IBMPlexMono-Medium.ttf", "Newsreader.ttf"):
            guarded(fails, f"the shipped face {fn} is the one drawn with (U-10: a stand-in font fails loudly)",
                    lambda fn=fn: os.path.getsize(os.path.join(HERE, "site", "assets", "fonts", fn)) > 50000)
        guarded(fails, "the renderer refuses a stand-in font rather than drawing with Pillow's default",
                lambda: _refuses_standin())
    # a long sentence cannot spill off the card: the layout either fits or the card is refused
    s = copy.deepcopy(spec_of("disputed"))
    s["sentences"] = ["A very long sentence about a thing " * 30]
    guarded(fails, "SYNTHETIC: text too long for the square makes no card (fail closed), never a clipped one",
            lambda: _refuses(s))
    # layout stays inside the square for every fixture
    for nm in ("likely", "unclear", "confirmed", "disputed"):
        ops = cs.layout(spec_of(nm))
        guarded(fails, f"{nm}: every line of text sits inside the 1080 square with its padding",
                lambda ops=ops: all(o["x1"] <= 1080 - cs.PAD and o["x0"] >= cs.PAD - 1 and o["y1"] <= 1080 - 20 for o in ops if o.get("kind") == "text"))


def _refuses(s):
    try:
        out = sc().layout(s)
    except sc().CardError:
        return True
    return False if out else True


def _refuses_standin():
    cs = sc()
    old = cs.og_render.FONTS
    cs.og_render.FONTS = "/nonexistent"
    try:
        cs.fonts_ok()
    except cs.CardError:
        return True
    finally:
        cs.og_render.FONTS = old
    return False


# ---- 9. wiring: the build, the run step, the sitemaps, no URL changed ----------------------------------------------

def wiring_cases(fails):
    print("9. wired into the build and the two run workflows; no URL changed")
    sb_src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
    guarded(fails, "the build hands the verdict and movers page builders a share context pointing at PUBLISH/og/why",
            lambda: re.search(r"share_cards\.Ctx\(directory=os\.path\.join\(PUBLISH, \"og\", \"why\"\)", sb_src))
    guarded(fails, "the build passes the share context to the verdict builder and to the movers builder",
            lambda: "_vd.build_pages(dateline=dateline, share=_share)" in sb_src
            and "_mv.build_pages(dateline=dateline, share=_share)" in sb_src)
    guarded(fails, "the build draws the day cards into the same directory", lambda: "share_cards.day_specs(" in sb_src and "share_cards.draw(d, _share.directory)" in sb_src)
    for wf in ("morning-read.yml", "crypto-news-brief.yml"):
        y = open(os.path.join(HERE, ".github", "workflows", wf), encoding="utf-8").read()
        guarded(fails, f"{wf}: share_queue.py runs after the verdict and movers steps, fail open, with a timeout",
                lambda y=y: re.search(r"movers\.py --write \|\| true.*?timeout \d+ python3 share_queue\.py \|\| true", y, re.S))
        guarded(fails, f"{wf}: the commit stages linkedin-queue/ by name (never git add -A)",
                lambda y=y: "git add linkedin-queue" in y)
        step = re.search(r"- name: [^\n]*[Ss]hare[^\n]*\n(.*?)(?=\n      - name:)", y, re.S)
        guarded(fails, f"{wf}: the share step takes no secret", lambda step=step: step and "secrets." not in step.group(1))
    guarded(fails, "the publicist workflow is untouched (still manual only)",
            lambda: "cron" not in re.sub(r"#.*", "", open(os.path.join(HERE, ".github", "workflows", "publicist.yml")).read()))
    import verdict
    with tempfile.TemporaryDirectory() as td:
        v, ev, day, slot = vrec("likely")
        vd, wd = os.path.join(td, "verdict"), os.path.join(td, "why")
        os.makedirs(vd)
        os.makedirs(wd)
        json.dump(v, open(os.path.join(vd, f"{day}-{slot}.json"), "w"))
        json.dump(ev, open(os.path.join(wd, f"{day}-{slot}.json"), "w"))
        a = [(b["rel"], b["path"]) for b in verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"))]
        b2 = [(b["rel"], b["path"]) for b in verdict.build_pages(vd, wd, tdir=os.path.join(td, "none"),
                                                                share=sc().Ctx(directory=os.path.join(td, "og"), today=dt.date(2026, 10, 20)))]
    guarded(fails, "the share context changes no page path: the same /why/ URLs with it and without it", lambda: a == b2 and a)


# ---- the cases that read a built tree ------------------------------------------------------------------------------

def tree(root, expect_pages=False):
    """The cases that read the tree a build wrote. Returns the failures. `expect_pages`: the build was given graded verdict
    records (the canary's fixture build), so a tree with no /why/ page is a failure; a plain build of a tree whose stored
    days graded nothing has none, says so, and is not failed for it."""
    fails = []
    print(f"10. the built tree {root}")
    pub = lambda rel: os.path.join(root, rel)
    rd = lambda rel: open(pub(rel), encoding="utf-8", errors="replace").read() if os.path.exists(pub(rel)) else ""
    pages = sorted(n[:-5] for n in os.listdir(pub("why")) if n.endswith(".html")) if os.path.isdir(pub("why")) else []
    if expect_pages:
        guarded(fails, f"the build wrote /why/ pages ({len(pages)})", lambda: pages)
    elif not pages:
        print("  note this tree has no /why/ page (its stored days graded nothing); the canary's fixture build is the one that "
              "asserts pages and their images")
    for slug in pages:
        h = rd(f"why/{slug}.html")
        img = _meta(h, "og:image")
        want = f"{ORIGIN}/og/why/{slug}.png"
        guarded(fails, f"/why/{slug}: og:image is its own square image and the file is in the tree at 1080 by 1080",
                lambda img=img, want=want, slug=slug: img == want and os.path.exists(pub(f"og/why/{slug}.png"))
                and _png_size(pub(f"og/why/{slug}.png")) == (1080, 1080))
    days = [n for n in os.listdir(pub("og/why")) if n.startswith("day-")] if os.path.isdir(pub("og/why")) else []
    guarded(fails, f"the day cards the build drew are 1080 by 1080 too ({len(days)})",
            lambda: (bool(days) or not expect_pages) and all(_png_size(pub("og/why/" + n)) == (1080, 1080) for n in days))
    guarded(fails, "the images add to the tree and remove nothing: the site card and the apple-touch icon are still written",
            lambda: os.path.exists(pub("og-image.png")) and os.path.exists(pub("apple-touch-icon.png")))
    sm = rd("sitemap-archive.xml") + rd("news-sitemap.xml")
    guarded(fails, "no image is listed in a sitemap as a page (the share images are not URLs of the site's pages)", lambda: "/og/why/" not in sm)
    total = sum(os.path.getsize(pub("og/why/" + n)) for n in os.listdir(pub("og/why"))) if os.path.isdir(pub("og/why")) else 0
    guarded(fails, f"the cards weigh under 100 KB each in the tree ({total // 1024} KB in all)",
            lambda: all(os.path.getsize(pub("og/why/" + n)) < 100 * 1024 for n in os.listdir(pub("og/why"))))
    return fails


def rulings_cases(fails):
    print("11. the strategist's rulings of October 20 (J-8, J-9 item 3): the Unclear cards with their own lines, no card at the next read")
    import verdict
    import sprint95_test as t95
    t = s93()
    d14 = t.day14()
    for what, fit, line in (("J-8(a) readings do not match", "contradict", verdict.READINGS_MISMATCH),
                            ("J-8(a) readings silent", "silent", verdict.READINGS_MISMATCH)):
        r = t95.synth_events([("syn-a", "wire", "Alpha Labs announced a partnership with Beta Corp", 30, fit)])
        v = verdict.record_from(r, "2026-10-14", "evening", day=d14)
        sp = sc().verdict_spec(v, "BTC", r, slug="2026-10-14-bitcoin", day="2026-10-14")
        guarded(fails, f"SYNTHETIC {what}: an Unclear card that prints its own line, names the event, claims no cause",
                lambda sp=sp, line=line: sp and sp["grade"] == "Unclear" and line in sp["words"] and sp["events"]
                and not BECAUSE.search(words_of(sp)))
    r = t95.synth_events([("syn-a", "listing", "Binance Will List Alpha (ALP)", 30, "agree")])
    v = verdict.record_from(r, "2026-10-14", "evening", day=d14)
    sp = sc().verdict_spec(v, "BTC", r, slug="2026-10-14-bitcoin", day="2026-10-14")
    guarded(fails, "SYNTHETIC J-9(3): a lone listing that ran against its own direction is an Unclear card with 'A reported event lines "
                   "up in time, but the move ran the other way.', naming the event",
            lambda: sp and sp["grade"] == "Unclear" and verdict.OTHER_WAY in sp["words"] and sp["events"])
    guarded(fails, "the Unclear card for both rulings carries Unclear's printed definition and no other grade word",
            lambda: sp and verdict.DEFINITIONS["Unclear"] in sp["words"] and set(GRADE.findall(words_of(sp))) == {"Unclear"})


def unit():
    fails = []
    for name, fn in (("cards", card_cases), ("tags", tag_cases), ("queue", queue_cases), ("no card", nocard_cases),
                     ("day", day_cases), ("words", words_cases), ("color", color_cases), ("image", image_cases),
                     ("wiring", wiring_cases), ("rulings of October 20", rulings_cases)):
        group(fails, name, fn)
    return fails


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1], "--expect-pages" in args)
    print(f"\nSPRINT 9.6: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
