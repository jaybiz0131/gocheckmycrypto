#!/usr/bin/env python3
"""U-9 plants for Sprint 9.6: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint96_test.py
run, the break undone in that copy and the test run again. Fresh copy per plant.
usage: sprint96_plants.py <repo> <workdir> <log>
A plant is (name, [(file, old text, new text), ...]); every old text must occur exactly once in its file or the plant is
reported NOT APPLIED. The restore is from the saved copy of the file, never a git checkout (the 1 October rule)."""
import os
import shutil
import subprocess
import sys
import time

repo, work, log = sys.argv[1:4]
SC, V, SB, M, Q = "share_cards.py", "verdict.py", "site_build.py", "movers.py", "share_queue.py"
PLANTS = [
    ("grade: a second grade word is printed on the Likely card (the chip says '(not Confirmed)')",
     [(SC, '"chip": f"Checked: {grade}",', '"chip": f"Checked: {grade} (not Confirmed)",')]),
    ("because: allowed on any grade, not only Confirmed",
     [(SC, 'if any(BECAUSE_RX.search(w) and w not in ok for w in spec["words"]):', 'if False:')]),
    ("figures: a figure the verdict page does not print is no longer caught",
     [(SC, 'miss = sorted(set(FIG_RX.findall(txt)) - set(FIG_RX.findall(page)))', 'miss = []')]),
    ("AI: an AI mention is no longer caught", [(SC, 'if AI_RX.search(txt):', 'if False:')]),
    ("person: a personal name is no longer caught", [(SC, 'if PERSON_RX.search(txt):', 'if False:')]),
    ("dash: a dash is no longer caught", [(SC, 'if DASH_RX.search(txt):', 'if False:')]),
    ("color truth: up and down colors swapped on the figure",
     [(SC, 'col = UP if f["value"] > 0 else DOWN if f["value"] < 0 else INK_ON_DARK', 'col = DOWN if f["value"] > 0 else UP if f["value"] < 0 else INK_ON_DARK')]),
    ("color truth: the arrow points the other way",
     [(SC, 'return ("\u25b2 " if f["value"] > 0 else "\u25bc " if f["value"] < 0 else "") + f["text"]',
       'return ("\u25bc " if f["value"] > 0 else "\u25b2 " if f["value"] < 0 else "") + f["text"]')]),
    ("color truth: the grade chip is drawn in the up color",
     [(SC, 'L.ops.append({"kind": "chip", "x0": x0, "y0": y, "x1": x0 + inner + tw + 24, "y1": y + h, "role": "chip", "fill": INK_ON_DARK})',
       'L.ops.append({"kind": "chip", "x0": x0, "y0": y, "x1": x0 + inner + tw + 24, "y1": y + h, "role": "chip", "fill": UP})')]),
    ("color truth: the family's red accent is back on the card (the rule across the top)",
     [(SC, 'L.rect(0, 0, W, 9, MUTED_2, "rule")', 'L.rect(0, 0, W, 9, og_render.RULE_DARK, "rule")')]),
    ("no card: a verdict withheld at the cap is drawn",
     [(SC, 'if not v or v.get("kind") != "graded" or v.get("grade") not in vd.GRADES:', 'if not v:'),
      (SC, 'grade = v["grade"]\n    sec_html', 'grade = v.get("grade") or v.get("grade_withheld") or "Likely"\n    sec_html')]),
    ("no card: Ether moved with Bitcoin is given a card (its kind guard and the empty-sentences guard both broken; either alone still holds)",
     [(SC, 'if not v or v.get("kind") != "graded" or v.get("grade") not in vd.GRADES:', 'if not v or v.get("kind") not in ("graded", "with_btc"):'),
      (SC, 'grade = v["grade"]\n    sec_html', 'grade = v.get("grade") or "Likely"\n    sec_html'),
      (SC, '    if not sents:\n        return None\n    ww =', '    ww =')]),
    ("no card: a verdict with a standing correction is passed around", [(SC, '    if v.get("corrections"):\n        return None', '    if False:\n        return None')]),
    ("day card: a day with no graded verdict says nothing", [(SC, 'if not graded:\n            lines = ["No verdict was graded', 'if False:\n            lines = ["No verdict was graded')]),
    ("day card: a graded day is listed as ungraded", [(SC, 'graded.append({"name": v.get("name") or sym,', 'graded.append({"name": "Nothing",')]),
    ("tags: the size tag is the site card's 1200 by 630", [(SB, '{(og_image_size or (1200, 630))[0]}', '1200')]),
    ("tags: twitter:card is summary_large_image", [(SC, '"twitter_card": "summary"}', '"twitter_card": "summary_large_image"}')]),
    ("tags: the image URL is relative", [(SC, '"og_image": ORIGIN + spec["image"],', '"og_image": spec["image"],')]),
    ("tags: the alt text is dropped", [(SC, '"og_image_alt": spec["alt"],', '"og_image_alt": None,')]),
    ("tags: the verdict page does not take the card's tags", [(V, "schema_extra=f'\\n<script type=\"application/ld+json\">{schema}</script>', **og)",
                                                           "schema_extra=f'\\n<script type=\"application/ld+json\">{schema}</script>')")]),
    ("tags: a Big movers page does not take the card's tags", [(M, "schema_extra=f'\\n<script type=\"application/ld+json\">{schema}</script>', **og)",
                                                            "schema_extra=f'\\n<script type=\"application/ld+json\">{schema}</script>')")]),
    ("tags: the build does not hand the verdict builder its share context", [(SB, 'built = _vd.build_pages(dateline=dateline, share=_share)', 'built = _vd.build_pages(dateline=dateline)')]),
    ("tags: an image that fails to draw still gets its tags", [(SC, '    if not draw(spec, ctx.directory):\n        return {}\n', '    draw(spec, ctx.directory)\n')]),
    ("queue: the post line carries a word that is not on the card", [(SC, 'return "\\n".join(list(spec["post_lines"]) + ["", ORIGIN + spec["page"], "", spec["foot"]])',
                                                                 'return "\\n".join(list(spec["post_lines"]) + ["", "Huge news for crypto.", ORIGIN + spec["page"], "", spec["foot"]])')]),
    ("queue: the publicist's gates are not applied", [(SC, '    if not ok:\n        print("::warning::share queue: "', '    if False:\n        print("::warning::share queue: "')]),
    ("queue: an entry that exists is rewritten", [(Q, '        if os.path.exists(path):\n            continue\n', '')]),
    ("queue: the archive is queued (no day limit)", [(Q, 'if (today - dt.date.fromisoformat(spec["day"])).days >= days:', 'if False:')]),
    ("queue: a card whose day is not final is queued", [(Q, '        if not spec.get("final"):\n            continue\n', '')]),
    ("queue: the queue step reaches for the network", [(Q, 'import argparse\n', 'import argparse\nimport urllib.request\n')]),
    ("queue: the day card is never queued", [(Q, 'return ctx.specs + share_cards.day_specs(vdir, wdir, tdir, today=ctx.today)', 'return ctx.specs')]),
    ("image: the square is 1200 wide", [(SC, 'SIZE = 1080\n', 'SIZE = 1200\n')]),
    ("image: the render is not deterministic", [(SC, '    img = og_render._halftone(img)\n    d = ImageDraw.Draw(img)\n    for o in ops:',
                                                '    img = og_render._halftone(img, alpha=8 + os.urandom(1)[0] % 64)\n    d = ImageDraw.Draw(img)\n    for o in ops:')]),
    ("image: a stand-in font is accepted", [(SC, 'if not os.path.isfile(p) or os.path.getsize(p) < 50_000:', 'if False:')]),
    ("image: text that does not fit is clipped, not refused", [(SC, '        if y <= limit:\n            return ops', '        if True:\n            return ops')]),
    ("image: the quantizer is dropped (weight)", [(SC, 'out = img.convert("RGB").quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE)',
                                                  'out = img.convert("RGB")')]),
    ("wiring: the morning workflow loses its share step", [(".github/workflows/morning-read.yml", 'run: timeout 120 python3 share_queue.py || true', 'run: echo skipped')]),
    ("wiring: the evening workflow stops staging the queue", [(".github/workflows/crypto-news-brief.yml", '[ -d share-queue ] && git add share-queue', 'echo no queue')]),
    ("wiring: the share step is handed the model key", [(".github/workflows/morning-read.yml", '      - name: Share queue (the square cards, never posted)\n        if: steps.guard.outputs.serve == \'true\'\n',
                                                         '      - name: Share queue (the square cards, never posted)\n        if: steps.guard.outputs.serve == \'true\'\n        env:\n          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}\n')]),
    ("pillow: share_cards imports Pillow at module level (the reviewer's failure)", [(SC, 'class _Lazy:', 'from PIL import Image as _Plant\n\n\nclass _Lazy:')]),
    ("pillow: og_render is imported at module level", [(SC, 'class _Lazy:', 'import og_render as _plant_og\n\n\nclass _Lazy:')]),
    ("because: a Confirmed day card is refused again (the allowance is the verdict card's only)",
     [(SC, 'else {g["sentence"] for g in spec.get("graded", []) if g["grade"] == "Confirmed"} if spec["kind"] == "day" else set())', 'else set())')]),
    ("figures: events that share the hour print its figure once per event again", [(SC, 'if len(rows) >= 2:', 'if False:')]),
    ("queue: the entries go to linkedin-queue/ again", [(Q, 'QUEUE = os.path.join(HERE, "share-queue")', 'QUEUE = os.path.join(HERE, "linkedin-queue")')]),
    ("queue: the entry heading names LinkedIn again", [(SC, "text = (f'# Share draft: ", "text = (f'# LinkedIn draft: ")]),
    ("day card: its figures are checked against its own words (trivially) again", [(SC, 'why = _problem(spec, " ".join(page_text))', 'why = _problem(spec, " ".join(spec["words"]))')]),
]


def run(cwd):
    r = subprocess.run([sys.executable, "scripts/sprint96_test.py"], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPYCACHEPREFIX=os.path.join(cwd, ".pyc")))
    out = r.stdout + r.stderr
    return r.returncode, [ln.strip() for ln in out.splitlines() if ln.startswith("  FAIL ")]


shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
lines = ["Sprint 9.6, U-9: each guarded thing broken on purpose in a throwaway copy of the tree, scripts/sprint96_test.py run, "
         "the same copy run again with the break undone from the saved copy. Fresh copy per plant. "
         + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
red = 0
ONLY = {int(x) for x in os.environ.get("ONLY", "").split(",") if x.strip()}
for i, (name, edits) in enumerate(PLANTS, 1):
    if ONLY and i not in ONLY:
        continue
    d = os.path.join(work, f"p{i}")
    os.makedirs(d)
    subprocess.run("tar --exclude=./.git --exclude=./site/publish --exclude=./review --exclude=__pycache__ -cf - . | (cd %s && tar xf -)" % d,
                   shell=True, cwd=repo, check=True)
    saved, bad = {}, False
    for rel, old, new in edits:
        p = os.path.join(d, rel)
        s = open(p, encoding="utf-8").read()
        if s.count(old) != 1:
            lines.append(f"PLANT {i} {name}: NOT APPLIED ({s.count(old)} matches of the text to break in {rel})")
            print(lines[-1])
            bad = True
            break
        saved.setdefault(p, s)
        open(p, "w", encoding="utf-8").write(s.replace(old, new))
    if bad:
        shutil.rmtree(d, ignore_errors=True)
        continue
    rc, fails = run(d)
    for p, s in saved.items():
        open(p, "w", encoding="utf-8").write(s)
    rc2, fails2 = run(d)
    red += 1 if (rc != 0 and rc2 == 0) else 0
    lines.append(f"PLANT {i} {name}: exit {rc}, {len(fails)} red; restored: exit {rc2}")
    for f in fails[:4]:
        lines.append("      " + f[:210])
    if len(fails) > 4:
        lines.append(f"      ... and {len(fails) - 4} more")
    print(lines[-1] if not fails else lines[-len(fails[:4]) - (2 if len(fails) > 4 else 1)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
lines.append(f"SUMMARY: {red} of {len(ONLY) or len(PLANTS)} plants went red and came back green")
open(log, "w").write("\n".join(lines) + "\n")
print(lines[-1])
