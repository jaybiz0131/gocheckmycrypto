#!/usr/bin/env python3
"""Hotfix 9.9h (October 26, 2026): the canary red on main since the morning read's commit 83b294e. Each case is named after
what it guards. Five failures, all from the day's stored data, none from code:

  1. sprint 9.5  a built page printed the old name "the Board" (the morning read's stored line on the home)
  2-3. sprint 9.7  two Brief-feed checks read the LIVE site/data/morning.json at a pinned October 20 clock
  4. sprint 9.7  "no feed has a dash" failed on an AI word inside a source link's address in the news feed
  5. sprint 9.8  the record listed a verdict (the real October 25 store entry) whose /why/ page the fixture build lacks

  python3 scripts/sprint99h_test.py          # exit 1 on any failure
NO MODEL CALL and no network. Fixtures: fixtures/sprint99h/morning-2026-10-26.json is the stored October 26 read, byte for
byte; fixtures/sprint97/morning-2026-10-20.json is the stored October 20 read as main held it at 540fd87.
"""
import contextlib
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


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def load(*parts):
    return json.load(open(os.path.join(HERE, *parts), encoding="utf-8"))


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def case_1_names(fails):
    print("1. the morning read and the old name 'the Board' (sprint 9.5)")
    import home
    import morning
    import phrases
    stored = load("fixtures", "sprint99h", "morning-2026-10-26.json")
    now = dt.datetime(2026, 10, 26, 16, 0, tzinfo=UTC)
    prompt = open(os.path.join(HERE, "prompts", "morning.md"), encoding="utf-8").read()
    m = re.search(r"\b[Tt]he Board\b", prompt)
    guarded(fails, "the morning prompt carries no old name" + (f" (found {m.group(0)!r})" if m else ""), lambda: not m)
    guarded(fails, "the morning prompt teaches the ruled name: Markets shows",
            lambda: "Markets shows" in prompt)
    guarded(fails, "phrases.has_old_name finds 'the Board shows' and 'the Board's' and not 'the Board of Governors'",
            lambda: phrases.has_old_name("ETFs saw outflows, the Board shows.") and phrases.has_old_name("the Board's tile")
            and not phrases.has_old_name("the Board of Governors met") and not phrases.has_old_name("Markets shows it"))
    obj = {"headline": "Bitcoin steady as the wire carries two items",
           "sentences": ["Spot ETFs saw outflows of $137.9M on the day, October 23, the Board shows.",
                         "The wire's top line: a bank filed a complaint.",
                         "Funding on Bitcoin perpetual futures is warm."],
           "narrative_line": "Quiet tape."}
    with quiet():
        head, sents, _line = morning.clean(obj, None)
    guarded(fails, "morning.clean cuts the sentence that carries the old name and keeps the others whole",
            lambda: sents == obj["sentences"][1:])
    guarded(fails, "the stored October 26 read carries the old name in its first sentence (the premise)",
            lambda: phrases.has_old_name(stored["sentences"][0]))
    mine = home.usable_morning(stored, None, now)
    guarded(fails, "today's stored read is used by the home with that one sentence withheld, the others as stored, none reworded",
            lambda: mine and mine["sentences"] == stored["sentences"][1:] and mine["headline"] == stored["headline"])
    guarded(fails, "the stored file itself is not changed by the home reading it",
            lambda: stored["sentences"][0].endswith("the Board shows."))
    allbad = dict(stored, sentences=[stored["sentences"][0]])
    guarded(fails, "a stored read left with no sentence falls back (usable_morning returns None), as a read with none does",
            lambda: home.usable_morning(allbad, None, now) is None)
    band = home.narrative_band({}, {"stamp_et": "x"}, None, now, mine)
    guarded(fails, "the home's Brief card, built from today's stored read, prints no old name",
            lambda: band and not re.search(r"\b[Tt]he Board\b", re.sub(r"<[^>]+>", " ", band)))


def case_2_pinned_morning(fails):
    print("2-3. the Brief-feed checks at the October 20 clock read a pinned fixture (sprint 9.7)")
    src = open(os.path.join(HERE, "scripts", "sprint97_test.py"), encoding="utf-8").read()
    lo = src.index("def news_brief_cases")
    hi = src.index("def why_cases")
    body = src[lo:hi]
    guarded(fails, "news_brief_cases does not read the live site/data/morning.json",
            lambda: '"site", "data", "morning.json"' not in body)
    guarded(fails, "it reads the pinned fixtures/sprint97/morning-2026-10-20.json instead",
            lambda: "morning-2026-10-20.json" in body)
    fx = load("fixtures", "sprint97", "morning-2026-10-20.json")
    guarded(fails, "the fixture is the October 20 read (date, slot)", lambda: fx["date_et"] == "2026-10-20" and fx["slot"] == "morning")


def case_4_feed_ai(fails):
    print("4. the feed scan: an AI word in desk prose fails, a source link's address is not desk prose (sprint 9.7)")
    import sprint97_test as s97
    url = "https://example.com/2026/10/25/woman-loses-money-after-ai-impersonator-poses-as-a-singer/"
    news = {"data": {"items": [{"line": "A woman lost money to a scam.", "links": [{"outlet": "Example", "url": url}]}]}}
    guarded(fails, "s97.feed_prose exists and a feed with an AI word only inside a link address has none",
            lambda: not s97.AI.search(s97.feed_prose(news)))
    guarded(fails, "an AI word in a line of the same feed is still found",
            lambda: s97.AI.search(s97.feed_prose({"data": {"items": [{"line": "An AI model priced it.", "links": [{"url": url}]}]}})))
    guarded(fails, "an AI word in a feed's title or outlet name is still found",
            lambda: s97.AI.search(s97.feed_prose({"title": "Built by artificial intelligence", "links": []}))
            and s97.AI.search(s97.feed_prose({"links": [{"outlet": "OpenAI Blog", "url": url}]})))
    guarded(fails, "a dash in a link address is still a dash (the dash scan reads the whole feed)",
            lambda: s97.DASH.search(json.dumps({"url": "https://x.com/a" + chr(0x2014) + "b"}, ensure_ascii=False)))


def case_5_record_store(fails):
    print("5. the canary's fixture build reads no stored verdict record (sprint 9.8)")
    import verdict_record
    import verify_pipeline as vp
    real = verdict_record.STORE
    tmp = tempfile.mkdtemp(prefix="s99h-")
    old = None
    try:
        with quiet():
            old = vp._verdict_fixture_dir(tmp)
        redirected = verdict_record.STORE
        guarded(fails, "while the fixture verdict dir stands, verdict_record.STORE is a scratch dir under the same root",
                lambda: redirected != os.path.join(HERE, "site", "data", "verdict", "record") and redirected.startswith(tmp))
        guarded(fails, "the real store holds a verdict the fixture dir does not (the premise: the October 25 Bitcoin entry)",
                lambda: os.path.exists(os.path.join(HERE, "site", "data", "verdict", "record", "2026-10-25-evening-bitcoin-231759.json")))
        import verdict as vd
        ents = verdict_record.view(dt.datetime(2026, 10, 26, 20, 0, tzinfo=UTC), vdir=vd.DIR, mdir=tmp + "/none", wdir=tmp + "/none")
        guarded(fails, "the record view built meanwhile lists no October 25 verdict",
                lambda: not any(r["date_et"] == "2026-10-25" for r in ents["rows"]))
    finally:
        vp._verdict_restore(old)
    guarded(fails, "_verdict_restore puts the real store back", lambda: verdict_record.STORE == real)


SEVEN = (
    "An AI-generated summary of three reports on Luxor's raise.",
    "Crypto Cronkite, the desk's AI editor, ranked this item first.",
    "AI summary: Luxor raised $16 million.",
    "Summary by AI of reports on Luxor's raise.",
    "Claude wrote this line from three reports.",
    "Our editor is an AI model; Luxor raised $16 million.",
    "Haiku 5.5 summarized three reports: Luxor raised $16 million.",
)
LUXOR_LINKS = [{"outlet": "Decrypt", "url": "https://decrypt.co/381847/bitcoin-mining-firm-luxor-raises-16-million-ai-compute"},
               {"outlet": "The Block", "url": "https://www.theblock.co/news/deals/2026-10-27-bitcoin-mining-ai-luxor-technology-funding-431858"}]
LUXOR_LINE = "Bitcoin miner Luxor raised $16 million from CMT Digital, Canaan, and MicroBT to expand AI compute trading, hardware, and derivatives."


def case_6_sourced_event_text(fails):
    print("6. the feed AI-word scan holds the desk's wording and any disclosure; an AI word its own sources carry is a reported subject (hotfix 9.9h2, J-20)")
    import api_feeds
    import sprint97_test as s97
    wpath = os.path.join(HERE, "site", "data", "why", "2026-10-27-evening.json")
    stored = json.load(open(wpath, encoding="utf-8"))
    luxor = [c for c in stored["candidates"] if c.get("kind") == "wire" and "AI compute" in (c.get("line") or "")]
    guarded(fails, "the premise: the stored October 27 evening evidence carries the Luxor wire line, and its own source titles carry 'AI compute'",
            lambda: bool(luxor) and any("ai compute" in t.lower() for t in luxor[0]["titles"]))
    now = dt.datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    feeds = api_feeds.why_feeds(now)
    guarded(fails, "today's why feeds, built from the stored records, pass the AI-word scan",
            lambda: all(not s97.AI.search(s97.feed_prose(f)) for f in feeds.values()))
    wire = json.load(open(os.path.join(HERE, "site", "data", "wire.json"), encoding="utf-8"))
    news = api_feeds.news_feed(wire, now)
    guarded(fails, "the news feed built from the stored wire passes the AI-word scan",
            lambda: not s97.AI.search(s97.feed_prose(news)))
    def cand(kind, line, links=None):
        return {"data": {"evidence": {"candidates": [{"id": "x", "kind": kind, "line": line, "links": links if links is not None else LUXOR_LINKS}]}}}
    def nitem(line, links=None):
        return {"name": "news", "data": {"items": [{"rank": 1, "id": "c1", "line": line, "links": links if links is not None else LUXOR_LINKS}]}}
    for label, mk in (("a wire candidate line", lambda t: cand("wire", t)), ("a news item line", nitem)):
        guarded(fails, f"plant: the Luxor line, whose AI subject its own sources carry, passes in {label}",
                lambda mk=mk: not s97.AI.search(s97.feed_prose(mk(LUXOR_LINE))))
        for t in SEVEN:
            guarded(fails, f"plant: {t!r} fails in {label}",
                    lambda mk=mk, t=t: s97.AI.search(s97.feed_prose(mk(t))))
        guarded(fails, f"plant: a line with the sources' AI subject AND a disclosure fails in {label}",
                lambda mk=mk: s97.AI.search(s97.feed_prose(mk("Luxor raised $16 million to expand AI compute, in an AI-generated summary."))))
        guarded(fails, f"plant: an AI word the sources lack fails in {label} even beside a carried one",
                lambda mk=mk: s97.AI.search(s97.feed_prose(mk("Luxor raised money for AI compute and an AI editor picked it."))))
    guarded(fails, "plant: an AI word with no links to carry it fails in a news item",
            lambda: s97.AI.search(s97.feed_prose(nitem("Miner raised money to expand AI compute.", links=[]))))
    guarded(fails, "plant: an AI word inside a press line (the outlet's own title) passes",
            lambda: not s97.AI.search(s97.feed_prose(cand("press", "OpenAI cut a crypto fee (CoinDesk)"))))
    guarded(fails, "plant: an AI word in a release candidate's line (the desk's template) still fails",
            lambda: s97.AI.search(s97.feed_prose(cand("release", "AI Jobs Report (Bureau of Labor Statistics)"))))
    guarded(fails, "plant: an AI disclosure in a verdict card sentence still fails",
            lambda: s97.AI.search(s97.feed_prose({"data": {"coins": {"BTC": {"card_text": ["Graded by an AI model from the evidence."]}}}})))
    guarded(fails, "plant: an AI disclosure in a Brief line still fails",
            lambda: s97.AI.search(s97.feed_prose({"data": {"items": [{"line": "This Brief was drafted by Claude."}]}})))
    guarded(fails, "plant: an AI word in a feed that is not the news feed's items (a Brief item line) still fails",
            lambda: s97.AI.search(s97.feed_prose({"name": "brief/latest", "data": {"items": [{"line": "An AI model priced it."}]}})))
    guarded(fails, "plant: a candidate's outlet name is still read",
            lambda: s97.AI.search(s97.feed_prose(cand("wire", "Miner raised money.", [{"outlet": "AI Daily", "url": "https://x.com/a"}]))))
    guarded(fails, "the dash scan is unchanged: a dash inside a wire line is still a dash",
            lambda: s97.DASH.search(json.dumps(cand("wire", "a" + chr(0x2014) + "b"), ensure_ascii=False)))


def unit():
    fails = []
    for fn in (case_1_names, case_2_pinned_morning, case_4_feed_ai, case_5_record_store, case_6_sourced_event_text):
        try:
            fn(fails)
        except Exception as e:                               # noqa: BLE001
            msg = f"{fn.__name__} could not run [{type(e).__name__}: {str(e)[:120]}]"
            print("  FAIL " + msg)
            fails.append(msg)
    return fails


def main():
    fails = unit()
    print(f"\nSPRINT 9.9h: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
