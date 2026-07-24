#!/usr/bin/env python3
"""
og_render.py: render a per-article Open Graph card (1200x630 PNG) from a headline, in PURE
Python (Pillow). No Chromium, no LLM, no image model, and nothing committed to the repo:
site_build.py calls render_card() at BUILD time (which runs on Netlify), writing each card
straight into the publish output. The brand fonts under site/assets/fonts/ are the only
committed asset (a one-time static dependency, not per-article growth).

Reproduces the Crypto Cronkite share card: newsprint paper ground, a red masthead rule,
the mono wordmark, a red kicker, a serif headline sized to its length, and the
"Never financial advice" foot.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "site", "assets", "fonts")
PAPER = (251, 250, 246)   # #FBFAF6
INK = (23, 24, 28)        # #17181C
MUTED = (92, 97, 107)     # #5C616B
LINE = (230, 226, 216)    # #E6E2D8
RULE = (180, 35, 24)      # #B42318
W, H = 1200, 630
PAD_X, PAD_TOP = 72, 64

_MONO_SB = os.path.join(FONTS, "IBMPlexMono-SemiBold.ttf")
_MONO_MD = os.path.join(FONTS, "IBMPlexMono-Medium.ttf")
_SERIF = os.path.join(FONTS, "Newsreader.ttf")


def _serif(size, weight=600):
    f = ImageFont.truetype(_SERIF, size)
    try:
        f.set_variation_by_axes([weight])  # Newsreader is a variable font
    except Exception:
        pass
    return f


def _tracked(draw, xy, text, font, fill, tracking):
    """Draw text with letter-spacing (Pillow has none natively). Returns the end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x - tracking


def _tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(ch, font=font) + tracking for ch in text) - tracking


def _wrap(draw, text, font, max_w, max_lines):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and (len(" ".join(lines)) < len(text)):
        while lines and draw.textlength(lines[-1] + "...", font=font) > max_w:
            lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
        lines[-1] = lines[-1].rstrip(",. ") + "..."
    return lines


def _headline_size(n):
    return 74 if n <= 42 else 62 if n <= 72 else 52 if n <= 104 else 44


def render_card(headline, kicker, out_path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    content_w = W - 2 * PAD_X

    # ---- masthead: wordmark + edition, red rule ----
    brand_f = ImageFont.truetype(_MONO_SB, 26)
    ed_f = ImageFont.truetype(_MONO_MD, 15)
    y = PAD_TOP
    x = _tracked(d, (PAD_X, y), "THE CRYPTO ", brand_f, INK, 3.6)
    x = _tracked(d, (x, y), "·", brand_f, RULE, 3.6)
    _tracked(d, (x, y), " CRONKITE", brand_f, INK, 3.6)
    ed = "CRYPTO, CHECKED"
    _tracked(d, (W - PAD_X - _tracked_width(d, ed, ed_f, 1.5), y + 6), ed, ed_f, MUTED, 1.5)
    rule_y = PAD_TOP + 44
    d.rectangle([PAD_X, rule_y, W - PAD_X, rule_y + 3], fill=RULE)

    # ---- kicker ----
    kick_f = ImageFont.truetype(_MONO_SB, 19)
    ky = rule_y + 30
    _tracked(d, (PAD_X, ky), (kicker or "Crypto News").upper(), kick_f, RULE, 3.0)

    # ---- headline (serif, sized to length, wrapped, max 4 lines) ----
    size = _headline_size(len(headline))
    hf = _serif(size, 600)
    lines = _wrap(d, headline, hf, content_w, 4)
    lh = int(size * 1.08)
    hy = ky + 40
    for ln in lines:
        d.text((PAD_X, hy), ln, font=hf, fill=INK)
        hy += lh

    # ---- foot: line, site left, NFA right ----
    foot_f = ImageFont.truetype(_MONO_MD, 16)
    fy = H - PAD_TOP - 34
    d.rectangle([PAD_X, fy, W - PAD_X, fy + 1], fill=LINE)
    _tracked(d, (PAD_X, fy + 20), "gocheckmycrypto.com", foot_f, MUTED, 0.8)
    nfa = "Never financial advice"
    nfa_sb = ImageFont.truetype(_MONO_SB, 16)
    _tracked(d, (W - PAD_X - _tracked_width(d, nfa, nfa_sb, 0.8), fy + 20), nfa, nfa_sb, RULE, 0.8)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--headline", required=True)
    ap.add_argument("--kicker", default="Crypto News")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print("wrote", render_card(a.headline, a.kicker, a.out))
