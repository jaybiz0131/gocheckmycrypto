#!/usr/bin/env python3
"""Program 8, Sprint 8.1: the daily answer and the 7.x cleanup, each case with a fixture.

  python3 scripts/sprint81_test.py            # unit cases, plus the built tree when site/publish exists
  python3 scripts/sprint81_test.py --site DIR # also the static and browser cases on a built tree

unit()        the direction word per sign (a down, an up and a flat fixture day), the dated page's
              freeze, the gate on every sentence, no "because" in the page's own voice, the
              structured data, the sitemap's lastmod, the home link and cadence line, the morning
              wire stamp, the compressed small prices.
static(site)  the same on the tree a build wrote.
browser(site) no element wider than its column at 1440 and 375 on /flows, /today/, and the home.
"""
import copy
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FIX = os.path.join(HERE, "fixtures", "home")


def _j(n):
    return json.load(open(os.path.join(FIX, n), encoding="utf-8"))


def _utc(y, mo, d, h, mi):
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc)


def _snap(btc_chg, btc_price=81500.0, utc="2026-10-14T12:17:00Z"):
    """The fixture snapshot, stamped as the run that read it (default: the 8:17 AM morning run)."""
    s = copy.deepcopy(_j("snapshot_from_2026-10-06_files.json"))
    s["stamp_utc"] = utc
    s["stamp_et"] = {"2026-10-14T12:17:00Z": "8:17 AM ET on Oct 14", "2026-10-14T23:12:00Z": "7:12 PM ET on Oct 14",
                     "2026-10-14T23:15:00Z": "7:15 PM ET on Oct 14"}.get(utc, utc)
    c = s["fields"]["coins"]["value"]["BTC"]
    c["chg_24h_pct"], c["price"] = btc_chg, btc_price
    return s


def _wire(day="2026-10-14"):
    return {"ranked_et": "7:14 PM ET on Oct 13", "refreshed_et": "8:18 AM ET on Oct 14",
            "items": [
                {"id": "w1", "line": "Regulators in Seoul blocked 27 exchange websites.",
                 "reported_utc": f"{day}T13:03:00Z", "source_count": 2, "primary": False,
                 "links": [{"outlet": "Decrypt", "url": "https://decrypt.co/a"},
                           {"outlet": "The Block", "url": "https://theblock.co/b"}]},
                {"id": "w2", "line": "A hot CPI print sent Bitcoin lower because rate-hike odds climbed.",
                 "reported_utc": f"{day}T12:33:00Z", "source_count": 1, "primary": False,
                 "links": [{"outlet": "CoinDesk", "url": "https://coindesk.com/c"}]},
                {"id": "w3", "line": "An item from another day.", "reported_utc": "2026-10-10T13:00:00Z",
                 "source_count": 1, "links": [{"outlet": "X", "url": "https://x.com/y"}]}]}


MORNING = {"date_et": "2026-10-14", "slot": "morning", "published_utc": "2026-10-14T12:18:55Z",
           "published_et": "8:18 AM ET on Oct 14", "headline": "The wire opens on Seoul",
           "sentences": ["The wire's top line is Seoul blocking exchange sites.",
                         "The Board shows funding calm."], "line": "x"}


class Counting:
    """A gate that passes everything and counts the sentences it was asked about."""
    def __init__(self):
        self.seen = []

    def text(self, text, surface, **kw):
        self.seen.append((surface, text))
        return text

    def save(self):
        pass


def check(cond, fails, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def _compose(snap, chg=None, now=None, wire=None, gate=None, ed=None, morning=MORNING):
    import today
    import twins_gate
    now = now or _utc(2026, 10, 14, 12, 30)
    gate = gate or twins_gate.Gate(snap, quiet=True)
    pulse = _j("pulse_2026-10-06T2311Z.json")
    return today.compose(snap, pulse, wire if wire is not None else _wire(), ed, morning, now, gate), gate, pulse


def unit():
    fails = []
    try:
        import home, today, twins_gate
        import site_build as sb
        print("A. the direction word follows the sign: a down, an up and a flat fixture day")
        for chg, want, title in ((-2.03, "down", "Why is crypto down today? Wednesday, October 14, 2026"),
                                 (1.8, "up", "Why is crypto up today? Wednesday, October 14, 2026"),
                                 (-0.2, "flat", "Crypto today: flat. Wednesday, October 14, 2026")):
            rec, _g, _p = _compose(_snap(chg))
            check(rec and rec["direction"] == want and rec["title"] == title and rec["h1"] == title, fails,
                  f"BTC {chg:+.2f}% reads {want}: {rec and rec['h1']!r}")
            if rec:
                txt = " ".join(rec["answer"])
                check((f"{abs(chg):.2f}%" in txt) and (want == "flat" or f" {want} " in txt), fails,
                      f"the answer says {want} with {abs(chg):.2f}%: {txt[:90]!r}")
        check(today.direction(0.5) == "flat" and today.direction(-0.5) == "flat"
              and today.direction(0.51) == "up" and today.direction(-0.51) == "down", fails,
              "plus or minus 0.5 is flat, 0.51 is not")
        check(today.direction(None) is None and _compose(_snap(None))[0] is None, fails,
              "no Bitcoin reading, no direction and no record")
        check(_compose(_snap(1.0), now=_utc(2026, 10, 14, 6, 0), morning=None)[0] is None, fails,
              "no morning read and no Edition today, no record")

    except Exception as e:
        check(False, fails, "section A crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home, today, twins_gate
        import site_build as sb
        print("B. the dated page freezes at the evening build")
        ed = {"slug": "2026-10-14-evening-brief", "date": "2026-10-14", "published_utc": "2026-10-14T23:16:00Z",
              "bottom_line": "The desk published no verified stories today."}
        eve_now = _utc(2026, 10, 14, 23, 30)
        eve, _g, pulse = _compose(_snap(-2.03, 81500.0, "2026-10-14T23:15:00Z"), now=eve_now, ed=ed)
        check(eve and eve["slot"] == "evening" and "Evening Edition, 7:16 PM ET" == eve["stamp_label"], fails,
              f"the evening record is the Edition's: {eve and eve['stamp_label']!r}")
        mor, _g, _p = _compose(_snap(-1.2, 82000.0))
        import twins_gate
        later = _snap(3.4, 90210.0)                      # the next morning's numbers, a different direction
        gate = twins_gate.Gate(later, quiet=True)
        nxt = _utc(2026, 10, 15, 12, 30)
        m2 = dict(MORNING, date_et="2026-10-15", published_utc="2026-10-15T12:18:00Z")
        a = today.build_pages(_snap(0), pulse, _wire(), None, None, nxt, gate, stored=[mor, eve])
        b = today.build_pages(later, pulse, _wire("2026-10-15"), None, m2, nxt, gate, stored=[mor, eve])
        da = {p: h for _f, h, p, _m in a}
        db = {p: h for _f, h, p, _m in b}
        check(da.get("/today/2026-10-14.html") and da["/today/2026-10-14.html"] == db["/today/2026-10-14.html"], fails,
              "the 14th's dated page is byte for byte the same after the 15th's morning build")
        check("$81,500" in db["/today/2026-10-14.html"] and "$82,000" not in db["/today/2026-10-14.html"], fails,
              "the dated page holds the evening record, not the morning's")
        check("/today/2026-10-15.html" in db and "$90,210" in db["/today/"] and "up today" in db["/today/"], fails,
              "the living page is the newest record (the 15th, up) and the 15th has its own dated page")
        only_morning = today.build_pages(_snap(0), pulse, _wire(), None, None, eve_now, gate, stored=[mor])
        check(any(p == "/today/2026-10-14.html" and "$82,000" in h for _f, h, p, _m in only_morning), fails,
              "before the evening build the dated page shows the morning record")

    except Exception as e:
        check(False, fails, "section B crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home, today, twins_gate
        import site_build as sb
        print("C. the twins gate runs on every sentence the page writes")
        cg = Counting()
        rec, _g, _p = _compose(_snap(-2.03), gate=cg)
        seen = [t for _s, t in cg.seen]
        check(all(s in seen for s in rec["answer"]) and len(rec["answer"]) >= 3, fails,
              f"each of the {len(rec['answer'])} answer sentences went through the gate")
        check(all(w["line"] in seen for w in rec["reported"]) and len(rec["reported"]) == 2, fails,
              "each wire line shown went through the gate, and the other day's item is not shown")
        real = twins_gate.Gate(_snap(-2.03), quiet=True)
        wrong = _wire()
        wrong["items"][0]["line"] = "Bitcoin ETF flows were negative while the snapshot reads an inflow."
        rec2, g2, _p = _compose(_snap(-2.03), gate=real, wire=wrong)
        check(all("negative while" not in w["line"] for w in rec2["reported"]) and g2.drops, fails,
              "a wire line the real gate drops is dropped from the page and logged")

    except Exception as e:
        check(False, fails, "section C crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home, today, twins_gate
        import site_build as sb
        print("D. no 'because' without a source")
        rec, _g, pulse = _compose(_snap(-2.03))
        page = today.body_html(rec, ["2026-10-13"])
        own = re.sub(r'<ol class="td-reps">.*?</ol>', "", page, flags=re.S)
        check(not today.CAUSAL.search(re.sub(r"<[^>]+>", " ", own)), fails,
              "outside the reported items the page never says because, due to or driven by")
        check("because rate-hike odds" in page and "CoinDesk" in page, fails,
              "a wire item may carry its source's cause, with its source named beside it")
        lifted = today.liftable("Bitcoin fell 2.1% on the day because rate-hike odds climbed.", "down",
                                twins_gate.Gate(_snap(-2.03), quiet=True))
        check(lifted is None, fails, "a read that says because is not lifted as the answer")
        ok = today.liftable("Bitcoin fell 2.0% on the day, to $81,500.", "down",
                            twins_gate.Gate(_snap(-2.03, 81500.0), quiet=True))
        check(ok == ["Bitcoin fell 2.0% on the day, to $81,500."], fails,
              "a read that states the move and passes the gate is lifted as it stands")
        check(today.liftable("Bitcoin rose 2.0% on the day.", "down", twins_gate.Gate(_snap(-2.03), quiet=True)) is None, fails,
              "a read that states the wrong direction is not lifted")
        check(not re.search(r"[–—]", page), fails, "no dash of either kind on the page")

    except Exception as e:
        check(False, fails, "section D crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home, today, twins_gate
        import site_build as sb
        print("E. structured data, stamps, archive")
        html, path, mod = today.render(rec, ["2026-10-13", "2026-10-12"], dated=False)
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        ld = json.loads(m.group(1)) if m else {}
        node = (ld.get("@graph") or [{}])[0]
        check(node.get("@type") == "NewsArticle" and node.get("mainEntityOfPage") == "https://gocheckmycrypto.com/today/"
              and node.get("datePublished", "").endswith("-04:00") and node.get("dateModified", "").endswith("-04:00")
              and node.get("publisher", {}).get("name") and node.get("headline") == rec["h1"], fails,
              f"NewsArticle parses with ET offsets, canonical and publisher: {json.dumps(node)[:160]}")
        check('<link rel="canonical" href="https://gocheckmycrypto.com/today/">' in html, fails, "/today/ is its own canonical")
        html2, path2, _m = today.render(rec, [], dated=True)
        check('rel="canonical" href="https://gocheckmycrypto.com/today/2026-10-14"' in html2 and path2 == "/today/2026-10-14.html", fails,
              "the dated page's canonical is /today/YYYY-MM-DD")
        check("Morning read, 8:18 AM ET" in html and "Next update: Evening Edition, tonight at 7:08 PM ET" in html, fails,
              "the stamp names the slot and its time, and the next update")
        check(html.count('href="/today/2026-1') == 2, fails, "the archive links the dated pages")
        check("Why is crypto down today? Wednesday, October 14, 2026" in html and "<title>Why is crypto down today?" in html, fails,
              "the title and headline carry the direction and the full date")
        check('class="chg down"' in html and 'class="chg up"' in html, fails,
              "each change is colored by its own sign (gainers up, Bitcoin down)")
        check(not re.search(r"<h2[^>]*>[^<]*\bwhy\b", html, re.I), fails, "no section heading says why")

    except Exception as e:
        check(False, fails, "section E crashed: " + type(e).__name__ + ": " + str(e)[:140])
    print("E2. fix 1: one honest stamp line; fix 2: the next update off the clock; fix 3: the archive")
    try:
        import home, today
        night = _utc(2026, 10, 14, 23, 50)                   # 7:50 PM ET, the Edition (7:08) failed
        old_ed = {"slug": "2026-10-13-evening-brief", "date": "2026-10-13", "published_utc": "2026-10-13T23:15:58Z",
                  "bottom_line": "x"}
        rec, _g, _p = _compose(_snap(-2.03, 81513.0, "2026-10-14T23:12:00Z"), now=night, ed=old_ed)
        want = "Numbers as of 7:12 PM ET \u00b7 tonight's Edition did not publish; text from the 8:18 AM read"
        check(rec and rec["stamp_label"] == want, fails, f"mismatched runs say so plainly: {rec and rec['stamp_label']!r}")
        check(rec and rec["next"] == "Next update: Morning read, tomorrow at 8:15 AM ET", fails,
              f"7:50 PM with the Edition failed: {rec and rec['next']!r}")
        card = home.next_brief(None, night)
        check(card == "Next Brief tomorrow at 8:15 AM ET" and rec["next"].endswith(card.split("Next Brief ")[1]), fails,
              "the daily answer and the home card name the same next slot")
        noon = _compose(_snap(-1.0, 82000.0, "2026-10-14T23:12:00Z"), now=_utc(2026, 10, 14, 16, 0))[0]
        check(noon and noon["stamp_label"] == "Numbers as of 7:12 PM ET \u00b7 text from the 8:18 AM read"
              and noon["next"] == "Next update: Evening Edition, tonight at 7:08 PM ET", fails,
              f"before the Edition slot the reason clause is absent and the next slot is tonight's: {noon and noon['stamp_label']!r}")
        same, _g, _p = _compose(_snap(-2.03), now=_utc(2026, 10, 14, 12, 30))
        check(same["stamp_label"] == "Morning read, 8:18 AM ET", fails, "matching runs keep 'Morning read, 8:18 AM ET'")
        ed2 = {"slug": "2026-10-14-evening-brief", "date": "2026-10-14", "published_utc": "2026-10-14T23:14:00Z",
               "bottom_line": "The desk published no verified stories today."}
        ev, _g, _p = _compose(_snap(-2.03, 81500.0, "2026-10-14T23:15:00Z"), now=_utc(2026, 10, 14, 23, 30), ed=ed2)
        check(ev["stamp_label"] == "Evening Edition, 7:14 PM ET" and ev["next"] == "Next update: Morning read, tomorrow at 8:15 AM ET", fails,
              f"matching evening runs keep 'Evening Edition, 7:14 PM ET': {ev['stamp_label']!r}")
        mor, _g, pulse = _compose(_snap(-2.03))
        prior = dict(mor, date_et="2026-10-13", title="x", h1="x")
        built = today.build_pages(_snap(-2.03), pulse, _wire(), None, MORNING, _utc(2026, 10, 14, 12, 30),
                                  twins_gate.Gate(_snap(-2.03), quiet=True), stored=[prior])
        living = next(h for _f, h, p, _m in built if p == "/today/")
        check('href="/today/2026-10-13"' in living and 'href="/today/2026-10-14"' not in living, fails,
              "the living page lists the earlier day and not today's own dated page")
        alone = today.build_pages(_snap(-2.03), pulse, _wire(), None, MORNING, _utc(2026, 10, 14, 12, 30),
                                  twins_gate.Gate(_snap(-2.03), quiet=True), stored=[])
        check("Earlier days" not in next(h for _f, h, p, _m in alone if p == "/today/"), fails,
              "with no earlier day there is no archive block")
    except Exception as e:
        check(False, fails, "section E2 crashed: " + type(e).__name__ + ": " + str(e)[:140])

    print("E3. a fallback morning: an honest stamp, never a morning read that did not run")
    try:
        import today
        last_ed = {"slug": "2026-10-14-evening-brief", "date": "2026-10-14", "published_utc": "2026-10-14T23:14:00Z",
                   "bottom_line": "x"}
        stale = dict(MORNING, date_et="2026-10-14")             # yesterday's read is on disk; today's fell back
        snap15 = _snap(-1.2, 82000.0, "2026-10-15T12:17:00Z")
        for hour, minute, why in ((12, 30, "this morning's read did not publish"),
                                  (11, 0, "this morning's read has not published yet")):
            rec, _g, _p = _compose(snap15, now=_utc(2026, 10, 15, hour, minute), ed=last_ed, morning=stale)
            want = f"Numbers as of 8:17 AM ET \u00b7 {why}; text from last night's 7:14 PM Edition"
            check(rec and rec["stamp_label"] == want and "Morning read" not in rec["stamp_label"], fails,
                  f"{hour - 4}:{minute:02d} AM: {rec and rec['stamp_label']!r}")
        rec, _g, _p = _compose(snap15, now=_utc(2026, 10, 15, 12, 30), ed=last_ed, morning=stale)
        check(rec["fallback"] and rec["answer_by"] == "template" and rec["date_et"] == "2026-10-15"
              and rec["published_utc"] == "2026-10-15T12:30:00Z" and rec["next"] == "Next update: Evening Edition, tonight at 7:08 PM ET", fails,
              "the fallback page is the template answer, dated today, modified now, next slot tonight")
        html, _p2, mod = today.render(rec, [], dated=False)
        check("Morning read, " not in html and "Why is crypto down today? Thursday, October 15, 2026" in html and mod == "2026-10-15T12:30:00Z", fails,
              "the rendered page never says 'Morning read,' and carries the day's own title and lastmod")
        check(_compose(snap15, now=_utc(2026, 10, 15, 12, 30), ed=None, morning=stale)[0] is None, fails,
              "no Edition on the desk at all: no page")
    except Exception as e:
        check(False, fails, "section E3 crashed: " + type(e).__name__ + ": " + str(e)[:140])

    try:
        import home
        import site_build as sb
        print("F. the home page: cadence line and the /today/ link")
        check(sb.NEWS_CADENCE_LINE == "The Brief, every morning and evening.", fails,
              "the cadence line is Jack's, exactly")
        snap = _j("snapshot_from_2026-10-06_files.json")
        band = home.narrative_band(_j("narrative.json"), snap, None, _utc(2026, 10, 14, 12, 30))
        check('<a href="/today/">Why crypto moved today &rarr;</a>' in band, fails, "the Brief card links /today/")
        src = open(os.path.join(HERE, "site_build.py"), encoding="utf-8").read()
        check("one checked, \"\n" not in src and "the Brief every evening" not in src, fails, "the old cadence line is gone from the build")

    except Exception as e:
        check(False, fails, "section F crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home
        import site_build as sb
        print("G. Item 1: the morning wire is stamped with the morning's own time")
        w = home.wire_top(_wire(), "", _utc(2026, 10, 14, 12, 30))
        check("Re-ranked 8:18 AM ET on Oct 14" in w and "7:14 PM ET on Oct 13" not in w, fails,
              "Moving the market carries the 8:18 AM stamp, not Monday night's")
        ev = home.wire_top(dict(_wire(), refreshed_et="7:14 PM ET on Oct 13"), "", _utc(2026, 10, 14, 23, 30))
        check("Ranked 7:14 PM ET on Oct 13" in ev and "Re-ranked" not in ev, fails,
              "an unrefreshed wire keeps its Edition stamp")

    except Exception as e:
        check(False, fails, "section G crashed: " + type(e).__name__ + ": " + str(e)[:140])
    try:
        import home
        import site_build as sb
        print("H. Item 2: small prices print compressed, the label reads the full number")
        for price, shown, label in ((3.682e-07, "$0.0₆3682", "0.0000003682 dollars"),
                                    (9e-05, "$0.0₄9000", "0.00009000 dollars"),
                                    (5.08e-06, "$0.0₅5080", "0.000005080 dollars")):
            check(sb._price_fmt(price) == shown and sb._price_label(price) == label, fails,
                  f"{price!r} prints {shown!r}, label {label!r}")
        check(sb._price_fmt(1e-4) == "$0.0001000" and sb._price_label(1e-4) == "" and sb._price_fmt(9.9996e-05) == "$0.0001000", fails,
              "$0.0001 and a price that rounds up to it print in full")
        row = "".join(sb._top100_rows([{"symbol": "BTT", "name": "BitTorrent", "price": 3.682e-07, "chg_24h_pct": -1.0,
                                        "rank": 90, "spark7d": [1, 2, 3, 2, 1, 2, 1], "mcap_usd": 1e8}]))
        check('aria-label="0.0000003682 dollars"' in row and "$0.0₆3682" in row and "pn-xlong" not in row, fails,
              "the Top 100 row carries the compressed price and the accessible label")
        css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read()
        check("pn-xlong" not in css and sb._price_class(sb._price_fmt(3.682e-07)) == "", fails, "the 10 px tier is gone")
    except Exception as e:
        check(False, fails, "section H crashed: " + type(e).__name__ + ": " + str(e)[:140])
    return fails


def static(site):
    fails = []
    print("S. the built tree")
    idx = os.path.join(site, "today", "index.html")
    check(os.path.exists(idx), fails, "the build wrote /today/")
    if os.path.exists(idx):
        h = open(idx, encoding="utf-8").read()
        check(re.search(r"<title>(Why is crypto (down|up) today\?|Crypto today: flat\.) \w+, \w+ \d+, 20\d\d", h), fails,
              "the title carries the direction and the date")
        m = re.search(r'application/ld\+json">(.*?)</script>', h, re.S)
        check(m and json.loads(m.group(1))["@graph"][0]["@type"] == "NewsArticle", fails, "its structured data parses")
        dated = [f for f in os.listdir(os.path.join(site, "today")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f)]
        check(bool(dated), fails, "a dated page was written")
        sm = open(os.path.join(site, "sitemap-priority.xml"), encoding="utf-8").read()
        check(re.search(r"<loc>https://gocheckmycrypto.com/today/</loc><lastmod>20\d\d-", sm), fails,
              "the sitemap carries /today/ with its lastmod")
        sa = open(os.path.join(site, "sitemap-archive.xml"), encoding="utf-8").read()
        check(all(f"/today/{f[:-5]}</loc><lastmod>" in sa for f in dated), fails, "and each dated page with its own")
    ih = open(os.path.join(site, "index.html"), encoding="utf-8").read()
    check("The Brief, every morning and evening." in ih and 'href="/today/"' in ih, fails,
          "the home carries the new cadence line and the /today/ link")
    return fails


def browser(site):
    node = shutil.which("node")
    mod = os.environ.get("PLAYWRIGHT_MODULE", "/opt/node-tools/node_modules/playwright")
    if not node or not os.path.isdir(mod):
        print("sprint 8.1: browser checks SKIPPED (node or playwright not found)")
        return []
    fails = []
    env = dict(os.environ, PLAYWRIGHT_MODULE=mod)
    pages = ["/flows.html", "/today/", "/"]
    for pg in pages:
        r = subprocess.run([node, os.path.join(HERE, "scripts", "column_fit.mjs"), site, pg],
                           capture_output=True, text=True, env=env, timeout=300)
        check(r.returncode == 0, fails, f"no element wider than its column and no table text under 12 px at 1440 and 375 on {pg}: "
                                         f"{(r.stdout or r.stderr).strip()[-240:] if r.returncode else 'ok'}")
    return fails


def main():
    fails = unit()
    site = os.path.join(HERE, "site", "publish")
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    if os.path.isdir(site) and "--unit" not in sys.argv:
        fails += static(site)
        fails += browser(site)
    print("\nSPRINT 8.1:", "FAIL" if fails else "PASS", f"({len(fails)} failing)" if fails else "")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
