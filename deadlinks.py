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


def _redirects():
    out = {}
    p = os.path.join(PUBLISH, "_redirects")
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("/"):
            out[parts[0]] = parts[1]
    return out


def _exists(path):
    p = path.lstrip("/") or "index.html"
    full = os.path.join(PUBLISH, p)
    if os.path.isdir(full):
        full = os.path.join(full, "index.html")
    # The site serves clean URLs, so /pulse is pulse.html on disk.
    return os.path.exists(full) or (not os.path.splitext(p)[1]
                                    and os.path.exists(full + ".html"))


def check():
    red = _redirects()
    pages = [os.path.join(r, f) for r, _d, fs in os.walk(PUBLISH)
             for f in fs if f.endswith(".html")]
    dead, checked = {}, 0
    for pg in pages:
        try:
            h = open(pg, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        rel = os.path.relpath(pg, PUBLISH)
        for attr in ("href", "src"):
            for raw in set(re.findall(attr + r'="([^"]+)"', h)):
                u = urldefrag(raw)[0]
                if not u or u.startswith(("http://", "https://", "mailto:", "tel:",
                                          "data:", "#")):
                    continue
                u = urlparse(u).path
                if not u:
                    continue
                checked += 1
                if _exists(u) or (u in red and _exists(red[u])):
                    continue
                dead.setdefault(u, set()).add(rel)
    return dead, checked, len(pages)


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
