#!/usr/bin/env python3
"""Program 9, Sprint 9.5b: the desktop board. Each case is named after what it guards.

  python3 scripts/sprint95b_test.py                   # unit cases; exit 1 on any failure
  python3 scripts/sprint95b_test.py --tree <dir>      # also the cases that read a built tree, and the browser half
  (verify_pipeline.py's canary calls unit() and tree() on the tree its build wrote)

THE BOARD LINE (docs/BOARD.md, 9.5b): at 1280 pixels and up the page wrapper widens from 1080 to about 1400 and the
home's front becomes a glance board (the verdict card, the Bitcoin and Ether lines, Big movers, Whale Watch and the
Brief in a grid, so the first screen at 1440 answers without scrolling); inner pages take the same width; nothing
changes under 1280; the token set only, no new font, script or color; the beacon stays. CLS zero on the home at both
widths. The 375 render is the same as Sprint 9.5's.

THE TWO RULES UNDER 1280 (J-11, the strategist's ruling of October 20, 2026, 3:35 PM ET, option 1): the one thing the board line forbade, a change
under 1280, was the thing its own definition of done (CLS zero at 375) and a 9.5 defect (the nav scrolling the page sideways from 768 to 1000) needed.
9.5b carries exactly two rules there: (1) the live stamp (#tapeLive) keeps three lines below 521 px, so the live price landing moves nothing; (2) the nav
wraps from 700 to 1019 px instead of scrolling the page sideways. Each sits in its own marked block whose text is held character for character
(fixtures/sprint95b/j11-stamp.css and j11-nav.css), and the 375 render test excludes exactly those two rules, by name: its 9.5 side is 9.5's CSS plus
those two files, nothing else. A third rule under 1280, anywhere, is red.

HOW "NOTHING ELSE CHANGES UNDER 1280" IS HELD, three ways, none of them a screenshot of one page:
  1. THE CSS: the 9.5b rules live in one marked block at the end of site.css and one at the end of system.css. Cut out,
     each file is byte for byte Sprint 9.5's (fixtures/sprint95b/site.95.css, system.95.css). Inside the block every rule
     is under @media (min-width:1280px), except the one that hides the Ether line below 1280.
  2. THE MARKUP: the one element 9.5b adds to the home is the Ether line, marked data-wide. With it cut out, the home
     fixtures are byte for byte Sprint 9.5's (fixtures/sprint95b/home-board-*.95.html). The Ether line is display:none
     under 1280, so it is not in the layout, the accessibility tree or the page's text.
  3. THE BROWSER (scripts/sprint95b_browser.mjs): at 375 and 390 the 9.5 page with the 9.5 CSS and the new page with the
     new CSS are laid out side by side: every element's rectangle is the same and the screenshots are pixel for pixel
     the same.

THE RECORDS ARE REAL: the home is drawn from the recorded 15 October Board (fixtures/why) with its real verdict and its
recorded whale flows, and from the same Board with no verdict. Cases marked SYNTHETIC change a real record by hand
to reach a rule the real days do not, and say so (Jack, 13 October 2026). NO MODEL CALL anywhere.
"""
import copy
import hashlib
import html as _html
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
FX = os.path.join(HERE, "fixtures", "sprint95b")
SITE_CSS = os.path.join(HERE, "site", "assets", "site.css")
SYSTEM_CSS = os.path.join(HERE, "site", "assets", "system.css")
MARK_BEGIN = "/* ===== Program 9, Sprint 9.5b"
MARK_END = "/* ===== end Sprint 9.5b ===== */"

# Sprint 9.5's HOME_JS, hashed on October 20, 2026 at 2453529. 9.5b edits no script and adds none.
HOME_JS_SHA256 = "4df64baaee46fe975e1d2e2bf832e6f6eb270fe3c053628e460c8cf02a4995e4"
# the two lines of Sprint 9.5's script that Sprint 9.7's marked block replaces (the tape's one CoinGecko read)
HOME_JS_95_FETCH = ("  fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple&vs_currencies=usd&include_24hr_change=true')\n"
                    "   .then(function(r){if(!r.ok)throw new Error(r.status);return r.json();}).then(function(d){\n")
# The script elements on Sprint 9.5's built home (ld+json, the as-of script and its call twice, the beacon, the tape's script,
# the hero and motion scripts, the service worker registration).
HOME_SCRIPT_COUNT_95 = 9


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


def read(p):
    return open(p, encoding="utf-8").read()


def visible(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h or "", flags=re.S | re.I)
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


# ---- a small CSS reader: which declaration wins at a viewport width ----------------------------------------------------

def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def flatten(css, conds=()):
    """[(media conditions, selector text, body)] for every style rule, nested @media included. @keyframes, @font-face and
    other at-rules are opaque and skipped."""
    css = _strip_comments(css)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        if prelude.startswith("@media"):
            out += flatten(body, conds + (prelude[6:].strip(),))
        elif not prelude.startswith("@"):
            out.append((conds, prelude, body.strip()))
        i = k
    return out


def media_holds(q, width):
    """True when a media query holds at `width` px (screen, light). Only width conditions are understood; any other
    condition (prefers-color-scheme, print, hover) is False, so a rule behind one is not counted."""
    for part in re.split(r"\s+and\s+|,", q):
        part = part.strip()
        if part in ("screen", "all", ""):
            continue
        m = re.fullmatch(r"\((min|max)-width:\s*([\d.]+)px\)", part)
        if not m:
            return False
        v = float(m.group(2))
        if (m.group(1) == "min" and width < v) or (m.group(1) == "max" and width > v):
            return False
    return True


def effective(css, selector, prop, width):
    """The last declaration of `prop` on a rule whose selector list names exactly `selector`, among the rules whose media
    hold at `width`. Specificity is not weighed: the rules this reads are one class each."""
    val = None
    for conds, sel, body in flatten(css):
        if selector not in [s.strip() for s in sel.split(",")] or not all(media_holds(c, width) for c in conds):
            continue
        for d in body.split(";"):
            if ":" in d and d.split(":", 1)[0].strip() == prop:
                val = d.split(":", 1)[1].strip().replace("!important", "").strip()
    return val


def px(v):
    m = re.fullmatch(r"([\d.]+)px", v or "")
    return float(m.group(1)) if m else None


J11_RULES = (("system.css", "J-11 rule 1", "j11-stamp.css"), ("site.css", "J-11 rule 2", "j11-nav.css"))


def _cut(css, begin, end):
    """(css with one marked block cut out with the blank line before it and the newline after it, the block's text or None)."""
    a = css.find(begin)
    b = css.find(end)
    if a < 0 or b < 0 or b < a:
        return css, None
    lo = a - 1 if a and css[a - 1] == "\n" else a
    hi = b + len(end)
    hi = hi + 1 if css[hi:hi + 1] == "\n" else hi
    return css[:lo] + css[hi:], css[a:b + len(end)]


def block_of(css):
    """(css with every 9.5b block cut out, the main 9.5b block's text or None). The two J-11 blocks (the strategist's ruling of
    October 20, 3:35 PM ET: the live stamp's three-line reserve and the nav's wrap, the only two rules 9.5b carries under 1280) are
    cut as well, and held to their exact text by j11_cases."""
    css, main = _cut(css, MARK_BEGIN, MARK_END)
    for n in (1, 2):
        css, _t = _cut(css, f"/* ===== Sprint 9.5b, J-11 rule {n}", f"/* ===== end J-11 rule {n} ===== */")
    return css, main


def j11_block(css, n):
    return _cut(css, f"/* ===== Sprint 9.5b, J-11 rule {n}", f"/* ===== end J-11 rule {n} ===== */")[1]


# ---- 1. the wrapper, read from the CSS ------------------------------------------------------------------------------------

def wrapper_cases(fails):
    css = read(SITE_CSS)
    print("1. the page wrapper: 1080 below 1280, about 1400 from 1280 up (read from the CSS)")
    at = lambda w: px(effective(css, ".wrap", "max-width", w))
    guarded(fails, "at 1440 the wrapper's max-width is 1400 (about 1400, from the board line)", lambda: at(1440) is not None and 1380 <= at(1440) <= 1440)
    guarded(fails, "at 1280 it is that same width, at 1920 it stops there (no wider)", lambda: at(1280) == at(1440) == at(1920) and at(1280) is not None and at(1280) > 1080)
    guarded(fails, "at 1279, 1100, 768 and 375 it is 1080, as in 9.5 (nothing changes under 1280)",
            lambda: [at(w) for w in (1279, 1100, 768, 375)] == [1080.0] * 4)
    guarded(fails, "the wrapper keeps its 22 px gutters at every width (padding is not touched)",
            lambda: all(effective(css, ".wrap", "padding", w) == "0 22px" for w in (375, 1279, 1280, 1440)))


# ---- 2. nothing changes under 1280: the CSS, cut and compared ---------------------------------------------------------------

NEW_FONT_OR_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\bhwb\(|\blab\(|\blch\(|@font-face|\burl\(|@import")
BASE_ALLOWED = ("[data-wide]", ".h-eline")


def under_1280_cases(fails):
    print("2. nothing changes under 1280: the 9.5b block and the two J-11 blocks cut out of each stylesheet leave Sprint 9.5's file, byte for byte")
    for name, path, base in (("site.css", SITE_CSS, "site.95.css"), ("system.css", SYSTEM_CSS, "system.95.css")):
        css = read(path)
        rest, blk = block_of(css)
        guarded(fails, f"{name}: the Sprint 9.5b block is there, marked at both ends", lambda blk=blk: blk is not None)
        guarded(fails, f"{name}: with the block cut out the file is Sprint 9.5's, byte for byte", lambda rest=rest, base=base: rest == read(os.path.join(FX, base)))
        if blk is None:
            continue
        rules = flatten(blk)
        stray = [(c, s) for c, s, b in rules if not any(re.fullmatch(r"\(min-width:\s*1280px\)", q.strip()) for q in c)
                 and not (any(a in s for a in BASE_ALLOWED) and b.replace(" ", "") in ("display:none", "display:none!important"))]
        guarded(fails, f"{name}: every rule in the block is under @media (min-width:1280px), except the one that hides the Ether line "
                       f"below 1280 ({'; '.join(s for _c, s in stray[:3])})", lambda stray=stray: not stray and len(rules) > 0)
        bad = NEW_FONT_OR_COLOR.findall(_strip_comments(blk))
        guarded(fails, f"{name}: no new font, color or url in the block (no hex, rgb, hsl, @font-face, url): tokens only ({bad[:3]})", lambda bad=bad: not bad)
        fam = [b for _c, _s, body in rules for b in re.findall(r"font-family:\s*([^;}]+)", body)]
        guarded(fails, f"{name}: every font-family in the block is one of the three tokens ({fam[:3]})",
                lambda fam=fam: all(re.fullmatch(r"var\(--(sans|serif|mono)\)(,[^;]*)?", f.strip()) for f in fam))
    # the media queries 9.5 already had still hold at the same widths: the 1100 two-column rule is where it was
    sysrest, _b = block_of(read(SYSTEM_CSS))
    guarded(fails, "the home's two columns still start at 1100 (9.5's rule is untouched; 9.5b changes them from 1280 only)",
            lambda: "@media (min-width:1100px){\n  body .h-cols{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:0 40px;" in sysrest)


# ---- 3. the markup: the Ether line is the only addition, and it is true -----------------------------------------------------

def fixture_html():
    import sprint95b_fixture as f
    return f.pages(None)


def _mask_v(h):
    """The two stamps that change with every commit and say nothing about the markup: the CSS content hash on the asset links,
    and the build-commit meta (git HEAD, 2453529 when the baselines were made), which differs at any commit after that one."""
    h = re.sub(r'<meta name="build-commit" content="[^"]*">', '<meta name="build-commit" content="X">', h)
    return re.sub(r"\?v=[0-9a-f]{10}", "?v=X", h)


def _cut_wide(h):
    """(html with every data-wide element cut out, how many were cut). The elements are leaf paragraphs, so a non-nested match is exact."""
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return ""
    return re.sub(r"<(\w+)\b[^>]*\bdata-wide\b[^>]*>.*?</\1>", sub, h, flags=re.S), n


def _cut_991(h):
    """SPRINT 9.9.1 (the ruling on J-8 of October 20, Review 1): the home's verdict card carries its window basis and direction as two
    attributes, and the card's place carries the notice when no verdict was read. With the notice card cut out and the two attributes
    taken off, the page is Sprint 9.5's again; scripts/sprint991_test.py holds the additions to account, as 9.7's one block is for the
    script below."""
    h = re.sub(r'<aside class="vd vd-next"[^>]*>.*?</aside>', "", h, flags=re.S)
    return re.sub(r'(<aside class="vd[^"]*" data-vd="BTC") data-vd-basis="[^"]*"(?: data-vd-dir="[^"]*")?', r"\1", h)


def _cut_992(h):
    """SPRINT 9.9.2 (one fact once): what 9.9.2 changes on the home, undone so the rest can still be held to Sprint 9.5's bytes;
    scripts/sprint992_test.py holds each change to account. The list's Ether item says it is the narrow one (data-narrow); the
    checked story's line and note are marked as one stored read (data-read); the wire's checked row points at that story instead
    of printing its line again; the week's closes and the 24-hour pair print at the price's precision (cents) where 9.5 printed
    whole dollars; and the Brief card's "Next Brief" yields to the verdict notice, which names the same slot ("Next read: ...")."""
    h = h.replace(" data-narrow", "")
    h = re.sub(r'<div data-read>(<h3 class="h-why-h">.*?</p>)</div>', r"\1", h, flags=re.S)
    m = re.search(r'<h3 class="h-why-h">(.*?)</h3>', h, flags=re.S)
    if m:
        h = h.replace("The top story, checked, above.", m.group(1))

    def whole(mm):
        v = float(mm.group(1).replace(",", ""))
        return f"<b>${v:,.0f}</b>" if v >= 1000 else mm.group(0)

    def cents_off(block):
        return re.sub(r"<b>\$([\d,]+\.\d\d)</b>", whole, block.group(0))
    h = re.sub(r'<p class="h-hl24"[^>]*>.*?</p>', cents_off, h, flags=re.S)
    h = re.sub(r'<span class="h-k [^"]*"[^>]*>.*?</span>', cents_off, h, flags=re.S)
    h = re.sub(r'aria-label="Bitcoin, \d+ daily closes, low [^"]*"',
               lambda b: re.sub(r"\$([\d,]+\.\d\d)", lambda mm: f"${float(mm.group(1).replace(',', '')):,.0f}", b.group(0)), h)
    n = re.search(r"Next read: (this morning|tonight|tomorrow) at (\d{1,2}:\d{2} [AP]M ET)", h)
    if n and 'class="h-next"' not in h:
        h = h.replace('<p class="h-today">', f'<p class="h-next">Next Brief {n.group(1)} at {n.group(2)}</p><p class="h-today">', 1)
    return h


def markup_cases(fails):
    print("3. the markup: the Ether line is the one thing added to the home, and it is the Board's own data")
    import home
    import site_build as sb
    import snapshot
    cur = fixture_html()
    for name in ("card", "nocard"):
        base = read(os.path.join(FX, f"home-board-{name}.95.html"))
        cut, n = _cut_wide(_mask_v(_cut_991(_cut_992(cur[name]))))
        guarded(fails, f"home ({name}): exactly one element is marked data-wide (the Ether line)", lambda n=n: n == 1)
        guarded(fails, f"home ({name}): with it cut out the page is Sprint 9.5's, byte for byte (the 375 markup)",
                lambda cut=cut, base=base: cut == _mask_v(base))
    h = cur["card"]
    m = re.search(r'<p class="[^"]*h-eline[^"]*"([^>]*data-wide[^>]*)>(.*?)</p>', h, re.S)
    guarded(fails, "the Ether line is a paragraph with data-eth-line, inside the tape block, after the Bitcoin line and its stamp",
            lambda: m and "data-eth-line" in m.group(1) and h.index('data-btc-line') < h.index("data-eth-line")
            and h.index('id="tapeLive"') < h.index("data-eth-line") and h.index("data-eth-line") < h.index('data-block="narrative"')
            and h.index('data-block="tape"') < h.index("data-eth-line"))
    import sprint93_test as t
    p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
    snap = snapshot.build(p, t.s92().load(f"flows_{t.D15()}.json"))
    eth = snapshot.coin(snap, "ETH")
    line = visible(m.group(0)) if m else ""
    guarded(fails, "its price is the Board's Ether price, written the way the tape writes Bitcoin's (sb._price_fmt)",
            lambda: sb._price_fmt(eth["price"]) in line and (m.group(0).count('data-tape="ethereum"') == 1))
    guarded(fails, "its change is the Board's 24-hour change, with the arrow and the sign the number has, labeled 24h",
            lambda: f"{abs(eth['chg_24h_pct']):.2f}%" in line and "24h" in line
            and ('▲' in line if eth["chg_24h_pct"] > 0 else '▼' in line if eth["chg_24h_pct"] < 0 else True)
            and 'data-tape-chg="ethereum"' in m.group(0))
    guarded(fails, "it is sourced: it names CoinGecko, the source the Board names for the coins (fields.coins.source)",
            lambda: "CoinGecko" in line and "CoinGecko" in (snap["fields"]["coins"].get("source") or ""))
    tape_blk = re.search(r'<section class="h-b h-tape"[^>]*data-block="tape">(.*?)</section>', h, re.S)
    guarded(fails, "it is stamped: the one stamp under the Bitcoin line (the coins' read time) is under it too, in the same block "
                   "(one stamp for the Board, Jack, 7 October)",
            lambda: tape_blk and tape_blk.group(1).count('class="h-live"') == 1 and 'data-eth-line' in tape_blk.group(1)
            and re.search(r'data-asof="%s"' % re.escape(snap["fields"]["coins"]["read_utc"]), tape_blk.group(1)))
    # the other Ether print (the tile in Where Bitcoin stands) is the same fact: it is hidden from 1280 so it prints once
    sysrest, blk = block_of(read(SYSTEM_CSS))
    rules = flatten(blk or "")
    hides_tile = any(any("min-width:1280px" in c for c in conds) and 'data-tile="ethereum"' in sel and re.search(r"display:\s*none", body)
                     for conds, sel, body in rules)
    shows_line = any(any("min-width:1280px" in c for c in conds) and ".h-eline" in sel and re.search(r"display:\s*(block|flex|grid)", body)
                     for conds, sel, body in rules)
    guarded(fails, "from 1280 the Ether tile in Where Bitcoin stands is hidden and the Ether line is shown: Ether's price prints once at every width "
                   "(the same fact never prints twice, October 11)", lambda: hides_tile and shows_line)
    guarded(fails, "below 1280 the Ether line is display:none in the base rule: not drawn, not read, not in the text",
            lambda: any(not any("min-width" in c for c in conds) and ".h-eline" in sel and re.fullmatch(r"display:none(!important)?", body.replace(" ", ""))
                        for conds, sel, body in rules))
    # SYNTHETIC: the Board without an Ether price, and without a 24-hour change, to reach the rules the real Board does not
    s2 = copy.deepcopy(snap)
    del s2["fields"]["coins"]["value"]["ETH"]["price"]
    guarded(fails, "SYNTHETIC: a Board with no Ether price draws no Ether line (nothing invented)", lambda: "data-eth-line" not in home.tape(s2))
    s3 = copy.deepcopy(snap)
    s3["fields"]["coins"]["value"]["ETH"].pop("chg_24h_pct")
    t3 = home.tape(s3)
    guarded(fails, "SYNTHETIC: a Board with an Ether price and no change draws the price and no change (no fake zero)",
            lambda: "data-eth-line" in t3 and 'data-tape-chg="ethereum"' not in t3 and "0.00%" not in re.search(r"<p class=\"[^\"]*h-eline.*?</p>", t3, re.S).group(0))
    s4 = copy.deepcopy(snap)
    s4["fields"]["coins"]["value"].pop("BTC")
    guarded(fails, "SYNTHETIC: a Board with no Bitcoin price draws the tape's waiting line and no Ether line (the tape's own fallback)",
            lambda: "data-eth-line" not in home.tape(s4))
    # no script was edited or added, and the beacon is not the 9.5b's to touch
    # Sprint 9.7 (the Worker live-price route, named by the board) adds one marked block to this script and replaces the two
    # lines it wraps; with that block cut out and those two lines put back, the script is Sprint 9.5's text, byte for byte
    def _js95(js):
        a = js.index("  // ===== Sprint 9.7: the Worker route")
        e = "  // ===== end Sprint 9.7 =====\n"
        b = js.index(e) + len(e)
        return js[:a] + HOME_JS_95_FETCH + js[b:]
    guarded(fails, "the tape's script is Sprint 9.5's (HOME_JS hashes the same, with Sprint 9.7's one marked block cut out): no new script, none edited",
            lambda: hashlib.sha256(_js95(home.HOME_JS).encode()).hexdigest() == HOME_JS_SHA256)


# ---- 4. the glance board's structure, from the CSS ----------------------------------------------------------------------------

def board_css_cases(fails):
    print("4. the glance board: the home's front is a grid from 1280, and inner pages' reading measures are held")
    sysrest, blk = block_of(read(SYSTEM_CSS))
    rules = flatten(blk or "")
    wide = lambda sel_part, prop: any(any("min-width:1280px" in c for c in conds) and sel_part in sel and re.search(prop, body)
                                      for conds, sel, body in rules)
    guarded(fails, "from 1280 the home's columns are a grid and the left column is itself a grid (verdict card, tape, Brief side by side)",
            lambda: wide(".h-cols", r"display:\s*grid|grid-template-columns") and wide(".h-l", r"display:\s*grid"))
    guarded(fails, "the verdict card is placed first, in the left column's first track (aside.vd)", lambda: wide("aside.vd", r"grid-column:\s*1"))
    guarded(fails, "the tape block (Bitcoin and Ether lines) and the Brief card are placed beside the card",
            lambda: wide('[data-block="tape"]', r"grid-column") and wide('[data-block="narrative"]', r"grid-column"))
    css = read(SITE_CSS)
    _r, sblk = block_of(css)
    guarded(fails, "site.css's block widens .wrap and nothing else about its box (max-width only)",
            lambda: sblk and any(sel.strip() == ".wrap" and re.fullmatch(r"max-width:\s*1400px;?", body.strip()) for conds, sel, body in flatten(sblk)))


# ---- J-11: the two rules 9.5b carries under 1280 -----------------------------------------------------------------------------

def j11_cases(fails):
    print("5. J-11 (strategist, October 20, 3:35 PM ET): 9.5b carries exactly two rules under 1280, held to their text")
    for n, (fname, label, fx) in enumerate(J11_RULES, 1):
        css = read(SYSTEM_CSS if fname == "system.css" else SITE_CSS)
        want = read(os.path.join(FX, fx)).strip()
        guarded(fails, f"{fname}: the {label} block is there once and is the named text, character for character (a third rule inside it, or a changed one, is red)",
                lambda css=css, want=want, n=n: css.count(f"/* ===== Sprint 9.5b, J-11 rule {n}") == 1 and (j11_block(css, n) or "").strip() == want)
    sy, si = read(SYSTEM_CSS), read(SITE_CSS)
    guarded(fails, "rule 1 by width: the live stamp (#tapeLive's p.h-live) has min-height 54.45px (three lines of its 18.15px) at 375 and 520, and none at 521",
            lambda: effective(sy, "body .h-tape .h-live", "min-height", 375) == "54.45px" and effective(sy, "body .h-tape .h-live", "min-height", 520) == "54.45px"
            and effective(sy, "body .h-tape .h-live", "min-height", 521) is None)
    guarded(fails, "rule 2 by width: the nav wraps at 700, 768, 900 and 1019, and not at 699 or 1020 (the tab bar below 700 is untouched)",
            lambda: all(effective(si, ".mh-nav .wrap", "flex-wrap", w) == "wrap" for w in (700, 768, 900, 1019))
            and all(effective(si, ".mh-nav .wrap", "flex-wrap", w) is None for w in (375, 699, 1020, 1280)))


# ---- the rest of the file -----------------------------------------------------------------------------------------------------

def unit():
    fails = []
    for name, fn in (("wrapper", wrapper_cases), ("under 1280", under_1280_cases), ("markup", markup_cases), ("board css", board_css_cases),
                     ("J-11", j11_cases)):
        group(fails, name, fn)
    return fails


def tree(root):
    """The cases that read a built tree. Returns the failures."""
    fails = []
    print(f"5. the built tree {root}")
    rd = lambda rel: read(os.path.join(root, rel)) if os.path.exists(os.path.join(root, rel)) else ""
    ix = rd("index.html")
    hrefs = re.findall(r'<link rel="stylesheet" href="/assets/(site|system)\.css\?v=[0-9a-f]{10}">', ix)
    guarded(fails, "the built home links site.css and system.css, versioned", lambda: hrefs == ["site", "system"])
    bs = rd("assets/site.css")
    guarded(fails, "the built site.css is the source's: .wrap is 1080 at 1279 and about 1400 at 1440 (read from the built file)",
            lambda: px(effective(bs, ".wrap", "max-width", 1279)) == 1080 and 1380 <= px(effective(bs, ".wrap", "max-width", 1440)) <= 1440)
    guarded(fails, "the built home has exactly one Ether line (the Board has an Ether price)", lambda: ix.count("data-eth-line") == 1)
    guarded(fails, "the built home's script elements are 9.5's: the same count, and the beacon exactly once",
            lambda: len(re.findall(r"<script\b", ix)) == HOME_SCRIPT_COUNT_95 and len(re.findall(r"<script\b[^>]*data-cf-beacon=", ix)) == 1)
    # every inner page takes the same width from the same stylesheet: each page links site.css and none carries a wrapper of its own
    pages = []
    for dp, _d, fs in os.walk(root):
        for f in fs:
            if f.endswith(".html") and not f.startswith(("home-board", "home-fixture", "movers-fixture")):
                pages.append(os.path.join(dp, f))
    no_css = [os.path.relpath(p, root) for p in pages if "<body" in read(p) and "/assets/site.css" not in read(p)]
    own = [os.path.relpath(p, root) for p in pages if re.search(r"max-width:\s*1080px", read(p))
           and not re.search(r"@media\s*\(min-width:\s*1280px\)\s*\{[^}]*max-width:\s*1400px", read(p))]
    guarded(fails, f"every built page links site.css, so every page takes the wrapper ({len(pages)} pages; without: {no_css[:3]})", lambda: not no_css)
    guarded(fails, f"no built page carries a 1080 wrapper of its own without its own 1400 from 1280 (the Edition's sheet does; {own[:3]})", lambda: not own)
    return fails


def fixture_pages(root):
    import sprint95b_fixture as f
    # SPRINT 9.9.2: the pages the browser holds to 9.5's render, with 9.9.2's changes undone (_cut_992; the notice is taken out
    # in the browser, as for 9.9.1)
    for name, html in f.pages(None).items():
        with open(os.path.join(root, f"home-board-{name}.html"), "w", encoding="utf-8") as fh:
            fh.write(_cut_992(html))


def browser(root):
    """The browser half (scripts/sprint95b_browser.mjs): the wrapper's rendered width, the first screen at 1440, the 375 render against
    9.5's, CLS on the home, every page type at 1280 and 1440. Returns (failures, output)."""
    node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
    if not node:
        return ["no node on this machine: the browser half did not run"], ""
    fixture_pages(root)
    r = subprocess.run([node, os.path.join(HERE, "scripts", "sprint95b_browser.mjs"), root], capture_output=True, text=True, timeout=5400)
    out = r.stdout + r.stderr
    fails = [ln[5:].strip() for ln in out.splitlines() if ln.startswith("FAIL ")]
    if r.returncode and not fails:
        fails = ["the browser run exited %d: %s" % (r.returncode, out[-300:])]
    return fails, out


def main():
    args = sys.argv[1:]
    fails = unit()
    if "--tree" in args:
        root = args[args.index("--tree") + 1]
        fails += tree(root)
        bf, out = browser(root)
        print(out)
        fails += ["browser: " + f for f in bf]
    print(f"\nSPRINT 9.5b: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
