#!/usr/bin/env python3
"""
verify_pipeline.py: self-verify the Crypto Cronkite pipeline. Same two-layer discipline as
the Pet recall verifier (_pipeline/verify_curated.py): an offline hard gate that blocks, and
a live notify-only check that never blocks a run.

  LAYER 1  offline canary (HARD FAIL, exit 1, blocks promotion). Proves the pipeline is wired
    and fails closed, with NO network and NO API key:
     - config.json, shill_rules.json well-formed; models carry no temperature/top_p/top_k
       (those 400 on the current model family).
     - prompts exist and carry their load-bearing guardrail tokens (editor: shill/rank;
       verifier: the three verdicts + adversarial; writer: DRAFT + not financial advice +
       human take).
     - shill canary: the deterministic belt scores a known shill headline as rejected and a
       primary-source real story as clean.
     - dedupe canary: two near-identical headlines collapse into one cluster.
     - full offline replay end-to-end (aggregate->editor->verifier->writer->digest) over the
       fixture: exact cluster count, exact editor split, all three verdicts present, only
       VERIFIED+REVIEW drafted, every draft DRAFT-tagged with an empty human_take + disclaimer.
     - fail-closed canaries: a missing API key fails the LLM call closed; a REJECT/hold story
       is never published; a replay-mode approval is refused by publish.
    Any deviation -> ::error:: + exit 1.

  LAYER 2  live source check (NOTIFY-ONLY, exit 3 on content mismatch, never blocks a run).
    Fetches each configured RSS feed and asserts HTTP 200 + looks-like-a-feed + carries at
    least one item (a feed-shaped channel serving zero items is as dead as a 404). A broken
    feed -> ::error:: + exit 3 (CI marks it failed / opens an issue) but never blocks. A
    network error -> ::warning:: only.

USAGE
  python3 verify_pipeline.py canary     # Layer 1 only (exit 0 pass / 1 fail)
  python3 verify_pipeline.py sources    # Layer 2 only (exit 0 pass / 3 mismatch)
  python3 verify_pipeline.py            # both; only Layer 1 affects the exit code
"""

import inspect
import glob
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common
import shill as shill_mod
import llm as llmlib

FIXTURE = os.path.join(HERE, "fixtures", "sample_feed.xml")


def gh(level, msg):
    print(f"::{level}::{msg}")


# ---- Layer 1 -----------------------------------------------------------------

def _check(cond, fails, msg):
    if not cond:
        fails.append(msg)


def _undefined_name_canary():
    """Every pipeline module must not reference a name it never binds.

    THIS EXISTS BECAUSE THE CANARY BELOW IT PASSED WHILE THE DESK WAS DOWN. On 2026-07-31 a
    scripted port added two call sites to autopilot.main() and left their `def`s behind. The
    dedupe canary was green, the replay was green, the offline gate was green, and every
    scheduled run died with `NameError: name '_rehash_of' is not defined` because the replay
    fixtures are all held by an earlier gate and never reach that branch. Two desks were down
    for two runs each before anyone read a traceback.

    A canary that exercises functions cannot see a caller that names a function which does
    not exist. Nothing dynamic is needed to catch it: the name is absent at parse time. This
    walks the AST of every module the pipeline actually runs and asserts that every loaded
    name is bound somewhere in that module, imported, or a builtin.

    Deliberately stdlib-only. `ruff check --select F821` finds the same thing and is better at
    it, but the canary is the hard gate in front of every run and must not depend on a tool
    the runner may not have installed. Scope-insensitive on purpose: it collects every
    binding anywhere in the file, so it cannot report a name that is merely out of scope. It
    catches the absent, which is the failure that took the desks down."""
    import ast
    import builtins
    fails = []
    mods = ["aggregate", "autopilot", "editor", "verifier", "researcher", "writer",
            "approver", "publish", "digest", "run", "site_build", "dedupe", "common"]
    for m in mods:
        path = os.path.join(HERE, f"{m}.py")
        if not os.path.exists(path):
            continue
        try:
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
        except SyntaxError as e:
            fails.append(f"undefined-name: {m}.py does not parse ({e})")
            continue
        bound = set(dir(builtins))
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)
            elif isinstance(n, ast.arg):
                bound.add(n.arg)
            elif isinstance(n, ast.alias):
                bound.add((n.asname or n.name).split(".")[0])
            elif isinstance(n, ast.ExceptHandler) and n.name:
                bound.add(n.name)
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                bound.update(n.names)
        used = {n.id for n in ast.walk(tree)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        missing = sorted(u for u in used - bound if not u.startswith("__"))
        _check(not missing, fails,
               f"undefined-name: {m}.py references {missing} which it never defines or "
               f"imports. Every scheduled run that reaches those lines dies with a "
               f"NameError, and no replay fixture has to reach them for that to be true.")
    return fails



def _one_definition_canary():
    """No pipeline module may define the same top-level name twice.

    Python takes the last definition and says nothing, so a duplicated function is invisible
    at import, at runtime, and to the undefined-name gate above, which only asks whether a
    name is bound at all. A scripted port on 2026-07-31 copied "everything from this function
    to end of file" out of one desk and pasted it into two others, carrying that desk's run()
    and main() along with it. Both desks then held two run() definitions, one referencing a
    module that does not exist on them, and every canary stayed green because the surviving
    definition happened to be the right one. It was luck, not design."""
    import ast
    fails = []
    mods = ["aggregate", "autopilot", "editor", "verifier", "researcher", "writer",
            "approver", "publish", "digest", "run", "site_build", "dedupe", "common", "llm"]
    for m in mods:
        path = os.path.join(HERE, f"{m}.py")
        if not os.path.exists(path):
            continue
        try:
            tree = ast.parse(open(path, encoding="utf-8").read(), path)
        except SyntaxError:
            continue  # the undefined-name canary already reports this
        seen, dupes = {}, []
        for node in tree.body:  # top level only; a nested helper may legitimately repeat
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in seen:
                    dupes.append(f"{node.name} (lines {seen[node.name]} and {node.lineno})")
                seen[node.name] = node.lineno
        _check(not dupes, fails,
               f"one-definition: {m}.py defines {'; '.join(dupes)} more than once at top "
               f"level. Python silently keeps the last, so half this file is dead code and "
               f"which half runs is an accident of ordering.")
    return fails

def _corpus_integrity_canary():
    """Two data defects the event matcher structurally cannot see.

    dedupe.py answers "is this the same STORY", which is the hard question and it
    answers it well. These two are not that question, which is why they slipped
    past every existing guard:

      DUPLICATE SLUGS. Two content records naming the same slug write the same
      file, and whichever builds last silently wins. The other story is gone with
      no error, no log line and no missing page to notice. Five on this desk when
      first measured, 2026-08-28.

      CIRCULAR update_of. Two records each naming the other as the story it
      updates, so neither is the origin. "Develops our earlier reporting" then
      points in a loop, and dupe_audit's canonical suggestion has no earliest
      match to anchor to.

    Reported here rather than in dedupe.py because they are corpus hygiene, not
    event similarity, and because dedupe.py is a synchronised chassis copy across
    three repos: it should not grow a second responsibility.
    """
    fails = []
    # BASELINED, and deliberately. This is a HARD GATE: adding it with a backlog
    # of known defects would stop the desk publishing on the first run, which is
    # exactly how a dated fixture took all three desks down for two days. So the
    # defects that already existed when the check was written are recorded in
    # corpus-baseline.json and reported without blocking, while anything NEW
    # fails immediately. Clearing an entry from the baseline is how the backlog
    # gets retired; the file should only ever shrink.
    baseline = set()
    _bl = os.path.join(HERE, "corpus-baseline.json")
    if os.path.exists(_bl):
        try:
            baseline = set(json.load(open(_bl, encoding="utf-8")).get("known", []))
        except Exception:
            baseline = set()

    def _report(key, msg):
        if key in baseline:
            gh("notice", "corpus (baselined, not blocking): " + msg)
        else:
            _check(False, fails, msg)

    recs = []
    for p in glob.glob(os.path.join(HERE, "site", "content", "*.json")):
        try:
            recs.append(json.load(open(p, encoding="utf-8")))
        except Exception:
            continue
    live = [r for r in recs if r.get("slug") and not r.get("example")]

    seen = {}
    for r in live:
        seen.setdefault(r["slug"], []).append(r)
    dupes = sorted(s for s, v in seen.items() if len(v) > 1)
    for slug in dupes:
        _report("slug:" + slug,
                "corpus: %d records share slug '%s' (one silently overwrites the other)"
                % (len(seen[slug]), slug[:58]))

    upd = {}
    for r in live:
        upd.setdefault(r["slug"], r.get("update_of") or "")
    circular = sorted({tuple(sorted((s, u))) for s, u in upd.items()
                       if u and upd.get(u) == s})
    for a, b in circular:
        _report("circular:%s|%s" % (a, b),
                "corpus: circular update_of, '%s' and '%s' each update the other"
                % (a[:34], b[:34]))
    return fails


def _conflict_canary():
    """U-13: a commit never carries a conflict marker, and preflight proves it.

    29 September 2026, from the Weather desk: its service worker carried
    `<<<<<<< Updated upstream` for SIX DAYS, from a stash applied on the 23rd.
    The file did not parse, so the offline shell and web push were dead the
    whole time; a published page carried an empty conflict where a reader could
    see it; and nothing looked broken because the site loads from the network
    anyway. Their preflight read the cache version with a pattern that found the
    FIRST of two values and passed.

    Three checks, as U-13 asks: no marker anywhere in the tree this desk
    publishes or runs, every script it serves or runs parses, and exactly one
    value wherever a conflict leaves two.

    WHY `=======` IS NOT MATCHED ON ITS OWN. Markdown underlines a title with a
    row of equals signs, and this repository's own handoff QUOTES all three
    markers in U-13's text. `<<<<<<<` and `>>>>>>>` at the start of a line are
    unambiguous; a bare `=======` line counts only in a file that already shows
    one of those. That is the difference between a gate and a nuisance.

    THE TRACKED TREE, NOT THE DISK. The Sports desk carries 919 untracked files
    whose names the Mac duplicated, "HANDOFF 2.md" and a whole "site/publish 7/"
    among them. Walking the disk would scan stale copies and report findings
    from files no deploy can reach. What a commit carries is what git tracks.
    """
    import os as _o
    import subprocess as _sp
    fails = []
    root = _o.path.dirname(_o.path.abspath(__file__))
    exts = (".py", ".js", ".mjs", ".json", ".html", ".css", ".yml", ".yaml", ".md",
            ".txt", ".xml", ".svg", ".webmanifest", ".sh")
    try:
        tracked = _sp.run(["git", "ls-files"], cwd=root, capture_output=True,
                          text=True, check=True).stdout.split("\n")
    except Exception as e:
        _check(False, fails, f"conflict canary: git ls-files failed ({e}), so nothing was scanned")
        return fails

    scanned = 0
    for rel in tracked:
        if not rel or not rel.endswith(exts):
            continue
        path = _o.path.join(root, rel)
        if not _o.path.exists(path):
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        scanned += 1
        lines = text.split("\n")
        marked = False
        for i, l in enumerate(lines):
            if l.startswith("<<<<<<<") or l.startswith(">>>>>>>"):
                marked = True
                _check(False, fails, f"conflict canary: {rel} line {i + 1} starts with a "
                                     f"conflict marker: {l[:40]!r}")
        if marked:
            for i, l in enumerate(lines):
                if l.strip() == "=======":
                    _check(False, fails, f"conflict canary: {rel} line {i + 1} is a bare "
                                         f"separator inside a file that has a marker")
    _check(scanned > 50, fails,
           f"conflict canary: only {scanned} tracked file(s) scanned, so this proves nothing")

    # EVERY SCRIPT PARSES. Python through the language's own compiler; JavaScript
    # through node, which the runners carry. A missing node is said out loud
    # rather than passing quietly.
    for rel in tracked:
        if not rel.endswith(".py"):
            continue
        path = _o.path.join(root, rel)
        if not _o.path.exists(path):
            continue
        try:
            compile(open(path, encoding="utf-8").read(), rel, "exec")
        except SyntaxError as e:
            _check(False, fails, f"conflict canary: {rel} does not parse: {e.msg} "
                                 f"at line {e.lineno}")
    node = None
    for cand in ("/opt/homebrew/bin/node", "/usr/bin/node", "/usr/local/bin/node"):
        if _o.path.exists(cand):
            node = cand
            break
    if node is None:
        from shutil import which as _which
        node = _which("node")
    js = [r for r in tracked
          if r.endswith((".js", ".mjs")) and "publish/" not in r
          and _o.path.exists(_o.path.join(root, r))]
    if node is None:
        print(f"conflict canary: SKIPPED the parse of {len(js)} script(s): node not found")
    else:
        for rel in js:
            r = _sp.run([node, "--check", _o.path.join(root, rel)], capture_output=True, text=True)
            first = (r.stderr or "").strip().splitlines()
            _check(r.returncode == 0, fails,
                   f"conflict canary: {rel} does not parse (node --check exit "
                   f"{r.returncode}): {first[0] if first else ''}")

    # EXACTLY ONE VALUE WHERE A CONFLICT LEAVES TWO. On this desk that is the
    # build stamp: two BUILD_COMMIT assignments is what a conflict in
    # site_build.py's header looks like, and whichever Python saw last would win
    # silently.
    sbp = _o.path.join(root, "site_build.py")
    if _o.path.exists(sbp):
        sb = open(sbp, encoding="utf-8").read()
        n = sum(1 for l in sb.split("\n") if l.startswith("BUILD_COMMIT = "))
        _check(n == 1, fails,
               f"conflict canary: site_build.py assigns BUILD_COMMIT {n} time(s) at the top "
               f"level, and a conflict is how it becomes two")
    return fails


def _workflow_canary():
    """CAUSE A of the 29 September failed-run audit: every workflow must LOAD.

    site-refresh.yml had `on: schedule:` with every cron line commented out,
    which Actions rejects: it created a run with ZERO JOBS, named by the file's
    path rather than its `name:`, and concluded failure on every push for eight
    days, from e2f3dd1 on 21 September. Nobody saw it because the mail says
    "site-refresh.yml" and the run has nothing in it to read.

    Checked WITHOUT pyyaml, because this pipeline is stdlib-only and the
    workflows install nothing but Pillow. A `schedule:` key must be followed by
    at least one `- cron:` before the next key at its own indentation.
    """
    import os as _o
    fails = []
    root = _o.path.dirname(_o.path.abspath(__file__))
    wf_dir = _o.path.join(root, ".github", "workflows")
    if not _o.path.isdir(wf_dir):
        _check(False, fails, "workflow canary: no .github/workflows directory")
        return fails
    files = sorted(f for f in _o.listdir(wf_dir) if f.endswith((".yml", ".yaml")))
    _check(bool(files), fails, "workflow canary: no workflow files to check")
    for fn in files:
        lines = open(_o.path.join(wf_dir, fn), encoding="utf-8").read().split("\n")
        _check(any(l.startswith("name:") for l in lines), fails,
               f"workflow canary: {fn} has no top-level name:, so Actions names it by path")
        for i, l in enumerate(lines):
            if l.strip() != "schedule:" or l.lstrip().startswith("#"):
                continue
            indent = len(l) - len(l.lstrip())
            crons = 0
            for nxt in lines[i + 1:]:
                if not nxt.strip() or nxt.lstrip().startswith("#"):
                    continue
                if len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                if nxt.lstrip().startswith("- cron:"):
                    crons += 1
            _check(crons > 0, fails,
                   f"workflow canary: {fn} line {i + 1} has a schedule: key with no "
                   f"- cron: under it, which Actions refuses to load")
    return fails


class _build_writes:
    """Record every path this process opens for writing while the block runs.

    The stamp canary's cleanup acts on this set and on nothing else. It wraps the four doors
    a Python build writes through: `open` (which `json.dump(open(..., "w"))`, `shutil.copy`
    and `living_tables` all use), `io.open` (pathlib's door), `os.open` with a write flag,
    and the destination of `os.replace` / `os.rename`. Another process's writes never pass
    through here, which is the point.
    """

    _W = getattr(os, "O_WRONLY", 1) | getattr(os, "O_RDWR", 2) | getattr(os, "O_CREAT", 0x200)

    def __init__(self, into):
        self.into = into

    def _note(self, path):
        if isinstance(path, int):
            return
        try:
            p = os.fspath(path)
            if isinstance(p, bytes):
                p = p.decode()
            self.into.add(os.path.realpath(p))
        except (TypeError, ValueError):
            pass

    def __enter__(self):
        import builtins, io
        self._saved = (builtins.open, io.open, os.open, os.replace, os.rename)
        b_open, i_open, o_open, o_replace, o_rename = self._saved
        note, W = self._note, self._W

        def _mode(args, kw):
            return kw.get("mode", args[0] if args else "r")

        def w_open(file, *a, **k):
            if any(c in _mode(a, k) for c in "wax+"):
                note(file)
            return b_open(file, *a, **k)

        def w_io_open(file, *a, **k):
            if any(c in _mode(a, k) for c in "wax+"):
                note(file)
            return i_open(file, *a, **k)

        def w_os_open(path, flags, *a, **k):
            if flags & W:
                note(path)
            return o_open(path, flags, *a, **k)

        def w_replace(src, dst, *a, **k):
            note(dst)
            return o_replace(src, dst, *a, **k)

        def w_rename(src, dst, *a, **k):
            note(dst)
            return o_rename(src, dst, *a, **k)

        builtins.open, io.open = w_open, w_io_open
        os.open, os.replace, os.rename = w_os_open, w_replace, w_rename
        return self

    def __exit__(self, *exc):
        import builtins, io
        builtins.open, io.open, os.open, os.replace, os.rename = self._saved
        return False


def _data_contract_canary():
    """THE DATA CONTRACT (5 October 2026). One snapshot; every surface prints its figures.

    Run on a snapshot built from the real site/data files and then MOVED to numbers no
    endpoint returns (Bitcoin at $12,345.67, whales $7.00B over 48 hours). Any surface that
    reads anything but the object prints a different number and goes red here. Each of the
    four checks was seen red under a plant named in the 5 October history.
    """
    import copy as _cp
    import re as _r
    import site_build as _sb
    import snapshot as _snapshot
    import chartmaster as _cm
    import twin_audit as _ta
    fails = []
    raw_p, raw_f = _sb.load_pulse(), _sb.load_flows()
    if not raw_p or not raw_f:
        _check(False, fails, "data contract: site/data carries no pulse.json or flows.json, "
                             "so nothing below can run")
        return fails
    snap = _cp.deepcopy(_snapshot.build(raw_p, raw_f))
    btc = snap["fields"]["coins"]["value"]["BTC"]
    btc["price"], btc["chg_24h_pct"] = 12345.67, 3.3
    snap["fields"]["whale_net"]["value"].update(
        {"net_usd": -7_000_000_000, "direction": "onto exchanges", "window_hours": 48})
    pv, fv = _snapshot.views(snap, raw_p, raw_f)
    want = _sb._price_fmt(12345.67)

    # 1. One endpoint per field: the coin page prints the field the Board prints.
    _old = _sb.SNAP
    try:
        _sb.SNAP = snap
        tiles = {t["key"]: t for t in _sb.board_tiles(pv, fv, {})}
        row = next(r for r in pv["movers"]["top100"] if r.get("symbol") == "BTC")
        page = _sb.render_coin_page(row, 1, pv, [], "TEST")
        strip = _sb.market_strip(pv)
        top = "".join(_sb._top100_rows(pv["movers"]["top100"][:3])) \
            if hasattr(_sb, "_top100_rows") else want
    finally:
        _sb.SNAP = _old
    _check((tiles.get("bitcoin") or {}).get("value") == want, fails,
           f"data contract: the Board's Bitcoin tile prints "
           f"{(tiles.get('bitcoin') or {}).get('value')!r}, not the snapshot's {want}")
    _pm = _r.search(r'<span class="lab">Price</span><span class="cn-v"><span>([^<]*)</span>',
                    page)
    _check(bool(_pm) and _pm.group(1) == want, fails,
           f"data contract: the coin page for BTC prints "
           f"{_pm.group(1) if _pm else 'no Price stat'}, not the snapshot's {want}; it is "
           f"reading a second endpoint")
    _check(want in strip, fails, f"data contract: the ticker's server fill does not print "
                                 f"the snapshot's {want}")
    _check(want in top, fails, f"data contract: the Top 100 row for BTC does not print the "
                               f"snapshot's {want}")
    for src in ("coins", "dominance", "total_cap", "whale_net", "fear_greed"):
        _check(bool((snap["fields"].get(src) or {}).get("source")), fails,
               f"data contract: the snapshot's {src} field names no source endpoint")

    # 2. Every stamp carries its zone (and the date): "7:26 PM ET on Oct 3".
    zone = _r.compile(r"\d{1,2}:\d{2} [AP]M ET on [A-Z][a-z]{2} \d{1,2}")
    for name, txt in (("snapshot.stamp_et", snap.get("stamp_et") or ""),
                      ("the ticker's stamp", _sb._ticker_built(pv)),
                      ("the Board's stamp", _sb.data_stamp(pv, promise_hours=1e9))):
        _check(bool(zone.search(txt)), fails,
               f"data contract: {name} carries no zone and date: {txt[:80]!r}")

    # 3. The Brief's lead line quotes the Board's numbers, window included.
    line = _sb.board_summary_line(pv, {"bitcoin": {"pct": 3.3}}, fv)
    _check(_sb.fmt_usd(7_000_000_000) in line and "2 days" in line, fails,
           f"data contract: the Brief's lead line does not quote the Board's whale figure "
           f"and window from the snapshot: {line[:120]!r}")
    _check((tiles.get("whales") or {}).get("value") == _sb.fmt_usd(7_000_000_000), fails,
           "data contract: the Board's whale tile does not print the snapshot's figure")
    real = _snapshot.build(raw_p, raw_f)
    try:
        dg = _cm.digest()
        dbtc = next((a for a in dg.get("assets") or [] if a.get("symbol") == "BTC"), {})
        _check(dbtc.get("price") == _snapshot.coin(real, "BTC").get("price"), fails,
               f"data contract: the Brief's digest gives Bitcoin {dbtc.get('price')} while "
               f"the Board's snapshot gives {_snapshot.coin(real, 'BTC').get('price')}")
    except ValueError as e:
        _check(False, fails, f"data contract: the digest could not be read ({e})")

    # 4. The twins check reads the object it is handed and nothing else.
    _check(_ta.figure_twins([{"slug": "t", "date": "2026-10-05",
                              "body": ["Bitcoin traded at $12,300 on the day."]}],
                            snap, day="2026-10-05") == [], fails,
           "data contract: the twins check flagged a story that matches the snapshot it was "
           "handed; it is reading another source")
    _check(len(_ta.figure_twins([{"slug": "t", "date": "2026-10-05",
                                  "body": ["Bitcoin traded at $86,540 on the day."]}],
                                snap, day="2026-10-05")) == 1, fails,
           "data contract: the twins check passed a story 600% off the snapshot it was "
           "handed; it is reading another source")
    return fails


def _live_layer_canary():
    """THE LIVE LAYER (5 October 2026). The ticker is the only surface that moves after the
    page loads; it says "live" and its zone; nothing else refreshes in the browser; Fear &
    Greed is off the ticker; Chart Master's boards lead and its read follows, dated in its
    own headline. Each check seen red under a plant named in the 5 October history."""
    import re as _r
    import site_build as _sb
    import snapshot as _snapshot
    fails = []
    raw_p, raw_f = _sb.load_pulse(), _sb.load_flows()
    if not raw_p or not raw_f:
        _check(False, fails, "live layer: no pulse.json or flows.json to render from")
        return fails
    pv, fv = _snapshot.views(_snapshot.build(raw_p, raw_f), raw_p, raw_f)
    home = _sb.render_home(_sb.load_content(), fv, pv, _sb.load_chartmaster() or {}, "TEST")
    m = _r.search(r'<section class="markets".*?</section>', home, _r.S)
    strip = m.group(0) if m else ""
    _check(bool(strip), fails, "live layer: the home page carries no ticker to check")
    board = home.replace(strip, "")
    scripts = " ".join(_r.findall(r"<script[^>]*>(.*?)</script>", home, _r.S))

    # 1. Nothing on the Board refreshes in the browser.
    for hook in ("data-live-px", "data-live-chg", "data-live-stamp", 'data-live="'):
        _check(hook not in board and hook not in scripts, fails,
               f"live layer: {hook} is on the home page, so a Board figure moves in the "
               f"browser under the build's stamp")
    pages = {"/pulse/prices": _sb.render_pulse_prices(pv, "TEST"),
             "/pulse": _sb.render_pulse_hub(pv, fv, _sb.load_chartmaster() or {}, "TEST")}
    for path, html in list(pages.items()) + [("/", home)]:
        _check("pulse-live.js" not in html, fails,
               f"live layer: {path} loads pulse-live.js, which refreshes Board figures in "
               f"the browser")
        _check('data-live="stamp"' not in html, fails,
               f"live layer: {path} carries a browser-filled 'updated' stamp")

    # 2. The ticker's own stamp says live, with its zone.
    _check('if(as){ as.textContent = "live \u00b7 " + etClock();' in strip, fails,
           "live layer: the ticker's stamp no longer reads 'live \u00b7 <time>'")
    _check(bool(_r.search(r'function etClock\(\)\{.*?\+ " ET";', strip, _r.S)), fails,
           "live layer: the ticker's live clock carries no zone")
    # "live" only after an OK answer that carried a price: a 429 is JSON too.
    _pf = _r.search(r'/simple/price[^"]*"\)\s*\.then\(function\(r\)\{if\(!r\.ok\)throw', strip)
    _check(bool(_pf) and "if(!landed)return;" in strip
           and strip.find("if(!landed)return;") < strip.find('"live \u00b7 "'), fails,
           "live layer: the ticker can say 'live' without a price having landed (a 429 or "
           "an empty answer would label the build's numbers live)")
    _m0 = _r.search(r'id="mktAsOf">(.*?)</span>\s*</span>', strip, _r.S)
    _check(bool(_m0) and "live" not in _m0.group(1)
           and bool(_r.search(r"\d{1,2}:\d{2} [AP]M ET on", _m0.group(1))), fails,
           f"live layer: the ticker's server-side label is not the build's stamp with its "
           f"zone and no 'live': {(_m0.group(1) if _m0 else '')[:80]!r}")

    # 3. Fear & Greed is off the ticker.
    _check("Fear &amp; Greed" not in strip and "alternative.me" not in strip
           and "data-fng" not in strip, fails,
           "live layer: Fear & Greed is back on the ticker; it belongs to the snapshot")

    # 4. Chart Master: boards first, then the read, dated in its headline.
    cm = {"date": "2026-09-21", "headline": "Test headline",
          "paragraphs": ["Bitcoin holds its range."]}
    page = _sb.render_chartmaster(cm, "TEST", pv)
    ic, ir = page.find('class="cm-charts"'), page.find('class="cm-read-h"')
    _check(ic != -1 and ir != -1 and ic < ir, fails,
           "live layer: Chart Master's read sits above the live boards")
    _check("The Chart Master&#x27;s read, September 21" in page
           or "The Chart Master's read, September 21" in page, fails,
           "live layer: Chart Master's read headline does not carry its date")
    _check("cm-newer" in page, fails,
           "live layer: a read older than the Board carries no line saying the boards are "
           "newer")

    # 5. The live mark is shown at every width (Jack, 6 October 2026: shown, never hidden).
    # The phone is most readers; a rule that hides the mark there hides the one promise the
    # contract made visible. scripts/ticker_mark_375.mjs reads it rendered; this reads the
    # stylesheet, so the canary catches it without a browser.
    css = open(os.path.join(HERE, "site", "assets", "site.css"), encoding="utf-8").read()
    css = _r.sub(r"/\*.*?\*/", "", css, flags=_r.S)
    for sel, body in _r.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if not _r.search(r"mkt-asof|mktAsOf|\.markets \.lab\b(?![-\w])", sel):
            continue
        if _r.search(r"mkt-asof \.stale", sel) and "mkt-asof," not in sel:
            continue
        _check(not _r.search(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0"
                             r"(?:px)?\s*(?:;|$)", body), fails,
               f"live layer: site.css hides the ticker's live mark ({sel.strip()[:60]} "
               f"{{{body.strip()[:40]}}})")
    return fails


def _stored_series_canary():
    """THE STORED SERIES (Jack, 6 October 2026). The Board's history is data/history/,
    appended per run and never refetched; a failed append fails honestly; a series never
    sets the page stamp; and the indicators equal the old 365-day section's to the cent on
    the same closes. Fixture: a captured /coins/bitcoin/market_chart?days=365 answer."""
    import datetime as _dt
    import hashlib
    import importlib.util
    import shutil
    import tempfile
    import urllib.error
    import history as _h
    import market_pulse as _mp
    import site_build as _sb
    import snapshot as _snapshot
    fails = []
    fx = os.path.join(HERE, "fixtures", "coingecko_market_chart_bitcoin_365d_2026-10-06.json")
    raw = json.load(open(fx, encoding="utf-8"))
    pts = raw["prices"]
    last_t = _dt.datetime.fromtimestamp(pts[-1][0] / 1000, tz=_dt.timezone.utc)
    now = last_t                                   # the moment the fixture was read
    full = _h.completed(_h.utc_day_closes(pts), now)
    tmp = tempfile.mkdtemp(prefix="series-canary-")
    calls = []

    def fetch_from(points):
        def f(url):
            calls.append(url)
            return {"prices": points}
        return f

    def r429(url):
        calls.append(url)
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
    try:
        # 1. A deleted series file triggers the bootstrap, and nothing else does.
        s, st, _ = _h.update("bitcoin", "BTC", fetch_from(pts), now=now, root=tmp)
        _check(st == "bootstrap" and len(calls) == 1 and "days=365" in calls[0], fails,
               f"stored series: a missing file did not bootstrap from 365 days "
               f"({st}, {calls})")
        calls.clear()
        _h.update("bitcoin", "BTC", fetch_from(pts), now=now, root=tmp)
        _check(not calls, fails, f"stored series: a current file made a call ({calls})")
        p = _h.path("bitcoin", tmp)
        ser = json.load(open(p, encoding="utf-8"))
        cut = sorted(ser["closes"])[-3:]
        for d in cut:                              # three days behind: an append, not a bootstrap
            del ser["closes"][d]
        json.dump(ser, open(p, "w", encoding="utf-8"))
        calls.clear()
        s, st, _ = _h.update("bitcoin", "BTC", fetch_from(pts), now=now, root=tmp)
        _check(st == "appended" and len(calls) == 1 and "days=365" not in calls[0]
               and sorted(s["closes"])[-3:] == cut, fails,
               f"stored series: a file three days behind did not append the three "
               f"missing days from a short read ({st}, {calls})")
        os.remove(_h.path("bitcoin", tmp))
        calls.clear()
        a, notes = _mp.section_assets({}, now=now, fetch=fetch_from(pts), root=tmp,
                                      log=lambda m: None)
        _check(len([c for c in calls if "days=365" in c]) == 1, fails,
               f"stored series: more than one bootstrap in one run "
               f"({len([c for c in calls if 'days=365' in c])})")
        _check(sum("one per run" in n for n in notes) == len(_mp.ASSETS) - 1, fails,
               f"stored series: the coins waiting on a bootstrap were not named ({notes})")

        # 2. The same date offered twice is stored once.
        s = _h.load("bitcoin", tmp)
        d0 = sorted(s["closes"])[-1]
        before = dict(s["closes"])
        added = _h.append(s, {d0: 1.0})
        _check(not added and s["closes"] == before, fails,
               f"stored series: {d0} offered twice was stored twice or overwritten")

        # 3. A 429 on the append leaves the series unchanged and says so by name.
        ser = json.load(open(_h.path("bitcoin", tmp), encoding="utf-8"))
        for d in sorted(ser["closes"])[-2:]:
            del ser["closes"][d]
        ser["through"] = max(ser["closes"])
        json.dump(ser, open(_h.path("bitcoin", tmp), "w", encoding="utf-8"))
        h0 = hashlib.sha256(open(_h.path("bitcoin", tmp), "rb").read()).hexdigest()
        logged = []
        assets, notes = _mp.section_assets({"BTC": pts[-1][1]}, now=now, fetch=r429,
                                           root=tmp, log=logged.append)
        h1 = hashlib.sha256(open(_h.path("bitcoin", tmp), "rb").read()).hexdigest()
        _check(h0 == h1, fails, "stored series: a 429 on the append changed the file")
        _check(any("BTC" in m and "/coins/bitcoin/market_chart" in m and "429" in m
                   for m in logged), fails,
               f"stored series: the 429 log line does not name the coin, the endpoint and "
               f"the error: {logged[:2]}")
        btc = next((x for x in assets if x["symbol"] == "BTC"), None)
        thr = ser["through"]
        pulse = {"assets": [btc] if btc else [], "written_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
        grid = _sb.board_tile_grid(_sb.board_tiles(pulse, {}, {}), {}, pulse, {}, cm_slot=False)
        want = _h.through_label(thr)
        _check(bool(btc) and want and want in grid, fails,
               f"stored series: after a failed append the Bitcoin tile does not print "
               f"'{want}'")
        # three days behind the run here: the stale mark is on the tile
        _check(f"{want}, stale" in grid, fails,
               "stored series: a series two or more days behind carries no stale mark")

        # 4. Two days behind: the stale mark, and the page stamp untouched.
        two = (now.date() - _dt.timedelta(days=2)).isoformat()
        one = (now.date() - _dt.timedelta(days=1)).isoformat()
        _check(_h.is_stale(two, now) and not _h.is_stale(one, now), fails,
               "stored series: the stale rule is not 'through the day before yesterday'")
        base = {"movers": {"top100": [{"symbol": "BTC", "price": 1.0, "rank": 1}]},
                "sections_utc": {"movers": "2026-10-06T11:00:00Z"},
                "generated_utc": "2026-10-06T11:00:00Z"}
        s_a = _snapshot.build(dict(base, assets=[{"symbol": "BTC", "through": one}]), {})
        s_b = _snapshot.build(dict(base, assets=[{"symbol": "BTC", "through": two}]), {})
        _check(s_a["stamp_utc"] == s_b["stamp_utc"] == "2026-10-06T11:00:00Z"
               and "series" in s_b and s_b["series"]["through"] == two, fails,
               f"stored series: the series moved the page stamp or is missing from the "
               f"snapshot ({s_a.get('stamp_utc')}, {s_b.get('stamp_utc')})")

        # 5. The indicators, from the stored series, equal the old section's to the cent.
        spec = importlib.util.spec_from_file_location(
            "ref_assets", os.path.join(HERE, "fixtures", "reference_section_assets_2026-10-05.py"))
        ref = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ref)
        old = ref.section_assets(lambda url: {"prices": pts}, [("bitcoin", "BTC")])[0]
        dates = sorted(full)
        new = _mp.asset_from_closes("bitcoin", "BTC", dates + [now.date().isoformat()],
                                    [full[d] for d in dates] + [pts[-1][1]])
        for k in ("price", "chg_24h_pct", "rsi14", "macd_above_signal", "sma50", "sma200",
                  "above_sma200", "golden_cross", "pct_from_high_12m", "high_12m_usd",
                  "vol30_pct", "spark", "spark_sma50", "spark_sma200", "spark_high",
                  "spark_low"):
            ov, nv = old.get(k), new.get(k)
            same = (ov == nv if not isinstance(ov, list) else
                    len(ov) == len(nv) and all(round(x, 2) == round(y, 2) for x, y in zip(ov, nv)))
            _check(same, fails, f"stored series: {k} differs from the old section on the "
                                f"same closes ({str(ov)[:40]} vs {str(nv)[:40]})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def _chartmaster_crash_canary():
    """THE CHART MASTER CRASH (6 October 2026). K-4 (6cab8b6) handed leverage_problems the
    digest's LIST where it reads an object with "assets", so every read that cleared the
    other belts died with "'list' object has no attribute 'get'", 22 September to 5
    October. A crash is not a refusal: one refused read, no second model call, the Edition
    completes. The commit message names the file's date only when a read published."""
    import re as _r
    import tempfile
    import chartmaster as _cm
    import llm as _llm
    fails = []
    # 1. The recorded run's digest (5 October Edition, d6ec0f4's pulse and flows) through
    # the arguments the stage passes: no belt may crash on them.
    rec = {"pulse.json": json.load(open(os.path.join(HERE, "fixtures",
                                                      "recorded_pulse_d6ec0f4.json"))),
           "flows.json": json.load(open(os.path.join(HERE, "fixtures",
                                                      "recorded_flows_d6ec0f4.json")))}
    real_load = _cm._load
    _cm._load = lambda n: rec.get(n, {})
    try:
        data = _cm.digest()
    finally:
        _cm._load = real_load
    text = ("Bitcoin funding on OKX is running at 10.5% annualized, and open interest on "
            "OKX holds near 2.45 billion.")
    obj = {"headline": "A test read", "paragraphs": [text, "Second.", "Third."]}
    try:
        _cm.validate(obj, **_cm._belt_inputs(data))
        crashed = ""
    except _cm.BeltCrash as e:
        crashed = str(e)
    except _llm.LLMError:
        crashed = ""                          # a refusal on content is not a crash
    _check(not crashed, fails, f"chartmaster: a belt crashed on the recorded digest: {crashed}")

    # 2. A belt that raises: one logged refusal, one model call, the stage exits 0.
    calls = []
    real = (_cm._price_belt, _llm.Client._live_raw, _cm.STATUS, _cm.SITE_DATA)
    tmp = tempfile.mkdtemp(prefix="cm-canary-")
    _cm.STATUS = os.path.join(tmp, "status.json")
    _cm.SITE_DATA = os.path.join(tmp, "chartmaster.json")

    def boom(*a):
        raise TypeError("planted")

    def fake_raw(self, stage, mc, system, user, retried_empty=False):
        calls.append(mc.get("model"))
        return json.dumps(obj)
    _cm._price_belt = boom
    _llm.Client._live_raw = fake_raw
    code = None
    prev_mode = os.environ.get("CRYPTO_LLM_MODE")
    os.environ["CRYPTO_LLM_MODE"] = "live"
    _cm._load = lambda n: rec.get(n, {})
    # THE PLANT NAMES ITSELF (7 October 2026). The stage's crash warning is right on a real
    # night and wrong in this log: on 6 October the Edition's canary step carried it as
    # "::warning::chartmaster: read refused" (23:11:45Z), the stage's own words on a green
    # run, and the scheduled canary outside stop-commands made it an annotation. The
    # stage's output is captured here and printed as the canary's plant, never as a
    # workflow command.
    import contextlib as _cl
    import io as _io
    cap = _io.StringIO()
    printed = []
    try:
        try:
            with _cl.redirect_stdout(cap):
                _cm.main()
        except SystemExit as e:
            code = e.code
        st = json.load(open(_cm.STATUS, encoding="utf-8"))
    finally:
        _cm._price_belt, _llm.Client._live_raw, _cm.STATUS, _cm.SITE_DATA = real
        _cm._load = real_load
        if prev_mode is None:
            os.environ.pop("CRYPTO_LLM_MODE", None)
        else:
            os.environ["CRYPTO_LLM_MODE"] = prev_mode
    for ln in cap.getvalue().splitlines():
        if ln.strip():
            printed.append("chartmaster crash canary, its own planted crash, expected: "
                           + _r.sub(r"^::\w+::", "", ln))
    for ln in printed:
        print(ln)
    _check("::warning::chartmaster: read refused" in cap.getvalue(), fails,
           "chartmaster: a real belt crash no longer warns from the stage")
    _check(printed and not any("::" in ln.split("expected: ", 1)[0] or
                               _r.search(r"::\w+::", ln) for ln in printed), fails,
           f"chartmaster: the canary's planted crash prints as a workflow command: {printed}")
    _check(code == 0, fails, f"chartmaster: a crashed belt did not let the Edition go on "
                             f"(exit {code})")
    _check(len(calls) == 1, fails, f"chartmaster: a crashed belt was retried: {len(calls)} "
                                   f"model calls ({calls})")
    _check(not st.get("published") and str(st.get("reason", "")).startswith(
        "belt crashed: price"), fails,
        f"chartmaster: the crash was not recorded as one refused read, 'belt crashed': {st}")

    # 3. The commit message reads the file's date and state, and no other date.
    f = os.path.join(tmp, "cm.json")
    json.dump({"date": "2026-09-21"}, open(f, "w"))
    s1 = os.path.join(tmp, "s1.json")
    json.dump({"published": False, "reason": "belt crashed: leverage: x"}, open(s1, "w"))
    s2 = os.path.join(tmp, "s2.json")
    json.dump({"published": True, "date": "2026-09-21"}, open(s2, "w"))
    m1 = _cm.commit_message(f, s1)
    m2 = _cm.commit_message(f, s2)
    m3 = _cm.commit_message(f, os.path.join(tmp, "absent.json"))
    _check(m1 == "brief: VERIFIED stories; Chart Master refused, belt crashed: leverage: x",
           fails, f"chartmaster: a refused night's message reads {m1!r}")
    _check(m2 == "brief: VERIFIED stories + Chart Master read 2026-09-21", fails,
           f"chartmaster: a published night's message reads {m2!r}")
    _check("did not run" in m3, fails, f"chartmaster: no status reads {m3!r}")
    # 4. The ledger row carries the stage's own calls, tokens and cost.
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("ops_ledger_t", os.path.join(HERE, "scripts", "ops_ledger.py"))
    _ol = _iu.module_from_spec(_sp)
    _sp.loader.exec_module(_ol)
    s4 = os.path.join(tmp, "s4.json")
    json.dump({"published": False, "model_calls": 3, "tokens": 41234, "usd": 0.0612}, open(s4, "w"))
    _check(_ol.chartmaster_spend(s4) == {"chartmaster_calls": 3, "chartmaster_tokens": 41234,
                                         "chartmaster_usd": 0.0612,
                                         "chartmaster_published": False}, fails,
           f"ledger: the Chart Master's spend is not on the row: {_ol.chartmaster_spend(s4)}")
    _check("tokens" in st and _ol.chartmaster_spend(os.path.join(tmp, "none.json")) == {}, fails,
           "ledger: the stage status carries no tokens, or a missing stage invents spend")
    for m in (m1, m2, m3):
        _check(set(_r.findall(r"\d{4}-\d{2}-\d{2}", m)) <= {"2026-09-21"}, fails,
               f"chartmaster: the commit message carries a date not in the file: {m!r}")
    return fails


def _week_movers_canary():
    """ITEM 3, the snapshot grows (6 October 2026): the week's seven closes and its low and
    high per coin from the /coins/markets sparkline field, and the movers from the same
    read, stablecoins never among them, the whole snapshot under 60 KB. Fixture: the
    endpoint's answer with sparkline=true, captured 2026-10-06 11:41Z."""
    import market_pulse as _mp
    import snapshot as _snapshot
    import stablecoins as _st
    fails = []
    fx = json.load(open(os.path.join(
        HERE, "fixtures", "coingecko_markets_sparkline_captured_2026-10-06T1141Z.json")))
    btc = next(c for c in fx if c["id"] == "bitcoin")
    sp = btc["sparkline_in_7d"]["price"]

    # 1. Seven closes on UTC day boundaries. last_updated 11:39:30Z, so the 168th point is
    # today 11:39 and today holds twelve points (00:39 to 11:39): index 155 is 23:39 on
    # October 5, that day's close, and index 11 is 23:39 on September 29.
    w = _mp.week_closes(sp, btc["last_updated"])
    days = sorted(w.get("closes7d") or {})
    _check(days == ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03",
                    "2026-10-04", "2026-10-05"], fails,
           f"week: the seven closes are not the seven completed UTC days: {days}")
    _check(w.get("closes7d", {}).get("2026-10-05") == round(sp[155], 2)
           and w.get("closes7d", {}).get("2026-09-29") == round(sp[11], 2), fails,
           "week: a close is not the last hourly price of its UTC day")
    # a point stamped exactly midnight closes the day before it
    w0 = _mp.week_closes(list(range(1, 49)), "2026-10-06T00:00:00Z")
    _check(w0.get("closes7d", {}).get("2026-10-05") == 48
           and "2026-10-06" not in w0.get("closes7d", {}), fails,
           f"week: the midnight point does not close the day before it: {w0}")
    # 1b. THE 23:00 UTC HOUR (7 October 2026). A read at 23:12Z, the Edition's own hour:
    # 168 hourly points start at 00:12 six days back, so the sparkline holds six completed
    # days, not seven. The day it lacks comes from the stored series (same UTC-close rule),
    # and a day the sparkline has is never replaced by the series.
    pts = [float(i + 1) for i in range(168)]
    stored = {f"2026-09-{d:02d}": 9000.0 + d for d in range(20, 31)}
    stored.update({f"2026-10-0{d}": 9100.0 + d for d in range(1, 7)})
    w23 = _mp.week_closes(pts, "2026-10-06T23:12:00Z", stored=stored)
    d23 = sorted(w23.get("closes7d") or {})
    _check(d23 == ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03",
                   "2026-10-04", "2026-10-05"], fails,
           f"week: a read at 23:12 UTC does not give the seven completed days: {d23}")
    _check(w23.get("closes7d", {}).get("2026-09-29") == 9029.0
           and w23.get("closes7d", {}).get("2026-10-05") == 144.0
           and w23.get("closes7d", {}).get("2026-09-30") == 24.0, fails,
           f"week: the 23:12 read's days are not the sparkline's, gap from the series: {w23}")
    _check(len(_mp.stored_closes("bitcoin")) >= 7 and _mp.stored_closes("no-such-coin") == {},
           fails, "week: the stored series is not read for the gap, or a coin without one "
                  "invents closes")
    # 2. The week's low and high over every point.
    _check(w.get("low7d") == round(min(sp), 2) and w.get("high7d") == round(max(sp), 2),
           fails, f"week: low/high are not the week's ({w.get('low7d')}, {w.get('high7d')})")

    # 3. The movers from the captured read: three rises and the fall in the top 20, ranked.
    sid = _st.ids()
    coins = {}
    for c in fx[:100]:
        sym = c["symbol"].upper()
        ch = c.get("price_change_percentage_24h")
        if sym in coins or ch is None:
            continue
        coins[sym] = {"rank": c["market_cap_rank"], "name": c["name"],
                      "chg_24h_pct": round(ch, 2)}
        if c["id"] in sid:
            coins[sym]["stablecoin"] = True
    m = _snapshot.movers(coins)
    _check([(r["symbol"], r["rank"]) for r in m.get("top20_rises") or []]
           == [("ZEC", 10), ("ADA", 15), ("XMR", 14)], fails,
           f"movers: the top-20 rises are wrong: {m.get('top20_rises')}")
    _check((m.get("top20_fall") or {}).get("symbol") == "RAIN"
           and (m.get("top20_fall") or {}).get("rank") == 19, fails,
           f"movers: the top-20 fall is wrong: {m.get('top20_fall')}")
    _check(len(m.get("standouts") or []) == 8 and all(
        abs(r["chg_24h_pct"]) > 5 for r in m["standouts"]), fails,
        f"movers: the top-100 standouts are wrong: {m.get('standouts')}")
    _check(coins.get("USDT", {}).get("stablecoin") is True, fails,
           "movers: USDT is not marked a stablecoin")

    # 4. The 5% line, a stablecoin, and the empty case, on a small market.
    def mk(rows):
        return {s: dict(rank=r, name=s, chg_24h_pct=c, **({"stablecoin": True} if st else {}))
                for s, r, c, st in rows}
    m2 = _snapshot.movers(mk([("AAA", 1, 0.1, False), ("BBB", 2, 0.2, False),
                              ("USDX", 3, 0.3, True), ("CCC", 4, -0.4, False),
                              ("DDD", 30, 5.1, False), ("EEE", 31, -4.9, False),
                              ("USDY", 32, 6.0, True)]))
    _check([r["symbol"] for r in m2["standouts"]] == ["DDD"], fails,
           f"movers: 5.1% must count and 4.9% must not: {m2['standouts']}")
    _check("USDX" not in [r["symbol"] for r in m2["top20_rises"]]
           and "USDY" not in [r["symbol"] for r in m2["standouts"]], fails,
           "movers: a stablecoin was a mover")
    m3 = _snapshot.movers(mk([("AAA", 1, 0.1, False), ("BBB", 50, -4.99, False)]))
    _check(m3["standouts"] == [] and m3["standouts_line"] == "none today", fails,
           f"movers: no standout does not read 'none today': {m3}")

    # 5. The snapshot with the week and the movers, under 60 KB, every field sourced.
    pulse = json.load(open(os.path.join(HERE, "fixtures", "recorded_pulse_d6ec0f4.json")))
    rows = []
    for c in fx[:100]:
        r = {"symbol": c["symbol"].upper(), "name": c["name"], "price": c["current_price"],
             "chg_24h_pct": c.get("price_change_percentage_24h"),
             "rank": c["market_cap_rank"], "gecko_id": c["id"],
             "mcap_usd": c.get("market_cap")}
        r.update(_mp.week_closes(c["sparkline_in_7d"]["price"], c.get("last_updated")))
        rows.append(r)
    pulse["movers"] = {"top100": rows}
    snap = _snapshot.build(pulse, json.load(open(os.path.join(
        HERE, "fixtures", "recorded_flows_d6ec0f4.json"))))
    size = len(json.dumps(snap, separators=(",", ":")).encode())
    print(f"week/movers canary: snapshot {size} bytes against 60000")
    _check(size < 60000, fails, f"snapshot: {size} bytes is over the 60 KB budget")
    for k in ("week", "movers"):
        f = (snap.get("fields") or {}).get(k) or {}
        _check(bool(f.get("value")) and "CoinGecko /coins/markets" in (f.get("source") or "")
               and f.get("read_utc"), fails,
               f"snapshot: the {k} field is missing or names no endpoint: {str(f)[:80]}")
    _check("sparkline=true" in ((snap.get("fields") or {}).get("week") or {}).get("source", ""),
           fails, "snapshot: the week field does not name its parameter")
    return fails


def _wire_canary():
    """PROGRAM 5 SPRINT 1b, THE NEWSROOM'S HALF (Jack, 5 October 2026; program section 9).
    The wire, the checked note, the writer stage turned off on the Edition path, the
    deterministic refresh, the twins gate on our text (dollar, week and month, direction),
    the News page and the Edition's cost line. Every check runs on fixtures with no model
    and no network; each was seen red under a plant (named in the 7 October report)."""
    import tempfile
    import twins_gate as _tg
    import wire as _w
    import snapshot as _snap
    import consistency_gate as _cg
    import site_build as _sb
    fails = []
    tmp = tempfile.mkdtemp(prefix="wire-canary-")
    snap = {"stamp_utc": "2026-10-07T23:10:00Z", "fields": {
        "coins": {"value": {"BTC": {"price": 100000.0, "chg_24h_pct": -0.58}}},
        "whale_net": {"value": {"net_usd": -152000000, "direction": "onto exchanges"}},
        "etf_flows": {"value": {"btc": {"latest_net_usd_m": 212.4, "latest_date": "2026-10-06"}}},
        "funding": {"value": {"BTC": {"funding_8h_pct": 0.0081}}}},
        "series": {"value": {"BTC": {"through": "2026-10-06", "chg_7d_pct": 2.75,
                                     "chg_30d_pct": 7.45}}}}
    log = os.path.join(tmp, "tg.json")

    def gate():
        return _tg.Gate(snap, log_path=log, quiet=True)
    sec = "https://www.sec.gov/newsroom/press-releases/2026-81"
    items = {"_meta": {"generated": "2026-10-07T23:09:00Z"}, "clusters": [
        {"id": "c1", "headline": "SEC approves in-kind creations for spot bitcoin ETFs",
         "source": "SEC", "url": sec, "timestamp": "2026-10-07T20:05:00Z",
         "corroboration": [{"name": "CoinDesk", "url": "https://www.coindesk.com/a",
                            "headline": "SEC Clears In-Kind Creations for Bitcoin ETFs - CoinDesk"},
                           {"name": "CoinDesk", "url": "https://www.coindesk.com/a-update",
                            "headline": "SEC Clears In-Kind Creations for Bitcoin ETFs"},
                           {"name": "The Block", "url": "https://www.theblock.co/b",
                            "headline": "SEC greenlights in-kind ETF creations"}]},
        {"id": "c2", "headline": "Exchange X pauses withdrawals after wallet incident",
         "source": "Cointelegraph", "url": "https://cointelegraph.com/news/x",
         "timestamp": "2026-10-07T18:00:00Z", "corroboration": []},
        {"id": "c3", "headline": "Lawmakers advance stablecoin bill",
         "source": "Decrypt", "url": "https://decrypt.co/s", "timestamp": "2026-10-07T17:00:00Z",
         "corroboration": [{"name": "CoinDesk", "url": "https://www.coindesk.com/s",
                            "headline": "Lawmakers Advance Stablecoin Bill"}]}]}

    def ranked(lines):
        out = []
        for c, ln in zip(items["clusters"], lines):
            urls = [c["url"]] + [x["url"] for x in c["corroboration"]]
            out.append({"id": c["id"], "headline": c["headline"], "why_it_matters": "x",
                        "wire_line": ln, "source_urls": urls,
                        "source_outlets": [c["source"]] + [x["name"] for x in c["corroboration"]]})
        return {"ranked": out}
    good = ["The SEC approved in-kind creations and redemptions for spot bitcoin ETFs.",
            "Exchange X paused withdrawals after what it called a wallet incident.",
            "A stablecoin bill cleared a House committee vote."]
    note = {"says": "The SEC's order states that in-kind creations are approved for the listed funds.",
            "unconfirmed": "Which issuers will use the change first could not be confirmed."}
    verd = {"verdicts": [{"id": "c1", "verdict": "VERIFIED", "note": note},
                         {"id": "c2", "verdict": "VERIFIED", "note": note},
                         {"id": "c3", "verdict": "NEEDS-HUMAN-REVIEW"}]}
    quiet = lambda *_a, **_k: None
    w = _w.build(ranked(good), items, verd, snap, "2026-10-07T23:09:00Z", gate=gate(), log=quiet)

    # 1. wire.json's shape and every field.
    for k in ("what_a_wire_line_is", "ranked_utc", "ranked_et", "refreshed_utc", "items",
              "checked", "dropped", "snapshot_stamp_utc"):
        _check(k in w, fails, f"wire: wire.json carries no '{k}'")
    need = ("rank", "id", "line", "board_reading", "source_count", "primary", "standing",
            "links", "reported_utc", "verdict", "mark")
    _check(len(w.get("items") or []) == 3 and all(all(k in i for k in need)
                                                  for i in w.get("items") or []), fails,
           f"wire: an item lacks a field: {[sorted(i) for i in w.get('items') or []]}")
    _check(w.get("ranked_et") == "7:09 PM ET on Oct 7", fails,
           f"wire: the stamp is not in ET with its zone: {w.get('ranked_et')!r}")
    # 2. A wire line identical to a source title fails, a corroborating member's title and
    # an outlet suffix included.
    _check(_w.is_verbatim("SEC clears in-kind creations for bitcoin ETFs",
                          _w.cluster_titles(items["clusters"][0])), fails,
           "wire: a line equal to a corroborating outlet's headline passed as the desk's own")
    wv = _w.build(ranked(["SEC approves in-kind creations for spot bitcoin ETFs"] + good[1:]),
                  items, verd, snap, "2026-10-07T23:09:00Z", gate=gate(), log=quiet)
    _check([i["id"] for i in wv["items"]] == ["c2", "c3"] and wv["dropped"]
           and "verbatim" in wv["dropped"][0]["why"], fails,
           f"wire: a verbatim headline reached the wire: {[i['line'] for i in wv['items']]}")
    # 3. The source count and the primary flag from the fixture clusters.
    by = {i["id"]: i for i in w["items"]}
    _check(by["c1"]["source_count"] == 3 and by["c1"]["primary"] is True
           and by["c1"]["links"][0]["url"] == sec, fails,
           f"wire: c1 should be 3 sources, primary, the SEC first: {by['c1']['source_count']}, "
           f"{by['c1']['primary']}, {by['c1']['links'][:1]}")
    _check(by["c2"]["source_count"] == 1 and by["c2"]["primary"] is False, fails,
           f"wire: c2 should be 1 source, not primary: {by['c2']['source_count']}, "
           f"{by['c2']['primary']}")
    _check(by["c1"]["board_reading"] == "Spot ETF net"
           and by["c3"]["board_reading"] == "Stablecoin float", fails,
           f"wire: the Board reading is not the tag rule's: {by['c1']['board_reading']!r}, "
           f"{by['c3']['board_reading']!r}")
    # 4. The checked note: present when the verifier clears the top item, on that item
    # only, with its badge; absent when it does not; never on a single-outlet story.
    ck = w.get("checked") or {}
    _check(ck.get("id") == "c1" and ck.get("badge") == "Verified" and ck.get("says")
           and ck.get("unconfirmed") and by["c1"]["mark"] == "checked"
           and by["c2"]["mark"] == by["c3"]["mark"] == "wire", fails,
           f"wire: the checked note is not on the top cleared item with its badge: {ck}")
    v2 = {"verdicts": [{"id": "c1", "verdict": "NEEDS-HUMAN-REVIEW", "note": note},
                       {"id": "c2", "verdict": "VERIFIED", "note": note},
                       {"id": "c3", "verdict": "REJECT"}]}
    w2 = _w.build(ranked(good), items, v2, snap, "2026-10-07T23:09:00Z", gate=gate(), log=quiet)
    _check(w2.get("checked") is None and all(i["mark"] == "wire" for i in w2["items"]), fails,
           f"wire: a note was written when nothing could lead and clear: {w2.get('checked')}")
    v3 = {"verdicts": [{"id": "c1", "verdict": "VERIFIED", "note": {"says": "x"}}]}
    _check(_w.build(ranked(good), items, v3, snap, "t", gate=gate(), log=quiet)["checked"] is None,
           fails, "wire: a note with one sentence missing was printed")

    # 5. The writer stage is absent from the Edition run; a breaking run keeps it.
    import common as _common
    import run as _run
    import writer as _writer
    import researcher as _res
    import approver as _appr
    saved = (_common.OUT_DIR, _w.WIRE_PATH, _tg.LOG_PATH, _writer.run, _res.run, _appr.run,
             os.environ.get("BREAKING"), os.environ.get("CRYPTO_RUN_PATH"),
             os.environ.get("CRYPTO_LLM_MODE"))
    called = []

    def stop(name):
        def f(*a, **k):
            called.append(name)
            raise RuntimeError(f"{name} was called on the wire path")
        return f
    try:
        _common.OUT_DIR = os.path.join(tmp, "out")
        os.makedirs(_common.OUT_DIR, exist_ok=True)
        _w.WIRE_PATH = os.path.join(tmp, "wire.json")
        _tg.LOG_PATH = log
        _writer.run, _res.run, _appr.run = stop("writer"), stop("researcher"), stop("approver")
        os.environ.pop("BREAKING", None)
        os.environ.pop("CRYPTO_RUN_PATH", None)
        import contextlib as _cl
        import io as _io
        with _cl.redirect_stdout(_io.StringIO()):
            rc = _run.run(mode="replay", fixture=os.path.join(HERE, "fixtures", "sample_feed.xml"))
        rep = json.load(open(os.path.join(_common.OUT_DIR, "run_report.json")))
        os.environ["BREAKING"] = "1"
        brk = _run.run_path()
    finally:
        (_common.OUT_DIR, _w.WIRE_PATH, _tg.LOG_PATH, _writer.run, _res.run, _appr.run) = saved[:6]
        for k, v in zip(("BREAKING", "CRYPTO_RUN_PATH", "CRYPTO_LLM_MODE"), saved[6:]):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    stages = [s["stage"] for s in rep.get("stages") or []]
    _check(rc == 0 and not called and "4-writer" not in stages and "4-wire" in stages
           and "4-writer" in (rep.get("stages_absent") or []) and rep.get("path") == "wire",
           fails, f"wire path: the writer stage is not absent from the Edition run "
                  f"(rc {rc}, called {called}, stages {stages}, absent {rep.get('stages_absent')})")
    _check("writer" not in ((rep.get("budget") or {}).get("by_stage") or {})
           and "verifier" in ((rep.get("budget") or {}).get("by_stage") or {}), fails,
           f"wire path: the spend by stage is wrong: {(rep.get('budget') or {}).get('by_stage')}")
    _check(brk == "story", fails, f"wire path: a breaking run left the story path ({brk})")
    _check(os.path.exists(os.path.join(tmp, "wire.json")), fails,
           "wire path: the Edition run wrote no wire.json")

    # 6. The deterministic refresh: re-counts, re-orders, and makes no model call.
    import llm as _llm
    import urllib.request as _ur
    real = (_llm.Client.__init__, _llm.Client.call_json, _ur.urlopen)

    def no_model(*a, **k):
        raise AssertionError("the refresh reached the model client or the network")
    later = [{"id": "n1", "headline": "Lawmakers advance stablecoin bill in committee vote",
              "source": "Reuters", "url": "https://www.reuters.com/s",
              "corroboration": [{"name": "Bloomberg", "url": "https://www.bloomberg.com/s",
                                 "headline": "Stablecoin bill advances"},
                                {"name": "AP", "url": "https://apnews.com/s",
                                 "headline": "House panel advances stablecoin bill"}]}]
    try:
        _llm.Client.__init__ = _llm.Client.call_json = no_model
        _ur.urlopen = no_model
        rf = _w.refresh(w, later, "2026-10-08T16:02:00Z")
        err = ""
    except AssertionError as e:
        rf, err = {}, str(e)
    finally:
        _llm.Client.__init__, _llm.Client.call_json, _ur.urlopen = real
    rid = [i["id"] for i in rf.get("items") or []]
    _check(not err, fails, f"wire refresh: {err}")
    _check(rid[:1] == ["c3"] and (rf.get("items") or [{}])[0].get("source_count") == 5
           and rf.get("refreshes") == 1 and rf.get("refreshed_et") == "12:02 PM ET on Oct 8",
           fails, f"wire refresh: the re-count or the order is wrong: {rid}, "
                  f"{[(i['id'], i['source_count']) for i in rf.get('items') or []]}")
    _check([i["line"] for i in rf.get("items") or []] and
           {i["id"]: i["line"] for i in rf["items"]} == {i["id"]: i["line"] for i in w["items"]}
           and rf.get("checked") == w.get("checked"), fails,
           "wire refresh: a line or the note was rewritten between runs")

    # 7. The twins gate: a Bitcoin figure 1.2% off is dropped with both numbers logged,
    # 0.8% off is kept; the Board's own figure and the snapshot are untouched.
    g = gate()
    t = g.text("Bitcoin traded near $101,200 at the close. Funding stayed calm.", "wire line #1")
    k = g.text("Bitcoin traded near $100,800 at the close.", "wire line #2")
    _check(t == "Funding stayed calm." and k == "Bitcoin traded near $100,800 at the close."
           and len(g.drops) == 1 and "$101,200.00" in g.drops[0]["why"]
           and "$100,000.00" in g.drops[0]["why"], fails,
           f"twins gate: 1.2% off not dropped or 0.8% off not kept, or the log lacks both "
           f"numbers: {t!r} / {k!r} / {g.drops}")
    _check(_snap.coin(snap, "BTC")["price"] == 100000.0, fails,
           "twins gate: the snapshot's figure was changed")
    _check(g.text("Bitcoin's 12-month high of $124,739 is far above.", "x") != "", fails,
           "twins gate: a dated high was read as today's price")
    # 8. Week and month: the series' figure is kept, the markets read's is dropped.
    g = gate()
    kept = g.text("Bitcoin is up 2.8% on the week and up 7.5% on the month.", "the Brief's body",
                  dollars=False)
    gone = g.text("Bitcoin is up 2.5% on the week.", "the Brief's body", dollars=False)
    gone2 = g.text("Bitcoin is up 7.0% over the past month.", "the Brief's body", dollars=False)
    _check(kept and not gone and not gone2 and len(g.drops) == 2
           and "+2.75%" in g.drops[0]["why"] and "+2.50%" in g.drops[0]["why"], fails,
           f"twins gate: series kept / markets dropped failed: {kept!r} {gone!r} {gone2!r} {g.drops}")
    s7 = _snap.series_windows(json.load(open(os.path.join(HERE, "data", "history",
                                                          "bitcoin.json")))["closes"])
    import chartmaster as _cmw
    _check(_cmw._window_changes({"spark": list(range(1, 65))}) == {}
           and _cmw._window_changes({"series_chg_7d_pct": 2.75}) == {"chg_7d_pct": 2.75},
           fails, "twins gate: the digest's week still comes from the 64-point spark")
    _check(s7.get("series_windows_through") >= "2026-10-05" and isinstance(
        s7.get("series_chg_7d_pct"), float), fails,
        f"twins gate: the stored series gives no week: {s7}")
    # 9. Direction: the word yields to the snapshot's sign; the board is never withheld.
    flows_before = json.dumps(snap["fields"]["whale_net"])
    g = gate()
    body = g.text("ETF inflows continued for a third day. Whale flows turned positive over "
                  "the day. Funding was positive.", "the Brief's body", dollars=False)
    _check(body == "ETF inflows continued for a third day. Funding was positive."
           and len(g.drops) == 1 and "whale net" in g.drops[0]["why"]
           and "-152,000,000" in g.drops[0]["why"], fails,
           f"twins gate: the mismatched whale word was not dropped with its log line: "
           f"{body!r} {g.drops}")
    _check(json.dumps(snap["fields"]["whale_net"]) == flows_before
           and _cg._victim_rank("whale-board", "", {"whale-board": "site/data/flows.json"},
                                {"site/data/flows.json"}) is None, fails,
           "twins gate: the board was changed, or the consistency gate may still withhold it")
    g.save()
    _check(len(json.load(open(log)).get("drops") or []) == 1, fails,
           "twins gate: the run's drops were not written to the log file")

    # 10. The News page: every element of the wire, and Jack's cadence line.
    wb = _sb.wire_block(w)
    for frag, what in (('class="wl-list"', "the numbered list"), (good[0], "the line"),
                       ("Reads with Spot ETF net", "the Board reading"),
                       ("3 sources", "the source count"), ("Primary source", "the primary mark"),
                       (f'href="{sec}"', "the link"), ('class="badge verified">Verified<', "the badge"),
                       ('class="wl-mark">Wire<', "the wire mark"),
                       ("4:05 PM ET on Oct 7", "the stamp"), (note["says"], "the note"),
                       (_w.WHAT_A_WIRE_LINE_IS, "the line under the list")):
        _check(frag in wb, fails, f"news page: the wire block lacks {what}")
    _check(wb.count('class="bd-stamp"') >= 4, fails, "news page: an item carries no stamp")
    _check(_sb.NEWS_CADENCE_LINE == ("The day's stories ranked and sourced by the desk, one "
                                     "checked, the Brief every evening."), fails,
           "news page: the cadence line is not Jack's words")
    real_wj = _sb.WIRE_JSON
    try:
        _sb.WIRE_JSON = os.path.join(tmp, "wire-page.json")
        json.dump(w, open(_sb.WIRE_JSON, "w"))
        hub = _sb.render_news_hub([], "TODAY")
    finally:
        _sb.WIRE_JSON = real_wj
    _check(_sb.esc(_sb.NEWS_CADENCE_LINE) in hub and 'class="wl-list"' in hub, fails,
           "news page: /news does not carry the wire and the cadence line")
    _check(_sb.wire_block({"items": []}) == "", fails, "news page: an empty wire rendered a list")

    # 11. The Edition's cost line, before and after.
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("ops_ledger_w", os.path.join(HERE, "scripts", "ops_ledger.py"))
    _ol = _iu.module_from_spec(_sp)
    _sp.loader.exec_module(_ol)
    runs = [{"t": "2026-10-04T23:25:15Z", "usd": 0.1889, "tokens": 114399, "outcome": "ran", "run": "a"},
            {"t": "2026-10-05T12:00:00Z", "usd": 0.0, "tokens": 0, "outcome": "stood down", "run": "b"},
            {"t": "2026-10-05T23:25:18Z", "usd": 0.2512, "tokens": 149861, "outcome": "ran", "run": "c"},
            {"t": "2026-10-06T15:00:00Z", "usd": 0.31, "tokens": 9, "outcome": "ran", "breaking": True, "run": "d"},
            {"t": "2026-10-06T23:21:59Z", "usd": 0.2718, "tokens": 163794, "outcome": "ran", "run": "e"}]
    row = {"t": "2026-10-07T23:20:00Z", "usd": 0.0911, "tokens": 51000, "run": "f",
           **_ol.stage_fields(rep)}
    line = _ol.cost_line(runs, row)
    _check(line.startswith("edition cost: 2026-10-07 $0.0911 (51000 tokens, path wire")
           and "before: 2026-10-04 $0.1889 (114399 tokens), 2026-10-05 $0.2512 (149861 tokens), "
               "2026-10-06 $0.2718 (163794 tokens)" in line
           and "absent 3.5-researcher, 4-writer" in line and "verifier $" in line, fails,
           f"ledger: the Edition's cost line is wrong: {line}")
    return fails


def _narrative_canary():
    """SPRINT 1b ITEM 2, the narrative line and its clause table. One sentence, two clauses,
    describing and never predicting; stored with the readings it was written from; between
    runs rewritten from the fixed table only on a threshold crossing (a sign change on spot
    ETF net, Fear & Greed crossing a band, funding leaving calm), and otherwise left alone.
    Fixtures only; each check seen red under a plant (named in the 7 October report)."""
    import copy as _copy
    import tempfile
    import narrative as _n
    import twins_gate as _tg
    import llm as _llm
    import site_build as _sb
    fails = []
    tmp = tempfile.mkdtemp(prefix="narr-canary-")
    snap = {"stamp_utc": "2026-10-07T23:10:00Z", "fields": {
        "coins": {"value": {"BTC": {"price": 100000.0, "chg_24h_pct": -1.21}}},
        "etf_flows": {"value": {"btc": {"latest_net_usd_m": 212.4, "latest_date": "2026-10-06"}}},
        "fear_greed": {"value": {"value": 54, "label": "Neutral"}},
        "funding": {"value": {"BTC": {"funding_8h_pct": 0.0081}}}}}
    wire = [{"id": "c1", "line": "The SEC approved in-kind creations for spot bitcoin ETFs.",
             "titles": ["SEC approves in-kind creations for spot bitcoin ETFs"]},
            {"id": "c2", "line": "A Senate panel advanced the market structure bill.",
             "titles": ["Senate panel advances crypto market structure bill"]},
            {"id": "c3", "line": "The CFTC opened a comment period on prediction markets.",
             "titles": ["CFTC opens comment period on event contracts"]}]
    gate = _tg.Gate(snap, log_path=os.path.join(tmp, "tg.json"), quiet=True)
    r = _n.readings(snap)
    # 1. The sentence from a fixture Board and wire: the table's, exactly; the model's when it
    # holds; the table's when the model's predicts.
    want = ("Bitcoin is drifting lower on spot ETF inflows; the news is mostly regulation.")
    _check(_n.table_line(r, wire) == want, fails,
           f"narrative: the table's sentence from the fixture is {_n.table_line(r, wire)!r}")
    ok_line = "Bitcoin slipped despite spot ETF inflows, on a day of regulators' filings."
    _check(_n.edition_line(ok_line, r, wire, gate) == (ok_line, "edition"), fails,
           "narrative: a model line that holds was not kept as the Edition's")
    _check(_n.edition_line("Bitcoin will likely rebound as ETF inflows build.", r, wire, gate)
           == (want, "table"), fails, "narrative: a predicting line was kept")
    _check(_n.edition_line("Bitcoin fell. Regulators were busy.", r, wire, gate)[1] == "table",
           fails, "narrative: a two-sentence line was kept")
    _check(_n.news_clause(wire[1:]) == "the news is mostly regulation"
           and _n.news_clause([wire[0], {"line": "Hackers drained a bridge of $8 million."}])
           == "the news is mixed, led by funds and ETFs"
           and _n.news_clause([]) == "the wire is quiet", fails,
           "narrative: the news clause does not follow the wire's top three")
    rec = _n.record(want, "table", r, wire, "2026-10-07T23:10:00Z")
    # 2. The readings named, on the record and in its small line.
    for frag in ("Bitcoin -1.21% on the day", "spot ETF net +212.4M USD (2026-10-06)",
                 "Fear & Greed 54 (neutral)", "funding +0.0081% per 8h (calm)"):
        _check(frag in rec["small_line"], fails,
               f"narrative: the small line does not name {frag!r}: {rec['small_line']!r}")
    _check(rec["readings"].get("etf_net_usd_m") == 212.4 and rec.get("written_et")
           == "7:10 PM ET on Oct 7", fails, "narrative: the record lacks its readings or stamp")
    # 3. No crossing leaves the line alone, even when readings move inside their bands.
    calm = _copy.deepcopy(snap)
    calm["fields"]["etf_flows"]["value"]["btc"]["latest_net_usd_m"] = 40.0
    calm["fields"]["fear_greed"]["value"]["value"] = 50
    calm["fields"]["coins"]["value"]["BTC"]["chg_24h_pct"] = 2.4
    same, crossed = _n.refresh(rec, calm, wire, "2026-10-08T16:02:00Z")
    _check(same is rec and crossed == [], fails,
           f"narrative: the line was rewritten with no threshold crossed: {crossed}")
    # 4. Each crossing rewrites from the table and only the table: no model client exists.
    real = (_llm.Client.__init__, _llm.Client.call_json)

    def no_model(*a, **k):
        raise AssertionError("the narrative refresh reached the model client")
    cases = []
    s1 = _copy.deepcopy(snap)
    s1["fields"]["etf_flows"]["value"]["btc"]["latest_net_usd_m"] = -88.0
    cases.append(("etf sign", s1, "Bitcoin is drifting lower on spot ETF outflows; "
                                  "the news is mostly regulation.", "changed sign"))
    s2 = _copy.deepcopy(snap)
    s2["fields"]["fear_greed"]["value"]["value"] = 41
    cases.append(("fear & greed band", s2, "Bitcoin is drifting lower with sentiment in fear; "
                                           "the news is mostly regulation.", "into fear"))
    s3 = _copy.deepcopy(snap)
    s3["fields"]["funding"]["value"]["BTC"]["funding_8h_pct"] = 0.0152
    cases.append(("funding leaves calm", s3, "Bitcoin is drifting lower with funding warming; "
                                             "the news is mostly regulation.", "left calm"))
    try:
        _llm.Client.__init__ = _llm.Client.call_json = no_model
        for name, sn, line, why in cases:
            try:
                new, cr = _n.refresh(rec, sn, wire, "2026-10-08T16:02:00Z")
            except AssertionError as e:
                new, cr = {}, []
                _check(False, fails, f"narrative: {name}: {e}")
            _check(new.get("line") == line and new.get("by") == "table"
                   and any(why in c for c in new.get("crossed") or []), fails,
                   f"narrative: {name} did not rewrite from the table: {new.get('line')!r} "
                   f"{new.get('crossed')}")
    finally:
        _llm.Client.__init__, _llm.Client.call_json = real
    # 4b. The Edition's writer (wrap.write_narrative) stores the model's line with "by".
    import wrap as _wrap
    p0 = os.path.join(tmp, "edition-narrative.json")
    import contextlib as _cl
    import io as _io
    with _cl.redirect_stdout(_io.StringIO()):
        er = _wrap.write_narrative(ok_line, r, wire, "2026-10-07T23:14:00Z", gate=gate, path=p0)
    _check(_n.load(p0) == er and er.get("by") == "edition" and er.get("line") == ok_line
           and er.get("readings") == r and len(er.get("wire_top3") or []) == 3, fails,
           f"narrative: the Edition's record is not stored as written: {er}")
    # 5. The build publishes it and says so; with no line it publishes nothing.
    p = os.path.join(tmp, "narrative.json")
    _n.write(rec, p)
    wrote = {}
    _check(_sb.publish_narrative(lambda k, v: wrote.update({k: v}), p) == want
           and json.loads(wrote.get(os.path.join("data", "narrative.json"), "{}")).get("line")
           == want, fails, "narrative: the build does not publish /data/narrative.json")
    _n.write({"line": ""}, p)
    wrote.clear()
    _check(_sb.publish_narrative(lambda k, v: wrote.update({k: v}), p) == "" and not wrote,
           fails, "narrative: an empty line was published")
    return fails


def _calendar_canary():
    """ITEM 4, calendar.json (6 October 2026). Each parser from its fixture, each clock
    from known dates, the schema (no entry without a source URL and a read stamp) and the
    today line's empty case. The FRED fixture is written to the documented shape and is
    named so: this desk holds no FRED key outside the workflow's secret."""
    import datetime as _dt
    import desk_calendar as _dc
    fails = []
    F = os.path.join(HERE, "fixtures", "calendar")

    def j(n):
        return json.load(open(os.path.join(F, n), encoding="utf-8"))
    read = "2026-10-06T11:51:03Z"
    # 1. FRED: future dates of the asked release only; no key, no entries and a placeholder.
    fr = _dc.parse_fred(j("fred_release_dates_DOCUMENTED_SHAPE_not_captured.json"), 10,
                        "CPI", "Consumer Price Index",
                        "https://fred.stlouisfed.org/release?rid=10", read, "2026-10-06")
    _check([e["date"] for e in fr] == ["2026-10-15", "2026-11-12"]
           and all(e["kind"] == "macro" and e["source"]["url"] for e in fr), fails,
           f"calendar: the FRED parser kept the wrong dates: {[e['date'] for e in fr]}")
    got, ph = _dc.read_fred("2026-10-06", None, fetch=lambda u: 1 / 0)
    _check(got == [] and "FRED" in ph, fails,
           "calendar: with no FRED key the macro entries are not absent with a placeholder")
    _check("include_release_dates_with_no_data=true" in _dc.fred_url(10, "K", "2026-10-06"),
           fails, "calendar: the FRED read does not ask for future release dates")

    # 2. Deribit: the next monthly and quarterly expiry, open interest summed by hand.
    now = _dt.datetime(2026, 10, 6, 11, 51, 3, tzinfo=_dt.timezone.utc)
    ins = j("deribit_instruments_BTC_captured_2026-10-06.json")
    book = j("deribit_book_summary_BTC_captured_2026-10-06.json")
    ex = _dc.parse_deribit("BTC", ins, book, read, now)
    oct30 = {i["instrument_name"] for i in ins["result"] if "-30OCT26-" in i["instrument_name"]}
    want_oi = round(sum(b["open_interest"] for b in book["result"]
                        if b["instrument_name"] in oct30), 1)
    _check(len(ex) == 2 and ex[0]["date"] == "2026-10-30" and ex[0]["time_et"] == "4:00 AM ET"
           and ex[0]["open_interest"] == want_oi and "monthly" in ex[0]["title"], fails,
           f"calendar: Deribit's next monthly is wrong: {ex[:1]} (want 2026-10-30, {want_oi})")
    _check(len(ex) == 2 and ex[1]["date"] == "2026-12-25" and "quarterly" in ex[1]["title"],
           fails, f"calendar: Deribit's next quarterly is wrong: {ex[1:]}")

    # 3. mempool.space: the estimate's own instant, in ET, marked computed.
    mp = _dc.parse_mempool(j("mempool_difficulty_adjustment_captured_2026-10-06.json"), read)
    _check(len(mp) == 1 and mp[0]["date"] == "2026-10-16" and mp[0]["time_et"] == "3:38 PM ET"  # 19:38:54Z, EDT
           and mp[0]["computed"] and "+4.12%" in mp[0]["title"]
           and "1,545 blocks" in mp[0]["title"], fails,
           f"calendar: the difficulty entry is wrong: {mp}")

    # 4. The statutory clocks from known dates, and a designation read from its text.
    _check([_dc.add_days("2026-04-29", n) for n in (45, 90, 180, 240)]
           == ["2026-06-13", "2026-07-28", "2026-10-26", "2026-12-25"], fails,
           "calendar: the 45/90/180/240-day clocks are wrong")
    txt = open(os.path.join(F, "fedreg_text_2026-10667_captured_2026-10-06.txt")).read()
    _check(_dc.deadline("designation-proceedings", "2026-05-29", txt)
           == ("2026-07-26", False, None), fails,
           "calendar: the designated date was not read from the notice's own text")
    oip = open(os.path.join(F, "fedreg_text_2026-01997_captured_2026-10-06.txt")).read()
    _check(_dc.deadline("proceedings", "2026-02-02", oip)
           == ("2026-05-27", True, "computed from the notice of 2025-11-28: 180 days"), fails,
           "calendar: proceedings are not 180 days from the original notice")
    _check(_dc.deadline("filing", "2026-08-19", "")[:2] == ("2026-10-03", True), fails,
           "calendar: a filing is not 45 days from its notice")
    # the filter: the captured search, every kept title a crypto product
    docs = j("fedreg_search_captured_2026-10-06.json")
    kept = [d for d in docs if _dc.is_crypto_etp(d["title"])]
    _check(len(docs) == 88 and len(kept) == 8, fails,
           f"calendar: the Federal Register filter kept {len(kept)} of {len(docs)}, not 8 of 88")
    _check(not any(_dc.is_crypto_etp(t) for t in (
        "Self-Regulatory Organizations; Cboe Exchange, Inc.; Notice of Filing and Immediate "
        "Effectiveness of a Proposed Rule Change To Amend Cboe Bitcoin U.S. ETF Index Options",
        "Self-Regulatory Organizations; NYSE American LLC; Order Instituting Proceedings To "
        "Determine Whether To Approve or Disapprove a Proposed Rule Change To List and Trade "
        "Options on the Grayscale CoinDesk Crypto 5 ETF")), fails,
        "calendar: the filter kept an options or immediate-effectiveness notice")
    vs = next((d for d in docs if d["document_number"] == "2026-16854"), {})
    _check(_dc.is_crypto_etp(vs.get("title")), fails,
           "calendar: a mixed filing naming Bitcoin and Ether products was dropped")
    _vt = open(os.path.join(F, "fedreg_text_2026-16854_captured_2026-10-06.txt")).read()
    _ve = _dc.fedreg_entries([vs], {"2026-16854": _vt}, "2026-09-01", read)
    _check(len(_ve) == 1 and _ve[0].get("notice_title") == vs.get("title"), fails,
           "calendar: a mixed filing's entry does not keep the notice's own title")
    texts = {}
    for d in kept:
        p = os.path.join(F, f"fedreg_text_{d['document_number']}_captured_2026-10-06.txt")
        if os.path.exists(p):
            texts[d["document_number"]] = open(p).read()
    fe = _dc.fedreg_entries(kept, texts, "2026-05-01", read)
    _check(not any("SR-NYSEARCA-2025-77" in e["title"] for e in fe), fails,
           "calendar: a filing the SEC approved still carries a deadline")

    # 5. The schema: no entry without a source URL and a read stamp; ET order; empty day.
    good = _dc.entry("2026-10-06", "A", "fomc", "Fed", "https://x", read, time_et="2:00 PM ET")
    early = _dc.entry("2026-10-06", "B", "expiry", "D", "https://y", read, time_et="4:00 AM ET")
    allday = _dc.entry("2026-10-06", "C", "holiday", "N", "https://z", "2026-10-06")
    nourl = _dc.entry("2026-10-06", "D", "macro", "FRED", "", read)
    nostamp = _dc.entry("2026-10-06", "E", "macro", "FRED", "https://f", "")
    cal = _dc.assemble([good, early, allday, nourl, nostamp], [], now, [])
    _check([e["title"] for e in cal["entries"]] == ["C", "B", "A"]
           and cal["dropped_without_source"] == 2, fails,
           f"calendar: an entry without a source URL or read stamp survived, or the day is "
           f"not in ET order: {[e['title'] for e in cal['entries']]}")
    _check(cal["today"]["line"] == "" and len(cal["today"]["entries"]) == 3, fails,
           "calendar: the today line lost the day's entries")
    empty = _dc.assemble([], [], now, [])
    _check(empty["today"] == {"date": "2026-10-06", "entries": [], "line": "nothing scheduled"},
           fails, f"calendar: an empty day does not read 'nothing scheduled': {empty['today']}")
    # 6. The yearly files and the unlocks file carry their sources.
    for e in _dc.fomc_entries("2026-10-06") + _dc.holiday_entries("2026-10-06") \
            + _dc.unlock_entries("2026-10-06"):
        _check(_dc.valid(e), fails, f"calendar: a yearly-file entry lacks a source: {e}")
    _check(any(e["date"] == "2026-10-28" for e in _dc.fomc_entries("2026-10-06")), fails,
           "calendar: the October FOMC meeting is missing")
    return fails


def _stamp_canary():
    """U-11's other half, and CAUSE B's fix: the canary BUILDS, then checks the two writers.

    Every page names the deploy that built it, and so does /stamp.txt. Without that a live
    read cannot name the deploy it is reading, and on 24 September neither desk could show
    that a documents-only push had NOT rebuilt the site, because Netlify posts no status to
    GitHub and a skipped build reads exactly like a paused one.

    CAUSE B of the 29 September failed-run audit was this canary itself. It read the publish
    directory in the working tree and failed closed when `stamp.txt` was absent. In a job that
    builds, that is right. In the canary job, which builds nothing, it is a gate asserting the
    output of a step that never ran: 66 failures, fixed at 31880d8 by exempting the job, which
    left the assertion untested rather than correct.

    So the canary builds its own tree now, into a temporary directory, and asserts there. That
    makes it true in any job, and it buys a stronger claim than before: because the build runs
    in this process, the commit in the output must equal BUILD_COMMIT, which the old version
    could only print a note about, since it could not tell a stale local build from the defect.

    WHAT THE DEFECT IS. Drift between the two writers. The meta tag and /stamp.txt must name
    the same commit as each other, and now also the commit this build was made from. Whether
    the DEPLOY carries that commit is a different question, asked against the deployed page by
    live_read.py, which is U-10's rule and not this one's.

    THREE THINGS THIS HAS TO BE CAREFUL ABOUT, each found by running it:

    1. `build()` reads the module global PUBLISH and begins by removing that tree. Pointing it
       at a temporary directory is therefore both how this works and the thing to get right:
       the global is restored in a finally, and the real publish directory is left untouched.
    2. `build()` prints its own `::error::` annotations, for instance when the Board is stale.
       Unredirected, a throwaway build would annotate the runner's log with errors belonging to
       no deploy. Its output is captured and only summarised, and shown only on a failure.
    3. `build()` writes tracked files OUTSIDE the publish tree, `site/data/living-tables.json`
       among them. Unrestored, every canary run would dirty the working tree. That is how the
       two data stashes dropped on 1 October were born. Any tracked file this build dirties and
       that was clean beforehand is restored from the index, byte for byte, in a finally. Files
       already dirty when it started are the author's and are not touched.
    """
    import io as _io
    import os as _o
    import re as _r
    import shutil as _sh
    import subprocess as _sp
    import tempfile as _tf
    import contextlib as _cl
    import site_build as _sb
    import live_read as _lr
    fails = []
    root = _o.path.dirname(_o.path.abspath(__file__))

    def _dirty():
        r = _sp.run(["git", "diff", "--name-only"], cwd=root, capture_output=True, text=True)
        return set(l for l in r.stdout.split("\n") if l)

    def _untracked():
        r = _sp.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root,
                    capture_output=True, text=True)
        return set(l for l in r.stdout.split("\n") if l)

    _c = _sb.BUILD_COMMIT
    _check(bool(_c) and _c != "unknown", fails,
           f"build stamp canary: the build cannot name its own commit ({_c!r}); every live "
           f"read would then assert against 'unknown' and pass")

    before = _dirty()
    untracked_before = _untracked()
    # THE STRAY WRITER, the plant this canary keeps (5 October 2026). On 4 October the day
    # history and the handoff, written by hand while this canary ran, were treated as the
    # build's and erased. So every run starts a second PROCESS that, while the build runs,
    # creates one file and rewrites one tracked file, the way an author's editor would. Both
    # must still be there after cleanup; then they are put back from a saved copy.
    _stray_new = _o.path.join(root, "fixtures", ".stamp-canary-stray.txt")
    _stray_tracked = _o.path.join(root, "fixtures", "sample_feed.xml")
    _stray_saved = open(_stray_tracked, "rb").read() if _o.path.exists(_stray_tracked) else None
    _stray_ok = (_stray_saved is not None and not _o.path.exists(_stray_new)
                 and "fixtures/sample_feed.xml" not in before)
    _stray_mark = b"<!-- written during the stamp canary by another process -->\n"
    _stray_proc = None
    if _stray_ok:
        _stray_proc = _sp.Popen([sys.executable, "-c",
                                 "import sys\n"
                                 "open(sys.argv[1],'wb').write(b'stray\\n')\n"
                                 "open(sys.argv[2],'ab').write(sys.argv[3].encode())\n",
                                 _stray_new, _stray_tracked, _stray_mark.decode()])
    real = _sb.PUBLISH
    tmp = _tf.mkdtemp(prefix="stamp-canary-")
    log = _io.StringIO()
    built_ok = False
    wrote = set()
    try:
        _sb.PUBLISH = _o.path.join(tmp, "publish")
        try:
            with _cl.redirect_stdout(log), _cl.redirect_stderr(log), _build_writes(wrote):
                _sb.build()
            built_ok = True
        except Exception as e:                       # fail closed, and say which build broke
            _check(False, fails, f"build stamp canary: the build raised {type(e).__name__}: {e}")
        out = _sb.PUBLISH

        if built_ok:
            print(f"build stamp canary: built a throwaway tree in {_o.path.basename(tmp)} "
                  f"({len(_o.listdir(out))} entries); the build's own log is captured, not "
                  f"this job's")
            _sf = _o.path.join(out, "stamp.txt")
            _check(_o.path.exists(_sf), fails,
                   "build stamp canary: the build wrote no /stamp.txt")
            if _o.path.exists(_sf):
                _stxt = open(_sf, encoding="utf-8").read()
                _mb = _r.search(r"commit ([0-9a-fA-F]{7,40}|unknown)", _stxt)
                _check(_mb is not None, fails,
                       "build stamp canary: /stamp.txt carries no commit line")
                _built = _mb.group(1) if _mb else ""
                _check(_built != "unknown", fails,
                       "build stamp canary: /stamp.txt says the build could not name its commit")
                # THE NEW ASSERTION. This build happened here, in this process, so there is no
                # such thing as a stale tree to excuse a mismatch.
                if _built and _built != "unknown":
                    _check(_built == _c, fails,
                           f"build stamp canary: this build wrote {_built[:12]} into /stamp.txt "
                           f"while BUILD_COMMIT is {_c[:12]}; the build cannot name the commit "
                           f"it was made from")
                _pages = [f for f in ["index.html", "news.html", "about.html"]
                          if _o.path.exists(_o.path.join(out, f))]
                _check(len(_pages) >= 2, fails,
                       "build stamp canary: fewer than two built pages, so the checks below "
                       "prove nothing")
                for _pg in _pages:
                    _h = open(_o.path.join(out, _pg), encoding="utf-8").read()
                    _m = _r.search(r'<meta name="build-commit" content="([^"]*)"', _h)
                    _check(_m is not None, fails,
                           f"build stamp canary: {_pg} carries no build-commit meta tag")
                    if _m:
                        _check(_m.group(1) == _built, fails,
                               f"build stamp canary: {_pg}'s stamp {_m.group(1)[:12]} and "
                               f"/stamp.txt's {_built[:12]} name different commits; the two "
                               f"writers drifted")
    finally:
        if _stray_proc is not None:
            _stray_proc.wait(timeout=30)            # its writes land before the cleanup looks
        _sb.PUBLISH = real
        _sh.rmtree(tmp, ignore_errors=True)
        # Restore only what this build dirtied, from the index, byte for byte. Never with
        # git checkout: the 1 October rule, bought by a plant that reverted its own subject.
        # THE OTHER HALF, found on 1 October when a rebase refused to run: the throwaway
        # build also CREATES files, and two of them left behind in the Sports repo blocked
        # a pull of the poller's own snapshot of the same data. Only files that did not
        # exist before this build are removed, so nothing of the author's is touched.
        # AND ONLY WHAT THE BUILD WROTE (5 October). A difference in the tree is not proof
        # the build made it: on 4 October the day history and the handoff, written by hand
        # during the run, were erased as the build's. `wrote` is the set of paths this
        # process opened for writing while the build ran; anything else is left as found.
        def _ours(rel):
            if _o.path.realpath(_o.path.join(root, rel)) in wrote:
                return True
            print(f"build stamp canary: left {rel} as found; it changed during the run but "
                  f"the build did not write it")
            return False
        for rel in sorted(r for r in _untracked() - untracked_before if _ours(r)):
            try:
                _o.remove(_o.path.join(root, rel))
                print(f"build stamp canary: removed {rel}, which the throwaway build created")
            except OSError as e:
                _check(False, fails, f"build stamp canary: the build created {rel} and it "
                                     f"could not be removed ({e}); the working tree is dirty")
        for rel in sorted(r for r in _dirty() - before if _ours(r)):
            blob = _sp.run(["git", "show", ":" + rel], cwd=root, capture_output=True)
            if blob.returncode == 0:
                with open(_o.path.join(root, rel), "wb") as fh:
                    fh.write(blob.stdout)
                print(f"build stamp canary: restored {rel}, which the throwaway build rewrote")
            else:
                _check(False, fails, f"build stamp canary: the build rewrote {rel} and it could "
                                     f"not be restored from the index; the working tree is dirty")
    if _stray_proc is not None:
        _stray_proc.wait(timeout=30)
        try:
            _check(_o.path.exists(_stray_new), fails,
                   "build stamp canary: a file another process wrote during the run "
                   "(fixtures/.stamp-canary-stray.txt) was removed by the cleanup; the cleanup "
                   "treats the author's writes as the build's")
            _now = open(_stray_tracked, "rb").read()
            _check(_now.endswith(_stray_mark), fails,
                   "build stamp canary: a tracked file another process rewrote during the run "
                   "(fixtures/sample_feed.xml) was restored by the cleanup; the cleanup "
                   "treats the author's edits as the build's")
        finally:
            if _o.path.exists(_stray_new):
                _o.remove(_stray_new)
            with open(_stray_tracked, "wb") as fh:
                fh.write(_stray_saved)
    else:
        _check(False, fails, "build stamp canary: the stray-writer plant could not run (its "
                             "fixture is missing or dirty), so the cleanup rule is untested")
    if fails and not built_ok:
        tail = log.getvalue().strip().split("\n")[-6:]
        for l in tail:
            print("    build log: " + l[:160])

    # The assertion itself must reject an empty stamp, or it compares nothing to nothing.
    _check(_lr.META.search('<meta name="build-commit" content="0123456789abcdef">')
           is not None, fails, "build stamp canary: live_read cannot find a stamp it is given")
    _check(_lr.META.search('<meta name="build-commit" content="">') is None, fails,
           "build stamp canary: live_read accepts an empty stamp as a commit")
    return fails


def _ignore_canary():
    """netlify_ignore decides whether a deploy runs at all, and it had no test.

    Its own docstring says "Pure, so the test below is the whole proof" and there was no
    test below it, on either desk. What it got wrong was the case with no test to catch
    it: an empty diff was read as "nothing to do" and skipped, when on this desk an empty
    diff means a scheduled or hook build, and those exist to refetch the market data that
    the build command fetches before the site is generated. The Board sat 39 hours stale
    while its refresh cron fired on time every day and was declined here.
    """
    import netlify_ignore as _ni
    import datetime as _dt
    fails = []

    _skip, _why = _ni.decide([])
    _check(_skip is False, fails,
           f"netlify ignore canary: a build with no changed files was SKIPPED. That is "
           f"the scheduled refresh, and the data desks refetch at build time, so "
           f"skipping it is what leaves the Board stale: {_why}")
    _skip, _why = _ni.decide(None)
    _check(_skip is False, fails,
           "netlify ignore canary: a build that cannot be diffed was skipped; every "
           "unclear case must resolve to building")
    _skip, _why = _ni.decide(["site_build.py"])
    _check(_skip is False, fails,
           "netlify ignore canary: a change to the generator did not build")
    # U-11 (24 September 2026): a commit that changes nothing in the published tree does not
    # build the site. The Pet and Parents desks each found three handoff commits in their
    # production deploy lists in one week, and the Sports desk spent two on 22 September.
    for _d in ["docs/HANDOFF.md", "README.md", "netlify_ignore.py", "docs/notes/a.md",
               "review-queue/2026-09-22.md"]:
        _check(_ni.decide([_d])[0] is True, fails,
               f"netlify ignore canary (U-11): {_d} built the site, and it cannot change a "
               f"pixel of it")
    _check(_ni.decide(["docs/HANDOFF.md", "README.md"])[0] is True, fails,
           "netlify ignore canary (U-11): a commit of nothing but documents built")
    # AND THE OTHER HALF, the half that costs a reader if it is wrong.
    _check(_ni.decide(["docs/HANDOFF.md", "site_build.py"])[0] is False, fails,
           "netlify ignore canary (U-11): the generator changed and the build was SKIPPED "
           "because a handoff file rode along in the same commit")
    _check(_ni.decide(["chartmaster.py"])[0] is False, fails,
           "netlify ignore canary (U-11): a Chart Master change did not build")
    _check(_ni.decide(["site/publish/index.html"])[0] is False, fails,
           "netlify ignore canary (U-11): a published page changed and did not build")
    _check(_ni.is_doc("site/data/x.md") is False, fails,
           "netlify ignore canary (U-11): a markdown file INSIDE the published tree was "
           "treated as a document; it can be served")
    # The two it is FOR: it must still skip them, or this fix has simply disabled it.
    _out = _dt.datetime(2026, 9, 22, 8, 0, tzinfo=_dt.timezone.utc)   # Tue 08:00, no window
    _check(_ni.in_posting_window(_out) is False, fails,
           "netlify ignore canary: the quiet-hours fixture is inside a posting window, "
           "so the two checks below prove nothing")
    _skip, _why = _ni.decide(["site/data/inactives/inactives-2026-09-22.json"], _out)
    _check(_skip is True, fails,
           f"netlify ignore canary: an inactives snapshot outside every posting window "
           f"now builds, so the fix above just switched the file off: {_why}")
    _skip, _why = _ni.decide(["ledger.json"], _out)
    _check(_skip is True, fails,
           f"netlify ignore canary: an ops-ledger row now builds: {_why}")
    # and inside a window it builds, which is the whole reason the windows exist.
    _in = _dt.datetime(2026, 9, 20, 18, 0, tzinfo=_dt.timezone.utc)   # Sunday 18:00
    _check(_ni.in_posting_window(_in) is True, fails,
           "netlify ignore canary: the Sunday-slate fixture is not in a posting window")
    _skip, _why = _ni.decide(["site/data/inactives/inactives-2026-09-20.json"], _in)
    _check(_skip is False, fails,
           "netlify ignore canary: an inactives snapshot inside a posting window did "
           "not build, and inside the window the board is the product")
    return fails


def _strip_canary():
    """D-5: four coins at 375, and a strip that says when it is cut.

    At 375 the strip showed two ticks at rest: the label held 109px of a 375px run, and
    everything from Solana rightward could only be reached by swiping a strip that gave
    no sign it scrolled. What the build is responsible for is the SHAPE that made the
    stylesheet's fix possible, and that is what this checks, because a phone width is a
    stylesheet question and a canary cannot measure one.
    """
    import site_build as _sb
    fails = []
    # NAMED, NOT GUESSED. The first cut of this tried several likely names in a loop
    # and returned quietly when none answered, so a typo in the name would have made
    # every check below disappear while the canary stayed green. It calls the one
    # function, and a strip that cannot be built is a failure rather than a silence.
    try:
        _s = _sb.market_strip(_sb.load_pulse())
    except Exception as _e:
        fails.append(f"D-5 canary: the markets strip could not be built: "
                     f"{type(_e).__name__}: {_e}")
        return fails
    _check(bool(_s and len(_s) > 200), fails,
           f"D-5 canary: the markets strip came back empty ({len(_s or '')} chars)")
    if not _s:
        return fails
    _check('class="mk-run"' in _s, fails,
           "D-5 canary: the markets strip has no scrolling run")
    _lab = _s.find('class="lab"')
    _run = _s.find('class="mk-run"')
    _check(_lab >= 0 and _run >= 0 and _lab < _run, fails,
           "D-5 canary: the Markets label is inside the scrolling run, where it holds "
           "109px of a 375px phone strip and costs two of the four coins")
    _check('role="region"' in _s and 'tabindex="0"' in _s, fails,
           "D-5 canary: the scrolling strip cannot be reached or announced by keyboard")
    # THE SETTER, NOT THE STRING. "data-more" appears in the remover too, so testing
    # for the bare name passed with the setter deleted: the fade would simply never
    # appear and the canary would not have noticed. Both halves are required, because
    # a strip that can raise the mark and never lower it is faded for ever.
    _check("setAttribute('data-more'" in _s, fails,
           "D-5 canary: nothing raises the cut mark, so a phone reader sees four coins "
           "and no sign that six more are off the edge")
    _check("removeAttribute('data-more')" in _s, fails,
           "D-5 canary: nothing clears the cut mark, so a strip with room to spare "
           "stays faded")
    return fails


# The desk's own furniture. Story bodies are excluded on purpose: a quotation is not
# ours to restyle.
CHROME_PAGES = ("index.html", "pulse.html", "wire.html", "news.html", "about.html",
                "standards.html", "method.html", "whale-watch.html")


def _first_screen_canary():
    """K-9: what a phone reader can reach, and what the page says it is.

    THE NAV SCROLLS AND SAID NOTHING. At 375 the row showed three of eight links and
    simply stopped after "Chart Master": News, The Edition, The Record, Learn and About
    were all reachable only by swiping a nav nobody swipes. News was among them, which
    is the one K-1 had just made the answer to "where is the news".
    """
    import site_build as _sb8
    fails = []
    _css = os.path.join(_sb8.ASSETS, "site.css")
    if os.path.exists(_css):
        _c = open(_css, encoding="utf-8").read()
        _check(".mh-nav .wrap[data-more]" in _c, fails,
               "K-9 canary: the nav has no cut mark, so on a phone it stops after three "
               "links with nothing saying five more exist")
    _js = _sb8.market_strip(_sb8.load_pulse())
    _check(".mh-nav .wrap" in _js, fails,
           "K-9 canary: nothing marks the nav as cut; the strip and the nav are one "
           "behaviour and one function should mark both")

    _ix = os.path.join(_sb8.PUBLISH, "index.html")
    if os.path.exists(_ix):
        _h = open(_ix, encoding="utf-8", errors="ignore").read()
        # ONE LINE SAYING WHAT THE SITE IS, and only one.
        _n = _h.count("Eight numbers explained every day")
        _check(_n == 1, fails,
               f"K-9 canary: the line that says what this site is appears {_n} times; "
               f"it is the one line of its kind on the page or it is noise")
        _check("cb-claim" in _h, fails,
               "K-9 canary: the Board's title carries no line under it")
    return fails


def _coin_chart_canary():
    """K-7: the coin chart, and the high that sat below the price.

    The page printed a seven-day line with no axis, no dates and no range, and its high
    came from a DIFFERENT snapshot than the price above it: on 21 September btc.html
    showed $85,698.00 over a high of $85,288.13. A high below the current price is not
    rounding, it is two sources on one screen.

    The browser draws the chart now, from the same place it already reads the live
    price, so the line, the high, the low and the price are one series. What a canary
    can hold is the shape of that: the build's line stays as the fallback, it says it
    is the fallback, and its own range includes the price it sits under.
    """
    import site_build as _sb7
    import json as _j7
    import re as _re7
    fails = []
    _pf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "site", "data", "pulse.json")
    if not os.path.exists(_pf):
        return fails
    _p = _j7.load(open(_pf, encoding="utf-8"))
    _coins = (_p.get("movers") or {}).get("top100") or []
    if not _coins:
        return fails

    _js = _sb7.COIN_CHART_JS
    _check("market_chart" in _js, fails,
           "K-7 canary: the chart does not fetch its own history, so it is still the "
           "build's shape with no scale")
    _check("data-days" in _sb7.render_coin_page(_coins[0], 1, _p, [], "x"), fails,
           "K-7 canary: the chart offers no ranges")
    _check("cn-cross" in _js and "mousemove" in _js, fails,
           "K-7 canary: the chart has no hover readout, so a reader cannot get a date "
           "and a price off it")
    _check("sma(" in _js, fails,
           "K-7 canary: the averages are not computed from the series shown, so they "
           "would be a second source on a chart built to end that")

    # THE HIGH IS NEVER BELOW THE PRICE, on every coin the desk builds a page for. This
    # is the defect itself, checked against the data rather than against one page.
    # READ OFF THE RENDERED PAGE, not recomputed. The first cut of this check built the
    # range itself as spark + [price] and then asked whether the max was below the
    # price, which it cannot be: the price is in the list. A check that cannot fail is
    # worse than no check, and this one would have passed with the fix deleted.
    _bad = []
    for _c in _coins[:40]:
        _sp = [v for v in (_c.get("spark7d") or []) if isinstance(v, (int, float))]
        _pr = _c.get("price")
        if not _sp or not isinstance(_pr, (int, float)):
            continue
        _html = _sb7.render_coin_page(_c, 1, _p, [], "x")
        # BOTH NUMBERS AS THE READER SEES THEM. Comparing the formatted high against the
        # raw price flagged SUI, whose price is 1.044 and whose high is the same value
        # rendered "$1.04": two spellings of one number, and not a contradiction on the
        # page at all. The contradiction is only real if the two printed strings
        # disagree, so both come off the rendered page.
        _mh = _re7.search(r"High (\$[\d,]+(?:\.\d+)?)", _html)
        _mp = _re7.search(r'class="cn-v"><span>(\$[\d,]+(?:\.\d+)?)', _html)
        if not (_mh and _mp):
            continue
        _f = lambda t: float(t.replace("$", "").replace(",", ""))
        if _f(_mh.group(1)) < _f(_mp.group(1)):
            _bad.append(f"{_c.get('symbol')} high {_mh.group(1)} < price {_mp.group(1)}")
    _check(not _bad, fails,
           f"K-7 canary: {len(_bad)} coin page(s) print a high below the price beside "
           f"it, which is the defect itself: {_bad[:3]}")
    # And the page that renders it carries the fallback and says so.
    _one = _sb7.render_coin_page(_coins[0], 1, _p, [], "x")
    _check("data-fallback" in _one, fails,
           "K-7 canary: there is no fallback line, so a blocked fetch leaves an empty "
           "box where the chart was")
    _check("from the last build" in _one, fails,
           "K-7 canary: the fallback does not say it is the fallback, so a stale line "
           "reads as a live one")
    return fails


def _chartmaster_charts_canary():
    """K-3: the Chart Master's page draws the tape it describes.

    The page had ZERO images and ZERO SVGs on a subject that is entirely charts: the
    read described a golden cross in prose on a page that would not draw one.
    """
    import site_build as _sb6
    import json as _j6
    fails = []
    _pf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "site", "data", "pulse.json")
    if not os.path.exists(_pf):
        return fails
    _p = _j6.load(open(_pf, encoding="utf-8"))
    _btc = next((x for x in (_p.get("assets") or [])
                 if str(x.get("symbol") or "").upper() == "BTC"), None)
    _check(_btc is not None, fails, "K-3 canary: no Bitcoin row to chart")
    if not _btc:
        return fails
    for _name, _svg in (("price", _sb6.cm_price_chart(_btc)),
                        ("rsi", _sb6.cm_rsi_chart(_btc)),
                        ("leverage", _sb6.cm_leverage_chart(_p.get("leverage")))):
        _check("<svg" in _svg, fails,
               f"K-3 canary: the {_name} chart draws nothing")
        _check("<figcaption" in _svg, fails,
               f"K-3 canary: the {_name} chart has no caption, so a reader is left to "
               f"work out what they are looking at")
        _check('role="img"' in _svg and "aria-label" in _svg, fails,
               f"K-3 canary: the {_name} chart is invisible to a screen reader")
    # The price chart carries a scale, which is the difference between this page and a
    # tile: a tile's chart is a shape beside a number, this page's subject IS the chart.
    _pc = _sb6.cm_price_chart(_btc)
    _check(_pc.count("<text") >= 5, fails,
           "K-3 canary: the price chart has no y-axis labels")
    _check("golden cross" in _pc or "below the 200-day" in _pc, fails,
           "K-3 canary: the price chart does not say what the two averages are doing, "
           "which is the reason both lines are on it")
    # The venue is named on the leverage chart, the same rule K-4 puts on the prose.
    _lc = _sb6.cm_leverage_chart(_p.get("leverage"))
    if _lc:
        _check("OKX" in _lc, fails,
               "K-3 canary: the leverage chart names no venue; one exchange's book is "
               "not the market's")
    # And the page itself carries them.
    _cm = os.path.join(_sb6.PUBLISH, "chartmaster.html")
    if os.path.exists(_cm):
        _h = open(_cm, encoding="utf-8", errors="ignore").read()
        _check(_h.count("cm-fig") >= 3, fails,
               f"K-3 canary: the page carries {_h.count('cm-fig')} figures, not three")
        _check(_h.find("cm-charts") < _h.find("cm-read"), fails,
               "K-3 canary: the charts are below the read, so the page still opens on "
               "prose about numbers the reader cannot see")
    return fails


def _where_is_news_canary():
    """K-1: a first-time visitor can tell which thing is the news.

    The nav offered "News desk", "The Record" and "The Edition"; the home page carried a
    Board brief, an Edition card, a "From the news desk" lane, a Record lane and a
    Record index. Five surfaces, and the one word that would have answered the question
    was not among them.
    """
    import site_build as _sb5
    import re as _re5
    fails = []
    _labels = [l for l, _ in _sb5.NAV]
    _check("News" in _labels, fails,
           f"K-1 canary: the nav has no entry called simply News: {_labels}")
    _check("News desk" not in _labels, fails,
           "K-1 canary: the nav still says 'News desk', which is a place and not a thing "
           "to read")
    _check("The Board" not in _labels, fails,
           "K-1 canary: The Board is in the nav, and the home page IS the Board")
    _check(_sb5.NAV_TITLES.get("/record.html"), fails,
           "K-1 canary: the Record's nav entry does not say what it holds")
    _tabs = [l for l, _, _ in _sb5.TAB_BAR]
    _check(_tabs == ["Board", "Whales", "News", "Edition", "Learn"], fails,
           f"K-1 canary: the phone tab bar is {_tabs}")

    _pub = _sb5.PUBLISH
    _nh = os.path.join(_pub, "news.html")
    if os.path.exists(_nh):
        _h = open(_nh, encoding="utf-8", errors="ignore").read()
        _check("What has happened" in _h, fails,
               "K-1 canary: the news front does not lead with what happened; it opens "
               "on a taxonomy")
        _check("By storyline" in _h, fails,
               "K-1 canary: the storyline library is gone from the news front")
        _rows = len(_re5.findall(r'class="nh-r"', _h))
        _check(_rows >= 2, fails,
               f"K-1 canary: the news front's chronological half has {_rows} row(s)")
        _check("/wire.html" in _h, fails,
               "K-1 canary: the Wire is not linked from the news front, and it is not "
               "in the nav either, so it is unreachable")
        # The first item on the front IS the newest thing the desk published.
        _first = _re5.search(r'class="nh-x" href="[^"]*">([^<]+)', _h)
        _rows_src = _sb5._wire_rows(_sb5.load_content(), None, hours=24 * 30)
        if _first and _rows_src:
            _check(_first.group(1).strip()[:40] == _rows_src[0]["text"].strip()[:40],
                   fails,
                   f"K-1 canary: the news front does not open on the newest item: "
                   f"{_first.group(1)[:40]!r} vs {_rows_src[0]['text'][:40]!r}")
    # The Board did not move: it is still reachable from the home page.
    _ix = os.path.join(_pub, "index.html")
    if os.path.exists(_ix):
        _ih = open(_ix, encoding="utf-8", errors="ignore").read()
        _check(_ih.count("/pulse.html") >= 2, fails,
               "K-1 canary: The Board left the nav and the home page does not link it, "
               "so the full Board is now hard to reach")
    return fails


def _flow_sign_canary():
    """K-6: one convention for an exchange flow, on every surface.

    The site used two at once. Tiles printed an unsigned amount with the direction in
    words, "$307.6M net off exchanges", while the by-asset chart, the 13-week trend and
    the exchange table printed signed numbers in which a minus means onto. The same
    movement was a positive number on one surface and a negative one on the next, and
    the morning build's stablecoin tile printed "-$255.4M net stablecoins onto
    exchanges" with the direction hardcoded under a value already saying it with a sign.

    Off exchanges is positive and green; onto exchanges is negative and red; the words
    ride beside the number every time.
    """
    import site_build as _sb4
    import re as _re4
    fails = []

    _amt, _w, _c = _sb4.flow_words(307600000)
    _check(_amt == "+$307.6M" and _w == "off exchanges" and _c == "up", fails,
           f"K-6 canary: money leaving an exchange is not positive and green: "
           f"{(_amt, _w, _c)}")
    _amt, _w, _c = _sb4.flow_words(-229200000)
    _check(_amt == "-$229.2M" and _w == "onto exchanges" and _c == "down", fails,
           f"K-6 canary: money arriving at an exchange is not negative and red: "
           f"{(_amt, _w, _c)}")
    _check(_sb4.flow_words(None) == (None, None, None), fails,
           "K-6 canary: a missing reading produces a number, which is the fake-zero rule")
    _check(_sb4.flow_words(0)[1] == "no net movement", fails,
           "K-6 canary: a true zero does not say so in words")

    # The rows pair each signed amount with the words that match its sign.
    _rows = _sb4._ww_rows({"by_asset": [{"symbol": "BTC", "net_usd": 307600000},
                                        {"symbol": "ETH", "net_usd": -229200000}]})
    _pairs = _re4.findall(r'class="ww-net [a-z]+">([^<]*)</span>'
                          r'<span class="bd-src">([^<]*)', _rows)
    _check(len(_pairs) == 2, fails,
           f"K-6 canary: the by-asset rows did not render both assets: {_pairs}")
    for _a, _wd in _pairs:
        _bad = (_a.startswith("-") and _wd == "off exchanges") or \
               (_a.startswith("+") and _wd == "onto exchanges")
        _check(not _bad, fails,
               f"K-6 canary: {_a} is labelled {_wd!r}, so the sign and the words say "
               f"opposite things about the same movement")

    # And the page says the convention once, at the top.
    _fl = os.path.join(_sb4.PUBLISH, "flows.html")
    if os.path.exists(_fl):
        _h = open(_fl, encoding="utf-8", errors="ignore").read()
        _check("Off exchanges is positive and green" in _h, fails,
               "K-6 canary: the Whale Watch page does not state the sign convention, "
               "so a reader has to infer it from the colours")
    return fails


def _news_lane_canary():
    """K-2: what the front page's news lane is allowed to say is new.

    Two stories from 12 July sat under "Checked stories" on 21 September. The age test
    read "if newest and d and too old: skip", so an item whose date could not be parsed
    failed the `d` clause and was kept: the one kind of item the desk knows least about
    was the one kind the filter could not touch.

    And a card carried "Verified" beside "Developing, single source", which reads as a
    contradiction to a stranger: the desk checking and hedging one sentence in one
    breath. Both facts still matter and both are still said, in one badge.
    """
    import site_build as _sb3
    import re as _re3
    fails = []

    _undated = {"title": "An undated story", "slug": "undated", "verdict": "VERIFIED",
                "published_utc": "", "date": "", "sources": []}
    _fresh = {"title": "A story from today", "slug": "fresh", "verdict": "VERIFIED",
              "published_utc": "2026-09-21T12:00:00Z", "sources": []}
    _html = _sb3._bd_news_cards([_undated, _fresh])
    _check("An undated story" not in _html, fails,
           "K-2 canary: an item with no parseable date reached the news lane, which is "
           "how two 12 July stories sat on the front page in September")

    # K-2 still holds under the 4 October badge law: one badge per card. The three
    # badges themselves are asserted in _three_badges_canary.
    _two = _sb3.verdict_badge("VERIFIED", {"sources": [{"url": "https://cointelegraph.com/x"}]})
    _check(_two.count("<span") == 1, fails,
           f"K-2 canary: a story carries two badges, which reads as the desk checking "
           f"and hedging the same sentence: {_two[:80]}")

    # And the built page carries no two-badge card.
    _idx = os.path.join(_sb3.PUBLISH, "index.html")
    if os.path.exists(_idx):
        _h = open(_idx, encoding="utf-8", errors="ignore").read()
        _pairs = _re3.findall(r'badge verified[^>]*>[^<]*</span>\s*<span class="badge '
                              r'developing', _h)
        _check(not _pairs, fails,
               f"K-2 canary: {len(_pairs)} card(s) on the front page carry two badges")
    return fails


def _one_leverage_canary():
    """K-5: one Leverage number, on the home tile and on the Board.

    The home tile printed the sum of five coins' open interest on OKX, $5.01B, under
    "Leverage". The Board printed Bitcoin's eight-hour funding rate under the same label
    from the same file. A reader clicking from one to the other watched the number halve
    and neither page said which of the two things the word meant.
    """
    import site_build as _sb2
    import json as _j2
    fails = []
    _pf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "site", "data", "pulse.json")
    if not os.path.exists(_pf):
        return fails
    _p = _j2.load(open(_pf, encoding="utf-8"))
    _v, _sub, _btc = _sb2.leverage_figure(_p)
    _check(_v is not None, fails,
           "K-5 canary: the Leverage figure cannot be computed from pulse.json")
    if _v is None:
        return fails
    _check(_v.endswith("%"), fails,
           f"K-5 canary: the Leverage headline is not a rate: {_v!r}")
    _check("per 8h" in (_sub or ""), fails,
           "K-5 canary: the eight-hour figure is not beside the annual one, which is "
           "what K-4's belt requires of every funding number this desk prints")
    _check("on OKX" in (_sub or "") or not (_btc or {}).get("venue"), fails,
           "K-5 canary: the open interest names no venue; one exchange's book is not "
           "the market's")
    # THE FIVE-COIN SUM IS A NUMBER WITH NO NAME and must not be printed as a figure.
    _pub = _sb2.PUBLISH
    _tot = sum((a.get("open_interest_usd") or 0)
               for a in ((_p.get("leverage") or {}).get("assets") or []))
    if _tot:
        _bare = _sb2.fmt_usd(_tot)
        for _pg in ("index.html", "pulse.html"):
            _fp = os.path.join(_pub, _pg)
            if os.path.exists(_fp):
                _check(_bare not in open(_fp, encoding="utf-8", errors="ignore").read(),
                       fails,
                       f"K-5 canary: {_pg} prints {_bare}, the sum of five coins' open "
                       f"interest on one exchange, which is not the market's, not any "
                       f"one asset's, and comparable to nothing else on the page")
    return fails


def _leverage_belt_canary():
    """K-4: the two numbers this desk got wrong in public.

    The read of 19 September said Bitcoin funding stood at "0.96% per eight hours,
    annualized to 10.5%". The feed's figure is 0.0096% per eight hours, which annualizes
    to exactly the 10.5% printed beside it, so the eight-hour number was a hundred times
    too large and refuted the annual one in the same sentence: 0.96 x 1,095 is 1,051%.
    The same read gave open interest with no venue, when the figures are one exchange's
    books and the source's own note says a single-venue snapshot is not a market total.
    """
    import chartmaster as _cm
    fails = []
    lev = {"assets": [{"symbol": "BTC", "venue": "OKX", "funding_8h_pct": 0.0096,
                       "funding_annual_pct": 10.5, "open_interest_usd": 2450000000}]}
    bad = ("Bitcoin funding rates stand at 0.96% per eight hours, annualized to 10.5%. "
           "Open interest remains substantial (Bitcoin 2.45 billion).")
    _p = _cm.leverage_problems(bad, lev)
    # Asserted on the BEHAVIOUR, not the wording. The first version matched the phrase
    # "eight-hour funding rate", so rewriting the belt's message to name the arithmetic
    # it had just done made the canary fail over a sentence the belt was catching
    # correctly. What must hold is that the sentence is rejected and the reason names
    # the eight-hour figure.
    _check(any("0.96" in x for x in _p), fails,
           f"K-4 canary: an eight-hour funding rate a hundred times too large passed "
           f"the belt, which is the sentence that went out on 19 September: {_p}")
    _check(any("open-interest" in x for x in _p), fails,
           "K-4 canary: an open-interest figure with no venue passed the belt")
    # THE FIXTURE PAIR (owner, 22 September). The belt compares the two PRINTED numbers
    # against each other and never against stored data that may be from another hour:
    # the per-interval rate times three intervals a day times 365, within rounding of
    # the annualized figure beside it.
    for _e, _a, _want in (("0.01", "11.0", True),      # 0.01 x 1,095 = 10.95
                          ("0.0021", "2.3", True),     # 0.0021 x 1,095 = 2.30
                          ("0.01", "8", False)):       # 10.95 is not 8
        _t = (f"Bitcoin funds at {_e}% per 8-hour interval on OKX, annualizing to "
              f"{_a}%. Open interest on OKX is 2.45 billion.")
        _p2 = _cm.leverage_problems(_t, lev)
        _check(bool(_p2) != _want, fails,
               f"K-4 canary: {_e}% per eight hours printed as {_a}% annualized should "
               f"{'pass' if _want else 'fail'} and did not: {_p2}")
    good = ("Bitcoin funding on OKX is running at 10.5% annualized. Open interest on "
            "OKX remains substantial (Bitcoin 2.45 billion).")
    _check(_cm.leverage_problems(good, lev) == [], fails,
           f"K-4 canary: the corrected wording is rejected, so the belt is not a rule "
           f"but a wall: {_cm.leverage_problems(good, lev)}")
    # AND THE PUBLISHED READ IS CLEAN. A belt that only guards the next read leaves the
    # wrong number on the site.
    import glob as _g
    import json as _j
    for _f in _g.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "site", "data", "chartmaster*.json")):
        try:
            _d = _j.load(open(_f, encoding="utf-8"))
        except Exception:
            continue
        _t = (_d.get("headline") or "") + " " + " ".join(_d.get("paragraphs") or [])
        # the correction quotes the original wording on purpose; it is not the prose
        _check(not _cm.leverage_problems(_t, lev), fails,
               f"K-4 canary: {os.path.basename(_f)} still carries a funding or "
               f"open-interest figure that breaks the rule")
    return fails


def _us_date_canary():
    """US date order on the desk's own chrome. Owner ruling, 21 September 2026.

    The Board stamped itself "21 Sep 2026" and the Wire's day headers read "SUNDAY 20
    SEPTEMBER". The audience is American and reads month first, so those are "Sep 21,
    2026" and "Sunday, September 20". Both were seen live rather than in review, which
    is why this is a check and not a note.

    CHROME ONLY, and deliberately. A story's own body may quote a source who wrote a
    date the other way round, and rewriting a quotation to match house style is a thing
    this desk has already ruled against once (see destyle). What the desk controls is
    its own furniture, and that is what this reads.
    """
    import os as _os
    import re as _re
    fails = []
    pub = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "site", "publish")
    if not _os.path.isdir(pub):
        return fails
    months = ("January|February|March|April|May|June|July|August|September|October|"
              "November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec")
    rx = _re.compile(r"\b(\d{1,2})\s+(" + months + r")\b")
    tag = _re.compile(r"<[^>]+>")
    for rel in CHROME_PAGES:
        fp = _os.path.join(pub, rel)
        if not _os.path.exists(fp):
            continue
        html = open(fp, encoding="utf-8", errors="ignore").read()
        # Strip <script> and <style> wholesale: a cron line or a JS date format is not
        # reader-facing copy and would report a date nobody sees.
        html = _re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
        # A LISTING PAGE IS NOT ALL FURNITURE. The archive and the front page carry
        # story headlines and summaries, which are the writers' words and may quote a
        # source's own date form. The docstring above says chrome only and this is what
        # makes that true: story blocks and links into /articles/ come out before the
        # scan, so the check reads the desk's furniture and not the desk's journalism.
        html = _re.sub(r"(?is)<article\b.*?</article>", " ", html)
        html = _re.sub(r'(?is)<a[^>]+href="/articles/[^"]*"[^>]*>.*?</a>', " ", html)
        html = _re.sub(r'(?is)<a[^>]+href="/edition/[^"]*"[^>]*>.*?</a>', " ", html)
        text = tag.sub(" ", html)
        for m in rx.finditer(text):
            around = text[max(0, m.start() - 40):m.end() + 20].strip()
            fails.append(f"US date canary: {rel} renders \"{m.group(0)}\" in day-month "
                         f"order; the audience reads month first. Near: "
                         f"{' '.join(around.split())[:90]}")
            break
    return fails


def layer1_canary():
    fails = []
    fails.extend(_us_date_canary())
    fails.extend(_leverage_belt_canary())
    fails.extend(_one_leverage_canary())
    fails.extend(_news_lane_canary())
    fails.extend(_flow_sign_canary())
    fails.extend(_one_story_canary())
    fails.extend(_dark_line_canary())
    fails.extend(_three_badges_canary())
    fails.extend(_whale_sentence_canary())
    fails.extend(_where_is_news_canary())
    fails.extend(_chartmaster_charts_canary())
    fails.extend(_coin_chart_canary())
    fails.extend(_first_screen_canary())
    # FIRST, because it is the cheapest and it catches the class that took two
    # desks down while every other canary here stayed green.
    fails.extend(_undefined_name_canary())
    fails.extend(_one_definition_canary())
    # PORTED FROM THE NEWS DESK 2026-08-29: catches two classes that shipped
    # on every desk and were invisible to every other check here, duplicate
    # slugs (two files silently sharing one URL) and circular or
    # self-referential update_of left behind by a retirement.
    fails.extend(_corpus_integrity_canary())
    fails.extend(_strip_canary())
    fails.extend(_ignore_canary())
    fails.extend(_conflict_canary())   # U-13
    fails.extend(_workflow_canary())   # Cause A of the 29 September audit
    fails.extend(_data_contract_canary())
    fails.extend(_live_layer_canary())
    fails.extend(_stored_series_canary())
    fails.extend(_chartmaster_crash_canary())
    fails.extend(_week_movers_canary())
    fails.extend(_calendar_canary())
    fails.extend(_wire_canary())
    fails.extend(_narrative_canary())
    fails.extend(_stamp_canary())
    cfg = common.load_config()

    # config + models
    for stage in ("editor", "verifier", "writer"):
        mc = cfg["models"].get(stage, {})
        _check(mc.get("model"), fails, f"config: models.{stage}.model missing")
        for bad in ("temperature", "top_p", "top_k"):
            _check(bad not in mc, fails, f"config: models.{stage} sets '{bad}' (rejected by the model API)")
    _check(cfg["publish"]["require_human_approval"] is True, fails,
           "config: publish.require_human_approval must be true (the human gate is load-bearing)")
    _check("REJECT" in cfg["publish"]["never_publish_verdict"], fails,
           "config: REJECT must be in never_publish_verdict")

    # shill rules
    rules = shill_mod.load_rules()
    _check(rules.get("tells"), fails, "shill_rules: no tells")
    for t in rules.get("tells", []):
        for f in ("id", "pattern", "weight", "reason"):
            _check(f in t, fails, f"shill_rules: tell missing '{f}': {t.get('id','?')}")

    # prompts carry their guardrails
    guards = {
        "editor.md": ["shill", "rank", "JSON"],
        "verifier.md": ["VERIFIED", "NEEDS-HUMAN-REVIEW", "REJECT", "adversarial"],
        "researcher.md": ["brief", "confidence", "bear_case", "unconfirmed", "thin"],
        "writer.md": ["DRAFT", "financial advice", "human take", "human_take", "brief",
                      "never pad", "what to watch"],
        "approver.md": ["APPROVE", "REJECT", "accuracy", "balance", "clarity", "compliance",
                        "smuggled"],
        "wrap.md": ["voice of reason", "what to watch", "never what to do", "no em dashes",
                    "todays_stories", "desk_boards"],
    }
    for name, toks in guards.items():
        try:
            text = common.load_prompt(name)
        except Exception as e:
            fails.append(f"prompt {name}: cannot read ({e})")
            continue
        low = text.lower()
        for tk in toks:
            _check(tk.lower() in low, fails, f"prompt {name}: missing guardrail token '{tk}'")

    # shill belt canary: a moon post is rejected; a primary-source item is clean
    moon = {"headline": "PEPECOIN to $10 imminent, get in early", "snippet": "sponsored presale, 100x moon",
            "source": "x", "source_tier": "unknown", "url": "http://x"}
    real = {"headline": "SEC charges Acme Labs over unregistered securities offering", "snippet": "",
            "source": "SEC", "source_tier": "primary", "url": "http://sec"}
    shill_mod.annotate([moon, real], rules)
    _check(moon["shill_rejected"] is True, fails,
           f"shill canary: moon post not rejected (score={moon['shill_score']})")
    _check(real["shill_rejected"] is False and real["shill_score"] == 0, fails,
           f"shill canary: primary-source item wrongly flagged (score={real['shill_score']})")

    # dedupe canary: two near-identical headlines collapse
    import aggregate
    dup = [
        {"headline": "SEC charges Acme Labs over unregistered securities offering",
         "source": "A", "source_tier": "primary", "url": "u1", "timestamp": "", "snippet": ""},
        {"headline": "SEC charges Acme Labs over unregistered securities offering, seeks penalties",
         "source": "B", "source_tier": "major", "url": "u2", "timestamp": "", "snippet": ""},
        {"headline": "Ethereum core developers set date for next network upgrade",
         "source": "C", "source_tier": "major", "url": "u3", "timestamp": "", "snippet": ""},
    ]
    clusters = aggregate.dedupe(dup, cfg)
    _check(len(clusters) == 2, fails, f"dedupe canary: expected 2 clusters, got {len(clusters)}")

    # whale-flow classification canary (offline, deterministic over the sample transactions)
    fails.extend(_whale_flow_canary())
    fails.extend(_window_belt_canary())
    fails.extend(_coin_screen_canary())
    fails.extend(_regwatch_canary())
    fails.extend(_hackwatch_canary())
    fails.extend(_fedreg_canary())
    fails.extend(_dedupe_guard_canary())
    fails.extend(_boundary_canary())
    fails.extend(_front_page_canary())
    fails.extend(_ingest_dedupe_canary())
    fails.extend(_preview_suppression_canary())
    fails.extend(_consistency_gate_canary())
    fails.extend(_merge_state_canary())
    fails.extend(_edition_repair_canary())
    fails.extend(_calendar_duty_canary())

    # full offline replay end-to-end over the fixture
    e2e_fails = _replay_e2e()
    fails.extend(e2e_fails)

    # fail-closed canaries
    fails.extend(_failclosed_canaries(cfg))

    # contract ladder + slot recovery (the 2026-07-15 self-healing layer)
    fails.extend(_contract_ladder_canary(cfg))

    if fails:
        for f in fails:
            gh("error", "canary: " + f)
        print(f"\nLAYER 1 CANARY: FAIL ({len(fails)} problem(s)) -> promotion BLOCKED (exit 1)")
        return 1
    print("LAYER 1 CANARY: PASS -> pipeline wired, shill/dedupe belts work, offline replay "
          "end-to-end produces a DRAFT-tagged review queue, and every fail-closed gate holds.")
    return 0


def _fedreg_canary():
    """Federal rulemaking onto the calendar, offline against fixture documents.

    The desk's regulatory awareness ran entirely off its own published stories via
    regwatch, so it could not know about a rule until someone else wrote about it. This
    closes that, and these cases pin the two things that make it trustworthy."""
    fails = []
    import datetime as _dt
    import fedreg as fr

    doc = {"title": "Permitted Payment Stablecoin Issuer Customer Identification Programs",
           "abstract": "FinCEN is proposing requirements for stablecoin issuers.",
           "publication_date": "2026-06-22", "type": "Proposed Rule",
           "comments_close_on": "2026-08-21", "document_number": "2026-1",
           "agencies": [{"name": "Financial Crimes Enforcement Network"}],
           "html_url": "http://fr/1", "docket_ids": ["FINCEN-2026-0001"]}
    ev = fr.events(docs=[doc], today=_dt.date(2026, 7, 31))
    kinds = {e["kind"] for e in ev}
    _check("proposed rule" in kinds, fails,
           "fedreg: the rule's publication is no longer an event")
    _check("comment deadline" in kinds, fails,
           "fedreg: the comment deadline is no longer an event; that deadline is the "
           "forward-looking thing this module exists to surface")
    dl = next((e for e in ev if e["kind"] == "comment deadline"), None)
    _check(dl and dl["date"] == "2026-08-21", fails,
           "fedreg: the deadline event is not dated on the closing date")
    _check(dl and ["fincen", "stablecoin"] in dl["match"], fails,
           "fedreg: match groups lost the agency+topic pairing, so coverage of the rule "
           "cannot be recognised")

    # a passed deadline is history, not a forthcoming event
    _check(not [e for e in fr.events(docs=[doc], today=_dt.date(2026, 9, 30))
                if e["kind"] == "comment deadline"], fails,
           "fedreg: a closed comment period is still being carried as a deadline")

    # an off-topic rule from a covered agency must not reach the calendar
    off = dict(doc, title="Submarine Cable Landing Licence Rules",
               abstract="Review of licensing procedures.", comments_close_on=None,
               document_number="2026-2")
    _check(fr.events(docs=[off], today=_dt.date(2026, 7, 31)) == [], fails,
           "fedreg: an off-topic rule reached the calendar; the term filter is what keeps "
           "this from burying the real ones")

    # THE QUIET FAILURE. The API returns zero for a quoted OR term the moment a date filter
    # is added, which looks exactly like "no crypto rulemaking" and is undetectable
    # downstream. One query per term is the fix; a single combined term must not come back.
    _check(isinstance(fr.TERMS, (list, tuple)) and len(fr.TERMS) >= 4, fails,
           "fedreg: TERMS collapsed to a combined query; the API silently returns zero for "
           "a quoted OR expression once a date filter is applied, which reads as clean")
    _check(not any(" OR " in t for t in fr.TERMS), fails,
           "fedreg: a term contains an OR expression, which the API drops to zero when "
           "combined with a date filter")

    # the reader-facing Week Ahead must keep running off the CURATED calendar only
    import inspect
    import week_ahead
    _check("fedreg" not in inspect.getsource(week_ahead), fails,
           "fedreg: week_ahead now reads the generated calendar; machine-selected entries "
           "would reach readers in a published story without review")
    return fails

def _hackwatch_canary():
    """The exploit coverage check, offline against a fixture ledger.

    Nobody schedules a hack, so the curated calendar cannot cover this beat and an
    independent ledger is the only way to answer "did we miss one?". Run against the live
    dataset over 30 days this found five uncovered exploits above $1M, including a $21.3M
    one, so the check earns its place; these cases keep it honest.

    The asymmetry matters: a false "uncovered" is a flag someone closes, a false "covered"
    is silence. So coverage requires BOTH the protocol name and exploit language, and the
    story must not predate the hack."""
    fails = []
    import datetime as _dt
    import hackwatch as hw

    today = _dt.date(2026, 7, 30)
    ts = int(_dt.datetime(2026, 7, 29, tzinfo=_dt.timezone.utc).timestamp())
    ledger = [
        {"date": ts, "amount": 21_300_000, "name": "BonkDAO", "technique": "Governance",
         "chain": ["Solana"], "source": "http://x"},
        {"date": ts, "amount": 5_000, "name": "Dustcoin", "technique": "Rug"},
    ]

    def run(stories):
        hw._corpus = lambda within_days=14: stories
        return hw.gaps(days_back=4, today=today, hacks=ledger)

    _check([e["title"] for e in run([])] == ["BonkDAO exploit, $21,300,000"], fails,
           "hackwatch: missed an uncovered exploit, or flagged one below the floor")

    _check(run([("2026-07-29", "bonkdao drained in a governance exploit")]) == [], fails,
           "hackwatch: real coverage was not recognised, which turns the flag into noise")

    _check(len(run([("2026-07-29", "bonkdao announces a new staking program")])) == 1, fails,
           "hackwatch: a story that merely names the protocol counted as exploit coverage; "
           "a false 'covered' is silent and is the failure that matters")

    _check(len(run([("2026-07-28", "bonkdao hit by an exploit")])) == 1, fails,
           "hackwatch: a story published BEFORE the exploit counted as coverage of it")

    _check(hw.gaps(days_back=4, today=_dt.date(2026, 8, 20), hacks=ledger) == [], fails,
           "hackwatch: an exploit outside the window is still being flagged")

    # an unreachable ledger must return None, which main() treats as "no check ran".
    # CAPTURED STDOUT (owner report 2026-08-25): this deliberate OSError("down") made
    # hackwatch print a REAL "hacks ledger unreachable" ::warning:: annotation on every
    # run since 2026-07-31, and the phantom trained the operator to believe the live
    # ledger was down for weeks while the real hackwatch step succeeded minutes later.
    # The assertion is unchanged; only the test's side-channel noise is contained.
    import contextlib as _ctx
    import io as _io
    hw._fetch = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))
    with _ctx.redirect_stdout(_io.StringIO()):
        _hw_ok = hw.gaps(days_back=4, today=today) is None
    _check(_hw_ok, fails,
           "hackwatch: an unreachable source no longer fails open; a check that cannot run "
           "must never look like a clean result")

    _check(hw._name_terms("AFX Bridge") == ["afx bridge", "bridge"] or
           hw._name_terms("AFX Bridge") == ["afx bridge"], fails,
           "hackwatch: name terms changed shape unexpectedly")
    _check("the" not in hw._name_terms("The Pool"), fails,
           "hackwatch: a short leading word became a match term and will match everything")
    return fails

def _regwatch_canary():
    """A tracked storyline must belong to the jurisdiction whose measure it is.

    The tracker paired an unhomed instrument with every country named ANYWHERE in a story,
    so a US Treasury sanctions piece citing Executive Order 13902, which also noted that
    the sanctioned shipping companies were based in China and Hong Kong, filed
    "China :: Executive Order" and "Hong Kong :: Executive Order". Those are not
    imprecise, they are false: neither country issued it.

    Jurisdictions now come from the headline and lede. The canary pins that the rule holds
    AND that it did not over-correct, because a tracker that files nothing is as useless as
    one that files nonsense."""
    fails = []
    import regwatch as rw

    story = {"title": "US Treasury sanctions Iranian firms using Bitcoin for maritime extortion",
             "dek": "OFAC designated two insurers under a US executive order.",
             "key_fact": "Both firms now fall under Executive Order 13902.",
             "body": ["The Treasury also designated eight shipping companies based in "
                      "China, Hong Kong and the Marshall Islands in the same action."]}
    full = rw._story_text(story)
    _, instr, _ = rw.extract(full)
    juris, _, _ = rw.extract(rw.subject_text(story))
    keys = {f"{a} :: {b}" for a, b in rw._pairs(juris, instr)}
    for bogus in ("China :: Executive Order", "Hong Kong :: Executive Order"):
        _check(bogus not in keys, fails,
               f"regwatch: filed {bogus!r}; a country mentioned in the body is not the "
               f"issuer of the measure")
    _check("United States :: Executive Order" in keys, fails,
           "regwatch: the story's actual jurisdiction stopped being filed, which is the "
           "over-correction that makes the tracker useless")

    # a jurisdiction named only in the body is a mention, not a storyline
    only_body = {"title": "Russia's parliament passes crypto market law",
                 "dek": "A transition period runs to 2027.",
                 "key_fact": "Retail investors face an annual cap.",
                 "body": ["EU countermeasures may tighten as reliance on crypto grows."]}
    j2, _, _ = rw.extract(rw.subject_text(only_body))
    _check("Russia" in j2, fails,
           "regwatch: Russia is invisible again; six regulatory headlines named it and the "
           "tracker filed them under the European Union instead")
    _check("European Union" not in j2, fails,
           "regwatch: a body-only mention is being tracked as that jurisdiction's own "
           "storyline")

    # The WIRING, not just the helpers. The first version of this canary tested _pairs and
    # subject_text underneath update(), so a regression that reverted update() to body-wide
    # jurisdictions passed clean. story_pairs is the real filing decision; exercise it.
    keys2 = {f"{a} :: {b}" for a, b in rw.story_pairs(story)[0]}
    _check("United States :: Executive Order" in keys2
           and "China :: Executive Order" not in keys2, fails,
           "regwatch: story_pairs files the wrong jurisdiction; the rule is not wired into "
           "the path update() actually takes")

    # Replay must not touch committed state. wrap.py calls update() on every edition,
    # including the replay this verifier runs, so without the guard a TEST RUN writes the
    # ledger. Sabotage-testing this very canary did exactly that: it wrote five false
    # storylines into regwatch.json that survived restoring the code, because update only
    # ever adds.
    import os as _os
    _before = _os.environ.get("CRYPTO_LLM_MODE")
    try:
        _os.environ["CRYPTO_LLM_MODE"] = "replay"
        _stat = _os.stat(rw.LEDGER).st_mtime_ns if _os.path.exists(rw.LEDGER) else None
        rw.update()
        _after = _os.stat(rw.LEDGER).st_mtime_ns if _os.path.exists(rw.LEDGER) else None
        _check(_stat == _after, fails,
               "regwatch: update() wrote the committed ledger during a replay run; a "
               "verification must never mutate committed state")
    finally:
        if _before is None:
            _os.environ.pop("CRYPTO_LLM_MODE", None)
        else:
            _os.environ["CRYPTO_LLM_MODE"] = _before
    return fails

def _coin_screen_canary():
    """Lock the on-chain supply check, offline.

    The board's whole claim is that a market cap is a price times a supply and that both
    are real. The other supply test compares CoinGecko against CoinGecko, so it can only
    catch a listing that disagrees with itself. This one is the independent read.

    Two properties, and the second matters more than the first. It must catch a cap built
    on more supply than exists; and it must NEVER fire on a multi-chain token, whose
    Ethereum supply is a fraction of its real total. A false positive here silently deletes
    a legitimate coin from the Top 100, which nobody would notice."""
    fails = []
    import coin_screen as cs

    eth_only = {"ethereum": "0xabc0000000000000000000000000000000000001"}
    _check(cs._ethereum_only_contract(eth_only) == eth_only["ethereum"], fails,
           "coin screen: an Ethereum-only token no longer qualifies for the on-chain check")
    for label, platforms in (
            ("multi-chain", {"ethereum": "0xabc", "solana": "So111"}),
            ("non-Ethereum only", {"solana": "So111"}),
            ("no platform at all (a native coin like BTC)", {}),
            ("a blank address", {"ethereum": ""})):
        _check(cs._ethereum_only_contract(platforms) is None, fails,
               f"coin screen: {label} would be checked against an Ethereum supply ceiling, "
               f"which is not its ceiling; that drops legitimate coins")

    # the arithmetic of the verdict itself
    over = 1_000 > 500 * cs.ONCHAIN_MARGIN      # claims twice what exists
    under = 400 > 500 * cs.ONCHAIN_MARGIN       # circulating below total, the normal case
    edge = 505 > 500 * cs.ONCHAIN_MARGIN        # inside the read-timing margin
    _check(over and not under and not edge, fails,
           "coin screen: the on-chain margin no longer separates fabricated supply from "
           "ordinary read timing")
    _check(1.0 < cs.ONCHAIN_MARGIN <= 1.10, fails,
           "coin screen: ONCHAIN_MARGIN left its band; it absorbs seconds of read timing "
           "against a hard ceiling, not a supply disagreement")
    _check("onchain" in cs.REASONS, fails,
           "coin screen: the onchain verdict has no reader-facing reason, so the board "
           "would drop a coin without saying why")
    return fails

def _dedupe_guard_canary():
    """The three-in-one-day failure, pinned as fixtures.

    On 2026-07-30 the desk published one Treasury designation three times. same_event() was
    never the problem: it matched all three pairs. These cases lock the four things that were
    wrong downstream, and the one case that must still get through, because a guard that
    holds everything is just a slower way to publish nothing."""
    fails = []
    import datetime as _dt
    import autopilot as ap
    import dedupe

    # THE FIXTURES BELOW CARRY ABSOLUTE DATES, so the clock they are judged against is pinned
    # beside them. Without this the canary is a time bomb: classify_published builds a 21-day
    # window from the wall clock, the Ostium origin is dated 2026-07-16, and on 2026-08-06 it
    # walked out of that window. The follow-up stopped matching, classified 'new' instead of
    # 'update', this canary's own assertion fired, and because layer 1 is a HARD GATE all
    # three desks stopped publishing for two days. Nothing was wrong with the guard.
    NOW = _dt.datetime(2026, 7, 31, 12, 0, tzinfo=_dt.timezone.utc)

    # CHASSIS SYNC. dedupe.py is one file copied into three repositories, so the only thing
    # keeping them honest is this hash plus the shared fixtures below. Editing the guard in
    # one desk and not the others reds every desk that was not updated.
    _sha = __import__("hashlib").sha256(
        open(dedupe.__file__, "rb").read()).hexdigest()[:16]
    _check(_sha == "49730f35f8d91525", fails,
           f"dedupe: this desk's dedupe.py is {_sha}, the chassis copy is 49730f35f8d91525. "
           f"The guard was changed in one repo and not the others; re-sync all three.")

    # (4) Title Case is not evidence. A headline yields capitalised tokens for ordinary
    # words, so novelty must be read from sentence-cased prose.
    title_sig = dedupe._signature(
        "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of Hormuz Passage")
    _check({"accepting", "insurers", "passage"} <= title_sig, fails,
           "dedupe: this fixture assumed Title Case pollutes _signature and it no longer "
           "does; re-check whether _claim_signature still needs to avoid headlines")
    # The fixture MUST carry a title, or pulling the headline back into the claim signature
    # changes nothing and this assertion tests nothing.
    claim = dedupe._claim_signature(
        {"title": "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of "
                  "Hormuz Passage",
         "key_fact": "HormuzSafe, an Iranian state-linked firm, accepts Bitcoin to collect "
                     "mandatory insurance fees from vessels transiting the Strait of Hormuz."})
    _check(not ({"accepting", "insurers", "passage"} & claim), fails,
           "dedupe: _claim_signature is reading the headline again; a reworded headline will "
           "look like new reporting and the same event will publish twice")

    # (1)(2) A retelling that adds nothing is a rehash, even when the wording differs enough
    # to beat a word-overlap threshold, and even when an older unrelated story also matched.
    pub = {"title": "US Treasury Sanctions Iranian Firms Using Bitcoin for Maritime Extortion",
           "key_fact": "US Treasury sanctioned two Iranian firms accepting Bitcoin to fund "
                       "IRGC operations via a coercive maritime insurance extortion scheme.",
           # Verbatim from the story that actually published at 18:40, not a paraphrase.
           # A shortened body made this fixture pass for the wrong reason on first run:
           # the retelling looked novel only because the excerpt omitted the Strait.
           "body": ["HormuzSafe Marine Services Authority and Persian Gulf Marine Insurance "
                    "Company were designated under Executive Order 13902.",
                    "HormuzSafe advertises itself as offering digital insurance, traffic "
                    "control, security and emergency response to vessels transiting the "
                    "Strait of Hormuz."]}
    retell = {"key_fact": "HormuzSafe, an Iranian state-linked firm, accepts Bitcoin and "
                          "digital assets to collect mandatory insurance fees from vessels "
                          "transiting the Strait of Hormuz, generating revenue for the IRGC."}
    covered = dedupe._covered_signature(pub)
    _check(len(dedupe._claim_signature(retell) - covered - dedupe._OUTLETS)
           < dedupe.NOVELTY_MIN, fails,
           "dedupe: a retelling that adds no new fact scores as novel; this is the shape "
           "that published one Treasury designation three times")

    # the case that MUST still pass: a real development adds a new actor and a new amount
    # Verbatim from the two stories the desk actually published on 2026-07-16. A paraphrase
    # here failed to trip same_event at all, so the follow-up came back "new" and the
    # assertion tested nothing.
    followup = {"key_fact": "The Ostium OLP vault lost approximately $24M USDC via oracle "
                            "manipulation; the exploiter converted stolen stablecoins to "
                            "12,086 ETH total and routed 10,540 ETH through Tornado Cash."}
    origin = {"title": "Ostium Suffers $18 Million Exploit as Oracle Attack Wave Continues "
                       "to Hit DeFi",
              "key_fact": "An attacker drained $18 million in USDC from Ostium's vault by "
                          "submitting oracle reports with future-dated timestamps, exposing "
                          "a critical gap in price-feed validation.",
              "body": ["The attack targeted Ostium's price-feed validation."]}
    _check(len(dedupe._claim_signature(followup) - dedupe._covered_signature(origin)
               - dedupe._OUTLETS) >= dedupe.NOVELTY_MIN, fails,
           "dedupe: a genuine follow-up with a new actor and a new amount is being held as a "
           "rehash; the guard has become a publish-nothing gate")

    # (2) NOVELTY AGAINST ALL PRIOR COVERAGE, exercised end to end against a controlled
    # corpus rather than inspected in source. An earlier version of this check only grepped
    # classify_published for "min(matches" and a revert to the oldest-match rule passed it
    # clean, which is the same weakness that let a canary sit over dead code for two days.
    stale = {"id": "c001", "slug": "iran-strikes",
             "title": "Crypto Little Changed as U.S. Launches Fresh Iran Strikes",
             "date": "2026-07-12",
             "key_fact": "Markets held steady after a reported Strait of Hormuz closure.",
             "body": ["Traders shrugged off the escalation."]}
    first = dict(pub, id="c112", slug="iran-sanctions-first", date="2026-07-30",
                 published_utc="2026-07-30T15:25:01Z")
    corpus = [stale, first]
    verdict, _t, _s = dedupe.classify_published(
        "US Sanctions Iranian Marine Insurers Accepting Bitcoin for Strait of Hormuz Passage",
        retell["key_fact"], corpus=corpus, now=NOW)
    _check(verdict == "rehash", fails,
           f"dedupe: a same-day retelling classified as {verdict!r} with an unrelated older "
           f"story in the corpus; that older story is exactly what made all three Iran "
           f"duplicates look novel on 2026-07-30")

    # and the same corpus must still let a real development through
    verdict2, _t2, _s2 = dedupe.classify_published(
        "Ostium Vault Exploiter Routes 10,540 ETH to Tornado Cash",
        followup["key_fact"], corpus=[dict(origin, id="c900", slug="ostium-origin",
                                           date="2026-07-16",
                                           published_utc="2026-07-16T07:33:18Z")],
        now=NOW)
    _check(verdict2 == "update", fails,
           f"dedupe: a genuine follow-up classified as {verdict2!r}; the guard has become a "
           f"publish-nothing gate")

    # (3) the guard must judge the shipped title
    _check('article_draft' in inspect.getsource(ap.main)
           and '.get("title")' in inspect.getsource(ap.main), fails,
           "dedupe: main() is judging the editor's headline again rather than the writer's "
           "title; the string checked must be the string shipped")
    return fails

def _boundary_canary():
    """The inverted-advisory failure, pinned as fixtures.

    On 2026-07-30 the desk drafted a hardware-wallet firmware advisory twice and the approver
    rejected it twice on accuracy, correctly: the second draft implied users on the PATCHED
    version were the ones at risk. These cases lock the four properties that stop that draft
    ever existing, plus the one case that must still publish, because a gate that holds every
    security story is just a slower way to leave readers uninformed."""
    fails = []
    import boundary as bnd
    import publish as pubmod
    import researcher
    import writer

    # CHASSIS SYNC, same discipline as dedupe.py: one file, three repositories, one hash.
    _sha = __import__("hashlib").sha256(open(bnd.__file__, "rb").read()).hexdigest()[:16]
    _check(_sha == "0cf27e0f447f1031", fails,
           f"boundary: this desk's boundary.py is {_sha}, the chassis copy is 0cf27e0f447f1031. "
           f"The module was changed in one repo and not the others; re-sync all three.")

    # (1) CLASSIFICATION. A firmware advisory with a version in it is boundary-class; a
    # security story with no boundary in it is not, or every story becomes a held story.
    _check(bnd.is_boundary_story(
        "Coldcard Mk4 firmware vulnerability lets an attacker extract the seed",
        "Coinkite patched the flaw in firmware 4.0.1."), fails,
        "boundary: a firmware advisory naming a version is not classified boundary-class; "
        "the fields that stop an inverted range would never be required")
    # Both negatives fire exactly ONE half of the classifier. That is deliberate: an earlier
    # pair fired neither, so relaxing the rule from AND to OR left them passing and the
    # sabotage run went clean. A negative fixture that no plausible break can flip is not a
    # test, and this is the second time on this desk a canary has passed over nothing.
    _check(not bnd.is_boundary_story(
        "Bitcoin falls below $60,000 before the Fed decision",
        "BTC traded down on the day, after a run above $62,000 earlier in the week."), fails,
        "boundary: an ordinary market story is classified boundary-class on its numbers "
        "alone; the gate will hold stories that have no boundary to confirm")
    _check(not bnd.is_boundary_story(
        "Coinkite discloses a firmware flaw and says a patch is coming",
        "The company said an advisory would follow and gave no further detail."), fails,
        "boundary: a security story with no version, date or threshold anywhere in it is "
        "classified boundary-class, so it can never satisfy fields that do not exist for it")

    # (2) VERBATIM, NOT PARAPHRASE. This is the whole point: "4.0.1 and earlier" tidied into
    # "up to 4.0.1" means the same thing to a reader and means the check has stopped running.
    advisory = [{"url": "https://blog.coinkite.com/advisory-2026-07",
                 "source_text": "Affected: Mk4 firmware 4.0.0 and earlier. Fixed in firmware "
                                "4.0.1. Users should update to 4.0.1 immediately."}]
    good = {"affected": "Mk4 firmware 4.0.0 and earlier", "fixed": "firmware 4.0.1",
            "user_action": "update to 4.0.1 immediately",
            "advisory_url": "https://blog.coinkite.com/advisory-2026-07"}
    ok, why = bnd.check_against_sources(good, advisory)
    _check(ok, fails, f"boundary: a block quoted verbatim from the advisory failed the "
                      f"check ({why}); the gate would hold every advisory story")

    tidied = dict(good, affected="versions up to 4.0.0")
    ok2, _ = bnd.check_against_sources(tidied, advisory)
    _check(not ok2, fails,
           "boundary: a paraphrased affected-versions string passed as verbatim; paraphrase "
           "is the exact step that inverted the Coldcard draft")

    inverted = dict(good, affected="Mk4 firmware 4.0.1 and later")
    ok3, _ = bnd.check_against_sources(inverted, advisory)
    _check(not ok3, fails,
           "boundary: an INVERTED range passed the advisory check; this is the published "
           "claim the whole change exists to prevent")

    # (3) SECOND-HAND IS NOT PRIMARY. A field quoted out of a news write-up of the advisory
    # is where the direction flips, so only text fetched from the advisory URL counts.
    ok4, why4 = bnd.check_against_sources(
        good, [{"url": "https://example.test/news-story",
                "source_text": "Affected: Mk4 firmware 4.0.0 and earlier. Fixed in firmware "
                               "4.0.1."}])
    _check(not ok4 and any("primary" in r for r in why4), fails,
           "boundary: the check accepted a news write-up as the advisory; second-hand "
           "sourcing is where a version range gets restated and inverted")

    for f in ("affected", "fixed", "user_action", "advisory_url"):
        ok5, _ = bnd.check_against_sources({k: v for k, v in good.items() if k != f}, advisory)
        _check(not ok5, fails, f"boundary: a block missing {f!r} passed as complete")

    # (4) THE WRITER GETS NO SAY. writer.py COPIES the block; if it ever starts trusting the
    # model's rendering of it, a paraphrase is back in the pipeline.
    art = {"title": "T", "body": "b", "boundary": {"affected": "WHATEVER THE MODEL SAID",
                                                   "fixed": "x", "user_action": "y",
                                                   "advisory_url": "z"}}
    writer._carry_boundary(art, {"brief": {"boundary": good, "boundary_required": True,
                                           "boundary_ok": True}})
    _check(art.get("boundary") == good, fails,
           "boundary: writer._carry_boundary did not overwrite the model's block with the "
           "brief's; the writer is restating the version range again")
    _check("_carry_boundary" in inspect.getsource(writer.validate), fails,
           "boundary: writer.validate no longer calls _carry_boundary, so nothing copies the "
           "fields and the draft carries whatever the model wrote")

    # (5) THE GATE IS FAIL-CLOSED AND READS THE DRAFT. An unconfirmed boundary holds, with no
    # retry path: retrying cannot make a vendor advisory fetchable.
    # Built fresh, NOT from art: _carry_boundary stamped boundary_ok=True onto art above, so
    # reusing it made the never-checked case inherit that True and pass for the wrong reason.
    # The absent-key case is the one that matters most here, so it has to be genuinely absent.
    base = {"title": "T", "body": "b", "boundary": dict(good)}
    _check(pubmod.boundary_block({"article_draft": dict(base, boundary_required=True,
                                                        boundary_ok=True)}) == "", fails,
           "boundary: publish is holding a story whose boundary IS confirmed")
    for bad in ({"boundary_required": True, "boundary_ok": False},
                {"boundary_required": True, "boundary_ok": None},
                {"boundary_required": True}):
        _check(pubmod.boundary_block({"article_draft": dict(base, **bad)}) != "", fails,
               f"boundary: publish let a boundary-class story through with {bad}; an "
               f"unconfirmed who-is-affected claim reached a reader")
    _check(pubmod.boundary_block({"article_draft": {"boundary_required": True,
                                                    "boundary_ok": True}}) != "", fails,
           "boundary: publish let through a story marked confirmed that carries no block to "
           "render; the panel would be absent and the prose says nothing about it, by design")
    _check(pubmod.boundary_block({"article_draft": {"title": "ordinary story"}}) == "", fails,
           "boundary: publish is holding an ordinary story that has no boundary at all")
    _check("boundary_block(" in inspect.getsource(pubmod.run), fails,
           "boundary: publish.run no longer calls boundary_block; the gate is unreachable "
           "and this canary is testing dead code")

    # (6) THE RESEARCHER STAMPS BOTH DIRECTIONS. A missing key and a negative answer look
    # identical downstream, and only one of them means the check ran.
    brief = {"id": "c011", "core_claim": "Coinkite patched a firmware flaw in 4.0.1."}
    researcher._stamp_boundary(brief, {"headline": "Coldcard firmware vulnerability lets an "
                                                   "attacker extract the seed",
                                       "source_texts": advisory})
    _check(brief.get("boundary_required") is True and brief.get("boundary_ok") is False, fails,
           f"boundary: a boundary-class brief with no block was stamped "
           f"required={brief.get('boundary_required')!r} ok={brief.get('boundary_ok')!r}; "
           f"the publish gate reads these and would let it through")
    plain = {"id": "c020", "core_claim": "Bitcoin traded near flat."}
    researcher._stamp_boundary(plain, {"headline": "Bitcoin holds steady", "source_texts": []})
    _check(plain.get("boundary_required") is False, fails,
           "boundary: an ordinary story was stamped boundary_required; every story would "
           "need a vendor advisory to publish")
    _check("_stamp_boundary" in inspect.getsource(researcher.validate), fails,
           "boundary: researcher.validate no longer calls _stamp_boundary, so no brief is "
           "ever classified and the gate never fires")

    # (7) RENDERING. Nothing is composed into a sentence, and an incomplete block renders
    # nothing at all rather than a panel with a blank row where the fix version goes.
    _check([lab for lab, _ in bnd.rows(good)] == ["Affected", "Fixed in", "What to do",
                                                  "Advisory"], fails,
           "boundary: the rendered panel changed shape; a reader scanning for the fix version "
           "should find it in the same place on every advisory story")
    _check(bnd.rows({"affected": "x"}) == [], fails,
           "boundary: an incomplete block still renders; a panel missing the fixed version "
           "answers the question wrong by omission")
    return fails


def _preview_suppression_canary():
    """A preview must never suppress coverage of the thing it previewed.

    This is the bug that cost the desk the FOMC decision on 2026-07-29. The Week Ahead
    published two days earlier listed "Wednesday, July 29: FOMC rate decision", and
    already_published() scanned it like any other story. When the Fed actually decided, the
    real story was ranked #1, VERIFIED against federalreserve.gov and APPROVED, then held
    as already-published. Every event the Week Ahead flags was pre-suppressed for the next
    five days, so the better the preview, the worse the blackout.

    The two assertions have to hold together: previews and editions must not suppress, and
    real coverage still must. Fixing the first by weakening the second would just trade a
    missed story for a duplicate."""
    fails = []
    import autopilot as ap

    # REACHABILITY FIRST. The previous version of this canary tested is_coverage() and
    # already_published() directly, and BOTH were dead: nothing in production called them, so
    # the FOMC preview fix passed its canary for two days without ever executing. Assert the
    # filter runs inside the gate that actually decides, and that the gate is the one
    # main() calls.
    import inspect
    import dedupe
    _gate_src = inspect.getsource(dedupe.classify_published)
    _check("is_coverage(" in _gate_src, fails,
           "preview suppression: classify_published no longer filters with is_coverage, so "
           "previews and editions can suppress or anchor a real story again")
    _check("classify_published(" in inspect.getsource(ap.main), fails,
           "preview suppression: main() no longer calls classify_published; the guard being "
           "asserted here is not the guard that runs")

    for label, doc in (
            ("a Week Ahead preview (by id)", {"id": "week-ahead-2026-07-27"}),
            ("a Week Ahead preview (by category)",
             {"id": "x", "category": "Week Ahead"}),
            ("a daily edition", {"id": "wrap-am-2026-07-30"})):
        _check(not ap.is_coverage(doc), fails,
               f"preview suppression: {label} counts as coverage and can suppress a "
               f"real story about the same event")
    _check(ap.is_coverage({"id": "c150", "category": "policy"}), fails,
           "preview suppression: a normal story stopped counting as coverage, which "
           "disables duplicate suppression entirely")

    # the fingerprint itself must still see the two as the same event; the fix is the
    # exclusion, not a weaker matcher
    # Verbatim from the 2026-07-27 Week Ahead and the story it suppressed. A paraphrase
    # here does NOT match, which this canary caught on its first run: shortened, the pair
    # fails same_event and the whole check would have passed for the wrong reason.
    _check(ap.same_event(
        "Federal Reserve issues FOMC statement",
        "The Federal Open Market Committee held rates steady in a 9-3 vote.",
        "The Week Ahead: FOMC rate decision; Coinbase second-quarter results; "
        "Strategy second-quarter results",
        "Wednesday, July 29: FOMC rate decision. The Federal Open Market Committee meets "
        "Tuesday and Wednesday; the rate decision lands Wednesday at 2:00 p.m. Eastern "
        "with a press conference at 2:30."), fails,
        "preview suppression: same_event no longer matches the preview to the event, so "
        "this canary would pass for the wrong reason")

    # The post-approval hold annotation. Formatting only, but the three call sites feed it
    # and a silent regression here re-hides exactly what the FOMC miss needed surfaced.
    notes = ap.held_after_approval_notes([
        {"headline": "Federal Reserve issues FOMC statement",
         "gate": "near-duplicate of a published story",
         "matched": "The Week Ahead: FOMC rate decision"},
        {"headline": "X", "gate": "figure conflicts with a published story", "matched": ""}])
    _check(len(notes) == 2 and "VERIFIED and APPROVED, then held" in notes[0]
           and "The Week Ahead" in notes[0], fails,
           "held-after-approval: the annotation stopped naming the story or the gate")
    _check(ap.held_after_approval_notes([]) == [] and ap.held_after_approval_notes(None) == [],
           fails, "held-after-approval: an empty run no longer annotates nothing")
    return fails



def _ingest_dedupe_canary():
    """The ingest backstop, and the corroboration the editor used to drop.

    Two Tether earnings stories published thirteen minutes apart on 2026-07-31 carrying the
    SAME cluster id, which is only possible across two overlapping runs: the first had not
    pushed when the second checked out, so autopilot's guard read a corpus that did not
    contain it. The publish-time gate cannot see a sibling that does not exist on its disk
    yet, so the last gate has to sit where content actually lands."""
    fails = []
    import site_build as sb
    import dedupe

    a = {"slug": "tether-a", "title": "Tether posts $1.5 billion operating profit in Q2 as "
         "reserve buffer falls by half", "date": "2026-07-31",
         "published_utc": "2026-07-31T18:41:06Z",
         "key_fact": "Tether's operating profit fell 69% year-over-year while its reserve "
         "buffer halved in a single quarter, even as USDT issuance grew by $446 million.",
         "sources": [{"url": "https://www.coindesk.com/business/2026/07/31/t"}],
         # VERBATIM body of the story that actually published at 18:41. Stripping it made
         # this fixture fail on the first run: _covered_signature reads title, key fact AND
         # body, so a prior story with no body "covers" almost nothing and its duplicate
         # looks novel. A fixture must not be thinner than the story it stands in for.
         "body": ["Tether reported $1.5 billion in net operating profit for Q2 2026, down 69% from $4.9 billion in the year-ago quarter, per CoinDesk. The stablecoin issuer's reserve buffer, the cushion between assets and liabilities, fell to $4.11 billion as of June 30, 2026, compared with $8.23 billion three months earlier, according to CoinDesk.", "Tether held $187.75 billion in assets against $183.64 billion in liabilities as of June 30, 2026, per a BDO attestation cited by CoinDesk. USDT issuance increased by about $446 million to $184.6 billion during Q2 2026, according to CoinDesk's reporting.", "The company increased physical gold holdings by 14 metric tons to roughly 146.2 metric tons during Q2 2026, up from 132.2 metric tons at the start of the quarter, per CoinDesk. Despite the increase in physical units, the value of those holdings fell to $18.84 billion from $19.84 billion during the quarter because the gold price dropped about 15% to just over $4,000 per ounce, according to CoinDesk."]}
    b = {"slug": "tether-b", "title": "Tether Q2 Profit Falls 69% as Reserve Buffer Halves "
         "to $4.1 Billion", "date": "2026-07-31", "published_utc": "2026-07-31T18:54:03Z",
         "key_fact": "Excess reserves fell by half in a single quarter to $4.11 billion, "
         "even as USDT issuance grew by $446 million to $184.6 billion.",
         "sources": [{"url": "https://www.coindesk.com/business/2026/07/31/t"}]}
    unrelated = {"slug": "kalshi", "title": "New York sues Kalshi, alleges it operates an "
                 "unlicensed gambling business", "date": "2026-07-31",
                 "published_utc": "2026-07-31T12:31:34Z",
                 "key_fact": "The New York attorney general sued Kalshi over sports event "
                 "contracts, alleging unlicensed gambling."}

    import json as _j, os as _o, tempfile as _t
    d = _t.mkdtemp()
    _j.dump(a, open(_o.path.join(d, "a.json"), "w"))
    _j.dump(unrelated, open(_o.path.join(d, "u.json"), "w"))

    path, prior, _mode = sb.same_event_on_disk(b, content=d)
    _check(bool(path) and prior.get("slug") == "tether-a", fails,
           "ingest-dedupe: the second Tether earnings story is not caught against the first; "
           "this is the pair that published thirteen minutes apart across two runs")

    # merging the wrong pair is worse than missing one: a hold loses a duplicate, a bad merge
    # loses a real story. same_event alone matched Kalshi to Tether in testing.
    far = dict(b, slug="tether-c", published_utc="2026-08-03T18:54:03Z", date="2026-08-03")
    _check(not sb.same_event_on_disk(far, content=d)[0], fails,
           "ingest-dedupe: the same event three days later still merges; the 24h window is "
           "not being applied and unrelated later coverage will be folded into old stories")
    # against a corpus holding ONLY the Tether story, so this asks the real question. Run
    # against a corpus that also held Kalshi, it matched Kalshi to itself, which is correct
    # behaviour and a useless assertion.
    d2 = _t.mkdtemp()
    _j.dump(a, open(_o.path.join(d2, "a.json"), "w"))

    # THE CASE THE NOVELTY TEST EXISTS FOR, and the one the first version of this canary
    # could not see: a genuine follow-up that same_event DOES match. Dropping the novelty
    # test passed the sabotage run clean, because every other fixture here fails same_event
    # anyway. Merging this pair would silently delete real reporting, which is the one
    # outcome worse than a duplicate. Verbatim from the two Ostium stories the desk published.
    origin = {"slug": "ostium-origin", "date": "2026-07-16",
              "published_utc": "2026-07-16T07:33:18Z",
              "title": "Ostium Suffers $18 Million Exploit as Oracle Attack Wave Continues "
                       "to Hit DeFi",
              "key_fact": "An attacker drained $18 million in USDC from Ostium's vault by "
                          "submitting oracle reports with future-dated timestamps, exposing "
                          "a critical gap in price-feed validation.",
              "body": ["The attack targeted Ostium's price-feed validation."]}
    followup = {"slug": "ostium-followup", "date": "2026-07-16",
                "published_utc": "2026-07-16T19:20:00Z",
                "title": "Ostium Vault Exploiter Routes 10,540 ETH to Tornado Cash",
                "key_fact": "The Ostium OLP vault lost approximately $24M USDC via oracle "
                            "manipulation; the exploiter converted stolen stablecoins to "
                            "12,086 ETH total and routed 10,540 ETH through Tornado Cash."}
    d3 = _t.mkdtemp()
    _j.dump(origin, open(_o.path.join(d3, "o.json"), "w"))
    _check(dedupe.same_event(origin["title"], origin["key_fact"],
                             followup["title"], followup["key_fact"]), fails,
           "ingest-dedupe: this fixture no longer trips same_event, so it cannot test whether "
           "the novelty gate protects a real development; replace it with a pair that does")
    _check(not sb.same_event_on_disk(followup, content=d3)[0], fails,
           "ingest-dedupe: a genuine follow-up (new actor, new amount, Tornado Cash) is being "
           "merged into the original exploit story. Merging away real reporting is worse than "
           "publishing a duplicate: the duplicate is visible and this is not")
    _check(not sb.same_event_on_disk(unrelated, content=d2)[0], fails,
           "ingest-dedupe: an unrelated story merges into an existing one; the novelty test "
           "that separates a duplicate from a different story is not running")
    _check(not sb.same_event_on_disk(dict(b, id="wrap-x"), content=d)[0], fails,
           "ingest-dedupe: an edition is being treated as a duplicate of the stories it "
           "summarises, which is what an edition is for")

    # the merge keeps the published URL and loses no sourcing
    import copy as _c
    tgt = _o.path.join(d, "a.json")
    before = _j.load(open(tgt))
    merged_in = dict(b, sources=[{"url": "https://example.test/second-outlet"}])
    sb.merge_into_existing(tgt, _c.deepcopy(before), merged_in)
    after = _j.load(open(tgt))
    _check(after.get("slug") == before.get("slug") and after.get("title") == before.get("title"),
           fails, "ingest-dedupe: the merge changed the published story's slug or title; the "
                  "existing URL may already be indexed and linked")
    _check(len(after.get("sources") or []) == 2, fails,
           "ingest-dedupe: the duplicate's sourcing was dropped rather than folded in; the "
           "one thing a second copy reliably adds is another outlet")
    _check(after.get("merged_from"), fails,
           "ingest-dedupe: the merge left no record of what was folded in")

    # THE CORROBORATION THE EDITOR DROPPED: 76% of stories carried one source while their
    # clusters averaged 17 corroborating outlets.
    import editor
    obj = {"ranked": [{"id": "c1", "headline": "h", "why_it_matters": "w", "source_urls": []}]}
    items = {"clusters": [{"id": "c1", "url": "https://primary.test/a", "source": "Primary",
                           "corroboration": [{"name": "Outlet B", "url": "https://b.test/x"},
                                             {"name": "Outlet C", "url": "https://c.test/y"}]}]}
    editor.attach_corroboration(obj, items)
    r = obj["ranked"][0]
    _check(len(r.get("source_urls") or []) == 3 and r.get("source_count") == 3, fails,
           f"editor: corroborating outlets are not being carried onto the ranked story "
           f"(got {r.get('source_urls')}); the desk gathers them and then publishes one source")
    _check("Outlet B" in (r.get("source_outlets") or []), fails,
           "editor: corroborating outlet NAMES are not carried, so no later stage can say "
           "who corroborated without re-deriving it from a URL")
    _check("attach_corroboration(" in inspect.getsource(editor.run), fails,
           "editor: attach_corroboration is no longer called from run(), so source_urls is "
           "back to whatever the model chose to echo")

    # ...AND THE HOP AFTER IT. The editor fix alone changed nothing on the page: the first
    # live run after it still shipped three stories at one source each, because the writer
    # model writes its own sources list and that is what publishes. The corroborating
    # outlets must ride the draft as a field the model never touches.
    import writer as writer_mod
    wobj = {"drafts": [{"id": "c1",
                        "article_draft": {"title": "t", "body": "b", "bottom_line": "x",
                                          "sources": ["https://primary.test/a"],
                                          "also_reported_by": ["MODEL SAID SO"]},
                        "script_skeleton": {"headline": "t", "summary": "s",
                                            "key_fact": "k", "sources": []}}]}
    wstories = [{"id": "c1", "headline": "t", "why_it_matters": "w",
                 "source_outlets": ["Primary", "Outlet B", "Outlet C"]}]
    writer_mod.validate(wobj, wstories)
    got = wobj["drafts"][0]["article_draft"].get("also_reported_by")
    _check(got == ["Outlet B", "Outlet C"], fails,
           f"writer: also_reported_by is {got!r}, not the corroborating outlets copied from "
           f"the editor (primary excluded, model overridden); the outlet list is shrinking "
           f"at a model hop again")
    # the assertion names the READ SIDE of the assignment, because a sabotage that kept the
    # key but assigned [] still contained the bare string and passed the first version.
    _check('art.get("also_reported_by")' in inspect.getsource(sb.ingest), fails,
           "site_build: ingest no longer reads also_reported_by off the draft, so the "
           "writer's copy dies one hop before the page")
    _check('also-reported' in inspect.getsource(sb.render_article), fails,
           "site_build: the article page no longer renders the also-reported line; the "
           "corroboration is carried all the way to the page and then not shown")
    # corroborated is not "developing": the badge discloses a story resting on ONE outlet
    _check(sb.verdict_badge("VERIFIED", {"sources": [{"url": "https://coindesk.com/a"}],
                                          "also_reported_by": ["The Block"]})
           == '<span class="badge verified">Verified</span>',
           fails, "site_build: a story corroborated by also_reported_by is not plain Verified")
    return fails

def _front_page_canary():
    """Two front-page defects found in the 2026-07-31 review, pinned so they cannot return.

    Both were the same kind of bug: a rule that looked like it governed something and did
    not. Neither failed a build, neither showed up in a link check, and both were visible to
    any reader who opened the homepage."""
    fails = []
    import datetime as _d
    import site_build as sb

    # (1) THE BOTTOM LINE HAD NO STALENESS RULE AT ALL. On 2026-07-31 the hero still carried
    # the July 28 Evening Brief, telling readers to watch an FOMC decision that had happened
    # two days before the build.
    def _it(slug, wrap, hours_old, bl=None):
        when = (_d.datetime(2026, 7, 31, 12, tzinfo=_d.timezone.utc)
                - _d.timedelta(hours=hours_old))
        out = {"slug": slug, "id": ("wrap-" + slug if wrap else "c1"), "kind": "brief",
               "title": "The Evening Brief: the day in crypto",
               "date": when.strftime("%Y-%m-%d"),
               "published_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if bl:
            out["bottom_line"] = bl
        return out

    for label, items, want in (
        ("a fresh edition", [_it("w", 1, 0, "read")], True),
        ("an edition 3h old with a story since", [_it("s", 0, 0), _it("w", 1, 3, "read")], True),
        # the exact 2026-07-31 shape: an old edition with newer reporting on the site
        ("a 25h-old edition with a story since", [_it("s", 0, 0), _it("w", 1, 25, "read")], False),
        # the desk going quiet is NOT staleness: nothing newer exists to contradict the read
        ("a 72h-old edition with nothing since", [_it("w", 1, 72, "read")], True),
    ):
        got = sb.current_bottom_line(items) is not None
        _check(got == want, fails,
               f"front page: {label} is {'shown' if got else 'retired'} and should be "
               f"{'shown' if want else 'retired'}; the Bottom Line staleness rule changed")
    _check("current_bottom_line(" in inspect.getsource(sb.render_home)
           and "current_bottom_line(" in inspect.getsource(sb.bottom_line_card), fails,
           "front page: a Bottom Line surface stopped going through current_bottom_line and "
           "is taking wraps[0] unconditionally again, which is how the July 28 brief held the "
           "hero on a July 31 build")

    # (2) TAG COLLAPSE. "regulation" was declared first with the broadest pattern in the file
    # and _hero_tag shows tags[0], so 111 of 156 published stories rendered "regulation".
    _check(sb.tags_for({"title": "Company reports record corporate treasury operations",
                        "dek": "", "key_fact": ""}) != ["regulation"], fails,
           "front page: 'regulation' matches corporate treasury again; that one word is much "
           "of how the tag reached 71% of the site")
    litig = sb.tags_for({"title": "Judge dismisses class action lawsuit against the exchange",
                         "dek": "", "key_fact": ""})
    # ORDER IS THE MECHANISM, so it needs a fixture that can see it. The litigation case
    # below cannot: "regulation" no longer matches a lawsuit at all, so moving it back to the
    # top of TAG_RULES left that assertion green and the sabotage run went clean. This story
    # matches legal AND regulation AND exchanges, so only the ordering decides what shows.
    both = sb.tags_for({"title": "SEC sues Coinbase over its unregistered exchange",
                        "dek": "", "key_fact": ""})
    _check(both and both[0] == "legal", fails,
           f"front page: a story matching legal, regulation and exchanges displays "
           f"{(both or [None])[0]!r}; TAG_RULES is ordered most-specific-first and _hero_tag "
           f"shows tags[0], so that ordering is the entire mechanism")
    _check(litig and litig[0] == "legal", fails,
           f"front page: a litigation story tags {litig} rather than leading with 'legal'; "
           f"the legal bucket exists because litigation is not rulemaking")
    # A tag claims what the story IS about, so it never reads the body: a 600-word body
    # mentions enough to match most of the rules in the list.
    _check(not sb.tags_for({"title": "Quiet day on the desk", "dek": "", "key_fact": "",
                            "body": ["The SEC, the CFTC and Congress were all mentioned here, "
                                     "alongside an exploit, a stablecoin and an ETF."]}), fails,
           "front page: tags_for is reading the body again; that is how one story came to "
           "match nearly every rule in the list")
    # ...and the live corpus must stay spread. Deliberately loose: this fires on collapse,
    # not on a news cycle that happens to run heavy on one topic for a week.
    try:
        items = [i for i in sb.load_content() if not i.get("example")]
    except Exception:
        items = []
    if len(items) >= 40:
        lead = {}
        for i in items:
            t = sb.tags_for(i)
            if t:
                lead[t[0]] = lead.get(t[0], 0) + 1
        top, n = max(lead.items(), key=lambda kv: kv[1]) if lead else ("", 0)
        _check(n / len(items) <= 0.40, fails,
               f"front page: {n/len(items):.0%} of published stories display {top!r}; the "
               f"taxonomy has collapsed to one chip again (it was 71% 'regulation')")
        untagged = sum(1 for i in items if not sb.tags_for(i))
        _check(untagged / len(items) <= 0.15, fails,
               f"front page: {untagged}/{len(items)} published stories carry no tag at all; "
               f"narrowing the rules has left a hole rather than a taxonomy")
    return fails


def _calendar_duty_canary():
    """The calendar duty is a MANDATE, not advice (2026-08-02: the FOMC decision died at
    the approver three runs straight and Strategy Q2 never entered intake, while the
    Week Ahead had promised readers both). This pins the enforcement semantics: a due
    event with no decision fails, a cover naming an unranked cluster fails, an empty
    pass reason fails, and a stated pass or a real cover passes."""
    import editor as ed
    import llm as llmlib
    fails = []
    duties = [{"title": "FOMC rate decision", "kind": "macro", "date": "2026-07-29",
               "match": [["fomc"]], "_cluster_ids": ["c1"]}]
    ranked = {"ranked": [{"id": "c1", "headline": "Fed holds", "why_it_matters": "x"}],
              "rejected": []}

    def dies(obj, label):
        try:
            ed.enforce_duties(obj, duties)
            fails.append(f"calendar duty: {label} was NOT caught")
        except llmlib.LLMError:
            pass

    def lives(obj, label):
        try:
            ed.enforce_duties(obj, duties)
        except llmlib.LLMError as e:
            fails.append(f"calendar duty: {label} wrongly rejected ({e})")

    dies(dict(ranked), "a due event with no decision at all")
    dies(dict(ranked, calendar_decisions=[{"title": "FOMC rate decision",
                                           "decision": "cover", "cluster_id": "c9"}]),
         "a cover naming an unranked cluster")
    dies(dict(ranked, calendar_decisions=[{"title": "FOMC rate decision",
                                           "decision": "pass", "reason": "  "}]),
         "a pass with an empty reason")
    dies(dict(ranked, calendar_decisions=[{"title": "FOMC rate decision",
                                           "decision": "maybe"}]),
         "a decision that is neither cover nor pass")
    lives(dict(ranked, calendar_decisions=[{"title": "FOMC rate decision",
                                            "decision": "cover", "cluster_id": "c1"}]),
          "a real cover")
    lives(dict(ranked, calendar_decisions=[{"title": "FOMC rate decision",
                                            "decision": "pass",
                                            "reason": "held for the minutes"}]),
          "a stated pass")
    # the synthetic-intake path: an event no feed carried still becomes decidable
    items = {"clusters": []}
    ev = [{"title": "Strategy second-quarter results", "kind": "earnings",
           "date": "2026-07-30", "match": [["strategy", "earnings"]],
           "source": "https://example.com/ir", "source_name": "Strategy IR",
           "detail": "Q2 results"}]
    ed.ensure_duty_clusters(items, ev)
    if not items["clusters"] or not ev[0].get("_cluster_ids"):
        fails.append("calendar duty: unclustered event did not get synthetic intake")
    else:
        c = items["clusters"][0]
        missing = [k for k in ("id", "headline", "source", "source_tier", "url",
                               "timestamp", "snippet", "corroboration", "shill_score",
                               "shill_flags", "shill_rejected") if k not in c]
        if missing:
            fails.append(f"calendar duty: synthetic cluster missing fields {missing}")
    if not fails:
        print("calendar-duty canary: mandate enforced (no silent decision, no fake "
              "cover, no empty pass), synthetic intake complete.")
    return fails


def _edition_repair_canary():
    """The edition floor (family audit 2026-09-02): sentence-grain cuts of what the
    trace checker flagged, belt repairs at the same grain, and the digest built only
    from published stories. Each must refuse when it would damage the product."""
    import edition_repair as er
    import wrap as wrapmod
    fails = []
    body = ("The first paragraph carries a real fact from the inputs. It also carries "
            "an invented figure of 412 goals that no input supports. A third sentence "
            "closes the paragraph honestly.\n\n"
            + "The second paragraph is long enough to keep the body over the floor once a "
              "sentence is cut, so the repair is legal rather than refused. " * 6)
    obj = {"hook_title": "A day of results and one invented number", "dek": "A dek.",
           "key_takeaway": "k", "body": body,
           "bottom_line": "The theme was results. The checkpoints are Friday's slate."}
    new, cuts = er.excise_claims(
        obj, ["It also carries an invented figure of 412 goals that no input supports."])
    _check(new is not None and cuts == 1 and "412 goals" not in new["body"], fails,
           "edition repair: a flagged sentence was not cut cleanly")
    _check(er.excise_claims(obj, ["a claim that appears nowhere in this edition"])[0] is None,
           fails, "edition repair: an unlocatable claim must refuse the cut")
    _check(er.excise_claims(obj, ["The theme was results.",
                                  "The checkpoints are Friday's slate."])[0] is None,
           fails, "edition repair: hollowing out The Bottom Line must refuse")
    short = dict(obj, body="One short paragraph with the invented figure of 412 goals. Two.")
    _check(er.excise_claims(short, ["invented figure of 412 goals"])[0] is None, fails,
           "edition repair: a cut that leaves the body under the floor must refuse")

    def belts(o):
        return wrapmod.belts(str(o.get("body", "")), str(o.get("dek", "")),
                                     str(o.get("bottom_line", "")), None)
    dirty = dict(obj, bottom_line=obj["bottom_line"] + " The favorite is poised to rally.")
    _check(belts(dirty), fails, "edition repair: the lane belt did not fire on the fixture")
    fixed, _ = er.belt_repair(dirty, belts, er.sentence_probe(belts))
    _check(fixed is not None and not belts(fixed) and "poised" not in fixed["bottom_line"],
           fails, "edition repair: a lane violation was not cut at sentence grain")

    stories = [{"title": f"Story {i} headline", "summary": "A verified summary sentence. "
                "Another sentence with a number, 12.", "key_fact": f"Key fact {i}.",
                "first_paragraphs": ["First paragraph of the story, verified and published."],
                "bottom_line": "The next checkpoint is the filing deadline on September 9.",
                "date": "2026-09-0" + str(1 + i % 2), "url": f"/articles/s{i}.html"}
               for i in range(6)]
    dg = er.digest_edition(stories, belts, wrapmod.bottom_line_lint)
    _check(dg is not None and dg.get("digest") is True and not belts(dg)
           and er.word_count(dg["body"]) >= er.MIN_BODY_WORDS, fails,
           "edition repair: the digest floor did not build a belts-clean edition")
    _check(er.digest_edition([], belts, wrapmod.bottom_line_lint) is None, fails,
           "edition repair: a digest with no stories must be None")
    return fails


def _merge_state_canary():
    """Lock the resolution rules for the files two overlapping publishes always collide on.

    The brief's retry rebases when main moves mid-run. site/content/ is additive and never
    conflicts, but editorial-log.json, regwatch.json and chartmaster.json are rewritten by
    every run, so overlapping runs always conflict there and the run died. These assertions
    pin what each merge must preserve, because getting editorial-log wrong silently deletes
    another run's editorial record and nothing would notice."""
    fails = []
    import merge_state as ms

    up = [{"date": "2026-07-29", "approved": 3, "rejected": [{"id": "other"}]}]
    mine = [{"date": "2026-07-29", "approved": 5, "rejected": [{"id": "mine"}]}]
    got = ms.merge_editorial_log(up, mine)
    ids = [r["id"] for e in got for r in e.get("rejected", [])]
    _check("other" in ids and "mine" in ids, fails,
           "merge_state: editorial-log merge dropped a run's record")
    _check(ms.merge_editorial_log(up, up) == up, fails,
           "merge_state: editorial-log merge duplicated an identical record")

    up_r = {"US :: A": {"dates": ["Jul 29"], "first_seen": "2026-07-01",
                        "last_seen": "2026-07-29"}}
    my_r = {"US :: A": {"dates": ["Jul 15"], "first_seen": "2026-07-01",
                        "last_seen": "2026-07-15"},
            "UK :: B": {"dates": ["Jul 28"], "first_seen": "2026-07-28",
                        "last_seen": "2026-07-28"}}
    got_r = ms.merge_regwatch(up_r, my_r)
    _check("UK :: B" in got_r, fails, "merge_state: regwatch merge dropped a measure")
    _check(got_r["US :: A"]["last_seen"] == "2026-07-29", fails,
           "merge_state: regwatch merge kept the older sighting")
    _check(set(got_r["US :: A"]["dates"]) == {"Jul 29", "Jul 15"}, fails,
           "merge_state: regwatch merge lost sighting dates")

    # snapshot, not a record: later date wins, tie goes to upstream (see merge_state)
    _check(ms.merge_chartmaster({"date": "2026-07-29", "headline": "up"},
                                {"date": "2026-07-29", "headline": "mine"})["headline"] == "up",
           fails, "merge_state: chartmaster tie did not go to upstream")
    _check(ms.merge_chartmaster({"date": "2026-07-28", "headline": "up"},
                                {"date": "2026-07-29", "headline": "mine"})["headline"] == "mine",
           fails, "merge_state: chartmaster ignored the later date")

    # The allowlist is pinned deliberately: anything auto-resolved during a rebase can
    # silently overwrite real work, so growing it is a reviewed decision, not a drift.
    # pulse.json and flows.json joined on 2026-08-28, when the publish step started
    # staging the market boards it had always refreshed and thrown away. Both are
    # regenerated snapshots rather than records, and merge_board keeps the one whose
    # DATA is newer, so an auto-resolve here cannot lose reporting.
    _check(set(ms.KNOWN) == {"editorial-log.json", "regwatch.json",
                             "site/data/chartmaster.json", "site/data/pulse.json",
                             "site/data/flows.json"}, fails,
           "merge_state: the auto-resolve allowlist changed; anything added here can "
           "silently overwrite real work during a rebase")
    # the board merger must pick by data age, never by which file was written last
    _check(ms.merge_board({"generated_utc": "2026-08-28T12:00:00Z"},
                          {"generated_utc": "2026-07-29T01:55:52Z"}
                          )["generated_utc"] == "2026-08-28T12:00:00Z", fails,
           "merge_state: a stale carried-forward board overwrote a fresher one")
    return fails


def _consistency_gate_canary():
    """Lock the window/date semantics of the cross-surface gate, offline.

    This exists because the gate blocked four production runs in three days, and every
    one of them was the same shape: two surfaces stating something TRUE at two different
    windows, which an unscoped metric could not tell apart from a contradiction. Three
    metrics were scoped one at a time, each after it had already cost a publish. These
    cases pin the behaviour so the fourth is not discovered the same way.

    Every metric whose number is reported at more than one window must be scoped; the
    audit assertion below fails if a new unscoped one is ever added."""
    fails = []
    import datetime as _dt
    import consistency_gate as cg

    for name, m in cg.METRICS.items():
        _check(m.get("scoped"), fails,
               f"consistency gate: metric '{name}' is unscoped; two true claims at "
               f"different windows would read as a contradiction and block a publish")

    def blocks(surf):
        return bool(cg.conflicts(surf))

    now = _dt.datetime.now(_dt.timezone.utc)
    today = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    older = (now - _dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # true at different windows: must NOT block
    for label, a, b in (
            ("btc day vs week", "bitcoin fell today", "bitcoin rose over the week"),
            ("dominance day vs month", "dominance fell in the last 24 hours",
             "dominance climbed over 30 days"),
            ("whale 2d vs 24h", "whales net off exchanges over the last 2 days",
             "whale flows onto exchanges over the last 24 hours"),
            ("etf week vs session", "etfs posted a weekly inflow",
             "etfs saw outflows in the latest session")):
        _check(not blocks([("story:a", a, None), ("chart-master", b, None)]), fails,
               f"consistency gate: false positive on {label} (both can be true)")

    # genuine contradictions: must block
    for label, a, b in (
            ("btc same day", "bitcoin rose today", "bitcoin fell today"),
            ("dominance same week", "dominance rose this week", "dominance fell this week"),
            ("btc unscoped", "bitcoin rallied", "bitcoin tumbled"),
            ("btc unscoped vs scoped", "bitcoin rallied", "bitcoin fell today"),
            ("etf unscoped vs week", "etf outflows persist", "etfs posted a weekly inflow")):
        _check(blocks([("story:a", a, None), ("chart-master", b, None)]), fails,
               f"consistency gate: missed a real contradiction on {label}")

    # a claim frozen on an earlier day is history, not a contradiction of a live board;
    # a same-day one still collides
    _check(not blocks([("story:a", "bitcoin rose today", older),
                       ("chart-master", "bitcoin fell today", None)]), fails,
           "consistency gate: stale story still colliding with a live board (deadlock)")
    _check(blocks([("story:a", "bitcoin rose today", today),
                   ("chart-master", "bitcoin fell today", None)]), fails,
           "consistency gate: same-day contradiction with a live board was not caught")

    # RECURRING ACTORS DO NOT PAIR FIGURES ALONE (2026-09-03, run 33768445949): "fbi"
    # paired an agent's $1M theft with a $560K Hamas seizure and blocked the publish.
    # A subject entity still pairs on its own; two shared entities always pair.
    import consistency as _cs
    _check(_cs.comparable_pair({"fbi"}) == set(), fails,
           "figure belt: a lone recurring actor (fbi) must not pair two stories")
    _check(_cs.comparable_pair({"avici"}) == {"avici"}, fails,
           "figure belt: a lone subject entity (avici) must still pair")
    _check(_cs.comparable_pair({"fbi", "avici"}) == {"fbi", "avici"}, fails,
           "figure belt: two shared entities must pair even when one is an actor")
    _check(_cs.comparable_pair({"etfs"}, cg._GENERIC_MARKET_TOKENS) == set(), fails,
           "figure belt: generic market vocabulary must not pair alone")


    # THE CONTRADICTION IS NOT THE WHOLE RUN (2026-09-03, run 33789773967): an unscoped
    # Chart Master whale line made the gate exit 1, which discarded the afternoon
    # edition AND the day's verified stories. The gate now withholds the colliding
    # surface and lets the rest publish; only what it cannot resolve fails the run.
    _paths = {"chart-master": "site/data/chartmaster.json",
              "story:a-brief-2026-09-03": "site/content/2026-09-03-a-brief.json",
              "story:plain-story": "site/content/2026-09-03-plain.json"}
    _c = {"metric": "whale exchange flows",
          "a": "story:a-brief-2026-09-03", "a_dir": "pos", "a_scope": "multiday",
          "b": "chart-master", "b_dir": "neg", "b_scope": "unscoped"}
    _both = set(_paths.values())
    _check(cg.is_blocking(_c, _both, _paths), fails,
           "consistency gate: a run that wrote both colliding surfaces must block")
    # the unscoped board is the offender by the gate's own name-the-window rule
    _check(cg._victim_rank("chart-master", "unscoped", _paths, _both)
           < cg._victim_rank("story:a-brief-2026-09-03", "multiday", _paths, _both), fails,
           "consistency gate: the unscoped surface must be withheld before the edition")
    _check(cg._victim_rank("story:plain-story", "multiday", _paths, _both)
           < cg._victim_rank("story:a-brief-2026-09-03", "multiday", _paths, _both), fails,
           "consistency gate: a story must be withheld before the guaranteed edition")
    _check(cg._victim_rank("chart-master", "unscoped", _paths, set()) is None, fails,
           "consistency gate: a surface this run did not write is never withheld")
    # a live UNSCOPED claim may not veto a new surface that named its window
    _one = {"site/content/2026-09-03-a-brief.json"}
    _check(not cg.is_blocking(_c, _one, _paths), fails,
           "consistency gate: a live unscoped claim must not block a scoped new surface")
    # ...but a live SCOPED claim that genuinely disagrees still blocks
    _c2 = dict(_c, b_scope="multiday")
    _check(cg.is_blocking(_c2, _one, _paths), fails,
           "consistency gate: a real scoped contradiction must still block")
    # git unavailable: fail closed
    _check(cg.is_blocking(_c, None, _paths), fails,
           "consistency gate: with git unavailable every conflict must block")

    return fails


def _window_belt_canary():
    """Lock the window belts, offline.

    WHY. The consistency gate is the LAST step before the publish and it has no retry, so
    a single loose sentence in the Chart Master or the edition discards a whole run of
    verified stories. The belts exist so that failure is caught earlier, inside the retry
    ladder, where the model gets another attempt and the stories still ship. ETF flows got
    a belt after it cost a publish; whale flows had the identical exposure, no belt, and
    cost run 30577704932 the same way on 2026-07-30.

    These cases pin the two properties that make a belt worth having: it fires on the
    phrasing the gate would have blocked, and it stays silent on phrasing the gate would
    have passed. A belt that fires on harmless prose burns the retry ladder and ends in
    the same place, with the previous read standing and nothing gained."""
    fails = []
    import chartmaster as cm

    day = {"direction": "onto exchanges", "window_hours": 24}
    multi = {"direction": "off exchanges", "window_hours": 48}

    # fires: exactly the shapes the gate treats as a collision
    for label, board, text in (
            ("unscoped contradiction (the 2026-07-30 failure)", day,
             "whales continued moving coins off exchanges into cold storage"),
            ("same-window contradiction", day,
             "over the last 24 hours whales moved off exchanges"),
            ("multiday board, multiday contradiction", multi,
             "over the last 2 days whales moved onto exchanges")):
        _check(bool(cm.whale_flow_problems(text, board)), fails,
               f"whale window belt: missed {label}")

    # silent: the gate would pass these, so the belt must not spend a retry on them
    for label, board, text in (
            ("agreement, unscoped", day,
             "whales pushed coins onto exchanges, adding sell pressure"),
            ("agreement, scoped", day,
             "in the last 24 hours whales moved onto exchanges"),
            ("a different window, both true at once", day,
             "whales have moved off exchanges over the last 7 days"),
            ("dual-grain phrasing naming both directions", day,
             "whales moved onto exchanges in the last 24 hours even as the 7 day trend "
             "stayed off exchanges into self-custody"),
            ("no whale claim", day, "bitcoin held its range and etf flows stayed positive"),
            ("day-scoped claim against a multiday board", multi,
             "in the last 24 hours whales moved onto exchanges")):
        _check(not cm.whale_flow_problems(text, board), fails,
               f"whale window belt: false positive on {label}")

    # no board direction means nothing to check against, never a blocked publish
    _check(cm.whale_flow_problems("whales moved off exchanges", {}) == [], fails,
           "whale window belt: fired with no board direction to compare against")

    # --- price belt: the third metric, added by audit rather than after a lost run ---
    down = [{"symbol": "BTC", "chg_24h_pct": -0.34, "chg_7d_pct": -1.59, "chg_30d_pct": -2.97}]
    mixed = [{"symbol": "BTC", "chg_24h_pct": 1.2, "chg_7d_pct": -3.0, "chg_30d_pct": -5.0}]
    for label, assets, text in (
            ("a day claim against a down day", down, "bitcoin rallied today"),
            ("a week claim against a down week", mixed, "bitcoin gained over the week"),
            ("an unscoped claim against an all-down tape", down,
             "bitcoin climbed as buyers stepped in"),
            ("an unscoped claim while the windows disagree", mixed, "bitcoin rose")):
        _check(bool(cm.price_problems(text, assets)), fails,
               f"price window belt: missed {label}")
    for label, assets, text in (
            ("an unscoped claim agreeing with every window", down,
             "bitcoin slid as sellers pressed"),
            ("a correct day claim", down, "bitcoin fell today"),
            ("dual-grain phrasing naming both", mixed,
             "bitcoin rose today even as it fell over the week"),
            ("no bitcoin claim", down, "ether led the majors higher")):
        _check(not cm.price_problems(text, assets), fails,
               f"price window belt: false positive on {label}")
    _check(cm.price_problems("bitcoin rallied today", []) == [], fails,
           "price window belt: fired with no asset numbers to compare against")
    # a window with no number must not be judged; silence beats a guess in a publish gate
    _check(not cm.price_problems("bitcoin gained over the week",
                                 [{"symbol": "BTC", "chg_24h_pct": -1.0}]), fails,
           "price window belt: judged a week claim with no week number")

    # --- THE INVARIANT, and the reason this canary exists ---
    # Every metric the consistency gate can block a publish on must be belted upstream, or
    # be listed as a deliberate exemption with a reason. The gate is the last step before
    # the push and has no retry, so an unbelted metric is a live run waiting to be thrown
    # away: that is exactly how ETF flows, then whale flows, each cost a publish. Adding a
    # metric to the gate without a belt now fails here instead of in production.
    import consistency_gate as cg
    BELTED = {"spot ETF flows": cm.etf_flow_problems,
              "whale exchange flows": cm.whale_flow_problems,
              "bitcoin price": cm.price_problems}
    for metric in cg.METRICS:
        _check(metric in BELTED or metric in cm.UNBELTED_METRICS, fails,
               f"window belt: the gate can block on '{metric}' and nothing belts it "
               f"upstream; add a belt or an explicit UNBELTED_METRICS reason")
    for metric in cm.UNBELTED_METRICS:
        _check(metric in cg.METRICS, fails,
               f"window belt: '{metric}' is exempted but the gate no longer checks it; "
               f"drop the stale exemption")

    # both surfaces that co-render must share the belts, or the unbelted one reintroduces
    # the failure. wrap.py calls into chartmaster for exactly this reason.
    import inspect
    import wrap
    src = inspect.getsource(wrap)
    for fn in ("etf_flow_problems", "whale_flow_problems", "price_problems"):
        _check(fn in src, fails,
               f"window belt: the edition no longer calls {fn}; it is a gate surface too")
    return fails

def _whale_flow_canary():
    """Lock the follow-the-money classification: stablecoins are scored separately from the
    volatile sell-pressure/accumulation signal, and direction follows net sign."""
    fails = []
    import whale_flows
    whale_sample = os.path.join(HERE, "fixtures", "whale_sample.json")
    txns = json.load(open(whale_sample, encoding="utf-8")).get("transactions", [])
    r = whale_flows.analyze(txns, 24)
    # exchange->exchange and wallet->wallet are excluded; 10 of the 12 sample txns count
    _check(r["txn_count"] == 10, fails, f"whale canary: expected 10 exchange-relevant txns, got {r['txn_count']}")
    _check(r["volatile"]["net_usd"] == 35000000, fails,
           f"whale canary: volatile net expected 35000000, got {r['volatile']['net_usd']}")
    _check(r["volatile"]["direction"] == "off exchanges", fails,
           f"whale canary: direction expected 'off exchanges', got {r['volatile']['direction']}")
    _check(r["stablecoins"]["net_buying_power_usd"] == 200000000, fails,
           f"whale canary: stablecoin buying power expected 200000000, got {r['stablecoins']['net_buying_power_usd']}")
    btc = next((a for a in r["by_asset"] if a["symbol"] == "BTC"), None)
    _check(btc and btc["net_usd"] < 0, fails, "whale canary: BTC should be net onto exchanges (negative)")
    _check(all(a["symbol"] not in whale_flows.STABLES for a in r["by_asset"]), fails,
           "whale canary: a stablecoin leaked into the volatile by_asset chart")
    return fails


def _replay_e2e():
    """Run the whole pipeline in replay mode over the fixture and assert the invariants."""
    fails = []
    os.environ["CRYPTO_LLM_MODE"] = "replay"
    cfg = common.load_config()
    client = llmlib.Client(cfg, mode="replay")
    import aggregate, editor, verifier, researcher, writer, approver, digest
    try:
        rc = aggregate.run(fixture=FIXTURE, out_path=os.path.join(common.OUT_DIR, "items.json"))
        _check(rc == 0, fails, f"replay: aggregate exit {rc}")
        items = common.read_out("items.json")
        _check(items["_meta"]["clusters"] == 5, fails,
               f"replay: expected 5 fixture clusters, got {items['_meta']['clusters']}")

        ed = editor.run(client=client)
        _check(len(ed["ranked"]) == 3 and len(ed["rejected"]) == 2, fails,
               f"replay: editor split expected 3/2, got {len(ed['ranked'])}/{len(ed['rejected'])}")

        ve = verifier.run(client=client)
        verds = {v["verdict"] for v in ve["verdicts"]}
        _check(verds == {"VERIFIED", "NEEDS-HUMAN-REVIEW", "REJECT"}, fails,
               f"replay: expected all three verdicts, got {sorted(verds)}")

        # Researcher: every draftable story gets a brief with a measured source_chars, and
        # REJECT stories are never briefed (no tokens spent on the dead).
        re_ = researcher.run(client=client)
        briefed = {b["id"] for b in re_["briefs"]}
        draftable = {v["id"] for v in ve["verdicts"] if v["verdict"] != "REJECT"}
        _check(briefed == draftable, fails,
               f"replay: researcher briefed {sorted(briefed)}, expected {sorted(draftable)}")
        _check(all("source_chars" in b for b in re_["briefs"]), fails,
               "replay: a brief is missing its measured source_chars")

        wr = writer.run(client=client)
        drafted = {d["id"] for d in wr["drafts"]}
        rejected_ids = {v["id"] for v in ve["verdicts"] if v["verdict"] == "REJECT"}
        _check(drafted and drafted.isdisjoint(rejected_ids), fails,
               f"replay: writer drafted a REJECT story or drafted nothing (drafted={drafted})")
        for d in wr["drafts"]:
            art = d["article_draft"]
            _check(art["status"] == "DRAFT", fails, f"replay: draft {d['id']} not DRAFT-tagged")
            _check(art["human_take"] == "", fails, f"replay: draft {d['id']} human_take not empty")
            _check("financial advice" in art["not_financial_advice"].lower(), fails,
                   f"replay: draft {d['id']} missing not-financial-advice disclaimer")

        # Approver: one categorized decision per draft; an unjudged draft would REJECT
        # (fail-closed coverage is exercised by the validate path itself).
        ap = approver.run(client=client)
        judged = {a["id"] for a in ap["approvals"]}
        _check(judged == drafted, fails,
               f"replay: approver judged {sorted(judged)}, expected {sorted(drafted)}")
        _check(all(a.get("category") in approver.CATEGORIES
                   for a in ap["approvals"] if a["decision"] == "REJECT"), fails,
               "replay: an approver REJECT is missing its category")

        # Depth gate (deterministic): short body + rich sources holds; short body + thin
        # sources passes (honest brevity); long body always passes.
        import autopilot
        _check(autopilot.depth_gate_holds(40, 5000) is True, fails,
               "depth gate: 40 words from 5000 chars of source material was NOT held")
        _check(autopilot.depth_gate_holds(40, 0) is False, fails,
               "depth gate: honest-thin story (40 words, no sources) was wrongly held")
        _check(autopilot.depth_gate_holds(450, 5000) is False, fails,
               "depth gate: full-length story was wrongly held")

        # BREAKING two-source gate (deterministic, fail-closed): a single-source breaking
        # story HOLDS unless its headline carries the unconfirmed label; two independent
        # sources publish; duplicate source names do not count as independence.
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk"]) is True, fails,
               "breaking gate: single-source story published as fact was NOT held")
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk", "The Block"]) is False, fails,
               "breaking gate: two-source story was wrongly held")
        _check(autopilot.breaking_two_source_holds(
                   "Unconfirmed: Exchange X may have halted withdrawals", ["CoinDesk"]) is False,
               fails, "breaking gate: labeled-unconfirmed single-source was wrongly held")
        _check(autopilot.breaking_two_source_holds(
                   "Exchange X halts withdrawals", ["CoinDesk", "coindesk", ""]) is True, fails,
               "breaking gate: duplicate source names wrongly counted as independent")

        # EVENT-FINGERPRINT DEDUP (2026-07-22): same-event-different-words duplicates that
        # headline-word overlap misses must be caught; genuinely distinct stories spared.
        _check(autopilot.same_event(
                   "Amazon Japan supplier to pay 2,300 contractors using regulated yen stablecoin", "",
                   "Amazon Japan logistics firm AZ-COM Maruwa to pay 2,300 partners with regulated yen", ""),
               fails, "dedup: same event with different words (Amazon Japan) was NOT caught")
        _check(autopilot.same_event(
                   "Hut 8 and IREN land billions in AI contracts", "",
                   "AI compute stocks bounce as Hut 8, IREN book AI capacity", ""),
               fails, "dedup: Hut 8/IREN same event was NOT caught")
        _check(not autopilot.same_event(
                   "Grayscale Files S-1 for Spot Worldcoin ETF", "",
                   "Movement Labs files for Chapter 11 bankruptcy", ""),
               fails, "dedup: two distinct stories were wrongly merged")
        _check(not autopilot.same_event(
                   "Russia Parliament passes crypto market law with $3,800 cap", "",
                   "UK Parliament launches inquiry into banking restrictions", ""),
               fails, "dedup: two different Parliament stories wrongly merged")

        # Daily edition (wrap): replay dry-run must produce a belts-clean edition item
        # that leads the page (negative rank) and carries the desk's stories as sources.
        import subprocess
        env = dict(os.environ, CRYPTO_LLM_MODE="replay")
        r = subprocess.run([sys.executable, os.path.join(HERE, "wrap.py"),
                            "--dry-run", "--edition", "morning"],
                           capture_output=True, text=True, env=env)
        _check(r.returncode == 0, fails, f"wrap dry-run failed: {(r.stdout + r.stderr)[-200:]}")
        if r.returncode == 0:
            if "no published stories in the window" in (r.stdout or ""):
                # HONEST SILENCE IS A LEGAL STATE (2026-08-03 wedge postmortem): wrap
                # reads the desk's REAL site/content even in replay, and when the tape
                # goes stale the dry run rightly declines to fabricate an edition. The
                # canary then crashed on the missing preview file, which hard-gated the
                # brief workflow, which meant a desk quiet past the story window COULD
                # NEVER RUN AGAIN to break its own silence: 2026-08-03's dead desk.
                # Fail-closed must never depend on the desk already being alive.
                print("canary: wrap dry-run declined honestly (no stories in the "
                      "window); edition belts will exercise on the next content day")
            else:
                try:
                    wp = common.read_out("wrap-preview.json")
                except FileNotFoundError:
                    wp = None
                    _check(False, fails, "wrap dry-run exited 0 with no preview and no "
                                         "honest-silence marker (unknown silent path)")
                if wp is not None:
                    _check(wp.get("rank", 0) < 0, fails, "wrap: edition rank must be negative (leads the page)")
                    _check(wp.get("human_take") == "", fails, "wrap: human_take must be empty")
                    _check("—" not in json.dumps(wp), fails, "wrap: em dash leaked into the edition")
                    _check(wp.get("sources"), fails, "wrap: edition must cite the desk's own stories")

        digest.run(date="canary")
        qmd = os.path.join(common.OUT_DIR, "review_queue", "canary.md")
        _check(os.path.exists(qmd), fails, "replay: digest did not write the review queue")
        tmpl = common.read_out("approval_template.json")
        _check(all(s["decision"] == "hold" for s in tmpl["stories"].values()), fails,
               "replay: approval template must default every story to 'hold'")
        _check(all(v["id"] not in tmpl["stories"] for v in ve["verdicts"] if v["verdict"] == "REJECT"),
               fails, "replay: a REJECT story leaked into the approval template")
    except Exception as e:
        fails.append(f"replay: end-to-end raised {type(e).__name__}: {e}")
    return fails


def _contract_ladder_canary(cfg):
    """The recovery layer (2026-07-15): a contract violation retries on the same model,
    then escalates ONE call to the rescue model, and replay mode never escalates."""
    fails = []

    class StubClient(llmlib.Client):
        def __init__(self, cfg, answers):
            super().__init__(cfg, mode="live")
            self.answers = list(answers)
            self.models_used = []

        def _live_raw(self, stage, model_cfg, system, user):
            self.models_used.append(model_cfg["model"])
            return self.answers.pop(0)

    def need_ranked(o):
        if "ranked" not in o:
            raise llmlib.LLMError("editor output missing 'ranked'")
        return o

    # (a) bad shape then good on rung 2: recovered, no escalation
    c = StubClient(cfg, ['{"id": "c000"}', '{"ranked": [], "rejected": []}'])
    try:
        obj = c.call_json("editor", "sys", "user", validate=need_ranked)
        _check("ranked" in obj and len(c.models_used) == 2, fails,
               f"ladder: retry did not recover (calls={c.models_used})")
        _check(c.models_used[0] == c.models_used[1], fails,
               "ladder: rung 2 must reuse the configured model")
    except llmlib.LLMError as e:
        fails.append(f"ladder: recoverable violation wrongly failed: {e}")

    # (b) two bad answers: rung 3 runs on the rescue model
    c2 = StubClient(cfg, ['nonsense', '{"wrong": 1}', '{"ranked": [], "rejected": []}'])
    try:
        c2.call_json("editor", "sys", "user", validate=need_ranked)
        _check(len(c2.models_used) == 3 and c2.models_used[2] == llmlib.RESCUE_MODEL, fails,
               f"ladder: third rung was not the rescue model (calls={c2.models_used})")
    except llmlib.LLMError as e:
        fails.append(f"ladder: rescue rung wrongly failed: {e}")

    # (c) three bad answers: fails closed
    c3 = StubClient(cfg, ['x', 'y', 'z'])
    try:
        c3.call_json("editor", "sys", "user", validate=need_ranked)
        fails.append("ladder: triple violation did NOT fail closed")
    except llmlib.LLMError:
        pass

    # (d) replay never retries/escalates: a fixture that fails validation fails the canary
    rc = llmlib.Client(cfg, mode="replay")
    try:
        rc.call_json("editor", "sys", "user",
                     validate=lambda o: (_ for _ in ()).throw(llmlib.LLMError("fixture bad")))
        fails.append("ladder: replay validation failure did NOT raise")
    except llmlib.LLMError:
        _check(rc.budget.calls == 1, fails,
               f"ladder: replay made {rc.budget.calls} calls (must be exactly 1, no ladder)")

    # (e) watcher slot recovery: past deadline + missing edition -> that slot; edition
    # present -> quiet; before deadline -> quiet
    import datetime as _dt
    import tempfile
    import watcher
    # PROGRAM 4, T-1 (2026-09-16): this tested the MORNING slot, which no longer runs.
    # The properties belong to slot recovery, not to that slot, so they are checked
    # against the one that survives.
    with tempfile.TemporaryDirectory() as td:
        late = _dt.datetime(2026, 7, 16, 2, 0, tzinfo=_dt.timezone.utc)
        _check(watcher.missed_slot(late, td) == "evening-brief", fails,
               "watcher recovery: past the deadline with no edition, did not fire")
        open(os.path.join(td, "2026-07-15-evening-brief.json"), "w").write("{}")
        _check(watcher.missed_slot(late, td) is None, fails,
               "watcher recovery: fired despite the edition existing")
        early = _dt.datetime(2026, 7, 15, 20, 0, tzinfo=_dt.timezone.utc)
        _check(watcher.missed_slot(early, td) is None, fails,
               "watcher recovery: fired before the deadline")
    # The guard that would have caught the sports desk's early Edition tonight: a slot
    # left in SLOT_DEADLINES with no cron is re-fired on every tick for the rest of
    # time, before the cooldown and before the cage, and each fire spends a full run.
    _check({s[0] for s in watcher.SLOT_DEADLINES} == {"evening-brief"}, fails,
           "watcher recovery: a slot with no cron is in SLOT_DEADLINES and would be "
           "re-fired on every tick for the rest of time")

    # (j) C-4: THE DESK REGISTER AND THE WORKFLOW FILES MUST AGREE, EXACTLY. desk.json
    # is how a person knows the newsroom is configured the way they think it is, and a
    # register nobody checks is a comment. Every active cron in a file must be in the
    # register, and every cron in the register must be in a file: no more and no less,
    # so a stale cron or a placeholder that never fires cannot survive a push.
    #
    # Comment out a cron and forget the register and this fails. Add one to the register
    # and forget the file and this fails. That is the point.
    _here = os.path.dirname(os.path.abspath(__file__))
    _dj = os.path.join(_here, "desk.json")
    _wfdir = os.path.join(_here, ".github", "workflows")
    if os.path.exists(_dj):
        _reg = json.load(open(_dj, encoding="utf-8"))
        _regwf = _reg.get("workflows") or {}
        _seen = set()
        for _fn in sorted(os.listdir(_wfdir)):
            if not _fn.endswith((".yml", ".yaml")):
                continue
            _seen.add(_fn)
            _txt = open(os.path.join(_wfdir, _fn), encoding="utf-8").read()
            # active cron lines only: a commented one is not a schedule
            # Strip the comment FIRST, then the quotes: a cron line reads
            #   - cron: "38 23 * * *"   # Evening Wrap slot
            # and stripping quotes before the comment leaves the closing one attached.
            _live = set(re.findall(r'^\s*-\s*cron:\s*["\']([^"\']+)["\']',
                                   _txt, re.M))
            _check(_fn in _regwf, fails,
                   f"desk register: {_fn} is not in desk.json")
            _want = {c.get("utc") for c in (_regwf.get(_fn) or {}).get("crons") or []}
            _check(_live == _want, fails,
                   f"desk register: {_fn} crons {sorted(_live)} do not match the "
                   f"register's {sorted(_want)}")
        for _fn in _regwf:
            _check(_fn in _seen, fails,
                   f"desk register: desk.json lists {_fn}, which has no workflow file")
        # the served slots are the recovery table, in one place (C-3)
        _check(set(_reg.get("served_slots") or []) ==
               {s[0] for s in watcher.SLOT_DEADLINES}, fails,
               f"desk register: served_slots {_reg.get('served_slots')} do not match "
               f"watcher.SLOT_DEADLINES")

    # (h) PROGRAM 4, X-2: THE SLOT GUARD, ON ITS NO-MODEL PATH. The guard lives in the
    # workflow YAML, so it is extracted and executed here with origin/main mocked. It
    # is the rule that makes "one Edition a day" true regardless of who dispatches, and
    # it was gated on EVENT == "schedule" until tonight, which let every dispatch spend.
    import re as _re
    import tempfile as _tf
    _wf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       ".github", "workflows", "crypto-news-brief.yml")

    def _guard_code():
        s = open(_wf, encoding="utf-8").read()
        m = _re.search(r"python3 - <<'PYEOF'\n(.*?)\n          PYEOF", s, _re.S)
        if not m:
            return None
        return "\n".join(l[10:] if l.startswith(" " * 10) else l
                          for l in m.group(1).split("\n"))

    def _guard(code, event, slot, cron, breaking, served):
        out = _tf.NamedTemporaryFile("w+", delete=False, suffix=".txt"); out.close()
        env = {"EVENT": event, "SLOT_NAME": slot, "SLOT_CRON": cron,
               "BREAKING": "1" if breaking else "0", "GITHUB_OUTPUT": out.name}
        old = dict(os.environ); os.environ.update(env)

        class _R:
            returncode = 0 if served else 1
            stdout = stderr = b""
        import io as _io
        import subprocess as _sp
        real, so = _sp.run, sys.stdout
        _sp.run = lambda *a, **k: _R()
        sys.stdout = _io.StringIO()
        try:
            exec(compile(code, "<guard>", "exec"), {"__name__": "__main__"})
        finally:
            sys.stdout = so; _sp.run = real
            os.environ.clear(); os.environ.update(old)
        res = dict(l.split("=", 1) for l in open(out.name).read().strip().split("\n")
                   if "=" in l)
        os.unlink(out.name)
        return res.get("serve")

    _code = _guard_code()
    _check(_code is not None, fails, "slot guard: could not read the guard from the workflow")
    if _code:
        # C-1: THE EDITION PATH, AS ONE TEST. The desk promises one Edition a day and
        # this is the rule that keeps that promise: at the slot, with no Edition file
        # for that slot and day on origin/main, the run WRITES one, whatever else
        # happened that day; with the file present it stands down at zero.
        #
        # On 2026-09-16 the crypto slot run never reached this guard. It died at the
        # offline canary gate on an assertion about a slot that had been removed an
        # hour earlier, and the desk got its Edition by luck, from a breaking run at
        # 8:43 PM. The rule was never the problem; nothing was checking that the rule
        # could be reached.
        _check(_guard(_code, "schedule", "", "8 23 * * *", False, False) == "true", fails,
               "C-1: at the slot with no Edition for the day, the run must write one")
        _check(_guard(_code, "schedule", "", "8 23 * * *", False, True) == "false", fails,
               "C-1: with the Edition already on origin/main, the run must stand down")
        _cases = [
            ("a cron for a slot already served must stand down",
             "schedule", "", "8 23 * * *", False, True, "false"),
            ("a cron for an unserved slot must run",
             "schedule", "", "8 23 * * *", False, False, "true"),
            ("a DISPATCH for a slot already served must stand down",
             "workflow_dispatch", "evening-brief", "", False, True, "false"),
            ("a dispatch naming no slot must stand down even with nothing served",
             "workflow_dispatch", "", "", False, False, "false"),
            ("a breaking run must still pass the guard",
             "workflow_dispatch", "evening-brief", "", True, True, "true"),
            # X-2b: the old Worker names slots on its old schedule until the deploy
            # lands. A dispatch naming a slot the desk no longer serves must stand
            # down even with nothing served, or it spends a run writing an Edition
            # for a retired slot.
            ("a dispatch naming a slot the desk no longer serves must stand down",
             "workflow_dispatch", "morning-brief", "", False, False, "false"),
            ("the same for afternoon-brief",
             "workflow_dispatch", "afternoon-brief", "", False, False, "false"),
        ]
        for _label, _ev, _slot, _cron, _brk, _served, _want in _cases:
            _check(_guard(_code, _ev, _slot, _cron, _brk, _served) == _want, fails,
                   "slot guard: " + _label)


    # THE BOTTOM LINE lane gate (owner directive 2026-07-15): the signature element's
    # own guardrail must block directional/predictive language and pass clean synthesis.
    import wrap as wrapmod
    clean = ("The day's theme was regulation outpacing the market: two agencies moved and "
             "the tape barely noticed. The honest read is that positioning stayed calm "
             "while the headlines ran hot. The coming checkpoints are Thursday's committee "
             "vote and the exchange's incident report.")
    _check(wrapmod.bottom_line_lint(clean) == [], fails,
           f"Bottom Line lane: clean synthesis wrongly flagged: {wrapmod.bottom_line_lint(clean)}")
    dirty = "Today's flush sets up for a move higher into the CPI print."
    _check(len(wrapmod.bottom_line_lint(dirty)) >= 1, fails,
           "Bottom Line lane: 'sets up for a move higher' was NOT blocked")
    _check(len(wrapmod.bottom_line_lint("Bitcoin looks poised to rally, brace for volatility.")) >= 2,
           fails, "Bottom Line lane: poised-to/brace-for was NOT blocked")

    # ATTRIBUTED OBSERVATIONS (2026-07-19): the desk reports what a source shows, it does
    # not assert a house opinion. Attributed phrasing passes; unattributed voice is blocked.
    attributed = ("Per CoinDesk's reporting the vote slipped to next week, and the desk's "
                  "Whale Watch board shows $162M moving onto exchanges.")
    _check(wrapmod.unattributed_lint(attributed) == [], fails,
           f"attribution: sourced phrasing wrongly flagged: {wrapmod.unattributed_lint(attributed)}")
    _check(len(wrapmod.unattributed_lint("The honest read is that nobody cares.")) >= 1, fails,
           "attribution: 'the honest read is' was NOT blocked")
    _check(len(wrapmod.unattributed_lint("Make no mistake, the real story is elsewhere.")) >= 2,
           fails, "attribution: 'make no mistake' / 'the real story is' were NOT blocked")

    # JURISDICTION TRACKER: real stated dates parse, prose numbers do not (a tracker that
    # invents a deadline is worse than no tracker).
    import regwatch
    _check(bool(regwatch.DATE_PAT.search("compliance deadline of January 20, 2027")), fails,
           "regwatch: a real stated deadline was NOT parsed")
    _check(not regwatch.DATE_PAT.search("rose by the 20 percent"), fails,
           "regwatch: prose number 'by the 20 percent' was wrongly parsed as a date")
    _check(not regwatch.DATE_PAT.search("due over 90 days"), fails,
           "regwatch: 'over 90 days' was wrongly parsed as a date")
    j, i, dts = regwatch.extract("The GENIUS Act compliance deadline of January 20, 2027 applies.")
    _check("United States" in j and "GENIUS Act" in i and dts, fails,
           f"regwatch: GENIUS Act storyline not filed correctly (j={j} i={i} d={dts})")
    j2, i2, _ = regwatch.extract("A US official commented on the EU's MiCA regime.")
    _check(i2 == ["MiCA"] and "European Union" in j2, fails,
           f"regwatch: MiCA should file under the EU only (j={j2} i={i2})")
    return fails


def _failclosed_canaries(cfg):
    fails = []
    # (a) missing key fails the LLM call closed
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        live = llmlib.Client(cfg, mode="live")
        try:
            live.call_json("editor", "sys", "user")
            fails.append("fail-closed: live call with no API key did NOT raise")
        except llmlib.LLMError:
            pass
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved

    # (b) budget cap trips
    tiny = llmlib.Budget(max_tokens=10, max_usd=100)
    try:
        tiny.record("claude-opus-4-8", {"input_tokens": 1000, "output_tokens": 1000})
        fails.append("fail-closed: budget cap did NOT trip on overspend")
    except llmlib.BudgetError:
        pass

    # (c) publish refuses a replay-mode approval and an unapproved/hold story
    import publish
    tmp = os.path.join(common.OUT_DIR, "approval_replay.json")
    common.write_out(os.path.basename(tmp), {"mode": "replay", "stories": {
        "c000": {"decision": "approve", "human_take": "x"}}})
    res = publish.run(approval_path=tmp)
    _check(res["published"] == [], fails, "fail-closed: publish accepted a replay-mode approval")

    common.write_out(os.path.basename(tmp), {"mode": "live", "stories": {
        "c000": {"decision": "hold", "human_take": ""}}})
    res2 = publish.run(approval_path=tmp)
    _check(res2["published"] == [], fails, "fail-closed: publish accepted a 'hold' story")
    return fails


# ---- Layer 2 -----------------------------------------------------------------

# Counts RSS <item> and Atom <entry> elements, namespace prefixes included, closing tags
# excluded. The trailing class is what keeps <itunes:owner> and <items> out of the count.
_ITEM_TAG = re.compile(r"<(?:[a-z0-9_.-]+:)?(?:item|entry)[\s/>]")


def _feed_items(body):
    return len(_ITEM_TAG.findall(body))


def layer2_sources():
    cfg = common.load_config()
    fails = []
    for f in cfg["sources"]["rss"]:
        name, url = f["name"], f["url"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": common.ua_for(url)})
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.getcode()
                # Whole body, not the first 2000 bytes. The head is enough to see the feed
                # SHAPE, but the items sit past it and an empty channel is only visible
                # from a full-body count (the zero-item check below).
                body = r.read().decode("utf-8", "replace").lower()
                head = body[:2000]
        except Exception as e:
            gh("warning", f"sources: '{name}' fetch failed ({url}): {e} -- soft warning only, NOT failing")
            continue
        if code != 200:
            # A feed with a configured API fallback is healthy when the FALLBACK serves
            # (the ESPN RSS hosts answer runner IPs with HTTP 202 bot challenges by
            # design; the pipeline never reads those URLs from CI, the aggregate's API
            # fallback does). Only a feed with no working fallback is a real liveness
            # failure. The probe gets two attempts: the 2026-08 Monday reds were
            # transient probe misses dressed up as seven dead feeds.
            fb = f.get("fallback_api")
            fb_note = "no fallback configured"
            if fb:
                fb_note = "fallback probe failed twice"
                for attempt in (1, 2):
                    try:
                        freq = urllib.request.Request(fb, headers={"User-Agent": common.ua_for(fb)})
                        with urllib.request.urlopen(freq, timeout=30) as fr:
                            if fr.getcode() == 200:
                                fb_note = "fallback OK"
                                break
                    except Exception:
                        pass
                    if attempt == 1:
                        time.sleep(3)
                if fb_note == "fallback OK":
                    print(f"LAYER 2 sources: OK '{name}' -> RSS {code} but API "
                          f"fallback resolves 200 (the path the pipeline uses).")
                    continue
            why = ("HTTP 202 bot challenge (runner-IP block)" if code == 202
                   else f"HTTP {code}")
            gh("error", f"sources: '{name}' -> {why}; {fb_note}: {url}")
            fails.append({"feed": name, "url": url, "status": why, "fallback": fb_note})
            continue
        if not ("<rss" in head or "<feed" in head or "<rdf" in head or "<?xml" in head):
            gh("error", f"sources: '{name}' did not look like an RSS/Atom feed: {url}")
            fails.append({"feed": name, "url": url,
                          "status": "HTTP 200 but not feed-shaped", "fallback": "n/a"})
            continue
        # A feed can serve a perfectly valid channel carrying ZERO items, which a
        # shape-only check reads as healthy forever: on 2026-09-03 all four Google News
        # lanes on the sports desk went to 0 items in production an hour after serving 12
        # each, and this probe saw nothing wrong. An empty channel is the same class of
        # dead as a 404, so it gets the same two attempts as the fallback probe above:
        # zero items is often a transient miss, and only a feed still empty on the second
        # read is worth filing.
        items = _feed_items(body)
        if items == 0:
            time.sleep(3)
            try:
                rreq = urllib.request.Request(url, headers={"User-Agent": common.ua_for(url)})
                with urllib.request.urlopen(rreq, timeout=30) as rr:
                    if rr.getcode() == 200:
                        items = _feed_items(rr.read().decode("utf-8", "replace").lower())
            except Exception:
                pass
        if items == 0:
            gh("error", f"sources: '{name}' -> HTTP 200 and feed-shaped but ZERO items "
                        f"on two reads: {url}")
            fails.append({"feed": name, "url": url,
                          "status": "HTTP 200 but zero items", "fallback": "n/a"})
            continue
        print(f"LAYER 2 sources: OK '{name}' -> HTTP 200, feed-shaped.")
    if fails:
        # Machine-readable failure list: the verify workflow's flag issue names the
        # feeds from this file instead of sending the owner into the run logs.
        os.makedirs("out", exist_ok=True)
        with open(os.path.join("out", "layer2_failures.json"), "w", encoding="utf-8") as fh:
            json.dump(fails, fh, indent=1)
        print(f"\nLAYER 2 SOURCES: {len(fails)} feed(s) failing -> notify (exit 3). Does NOT block a run.")
        return 3
    print("LAYER 2 SOURCES: PASS -> all configured feeds resolve 200 and look like feeds.")
    return 0


def _one_story_canary():
    """Jack, 4 October 2026: the evening Edition publishes ONE story, the top-ranked one
    that may lead (two independent sources or one primary); the rest are held, and only
    the ones that could have led are carried, to the next Edition and no further."""
    import autopilot as _ap
    import json as _js
    import tempfile as _tf
    fails = []
    _c = [{"cid": "c4", "rank": 4, "headline": "four", "standing": "corroborated"},
          {"cid": "c1", "rank": 1, "headline": "one", "standing": "single"},
          {"cid": "c2", "rank": 2, "headline": "two", "standing": "primary"},
          {"cid": "c9", "rank": 9, "headline": "nine", "standing": "corroborated"}]
    _ch, _held = _ap.choose_one(_c)
    _check(_ch and _ch["cid"] == "c2", fails,
           f"one-story canary: the top-ranked story that may lead was not chosen: {_ch}")
    _check(sorted(h["cid"] for h in _held) == ["c1", "c4", "c9"], fails,
           f"one-story canary: every other approved story is not held: {_held}")
    _why = {h["cid"]: h["why"] for h in _held}
    _check(_why.get("c1") == _ap.SECONDARY and _why.get("c4") == _ap.ONE_A_DAY, fails,
           f"one-story canary: a hold does not say why: {_why}")
    _ch0, _h0 = _ap.choose_one([dict(_c[1])])
    _check(_ch0 is None and len(_h0) == 1, fails,
           "one-story canary: a story on one secondary outlet was made the day's story")

    # The hold lives to the next Edition and no further.
    _d = _tf.mkdtemp()
    _p = os.path.join(_d, "hold.json")
    _drafts = {h["cid"]: {"id": h["cid"], "article_draft": {"title": h["headline"]}}
               for h in _held}
    _ap.write_hold(_p, "2026-10-04", "2026-10-04T23:14:00Z", _ch, _held, _drafts)
    _rec = _js.load(open(_p))
    _check(_rec["published"] == 1 and _rec["chosen"]["cid"] == "c2", fails,
           f"one-story canary: the hold file does not record the day's story: {_rec}")
    _check(sorted(h["cid"] for h in _ap.carried_holds("2026-10-05", _p)) == ["c4", "c9"],
           fails, "one-story canary: the next Edition does not see the stories held for it")
    _check(_ap.carried_holds("2026-10-06", _p) == [], fails,
           "one-story canary: a hold outlived the next Edition")
    _check(_ap.carried_holds("2026-10-04", _p) == [], fails,
           "one-story canary: the same day's Edition re-offered its own holds")
    return fails


def _dark_line_canary():
    """The cadence said on the page, and the dark line only AFTER the slot has run."""
    import site_build as _sb
    import datetime as _dtm
    fails = []
    _now = lambda s: _dtm.datetime.fromisoformat(s.replace("Z", "+00:00"))
    _old = [{"title": "Yesterday's story", "verdict": "VERIFIED",
             "published_utc": "2026-10-03T23:14:00Z", "sources": []}]
    _ran = {"edition_date": "2026-10-04", "published": 0}
    # a morning build reads the hold the PREVIOUS evening wrote, after a zero day too
    _morning = _sb.dark_line(_old, {"edition_date": "2026-10-03", "published": 0},
                             _now("2026-10-04T13:00:00Z"))
    _check(_morning == "", fails,
           f"dark-line canary: a build before the slot says the day failed: {_morning[:80]}")
    _before = _sb.dark_line(_old, {"edition_date": "2026-10-03"}, _now("2026-10-04T22:00:00Z"))
    _check(_before == "", fails,
           "dark-line canary: the dark line printed before today's Edition slot ran")
    _after = _sb.dark_line(_old, _ran, _now("2026-10-04T23:40:00Z"))
    _check("Nothing cleared the bar today." in _after and "October 4" in _after, fails,
           f"dark-line canary: a zero day after the slot does not say so, with the date: "
           f"{_after[:120]}")
    _one = _old + [{"title": "Today's story", "verdict": "VERIFIED",
                    "published_utc": "2026-10-04T23:14:00Z", "sources": []}]
    _check(_sb.dark_line(_one, _ran, _now("2026-10-04T23:40:00Z")) == "", fails,
           "dark-line canary: the dark line printed on a day a story published")
    _check(_sb.CADENCE_LINE == ("One checked story a day, in the evening, Eastern time. "
                                "More only when news breaks."), fails,
           "dark-line canary: the cadence line is not Jack's sentence")
    # /news states the wire path in Jack's words (7 October 2026); the home page keeps the
    # October 4 sentence until Sprint 2 builds it.
    for _pg, _line in (("news.html", _sb.NEWS_CADENCE_LINE), ("index.html", _sb.CADENCE_LINE)):
        _f = os.path.join(_sb.PUBLISH, _pg)
        if os.path.exists(_f):
            _h = open(_f, encoding="utf-8", errors="ignore").read()
            _check(_sb.esc(_line) in _h, fails,
                   f"dark-line canary: {_pg} does not state the cadence")
    return fails


def _three_badges_canary():
    """Three badges, and only three (Jack, 4 October 2026). Fixtures: two sources, one
    primary, one secondary, a breaking single."""
    import site_build as _sb
    import re as _re
    fails = []
    two = {"verdict": "VERIFIED", "sources": [{"url": "https://www.coindesk.com/a"},
                                              {"url": "https://www.theblock.co/b"}]}
    prim = {"verdict": "VERIFIED", "sources": [{"url": "https://www.sec.gov/newsroom/x"}]}
    sec = {"verdict": "VERIFIED", "sources": [{"url": "https://cointelegraph.com/news/y"}]}
    brk = {"verdict": "VERIFIED", "breaking": True,
           "sources": [{"url": "https://cointelegraph.com/news/z"}]}
    _txt = lambda i: _re.sub(r"<[^>]+>", "", _sb.verdict_badge(i["verdict"], i))
    _check(_txt(two) == "Verified", fails, f"badges: two sources read {_txt(two)!r}")
    _check(_txt(prim) == "Verified, primary source", fails,
           f"badges: one primary source reads {_txt(prim)!r}")
    _check(_txt(sec) == "Unconfirmed, one report", fails,
           f"badges: one secondary outlet reads {_txt(sec)!r}")
    _check(_txt(brk) == "Unconfirmed, one report" and "Verified" not in _txt(brk), fails,
           f"badges: a breaking single reads {_txt(brk)!r}")
    _seen = {_txt(i) for i in (two, prim, sec, brk)} | {
        _txt({"verdict": "NEEDS-HUMAN-REVIEW", "sources": two["sources"]})}
    _check(_seen <= {"Verified", "Verified, primary source", "Unconfirmed, one report", ""},
           fails, f"badges: a fourth badge exists: {_seen}")
    # the primary source is listed first
    _mixed = [{"url": "https://cointelegraph.com/a"}, {"url": "https://www.sec.gov/b"}]
    _check(_sb.standing.primary_first(_mixed)[0]["url"] == "https://www.sec.gov/b", fails,
           "badges: a primary source is not first in the story's source list")
    # Standards says what each badge means, and spells labeled the American way
    _st = _sb.render_standards("")
    for _b in ("Verified", "Verified, primary source", "Unconfirmed, one report"):
        _check(f"<b>{_b}</b>" in _st, fails, f"badges: Standards does not define {_b!r}")
    _check("labelled" not in _st and "single weak source is labeled" in _st, fails,
           "badges: Standards still spells labelled, or lost the single-weak-source sentence")
    return fails


def _whale_sentence_canary():
    """/flows said no exchange-size whale moves hit the feed in 24 hours over a table of
    sixteen $50M transfers, aged against the newest move rather than the clock. One
    function, one window, one threshold, for the sentence and the table (4 October 2026)."""
    import site_build as _sb
    import re as _re
    fails = []
    _t = 1_790_000_000
    _mv = lambda usd, sym, ts, to="okex": {"symbol": sym, "usd": usd, "ts": ts, "to": to,
                                           "from": "unknown wallet", "hash": "h", "blockchain": "x"}
    # txn_count deliberately disagrees with the rows, and one move sits under the floor:
    # a fixture whose parts sum to its total cannot catch a count taken from the total
    _f = {"window_hours": 48, "window_widened_from": 24, "txn_count": 16,
          "generated_utc": "2026-09-21T12:00:00Z",
          "volatile": {"net_usd": -91_242_248, "direction": "onto exchanges"},
          "top_inflows": [_mv(80e6, "BTC", _t), _mv(60e6, "ETH", _t - 3600)],
          "top_outflows": [_mv(70e6, "BTC", _t - 7200, "binance"), _mv(55e6, "SOL", _t),
                           _mv(51e6, "ETH", _t), _mv(40e6, "XRP", _t)]}
    _w = _sb.whale_window(_f)
    _n = _re.search(r"(\d+) transfers? of \$50M", _w["sentence"])
    _check(_n is not None and int(_n.group(1)) == len(_w["moves"]) == 5, fails,
           f"whale canary: the sentence's count is not the table's rows: "
           f"{_w['sentence']!r} over {len(_w['moves'])} rows")
    _check(_sb._win_phrase(48) in _w["sentence"] and "$91.2M" in _w["sentence"]
           and "onto exchanges" in _w["sentence"], fails,
           f"whale canary: the sentence does not state the window and the net: "
           f"{_w['sentence']!r}")
    _html = _sb.render_flows(_f, "")
    _rows = len(_re.findall(r'<td class="sym2">', _html))
    _check(_rows == len(_w["moves"]), fails,
           f"whale canary: /flows lists {_rows} transfer rows, its sentence says "
           f"{len(_w['moves'])}")
    _check(_w["sentence"] in _html, fails, "whale canary: /flows does not print the sentence")
    _check("Okex" not in _html and "okex" not in _html.lower().replace("okx", ""), fails,
           "whale canary: /flows printed Okex; the name table says OKX")
    _check(_sb.venue_name("Okex") == "OKX" and _sb.destyle("OKEx and Okex") == "OKX and OKX",
           fails, "whale canary: OKX is not one spelling everywhere")
    return fails

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "canary":
        sys.exit(layer1_canary())
    if cmd == "sources":
        sys.exit(layer2_sources())
    c = layer1_canary()
    s = layer2_sources()
    print(f"\n[gate] Layer1 canary = {'PASS' if c == 0 else 'FAIL'} | "
          f"Layer2 sources = {'PASS' if s == 0 else 'MISMATCH (notify, non-blocking)'}")
    sys.exit(c)  # ONLY Layer 1 blocks


if __name__ == "__main__":
    main()
