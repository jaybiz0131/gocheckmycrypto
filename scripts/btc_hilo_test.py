#!/usr/bin/env python3
"""One figure, one source: Bitcoin's high and low on the home page and on /coins/btc
(Jack, 5 October ruling; 13 October 2026).

Reads the BUILT home page and the BUILT /coins/btc and fails when
  1. the 24h high or low on the two pages differ, or one page has them and the other does not;
  2. the 7D high or low on the two pages differ (the tape's HIGH and LOW are the seven stored
     daily closes; /coins/btc used to print a second pair from the hourly sparkline);
  3. a high or low is printed without its window ("HIGH", "High $"): every one says 7D or 24h.

  python3 scripts/btc_hilo_test.py            # builds a throwaway tree, then checks it (minutes)
  python3 scripts/btc_hilo_test.py --fast     # renders the home tape and /coins/btc's chart block
                                              # from the same snapshot (a second; the canary's)
  python3 scripts/btc_hilo_test.py --tree DIR # checks an already built tree (the canary's own)

The throwaway build carries Bitcoin's REAL 24-hour pair, recorded from CoinGecko /coins/markets
at 2026-10-13T23:04:42Z (fixtures/coingecko/markets_bitcoin_2026-10-13T2304Z.json): high 84,074,
low 81,018. The committed pulse.json predates the field. Exit 1 on any failure.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

MONEY = r"\$([\d,]+(?:\.\d+)?)"


def _n(s):
    return float(s.replace(",", ""))


def read_home(html):
    out = {"hl24": None, "hi7": None, "lo7": None, "unlabeled": False}
    m = re.search(r'data-hl24>24h high <b>' + MONEY + r'</b> · low <b>' + MONEY + r'</b>', html)
    if m:
        out["hl24"] = (_n(m.group(2)), _n(m.group(1)))      # (low, high)
    hi = re.search(r'h-k-hi[^"]*"[^>]*>([^<]*?)<b>' + MONEY + '</b>', html)
    lo = re.search(r'h-k-lo[^"]*"[^>]*>([^<]*?)<b>' + MONEY + '</b>', html)
    if hi and lo:
        out["hi7"], out["lo7"] = _n(hi.group(2)), _n(lo.group(2))
        out["unlabeled"] = not (hi.group(1).strip().upper().startswith("7D")
                                and lo.group(1).strip().upper().startswith("7D"))
    return out


def read_coin(html):
    out = {"hl24": None, "hi7": None, "lo7": None, "unlabeled": False}
    sec = re.search(r'<section class="cc"[^>]*>', html)
    attrs = dict(re.findall(r'data-(hi7|lo7|hi24|lo24)="([^"]+)"', sec.group(0))) if sec else {}
    if "hi24" in attrs and "lo24" in attrs:
        out["hl24"] = (float(attrs["lo24"]), float(attrs["hi24"]))
    cap = re.search(r'data-coin-cap>(.*?)</p>', html, re.S)
    cap = re.sub(r"<[^>]+>", "", cap.group(1)) if cap else ""
    m = re.search(r"7D high " + MONEY + r", 7D low " + MONEY, cap)
    if m:
        out["hi7"], out["lo7"] = _n(m.group(1)), _n(m.group(2))
    elif re.search(r"\b[Hh]igh \$|\b[Ll]ow \$", cap):
        out["unlabeled"] = True
        mm = re.search(r"[Hh]igh " + MONEY + r", low " + MONEY, cap)
        if mm:
            out["hi7"], out["lo7"] = _n(mm.group(1)), _n(mm.group(2))
    if "hi7" in attrs and "lo7" in attrs and out["hi7"] is None:
        out["hi7"], out["lo7"] = float(attrs["hi7"]), float(attrs["lo7"])
    return out


def check(home_html, coin_html, need_24h=False):
    """The failures (list of strings) for one pair of built pages."""
    h, c = read_home(home_html), read_coin(coin_html)
    fails = []
    for who, r in (("home page", h), ("/coins/btc", c)):
        if r["unlabeled"]:
            fails.append(f"{who}: a high or low is printed without its window (7D or 24h)")
    if h["hi7"] is None or c["hi7"] is None:
        fails.append(f"7D high/low missing: home {h['hi7']}, /coins/btc {c['hi7']}")
    elif round(h["hi7"]) != round(c["hi7"]) or round(h["lo7"]) != round(c["lo7"]):
        fails.append(f"7D high/low differ: home {h['hi7']:,.0f}/{h['lo7']:,.0f}, "
                     f"/coins/btc {c['hi7']:,.2f}/{c['lo7']:,.2f}")
    if need_24h and (h["hl24"] is None or c["hl24"] is None):
        fails.append(f"24h high/low missing: home {h['hl24']}, /coins/btc {c['hl24']}")
    elif (h["hl24"] is None) != (c["hl24"] is None):
        fails.append(f"24h high/low on one page only: home {h['hl24']}, /coins/btc {c['hl24']}")
    elif h["hl24"] and (round(h["hl24"][0]) != round(c["hl24"][0])
                        or round(h["hl24"][1]) != round(c["hl24"][1])):
        fails.append(f"24h low/high differ: home {h['hl24']}, /coins/btc {c['hl24']}")
    return fails


def build_tree():
    """Build a throwaway site whose pulse.json carries Bitcoin's recorded 24h pair."""
    import site_build as sb
    fx = json.load(open(os.path.join(HERE, "fixtures", "coingecko",
                                     "markets_bitcoin_2026-10-13T2304Z.json"), encoding="utf-8"))[0]
    real_pub, real_lp = sb.PUBLISH, sb.load_pulse
    tmp = tempfile.mkdtemp(prefix="btc-hilo-")
    data = os.path.join(HERE, "site", "data")
    saved = {}
    for root, _d, files in os.walk(data):
        for f in files:
            p = os.path.join(root, f)
            saved[p] = open(p, "rb").read()

    def patched():
        p = real_lp()
        for r in ((p.get("movers") or {}).get("top100")) or []:
            if r.get("symbol") == "BTC":
                r["high_24h"], r["low_24h"] = fx["high_24h"], fx["low_24h"]
        return p
    sb.PUBLISH, sb.load_pulse = os.path.join(tmp, "publish"), patched
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            sb.build()
        out = sb.PUBLISH
        home = open(os.path.join(out, "index.html"), encoding="utf-8").read()
        coin = open(os.path.join(out, "coins", "btc.html"), encoding="utf-8").read()
        return home, coin
    finally:
        sb.PUBLISH, sb.load_pulse = real_pub, real_lp
        for p, b in saved.items():                       # put back what the build rewrote
            if os.path.exists(p) and open(p, "rb").read() != b:
                open(p, "wb").write(b)
        keep = os.environ.get("BTC_HILO_KEEP")          # a copy of the built tree, for the screenshots
        if keep and os.path.isdir(os.path.join(tmp, "publish")):
            shutil.rmtree(keep, ignore_errors=True)
            shutil.copytree(os.path.join(tmp, "publish"), keep)
        shutil.rmtree(tmp, ignore_errors=True)


def fast_pages():
    """The home tape and /coins/btc's chart block, rendered from ONE snapshot built from the
    committed Board files with Bitcoin's recorded 24h pair put in its row."""
    import home
    import site_build as sb
    import snapshot
    fx = json.load(open(os.path.join(HERE, "fixtures", "coingecko",
                                     "markets_bitcoin_2026-10-13T2304Z.json"), encoding="utf-8"))[0]
    j = lambda n: json.load(open(os.path.join(HERE, "site", "data", n), encoding="utf-8"))
    pulse, flows = j("pulse.json"), j("flows.json")
    row = [r for r in pulse["movers"]["top100"] if r.get("symbol") == "BTC"][0]
    row["high_24h"], row["low_24h"] = fx["high_24h"], fx["low_24h"]
    snap = snapshot.build(pulse, flows)
    real = sb.SNAP
    sb.SNAP = snap
    try:
        return (home.tape(snap),
                sb.render_coin_chart(row, row.get("name") or "Bitcoin", row.get("gecko_id") or "bitcoin",
                                     row.get("spark7d") or []))
    finally:
        sb.SNAP = real


def main():
    if "--fast" in sys.argv:
        home, coin = fast_pages()
        need = True
    elif "--tree" in sys.argv:
        d = sys.argv[sys.argv.index("--tree") + 1]
        home = open(os.path.join(d, "index.html"), encoding="utf-8").read()
        coin = open(os.path.join(d, "coins", "btc.html"), encoding="utf-8").read()
        need = False
    else:
        home, coin = build_tree()
        need = True
    fails = check(home, coin, need_24h=need)
    h, c = read_home(home), read_coin(coin)
    print(f"home:      24h {h['hl24']}  7D hi/lo {h['hi7']}/{h['lo7']}  unlabeled={h['unlabeled']}")
    print(f"/coins/btc: 24h {c['hl24']}  7D hi/lo {c['hi7']}/{c['lo7']}  unlabeled={c['unlabeled']}")
    for f in fails:
        print("FAIL", f)
    print("ok: one figure, one source" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


# the pair is (low, high) everywhere in this file
if __name__ == "__main__":
    sys.exit(main())
