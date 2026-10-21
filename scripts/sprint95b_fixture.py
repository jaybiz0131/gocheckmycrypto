"""Sprint 9.5b: the home fixtures, drawn from the recorded 15 October Board (fixtures/why) with its real verdict and its
recorded whale flows. Shared by scripts/sprint95b_test.py and the baseline made from Sprint 9.5's head."""
import copy
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
UTC = dt.timezone.utc


def pages(root, names=("card", "nocard")):
    """Write home-board-card.html (the 15 October Board with the verdict it really grades) and home-board-nocard.html (the same
    Board, no verdict) into `root`. The flows are the recorded 15 October ones, so Whale flows is on the Board."""
    import site_build as sb
    import home
    import snapshot
    import sprint93_test as t
    import sprint95_test as s95
    p = copy.deepcopy(t.s92().load(f"pulse_{t.D15()}.json"))
    fl = t.s92().load(f"flows_{t.D15()}.json")
    old = sb.SNAP
    sb.SNAP = snapshot.build(p, fl)
    # the masthead's build moment is the baselines' own (SITE_BUILD_NOW=2026-10-20T07:20:00Z, README.txt), whatever clock the
    # calling process holds: the canary draws these after its own build has cached the wall clock
    old_now = sb._NOW_CACHE
    sb._NOW_CACHE = dt.datetime(2026, 10, 20, 7, 20, tzinfo=UTC)
    out = {}
    try:
        now = dt.datetime(2026, 10, 15, 23, 50, tzinfo=UTC)
        for name, v in (("card", s95.v15()), ("nocard", None)):
            if name not in names:
                continue
            above = home.above_fold(sb.SNAP, p, fl, sb.board_deltas(p), t.s92().load(f"wire_{t.D15()}.json"), {}, {},
                                    sb.NEWS_CADENCE_LINE, now=now, verdict=v)
            body = (f'<main class="wrap h-page"><section class="page"><h1 class="sr-only">GoCheckMyCrypto: fixture</h1>'
                    f'{above}</section></main>')
            html = sb.shell("Home board fixture - GoCheckMyCrypto", "fixture", "The Board", body, "T", body_class="h-home",
                            path="/", system_css=True, third_party=False)
            out[name] = html
            if root:
                with open(os.path.join(root, f"home-board-{name}.html"), "w", encoding="utf-8") as f:
                    f.write(html)
    finally:
        sb.SNAP = old
        sb._NOW_CACHE = old_now
    return out
