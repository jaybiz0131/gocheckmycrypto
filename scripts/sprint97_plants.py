#!/usr/bin/env python3
"""U-9 plants for Sprint 9.7: each guarded thing broken on purpose in a throwaway copy, scripts/sprint97_test.py run, the break
undone and the test run again. Fresh copy per plant.

usage: sprint97_plants.py <repo> <built publish dir> <workdir> <log>

Two kinds. A SOURCE plant breaks one of the repository's files in a copy of the repository and runs the unit cases. A TREE plant
breaks one file of a copy of the built tree and runs the tree cases (with the browser script where the thing guarded is in the
browser). A plant is (name, kind, [(file, old text, new text), ...]); every old text must occur exactly once in its file or the
plant is reported NOT APPLIED. The restore is from the saved copy of the file, never a git checkout (the 1 October rule)."""
import os
import shutil
import subprocess
import sys

repo, tree_src, work, log = sys.argv[1:5]
AF, SB, SN, HM, WK, VP = "api_feeds.py", "site_build.py", "snapshot.py", "home.py", "worker/live-prices.mjs", "verify_pipeline.py"
H = "index.html"
PLANTS = [
    # ---- the one stale rule
    ("stale: the boundary is inclusive (exactly three hours old counts as stale)", "src", [(SN, "return h > (STALE_HOURS if hours is None else hours)", "return h >= (STALE_HOURS if hours is None else hours)")]),
    ("stale: a feed with an as-of it cannot read is called fresh", "src", [(AF, "return True if got is None else bool(got)", "return False if got is None else bool(got)")]),
    ("stale: the feed's window is its own (6 hours), not the page's", "src", [(AF, '"stale_after_hours": snapshot.STALE_HOURS', '"stale_after_hours": 6')]),
    # ---- shapes and figures
    ("top100: the price shown is not the page's string", "src", [(AF, '"shown": {"price": sb._price_fmt(price) if price else None,', '"shown": {"price": f"{price:,.0f}" if price else None,')]),
    ("top100: the feed's as-of is the build moment, not the Board's reading", "src", [(AF, 'return envelope("top100", "/pulse/prices", (pulse or {}).get("generated_utc"), now,', 'return envelope("top100", "/pulse/prices", _iso(now), now,')]),
    ("whales: the sentence is reworded", "src", [(AF, '"sentence": ww["sentence"],', '"sentence": ww["sentence"].replace("transfer", "move"),')]),
    ("news: a wire line reaches the feed cut short", "src", [(AF, '"line": i.get("line"),', '"line": (i.get("line") or "")[:40],')]),
    ("movers: a record that is not current for the Board is listed anyway", "src", [(AF, "cur = mv.current(rec, board_utc) if rec else None", "cur = rec")]),
    ("coin: the price is taken from the raw value, not the tile the page printed", "src", [(AF, '"shown": {"price": price_tile["figure"] if price_tile else (sb._price_fmt(price) if price else None),', '"shown": {"price": f"{price}" if price else None,')]),
    ("why: the dated feed carries a sentence the card does not print", "src", [(AF, '"card_text": list(card),', '"card_text": list(card) + ["It moved because of the news."],')]),
    ("index: a feed is left out of the index", "src", [(AF, '        if f.get("name") == "index":\n            continue\n', '        if f.get("name") == "index" or f.get("name") == "whales":\n            continue\n')]),
    ("index: the count of stale feeds is wrong", "src", [(AF, '"stale_count": sum(1 for r in rows if r["stale"]),', '"stale_count": 0,')]),
    # ---- the backfill refuses an unstored day
    ("backfill: a day with no stored verdict record is built anyway", "src", [(AF, '    if not recs:\n        return {"day": day, "ok": False, "why": "no stored verdict record", "pages": [], "slots": []}\n', '')]),
    ("backfill: any string is taken for a date", "src", [(AF, 'return bool(re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", str(day))) and _dt.date.fromisoformat(str(day)) is not None', 'return True')]),
    ("backfill: a stored day that graded nothing is given a page", "src", [(AF, "    if not pages:\n        return {", "    pages = pages or [vd.url(day, 'BTC')]\n    if not pages:\n        return {")]),
    ("why: a dated feed is invented for a day with no record", "src", [(AF, "        recs = _day_records(d, vdir)\n        if not recs:\n            continue\n", "        recs = _day_records(d, vdir) or [{'slot': 'evening', 'coins': {}}]\n")]),
    # ---- events
    ("events: the breaking line is a copy that has drifted (1 percent)", "src", [(AF, "if isinstance(mp, (int, float)) and abs(mp) >= BREAKING_LINE_PCT:", "if isinstance(mp, (int, float)) and abs(mp) >= 1.0:")]),
    ("events: the log is not cut to 50", "src", [(AF, '"events": uniq[:EVENT_LIMIT]})', '"events": uniq})')]),
    ("events: a coin in place 40 counts as a top-10 mover", "src", [(AF, "if isinstance(pos, int) and pos <= TOP_RANK_FOR_EVENT:", "if isinstance(pos, int):")]),
    ("events: the example Brief is an event", "src", [(AF, 'if i.get("example") or not str(i.get("id", "")).startswith("wrap-")', 'if not str(i.get("id", "")).startswith("wrap-")')]),
    ("events: any change of grade is a verdict that moved", "src", [(AF, 'if prev and prev != grade and grade in ("Confirmed", "Disputed"):', "if prev and prev != grade:")]),
    ("events: oldest first", "src", [(AF, "e[\"id\"]), reverse=True)\n    uniq", "e[\"id\"]), reverse=False)\n    uniq")]),
    ("events: a correction is given a time the record does not hold", "src", [(AF, 'events.append(_event("correction", f"{day}-{row[\'what\']}-{row[\'text\']}", None, day,', 'events.append(_event("correction", f"{day}-{row[\'what\']}-{row[\'text\']}", day + "T12:00:00Z", day,')]),
    # ---- the search pass
    ("title: the home's title is the brand alone again", "src", [(SB, 'HOME_TITLE = f"Crypto prices today and why they moved - {NAME}"', 'HOME_TITLE = f"{FAMILY} - Crypto, checked."')]),
    ("title: the Top 100's title loses its query words", "src", [(SB, 'TOP100_TITLE = f"Top 100 crypto prices today by market cap - {NAME}"', 'TOP100_TITLE = f"Top 100 - Markets - {NAME}"')]),
    ("h1: the coin page's heading is an h2 again", "src", [(SB, '<h1 class="cn-title">{esc(name)}<span class="cn-sym">{esc(sym)}</span></h1>', '<h2 class="cn-title">{esc(name)}<span class="cn-sym">{esc(sym)}</span></h2>')]),
    ("h1: the h1 has lost the h2's margin", "src", [(SB, "margin:1.4em 0 .4em;color:var(--ink)}", "margin:0;color:var(--ink)}")]),
    ("h1: the h1 uses a hard-coded color", "src", [(SB, "letter-spacing:-.005em;margin:1.4em 0 .4em;color:var(--ink)}", "letter-spacing:-.005em;margin:1.4em 0 .4em;color:#0F1B2D}")]),
    # ---- the route's client and the Worker
    ("live: the home takes a stale route answer", "src", [(HM, "return d&&d.stale===false&&d.simple", "return d&&d.simple")]),
    ("live: the home waits on the route with no time limit", "src", [(HM, "tm=ac?setTimeout(function(){ac.abort();},3000):0;", "tm=0;")]),
    ("live: the home has lost the CoinGecko fallback", "src", [(HM, "return d?d.simple:cg();", "return d?d.simple:{};")]),
    ("live: every page carries the route meta even when none is set", "src", [(SB, "\"gcm-live-prices\" content=\"{esc(LIVE_PRICE_URL)}\">\\n' if LIVE_PRICE_URL else \"\"", "\"gcm-live-prices\" content=\"{esc(LIVE_PRICE_URL)}\">\\n'")]),
    ("live: the canary admits the route host whether or not the build names it", "src", [(VP, "return HOME_HOSTS + ((m.group(1),) if m else ())", "return HOME_HOSTS + ('worker.example',)")]),
    ("worker: the cache holds an answer ten minutes", "src", [(WK, "export const LIVE_TTL_S = 60; ", "export const LIVE_TTL_S = 600;")]),
    ("worker: the last good answer is served as if fresh", "src", [(WK, "{ ...good, stale: true }", "{ ...good, stale: false }")]),
    ("worker: any origin may read it", "src", [(WK, "if (SITE_ORIGINS.includes(origin)) h[\"Access-Control-Allow-Origin\"] = origin;", "h[\"Access-Control-Allow-Origin\"] = origin || \"*\";")]),
    ("worker: ids are not checked", "src", [(WK, "export const ID_RX = /^[a-z0-9][a-z0-9-]{0,59}$/;", "export const ID_RX = /.*/;")]),
    ("worker: a CoinGecko failure with nothing held answers 200 with nothing", "src", [(WK, 'return json(request, { ok: false, why: "CoinGecko did not answer and no earlier answer is held" }, 502,', 'return json(request, { ok: false, why: "CoinGecko did not answer and no earlier answer is held" }, 200,')]),
    ("worker: a cookie is set", "src", [(WK, '"content-type": "application/json", ...cors(request), ...(extra || {}) }', '"content-type": "application/json", "set-cookie": "a=1", ...cors(request), ...(extra || {}) }')]),
    # ---- the watchlist (marks the table's own rows; no figure of its own)
    ("watchlist: the script asks the network", "src", [(SB, "  var only=panel.querySelector('[data-wl-only-btn]')", "  fetch('/x');\n  var only=panel.querySelector('[data-wl-only-btn]')")]),
    ("watchlist: the script sets a cookie", "src", [(SB, "  only.addEventListener('click',", "  document.cookie='wl=1';\n  only.addEventListener('click',")]),
    ("watchlist: a second store is used", "src", [(SB, "var KEY='gcmc_coins', root=document.documentElement, panel", "var KEY='wl_coins', root=document.documentElement, panel")]),
    ("watchlist: the panel reprints a saved coin's price (the same fact twice)", "src", [(SB, "'<h2 class=\"wp-h\">Your watchlist</h2>'", "'<h2 class=\"wp-h\">Your watchlist</h2><span class=\"wp-px\">$1</span>'")]),
    ("watchlist: the storage test is dropped (a denied store throws out of the script)", "src", [(SB, "  try{ localStorage.setItem('__t','1'); localStorage.removeItem('__t'); store=localStorage; }\n  catch(e){ root.removeAttribute('data-wl-n'); return; }\n", "  store=localStorage;\n")]),
    ("watchlist: the panel's height is not a fixed number", "src", [(SB, "{display:block;height:127px}", "{display:block}")]),
    ("watchlist: the heading box is not fixed", "src", [(SB, "box-sizing:border-box;height:24px;overflow:hidden;white-space:nowrap;font:600 18px/24px", "box-sizing:border-box;overflow:hidden;white-space:nowrap;font:600 18px/24px")]),
    ("watchlist: the head script marks no row", "src", [(SB, "td.sym2::after{content:", "td.sym2::first-line{content:")]),
    ("watchlist: saved rows are not filtered when asked", "src", [(SB, "html[data-wl-only] '+T+'tr{display:none}", "html[data-wl-only] '+T+'tr{}")]),
    ("watchlist: the head script is dropped from the page (the panel would appear late)", "src", [(SB, "                       schema_extra=watchlist_head(coins))", "                       schema_extra=\"\")")]),
    ("watchlist: the wiring script is put before the table", "src", [(SB, '""" + TOP100_JS + watchlist_script(coins)', '""" + TOP100_JS'), (SB, "  {watchlist_panel(coins)}\n  <div class=\"coin-search\" role=\"search\">", "  {watchlist_panel(coins)}{watchlist_script(coins)}\n  <div class=\"coin-search\" role=\"search\">")]),
    # ---- the feeds after review 1
    ("brief: the feed ignores the morning read (the review's failure)", "src", [(AF, "    m = home.usable_morning(morning, ed, now)\n    if m:", "    m = None\n    if m:")]),
    ("brief: the feed takes the morning read whatever its day", "src", [(AF, "    m = home.usable_morning(morning, ed, now)\n", "    m = dict(morning, morning=True, date=morning.get('date_et')) if morning else None\n")]),
    ("events: the Morning Brief is not an event", "src", [(AF, '    if morning and morning.get("headline") and morning.get("sentences") and _utc(morning.get("published_utc")):', "    if False:")]),
    ("events: a morning read with no sentences is an event", "src", [(AF, 'if morning and morning.get("headline") and morning.get("sentences") and _utc', 'if morning and morning.get("headline") and _utc')]),
    ("why: an ungraded coin's sentence is carried again", "src", [(AF, "if graded else []", "if True else []")]),
    ("why: the full graded line is carried again", "src", [(AF, 'coins[sym] = {"name": v.get("name"), "kind": v.get("kind"), "grade": v.get("grade"), "card_text": list(card),', 'coins[sym] = {"name": v.get("name"), "kind": v.get("kind"), "grade": v.get("grade"), "card_text": list(card), "text": list(v.get("text") or []),')]),
    ("movers: the change loses its window", "src", [(AF, '"window": "24 hours", "move_pct": x["move_pct"],', '"move_pct": x["move_pct"],')]),
    ("events: the change loses its window", "src", [(AF, '{"place": pos, "move_pct": x["move_pct"], "window": "24 hours"}', '{"place": pos, "move_pct": x["move_pct"]}')]),
    ("home: the 9.7 block of the tape's script is edited", "src", [(HM, "tm=ac?setTimeout(function(){ac.abort();},3000):0;", "tm=ac?setTimeout(function(){ac.abort();},4000):0;")]),
    # ---- wiring
    ("wiring: the build does not write the feeds", "src", [(SB, "    _write_api_feeds(w, items, pulse, flows, _board_tiles, _coin_tiles)\n", "")]),
    ("wiring: the suite does not run this test", "src", [("scripts/sprint95_suite.sh", 'run "scripts/sprint97_test.py --tree $TREE" python3 scripts/sprint97_test.py --tree "$TREE"\n', "")]),
    # ---- the built tree
    ("tree: a shown price in top100.json is not on the page", "tree", [("api/v1/top100.json", '"shown":{"price":"$82,893.00"', '"shown":{"price":"$92,893.00"')]),
    ("tree: markets.json is called fresh when it is not", "tree", [("api/v1/markets.json", '"stale":true,"stale_after_hours"', '"stale":false,"stale_after_hours"')]),
    ("tree: a coin's feed is missing", "tree", [("api/v1/coins/eth.json", None, None)]),
    ("tree: the index names a feed that is not there", "tree", [("api/v1/index.json", '"path":"/api/v1/whales.json"', '"path":"/api/v1/whales-gone.json"')]),
    ("tree: a feed carries a dash", "tree", [("api/v1/news.json", '"ranked_et":', '"x":"a' + chr(0x2014) + 'b","ranked_et":')]),
    ("tree: a coin page has no h1", "tree", [("coins/eth.html", '<h1 class="cn-title">', '<h2 class="cn-title">')]),
    ("tree: the home's title is the brand alone", "tree", [(H, "<title>Crypto prices today and why they moved - GoCheckMyCrypto</title>", "<title>GoCheckMyCrypto - Crypto, checked.</title>")]),
    ("tree: the beacon is gone from a coin page", "tree", [("coins/btc.html", "data-cf-beacon=", "data-x=")]),
    ("tree: a page's URL is gone", "tree", [("pulse/etf.html", None, None)]),
    ("tree: a feed is in a sitemap as a page", "tree", [("sitemap-priority.xml", "</urlset>", "<url><loc>https://gocheckmycrypto.com/api/v1/top100.json</loc></url></urlset>")]),
    ("browser: the head script is dropped from the built page (the panel appears when the late script runs)", "browser", [("pulse/prices.html", None, "drop-head-script")]),
    ("browser: the panel reprints BTC's price", "browser", [("pulse/prices.html", '<h2 class="wp-h">Your watchlist</h2>', '<h2 class="wp-h">Your watchlist</h2><p>$82,893.00</p>')]),
    ("browser: the saved rows are not marked in the built page", "browser", [("pulse/prices.html", "td.sym2::after{content:", "td.sym2::first-line{content:")]),
    ("browser: the wiring script asks its own host", "browser", [("pulse/prices.html", "  var only=panel.querySelector('[data-wl-only-btn]')", "  fetch('/data/snapshot.json');\n  var only=panel.querySelector('[data-wl-only-btn]')")]),
    ("browser: the home takes a stale route answer", "browser", [(H, "d.stale===false&&", "")]),
    ("browser: the home has no fallback when the route fails", "browser", [(H, "return d?d.simple:cg();", "return d?d.simple:{};")]),
    ("browser: the home asks the route even with no address named", "browser", [(H, "var LM=document.querySelector('meta[name=\"gcm-live-prices\"]'),LIVE=LM?LM.getAttribute('content'):'';", "var LIVE='https://worker.test/live/prices';")]),
    ("browser: the coin heading's size is not the h2's", "browser", [("coins/btc.html", "font-size:23px;line-height:1.2", "font-size:28px;line-height:1.2")]),
]

SKIP = {".git", "node_modules", "shots", "review", "docs", "out", "__pycache__"}


def ignore(d, names):
    rel = os.path.relpath(d, repo)
    out = {n for n in names if n == "__pycache__"}
    if rel == ".":
        out |= {n for n in names if n in SKIP}
    if rel == "site":
        out |= {n for n in names if n == "publish"}
    return out


def fresh_repo(dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(repo, dst, ignore=ignore, symlinks=True)


def run(cmd, cwd, timeout=1200):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    reds = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.startswith("  FAIL")]
    return r.returncode, reds


def apply(root, edits):
    saved = {}
    for f, old, new in edits:
        p = os.path.join(root, f)
        if old is None and new is None:
            saved[f] = None
            saved[f + "::bytes"] = open(p, "rb").read()
            os.remove(p)
            continue
        txt = open(p, encoding="utf-8").read()
        if new == "drop-head-script":
            a = txt.index("<script>(function(){try{var v=JSON.parse(localStorage.getItem('gcmc_coins')")
            b = txt.index("</script>", a) + len("</script>")
            saved.setdefault(f, txt)
            open(p, "w", encoding="utf-8").write(txt[:a] + txt[b:])
            continue
        if txt.count(old) != 1:
            if saved:
                restore(root, saved)
            return None, f"NOT APPLIED: {f}: old text occurs {txt.count(old)} time(s)"
        saved.setdefault(f, txt)            # the file as it was before ANY edit of this plant, so two edits to one file restore whole
        open(p, "w", encoding="utf-8").write(txt.replace(old, new, 1))
    return saved, ""


def restore(root, saved):
    for f, txt in saved.items():
        if f.endswith("::bytes"):
            open(os.path.join(root, f[:-7]), "wb").write(txt)
        elif txt is not None:
            open(os.path.join(root, f), "w", encoding="utf-8").write(txt)


lines = []
done_red = 0
n_applied = 0
tree_copy = os.path.join(work, "tree")
os.makedirs(work, exist_ok=True)
repo_copy = os.path.join(work, "repo")
fresh_repo(repo_copy)
print(f"{len(PLANTS)} plants")
for i, (name, kind, edits) in enumerate(PLANTS, 1):
    if kind == "src":
        saved, why = apply(repo_copy, edits)
        if saved is None:
            lines.append(f"PLANT {i} {name}: {why}")
            print(lines[-1])
            continue
        n_applied += 1
        rc, reds = run([sys.executable, "scripts/sprint97_test.py"], repo_copy)
        restore(repo_copy, saved)
        rc2, reds2 = run([sys.executable, "scripts/sprint97_test.py"], repo_copy)
    else:
        if os.path.exists(tree_copy):
            shutil.rmtree(tree_copy)
        shutil.copytree(tree_src, tree_copy)
        saved, why = apply(tree_copy, edits)
        if saved is None:
            lines.append(f"PLANT {i} {name}: {why}")
            print(lines[-1])
            continue
        n_applied += 1
        flag = [] if kind == "browser" else ["--no-browser"]
        rc, reds = run([sys.executable, os.path.join(repo, "scripts", "sprint97_test.py"), "--tree", tree_copy] + flag, repo)
        restore(tree_copy, saved)
        rc2, reds2 = run([sys.executable, os.path.join(repo, "scripts", "sprint97_test.py"), "--tree", tree_copy] + flag, repo)
    went_red = rc != 0
    done_red += 1 if (went_red and rc2 == 0) else 0
    lines.append(f"PLANT {i} {name}: exit {rc}, {len(reds)} red; restored: exit {rc2}")
    for r in reds[:2]:
        lines.append("      " + r)
    if rc2 != 0:
        lines.append("      STILL RED AFTER RESTORE: " + "; ".join(reds2[:2]))
    print(lines[-1] if not reds else "\n".join(lines[-1 - min(2, len(reds)):]))
lines.append(f"SUMMARY: {done_red} of {len(PLANTS)} plants went red and came back green ({n_applied} applied)")
open(log, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(lines[-1])
