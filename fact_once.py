#!/usr/bin/env python3
"""ONE FACT ONCE, AT THE BUILD (Sprint 9.9.2, fix round 2, review 1 at 81b63fa): every page the build writes passes through
withhold() before it is written, and a sentence or a story item that prints a fact the page already prints is withheld.

WHAT IS WITHHELD, AND WHAT NEVER IS. Nothing is ever reworded (J-10): a sentence is printed whole or not at all, and a story item
(a list row or a card that links a stored story) is printed whole or not at all. Three kinds of printing stand and are never touched:
  - the page's data: tiles, tables, charts, headings, every line the build writes from the desk's numbers;
  - a stored text's own body: a story's headline and body (class prose), an Edition's brief (class ed-brief). A dated read stays as
    published (C6), so when it and a quotation print one fact, the quotation goes;
  - everything a page prints that is not one of the two kinds below.
What may be withheld is what QUOTES a stored text or a story: a summary block (a dek, a key fact, a take, a bottom line, a callout, a
card's summary, the home Brief card's lines, an Edition card's dek and copy, a past read in an archive), sentence by sentence; and a
story item in a list (related stories, an Edition's rail, an archive's rows), whole. A sentence is withheld when it prints a figure, or
a named reading (Fear & Greed, RSI), that the page prints elsewhere; an item when its headline does. The test of "one fact" is the
sweep's own (fact_sweep.py): the same figure, in the same window, with a subject word in common. Everything withheld is a quotation of
something still printed, on this page or on its own: the fact stays on the page, printed once.

A block left with nothing is withheld with its label; a list left with no item is withheld with its heading. No network, no model."""
import html as _html
import re
from html.parser import HTMLParser

import fact_sweep as fs

# a summary block quoting a stored text: withheld sentence by sentence
SENT = frozenset(("dek", "ed-dek", "keyfact", "take", "bottomline", "callout", "summary", "ed-copy", "h-nline", "bl-read",
                  "cm-entry-h", "bd-read", "bp-row"))
# the boxes that only hold story items (a story's "Related stories", an Edition's rail): one left with no item goes with its heading
LISTS = frozenset(("related", "more-on", "link-list", "ed-rail", "ed-front", "ed-downpage", "cn-news", "bd-rec-rows"))
# A COMPLETE LISTING lists every story it covers (the archive, the month and topic pages): a story is never dropped from one. Its row
# stays, with its link and its date; only a headline that prints a fact the page already lists is withheld, and the link says so.
POINTER = "Another report on an event this page lists"


def complete_listing(rel):
    return rel in ("archive.html", "news.html") or rel.startswith("news/")
VOID = fs.VOID


class _Node(fs.El):
    __slots__ = ("s0", "s1", "e0", "e1")


class _Tree(HTMLParser):
    """fact_sweep's tree, with each element's place in the source: s0 and s1 bound its start tag, e0 and e1 its end tag."""

    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.src = src
        self.lines = [0]
        for m in re.finditer("\n", src):
            self.lines.append(m.end())
        self.root = _Node("#root", {}, None)
        self.root.s0 = self.root.s1 = 0
        self.root.e0 = self.root.e1 = len(src)
        self.cur = self.root

    def _at(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def _new(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        e = _Node(tag, a, self.cur)
        e.s0 = self._at()
        e.s1 = e.s0 + len(self.get_starttag_text() or "")
        e.e0 = e.e1 = e.s1
        self.cur.kids.append(e)
        return e

    def handle_starttag(self, tag, attrs):
        e = self._new(tag, attrs)
        if tag not in VOID:
            self.cur = e

    def handle_startendtag(self, tag, attrs):
        self._new(tag, attrs)

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is None or n.parent is None:
            return
        at = self._at()
        k = self.src.find(">", at)
        end = k + 1 if k >= 0 else len(self.src)
        # every element the end tag closes (one left open inside it too) ends here
        c = self.cur
        while c is not n:
            c.e0 = c.e1 = at
            c = c.parent
        n.e0, n.e1 = at, end
        self.cur = n.parent

    def handle_data(self, data):
        t = _Node("#text", {}, self.cur)
        t.text = data
        t.s0 = self._at()
        t.s1 = t.e0 = t.e1 = t.s0 + len(data)
        self.cur.kids.append(t)


def _role(e):
    """'canon', 'sent', 'item' or None (the page's data), from the nearest ancestor that says."""
    for a in fs.ancestors(e):
        if a.cls & fs.CANON or a.tag == "h1":
            return "canon", a
        if a.cls & SENT:
            return "sent", a
        if a.tag != "#root" and fs.story_item(a):
            return "item", a
    return None, None


def _story_link(e):
    return e.tag == "a" and fs.STORY_HREF.match(e.attrs.get("href") or "") is not None


def _printed(dom):
    """Every printed text node (text, element), the widths together: a figure printed at either width is printed."""
    return fs.printed(dom, fs.Sheet([], 1440))


# ---- the sentences of a block ----------------------------------------------------------------------------------------------

_TOK = re.compile(r"<[^>]*>|[^<]+")
_ABBR = re.compile(r"(?:\b(?:Inc|Corp|Ltd|Co|Jr|Sr|Mr|Ms|Mrs|Dr|St|No|vs|Gov|Sen|Rep|Gen|Lt|Col|approx|est)|\b[A-Z](?:\.[A-Z])*)\.$")


def sentences(inner):
    """The raw HTML of a block's inner part, cut into sentences at depth 0 (never inside an inline element): [raw chunk]."""
    toks = _TOK.findall(inner)
    out, cur, depth = [], "", 0
    for t in toks:
        if t.startswith("<"):
            m = re.match(r"<\s*(/)?\s*([a-zA-Z0-9]+)", t)
            if m and m.group(2).lower() not in VOID and not t.endswith("/>"):
                depth += -1 if m.group(1) else 1
            cur += t
            continue
        if depth > 0:
            cur += t
            continue
        pos = 0
        for m in re.finditer(r"(?<=[.!?])(?:[\"”’')\]]*)\s+(?=[\"“‘(]?[A-Z0-9$])", t):
            head = cur + t[pos:m.start()]
            word = re.search(r"\S+$", _html.unescape(re.sub(r"<[^>]+>", "", head)).rstrip("\"”’')]"))
            if word and _ABBR.search(word.group(0)) and not re.search(r"\d[KMBT%]?\.$", word.group(0)):
                continue                      # "U.S. Freezes", "Inc. said": not a sentence's end
            out.append(cur + t[pos:m.end()])
            cur, pos = "", m.end()
        cur += t[pos:]
    if cur.strip():
        out.append(cur)
    return out


def _plain(raw):
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


# ---- one fact ---------------------------------------------------------------------------------------------------------------

def _readings(text, subj_default):
    """The named readings a sentence prints: {(name, subject)}."""
    out = set()
    for name, rx, unit in fs.LABELS:
        for m in rx.finditer(text):
            n = fs.NUM_AFTER.match(text[m.end():])
            if not n:
                continue
            if unit == "$" and not n.group(1):
                continue
            if unit == "n" and (n.group(1) or n.group(3)):
                continue
            if name == "Fear & Greed":
                out.add((name, "market"))
                continue
            head = text[max(text.rfind(". ", 0, m.start()), 0):m.start()]
            hits = [(cm.start(), sym) for sym, crx in fs.COINS for cm in crx.finditer(head)]
            out.add((name, max(hits)[1] if hits else subj_default))
    return out


def withhold(src, rel=""):
    """(html, [what was withheld]) for one built page. A page with nothing to withhold comes back byte for byte."""
    if "<body" not in src:
        return src, []
    tree = _Tree(src)
    tree.feed(src)
    tree.close()
    dom = tree.root
    fs._ITEM.clear()
    fs._TEMPLATE.clear()
    nodes = _printed(dom)
    coin = rel.startswith("coins/")
    # 1. what stands: the page's data and every stored text's own body, wherever it sits on the page
    fixed_nodes = [(t, e) for t, e in nodes if _role(e)[0] in (None, "canon")]
    figs = fs.figures(fixed_nodes)
    fs.set_windows(fixed_nodes, figs)
    ticks = fs.axis_ticks(figs)
    printed = [g for g in figs if id(g) not in ticks and (fs.significant(g) or fs.in_text(g.el))]
    reads = set()
    for name, subj, _v, el, _l in (fs.labeled(fixed_nodes, one_subject=coin) + fs.table_readings(dom, fixed_nodes)
                                    + fs.figure_readings(dom, fixed_nodes)):
        if name == "Fear & Greed":
            reads.add((name, "market"))
        elif isinstance(subj, str) and subj != "page":
            reads.add((name, subj))
        elif subj is None or subj == "page":
            reads.add((name, None))
    # 1b. THE HOME'S LEAD SENTENCE STANDS. The home is the Morning Brief's only page, and the feed promises its title and lead sentence
    # there (api/v1/brief/latest.json; sprint 9.7's check). So that sentence is never withheld: a data figure printed alone in its
    # element that repeats it yields instead, its element saying where the figure is ("In the Brief"), the tile keeping its label,
    # window and source; a gauge's number is withheld with its drawing kept.
    edits, said, gone = [], [], set()
    lead_el, lead_chunk = None, None
    if rel == "index.html":
        lead_el = next((e for e in fs._walk(dom) if "h-nline" in e.cls and "h-nsum" not in e.cls), None)
        if lead_el is not None:
            ch = sentences(tree.src[lead_el.s1:lead_el.e0])
            lead_chunk = ch[0] if ch else None
    if lead_chunk is not None:
        ltext = _plain(lead_chunk)
        lx = _figs(ltext, lead_el)
        lrd = _readings(ltext, None)
        keep_printed = []
        for g in printed:
            if any(fs.one_fact(x, g) for x in lx) and _leaf_figure(g):
                edits.append((g.el.s1, g.el.e0, "In the Brief"))
                said.append(("yielded", rel, g.raw.strip()))
            else:
                keep_printed.append(g)
        printed = keep_printed + lx
        for name, subj, v, el, _l in fs.labeled(fixed_nodes, one_subject=False):
            if el is not None and (name, "market" if name == "Fear & Greed" else subj) in {(n, s if n != "Fear & Greed" else "market")
                                                                                          for n, s in lrd} \
                    and fs.BARE.match(fs._text(el) or "") and el is not lead_el:
                edits.append((el.s0, el.e1, ""))
                said.append(("yielded", rel, f"{name} {v}"))
        reads.update(lrd)
    # 2. what quotes it, in the order a reader meets it
    units = []

    def walk(e):
        for k in e.elems():
            if k.tag in fs.NOTEXT or "sr-only" in k.cls or "hidden" in k.attrs:
                continue
            role, root = _role(k)
            if role == "item" and root is k:
                units.append(("item", k))
                walk(k)
                continue
            # a unit is a paragraph or a list entry (or an element carrying the summary class itself), never a block's label
            leaf = (k.tag in ("p", "li", "dd", "div", "blockquote") or bool(k.cls & SENT)) and "lab" not in k.cls and \
                not any(c.tag in ("p", "li", "dd", "div", "ul", "ol") for c in k.elems()) and fs._text(k).strip()
            if role == "sent" and leaf:
                units.append(("sent", k))
                continue
            if role == "item" and leaf and k.tag in ("p", "dd", "div") and not any(_story_link(a) for a in fs._walk(k)):
                units.append(("sent", k))      # a card's summary with no class of its own (an Edition rail card's paragraph)
                continue
            walk(k)
    walk(dom)
    for kind, el in units:
        if any(id(a) in gone for a in fs.ancestors(el)):
            continue
        if kind == "item":
            head = el if el.tag == "a" else next((a for a in fs._walk(el) if _story_link(a)), el)
            text = " ".join(fs._text(head).split())
            xs = _figs(text, head)
            if _hit(xs, printed, reads, _readings(text, None)) and "ed-lead" not in el.cls:
                # (an Edition's lead card is never withheld whole: the news front opens on the newest item, K-1; its quoted
                # sentences are judged below like any others)
                if complete_listing(rel) and head is not el and head.tag == "a":
                    edits.append((head.s1, head.e0, POINTER))
                    said.append(("headline", rel, text[:120]))
                    continue
                edits.append((el.s0, el.e1, ""))
                gone.add(id(el))
                said.append(("item", rel, text[:120]))
                continue
            printed.extend(xs)
            continue
        inner = tree.src[el.s1:el.e0]
        keep, out = [], []
        for i, ch in enumerate(sentences(inner)):
            if el is lead_el and i == 0:
                keep.append(ch)              # the lead sentence stands (1b)
                continue
            text = _plain(ch)
            xs = _figs(text, el)
            rd = _readings(text, None)
            if (xs or rd) and _hit(xs, printed, reads, rd):
                out.append(text)
                continue
            keep.append(ch)
            printed.extend(xs)
            reads.update(rd)
        if not out:
            continue
        said += [("sentence", rel, t[:120]) for t in out]
        if keep and any(_plain(c) for c in keep):
            edits.append((el.s1, el.e0, " ".join(c.strip() for c in keep)))
        else:
            edits.append((el.s0, el.e1, ""))
            gone.add(id(el))
    if not edits:
        return src, []
    # 3. a block or a list left with nothing is withheld with its label or heading
    unit_ids = {id(u) for _kind, u in units}
    for holder in _holders(dom):
        units_in = [k for k in fs._walk(holder) if id(k) in unit_ids]
        if units_in and all(id(k) in gone or any(id(a) in gone for a in fs.ancestors(k)) for k in units_in):
            if not any(id(a) in gone for a in fs.ancestors(holder)):
                edits.append((holder.s0, holder.e1, ""))
                gone.add(id(holder))
    out = src
    for a, b, rep in sorted(_outer(edits), key=lambda x: x[0], reverse=True):
        out = out[:a] + rep + out[b:]
    return out, said


def _leaf_figure(g):
    """A figure printed alone in its element ("+$110.3M" in a tile, "$79,839" on the tape), arrows and signs aside."""
    if g.el is None or g.el.elems():
        return False
    t = re.sub(r"[\u25b2\u25bc+\-\u2212\s]", "", fs._text(g.el))
    return t == re.sub(r"[+\-\u2212\s]", "", g.raw)


def _figs(text, el):
    """The figures a sentence or a headline prints, each tied to the element it prints in (for the sweep's own test)."""
    xs = fs.figures([(text, el)])
    fs.set_windows([(text, el)], xs)
    return xs


def _hit(xs, printed, reads, rd):
    if any(fs.one_fact(x, g) for x in xs for g in printed):
        return True
    for name, subj in rd:
        if (name, subj) in reads or (name, None) in reads or (subj is None and any(n == name for n, _s in reads)):
            return True
    return False


def _holders(dom):
    """The blocks that only hold quoted units: a summary block with its label (a key fact's "The key fact"), a list of story items
    with its heading (a "Related stories" box)."""
    for e in fs._walk(dom):
        if e.cls & SENT or e.cls & LISTS:
            yield e


def _outer(edits):
    """The edits with any edit inside another dropped (the outer one removes it already)."""
    edits = sorted(set(edits), key=lambda x: (x[0], -x[1]))
    out = []
    for a, b, r in edits:
        if out and a >= out[-1][0] and b <= out[-1][1] and (a, b) != (out[-1][0], out[-1][1]):
            if out[-1][2] == "":
                continue
            # a sentence edit inside a block edit that keeps text: the block's own edit already holds the kept text
            continue
        out.append((a, b, r))
    return out
