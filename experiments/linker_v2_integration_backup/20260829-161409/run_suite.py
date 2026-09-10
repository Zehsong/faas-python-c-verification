#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


def normalize_verdict(text):
    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line == "EQ":
            return "EQ"

        if line == "NEQ":
            return "NEQ"

        if line.startswith("UNKNOWN"):
            return "UNKNOWN"

    return "UNKNOWN"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run verify-equiv regression cases "
            "from a JSON suite."
        )
    )

    parser.add_argument(
        "suite",
        help="path to regression JSON",
    )

    args = parser.parse_args()

    project = Path.cwd().resolve()

    suite_path = Path(
        args.suite
    ).resolve()

    data = json.loads(
        suite_path.read_text()
    )

    verify = (
        project
        / "tools"
        / "verify-equiv"
        / "verify-equiv"
    )

    cases = data["cases"]

    passed = 0
    results = []

    for case in cases:
        name = case["name"]
        expected = case["expect"]

        workdir = (
            project
            / case.get(
                "workdir",
                f"experiments/regression_runs/{name}"
            )
        )

        cmd = [
            str(verify),

            "--python",
            str(project / case["python"]),

            "--py-function",
            case["py_function"],

            "--c",
            str(project / case["c"]),

            "--c-function",
            case["c_function"],

            "--return",
            case["return"],

            "--workdir",
            str(workdir),

            "--timeout",
            str(case.get("timeout", 120)),

            "--unwind",
            str(case.get("unwind", 12)),
        ]

        for param in case.get(
            "params",
            []
        ):
            cmd.extend([
                "--param",
                param,
            ])

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        verdict = normalize_verdict(
            proc.stdout
        )

        ok = verdict == expected

        if ok:
            passed += 1

        results.append(
            (
                name,
                expected,
                verdict,
                "PASS" if ok else "FAIL",
                proc.stdout,
            )
        )

        print(
            f"{name:<24} "
            f"expected={expected:<7} "
            f"actual={verdict:<7} "
            f"{'PASS' if ok else 'FAIL'}"
        )

        if not ok:
            print()
            print(proc.stdout)
            print()

    print()
    print("=" * 72)

    print(
        f"REGRESSION SUMMARY: "
        f"{passed}/{len(cases)} passed"
    )

    print("=" * 72)

    if passed != len(cases):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
