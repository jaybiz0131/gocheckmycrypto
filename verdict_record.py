#!/usr/bin/env python3
"""
verdict_record.py: the verdict record, /why/record/ (Program 9, Sprint 9.8; AUDIT.md section 3.6, row 9.8).

The desk's own grades scored after the fact: how many Likely verdicts a later primary source confirmed, how many were
reversed, how many still await a later source, with Confirmed, Disputed and Unclear counted beside them as graded at the
time. From 9.3's first verdict record on. No model call, no request: everything here is read from stored records.

WHERE A VERDICT'S LATER FATE COMES FROM (what 9.3 to 9.5 store, read October 25, 2026):
  - Each slot's verdict record (site/data/verdict/<date>-<slot>.json, 9.3) and Big movers record (site/data/movers/, 9.4)
    holds the grade that slot gave. A later slot of the same ET day grades the same move again ("Verdict at the next read",
    J-8 b), and the /why/ page carries the day's newest graded verdict. That later read is the only stored place a verdict's
    later fate appears: a later read that grades the move Confirmed needs a primary source stating the cause (the grading
    rules of October 19 and 20; a listing never Confirms), so it is the later primary source the record counts.
  - Nothing stored the outcome itself: no file links a verdict to what became of it, and a slot's record can be rewritten
    (verdict.py rewrites a slot when a newer evidence record arrives; movers.py writes its slot whole). So the record starts
    storing it now, append-only: one frozen file per graded verdict and one per resolved Likely verdict, under
    site/data/verdict/record/, written once with exclusive create and never rewritten (the why records' rule). The run
    steps (verdict.py and movers.py --write) call sync(); the build reads the same stores and never writes.
  - Corrections (9.5) are free text on a story, a verdict or a day's answer. A correction is never read as an outcome here.

THE RULES (the same move is one coin on one ET day; a later day's read measures a different move):
  confirmed later  a later read of the same move graded it Confirmed on an event the Likely verdict named.
  reversed         a later read graded it Disputed or Unclear, or Confirmed or Likely on events the Likely verdict did not name.
  awaiting         no later read has graded the same move, or the later reads were Likely on the same events.
  An event is the same event when its candidate id is the same or one of its source articles is the same page (a wire
  cluster's id is renumbered between runs; an article address is not). A shared word is never an identity.
  Not graded, not counted: a move under the threshold, Ether moving with Bitcoin, a move held for the next read, a verdict
  withheld at the spend cap. A stored outcome is never recomputed: the first outcome stored for a verdict stands.
"""
import datetime as _dt
import html as _html
import json
import os
import re
import sys
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "site", "data", "verdict", "record")
URL = "/why/record/"
REL = "why/record/index.html"
FEED = "why/record"
GRADES = ("Confirmed", "Likely", "Disputed", "Unclear")
SLOT_WORDS = {"morning": "Morning Brief read", "evening": "Evening Brief read"}
OUTCOME_WORDS = {"confirmed_later": "Confirmed later", "reversed": "Reversed", "awaiting": "Awaiting a later source"}
KEY_RX = re.compile(r"[a-z0-9-]+")
# THE PAGE'S OWN RULES, inline in its head as Sprint 9.7 did for the coin heading (site_build.COIN_TITLE_STYLE): the shared
# stylesheets are held byte for byte to Sprint 9.5's outside the 9.5b block (scripts/sprint95b_test.py), and these rules reach
# only this page. The tally in the verdict card's frame, each count in the mono figures, the Likely outcomes edged like the
# corrections log (ink for confirmed later, the rule for reversed, dotted for awaiting); the grade badges keep the verdict
# card's shapes (solid Confirmed, half-filled Likely, dashed Disputed, dotted Unclear). Tokens only: no new font or color.
RECORD_STYLE = """<style>
.page .vr-tally{margin:20px 0 26px;padding:16px 18px 14px;background:var(--card);border:1px solid var(--line);border-radius:14px}
.page h2.vr-h{font:600 21px/1.25 var(--serif);letter-spacing:-.005em;color:var(--ink);margin:26px 0 8px;padding:0;border:0;
  text-transform:none}
.page .vr-tally h2.vr-h{margin:0 0 4px}
.page .vr-tally p{margin:0}
.page p.vr-win{font:12px/1.5 var(--mono);color:var(--muted);font-variant-numeric:tabular-nums;margin:0 0 12px}
.page p.vr-win.stale{color:var(--ink)}
.page p.vr-win .asof-age{color:var(--rule);font-weight:600}
.page .vr-tally p.vr-st{font:17px/1.5 var(--serif);color:var(--ink);margin:0 0 12px}
.page .vr-blk{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}
.page .vr-tally p.vr-bh{font:600 12px/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.page p.vr-bh .vr-n{font-size:13px;color:var(--ink);margin-left:6px;font-variant-numeric:tabular-nums}
.page .vr-g{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.page .vr-c{border:1px solid var(--line);border-radius:8px;padding:10px 10px 9px;min-width:0;overflow-wrap:anywhere}
.page .vr-c .vr-n{display:block;font:600 28px/1.1 var(--mono);color:var(--ink);font-variant-numeric:tabular-nums}
.page .vr-c .vr-lb{display:block;margin-top:5px;font:13px/1.35 var(--sans);color:var(--muted)}
.page .vr-c.vr-up{border-left:3px solid var(--ink)}
.page .vr-c.vr-dn{border-left:3px solid var(--rule)}
.page .vr-tally p.vr-rd{border-top:1px solid var(--line);margin-top:12px;padding-top:10px;font:12px/1.5 var(--mono);color:var(--muted)}
.page p.vr-rd .vr-n{color:var(--ink)}
.page ul.vr-def{margin:0 0 14px;padding-left:20px}
.page ul.vr-def li{margin:0 0 8px}
.page ol.vr-l{list-style:none;margin:12px 0 22px;padding:0}
.page li.vr-r{margin:0 0 12px;padding:12px 16px 13px;background:var(--card);border:1px solid var(--line);border-radius:8px}
.page li.vr-r p{margin:0}
.page li.vr-r p.vr-w{margin:0 0 4px;font:600 12px/1.5 var(--mono);color:var(--muted)}
.page li.vr-r p.vr-t{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;font:600 18px/1.35 var(--serif);color:var(--ink)}
.page p.vr-t a{color:var(--ink);text-underline-offset:3px}
.page li.vr-r p.vr-o{margin:8px 0 0;padding-left:10px;border-left:3px dotted var(--line);font:15px/1.5 var(--sans);color:var(--ink)}
.page li.vr-r p.vr-o-confirmed-later{border-left:3px solid var(--ink)}
.page li.vr-r p.vr-o-reversed{border-left:3px solid var(--rule)}
.page .vr-b{display:inline-flex;align-items:center;gap:7px;font:600 11.5px/1.2 var(--mono);letter-spacing:.08em;
  text-transform:uppercase;white-space:nowrap;padding:4px 10px 4px 9px;border-radius:3px;border:1.5px solid var(--ink);color:var(--ink)}
.page .vr-b::before{content:"";flex:none;width:8px;height:8px;border-radius:50%;box-sizing:border-box;border:1.5px solid currentColor}
.page .vr-b.vr-confirmed{background:var(--tag-bg)}
.page .vr-b.vr-confirmed::before{background:currentColor}
.page .vr-b.vr-likely::before{background:linear-gradient(90deg,currentColor 50%,transparent 50%)}
.page .vr-b.vr-disputed{background:var(--review-bg);color:var(--review-fg);border-color:var(--review-fg);border-style:dashed}
.page .vr-b.vr-unclear{background:var(--tag-bg);color:var(--tag-fg);border-color:var(--tag-fg);border-style:dotted}
.page .vr-b.vr-unclear::before{display:none}
.page p.vr-empty{margin:12px 0 22px;font:17px/1.55 var(--serif);color:var(--ink)}
@media (max-width:520px){.page .vr-tally{padding:14px 14px 12px}.page .vr-g{gap:6px}.page .vr-c{padding:8px 8px 7px}
  .page .vr-c .vr-n{font-size:24px}.page .vr-c .vr-lb{font-size:12.5px}}
</style>"""


def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def _vd():
    import verdict
    return verdict


def _mv():
    import movers
    return movers


def _parse(s):
    try:
        return _dt.datetime.strptime(str(s or "").strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _link(u):
    """An article address as an identity: host and path, lower-case host, no query, no fragment, no trailing slash."""
    try:
        p = urlsplit(str(u or "").strip())
    except ValueError:
        return ""
    if not p.netloc:
        return ""
    host = p.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return host + (p.path.rstrip("/") or "/")


def _slot_key(slot):
    return re.sub(r"[^a-z0-9-]+", "-", str(slot or "").lower()).strip("-")


def _key(day, slot, slug, made):
    m = _parse(made)
    return f"{day}-{_slot_key(slot)}-{slug}-{m.strftime('%H%M%S') if m else 'nomade'}"


# ---- the entries: every graded verdict in the stored slot records ------------------------------------------------------

def _evidence_links(ev, ids):
    out = []
    for c in (ev or {}).get("candidates") or []:
        if c.get("id") in ids:
            for ln in (c.get("links") or []) + (c.get("report_links") or []):
                k = _link((ln or {}).get("url"))
                if k and k not in out:
                    out.append(k)
    return sorted(out)


def _entry(rec, sym, v, slug, name, url, source, ev):
    events = sorted({r.get("id") for r in v.get("refs") or [] if r.get("id")}
                    | ({(v.get("cand") or {}).get("id")} if v.get("grade") == "Confirmed" and (v.get("cand") or {}).get("id")
                       else set()))
    made = rec.get("made_utc") or ""
    return {"key": _key(rec.get("date_et"), rec.get("slot"), slug, made), "date_et": rec.get("date_et"),
            "slot": rec.get("slot"), "made_utc": made, "coin_sym": sym, "coin_slug": slug, "coin_name": name,
            "grade": v.get("grade"), "events": events, "links": _evidence_links(ev, set(events)), "url": url,
            "source": source, "window_words": v.get("window_words"), "move_pct": v.get("move_pct"),
            "timing_rule_version": ((rec.get("timing_rule") or (ev or {}).get("timing_rule") or {}).get("version")),
            "corrected": bool(v.get("corrections"))}


def entries(vdir=None, mdir=None, wdir=None):
    """Every graded verdict the stored slot records hold, Bitcoin and Ether (verdict.py) and Big movers (movers.py), as
    entries. A coin with no grade (flat, with Bitcoin, the next read, withheld at the cap) is none."""
    vd, we = _vd(), None
    out = []
    for n in vd._names(vdir):
        rec = vd.load(n[:10], n[11:-5], vdir)
        if not rec:
            continue
        rec = dict(rec, date_et=rec.get("date_et") or n[:10], slot=rec.get("slot") or n[11:-5])
        ev = None
        for sym, v in (rec.get("coins") or {}).items():
            if v.get("grade") not in GRADES:
                continue
            if ev is None:
                try:
                    import why_evidence as we
                    ev = we.load(rec["date_et"], rec["slot"], wdir) or {}
                except Exception:                            # noqa: BLE001
                    ev = {}
            name, slug = vd.NAMES.get(sym, (v.get("name") or sym, sym.lower()))
            if sym in ("BTC", "ETH"):
                name, slug = {"BTC": ("Bitcoin", "bitcoin"), "ETH": ("Ether", "ether")}[sym]
            out.append(_entry(rec, sym, v, slug, name, f"/why/{rec['date_et']}-{slug}", "verdict", ev))
    mv = _mv()
    for rec in mv.records(mdir):
        for sym, e in (rec.get("coins") or {}).items():
            v = (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {})
            if v.get("grade") not in GRADES or not e.get("evidence"):
                continue                                     # movers.build_pages builds a page only with its evidence
            slug = e.get("gecko_id") or sym.lower()
            out.append(_entry(rec, sym, v, slug, e.get("name") or sym, f"/why/{rec.get('date_et')}-{slug}", "movers",
                              e.get("evidence")))
    return out


def dedupe(es):
    """One verdict per slot reading: the same slot and coin stored again with the same grade and the same events (a re-run
    that changed nothing) is not a second verdict. Keeps the first stored."""
    out, seen = [], set()
    for e in sorted(es, key=lambda e: (e.get("made_utc") or "", e["key"])):
        sig = (e.get("date_et"), _slot_key(e.get("slot")), e.get("coin_slug") or e.get("coin_sym"), e.get("grade"),
               tuple(sorted(e.get("events") or [])))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(e)
    return out


# ---- the outcomes ------------------------------------------------------------------------------------------------------

def _same_event(a, b):
    if set(a.get("events") or []) & set(b.get("events") or []):
        return True
    la = {_link(x) or x for x in a.get("links") or []}
    lb = {_link(x) or x for x in b.get("links") or []}
    return bool((la - {""}) & (lb - {""}))


def resolve(es):
    """{key: outcome} for every Likely entry a later read of the same move has resolved, by the rules in the module
    docstring. A Likely with no deciding later read is absent (awaiting)."""
    es = dedupe(es)
    by = {}
    for e in es:
        by.setdefault((e.get("date_et"), e.get("coin_slug") or e.get("coin_sym")), []).append(e)
    out = {}
    for group in by.values():
        group.sort(key=lambda e: (e.get("made_utc") or "", e["key"]))
        for i, e in enumerate(group):
            if e.get("grade") != "Likely":
                continue
            for later in group[i + 1:]:
                g = later.get("grade")
                same = _same_event(e, later)
                if g == "Likely" and same:
                    continue                                 # still Likely on the same events: no later source yet
                if g == "Confirmed" and same:
                    res, why = "confirmed_later", ("a later read of the same move graded it Confirmed on an event this "
                                                   "verdict named: a primary source states the cause")
                elif g in ("Disputed", "Unclear"):
                    res, why = "reversed", f"a later read of the same move graded it {g}"
                else:
                    res, why = "reversed", f"a later read of the same move graded it {g} on events this verdict did not name"
                out[e["key"]] = {"key": e["key"], "outcome": res, "basis": "later_read", "rule": why,
                                 "resolved_utc": later.get("made_utc"),
                                 "later": {"key": later["key"], "grade": g, "slot": later.get("slot"),
                                           "made_utc": later.get("made_utc"), "url": later.get("url")},
                                 "shared_events": sorted(set(e.get("events") or []) & set(later.get("events") or []))}
                break
    return out


# ---- the store: one frozen file per entry and per outcome --------------------------------------------------------------

def _safe(key):
    return bool(key) and KEY_RX.fullmatch(key) is not None


def _write_once(path, obj):
    """Exclusive create: a file that exists is never opened for writing. True when this call wrote it."""
    try:
        with open(path, "x", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        return True
    except FileExistsError:
        return False


def store_entry(store, entry):
    if not _safe(entry.get("key")):
        return None
    os.makedirs(store, exist_ok=True)
    p = os.path.join(store, entry["key"] + ".json")
    return p if _write_once(p, dict(entry, kind="verdict")) else None


def store_outcome(store, outcome):
    if not _safe(outcome.get("key")):
        return None
    os.makedirs(store, exist_ok=True)
    p = os.path.join(store, outcome["key"] + ".outcome.json")
    return p if _write_once(p, dict(outcome, kind="outcome")) else None


def load_store(store=None):
    """(entries, {key: outcome}) as stored. A file that cannot be read is skipped and said."""
    d = store or STORE
    es, outs = [], {}
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return es, outs
    for n in names:
        if not n.endswith(".json"):
            continue
        try:
            obj = json.load(open(os.path.join(d, n), encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"::warning::verdict record: {n} could not be read ({type(e).__name__})")
            continue
        if n.endswith(".outcome.json") and obj.get("kind") == "outcome" and obj.get("key"):
            outs.setdefault(obj["key"], obj)
        elif obj.get("kind") == "verdict" and obj.get("key") and obj.get("grade") in GRADES:
            es.append(obj)
    return es, outs


def merged(vdir=None, mdir=None, wdir=None, store=None):
    """(entries, outcomes, new_entries, new_outcomes): the stored ones first, then whatever the slot records hold that the
    store does not yet, and the outcomes of Likely entries not yet stored as resolved. Nothing stored is changed."""
    s_es, s_outs = load_store(store)
    have = {e["key"] for e in s_es}
    new_es = [e for e in entries(vdir, mdir, wdir) if e["key"] not in have]
    es = dedupe(s_es + new_es)
    keep = {e["key"] for e in es}
    new_es = [e for e in new_es if e["key"] in keep]
    computed = resolve(es)
    new_outs = {k: o for k, o in computed.items() if k not in s_outs}
    outs = dict(s_outs)
    outs.update(new_outs)
    return es, outs, new_es, new_outs


def sync(vdir=None, mdir=None, wdir=None, store=None, save=True):
    """The run step's store: every new graded verdict and every new outcome written once. Returns {entries, outcomes,
    written}. With save=False nothing is written."""
    es, outs, new_es, new_outs = merged(vdir, mdir, wdir, store)
    written = []
    if save:
        for e in new_es:
            p = store_entry(store or STORE, e)
            if p:
                written.append(p)
        for o in new_outs.values():
            p = store_outcome(store or STORE, o)
            if p:
                written.append(p)
    if written:
        print(f"verdict record: stored {len(written)} new file(s) under {store or STORE}")
    return {"entries": es, "outcomes": outs, "written": written}


# ---- the view: the tally, the window and the rows ----------------------------------------------------------------------

def reads(vdir=None, mdir=None):
    """The reads stored in the window: {coins, movers, first_utc, last_utc}. A read is one slot's record, graded or not."""
    vd = _vd()
    times, n_c, n_m = [], 0, 0
    for n in vd._names(vdir):
        r = vd.load(n[:10], n[11:-5], vdir)
        if r:
            n_c += 1
            if _parse(r.get("made_utc")):
                times.append(r["made_utc"])
    for r in _mv().records(mdir):
        n_m += 1
        if _parse(r.get("made_utc")):
            times.append(r["made_utc"])
    return {"coins": n_c, "movers": n_m, "first_utc": min(times) if times else None, "last_utc": max(times) if times else None}


def view(now, vdir=None, mdir=None, wdir=None, store=None, built=None):
    """Everything the page and the feed print, from stored records only. `built`: the /why/ addresses this build wrote (None:
    every row links). Never writes."""
    import snapshot
    es, outs, _n, _o = merged(vdir, mdir, wdir, store)
    rd = reads(vdir, mdir)
    times = [t for t in [rd["first_utc"], rd["last_utc"]] + [e.get("made_utc") for e in es] if _parse(t)]
    begins = min(times) if times else None
    through = max(times) if times else None
    counts = {"likely": 0, "likely_confirmed_later": 0, "likely_reversed": 0, "likely_awaiting": 0,
              "confirmed": 0, "disputed": 0, "unclear": 0}
    rows = []
    for e in sorted(es, key=lambda e: (e.get("made_utc") or "", e["key"]), reverse=True):
        g = e["grade"]
        outcome, detail = None, None
        if g == "Likely":
            counts["likely"] += 1
            o = outs.get(e["key"])
            if o and o.get("outcome") in ("confirmed_later", "reversed"):
                outcome = o["outcome"]
                lt = o.get("later") or {}
                detail = {"later_grade": lt.get("grade"), "later_slot": lt.get("slot"), "later_made_utc": lt.get("made_utc"),
                          "later_url": lt.get("url"), "rule": o.get("rule"), "basis": o.get("basis")}
            else:
                outcome = "awaiting"
            counts["likely_" + outcome] += 1
        else:
            counts[g.lower()] += 1
        rows.append({"key": e["key"], "date_et": e.get("date_et"), "slot": e.get("slot"), "made_utc": e.get("made_utc"),
                     "coin_sym": e.get("coin_sym"), "coin_name": e.get("coin_name"), "grade": g, "url": e.get("url"),
                     "linked": built is None or e.get("url") in built, "outcome": outcome, "outcome_detail": detail,
                     "source": e.get("source"), "timing_rule_version": e.get("timing_rule_version"),
                     "corrected": bool(e.get("corrected"))})
    stale = snapshot.is_stale(through, now) if through else None
    return {"begins_utc": begins, "through_utc": through, "stale": stale,
            "age": snapshot.age_phrase(through, now) if through else "",
            "reads": {"coins": rd["coins"], "movers": rd["movers"]}, "counts": counts, "rows": rows,
            "graded": len(rows)}


# ---- the page ----------------------------------------------------------------------------------------------------------

def _we():
    import why_evidence
    return why_evidence


def _when(utc):
    """'7:16 PM ET on Oct 19, 2026' from a UTC stamp."""
    t = _parse(utc)
    if not t:
        return ""
    we = _we()
    e = t.astimezone(we.ET)
    return f"{we.clock(int(t.timestamp()))} on {e.strftime('%b')} {e.day}, {e.year}"


def _day(day):
    try:
        d = _dt.date.fromisoformat(str(day))
    except ValueError:
        return str(day or "")
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _slot_words(slot):
    return SLOT_WORDS.get(slot) or ("Breaking read" if str(slot or "").startswith("breaking") else "Read")


def _n(key, val):
    return f'<b class="vr-n" data-rc="{key}">{int(val)}</b>'


def _tally(v):
    c, rd = v["counts"], v["reads"]
    if v["begins_utc"]:
        stamp = (f'Counted from the first verdict record, {_e(_when(v["begins_utc"]))}, through the newest read, '
                 f'{_e(_when(v["through_utc"]))}.')
        import snapshot
        cls = "vr-win stale" if v["stale"] else "vr-win"
        age = f'<span class="asof-age"> · {_e(v["age"])}</span>' if v["stale"] and v["age"] else ""
        win = f'<p class="{cls}"{snapshot.asof_attr(v["through_utc"])}>{stamp}{age}</p>'
    else:
        win = '<p class="vr-win">No verdict record is stored yet, so there is no window to count.</p>'
    if not v["graded"] and v["begins_utc"]:
        status = '<p class="vr-st">No move has been graded since the record began.</p>'
    elif c["likely"] and not (c["likely_confirmed_later"] or c["likely_reversed"]):
        status = '<p class="vr-st">No Likely verdict has a later source yet.</p>'
    else:
        status = ""
    cell = lambda key, label, cls="": (f'<div class="vr-c{(" " + cls) if cls else ""}">{_n(key, c[key])}'
                                      f'<span class="vr-lb">{_e(label)}</span></div>')
    return (f'<section class="vr-tally" aria-labelledby="vr-th">'
            f'<h2 id="vr-th" class="vr-h">The tally</h2>{win}{status}'
            f'<div class="vr-blk"><p class="vr-bh">Likely verdicts {_n("likely", c["likely"])}</p>'
            f'<div class="vr-g">{cell("likely_confirmed_later", "Confirmed later by a primary source", "vr-up")}'
            f'{cell("likely_reversed", "Reversed by a later read", "vr-dn")}'
            f'{cell("likely_awaiting", "Still awaiting a later source")}</div></div>'
            f'<div class="vr-blk"><p class="vr-bh">The other grades, as given at the time</p>'
            f'<div class="vr-g">{cell("confirmed", "Confirmed")}{cell("disputed", "Disputed")}{cell("unclear", "Unclear")}</div></div>'
            f'<p class="vr-rd">Reads in this window: {_n("reads_coins", rd["coins"])} of Bitcoin and Ether, '
            f'{_n("reads_movers", rd["movers"])} of Big movers.</p>'
            f'</section>')


def _row(r):
    title = f'Why {r["coin_name"]} moved, {_day(r["date_et"])}'
    head = (f'<a href="{_e(r["url"])}">{_e(title)}</a>' if r["linked"] else
            f'<span class="vr-nl">{_e(title)}</span>')
    meta = f'{_e(_slot_words(r["slot"]))}, {_e(_when(r["made_utc"]))}'
    g = r["grade"]
    badge = f'<span class="vr-b vr-{g.lower()}">{_e(g)}</span>'
    out = ""
    if r["outcome"]:
        word = OUTCOME_WORDS[r["outcome"]]
        d = r.get("outcome_detail") or {}
        if r["outcome"] == "awaiting":
            why = "No later read of the same move has resolved it."
        else:
            why = (f'The {_slot_words(d.get("later_slot"))} graded the same move {d.get("later_grade")}, '
                   f'{_when(d.get("later_made_utc"))}.')
        out = (f'<p class="vr-o vr-o-{r["outcome"].replace("_", "-")}"><b>{_e(word)}.</b> {_e(why)}</p>')
    nl = '' if r["linked"] else '<p class="vr-o">No page was built for this verdict on this build.</p>'
    corr = ('<p class="vr-o">This verdict carries a correction, listed on <a href="/corrections.html">corrections</a>.</p>'
            if r.get("corrected") else "")
    return (f'<li class="vr-r" data-vr="{_e(r["key"])}"><p class="vr-w">{meta}</p>'
            f'<p class="vr-t">{head} {badge}</p>{out}{nl}{corr}</li>')


def render(v, dateline):
    import site_build as sb
    rows = "".join(_row(r) for r in v["rows"])
    listing = (f'<ol class="vr-l">{rows}</ol>' if rows else
               '<p class="vr-empty">No graded verdict to list yet. A move under the threshold, Ether moving with Bitcoin, '
               'and a move held for the next read get no grade, and none is listed here.</p>')
    begins = (f'The record begins with the desk\'s first stored verdict record, {_e(_when(v["begins_utc"]))}, and every '
              f'graded verdict since is listed below, newest first.' if v["begins_utc"] else
              'The record begins with the desk\'s first stored verdict record. None is stored yet.')
    body = f"""<main class="wrap narrow"><section class="page vr-page">
  <span class="kicker">Why it moved</span>
  <h1>The verdict record</h1>
  <p class="lede">How the desk's own grades held up afterwards: whether a later primary source confirmed a Likely verdict,
     or a later read of the same move reversed it.</p>
  {_tally(v)}
  <h2 class="vr-h">How a verdict is scored here</h2>
  <ul class="vr-def">
    <li><b>Confirmed later.</b> A later read of the same move, the same coin on the same ET day, graded it Confirmed on an
        event the Likely verdict named. Confirmed needs a primary source stating the cause.</li>
    <li><b>Reversed.</b> A later read of the same move graded it Disputed or Unclear, or named none of the events the
        Likely verdict named.</li>
    <li><b>Awaiting a later source.</b> No later read has resolved it. A verdict with no later primary source is never
        counted as confirmed.</li>
    <li><b>Confirmed, Disputed and Unclear</b> are counted as they were graded at the time, by the rules on
        <a href="/method.html">how we check</a>.</li>
  </ul>
  <p>{begins} Each verdict and its outcome are stored once and never rewritten; a correction is listed on
     <a href="/corrections.html">corrections</a>.</p>
  <h2 class="vr-h">Every graded verdict</h2>
  {listing}
  <p class="nfa">{_e(sb.NFA)}</p>
</section></main>"""
    return sb.shell(f"The verdict record: how our grades held up - {sb.NAME}",
                    "Every move GoCheckMyCrypto graded, and how the grade held up: Likely verdicts a later primary source "
                    "confirmed, reversed, or still awaiting a later source.",
                    "Today", body, dateline, path=URL, schema_extra="\n" + RECORD_STYLE)


def render_unreadable(dateline, why=""):
    """The page when the record could not be drawn on this build: still built, and it says so."""
    import site_build as sb
    body = """<main class="wrap narrow"><section class="page vr-page">
  <span class="kicker">Why it moved</span>
  <h1>The verdict record</h1>
  <p class="lede">The record could not be read on this build. The stored verdicts are unchanged, and each is still on its
     own page under <a href="/today/">Why it moved</a>.</p>
</section></main>"""
    return sb.shell(f"The verdict record: how our grades held up - {sb.NAME}",
                    "How GoCheckMyCrypto's graded verdicts held up afterwards.", "Today", body, dateline, path=URL)


# ---- the feed ----------------------------------------------------------------------------------------------------------

def feed(v, now):
    """/api/v1/why/record.json in 9.7's envelope (api_feeds.envelope): the page's own counts, window and rows."""
    import api_feeds as af
    import verdict as vd
    data = {"window": {"begins_utc": v["begins_utc"], "through_utc": v["through_utc"],
                       "begins_et": _when(v["begins_utc"]) or None, "through_et": _when(v["through_utc"]) or None,
                       "what": "from the desk's first stored verdict record through the newest read"},
            "counts": dict(v["counts"]), "reads": dict(v["reads"]), "graded": v["graded"],
            "definitions": {"confirmed_later": "a later read of the same move (the same coin on the same ET day) graded it "
                                               "Confirmed on an event the Likely verdict named",
                            "reversed": "a later read of the same move graded it Disputed or Unclear, or named none of the "
                                        "events the Likely verdict named",
                            "awaiting": "no later read has resolved it; never counted as confirmed",
                            "grades": dict(vd.DEFINITIONS)},
            "verdicts": [{"key": r["key"], "date_et": r["date_et"], "slot": r["slot"], "made_utc": r["made_utc"],
                          "coin": r["coin_sym"], "name": r["coin_name"], "grade": r["grade"], "url": r["url"],
                          "outcome": r["outcome"], "outcome_detail": r["outcome_detail"],
                          "timing_rule_version": r["timing_rule_version"]} for r in v["rows"]]}
    return af.envelope(FEED, URL, v["through_utc"], now,
                       ["the desk's stored verdict and Big movers records, and the verdict record's own store"], data)


if __name__ == "__main__":
    if "--sync" in sys.argv[1:]:
        sync()
    sys.exit(0)
