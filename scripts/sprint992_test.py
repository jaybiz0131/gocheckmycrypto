#!/usr/bin/env python3
"""Sprint 9.9.2 (October 27, 2026): one fact once. Each case is named after what it guards.

  python3 scripts/sprint992_test.py                          # unit cases; exit 1 on any failure
  python3 scripts/sprint992_test.py --tree <dir> [--data <dir>]  # also the whole-site sweep of a built tree
  python3 scripts/sprint992_test.py --sweep <dir> [--data <dir>] # the sweep alone, every finding printed by page
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote, with the data it read)

The definition of done (docs/BOARD.md, 9.9.2): a canary check that fails on any figure printed twice on any page and on
any derived figure whose precision differs from its row, seen red on today's production copy first; the sweep's count of
fixes in the report. The sweep is one_fact.py: every page in the sitemaps, not a sample.

The HTML in the checker cases below is SYNTHETIC, written for the case and labeled so; the tree cases read a real build.
NO MODEL CALL and no network anywhere.
"""
import contextlib
import datetime as dt
import html as _html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc
EM = re.compile("[\u2013\u2014]")


def guarded(fails, msg, fn):
    try:
        ok = bool(fn())
    except Exception as e:                                   # noqa: BLE001
        ok, msg = False, f"{msg} [{type(e).__name__}: {str(e)[:90]}]"
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def group(fails, name, fn):
    try:
        fn(fails)
    except Exception as e:                                   # noqa: BLE001
        msg = f"group {name} could not run [{type(e).__name__}: {str(e)[:100]}]"
        print("  FAIL " + msg)
        fails.append(msg)


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf


def visible(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h or "", flags=re.S | re.I)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def page(body):
    """A SYNTHETIC page around a body."""
    return f"<!doctype html><html><head><title>t</title></head><body><main>{body}</main></body></html>"


def kinds(h):
    import one_fact
    return [k for k, _t in one_fact.page_findings(page(h))]


# ---- 1. the checker: what is a twin and what is not ---------------------------------------------------------------------

def checker_cases(fails):
    print("1. the checker (SYNTHETIC pages): a figure printed twice is red; two facts that share a number are not")
    import one_fact
    guarded(fails, "a tile and a sentence printing one figure are a twin",
            lambda: kinds('<p>ETFs took in $110.3M on the day.</p><article class="tl"><h3>ETF flows</h3>'
                          '<p class="tl-f">+$110.3M</p></article>') == ["twin"])
    guarded(fails, "'$110.3 million' in words and '$110.3M' on a tile are one figure",
            lambda: kinds('<p>ETFs took in $110.3 million.</p><p>ETF flows +$110.3M</p>') == ["twin"])
    guarded(fails, "a percentage in the answer and in its own table row is a twin (the row's subject named in the sentence)",
            lambda: kinds('<p>Ether was down 0.64% over the same 24 hours.</p><ul><li>Ether <span>$2,313</span> '
                          '<span>0.64%</span></li></ul>') == ["twin"])
    guarded(fails, "two coins in one table that fell the same amount are two facts",
            lambda: kinds('<table><tr><td>SOL</td><td>-0.6%</td></tr><tr><td>XRP</td><td>-0.6%</td></tr></table>') == [])
    guarded(fails, "a row's figure beside a sentence about another subject is not a twin (the subject floor)",
            lambda: kinds('<p>In the next 60 minutes Bitcoin fell 1.00%.</p><ul><li>Ether <span>1.00%</span></li></ul>') == [])
    guarded(fails, "a figure a stored read repeats inside itself is the read's (J-10), not a twin",
            lambda: kinds('<div data-read><h1>Conduit sues over $2.76 million</h1><p>The $2.76 million was frozen.</p></div>') == [])
    guarded(fails, "a stored read and the page's own tile printing one figure are a twin",
            lambda: kinds('<div data-read><p>The index reads 48, and ETFs took in $5.1 million.</p></div>'
                          '<p class="tl-f">+$5.1M</p>') == ["twin"])
    guarded(fails, "two records of a declared list (data-records) are two facts",
            lambda: kinds('<div data-records><div><p>Whales moved $1.5 billion.</p></div><div><p>Inflows hit $1.5 billion.</p></div></div>') == [])
    guarded(fails, "a price and a 7-day high close that are both $1.00 are two facts (named as different quantities)",
            lambda: kinds('<p>Seven days. 7D high close $1.00, 7D low close $0.9998.</p><article><h3>Price</h3><p>$1.00</p></article>') == [])
    guarded(fails, "the Ether line shown only from 1280 and the Ether tile shown only under 1280 print once at each width",
            lambda: kinds('<p data-wide>Ether $2,312.84</p><ul><li data-narrow>Ether $2,312.84</li></ul>') == [])
    guarded(fails, "...and the same pair with neither marked is a twin at every width",
            lambda: kinds('<p>Ether $2,312.84</p><ul><li>Ether $2,312.84</li></ul>') == ["twin"])
    guarded(fails, "text in a hidden element or a screen-reader span is not printed",
            lambda: kinds('<p>$110.3M</p><p hidden>$110.3M</p><span class="sr-only">$110.3M</span>') == [])
    guarded(fails, "ONE 200-DAY VALUE PER PAGE: two different 200-day values are red",
            lambda: kinds('<p>200-day line $73,024.55</p><div><span>200-day average</span><span>$72,988.58</span></div>') == ["twin"])
    guarded(fails, "ONE RSI PER PAGE: a tile's RSI and a levels block's RSI are red, whatever the values",
            lambda: kinds('<article><h3>RSI (14)</h3><p>41</p></article><div><span>RSI (14)</span><span>40</span></div>') == ["twin"])
    guarded(fails, "ONE FEAR AND GREED PER PAGE: a sentence's reading and the gauge's are red",
            lambda: kinds('<p>The Fear &amp; Greed index reads 48, neutral.</p><div><div><p>48</p></div>'
                          '<div><p>Fear &amp; Greed</p><p>Neutral</p></div></div>') == ["twin"])
    guarded(fails, "PRECISION: a row printing a price at four decimals and an average at two is red",
            lambda: kinds('<table><tr><th>DOGE</th><td>$0.0771</td><td>$0.09</td></tr></table>') == ["precision"])
    guarded(fails, "...and a row at one precision is not",
            lambda: kinds('<table><tr><th>DOGE</th><td>$0.0771</td><td>$0.0867</td></tr></table>') == [])
    guarded(fails, "...a marked row (data-row) is read like a table row",
            lambda: kinds('<div data-row><p>Price $79,839.00</p><p>200-day line $73,024</p></div>') == ["precision"])
    guarded(fails, "a zero is not counted ($0 and 0.00% are printed by many unrelated rows)",
            lambda: kinds('<p>$0 shorts</p><p>0.00%</p><p>$0 longs</p><p>0.00%</p>') == [])
    # the data-aware rule: a stored average printed with more decimals than it carries
    tmp = tempfile.mkdtemp(prefix="s992-prec-")
    try:
        os.makedirs(os.path.join(tmp, "data"))
        os.makedirs(os.path.join(tmp, "site", "coins"))
        json.dump({"assets": [{"symbol": "DOGE", "price": 0.0771, "sma50": 0.09, "sma200": 0.086658}]},
                  open(os.path.join(tmp, "data", "pulse.json"), "w"))
        open(os.path.join(tmp, "site", "coins", "doge.html"), "w").write(
            page('<div data-row><p>Price $0.07711</p><p>50-day average $0.09000</p><p>200-day line $0.08666</p></div>'))
        r = one_fact.precision_findings(os.path.join(tmp, "site"), os.path.join(tmp, "data"))
        guarded(fails, "PRECISION, STORED: an average stored as 0.09 and printed $0.09000 is red (a rounding printed as the figure)",
                lambda: list(r) == ["/coins/doge"] and len(r["/coins/doge"]) == 1 and "sma50" in r["/coins/doge"][0][1])
        guarded(fails, "...and one stored at six decimals and printed at five is not",
                lambda: not any("sma200" in t for _k, t in r.get("/coins/doge", [])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # the sweep reads every page the sitemaps list, and names a listed page the tree lacks
    tmp = tempfile.mkdtemp(prefix="s992-sweep-")
    try:
        locs = "".join(f"<url><loc>https://gocheckmycrypto.com{u}</loc></url>" for u in ("/", "/a", "/b/", "/gone"))
        open(os.path.join(tmp, "sitemap-priority.xml"), "w").write(f"<urlset>{locs}</urlset>")
        open(os.path.join(tmp, "index.html"), "w").write(page("<p>$1.63B</p><p>-$1.63B</p>"))
        open(os.path.join(tmp, "a.html"), "w").write(page("<p>$1.63B</p>"))
        os.makedirs(os.path.join(tmp, "b"))
        open(os.path.join(tmp, "b", "index.html"), "w").write(page("<p>5.2%</p><p>5.2%</p>"))
        res, n = one_fact.sweep(tmp)
        guarded(fails, "the sweep reads every sitemap page (4 listed), finds the twin on / and on /b/, and names /gone missing",
                lambda: n == 4 and sorted(res) == ["/", "/b/", "/gone"] and res["/gone"][0][0] == "missing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- the tree this build wrote ------------------------------------------------------------------------------------------

def sweep_report(root, data_dir=None):
    import one_fact
    res, n = one_fact.sweep(root)
    if data_dir:
        for u, fs in one_fact.precision_findings(root, data_dir).items():
            res.setdefault(u, []).extend(fs)
    return res, n


def tree(root, data_dir=None):
    fails = []
    print("9. the whole site, every page in the sitemaps: one fact once, every derived figure at its row's precision")
    res, n = sweep_report(root, data_dir if data_dir is not None else os.path.join(HERE, "site", "data"))
    guarded(fails, f"the sweep read the sitemaps ({n} pages)", lambda: n >= 100)
    for u in sorted(res):
        for kind, t in res[u][:6]:
            fails.append(f"{u}: {kind}: {t[:300]}")
            print(f"  FAIL {u}: {kind}: {t[:300]}")
    if not res:
        print("  ok   no figure printed twice on any page, no derived figure off its row's precision")
    return fails


def unit(only=()):
    fails = []
    for name, fn in (("checker", checker_cases),):
        if only and name not in only:
            continue
        group(fails, name, fn)
    return fails


def main():
    args = sys.argv[1:]
    data = args[args.index("--data") + 1] if "--data" in args else None
    if "--sweep" in args:
        res, n = sweep_report(args[args.index("--sweep") + 1], data)
        for u in sorted(res):
            for kind, t in res[u]:
                print(f"{u}\t{kind}\t{t}")
        print(f"ONE FACT SWEEP: {n} pages read, {len(res)} with a finding, {sum(len(v) for v in res.values())} finding(s)")
        return 1 if res else 0
    only = args[args.index("--only") + 1].split(",") if "--only" in args else ()
    fails = unit(only)
    if "--tree" in args:
        fails += tree(args[args.index("--tree") + 1], data)
    print(f"\nSPRINT 9.9.2: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
