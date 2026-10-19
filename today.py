#!/usr/bin/env python3
"""
today.py: the daily answer (Program 8, Sprint 8.1; Jack's approval of 14 October 2026).

"Why is crypto down today" is one of the most repeated crypto searches. The site answers it twice
a day, at the morning and the evening build, from what the build already has: the snapshot, the
Top 100, the wire, the Board, and the morning read or the Edition. NO MODEL CALL.

  /today/              the living page: always the newest of the day's two records
  /today/YYYY-MM-DD    the dated page: the day's evening record once it exists, else the morning
                       one; it never changes after the evening build, except a correction

THE PAGE SAYS WHAT MOVED, BY HOW MUCH, IN WHAT WINDOW, and which reported events sit beside it,
each with its sources. It never says "because" in its own voice (a wire item may, because its
source does), it never predicts and it never advises. Every sentence it writes passes the twins
gate; a dropped sentence is logged as 7.3 built it. Every change carries its own arrow and color
(color truth).

A RECORD is the page's frozen content (site/data/today/YYYY-MM-DD-<slot>.json). The workflows
write one at each slot (`python3 today.py --write`) and commit it, which is how a dated page
stays what it was at the evening build; a build with no stored record for the slot composes one
from the files in hand, so the first build after a slot is never blank.
"""
import datetime as _dt
import json
import os
import re
import sys

import common

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "site", "data", "today")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-4))

FLAT_PCT = 0.5                    # Program 8, section 2: Bitcoin within plus or minus 0.5 percent
MAX_REPORTED = 5
ARCHIVE_N = 7
SAME_RUN_MIN = 30             # a read and a snapshot within 30 minutes are one run
SLOT_LABEL = {"morning": "Morning read", "evening": "Evening Edition"}

# The page's own voice never explains a move. A wire item may carry a cause, because its source does.
CAUSAL = re.compile(r"\b(because|due to|owing to|thanks to|as a result of|driven by|caused by|"
                    r"on account of|so that|therefore|in response to)\b", re.I)
ADVICE = re.compile(r"\b(buy|sell|should|must|invest\w*|recommend\w*|opportunit\w*|dip)\b", re.I)
DIR_WORDS = {"down": r"\b(down|fell|fall\w*|lower|lost|declin\w*|drop\w*|slid\w*|slump\w*|dipp\w*)\b",
             "up": r"\b(up|rose|rise\w*|higher|gain\w*|climb\w*|advanc\w*|rall\w*|surg\w*)\b",
             "flat": r"\b(flat|unchanged|steady|little changed|within)\b"}


# ---- the direction, the title -------------------------------------------------------------

def direction(chg):
    """'down', 'up' or 'flat' from Bitcoin's 24-hour change; None with no reading."""
    if not isinstance(chg, (int, float)) or isinstance(chg, bool):
        return None
    if abs(chg) <= FLAT_PCT:
        return "flat"
    return "up" if chg > 0 else "down"


def long_date(d):
    """'Wednesday, October 14, 2026'."""
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def heading(dirn, d):
    """(title, headline) from the day's real direction, with the full date in Eastern."""
    when = long_date(d)
    if dirn == "flat":
        h = f"Crypto today: flat. {when}"
    else:
        h = f"Why is crypto {dirn} today? {when}"
    return h, h


# ---- composing a record -----------------------------------------------------------------

def _et(utc):
    try:
        return _dt.datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=_dt.timezone.utc).astimezone(ET)
    except (TypeError, ValueError):
        return None


def _clock(dt):
    return dt.strftime("%-I:%M %p ET")


def _pct(v):
    return f"{abs(v):.2f}%"


def _word(v):
    return "up" if v > 0 else "down" if v < 0 else "unchanged"


def movers(pulse):
    """The Top 100's three biggest gainers and losers by 24 hours: only a coin that moved the
    way its list says (a gainer is above zero, a loser below it)."""
    import snapshot as _snapshot
    rows = [c for c in (((pulse or {}).get("movers") or {}).get("top100") or [])
            if isinstance(c.get("chg_24h_pct"), (int, float)) and isinstance(c.get("rank"), int)
            and c["rank"] <= _snapshot.MOVER_RANK_MAX and not _snapshot.is_stablecoin(c)]
    gain = sorted((c for c in rows if c["chg_24h_pct"] > 0), key=lambda c: -c["chg_24h_pct"])[:3]
    lose = sorted((c for c in rows if c["chg_24h_pct"] < 0), key=lambda c: c["chg_24h_pct"])[:3]
    import site_build as sb
    pick = lambda c: {"symbol": c.get("symbol"), "name": c.get("name"), "chg": c["chg_24h_pct"],
                      "slug": sb._coin_slug(c)}
    return [pick(c) for c in gain], [pick(c) for c in lose]


def template_sentences(d, dirn, btc, eth, cap, gain, lose):
    """The answer built from the numbers alone: what moved, how much, in what window. Fixed
    wording, no adjective beyond the copy law's list, no cause."""
    import home
    import site_build as sb
    when = f"{d.strftime('%A, %B')} {d.day}"
    c = btc["chg"]
    cd = btc.get("chg_day")
    if cd is not None:
        # THE DAY IS THE ET DAY (Sprint 9.1): the headline direction is the move since midnight
        # Eastern, and the rolling 24 hours follows in its own sentence with its own window
        if dirn == "flat":
            s = [f"On {when}, Bitcoin was flat since midnight ET, at {home._whole(btc['price'])}, "
                 f"a change of {cd:+.2f}%."]
        else:
            s = [f"On {when}, Bitcoin was {_word(cd)} {_pct(cd)} since midnight ET, to "
                 f"{home._whole(btc['price'])}."]
        if isinstance(c, (int, float)):
            s.append(f"Over the last 24 hours it was {_word(c)} {_pct(c)}.")
    elif dirn == "flat":
        s = [f"On {when}, Bitcoin was flat over the last 24 hours, at {home._whole(btc['price'])}, "
             f"a change of {c:+.2f}%."]
    else:
        s = [f"On {when}, Bitcoin was {_word(c)} {_pct(c)} over the last 24 hours, to "
             f"{home._whole(btc['price'])}."]
    if cap and isinstance(cap.get("chg"), (int, float)):
        s.append(f"The whole market's value was {_word(cap['chg'])} {_pct(cap['chg'])} over the same "
                 f"24 hours, to {sb.fmt_usd(cap['usd'])}.")
    if eth and isinstance(eth.get("chg"), (int, float)):
        s.append(f"Ether was {_word(eth['chg'])} {_pct(eth['chg'])} over the same 24 hours.")
    if gain and lose:
        s.append(f"Among the Top 100, {gain[0]['symbol']} gained {_pct(gain[0]['chg'])} and "
                 f"{lose[0]['symbol']} lost {_pct(lose[0]['chg'])} over 24 hours.")
    elif gain:
        s.append(f"Among the Top 100, {gain[0]['symbol']} gained {_pct(gain[0]['chg'])} over 24 hours.")
    elif lose:
        s.append(f"Among the Top 100, {lose[0]['symbol']} lost {_pct(lose[0]['chg'])} over 24 hours.")
    return s


def liftable(text, dirn, gate):
    """The morning read's or the Edition's text, when it can stand as the answer as it is: it
    names Bitcoin, states the day's direction the way the sign says, carries a figure, and every
    sentence passes the copy law and the twins gate. Else None, and the template answers."""
    import twins_gate
    text = " ".join(str(text or "").split())
    if not text or CAUSAL.search(text) or ADVICE.search(text) or re.search(r"[–—]", text):
        return None
    if not re.search(r"\b(bitcoin|btc)\b", text, re.I) or not re.search(r"\d\s*(%|percent)", text):
        return None
    if not re.search(DIR_WORDS[dirn], text, re.I):
        return None
    out = []
    for s in twins_gate.sentences(text):
        kept = gate.text(s, "the daily answer (lifted)", dollars=True)
        if kept.strip() != s.strip():
            return None
        out.append(s)
    return out or None


def wire_items(wire, d, gate):
    """Up to five wire items reported on `d` (Eastern), each with its sources and time. The
    item's line is the desk's one-line summary of what its sources report; it is gated like any
    sentence and a dropped line drops the item."""
    out = []
    for w in ((wire or {}).get("items") or []):
        t = _et(w.get("reported_utc"))
        if not w.get("line") or t is None or t.date() != d:
            continue
        line = gate.text(str(w["line"]).strip(), "the daily answer (reported)", dollars=True).strip()
        if not line:
            continue
        links = [{"outlet": l.get("outlet") or "Source", "url": l.get("url")}
                 for l in (w.get("links") or []) if l.get("url")]
        out.append({"line": line, "time": f"{t.strftime('%-I:%M %p')} ET",
                    "source_count": int(w.get("source_count") or len(links) or 0),
                    "primary": bool(w.get("primary")), "links": links[:4]})
        if len(out) == MAX_REPORTED:
            break
    return out


def board_rows(snap, pulse):
    """The Board's four readings the page carries, each with its window, source and stamp."""
    import snapshot as _s
    st = (snap or {}).get("stamp_et") or ""
    rows = []
    etf = ((_s.value(snap, "etf_flows") or {}).get("btc") or {})
    if isinstance(etf.get("latest_net_usd_m"), (int, float)):
        v = etf["latest_net_usd_m"]
        rows.append({"key": "etf", "label": "Bitcoin spot ETF net", "value": v,
                     "window": f"one trading day, {etf.get('latest_date') or 'latest'}",
                     "source": "Farside Investors", "stamp": st, "directional": True})
    liq = None
    for a in (((pulse or {}).get("leverage") or {}).get("assets") or []):
        if a.get("symbol") == "BTC":
            liq = a.get("liquidations")
    if isinstance(liq, dict) and isinstance(liq.get("longs_usd"), (int, float)):
        rows.append({"key": "liq", "label": "Bitcoin liquidations", "longs": liq["longs_usd"],
                     "shorts": liq.get("shorts_usd") or 0,
                     "window": "last " + common.hours_phrase(liq.get('window_hours', 2)), "source": "OKX",
                     "stamp": st, "directional": False})
    f = ((_s.value(snap, "funding") or {}).get("BTC") or {})
    if isinstance(f.get("funding_8h_pct"), (int, float)):
        rows.append({"key": "funding", "label": "Bitcoin funding", "value": f["funding_8h_pct"],
                     "window": "current 8-hour period", "source": f.get("venue") or "OKX",
                     "stamp": st, "directional": False})
    fg = _s.value(snap, "fear_greed") or {}
    if isinstance(fg.get("value"), (int, float)):
        rows.append({"key": "fng", "label": "Fear & Greed", "value": fg["value"],
                     "word": fg.get("label") or "", "window": "today",
                     "source": "alternative.me", "stamp": st, "directional": False})
    return rows


def next_update(slot, now):
    """'Next update: Morning read, tomorrow at 8:15 AM ET'. Read off the clock by the same function
    the home card uses (home.next_slot), so after the evening slot has run OR failed it names
    tomorrow's morning read, and the two surfaces cannot disagree."""
    import home
    kind, when = home.next_slot(now)
    return f"Next update: {SLOT_LABEL[kind]}, {when}"


def stamp_line(slot, src_utc, snap_utc, snap_stamp_et, now, fallback=False):
    """ONE HONEST LINE (Jack, 14 October 2026). When the text and the numbers come from the same
    run, the slot and its time ("Morning read, 8:18 AM ET"). When they do not, both times and
    the reason: "Numbers as of 7:12 PM ET, tonight's Edition did not publish; text from the 8:18
    AM read". FALLBACK (15 October): no read ran for the slot, so the line never names a morning
    read it does not have: "Numbers as of 8:17 AM ET \u00b7 this morning's read did not publish;
    text from last night's 7:14 PM Edition"."""
    pub, snap_t = _et(src_utc), _et(snap_utc)
    label = SLOT_LABEL[slot]
    if fallback:
        n = now.astimezone(ET)
        import home
        if n >= _evening_et(now):
            why = "tonight's Edition did not publish"
        elif n >= n.replace(hour=home.MORNING_ET[0], minute=home.MORNING_ET[1], second=0, microsecond=0):
            why = "this morning's read did not publish"
        else:
            why = "this morning's read has not published yet"
        nums = f"Numbers as of {_clock(snap_t)} \u00b7 " if snap_t else ""
        if pub is None:
            return f"{nums}{why}"
        when = ("last night's" if (n.date() - pub.date()).days == 1 and pub.hour >= 17
                else f"the {pub.strftime('%b')} {pub.day}")
        return f"{nums}{why}; text from {when} {pub.strftime('%-I:%M %p')} Edition"
    if pub is None:
        return label
    here = f"{label}, {_clock(pub)}"
    if snap_t is None or abs((snap_t - pub).total_seconds()) <= SAME_RUN_MIN * 60:
        return here
    kind = "read" if slot == "morning" else "Edition"
    reason = ""
    if slot == "morning" and now.astimezone(ET) >= _evening_et(now):
        reason = "tonight's Edition did not publish; "
    return (f"Numbers as of {_clock(snap_t)} \u00b7 {reason}text from the "
            f"{pub.strftime('%-I:%M %p')} {kind}")


def _evening_et(now):
    import home
    n = now.astimezone(ET)
    return _dt.datetime(n.year, n.month, n.day, home.EDITION_UTC[0], home.EDITION_UTC[1],
                        tzinfo=_dt.timezone.utc).astimezone(ET)


def slot_of(now, ed, morning):
    """('evening', source dict) once today's Edition has run, else ('morning', the read) when
    today's read ran, else (None, None)."""
    import home
    day = now.astimezone(ET).date()
    et = _et((ed or {}).get("published_utc"))
    if ed and et is not None and et.date() == day and et.hour >= 17:
        return "evening", ed
    m = home.usable_morning(morning, ed, now)
    if m:
        return "morning", m
    return None, None


def compose(snap, pulse, wire, ed, morning, now, gate, first_utc=None):
    """The day's record at this slot, or None when there is no slot read today or no Bitcoin
    reading to take a direction from (the page then says nothing rather than guess)."""
    import snapshot as _s
    slot, src = slot_of(now, ed, morning)
    fallback = False
    if not slot:
        # NO READ FOR THIS SLOT (the morning fell back, or the Edition did not publish): the page is
        # still the day's answer, built from the numbers alone, and says so. The last Edition on
        # the desk is the only text it may name, and it never claims a read that did not run.
        if not (ed and _et(ed.get("published_utc"))):
            return None
        # THE SLOT IS THE READ'S, AND A PAGE WITH NO READ TAKES THE CLOCK'S (Sprint 9.1, 8.3 item 5).
        # The 7:15 PM run of 15 October found no Edition, composed a numbers-only page and filed it
        # as the MORNING record: a morning that no morning read wrote, frozen. A fallback page is
        # filed under the slot the clock is in, flagged fallback, and a real read replaces it.
        slot = "evening" if now.astimezone(ET) >= _evening_et(now) else "morning"
        src, fallback = ed, True
    btc = dict(_s.coin(snap, "BTC") or {})
    btc_chg = btc.get("chg_24h_pct")
    d = now.astimezone(ET).date()
    # THE DIRECTION IS THE ET DAY'S (Sprint 9.1, AUDIT.md 1.1): the move since midnight Eastern,
    # not Bitcoin's rolling 24 hours at the hour the page happened to be written. A snapshot
    # whose midnight open belongs to another ET day (a carried-forward read) does not count; the
    # page then falls back to the rolling 24 hours and says so in `direction_basis`.
    chg_day = btc.get("chg_et_day_pct") if (
        isinstance(btc.get("chg_et_day_pct"), (int, float))
        and btc.get("open_et_day") == d.isoformat()) else None
    basis = "et_day" if chg_day is not None else "rolling_24h"
    dirn = direction(chg_day if chg_day is not None else btc_chg)
    if dirn is None or not isinstance(btc.get("price"), (int, float)):
        return None
    btc = {"price": btc["price"], "chg": btc_chg, "chg_day": chg_day}
    e = _s.coin(snap, "ETH") or {}
    eth = ({"price": e.get("price"), "chg": e.get("chg_24h_pct")}
           if isinstance(e.get("chg_24h_pct"), (int, float)) else None)
    c = _s.value(snap, "total_cap") or {}
    cap = ({"usd": c.get("usd"), "chg": c.get("chg_24h_pct")}
           if isinstance(c.get("usd"), (int, float)) and isinstance(c.get("chg_24h_pct"), (int, float))
           else None)
    gain, lose = movers(pulse)
    title, h1 = heading(dirn, d)
    # a read written about the rolling 24 hours is lifted only when that window points the way the
    # ET day does; when they disagree the template states both, each with its own window
    lifted = None if (fallback or direction(btc_chg) != dirn) else liftable(
        " ".join(src.get("sentences") or []) if slot == "morning"
        else (src.get("bottom_line") or src.get("dek") or ""), dirn, gate)
    if lifted:
        answer, by = lifted, slot
    else:
        answer = [s for s in (gate.text(x, "the daily answer", dollars=True).strip()
                              for x in template_sentences(d, dirn, btc, eth, cap, gain, lose)) if s]
        by = "template"
    pub = _et(src.get("published_utc"))
    stamp = stamp_line(slot, src.get("published_utc"), (snap or {}).get("stamp_utc"),
                       (snap or {}).get("stamp_et"), now, fallback=fallback)
    # a fallback page was written NOW, whatever the last Edition's own time: its dates are its own
    stamp_utc = (now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if fallback
                 else src.get("published_utc"))
    return {"date_et": d.isoformat(), "slot": slot, "published_utc": stamp_utc,
            "first_utc": first_utc or stamp_utc, "direction": dirn, "direction_basis": basis,
            "title": title, "h1": h1,
            "stamp_label": stamp,
            "composed_utc": now.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "board_stamp_et": (snap or {}).get("stamp_et") or "",
            "answer": answer, "answer_by": by, "fallback": fallback,
            "btc": btc, "eth": eth, "cap": cap, "gainers": gain, "losers": lose,
            "reported": wire_items(wire, d, gate), "board": board_rows(snap, pulse),
            "next": next_update(slot, now), "corrections": []}


# ---- records on disk: the freeze ------------------------------------------------------------

def _path(rec, directory=None):
    return os.path.join(directory or DIR, f"{rec['date_et']}-{rec['slot']}.json")


def write_record(rec, directory=None):
    p = _path(rec, directory)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1)
    return p


def load_records(directory=None):
    out = []
    d = directory or DIR
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}-(morning|evening)\.json", n):
                try:
                    out.append(json.load(open(os.path.join(d, n), encoding="utf-8")))
                except (OSError, ValueError):
                    pass
    return out


def pages(stored, live):
    """(living, dated) from the stored records and the one composed now. A stored record for
    a slot always wins over a composed one (that is the freeze). `dated` is {date: record}: the
    day's evening record when it exists, else its morning one. `living` is the newest."""
    by = {(r["date_et"], r["slot"]): r for r in stored}
    if live and (live["date_et"], live["slot"]) not in by:
        by[(live["date_et"], live["slot"])] = live
    dated = {}
    for (day, slot), r in by.items():
        if day not in dated or slot == "evening":
            dated[day] = r
    living = max(by.values(), key=lambda r: (r["date_et"], r["slot"] == "evening"), default=None)
    return living, dated


# ---- the page ---------------------------------------------------------------------------------

def _e(s):
    import home
    return home._e(s)


def _chg(v):
    import home
    return home.change_html(v, "chg")


def _core(label, price_html, chg, window="24 hours"):
    return (f'<li class="td-row"><span class="td-n">{_e(label)}</span>'
            f'<span class="td-p">{price_html}</span>{_chg(chg)}'
            f'<span class="td-w">{_e(window)}</span></li>')


def _board_html(r):
    import site_build as sb
    k = r["key"]
    if k == "etf":
        v = r["value"]
        fig = (f"{'+' if v > 0 else '-' if v < 0 else ''}{sb.fmt_usd(abs(v) * 1e6)}" if v else "flat")
        cls = " up" if v > 0 else " down" if v < 0 else ""
        fig_html = f'<span class="td-f{cls}">{_e(fig)}</span>'
    elif k == "liq":
        fig_html = (f'<span class="td-f">{_e(sb.fmt_usd(r["longs"]))} longs, '
                    f'{_e(sb.fmt_usd(r["shorts"]))} shorts</span>')
    elif k == "funding":
        fig_html = f'<span class="td-f">{r["value"]:+.4f}%</span>'
    else:
        fig_html = f'<span class="td-f">{r["value"]:g}</span> <span class="td-w">{_e(r.get("word"))}</span>'
    return (f'<li class="td-row"><span class="td-n">{_e(r["label"])}</span>{fig_html}'
            f'<span class="td-w">{_e(r["window"])} &middot; {_e(r["source"])} &middot; {_e(r["stamp"])}</span></li>')


def iso_et(utc):
    t = _et(utc)
    return t.isoformat() if t else ""


def schema(rec, url):
    import site_build as sb
    return json.dumps({"@context": "https://schema.org", "@graph": [{
        "@type": "NewsArticle", "headline": rec["h1"], "url": url, "mainEntityOfPage": url,
        "description": " ".join(rec["answer"])[:300],
        "datePublished": iso_et(rec.get("first_utc") or rec.get("published_utc")),
        "dateModified": iso_et(rec.get("published_utc")),
        "author": {"@type": "Organization", "name": sb.NAME, "url": sb.ORIGIN + "/news.html"},
        "publisher": {"@type": "Organization", "@id": sb.ORIGIN + "/#publisher", "name": sb.FAMILY,
                      "url": sb.ORIGIN + "/",
                      "logo": {"@type": "ImageObject", "url": sb.ORIGIN + "/publisher-logo-512.png",
                               "width": 512, "height": 512}}}]}, ensure_ascii=False)


def body_html(rec, archive_dates, here=None, evidence=None):
    """The page, top to bottom: the answer, what moved, what lined up with the move (Sprint 9.2,
    when the day's slot has an evidence record), what was reported beside it, the Board, the
    stamp, the archive. A wire item the evidence lists is not listed again under "reported"."""
    import site_build as sb
    import home
    btc, eth, cap = rec["btc"], rec.get("eth"), rec.get("cap")
    if btc.get("chg_day") is not None:
        core = [_core("Bitcoin", _e(home._whole(btc["price"])), btc["chg_day"], "since midnight ET")]
        if isinstance(btc.get("chg"), (int, float)):
            core.append(_core("Bitcoin", "", btc["chg"], "last 24 hours"))
    else:
        core = [_core("Bitcoin", _e(home._whole(btc["price"])), btc["chg"])]
    if eth:
        core.append(_core("Ether", _e(home._whole(eth["price"])) if eth.get("price") else "", eth["chg"]))
    if cap:
        core.append(_core("Whole market", _e(sb.fmt_usd(cap["usd"])), cap["chg"]))

    def lst(rows):
        return "".join(
            f'<li class="td-row"><span class="td-n"><a href="/coins/{_e(r.get("slug") or str(r["symbol"]).lower())}">'
            f'{_e(r["symbol"])}</a> <span class="td-w">{_e(r.get("name") or "")}</span></span>'
            f'{_chg(r["chg"])}<span class="td-w">24 hours</span></li>' for r in rows)
    gain, lose = rec.get("gainers") or [], rec.get("losers") or []
    moved = (f'<ul class="td-list">{"".join(core)}</ul>'
             + (f'<h3 class="td-h3">Biggest gains in the Top 100</h3><ul class="td-list">{lst(gain)}</ul>' if gain else "")
             + (f'<h3 class="td-h3">Biggest losses in the Top 100</h3><ul class="td-list">{lst(lose)}</ul>' if lose else ""))
    ev_html, shown = "", set()
    if evidence:
        try:
            import why_evidence
            ev_html = why_evidence.section_html(evidence, "BTC", live=(here != "dated"),
                                                corrections=rec.get("corrections"))
            shown = why_evidence.wire_urls_shown(evidence) if ev_html else set()
        except Exception as e:                      # fail open: the page as it was
            print(f"::warning::today: the evidence was not drawn ({type(e).__name__}: {e})")
            ev_html, shown = "", set()
    reported_all = rec.get("reported") or []
    reported_left = [w for w in reported_all if not ({l.get("url") for l in w.get("links") or []} & shown)]
    rep = ""
    for w in reported_left:
        names = ", ".join(f'<a href="{_e(l["url"])}" rel="noopener">{_e(l["outlet"])}</a>' for l in w["links"])
        n = w["source_count"]
        rep += (f'<li class="td-rep"><span class="td-line">{_e(w["line"])}</span>'
                f'<span class="td-w">{_e(w["time"])} &middot; {n} source{"" if n == 1 else "s"}'
                f'{" &middot; Primary source" if w["primary"] else ""}'
                f'{(" &middot; " + names) if names else ""}</span></li>')
    reported = (f'<ol class="td-reps">{rep}</ol>' if rep else
                '<p class="td-w">No wire item reported today has cleared the desk yet.</p>')
    reported_sec = (f'<section class="td-sec"><h2>What was reported beside it</h2>{reported}\n'
                    f'    <p class="td-w">These are separate reports. The desk does not say one caused the other.</p></section>'
                    if (rep or len(reported_left) == len(reported_all)) else "")
    board = "".join(_board_html(r) for r in rec.get("board") or [])
    arch = "".join(f'<li><a href="/today/{d}">{_e(long_date(_dt.date.fromisoformat(d)))}</a></li>'
                   for d in archive_dates)
    corr = "".join(f'<p class="td-corr"><b>Correction, {_e(c.get("date"))}.</b> {_e(c.get("text"))}</p>'
                   for c in rec.get("corrections") or [])
    ans = " ".join(rec["answer"])
    return f"""<main class="wrap"><section class="page td-page">
  <span class="kicker">Today</span>
  <h1>{_e(rec['h1'])}</h1>
  <p class="td-stamp">{_e(rec['stamp_label'])}</p>
  <section class="td-answer" aria-label="The answer"><p>{_e(ans)}</p></section>
  {corr}
  <section class="td-sec"><h2>What moved</h2>{moved}</section>
  {ev_html}
  {reported_sec}
  <section class="td-sec"><h2>The Board</h2><ul class="td-list">{board}</ul></section>
  <p class="td-next">{_e(rec['next'])}</p>
  {'<p class="td-w">This is the record of its day. The latest answer is at <a href="/today/">/today/</a>.</p>' if here == "dated" else ''}
  {f'<section class="td-sec td-arch"><h2>Earlier days</h2><ul>{arch}</ul></section>' if arch else ''}
</section></main>"""


def render(rec, archive_dates, dated, dateline="", evidence=None):
    """(html, path, lastmod) for one page; `dated` False renders the living /today/."""
    import site_build as sb
    path = f"/today/{rec['date_et']}.html" if dated else "/today/"
    url = sb.ORIGIN + (f"/today/{rec['date_et']}" if dated else "/today/")
    desc = " ".join(rec["answer"])[:200]
    html = sb.shell(f"{rec['title']} - {sb.NAME}", desc, "Today", body_html(rec, archive_dates, "dated" if dated else "living", evidence), dateline,
                    path=path, og_type="article",
                    schema_extra=f'\n<script type="application/ld+json">{schema(rec, url)}</script>')
    return html, path, rec.get("published_utc")


def _evidence(rec, why_dir=None):
    """The stored evidence record (why_evidence.py) for the record's day and slot, or None. Never
    raises: a page with no evidence is the page as it was before Sprint 9.2."""
    try:
        import why_evidence
        return why_evidence.load(rec["date_et"], rec["slot"], why_dir)
    except Exception:                               # noqa: BLE001
        return None


def build_pages(snap, pulse, wire, ed, morning, now, gate, stored=None, dateline="", why_dir=None):
    """[(relative file, html, sitemap path, lastmod)] for the living page and every dated one."""
    stored = load_records() if stored is None else stored
    first = None
    live = compose(snap, pulse, wire, ed, morning, now, gate)
    if live:
        same = [r for r in stored if r["date_et"] == live["date_et"] and r["slot"] == "morning"]
        if same and live["slot"] == "evening":
            live["first_utc"] = same[0].get("first_utc") or same[0].get("published_utc")
    living, dated = pages(stored, live)
    out = []
    if not living:
        return out
    days = sorted(dated, reverse=True)
    # today's own dated page is not an "earlier day": the living page lists only the days before it
    html, path, mod = render(living, [d for d in days if d < living["date_et"]][:ARCHIVE_N],
                             dated=False, dateline=dateline, evidence=_evidence(living, why_dir))
    out.append(("today/index.html", html, path, mod))
    for day in days:
        # a dated page links only the days BEFORE it, so nothing a later day adds can change it
        rest = [x for x in days if x < day][:ARCHIVE_N]
        html, path, mod = render(dated[day], rest, dated=True, dateline=dateline,
                                 evidence=_evidence(dated[day], why_dir))
        out.append((f"today/{day}.html", html, path, mod))
    return out


def main():
    """python3 today.py --write: compose this slot's record from the files in hand and store it.
    Exits 0 whatever happens (the workflows call it as an extra step, never a gate)."""
    if "--write" not in sys.argv[1:]:
        print("usage: python3 today.py --write")
        return 2
    try:
        import home
        import site_build as sb
        import snapshot as _s
        import twins_gate
        pulse, flows = sb.load_pulse(), sb.load_flows()
        snap = _s.build(pulse, flows)
        pulse, flows = _s.views(snap, pulse, flows)
        now = _dt.datetime.now(_dt.timezone.utc)
        items = sb.load_content()
        gate = twins_gate.Gate(snap)
        rec = compose(snap, pulse, home.load_json(sb.WIRE_JSON), sb.current_bottom_line(items),
                      home.load_json(sb.MORNING_JSON), now, gate)
        gate.save()
        if not rec:
            print("today: no slot read today or no Bitcoin reading; no record written")
            return 0
        have = os.path.join(DIR, f"{rec['date_et']}-{rec['slot']}.json")
        if os.path.exists(have):
            try:
                was_fallback = bool(json.load(open(have, encoding="utf-8")).get("fallback"))
            except (OSError, ValueError):
                was_fallback = False
            # a numbers-only page is a stand-in: the slot's own read replaces it, once
            if not (was_fallback and not rec.get("fallback")):
                print(f"today: {os.path.basename(have)} already stored; a stored record is frozen")
                return 0
            print(f"today: {os.path.basename(have)} was a numbers-only stand-in; the slot's own read replaces it")
        print(f"today: wrote {write_record(rec)} ({rec['direction']}, {rec['answer_by']})")
    except Exception as e:                           # never a gate on a slot
        print(f"::warning::today: no record written ({type(e).__name__}: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
