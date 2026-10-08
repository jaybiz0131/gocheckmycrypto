#!/usr/bin/env python3
"""
wire.py: the wire, the News page's surface (Jack, 5 October 2026, program section 9).

"Worry less about writing and more about putting the best relevant stories at the top
based on what the desk thinks is relevant and accurate; the desk vets, we publish, we do not
rewrite, we show the source." The daily written story ends. The wire is the day's ranked
clusters, each in the desk's own one line, its sources counted and linked; the top item that
clears the verifier carries a checked note of two sentences and the badge.

  THE EDITION RUN (run.py, the wire path): `build()` reads the editor's ranking (with its
  `wire_line`, written from the cluster's key fact in the same call that ranks), the
  clusters behind it and the verifier's verdicts (with the note's two sentences, written in
  the same call that verifies), and writes site/data/wire.json. No model call is made here.

  BETWEEN RUNS (`python3 wire.py --refresh`, in the Netlify build): the deterministic desk
  editor re-reads the keyless feeds, re-counts each item's sources against the clusters it
  finds now, and re-orders. It never imports the model client and never writes a line.

Rules, each proven in the canary:
  - A wire line is never an outlet's headline verbatim: it is checked against EVERY source
    title in its cluster, and a line that matches one is not printed; the item is dropped
    and logged.
  - The source count is the number of independent outlets (standing.outlets); the primary
    flag is set when one source is the company's or the regulator's own (standing.is_primary).
  - The Board reading an item touches comes from the tag rules (site_build.TAG_RULES), the
    same table the watcher's cage and the site's sections read.
  - The checked note exists only for the top item whose verdict is VERIFIED and whose
    sources can lead (two independent outlets, or one primary), and only when the verifier
    wrote both sentences. Its badge is one of the three of October 4.
  - Every line and both note sentences pass the twins gate (twins_gate.py).
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WIRE_PATH = os.path.join(HERE, "site", "data", "wire.json")
MAX_LINE = 160

# The tag rules name the subject; this names the Board reading a subject touches. A tag with
# no reading touches none, and the item says so by printing nothing, never a guess.
TAG_READING = {
    "etfs-funds": "Spot ETF net",
    "stablecoins": "Stablecoin float",
    "exchanges": "Whale net, exchange flows",
    "macro": "Fear & Greed",
    "bitcoin": "Bitcoin price",
    "markets": "Bitcoin price",
    "ethereum": "Ether price",
}

WHAT_A_WIRE_LINE_IS = ("Each line is the desk's own one-line summary of a story it ranked, "
                       "with its sources counted and linked. It is not a story the desk "
                       "wrote or checked; only the item with a badge was checked.")

BADGES = {"corroborated": "Verified", "primary": "Verified, primary source",
          "single": "Unconfirmed, one report"}


def _norm(s):
    s = re.sub(r"\s+[-|–—]\s+[^-|–—]{2,40}$", "", str(s or ""))
    return " ".join(re.sub(r"[^a-z0-9$%.]+", " ", s.lower()).split()).strip(" .")


def is_verbatim(line, titles):
    """True when the line IS a source title: the same words in the same order once case,
    punctuation and an outlet suffix (" - CoinDesk") are set aside."""
    n = _norm(line)
    return bool(n) and any(n == _norm(t) for t in titles or [] if t)


def cluster_titles(cluster):
    out = []
    for t in [cluster.get("headline")] + [x.get("headline")
                                          for x in cluster.get("corroboration") or []]:
        if t and t not in out:
            out.append(t)
    return out


def board_reading(text):
    """The Board reading a story touches, from the first tag rule it matches that has one."""
    try:
        from site_build import TAG_RULES
    except Exception:
        return ""
    for tag, pat in TAG_RULES:
        if tag in TAG_READING and re.search(pat, text or "", re.I):
            return TAG_READING[tag]
    return ""


def _links(urls, outlets_by_url):
    import standing
    out, seen = [], set()
    for u in standing.primary_first(urls):
        h = standing.host(u)
        if not u or u in seen or not h:
            continue
        seen.add(u)
        out.append({"url": u, "outlet": outlets_by_url.get(u) or h,
                    "primary": standing.is_primary(u)})
    return out


def _count(urls, names):
    import standing
    return len(standing.outlets(urls, names))


def _et(utc):
    try:
        from zoneinfo import ZoneInfo
        t = datetime.datetime.fromisoformat(str(utc).replace("Z", "+00:00"))
        return t.astimezone(ZoneInfo("America/New_York")).strftime("%-I:%M %p ET on %b %-d")
    except Exception:
        return ""


def build(editor_obj, items_obj, verifier_obj, snap, run_utc, gate=None, log=print):
    """The wire from one Edition run's own outputs. Returns the wire.json object."""
    import standing
    import twins_gate
    gate = gate or twins_gate.Gate(snap)
    clusters = {c.get("id"): c for c in (items_obj or {}).get("clusters") or []}
    verdicts = {v.get("id"): v for v in (verifier_obj or {}).get("verdicts") or []}
    wire, dropped = [], []
    for rank, r in enumerate((editor_obj or {}).get("ranked") or [], 1):
        c = clusters.get(r.get("id")) or {}
        titles = cluster_titles(c) + [r.get("headline") or ""]
        line = " ".join(str(r.get("wire_line") or "").split())
        why = ""
        if not line:
            why = "the editor wrote no wire line"
        elif len(line) > MAX_LINE:
            why = f"the wire line runs {len(line)} characters, over {MAX_LINE}"
        elif is_verbatim(line, titles):
            why = "the wire line is a source's headline verbatim"
        else:
            from site_build import destyle
            line = destyle(line)
            kept = gate.text(line, f"wire line #{rank}")
            if kept.strip() != line.strip():
                why = "the twins gate dropped the line"
        if why:
            dropped.append({"rank": rank, "id": r.get("id"), "why": why})
            log(f"wire: #{rank} {r.get('id')} not on the wire: {why}")
            continue
        urls = [u for u in r.get("source_urls") or [] if u]
        names = r.get("source_outlets") or []
        by_url = {c.get("url"): c.get("source")}
        by_url.update({x.get("url"): x.get("name") for x in c.get("corroboration") or []})
        links = _links(urls, by_url)
        st = standing.standing(urls, names)
        wire.append({
            "rank": rank, "id": r.get("id"), "line": line,
            "titles": cluster_titles(c)[:8],
            "board_reading": board_reading(" ".join(titles + [line])),
            "source_count": _count(urls, names),
            "primary": any(l["primary"] for l in links),
            "standing": st,
            "links": links,
            "reported_utc": c.get("timestamp") or "",
            "verdict": (verdicts.get(r.get("id")) or {}).get("verdict", ""),
        })
    note = checked_note(wire, verdicts, gate, log)
    for w in wire:
        w["mark"] = "checked" if note and w["id"] == note["id"] else "wire"
    return {"what": "the day's ranked clusters, in the desk's own one line, sources counted "
                    "and linked (Jack, 5 October 2026)",
            "what_a_wire_line_is": WHAT_A_WIRE_LINE_IS,
            "ranked_utc": run_utc, "ranked_et": _et(run_utc),
            "refreshed_utc": run_utc, "refreshed_et": _et(run_utc),
            "refreshes": 0,
            "snapshot_stamp_utc": (snap or {}).get("stamp_utc", ""),
            "items": wire, "checked": note, "dropped": dropped}


def checked_note(wire, verdicts, gate, log=print):
    """The note for the top item that clears the verifier, or None."""
    for w in wire:
        v = verdicts.get(w["id"]) or {}
        if v.get("verdict") != "VERIFIED" or w["standing"] not in ("corroborated", "primary"):
            continue
        n = v.get("note") or {}
        says = " ".join(str(n.get("says") or "").split())
        unconf = " ".join(str(n.get("unconfirmed") or "").split())
        if not says or not unconf:
            log(f"wire: #{w['rank']} {w['id']} cleared the verifier but the note's two "
                f"sentences were not written; no checked note")
            return None
        from site_build import destyle
        says, unconf = destyle(says), destyle(unconf)
        k1 = gate.text(says, "checked note, what the source says")
        k2 = gate.text(unconf, "checked note, what could not be confirmed")
        if k1.strip() != says.strip() or k2.strip() != unconf.strip():
            log(f"wire: #{w['rank']} {w['id']} the twins gate dropped a note sentence; "
                f"no checked note")
            return None
        link, why = note_link(says, w["links"])
        if link is None:
            log(f"wire: #{w['rank']} {w['id']} the note {why}; no checked note")
            return None
        return {"id": w["id"], "rank": w["rank"], "says": says, "unconfirmed": unconf,
                "badge": BADGES[w["standing"]], "standing": w["standing"],
                "source": link.get("url", ""), "outlet": link.get("outlet", "")}
    return None


def _stem(name):
    """'CoinDesk' -> 'coindesk', 'www.theblock.co' -> 'theblock'."""
    n = (name or "").lower().strip()
    if "." in n and " " not in n:
        parts = [p for p in n.split(".") if p and p != "www"]
        n = parts[0] if parts else n
    return re.sub(r"[^a-z0-9]+", "", n)


def news_outlets():
    """The secondary outlets the desk reads (config sources not tiered primary)."""
    try:
        import common
        src = common.load_config().get("sources") or []
        src = src.get("rss", src) if isinstance(src, dict) else src
        return [s["name"] for s in src if isinstance(s, dict) and s.get("name")
                and s.get("tier") != "primary"]
    except Exception:
        return []


def note_link(says, links):
    """THE NOTE NAMES THE OUTLET IT LINKS (8 October 2026). The 7 October note said
    "Decrypt reports" and linked CoinDesk. Returns (link, why): the item's link whose
    outlet the sentence names; the first link when it names none of the item's outlets
    and no other outlet; (None, why) when it names an outlet the item does not link."""
    flat = re.sub(r"[^a-z0-9]+", "", (says or "").lower())
    for l in links or []:
        if _stem(l.get("outlet")) and _stem(l.get("outlet")) in flat:
            return l, ""
    linked = {_stem(l.get("outlet")) for l in links or []}
    for name in news_outlets():
        if _stem(name) and _stem(name) in flat and _stem(name) not in linked:
            return None, f"names {name}, which the item does not link"
    return ((links or [None])[0]), ""


def write(obj, path=None):
    path = path or WIRE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")


def load(path=None):
    try:
        return json.load(open(path or WIRE_PATH, encoding="utf-8"))
    except Exception:
        return None


# ---- between runs: the deterministic desk editor ------------------------------------------

def refresh(wire, clusters, now_utc):
    """Re-count each item's sources against the clusters read now and re-order: most
    independent outlets first, the Edition's rank breaking ties. Lines, notes and badges
    are never rewritten. Pure: no network, no model."""
    import dedupe
    if not wire or not wire.get("items"):
        return wire
    out = dict(wire)
    items = []
    for w in wire["items"]:
        w = dict(w)
        urls = [l["url"] for l in w.get("links") or []]
        names = [l.get("outlet") for l in w.get("links") or []]
        titles = w.get("titles") or []
        known = set(urls)
        for c in clusters or []:
            members = [(c.get("url"), c.get("source"), c.get("headline"))] + [
                (x.get("url"), x.get("name"), x.get("headline"))
                for x in c.get("corroboration") or []]
            # the same story: a URL already behind the item, or a cluster headline the
            # intake's own matcher calls the same event as one of the item's source titles
            if not (known & {m[0] for m in members if m[0]}) and not any(
                    dedupe.same_event(t, "", c.get("headline") or "", "") for t in titles):
                continue
            for u, n, h in members:
                if u and u not in known:
                    known.add(u)
                    urls.append(u)
                    names.append(n)
        by_url = {l["url"]: l.get("outlet") for l in w.get("links") or []}
        for c in clusters or []:
            by_url.setdefault(c.get("url"), c.get("source"))
            for x in c.get("corroboration") or []:
                by_url.setdefault(x.get("url"), x.get("name"))
        w["links"] = _links(urls, by_url)
        w["source_count"] = _count(urls, [n for n in names if n])
        w["primary"] = any(l["primary"] for l in w["links"])
        items.append(w)
    items.sort(key=lambda w: (-w["source_count"], w.get("rank") or 10 ** 6))
    out["items"] = items
    out["refreshed_utc"] = now_utc
    out["refreshed_et"] = _et(now_utc)
    out["refreshes"] = int(wire.get("refreshes") or 0) + 1
    return out


def _read_clusters():
    """The keyless feeds, clustered the way intake clusters them. RSS only: the lanes that
    need a key do not run in the build."""
    import aggregate
    cfg = aggregate.load_config()
    raw, ok, _total = aggregate.gather_rss(cfg)
    fresh = aggregate.within_lookback(raw, cfg["lookback_hours"])
    return aggregate.dedupe(fresh, cfg), ok


def main():
    if "--refresh" not in sys.argv[1:]:
        print("usage: python3 wire.py --refresh   (the Edition run writes the wire via run.py)")
        return 2
    w = load()
    if not w or not w.get("items"):
        print("wire: no wire.json to refresh; nothing changed")
        return 0
    try:
        clusters, ok = _read_clusters()
    except Exception as e:
        print(f"wire: feeds unreadable ({type(e).__name__}: {e}); the wire stands as written")
        return 0
    if not ok:
        print("wire: no feed answered; the wire stands as written")
        return 0
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = refresh(w, clusters, now)
    write(new)
    print(f"wire: re-counted {len(new['items'])} item(s) against {len(clusters)} cluster(s) "
          f"from {ok} feed(s); no model call")
    return 0


if __name__ == "__main__":
    sys.exit(main())
