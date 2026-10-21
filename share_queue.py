#!/usr/bin/env python3
"""
share_queue.py: the queue Jack posts the square cards from (Program 9, Sprint 9.6).

For each new share card (a graded verdict's, a Big mover's, a day's) it files one markdown entry into share-queue/, in
the shape publicist.py files its drafts in (the desk does not post to LinkedIn, so this folder is not linkedin-queue/ and
names no channel; the publicist's own folder and files are untouched): the page, the card's image (its address and its path), a box for Jack's own
framing, and a ready-to-paste post line built only from the card's own words. Jack opens an entry, adds his line and posts
by hand. NOTHING POSTS and NOTHING IS READ FROM THE ENVIRONMENT: this file has no network call and no credential.

A card is new when its entry file does not exist. An entry that exists is never rewritten, so Jack's framing stays. A
verdict card is queued once its day is final (the evening record exists, or the day is over), so the card queued is the
card that stays up, and only for the last DAYS Eastern dates (today and the two before it), so the first run does not queue the archive.

  python3 share_queue.py               # file the new entries
  python3 share_queue.py --dry-run     # name them, file nothing
  python3 share_queue.py --days 3

Fail open for the workflow: a problem prints ::warning:: and the run still exits 0.
"""
import argparse
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "share-queue")      # its own folder: this queue is channel-neutral, never linkedin-queue/
DAYS = 3


def specs(vdir=None, wdir=None, tdir=None, mdir=None, today=None):
    """Every card the records give, verdict and mover cards from the page builders (so a card is exactly the one the page
    carries), then the day cards. No image is drawn and no tag is written here."""
    import share_cards
    import verdict
    ctx = share_cards.Ctx(directory=None, today=today)
    verdict.build_pages(vdir, wdir, tdir, share=ctx)
    try:
        import movers
        movers.build_pages(mdir, share=ctx)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::share queue: the Big movers cards were not read ({type(e).__name__}: {e})")
    return ctx.specs + share_cards.day_specs(vdir, wdir, tdir, today=ctx.today)


def run(vdir=None, wdir=None, tdir=None, mdir=None, qdir=None, today=None, days=DAYS, dry=False):
    """The paths of the entries written (or, on a dry run, that would be). A card outside the last `days` Eastern dates, one whose
    day is not final, one without an entry-worthy post (the publicist's gates) and one already queued are skipped."""
    import share_cards
    today = today or share_cards.et_today()
    qdir = qdir or QUEUE
    wrote = []
    for spec in specs(vdir, wdir, tdir, mdir, today):
        if not spec.get("final"):
            continue
        if (today - dt.date.fromisoformat(spec["day"])).days >= days:      # the last `days` Eastern dates, today included
            continue
        made = share_cards.queue_entry(spec)
        if not made:
            continue
        name, text = made
        path = os.path.join(qdir, name)
        if os.path.exists(path):
            continue
        if not dry:
            os.makedirs(qdir, exist_ok=True)
            open(path, "w", encoding="utf-8").write(text)
        wrote.append(path)
    return sorted(wrote)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        wrote = run(days=a.days, dry=a.dry_run)
    except Exception as e:                                       # noqa: BLE001
        print(f"::warning::share queue: nothing was queued ({type(e).__name__}: {e})")
        return 0
    for p in wrote:
        print(f"share queue: {'WOULD QUEUE' if a.dry_run else 'QUEUED'} -> {os.path.relpath(p, HERE)} (nothing posted)")
    if not wrote:
        print("share queue: no new card to queue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
