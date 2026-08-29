#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/workspaces/faas-python-c-verification")
VERIFY = ROOT / "tools/verify-equiv/verify-equiv"

PY_ADAPTER = "__VEQ_PY_LIST_INT_ADAPTER"
C_ADAPTER = "__VEQ_C_LIST_INT_ADAPTER"


def ident(x, what):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x):
        raise SystemExit(f"invalid {what}: {x!r}")


def build_python_adapter(target, n):
    elems = [f"e{i}" for i in range(n)]

    params = ", ".join(
        ["selector: int"] +
        [f"{e}: int" for e in elems]
    )

    lines = [
        "",
        "",
        f"def {PY_ADAPTER}({params}) -> int:",
        "    xs: list[int] = []",
    ]

    #
    # Canonical bounded-sequence representation:
    #
    # selector <= 0  -> []
    # selector == 1  -> [e0]
    # selector == 2  -> [e0, e1]
    # ...
    # selector >= n  -> [e0, ..., e(n-1)]
    #
    # Crucially, do NOT reassign xs to another list object.
    # Build one list incrementally so that ESBMC does not need
    # whole-list copy semantics across symbolic branches.
    #
    for i, elem in enumerate(elems):
        lines += [
            f"    if selector >= {i + 1}:",
            f"        xs.append({elem})",
        ]

    lines += [
        f"    return {target}(xs)",
        "",
    ]

    return "\n".join(lines)


def build_c_adapter(target, n):
    elems = [f"e{i}" for i in range(n)]

    params = ", ".join(
        ["int selector"] +
        [f"int {e}" for e in elems]
    )

    init = ", ".join(elems)

    lines = [
        "",
        "",
        f"int {C_ADAPTER}({params})",
        "{",
        "    int n;",
        "",
        "    if (selector <= 0)",
        "        n = 0;",
    ]

    for k in range(1, n):
        lines += [
            f"    else if (selector == {k})",
            f"        n = {k};",
        ]

    lines += [
        "    else",
        f"        n = {n};",
        "",
        f"    int xs[{n}] = {{{init}}};",
        f"    return {target}(xs, n);",
        "}",
        "",
    ]

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Verify Python list[int] against "
            "C int* + length using canonical logical inputs."
        )
    )

    ap.add_argument("--python", required=True)
    ap.add_argument("--py-function", required=True)

    ap.add_argument("--c", required=True)
    ap.add_argument("--c-function", required=True)

    ap.add_argument(
        "--max-len",
        type=int,
        default=4,
    )

    ap.add_argument(
        "--unwind",
        type=int,
        default=None,
        help=(
            "ESBMC unwind bound. "
            "Default: max_len + 2."
        ),
    )

    ap.add_argument(
        "--timeout",
        type=int,
        default=180,
    )

    ap.add_argument("--workdir")

    args = ap.parse_args()

    ident(args.py_function, "Python function")
    ident(args.c_function, "C function")

    if not 1 <= args.max_len <= 16:
        raise SystemExit(
            "--max-len must currently be between 1 and 16"
        )

    effective_unwind = (
        args.unwind
        if args.unwind is not None
        else args.max_len + 2
    )

    py_src = Path(args.python).resolve()
    c_src = Path(args.c).resolve()

    if not py_src.exists():
        raise SystemExit(f"Python file not found: {py_src}")

    if not c_src.exists():
        raise SystemExit(f"C file not found: {c_src}")

    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        workdir = (
            Path.cwd()
            / ".verify-list-int-runs"
            / stamp
        )

    generated = workdir / "generated"
    checkdir = workdir / "check"

    generated.mkdir(
        parents=True,
        exist_ok=True,
    )

    py_generated = generated / "python_adapter.py"
    c_generated = generated / "c_adapter.c"

    py_generated.write_text(
        py_src.read_text()
        + "\n"
        + build_python_adapter(
            args.py_function,
            args.max_len,
        )
    )

    c_generated.write_text(
        c_src.read_text()
        + "\n"
        + build_c_adapter(
            args.c_function,
            args.max_len,
        )
    )

    cmd = [
        str(VERIFY),

        "--python",
        str(py_generated),

        "--py-function",
        PY_ADAPTER,

        "--c",
        str(c_generated),

        "--c-function",
        C_ADAPTER,

        "--param",
        "selector:int",
    ]

    for i in range(args.max_len):
        cmd += [
            "--param",
            f"e{i}:int",
        ]

    cmd += [
        "--return",
        "int",

        "--unwind",
        str(effective_unwind),

        "--timeout",
        str(args.timeout),

        "--workdir",
        str(checkdir),
    ]

    print(
        f"Logical domain: list[int], "
        f"0 <= len(xs) <= {args.max_len}"
    )

    print(
        f"Unwind bound: {effective_unwind}"
    )

    print(
        "Canonical representation: "
        "selector + "
        + ", ".join(
            f"e{i}" for i in range(args.max_len)
        )
    )

    print()

    result = subprocess.run(cmd)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
