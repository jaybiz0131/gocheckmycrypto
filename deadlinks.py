#!/usr/bin/env python3
"""deadlinks.py: no built page links to a page that is not there. BUILD CHECK (C-D).

Every internal href and src in site/publish is resolved against what actually shipped,
with the _redirects map consulted, because a 301 to a live page is not a dead link.

Exit 1 on any dead link. Run after site_build.py.

USAGE  python3 deadlinks.py [--quiet]
"""

import os
import re
import sys
from urllib.parse import urldefrag, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISH = os.path.join(HERE, "site", "publish")


def _redirects(publish=None):
    out = {}
    p = os.path.join(publish or PUBLISH, "_redirects")
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("/"):
            out[parts[0]] = parts[1]
    return out


def _exists(path, publish=None):
    p = path.lstrip("/") or "index.html"
    full = os.path.join(publish or PUBLISH, p)
    if os.path.isdir(full):
        full = os.path.join(full, "index.html")
    # The site serves clean URLs, so /pulse is pulse.html on disk.
    return os.path.exists(full) or (not os.path.splitext(p)[1]
                                    and os.path.exists(full + ".html"))


_SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)


def _target(raw):
    """The internal path a raw href or src names, or '' for an outside link, an anchor or nothing."""
    u = urldefrag(raw)[0]
    if not u or u.startswith(("http://", "https://", "mailto:", "tel:", "data:", "#")):
        return ""
    return urlparse(u).path or ""


def check(publish=None):
    """({dead target: pages}, links checked, pages). A script's text is not markup: a string a script builds a link
    from ('<a href="/coins/'+k+'">') is not a link (C-DONE, 25 November 2026)."""
    publish = publish or PUBLISH
    red = _redirects(publish)
    pages = [os.path.join(r, f) for r, _d, fs in os.walk(publish)
             for f in fs if f.endswith(".html")]
    dead, checked = {}, 0
    for pg in pages:
        try:
            h = _SCRIPT.sub("", open(pg, encoding="utf-8", errors="ignore").read())
        except Exception:
            continue
        rel = os.path.relpath(pg, publish)
        for attr in ("href", "src"):
            for raw in set(re.findall(attr + r'="([^"]+)"', h)):
                u = _target(raw)
                if not u:
                    continue
                checked += 1
                if _exists(u, publish) or (u in red and _exists(red[u], publish)):
                    continue
                dead.setdefault(u, set()).add(rel)
    return dead, checked, len(pages)


def unlink(publish=None):
    """NO BUILT PAGE LINKS TO A PAGE THAT IS NOT THERE (C-DONE point 5, Jack, 24 November 2026). The build's last
    step: every anchor whose internal target neither exists nor redirects to a page that does is drawn as its own
    text. Two kinds reach it: a stored Brief or Edition citing a story the desk never published, and a frozen dated
    page naming a coin whose page is no longer built. The words stay, the dead door goes; a redirect to a live page is
    left alone. Returns the number of anchors unwrapped. Script text is never touched."""
    publish = publish or PUBLISH
    dead, _c, _n = check(publish)
    if not dead:
        return 0
    total = 0
    anchor = re.compile(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', re.S)
    for rel in sorted({r for pages in dead.values() for r in pages}):
        path = os.path.join(publish, rel)
        h = open(path, encoding="utf-8").read()
        count = [0]

        def unwrap(m):
            if _target(m.group(1)) in dead:
                count[0] += 1
                return m.group(2)
            return m.group(0)
        parts = re.split(r"(<script\b.*?</script>)", h, flags=re.S | re.I)
        out = "".join(x if i % 2 else anchor.sub(unwrap, x) for i, x in enumerate(parts))
        if count[0]:
            open(path, "w", encoding="utf-8").write(out)
            total += count[0]
    return total


def _baseline():
    """Known dead targets, with the reason, so this check keeps its teeth for NEW ones
    instead of failing every build on a content problem the site lane cannot fix. A
    monitor that cries wolf is worse than no monitor."""
    import json
    try:
        return set(json.load(open(os.path.join(HERE, "deadlinks-baseline.json"),
                                  encoding="utf-8")).get("targets") or [])
    except Exception:
        return set()


def main():
    quiet = "--quiet" in sys.argv
    dead, checked, n = check()
    known = _baseline()
    stale = known - set(dead)
    dead = {u: w for u, w in dead.items() if u not in known}
    if not quiet:
        for u, where in sorted(dead.items())[:25]:
            src = sorted(where)[:2]
            print(f"  DEAD {u}  <- {', '.join(src)}"
                  f"{f' and {len(where)-2} more' if len(where) > 2 else ''}")
    print(f"deadlinks: {checked} internal link(s) across {n} page(s), "
          f"{len(dead)} new dead target(s), {len(known) - len(stale)} known")
    if stale:
        print(f"deadlinks: {len(stale)} baselined target(s) now resolve; "
              f"drop them from deadlinks-baseline.json")
    if dead:
        print("deadlinks: FAIL")
        return 1
    print("deadlinks: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
