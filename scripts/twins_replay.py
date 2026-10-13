#!/usr/bin/env python3
"""Replay every recorded Edition and morning read from 7 October to today through the OLD twins
gate (origin/main's twins_gate.py) and the NEW one (this tree's), against the snapshot each
Edition was written under (fixtures/twins/snapshot_<day>.json, rebuilt from that run's committed
pulse.json and flows.json).

  python3 scripts/twins_replay.py [old_gate_ref]      # default origin/main

Prints one row for every sentence on which the two gates differ, and the seven recorded drops
of 9 and 10 October; then the counts of the sentences both gates keep. The "right" column is
filled by hand in docs/REPORT (a person checked each differing sentence against the data); this
script only prints verdicts.

Recorded Editions: 8, 9, 10 and 11 October (7 October's Brief was withheld, 12 October's run
failed at the canary). Recorded morning reads: none (the morning run has not fired in
production; docs/HANDOFF.md section 10).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

COMMITS = {"2026-10-08": "b281882", "2026-10-09": "cbf7e80", "2026-10-10": "8533a17",
           "2026-10-11": "7d8971b"}


def load_old(ref):
    src = subprocess.check_output(["git", "show", f"{ref}:twins_gate.py"], cwd=HERE).decode()
    path = os.path.join(tempfile.mkdtemp(prefix="old-gate-"), "twins_gate_old.py")
    open(path, "w").write(src)
    spec = importlib.util.spec_from_file_location("twins_gate_old", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_json(sha, path):
    try:
        return json.loads(subprocess.check_output(["git", "show", f"{sha}:{path}"], cwd=HERE,
                                                  stderr=subprocess.DEVNULL))
    except Exception:
        return None


def surfaces(day, sha):
    """[(surface, text, flags)] for one Edition: the published Brief, the narrative line, the
    wire lines and the checked note."""
    ed = git_json(sha, f"site/content/{day}-evening-brief.json") or {}
    out = []
    for k in ("title", "dek", "key_fact", "bottom_line", "human_take"):
        if isinstance(ed.get(k), str) and ed[k].strip():
            out.append((f"Brief {k}", ed[k], {"dollars": k in ("title", "dek", "key_fact")}))
    body = ed.get("body")
    paras = body.split("\n") if isinstance(body, str) else (body or [])
    for i, p in enumerate(paras, 1):
        if str(p).strip():
            out.append((f"Brief body {i}", p, {"dollars": False}))
    nj = git_json(sha, "site/data/narrative.json") or {}
    if nj.get("line"):
        out.append(("narrative line", nj["line"], {}))
    wj = git_json(sha, "site/data/wire.json") or {}
    for it in wj.get("items") or []:
        out.append((f"wire #{it.get('rank')}", it.get("line") or "", {}))
    note = (wj.get("checked") or {})
    for k in ("says", "means", "note"):
        if isinstance(note.get(k), str) and note[k].strip():
            out.append((f"checked note {k}", note[k], {}))
    return [(s, t, f) for s, t, f in out if t and t.strip()]


# the seven recorded drops (scripts/twins_gate_test.py holds the same text and its provenance)
def recorded():
    sys.path.insert(0, os.path.join(HERE, "scripts"))
    import twins_gate_test as T
    return [(cid, day, surface, s) for cid, day, surface, s, _n in T.KEEP]


def verdict(mod, snap, text, surface, **kw):
    g = mod.Gate(snap, log_path="", quiet=True)
    kept = g.text(text, surface, **kw)
    return ("KEEP" if kept.strip() == text.strip() else
            "DROP(unparsed)" if getattr(g, "unparsed", 0) else "DROP"), g.drops


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    old = load_old(ref)
    import twins_gate as new
    rows, same_keep, same_drop = [], 0, []
    for day, sha in COMMITS.items():
        snap = json.load(open(os.path.join(HERE, "fixtures", "twins", f"snapshot_{day}.json")))
        sents = []
        for surface, text, kw in surfaces(day, sha):
            for s in new.sentences(text):
                sents.append((surface, s, kw))
        for surface, s, kw in sents:
            vo, do = verdict(old, snap, s, surface, **kw)
            vn, dn = verdict(new, snap, s, surface, **kw)
            if vo != vn:
                rows.append((day, surface, s, vo, vn, (do or dn)[0]["why"]))
            elif vo == "KEEP":
                same_keep += 1
            else:
                same_drop.append((day, surface, s, vo))
    print(f"REPLAY, old gate = {ref}:twins_gate.py, new gate = this tree")
    print("\n## the seven recorded drops of 9 and 10 October")
    for cid, day, surface, s in recorded():
        snap = json.load(open(os.path.join(HERE, "fixtures", "twins", f"snapshot_{day}.json")))
        vo, do = verdict(old, snap, s, surface)
        vn, dn = verdict(new, snap, s, surface)
        print(f"{cid} | {day} {surface} | old {vo} | new {vn} | {s}")
    print("\n## published sentences on which the gates differ")
    for r in rows:
        print(" | ".join(str(x) for x in r))
    print(f"\n## published sentences both gates KEEP: {same_keep}")
    print(f"## published sentences both gates DROP: {len(same_drop)}")
    for r in same_drop:
        print("  ", " | ".join(str(x) for x in r))
    n = sum(len([1 for _ in new.sentences(t)]) for d, sha in COMMITS.items()
            for _s, t, _k in surfaces(d, sha))
    print(f"## sentences replayed: {n} across {len(COMMITS)} Editions")


if __name__ == "__main__":
    main()
