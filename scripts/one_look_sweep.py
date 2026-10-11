#!/usr/bin/env python3
"""one_look_sweep.py <built-site-dir> [--list]

Program 6, Sprint 6.1 (11 October 2026): the two sweeps and the look checks over a built site.
  cronkite  the retired name "Cronkite" anywhere in the published tree except a URL slug
            (the launch story keeps /articles/why-crypto-cronkite.html: URLs never change)
  persona   the desk persona's phrases: technician, carved over his door, He has one rule,
            Spellbook, wizard, the Walter Cronkite sign-off, sig-script, "character of this desk"
  wash      the gradient wash, the photo band and the decorative marks: class "ground", a
            radial or linear gradient in site.css or system.css that is not a mask, hero poster
            and loop files referenced, /assets/marks/ images in a page
Story text is the sources' own words and is not a persona phrase's home, so the persona sweep
runs on pages' chrome: every page with the <article class="article"> body and the edition's lead
copy cut out. Exit 1 when any sweep finds anything; prints counts and, with --list, each hit.
"""
import os
import re
import sys

root = sys.argv[1]
show = "--list" in sys.argv
PERSONA = re.compile(r"desk's technician|carved over his door|He has one rule|Spellbook|wizard|"
                     r"Walter Cronkite|sig-script|character of this desk|anchor-desk|"
                     r"And that's the way it is", re.I)
CRON = re.compile(r"(?<![-/\w])Cronkite|Crypto Cronkite|CryptoCronkite", re.I)
WASH = re.compile(r'class="ground"|hero-poster|hero-loop|/assets/marks/|class="cb-hero|class="ww-hero')
hits = {"cronkite": [], "persona": [], "wash": []}
nfiles = 0
for dp, _dn, fns in os.walk(root):
    for fn in fns:
        if not fn.endswith((".html", ".css", ".xml", ".json", ".webmanifest", ".js", ".txt", ".svg")):
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, root)
        try:
            s = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        nfiles += 1
        for m in CRON.finditer(s):
            hits["cronkite"].append((rel, s.count("\n", 0, m.start()) + 1, s[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")))
        chrome = re.sub(r'<div class="prose">.*?</div>', "", s, flags=re.S)
        chrome = re.sub(r'<div class="ed-copy">.*?</div>', "", chrome, flags=re.S)
        chrome = re.sub(r'<div class="ed-brief-cols">.*?</div>', "", chrome, flags=re.S)
        if fn.endswith(".html") and "/articles/" in "/" + rel.replace(os.sep, "/"):
            chrome = re.sub(r"<article.*?</article>", "", chrome, flags=re.S)
        for m in PERSONA.finditer(chrome):
            hits["persona"].append((rel, chrome.count("\n", 0, m.start()) + 1, chrome[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")))
        if fn.endswith(".css"):
            for m in re.finditer(r"([^{}]*)\{([^{}]*gradient[^{}]*)\}", s):
                if "mask" in m.group(2) and "background" not in m.group(2):
                    continue
                hits["wash"].append((rel, s.count("\n", 0, m.start()) + 1, (m.group(1).strip()[:60] + "{" + m.group(2).strip()[:60])))
        elif fn.endswith(".html"):
            for m in WASH.finditer(s):
                hits["wash"].append((rel, s.count("\n", 0, m.start()) + 1, m.group(0)))
bad = 0
for k, v in hits.items():
    print(f"{k:9s} {len(v)} hit(s) in {len({h[0] for h in v})} file(s)  [{nfiles} files swept]")
    bad += len(v)
    if show:
        for rel, ln, ctx in v[:400]:
            print(f"   {rel}:{ln}: {ctx}")
print("ONE LOOK SWEEP: " + ("FAIL" if bad else "PASS"))
sys.exit(1 if bad else 0)
