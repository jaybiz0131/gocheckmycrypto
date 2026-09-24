#!/usr/bin/env python3
"""netlify_ignore.py: PROGRAM 4, T-3. Decide whether a push deserves a build.

Netlify's contract: exit 0 = SKIP the build, exit 1 = BUILD. The default is to build,
and every unclear case here resolves to building. A missed build shows a reader stale
numbers; a skipped build that should have run is the failure this file must not cause,
so it errs toward spending.

What it skips: a push that touches nothing but inactives snapshots outside the posting
windows, and a push that touches nothing but the ops ledger. Those are the two kinds of
commit that change no pixel on the site.

Why the windows matter: inside a posting window an inactives snapshot IS the product
(M-3 wants a posted list on the page within a minute), so it always builds. Outside
them the poller is writing snapshots nobody is reading yet; the evening Edition's own
push will carry them.
"""
import datetime
import os
import subprocess
import sys

# The inactives poller's own windows, in UTC, from .github/workflows/inactives.yml.
# (weekday set, first hour, last hour) with Monday = 0.
WINDOWS = [
    ({6}, 15, 23),          # Sunday slate, through the night game
    ({0, 1, 4, 5}, 0, 4),   # night games after UTC midnight
    ({0, 3, 4}, 22, 23),    # Mon/Thu/Fri night lists
    ({5}, 16, 23),          # Saturday slate
]

SKIPPABLE_PREFIXES = ("site/data/inactives/",)
SKIPPABLE_FILES = ("ledger.json",)

# U-11 (24 September 2026). A COMMIT THAT CHANGES NOTHING IN THE PUBLISHED TREE DOES NOT
# BUILD THE SITE. Checked against netlify.toml's build command on this desk, which runs
# whale_flows.py, market_pulse.py and site_build.py: none of them reads a markdown file or
# anything under docs/. A wrong entry here costs a missed build, so nothing goes in unchecked.
DOC_PREFIXES = ("docs/", "shots/", "review-queue/")
DOC_SUFFIXES = (".md",)
# NOT the .md files by name: DOC_SUFFIXES already covers them, and naming them as well is
# configuration that cannot fail. The Sports desk found that with a U-9 break on 24 September.
DOC_FILES = ("netlify_ignore.py", ".gitignore")


def is_doc(p):
    """True when a path cannot change a single pixel of the published site.

    site_build.py is deliberately NOT here: a change to the generator is the most
    site-changing commit there is.
    """
    if p in DOC_FILES or p.startswith(DOC_PREFIXES):
        return True
    return p.endswith(DOC_SUFFIXES) and not p.startswith("site/")


def in_posting_window(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    for days, lo, hi in WINDOWS:
        if now.weekday() in days and lo <= now.hour <= hi:
            return True
    return False


def changed_files():
    """Paths changed since the last built commit, or None when that cannot be known."""
    base = os.environ.get("CACHED_COMMIT_REF")
    head = os.environ.get("COMMIT_REF") or "HEAD"
    if not base:
        return None
    r = subprocess.run(["git", "diff", "--name-only", base, head],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.splitlines() if p.strip()]


def decide(paths, now=None):
    """(skip, reason). Pure, so the test below is the whole proof."""
    if paths is None:
        return False, "cannot diff against the last built commit; building"
    if not paths:
        # THE ONE CASE THIS FILE GOT EXACTLY BACKWARDS, and it cost the Board.
        #
        # A build with no changed files is not a pointless build: it is a SCHEDULED or
        # HOOK-TRIGGERED one, and on this desk those exist precisely to re-fetch data.
        # The Netlify build command runs whale_flows.py and market_pulse.py BEFORE
        # site_build.py, so the numbers on the Board come from the build, not from the
        # commit. Skipping a build because the repo has not changed skips the fetch that
        # was the entire point of firing it.
        #
        # Measured: the Board's snapshot sat at 2026-09-19T23:11:01Z until Monday
        # afternoon, 39 hours, while the noon refresh cron fired every day as designed
        # and was skipped every time. It is also why adding more build hooks in A-1 did
        # nothing for this desk: every hook ping with no new commit was declined here.
        # Running market_pulse by hand fetched 7 of 8 sections on the first try, so
        # nothing was ever wrong with the sources.
        #
        # This is what the docstring above already asks for: a skipped build that should
        # have run is the failure this file must not cause.
        return False, "no files changed, so this is a scheduled or hook build; the " \
                      "data desks refetch at build time and that is the point of it"
    unskippable = [p for p in paths
                   if not (p.startswith(SKIPPABLE_PREFIXES) or p in SKIPPABLE_FILES
                           or is_doc(p))]
    if unskippable:
        return False, f"{len(unskippable)} file(s) that change the site, e.g. {unskippable[0]}"
    if any(p.startswith(SKIPPABLE_PREFIXES) for p in paths) and in_posting_window(now):
        return False, "inactives changed inside a posting window; the board is the product"
    if all(is_doc(p) for p in paths):
        return True, (f"{len(paths)} file(s), all outside the published tree "
                      f"(U-11), e.g. {paths[0]}")
    return True, f"{len(paths)} file(s), none of which change the site"


if __name__ == "__main__":
    try:
        skip, why = decide(changed_files())
    except Exception as exc:          # never skip because this file broke
        print(f"netlify ignore: erred ({exc}); building")
        sys.exit(1)
    print(f"netlify ignore: {'SKIP' if skip else 'BUILD'} - {why}")
    sys.exit(0 if skip else 1)
