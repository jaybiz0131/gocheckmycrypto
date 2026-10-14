#!/usr/bin/env python3
"""
today.py: the daily answer (Program 8, Sprint 8.1; Jack's ruling of 14 October 2026).

"Why is crypto down today" and "why is crypto up today" are the most repeated crypto
searches. The site answers it twice a day, from numbers and reads it already has, with NO
model call: the snapshot (Bitcoin, Ether, the whole market, the Top 100 by 24h), the Board's
ETF net, liquidations, funding and Fear & Greed, the morning read or the Edition, and the
wire. One living page, /today/, always the newest of the day's two, and a dated page per day,
/today/YYYY-MM-DD, that freezes at the evening build.

    python3 today.py --write morning     # after morning.py, in morning-read.yml
    python3 today.py --write evening     # after the Edition, in crypto-news-brief.yml
    python3 today.py --correct 2026-10-14 "what was wrong and what is right"

HOW IT STAYS FROZEN. A record is one JSON file, site/data/today/YYYY-MM-DD.json, committed by
the workflow that wrote it. The build only RENDERS records (a pure function of the record and
the days before it), so a dated page cannot change after the evening record exists: write()
refuses a second write to a frozen day, and the rendering of a day never reads a later day.
The one exception is a correction under the corrections policy, which is printed on the page.

THE COPY LAW HOLDS. Every sentence goes through the twins gate (twins_gate.Gate) when the
record is written, and a dropped sentence is logged exactly as 7.3 built it (out/twins-gate.json
and, here, the record's own `drops`). The page never says "because" or any causal phrase in
the desk's own voice, never predicts, never advises. A wire line is the desk's one-line
summary of a story with its sources linked; whatever it says, its sources say.
"""
import datetime as _dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "site", "data", "today")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-4))

ORIGIN = "https://gocheckmycrypto.com"
FLAT_PCT = 0.5               # Bitcoin within plus or minus this, 24h, is a flat day
WIRE_MAX = 5
CONTEXT_MAX = 2
# Causal phrases the desk's own voice never uses. A wire line may carry one (its sources
# are linked beside it); a sentence the desk wrote or lifted may not.
CAUSAL = re.compile(r"\b(because|due to|driven by|caused by|as a result|thanks to|owing to|"
                    r"on account of|fuell?ed by|sparked by|triggered by|stems? from|"
                    r"the reason)\b", re.I)


def _e(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


def _utc(ts):
    try:
        d = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)


def et_time(ts):
    d = _utc(ts)
    return d.astimezone(ET).strftime("%-I:%M %p ET") if d else ""


def et_date(ts):
    d = _utc(ts)
    return d.astimezone(ET).date().isoformat() if d else ""


def et_iso(ts):
    """A schema.org datetime in the Eastern offset: 2026-10-14T08:18:55-04:00."""
    d = _utc(ts)
    return d.astimezone(ET).isoformat(timespec="seconds") if d else ""


def long_date(iso):
    d = _dt.date.fromisoformat(iso)
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def usd_price(v):
    """Whole dollars from $1,000 up, as the home tape prints Bitcoin; else the site's price format."""
    import site_build as sb
    return f"${v:,.0f}" if isinstance(v, (int, float)) and v >= 1000 else sb._price_fmt(v)


def direction(chg):
    """'down', 'up' or 'flat' from Bitcoin's 24h change as the page prints it (two places).
    Within plus or minus 0.5 percent, inclusive, is flat."""
    c = round(float(chg), 2)
    if abs(c) <= FLAT_PCT:
        return "flat"
    return "up" if c > 0 else "down"


def headline(dirn, iso):
    """(h1, title): the day's real direction from Bitcoin's 24h change, with the full date."""
    d = long_date(iso)
    if dirn == "flat":
        return f"Crypto today: flat. {d}", f"Crypto today: flat. {d}"
    h = f"Why is crypto {dirn} today? {d}"
    return h, h


def _word(v):
    return "up" if v > 0 else "down" if v < 0 else "unchanged"


# ---- the record ----------------------------------------------------------------------------

def _gated(gate, surface, text, drops):
    """text through the twins gate; a sentence it drops is logged in the record too."""
    if not (text or "").strip():
        return ""
    before = len(gate.drops)
    kept = gate.text(text, surface, dollars=True)
    for d in gate.drops[before:]:
        drops.append({"surface": surface, "sentence": d.get("dropped"), "why": d.get("why"),
                      "kind": d.get("kind")})
    return kept


def _sentences(text):
    import twins_gate
    return twins_gate.sentences(text)


def _law_ok(s):
    """The copy law for a sentence in the desk's own voice."""
    import narrative
    import wrap
    return not (narrative._PREDICT.search(s) or wrap.bottom_line_lint(s)
                or wrap.unattributed_lint(s) or CAUSAL.search(s) or re.search(r"[–—]", s))


_UP = r"up|rose|rising|gained|gains?|higher|climbed|advanced|jumped|rallied|surged"
_DOWN = r"down|fell|falling|lost|lower|dropped|declined|slid|slipped|sank|slumped|tumbled|dipped"
_DAY = r"24[- ]hours?|past day|on the day|today|overnight|so far today|since yesterday"
_COIN_DAY = re.compile(
    r"\b(bitcoin|btc|ether(?:eum)?|eth)\b([^.;]{0,50}?)\b(" + _UP + "|" + _DOWN + r")\b"
    r"(?:\s+(\d+(?:\.\d+)?)\s*(?:%|percent))?([^.;]{0,40})", re.I)


def day_claim_wrong(s, snap):
    """A reason when a sentence states Bitcoin's or Ether's move over the day and the snapshot
    reads otherwise. The twins gate reads a coin's week and month and its dollar price but not
    its 24-hour change (the band quotes none), and this page quotes it, so a lifted sentence
    gets this check beside the gate's own. A window other than the day is the gate's to read."""
    import snapshot as S
    for m in _COIN_DAY.finditer(s):
        sym = "BTC" if m.group(1).lower() in ("bitcoin", "btc") else "ETH"
        chg = S.coin(snap, sym).get("chg_24h_pct")
        tail = m.group(2) + " " + m.group(5)
        windowed = re.search(_DAY, tail + " " + s[m.end():], re.I) is not None
        other = re.search(r"week|month|7[- ]day|30[- ]day|year|session|since (?:the )?(?:\w+ )?\d", tail, re.I)
        if not isinstance(chg, (int, float)) or other or not (windowed or m.group(4)):
            continue
        if m.group(4) and not windowed:
            continue                                  # a bare "up 3%" with no window is not read
        said = 1 if re.fullmatch(_UP, m.group(3), re.I) else -1
        if round(chg, 2) != 0 and said != (1 if chg > 0 else -1):
            return f"{sym} {m.group(3)} over the day in our text against the snapshot's {chg:+.2f}%"
        if m.group(4) and abs(float(m.group(4)) - abs(chg)) > 0.05:
            return f"{sym} {m.group(4)}% over the day in our text against the snapshot's {chg:+.2f}%"
    return ""


def _movers(coins):
    """The three largest gains and declines among the Top 100 by 24h (stablecoins out)."""
    live = [dict(v, symbol=k) for k, v in (coins or {}).items()
            if isinstance(v.get("rank"), int) and v["rank"] <= 100 and not v.get("stablecoin")
            and isinstance(v.get("chg_24h_pct"), (int, float))]

    def row(c):
        return {"symbol": c["symbol"], "name": c.get("name") or c["symbol"], "rank": c["rank"],
                "chg": c["chg_24h_pct"]}
    up = sorted((c for c in live if c["chg_24h_pct"] > 0), key=lambda c: (-c["chg_24h_pct"], c["rank"]))
    dn = sorted((c for c in live if c["chg_24h_pct"] < 0), key=lambda c: (c["chg_24h_pct"], c["rank"]))
    return [row(c) for c in up[:3]], [row(c) for c in dn[:3]]


def _board(snap, pulse, gate, drops, stamp):
    """The four Board readings, each with its window, source and stamp."""
    import snapshot as S
    import site_build as sb
    rows = []

    def add(key, label, fig, direction_, text, window, source):
        t = _gated(gate, f"the daily answer, Board: {label}", text, drops)
        if t:
            rows.append({"key": key, "label": label, "figure": fig, "dir": direction_,
                         "text": t, "window": window, "source": source, "stamp": stamp})
    etf = (S.value(snap, "etf_flows") or {}).get("btc") or {}
    net = etf.get("latest_net_usd_m")
    if isinstance(net, (int, float)):
        fig = (f"{'+' if net > 0 else '-' if net < 0 else ''}{sb.fmt_usd(abs(net) * 1e6)}"
               if net else "flat")
        add("etf", "Spot ETF net", fig, "up" if net > 0 else "down" if net < 0 else "",
            f"Bitcoin spot ETF net for the {etf.get('latest_date')} session was {fig}.",
            f"one trading day, {etf.get('latest_date')}", "Farside Investors")
    liq = None
    for a in ((pulse or {}).get("leverage") or {}).get("assets") or []:
        if a.get("symbol") == "BTC":
            liq = a.get("liquidations")
    if isinstance(liq, dict) and isinstance(liq.get("longs_usd"), (int, float)):
        win = f"the last {liq.get('window_hours')} hours"
        add("liq", "Liquidations", f"{sb.fmt_usd(liq['longs_usd'])} long, {sb.fmt_usd(liq.get('shorts_usd') or 0)} short",
            "", f"Bitcoin perpetuals on OKX closed {sb.fmt_usd(liq['longs_usd'])} of long and "
                f"{sb.fmt_usd(liq.get('shorts_usd') or 0)} of short positions in {win}.",
            win + ", one venue", "OKX")
    f = (S.value(snap, "funding") or {}).get("BTC") or {}
    if isinstance(f.get("funding_8h_pct"), (int, float)):
        v = f["funding_8h_pct"]
        add("funding", "Funding", f"{v:+.4f}%", "",
            f"Bitcoin perpetual funding is {v:+.4f}% per 8 hours.",
            "the current 8-hour period", f.get("venue") or "OKX")
    fg = S.value(snap, "fear_greed") or {}
    if isinstance(fg.get("value"), (int, float)):
        add("fng", "Fear & Greed", f"{fg['value']:g}", "",
            f"The Fear & Greed index reads {fg['value']:g}, {sb._fng_band(fg['value'])}.",
            "today", "alternative.me")
    return rows


def _wire(wire, iso, gate, drops):
    """Up to five wire items ranked that day, each with its sources and time."""
    if not wire:
        return [], ""
    stamps = [et_date(wire.get(k)) for k in ("refreshed_utc", "ranked_utc")]
    if iso not in stamps:
        return [], ""
    out = []
    for w in wire.get("items") or []:
        links = [l for l in (w.get("links") or []) if l.get("url")]
        if not w.get("line") or not links:
            continue
        line = _gated(gate, "the daily answer, wire", w["line"], drops)
        if not line:
            continue
        when = et_time(w.get("reported_utc")) or et_time(wire.get("refreshed_utc") or wire.get("ranked_utc"))
        out.append({"line": line, "sources": int(w.get("source_count") or len(links)),
                    "primary": bool(w.get("primary")), "time": when,
                    "outlets": [{"outlet": l.get("outlet") or "Source", "url": l["url"]} for l in links[:3]]})
        if len(out) == WIRE_MAX:
            break
    stamp = et_time(wire.get("refreshed_utc") or wire.get("ranked_utc"))
    return out, stamp


def build_record(snap, pulse, wire, morning, edition, slot, now, gate=None, iso=None):
    """The day's record from what the build already has; None when Bitcoin has no 24h change.
    Pure on its arguments (no network, no model, no clock but `now`)."""
    import snapshot as S
    import site_build as sb
    import twins_gate
    gate = gate or twins_gate.Gate(snap, quiet=True)
    btc = S.coin(snap, "BTC")
    chg = btc.get("chg_24h_pct")
    if not isinstance(chg, (int, float)) or not isinstance(btc.get("price"), (int, float)):
        return None
    iso = iso or now.astimezone(ET).date().isoformat()
    stamp_et = (snap or {}).get("stamp_et") or ""
    drops = []
    eth = S.coin(snap, "ETH")
    cap = S.value(snap, "total_cap") or {}
    dn = direction(chg)

    # 1. the answer: the numbers in a fixed template ...
    parts = [f"As of {stamp_et}, Bitcoin is {_word(chg)} {abs(chg):.2f}% over the past 24 hours, "
             f"at {usd_price(btc['price'])}."]
    tail = []
    if isinstance(eth.get("chg_24h_pct"), (int, float)):
        tail.append(f"Ether is {_word(eth['chg_24h_pct'])} {abs(eth['chg_24h_pct']):.2f}%")
    if isinstance(cap.get("chg_24h_pct"), (int, float)) and isinstance(cap.get("usd"), (int, float)):
        tail.append(f"the whole crypto market cap is {_word(cap['chg_24h_pct'])} "
                    f"{abs(cap['chg_24h_pct']):.2f}%, at {sb.fmt_usd(cap['usd'])}")
    if tail:
        parts.append(f"{tail[0]} over the same 24 hours." if len(tail) == 1 else
                     f"{tail[0]}, and {tail[1]}, over the same 24 hours.")
    gains, falls = _movers(S.value(snap, "coins"))

    def names(rows):
        return ", ".join(f"{r['name']} ({r['chg']:+.2f}%)" for r in rows)
    if gains or falls:
        bits = []
        if gains:
            bits.append(f"the largest 24-hour gains are {names(gains)}")
        if falls:
            bits.append(f"the largest 24-hour declines are {names(falls)}")
        parts.append("Among the top 100 coins, " + "; ".join(bits) + ".")
    answer = [{"text": t, "lifted": False, "gated": True} for t in
              (_gated(gate, "the daily answer", " ".join(parts), drops),) if t]
    # ... or lifted from the read when the read itself says what moved, how much, in what window
    read_label, read_url, read_sents, read_head = "", "", [], ""
    if slot == "morning" and morning and morning.get("sentences"):
        read_label, read_sents = "Morning read", [s for s in morning["sentences"]]
        read_head = morning.get("headline") or ""
    elif slot == "evening" and edition:
        read_label = "Evening Edition"
        read_url = f"/articles/{edition.get('slug')}.html" if edition.get("slug") else ""
        body = edition.get("body") or []
        body = body if isinstance(body, list) else [str(body)]
        read_sents = _sentences(" ".join(x for x in [edition.get("dek") or ""] + body[:1]))
        read_head = edition.get("title") or ""
    kept = []
    for s in read_sents:
        if not _law_ok(s):
            drops.append({"surface": "the daily answer, " + read_label.lower(), "sentence": s,
                          "why": "copy law: a causal phrase, a prediction, advice or a dash",
                          "kind": "law"})
            continue
        why = day_claim_wrong(s, snap)
        if why:
            drops.append({"surface": "the daily answer, " + read_label.lower(), "sentence": s,
                          "why": why, "kind": "wrong"})
            continue
        g = _gated(gate, f"the daily answer, {read_label.lower()}", s, drops)
        if g == s:
            kept.append(s)
    lifted = [s for s in kept if re.search(r"\bBitcoin\b", s) and re.search(r"\d+(\.\d+)?%", s)
              and re.search(r"24[- ]hours?|overnight|past day|on the day", s, re.I)]
    if lifted:                        # passes as it stands and says what moved, how much, when
        answer = [{"text": " ".join(lifted[:2]), "lifted": True, "gated": True}]
    context = [{"text": s, "from": read_label, "url": read_url, "gated": True}
               for s in kept[:CONTEXT_MAX] if s not in " ".join(a["text"] for a in answer)]

    wire_items, wire_stamp = _wire(wire, iso, gate, drops)
    published = (morning or {}).get("published_utc") if slot == "morning" else (edition or {}).get("published_utc")
    written = published if (read_sents and published and et_date(published) == iso) else \
        now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if slot == "morning":
        label = f"Morning read, {et_time(written)}" if written == published else f"Morning build, {et_time(written)}"
    else:
        label = f"Evening Edition, {et_time(written)}" if written == published else f"Evening build, {et_time(written)}"
    import home
    nb = home.next_brief(None, _utc(written))
    nxt = nb.replace("Next Brief", "Next update", 1)
    return {"date_et": iso, "slot": slot, "frozen": slot == "evening",
            "first_utc": written, "written_utc": written, "stamp_label": label,
            "snapshot_stamp_et": stamp_et, "direction": dn,
            "btc": {"price": btc["price"], "chg": chg},
            "eth": {"price": eth.get("price"), "chg": eth.get("chg_24h_pct")},
            "cap": {"usd": cap.get("usd"), "chg": cap.get("chg_24h_pct")},
            "gainers": gains, "decliners": falls, "answer": answer, "context": context,
            "read": {"label": read_label, "headline": read_head, "url": read_url},
            "board": _board(snap, pulse, gate, drops, stamp_et),
            "wire": wire_items, "wire_stamp": wire_stamp, "next": nxt, "drops": drops,
            "corrections": []}


# ---- storage -------------------------------------------------------------------------------

def path_for(iso, d=None):
    return os.path.join(d or DIR, f"{iso}.json")


def load_all(d=None):
    d = d or DIR
    out = []
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", n):
                try:
                    out.append(json.load(open(os.path.join(d, n), encoding="utf-8")))
                except (OSError, ValueError):
                    print(f"::warning::today: {n} is unreadable and is skipped")
    return sorted(out, key=lambda r: r.get("date_et", ""))


def write(rec, d=None, correction=None):
    """(ok, why). A day whose evening record exists is frozen: the only write it takes is a
    correction, which is kept on the page with its time."""
    d = d or DIR
    p = path_for(rec["date_et"], d)
    old = None
    if os.path.exists(p):
        try:
            old = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            old = None
    if old:
        if old.get("frozen") and not correction:
            return False, f"{rec['date_et']} is frozen at its evening build"
        if old.get("slot") == "evening" and rec.get("slot") == "morning":
            return False, "a morning record never replaces the evening one"
        rec["first_utc"] = old.get("first_utc") or rec["first_utc"]
        rec["corrections"] = list(old.get("corrections") or [])
    if correction:
        if not old:
            return False, "there is nothing to correct"
        rec = dict(old)
        rec["corrections"] = list(old.get("corrections") or []) + [
            {"note": correction, "at_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}]
        rec["written_utc"] = rec["corrections"][-1]["at_utc"]
    os.makedirs(d, exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return True, ""


# ---- the page ------------------------------------------------------------------------------

def archive_dates(recs, upto, living):
    dates = sorted({r["date_et"] for r in recs if r["date_et"] <= upto})
    return dates[-7:]


def _coin_href(sym):
    return "/coins/" + str(sym).lower()


def _chg(v):
    cls = "up" if v and v > 0 else "down" if v and v < 0 else ""
    return f'<span class="h-mc {cls}">{v:+.2f}%</span>' if isinstance(v, (int, float)) else ""


def _sent(entry):
    if entry.get("gated") is not True:
        raise ValueError("an ungated sentence reached the page")
    return _e(entry["text"])


def render(rec, recs, living=False):
    """{title, desc, h1, body, schema, path, canonical} for one record; pure."""
    iso = rec["date_et"]
    h1, title = headline(rec["direction"], iso)
    answer = "".join(f'<p class="td-ans">{_sent(a)}</p>' for a in rec["answer"])
    ctx = ""
    if rec["context"]:
        src = rec["context"][0]
        lab = _e(src.get("from") or "The read")
        link = (f' <a href="{_e(src["url"])}">Read the {lab.lower()}</a>' if src.get("url") else "")
        ctx = (f'<p class="td-from"><b>From the {lab.lower()}.</b> '
               + " ".join(_sent(c) for c in rec["context"]) + link + "</p>")
    corr = "".join(f'<p class="td-corr"><b>Correction, {_e(et_time(c["at_utc"]))} ET on '
                   f'{_e(et_date(c["at_utc"]))}.</b> {_e(c["note"])}</p>' for c in rec.get("corrections") or [])

    def mrow(name, sym, price, chg):
        nm = f'<a href="{_coin_href(sym)}">{_e(name)}</a>'
        pr = f'<span class="td-v">{_e(price)}</span>' if price else '<span class="td-v"></span>'
        return f'<li>{nm}{pr}{_chg(chg)}</li>'
    core = [mrow("Bitcoin", "BTC", usd_price(rec["btc"]["price"]), rec["btc"]["chg"])]
    if isinstance(rec["eth"].get("chg"), (int, float)):
        core.append(mrow("Ether", "ETH", usd_price(rec["eth"]["price"]), rec["eth"]["chg"]))
    if isinstance(rec["cap"].get("chg"), (int, float)):
        import site_build as sb
        core.append(f'<li><span>Total market cap</span><span class="td-v">{_e(sb.fmt_usd(rec["cap"]["usd"]))}</span>'
                    f'{_chg(rec["cap"]["chg"])}</li>')

    def mlist(rows):
        return "<ul class=\"td-moved\">" + "".join(
            mrow(r["name"], r["symbol"], "", r["chg"]) for r in rows) + "</ul>"
    moved = (f'<section class="h-b td-moved-b" data-block="moved"><h2 class="h-h">What moved</h2>'
             f'<p class="td-w">Price change over 24 hours, as of {_e(rec["snapshot_stamp_et"])}. Source: CoinGecko.</p>'
             f'<ul class="td-moved">{"".join(core)}</ul>'
             + (f'<h3 class="td-h3">Biggest gains in the top 100</h3>{mlist(rec["gainers"])}' if rec["gainers"] else "")
             + (f'<h3 class="td-h3">Biggest declines in the top 100</h3>{mlist(rec["decliners"])}' if rec["decliners"] else "")
             + '</section>')

    if rec["wire"]:
        lis = []
        for w in rec["wire"]:
            bits = [f'{w["sources"]} source{"" if w["sources"] == 1 else "s"}']
            if w.get("primary"):
                bits.append('<span class="h-prim">Primary source</span>')
            bits += [f'<a href="{_e(o["url"])}" rel="noopener">{_e(o["outlet"])}</a>' for o in w["outlets"]]
            if w.get("time"):
                bits.append(_e(w["time"]))
            lis.append(f'<li class="h-wi"><span class="h-wl">{_e(w["line"])}</span>'
                       f'<span class="h-wmeta">{" &middot; ".join(bits)}</span></li>')
        reported = (f'<ol class="h-wire">{"".join(lis)}</ol>'
                    f'<p class="td-w">The wire ranked {_e(rec["wire_stamp"])}. Each line is the desk\'s own '
                    f'one-line summary of a story, with its sources linked beside it. It is shown next to the '
                    f'move and is not offered as its explanation.</p>')
    else:
        reported = '<p class="h-wait">No wire item has been ranked today yet.</p>'
    beside = f'<section class="h-b" data-block="reported"><h2 class="h-h">What was reported beside it</h2>{reported}</section>'

    brows = []
    for b in rec["board"]:
        fig = f'<span class="td-bf {b["dir"]}">{_e(b["figure"])}</span>'
        brows.append(f'<li><span class="td-bl">{_e(b["label"])}</span>{fig}'
                     f'<span class="td-bw">{_e(b["window"])}. {_e(b["source"])}, {_e(b["stamp"])}.</span></li>')
    board = (f'<section class="h-b" data-block="board"><h2 class="h-h">The Board</h2>'
             + (f'<ul class="td-board">{"".join(brows)}</ul>' if brows else '<p class="h-wait">Waiting for the Board\'s readings.</p>')
             + '</section>')

    stamp = (f'<section class="h-b" data-block="stamp"><p class="td-stamp">{_e(rec["stamp_label"])} '
             f'on {_e(long_date(iso))}. {_e(rec["next"])}.</p></section>')

    dates = archive_dates(recs, iso, living)
    items = []
    for dd in reversed(dates):
        if dd == iso and not living:
            items.append(f'<li aria-current="page">{_e(long_date(dd))}</li>')
        else:
            items.append(f'<li><a href="/today/{dd}">{_e(long_date(dd))}</a></li>')
    arch = (f'<nav class="h-b td-archive" aria-label="Earlier days" data-block="archive"><h2 class="h-h">Earlier days</h2>'
            f'<ul>{"".join(items)}</ul></nav>')

    eyebrow = "THE DAILY ANSWER" + (" · LIVE" if living else "")
    body = (f'<main class="wrap h-page td-page"><section class="page">'
            f'<p class="h-eye">{_e(eyebrow)}</p><h1 class="td-h1">{_e(h1)}</h1>'
            f'<section class="h-b td-answer" data-block="answer">{answer}{ctx}{corr}</section>'
            f'{moved}{beside}{board}{stamp}{arch}</section></main>')
    path = "/today/" if living else f"/today/{iso}.html"
    url = ORIGIN + ("/today/" if living else f"/today/{iso}")
    desc = rec["answer"][0]["text"] if rec["answer"] else h1
    desc = desc if len(desc) <= 300 else desc[:297].rstrip() + "..."
    return {"title": title, "h1": h1, "desc": desc, "body": body, "path": path, "url": url,
            "schema": schema(rec, h1, desc, url)}


def schema(rec, h1, desc, url):
    from site_build import FAMILY, NAME, OG_IMAGE
    first, mod = et_iso(rec["first_utc"]), et_iso(rec["written_utc"])
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "NewsArticle", "headline": h1, "description": desc, "url": url,
         "mainEntityOfPage": url, "image": OG_IMAGE, "datePublished": first, "dateModified": mod,
         "author": {"@type": "Organization", "name": NAME, "url": ORIGIN + "/news.html"},
         "publisher": {"@type": "Organization", "@id": ORIGIN + "/#publisher", "name": FAMILY,
                       "url": ORIGIN + "/",
                       "logo": {"@type": "ImageObject", "url": ORIGIN + "/publisher-logo-512.png",
                                "width": 512, "height": 512}}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": ORIGIN + "/"},
            {"@type": "ListItem", "position": 2, "name": "The daily answer", "item": ORIGIN + "/today/"},
            {"@type": "ListItem", "position": 3, "name": h1, "item": url}]}]}
    return '\n<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def sitemap_entries(recs):
    """[(path, lastmod)]: /today/ with the newest record's real time, each dated page with its own."""
    if not recs:
        return []
    newest = recs[-1]
    out = [("/today/", newest["written_utc"])]
    out += [(f"/today/{r['date_et']}.html", r["written_utc"]) for r in reversed(recs)]
    return out


def waiting_page():
    return {"title": "The daily answer", "h1": "The daily answer",
            "desc": "Why crypto moved today, answered twice a day from the Board and the wire.",
            "body": '<main class="wrap h-page td-page"><section class="page"><p class="h-eye">THE DAILY ANSWER</p>'
                    '<h1 class="td-h1">The daily answer</h1><p class="h-wait">The first answer arrives with the '
                    'next morning read or evening Edition.</p></section></main>',
            "path": "/today/", "url": ORIGIN + "/today/", "schema": ""}


# ---- the workflow entry --------------------------------------------------------------------

def _j(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def latest_evening_edition(now, content=None, hours=8):
    """The evening Edition this run wrote, or None. Only an Edition published in the last eight
    hours, between 6 PM and 5 AM Eastern, freezes a day: a breaking run at 2 PM never does."""
    content = content or os.path.join(HERE, "site", "content")
    best = None
    for n in sorted(os.listdir(content)) if os.path.isdir(content) else []:
        if not n.endswith("-evening-brief.json"):
            continue
        try:
            it = json.load(open(os.path.join(content, n), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pub = _utc(it.get("published_utc"))
        if not pub or not 0 <= (now - pub).total_seconds() <= hours * 3600:
            continue
        h = pub.astimezone(ET).hour
        if h >= 18 or h < 5:
            best = it
    return best


def main(argv=None):
    argv = argv or sys.argv[1:]
    if "--correct" in argv:
        i = argv.index("--correct")
        iso, note = argv[i + 1], argv[i + 2]
        ok, why = write({"date_et": iso}, correction=note)
        print("today: correction recorded" if ok else f"::warning::today: {why}")
        return 0 if ok else 1
    if "--write" not in argv:
        print(__doc__)
        return 2
    slot = argv[argv.index("--write") + 1]
    now = _dt.datetime.now(_dt.timezone.utc)
    import snapshot as S
    import twins_gate
    data = os.path.join(HERE, "site", "data")
    pulse, flows = _j(os.path.join(data, "pulse.json")), _j(os.path.join(data, "flows.json"))
    snap = S.build(pulse, flows)
    gate = twins_gate.Gate(snap)
    morning = _j(os.path.join(data, "morning.json"))
    if morning and morning.get("date_et") != now.astimezone(ET).date().isoformat():
        morning = None
    edition, iso = None, None
    if slot == "evening":
        edition = latest_evening_edition(now)
        if not edition:
            print("today: no evening Edition in the last 8 hours (a breaking run, or the slot has not run); "
                  "the day is not frozen")
            return 0
        iso = edition.get("date") or et_date(edition.get("published_utc"))
    rec = build_record(snap, pulse, _j(os.path.join(data, "wire.json")), morning, edition, slot, now, gate, iso)
    if not rec:
        print("::warning::today: Bitcoin has no 24h change in the snapshot; no daily answer written")
        return 0
    gate.save()
    ok, why = write(rec)
    print(f"today: {rec['date_et']} {slot} written ({rec['direction']}; {len(rec['drops'])} sentence(s) dropped)"
          if ok else f"today: not written: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
