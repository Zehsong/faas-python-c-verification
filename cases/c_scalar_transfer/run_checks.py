#!/usr/bin/env python3
"""Post-freeze scalar transfer experiment; no finder/backend modifications.

Expected formulas below are used only after discovery. The ordered vocabulary
uses every pair of input names, without inspecting bodies or expected answers.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
CASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from c_backend import save_json
from c_scalar_backend import bind_contract
from condition_runner import run
from find_c_conditions import parse_args


def text_hash(path):
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def check_engine(root=ROOT, lock_path=CASE / "engine-lock.json"):
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    changed = [name for name, digest in lock["files"].items()
               if not (root / name).is_file() or text_hash(root / name) != digest]
    actual = {p.relative_to(root).as_posix() for p in (root / "tools/find-cond-equiv").glob("*.py")
              if not p.name.startswith("test_")}
    changed += sorted(actual - set(lock["files"]))
    if changed:
        raise ValueError("frozen engine differs from recorded baseline: " + ", ".join(changed))
    return lock


def ordered_hypotheses(fields):
    return {"predicates": [f"{a} <= {b}" for a, b in itertools.permutations(fields, 2)], "seeds": []}


def schedule(repeats):
    for repeat in range(1, repeats + 1):
        for name in ("equivalent_31", "unequal_31"):
            yield repeat, name, "baseline", True
        for index, name in enumerate(("reordered_7", "reordered_31")):
            methods = ("baseline", "ordered") if (repeat + index) % 2 else ("ordered", "baseline")
            for method in methods:
                yield repeat, name, method, method == "ordered"


def expected_condition(name):
    if name == "equivalent_31":
        return "true"
    if name == "unequal_31":
        return "false"
    if name in ("reordered_7", "reordered_31"):
        return "(finder_low <= finder_high) || (finder_x <= finder_high) || (finder_x >= finder_low)"
    raise ValueError("unknown transfer case")


def diagnostics(report):
    reasons = [report["reason"]] if report.get("reason") else []
    for name, query in report.get("state_obligations", {}).items():
        if query.get("status") != "PROVED":
            reasons.append(f"{name}: {query.get('reason', query.get('status'))}")
    for event in report.get("search", {}).get("history", []):
        if event.get("status") == "UNKNOWN" or event.get("reason"):
            evidence = event.get("evidence", {})
            reasons.append(event.get("reason") or evidence.get("reason") or "unresolved predicate region")
    for name, query in report.get("final_validation", {}).items():
        if query.get("status") != "PROVED":
            reasons.append(f"{name}: {query.get('reason', query.get('status'))}")
    return list(dict.fromkeys(reasons))


def assess(report, validation, required):
    safe = report.get("state_obligations", {}).get("safety", {}).get("status") == "PROVED"
    status = report["status"]
    if status == "EXACT":
        credible = (report.get("exact") is True and validation is not None
                    and validation.get("status") == "PROVED"
                    and all(report.get("final_validation", {}).get(k, {}).get("status") == "PROVED"
                            for k in ("sufficiency", "complement")))
    elif status == "PARTIAL":
        credible = validation is not None and validation.get("status") == "PROVED"
    else:
        credible = status == "UNKNOWN" and not report.get("exact") and bool(diagnostics(report))
    integrity = safe and credible
    return integrity, integrity and (not required or status == "EXACT")


def binary_identity(command):
    path = shutil.which(command)
    return None if path is None else {"path": str(Path(path).resolve()),
                                      "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def execute(args):
    lock = check_engine()
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="comparison-", dir=root))
    inputs = directory / "experiment-inputs"
    inputs.mkdir()
    sources = [p for p in CASE.iterdir() if p.suffix in (".c", ".json", ".py", ".sh", ".md")]
    before = {p.name: text_hash(p) for p in sources}
    for source in sources:
        shutil.copyfile(source, inputs / source.name)
    save_json(inputs / "engine-lock.json", lock)
    identities = {name: binary_identity(getattr(args, name)) for name in ("cc", "esbmc")}
    import pycparser
    environment = {"python": sys.version, "pycparser_version": pycparser.__version__}
    results = []
    seeds_by_case = {}
    for repeat, name, method, required in schedule(args.repeats):
        check_engine()
        label = f"r{repeat}-{name}-{method}"
        work = directory / label
        work.mkdir()
        settings = parse_args(["--contract", str(CASE / f"{name}.json"), "--esbmc", args.esbmc,
                               "--cc", args.cc, "--timeout", str(args.timeout),
                               "--max-seconds", str(args.max_seconds), "--max-queries", str(args.max_queries),
                               "--max-predicates", "24", "--workdir", str(work)])
        backend_type = bind_contract(settings.contract)
        seeds = backend_type.default_seeds(settings.state_mode)
        seeds_by_case.setdefault(name, seeds)
        if seeds != seeds_by_case[name]:
            raise ValueError("paired initial seeds changed")
        save_json(work / "initial-seeds.json", seeds)
        if method == "ordered":
            proposal = work / "hypotheses.json"
            save_json(proposal, ordered_hypotheses(backend_type.fields))
            settings.hypotheses = str(proposal)
        print(f"\n{label}", flush=True)
        started = time.monotonic()
        report = run(settings, backend_type)
        elapsed = time.monotonic() - started
        # Assessment uses a separate budget, explicitly excluded from discovery
        # query/time metrics. No expected formula is passed to run().
        validation = None
        validation_seconds = 0.0
        validation_queries = 0
        if report["status"] in ("EXACT", "PARTIAL") and report.get("condition_c"):
            started = time.monotonic()
            checkdir = Path(report["artifacts"]) / "assessment"
            checkdir.mkdir()
            backend = backend_type(settings, checkdir)
            backend.prepare()
            if report["status"] == "EXACT":
                validation = backend.query("expected", report["condition_c"], expected=expected_condition(name))
            else:
                backend.restore_obligations(report.get("state_obligations", {}))
                validation = backend.query("equal", report["condition_c"])
            validation_seconds = time.monotonic() - started
            validation_queries = len(backend.queries)
        integrity, passed = assess(report, validation, required)
        replays = json.loads((Path(report["artifacts"]) / "replays.json").read_text(encoding="utf-8"))
        initial_replay = next((r["stdin"] for r in replays if r["origin"] == "boundary_seeds"), None)
        initial_stdin = "".join(" ".join(str(row[f]) for f in backend_type.fields) + "\n" for row in seeds)
        replay_matches = initial_replay == initial_stdin
        integrity = integrity and replay_matches
        passed = passed and replay_matches
        check_engine()
        row = dict(label=label, repeat=repeat, case=name, vocabulary=method, required=required,
                   status=report["status"], passed=passed, integrity=integrity,
                   queries=report.get("queries_used", 0), elapsed_seconds=round(elapsed, 6),
                   condition_chars=len(report.get("condition") or ""), condition=report.get("condition"),
                   reasons=diagnostics(report), initial_seeds=seeds, initial_replay_matches=replay_matches,
                   validation=validation, validation_seconds=round(validation_seconds, 6), report=report)
        row["validation_queries"] = validation_queries
        results.append(row)
        print(f"{label}: {row['status']} queries={row['queries']} time={row['elapsed_seconds']:.3f}s "
              f"{'required' if required else 'exploratory'}={'PASS' if passed else 'NOT ESTABLISHED'}", flush=True)
        save_json(directory / "progress.json", results)
    unchanged = (before == {p.name: text_hash(p) for p in sources}
                 and identities == {n: binary_identity(getattr(args, n)) for n in identities})
    check_engine()
    summary = dict(schema=1, baseline_commit=lock["baseline_commit"], engine_unchanged=True,
                   experiment_inputs_and_binaries_unchanged=unchanged, binaries=identities, environment=environment,
                   required_passed=sum(r["passed"] for r in results if r["required"]),
                   required_total=sum(r["required"] for r in results),
                   discovery_exact=sum(r["status"] == "EXACT" for r in results), total_runs=len(results),
                   all_reports_valid=all(r["integrity"] for r in results),
                   budgets=dict(max_queries=args.max_queries, max_seconds=args.max_seconds,
                                timeout=args.timeout, max_predicates=24, repeats=args.repeats),
                   source_hashes=before, results=results, artifacts=str(directory),
                   provenance="Authored after engine freeze; integration experiment, not independent blind evaluation.")
    summary["passed"] = (unchanged and summary["all_reports_valid"]
                         and summary["required_passed"] == summary["required_total"])
    columns = ("label", "repeat", "case", "vocabulary", "required", "status", "passed", "integrity",
               "queries", "elapsed_seconds", "condition_chars", "validation_queries", "validation_seconds", "condition", "reasons")
    with (directory / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    save_json(directory / "results.json", summary)
    save_json(root / "results.json", summary)
    print(f"C TRANSFER ACCEPTANCE: {summary['required_passed']}/{summary['required_total']} required runs passed")
    print(f"Discovery EXACT: {summary['discovery_exact']}/{summary['total_runs']}; "
          f"all reports valid={summary['all_reports_valid']}; engine unchanged=True; inputs/tools unchanged={unchanged}")
    print(f"Artifacts: {directory}")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-queries", type=int, default=96)
    parser.add_argument("--max-seconds", type=float, default=120)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--workdir", default=".verify-equiv-runs/c-transfer")
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 10 or args.max_queries < 4 or not all(
            math.isfinite(n) and n > 0 for n in (args.max_seconds, args.timeout)):
        parser.error("1..10 repeats, >=4 queries and positive finite time budgets required")
    try:
        return 0 if execute(args)["passed"] else 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Transfer experiment incomplete: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
