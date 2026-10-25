#!/usr/bin/env python3
"""Sprint 9.8: write the verdict record drawn from scripts/sprint98_test.py's fixture (SYNTHETIC from real 14, 15 and 16 October
records, populated, with a reversed verdict) into a COPY of a built tree, at why/record-fixture/index.html, for the screenshots.
Nothing in the repository is written; the fixture lives in a scratch directory and is removed.

usage: sprint98_fixture_page.py <tree copy>"""
import datetime as dt
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))


def main(tree):
    import sprint98_test as t
    import verdict_record as vr
    td = tempfile.mkdtemp(prefix="s98fx-")
    try:
        fx = t.fixture(td)
        v = vr.view(dt.datetime(2026, 10, 17, 23, 30, tzinfo=dt.timezone.utc), vdir=fx["vdir"], mdir=fx["mdir"],
                    wdir=fx["wdir"], store=fx["store"])
        html = vr.render(v, "OCTOBER 17, 2026")
    finally:
        shutil.rmtree(td, ignore_errors=True)
    p = os.path.join(tree, "why", "record-fixture", "index.html")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(html)
    print(f"wrote {p}: {v['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
