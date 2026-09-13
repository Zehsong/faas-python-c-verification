#!/usr/bin/env python3
"""Run the C/C cache obligations through verify-equiv; retain all raw logs."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "verify-equiv"))
from verify_equiv import DEFAULT_ESBMC

EXPECTED = {
    "good_sequence": "EQ", "bad_sequence": "NEQ",
    "good_induction": "EQ", "bad_induction": "NEQ",
    "bad_conditional_step": "EQ", "bad_empty_miss": "NEQ",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=DEFAULT_ESBMC)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--workdir", default=".verify-equiv-runs/same-language-cache")
    args = parser.parse_args()
    output = Path(args.workdir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for entry, expected in EXPECTED.items():
        run_dir = output / entry
        run_dir.mkdir(exist_ok=True)
        # Never read an old result if a new invocation cannot produce one.
        report_path = run_dir / "result.json"
        report_path.unlink(missing_ok=True)
        command = [sys.executable, str(ROOT / "tools/verify-equiv/verify_equiv.py"),
                   "--c-harness", str(HERE / "cache_demo.c"), "--entry", entry,
                   "--scope-file", str(HERE / "scopes.json"),
                   "--esbmc", args.esbmc, "--timeout", str(args.timeout),
                   "--workdir", str(run_dir)]
        proc = subprocess.run(command, capture_output=True, text=True)
        (run_dir / "driver.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {
            "verdict": "UNKNOWN", "reason": "driver produced no report"}
        verdict = report["verdict"]
        passed = verdict == expected and proc.returncode == {"EQ": 0, "NEQ": 1}.get(expected)
        results.append({"entry": entry, "expected": expected, "actual": verdict,
                        "passed": passed, "reason": report.get("reason"),
                        "artifacts": str(run_dir)})
        print(f"{entry}: {verdict} (expected {expected})", flush=True)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0 if all(item["passed"] for item in results) else 2


if __name__ == "__main__":
    sys.exit(main())
