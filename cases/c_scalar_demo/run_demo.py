#!/usr/bin/env python3
"""Assemble a browsable demo from real finder artifacts; no new proof engine."""
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


CASES = (
    ("all-inputs", "c_scalar/parity.json", "EXACT", "ALL_INPUTS", []),
    ("conditional", "c_scalar/max_min.json", "EXACT", "REGION", []),
    ("no-equal-inputs", "c_scalar_transfer/unequal_31.json", "EXACT", "NO_INPUTS", []),
    ("budget-limited", "c_scalar/max_min.json", "UNKNOWN", "NO_EQUIVALENCE_CLAIM", ["--max-queries", "4"]),
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def snapshot_pair(source, destination):
    """Make a portable, editable pair without overwriting repository fixtures."""
    destination.mkdir(parents=True)
    contract = read_json(source)
    shutil.copyfile(source, destination / "source-contract.json")
    for side in ("original", "candidate"):
        original = source.parent / contract[side]["source"]
        shutil.copyfile(original, destination / f"{side}.c")
        contract[side]["source"] = f"{side}.c"
    path = destination / "contract.json"
    save_json(path, contract)
    return path


def binary_identity(command):
    binary = shutil.which(command)
    if binary is None:
        return {"requested": command, "path": None, "sha256": None}
    path = Path(binary).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"requested": command, "path": str(path), "sha256": digest.hexdigest()}


def replayed_counterexample(summary, queries):
    """Select only an equality refutation actually replayed by the backend."""
    scope = summary.get("scope") or {}
    inputs = scope.get("inputs", {})
    safety = summary["obligations"]["state"].get("safety", {})
    if safety.get("status") != "PROVED" or not inputs:
        return None
    for index, query in enumerate(queries):
        row, witness = query.get("native_replay"), query.get("witness")
        if query.get("kind") != "equal" or query.get("status") != "REFUTED":
            continue
        if not isinstance(row, dict) or not isinstance(witness, dict):
            continue
        if any(type(row.get(k)) is not int or row[k] != witness.get(k)
               or not spec["min"] <= row[k] <= spec["max"] for k, spec in inputs.items()):
            continue
        if any(type(row.get(k)) is not int for k in ("r_original", "r_cached")):
            continue
        if row["r_original"] == row["r_cached"]:
            continue
        return {"inputs": {k: row[k] for k in inputs}, "original_return": row["r_original"],
                "candidate_return": row["r_cached"], "query_index": index,
                "query_directory": f"query-{index:03d}-equal",
                "provenance": "ESBMC equality counterexample replayed by the native backend; one input, not a region proof"}
    return None


def render_overview(results, witness):
    lines = ["# C conditional-equivalence demo", "",
             "These are executed integration examples, not a held-out benchmark.", "",
             "Open each report for its domain, observations, safety checks and proof obligations.",
             "Conditions below are copied from versioned results; expected answers are not supplied to discovery.", "",
             "| Example | Actual result | Meaning | Demo expectation met | Report |",
             "|---|---|---|---|---|"]
    for item in results:
        name, summary = item["name"], item.get("summary")
        status = summary["status"] if summary else "DEMO_ERROR"
        meaning = summary["claim"]["meaning"] if summary else "No result available"
        link = f"[report]({name}/report.md)" if summary else "See results.json"
        lines.append(f"| {name} | {status} | {meaning} | {'yes' if item['passed'] else 'no'} | {link} |")
    for item in results:
        name, summary = item["name"], item.get("summary")
        lines += ["", f"## {name}", ""]
        if not summary:
            lines += [item["error"]]
            continue
        scope = summary.get("scope") or {}
        fields = scope.get("inputs", {})
        lines += ["Input domain: " + "; ".join(f"{k}: {s['type']} in {s['min']}..{s['max']}" for k, s in fields.items()),
                  "", "Observation: " + str(scope.get("observations", "not established")), ""]
        condition = summary["claim"]["condition"]
        lines += ["Certified condition:", "", "```text", condition, "```"] if condition is not None else ["No certified condition."]
        codes = list(dict.fromkeys(d["code"] for d in summary["diagnostics"]))
        if codes:
            lines += ["", "Diagnostics: " + ", ".join(codes)]
        lines += ["", f"Editable pair: [contract]({name}/inputs/contract.json), "
                  f"[original]({name}/inputs/original.c), [candidate]({name}/inputs/candidate.c)."]
    lines += ["", "## Replayed counterexample to unconditional equality", ""]
    if witness:
        query = "conditional/" + witness["artifact_directory"] + "/" + witness["query_directory"]
        lines += ["```json", json.dumps(witness["inputs"], indent=2), "```", "",
                  f"Original returns {witness['original_return']}; candidate returns {witness['candidate_return']}.", "",
                  f"[Solver log]({query}/verify.log) and [query evidence]({query}/result.json).",
                  "The backend already executed this input after proving whole-domain safety.",
                  "One unequal input refutes unconditional equality; it does not classify a whole region."]
    else:
        lines += ["No suitable solver counterexample with successful native replay was recorded."]
    lines += ["", "## Reading the results", "",
              "EXACT certifies equality inside the condition and inequality outside it within the declared domain.",
              "PARTIAL certifies equality only inside the condition; outside remains incompletely classified.",
              "UNKNOWN publishes no certified condition. NO_INPUTS means a nonempty domain with no equal inputs.",
              "The budget-limited example is expected to remain UNKNOWN with QUERY_BUDGET_EXHAUSTED.",
              "Missing tools or other failures do not satisfy that demonstration expectation.", "",
              "Scope: supported pure scalar C, return observation only. No new arrays, pointers or state support.",
              "Per-query harnesses, commands, logs and native replays remain in the individual run directories.",
              "Some raw evidence paths describe the original machine; the links in this overview are archive-relative.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--workdir", default=".verify-equiv-runs/c-demo")
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="demo-", dir=root))
    identities = {name: binary_identity(getattr(args, name)) for name in ("esbmc", "cc")}
    shutil.copyfile(__file__, directory / "run_demo.py")
    results, witness = [], None
    for name, fixture, expected_status, expected_meaning, extra in CASES:
        work = directory / name
        print(f"\n{name}", flush=True)
        item = {"name": name, "passed": False, "fixture": fixture}
        try:
            contract = snapshot_pair(ROOT / "cases" / fixture, work / "inputs")
            command = ["--contract", str(contract), "--esbmc", args.esbmc, "--cc", args.cc,
                       "--workdir", str(work), *extra]
            save_json(work / "invocation.json", [sys.executable, str(ROOT / "tools/find-cond-equiv/find_c_conditions.py"), *command])
            rc = find_main(command)
            summary = validate_summary(read_json(work / "verification-result.json"))
            item.update(summary=summary, exit_code=rc)
            item["passed"] = (summary["status"] == expected_status and summary["claim"]["meaning"] == expected_meaning
                              and rc == (0 if expected_status == "EXACT" else 2) and (work / "report.md").is_file())
            if name == "budget-limited":
                item["passed"] = item["passed"] and summary["metrics"]["queries"] == 4 and any(
                    d["code"] == "QUERY_BUDGET_EXHAUSTED" for d in summary["diagnostics"])
            if name == "conditional":
                artifacts = Path(summary["artifacts"]["directory"])
                queries = artifacts / "queries.json"
                witness = replayed_counterexample(summary, read_json(queries)) if queries.is_file() else None
                if witness:
                    witness["artifact_directory"] = artifacts.relative_to(work).as_posix()
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            item.update(passed=False, error=f"Demo assembly failed: {exc}")
        results.append(item)
        print(f"{name}: {'PASS' if item['passed'] else 'NOT ESTABLISHED'}", flush=True)
    after = {name: binary_identity(getattr(args, name)) for name in identities}
    report = {"results": results, "counterexample": witness, "tools_before": identities, "tools_after": after,
              "tools_unchanged": identities == after, "artifacts": str(directory),
              "passed": sum(item["passed"] for item in results) + int(witness is not None), "total": 5,
              "provenance": "Demo over existing integration fixtures; backend evidence only, no autonomous agent or new research benchmark"}
    report["ready"] = report["passed"] == report["total"] and report["tools_unchanged"]
    save_json(directory / "results.json", report)
    save_json(root / "results.json", report)
    (directory / "README.md").write_text(render_overview(results, witness), encoding="utf-8")
    print(f"Replayed counterexample: {'PASS' if witness else 'NOT ESTABLISHED'}")
    print(f"C SCALAR DEMO: {'READY' if report['ready'] else 'INCOMPLETE'} ({report['passed']}/5 checks; tools unchanged={report['tools_unchanged']})")
    print(f"Open overview: {directory / 'README.md'}")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
