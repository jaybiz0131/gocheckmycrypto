#!/usr/bin/env python3
"""
sprint65_sheets.py <proofdir> <outdir>

Sprint 6.5 contact sheets for Jack, from sprint65_proof.mjs and chart_closeups.mjs output: before beside
after, at 375, light and dark, every picture drawn from recorded data. Writes three JPEGs:
  contact-btc-averages.jpg   BTC 1Y and 1M close-ups (where each average starts, the caption)
  contact-top100-first.jpg   the Top 100's first screen
  contact-top100-rows.jpg    the rows with the longest price and the longest names
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BG, INK, MUT = (245, 246, 248), (15, 27, 45), (96, 108, 125)


def font(sz, bold=False):
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")
    return ImageFont.truetype(f, sz) if os.path.exists(f) else ImageFont.load_default()


def load(p, w=375):
    im = Image.open(p).convert("RGB")
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def sheet(cells, cols, labels_top, labels_left, title, out, pad=14, lw=96):
    # cells: list of rows, each a list of images; labels_top: column titles; labels_left: row titles
    cw = max(i.width for r in cells for i in r)
    rh = [max(i.height for i in r) for r in cells]
    W = lw + cols * (cw + pad) + pad
    H = 70 + 30 + sum(rh) + pad * (len(cells) + 1)
    s = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(s)
    d.text((pad, 14), title, font=font(18, True), fill=INK)
    d.text((pad, 42), "375 px wide, light and dark, recorded data only", font=font(12), fill=MUT)
    y = 100
    for c, t in enumerate(labels_top):
        d.text((lw + pad + c * (cw + pad), 76), t, font=font(13, True), fill=INK)
    for r, row in enumerate(cells):
        d.text((pad, y + 4), labels_left[r], font=font(12, True), fill=INK)
        for c, im in enumerate(row):
            s.paste(im, (lw + pad + c * (cw + pad), y))
        y += rh[r] + pad
    s.save(out, quality=88)
    print("wrote", out, s.size)


def main(proof, out):
    os.makedirs(out, exist_ok=True)
    P = lambda *a: os.path.join(proof, *a)
    top = ["BEFORE (Sprint 6.4 code, real 365-day data)", "AFTER (Sprint 6.5)"]
    cells, left = [], []
    for rg, lab in (("1y", "1Y"), ("1m", "1M")):
        for th in ("light", "dark"):
            cells.append([load(P("chart-before", f"btc-chart-{rg}-375-{th}.png")), load(P("chart-after", f"btc-chart-{rg}-375-{th}.png"))])
            left.append(f"BTC {lab}\n{th}")
    sheet(cells, 2, top, left, "Sprint 6.5: BTC 1Y and 1M, where each average starts", os.path.join(out, "contact-btc-averages.jpg"))
    cells, left = [], []
    cells.append([load(P(f"top100-first-{b}-{th}.png")) for th in ("light", "dark") for b in ("before", "after")])
    sheet(cells, 4, ["BEFORE light", "AFTER light", "BEFORE dark", "AFTER dark"], ["Top 100\nfirst screen"],
          "Sprint 6.5: the Top 100's first screen", os.path.join(out, "contact-top100-first.jpg"))
    cells, left = [], []
    for sym, lab in (("BTT", "BTT\nlongest price"), ("SHIB", "SHIB\n12-char price"), ("HYPE", "HYPE\nHyperliquid"), ("CAKE", "CAKE\nPancakeSwap"),
                     ("FET", "FET\nlongest name"), ("BinanceLife", "BinanceLife")):
        cells.append([load(P(f"row-{sym}-{b}-{th}.png")) for th in ("light", "dark") for b in ("before", "after")])
        left.append(lab)
    sheet(cells, 4, ["BEFORE light", "AFTER light", "BEFORE dark", "AFTER dark"], left,
          "Sprint 6.5: the Top 100 rows with the longest price and names (production's recorded rows)", os.path.join(out, "contact-top100-rows.jpg"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
