#!/usr/bin/env python3
"""
verdict_record.py: the verdict record (Program 9, Sprint 9.8; AUDIT.md section 3.6, row 9.8).

A public page, /verdict-record.html, scoring the desk's own grades after the fact: how many Likely verdicts a later primary source
confirmed, and how many it reversed, with the record accumulating from 9.3's first stored verdict on.

IT COUNTS ONLY WHAT IS STORED. Two stores, nothing else:
  the verdicts     every graded verdict the desk printed: site/data/verdict/<date>-<slot>.json (Bitcoin and Ether, 9.3)
                   and site/data/movers/<date>-<slot>.json (Big movers, 9.4). One verdict per /why/ address, the one its page
                   shows (the day's newest graded record), so the record scores exactly what a reader could read. A verdict
                   withheld at the cap printed no grade and is not on the record.
  the later sources  site/data/verdict-record.json, a list. Each names the verdict's /why/ address, the source, its link, the
                   moment it was published, whether it is a primary source, and its finding: "confirms" (it states the cause
                   the verdict named) or "reverses" (it states a different cause, or shows the named event could not be it).

A LATER SOURCE COUNTS only when it is primary, links somewhere a reader can open, was published after the verdict was made,
names a stored graded verdict, and carries one of the two findings; anything else is counted nowhere and named in the build log
(and refused at --add). A verdict any counted source reverses is reversed, even when another confirms it: the record scores
against the desk, never for it. A verdict with no counted source is open ("not yet revisited").

NO MODEL CALL, no fetch. The page is built from the two stores by site_build.py; the figures are stamped with the newest
record they come from, never the build clock, so a stale count never reads as live.

    python3 verdict_record.py                       # print the tally of the stored records
    python3 verdict_record.py --add '<json entry>'  # store one later source after checking it can count
"""
import datetime as _dt
import html as _html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "site", "data", "verdict-record.json")
PATH = "/verdict-record.html"
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")
FINDINGS = ("confirms", "reverses")
# ONE NAME PER COUNT (review 1): the headline, the table, the rows and each verdict page's line use these words and no others
STATUS_WORDS = {"confirmed": "Confirmed later",
                "reversed": "Reversed later",
                "open": "Not yet revisited"}
DASH = re.compile("[\\u2013\\u2014]")
BECAUSE = re.compile(r"\bbecause\b", re.I)


def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def _parse(s):
    try:
        t = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=_dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def _vd():
    import verdict
    return verdict


def _mv():
    import movers
    return movers


# ---- the verdicts ----------------------------------------------------------------------------------------------------

def graded(vdir=None, mdir=None):
    """Every graded verdict stored, one per /why/ address (the one its page shows), oldest first:
    [{url, day, slot, sym, name, grade, made_utc, kind}]. kind is "coin" for Bitcoin and Ether, "mover" for Big movers."""
    vd = _vd()
    out = {}
    by_day = {}
    for n in vd._names(vdir):
        r = vd.load(n[:10], n[11:-5], vdir)
        if r:
            by_day.setdefault(n[:10], []).append(r)
    for day, recs in by_day.items():
        # the page's lead: the evening record first (verdict.build_pages)
        recs.sort(key=lambda r: r.get("slot") == "evening", reverse=True)
        for sym in ("BTC", "ETH"):
            g = [r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade")]
            if not g:
                continue
            v = g[0]["coins"][sym]
            if v.get("grade") not in GRADES:
                continue
            u = vd.url(day, sym)
            out[u] = {"url": u, "day": day, "slot": g[0].get("slot"), "sym": sym, "name": v.get("name") or vd.NAMES[sym][0],
                      "grade": v["grade"], "made_utc": g[0].get("made_utc"), "kind": "coin"}
    try:
        mv = _mv()
        by = {}
        for r in mv.records(mdir):
            for sym, e in (r.get("coins") or {}).items():
                v = (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {})
                if v.get("grade") in GRADES and e.get("evidence"):
                    by.setdefault((r.get("date_et"), e.get("gecko_id") or sym.lower()), []).append((r, sym, e, v))
        for (day, cid), items in by.items():
            # the page's lead: the newest window, then the newest record (movers.build_pages)
            items.sort(key=lambda t: ((t[0].get("window") or {}).get("end_utc") or "", t[0].get("made_utc") or ""),
                       reverse=True)
            r, sym, e, v = items[0]
            u = f"/why/{day}-{cid}"
            if u in out:                                   # the coin's own page wins, as the build does
                continue
            out[u] = {"url": u, "day": day, "slot": r.get("slot"), "sym": sym, "name": e.get("name") or sym,
                      "grade": v["grade"], "made_utc": (e.get("verdict") or {}).get("made_utc") or r.get("made_utc"),
                      "kind": "mover"}
    except Exception as ex:                                # noqa: BLE001  fail open: the coin verdicts stand
        print(f"::warning::verdict record: the Big movers' verdicts were not read ({type(ex).__name__}: {ex})")
    return sorted(out.values(), key=lambda v: (v["day"], v["url"]))


def first_day(vdir=None, mdir=None):
    """The ET date of the first stored verdict record of any kind, graded or not: where the record starts. None when none."""
    days = [n[:10] for n in _vd()._names(vdir)]
    try:
        days += [n[:10] for n in _mv().names(mdir)]
    except Exception:                                      # noqa: BLE001
        pass
    return min(days) if days else None


# ---- the later sources -----------------------------------------------------------------------------------------------

def load_later(path=None):
    try:
        d = json.load(open(path or STORE, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = d.get("later") if isinstance(d, dict) else d
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def problems(entry, by_url):
    """Why a later source cannot count; [] when it can."""
    why = []
    v = by_url.get(str(entry.get("verdict") or ""))
    if v is None:
        why.append(f"no stored graded verdict at {entry.get('verdict')!r}")
    if entry.get("primary") is not True:
        why.append("not a primary source")
    if entry.get("finding") not in FINDINGS:
        why.append(f"finding {entry.get('finding')!r} is neither confirms nor reverses")
    if not re.match(r"^https?://\S+$", str(entry.get("url") or "")):
        why.append("no link a reader can open")
    if not str(entry.get("source") or "").strip():
        why.append("the source is not named")
    pub = _parse(entry.get("published_utc"))
    if pub is None:
        why.append("no published time")
    elif v is not None:
        made = _parse(v.get("made_utc"))
        if made is None or pub <= made:
            why.append("published before the verdict was made, so it is not a later source")
    for k in ("source", "says"):
        s = str(entry.get(k) or "")
        if DASH.search(s):
            why.append(f"{k} carries a dash")
        if BECAUSE.search(s):
            why.append(f"{k} says 'because'")
    return why


def tally(verdicts, later, first=None):
    """The record: {by_grade: {grade: {graded, confirmed, reversed, open}}, total, rows (newest first), ignored, first, through}."""
    by_url = {v["url"]: v for v in verdicts}
    counted, ignored = {}, []
    for e in later or []:
        why = problems(e, by_url)
        if why:
            ignored.append({"entry": e, "why": why})
        else:
            counted.setdefault(e["verdict"], []).append(e)
    rows = []
    for v in verdicts:
        srcs = sorted(counted.get(v["url"], []), key=lambda e: e.get("published_utc") or "")
        rev = [e for e in srcs if e["finding"] == "reverses"]
        con = [e for e in srcs if e["finding"] == "confirms"]
        status = "reversed" if rev else "confirmed" if con else "open"
        rows.append(dict(v, status=status, source=(rev or con or [None])[0], sources=srcs))
    by_grade = {g: {"graded": 0, "confirmed": 0, "reversed": 0, "open": 0} for g in GRADES}
    for r in rows:
        by_grade[r["grade"]]["graded"] += 1
        by_grade[r["grade"]][r["status"]] += 1
    total = {k: sum(b[k] for b in by_grade.values()) for k in ("graded", "confirmed", "reversed", "open")}
    rows.sort(key=lambda r: (r["day"], r["url"]), reverse=True)
    made = [v.get("made_utc") for v in verdicts if v.get("made_utc")]
    pubs = [e.get("published_utc") for es in counted.values() for e in es]
    return {"by_grade": by_grade, "total": total, "rows": rows, "ignored": ignored, "first": first,
            "through": max(made + pubs) if (made or pubs) else None}


def add_later(entry, path=None, vdir=None, mdir=None, now=None):
    """Store one later source when it can count. Returns (stored, reasons)."""
    entry = dict(entry)
    entry.setdefault("recorded_utc", (now or _dt.datetime.now(_dt.timezone.utc)).astimezone(_dt.timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ"))
    why = problems(entry, {v["url"]: v for v in graded(vdir, mdir)})
    if why:
        return False, why
    p = path or STORE
    try:
        d = json.load(open(p, encoding="utf-8"))
        if not isinstance(d, dict):
            d = {"later": d if isinstance(d, list) else []}
    except (OSError, ValueError):
        d = {}
    d.setdefault("what", WHAT)
    d.setdefault("later", [])
    d["later"].append(entry)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
        f.write("\n")
    return True, []


WHAT = ("The later sources the verdict record scores the desk's graded verdicts against (verdict_record.py). One entry per "
        "source: verdict (its /why/ address), source (the name), url, published_utc, primary (true), finding (confirms or "
        "reverses), says (one line of what it states), recorded_utc. Add with python3 verdict_record.py --add.")


# ---- the page -----------------------------------------------------------------------------------------------------------

STYLE = """<style>
.vr-page .vr-n{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:18px 0;padding:0;list-style:none}
.vr-page .vr-n li{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:12px 14px}
.vr-page .vr-n b{display:block;font:700 28px/1.1 var(--mono);color:var(--ink)}
.vr-page .vr-n span{display:block;font:13px/1.35 var(--sans);color:var(--muted);margin-top:4px}
.vr-page .vr-tw{overflow-x:auto;margin:12px 0 18px}
.vr-page table.vr-t{border-collapse:collapse;width:100%;font:14px/1.4 var(--sans)}
.vr-page .vr-t th,.vr-page .vr-t td{border-bottom:1px solid var(--line);padding:8px 4px;text-align:right;color:var(--ink)}
@media (max-width:520px){.vr-page table.vr-t{font-size:13px}.vr-page .vr-t thead th{font-size:10.5px;letter-spacing:0}}
.vr-page .vr-t th:first-child,.vr-page .vr-t td:first-child{text-align:left}
.vr-page .vr-t thead th{font:600 12px/1.3 var(--mono);color:var(--muted)}
.vr-page ol.vr-l{list-style:none;margin:12px 0;padding:0}
.vr-page .vr-l li{border-bottom:1px solid var(--line);padding:10px 0}
.vr-page .vr-l p{margin:0 0 4px}
.vr-page .vr-s{font:12px/1.4 var(--mono);color:var(--muted)}
</style>"""


def _day(iso):
    d = _dt.date.fromisoformat(iso)
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def _et(utc):
    t = _parse(utc)
    if t is None:
        return ""
    import why_evidence as we
    e = t.astimezone(we.ET)
    return f"{e.strftime('%B')} {e.day}, {e.year}, {e.strftime('%-I:%M %p')} ET"


def _row(r):
    lead = (f'<p><a href="{_e(r["url"])}">Why {_e(r["name"])} moved, {_e(_day(r["day"]))}</a></p>'
            f'<p class="vr-s">Graded {_e(r["grade"])}. {_e(STATUS_WORDS[r["status"]])}.</p>')
    for e in r.get("sources") or []:
        word = "Reversed later by" if e["finding"] == "reverses" else "Confirmed later by"
        says = str(e.get("says") or "").strip()
        lead += (f'<p class="vr-s">{word} <a href="{_e(e["url"])}" rel="noopener">{_e(e["source"])}</a>, published '
                 f'{_e(_et(e["published_utc"]))}.{(" " + _e(says)) if says else ""}</p>')
    return f'<li class="vr-r vr-{_e(r["status"])}">{lead}</li>'


def standing(url, made_utc, later=None):
    """How one verdict stands on the record, by the record's own rules: (status, the counted source or None)."""
    v = {"url": url, "made_utc": made_utc}
    t = tally([v | {"day": "", "grade": "Likely"}], load_later() if later is None else later)
    r = t["rows"][0]
    return r["status"], r["source"]


def standing_html(url, made_utc, later=None):
    """The line a verdict's own /why/ page prints under its card (review 1): its standing on the record, linked. Fails open
    to no line, never to a claim."""
    try:
        st, e = standing(url, made_utc, later)
    except Exception as ex:                                # noqa: BLE001
        print(f"::warning::verdict record: no standing line for {url} ({type(ex).__name__}: {ex})")
        return ""
    if st == "open":
        said = ("Not yet revisited: no primary source published after this verdict has been recorded against it.")
    else:
        said = (f'{"Reversed later by" if st == "reversed" else "Confirmed later by"} '
                f'<a href="{_e(e["url"])}" rel="noopener">{_e(e["source"])}</a>, published {_e(_et(e["published_utc"]))}.')
    return (f'<p class="td-w vr-standing">{said if st != "open" else _e(said)} How the desk\'s verdicts hold up is counted on '
            f'<a href="{_e(PATH)}">the verdict record</a>.</p>')


def page_body(t):
    lk = t["by_grade"]["Likely"]
    tot = t["total"]
    first = (f" It counts every verdict stored from {_e(_day(t['first']))} on." if t.get("first") else "")
    through = (f'<p class="vr-s">Counted from the stored records, the newest made {_e(_et(t["through"]))}.</p>'
               if t.get("through") else "")
    nums = "".join(f"<li><b>{n}</b><span>{_e(w)}</span></li>" for n, w in (
        (lk["graded"], "Likely verdicts"), (lk["confirmed"], "confirmed later"),
        (lk["reversed"], "reversed later"), (lk["open"], "not yet revisited")))
    if not tot["graded"]:
        state = ("<p>No graded verdict is stored yet, so there is nothing to score. Every verdict the desk grades joins "
                 "this record as it is made, and stays on it.</p>")
    elif not (tot["confirmed"] or tot["reversed"]):
        state = (f"<p>No verdict has been revisited yet. {tot['graded']} graded verdict{'s are' if tot['graded'] != 1 else ' is'} "
                 "on the record, each waiting for a primary source published after it.</p>")
    else:
        state = ""
    trs = "".join(f'<tr><td>{_e(g)}</td><td>{b["graded"]}</td><td>{b["confirmed"]}</td><td>{b["reversed"]}</td>'
                  f'<td>{b["open"]}</td></tr>' for g, b in t["by_grade"].items())
    trs += (f'<tr><td>All grades</td><td>{tot["graded"]}</td><td>{tot["confirmed"]}</td><td>{tot["reversed"]}</td>'
            f'<td>{tot["open"]}</td></tr>')
    table = (f'<div class="vr-tw"><table class="vr-t"><thead><tr><th scope="col">Grade</th><th scope="col">Graded</th>'
             f'<th scope="col">Confirmed later</th><th scope="col">Reversed later</th><th scope="col">Not yet revisited</th></tr></thead>'
             f'<tbody>{trs}</tbody></table></div>')
    listing = (f'<h2>Every graded verdict, newest first</h2><ol class="vr-l">{"".join(_row(r) for r in t["rows"])}</ol>'
               if t["rows"] else "")
    return f"""<main class="wrap narrow"><section class="page vr-page">{STYLE}
  <span class="kicker">Why it moved</span>
  <h1>The verdict record</h1>
  <p class="lede">How the desk's own grades held up after the fact: how many Likely verdicts were confirmed later, and how
     many were reversed later. A verdict is confirmed later when a primary source published after it states the cause and
     names what the verdict named; it is reversed later when such a source names a different cause, or shows that what the
     verdict named could not have moved the price.{first}</p>
  <ul class="vr-n">{nums}</ul>
  {through}
  {state}
  <h2>By grade</h2>
  <p>A verdict any later primary source reverses is counted reversed, even when another source confirms it. A source that is
     not primary, or that was published before the verdict, is not counted. The four grades are defined on
     <a href="/method.html">how we check</a>.</p>
  {table}
  {listing}
</section></main>"""


def page_html(t, dateline):
    import site_build as sb
    desc = ("How GoCheckMyCrypto's Likely verdicts held up: how many a later primary source confirmed, and how many it "
            "reversed, counted from the stored records.")
    return sb.shell(f"The verdict record - {sb.NAME}", desc, "Today", page_body(t), dateline, path=PATH)


def build(dateline, vdir=None, mdir=None, path=None):
    """(html, tally) for /verdict-record.html from the stores; prints the counts and every ignored later source."""
    vs = graded(vdir, mdir)
    t = tally(vs, load_later(path), first=first_day(vdir, mdir))
    for i in t["ignored"]:
        print(f"::warning::verdict record: a later source for {i['entry'].get('verdict')!r} is not counted "
              f"({'; '.join(i['why'])})")
    lk = t["by_grade"]["Likely"]
    print(f"verdict record: {t['total']['graded']} graded verdict(s); Likely {lk['graded']}: {lk['confirmed']} confirmed, "
          f"{lk['reversed']} reversed, {lk['open']} open")
    return page_html(t, dateline), t


def main():
    args = sys.argv[1:]
    if args[:1] == ["--add"] and len(args) == 2:
        ok, why = add_later(json.loads(args[1]))
        print("verdict record: stored" if ok else "verdict record: refused (" + "; ".join(why) + ")")
        return 0 if ok else 1
    t = tally(graded(), load_later(), first=first_day())
    print(json.dumps({"by_grade": t["by_grade"], "total": t["total"], "first": t["first"], "through": t["through"],
                      "ignored": t["ignored"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
