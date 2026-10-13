#!/usr/bin/env python3
"""
masthead_test.py: the masthead's date (Program 6 Sprint 6.5, 13 October 2026; carried from Sports).

On Sports the masthead took its date from the newest story and a script rewrote it from the
reader's clock, so a page built Oct 13 read "OCTOBER 12". Crypto's masthead took the build clock's
Eastern day in Sprint 7.1; this is the test that was missing. It renders every page type's masthead
with the clock a day AFTER the newest story, at 12:35 PM, 10:30 PM and 12:05 AM Eastern (10:30 PM
is already the next day in UTC and 12:05 AM is the first minutes of the day), and checks:

  - the date printed is the build clock's day in ET, not the newest story's and not UTC's
  - data-build-date says the same day
  - an article keeps its own dateline under its headline
  - no script on the site writes to the masthead date (the browser clock never rewrites it)

    python3 scripts/masthead_test.py [--site site/publish]
"""
import datetime
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

# SYNTHETIC CLOCKS: three build times (Eastern), each the day after the newest story's date.
CLOCKS = [("12:35 PM", 12, 35), ("10:30 PM", 22, 30), ("12:05 AM", 0, 5)]


def _mast_day(html):
    m = re.search(r'<span class="mh-dateline" data-build-date="([0-9-]+)">([^<]*)</span>', html)
    return (m.group(1), m.group(2)) if m else (None, None)


def unit():
    import site_build as sb
    fails = []
    newest = datetime.date(2026, 10, 12)                 # the newest story's day
    build_day = datetime.date(2026, 10, 13)              # the build is a day after it
    items = [i for i in sb.load_content() if not i.get("example")]
    art = next((i for i in items if i.get("date") and i.get("slug")), None)
    saved = sb._NOW_CACHE
    try:
        for label, h, mi in CLOCKS:
            et = datetime.datetime(build_day.year, build_day.month, build_day.day, h, mi, tzinfo=sb._ET_ZONE)
            sb._NOW_CACHE = et.astimezone(datetime.timezone.utc)
            want = f"{build_day.strftime('%a').upper()} · {build_day.strftime('%b').upper()} {build_day.day}, {build_day.year}"
            pages = {"shell (every page type but articles)": sb.shell("T", "d", "Latest", "<p>x</p>", sb.fmt_date(newest.isoformat()).upper())}
            if art:
                pages["article"] = sb.render_article(art, items)
            for name, html in pages.items():
                iso, txt = _mast_day(html)
                if iso != build_day.isoformat() or txt != want:
                    fails.append(f"{label} ET, {name}: masthead reads {txt!r} / {iso!r}, expected {want!r} / {build_day.isoformat()!r} "
                                 f"(newest story {newest.isoformat()}, UTC day {et.astimezone(datetime.timezone.utc).date().isoformat()})")
            if art:
                own = sb.fmt_date(art["date"])
                h2 = pages["article"]
                if own not in re.sub(r"<[^>]+>", " ", h2) or 'class="dateline"' not in h2:
                    fails.append(f"{label} ET: the article lost its own dateline ({own!r})")
    finally:
        sb._NOW_CACHE = saved
    return fails


def static(site):
    fails = []
    pages = glob.glob(os.path.join(site, "**", "*.html"), recursive=True)
    days = set()
    n = 0
    for f in pages:
        h = open(f, encoding="utf-8", errors="replace").read()
        iso, txt = _mast_day(h)
        if iso is None:
            continue
        n += 1
        d = datetime.date.fromisoformat(iso)
        if txt != f"{d.strftime('%a').upper()} · {d.strftime('%b').upper()} {d.day}, {d.year}":
            fails.append(f"{os.path.relpath(f, site)}: masthead text {txt!r} does not match its own build day {iso}")
        days.add(iso)
        for s in re.findall(r"<script[^>]*>(.*?)</script>", h, re.S):
            if "mh-dateline" in s or "data-build-date" in s:
                fails.append(f"{os.path.relpath(f, site)}: a script touches the masthead date")
    for f in glob.glob(os.path.join(site, "assets", "*.js")):
        s = open(f, encoding="utf-8", errors="replace").read()
        if "mh-dateline" in s or "data-build-date" in s:
            fails.append(f"assets/{os.path.basename(f)}: a script touches the masthead date")
    if n < 50:
        fails.append(f"only {n} built pages carry a masthead date; the check proves nothing")
    if len(days) > 1:
        fails.append(f"the build printed more than one masthead day: {sorted(days)}")
    return fails


def main():
    site = os.path.join(HERE, "site", "publish")
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    fails = unit()
    if os.path.isdir(site):
        fails += static(site)
    for f in fails:
        print("FAIL", f)
    print("MASTHEAD:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
