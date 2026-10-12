#!/usr/bin/env python3
"""
color_truth.py: a figure's color and arrow agree with the number printed beside it
(Jack's ruling 4, 12 October 2026, Program 7 Sprint 7.1).

`contradictions(html)` reads rendered markup and names every place where they do not:

  * a tile whose figure is colored one way while a change printed on the same tile, outside
    its own colored span, says the other way ("+0.05%" green beside "Down 0.67% since
    yesterday's close");
  * a change that carries its own color (a span classed up or down) whose sign or arrow
    says the other way;
  * the home band's sentence quoting a Bitcoin day change (Program 6.2: the tape is the one
    place it prints, so the band can never disagree with it).

`python3 scripts/color_truth_test.py` renders a fixture where the 24-hour change and the
since-close change disagree in sign and runs this over it.
"""

import html as _html
import re

_ARTICLE = re.compile(r'<article class="tl(?: [^"]*)?"[^>]*>(.*?)</article>', re.S)
_FIG = re.compile(r'<p class="tl-f( up| down)?"')
# a change that carries its own color: any element classed up or down that is not the figure
_SELF = re.compile(r'<(span|b|em)\s+class="(?![^"]*\btl-f\b)([^"]*?\b(up|down)\b[^"]*)"[^>]*>'
                   r'(.*?)</\1>', re.S)
_CHG = re.compile(r'(?:(?<![\w$.])([+\-−])\s?\d[\d,]*(?:\.\d+)?\s*%'
                  r'|\b(up|down)\s+(?:by\s+)?\d[\d,]*(?:\.\d+)?\s*(?:%|percent)'
                  r'|([▲▼])\s*[+\-−]?\d[\d,]*(?:\.\d+)?\s*%)', re.I)
_BAND = re.compile(r'<p class="h-nline">(.*?)</p>', re.S)


def _text(s):
    return _html.unescape(re.sub(r"<[^>]+>", " ", s))


def _signs(text):
    out = []
    for m in _CHG.finditer(text):
        sym, word, arrow = m.group(1), m.group(2), m.group(3)
        if arrow:
            out.append(("up" if arrow == "▲" else "down", m.group(0).strip()))
        elif word:
            out.append(("up" if word.lower() == "up" else "down", m.group(0).strip()))
        elif sym:
            out.append(("up" if sym == "+" else "down", m.group(0).strip()))
    return out


def contradictions(html):
    found = []
    for m in _SELF.finditer(html):
        cls = m.group(3)
        for sign, said in _signs(_text(m.group(4))):
            if sign != cls:
                found.append(f"a change colored {cls} reads {said!r}")
    for art in _ARTICLE.finditer(html):
        body = art.group(1)
        fm = _FIG.search(body)
        fig = (fm.group(1) or "").strip() if fm else ""
        if not fig:
            continue
        rest = _SELF.sub(" ", body)
        name = _text(re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S).group(1)).strip() \
            if "<h3" in body else "?"
        for sign, said in _signs(_text(rest)):
            if sign != fig:
                found.append(f"tile {name!r}: figure colored {fig} beside {said!r}")
    for b in _BAND.finditer(html):
        for _sign, said in _signs(_text(b.group(1))):
            found.append(f"the home band's sentence quotes a change ({said!r})")
    return found
