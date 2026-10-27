#!/usr/bin/env python3
"""ONE FACT ONCE (Sprint 9.9.2, October 27, 2026): the site-wide sweep against the standing law "the same fact printed twice",
measured on every page of a built tree, not sampled.

    python3 fact_sweep.py <tree>            # every finding, one line each; exit 1 on any
    python3 fact_sweep.py <tree> --count    # the count per kind and per page family
    python3 fact_sweep.py <tree> --history data/history   # also every average against the desk's stored closes

What a page PRINTS is what a reader sees at a width, so every page is read twice, at 375 and at 1440 pixels, through the site's own
stylesheets: an element the stylesheet hides at that width (the wide and narrow chart twins, the tape's Ether line under 1280, the
Markets columns hidden on a phone) prints nothing there. Screen-reader-only text, the document title and an SVG <title> tooltip are
not printed. Content a reader reveals by a control on the page (a closed <details>, the "Show all columns" box) counts as printed.

Four checks, each named in its finding:

  twice      the same figure (a dollar amount or a percentage, compared at the coarser of the two printings, sign and arrow aside)
             printed twice on one page at one width. Two rows of one table or one list are two subjects (two coins at $1.00 are two
             facts); a chart's axis tick is the chart's scale, not a fact.
  label      a named reading printed twice on one page for one subject, whatever its values: the 200-day average, the 50-day
             average, RSI, Fear & Greed. "One 200-day value per page."
  precision  a derived figure printed at a precision its row does not share: every dollar figure of one table row at one number
             of decimals, and a moving average at the decimals of the price printed for its asset on the page.
  stamp      a dated block without its own read's date and age in the house wording ("Chart levels, read Oct 25, 8:17 PM ET"), and
             the retired "from the last build".

THE SCOPE, stated once. The sweep reads the figures the build prints from the desk's data. The words of a stored story, Brief,
Edition or read (its headline, dek, body, key fact, bottom line, source and related lists, the card summaries that quote them) are
a writer's words, stored and never reworded (J-10); a headline that restates its body's figure is the story, not a figure printed
twice. Those regions are named in PROSE below, each by the class the build gives it, and nothing else is set aside.
No network, no model."""
import collections
import html as _html
import os
import re
import sys
from html.parser import HTMLParser

WIDTHS = (375, 1440)

# The words of stored writing (see THE SCOPE above). Each is the class the build gives a stored story's, Brief's, Edition's or
# read's text, or a card that quotes it; an element carrying one, and everything inside it, is read as prose, not as data.
PROSE = frozenset((
    "prose", "dek", "bottomline", "keyfact", "sources", "related", "callout", "link-list", "more-on",   # a stored story's page
    "summary",                                                                     # a card quoting a story's summary (archive, coverage)
    "ed-brief", "ed-sheet", "ed-front", "ed-lead", "ed-downpage", "ed-rail",        # a stored Edition's page
    "bl-hist", "bl-read",                                                          # the Brief archive's stored reads
    "nh-t", "nh-x",                                                                # the news front's story headlines
    "cm-read", "cm-headline", "cm-entry",                                          # a stored Chart Master read's words
    "bp-row",                                                                      # a story's quoted price block, stored with it
    "lr-t", "lx",                                                                  # Learn's written explainers and their pages
    "bd-rec-t", "bd-rec-hl",                                                       # the record of past stories, headlines quoted
    "td-corr", "td-line", "ev-l",                                                  # a stored correction's words; a wire line's words
    "td-read",                                                                     # a /today/ answer lifted whole from a stored Brief
    "h-nline", "h-bt",                                                             # the home Brief card's stored line and headline
))

VOID = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "base", "col", "embed", "param", "track"}
NOTEXT = {"script", "style", "noscript", "template", "title", "head", "desc"}
BLOCK = {"p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section", "aside", "article", "figure",
         "figcaption", "header", "footer", "nav", "ul", "ol", "table", "dt", "dd", "dl", "main", "summary", "details", "blockquote",
         "caption", "thead", "tbody", "form", "label", "text", "svg", "button"}
ROWS = {"tr", "li", "dt", "dd"}


# ---- the DOM ------------------------------------------------------------------------------------------------------------

class El:
    __slots__ = ("tag", "attrs", "cls", "parent", "kids", "text", "idx")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids = tag, attrs, parent, []
        self.cls = set((attrs.get("class") or "").split())
        self.text = None                     # a text node carries its string here and tag "#text"
        self.idx = 0

    def elems(self):
        return [k for k in self.kids if k.tag != "#text"]


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        e = El(tag, a, self.cur)
        self.cur.kids.append(e)
        if tag not in VOID:
            self.cur = e

    def handle_startendtag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self.cur.kids.append(El(tag, a, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        t = El("#text", {}, self.cur)
        t.text = data
        self.cur.kids.append(t)


def parse(h):
    p = _Tree()
    p.feed(h)
    p.close()
    return p.root


# ---- the stylesheet: display only, at a width ---------------------------------------------------------------------------

def _media_ok(q, width):
    q = q.strip().lower()
    if not q:
        return True
    for part in q.split(","):
        part = part.strip()
        if part.startswith("not ") or "print" in part:
            continue
        ok = True
        for feat in re.findall(r"\(([^)]*)\)", part):
            k, _, v = feat.partition(":")
            k, v = k.strip(), v.strip()
            if k in ("min-width", "max-width"):
                m = re.match(r"([\d.]+)px", v)
                if not m:
                    ok = False
                    break
                px = float(m.group(1))
                ok = width >= px if k == "min-width" else width <= px
            elif k == "prefers-reduced-motion":
                ok = v == "no-preference"
            elif k == "prefers-color-scheme":
                ok = v == "light"
            elif k in ("hover", "pointer"):
                ok = width >= 1024 and v in ("hover", "fine")
            else:
                ok = False
            if not ok:
                break
        if ok:
            return True
    return False


def _rules(css, width):
    """[(selector, display, important, order)] for the rules that apply at `width`, in source order."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, order = [], 0, 0

    def block(s, media_ok):
        nonlocal order
        j = 0
        while j < len(s):
            k = s.find("{", j)
            if k < 0:
                break
            head = s[j:k].strip()
            depth, e = 1, k + 1
            while e < len(s) and depth:
                depth += {"{": 1, "}": -1}.get(s[e], 0)
                e += 1
            body = s[k + 1:e - 1]
            j = e
            if head.startswith("@media"):
                block(body, media_ok and _media_ok(head[6:], width))
            elif head.startswith("@supports"):
                block(body, media_ok)
            elif head.startswith("@"):
                continue
            elif media_ok:
                m = re.search(r"(?:^|;)\s*display\s*:\s*([^;!]+)(!\s*important)?", body)
                if m:
                    for sel in _split_top(head):
                        order += 1
                        out.append((sel.strip(), m.group(1).strip(), bool(m.group(2)), order))
    block(css, True)
    return out


def _split_top(s, sep=","):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p for p in parts if p.strip()]


_COMPOUND = re.compile(r"""(\*|[a-zA-Z][\w-]*)|\.([\w-]+)|\#([\w-]+)|\[([\w-]+)(?:([~|^$*]?=)["']?([^"'\]]*)["']?)?\]|::?([\w-]+)(\((?:[^()]|\([^()]*\))*\))?""")


def _compile(sel):
    """A selector as [(combinator, compound)], or None when it names something the sweep does not model (a pseudo-element)."""
    toks, cur, comb, i = [], "", " ", 0
    sel = sel.strip()
    depth = 0
    parts = []
    while i < len(sel):
        ch = sel[i]
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if depth == 0 and ch in " >+~":
            if cur:
                parts.append((comb, cur))
                cur = ""
                comb = " "
            if ch != " ":
                comb = ch
            i += 1
            continue
        cur += ch
        i += 1
    if cur:
        parts.append((comb, cur))
    out = []
    for c, comp in parts:
        items, pos = [], 0
        for m in _COMPOUND.finditer(comp):
            if m.start() != pos:
                return None
            pos = m.end()
            if m.group(1):
                items.append(("tag", m.group(1).lower()))
            elif m.group(2):
                items.append(("cls", m.group(2)))
            elif m.group(3):
                items.append(("id", m.group(3)))
            elif m.group(4):
                items.append(("attr", (m.group(4), m.group(5), m.group(6))))
            elif m.group(7):
                if m.group(0).startswith("::") or m.group(7) in ("before", "after", "marker", "placeholder") \
                        or m.group(7).startswith("-webkit"):
                    return None
                arg = (m.group(8) or "")[1:-1]
                items.append(("pseudo", (m.group(7), arg)))
        if pos != len(comp):
            return None
        out.append((c, items))
    return out


def _spec(sel):
    a = len(re.findall(r"#[\w-]+", sel))
    b = len(re.findall(r"\.[\w-]+|\[[^\]]+\]|:(?!:)(?!not\b|is\b|where\b)[\w-]+", sel))
    c = len(re.findall(r"(?:^|[\s>+~(])([a-zA-Z][\w-]*)", sel))
    return (a, b, c)


def _siblings(e):
    return e.parent.elems() if e.parent is not None else [e]


def _nth(arg, n):
    arg = arg.replace(" ", "")
    if arg == "odd":
        return n % 2 == 1
    if arg == "even":
        return n % 2 == 0
    m = re.fullmatch(r"([+-]?\d*)n([+-]\d+)?", arg)
    if m:
        a = int(m.group(1) + "1") if m.group(1) in ("", "+", "-") else int(m.group(1))
        b = int(m.group(2) or 0)
        return (n - b) % a == 0 and (n - b) // a >= 0 if a else n == b
    return arg.isdigit() and n == int(arg)


def _match_compound(e, items):
    if e is None or e.tag.startswith("#"):
        return False
    for kind, v in items:
        if kind == "tag":
            if v != "*" and e.tag != v:
                return False
        elif kind == "cls":
            if v not in e.cls:
                return False
        elif kind == "id":
            if e.attrs.get("id") != v:
                return False
        elif kind == "attr":
            name, op, val = v
            if name not in e.attrs:
                return False
            got = e.attrs.get(name) or ""
            if op == "=" and got != val:
                return False
            if op == "~=" and val not in got.split():
                return False
            if op == "^=" and not got.startswith(val):
                return False
            if op == "*=" and val not in got:
                return False
        elif kind == "pseudo":
            name, arg = v
            if name in ("not",):
                if any(_matches(e, s) for s in _split_top(arg)):
                    return False
            elif name in ("is", "where"):
                if not any(_matches(e, s) for s in _split_top(arg)):
                    return False
            elif name == "has":
                if not any(_has(e, s) for s in _split_top(arg)):
                    return False
            elif name == "root":
                if e.tag != "html":
                    return False
            elif name == "first-child":
                if _siblings(e)[0] is not e:
                    return False
            elif name == "last-child":
                if _siblings(e)[-1] is not e:
                    return False
            elif name == "nth-child":
                if not _nth(arg, _siblings(e).index(e) + 1):
                    return False
            elif name == "nth-of-type":
                same = [s for s in _siblings(e) if s.tag == e.tag]
                if not _nth(arg, same.index(e) + 1):
                    return False
            elif name == "checked":
                pass                         # a control the reader sets: its revealed state counts as printed
            else:
                return False                 # hover, focus, target, disabled: not the page as it loads
    return True


_CACHE = {}


def _matches(e, sel):
    prog = _CACHE.get(sel)
    if prog is None:
        prog = _CACHE[sel] = _compile(sel) or False
    if not prog:
        return False
    return _match_from(e, prog, len(prog) - 1)


def _match_from(e, prog, i):
    comb, items = prog[i]
    if not _match_compound(e, items):
        return False
    if i == 0:
        return True
    if comb == ">":
        return _match_from(e.parent, prog, i - 1)
    if comb == " ":
        p = e.parent
        while p is not None:
            if _match_from(p, prog, i - 1):
                return True
            p = p.parent
        return False
    sib = _siblings(e)
    k = sib.index(e)
    if comb == "+":
        return k > 0 and _match_from(sib[k - 1], prog, i - 1)
    if comb == "~":
        return any(_match_from(s, prog, i - 1) for s in sib[:k])
    return False


def _has(e, sel):
    sel = sel.strip()
    stack = list(e.elems())
    while stack:
        k = stack.pop()
        if _matches(k, sel):
            return True
        stack.extend(k.elems())
    return False


_RULES = {}


def _rules_cached(css, width):
    key = (hash(css), len(css), width)
    if key not in _RULES:
        _RULES[key] = _rules(css, width)
    return _RULES[key]


class Sheet:
    """The site's stylesheets at one width, reduced to the rules that set display."""

    def __init__(self, css_texts, width):
        self.width = width
        self.rules = []
        for k, css in enumerate(css_texts):
            # source order across sheets: a later sheet's rule wins a tie, so each sheet's order is offset past the one before
            self.rules += [(s, d, imp, o + k * 1_000_000) for s, d, imp, o in _rules_cached(css, width)]
        self.rules = [(s, d, imp, o, _spec(s)) for s, d, imp, o in self.rules]
        # an index by the last compound's class, tag or id, so each element meets only the rules that can name it
        self.by = collections.defaultdict(list)
        for r in self.rules:
            prog = _compile(r[0])
            if not prog:
                continue
            last = prog[-1][1]
            key = next((("cls", v) for k, v in last if k == "cls"), None) or \
                next((("id", v) for k, v in last if k == "id"), None) or \
                next((("tag", v) for k, v in last if k == "tag" and v != "*"), None) or ("any", None)
            self.by[key].append(r)

    def display(self, e):
        cands = list(self.by.get(("any", None), ())) + list(self.by.get(("tag", e.tag), ()))
        for c in e.cls:
            cands += self.by.get(("cls", c), ())
        if e.attrs.get("id"):
            cands += self.by.get(("id", e.attrs["id"]), ())
        best = None
        for sel, disp, imp, order, spec in cands:
            if _matches(e, sel):
                key = (imp, spec, order)
                if best is None or key > best[0]:
                    best = (key, disp)
        st = e.attrs.get("style") or ""
        m = re.search(r"display\s*:\s*([^;!]+)(!\s*important)?", st)
        if m and (best is None or not best[0][0] or m.group(2)):
            return m.group(1).strip()
        if best is not None:
            return best[1]
        return "none" if "hidden" in e.attrs else None


def site_css(root, h):
    """The stylesheets a page links from /assets/ (the build's own files, read from the tree)."""
    out = []
    for href in re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="(/assets/[^"?]+)', h) + \
            re.findall(r'<link[^>]+href="(/assets/[^"?]+\.css)[^"]*"[^>]+rel="stylesheet"', h):
        p = os.path.join(root, href.lstrip("/"))
        if os.path.exists(p):
            out.append(open(p, encoding="utf-8", errors="replace").read())
    return out


# ---- what a page prints --------------------------------------------------------------------------------------------------

def printed(dom, sheet):
    """[(text, element)] for every text node the page prints at the sheet's width, in document order."""
    out = []

    def walk(e, hidden_ancestor):
        for k in e.kids:
            if k.tag == "#text":
                if k.text.strip():
                    out.append((k.text, e))
                continue
            if k.tag in NOTEXT:
                continue
            if "sr-only" in k.cls or "visually-hidden" in k.cls:
                continue
            if sheet.display(k) == "none":
                continue
            walk(k, hidden_ancestor)
    walk(dom, False)
    return out


def ancestors(e):
    while e is not None:
        yield e
        e = e.parent


STORY_HREF = re.compile(r"^/(?:articles|edition|bottom-line)/")


def in_prose(e):
    """Inside stored writing: an element of PROSE, or a link to a stored story (its text is that story's headline)."""
    return any(a.cls & PROSE or (a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or "")) for a in ancestors(e))


ROW_CLASS = re.compile(r"row$")


def row_of(e):
    """The nearest row the element sits in (a table row, a list item, or an element the build marks as a row by its class: lrow,
    td-row, cn-row), or None."""
    for a in ancestors(e):
        if a.tag in ROWS:
            return a
        rc = {c for c in a.cls if ROW_CLASS.search(c)}
        # a row by its class repeats (a sibling carries the same class) and holds no reading tile or card (a grid named tl-row
        # holds tiles: it is a container, not a row)
        if rc and a.parent is not None and any(k is not a and (k.cls & rc) for k in a.parent.elems()) \
                and not any(k.tag in ("article", "div", "section") and ("tl" in k.cls or any("card" in c for c in k.cls))
                            for k in a.elems()):
            return a
    return None


def tile_of(e):
    """The nearest reading tile or card the element sits in (class tl, or a class naming a card), or None."""
    for a in ancestors(e):
        if a.tag in ("article", "div", "section", "aside") and ("tl" in a.cls or any("card" in c for c in a.cls)):
            return a
    return None


def two_subjects(a, b, wa=None, wb=None):
    """Two rows (of one table or list, or of two) are two subjects: each row names its own (a coin, a transfer, an exchange, a week).
    So are two sibling cards of one kind (the per-coin cards of a Markets page), and two reading tiles, each one reading under the
    tile law, unless both figures state one window (then the second tile repeats the first's figure)."""
    ra, rb = row_of(a), row_of(b)
    if ra is not None and rb is not None and ra is not rb:
        return True
    ta, tb = tile_of(a), tile_of(b)
    if ta is not None and tb is not None and ta is not tb and ta.tag == tb.tag and ta.cls == tb.cls \
            and not (wa and wb and wa == wb):
        return True
    pa, pb = list(ancestors(a))[::-1], list(ancestors(b))[::-1]
    k = 0
    while k < min(len(pa), len(pb)) and pa[k] is pb[k]:
        k += 1
    if k < len(pa) and k < len(pb):
        x, y = pa[k], pb[k]
        if x.tag == y.tag and x.cls == y.cls and any("card" in c for c in x.cls):
            return True
    return False


def block_of(e):
    for a in ancestors(e):
        if a.tag in BLOCK:
            return a
    return e


def svg_of(e):
    for a in ancestors(e):
        if a.tag == "svg":
            return a
    return None


# ---- figures -------------------------------------------------------------------------------------------------------------

FIG = re.compile(r"(?<![\w$.,])([+\-−]?)\$(\d[\d,]*(?:\.\d+)?)(?:\s?([KMBT])\b)?|(?<![\w.,$])([+\-−]?)(\d[\d,]*(?:\.\d+)?)%")
NEXT_TIME = re.compile(r"\b[Nn]ext (?:read|Brief|update)\b[^.]{0,40}?((?:this morning|this evening|tonight|tomorrow|today) at "
                       r"\d{1,2}:\d\d [AP]M ET)")
MAG = {"": 1, None: 1, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


class Fig:
    __slots__ = ("unit", "value", "dec", "sig", "raw", "el", "start", "num", "mag", "sign", "window")

    def __init__(self, unit, num, mag, raw, el, start):
        num = num.rstrip(",")
        self.unit = unit
        self.dec = len(num.split(".")[1]) if "." in num else 0
        self.value = float(num.replace(",", "")) * MAG[mag]
        digits = num.replace(",", "").replace(".", "").lstrip("0")
        self.sig = len(digits)
        self.raw, self.el, self.start = raw, el, start
        self.num, self.mag = num.replace(",", ""), mag or ""
        self.sign = 0
        self.window = None

    def step(self):
        """The rounding step the printing carries (0.01 for $79,771.00, 1e7 for $1.59B)."""
        mag = 1
        m = re.search(r"([KMBT])\s*$", self.raw)
        if m:
            mag = MAG[m.group(1)]
        return mag * 10 ** (-self.dec)

    def same(self, other):
        """One figure, printed twice: the same digits (sign and arrow aside), or, when both carry four significant digits or
        more, the finer printing rounded to the coarser ($79,771 and $79,771.00). A coarse figure ($100, 9.2%) is compared by
        its digits only, so a headline's round number never pairs with a price."""
        if self.unit != other.unit:
            return False
        if self.sign and other.sign and self.sign != other.sign:
            return False                     # +2.0% and "down 2.0%" are two facts
        if self.window and other.window and self.window != other.window:
            return False                     # 0.60% over 24 hours and 0.60% in one hour are two facts
        if self.num == other.num and self.mag == other.mag:
            return True
        if min(self.sig, other.sig) < 4:
            return False
        st = max(self.step(), other.step())
        return abs(abs(self.value) - abs(other.value)) <= st / 2 + 1e-12 * max(1.0, abs(self.value))


SIGN_WORDS = re.compile(r"(\u25b2|\u25bc|\b(?:up|down|rose|fell|gained|lost|higher|lower)\b)[^\d$%]{0,6}$", re.I)


def figures(nodes):
    """Every figure printed in a list of (text, element) nodes, with the element that prints it and its sign when the page states
    one (a sign, an arrow or a direction word just before it)."""
    out = []
    prev = ""
    for text, el in nodes:
        for m in FIG.finditer(text):
            if m.group(2) is not None:
                f = Fig("$", m.group(2), m.group(3), m.group(0), el, m.start())
                sg = m.group(1)
            else:
                f = Fig("%", m.group(5), None, m.group(0), el, m.start())
                sg = m.group(4)
            if sg:
                f.sign = 1 if sg == "+" else -1
            else:
                w = SIGN_WORDS.search((prev + " " + text[:m.start()])[-40:])
                if w:
                    f.sign = 1 if w.group(1).lower() in ("\u25b2", "up", "rose", "gained", "higher") else -1
            out.append(f)
        prev = text[-40:]
    return out


WINDOWS = (("hour", re.compile(r"\b(?:in the hour|the hour|onset hour|next 60 minutes|one hour|per hour)\b", re.I)),
           ("day", re.compile(r"\b(?:since midnight|on the day|since yesterday|today|one trading day|latest day)\b", re.I)),
           ("24h", re.compile(r"\b(?:24 hours|24-hour|24h|rolling 24)\b", re.I)),
           ("7d", re.compile(r"\b(?:7 days|7-day|7D|seven days|week)\b", re.I)),
           ("30d", re.compile(r"\b(?:30 days|30-day|month)\b", re.I)),
           ("90d", re.compile(r"\b(?:90 days|90-day)\b", re.I)),
           ("1y", re.compile(r"\b(?:12-mo|12-month|12 months|one year|365 days)\b", re.I)))
HEADING = {"h1", "h2", "h3", "h4", "caption"}


def _window_of(text, at=None):
    """The window a text states; with `at` (a figure's offset in it), the window phrase nearest that figure, so "Bitcoin up since
    yesterday, and $1.59B onto exchanges in 7 days" gives the whale figure its seven days."""
    hits = [(m.start(), name) for name, rx in WINDOWS for m in rx.finditer(text or "")]
    if not hits:
        return None
    if at is None:
        return next(name for name, rx in WINDOWS if rx.search(text or ""))
    return min(hits, key=lambda h: (abs(h[0] - at), h[0] < at))[1]


def set_windows(nodes, figs):
    """Each figure's window, read from its own sentence in its block, or, for a figure in a table or list row whose sentence names
    none, from the heading the row sits under. A figure whose window is stated nowhere keeps None and pairs with any window."""
    head, heads = "", {}
    for t, e in nodes:
        if any(a.tag in HEADING for a in ancestors(e)):
            head = t
        heads[id(e)] = head
    for f in figs:
        b = block_of(f.el)
        line = " ".join(_text(b).split())
        raw = f.raw.strip()
        k = line.find(raw)
        sent, at = line, None
        if k >= 0:
            a = max(line.rfind(". ", 0, k), line.rfind("; ", 0, k))
            z = [x for x in (line.find(". ", k), line.find("; ", k)) if x >= 0]
            a0 = a + 1 if a >= 0 else 0
            sent, at = line[a0:min(z) if z else len(line)], k - a0
        # the clause the figure sits in decides first (", and $1.59B onto exchanges in 7 days"), then its sentence
        clause = None
        if at is not None:
            c0 = sent.rfind(", ", 0, at)
            c1 = sent.find(", ", at)
            clause = sent[c0 + 2 if c0 >= 0 else 0:c1 if c1 >= 0 else len(sent)]
        f.window = _window_of(clause) if clause and _window_of(clause) else _window_of(sent, at)
        if f.window is None and row_of(f.el) is not None:
            r = row_of(f.el)
            f.window = _window_of(" ".join(_text(r).split())) or _window_of(heads.get(id(f.el), ""))
        if f.window is None and tile_of(f.el) is not None:
            # a tile states its figure's window on its own window line ("Spot, US dollars; the change is the rolling 24 hours")
            t = tile_of(f.el)
            wl = next((k for k in _walk(t) if "tl-w" in k.cls), None)
            f.window = _window_of(" ".join(_text(wl).split())) if wl is not None else None


def significant(f):
    """A figure precise enough to name one fact: three significant digits for a dollar amount, two for a percentage."""
    return f.sig >= (3 if f.unit == "$" else 2)


def axis_ticks(figs):
    """The figures that are a chart's scale: text in an <svg> whose class names a tick or an axis, or three or more figures of one
    unit in one <svg> evenly spaced."""
    ticks = set()
    by = collections.defaultdict(list)
    for f in figs:
        s = svg_of(f.el)
        if s is None:
            continue
        if any(re.search(r"tick|axis|grid", c) for a in ancestors(f.el) for c in a.cls):
            ticks.add(id(f))
            continue
        by[(id(s), f.unit)].append(f)
    for group in by.values():
        vals = sorted(set(round(f.value, 9) for f in group))
        if len(vals) >= 3:
            gaps = [b - a for a, b in zip(vals, vals[1:])]
            if max(gaps) - min(gaps) <= max(1e-9, 0.02 * max(gaps)):
                ticks.update(id(f) for f in group)
    return ticks


def _ctx(f):
    b = block_of(f.el)
    t = " ".join(_text(b).split())
    return t[:110]


def _text(e):
    if e.tag == "#text":
        return e.text
    return " ".join(_text(k) for k in e.kids if k.tag not in NOTEXT)


# ---- labeled readings ----------------------------------------------------------------------------------------------------

LABELS = (
    ("the 200-day average", re.compile(r"\b200-day(?: average| line| avg|)\b", re.I), "$"),
    ("the 50-day average", re.compile(r"\b50-day(?: average| line| avg|)\b", re.I), "$"),
    ("RSI", re.compile(r"\bRSI(?:-14| \(14\)|)", re.I), "n"),
    ("Fear & Greed", re.compile(r"\bFear (?:&|and) Greed\b", re.I), "n"),
)
NUM_AFTER = re.compile(r"^(?:\s|:|\b(?:of|is|at|line|average|avg)\b)*(\$?)(\d[\d,]*(?:\.\d+)?)(%?)")


def card_of(e):
    for a in ancestors(e):
        if a.tag in ("div", "section", "article", "aside", "li") and any("card" in c for c in a.cls):
            return id(a)
    return "page"


def labeled(nodes, one_subject=False):
    """(label, subject, value text, element, context) for each named reading printed with its value right after its label, the
    value in the same block or the next one printed ("RSI (14)" over "41" in a reading tile)."""
    out = []
    flat, owners = "", []
    for text, el in nodes:
        t = " ".join(text.split())
        if not t:
            continue
        owners.append((len(flat), el))
        flat += t + " "
    import bisect
    starts = [o for o, _e in owners]
    for name, rx, unit in LABELS:
        for m in rx.finditer(flat):
            n = NUM_AFTER.match(flat[m.end():])
            if not n:
                continue
            if unit == "$" and not n.group(1):
                continue
            if unit == "n" and (n.group(1) or n.group(3)):
                continue
            el = owners[bisect.bisect_right(starts, m.start()) - 1][1]
            subj = row_subject(el)
            if subj is None and not one_subject:
                subj = card_of(el)
            out.append((name, subj, n.group(1) + n.group(2) + n.group(3), el, flat[max(0, m.start() - 20):m.end() + 30]))
    return out


def row_subject(el):
    r = row_of(el)
    if r is None:
        return None
    first = next((k for k in r.elems() if k.tag in ("th", "td")), None) if r.tag == "tr" else None
    return " ".join(_text(first if first is not None else r).split())[:40] if first is not None else id(r)


# ---- the checks ---------------------------------------------------------------------------------------------------------

def sweep_page(h, css_texts, rel=""):
    """Every finding on one page, as (kind, width, text). An empty list is a page that prints each fact once."""
    findings = []
    dom = parse(h)
    for w in WIDTHS:
        sheet = Sheet(css_texts, w)
        nodes = [(t, e) for t, e in printed(dom, sheet) if not in_prose(e)]
        figs = figures(nodes)
        set_windows(nodes, figs)
        ticks = axis_ticks(figs)
        facts = [f for f in figs if id(f) not in ticks and significant(f)]
        # twice
        seen = []
        reported = set()
        for f in facts:
            for g in seen:
                if not f.same(g):
                    continue
                if two_subjects(f.el, g.el, f.window, g.window):
                    continue
                key = (f.unit, round(abs(f.value), 6))
                if key in reported:
                    break
                reported.add(key)
                findings.append(("twice", w, f"{rel} at {w}: {g.raw.strip()} printed twice ({_ctx(g)!r} and {_ctx(f)!r})"))
                break
            seen.append(f)
        # label
        by = collections.defaultdict(list)
        coin = rel.startswith("coins/")
        for name, subj, val, el, line in labeled(nodes, one_subject=coin):
            by[(name, subj)].append((val, line))
        for (name, subj), vals in by.items():
            if len(vals) > 1:
                findings.append(("label", w, f"{rel} at {w}: {name} printed {len(vals)} times "
                                             f"({'; '.join(repr(l[:70]) for _v, l in vals[:3])})"))
        # precision: one table row's dollar figures at one number of decimals
        rows = collections.defaultdict(list)
        for f in figs:
            r = row_of(f.el)
            if f.unit == "$" and r is not None and r.tag == "tr" and not re.search(r"[KMBT]\s*$", f.raw):
                rows[id(r)].append(f)
        for fs in rows.values():
            decs = sorted(set(f.dec for f in fs))
            if len(decs) > 1:
                findings.append(("precision", w, f"{rel} at {w}: one row prints {', '.join(f.raw for f in fs)} "
                                                 f"at {' and '.join(map(str, decs))} decimals ({_ctx(fs[0])!r})"))
        # precision: a moving average at its asset's price decimals (the page's price, labeled "Price")
        price = _page_price(nodes)
        if price is not None:
            for name, subj, val, el, line in labeled(nodes, one_subject=True):
                if name.endswith("day average") and subj is None and val.startswith("$"):
                    d = len(val.split(".")[1]) if "." in val else 0
                    if d != price.dec:
                        findings.append(("precision", w, f"{rel} at {w}: {name} {val} at {d} decimals beside the price "
                                                         f"{price.raw} at {price.dec}"))
        vis = " ".join(" ".join(t.split()) for t, _e in nodes)
        # next: the time of the next slot, printed once ("the home's next slot time printed once")
        nxt = collections.Counter(m.group(1) for m in NEXT_TIME.finditer(vis))
        for when, k in nxt.items():
            if k > 1:
                findings.append(("next", w, f"{rel} at {w}: the next slot's time '{when}' printed {k} times"))
        # stamp
        if re.search(r"\bfrom the last build\b", vis):
            findings.append(("stamp", w, f"{rel} at {w}: prints 'from the last build' (retired: a block names its own read)"))
        for m in re.finditer(r"(?:Chart levels|The chart read)(?: (?:for|on) [A-Z][\w ]+?)?, (?:read )?([A-Z][a-z]{2}[a-z]* \d{1,2})\b"
                             r"(?!, \d{1,2}:\d\d [AP]M ET)(?!, 20\d\d)", vis):
            findings.append(("stamp", w, f"{rel} at {w}: '{m.group(0)}' carries a date with no read time "
                                         f"(the house wording: 'Chart levels, read Oct 25, 8:17 PM ET')"))
        if findings and w == WIDTHS[0]:
            pass
    # one finding per (kind, text) across widths: a fact printed twice at both widths is one fault
    out, keys = [], set()
    for k, w, t in findings:
        key = (k, re.sub(r" at \d+:", ":", t))
        if key not in keys:
            keys.add(key)
            out.append((k, w, t))
    return out


# ---- a moving average against the desk's own series --------------------------------------------------------------------

BOARD = (("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL"), ("ripple", "XRP"), ("binancecoin", "BNB"),
         ("dogecoin", "DOGE"), ("cardano", "ADA"))
COIN_PAGE = {"BTC": "coins/btc.html", "ETH": "coins/eth.html", "SOL": "coins/sol.html", "XRP": "coins/xrp.html",
             "BNB": "coins/bnb.html", "DOGE": "coins/doge.html", "ADA": "coins/ada.html"}


def series_averages(history_dir, cid, days=10):
    """{window: [values]} for the 50- and 200-day averages the desk's stored closes give, through each of the last `days` closes,
    with and without a day's price appended (the run appends one): every value a correct build could print for the coin."""
    import json as _json
    try:
        closes = (_json.load(open(os.path.join(history_dir, f"{cid}.json"), encoding="utf-8")).get("closes") or {})
    except Exception:
        return {}
    dates = sorted(closes)
    vals = [float(closes[d]) for d in dates]
    out = {50: [], 200: []}
    for k in range(max(1, len(vals) - days), len(vals) + 1):
        base = vals[:k]
        for tail in ([], vals[k:k + 1]):
            seq = base + tail
            for n in (50, 200):
                if len(seq) >= n:
                    out[n].append(sum(seq[-n:]) / n)
    return out


def _walk(e):
    for k in e.elems():
        yield k
        yield from _walk(k)


def table_averages(dom):
    """(label, None, value text, cell, context) for each cell of a table column headed 50-day or 200-day (the Chart Master table)."""
    out = []
    for t in (e for e in _walk(dom) if e.tag == "table"):
        rows = [e for e in _walk(t) if e.tag == "tr"]
        if not rows:
            continue
        head = [" ".join(_text(c).split()) for c in rows[0].elems() if c.tag in ("th", "td")]
        cols = {i: ("the 200-day average" if "200" in h else "the 50-day average") for i, h in enumerate(head)
                if re.search(r"\b(?:50|200)-day\b", h)}
        for r in rows[1:]:
            cells = [c for c in r.elems() if c.tag in ("th", "td")]
            for i, name in cols.items():
                if i < len(cells):
                    v = " ".join(_text(cells[i]).split())
                    if re.fullmatch(r"\$\d[\d,]*(?:\.\d+)?", v):
                        out.append((name, None, v, cells[i], " ".join(_text(r).split())))
    return out


def averages_check(tree, history_dir, pages=None):
    """Every 50- and 200-day average printed for a Board coin past two decimals, against the desk's own series. A figure whose
    digits past the second decimal are zeros, and which no close of the last ten days gives at those decimals, is a two-decimal
    figure padded to its row's precision ($0.0900 for an average stored as 0.09 when the closes give 0.0875): it is printed at a
    precision the desk does not hold, a "precision" finding. (A build that reads the market at build time can hold a close the
    tree's series does not, so an unpadded figure is not judged here; its row's decimals are.)"""
    found = []
    rels = pages or (list(COIN_PAGE.values()) + ["chartmaster.html", "pulse/posture.html"])
    sym_re = re.compile(r"\b(" + "|".join(s for _c, s in BOARD) + r")\b")
    cid_of = dict((s, c) for c, s in BOARD)
    cache = {}
    for rel in rels:
        p = os.path.join(tree, rel)
        if not os.path.exists(p):
            continue
        h = open(p, encoding="utf-8", errors="replace").read()
        dom = parse(h)
        sheet = Sheet(site_css(tree, h) + re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", h), WIDTHS[1])
        nodes = [(t, e) for t, e in printed(dom, sheet) if not in_prose(e)]
        page_sym = next((s for s, r in COIN_PAGE.items() if r == rel), None)
        for name, _subj, val, el, ctx in labeled(nodes, one_subject=bool(page_sym)) + table_averages(dom):
            if not name.endswith("day average") or not val.startswith("$"):
                continue
            sym = page_sym
            if sym is None:
                for a in ancestors(el):
                    if a.tag in ROWS or any("card" in c for c in a.cls):
                        m = sym_re.search(_text(a))
                        if m:
                            sym = m.group(1)
                            break
            if sym is None:
                continue
            n = 200 if name.startswith("the 200") else 50
            if sym not in cache:
                cache[sym] = series_averages(history_dir, cid_of[sym])
            cands = cache[sym].get(n) or []
            if not cands:
                continue
            num = val[1:].replace(",", "")
            dec = len(num.split(".")[1]) if "." in num else 0
            v = float(num)
            padded = dec > 2 and re.fullmatch(r"\d*\.\d\d0+", num) is not None
            if padded and not any(abs(round(c, dec) - v) <= 10 ** (-dec) * 1.01 for c in cands):
                near = min(cands, key=lambda c: abs(c - v))
                found.append(("precision", WIDTHS[1], f"{rel}: {sym} {name} printed {val} at {dec} decimals; the desk's series "
                                                      f"gives {near:.{dec + 2}f}, so the printed digits are not the desk's figure"))
    out, seen = [], set()
    for f in found:
        if f[2] not in seen:
            seen.add(f[2])
            out.append(f)
    return out


def _page_price(nodes):
    """The price a coin page prints in its Price reading: the figure after a block that says exactly 'Price'."""
    for i, (t, e) in enumerate(nodes):
        if t.strip() == "Price" and i + 1 < len(nodes):
            fs = figures([nodes[i + 1]])
            if fs and fs[0].unit == "$":
                return fs[0]
    return None


def sweep(tree, pages=None, history_dir=None):
    """{rel: [findings]} for every .html page under `tree` (or the `pages` given, relative paths); with `history_dir` (the desk's
    stored closes, data/history) the averages are also read against the series."""
    out = {}
    rels = pages or sorted(os.path.relpath(os.path.join(dp, f), tree) for dp, _d, fs in os.walk(tree) for f in fs
                           if f.endswith(".html"))
    css_cache = {}
    for rel in rels:
        h = open(os.path.join(tree, rel), encoding="utf-8", errors="replace").read()
        if "<body" not in h:
            continue
        hrefs = tuple(re.findall(r'href="(/assets/[^"?]+\.css)', h))
        if hrefs not in css_cache:
            css_cache[hrefs] = site_css(tree, h)
        inline = re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", h)
        f = sweep_page(h, css_cache[hrefs] + inline, rel)
        if f:
            out[rel] = f
    if history_dir:
        for k, w, t in averages_check(tree, history_dir, pages=[r for r in (pages or rels)
                                                                    if r in set(COIN_PAGE.values()) | {"chartmaster.html", "pulse/posture.html"}]):
            out.setdefault(t.split(":", 1)[0], []).append((k, w, t))
    return out


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    tree = argv[0]
    hd = argv[argv.index("--history") + 1] if "--history" in argv else None
    res = sweep(tree, history_dir=hd)
    n = sum(len(v) for v in res.values())
    if "--count" in argv:
        kinds = collections.Counter(k for v in res.values() for k, _w, _t in v)
        fam = collections.Counter(r.split("/")[0] if "/" in r else r for r in res)
        print(f"FACT SWEEP: {n} finding(s) on {len(res)} page(s); by kind {dict(kinds)}; by family {dict(fam)}")
    else:
        for rel, fs in res.items():
            for k, _w, t in fs:
                print(f"{k.upper():9} {t}")
        print(f"FACT SWEEP: {n} finding(s) on {len(res)} page(s)")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
