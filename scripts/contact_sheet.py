#!/usr/bin/env python3
"""
contact_sheet.py <before-dir> <after-dir> <out.jpg> <slug> <title>

Program 7 Sprint 7.1: one page group's contact sheet for Jack, before beside after, at 375
and 1440, light and dark, from page_shots.mjs output (<slug>-<width>-<theme>.png). Each shot
is the top of the page (the first 1,800 px at 375, the first 1,100 px at 1440), labelled.
Pillow only; no network.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

BG, INK = (245, 246, 248), (15, 27, 45)


def _font(size):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _shot(d, slug, w, theme, crop_h, scale_w):
    p = os.path.join(d, f"{slug}-{w}-{theme}.png")
    if not os.path.exists(p):
        im = Image.new("RGB", (scale_w, int(crop_h * scale_w / w)), (220, 220, 220))
        ImageDraw.Draw(im).text((10, 10), "missing", fill=INK, font=_font(16))
        return im
    im = Image.open(p).convert("RGB")
    im = im.crop((0, 0, im.width, min(im.height, crop_h)))
    return im.resize((scale_w, int(im.height * scale_w / im.width)), Image.LANCZOS)


def main(before, after, out, slug, title):
    pad, lab = 16, 26
    f = _font(15)
    phone = [(theme, d, tag) for theme in ("light", "dark")
             for d, tag in ((before, "before"), (after, "after"))]
    tiles1 = [(_shot(d, slug, 375, th, 1800, 300), f"375 {th}, {tag}") for th, d, tag in phone]
    tiles2 = [(_shot(d, slug, 1440, th, 1100, 560), f"1440 {th}, {tag}") for th, d, tag in phone]
    w1 = sum(t.width for t, _ in tiles1) + pad * 5
    w2 = 2 * 560 + pad * 3
    W = max(w1, w2)
    h1 = max(t.height for t, _ in tiles1) + lab
    h2a = max(t.height for t, _ in tiles2[:2]) + lab
    h2b = max(t.height for t, _ in tiles2[2:]) + lab
    H = 50 + h1 + pad + h2a + pad + h2b + pad
    sheet = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 14), title, fill=INK, font=_font(22))
    x, y = pad, 50
    for t, cap in tiles1:
        dr.text((x, y), cap, fill=INK, font=f)
        sheet.paste(t, (x, y + lab))
        x += t.width + pad
    y += h1 + pad
    for row in (tiles2[:2], tiles2[2:]):
        x = pad
        for t, cap in row:
            dr.text((x, y), cap, fill=INK, font=f)
            sheet.paste(t, (x, y + lab))
            x += t.width + pad
        y += max(t.height for t, _ in row) + lab + pad
    sheet.save(out, "JPEG", quality=82, optimize=True)
    print(f"wrote {out} {sheet.size}")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
