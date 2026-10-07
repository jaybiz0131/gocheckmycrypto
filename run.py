#!/usr/bin/env python3
"""
run.py: the orchestrator for Stages 1-5. FAIL-CLOSED. NEVER PUBLISHES.

Runs aggregate -> editor -> verifier -> researcher -> writer -> approver -> digest in order
and writes a run report.
If ANY stage errors, it stops, records status=failed, and exits non-zero so CI flags a human.
It deliberately does NOT call publish.py: publishing is a separate, human-approved step (Stage
6), the whole point of the design. The scheduled job runs THIS; a human reviews the digest and
runs publish.py only after approving.

USAGE
  python3 run.py                         # live run (needs ANTHROPIC_API_KEY)
  python3 run.py --mode replay           # offline end-to-end over fixtures (no key, no spend)
  python3 run.py --fixture fixtures/sample_feed.xml --mode replay   # full offline wiring test
  python3 run.py --mode replay --path story     # the breaking path (BREAKING=1 picks it too)
"""

import os
import sys
import traceback

import common
import llm as llmlib
import aggregate
import editor
import verifier
import researcher
import writer
import approver
import digest


# THE WIRE PATH (Jack, 5 October 2026, program section 9): "the desk vets, we publish, we
# do not rewrite, we show the source". The daily written story ends. The scheduled Edition
# run ranks and verifies, then writes the wire (wire.json) with one checked note for the top
# item that clears the verifier; the researcher, the writer and the approver are turned off
# on this path, NOT deleted: their code stays, the run does not call them, and the run
# report and the ledger name them absent. The verifier's cost is the note's cost.
# THE STORY PATH stays for the caged breaking runs (BREAKING=1), which continue as they are.
STORY_ONLY_STAGES = ["3.5-researcher", "4-writer", "4.5-approver", "5-digest"]


def run_path(path=None):
    """'story' for a breaking run (or when named), else 'wire'."""
    p = (path or os.environ.get("CRYPTO_RUN_PATH") or "").strip().lower()
    if p in ("wire", "story"):
        return p
    return "story" if os.environ.get("BREAKING") == "1" else "wire"


def run_wire(client, report, record):
    """Stage 4 on the wire path: the wire and its checked note, no model call."""
    import wire
    import twins_gate
    items = common.read_out("items.json")
    gate = twins_gate.Gate(twins_gate.current_snapshot())
    obj = wire.build(common.read_out("editor.json"), items,
                     common.read_out("verifier.json"), gate.snap,
                     items["_meta"]["generated"], gate=gate)
    gate.save()
    wire.write(obj)
    common.write_out("wire.json", obj)
    record("4-wire", True, f"{len(obj['items'])} on the wire, "
                           f"{'one checked' if obj.get('checked') else 'none checked'}, "
                           f"{len(obj['dropped'])} dropped")
    print(f"[run] wire: {len(obj['items'])} item(s), checked note "
          f"{'on #' + str(obj['checked']['rank']) if obj.get('checked') else 'absent'}, "
          f"{len(gate.drops)} twins-gate drop(s)")
    return obj


def run(mode="live", fixture=None, path=None):
    os.environ["CRYPTO_LLM_MODE"] = mode
    cfg = common.load_config()
    client = llmlib.Client(cfg, mode=mode)  # one client => one shared budget across stages
    path = run_path(path)
    report = {"mode": mode, "path": path, "stages": [], "status": "running",
              "stages_absent": STORY_ONLY_STAGES if path == "wire" else []}

    def record(name, ok, detail=""):
        report["stages"].append({"stage": name, "ok": ok, "detail": detail})

    attempted = "1-aggregate"
    try:
        rc = aggregate.run(fixture=fixture, out_path=os.path.join(common.OUT_DIR, "items.json"))
        if rc != 0:
            record("1-aggregate", False, f"exit {rc}")
            raise RuntimeError("aggregation failed (zero sources or empty intake)")
        record("1-aggregate", True)

        attempted = "2-editor"
        editor.run(client=client);     record("2-editor", True)
        attempted = "3-verifier"
        verifier.run(client=client);   record("3-verifier", True)
        if path == "wire":
            attempted = "4-wire"
            try:
                run_wire(client, report, record)
            except Exception as e:
                # THE WIRE IS NOT THE EDITION: a wire that cannot be written leaves the
                # previous wire.json standing and the Brief still runs after this step.
                record("4-wire", False, f"{type(e).__name__}: {e}")
                common.gh("warning", f"run: the wire was not written ({type(e).__name__}: "
                                     f"{e}); the previous wire.json stands")
                traceback.print_exc()
            report["status"] = "wire-written"
            report["budget"] = client.budget.summary()
            common.write_out("run_report.json", report)
            print(f"\n[run] OK - mode={mode}, path=wire, budget={client.budget.summary()}")
            print(f"[run] Stages absent on the wire path: {', '.join(STORY_ONLY_STAGES)}")
            return 0

        attempted = "3.5-researcher"
        researcher.run(client=client); record("3.5-researcher", True)
        attempted = "4-writer"
        writer.run(client=client);     record("4-writer", True)
        attempted = "4.5-approver"
        approver.run(client=client);   record("4.5-approver", True)

        date = common.read_out("items.json")["_meta"]["generated"][:10]
        attempted = "5-digest"
        digest.run(date=date);         record("5-digest", True)

        report["status"] = "ready-for-human-review"
        report["budget"] = client.budget.summary()
        report["review_queue"] = f"out/review_queue/{date}.md"
        common.write_out("run_report.json", report)
        print(f"\n[run] OK - mode={mode}, budget={client.budget.summary()}")
        print(f"[run] Review queue ready: out/review_queue/{date}.md")
        print(f"[run] Nothing published. Approve in out/approval_template.json, then run publish.py.")
        return 0
    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)
        try:
            common.write_out("run_report.json", report)
        except Exception:
            pass
        common.gh("error", f"run: pipeline FAILED at {attempted}: {e} "
                  f"-> FAIL-CLOSED, nothing published.")
        traceback.print_exc()
        return 1


def main():
    argv = sys.argv[1:]
    mode = argv[argv.index("--mode") + 1] if "--mode" in argv else "live"
    fixture = argv[argv.index("--fixture") + 1] if "--fixture" in argv else None
    path = argv[argv.index("--path") + 1] if "--path" in argv else None
    sys.exit(run(mode=mode, fixture=fixture, path=path))


if __name__ == "__main__":
    main()
