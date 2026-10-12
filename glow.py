#!/usr/bin/env python3
"""
glow.py: the one line style for every line chart on the site (Program 7, Sprint 7.1).

Jack's approved design, part 2: the line 3 px in the direction color with a glow (an SVG
gaussian blur at stdDeviation 4, merged twice under the source), the high and low as white
dots ringed in green and red, each glowing, and the last point as a 6 px dot on a soft halo
(radius 16, 55 percent to 0). The home page's Bitcoin card draws its own copy of this with
labels and day names (home.tape_chart); every other chart calls here.

DEFS goes once on every page (site_build.shell): one filter and three halo gradients, read
by id from any inline SVG on the page, so a chart carries no defs of its own. The filter's
region is absolute user units, wide enough for every chart's viewBox: in user space a
percentage would resolve against the 0 by 0 defs SVG and erase the line, and the default
bounding-box region would erase a flat (zero-height) series. The gradients
take their color from the tokens, so dark mode needs nothing extra.

Two kinds of chart call this. A chart that keeps its aspect gets round dots and an even
glow from plain circles. A chart drawn with preserveAspectRatio="none" (stretched to its
box) would turn a circle into an ellipse, so `stretched=True` draws each dot as a zero-length
round-capped stroke with vector-effect non-scaling-stroke, which stays round at any stretch.

Glow is static: nothing here animates.
"""

FILTER = "gl"

DEFS = ('<svg class="gl-defs" width="0" height="0" aria-hidden="true" focusable="false" '
        'style="position:absolute;width:0;height:0;overflow:hidden">'
        '<defs><filter id="gl" filterUnits="userSpaceOnUse" x="-500" y="-500" '
        'width="5000" height="3000">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
        '</feMerge></filter>'
        + "".join(f'<radialGradient id="gl-halo-{k}"><stop offset="0" style="stop-color:{c};'
                  f'stop-opacity:.55"/><stop offset="1" style="stop-color:{c};stop-opacity:0"/>'
                  f'</radialGradient>'
                  for k, c in (("up", "var(--up-line)"), ("down", "var(--down-line)"),
                               ("flat", "var(--ink)")))
        + '</defs></svg>')


def direction(vals):
    """'up', 'down' or 'flat': the series' own last against its first."""
    v = [x for x in vals or [] if isinstance(x, (int, float))]
    if len(v) < 2 or v[-1] == v[0]:
        return "flat"
    return "up" if v[-1] > v[0] else "down"


def line(points, d, stretched=False, width=None):
    """The data line. `points` is the polyline's points string."""
    d = d if d in ("up", "down") else "flat"
    ve = ' vector-effect="non-scaling-stroke"' if stretched else ""
    sw = f' style="stroke-width:{width}"' if width else ""
    return (f'<polyline class="gl-l {d}" points="{points}" filter="url(#{FILTER})"{ve}{sw}/>')


def _dot(x, y, cls, size, stretched):
    if stretched:
        return (f'<path class="{cls}" d="M{x:.1f},{y:.1f}h0" vector-effect="non-scaling-stroke" '
                f'style="stroke-linecap:round;stroke-width:{size}px"/>')
    return f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{size / 2:g}"/>'


def marks(xy, vals, d, stretched=False, scale=1.0, hilo=True):
    """The glowing marks: a halo and a 6 px dot on the last point, and (with `hilo`) the
    high and low as white dots ringed in green and red. `xy` are the line's points as
    (x, y) in the SVG's units; `scale` is SVG units per CSS pixel at the chart's usual
    size, so a dot is 6 px and the halo 16 px where the chart is read."""
    if not xy or len(xy) != len(vals):
        return ""
    d = d if d in ("up", "down") else "flat"
    s = float(scale or 1.0)
    out = []
    lx, ly = xy[-1]
    if stretched:
        out.append(f'<path class="gl-halo {d}" d="M{lx:.1f},{ly:.1f}h0" '
                   f'vector-effect="non-scaling-stroke" style="stroke-linecap:round;'
                   f'stroke-width:14px;opacity:.3"/>')
    else:
        out.append(f'<circle class="gl-halo" cx="{lx:.1f}" cy="{ly:.1f}" r="{16 * s:g}" '
                   f'fill="url(#gl-halo-{d})"/>')
    if hilo and len(vals) >= 3:
        hi, lo = vals.index(max(vals)), vals.index(min(vals))
        for i, cls in ((hi, "gl-hi"), (lo, "gl-lo")):
            if i == len(vals) - 1:
                continue
            x, y = xy[i]
            if stretched:
                ring = "var(--up-line)" if cls == "gl-hi" else "var(--down-line)"
                out.append(f'<path d="M{x:.1f},{y:.1f}h0" vector-effect="non-scaling-stroke" '
                           f'style="stroke:{ring};stroke-linecap:round;stroke-width:9px"/>'
                           f'<path d="M{x:.1f},{y:.1f}h0" vector-effect="non-scaling-stroke" '
                           f'style="stroke:#FFFFFF;stroke-linecap:round;stroke-width:4px"/>')
            else:
                out.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{4.5 * s:g}" '
                           f'style="stroke-width:{2.5 * s:g}"/>')
    if stretched:
        col = {"up": "var(--up-line)", "down": "var(--down-line)"}.get(d, "var(--ink)")
        out.append(f'<path class="gl-now {d}" d="M{lx:.1f},{ly:.1f}h0" '
                   f'vector-effect="non-scaling-stroke" style="stroke:{col};'
                   f'stroke-linecap:round;stroke-width:6px"/>')
    else:
        out.append(f'<circle class="gl-now {d}" cx="{lx:.1f}" cy="{ly:.1f}" r="{3 * s:g}"/>')
    return f'<g class="gl-marks" filter="url(#{FILTER})">{"".join(out)}</g>'


def parse(points):
    """'x,y x,y' to [(x, y)]."""
    out = []
    for p in str(points or "").split():
        try:
            a, b = p.split(",")
            out.append((float(a), float(b)))
        except ValueError:
            continue
    return out
