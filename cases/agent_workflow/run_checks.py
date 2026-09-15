#!/usr/bin/env python3
"""Scripted protocol controls, NOT an evaluation of autonomous agent discovery."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
import agent_workflow as workflow
from find_cache_conditions import PROPERTIES, check_obligation, oracle


def expected_after_run(case, variant, domain):
    if case == "prime":
        # Imported only at independent acceptance, not by the workflow/agent.
        spec = importlib.util.spec_from_file_location("prime_acceptance", ROOT / "cases/prime_lookup/run_checks.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.expected_condition(variant, tuple(map(int, domain.split(":"))))
    if case == "cache":
        return "finder_x == UINT32_MAX"
    return "!finder_valid || finder_x != finder_key || finder_config == finder_cached_config"


def independent_check(directory, config, result):
    backend_type, settings = workflow.adapter(config)
    phase = directory / "independent-acceptance"
    phase.mkdir()
    backend = backend_type(settings, phase)
    published = result["best_result"]["candidate_c"]
    expected = expected_after_run(config["case"], config["variant"], config["domain"])
    source = phase / "harness.c"
    source.write_text(backend.make_harness(backend.model, config["variant"], settings.state_mode,
                      "expected", expected=f"({published}) == ({expected})"), encoding="utf-8")
    command = [config["esbmc"], str(source), "--function", "finder_entry", "--z3",
               "--unwind", str(backend.unwind), "--overflow-check"]
    checked = check_obligation(oracle, command, phase / "verify.log", config["timeout"], PROPERTIES["expected"])
    workflow.save(phase / "result.json", checked)
    return checked


def run_checks(args):
    parent = Path(args.workdir).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="controls-", dir=parent))
    base = {"case": "prime", "variant": "fallback", "domain": "0:127", "state_mode": "invariant",
            "goal": "exact", "esbmc": args.esbmc, "cc": args.cc, "timeout": args.timeout,
            "max_seconds": 300, "max_queries": 64, "max_rounds": 8}
    exact_truncated = {"any": ["x <= 31"] + [f"x % {d} == 0" for d in (2, 3, 5, 7, 11)]}
    config_condition = {"any": [{"not": "valid"}, "x != key", "config == cached_config"]}
    # Expected outcomes and the final candidates are intentionally scripted to
    # exercise protocol/proof boundaries; do not use them as agent input in a
    # discovery benchmark or claim an improvement in solver/LLM performance.
    cases = [
        ("fallback-controls", {}, [(True, {"domain": "0:31"}, "REJECTED"),
                                    (False, {}, "EMPTY_CANDIDATE"), (True, {}, "EXACT")]),
        ("truncated-refinement", {"variant": "truncated"},
         [(True, {"seeds": [{"x": 37}]}, "REFUTED"), ("x <= 31", {}, "PARTIAL"),
          ({"any": ["x <= 31", "x % 2 == 0"]}, {}, "PARTIAL"), (exact_truncated, {}, "EXACT")]),
        ("mutant-refinement", {"variant": "mutant"},
         [(True, {"seeds": [{"x": 9}]}, "REFUTED"), ("x != 9", {}, "EXACT")]),
        ("all-unequal", {"variant": "truncated", "domain": "37:37"}, [(False, {}, "EXACT")]),
        ("cache-empty", {"case": "cache", "variant": "bad_miss", "domain": None, "state_mode": "empty"},
         [(True, {"seeds": [{"x": 1, "valid": 0, "key": 0, "value": 0}]}, "REFUTED"),
          ("x == 4294967295", {}, "EXACT")]),
        ("config-state", {"case": "config-cache", "variant": "stale", "domain": None},
         [(True, {}, "REFUTED"), (config_condition, {}, "EXACT")]),
        ("sufficient-only", {"variant": "truncated", "goal": "sufficient"}, [("x <= 31", {}, "PARTIAL")]),
        ("missing-solver", {"esbmc": "missing-agent-workflow-test-esbmc"}, []),
    ]
    results = []
    for name, changes, proposals in cases:
        config = {**base, **changes}
        row = {"case": name, "passed": False, "kind": "scripted protocol control", "rounds": []}
        try:
            directory, result = workflow.start(config, output / name)
            row["artifacts"] = str(directory)
            if name == "missing-solver":
                row["passed"] = result["status"] == "UNKNOWN" and result["phase"] == "UNKNOWN" and result["condition"] is None
            else:
                if result["phase"] != "READY":
                    raise RuntimeError(f"session initialization is {result['phase']}")
                for index, (condition, extra, expected) in enumerate(proposals, 1):
                    proposal = {"session_id": result["session_id"], "round": index, "condition": condition, **extra}
                    path = output / name / f"scripted-proposal-{index}.json"
                    workflow.save(path, proposal)
                    before = result["queries_used"]
                    result = workflow.step(directory, path)
                    latest = result["latest_feedback"]
                    actual = latest["status"]
                    row["rounds"].append({"expected": expected, "actual": actual,
                                           "queries_added": result["queries_used"] - before})
                    if actual != expected:
                        raise RuntimeError(f"round {index}: expected {expected}, got {actual}")
                    if expected in ("REJECTED", "REFUTED") and result["queries_used"] != before:
                        raise RuntimeError("scripted native/validation rejection unexpectedly used solver queries")
                row["passed"] = result["goal_reached"]
                if result["status"] == "EXACT":
                    row["independent_acceptance"] = independent_check(directory, config, result)
                    row["passed"] &= row["independent_acceptance"]["status"] == "PROVED"
                elif config["goal"] == "sufficient":
                    row["passed"] &= "complement" not in result["best_result"]["checks"]
            row["result"] = result
        except (OSError, ValueError, RuntimeError) as exc:
            row["reason"] = str(exc)
        results.append(row)
        workflow.save(output / "results.json", results)
        print(f"{name}: {'PASS' if row['passed'] else 'FAIL'}", flush=True)
    workflow.save(parent / "results.json", results)
    count = sum(row["passed"] for row in results)
    print(f"AGENT WORKFLOW ACCEPTANCE: {count}/{len(results)} passed")
    print("Scripted protocol controls; no autonomous-agent performance claim.")
    print(f"Artifacts: {output}")
    return 0 if count == len(results) else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--workdir", default=".verify-equiv-runs/agent-acceptance")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("positive finite timeout required")
    return run_checks(args)


if __name__ == "__main__":
    sys.exit(main())
