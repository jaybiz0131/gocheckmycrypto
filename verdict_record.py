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
    site/data/verdict/record/, written once (a temp file hard-linked to the final name, which fails when it exists) and
    never rewritten (the why records' rule). The run
    steps (verdict.py and movers.py --write) call sync(); the build reads the same stores and never writes.
  - Corrections (9.5) are free text on a story, a verdict or a day's answer. A correction is never read as an outcome here.

THE RULES (the same move is one coin on one ET day; a later day's read measures a different move):
  confirmed later  a later read of the same move graded it Confirmed on an event the Likely verdict named.
  reversed         a later read graded it Disputed or Unclear, or Confirmed or Likely on events the Likely verdict did not name.
  awaiting         not resolved yet, and the read window is still open: the same ET day, before that day's Evening Brief
                   read (the day's last scheduled read) is stored.
  unresolved       still Likely: the read window closed with no later source. A Likely from the Evening Brief read is
                   unresolved at once. Nothing past the ET day is sought (a later-source path past the day is a proposal).
  An event is the same event when it shares a STABLE id (STABLE_IDS: built from the event's own date, time or document
  number) or a source article of a wire story. A wire candidate's id is a per-run position and is never compared; a shared
  word or a shared schedule page is never an identity.
  One verdict per read: a slot rewritten by a later run counts once, with its last stored grade; the replaced grade stays
  in the store. A stored file of any other shape is skipped, logged and counted on the page and in the feed.
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
OUTCOME_WORDS = {"confirmed_later": "Confirmed later", "reversed": "Reversed", "awaiting": "Awaiting a later source",
                 "unresolved": "No later source by the end of its ET day"}
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
.page .vr-g.vr-g4{grid-template-columns:repeat(4,minmax(0,1fr))}
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
.page li.vr-r p.vr-o-unresolved{border-left:3px solid var(--line)}
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
@media (max-width:520px){.page .vr-tally{padding:14px 14px 12px}.page .vr-g{gap:6px}.page .vr-g.vr-g4{grid-template-columns:repeat(2,minmax(0,1fr))}.page .vr-c{padding:8px 8px 7px}
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


# ---- the identity of an event: what is stable across runs -----------------------------------------------------------
#
# A wire candidate's id is "wire-" plus the cluster's id, and that is its POSITION in the run's ranking (aggregate.py,
# f"c{i:03d}"): wire-c010 named the Cysic bridge halt on October 19 and France's National Assembly vote on October 20.
# It is never an identity. A wire story is the same story when one of its source articles is the same page.
# Every other family below builds its id from the event's own date, time or document number, read from the source,
# so one event gets the same id in every run that sees it. Only an id of one of these forms is compared.
STABLE_IDS = {
    "bls": (r"bls-\d{8}-[a-z][a-z-]*", "the release's ET date and name, from the BLS schedule (why_evidence._bls)"),
    "bea": (r"bea-\d{8}-[a-z][a-z-]*", "the release's ET date and name, from BEA's release dates (why_evidence._bea)"),
    "fomc": (r"fomc-\d{4}-\d{2}-\d{2}", "the meeting's last day, from the stored FOMC calendar (why_evidence._fomc)"),
    "ff": (r"ff-\d{9,}-[a-z0-9][a-z0-9-]*", "the release's epoch time and title, from the ForexFactory calendar"),
    "fr": (r"fr-\d{4}-\d{3,6}", "the Federal Register document number (why_evidence._fedreg)"),
    "press": (r"(?:federal reserve|sec|cftc)-\d{9,}", "the outlet and its own feed stamp, from its RSS (why_evidence._rss)"),
    "hack": (r"hack-\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*", "the exploit's date and name, from DefiLlama (why_evidence._hacks)"),
    "unlock": (r"unlock-[a-z0-9]+-\d{9,}", "the coin and the unlock's epoch time (movers.unlock_candidates)"),
    "listing": (r"listing-[a-z0-9]+-\d{9,}-[a-z0-9-]*", "the venue, the notice's epoch time and title (movers.listing_candidates)"),
    "delisting": (r"delisting-[a-z0-9]+-\d{9,}-[a-z0-9-]*", "the venue, the notice's epoch time and title"),
}
_STABLE_RX = re.compile("|".join(f"(?:{rx})" for rx, _why in STABLE_IDS.values()))


def is_stable_id(cid):
    """True for an id of a family whose id is built from the event itself (STABLE_IDS); never for a wire position."""
    return isinstance(cid, str) and _STABLE_RX.fullmatch(cid) is not None


# ---- the entries: every graded verdict in the stored slot records ------------------------------------------------------

def _skip(skips, what, err):
    print(f"::warning::verdict record: {what} could not be read ({err}); left out of the count")
    if skips is not None:
        skips.append(what)


def _evidence_links(ev, ids):
    """The source articles of the named WIRE candidates, the one identity a wire story has across runs. A release's or a
    filing's link is a shared schedule or index page (every BLS release in a month links the same one), never an identity."""
    out = []
    for c in (ev or {}).get("candidates") or []:
        if not isinstance(c, dict) or c.get("id") not in ids or is_stable_id(c.get("id")) or c.get("kind") != "wire":
            continue
        for ln in (c.get("links") or []) + (c.get("report_links") or []):
            k = _link((ln or {}).get("url") if isinstance(ln, dict) else "")
            if k and k not in out:
                out.append(k)
    return sorted(out)


def _entry(rec, sym, v, slug, name, url, source, ev):
    events = sorted({r.get("id") for r in v.get("refs") or [] if isinstance(r, dict) and isinstance(r.get("id"), str)}
                    | ({(v.get("cand") or {}).get("id")} if v.get("grade") == "Confirmed"
                       and isinstance((v.get("cand") or {}).get("id"), str) else set()))
    made = rec.get("made_utc") or ""
    return {"key": _key(rec.get("date_et"), rec.get("slot"), slug, made), "date_et": rec.get("date_et"),
            "slot": rec.get("slot"), "made_utc": made, "coin_sym": sym, "coin_slug": slug, "coin_name": name,
            "grade": v.get("grade"), "events": events, "links": _evidence_links(ev, set(events)), "url": url,
            "source": source, "window_words": v.get("window_words"), "move_pct": v.get("move_pct"),
            "timing_rule_version": ((rec.get("timing_rule") or (ev or {}).get("timing_rule") or {}).get("version")),
            "corrected": bool(v.get("corrections"))}


def entries(vdir=None, mdir=None, wdir=None, skips=None):
    """Every graded verdict the stored slot records hold, Bitcoin and Ether (verdict.py) and Big movers (movers.py), as
    entries. A coin with no grade (flat, with Bitcoin, the next read, withheld at the cap) is none. A record or a coin that
    is not the shape the run writes is skipped, logged and counted in `skips`, never guessed at."""
    vd = _vd()
    out = []
    for n in vd._names(vdir):
        try:
            rec = vd.load(n[:10], n[11:-5], vdir)
            if not rec:
                continue
            rec = dict(rec, date_et=rec.get("date_et") or n[:10], slot=rec.get("slot") or n[11:-5])
            ev, bad = None, False
            for sym, v in rec["coins"].items():
                try:
                    if not isinstance(v, dict):
                        raise TypeError(f"{sym} is a {type(v).__name__}")
                    if v.get("grade") not in GRADES:
                        continue
                    if ev is None:
                        try:
                            import why_evidence as we
                            ev = we.load(rec["date_et"], rec["slot"], wdir) or {}
                            ev = ev if isinstance(ev, dict) else {}
                        except Exception:                    # noqa: BLE001
                            ev = {}
                    name, slug = {"BTC": ("Bitcoin", "bitcoin"), "ETH": ("Ether", "ether")}.get(
                        sym, vd.NAMES.get(sym, (v.get("name") or sym, str(sym).lower())))
                    out.append(_entry(rec, sym, v, slug, name, f"/why/{rec['date_et']}-{slug}", "verdict", ev))
                except Exception as e:                       # noqa: BLE001
                    bad = True
                    print(f"::warning::verdict record: verdict/{n}: {sym} could not be read ({type(e).__name__})")
            if bad:
                _skip(skips, f"verdict/{n}", "a coin in it is not the shape the run writes")
        except Exception as e:                               # noqa: BLE001
            _skip(skips, f"verdict/{n}", type(e).__name__)
    mv = _mv()
    for n in mv.names(mdir):
        try:
            m = mv.NAME_RX.fullmatch(n)
            rec = mv.load(m.group(1), m.group(2), mdir)
            if not rec:
                continue
            if not rec.get("date_et"):
                print(f"::warning::verdict record: movers/{n} has no date_et; its verdicts are left out, never dated by guess")
                if skips is not None:
                    skips.append(f"movers/{n}")
                continue
            bad = False
            for sym, e in (rec.get("coins") or {}).items():
                try:
                    v = (((e.get("verdict") or {}).get("coins") or {}).get(sym) or {})
                    if v.get("grade") not in GRADES or not e.get("evidence"):
                        continue                             # movers.build_pages builds a page only with its evidence
                    slug = e.get("gecko_id") or str(sym).lower()
                    out.append(_entry(rec, sym, v, slug, e.get("name") or sym, f"/why/{rec['date_et']}-{slug}", "movers",
                                      e.get("evidence")))
                except Exception as ex:                      # noqa: BLE001
                    bad = True
                    print(f"::warning::verdict record: movers/{n}: {sym} could not be read ({type(ex).__name__})")
            if bad:
                _skip(skips, f"movers/{n}", "a coin in it is not the shape the run writes")
        except Exception as e:                               # noqa: BLE001
            _skip(skips, f"movers/{n}", type(e).__name__)
    return out


def dedupe(es):
    """ONE VERDICT PER READ (review 1): a slot rewritten by a later run of the same slot is one read, counted once with its
    last stored grade. The replaced grade stays in the store (append-only), and an outcome already stored for it stands."""
    last = {}
    for e in sorted(es, key=lambda e: (e.get("made_utc") or "", e["key"])):
        last[(e.get("date_et"), _slot_key(e.get("slot")), e.get("coin_slug") or e.get("coin_sym"))] = e
    return sorted(last.values(), key=lambda e: (e.get("made_utc") or "", e["key"]))


# ---- the outcomes ------------------------------------------------------------------------------------------------------

def _same_event(a, b):
    """The same event: a shared STABLE id (STABLE_IDS), or a shared source article of a wire story. Never a wire position,
    never a shared word, never a shared schedule page."""
    sa = {x for x in a.get("events") or [] if is_stable_id(x)}
    sb_ = {x for x in b.get("events") or [] if is_stable_id(x)}
    if sa & sb_:
        return True
    la = {_link(x) or x for x in a.get("links") or [] if isinstance(x, str)}
    lb = {_link(x) or x for x in b.get("links") or [] if isinstance(x, str)}
    return bool((la - {""}) & (lb - {""}))


def resolve(es):
    """{key: outcome} for every Likely entry a later read of the same move has resolved, by the rules in the module
    docstring. A Likely with no deciding later read is absent (awaiting while its day's reads can still come, else
    unresolved: see view())."""
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
                                 "shared_events": sorted({x for x in set(e.get("events") or []) & set(later.get("events") or [])
                                                          if is_stable_id(x)})}
                break
    return out


# ---- the store: one frozen file per entry and per outcome --------------------------------------------------------------

def _safe(key):
    return isinstance(key, str) and bool(key) and KEY_RX.fullmatch(key) is not None


def _write_once(path, obj):
    """Written once, whole or not at all: the JSON goes to a temp file in the same directory, is flushed to disk, and is
    then hard-linked to the final name, which fails when that name exists (the exclusive create holds). A write cut
    halfway leaves no file under the final name, and the temp file is always removed. True when this call wrote it."""
    if os.path.exists(path):
        return False
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False
        return True
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


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


def _entry_ok(o):
    return (isinstance(o, dict) and o.get("kind") == "verdict" and _safe(o.get("key")) and o.get("grade") in GRADES
            and isinstance(o.get("events", []), list) and isinstance(o.get("links", []), list)
            and all(isinstance(x, str) for x in o.get("events", []) + o.get("links", []))
            and isinstance(o.get("date_et"), str) and isinstance(o.get("made_utc", ""), str))


def _outcome_ok(o):
    return (isinstance(o, dict) and o.get("kind") == "outcome" and _safe(o.get("key"))
            and o.get("outcome") in ("confirmed_later", "reversed") and isinstance(o.get("later", {}), dict))


def load_store(store=None, skips=None):
    """(entries, {key: outcome}) as stored. A file of any other type or shape is skipped, logged and counted."""
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
            with open(os.path.join(d, n), encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:                               # noqa: BLE001
            _skip(skips, f"record/{n}", type(e).__name__)
            continue
        if n.endswith(".outcome.json"):
            if _outcome_ok(obj):
                outs.setdefault(obj["key"], obj)
            else:
                _skip(skips, f"record/{n}", "not an outcome the run writes")
        elif _entry_ok(obj):
            es.append(obj)
        else:
            _skip(skips, f"record/{n}", "not a verdict entry the run writes")
    return es, outs


def merged(vdir=None, mdir=None, wdir=None, store=None, skips=None):
    """(entries, outcomes, new_entries, new_outcomes). `entries` holds every stored entry and every one the slot records hold
    that the store does not yet, ONE PER READ (dedupe); `new_entries` is every slot-record entry not yet stored, each a file
    of its own (append-only: a replaced grade is kept). Outcomes: the stored ones, then those of Likely entries not yet
    stored as resolved. Nothing stored is changed."""
    s_es, s_outs = load_store(store, skips)
    have = {e["key"] for e in s_es}
    new_es = [e for e in entries(vdir, mdir, wdir, skips) if e["key"] not in have]
    es = dedupe(s_es + new_es)
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
    """The reads stored: {coins, movers, first_utc, last_utc, evening}. A read is one slot's record, graded or not.
    `evening` is {(source, date_et)} for each day whose Evening Brief read is stored."""
    vd, mv = _vd(), _mv()
    times, n_c, n_m, evening = [], 0, 0, set()
    for n in vd._names(vdir):
        try:
            r = vd.load(n[:10], n[11:-5], vdir)
        except Exception:                                    # noqa: BLE001
            r = None
        if r:
            n_c += 1
            if n[11:-5] == "evening":
                evening.add(("verdict", n[:10]))
            if _parse(r.get("made_utc")):
                times.append(r["made_utc"])
    for n in mv.names(mdir):
        try:
            m = mv.NAME_RX.fullmatch(n)
            r = mv.load(m.group(1), m.group(2), mdir)
        except Exception:                                    # noqa: BLE001
            r = None
        if r:
            n_m += 1
            if m.group(2) == "evening":
                evening.add(("movers", m.group(1)))
            if _parse(r.get("made_utc")):
                times.append(r["made_utc"])
    return {"coins": n_c, "movers": n_m, "first_utc": min(times) if times else None,
            "last_utc": max(times) if times else None, "evening": evening}


def window_open(e, now, evening):
    """THE READ WINDOW (review 1). A Likely verdict can be resolved only by a later read of the same move: the same coin on
    the same ET day. The window is open while a later read can still come that day: its own read was not the Evening Brief
    read (the day's last scheduled read), that day's Evening Brief read is not yet stored, and the ET day has not ended.
    Nothing past the ET day is sought."""
    if _slot_key(e.get("slot")) == "evening" or (e.get("source"), e.get("date_et")) in evening:
        return False
    try:
        d = _dt.date.fromisoformat(str(e.get("date_et")))
    except ValueError:
        return False
    we = _we()
    day_end = _dt.datetime(d.year, d.month, d.day, tzinfo=we.ET) + _dt.timedelta(days=1)
    return now < day_end.astimezone(_dt.timezone.utc)


def view(now, vdir=None, mdir=None, wdir=None, store=None, built=None):
    """Everything the page and the feed print, from stored records only. `built`: the /why/ addresses this build wrote (None:
    every row links). Never writes. A stored file it cannot read is left out and counted in `skipped`."""
    import snapshot
    skips = []
    es, outs, _n, _o = merged(vdir, mdir, wdir, store, skips)
    rd = reads(vdir, mdir)
    times = [t for t in [rd["first_utc"], rd["last_utc"]] + [e.get("made_utc") for e in es] if _parse(t)]
    begins = min(times) if times else None
    through = max(times) if times else None
    counts = {"likely": 0, "likely_confirmed_later": 0, "likely_reversed": 0, "likely_awaiting": 0, "likely_unresolved": 0,
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
                outcome = "awaiting" if window_open(e, now, rd["evening"]) else "unresolved"
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
            "graded": len(rows), "skipped": len(skips), "skipped_files": sorted(skips)}


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
    # each fact once (review 1): the record's start is said here and only here; that nothing is graded, here and only here
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
            f'<div class="vr-g vr-g4">{cell("likely_confirmed_later", "Confirmed later by a primary source", "vr-up")}'
            f'{cell("likely_reversed", "Reversed by a later read", "vr-dn")}'
            f'{cell("likely_awaiting", "Awaiting: a later read can still come today")}'
            f'{cell("likely_unresolved", "Still Likely: no later source by the end of its ET day")}</div></div>'
            f'<div class="vr-blk"><p class="vr-bh">The other grades, as given at the time</p>'
            f'<div class="vr-g">{cell("confirmed", "Confirmed")}{cell("disputed", "Disputed")}{cell("unclear", "Unclear")}</div></div>'
            f'<p class="vr-rd">Reads in this window: {_n("reads_coins", rd["coins"])} of Bitcoin and Ether, '
            f'{_n("reads_movers", rd["movers"])} of Big movers.</p>'
            + (f'<p class="vr-rd">{_n("skipped", v["skipped"])} stored file{"s" if v["skipped"] != 1 else ""} could not be '
               f'read and {"are" if v["skipped"] != 1 else "is"} left out of these counts.</p>' if v.get("skipped") else "")
            + '</section>')


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
            why = "A later read of the same move can still come before this ET day's Evening Brief read."
        elif r["outcome"] == "unresolved":
            why = "Still Likely: no later read of the same move resolved it before its ET day's reads were done."
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
    # no list and no second sentence when nothing is graded: the tally says so, once
    listing = (f'<h2 class="vr-h">Every graded verdict</h2>\n  <ol class="vr-l">{rows}</ol>' if rows else "")
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
    <li><b>Awaiting a later source.</b> The read window is the same ET day: a later read of the same coin can still come
        before that day's Evening Brief read. The Evening Brief read is the day's last scheduled read. A verdict with no
        later primary source is never counted as confirmed.</li>
    <li><b>No later source by the end of its ET day.</b> Still Likely: the day's reads were done and none resolved it, so a
        Likely from the Evening Brief read lands here at once. Nothing past the ET day is sought.</li>
    <li><b>Confirmed, Disputed and Unclear</b> are counted as they were graded at the time, by the rules on
        <a href="/method.html">how we check</a>.</li>
    <li><b>Not graded, not counted:</b> a move under the threshold, Ether moving with Bitcoin, a move held for the next
        read, and a check that did not run.</li>
  </ul>
  <p>Each graded verdict is listed newest first, one per read; when a read was rewritten, its last stored grade. Each
     verdict and its outcome are stored once and never rewritten, and a correction is listed on
     <a href="/corrections.html">corrections</a>.</p>
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
            "state": "partial" if v.get("skipped") else "complete", "skipped": v.get("skipped", 0),
            "skipped_files": list(v.get("skipped_files") or []),
            "counts": dict(v["counts"]), "reads": dict(v["reads"]), "graded": v["graded"],
            "definitions": {"confirmed_later": "a later read of the same move (the same coin on the same ET day) graded it "
                                               "Confirmed on an event the Likely verdict named",
                            "reversed": "a later read of the same move graded it Disputed or Unclear, or named none of the "
                                        "events the Likely verdict named",
                            "awaiting": "no later read has resolved it yet, and one can still come: the same ET day, before "
                                        "that day's Evening Brief read; never counted as confirmed",
                            "unresolved": "still Likely: no later source by the end of its ET day (the read window); "
                                          "nothing past the ET day is sought",
                            "grades": dict(vd.DEFINITIONS)},
            "verdicts": [{"key": r["key"], "date_et": r["date_et"], "slot": r["slot"], "made_utc": r["made_utc"],
                          "coin": r["coin_sym"], "name": r["coin_name"], "grade": r["grade"], "url": r["url"],
                          "outcome": r["outcome"], "outcome_detail": r["outcome_detail"],
                          "timing_rule_version": r["timing_rule_version"]} for r in v["rows"]]}
    return af.envelope(FEED, URL, v["through_utc"], now,
                       ["the desk's stored verdict and Big movers records, and the verdict record's own store"], data)


def feed_unreadable(now, why=""):
    """The feed when the record could not be drawn at all: still written (the page says the same), no as-of, stale, no counts."""
    import api_feeds as af
    return af.envelope(FEED, URL, None, now, ["the desk's stored verdict and Big movers records, and the verdict record's own store"],
                       {"state": "unreadable", "why": why or "the record could not be read on this build", "counts": None,
                        "verdicts": [], "window": None})


if __name__ == "__main__":
    if "--sync" in sys.argv[1:]:
        sync()
    sys.exit(0)
