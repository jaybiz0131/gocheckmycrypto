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

THE SCOPE, stated once (fix round 2, review 1 at 81b63fa). Every printed figure is read, stored writing included: a Brief line beside
a tile, a dek or key fact restating its story's body, a card summary under its own headline, a story link, a data table inside a
read's card. Nothing is set aside for being prose. Two rules decide that two printings are two facts, and each is about the reader:
  - two rows of one table are two subjects (two coins at $1.00); two rows of a list are too, unless they print one figure and share
    two subject words (two stories on one seizure, "$52.8M in USDT ... Xinbi", are one event printed twice);
  - in stored writing, a figure is one fact only when its two printings share a subject word: "a 25% tariff on Brazilian goods" and
    "a 25% stake in Animoca" print the same digits and are two facts. A single shared token is not an identity (CLAUDE.md, section 2).
Within one story (its card, or a story page's own regions) a headline and a line under it printing one figure are one fact by the
figure alone ("$90T Market" over "the $90 trillion market"). The whole decision is one function, one_fact(), which the build's own
pass (fact_once.py) calls too, so what the build withholds and what the sweep finds cannot drift apart.

ONE PRINTING (fix round 3, entry 2026-10-27-C8, J-18 option (1)). A published unit repeating its own figure within itself is the
house's normal form, not two facts, so these pairs count as one printing and are not findings:
  - a stored unit's own repeats: one story's headline, dek and body (its key fact, take, bottom line and the headline and summary
    a card quotes from it are that story's own fields too, wherever on the page they print); one Edition card or brief; one
    correction; one stored read (a Brief line, a Chart Master read, a /today/ answer);
  - an Edition lead beside its own Brief on the same page: its headline, and so its dek and copy (the lead is the Brief's own unit);
  - two corrections quoting one figure (a correction quotes what it corrects), and so a story page's own correction or editor's
    note quoting the story it sits on;
  - a figure inside an in-page link whose target prints that figure (the /today/ answer linking its evidence item: the evidence item
    carries the figure, the answer links it).
Everything else is a finding and the canary fails on it: any figure printed twice across two units, and any figure printed twice
where either printing is outside stored text. The pairs counted as one printing are tallied by reason on every run (unit()), never
listed as passes of the law. unit_of() is the one definition, and the build's pass (fact_once.py) calls the same function.
No network, no model."""
import collections
import html as _html
import os
import re
import sys
from html.parser import HTMLParser

WIDTHS = (375, 1440)

# The classes the build gives stored writing (see THE SCOPE above): a stored story's, Brief's, Edition's or read's text, or a card that
# quotes it. NOTHING HERE IS SET ASIDE: every figure inside these is read. The list decides only the shared-subject rule for two
# printings in writing; which printings are one stored unit is unit_of()'s alone (ONE PRINTING, above).
TEXT = frozenset((
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
# THE UNITS (C8). A story page's own stored fields: its headline (the article's h1) and these.
STORY_FIELDS = frozenset(("prose", "dek", "keyfact", "take", "bottomline"))
# A card or a row that links one story quotes that story's fields: its headline (the link) and its summary, under one of these.
CARD_FIELDS = frozenset(("summary", "dek", "bd-read", "ed-dek", "ed-copy", "nx-read", "keyfact", "bottomline", "take"))
# A stored text that is not a story: an Edition's brief, a stored Brief read in an archive, the home's Morning Brief card, a Chart
# Master read, a /today/ answer, a wire line. Each element carrying one of these classes is one unit.
STORED_ROOT = frozenset(("ed-brief", "bl-read", "h-narrative", "cm-read", "td-read", "td-line", "ev-l"))
# A printed correction (the corrections log's entry, a dated page's correction, a chart read's, a story's own): one unit each, and two
# corrections quoting one figure are one printing (a correction quotes what it corrects).
CORR = frozenset(("co-t", "td-corr", "cm-corr"))
# A story's own body (with its headline) and an Edition's brief: never a story item the build may withhold.
CANON = frozenset(("prose", "ed-brief"))

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


def in_text(e):
    """Inside stored writing: an element of TEXT, a link to a stored story (its text is that story's headline), or a story page's
    headline. Read like everything else; this only decides the shared-subject rule."""
    for a in ancestors(e):
        if a.cls & TEXT or (a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or "")):
            return True
        if a.tag == "h1" and _piece(a) is not None:
            return True
    return False


def _piece(e):
    """The stored text a printing is the own body of: the story (its headline and its body) or the Edition brief it sits in; None for
    everything else (a quotation, a card, a tile, a table)."""
    for a in ancestors(e):
        if "ed-brief-cites" in a.cls or "sources" in a.cls:
            return None                      # a citation list inside a stored text is not that text's own words
        if a.cls & CANON:
            return _art(a)
        if a.tag == "h1":
            art = _art(a)
            if art is not None and any(k.cls & CANON for k in _walk(art)):
                return art
            return None
    return None


def _art(e):
    for a in ancestors(e):
        if a.tag == "article" or a.parent is None or a.tag == "main":
            return a
    return None


STOP = frozenset("""a about above after again against all also an and any are as at be been before being below between both but by
can could did do does down during each few for from further had has have having he her here hers him his how i if in into is it its
just more most no nor not now of off on once only or other our out over own same she should so some such than that the their them
then there these they this those through to too under until up very was we were what when where which while who whom why will with
would you your said says say according reported reports report desk per new one two three four five six seven eight nine ten
percent million billion trillion thousand crypto cryptocurrency cryptocurrencies market markets price prices day days week weeks
month months year years today yesterday tomorrow hour hours since last next first total amount
january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday
morning afternoon evening night brief""".split())


def subject_words(text):
    """The words of a printing that can name its subject: lower case, three letters or more, a plural's s dropped, no figure, no
    function word, no date or window word, none of the words every market line carries."""
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text or ""):
        w = w.lower().strip("'-").replace("'s", "")
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            w = w[:-1]
        if len(w) >= 3 and w not in STOP:
            out.add(w)
    return out


def _clause(f):
    """The text a printing says its fact in: a story link's headline; its sentence in its block; or for a tile, a row or a short block,
    the whole of it (a row's status labels, "Unconfirmed, one report", are not the subject: a story row speaks in its headline)."""
    link = next((a for a in ancestors(f.el) if a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or "")), None)
    if link is not None:
        return " ".join(_text(link).split())
    # writing speaks in its own sentence (a card's summary is not the whole card); data in its tile or row
    holder = block_of(f.el) if in_text(f.el) else (tile_of(f.el) or row_of(f.el) or block_of(f.el))
    line = " ".join(_text(holder).split())
    if len(line) <= 160:
        return line
    k = line.find(f.raw.strip())
    if k < 0:
        return line
    a = max(line.rfind(". ", 0, k), line.rfind("; ", 0, k))
    z = [x for x in (line.find(". ", k), line.find("; ", k)) if x >= 0]
    return line[a + 1 if a >= 0 else 0:min(z) if z else len(line)]


def shared_subject(f, g, need=1):
    return len(subject_words(_clause(f)) & subject_words(_clause(g))) >= need


_ITEM = {}


def _story_urls(e):
    return {(k.attrs.get("href") or "").split("#")[0].replace(".html", "") for k in [e] + list(_walk(e))
            if k.tag == "a" and STORY_HREF.match(k.attrs.get("href") or "")}


def story_item(a):
    """A row or a card that links one stored story, among siblings that link stories (a list, a run of links, a grid of cards), never
    inside a stored text's own body, never a citation in a Sources list (a source is never withheld), and never a story page's own
    article."""
    key = id(a)
    if key in _ITEM:
        return _ITEM[key]
    ok = a.tag in ("a", "li", "article", "div") and a.parent is not None and not (a.cls & CANON) and "article" not in a.cls \
        and len(_story_urls(a)) == 1 \
        and (a.tag in ("li", "article") or sum(1 for k in a.parent.elems() if _story_urls(k)) >= 2) \
        and not any(p.cls & CANON or "sources" in p.cls for p in ancestors(a))
    _ITEM[key] = ok
    return ok


def story_of(e):
    """The story a printing belongs to: the story item (card or row) it sits in, or the story page's own article; None for the rest."""
    for a in ancestors(e):
        if a.tag != "#root" and story_item(a):
            return a
        if a.tag == "article" and "article" in a.cls:
            return a
    return None


def is_head(e):
    """A story's headline: a story page's h1, or the link that names a story in a list."""
    return any(a.tag == "h1" or (a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or "")) for a in ancestors(e))


def one_fact(f, g):
    """THE TEST, used by the sweep and by the build's own pass (fact_once.py) alike: are two printings one fact printed twice?
    The same figure (sign and window agreeing), and then, by where the two sit:
      - two subjects (two table rows, two list rows or story cards not on one event, two reading tiles): no;
      - a coarse figure ($3.8B, 9%): only inside writing, with a subject word in common within one story, two across stories;
      - writing on either side: with a subject word in common (a 25% tariff and a 25% stake are two facts);
      - data on both sides: yes.
    (Two printings inside one story are one printing whatever this says: one_printing(), entry 2026-10-27-C8.)"""
    if not f.same(g):
        return False
    if two_subjects(f.el, g.el, f.window, g.window, f, g):
        return False
    sf, sg = story_of(f.el), story_of(g.el)
    ss = sf is not None and sf is sg
    if not (significant(f) and significant(g)):
        return in_text(f.el) and in_text(g.el) and shared_subject(f, g, need=1 if ss else 2)
    if in_text(f.el) or in_text(g.el):
        return shared_subject(f, g)
    return True


ROW_CLASS = re.compile(r"row$")


def row_of(e):
    """The nearest row the element sits in (a table row, a list item, or an element the build marks as a row by its class: lrow,
    td-row, cn-row), or None."""
    for a in ancestors(e):
        if a.tag in ROWS:
            return a
        if a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or "") and a.parent is not None and \
                sum(1 for k in a.parent.elems() if k.tag == "a" and STORY_HREF.match(k.attrs.get("href") or "")) > 1:
            return a                         # a run of story links (a coin page's "Checked by the desk"): each link is a row
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


def two_subjects(a, b, wa=None, wb=None, fa=None, fb=None):
    """Two rows (of one table or list, or of two) are two subjects: each row names its own (a coin, a transfer, an exchange, a week).
    A table row always does. A list row (a story, a wire line, a card) does unless the two print one figure and share two subject
    words: two stories on one seizure are one event, its figure printed twice. So are two sibling cards of one kind (the per-coin
    cards of a Markets page), and two reading tiles, each one reading under the tile law, unless both figures state one window (then
    the second tile repeats the first's figure)."""
    ra, rb = row_of(a), row_of(b)
    if ra is not None and rb is not None and ra is not rb:
        if ra.tag == "tr" or rb.tag == "tr" or fa is None or fb is None:
            return True
        return not _one_event(fa, fb, ra, rb)
    ta, tb = tile_of(a), tile_of(b)
    if ta is not None and tb is not None and ta is not tb and ta.tag == tb.tag and ta.cls == tb.cls \
            and not (wa and wb and wa == wb):
        if fa is not None and fb is not None and _has_story(ta) and _has_story(tb):
            return not _one_event(fa, fb, ta, tb)    # two story cards: two subjects only when not one event
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


_TEMPLATE = {}


def _template(row):
    """The words a list's rows all carry ("In the next 60 minutes Bitcoin rose ..."): words in half or more of the row's siblings of
    its kind, counted when the list has three rows or more. They are the list's wording, not any row's subject: the floor measured
    from the list itself, not kept by hand."""
    par = row.parent
    if par is None:
        return set()
    key = id(par)
    if key not in _TEMPLATE:
        sib = [k for k in par.elems() if k.tag == row.tag and k.cls == row.cls]
        out = set()
        if len(sib) >= 3:
            from collections import Counter
            c = Counter(w for k in sib for w in subject_words(" ".join(_text(k).split())))
            out = {w for w, n in c.items() if n * 2 >= len(sib)}
        _TEMPLATE[key] = out
    return _TEMPLATE[key]


def _one_event(fa, fb, ra, rb):
    """Two rows or two story cards printing one figure are one event when they share two subject words beyond their list's own
    wording."""
    shared = subject_words(_clause(fa)) & subject_words(_clause(fb))
    if is_head(fa.el) or is_head(fb.el):
        return len(shared) >= 2              # a headline names its own story: its words are its subject, never the list's wording
    return len(shared - _template(ra) - _template(rb)) >= 2


def _has_story(e):
    return any(k.tag == "a" and STORY_HREF.match(k.attrs.get("href") or "") for k in _walk(e))


def in_corr(e):
    return any(a.cls & CORR or ("callout" in a.cls and "corrected" in a.cls) for a in ancestors(e))


def _norm_href(h):
    return (h or "").split("#")[0].split("?")[0].replace(".html", "").rstrip("/")


# The pairs counted as one printing under C8 in this process, by reason: printed on every run, never a pass of the law in disguise.
ONE = collections.Counter()


class _Pin:
    """A named reading's element, in the shape one_printing() reads."""
    __slots__ = ("el",)

    def __init__(self, el):
        self.el = el


def unit_of(e, own=None):
    """THE UNIT (C8): the stored unit a printing belongs to, as a key, or None for text the build writes (a tile, a table, a label,
    a stamp, a line of the page's own). `own` is the page's own address ("/articles/<slug>"), so a story page's headline and fields
    are that story's. The key of a story is its address, wherever its headline or a field of it prints: a card's headline and summary,
    a link's headline and the story page's own fields are one story. Every other stored text is its own element."""
    story_field = card_field = False
    for a in ancestors(e):
        if a.tag == "#root":
            break
        if a.cls & CORR or ("callout" in a.cls and "corrected" in a.cls):
            return ("corr", id(a))
        if a.tag == "a" and STORY_HREF.match(a.attrs.get("href") or ""):
            return ("story", _norm_href(a.attrs.get("href")))
        if a.cls & STORED_ROOT:
            return ("text", id(a))
        if a.tag == "h1" or a.cls & STORY_FIELDS:
            story_field = True
        if a.cls & CARD_FIELDS or (a.tag == "p" and not a.cls):
            card_field = True              # a card's summary (an Edition rail card's paragraph carries no class of its own)
        if a.tag == "article" and "article" in a.cls:
            # a story page's own article: its h1 and its stored fields are the page's story; anything else in it (a callout the build
            # writes, a share row, a board panel) is the build's
            return ("story", _norm_href(own)) if story_field and own else None
        if card_field and story_item(a):
            urls = _story_urls(a)
            return ("story", _norm_href(next(iter(urls)))) if len(urls) == 1 else None
    return None


def _own_note(e, own):
    """A story page's own correction or editor's note (its stored fields "corrected" and "consolidated"): it quotes what it corrects,
    so a figure it shares with the story it sits on is one printing."""
    if not own:
        return False
    for a in ancestors(e):
        if "callout" in a.cls and ("corrected" in a.cls or "consolidated" in a.cls):
            return any(b.tag == "article" and "article" in b.cls for b in ancestors(a))
    return False


def _in_lead(e):
    """Inside an Edition's lead card: its headline, dek and copy. The lead is the Brief's own unit (C8)."""
    return any("ed-lead" in a.cls for a in ancestors(e))


def _in_brief(e):
    return any("ed-brief" in a.cls for a in ancestors(e))


def _ref_target(e, dom_ids):
    """The element an in-page link names ("#ev-wire-c010"), when the printing sits inside one."""
    for a in ancestors(e):
        if a.tag == "a" and (a.attrs.get("href") or "").startswith("#"):
            return dom_ids.get(a.attrs["href"][1:])
    return None


def one_printing(f, g, own=None, dom_ids=None):
    """Why two printings of one fact count as one printing under C8, or None when they are two (a finding)."""
    ua, ub = unit_of(f.el, own), unit_of(g.el, own)
    if ua is not None and ua == ub:
        return "one stored unit repeating its own figure"
    if in_corr(f.el) and in_corr(g.el):
        return "two corrections quoting one figure"
    for x, y in ((f, g), (g, f)):
        if _own_note(x.el, own) and unit_of(y.el, own) == ("story", _norm_href(own)):
            return "a story's own correction or editor's note quoting the story"
    if (_in_lead(f.el) and _in_brief(g.el)) or (_in_lead(g.el) and _in_brief(f.el)):
        return "an Edition lead beside its own Brief"
    if dom_ids:
        for x, y in ((f, g), (g, f)):
            t = _ref_target(x.el, dom_ids)
            if t is not None and any(a is t for a in ancestors(y.el)):
                return "an in-page link to the item that prints the figure"
    return None


def one_event(text_a, text_b, coarse=False):
    """Two printed lines (two stories' headlines) are one event when they print one figure and share two subject words: the sweep's
    own rule for two list rows, for a build that chooses what a list shows ("US seizes Xinbi Telegram channels, restrains $52.8M in
    USDT" and "U.S. Freezes $52.8M in USDT Tied to Xinbi Guarantee Scam Marketplace")."""
    # coarse=True reads a coarse figure too ("$61M"), as the sweep pairs one in writing that shares two subject words
    fa = [f for f in figures([(text_a or "", None)]) if coarse or significant(f)]
    fb = [f for f in figures([(text_b or "", None)]) if coarse or significant(f)]
    if not any(x.same(y) for x in fa for y in fb):
        return False
    return len(subject_words(text_a) & subject_words(text_b)) >= 2


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

FIG = re.compile(r"(?<![\w$.,])([+\-−]?)\$(\d[\d,]*(?:\.\d+)?)(?:\s?([KMBT])\b|\s((?i:thousand|million|billion|trillion))\b)?"
                 r"|(?<![\w.,$])([+\-−]?)(\d[\d,]*(?:\.\d+)?)%")
MAG_WORD = {"thousand": "K", "million": "M", "billion": "B", "trillion": "T"}
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
        """The rounding step the printing carries (0.01 for $79,771.00, 1e7 for $1.59B or "$1.59 billion")."""
        return MAG[self.mag or None] * 10 ** (-self.dec)

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


SIGN_WORDS = re.compile(r"(\u25b2|\u25bc|\b(?:up|down|rose|fell|gained|gain|make|made|lost|lose|higher|lower)\b)[^\d$%]{0,6}$", re.I)


def figures(nodes):
    """Every figure printed in a list of (text, element) nodes, with the element that prints it and its sign when the page states
    one (a sign, an arrow or a direction word just before it)."""
    out = []
    prev = ""
    for text, el in nodes:
        for m in FIG.finditer(text):
            if m.group(2) is not None:
                f = Fig("$", m.group(2), m.group(3) or MAG_WORD.get((m.group(4) or "").lower()), m.group(0), el, m.start())
                sg = m.group(1)
            else:
                f = Fig("%", m.group(6), None, m.group(0), el, m.start())
                sg = m.group(5)
            if sg:
                f.sign = 1 if sg == "+" else -1
            else:
                w = SIGN_WORDS.search((prev + " " + text[:m.start()])[-40:])
                if w:
                    f.sign = 1 if w.group(1).lower() in ("\u25b2", "up", "rose", "gained", "gain", "make", "made", "higher") else -1
            out.append(f)
        prev = text[-40:]
    return out


WINDOWS = (("settled", re.compile(r"\bperiod that settled\b", re.I)),          # a funding period's settlement record
           ("current", re.compile(r"\bcurrent 8-hour period\b", re.I)),       # the period open now: another period, another fact
           ("hour", re.compile(r"\b(?:in the hour|the hour|onset hour|next 60 minutes|one hour|per hour)\b", re.I)),
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
NUM_AFTER = re.compile(r"^(?:\s|:|\b(?:of|is|at|line|average|avg|index|reads|read|stands|stood|sits|was|near)\b)*"
                       r"(\$?)(\d[\d,]*(?:\.\d+)?)(%?)(?![\d,]*\s*(?:days?|-day)\b)")
BARE = re.compile(r"^\s*[+\-−]?(\d{1,3}(?:\.\d+)?)\s*$")
# The fixed marks of a reading's own scale: a gauge's 0, 30, 70 and 100 are its scale, not a reading.
SCALE = {"RSI": {"0", "30", "70", "100"}, "Fear & Greed": {"0", "25", "50", "75", "100"}}
COINS = (("BTC", re.compile(r"\b(?:(?i:bitcoin)|BTC)\b")), ("ETH", re.compile(r"\b(?:(?i:ether|ethereum)|ETH)\b")),
         ("SOL", re.compile(r"\b(?:(?i:solana)|SOL)\b")), ("XRP", re.compile(r"\bXRP\b")), ("BNB", re.compile(r"\bBNB\b")),
         ("DOGE", re.compile(r"\b(?:(?i:dogecoin)|DOGE)\b")), ("ADA", re.compile(r"\b(?:(?i:cardano)|ADA)\b")))


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
            subj = "market" if name == "Fear & Greed" else row_subject(el)
            if subj is None and not one_subject:
                # the coin its own sentence names before the label ("Bitcoin's RSI stands at 40.6"), else its card
                head = flat[max(flat.rfind(". ", 0, m.start()), 0):m.start()]
                hits = [(cm.start(), sym) for sym, crx in COINS for cm in crx.finditer(head)]
                subj = max(hits)[1] if hits else card_of(el)
            out.append((name, subj, n.group(1) + n.group(2) + n.group(3), el, flat[max(0, m.start() - 20):m.end() + 30]))
    # the value before its label: a tile or gauge prints "48" and then "Fear & Greed" (the home's Sentiment tile)
    for i, (text, el) in enumerate(nodes):
        b = BARE.match(text)
        if not b or svg_of(el) is not None:
            continue
        nxt = " ".join(" ".join(t.split()) for t, _e in nodes[i + 1:i + 3])
        for name, rx, unit in LABELS:
            m = rx.match(nxt)
            if m and unit == "n" and b.group(1) not in SCALE.get(name, ()):
                subj = "market" if name == "Fear & Greed" else (row_subject(el) if not one_subject else None)
                if subj is None and not one_subject:
                    subj = card_of(el)
                out.append((name, subj, b.group(1), el, f"{b.group(1)} {nxt[:60]}"))
    return out


def table_readings(dom, nodes):
    """(label, row subject, value, cell, context) for each printed cell of a table column headed by a named reading (the Chart Master
    table's RSI-14, 50-day and 200-day columns): one reading of the row's asset."""
    shown = {id(e) for _t, e in nodes}
    out = []
    for t in (e for e in _walk(dom) if e.tag == "table"):
        rows = [e for e in _walk(t) if e.tag == "tr"]
        if not rows:
            continue
        head = [" ".join(_text(c).split()) for c in rows[0].elems() if c.tag in ("th", "td")]
        cols = {}
        for i, h in enumerate(head):
            for name, rx, unit in LABELS:
                if rx.search(h):
                    cols[i] = (name, unit)
                    break
        for r in rows[1:]:
            cells = [c for c in r.elems() if c.tag in ("th", "td")]
            if not cells:
                continue
            subj = " ".join(_text(cells[0]).split())[:40]
            for i, (name, unit) in cols.items():
                if i < len(cells) and any(id(k) in shown for k in [cells[i]] + list(_walk(cells[i]))):
                    v = " ".join(_text(cells[i]).split())
                    if re.fullmatch(r"\$?\d[\d,]*(?:\.\d+)?%?", v):
                        out.append((name, subj, v, cells[i], f"{subj} {name} {v}"))
    return out


def figure_readings(dom, nodes):
    """(label, subject, value, element, context) for a chart that prints its reading in the drawing and names it in its caption (the
    RSI gauge on /chartmaster: "40.8" over the scale, "The 14-day RSI, one reading." under it). The subject is the coin the caption or
    the drawing's label names, or None when neither names one."""
    shown = {id(e) for _t, e in nodes}
    out = []
    for fig in (e for e in _walk(dom) if e.tag == "figure"):
        cap = next((k for k in _walk(fig) if k.tag == "figcaption"), None)
        if cap is None:
            continue
        ctext = " ".join(_text(cap).split())
        for name, rx, unit in LABELS:
            if unit != "n" or not rx.search(ctext):
                continue
            label_text = ctext + " " + " ".join(s.attrs.get("aria-label") or "" for s in _walk(fig) if s.tag == "svg")
            subj = next((sym for sym, crx in COINS if crx.search(ctext)), None)
            seen = set()
            for t in (k for k in _walk(fig) if k.tag == "text" and id(k) in shown):
                v = " ".join(_text(t).split())
                b = BARE.match(v)
                if b and b.group(1) not in SCALE.get(name, ()) and b.group(1) not in seen:
                    seen.add(b.group(1))
                    out.append((name, subj, b.group(1), t, f"{name} {b.group(1)} ({ctext[:50]})"))
            break
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
    _ITEM.clear()
    _TEMPLATE.clear()
    own = "/" + rel[:-5] if rel.endswith(".html") else None
    ids = {e.attrs["id"]: e for e in _walk(dom) if e.attrs.get("id")}
    for w in WIDTHS:
        sheet = Sheet(css_texts, w)
        nodes = printed(dom, sheet)
        figs = figures(nodes)
        set_windows(nodes, figs)
        ticks = axis_ticks(figs)
        # a coarse figure ($3.8B, 9%) is a fact too, but it pairs only inside writing and only with two subject words in common
        facts = [f for f in figs if id(f) not in ticks and (significant(f) or in_text(f.el))]
        # twice: every pair of printings of one fact is a finding unless C8 counts it as one printing (ONE PRINTING, above)
        seen = []
        reported = set()
        for f in facts:
            for g in seen:
                if not one_fact(f, g):
                    continue
                why = one_printing(f, g, own, ids)
                if why:
                    ONE[why] += 1
                    continue
                key = (f.unit, round(abs(f.value), 6))
                if key not in reported:
                    reported.add(key)
                    findings.append(("twice", w, f"{rel} at {w}: {g.raw.strip()} printed twice ({_ctx(g)!r} and {_ctx(f)!r})"))
                break
            seen.append(f)
        # label
        by = collections.defaultdict(list)
        coin = rel.startswith("coins/")
        reads = labeled(nodes, one_subject=coin) + table_readings(dom, nodes) + figure_readings(dom, nodes)
        for name, subj, val, el, line in reads:
            by[(name, subj)].append((val, line, el))
        for (name, subj), vals in by.items():
            if len(vals) > 1:
                pins = [_Pin(e) for _v, _l, e in vals]
                whys = [one_printing(a, b, own, ids) for i, a in enumerate(pins) for b in pins[i + 1:]]
                if all(whys):
                    for why in whys:
                        ONE[why] += 1
                    continue
                findings.append(("label", w, f"{rel} at {w}: {name} printed {len(vals)} times "
                                             f"({'; '.join(repr(l[:70]) for _v, l, _e in vals[:3])})"))
        # an unnamed reading beside named ones: "40.8" under a gauge with no coin, beside the table's BTC row at 40.6. The reader
        # cannot tell whose it is, and if it is one of theirs it is that one's reading printed twice.
        for name in {n for (n, _s) in by}:
            named = [s for (n, s) in by if n == name and isinstance(s, str) and s not in ("market", "page")]
            un = next((k for k in ((name, None), (name, "page")) if k in by), None)
            if named and un is not None and not coin:
                pins = [_Pin(e) for k in [un] + [(name, s) for s in named] for _v, _l, e in by[k]]
                whys = [one_printing(a, b, own, ids) for i, a in enumerate(pins) for b in pins[i + 1:]]
                if all(whys):
                    for why in whys:
                        ONE[why] += 1
                    continue
                findings.append(("label", w, f"{rel} at {w}: {name} printed for no named subject "
                                             f"({by[un][0][1][:60]!r}) beside {', '.join(named[:4])}"))
        # precision: one table row's dollar figures at one number of decimals
        rows = collections.defaultdict(list)
        for f in figs:
            r = row_of(f.el)
            if f.unit == "$" and r is not None and r.tag == "tr" and not f.mag:
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
        nodes = printed(dom, sheet)
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
    print("FACT SWEEP: pairs counted as one printing under entry 2026-10-27-C8: "
          + ("; ".join(f"{why}: {k}" for why, k in sorted(ONE.items())) or "none"))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
