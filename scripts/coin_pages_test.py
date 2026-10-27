#!/usr/bin/env python3
"""
coin_pages_test.py: Program 7 Sprint 6.4 (13 October 2026), the coin pages and the Top 100.

    python3 scripts/coin_pages_test.py [--site site/publish] [--no-browser]

Three layers, each exit-1 on a failure and each failure named:
  unit     coinpage.py on fixtures: the sparkline's color is its own seven days, the readings
           grid colors each tile by its own change only, the Chart Master card is dated and
           says when it is old, the unlock line is absent without data.
  static   the built tree: every coin page carries the shared chart file once, four tabs,
           the tiles, the cold-storage card; the Top 100 has its search and 100 linked rows.
  browser  scripts/coin_pages_browser.mjs (chart colors per window, the averages on 1M and 1Y
           only, search, the empty case, no sideways scroll at 375). Skipped, out loud, when
           node or playwright is not found.
"""
import datetime
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


def unit():
    import coinpage as cp
    import site_build as sb
    fails = []

    def chk(ok, msg):
        if not ok:
            fails.append(msg)

    falling, rising = [10, 9, 8, 7, 6], [1, 2, 3, 4, 5]
    chk('data-dir="down"' in cp.row_spark(falling) and 'rs-l down' in cp.row_spark(falling), "sparkline: a falling week is not down")
    chk('data-dir="up"' in cp.row_spark(rising), "sparkline: a rising week is not up")
    chk("filter" not in cp.row_spark(rising), "sparkline: glow at row size")
    chk(cp.row_spark([1]) == "", "sparkline: one point drew a line")
    coin = {"symbol": "ZZZ", "name": "Zed", "chg_24h_pct": 4.0, "spark7d": falling, "price": 1.5}
    row = sb._top100_rows([coin])
    chk('rs-l down' in row and 'rs-l up' not in row, "top100 row: up on the day but down on the week must draw down")

    c = {"symbol": "BTC", "name": "Bitcoin", "gecko_id": "bitcoin", "price": 80000.0, "chg_24h_pct": 1.2,
         "chg_7d_pct": -3.4, "chg_30d_pct": 5.0, "mcap_usd": 1.6e12, "volume_24h": 3e10}
    asset = {"symbol": "BTC", "price": 80000.0, "sma50": 78000.0, "sma200": 70000.0, "rsi14": 55.0}
    html = cp.reading_tiles(c, 1, asset, "7:00 PM ET on Oct 12")
    import color_truth
    chk(not color_truth.contradictions(html), f"tiles: color truth {color_truth.contradictions(html)[:2]}")
    # SPRINT 9.9.2 (one fact once): the 24-hour change is the price tile's own badge, green beside +1.20%; the 7-day change is the chart
    # header's alone (its color is its own window's, tested with the chart), so neither prints as a tile of its own
    chk(re.search(r'data-reading="coin-price"><h3[^>]*>Price</h3><p class="tl-f">\$80,000\.00 <span class="tl-c chg up">\u25b2 1\.20%</span>', html),
        "tiles: the 24h change is not green beside +1.20% on the price tile")
    chk('data-reading="coin-24h"' not in html and 'data-reading="coin-7d"' not in html and "-3.40%" not in html,
        "tiles: a 24h or 7d tile prints a change the price tile or the chart header already prints")
    chk(re.search(r'data-reading="coin-price"><h3[^>]*>Price</h3><p class="tl-f">', html), "tiles: the price figure is colored")
    chk('data-reading="coin-200d"' in html and 'data-reading="rsi-14"' in html, "tiles: Board coin lacks 200-day or RSI")
    chk('data-reading="coin-200d"' not in cp.reading_tiles(c, 1, None, "7:00 PM ET on Oct 12"), "tiles: a 200-day tile with no Board data")

    esc, fd = sb.esc, sb.fmt_date
    today = datetime.date(2026, 10, 13)
    prose = {"date": "2026-10-13", "headline": "h", "paragraphs": ["Bitcoin holds its 200-day line. Ethereum is weak. Bitcoin RSI is 55."]}
    card = cp.chartmaster_card(c, prose, asset, today, esc, fd)
    chk("Bitcoin holds" in card and "Ethereum" not in card and "October 13, 2026" in card, "cm card: not the coin's own sentences under the read's date")
    other = {"symbol": "XYZ", "name": "Xyz", "price": 1.0}
    chk(cp.chartmaster_card(other, prose, None, today, esc, fd) == "", "cm card: a card for a coin with neither read nor levels")
    lv = cp.chartmaster_card(c, {"date": "2026-10-13", "paragraphs": ["Ethereum only."]}, asset, today, esc, fd, board_day="2026-10-12")
    chk("Chart levels, October 12" in lv, "cm card: levels not dated by the Board")       # 9.9.2: the house wording
    old = cp.chartmaster_card(c, dict(prose, date="2026-10-08"), asset, today, esc, fd)
    chk("October 8" in old and "5 days old" in old, "cm card: an old read does not say its date and age")

    tmp = tempfile.mkdtemp()
    try:
        f = os.path.join(tmp, "u.json")
        json.dump({"read_date": "2026-10-06", "projects": [
            {"gecko_id": "bitcoin", "symbol": "BTC", "next_unlock": None, "source_url": "https://x"},
            {"gecko_id": "aptos", "symbol": "APT", "source_url": "https://apt.example/u", "read_date": "2026-10-06",
             "next_unlock": {"date": "2026-10-20", "amount": "$10M", "share": "1%"}},
            {"gecko_id": "old", "symbol": "OLD", "source_url": "https://o", "next_unlock": {"date": "2026-09-01"}}]}, open(f, "w"))
        u = lambda cc: cp.unlock_line(cc, today, esc, sb.fmt_short_date, path=f)
        chk(u(c) == "" and u({"gecko_id": "old", "symbol": "OLD"}) == "" and u({"gecko_id": "none"}) == "", "unlock: a line for a coin without a future dated unlock")
        chk("apt.example" in u({"gecko_id": "aptos", "symbol": "APT"}) and "read" in u({"gecko_id": "aptos"}), "unlock: no source or read date")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    wire = {"items": [{"line": "Bitcoin ETFs saw outflows", "reported_utc": "2026-10-12T10:00:00Z", "links": [{"url": "https://a", "outlet": "A"}], "source_count": 1},
                      {"line": "Bitcoin hits a level", "reported_utc": "2026-10-13T10:00:00Z", "links": [], "source_count": 2},
                      {"line": "A sold-out show", "titles": [], "reported_utc": "2026-10-13T11:00:00Z"}]}
    hits = cp.wire_stories({"symbol": "SOL", "name": "Solana"}, wire)
    chk(hits == [], "stories: SOL matched 'sold'")
    hits = cp.wire_stories(c, wire)
    chk([h["line"] for h in hits] == ["Bitcoin hits a level", "Bitcoin ETFs saw outflows"], "stories: not newest first")
    return fails


def no_ledger_symbols():
    """Lower-case symbols of the coins whose page carries no Ledger card under Sprint 9.5's rule, from the Board and the
    Big movers record the build reads (site_build._past_mover_line's own rule, read here from the data)."""
    import site_build as sb
    import movers as mv
    pulse = sb.load_pulse() or {}
    rec = sb._movers_rec(None)
    out = set()
    for c in (pulse.get("movers") or {}).get("top100") or []:
        sym = str(c.get("symbol") or "")
        chg = c.get("chg_24h_pct")
        if (isinstance(chg, (int, float)) and abs(chg) >= mv.GATE["move_min_pct"]) or sym in mv.listed(
                rec, pulse.get("generated_utc") or ""):
            out.add(sym.lower())
    return out


def page_fails(f, h, no_ledger):
    """One coin page's static checks."""
    fails = []
    if len(re.findall(r'src="/assets/coinchart\.js\?v=', h)) != 1:
        fails.append(f"static: {f} does not carry the shared chart file exactly once")
    if h.count('role="tab"') != 4 or "market_chart" in h:
        fails.append(f"static: {f} tabs or inline chart code wrong")
    # SPRINT 9.5's rule (AUDIT.md 3.4 move 7): a coin past the mover line that day (on the Big movers record, or a
    # 24-hour move at or past the gate's first leg) carries NO Ledger card; every other coin carries it.
    past = f[:-5].lower() in no_ledger
    if 'data-reading="coin-price"' not in h:
        fails.append(f"static: {f} lacks the price tile")
    if past and 'class="cn-cold"' in h:
        fails.append(f"static: {f} carries the cold-storage card though its coin moved past the mover line")
    if not past and 'class="cn-cold"' not in h:
        fails.append(f"static: {f} lacks the cold-storage card")
    return fails


def static(site, min_pages=90):
    fails = []
    no_ledger = no_ledger_symbols()
    coins = os.path.join(site, "coins")
    pages = sorted(f for f in os.listdir(coins) if f.endswith(".html"))
    if len(pages) < min_pages:
        fails.append(f"static: only {len(pages)} coin pages")
    for f in pages:
        h = open(os.path.join(coins, f), encoding="utf-8").read()
        fails += page_fails(f, h, no_ledger)
    # Sprint 6.5: comments are stripped from the stylesheets at publish only. The published copy has no
    # comment marker; the source keeps its comments (they carry the reasons).
    for css in ("site.css", "system.css"):
        pub = os.path.join(site, "assets", css)
        src = os.path.join(HERE, "site", "assets", css)
        if not os.path.exists(pub):
            fails.append(f"static: published assets/{css} is missing")
            continue
        if "/*" in open(pub, encoding="utf-8").read():
            fails.append(f"static: published assets/{css} still carries a comment (/*)")
        if "/*" not in open(src, encoding="utf-8").read():
            fails.append(f"static: the source site/assets/{css} lost its comments; stripping is at publish only")
    p = open(os.path.join(site, "pulse", "prices.html"), encoding="utf-8").read()
    if "data-coin-search" not in p or p.count('href="/coins/') < 100 or "No coin matches" not in p:
        fails.append("static: the Top 100 lacks search, 100 links or the empty message")
    return fails


def browser(site):
    node = shutil.which("node")
    mod = os.environ.get("PLAYWRIGHT_MODULE", "/opt/node-tools/node_modules/playwright")
    if not node or not os.path.isdir(mod):
        print("coin pages: browser checks SKIPPED (node or playwright not found)")
        return []
    env = dict(os.environ, PLAYWRIGHT_MODULE=mod)
    out = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    r = subprocess.run([node, os.path.join(HERE, "scripts", "coin_pages_browser.mjs"), site],
                       stdout=out, stderr=subprocess.STDOUT, env=env, timeout=900)
    out.seek(0)
    lines = [l.rstrip() for l in out if l.startswith("FAIL")]
    out.close()
    os.unlink(out.name)
    return lines or ([f"browser: exit {r.returncode}"] if r.returncode else [])


def main():
    site = os.path.join(HERE, "site", "publish")
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    fails = unit()
    if os.path.isdir(os.path.join(site, "coins")):
        fails += static(site)
        if "--no-browser" not in sys.argv:
            fails += browser(site)
    else:
        fails.append(f"no built tree at {site}")
    for f in fails:
        print("FAIL", f)
    print("COIN PAGES:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
