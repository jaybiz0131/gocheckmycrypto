#!/usr/bin/env python3
"""
share_cards.py: the share loop, re-aimed (Program 9, Sprint 9.6; AUDIT.md section 3.6, row 9.6, with Program 8.3's
share loop as its shape).

One square card (1080 by 1080) per graded verdict, one per day, built on the VERDICT card (verdict.py) and never on the
Brief. A card is made of the verdict record's own words and the evidence record's own facts, and of nothing else:

  - the verdict's own grade, its window named, its named event or events (the section form of the verdict's sentences,
    which names an event by its subject and leaves its time, source and figure to the rows under it);
  - a row per named event: its time and its source as the verdict page prints them, and the one figure the page prints
    for it (the hour after it), with the price source named once;
  - "because" only on Confirmed; no grade word but the card's own; no AI mention, no personal name, no dash; and no
    figure the verdict page does not print. A card that breaks one of these is not drawn (fail closed): there is no
    card, and the page keeps the site's card.

COLOR TRUTH (Jack, October 12, 2026): a figure is colored by its own sign and carries its own arrow; the grade mark is
neutral ink and is never up or down colored; nothing else on the card is drawn in the up or down color.

A verdict at the next read, and a verdict withheld at the cap, make no card. A day with no graded verdict gets a day
card that says so and invents nothing.

The image is drawn in pure Python (Pillow), deterministically, from the fonts under site/assets/fonts, by the existing
renderer's helpers (scripts/og_render.py). It is drawn at build time into PUBLISH/og/why/<slug>.png; nothing per-card
is committed. The queue entry (queue_entry) takes the publicist's file shape; nothing posts and nothing needs a
credential (share_queue.py writes the files).
"""
import datetime as _dt
import html as _html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import og_render  # noqa: E402  (the existing renderer: ground, wordmark, tracking, fonts)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ORIGIN = "https://" + og_render.DOMAIN
SIZE = 1080
W = H = SIZE
PAD = 72
IMG_DIR = "/og/why"
FOOT_NOTE = "Not financial advice."

# the colors: the dark theme's own tokens (site/assets/system.css, --up and --down under dark), the card ground's
# neutrals, and nothing else. A grade mark is drawn in NEUTRALS only. The family's red accent is left off this card on
# purpose: it sits within a shade of the down color, and on a verdict card the only red or green is a figure's own.
UP = (0x4A, 0xDE, 0x80)
DOWN = (0xFF, 0x6B, 0x5E)
INK_ON_DARK = og_render.PAPER           # (251, 250, 246)
MUTED = (178, 183, 192)
MUTED_2 = (132, 137, 147)
RULE_LINE = (52, 55, 62)
NEUTRALS = {INK_ON_DARK, MUTED, MUTED_2, RULE_LINE, og_render.GROUND}

GRADE_RX = re.compile(r"\b(confirmed|likely|disputed|unclear)\b", re.I)
BECAUSE_RX = re.compile(r"\bbecause\b", re.I)
DASH_RX = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
AI_RX = re.compile(r"\bA\.?I\b|artificial|machine[- ]learn|language model|\bLLM\b|\bGPT|\bClaude\b|\bAnthropic\b|\bHaiku\b|"
                   r"\bSonnet\b|\bOpenAI\b|\bchatbot\b|algorithm|\bautomated\b|\bgenerated\b", re.I)
PERSON_RX = re.compile(r"(?<!Crypto )\bCronkite\b|\bWalter\b|\bJack\b|\bBerno\b|\bfounder\b|\beditor-in-chief\b", re.I)
FIG_RX = re.compile(r"\b\d{1,2}:\d{2} [AP]M\b|\d[\d,]*\.?\d*\s?%|\$[\d,]+(?:\.\d+)?(?:[KMB]| million| billion)?|\d[\d,.]*\s?bp\b")

MAX_EVENTS = 3
FONT_FILES = ("IBMPlexMono-SemiBold.ttf", "IBMPlexMono-Medium.ttf", "Newsreader.ttf")


class CardError(Exception):
    """A card that cannot be drawn truthfully: a stand-in font, text that will not fit. The build leaves the card out."""


def _vd():
    import verdict
    return verdict


def _we():
    import why_evidence
    return why_evidence


def _e(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def visible(h):
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _long_date(day):
    d = _dt.date.fromisoformat(day)
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def et_today(now=None):
    from zoneinfo import ZoneInfo
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return now.astimezone(ZoneInfo("America/New_York")).date()


class Ctx:
    """What a page builder is handed: where the square images go (None draws nothing and tags nothing), the ET date
    'today' for the finality of a day, and the list every spec offered is kept in."""

    def __init__(self, directory=None, today=None, specs=None):
        self.directory = directory
        self.today = today or et_today()
        self.specs = specs if specs is not None else []

    def final(self, day, slots):
        """A day's cards are final once its evening record exists or the day is over."""
        return "evening" in set(slots) or day < self.today.isoformat()


def image_path(slug):
    return f"{IMG_DIR}/{slug}.png"


def image_url(slug):
    return ORIGIN + image_path(slug)


# ---- the spec of a verdict card ---------------------------------------------------------------------------------------

def verdict_spec(vrec, sym, ev, slug, day, corrections=None):
    """The card for one graded verdict, or None: a verdict at the next read, one withheld at the cap, Ether moving
    with Bitcoin, a flat day, a verdict with a standing correction, or a card that fails its own checks makes none."""
    vd, we = _vd(), _we()
    v = ((vrec or {}).get("coins") or {}).get(sym)
    if not v or v.get("kind") != "graded" or v.get("grade") not in vd.GRADES:
        return None
    if v.get("corrections"):
        return None                                 # a verdict with a standing correction is not passed around
    wend = vd._parse(((vrec or {}).get("window") or {}).get("end_utc"))
    if wend is None:
        return None
    w1 = int(wend.timestamp())
    name = v.get("name") or sym
    grade = v["grade"]
    sec_html = we.section_html(ev, sym, live=False, corrections=corrections, graded=grade, marks=vd.marks(vrec, sym)) if ev else ""
    with_section = bool(sec_html)
    sents = vd.text_sec(v) if with_section else None
    use_sec = sents is not None
    if not use_sec:
        sents = list(v.get("text") or v.get("line") or [])
    sents = [s for s in sents if s and s.strip()]
    if not sents:
        return None
    ww = v.get("window_words") or vd.WINDOW_WORDS["rolling_24h"]
    window = f"{_cap(ww)}, to {we.clock(w1)}"
    events, figures, price = [], [], ""
    coin = ((ev or {}).get("coins") or {}).get(sym) or {}
    if use_sec:
        by_id = {t["id"]: t for t in coin.get("tests") or []}
        cands = {c["id"]: c for c in (ev or {}).get("candidates") or []}
        src = (coin.get("series") or {}).get("source")
        price = f"Prices: {src}." if src else ""
        for ref in v.get("refs") or []:
            c = cands.get(ref.get("id"))
            if not c:
                continue
            events.append(_event_row(ref, c, by_id.get(c["id"]), w1, price, coin))
        for row in events:
            if row["figure"]:
                figures.append(row["figure"])
        if not figures:
            price = ""
    shown = events[:MAX_EVENTS]
    spec = {"kind": "verdict", "slug": slug, "day": day, "key": slug[len(day) + 1:], "sym": sym,
            "heading": f"Why {name} moved", "date": _long_date(day), "window": window, "grade": grade,
            "chip": f"Checked: {grade}", "definition": vd.DEFINITIONS[grade], "sentences": sents,
            "events": shown, "more": len(events) - len(shown), "figures": [r["figure"] for r in shown if r["figure"]],
            "price": price if any(r["figure"] for r in shown) else "",
            "page": f"/why/{slug}", "image": image_path(slug), "foot": FOOT_NOTE, "domain": og_render.DOMAIN}
    spec["words"] = _words(spec)
    spec["post_lines"] = [spec["heading"], spec["date"], spec["chip"]] + list(sents)
    page = visible(vd.card_html(vrec, sym, where="page", live=False, corrections=corrections, link=False, with_section=with_section)
                   + sec_html)
    why = _problem(spec, page)
    if why:
        print(f"::warning::share card: no card for {slug}: {why}")
        return None
    spec["alt"] = _alt(spec)
    return spec


def _event_row(ref, c, test, w1, price, coin):
    """One named event: its subject, the time and the source the page prints for it, and the one figure the page prints
    (the hour after it, or the rest of the window), colored by its own sign."""
    we = _we()
    facts = []
    ev_t = we._parse_utc(c.get("event_utc"))
    if ev_t is not None:
        facts.append(f'Event {we.day_clock(int(ev_t.timestamp()), w1)}' + (" (scheduled)" if c.get("scheduled") else "")
                     + f', {c.get("event_basis") or ""}'.rstrip(", "))
    elif c.get("event_day"):
        facts.append(f'Event day {c["event_day"]}, {c.get("event_basis") or ""}'.rstrip(", "))
    rp = we._parse_utc(c.get("report_utc"))
    if rp is not None:
        k = int(c.get("source_count") or 0)
        facts.append(f'First reported {we.day_clock(int(rp.timestamp()), w1)}' + (f', {k} source{"" if k == 1 else "s"}' if k else ""))
    if c.get("primary"):
        facts.append("Primary source")
    outlets = []
    for l in (c.get("report_links") or c.get("links") or []):
        o = l.get("outlet")
        if o and o not in outlets:
            outlets.append(o)
    if outlets:
        facts.append(", ".join(outlets[:3]))
    fig = None
    r = (test or {}).get("result") or {}
    if r.get("share_pct") is not None and r.get("after_pct") is not None and r["after_pct"]:
        a = r["after_pct"]
        fig = {"label": "The rest of the window" if r.get("share_partial") else "The next 60 minutes", "value": a,
               "text": f"{abs(a):.2f}%", "source": price}
    return {"id": c.get("id"), "title": _cap(ref.get("text") or ""), "facts": facts, "figure": fig}


def fig_text(f):
    """The figure as printed: its own arrow, then its magnitude."""
    return ("▲ " if f["value"] > 0 else "▼ " if f["value"] < 0 else "") + f["text"]


def _words(spec):
    """Every string the card prints, in reading order. The queue's post line and the tests read this list."""
    w = []
    if spec["kind"] == "verdict":
        w += [spec["heading"], spec["date"], spec["window"], spec["chip"], spec["definition"]] + list(spec["sentences"])
        for e in spec["events"]:
            w.append(e["title"])
            w += list(e["facts"])
            if e["figure"]:
                w.append(f'{e["figure"]["label"]}: {fig_text(e["figure"])}')
        if spec["more"]:
            w.append(f'{spec["more"]} more on the page.')
        if spec["price"]:
            w.append(spec["price"])
    else:
        w += [spec["heading"], spec["date"]]
        for g in spec["graded"]:
            w += [g["name"], g["chip"], g["sentence"]]
        w += list(spec["lines"])
    w += [spec["domain"], spec["foot"]]
    return w


def _problem(spec, page):
    """'' when the card passes every check, else the first reason it does not: the checks the board names."""
    txt = " ".join(spec["words"])
    seen = {m.lower() for m in GRADE_RX.findall(txt)}
    own = {g.lower() for g in ([spec["grade"]] if spec["kind"] == "verdict" else [x["grade"] for x in spec["graded"]])}
    if not seen <= own:
        return f"a grade word that is not the card's own ({sorted(seen - own)})"
    if BECAUSE_RX.search(txt) and not (spec["kind"] == "verdict" and spec["grade"] == "Confirmed"):
        return "'because' on a card that is not Confirmed"
    if AI_RX.search(txt):
        return "an AI mention"
    if PERSON_RX.search(txt):
        return "a personal name"
    if DASH_RX.search(txt):
        return "a dash"
    miss = sorted(set(FIG_RX.findall(txt)) - set(FIG_RX.findall(page)))
    if miss:
        return f"a figure the verdict page does not print ({miss})"
    return ""


def _alt(spec):
    if spec["kind"] == "verdict":
        a = f'{spec["heading"]}, {spec["date"]}. {spec["chip"]}. {spec["sentences"][0]}'
    else:
        a = f'{spec["heading"]}, {spec["date"]}. ' + (" ".join(f'{g["name"]}: {g["chip"]}.' for g in spec["graded"])
                                                      or spec["lines"][0])
    return a[:400]


def shell_kwargs(spec):
    """The keyword arguments site_build.shell takes for the page this card belongs to."""
    return {"og_image": ORIGIN + spec["image"], "og_image_size": (SIZE, SIZE), "og_image_alt": spec["alt"],
            "twitter_card": "summary"}


# ---- the day card ------------------------------------------------------------------------------------------------------

def day_specs(vdir=None, wdir=None, tdir=None, today=None):
    """[spec] for every day that has a verdict record, oldest first. The day's graded verdicts (the newest slot's, as the
    verdict page carries), or the card that says no verdict was graded. Bitcoin and Ether only."""
    vd = _vd()
    today = today or et_today()
    import json
    by_day = {}
    for n in vd._names(vdir):
        r = vd.load(n[:10], n[11:-5], vdir)
        if r:
            by_day.setdefault(n[:10], []).append(r)
    tdd = tdir or os.path.join(HERE, "site", "data", "today")
    out = []
    for day, recs in sorted(by_day.items()):
        recs.sort(key=lambda r: r.get("slot") == "evening", reverse=True)
        graded, lines = [], []
        for sym in ("BTC", "ETH"):
            hit = next((r for r in recs if ((r.get("coins") or {}).get(sym) or {}).get("grade")
                        and ((r.get("coins") or {}).get(sym) or {}).get("kind") == "graded"), None)
            if hit:
                v = hit["coins"][sym]
                if v.get("corrections"):
                    continue
                ev = _we().load(day, hit.get("slot"), wdir)
                sents = (vd.text_sec(v) if ev and _we().section_html(ev, sym, live=False) else None) or list(v.get("text") or v.get("line") or [])
                if not sents:
                    continue
                graded.append({"name": v.get("name") or sym, "grade": v["grade"], "chip": f'Checked: {v["grade"]}',
                               "sentence": sents[0], "page": f"/why/{vd.slug(day, sym)}"})
                continue
            first = next((((r.get("coins") or {}).get(sym)) for r in recs if (r.get("coins") or {}).get(sym)), None) or {}
            if first.get("kind") == "with_btc":
                lines.append((first.get("line") or ["Ether moved with Bitcoin."])[0])
            elif first.get("kind") == "flat":
                lines.append(f'{first.get("name") or sym} was flat, so nothing was graded.')
        if not graded:
            lines = ["No verdict was graded for Bitcoin or Ether."] + lines
        has_today = any(os.path.exists(os.path.join(tdd, f"{day}-{sl}.json")) for sl in ("morning", "evening"))
        page = f"/today/{day}" if has_today else (graded[0]["page"] if graded else None)
        if page is None:
            continue
        slug = f"day-{day}"
        spec = {"kind": "day", "slug": slug, "day": day, "key": "day", "heading": "The day's verdicts", "date": _long_date(day),
                "graded": graded, "lines": lines, "figures": [], "events": [], "page": page, "image": image_path(slug),
                "foot": FOOT_NOTE, "domain": og_render.DOMAIN, "final": "evening" in {r.get("slot") for r in recs} or day < today.isoformat()}
        spec["words"] = _words(spec)
        spec["post_lines"] = [spec["heading"], spec["date"]] + [x for g in graded for x in (g["name"], g["chip"], g["sentence"])] + list(lines)
        # the day card prints no figure; its grades and sentences are the /why/ pages' own, so only the checks on words apply
        why = _problem(spec, " ".join(spec["words"]))
        if why:
            print(f"::warning::share card: no day card for {day}: {why}")
            continue
        spec["alt"] = _alt(spec)
        out.append(spec)
    return out


# ---- attaching a card to a page builder -------------------------------------------------------------------------------

def for_page(ctx, vrec, sym, ev, slug, day, slots, corrections=None):
    """What a verdict or movers page builder calls: the shell keyword arguments for the page's own square image, {} when
    the build draws none (no context, no directory, no card, or an image that could not be drawn). The spec is kept in
    the context either way, for the queue."""
    if ctx is None:
        return {}
    try:
        spec = verdict_spec(vrec, sym, ev, slug, day, corrections)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::share card: {slug} was not specified ({type(e).__name__}: {e})")
        return {}
    if not spec:
        return {}
    spec["final"] = ctx.final(day, slots)
    ctx.specs.append(spec)
    if not ctx.directory:
        return {}
    if not draw(spec, ctx.directory):
        return {}
    return shell_kwargs(spec)


def draw(spec, directory):
    """Draw one spec to <directory>/<slug>.png. False (with a warning) when it cannot be drawn."""
    try:
        render(spec, os.path.join(directory, spec["slug"] + ".png"))
        spec["rendered"] = True
        return True
    except Exception as e:                                       # noqa: BLE001
        spec["rendered"] = False
        print(f"::warning::share card: {spec['slug']} was not drawn ({type(e).__name__}: {e})")
        return False


# ---- the queue entry ---------------------------------------------------------------------------------------------------

def post_text(spec):
    """The suggested post: the card's own words and the page's address, in lines."""
    return "\n".join(list(spec["post_lines"]) + ["", ORIGIN + spec["page"], "", spec["foot"]])


def queue_entry(spec):
    """(file name, text) in the publicist's queue shape (publicist.file_draft), or None when the post fails the
    publicist's own gates. Nothing here posts anything."""
    import publicist
    url = ORIGIN + spec["page"]
    post = post_text(spec)
    ok, rep = publicist.run_gates(post, url)
    if not ok:
        print("::warning::share queue: " + spec["slug"] + " failed the publicist's gates: " + "; ".join(r for r in rep if r.startswith("FAIL")))
        return None
    name = f'{spec["day"]}-why-{spec["key"]}.md'
    text = (f'# LinkedIn draft: {spec["heading"]}, {spec["date"]}\n\n'
            f'Story: {url}\n\n'
            f'Image: {ORIGIN}{spec["image"]}\n'
            f'Image path: {spec["image"]}\n'
            f'(The square card is drawn by the build; save it from the Image address once the build that carries this '
            f'verdict has deployed.)\n\n'
            f'YOUR FRAMING (add 1-2 lines of your own take above the draft before posting):\n\n'
            f'> _______________________________________________\n\n'
            f'---- READY-TO-PASTE DRAFT (passed all {len(rep)} gates) ----\n\n'
            f'{post}\n')
    return name, text


# ---- the drawing -------------------------------------------------------------------------------------------------------

def fonts_ok():
    """U-10: the card is drawn with the shipped faces or not at all. A missing or stand-in file raises."""
    for fn in FONT_FILES:
        p = os.path.join(og_render.FONTS, fn)
        if not os.path.isfile(p) or os.path.getsize(p) < 50_000:
            raise CardError(f"the shipped face {fn} is not at {og_render.FONTS}; a stand-in font is never drawn")
    return True


def _mono(weight, size):
    return ImageFont.truetype(os.path.join(og_render.FONTS, "IBMPlexMono-SemiBold.ttf" if weight >= 600 else "IBMPlexMono-Medium.ttf"), size)


def _serif(size, weight=600):
    f = ImageFont.truetype(os.path.join(og_render.FONTS, "Newsreader.ttf"), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:                                            # noqa: BLE001
        pass
    return f


_M = None


def _meas():
    global _M
    if _M is None:
        _M = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    return _M


def _wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if _meas().textlength(trial, font=font) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def _wrap_units(units, font, width, sep=" · "):
    """Lines of whole facts joined by a middle dot; a fact is never split unless it alone is wider than the line."""
    lines, cur = [], ""
    for u in units:
        trial = (cur + sep + u) if cur else u
        if _meas().textlength(trial, font=font) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        if _meas().textlength(u, font=font) <= width:
            cur = u
        else:
            parts = _wrap(u, font, width)
            lines += parts[:-1]
            cur = parts[-1]
    if cur:
        lines.append(cur)
    return lines


class _Lay:
    def __init__(self):
        self.ops, self.y = [], 0

    def rect(self, x0, y0, x1, y1, fill, role="rule"):
        self.ops.append({"kind": "rect", "x0": x0, "y0": y0, "x1": x1, "y1": y1, "fill": fill, "role": role})

    def text(self, x, y, s, font, fill, role="text", tracking=0.0, size=0):
        w = og_render._tracked_width(_meas(), s, font, tracking) if tracking else _meas().textlength(s, font=font)
        self.ops.append({"kind": "text", "x0": x, "y0": y, "x1": x + w, "y1": y + int(size * 1.3), "text": s, "font": font,
                         "fill": fill, "role": role, "tracking": tracking})
        return w


def layout(spec):
    """The card as drawing operations, every text with its box. Raises CardError when the words do not fit the square."""
    fonts_ok()
    foot_top = H - 96
    limit = foot_top - 28
    last = None
    for body in (40, 37, 34, 31, 28):
        try:
            ops, y = _layout(spec, body, foot_top)
        except CardError as e:
            last = e
            continue
        if y <= limit:
            return ops
        last = CardError(f"the card's text runs to {y}, past {limit}, at body size {body}")
    raise last or CardError("the card does not fit")


def _layout(spec, body, foot_top):
    L = _Lay()
    L.rect(0, 0, W, 9, MUTED_2, "rule")
    L.ops.append({"kind": "wordmark", "x0": PAD, "y0": 36, "x1": PAD + 330, "y1": 36 + 52, "size": 40})
    kick = _mono(600, 18)
    kw = og_render._tracked_width(_meas(), "WHY IT MOVED", kick, 3.0)
    L.text(W - PAD - kw, 54, "WHY IT MOVED", kick, MUTED, "kicker", 3.0, 18)
    L.rect(PAD, 104, W - PAD, 107, MUTED_2, "rule")
    y = 138
    L.text(PAD, y, spec["date"], _mono(500, 24), MUTED, "date", 0, 24)
    y += 44
    hsize = 84
    while True:
        hf = _serif(hsize, 600)
        lines = _wrap(spec["heading"], hf, W - 2 * PAD)
        if len(lines) <= 2 or hsize <= 56:
            break
        hsize -= 8
    for ln in lines:
        L.text(PAD, y, ln, hf, INK_ON_DARK, "heading", 0, hsize)
        y += int(hsize * 1.08)
    y += 6
    if spec["kind"] == "verdict":
        L.text(PAD, y, spec["window"], _mono(500, 22), MUTED, "window", 0, 22)
        y += 46
        y = _chip(L, y, spec["chip"], spec["grade"])
        y += 18
        for ln in _wrap(spec["definition"], _serif(23, 400), W - 2 * PAD)[:3]:
            L.text(PAD, y, ln, _serif(23, 400), MUTED, "definition", 0, 23)
            y += 30
        y += 20
        sf = _serif(body, 500)
        for s in spec["sentences"]:
            for ln in _wrap(s, sf, W - 2 * PAD):
                L.text(PAD, y, ln, sf, INK_ON_DARK, "sentence", 0, body)
                y += int(body * 1.22)
            y += 8
        y += 6
        for e in spec["events"]:
            y = _event(L, y, e)
        if spec["more"]:
            L.text(PAD, y, f'{spec["more"]} more on the page.', _mono(500, 19), MUTED_2, "more", 0, 19)
            y += 30
        if spec["price"]:
            L.text(PAD, y + 4, spec["price"], _mono(500, 18), MUTED_2, "price", 0, 18)
            y += 34
    else:
        y += 8
        for g in spec["graded"]:
            L.text(PAD, y, g["name"], _serif(44, 600), INK_ON_DARK, "name", 0, 44)
            y += 56
            y = _chip(L, y, g["chip"], g["grade"])
            y += 14
            sf = _serif(body, 500)
            for ln in _wrap(g["sentence"], sf, W - 2 * PAD):
                L.text(PAD, y, ln, sf, INK_ON_DARK, "sentence", 0, body)
                y += int(body * 1.22)
            y += 26
        sf = _serif(body + 4, 500)
        for s in spec["lines"]:
            for ln in _wrap(s, sf, W - 2 * PAD):
                L.text(PAD, y, ln, sf, INK_ON_DARK, "sentence", 0, body + 4)
                y += int((body + 4) * 1.22)
            y += 10
    L.rect(PAD, foot_top, W - PAD, foot_top + 1, RULE_LINE, "rule")
    L.text(PAD, foot_top + 24, spec["domain"], _mono(500, 18), MUTED_2, "foot", 0.8, 18)
    nf = _mono(600, 18)
    nw = og_render._tracked_width(_meas(), spec["foot"], nf, 0.8)
    L.text(W - PAD - nw, foot_top + 24, spec["foot"], nf, MUTED, "foot", 0.8, 18)
    return L.ops, y


def _chip(L, y, label, grade):
    """The grade mark: a neutral outlined chip with a dot (Confirmed full, Likely half, Disputed hollow, Unclear none), the
    way the site's own chip is told apart without color. Never up or down colored."""
    f = _mono(600, 26)
    tw = _meas().textlength(label, font=f)
    x0, h = PAD, 54
    mark = grade in ("Confirmed", "Likely", "Disputed")
    inner = 24 + (26 if mark else 0)
    L.ops.append({"kind": "chip", "x0": x0, "y0": y, "x1": x0 + inner + tw + 24, "y1": y + h, "role": "chip", "fill": INK_ON_DARK})
    if mark:
        L.ops.append({"kind": "dot", "grade": grade, "cx": x0 + 24 + 9, "cy": y + h // 2, "r": 9, "x0": x0 + 24, "y0": y + h // 2 - 9,
                      "x1": x0 + 42, "y1": y + h // 2 + 9, "role": "chip-mark", "fill": INK_ON_DARK})
    L.text(x0 + inner, y + 11, label, f, INK_ON_DARK, "chip-text", 0, 26)
    L.ops[-1]["role"] = "chip"
    return y + h


def _event(L, y, e):
    tf = _serif(31, 600)
    L.text(PAD, y, e["title"], tf, INK_ON_DARK, "event", 0, 31)
    y += 42
    ff = _mono(500, 19)
    for ln in _wrap_units(e["facts"], ff, W - 2 * PAD)[:2]:
        L.text(PAD, y, ln, ff, MUTED, "facts", 0, 19)
        y += 27
    if e["figure"]:
        f = e["figure"]
        lab = f'{f["label"]}:'
        w = L.text(PAD, y + 2, lab, ff, MUTED, "figure-label", 0, 19)
        col = UP if f["value"] > 0 else DOWN if f["value"] < 0 else INK_ON_DARK
        t = fig_text(f)
        ft = _mono(600, 30)
        L.text(PAD + w + 16, y - 3, t, ft, col, "figure", 0, 30)
        L.ops[-1].update(sign=(f["value"] > 0) - (f["value"] < 0))
        y += 40
    return y + 20


def render(spec, path):
    """Draw the card to a PNG of 1080 by 1080 at `path`. Deterministic: the same spec draws the same bytes."""
    ops = layout(spec)
    img = Image.new("RGBA", (W, H), og_render.GROUND + (255,))
    mark = Image.new("RGBA", (og_render.W, og_render.H), og_render.GROUND + (255,))
    og_render._data_mark(mark, 0.5)
    img.paste(mark.crop((420, 0, og_render.W, og_render.H)), (W - (og_render.W - 420), H - og_render.H - 100))
    img = og_render._halftone(img)
    d = ImageDraw.Draw(img)
    for o in ops:
        k = o["kind"]
        if k == "rect":
            d.rectangle([o["x0"], o["y0"], o["x1"], o["y1"]], fill=o["fill"])
        elif k == "wordmark":
            end = og_render._wordmark_dark(img, o["x0"], o["y0"], o["size"], MUTED)
            d = ImageDraw.Draw(img)
            o["x1"] = end
        elif k == "chip":
            d.rounded_rectangle([o["x0"], o["y0"], o["x1"], o["y1"]], radius=27, outline=o["fill"], width=2)
        elif k == "dot":
            cx, cy, r = o["cx"], o["cy"], o["r"]
            box = [cx - r, cy - r, cx + r, cy + r]
            if o["grade"] == "Confirmed":
                d.ellipse(box, fill=o["fill"])
            elif o["grade"] == "Likely":
                d.ellipse(box, outline=o["fill"], width=2)
                d.pieslice(box, 90, 270, fill=o["fill"])
            else:
                d.ellipse(box, outline=o["fill"], width=2)
        elif k == "text" and o.get("role") == "figure":
            # IBM Plex Mono has no arrow glyph, so the figure's own arrow is drawn as a triangle in the figure's color
            txt = o["text"]
            x = o["x0"]
            if txt[:1] in ("▲", "▼"):
                sz = o["font"].size
                top, bot = o["y0"] + int(sz * 0.30), o["y0"] + int(sz * 0.88)
                mid = x + int(sz * 0.30)
                tri = ([(x, bot), (x + int(sz * 0.6), bot), (mid, top)] if txt[0] == "▲"
                       else [(x, top), (x + int(sz * 0.6), top), (mid, bot)])
                d.polygon(tri, fill=o["fill"])
                x += int(sz * 0.6) + int(sz * 0.4)
                txt = txt[2:]
            d.text((x, o["y0"]), txt, font=o["font"], fill=o["fill"])
        elif k == "text":
            if o.get("tracking"):
                og_render._tracked(d, (o["x0"], o["y0"]), o["text"], o["font"], o["fill"], o["tracking"])
            else:
                d.text((o["x0"], o["y0"]), o["text"], font=o["font"], fill=o["fill"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out = img.convert("RGB").quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE)
    out.save(path, "PNG", optimize=True)
    return path
