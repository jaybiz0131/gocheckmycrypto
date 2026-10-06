#!/usr/bin/env python3
"""desk_calendar.py: site/data/calendar.json, the Today line's data (6 October 2026).

Five sources of record, each named on every entry it makes, and nothing else:

  macro         FRED fred/release/dates, include_release_dates_with_no_data=true (key:
                FRED_API_KEY from the repository's secrets, passed by the workflow; without
                it the macro entries are absent and one placeholder names FRED)
  fomc          data/calendar/fomc-<year>.json, from the Federal Reserve's meeting page
  holiday       data/calendar/us-market-holidays-<year>.json, from the NYSE's page
  expiry        Deribit public/get_instruments and public/get_book_summary_by_currency
  difficulty    mempool.space /api/v1/difficulty-adjustment
  etf-deadline  Federal Register documents API, SEC notices on crypto exchange-traded
                products; the designated date read from a designation notice's text, or
                the statutory clock computed from a notice's publication date
  unlock        data/calendar/unlocks.json, hand-kept, entries only where a project's own
                page gives a date

Every entry: date, time_et (when the source gives one), title, kind, source {name, url},
read_utc, computed, computed_from. No entry exists without a source URL and a read stamp.

    python3 desk_calendar.py            # read the sources now and write the file
"""
import datetime as _dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "data", "calendar.json")
CAL_DIR = os.path.join(HERE, "data", "calendar")
UA = "GoCheckMyCrypto/1.0 (+https://gocheckmycrypto.com)"
HORIZON_DAYS = 120
KINDS = ("macro", "fomc", "expiry", "difficulty", "etf-deadline", "unlock", "holiday")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                  # pragma: no cover
    ET = _dt.timezone(_dt.timedelta(hours=-5))

# FRED release ids, read from FRED's public release pages (no key) on 2026-10-06 11:49Z.
FRED_RELEASES = [
    (10, "CPI", "Consumer Price Index", "https://fred.stlouisfed.org/release?rid=10"),
    (54, "PCE", "Personal Income and Outlays", "https://fred.stlouisfed.org/release?rid=54"),
    (50, "Jobs report", "Employment Situation", "https://fred.stlouisfed.org/release?rid=50"),
    (53, "GDP", "Gross Domestic Product", "https://fred.stlouisfed.org/release?rid=53"),
    (9, "Retail sales", "Advance Monthly Sales for Retail and Food Services",
     "https://fred.stlouisfed.org/release?rid=9"),
]
FRED_API = "https://api.stlouisfed.org/fred/release/dates"
DERIBIT = "https://www.deribit.com/api/v2/public/"
MEMPOOL = "https://mempool.space/api/v1/difficulty-adjustment"
FEDREG = "https://www.federalregister.gov/api/v1/documents.json"


def _utcnow():
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url, timeout=60, text=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return raw.decode("utf-8", "replace") if text else json.loads(raw)


def _clock(t):
    """A UTC instant as its ET date and '4:00 AM ET'."""
    e = t.astimezone(ET)
    return e.date().isoformat(), e.strftime("%-I:%M %p") + " ET"


def entry(date, title, kind, source_name, source_url, read_utc, time_et=None,
          computed=False, computed_from=None, **extra):
    assert kind in KINDS, kind
    e = {"date": date, "time_et": time_et, "title": title, "kind": kind,
         "source": {"name": source_name, "url": source_url}, "read_utc": read_utc,
         "computed": bool(computed), "computed_from": computed_from}
    e.update(extra)
    return e


# ---- macro: FRED --------------------------------------------------------------------

def fred_url(rid, key, today):
    return FRED_API + "?" + urllib.parse.urlencode({
        "release_id": rid, "api_key": key, "file_type": "json",
        "include_release_dates_with_no_data": "true", "realtime_start": today,
        "sort_order": "asc", "limit": "1000"})


def parse_fred(answer, rid, short, name, page, read_utc, today):
    out = []
    for r in (answer or {}).get("release_dates") or []:
        d = str(r.get("date") or "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= today and \
                int(r.get("release_id", rid)) == rid:
            out.append(entry(d, f"{short}: {name}", "macro", "FRED release dates",
                             f"https://fred.stlouisfed.org/releases/calendar?rid={rid}",
                             read_utc, release_id=rid, release_page=page))
    return out


def read_fred(today, key, fetch=_get):
    if not key:
        return [], "Macro release dates are waiting on FRED (api.stlouisfed.org " \
                   "fred/release/dates): no FRED key in this run."
    out = []
    for rid, short, name, page in FRED_RELEASES:
        read = _iso(_utcnow())
        out += parse_fred(fetch(fred_url(rid, key, today)), rid, short, name, page, read,
                          today)
    return out, ""


# ---- yearly files: FOMC and market holidays -----------------------------------------

def fomc_entries(today, root=CAL_DIR):
    out = []
    for fn in sorted(os.listdir(root)):
        if not re.fullmatch(r"fomc-\d{4}\.json", fn):
            continue
        d = json.load(open(os.path.join(root, fn), encoding="utf-8"))
        for m in d.get("meetings") or []:
            if m["end"] < today:
                continue
            sep = ", with a Summary of Economic Projections" if m.get("sep") else ""
            out.append(entry(m["start"], f"FOMC meeting begins ({m['as_printed'].rstrip('*')})",
                             "fomc", d["source_name"], d["source_url"], d["read_date"]))
            out.append(entry(m["end"], f"FOMC meeting concludes{sep}", "fomc",
                             d["source_name"], d["source_url"], d["read_date"]))
    return out


def holiday_entries(today, root=CAL_DIR):
    out = []
    for fn in sorted(os.listdir(root)):
        if not re.fullmatch(r"us-market-holidays-\d{4}\.json", fn):
            continue
        d = json.load(open(os.path.join(root, fn), encoding="utf-8"))
        for h in d.get("closed") or []:
            if h["date"] >= today:
                out.append(entry(h["date"], f"US stock markets closed: {h['holiday']}",
                                 "holiday", d["source_name"], d["source_url"], d["read_date"]))
        for h in d.get("early_close") or []:
            if h["date"] >= today:
                out.append(entry(h["date"], "US stock markets close early", "holiday",
                                 d["source_name"], d["source_url"], d["read_date"],
                                 time_et=h["time_et"]))
    return out


# ---- options expiries: Deribit --------------------------------------------------------

def _last_friday(y, m):
    nxt = _dt.date(y + (m == 12), m % 12 + 1, 1)
    d = nxt - _dt.timedelta(days=1)
    while d.weekday() != 4:
        d -= _dt.timedelta(days=1)
    return d


def parse_deribit(currency, instruments, book, read_utc, now):
    """The next monthly and the next quarterly expiry, each with open interest summed
    across every strike and both sides. Monthly is the listed expiry on the last Friday of
    its month; quarterly is that in March, June, September or December. Fields read:
    instruments' instrument_name and expiration_timestamp; book's instrument_name and
    open_interest."""
    exp = {}
    for i in (instruments or {}).get("result") or []:
        exp[i["instrument_name"]] = i["expiration_timestamp"]
    oi = {}
    for b in (book or {}).get("result") or []:
        ts = exp.get(b.get("instrument_name"))
        if ts is not None and isinstance(b.get("open_interest"), (int, float)):
            oi[ts] = oi.get(ts, 0.0) + b["open_interest"]
    future = sorted({t for t in exp.values() if t > now.timestamp() * 1000})

    def is_monthly(ts):
        d = _dt.datetime.fromtimestamp(ts / 1000, tz=_dt.timezone.utc).date()
        return d == _last_friday(d.year, d.month)
    monthly = next((t for t in future if is_monthly(t)), None)
    quarterly = next((t for t in future if is_monthly(t) and
                      _dt.datetime.fromtimestamp(t / 1000, tz=_dt.timezone.utc).month
                      in (3, 6, 9, 12)), None)
    out = []
    for label, ts in (("monthly", monthly), ("quarterly", quarterly)):
        if ts is None:
            continue
        t = _dt.datetime.fromtimestamp(ts / 1000, tz=_dt.timezone.utc)
        d, tm = _clock(t)
        amt = oi.get(ts, 0.0)
        name = "Bitcoin" if currency == "BTC" else "Ether"
        out.append(entry(
            d, f"Deribit {name} {label} options expiry, open interest "
               f"{amt:,.0f} {currency}", "expiry", "Deribit public API",
            f"{DERIBIT}get_book_summary_by_currency?currency={currency}&kind=option",
            read_utc, time_et=tm, open_interest=round(amt, 1), unit=currency,
            fields_read="get_instruments: instrument_name, expiration_timestamp; "
                        "get_book_summary_by_currency: instrument_name, open_interest"))
    return out


def read_deribit(now, fetch=_get):
    out = []
    for c in ("BTC", "ETH"):
        read = _iso(_utcnow())
        ins = fetch(f"{DERIBIT}get_instruments?currency={c}&kind=option&expired=false")
        book = fetch(f"{DERIBIT}get_book_summary_by_currency?currency={c}&kind=option")
        out += parse_deribit(c, ins, book, read, now)
    return out


# ---- difficulty: mempool.space -------------------------------------------------------

def parse_mempool(a, read_utc):
    ms = (a or {}).get("estimatedRetargetDate")
    if not isinstance(ms, (int, float)):
        return []
    d, tm = _clock(_dt.datetime.fromtimestamp(ms / 1000, tz=_dt.timezone.utc))
    ch = a.get("difficultyChange")
    rem = a.get("remainingBlocks")
    title = "Bitcoin difficulty adjustment"
    if isinstance(ch, (int, float)):
        title += f", estimated {ch:+.2f}%"
    if isinstance(rem, int):
        title += f", {rem:,} blocks to go"
    return [entry(d, title, "difficulty", "mempool.space", MEMPOOL, read_utc,
                  time_et=tm, computed=True,
                  computed_from="mempool.space's estimate (estimatedRetargetDate, "
                                "difficultyChange, remainingBlocks)",
                  next_retarget_height=a.get("nextRetargetHeight"))]


# ---- ETF decision deadlines: the Federal Register ------------------------------------

_ASSET = re.compile(r"\b(bitcoin|ether|ethereum|solana|xrp|litecoin|dogecoin|cardano|"
                    r"avalanche|avax|polkadot|sui|hedera|hbar|chainlink|tron|stellar|bnb|"
                    r"hyperliquid|aptos|crypto|cryptocurrency|digital asset)\b", re.I)
_PRODUCT = re.compile(r"\b(trust|etf|fund|exchange[- ]traded)\b", re.I)
_STAGE = re.compile(r"(notice of filing of|designation of a longer period|instituting "
                    r"proceedings|approv|disapprov|withdrawal)", re.I)
FEDREG_TERM = ('"proposed rule change" (bitcoin | ether | crypto | solana | xrp | '
               'litecoin | dogecoin | "digital asset")')


def fedreg_url(since, page=1):
    params = [("conditions[agencies][]", "securities-and-exchange-commission"),
              ("conditions[type][]", "NOTICE"), ("conditions[term]", FEDREG_TERM),
              ("conditions[publication_date][gte]", since), ("order", "newest"),
              ("per_page", "100"), ("page", str(page))]
    for f in ("title", "publication_date", "document_number", "html_url", "raw_text_url"):
        params.append(("fields[]", f))
    return FEDREG + "?" + urllib.parse.urlencode(params)


def is_crypto_etp(title):
    """A notice on an exchange-traded product holding a crypto asset, at a stage that
    sets or ends a Commission deadline. Not: filings effective on filing (no deadline),
    options on a product (not a product holding the asset)."""
    t = title or ""
    return bool(_ASSET.search(t) and _PRODUCT.search(t) and _STAGE.search(t)
                and not re.search(r"immediate effectiveness", t, re.I)
                and not re.search(r"\boptions?\b", t, re.I))


def stage_of(title):
    t = (title or "").lower()
    if "withdrawal" in t or "disapprov" in t and "whether to approve or disapprove" not in t:
        return "closed"
    if re.search(r"order (granting|approving)|accelerated approval|granting approval", t):
        return "closed"
    if "designation of a longer period" in t:
        return "designation-proceedings" if "proceedings" in t else "designation"
    if "instituting proceedings" in t:
        return "proceedings"
    if "notice of filing of" in t:
        return "filing"
    return ""


_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DESIGNATES = re.compile(r"designates\s+(" + _MONTHS + r")\s+(\d{1,2}),\s+(\d{4})", re.I)
_PUBLISHED = re.compile(r"published for comment in the Federal Register on\s+(" + _MONTHS +
                        r")\s+(\d{1,2}),\s+(\d{4})", re.I)
_FILE_NO = re.compile(r"File No\.\s*(SR-[A-Za-z]+-\d{4}-\d+)")


def _date(m):
    return _dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                 "%B %d %Y").date()


def add_days(iso, n):
    return (_dt.date.fromisoformat(iso) + _dt.timedelta(days=n)).isoformat()


def deadline(stage, pub, text):
    """(date, computed, computed_from) for one document, or None.

    Section 19(b)(2): 45 days from the notice's publication, extended to 90 by a
    designation; once proceedings are instituted, 180 days from publication, extended to
    240 by a designation. A designation that states its date is read from its own text."""
    m = _DESIGNATES.search(text or "")
    if stage.startswith("designation") and m:
        return _date(m).isoformat(), False, None
    orig = _PUBLISHED.search(text or "")
    base = _date(orig).isoformat() if orig else None
    if stage == "filing":
        return add_days(pub, 45), True, f"computed from the notice of {pub}: 45 days"
    if stage == "designation" and base:
        return add_days(base, 90), True, f"computed from the notice of {base}: 90 days"
    if stage == "proceedings" and base:
        return add_days(base, 180), True, f"computed from the notice of {base}: 180 days"
    if stage == "designation-proceedings" and base:
        return add_days(base, 240), True, f"computed from the notice of {base}: 240 days"
    return None


def fedreg_entries(docs, texts, today, read_utc):
    """docs: the search's results; texts: {document_number: raw text}. One entry per SR
    file, from its latest document, unless a later document closed it."""
    by_file = {}
    for d in docs:
        if not is_crypto_etp(d.get("title")):
            continue
        txt = texts.get(d["document_number"]) or ""
        fm = _FILE_NO.search(txt)
        key = fm.group(1).upper() if fm else d["document_number"]
        by_file.setdefault(key, []).append(d)
    out = []
    for key, ds in by_file.items():
        ds.sort(key=lambda x: x["publication_date"])
        last = ds[-1]
        st = stage_of(last["title"])
        if st in ("", "closed"):
            continue
        dl = deadline(st, last["publication_date"], texts.get(last["document_number"]))
        if not dl or dl[0] < today:
            continue
        date, computed, cfrom = dl
        name = re.sub(r"^Self-Regulatory Organizations;\s*", "", last["title"])
        name = re.split(r";\s*(?:Notice|Order)", name)[0]
        prod = re.search(r"(?:Shares of (?:the )?)(.+?)(?: [Uu]nder | Pursuant|,|$)",
                         last["title"])
        title = (f"SEC deadline: {prod.group(1) if prod else 'crypto exchange-traded product'}"
                 f" ({name}, {key})")
        out.append(entry(date, title, "etf-deadline", "Federal Register",
                         last["html_url"], read_utc, computed=computed,
                         computed_from=cfrom, document_number=last["document_number"],
                         sr_file=key))
    return out


def read_fedreg(today, fetch=_get):
    since = add_days(today, -250)
    read = _iso(_utcnow())
    first = fetch(fedreg_url(since))
    docs = list(first.get("results") or [])
    for p in range(2, int(first.get("total_pages") or 1) + 1):
        docs += fetch(fedreg_url(since, p)).get("results") or []
    kept = [d for d in docs if is_crypto_etp(d.get("title"))]
    texts = {}
    for d in kept:
        if d.get("raw_text_url"):
            texts[d["document_number"]] = fetch(d["raw_text_url"], text=True)
    return fedreg_entries(kept, texts, today, read), docs, kept


# ---- unlocks: hand-kept -------------------------------------------------------------

def unlock_entries(today, root=CAL_DIR):
    d = json.load(open(os.path.join(root, "unlocks.json"), encoding="utf-8"))
    out = []
    for p in d.get("projects") or []:
        u = p.get("next_unlock") or {}
        if u.get("date") and u["date"] >= today and p.get("source_url"):
            out.append(entry(u["date"], f"{p['symbol']} token unlock" +
                             (f", {u['amount']}" if u.get("amount") else "") +
                             (f" ({u['share']} of supply)" if u.get("share") else ""),
                             "unlock", f"{p['symbol']} project page", p["source_url"],
                             p.get("read_date"), time_et=u.get("time_et")))
    for ln in ((d.get("jack") or {}).get("lines") or []):
        if ln.get("date") and ln["date"] >= today and ln.get("source_url") and ln.get("title"):
            out.append(entry(ln["date"], ln["title"], "unlock", "added by the desk",
                             ln["source_url"], ln.get("added") or d.get("read_date"),
                             time_et=ln.get("time_et")))
    return out


# ---- the file -------------------------------------------------------------------------

def _tsort(e):
    t = e.get("time_et")
    if not t:
        return (e["date"], -1)
    hm = _dt.datetime.strptime(t.replace(" ET", ""), "%I:%M %p")
    return (e["date"], hm.hour * 60 + hm.minute)


def valid(e):
    """No entry without a source URL and a read stamp."""
    return bool(e.get("date") and e.get("title") and e.get("kind") in KINDS
                and (e.get("source") or {}).get("url") and e.get("read_utc"))


def today_line(entries, today):
    day = sorted((e for e in entries if e["date"] == today), key=_tsort)
    return {"date": today, "entries": day, "line": "" if day else "nothing scheduled"}


def assemble(entries, placeholders, now, statuses):
    today = now.astimezone(ET).date().isoformat()
    end = add_days(today, HORIZON_DAYS)
    good = [e for e in entries if valid(e) and today <= e["date"] <= end]
    dropped = [e for e in entries if not valid(e)]
    good.sort(key=_tsort)
    return {"generated_utc": _iso(now),
            "stamp_et": now.astimezone(ET).strftime("%-I:%M %p") + " ET on " +
            now.astimezone(ET).strftime("%b %-d"),
            "window": {"from": today, "to": end},
            "sources": statuses, "placeholders": placeholders,
            "dropped_without_source": len(dropped),
            "today": today_line(good, today), "entries": good}


def build(now=None, key=None):
    now = now or _utcnow()
    today = now.astimezone(ET).date().isoformat()
    entries, placeholders, statuses = [], [], []

    def run(name, fn):
        try:
            got = fn()
            statuses.append({"source": name, "status": "ok", "entries": len(got)})
            entries.extend(got)
        except Exception as e:
            statuses.append({"source": name, "status": f"failed: {e}"[:160], "entries": 0})
            print(f"::warning::calendar: {name} failed ({e}); its entries are absent")

    def fred():
        got, ph = read_fred(today, key)
        if ph:
            placeholders.append(ph)
        return got
    run("FRED release dates", fred)
    run("FOMC yearly file", lambda: fomc_entries(today))
    run("NYSE holidays yearly file", lambda: holiday_entries(today))
    run("Deribit", lambda: read_deribit(now))
    run("mempool.space", lambda: parse_mempool(_get(MEMPOOL), _iso(_utcnow())))
    fr = {}

    def fedreg():
        got, docs, kept = read_fedreg(today)
        fr.update(docs=docs, kept=kept)
        return got
    run("Federal Register", fedreg)
    run("unlocks file", lambda: unlock_entries(today))
    return assemble(entries, placeholders, now, statuses), fr


def main():
    cal, fr = build(key=os.environ.get("FRED_API_KEY", "").strip() or None)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(cal, fh, indent=1)
    by = {}
    for e in cal["entries"]:
        by[e["kind"]] = by.get(e["kind"], 0) + 1
    print(f"calendar: {len(cal['entries'])} entries {by}; today {cal['today']['date']}: "
          f"{len(cal['today']['entries']) or cal['today']['line']}")
    for p in cal["placeholders"]:
        print(f"calendar: {p}")
    if "-v" in sys.argv[1:]:
        print(f"Federal Register: {len(fr.get('docs') or [])} returned, "
              f"{len(fr.get('kept') or [])} kept; first ten kept:")
        for d in (fr.get("kept") or [])[:10]:
            print(f"  {d['publication_date']} {d['document_number']} {d['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
