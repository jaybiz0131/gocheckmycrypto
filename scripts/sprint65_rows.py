#!/usr/bin/env python3
"""
sprint65_rows.py <production-prices.html> <outdir>

Sprint 6.5 proof. Reads the Top 100 page production served (its 100 real rows, recorded) and writes
<outdir>/rows-before.html (the tbody exactly as production served it) and <outdir>/rows-after.html
(the same rows with the new name cell and price class from site_build, every other cell verbatim),
so the contact sheets show real rows, before beside after. Prints the longest-price and
longest-name symbols. Nothing here is synthetic.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main(src, out):
    import site_build as sb
    h = open(src, encoding="utf-8").read()
    body = re.search(r"<tbody[^>]*>(.*?)</tbody>", h, re.S).group(1)
    rows = re.findall(r"<tr data-sym=.*?</tr>", body, re.S)
    new = []
    for r in rows:
        sym = re.search(r'data-sym="([^"]*)"', r).group(1)
        m = re.search(r'<td class="sym2"><a class="t1-a" href="([^"]*)">(.*?)<span class="mut"> &middot; <span class="t1-name">([^<]*)</span></span></a></td>', r, re.S)
        nm_html = m.group(3)
        import html as _h
        nm = _h.unescape(nm_html)
        cell = (f'<td class="sym2"><a class="t1-a" href="{m.group(1)}" title="{sb.esc(nm)}" aria-label="{sb.esc(nm)} ({sb.esc(sym)})">'
                f'{m.group(2)}<span class="mut"><span class="t1-dot"> &middot; </span>'
                f'<span class="t1-name">{sb._name_words(nm)}</span></span></a></td>')
        r2 = r.replace(m.group(0), cell)
        pm = re.search(r'<td class="pnum( pn-long)?" data-cell="price" data-val="([^"]*)">([^<]*)</td>', r2)
        r2 = r2.replace(pm.group(0), f'<td class="pnum{sb._price_class(_h.unescape(pm.group(3)))}" data-cell="price" data-val="{pm.group(2)}">{pm.group(3)}</td>')
        new.append(r2)
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "rows-before.html"), "w", encoding="utf-8").write("".join(rows))
    open(os.path.join(out, "rows-after.html"), "w", encoding="utf-8").write("".join(new))
    syms = [(re.search(r'data-sym="([^"]*)"', r).group(1), re.search(r'data-cell="price" data-val="[^"]*">([^<]*)<', r).group(1),
             re.search(r'class="t1-name">([^<]*)<', r).group(1)) for r in rows]
    lp = max(syms, key=lambda x: len(x[1]))
    ln = max(syms, key=lambda x: max(len(w) for w in x[2].split()))
    print(f"rows {len(rows)}; longest price {lp[0]} {lp[1]}; longest word {ln[0]} {ln[2]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
