"""Reviewed C/C product-harness adapter for the existing verify-equiv oracle.

The harness author supplies the state relation, assumptions and observations.
This adapter does not infer a product program from arbitrary source files.
"""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

REACHABILITY_PROPERTY = "__VERIFY_EQUIV_REACHABILITY__"


def main(argv, oracle):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c-harness", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--scope-file", required=True,
                        help="JSON mapping entry names to declared proof scopes")
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--unwind", type=int, default=12)
    parser.add_argument("--workdir")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.entry):
        parser.error("--entry must be a C identifier")
    if args.timeout <= 0 or args.unwind <= 0:
        parser.error("--timeout and --unwind must be positive")

    if args.workdir:
        workdir = Path(args.workdir).resolve()
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        root = Path(".verify-equiv-runs")
        root.mkdir(exist_ok=True)
        workdir = Path(tempfile.mkdtemp(prefix="c-harness-", dir=root)).resolve()
    # Reusing an output directory must never expose old proof logs as this run.
    for filename in ("version.log", "reachability.log", "verify.log", "result.json"):
        (workdir / filename).unlink(missing_ok=True)
    report = {"verdict": "UNKNOWN", "route": "c-harness",
              "entry": args.entry, "unwind": args.unwind,
              "automatic_condition_discovery": False}

    def finish(verdict, reason):
        report.update(verdict=verdict, reason=reason)
        (workdir / "result.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(verdict)
        print(f"Reason: {reason}")
        print("Declared proof scope: " + json.dumps(report.get("scope"), ensure_ascii=True))
        print(f"Artifacts: {workdir}")
        return {"EQ": 0, "NEQ": 1, "UNKNOWN": 2}[verdict]

    try:
        source = Path(args.c_harness).resolve(strict=True)
        source_bytes = source.read_bytes()
        scopes = json.loads(Path(args.scope_file).read_text(encoding="utf-8"))
        scope = scopes[args.entry]
        required = {"inputs", "initial_state", "observations", "assumptions", "bound"}
        if not isinstance(scope, dict) or not required <= scope.keys():
            raise ValueError(f"scope must contain {sorted(required)}")
        report.update(source=str(source), source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                      scope=scope, scope_origin="author supplied; review against harness")
        (workdir / "harness-source.c").write_bytes(source_bytes)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return finish("UNKNOWN", f"invalid source/scope: {exc}")

    executable = shutil.which(args.esbmc)
    if executable is None:
        return finish("UNKNOWN", f"ESBMC executable not found: {args.esbmc}")
    executable = str(Path(executable).resolve())
    report["esbmc"] = executable
    version_log = workdir / "version.log"
    rc, timeout = oracle.run([executable, "--version"], version_log, args.timeout)
    report["version_output"] = oracle.read_text(version_log)
    if timeout or rc != 0:
        return finish("UNKNOWN", "could not establish ESBMC version")

    # No disabled safety or unwinding assertions. uint32_t wrap is intentional;
    # unsigned-overflow checking must not be enabled for this model.
    command = [executable, str(source), "--function", args.entry, "--z3",
               "--unwind", str(args.unwind), "--overflow-check"]
    report["command"] = command
    probe_log = workdir / "reachability.log"
    probe_rc, timeout = oracle.run(
        command + ["-DVERIFY_EQUIV_REACHABILITY=1"], probe_log, args.timeout)
    report["reachability_returncode"] = probe_rc
    if timeout or probe_rc == 0 or oracle.classify_verification(
            probe_log, REACHABILITY_PROPERTY) != "NEQ":
        return finish("UNKNOWN", "observation reachability probe did not produce its expected violation")

    verify_log = workdir / "verify.log"
    rc, timeout = oracle.run(command, verify_log, args.timeout)
    report["verification_returncode"] = rc
    verdict = oracle.classify_verification(verify_log)
    report["violation"] = oracle.extract_violated_property(verify_log)
    report["counterexample_trace"] = oracle.extract_counterexample(
        verify_log, [(name, "int") for name in
                     ("x", "x0", "x1", "x2", "r_original", "r_cached", "before", "cache")])
    if timeout:
        return finish("UNKNOWN", "verification timeout")
    if verdict == "EQ" and rc == 0:
        return finish("EQ", "all harness obligations hold within the declared model")
    if verdict == "NEQ" and rc != 0:
        return finish("NEQ", "target return-value equivalence assertion violated; see verify.log")
    return finish("UNKNOWN", f"no definitive relational verdict (status={verdict}, rc={rc})")
