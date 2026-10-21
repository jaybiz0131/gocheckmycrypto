#!/usr/bin/env python3
"""living_tables.py: the three C-C tables' data. A site-lane fetcher.

Each table is independent. A source that fails leaves the last good stored copy of its
table in the file, with its own as-of stamp, and its page is built from that copy and marked
stale (hotfix 9.6h). Nothing here interpolates or fills.

  1. ETF flows by issuer      Farside, the same table the Board's aggregate comes from
  2. Stablecoin supply by issuer  DefiLlama, the same source the dry-powder tile uses
  3. Whale Watch history by week  flows.json, which already carries weekly history

ON FARSIDE AND WHY THE PARSER IS DEFENSIVE. The page answers 403 to this machine's
egress and serves fine from a CI runner, which is the CHALLENGED class this family has
documented twice. So the issuer parser is written to prove itself before it publishes:
it must find a header row naming the funds AND data rows whose per-fund cells sum to
roughly the total column, or it returns nothing. A scrape of a page I cannot see is
otherwise a guess with a table around it.

USAGE  python3 living_tables.py          refresh
       python3 living_tables.py --report read the committed file
"""

import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "site", "data", "living-tables.json")
FLOWS = os.path.join(HERE, "site", "data", "flows.json")
FARSIDE = "https://farside.co.uk/btc/"
LLAMA = "https://stablecoins.llama.fi/stablecoins?includePrices=false"
UA = "Mozilla/5.0 (compatible; GoCheckMyCrypto/1.0; +https://gocheckmycrypto.com)"
TIMEOUT = 30
STALE_HOURS = 30
MIN_ROWS = 4          # a table below this is not a table


def _get(url, as_json=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw.decode("utf-8", "replace")


def _num(s):
    s = (s or "").replace(",", "").replace("$", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s in ("", "-", "&nbsp;"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def etf_by_issuer():
    """Per-fund daily flows. Proves the shape before publishing: the fund cells must
    reconcile to the total column, or this returns nothing."""
    try:
        html = _get(FARSIDE, as_json=False)
    except Exception as e:
        print(f"  etf_by_issuer: source unreachable ({type(e).__name__}); table omitted")
        return None
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    header, data = None, []
    for tr in rows:
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) < 4:
            continue
        if header is None and not re.match(r"^\d{1,2} \w{3} \d{4}$", cells[0]):
            # the first wide non-date row names the funds
            names = [c for c in cells[1:-1] if c and not _num(c)]
            if len(names) >= 3:
                header = names
            continue
        if re.match(r"^\d{1,2} \w{3} \d{4}$", cells[0]):
            total = _num(cells[-1])
            funds = [_num(c) for c in cells[1:-1]]
            if total is None or len(funds) != len(header or []):
                continue
            got = [f for f in funds if f is not None]
            if not got:
                continue
            # THE PROOF: the parts must add up to the whole, within rounding.
            if abs(sum(got) - total) > max(1.0, abs(total) * 0.02):
                continue
            data.append({"date": cells[0], "total_usd_m": total,
                         "funds": {h: v for h, v in zip(header, funds) if v is not None}})
    if not header or len(data) < MIN_ROWS:
        print(f"  etf_by_issuer: shape not proven ({len(data)} reconciled row(s)); "
              f"table omitted")
        return None
    data = data[-30:]
    print(f"  etf_by_issuer: {len(header)} issuers, {len(data)} days")
    return {"issuers": header, "days": data,
            "source": "Farside Investors, issuer filings"}


def stables_by_issuer(top=15):
    try:
        d = _get(LLAMA)
    except Exception as e:
        print(f"  stables_by_issuer: source unreachable ({type(e).__name__}); omitted")
        return None
    rows = []
    for a in d.get("peggedAssets") or []:
        cur = (a.get("circulating") or {}).get("peggedUSD")
        if not isinstance(cur, (int, float)) or cur <= 0:
            continue
        prev = (a.get("circulatingPrevWeek") or {}).get("peggedUSD")
        chg = None
        if isinstance(prev, (int, float)) and prev:
            chg = (cur / prev - 1) * 100
        rows.append({"symbol": a.get("symbol") or "", "name": a.get("name") or "",
                     "circulating_usd": round(cur), "chg_7d_pct": chg,
                     "peg": a.get("pegType") or ""})
    if len(rows) < MIN_ROWS:
        print("  stables_by_issuer: too few rows; omitted")
        return None
    rows.sort(key=lambda r: -r["circulating_usd"])
    total = sum(r["circulating_usd"] for r in rows)
    rows = rows[:top]
    for r in rows:
        r["share_pct"] = round(r["circulating_usd"] / total * 100, 2) if total else None
    print(f"  stables_by_issuer: {len(rows)} issuers of {total/1e9:.0f}B total")
    return {"rows": rows, "total_usd": total,
            "source": "DefiLlama stablecoin circulating supply"}


def whales_by_week():
    try:
        f = json.load(open(FLOWS, encoding="utf-8"))
    except Exception:
        return None
    h = [x for x in (f.get("history") or [])
         if isinstance(x.get("net_usd"), (int, float))]
    if len(h) < MIN_ROWS:
        print("  whales_by_week: too few weeks; omitted")
        return None
    print(f"  whales_by_week: {len(h)} weeks")
    return {"weeks": h, "source": "Whale Alert public feed, transfers of $50M and up"}


# Tables whose source answered during THIS process's refresh. None until a refresh has run;
# load() then falls back to the age of each table's own stamp.
FRESH = None

KEYS = ("etf_by_issuer", "stables_by_issuer", "whales_by_week")


def _iso_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_stored():
    """The committed file as it is, however old. None when absent or unreadable. Each
    table's own as-of stamp is in `fetched`; a file written before that map existed gives
    every table the file's own stamp."""
    try:
        d = json.load(open(OUT, encoding="utf-8"))
        tables = d["tables"]
        if not isinstance(tables, dict):
            return None
    except Exception:
        return None
    fetched = dict(d.get("fetched") or {})
    for k in tables:
        fetched.setdefault(k, d.get("fetched_at") or "")
    d["fetched"] = fetched
    return d


def refresh():
    """Fetch every table; keep the last good copy of any that fails (9.6h, October 21).

    A source that refuses leaves the stored table where it is, with its own as-of stamp,
    so the page for it is built from the last good read and marked stale, instead of the
    table being dropped from the file and the page answering 404. The file is rewritten
    only when at least one table was read fresh."""
    global FRESH
    stored = read_stored() or {"tables": {}, "fetched": {}}
    tables = dict(stored["tables"])
    fetched = dict(stored["fetched"])
    now = _iso_now()
    fresh = set()
    for key, fn in (("etf_by_issuer", etf_by_issuer),
                    ("stables_by_issuer", stables_by_issuer),
                    ("whales_by_week", whales_by_week)):
        t = fn()
        if t:
            tables[key] = t
            fetched[key] = now
            fresh.add(key)
        elif key in tables:
            print(f"  {key}: not read this run; the last good table (as of "
                  f"{fetched.get(key) or 'unknown'}) is kept")
    FRESH = fresh
    if not fresh:
        print("living_tables: nothing resolved; committed file left alone")
        return None
    payload = {"fetched_at": now, "fetched": fetched, "tables": tables}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    print(f"living_tables: {len(fresh)} of 3 table(s) read fresh, "
          f"{len(tables) - len(fresh)} kept from the last good read")
    return payload


def load():
    """The stored tables for the build, however old, with `stale` naming every table not
    read fresh by this process's refresh (or, with no refresh run, older than STALE_HOURS).
    A stale table is shown stale; it is never withheld."""
    d = read_stored()
    if d is None:
        return {"fetched_at": "", "fetched": {}, "tables": {}, "stale": list(KEYS)}
    now = datetime.datetime.now(datetime.timezone.utc)
    stale = []
    for k in d["tables"]:
        if FRESH is not None:
            if k not in FRESH:
                stale.append(k)
            continue
        try:
            t = datetime.datetime.strptime(d["fetched"][k], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc)
            if (now - t).total_seconds() / 3600 > STALE_HOURS:
                stale.append(k)
        except Exception:
            stale.append(k)
    d["stale"] = stale
    return d


def main():
    d = load() if "--report" in sys.argv else refresh()
    print("living_tables:", sorted((d or {}).get("tables", {})) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
