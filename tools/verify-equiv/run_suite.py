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


def scalar_command(project, case, workdir):
    verify = (
        project
        / "tools"
        / "verify-equiv"
        / "verify-equiv"
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

    for param in case.get("params", []):
        cmd.extend([
            "--param",
            param,
        ])

    return cmd


def list_int_command(project, case, workdir):
    verify = (
        project
        / "tools"
        / "verify-equiv"
        / "verify-list-int"
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

        "--max-len",
        str(case["max_len"]),

        "--timeout",
        str(case.get("timeout", 120)),

        "--workdir",
        str(workdir),
    ]

    if "unwind" in case:
        cmd.extend([
            "--unwind",
            str(case["unwind"]),
        ])

    return cmd


def build_command(project, case, workdir):
    driver = case.get(
        "driver",
        "scalar",
    )

    if driver == "scalar":
        return scalar_command(
            project,
            case,
            workdir,
        )

    if driver == "list-int":
        return list_int_command(
            project,
            case,
            workdir,
        )

    raise ValueError(
        f"unsupported regression driver: {driver}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run verify-equiv relational regression cases."
        )
    )

    parser.add_argument(
        "suite",
        help="path to regression JSON",
    )

    args = parser.parse_args()

    project = Path.cwd().resolve()
    suite_path = Path(args.suite).resolve()

    data = json.loads(
        suite_path.read_text()
    )

    cases = data["cases"]

    passed = 0
    results = []

    print()
    print("=" * 72)
    print("RELATIONAL REGRESSION SUITE")
    print("=" * 72)

    for case in cases:
        name = case["name"]
        expected = case["expect"]

        workdir = (
            project
            / case.get(
                "workdir",
                f"experiments/regression_runs/{name}",
            )
        )

        cmd = build_command(
            project,
            case,
            workdir,
        )

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
                proc.returncode,
                proc.stdout,
            )
        )

        print(
            f"{name:<26} "
            f"expected={expected:<7} "
            f"actual={verdict:<7} "
            f"{'PASS' if ok else 'FAIL'}"
        )

        if not ok:
            print()
            print(
                f"driver={case.get('driver', 'scalar')}"
            )
            print(
                f"process_rc={proc.returncode}"
            )
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
