#!/usr/bin/env python3
"""ONE FACT ONCE, AT THE BUILD (Sprint 9.9.2; fix round 3 under entry 2026-10-27-C8): every page the build writes passes through
withhold() before it is written, and a quoted unit that prints a fact the page already prints is withheld whole.

NOTHING STORED IS EVER CUT (J-10, C6). A stored unit prints whole as published or is withheld whole: no sentence is ever taken out of a
headline, a dek, a body, a key fact, a bottom line, a Brief, a card's summary or a correction. A story page's own fields, an Edition's
brief, a correction, a stored read and the page's own data are never withheld at all.

WHAT MAY BE WITHHELD is a whole quoted unit: a story item (a row, a card or a link that quotes one stored story elsewhere on the site:
related stories, an Edition's rail and down-page cards, the news front's rows) or, on a complete index, a card's summary field (the
entry, its headline and its link always stay). It is withheld only when both hold, at each width a reader can see it (375 and 1440,
through the site's own stylesheets):
  1. it prints a fact that something else on the page prints, and the sweep counts the two as two printings (fact_sweep.one_fact and
     fact_sweep.one_printing: the same test the canary runs, so the build and the gate cannot drift apart);
  2. every fact it prints (each figure, each named reading) stays printed on the page by something that stays: the fact is never
     hidden, only its second printing.
The units are read in the order a reader meets them, so it is the second listing that goes.

A COMPLETE INDEX KEEPS EVERY ENTRY: the archive, the month archives, the storyline pages and the Record's full index never lose a row.

THE HOME. The Morning Brief card is a stored unit and prints whole; a data figure printed alone in its element that repeats a fact the
card prints yields instead (its element says "In the Brief", the tile keeping its label, window and source), and a gauge's number that
repeats a reading the card prints is withheld with its drawing kept. Data is the build's own line, never a stored text.

A list left with no item is withheld with its heading. No network, no model."""
import os
import re
from html.parser import HTMLParser

import fact_sweep as fs

HERE = os.path.dirname(os.path.abspath(__file__))
# the boxes that only hold story items (a story's "Related stories", an Edition's rail): one left with no item goes with its heading
LISTS = frozenset(("related", "more-on", "link-list", "ed-rail", "ed-downpage", "cn-news", "bd-rec-rows"))
VOID = fs.VOID
_CSS = {}


def complete_index(rel, el=None):
    """A page or a region that lists every story it covers, by its own words: the archive ("Every published story"), a month archive
    and a storyline's pages ("Every checked story ..."), and the Record's full index. It never loses an entry."""
    if rel == "archive.html" or (rel.startswith("news/") and rel.endswith(".html")):
        return True
    return el is not None and any("bd-rec-index" in a.cls for a in fs.ancestors(el))


def site_css():
    """The site's two stylesheets as the build ships them (the build strips only their comments)."""
    if not _CSS:
        for n in ("site.css", "system.css"):
            p = os.path.join(HERE, "site", "assets", n)
            _CSS[n] = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    return [_CSS["site.css"], _CSS["system.css"]]


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


def _inside(e, u):
    return any(a is u for a in fs.ancestors(e))


def _story_link(e):
    return e.tag == "a" and fs.STORY_HREF.match(e.attrs.get("href") or "") is not None


def _candidates(dom, rel, own):
    """The quoted units a reader meets, in order: (element, kind)."""
    out = []

    def walk(e):
        for k in e.elems():
            if k.tag in fs.NOTEXT:
                continue
            if k.tag != "#root" and fs.story_item(k) and "ed-lead" not in k.cls:
                urls = fs._story_urls(k)
                if own and fs._norm_href(next(iter(urls))) == fs._norm_href(own):
                    walk(k)
                    continue
                if complete_index(rel, k):
                    # the entry stays; only a card's summary field may go, whole
                    for f in fs._walk(k):
                        if f.cls & fs.CARD_FIELDS or (f.tag == "p" and not f.cls and not any(_story_link(x) for x in fs._walk(f))):
                            out.append((f, "summary"))
                    continue
                out.append((k, "item"))
                continue
            walk(k)
    walk(dom)
    return out


def _facts(nodes):
    """(figures, readings) printed in a list of (text, element) nodes: the facts the sweep reads."""
    figs = fs.figures(nodes)
    fs.set_windows(nodes, figs)
    ticks = fs.axis_ticks(figs)
    figs = [f for f in figs if id(f) not in ticks and (fs.significant(f) or fs.in_text(f.el))]
    reads = []
    for name, subj, _v, el, _l in fs.labeled(nodes):
        if el is not None:
            reads.append(("market" if name == "Fear & Greed" else subj, name, el))
    return figs, reads


def withhold(src, rel="", css=None):
    """(html, [what was withheld]) for one built page. A page with nothing to withhold comes back byte for byte."""
    if "<body" not in src:
        return src, []
    tree = _Tree(src)
    tree.feed(src)
    tree.close()
    dom = tree.root
    fs._ITEM.clear()
    fs._TEMPLATE.clear()
    own = "/" + rel[:-5] if rel.endswith(".html") else None
    ids = {e.attrs["id"]: e for e in fs._walk(dom) if e.attrs.get("id")}
    sheets = (css if css is not None else site_css()) + re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", src)
    views = []
    for w in fs.WIDTHS:
        nodes = fs.printed(dom, fs.Sheet(sheets, w))
        figs, reads = _facts(nodes)
        views.append((w, figs, reads))
    edits, said, gone = [], [], []

    # 1. THE HOME: data yields to the Morning Brief card, which prints whole
    if rel == "index.html":
        card = next((e for e in fs._walk(dom) if "h-narrative" in e.cls), None)
        if card is not None:
            done = set()
            for _w, figs, reads in views:
                mine = [x for x in figs if _inside(x.el, card)]
                for g in figs:
                    if _inside(g.el, card) or id(g.el) in done or fs.unit_of(g.el, own) is not None:
                        continue
                    if any(fs.one_fact(x, g) for x in mine) and _leaf_figure(g):
                        done.add(id(g.el))
                        edits.append((g.el.s1, g.el.e0, "In the Brief"))
                        said.append(("yielded", rel, g.raw.strip()))
                card_reads = {(s, n) for s, n, el in reads if _inside(el, card)}
                for s, n, el in reads:
                    if _inside(el, card) or id(el) in done or (s, n) not in card_reads:
                        continue
                    if fs.BARE.match(fs._text(el) or ""):
                        done.add(id(el))
                        edits.append((el.s0, el.e1, ""))
                        said.append(("yielded", rel, f"{n} {fs._text(el).strip()}"))

    # 2. QUOTED UNITS, in the order a reader meets them: the second printing goes, and only when its facts stay printed
    cands = _candidates(dom, rel, own)
    order = {id(u): i for i, (u, _k) in enumerate(cands)}

    def _later(el, i):
        """True when `el` sits in a quoted unit the reader meets after unit i (it may go in its turn)."""
        return any(order.get(id(a), -1) > i for a in fs.ancestors(el))
    for i, (u, kind) in enumerate(cands):
        if any(_inside(u, g) for g in gone):
            continue
        twin, covered, shown = False, True, False
        for _w, figs, reads in views:
            mine = [x for x in figs if _inside(x.el, u)]
            mine_r = [(s, n) for s, n, el in reads if _inside(el, u)]
            # what stays: everything not in this unit, not withheld, and not a later quoted unit (it may go in its turn)
            rest = [g for g in figs if not _inside(g.el, u) and not any(_inside(g.el, x) for x in gone)
                    and not _later(g.el, i)]
            rest_r = {(s, n) for s, n, el in reads if not _inside(el, u) and not any(_inside(el, x) for x in gone)
                      and not _later(el, i)}
            if mine or mine_r:
                shown = True
            for x in mine:
                hits = [g for g in rest if fs.one_fact(x, g)]
                if not hits:
                    covered = False
                elif any(not fs.one_printing(x, g, own, ids) for g in hits):
                    twin = True
            for s, n in mine_r:
                if (s, n) in rest_r:
                    twin = True
                else:
                    covered = False
        if shown and twin and covered:
            gone.append(u)
            edits.append((u.s0, u.e1, ""))
            text = " ".join(fs._text(u).split())
            said.append((kind, rel, text[:120]))
    if not edits:
        return src, []
    # 3. a list left with no item is withheld with its heading
    for holder in (e for e in fs._walk(dom) if e.cls & LISTS):
        items = [k for k in fs._walk(holder) if k.tag != "#root" and fs.story_item(k)]
        if items and all(any(_inside(k, g) for g in gone) for k in items) and not any(_inside(holder, g) for g in gone):
            edits.append((holder.s0, holder.e1, ""))
            gone.append(holder)
    out = src
    for a, b, rep in sorted(_outer(edits), key=lambda x: x[0], reverse=True):
        out = out[:a] + rep + out[b:]
    return out, said


def vanished(src, out, css=None):
    """The figures `src` prints at a width that `out` prints nowhere at that width: what a withholding hid. The pass is built so this
    is always empty (a unit goes only when every fact it prints stays printed); the build runs it on every page it changed and the
    canary fails on anything it finds."""
    def vals(h):
        dom = fs.parse(h)
        sheets = (css if css is not None else site_css()) + re.findall(r"(?is)<style\b[^>]*>(.*?)</style>", h)
        return {w: fs.figures(fs.printed(dom, fs.Sheet(sheets, w))) for w in fs.WIDTHS}
    a, b = vals(src), vals(out)
    # one figure is the same figure at either precision ($63,654 and $63,653.85: fact_sweep.Fig.same), sign and window aside
    lost = set()
    for w in a:
        for f in a[w]:
            if not any(f.unit == g.unit and f.num == g.num and f.mag == g.mag or _same_value(f, g) for g in b[w]):
                lost.add(f.raw.strip())
    return sorted(lost)


def _same_value(f, g):
    if f.unit != g.unit or min(f.sig, g.sig) < 4:
        return False
    st = max(f.step(), g.step())
    return abs(abs(f.value) - abs(g.value)) <= st / 2 + 1e-12 * max(1.0, abs(f.value))


def _leaf_figure(g):
    """A figure printed alone in its element ("+$110.3M" in a tile, "$79,839" on the tape), arrows and signs aside."""
    if g.el is None or g.el.elems():
        return False
    t = re.sub(r"[▲▼+\-−\s]", "", fs._text(g.el))
    return t == re.sub(r"[+\-−\s]", "", g.raw)


def _outer(edits):
    """The edits with any edit inside another dropped (the outer one removes it already)."""
    edits = sorted(set(edits), key=lambda x: (x[0], -x[1]))
    out = []
    for a, b, r in edits:
        if out and a >= out[-1][0] and b <= out[-1][1]:
            continue
        out.append((a, b, r))
    return out
