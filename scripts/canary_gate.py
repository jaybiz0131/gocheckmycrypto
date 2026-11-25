#!/usr/bin/env python3
"""canary_gate.py: the publish-time gate (C-DONE, November 2026).

The offline canary is a hard gate at the top of every publishing run, and it reads the tree it is handed: the code and
the data the desk's own runs stored. Four times in thirty days (October 23, October 29, November 9, November 13) a line
the desk had stored the night before turned a case red, and the desk locked itself: only a run could replace the line,
and no run could pass the gate while the line stood. Each time a session had to find the case and release it.

The code is gated where it changes. No merge reaches main without `verify_pipeline.py canary` passing on the exact
tree, and verify-crypto-pipeline.yml runs the canary on every push. So at publish time a red canary has one of two
causes, and this script tells them apart by running the canary once more:

  1. Run the canary on the tree as it stands. Green: exit 0.
  2. Red: find the last commit on main that changed anything a run does not write (RUN_WRITTEN is what the runs
     commit: stories, boards, ledgers, queues). That commit's tree is the code as it was last gated, with the data it
     was gated on. If HEAD is that commit, the code itself is red: exit with the canary's status.
  3. Otherwise run the canary on that commit in a worktree. Green there means the same code passes on the data it was
     merged with, so the red comes from data stored since: the run goes on (exit 0) and every failing case is named in
     a warning, because the next run is the only thing that can replace stored data and stopping it publishes nothing
     and fixes nothing. Red there too, or no such commit in reach: exit with the canary's status, as before.

Fail-closed means the wrong thing does not ship; it does not mean nothing ships. The cases still fail hard at push
time and on the weekly check, which is where the next session reads them.

  python3 scripts/canary_gate.py              # the gate; writes out/canary-gate.json
  python3 scripts/canary_gate.py --annotate   # print the verdict as workflow annotations (after stop-commands closes)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# What the desk's runs commit (every `git add` in .github/workflows/): a commit touching only these is a run's, not code.
RUN_WRITTEN = ("site/content/", "site/data/", "data/", "share-queue/", "linkedin-queue/", "review-queue/")
RUN_WRITTEN_FILES = ("ledger.json", "editorial-log.json", "regwatch.json", "linkedin-posted.json")
REACH = 400            # first-parent commits searched for the last code commit (about eighty days of runs)
CANARY = [sys.executable, "verify_pipeline.py", "canary"]


def is_run_written(path):
    return path in RUN_WRITTEN_FILES or path.startswith(RUN_WRITTEN)


def last_code_commit(log):
    """The newest commit that changed a path no run writes. `log` is [(sha, [paths])], newest first."""
    for sha, paths in log:
        if any(not is_run_written(p) for p in paths):
            return sha
    return None


def parse_log(text):
    """[(sha, [paths])] from `git log --first-parent -m --format=@%H --name-only`."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("@"):
            out.append((line[1:], []))
        elif line and out:
            out[-1][1].append(line)
    return out


def failing_cases(output):
    """The canary's own names for what failed, in order, once each."""
    seen, out = set(), []
    for line in output.splitlines():
        s = line.strip()
        for mark in ("::error::canary: ", "FAIL "):
            if s.startswith(mark):
                name = s[len(mark):].strip()
                if name and name not in seen and not name.startswith("(") and "LAYER 1" not in name:
                    seen.add(name)
                    out.append(name)
    return out


def verdict(rc_now, head_is_code, rc_base):
    """'pass', 'data' (the run goes on) or 'wiring' (the run stops). `rc_base` is the canary's status on the last code
    commit, None when it could not be run."""
    if rc_now == 0:
        return "pass"
    if head_is_code or rc_base is None or rc_base != 0:
        return "wiring"
    return "data"


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def _run_canary(cwd, cmd, echo=True):
    env = dict(os.environ, PYTHONPYCACHEPREFIX=tempfile.mkdtemp(prefix="canary-pyc-"))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    out = (p.stdout or "") + (p.stderr or "")
    if echo:
        sys.stdout.write(out)
        sys.stdout.flush()
    return p.returncode, out


def gate(repo=HERE, cmd=None):
    """Run the gate in `repo`. Returns the record written to out/canary-gate.json; its 'exit' is the status to leave with."""
    cmd = cmd or CANARY
    rc, out = _run_canary(repo, cmd)
    rec = {"verdict": "pass", "exit": 0, "cases": [], "head": _git(repo, "rev-parse", "HEAD").stdout.strip()}
    if rc != 0:
        rec["cases"] = failing_cases(out)
        if _git(repo, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
            _git(repo, "fetch", "-q", f"--deepen={REACH}")          # a CI checkout holds one commit; reach back for the code
        log = parse_log(_git(repo, "log", "--first-parent", "-m", "--format=@%H", "--name-only", "-n", str(REACH)).stdout)
        code = last_code_commit(log)
        rec["code_commit"] = code
        rc_base = None
        if code and code != rec["head"]:
            wt = tempfile.mkdtemp(prefix="canary-base-")
            try:
                if _git(repo, "worktree", "add", "--detach", "--force", wt, code).returncode == 0:
                    print(f"\nCANARY GATE: red on the tree as it stands; running the canary on the last code commit {code[:7]}")
                    rc_base, base_out = _run_canary(wt, cmd, echo=False)
                    print(f"CANARY GATE: the canary on {code[:7]} left with status {rc_base}")
                    if rc_base != 0:
                        rec["base_cases"] = failing_cases(base_out)
                        for c in rec["base_cases"]:
                            print(f"CANARY GATE: red on {code[:7]} too: {c}")
            finally:
                _git(repo, "worktree", "remove", "--force", wt)
                shutil.rmtree(wt, ignore_errors=True)
                _git(repo, "worktree", "prune")
        v = verdict(rc, code == rec["head"], rc_base)
        rec.update(verdict=v, canary_exit=rc, base_exit=rc_base, exit=0 if v == "data" else rc)
        if v == "data":
            print(f"CANARY GATE: DATA. The code passes on the tree it was merged with ({code[:7]}); {len(rec['cases'])} "
                  f"case(s) fail on data stored since. The run goes on; the cases are named in the warning.")
        else:
            why = ("HEAD is the last code commit" if code == rec["head"] else
                   "no code commit in reach" if not code else "the last code commit is red too")
            print(f"CANARY GATE: WIRING ({why}). The run stops.")
    os.makedirs(os.path.join(repo, "out"), exist_ok=True)
    json.dump(rec, open(os.path.join(repo, "out", "canary-gate.json"), "w", encoding="utf-8"), indent=1)
    return rec


def annotate(repo=HERE):
    """The verdict as workflow annotations and a step summary. Printed by the step after stop-commands closes."""
    try:
        rec = json.load(open(os.path.join(repo, "out", "canary-gate.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if rec.get("verdict") != "data":
        return 0
    cases = rec.get("cases") or []
    head = (f"canary: {len(cases)} case(s) fail on data the desk stored since code commit "
            f"{str(rec.get('code_commit') or '')[:7]}; the code passes on the tree it was merged with, so this run goes on")
    print(f"::warning::{head}")
    for c in cases[:10]:
        print(f"::warning::canary (stored data): {c}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Canary: stored data\n\n{head}.\n\n" + "".join(f"- {c}\n" for c in cases) + "\n")
    return 0


if __name__ == "__main__":
    if "--annotate" in sys.argv:
        sys.exit(annotate())
    sys.exit(gate()["exit"])
