#!/usr/bin/env python3
"""
one_fact.py: one fact once, measured on every page of the built site (Sprint 9.9.2, October 27, 2026).

The standing law (docs/BOARD.md): the same fact never prints twice. From 9.9.2 on the reviewer scores the site, not
the sprint, so this reads EVERY page the sitemaps list, not a sample, and answers two questions per page:

  1. TWINS. Is any figure printed twice? A figure is a dollar amount, a percentage or a basis-point figure as the
     page prints it, plus the labeled readings a bare number carries (RSI, Fear and Greed). Two prints of one figure
     are a twin unless the page itself says they are two facts:
       - both sit in one table or one list (table, ul, ol, dl): a table lists distinct things, so two coins that
         both fell 0.6% are two facts, not one fact twice;
       - both sit inside one stored read (an element marked data-read): an article, a Brief or a Chart Master read
         is printed as it was published and never reworded (J-10), so a figure its own text repeats is the read's;
       - a printed correction (an element marked data-quote) quotes the figures it corrects or confirms, as published,
         and is not read for figures at all.
     A figure in a table and the same figure outside it IS a twin (the /today/ answer restating its own table).
     ONE VALUE PER PAGE: the 200-day and 50-day averages, RSI and Fear and Greed print once per page outside a
     table, whatever the value: two different 200-day values on one page is the defect Review 1 found on /coins/btc.
  2. PRECISION. Does every price-level figure in a row print at the row's precision? A row is a table row or an
     element marked data-row (one asset's levels). A price-level figure is a plain dollar amount, no K, M, B or T.

WHAT A READER SEES, PER WIDTH. An element marked data-wide prints only from 1280 pixels; one marked data-narrow only
under 1280 (the stylesheet hides each at the other width). The page is read twice, once at each width, and a twin
at either width counts. Text in a hidden element, a screen-reader-only span, a script, a style or an SVG is not
printed and is not read.

Zero values are not counted (a $0 or a 0.00% is printed by many unrelated rows). Nothing here reads the network or
spends a model call.
"""
import html as _html
import os
import re
from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "svg", "noscript", "template", "head", "title", "iframe", "select", "math"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
GRID_TAGS = {"table", "ul", "ol", "dl"}
BLOCK_TAGS = {"p", "li", "tr", "td", "th", "div", "article", "section", "aside", "dd", "dt", "figcaption",
              "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer", "nav", "main", "figure", "body",
              "caption", "summary", "details", "form", "label", "button"}

_MAG = r"(?:\s?(?:[KMBT]\b|thousand\b|million\b|billion\b|trillion\b))"
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)" + r"(" + _MAG + r")?")
PCT = re.compile(r"(?<![\w.,])(\d[\d,]*(?:\.\d+)?)\s?(%|percent\b)")
BP = re.compile(r"(?<![\w.,])(\d+(?:\.\d+)?)\s?bp\b")
# a bare number standing alone in its element is a figure; what it is, the label around it says
BARE = re.compile(r"^\s*[+\-−]?(\d{1,3}(?:\.\d+)?)\s*$")
LABELS = (
    ("RSI", re.compile(r"\bRSI\b(?:[\s-]*\(?14\)?)?(?:\s+(?:of|at|is|reads|near))?\s+(\d{1,3}(?:\.\d+)?)\b(?!\s*(?:daily|days?)\b)")),
    ("Fear and Greed", re.compile(r"\bFear (?:&|and) Greed\b(?: [Ii]ndex)?(?:\s+(?:reads|at|of|is|stands at|was))?\s+(\d{1,3})\b")),
    ("Fear and Greed", re.compile(r"(?<![\w.,$])(\d{1,3})\s+Fear (?:&|and) Greed\b")),
)
NEXT_SLOT = re.compile(r"\bNext\b[^.|]{0,48}?\b\d{1,2}:\d{2}\s?[AP]M ET\b")
AVERAGES = (("200-day average", re.compile(r"200-day")), ("50-day average", re.compile(r"50-day")))
_MAG_NORM = {"thousand": "K", "million": "M", "billion": "B", "trillion": "T"}


class Node:
    __slots__ = ("tag", "attrs", "parent", "children", "text")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.text = tag, attrs, parent, [], None

    def has(self, a):
        return a in self.attrs

    def cls(self):
        return (self.attrs.get("class") or "").split()


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        t = Node("#text", {}, self.cur)
        t.text = data
        self.cur.children.append(t)


def parse(h):
    p = _Tree()
    p.feed(h)
    p.close()
    return p.root


def _printed(n, view):
    """False when this element does not print at this width (or at all)."""
    if n.tag in SKIP_TAGS or n.has("hidden"):
        return False
    c = n.cls()
    if "sr-only" in c or "visually-hidden" in c:
        return False
    if view == "narrow" and n.has("data-wide"):
        return False
    if view == "wide" and n.has("data-narrow"):
        return False
    return True


def _quoted(n):
    """An element marked data-quote: a published correction quoting the figures it corrects or confirms. It prints them to
    say what was wrong, and it is kept as published; its figures are not counted against the page's own."""
    return n.has("data-quote")


def _text(n, view):
    if n.tag == "#text":
        return n.text
    if not _printed(n, view):
        return ""
    sep = " " if n.tag in BLOCK_TAGS else ""
    return sep + "".join(_text(c, view) for c in n.children) + sep


def _norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def _val(num):
    """A printed number by its value, so one figure printed at two precisions is one figure: 0.8% and 0.80%, $82,119 and
    $82,119.00 (the key keeps the value's own digits, grouped as printed)."""
    try:
        v = float(num.replace(",", ""))
    except ValueError:
        return num
    t = f"{v:,.6f}".rstrip("0").rstrip(".")
    return t


def _zero(num):
    return not re.sub(r"[^1-9]", "", num)


class Occ:
    __slots__ = ("key", "grid", "read", "unit", "row", "snippet", "price_level", "decimals", "item", "text", "quals", "raw", "sign", "window")

    def __init__(self, key, grid, read, unit, row, snippet, price_level=False, decimals=None, item=None, text="",
                 quals=frozenset()):
        self.key, self.grid, self.read, self.unit, self.row, self.snippet = key, grid, read, unit, row, snippet
        self.price_level, self.decimals, self.item, self.text, self.quals = price_level, decimals, item, text, quals
        self.raw = key[1]
        self.sign, self.window = None, None


# What a dollar figure is a figure OF, read from the words just before it: two equal figures named as different
# quantities (a stablecoin's price and its 7-day high close, both $1.00) are two facts.
QUALS = ("price", "high", "low", "close", "open", "average", "avg", "cap", "volume", "supply", "all-time")


_NEG = re.compile(r"(?:[-\u2212\u25bc]\s*\$?\s*|\b(?:down|fell|lost|lower|off|out|outflows?|onto)\b[^.$%\d]{0,12})$", re.I)
_POS = re.compile(r"(?:[+\u25b2]\s*\$?\s*|\b(?:up|rose|gained|higher|in|into|inflows?)\b[^.$%\d]{0,12})$", re.I)
_WINDOWS = (("hour", r"\b(?:hour|60 minutes|onset)\b"), ("midnight", r"\bsince midnight\b"),
            ("30d", r"\b(?:30 days|30-day|thirty days|month|1M)\b"), ("7d", r"\b(?:7 days|7-day|seven days|week|7D)\b"),
            ("24h", r"\b(?:24 hours|24-hour|24h|the day)\b"), ("year", r"\b(?:year|12-mo|12-month|1Y)\b"))


def _sign(before):
    """The direction a figure is printed with: -1, 1, or None when it carries none."""
    b = before[-16:]
    if _NEG.search(b):
        return -1
    if _POS.search(b):
        return 1
    return None


def _window(n, sentence):
    """The window a figure is printed in: an ancestor's data-window, else the window its own sentence names, else None."""
    while n is not None:
        if n.has("data-window"):
            return n.attrs.get("data-window") or None
        n = n.parent
    found = [w for w, rx in _WINDOWS if re.search(rx, sentence)]
    return found[0] if len(found) == 1 else None


def _sentence(t, i):
    a = max(t.rfind(". ", 0, i), t.rfind(" | ", 0, i))
    b = t.find(". ", i)
    return t[a + 1 if a >= 0 else 0:b if b >= 0 else len(t)]


def _quals(before):
    w = re.findall(r"[a-z][a-z\-]*", before.lower())
    return frozenset(q for q in QUALS if q in w)


def _units(root, view):
    """Each printed text run with its context: (text, unit, grid, read, row). The unit is the innermost block element."""
    out = []

    def walk(n, unit, grid, read, row, item):
        for c in n.children:
            if c.tag == "#text":
                if c.text and c.text.strip():
                    out.append((c.text, unit, grid, read, row, item))
                continue
            if not _printed(c, view) or _quoted(c):
                continue
            u = c if c.tag in BLOCK_TAGS else unit
            g = c if (c.tag in GRID_TAGS or c.has("data-records")) else grid
            r = read if read is not None else (c if c.has("data-read") else None)   # the outermost stored read
            w = c if (c.tag == "tr" or c.has("data-row")) else row
            it = c if (c.tag in ("li", "tr", "dt", "dd") or n.has("data-records")) else item
            walk(c, u, g, r, w, it)
    walk(root, None, None, None, None, None)
    return out


def _bare(t):
    """A figure standing alone in its element: a number, a dollar amount or a percentage, with a sign or an arrow."""
    t = re.sub(r"^[\s+\-\u2212\u25b2\u25bc]+", "", t or "").strip()
    return bool(BARE.match(t) or MONEY.fullmatch(t) or PCT.fullmatch(t))


def _label_scope(unit, view):
    """The text a bare figure's label is read from: its unit, or the nearest enclosing block whose text is more than
    the bare number (a tile's figure sits in its own element, its label in the tile)."""
    n = unit
    for _ in range(4):
        if n is None:
            return ""
        t = _norm_ws(_text(n, view))
        if not _bare(t):
            return t
        n = n.parent
        while n is not None and n.tag not in BLOCK_TAGS:
            n = n.parent
    return ""


def occurrences(root, view):
    """Every figure the page prints at this width, as Occ records."""
    occ = []
    runs = _units(root, view)
    by_unit = {}
    for text, unit, grid, read, row, item in runs:
        by_unit.setdefault(id(unit), (unit, grid, read, row, item, []))[5].append(text)
    for _uid, (unit, grid, read, row, item, texts) in by_unit.items():
        t = _norm_ws(" ".join(_html.unescape(x) for x in texts))
        if not t:
            continue
        snip = t[:160]
        taken = []
        lab_text = _label_scope(unit, view) if _bare(t) else t
        for m in MONEY.finditer(t):
            num, mag = m.group(1).rstrip(","), (m.group(2) or "").strip()
            num = num.rstrip(".")
            if _zero(num):
                continue
            mag = _MAG_NORM.get(mag.lower(), mag.upper()) if mag else ""
            dec = len(num.split(".")[1]) if "." in num else 0
            label = None
            before = t[max(0, m.start() - 70):m.start()]
            if "$" not in before[-40:]:
                for name, rx in AVERAGES:
                    hits = list(rx.finditer(before))
                    if hits and not re.search(r"\$|\d%", before[hits[-1].end():]):
                        label = name
                        break
            if lab_text is t:
                q = _quals(t[max(0, m.start() - 40):m.start()])
            else:
                i = lab_text.find(m.group(0))
                q = _quals(lab_text[max(0, i - 40):i] if i >= 0 else lab_text[:40])
            o = Occ(("money", "$" + _val(num) + mag), grid, read, unit, row, snip, price_level=not mag, decimals=dec,
                    item=item, text=t, quals=q)
            o.raw = "$" + num + mag
            o.sign = _sign(t[max(0, m.start() - 16):m.start()])
            occ.append(o)
            if label:
                occ.append(Occ(("one", label), grid, read, unit, row, snip))
            taken.append((m.start(), m.end()))
        for m in PCT.finditer(t):
            if any(a <= m.start() < b for a, b in taken):
                continue
            num = m.group(1).rstrip(",")
            if _zero(num):
                continue
            o = Occ(("pct", _val(num) + "%"), grid, read, unit, row, snip, item=item, text=t)
            o.sign = _sign(t[max(0, m.start() - 16):m.start()])
            ctx = lab_text if lab_text is not t else _sentence(t, m.start())
            if lab_text is not t:
                i = lab_text.find(m.group(0))
                ctx = lab_text[:i] if i >= 0 else lab_text          # a tile's label stands before its figure
            o.window = _window(unit, ctx)
            occ.append(o)
        for m in BP.finditer(t):
            if not _zero(m.group(1)):
                occ.append(Occ(("bp", m.group(1) + " bp"), grid, read, unit, row, snip, item=item, text=t))
        # THE NEXT SLOT ONCE PER PAGE (Sprint 9.9.2, from 9.9.1's reviewer): "Next Brief tonight at 7:08 PM ET" and "Next read:
        # tonight at 7:08 PM ET" are one fact, the next slot's time
        for m in NEXT_SLOT.finditer(t):
            occ.append(Occ(("one", "the next slot's time"), grid, read, unit, row, snip))
        scope = _label_scope(unit, view) if BARE.match(t) else t
        if BARE.match(t) or re.search(r"RSI|Fear (?:&|and) Greed", t):
            seen = set()
            for name, rx in LABELS:
                for m in rx.finditer(scope):
                    if BARE.match(t) and m.group(1) != BARE.match(t).group(1):
                        continue
                    k = (name, int(round(float(m.group(1)))))
                    if k in seen:
                        continue
                    seen.add(k)
                    occ.append(Occ(("one", name), grid, read, unit, row, snip))
                    break
    return occ


def _sig(key):
    """Significant digits of a printed figure: $1.63B has three, $50M one, 0.52% two."""
    return len(re.sub(r"^0+", "", re.sub(r"[^0-9]", "", key[1].split(" ")[0])))


_STOP = {"the", "a", "an", "of", "on", "in", "for", "and", "to", "at", "by", "with", "from", "this", "that"}


def _item_label(item, view):
    """What a table row or list item is about: its first printed word that is a name (the coin, the outlet, the day)."""
    if item is None:
        return ""
    for w in re.findall(r"[A-Za-z][A-Za-z0-9&'.\-]*", _norm_ws(_text(item, view))):
        w = re.sub(r"'s$", "", w)
        if w.lower() not in _STOP and len(w) >= 2:
            return w
    return ""


def figure_keys(h):
    """The set of figures a piece of HTML prints, at either width, as the keys the sweep compares."""
    root = parse(h)
    return {o.key for v in ("narrow", "wide") for o in occurrences(root, v)}


def twins_between(a_html, b_html):
    """The figures piece A prints that piece B prints too, as the sweep would pair them (subject, sign, window and the
    rest), at either width: the keys of A's prints that are a twin of one of B's."""
    out = set()
    for view in ("narrow", "wide"):
        ra, rb = parse(f"<div>{a_html}</div>"), parse(f"<div>{b_html}</div>")
        oa, ob = occurrences(ra, view), occurrences(rb, view)
        for x in oa:
            if any(x.key == y.key and _twin(x, y, view) for y in ob):
                out.add(x.key)
    return out


def _twin(a, b, view="wide"):
    if a.grid is not None and a.grid is b.grid:
        return False
    if a.read is not None and a.read is b.read:
        return False
    if a.key[0] == "money" and a.quals != b.quals:
        return False                              # named as two different quantities
    if a.sign is not None and b.sign is not None and a.sign != b.sign:
        return False                              # -0.01% and +0.01%: two values
    if a.window is not None and b.window is not None and a.window != b.window:
        return False                              # a 24-hour and a 7-day change that are both 0.65%: two facts
    if a.unit is b.unit:
        return False                              # one line: a range or a pair ("7.5% to 7.5%"), or one label read twice
    # THE SUBJECT FLOOR (CLAUDE.md: a shallow key is not an identity). Two coins can fall the same 0.64%, and two
    # transfers can both be $499.8M: when a print sits in a table row or a list item, the twin needs that row's
    # subject (its first name: "Ether", "MORPHO", "Binance") in the other print's line.
    if True:
        for x, y in ((a, b), (b, a)):
            if x.item is not None:
                lab = _item_label(x.item, view)
                if not lab or not re.search(r"\b" + re.escape(lab.lower()) + r"\b", (y.text or "").lower()):
                    return False
    return True


def page_findings(h):
    """[(kind, text)] for one page: kind 'twin' or 'precision'."""
    root = parse(h)
    found, seen = [], set()
    for view in ("narrow", "wide"):
        occ = occurrences(root, view)
        groups = {}
        for o in occ:
            groups.setdefault(o.key, []).append(o)
        for key, os_ in groups.items():
            if len(os_) < 2:
                continue
            twins = [(a, b) for i, a in enumerate(os_) for b in os_[i + 1:] if _twin(a, b, view)]
            if not twins:
                continue
            what = key[1] if key[0] != "one" else f"{key[1]} (one value per page)"
            snips = []
            for a, b in twins:
                for o in (a, b):
                    if o.snippet not in snips:
                        snips.append(o.snippet)
            line = f"{what} printed {len(snips) if key[0] == 'one' else len(os_)} times: " + " || ".join(snips[:4])
            if ("twin", what) not in seen:
                seen.add(("twin", what))
                found.append(("twin", line))
        rows = {}
        for o in occ:
            if o.row is not None and o.key[0] == "money" and o.price_level:
                rows.setdefault(id(o.row), (o.row, []))[1].append(o)
        for _rid, (row, os_) in rows.items():
            decs = sorted({o.decimals for o in os_})
            if len(decs) > 1:
                rt = _norm_ws(_text(row, view))[:160]
                k = ("precision", rt)
                if k not in seen:
                    seen.add(k)
                    found.append(("precision", f"a row prints {', '.join(o.key[1] for o in os_)} at "
                                               f"{' and '.join(str(d) for d in decs)} decimals: {rt}"))
    return found


def sitemap_pages(root):
    """Every page the built site's sitemaps list, as (url path, file path or None)."""
    locs = []
    for sm in ("sitemap-priority.xml", "sitemap-archive.xml", "news-sitemap.xml"):
        p = os.path.join(root, sm)
        if os.path.exists(p):
            locs += re.findall(r"<loc>https?://[^/<]+(/[^<]*)</loc>", open(p, encoding="utf-8").read())
    out = []
    for u in dict.fromkeys(locs):
        base = u.split("#")[0].split("?")[0]
        f = None
        for c in (base.rstrip("/") + ".html", base.rstrip("/") + "/index.html", base):
            q = os.path.join(root, c.lstrip("/"))
            if c and os.path.isfile(q):
                f = q
                break
        out.append((u, f))
    return out


def sweep(root):
    """{url: [(kind, text)]} for every sitemap page with a finding, plus '(missing)' entries for a listed page the
    tree does not hold. The count of pages read is returned beside it."""
    res = {}
    pages = sitemap_pages(root)
    for u, f in pages:
        if f is None:
            res[u] = [("missing", "listed in the sitemap, not in the tree")]
            continue
        fs = page_findings(open(f, encoding="utf-8", errors="replace").read())
        if fs:
            res[u] = fs
    return res, len(pages)


# ---- 3. a stored average printed with more decimals than it carries -----------------------------------------------------

def _decimals(v):
    t = repr(float(v))
    if "e" in t:
        return 12
    return len(t.split(".")[1].rstrip("0")) if "." in t else 0


def stored_averages(data_dir):
    """[(where, symbol, field, value)] for every stored 50-day and 200-day average the build prints from: the Board's
    assets (pulse.json), the current Chart Master card and the dated ones it keeps (chartmaster.json, chartmaster/)."""
    import glob
    import json
    out = []

    def rows(path, key):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            return []
        return [r for r in (d.get(key) or []) if isinstance(r, dict)]
    for r in rows(os.path.join(data_dir, "pulse.json"), "assets"):
        out += [("pulse.json", r.get("symbol"), f, r[f], r) for f in ("sma50", "sma200") if isinstance(r.get(f), (int, float))]
    for p in [os.path.join(data_dir, "chartmaster.json")] + sorted(glob.glob(os.path.join(data_dir, "chartmaster", "*.json"))):
        for r in rows(p, "levels"):
            out += [(os.path.relpath(p, data_dir), r.get("symbol"), f, r[f], r) for f in ("sma50", "sma200")
                    if isinstance(r.get(f), (int, float))]
    return out


def precision_findings(root, data_dir):
    """{url: [("precision", text)]}: a stored average printed with more decimals than the stored value carries (and
    more than cents), which prints a rounding as if it were the figure: DOGE's 200-day average stored as 0.09 and
    printed $0.0900 beside a price of $0.0770. Read on the pages that print averages: the Chart Master's, the coin
    page of the average's own coin, Price posture and the home."""
    res, seen = {}, set()
    for where, sym, field, v, _r in stored_averages(data_dir):
        d = _decimals(v)
        pads = {f"${v:,.{p}f}" for p in range(max(d, 2) + 1, 7)}
        if not pads or not sym:
            continue
        for rel in ("chartmaster.html", f"coins/{str(sym).lower()}.html", "pulse/posture.html", "index.html"):
            f = os.path.join(root, rel)
            if not os.path.exists(f):
                continue
            root_n = parse(open(f, encoding="utf-8", errors="replace").read())
            printed = {o.raw for o in occurrences(root_n, "wide") if o.key[0] == "money"} | \
                      {o.raw for o in occurrences(root_n, "narrow") if o.key[0] == "money"}
            hit = sorted(x for x in pads if x in printed)
            url = "/" + rel[:-5] if rel != "index.html" else "/"
            if hit and (url, sym, field, hit[0]) not in seen:
                seen.add((url, sym, field, hit[0]))
                res.setdefault(url, []).append(("precision", f"{sym} {field} stored as {v} ({d} decimals, {where}) and printed "
                                                             f"as {hit[0]}, a rounding printed as if it were the figure"))
    return res


if __name__ == "__main__":
    import sys
    r, n = sweep(sys.argv[1])
    if len(sys.argv) > 2:
        for u, fs in precision_findings(sys.argv[1], sys.argv[2]).items():
            r.setdefault(u, []).extend(fs)
    for u in sorted(r):
        for kind, t in r[u]:
            print(f"{u}\t{kind}\t{t}")
    print(f"ONE FACT SWEEP: {n} pages read, {len(r)} with a finding, "
          f"{sum(len(v) for v in r.values())} finding(s)")
