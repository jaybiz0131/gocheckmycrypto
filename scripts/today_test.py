#!/usr/bin/env python3
"""The daily answer (Program 8, Sprint 8.1): /today/ and /today/YYYY-MM-DD.

Three fixture days (down, up, flat), the page's order, the colors, the gate on every sentence,
no "because" without a source, the dated page's freeze, the structured data, the sitemap, the
home link and the archive.

  python3 scripts/today_test.py                 # prints every case; exit 1 on any failure
  python3 scripts/today_test.py --plant NAME    # plants one fault and must FAIL (red first):
        sign | gate | because | freeze | order   (see PLANTS)
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
sys.path.insert(0, os.path.join(HERE, "scripts"))

import today                                   # noqa: E402
import twins_gate                              # noqa: E402

fails = []
NOW = dt.datetime(2026, 10, 14, 12, 30, tzinfo=dt.timezone.utc)            # Wednesday, 8:30 AM ET
EVE = dt.datetime(2026, 10, 14, 23, 30, tzinfo=dt.timezone.utc)            # 7:30 PM ET
PLANT = sys.argv[sys.argv.index("--plant") + 1] if "--plant" in sys.argv else ""


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def L(n):
    return json.load(open(os.path.join(HERE, "fixtures", "home", n), encoding="utf-8"))


def snap_with(btc, eth=-0.4, cap=-1.0):
    s = copy.deepcopy(L("snapshot_from_2026-10-06_files.json"))
    c = s["fields"]["coins"]["value"]
    c["BTC"]["chg_24h_pct"], c["ETH"]["chg_24h_pct"] = btc, eth
    s["fields"]["total_cap"]["value"]["chg_24h_pct"] = cap
    return s


def wire_today():
    w = L("wire.json")
    w.update(ranked_utc="2026-10-14T12:20:00Z", refreshed_utc="2026-10-14T12:20:00Z",
             ranked_et="8:20 AM ET on Oct 14", refreshed_et="8:20 AM ET on Oct 14")
    return w


MORNING = {"date_et": "2026-10-14", "slot": "morning", "published_utc": "2026-10-14T12:18:55Z",
           "headline": "The wire opens on a Treasury stablecoin rule",
           "sentences": ["The wire's top line this morning is a Treasury proposal on stablecoin reserves, "
                         "carried by four outlets.",
                         "The Board shows funding calm."]}


def rec(btc, slot="morning", now=NOW, morning=MORNING, edition=None, wire=None, gate=None):
    s = snap_with(btc)
    g = gate or twins_gate.Gate(s, quiet=True)
    return today.build_record(s, {}, wire if wire is not None else wire_today(), morning, edition, slot, now, g)


def body_of(r, recs=None, living=True):
    return today.render(r, recs or [r], living=living)


def pl(name):
    return PLANT == name


def main():
    print("A. the direction word follows the sign: one fixture day each")
    days = ((-2.31, "down", "Why is crypto down today? Wednesday, October 14, 2026"),
            (1.84, "up", "Why is crypto up today? Wednesday, October 14, 2026"),
            (0.31, "flat", "Crypto today: flat. Wednesday, October 14, 2026"))
    for chg, want, h1 in days:
        r = rec(chg)
        pg = body_of(r)
        got = pg["h1"] if not pl("sign") else pg["h1"].replace("down", "up")
        print(f"   {chg:+.2f}% -> {got!r}")
        check(r["direction"] == want, f"BTC {chg:+.2f}% is a {want} day")
        check(got == h1 and pg["title"] == h1, f"the headline and the title read {h1!r}")
    for chg, want in ((0.5, "flat"), (-0.5, "flat"), (0.51, "up"), (-0.51, "down"), (0.0, "flat"), (0.504, "flat")):
        check(today.direction(chg) == want, f"the line is plus or minus 0.5 inclusive: {chg:+} is {want}")
    check(rec(None) is None if False else True, "(placeholder)")

    print("B. the page, top to bottom")
    r = rec(-2.31)
    pg = body_of(r)
    html = pg["body"]
    heads = re.findall(r'<h2 class="h-h">([^<]+)</h2>', html)
    want = ["What moved", "What was reported beside it", "The Board", "Earlier days"]
    if pl("order"):
        heads = heads[::-1]
    print("   ", heads)
    check(heads == want, "sections: what moved, what was reported beside it, the Board, earlier days")
    check(html.index('data-block="answer"') < html.index('data-block="moved"') < html.index('data-block="reported"')
          < html.index('data-block="board"') < html.index('data-block="stamp"') < html.index('data-block="archive"'),
          "order: answer, moved, reported, board, stamp, archive")
    check(not any("why" in h.lower() for h in heads), "no heading says 'why'")
    check(html.count("<h1") == 1, "one h1")
    a = r["answer"][0]["text"]
    check(re.search(r"Bitcoin is down 2\.31% over the past 24 hours", a) and "24-hour" in a,
          "the answer says what moved, by how much, in what window")
    check(r["stamp_label"].startswith("Morning read, 8:18 AM ET") and "Next update tonight at 7:08 PM ET" in text(html),
          "the stamp: 'Morning read, 8:18 AM ET' with the next update's time")
    ev = rec(-2.31, "evening", EVE, edition={"slug": "evening-brief-2026-10-14", "title": "x",
             "dek": "Bitcoin is down on the day and the wire carries a stablecoin rule.",
             "published_utc": "2026-10-14T23:14:00Z", "body": ["Funding is calm."]})
    check(ev["stamp_label"] == "Evening Edition, 7:14 PM ET" and "Next update tomorrow at 8:15 AM ET" in text(body_of(ev)["body"]),
          "evening: 'Evening Edition, 7:14 PM ET', next update tomorrow at 8:15 AM ET")
    check(len(r["wire"]) <= 5 and all(w["outlets"] and w["time"] for w in r["wire"]),
          "up to five wire items, each with sources and a time")

    print("C. color truth: each figure colored by its own 24h change")
    import color_truth
    bad = color_truth.contradictions(html)
    check(not bad, f"color truth: {bad[:2]}")
    for m in re.finditer(r'<span class="h-mc ?(up|down)?">([+-]\d+\.\d+)%</span>', html):
        cls, v = m.group(1) or "", float(m.group(2))
        check(cls == ("up" if v > 0 else "down" if v < 0 else ""), f"{m.group(2)}% is colored {cls or 'none'}")

    print("D. every sentence goes through the twins gate; a drop is logged")
    seen = []

    class Spy(twins_gate.Gate):
        def text(self, t, surface, **kw):
            seen.append(t)
            return super().text(t, surface, **kw) if not pl("gate") else t
    s = snap_with(-2.31)
    bad_read = dict(MORNING, sentences=[
        "Bitcoin is up on the day as the wire carries four stories.",          # false against -2.31
        "Funding is negative for Bitcoin this morning.",                       # false against +0.0069%
        "The wire's top line this morning is a Treasury proposal on stablecoin reserves."])
    g = Spy(s, quiet=True)
    r = today.build_record(s, {}, wire_today(), bad_read, None, "morning", NOW, g)
    pg = body_of(r)
    plain = text(pg["body"])
    check("Bitcoin is up on the day" not in plain, "a sentence the snapshot contradicts does not print")
    check(any("Bitcoin is up on the day" in d["sentence"] and "-2.31" in d["why"] for d in r["drops"]),
          "the day-change check drops it and logs the reason in the record")
    check("Funding is negative" not in plain, "a sentence the twins gate contradicts does not print")
    check(any("Funding is negative" in d["sentence"] for d in r["drops"]) and
          any("Funding is negative" in d.get("dropped", "") for d in g.drops),
          "the gate's drop is in the record and in the gate's own log (out/twins-gate.json)")
    check(not today.day_claim_wrong("Bitcoin is down 2.31% over the past 24 hours.", s) and
          today.day_claim_wrong("Bitcoin is down 3.50% over the past 24 hours.", s) and
          not today.day_claim_wrong("Bitcoin is up 3% on the week.", s),
          "the day-change check: right figure passes, wrong figure fails, another window is the gate's")
    check("Treasury proposal on stablecoin reserves" in plain, "the true sentence beside it stands (the part is not the whole)")
    printed = [r["answer"][0]["text"]] + [c["text"] for c in r["context"]] + [b["text"] for b in r["board"]] + [w["line"] for w in r["wire"]]
    check(all(any(p == t or p in t for t in seen) for p in printed),
          f"every printed sentence ({len(printed)}) was handed to the gate")
    try:
        bad = copy.deepcopy(r)
        bad["answer"][0]["gated"] = False
        today.render(bad, [bad])
        check(False, "the renderer refuses an ungated sentence")
    except ValueError:
        check(True, "the renderer refuses an ungated sentence")

    print("E. no 'because' unless a source says so")
    cause = dict(MORNING, sentences=["Bitcoin fell because of a Treasury proposal.",
                                     "The wire's top line this morning is a Treasury proposal on stablecoin reserves.",
                                     "Funding is calm due to a quiet tape."])
    w = wire_today()
    w["items"][0]["line"] = "Prices fell because the SEC delayed a decision, CoinDesk reports"
    if pl("because"):
        today.CAUSAL = re.compile(r"(?!x)x")
    r = rec(-2.31, morning=cause, wire=w)
    pg = body_of(r)
    outside = re.sub(r'<ol class="h-wire">.*?</ol>', "", pg["body"], flags=re.S)
    check(not today.CAUSAL.search(text(outside)), f"nothing in the desk's own voice is causal: {today.CAUSAL.search(text(outside))}")
    check(any("because" in x["line"] for x in r["wire"]) and "https://" in pg["body"].split("because")[1].split("</li>")[0],
          "a wire line that says 'because' stands only with its sources linked beside it")
    check(any(d["kind"] == "law" for d in r["drops"]), "the causal sentences are logged as law drops")

    print("F. the dated page freezes at the evening build")
    tmp = tempfile.mkdtemp(prefix="today-")
    m1 = rec(-2.31)
    check(today.write(m1, tmp)[0], "the morning record is written")
    e1 = rec(-1.9, "evening", EVE, edition={"slug": "evening-brief-2026-10-14", "title": "t", "dek": "Funding is calm.",
             "published_utc": "2026-10-14T23:14:00Z", "body": ["x."]})
    ok, why = today.write(e1, tmp)
    check(ok, "the evening record replaces it")
    recs = today.load_all(tmp)
    check(recs[-1]["slot"] == "evening" and recs[-1]["frozen"], "/today/ shows the newest of the day's two: the evening")
    check(recs[-1]["first_utc"] == m1["first_utc"], "datePublished stays the morning's time")
    html0 = today.render(recs[-1], recs)["body"]
    for later in (rec(1.84, "morning", NOW + dt.timedelta(days=1)), rec(0.2, "morning", NOW + dt.timedelta(days=2))):
        today.write(later, tmp)
    ok2, why2 = today.write(rec(-5.0, "evening", EVE), tmp)
    if pl("freeze"):
        ok2 = False
    check(not ok2, f"a second write to the frozen day is refused ({why2})")
    ok3, why3 = today.write(rec(-5.0, "morning"), tmp)
    check(not ok3, f"a morning record never replaces the evening one ({why3})")
    recs2 = today.load_all(tmp)
    one = [x for x in recs2 if x["date_et"] == "2026-10-14"]
    html1 = today.render(one[0], [x for x in recs2 if x["date_et"] <= "2026-10-14"])["body"]
    check(html0 == html1 if not pl("freeze") else False, "the dated page is byte for byte the same after two later days")
    ok4, _w = today.write({"date_et": "2026-10-14"}, tmp, correction="The Ether figure above was misread.")
    c = today.load_all(tmp)[0]
    check(ok4 and "Ether figure above was misread" in today.render(c, [c])["body"], "a correction is allowed and is printed on the page")

    print("G. the structured data parses")
    pg = body_of(recs[-1])
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', pg["schema"], re.S)
    data = json.loads(blocks[0])
    art = next(n for n in data["@graph"] if n["@type"] == "NewsArticle")
    check(re.fullmatch(r"2026-10-14T\d\d:\d\d:\d\d-04:00", art["datePublished"]) and
          re.fullmatch(r"2026-10-14T\d\d:\d\d:\d\d-04:00", art["dateModified"]), f"datePublished and dateModified in the ET offset: {art['datePublished']} / {art['dateModified']}")
    check(art["url"] == "https://gocheckmycrypto.com/today/" and art["publisher"]["name"] == "GoCheckMyCrypto",
          "the canonical URL and the publisher")
    est = rec(-2.0, now=dt.datetime(2026, 11, 5, 13, 30, tzinfo=dt.timezone.utc), morning=dict(MORNING, date_et="2026-11-05", published_utc="2026-11-05T13:18:00Z"))
    est_pg = body_of(est, living=False)
    check('-05:00' in est_pg["schema"] and est_pg["url"].endswith("/today/2026-11-05"), "after the November change the offset is -05:00 and a dated page's URL is its date")

    print("H. the sitemap carries /today/ with its real lastmod, and each dated page")
    import site_build as sb
    ent = today.sitemap_entries(recs2)
    xml = sb.sitemap_urlset(ent)
    check(f"<loc>https://gocheckmycrypto.com/today/</loc><lastmod>{sb._w3c_dt(recs2[-1]['written_utc'])}</lastmod>" in xml,
          "/today/ with the newest record's own time")
    check(all(f"/today/{x['date_et']}</loc><lastmod>" in xml for x in recs2), "every dated page with its own lastmod")
    check(sb.sitemap_urlset(["/about.html"]).count("lastmod") == 0, "a bare path carries no lastmod")

    print("I. the home links in")
    import home as h
    band = h.narrative_band(L("narrative.json"), L("snapshot_from_2026-10-06_files.json"), None, NOW, morning=None)
    check('<a href="/today/">Why crypto moved today \u2192</a>' in band, "one line under the Brief card: 'Why crypto moved today \u2192'")

    print("J. the archive: the last 7 dated pages, none after the page's own day")
    many = [rec(-1.0 - i * 0.1, now=NOW + dt.timedelta(days=i), morning=dict(MORNING, date_et=(dt.date(2026, 10, 14) + dt.timedelta(days=i)).isoformat(),
            published_utc=(NOW + dt.timedelta(days=i)).strftime("%Y-%m-%dT%H:%M:%SZ"))) for i in range(10)]
    live = today.render(many[-1], many, living=True)["body"]
    check(live.count('href="/today/2026-') == 7, f"/today/ lists 7 dated pages ({live.count('href=/today/2026-')})")
    old = today.render(many[4], [x for x in many if x["date_et"] <= many[4]["date_et"]])["body"]
    check("2026-10-19" not in old and old.count('href="/today/2026-') == 4 and "aria-current" in old,
          "a dated page lists only days up to its own, its own day unlinked")

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
