#!/usr/bin/env python3
"""Codespace acceptance: discover first, then independently check held-out answers.

The expected conditions below are never imported by the search implementation.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from find_cache_conditions import save_json, check_obligation, oracle, PROPERTIES

CASES = [
    ("good", "invariant", "true"),
    ("bad_miss", "invariant", "(finder_valid && finder_key == finder_x) || finder_x == UINT32_MAX"),
    ("bad_hit", "invariant", "!(finder_valid && finder_key == finder_x) || finder_x == UINT32_MAX"),
    ("bad_miss_two", "invariant", "(finder_valid && finder_key == finder_x) || finder_x == UINT32_C(1)"),
    ("bad_miss", "empty", "finder_x == UINT32_MAX"),
]


def main(cases=CASES, adapter=None, default_workdir=".verify-equiv-runs/finder-acceptance", label="FINDER ACCEPTANCE"):
    if adapter is None:
        import find_cache_conditions as adapter
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--workdir", default=default_workdir)
    args = parser.parse_args()
    output = Path(args.workdir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for variant, state_mode, expected in cases:
        name = f"{variant}-{state_mode}"
        print(f"\n{name}", flush=True)
        settings = adapter.parse_args(["--variant", variant, "--state-mode", state_mode,
                               "--esbmc", args.esbmc, "--cc", args.cc, "--timeout", str(args.timeout),
                               "--max-seconds", str(args.max_seconds), "--workdir", str(output / name)])
        report = adapter.run(settings)
        acceptance = {"status": "UNKNOWN", "reason": "finder did not certify an exact condition"}
        if report["status"] == "EXACT" and report.get("condition_c"):
            directory = Path(report["artifacts"]) / "held-out-acceptance"
            directory.mkdir()
            model = (Path(report["artifacts"]) / "inputs/cache_model.h").read_text(encoding="utf-8")
            source = directory / "harness.c"
            source.write_text(adapter.make_harness(model, variant, state_mode, "expected",
                expected=f"({report['condition_c']}) == ({expected})"), encoding="utf-8")
            command = [report["esbmc"], str(source), "--function", "finder_entry", "--z3",
                       "--unwind", "12", "--overflow-check"]
            acceptance = check_obligation(oracle, command, directory / "verify.log",
                                           args.timeout, PROPERTIES["expected"])
            save_json(directory / "result.json", acceptance)
        passed = report["status"] == "EXACT" and acceptance["status"] == "PROVED"
        results.append({"case": name, "passed": passed, "status": report["status"],
                        "discovered_condition": report["condition"],
                        "held_out_validation": acceptance, "artifacts": report["artifacts"]})
        print(f"{name}: {'PASS' if passed else 'NOT PROVED'}", flush=True)
    save_json(output / "results.json", results)
    passed_count = sum(row["passed"] for row in results)
    print(f"\n{label}: {passed_count}/{len(results)} passed")
    return 0 if passed_count == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
