#!/usr/bin/env python3
"""M2 result/diagnostic acceptance using existing scalar programs and ESBMC."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from c_backend import save_json
from find_c_conditions import main as find_main
from result_contract import validate_summary
import agent_workflow as workflow


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--workdir", default=".verify-equiv-runs/m2-results")
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="checks-", dir=root))
    shutil.copyfile(ROOT / "schemas/verification-result-v1.schema.json", directory / "verification-result-v1.schema.json")
    results = []
    cases = [
        ("all-inputs", "c_scalar/parity.json", "EXACT", "ALL_INPUTS", None, []),
        ("conditional", "c_scalar/max_min.json", "EXACT", "REGION", None, []),
        ("no-inputs", "c_scalar_transfer/unequal_31.json", "EXACT", "NO_INPUTS", None, []),
        ("query-budget", "c_scalar/max_min.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", "QUERY_BUDGET_EXHAUSTED", ["--max-queries", "4"]),
        ("unsafe-division", "c_scalar/unsafe_division.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", "SAFETY_OR_OTHER_PROPERTY_FAILURE", []),
        ("short-unwind", "c_scalar/insufficient_unwind.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", "UNWINDING_INCOMPLETE", []),
        ("missing-solver", "c_scalar/max_min.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", "SOLVER_NOT_FOUND", []),
        ("empty-domain", "result_contract/empty_domain.json", "EMPTY_DOMAIN", "NO_EQUIVALENCE_CLAIM", "EMPTY_DOMAIN", []),
        ("unsupported", "result_contract/unsupported.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", "UNSUPPORTED_INPUT", []),
    ]
    for name, contract, status, meaning, code, extra in cases:
        work = directory / name
        print(f"\n{name}", flush=True)
        solver = "intentionally-missing-m2-esbmc" if name == "missing-solver" else args.esbmc
        rc = find_main(["--contract", str(ROOT / "cases" / contract), "--workdir", str(work),
                        "--esbmc", solver, "--cc", args.cc, *extra])
        summary = validate_summary(json.loads((work / "verification-result.json").read_text(encoding="utf-8")))
        legacy = json.loads((work / "result.json").read_text(encoding="utf-8"))
        codes = {d["code"] for d in summary["diagnostics"]}
        passed = (summary["status"] == status and summary["claim"]["meaning"] == meaning
                  and (code is None or code in codes) and rc == (0 if status == "EXACT" else 2)
                  and (work / "report.md").is_file())
        if name in ("unsafe-division", "short-unwind", "missing-solver", "empty-domain", "unsupported"):
            passed = passed and summary["metrics"]["native_samples"] == 0
        if name == "query-budget":
            passed = passed and summary["metrics"]["queries"] == 4 and summary["domain"]["status"] == "NONEMPTY"
        results.append(dict(name=name, passed=passed, result=summary, legacy_status=legacy["status"], exit_code=rc))
        print(f"{name}: {'PASS' if passed else 'NOT ESTABLISHED'}", flush=True)

    config = dict(case="c", contract=str(ROOT / "cases/c_scalar/max_min.json"), variant="pair", state_mode="stateless",
                  domain=None, goal="exact", esbmc=args.esbmc, cc=args.cc, timeout=30,
                  max_seconds=300, max_queries=64, max_rounds=3)
    session, initial = workflow.start(config, directory / "agent-partial")
    if initial["phase"] == "READY":
        proposal = directory / "partial-proposal.json"
        save_json(proposal, dict(session_id=initial["session_id"], round=1, condition={"all": ["x == 0", "y == 0"]}))
        workflow.step(session, proposal)
    partial = validate_summary(json.loads((session / "verification-result.json").read_text(encoding="utf-8")))
    passed = (partial["status"] == "PARTIAL" and partial["claim"]["meaning"] == "SUFFICIENT_REGION"
              and partial["obligations"]["sufficiency"]["status"] == "PROVED"
              and partial["obligations"]["complement"]["status"] == "NOT_CHECKED"
              and "COMPLETENESS_NOT_ESTABLISHED" in {d["code"] for d in partial["diagnostics"]})
    results.append(dict(name="agent-partial", passed=passed, result=partial))
    print(f"agent-partial: {'PASS' if passed else 'NOT ESTABLISHED'}")
    binary = shutil.which(args.esbmc)
    report = dict(passed=sum(r["passed"] for r in results), total=len(results), results=results, artifacts=str(directory),
                  esbmc=None if not binary else dict(path=str(Path(binary).resolve()), sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest()),
                  provenance="Executed acceptance checks; the agent candidate is a scripted protocol control.")
    save_json(directory / "results.json", report)
    save_json(root / "results.json", report)
    print(f"M2 RESULT ACCEPTANCE: {report['passed']}/{report['total']} passed")
    print(f"Artifacts: {directory}")
    return 0 if report["passed"] == report["total"] else 2


if __name__ == "__main__":
    sys.exit(main())
