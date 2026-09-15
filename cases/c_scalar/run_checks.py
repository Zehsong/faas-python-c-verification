#!/usr/bin/env python3
"""Formal acceptance of configuration-only C pairs and fail-closed controls.

Expected formulas are confined to this acceptance runner; discovery never reads
them. Agent proposals here are scripted protocol tests, not agent performance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from c_scalar_backend import bind_contract
from condition_runner import run
from find_c_conditions import parse_args
from c_backend import save_json
import agent_workflow as workflow

CASE = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--workdir", default=".verify-equiv-runs/c-scalar-acceptance")
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="checks-", dir=root))
    results = []
    def record(name, passed, **details):
        results.append(dict(name=name, passed=passed, **details))
        print(f"{name}: {'PASS' if passed else 'NOT PROVED'}", flush=True)

    for name, expected in (("max_min", "finder_x == finder_y"), ("parity", "true"),
                           ("series", "true"), ("series_mutant", "finder_n == UINT32_C(0)"),
                           ("insufficient_unwind", None), ("unsafe_division", None)):
        settings = parse_args(["--contract", str(CASE / f"{name}.json"), "--esbmc", args.esbmc,
                               "--cc", args.cc, "--workdir", str(directory / name)])
        backend_type = bind_contract(settings.contract)
        report = run(settings, backend_type)
        match = None
        if expected is not None and report["status"] == "EXACT":
            checkdir = Path(report["artifacts"]) / "held-out-validation"
            checkdir.mkdir()
            backend = backend_type(settings, checkdir)
            backend.prepare()
            match = backend.query("expected", report["condition_c"], expected=expected)
            passed = match["status"] == "PROVED"
        elif expected is None:
            safety = report.get("state_obligations", {}).get("safety", {})
            # Require a real backend safety/unwinding violation, not missing ESBMC.
            passed = (report["status"] == "UNKNOWN" and report.get("traces_collected") == 0
                      and safety.get("status") == "UNKNOWN" and safety.get("returncode") not in (None, 0)
                      and not safety.get("timed_out") and bool(safety.get("violation")))
        else:
            passed = False
        record(name, passed, report=report, expected_condition_check=match)

    config = dict(case="c", contract=str(CASE / "max_min.json"), variant="pair", state_mode="stateless",
                  domain=None, goal="exact", esbmc=args.esbmc, cc=args.cc, timeout=30,
                  max_seconds=300, max_queries=64, max_rounds=8)
    session, started = workflow.start(config, directory / "agent")
    stepped = None
    if started["phase"] == "READY":
        proposal = directory / "proposal.json"
        save_json(proposal, dict(session_id=started["session_id"], round=1, condition="x == y", seeds=[]))
        stepped = workflow.step(session, proposal)
    record("agent-scalar-contract", bool(stepped and stepped["status"] == "EXACT"), initialization=started, result=stepped)
    _, missing = workflow.start({**config, "esbmc": "intentionally-missing-c-scalar-esbmc"}, directory / "missing-solver")
    record("missing-solver", missing["status"] == "UNKNOWN" and missing["phase"] == "UNKNOWN" and missing["queries_used"] == 0, result=missing)
    binary = shutil.which(args.esbmc)
    report = dict(passed=sum(row["passed"] for row in results), total=len(results), results=results,
                  esbmc=None if not binary else dict(path=str(Path(binary).resolve()), sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest()),
                  artifacts=str(directory), provenance="Run locally by this acceptance process; scripted agent proposal.")
    save_json(directory / "results.json", report)
    save_json(root / "results.json", report)
    print(f"C SCALAR ACCEPTANCE: {report['passed']}/{report['total']} passed")
    print(f"Artifacts: {directory}")
    return 0 if report["passed"] == report["total"] else 2


if __name__ == "__main__":
    sys.exit(main())
