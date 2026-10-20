#!/usr/bin/env python3
"""U-9 browser plants for Sprint 9.5: a copy of a built tree, one break planted in it, scripts/sprint95_browser.mjs run.
usage: bplants.py <repo> <built publish dir> <workdir> <log>"""
import os, re, shutil, subprocess, sys, time
repo, tree, work, log = sys.argv[1:5]
PLANTS = [
 ("CLS: the coin chart's tabs hide with display:none again (the script waking them moves the chart's head)", "assets/system.css",
  ".cc-tabs[hidden]{display:flex;visibility:hidden}", ".cc-tabs[hidden]{display:none}"),
 ("CLS: the chart caption loses its reserved three lines", "assets/system.css",
  "@media (max-width:767px){body .cc-cap{min-height:63px}}", ""),
 ("CLS: the three small faces are no longer preloaded (the masthead and the stamps reflow when they land)", "coins/btc.html", None, None),
 ("CLS: the stale-state script is a deferred file again, not inline", "coins/btc.html", None, None),
 ("tables: the toggle no longer hides the xs-x columns at 375", "assets/system.css",
  ".fit-cb+.fit-more+.fit-tbl .xs-x{display:none}", ""),
 ("charts: the wide geometry shows at 375 again (labels at 5 to 6 px)", "assets/system.css",
  "@media (max-width:599px){.rc-w{display:none}.rc-n{display:block}}", ""),
 ("tab bar: a sixth tab is drawn on every page (Charts)", "index.html", None, None),
 ("contrast: the sentiment chart's zone labels take the zone's own color at 75% again", "pulse/sentiment.html", None, None),
 ("first object: the verdict card's page order (card after the Brief card) in the fixture", "home-fixture-card.html", None, None),
]
lines = ["Sprint 9.5, U-9, the browser half: a copy of a built tree, one break planted in it, scripts/sprint95_browser.mjs run (headless Chromium, "
         "every other host aborted). " + time.strftime("%a %b %d %Y, %I:%M %p %Z")]
ONLY = [int(x) for x in os.environ.get("PLANTS_ONLY", "").split(",") if x]
for i, (name, rel, old, new) in enumerate(PLANTS, 1):
    if ONLY and i not in ONLY:
        continue
    d = os.path.join(work, f"b{i}")
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(tree, d)
    p = os.path.join(d, rel)
    s = open(p, encoding="utf-8").read()
    if old is None:
        if rel == "coins/btc.html" and "faces" not in name:
            m = re.search(r"<script>\(function \(\) \{.*?data-asof.*?</script>", s, re.S) or re.search(r"<script>\(function \(\) \{\n'use strict';.*?</script>", s, re.S)
            if not m:
                lines.append(f"PLANT {i} {name}: NOT APPLIED"); continue
            s2 = s.replace(m.group(0), '<script defer src="/assets/asof.js"></script>')
            for other in ("coins/eth.html",):
                q = os.path.join(d, other); t = open(q, encoding="utf-8").read()
                mm = re.search(r"<script>\(function \(\) \{\n'use strict';.*?</script>", t, re.S)
                if mm: open(q, "w", encoding="utf-8").write(t.replace(mm.group(0), '<script defer src="/assets/asof.js"></script>'))
        elif rel == "pulse/sentiment.html":
            s2 = s.replace('class="band-lab" fill="var(--muted)"', 'class="band-lab" style="fill:#2E7D4F;opacity:.75"')
            s2 = s2.replace('</svg>', '</svg>') if s2 != s else s
        elif "faces" in name:
            pre = re.findall(r'<link rel="preload" as="font" type="font/woff2" crossorigin href="/assets/fonts/(?:newsreader-italic-700|plexmono-400|plexmono-700)\.woff2">', s)
            s2 = s
            for x in pre: s2 = s2.replace(x, "")
            q = os.path.join(d, "coins/eth.html"); t = open(q, encoding="utf-8").read()
            for x in pre: t = t.replace(x, "")
            open(q, "w", encoding="utf-8").write(t)
        elif rel == "index.html":
            s2 = s.replace('</nav>\n</body>', '<a class="tb-item" href="/chartmaster.html"><span>Charts</span></a></nav>\n</body>', 1) if '</nav>\n</body>' in s else s
            if s2 == s:
                s2 = re.sub(r'(<nav class="tabbar".*?)(</nav>)', r'\1<a class="tb-item" href="/chartmaster.html"><span>Charts</span></a>\2', s, count=1, flags=re.S)
        else:
            a = s.index('<div class="h-l"><aside'); b = s.index('</aside>', a) + len('</aside>')
            card = s[a + len('<div class="h-l">'):b]
            s2 = s.replace(card, "", 1)
            k = s2.index('data-block="narrative"'); k2 = s2.index("</section>", k) + len("</section>")
            s2 = s2[:k2] + card + s2[k2:]
        if s2 == s:
            lines.append(f"PLANT {i} {name}: NOT APPLIED"); continue
    else:
        if s.count(old) != 1:
            lines.append(f"PLANT {i} {name}: NOT APPLIED ({s.count(old)} matches)"); continue
        s2 = s.replace(old, new)
    open(p, "w", encoding="utf-8").write(s2)
    r = subprocess.run(["node", os.path.join(repo, "scripts", "sprint95_browser.mjs"), d], capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    fails = [ln for ln in out.splitlines() if ln.startswith("FAIL ")]
    lines.append(f"PLANT {i} {name}: exit {r.returncode}, {len(fails)} red")
    for f in fails[:5]:
        lines.append("      " + f[:230])
    print(lines[-1 - min(len(fails), 5)], flush=True)
    shutil.rmtree(d, ignore_errors=True)
lines.append("The same tree unplanted: see the suite log (all checks hold).")
open(log, "w").write("\n".join(lines) + "\n")
print("done")
