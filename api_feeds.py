#!/usr/bin/env python3
"""api_feeds.py: the app-ready feeds, /api/v1/ (Program 9, Sprint 9.7; AUDIT.md sections 3.5 and 3.6).

One JSON file per screen, written by the build that writes the pages, from the records the pages are drawn from:

    top100.json            /pulse/prices        the Board's Top 100 rows
    markets.json           /pulse               the tiles the Board printed, as they printed them
    movers.json            /pulse/movers        the Big movers list
    whales.json            /flows               Whale Watch
    news.json              /news                the wire's day, ranked
    brief/latest.json      the Brief's page     the newest Brief
    why/today.json         /today, /why         the newest stored day's verdicts and evidence
    why/<date>.json        /today/<date>        one file per STORED day, never an unstored one
    why/record.json        /why/record/         the verdict record: the tally and every graded verdict (Sprint 9.8)
    coins/<slug>.json      /coins/<slug>        a coin page's readings
    events.json            (no page)            the newest 50 events that WOULD push, from stored records
    index.json                                  the list of the above, with each one's as-of and stale flag

Every file is one envelope: schema, version, name, path, page, as_of_utc, built_utc, stale, stale_after_hours, age_hours,
sources, data. Three rules hold for all of them.

  1. THE SAME RECORDS AS THE PAGE. A figure in a feed is the page's own string (`shown`) beside the raw value, taken from
     the same formatter or, for the Board's and a coin's readings, from the tile the page printed (tile.record). A figure
     the page does not print is not in the feed. scripts/sprint97_test.py reads every feed against its built page.
  2. STAMPED WITH ITS SOURCE TIME. `as_of_utc` is the instant of the reading the page's stamp states; a feed whose instant
     cannot be read says null and is stale.
  3. THE SITE'S OWN STALE RULE. `stale` is snapshot.is_stale: older than STALE_HOURS (3) at the build's moment, the same
     comparison asof.js makes in the browser. An app should apply it again at the moment it reads
     (`as_of_utc`, `stale_after_hours`), as the pages do.

Nothing here makes a request or a model call, and nothing is invented: an absent record is an absent field or an empty list,
and a day with no stored verdict record has no file.
"""
import datetime as _dt
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = 1
BASE = "/api/v1"
DOMAIN = "gocheckmycrypto.com"
EVENT_LIMIT = 50
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")
# AUDIT.md 3.1, the Breaking row: the whole market or Bitcoin moves 5% or more inside 24 hours. The watcher's own constant,
# never a copy, so a move of the line there moves it here.
try:
    import watcher as _watcher
    BREAKING_LINE_PCT = _watcher.MARKET_24H_PCT
except Exception:                                            # pragma: no cover
    BREAKING_LINE_PCT = 5.0
TOP_RANK_FOR_EVENT = 10        # AUDIT.md 3.5 item 2: "a top-10 coin past its mover line"


def _utc(ts):
    try:
        return _dt.datetime.strptime(str(ts or "").strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _iso(dt):
    return dt.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_stale(as_of_utc, now, hours=None):
    """The site's one stale rule (snapshot.is_stale). A feed has to say something about a reading it cannot date: stale."""
    import snapshot
    got = snapshot.is_stale(as_of_utc, now, hours)
    return True if got is None else bool(got)


def envelope(name, page, as_of_utc, now, sources, data):
    """One feed's envelope. `as_of_utc` that cannot be read is null (and the feed is stale)."""
    import snapshot
    as_of = str(as_of_utc).strip() if _utc(as_of_utc) else None
    h = snapshot.age_hours(as_of, now) if as_of else None
    return {"schema": f"{DOMAIN}/api/v1/{name}", "version": VERSION, "name": name, "path": f"{BASE}/{name}.json",
            "page": page, "as_of_utc": as_of, "built_utc": _iso(now), "stale": is_stale(as_of, now),
            "stale_after_hours": snapshot.STALE_HOURS, "age_hours": round(h, 2) if h is not None else None,
            "sources": list(sources), "data": data}


def _sb():
    import site_build
    return site_build


def _round(v, n=6):
    return round(float(v), n) if isinstance(v, (int, float)) else None


# ---- the Board's Top 100 ---------------------------------------------------------------------------------------

def top100_feed(pulse, now):
    sb = _sb()
    import snapshot
    coins = ((pulse or {}).get("movers") or {}).get("top100") or []
    rows = []
    for pos, c in enumerate(coins, 1):
        chg, price, mcap, vol = c.get("chg_24h_pct"), c.get("price"), c.get("mcap_usd"), c.get("volume_24h")
        slug = sb._coin_slug(c)
        rows.append({
            "rank": pos, "symbol": c.get("symbol") or "", "name": c.get("name") or "",
            "slug": slug, "url": f"/coins/{slug}", "price": price, "chg_24h_pct": chg, "mcap_usd": mcap, "volume_24h": vol,
            "spark7d": [_round(x) for x in (c.get("spark7d") or [])],
            "shown": {"price": sb._price_fmt(price) if price else None,
                      "chg_24h": sb.pct_text(chg) if chg is not None else None,
                      "mcap": sb.fmt_usd(mcap or 0) if mcap is not None else None,
                      "volume": sb.fmt_usd(vol) if vol else None}})
    return envelope("top100", "/pulse/prices", (pulse or {}).get("generated_utc"), now,
                    [snapshot.SOURCES["coins"] + " (the Board's snapshot)"],
                    {"count": len(rows), "rows": rows,
                     "screened_out": [{"symbol": o.get("symbol"), "reason": o.get("reason")}
                                      for o in (((pulse or {}).get("movers") or {}).get("screened_out") or [])]})


# ---- the Board's tiles -----------------------------------------------------------------------------------------

def _tile_row(t, now):
    return {"key": t["key"], "label": t["label"], "figure": t["figure"], "change_pct": t.get("change_pct"),
            "window": t["window"], "since": t["since"], "source": t["source"], "stamp": t["stamp"],
            "as_of_utc": t.get("as_of_utc"), "stale": is_stale(t.get("as_of_utc"), now)}


def markets_feed(tiles, snap, now):
    """The Board's tiles exactly as tile.render printed them while /pulse was drawn."""
    snap = snap or {}
    rows = [_tile_row(t, now) for t in (tiles or [])]
    as_of = snap.get("stamp_utc") or min((r["as_of_utc"] for r in rows if r["as_of_utc"]), default=None)
    return envelope("markets", "/pulse", as_of, now, sorted({r["source"] for r in rows}) or ["the Board's snapshot"],
                    {"stamp_et": snap.get("stamp_et") or None, "tiles": rows})


# ---- Big movers ------------------------------------------------------------------------------------------------

def movers_feed(rec, pulse, now):
    import movers as mv
    board_utc = (pulse or {}).get("generated_utc") or ""
    cur = mv.current(rec, board_utc) if rec else None
    if not cur:
        return envelope("movers", "/pulse/movers", None, now, ["the desk's Big movers record"],
                        {"state": "no_current_reading", "rule": dict(mv.GATE), "coins": []})
    g = cur.get("gate") or {}
    held = g.get("over_cap") or []
    rows = []
    for x in (g.get("passed") or []) + held:
        e = (cur.get("coins") or {}).get(x["sym"]) or {}
        v = (((e.get("verdict") or {}).get("coins") or {}).get(x["sym"]) or {})
        grade, url = v.get("grade"), v.get("url")
        if x in held:
            shown = "Past the cap"
        elif grade and url:
            shown = f"Checked: {grade}"
        elif v.get("kind") == "withheld":
            shown = "Not checked today"
        elif v.get("kind") == "next_read":
            shown = "Verdict at the next read"
        else:
            shown = "No grade"
        rows.append({"pos": x.get("pos"), "symbol": x["sym"], "name": x["name"], "url": mv.coin_href(x["sym"], x["name"]),
                     "window": "24 hours", "move_pct": x["move_pct"], "excess_pts": x.get("excess_pts"), "multiple": x.get("multiple"),
                     "held": x in held, "grade": grade if (grade and url) else None, "verdict_url": url if grade else None,
                     "shown": {"move": mv._pct(x["move_pct"]), "grade": shown}})
    return envelope("movers", "/pulse/movers", (cur.get("window") or {}).get("end_utc"), now,
                    ["the desk's Big movers record (AUDIT.md 3.2)"],
                    {"state": "current", "rule": dict(mv.GATE), "date_et": cur.get("date_et"), "slot": cur.get("slot"),
                     "coins": rows})


# ---- Whale Watch -----------------------------------------------------------------------------------------------

def whales_feed(flows, now):
    sb = _sb()
    flows = flows or {}
    ww = sb.whale_window(flows)
    v, s = flows.get("volatile") or {}, flows.get("stablecoins") or {}

    def move(m):
        return {"symbol": m.get("symbol"), "usd": m.get("usd"), "from": sb.venue_name(m.get("from")),
                "to": sb.venue_name(m.get("to")), "ts": m.get("ts"), "stable": bool(m.get("stable")),
                "url": m.get("url") or (f"https://whale-alert.io/transaction/{m['blockchain']}/{m['hash']}"
                                        if m.get("hash") and m.get("blockchain") else None),
                "shown": {"usd": sb.fmt_usd(m.get("usd", 0))}}

    ex = []
    for e in flows.get("by_exchange") or []:
        n = e.get("net_usd", 0)
        ex.append({"exchange": sb.venue_name(e.get("exchange")), "inflow_usd": e.get("inflow_usd"),
                   "outflow_usd": e.get("outflow_usd"), "net_usd": n,
                   "shown": {"net": ("+" if n >= 0 else "") + sb.fmt_usd(n)}})
    weeks = []
    for w in flows.get("history") or []:
        n = w.get("net_usd", 0)
        weeks.append({"week_ending": w.get("week_ending"), "net_usd": n,
                      "shown": {"net": ("+" if n >= 0 else "") + sb.fmt_usd(n)}})
    net = v.get("net_usd")
    return envelope("whales", "/flows", flows.get("generated_utc"), now,
                    ["Whale Alert public archive" if flows.get("source") != "blockscout" else "Blockscout public explorer"],
                    {"window_hours": flows.get("window_hours"), "sentence": ww["sentence"], "count": ww["count"],
                     "volatile": {"net_usd": net if isinstance(net, (int, float)) else None, "direction": v.get("direction"),
                                  "inflow_usd": v.get("inflow_usd"), "outflow_usd": v.get("outflow_usd")},
                     "stablecoins": {"net_buying_power_usd": s.get("net_buying_power_usd")},
                     "by_asset": [{"symbol": a.get("symbol"), "net_usd": a.get("net_usd")} for a in flows.get("by_asset") or []],
                     "by_exchange": ex, "weeks": weeks,
                     "moves_in": [move(m) for m in ww["inflows"]], "moves_out": [move(m) for m in ww["outflows"]]})


# ---- the wire and the Brief ------------------------------------------------------------------------------------

def news_feed(wire, now):
    wire = wire or {}
    items = []
    for i in wire.get("items") or []:
        items.append({"rank": i.get("rank"), "id": i.get("id"), "line": i.get("line"), "standing": i.get("standing"),
                      "source_count": i.get("source_count"), "primary": bool(i.get("primary")),
                      "board_reading": i.get("board_reading"),
                      "links": [{"outlet": l.get("outlet"), "url": l.get("url"), "primary": bool(l.get("primary"))}
                                for l in i.get("links") or []]})
    return envelope("news", "/news", wire.get("ranked_utc"), now,
                    ["the desk's wire: clusters ranked by the desk, sources counted and linked"],
                    {"ranked_et": wire.get("ranked_et"), "items": items})


def brief_feed(ed, now, morning=None):
    """The newest Brief, by the home Brief card's own choice: home.usable_morning (the morning read, when it is today's in Eastern and no
    later Edition has superseded it), else the day's Edition (current_bottom_line). One function, so the two cannot disagree."""
    import home
    m = home.usable_morning(morning, ed, now)
    if m:
        return envelope("brief/latest", "/", m.get("published_utc"), now, ["the desk's Morning Brief"],
                        {"state": "current", "title": m.get("headline"), "dek": None, "slot": "morning", "date": m.get("date_et"),
                         "published_utc": m.get("published_utc"), "sentences": list(m.get("sentences") or []),
                         "line": (m.get("line") or "").strip() or None, "bottom_line": None, "key_fact": None, "url": "/"})
    if not ed:
        return envelope("brief/latest", "/bottom-line", None, now, ["the Brief"], {"state": "none"})
    ident = str(ed.get("id") or "")
    slot = "evening" if ident.startswith("wrap-pm") or "evening" in str(ed.get("slug")) else (
        "morning" if ident.startswith("wrap-am") or "morning" in str(ed.get("slug")) else None)
    return envelope("brief/latest", f"/articles/{ed.get('slug')}.html", ed.get("published_utc"), now, ["the desk's Brief"],
                    {"state": "current", "title": ed.get("title"), "dek": ed.get("dek"), "slot": slot, "date": ed.get("date"),
                     "published_utc": ed.get("published_utc"), "sentences": [], "line": None, "bottom_line": ed.get("bottom_line"),
                     "key_fact": ed.get("key_fact"), "url": f"/articles/{ed.get('slug')}.html"})


# ---- a coin page -----------------------------------------------------------------------------------------------

def coin_feed(c, pos, tiles, pulse, now, facts=None):
    sb = _sb()
    sym = c.get("symbol") or ""
    slug = sb._coin_slug(c)
    readings = [_tile_row(t, now) for t in (tiles or [])]
    price_tile = next((r for r in readings if r["key"] == "coin-price"), None)
    chg_tile = next((r for r in readings if r["key"] == "coin-24h"), None)
    price, chg = c.get("price"), c.get("chg_24h_pct")
    facts = facts or {}
    data = {"symbol": sym, "name": c.get("name") or sym, "slug": slug, "url": f"/coins/{slug}", "rank": pos,
            "price": price, "chg_24h_pct": chg, "chg_7d_pct": c.get("chg_7d_pct"), "chg_30d_pct": c.get("chg_30d_pct"),
            "mcap_usd": c.get("mcap_usd"), "volume_24h": c.get("volume_24h"),
            "spark7d": [_round(x) for x in (c.get("spark7d") or [])],
            "shown": {"price": price_tile["figure"] if price_tile else (sb._price_fmt(price) if price else None),
                      "chg_24h": chg_tile["figure"] if chg_tile else None},
            "readings": readings,
            "verdict": {"grade": facts.get("grade"), "url": facts.get("url")} if facts.get("grade") else None}
    return envelope(f"coins/{slug}", f"/coins/{slug}", (pulse or {}).get("generated_utc"), now,
                    ["CoinGecko, as the page's readings state"], data)


# ---- the verdicts, by day: from STORED records only ------------------------------------------------------------

def _vd():
    import verdict
    return verdict


def _day_records(day, vdir=None):
    vd = _vd()
    out = []
    for n in vd._names(vdir):
        if n[:10] == day:
            r = vd.load(day, n[11:-5], vdir)
            if r:
                out.append(r)
    return out


def _valid_day(day):
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(day))) and _dt.date.fromisoformat(str(day)) is not None
    except ValueError:
        return False


def backfill(day, vdir=None, wdir=None):
    """Whether the dated pages for `day` can be built, from stored records only. A day with no stored VERDICT record is
    refused, whatever else is stored for it: an evidence record alone has never been graded, and grading it now would be
    writing a verdict the desk did not make then. A stored day that graded nothing gets no page. Nothing is written."""
    if not _valid_day(day):
        return {"day": day, "ok": False, "why": "not a date", "pages": [], "slots": []}
    recs = _day_records(day, vdir)
    if not recs:
        return {"day": day, "ok": False, "why": "no stored verdict record", "pages": [], "slots": []}
    vd = _vd()
    pages = [vd.url(day, sym) for sym in ("BTC", "ETH")
             if any(((r.get("coins") or {}).get(sym) or {}).get("grade") for r in recs)]
    slots = sorted(r.get("slot") for r in recs)
    if not pages:
        return {"day": day, "ok": False, "why": "no graded verdict in the stored record", "pages": [], "slots": slots}
    return {"day": day, "ok": True, "why": "", "pages": pages, "slots": slots}


def backfill_all(vdir=None, wdir=None):
    """Every stored day, once, with what the backfill makes of it: {days: [backfill(...)], pages: [...]}."""
    vd = _vd()
    days = sorted({n[:10] for n in vd._names(vdir)})
    rows = [backfill(d, vdir, wdir) for d in days]
    return {"days": rows, "pages": [p for r in rows for p in r["pages"]]}


def _day_data(day, recs, wdir=None, tdir=None):
    vd = _vd()
    import why_evidence as we
    recs = sorted(recs, key=lambda r: r.get("slot") == "evening", reverse=True)
    lead = None
    for sym in ("BTC", "ETH"):
        lead = next((r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade")), None) or lead
    lead = lead or recs[0]
    ev = we.load(day, lead.get("slot"), wdir)
    coins = {}
    for sym, v in (lead.get("coins") or {}).items():
        # the sentences the verdict page's card prints: with the evidence list beside it the card uses the section form
        # (verdict.text_sec), which points at the listed item instead of repeating its time; `text` is the full graded line
        # only what the page prints: a graded coin's card sentences (the section form beside the evidence list). A coin with no grade
        # prints no sentence on the page that is the feed's (an Ether "moved with Bitcoin" line is on the Ether coin page only).
        graded = bool(v.get("grade"))
        card = ((vd.text_sec(v) if ev else None) or list(v.get("text") or [])) if graded else []
        coins[sym] = {"name": v.get("name"), "kind": v.get("kind"), "grade": v.get("grade"), "card_text": list(card),
                      "window_words": v.get("window_words"), "basis": v.get("basis"),
                      "url": v.get("url") if v.get("grade") else None}
    evidence = None
    if ev:
        evidence = {"window": ev.get("window"), "candidates": [
            {"id": c.get("id"), "kind": c.get("kind"), "line": c.get("line"), "event_utc": c.get("event_utc"),
             "report_utc": c.get("report_utc"), "scheduled": c.get("scheduled"), "primary": c.get("primary"),
             "source_count": c.get("source_count"), "links": c.get("links") or []} for c in ev.get("candidates") or []],
            "series": {}}
        for sym, ce in (ev.get("coins") or {}).items():
            s = ce.get("series") or {}
            evidence["series"][sym] = {"source": s.get("source"), "bar_min": s.get("bar_min"), "points": s.get("points") or [],
                                       "run": ce.get("run")}
    return {"state": "stored", "note": "A dated file is a stored record of that day; stale follows the same rule as any reading, "
                                      "so a past day is stale and is read as the archive it is.",
            "date_et": day, "slot": lead.get("slot"), "slots": sorted(r.get("slot") for r in recs),
            "made_utc": lead.get("made_utc"), "window": lead.get("window"), "coins": coins, "evidence": evidence}


def why_feeds(now, vdir=None, wdir=None, tdir=None):
    """{relative path: envelope}: why/<date>.json for each STORED verdict day, and why/today.json for the newest. No stored
    record: today.json says so and no dated file exists."""
    vd = _vd()
    days = sorted({n[:10] for n in vd._names(vdir)})
    out = {}
    for d in days:
        recs = _day_records(d, vdir)
        if not recs:
            continue
        data = _day_data(d, recs, wdir, tdir)
        out[f"why/{d}.json"] = envelope(f"why/{d}", f"/today/{d}", data["made_utc"], now,
                                        ["the desk's stored verdict record and its evidence record"], data)
    if days and f"why/{days[-1]}.json" in out:
        newest = out[f"why/{days[-1]}.json"]
        out["why/today.json"] = envelope("why/today", "/today/", newest["as_of_utc"], now, newest["sources"], newest["data"])
    else:
        out["why/today.json"] = envelope("why/today", "/today/", None, now, ["the desk's stored verdict record"],
                                         {"state": "none_stored", "coins": {}})
    return out


# ---- events: what WOULD push (AUDIT.md 3.5 item 2) --------------------------------------------------------------

def _event(kind, key, at_utc, date_et, title, url, coin=None, detail=None):
    eid = kind + "-" + hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:10]
    return {"id": eid, "kind": kind, "at_utc": at_utc, "date_et": date_et, "title": title, "url": url, "coin": coin,
            "detail": detail}


def events_feed(items, now, vdir=None, mdir=None, tdir=None, morning=None):
    """The newest 50 events that would push, from stored records only: a graded verdict on a move past the breaking line; a
    top-10 coin past its mover line; a verdict that moves to Confirmed or Disputed; a Brief published; a correction. Two
    weeks of this log is how Jack sets the push volume (AUDIT.md 3.5). Nothing is sent."""
    sb = _sb()
    vd = _vd()
    import movers as mv
    events, seen_at = [], []
    # verdicts: graded on a move past the line, and verdicts that move
    recs = []
    for n in vd._names(vdir):
        r = vd.load(n[:10], n[11:-5], vdir)
        if r:
            recs.append(r)
    recs.sort(key=lambda r: (r.get("date_et") or "", r.get("made_utc") or ""))
    last = {}
    for r in recs:
        day, slot, made = r.get("date_et"), r.get("slot"), r.get("made_utc")
        seen_at.append(made)
        for sym, v in (r.get("coins") or {}).items():
            grade = v.get("grade")
            if not grade:
                continue
            mp = v.get("move_pct")
            name = v.get("name") or sym
            if isinstance(mp, (int, float)) and abs(mp) >= BREAKING_LINE_PCT:
                events.append(_event("verdict_past_breaking_line", f"{day}-{slot}-{sym}", made, day,
                                     f"Why {name} moved {v.get('window_words') or ''}: {grade}".replace("  ", " "),
                                     v.get("url") or "/today/", sym,
                                     {"move_pct": mp, "window": v.get("window_words") or "24 hours", "line_pct": BREAKING_LINE_PCT, "basis": v.get("basis")}))
            prev = last.get((day, sym))
            if prev and prev != grade and grade in ("Confirmed", "Disputed"):
                events.append(_event("verdict_moved", f"{day}-{slot}-{sym}-{prev}-{grade}", made, day,
                                     f"Why {name} moved: the check went from {prev} to {grade}",
                                     v.get("url") or "/today/", sym, {"from": prev, "to": grade}))
            last[(day, sym)] = grade
    # movers: a top-10 coin past the mover line
    for r in mv.records(mdir):
        made = r.get("made_utc")
        seen_at.append(made)
        for x in (r.get("gate") or {}).get("passed") or []:
            pos = x.get("pos")
            if isinstance(pos, int) and pos <= TOP_RANK_FOR_EVENT:
                events.append(_event("top10_mover", f"{r.get('date_et')}-{r.get('slot')}-{x['sym']}", made, r.get("date_et"),
                                     f"{x['name']} ({x['sym']}) moved {mv._pct(x['move_pct'])} in 24 hours, past the Big movers line",
                                     mv.coin_href(x["sym"], x["name"]), x["sym"],
                                     {"place": pos, "move_pct": x["move_pct"], "window": "24 hours"}))
    # Briefs
    for i in items or []:
        if i.get("example") or not str(i.get("id", "")).startswith("wrap-") or not _utc(i.get("published_utc")):
            continue
        seen_at.append(i["published_utc"])
        events.append(_event("brief_published", i.get("id"), i["published_utc"], str(i.get("date") or "")[:10],
                             sb.destyle(i.get("title") or "The Brief"), f"/articles/{i.get('slug')}.html", None, None))
    # the Morning Brief: the stored morning read, when it is the kind the home shows (a headline and its sentences)
    if morning and morning.get("headline") and morning.get("sentences") and _utc(morning.get("published_utc")):
        seen_at.append(morning["published_utc"])
        events.append(_event("brief_published", "morning-" + str(morning.get("date_et")), morning["published_utc"],
                             str(morning.get("date_et") or "")[:10], sb.destyle(f"The Morning Brief: {morning['headline']}"), "/", None, None))
    # corrections: dated, never timed
    try:
        for row in sb.corrections_log(items or [], vdir, tdir):
            day = row["when"] or row.get("story_date") or ""
            events.append(_event("correction", f"{day}-{row['what']}-{row['text']}", None, day,
                                 f"Correction: {row['what']}", row["href"], None, {"text": row["text"]}))
    except Exception:                                        # fail open: the other events stand
        pass
    events.sort(key=lambda e: (e["at_utc"] or (e["date_et"] + "T00:00:00Z"), e["id"]), reverse=True)
    uniq, ids = [], set()
    for e in events:
        if e["id"] not in ids:
            ids.add(e["id"])
            uniq.append(e)
    as_of = max((t for t in seen_at if _utc(t)), default=None)
    return envelope("events", None, as_of, now,
                    ["the desk's stored verdict, Big movers, Brief and correction records"],
                    {"limit": EVENT_LIMIT, "breaking_line_pct": BREAKING_LINE_PCT,
                     "kinds": {"verdict_past_breaking_line": "a graded verdict on a move at or past the breaking line",
                               "top10_mover": "a top-10 coin past the Big movers line",
                               "verdict_moved": "a verdict that moved to Confirmed or to Disputed",
                               "brief_published": "the Morning or Evening Brief published",
                               "correction": "a correction (dated; its time is not recorded)"},
                     "note": "Events that WOULD push. Nothing is sent. A correction carries its date and no time.",
                     "events": uniq[:EVENT_LIMIT]})


# ---- the index -------------------------------------------------------------------------------------------------

def index_feed(feeds, now):
    rows = []
    for rel, f in feeds.items():
        if f.get("name") == "index":
            continue
        rows.append({"name": f["name"], "path": f["path"], "page": f["page"], "as_of_utc": f["as_of_utc"], "stale": f["stale"]})
    rows.sort(key=lambda r: r["path"])
    newest = max((r["as_of_utc"] for r in rows if r["as_of_utc"]), default=None)
    return envelope("index", "/", newest, now, ["the feeds listed"],
                    {"stale_count": sum(1 for r in rows if r["stale"]), "count": len(rows), "feeds": rows,
                     "how_to_read": "Every feed carries as_of_utc and a stale flag. stale is true when as_of_utc is more than "
                                    "stale_after_hours old at built_utc; apply the same comparison again when you read."})


def _record_feed(ctx, now):
    import verdict_record as vr
    v = vr.view(now, vdir=ctx.get("vdir"), mdir=ctx.get("mdir"), wdir=ctx.get("wdir"), store=ctx.get("rstore"))
    return vr.feed(v, now)


def build_all(ctx):
    """{relative path: envelope} from the build's own inputs. `ctx`: now, snap, pulse, flows, items, wire, ed, movers_rec,
    board_tiles, coin_tiles {slug: (coin, rank, tiles, facts)}, and the stored-record directories (None for the defaults).
    A feed that cannot be built is a warning and no file: the pages never wait on a feed."""
    now = ctx["now"]
    out = {}

    def put(rel, fn):
        try:
            out[rel] = fn()
        except Exception as e:                               # noqa: BLE001
            print(f"::warning::api feeds: {rel} was not written ({type(e).__name__}: {e})")

    put("top100.json", lambda: top100_feed(ctx["pulse"], now))
    put("markets.json", lambda: markets_feed(ctx.get("board_tiles"), ctx.get("snap"), now))
    put("movers.json", lambda: movers_feed(ctx.get("movers_rec"), ctx["pulse"], now))
    put("whales.json", lambda: whales_feed(ctx.get("flows"), now))
    put("news.json", lambda: news_feed(ctx.get("wire"), now))
    put("brief/latest.json", lambda: brief_feed(ctx.get("ed"), now, ctx.get("morning")))
    try:
        out.update(why_feeds(now, ctx.get("vdir"), ctx.get("wdir"), ctx.get("tdir")))
    except Exception as e:                                   # noqa: BLE001
        print(f"::warning::api feeds: the dated verdict feeds were not written ({type(e).__name__}: {e})")
    # SPRINT 9.8: the verdict record, /why/record/, from the same stores the page reads
    put("why/record.json", lambda: _record_feed(ctx, now))
    put("events.json", lambda: events_feed(ctx.get("items"), now, ctx.get("vdir"), ctx.get("mdir"), ctx.get("tdir"), ctx.get("morning")))
    for slug, (c, pos, tiles, facts) in (ctx.get("coin_tiles") or {}).items():
        put(f"coins/{slug}.json", lambda c=c, pos=pos, tiles=tiles, facts=facts: coin_feed(c, pos, tiles, ctx["pulse"], now, facts))
    out["index.json"] = index_feed(out, now)
    return out
