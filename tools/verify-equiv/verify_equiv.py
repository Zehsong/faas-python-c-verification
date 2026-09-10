#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_ESBMC = "/workspaces/esbmc-current/build/src/esbmc/esbmc"

SUPPORTED_TYPES = {"int", "bool"}

PY_C_TYPES = {
    "int": "long",
    "bool": "_Bool",
}

TARGET_C_TYPES = {
    "int": "int",
    "bool": "_Bool",
}

RELATIONAL_PROPERTY = "__VERIFY_EQUIV_RELATIONAL_PROPERTY__"


# ============================================================================
# CLI helpers
# ============================================================================

def parse_param(text):
    if ":" not in text:
        raise argparse.ArgumentTypeError(
            f"parameter must be NAME:TYPE, got {text!r}"
        )

    name, typ = text.split(":", 1)
    name = name.strip()
    typ = typ.strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise argparse.ArgumentTypeError(
            f"invalid parameter name: {name!r}"
        )

    if typ not in SUPPORTED_TYPES:
        raise argparse.ArgumentTypeError(
            f"unsupported parameter type {typ!r}; "
            f"supported: {sorted(SUPPORTED_TYPES)}"
        )

    return name, typ


def validate_identifier(name, what):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise SystemExit(
            f"UNKNOWN\n"
            f"Reason: v1 requires a simple module-level "
            f"{what} identifier, got {name!r}"
        )


# ============================================================================
# Process execution
# ============================================================================

def run(cmd, logfile, timeout):
    logfile = Path(logfile)

    logfile.parent.mkdir(parents=True, exist_ok=True)

    with logfile.open("w") as trace:
        trace.write(
            "VERIFY_EQUIV_COMMAND: "
            + " ".join(str(x) for x in cmd)
            + "\n"
        )

    try:
        with logfile.open("a") as out:
            proc = subprocess.run(
                cmd,
                stdout=out,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )

        return proc.returncode, False

    except subprocess.TimeoutExpired:
        with logfile.open("a") as out:
            out.write(
                f"\nVERIFY_EQUIV_INTERNAL: "
                f"timeout after {timeout}s\n"
            )

        return 124, True


def read_text(path):
    path = Path(path)

    if not path.exists():
        return ""

    return path.read_text(errors="replace")


def tail_interesting(path, limit=30):
    lines = read_text(path).splitlines()

    patterns = (
        "ERROR",
        "Unsupported",
        "unsupported",
        "TypeError",
        "NotImplementedError",
        "no body",
        "Failed",
        "failed",
        "Relational bridge",
        "unwind",
        "unwinding",
    )

    result = [
        line
        for line in lines
        if any(p in line for p in patterns)
    ]

    return result[-limit:]


# ============================================================================
# GOTO export
# ============================================================================

def export_goto(
    esbmc,
    source,
    output,
    log,
    timeout,
    entry_function=None,
):
    cmd = [
        esbmc,
        str(source),
    ]

    if entry_function is not None:
        cmd.extend([
            "--function",
            str(entry_function),
        ])

    cmd.extend([
        "--output-goto",
        str(output),
    ])

    rc, timed_out = run(
        cmd,
        log,
        timeout,
    )

    if timed_out:
        return False, "TIMEOUT"

    #
    # Current ESBMC may return RC=6 after successfully writing
    # --output-goto.  The binary itself is authoritative.
    #
    if output.exists() and output.stat().st_size > 0:
        return True, f"export_rc={rc}"

    return False, f"export failed, rc={rc}"


# ============================================================================
# Relational harness
# ============================================================================

def _build_harness_base(params, return_type):
    py_ret = PY_C_TYPES[return_type]
    c_ret = TARGET_C_TYPES[return_type]

    py_decl_args = []
    c_decl_args = []

    declarations = []

    py_call_args = []
    c_call_args = []

    for name, typ in params:
        py_type = PY_C_TYPES[typ]
        c_type = TARGET_C_TYPES[typ]

        py_decl_args.append(
            f"{py_type} {name}"
        )

        c_decl_args.append(
            f"{c_type} {name}"
        )

        if typ == "int":
            #
            # One logical symbolic value:
            #
            #   int32 x
            #      / \
            #     /   \
            # Python  C
            # long    int
            #
            declarations.append(
                f"    int {name} = "
                f"__VERIFIER_nondet_int();"
            )

            py_call_args.append(
                f"(long){name}"
            )

            c_call_args.append(name)

        elif typ == "bool":
            declarations.append(
                f"    _Bool {name} = "
                f"(__VERIFIER_nondet_int() != 0);"
            )

            py_call_args.append(name)
            c_call_args.append(name)

    py_decl = (
        ", ".join(py_decl_args)
        if py_decl_args
        else "void"
    )

    c_decl = (
        ", ".join(c_decl_args)
        if c_decl_args
        else "void"
    )

    py_args = ", ".join(py_call_args)
    c_args = ", ".join(c_call_args)

    body_decls = "\n".join(declarations)

    return f'''/*
 * AUTO-GENERATED BY verify-equiv v2.
 *
 * Neither placeholder is an implementation.
 *
 * After GOTO merge:
 *
 *   __ESBMC_PY_TARGET -> real Python GOTO function
 *   __ESBMC_C_TARGET  -> real C GOTO function
 */

extern int __VERIFIER_nondet_int(void);

/*
 * Complete Python frontend/module entry preserved by the
 * relational GOTO linker.
 *
 * This establishes static-lifetime/module/runtime state before
 * a symbolic request enters the translated function.
 */
extern void __ESBMC_PY_MODULE_ENTRY(void);

extern {py_ret} __ESBMC_PY_TARGET({py_decl});
extern {c_ret}  __ESBMC_C_TARGET({c_decl});

int equiv_main(void)
{{
    /*
     * Python frontend semantics include module/static/runtime
     * initialization.  Do not jump directly into the Python target.
     */
    __ESBMC_PY_MODULE_ENTRY();

{body_decls}

    long r_py =
        (long)__ESBMC_PY_TARGET({py_args});

    long r_c =
        (long)__ESBMC_C_TARGET({c_args});

    __ESBMC_assert(
        r_py == r_c,
        "{RELATIONAL_PROPERTY}"
    );

    return 0;
}}

int main(void)
{{
    return equiv_main();
}}
'''


# ============================================================================
# Fail-closed relational preflight
# ============================================================================

def relational_preflight(
    esbmc,
    py_gb,
    c_gb,
    harness_gb,
    py_function,
    c_function,
    logfile,
    timeout,
):
    cmd = [
        esbmc,
        "--binary",
        str(py_gb),
        str(c_gb),
        str(harness_gb),

        "--equiv-py-target",
        py_function,

        "--equiv-c-target",
        c_function,

        "--function",
        "c:@F@equiv_main",

        "--show-call-sites",
    ]

    rc, timed_out = run(
        cmd,
        logfile,
        timeout,
    )

    if timed_out:
        return False, "preflight timeout"

    text = read_text(logfile)

    failures = []

    #
    # Python frontend/module initialization MUST survive relational linking.
    #
    # Runtime-backed Python values (list/dict/string/etc.) may depend on this
    # state.  Skipping it previously produced false relational counterexamples.
    #
    module_preserve_marker = (
        "preserved Python module entry as "
        "`c:@F@__ESBMC_PY_MODULE_ENTRY`"
    )

    if module_preserve_marker not in text:
        failures.append(
            "Python module entry was not preserved"
        )

    #
    # The relational harness MUST execute the preserved module entry before
    # entering the Python/C targets.
    #
    if not re.search(
        r"c:@F@equiv_main\s*->\s*"
        r"c:@F@__ESBMC_PY_MODULE_ENTRY\s*\(",
        text,
    ):
        failures.append(
            "equiv_main does not call the preserved Python module entry"
        )

    #
    # Both relational linker rewrites MUST occur.
    #
    if "__ESBMC_PY_TARGET" not in text:
        failures.append(
            "Python relational target was not retargeted"
        )

    if "__ESBMC_C_TARGET" not in text:
        failures.append(
            "C relational target was not retargeted"
        )

    #
    # Final verification entry MUST be equiv_main.
    #
    if not re.search(
        r"__ESBMC_main\s*->\s*"
        r"c:@F@equiv_main\s*\(",
        text,
    ):
        failures.append(
            "__ESBMC_main does not reach equiv_main"
        )

    #
    # equiv_main MUST call the real Python target.
    #
    py_pattern = (
        r"c:@F@equiv_main\s*->\s*"
        r"py:.*@F@"
        + re.escape(py_function)
        + r"\s*\("
    )

    if not re.search(py_pattern, text):
        failures.append(
            "equiv_main does not call the Python target"
        )

    #
    # equiv_main MUST call the real C target.
    #
    c_pattern = (
        r"c:@F@equiv_main\s*->\s*"
        r"c:.*@F@"
        + re.escape(c_function)
        + r"\s*\("
    )

    if not re.search(c_pattern, text):
        failures.append(
            "equiv_main does not call the C target"
        )

    if failures:
        return False, "; ".join(failures)

    return True, f"preflight_rc={rc}"


# ============================================================================
# Counterexample parsing
# ============================================================================

def extract_counterexample(
    logfile,
    params,
):
    lines = read_text(logfile).splitlines()

    wanted = [
        name
        for name, _ in params
    ] + [
        "r_py",
        "r_c",
    ]

    result = []

    for line in lines:
        stripped = line.strip()

        for name in wanted:
            #
            # Match:
            #
            #   x = 10
            #
            # but NOT:
            #
            #   r_py == r_c
            #
            if re.match(
                rf"^{re.escape(name)}\s*=(?!=)",
                stripped,
            ):
                if stripped not in result:
                    result.append(stripped)

    return result


def extract_violated_property(logfile):
    lines = read_text(logfile).splitlines()

    result = []

    for i, line in enumerate(lines):
        if "Violated property:" in line:
            result.extend(
                lines[i:i + 10]
            )

    return [
        line.strip()
        for line in result[-15:]
        if line.strip()
    ]


# ============================================================================
# Verdict classification
# ============================================================================

def classify_verification(logfile):
    text = read_text(logfile)

    if "VERIFICATION SUCCESSFUL" in text:
        return "EQ"

    if "VERIFICATION FAILED" in text:
        #
        # Only call it NEQ if OUR relational property is
        # the property that failed.
        #
        # Any other ESBMC failure is conservatively UNKNOWN.
        #
        if RELATIONAL_PROPERTY in text:
            return "NEQ"

        return "UNKNOWN_PROPERTY_FAILURE"

    return "UNKNOWN"


# ============================================================================
# Main
# ============================================================================


def build_harness(params, return_type, domains=()):
    text = _build_harness_base(params, return_type)

    if not domains:
        return text

    import re as _re

    assumptions = []
    for name, lower, upper in domains:
        assumptions.append(
            f"    __ESBMC_assume({name} >= {lower});"
        )
        assumptions.append(
            f"    __ESBMC_assume({name} <= {upper});"
        )

    assumption_text = "\n".join(assumptions) + "\n"

    # Declare the ESBMC intrinsic.
    if "__ESBMC_assume(_Bool)" not in text:
        text = (
            "extern void __ESBMC_assume(_Bool);\n"
            + text
        )

    # Insert D(x) after all shared symbolic inputs have been
    # created, but before either program target is executed.
    #
    # The generated harness always declares all symbolic inputs
    # before the first "long r_py =" assignment.
    pattern = r"(?m)^(\s*long\s+r_py\s*=)"

    text, count = _re.subn(
        pattern,
        lambda m: assumption_text + "\n" + m.group(1),
        text,
        count=1,
    )

    if count != 1:
        raise RuntimeError(
            "could not inject domain assumptions into equiv_main"
        )

    return text

def main():
    parser = argparse.ArgumentParser(
        prog="verify-equiv",
        description=(
            "Fail-closed experimental Python<->C "
            "relational equivalence checker."
        ),
    )

    parser.add_argument(
        "--python",
        required=True,
    )

    parser.add_argument(
        "--py-function",
        required=True,
    )

    parser.add_argument(
        "--c",
        required=True,
    )

    parser.add_argument(
        "--c-function",
        required=True,
    )

    parser.add_argument(
        "--param",
        action="append",
        type=parse_param,
        default=[],
        help="logical parameter NAME:TYPE; TYPE=int|bool",
    )

    parser.add_argument(
        "--domain",
        action="append",
        default=[],
        metavar="NAME:LOWER:UPPER",
        help=(
            "restrict an int parameter to an inclusive interval; "
            "repeat for multiple parameters"
        ),
    )

    parser.add_argument(
        "--return",
        dest="return_type",
        choices=sorted(SUPPORTED_TYPES),
        required=True,
    )

    parser.add_argument(
        "--esbmc",
        default=DEFAULT_ESBMC,
    )

    parser.add_argument(
        "--unwind",
        type=int,
        default=12,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
    )

    parser.add_argument(
        "--workdir",
        default=None,
    )

    args = parser.parse_args()

    param_types = dict(args.param)
    domains = []
    seen_domain_params = set()

    for spec in args.domain:
        parts = spec.split(":")

        if len(parts) != 3:
            parser.error(
                f"invalid --domain {spec!r}; "
                "expected NAME:LOWER:UPPER"
            )

        name, lower_text, upper_text = parts

        if name not in param_types:
            parser.error(
                f"--domain refers to unknown parameter {name!r}"
            )

        if param_types[name] != "int":
            parser.error(
                f"--domain currently supports int parameters only; "
                f"{name!r} is {param_types[name]!r}"
            )

        if name in seen_domain_params:
            parser.error(
                f"duplicate --domain for {name!r}"
            )

        try:
            lower = int(lower_text)
            upper = int(upper_text)
        except ValueError:
            parser.error(
                f"invalid integer bounds in --domain {spec!r}"
            )

        if lower > upper:
            parser.error(
                f"lower bound exceeds upper bound in "
                f"--domain {spec!r}"
            )

        if lower < -2147483648 or upper > 2147483647:
            parser.error(
                f"--domain {spec!r} exceeds shared int32 domain"
            )

        seen_domain_params.add(name)
        domains.append((name, lower, upper))


    validate_identifier(
        args.py_function,
        "Python function",
    )

    validate_identifier(
        args.c_function,
        "C function",
    )

    py_file = Path(args.python).resolve()
    c_file = Path(args.c).resolve()
    esbmc = str(Path(args.esbmc).resolve())

    if not py_file.exists():
        print("UNKNOWN")
        print(
            f"Reason: Python file not found: "
            f"{py_file}"
        )
        return 2

    if not c_file.exists():
        print("UNKNOWN")
        print(
            f"Reason: C file not found: "
            f"{c_file}"
        )
        return 2

    if not Path(esbmc).exists():
        print("UNKNOWN")
        print(
            f"Reason: ESBMC binary not found: "
            f"{esbmc}"
        )
        return 2

    #
    # Require BOTH relational extensions.
    #
    try:
        help_text = subprocess.check_output(
            [esbmc, "--help"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        )

    except Exception as exc:
        print("UNKNOWN")
        print(
            f"Reason: could not execute ESBMC: {exc}"
        )
        return 2

    required_options = (
        "equiv-py-target",
        "equiv-c-target",
    )

    for option in required_options:
        if option not in help_text:
            print("UNKNOWN_INTERNAL")
            print(
                f"Reason: ESBMC build does not contain "
                f"--{option}"
            )
            return 2

    if args.workdir:
        workdir = Path(args.workdir).resolve()

    else:
        stamp = time.strftime(
            "%Y%m%d-%H%M%S"
        )

        workdir = (
            Path.cwd()
            / ".verify-equiv-runs"
            / (
                f"{args.py_function}__"
                f"{args.c_function}__"
                f"{stamp}"
            )
        )

    workdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    py_gb = workdir / "python.gb"
    c_gb = workdir / "c.gb"
    harness_gb = workdir / "harness.gb"

    harness_c = (
        workdir / "equiv_harness.c"
    )

    py_log = (
        workdir / "python_export.log"
    )

    c_log = (
        workdir / "c_export.log"
    )

    harness_log = (
        workdir / "harness_export.log"
    )

    preflight_log = (
        workdir / "preflight.log"
    )

    verify_log = (
        workdir / "verification.log"
    )

    #
    # Generate harness.
    #
    harness_c.write_text(
        build_harness(
            args.param,
            args.return_type,
            domains,
        )
    )

    #
    # Python -> GOTO
    #
    ok, reason = export_goto(
        esbmc,
        py_file,
        py_gb,
        py_log,
        args.timeout,
    )

    if not ok:
        print("UNKNOWN")
        print(
            f"Reason: Python frontend/GOTO export: "
            f"{reason}"
        )

        for line in tail_interesting(py_log):
            print(f"  {line}")

        print(f"Artifacts: {workdir}")
        return 2

    #
    # C -> GOTO.
    #
    # No source-level main() is required.
    #
    ok, reason = export_goto(
        esbmc,
        c_file,
        c_gb,
        c_log,
        args.timeout,
        entry_function=args.c_function,
    )

    if not ok:
        print("UNKNOWN")
        print(
            f"Reason: C frontend/GOTO export: "
            f"{reason}"
        )

        for line in tail_interesting(c_log):
            print(f"  {line}")

        print(f"Artifacts: {workdir}")
        return 2

    #
    # Harness -> GOTO
    #
    ok, reason = export_goto(
        esbmc,
        harness_c,
        harness_gb,
        harness_log,
        args.timeout,
    )

    if not ok:
        print("UNKNOWN_INTERNAL")
        print(
            f"Reason: harness GOTO export: "
            f"{reason}"
        )

        print(f"Artifacts: {workdir}")
        return 2

    #
    # FAIL-CLOSED PRE-FLIGHT.
    #
    # Never accept VERIFICATION SUCCESSFUL until we have
    # independently established the intended relational
    # entry/call structure.
    #
    ok, reason = relational_preflight(
        esbmc,
        py_gb,
        c_gb,
        harness_gb,
        args.py_function,
        args.c_function,
        preflight_log,
        args.timeout,
    )

    if not ok:
        print("UNKNOWN_INTERNAL")
        print(
            f"Reason: relational preflight failed: "
            f"{reason}"
        )

        for line in tail_interesting(
            preflight_log
        ):
            print(f"  {line}")

        print(f"Artifacts: {workdir}")
        return 2

    #
    # Actual relational verification.
    #
    verify_cmd = [
        esbmc,

        "--binary",
        str(py_gb),
        str(c_gb),
        str(harness_gb),

        "--equiv-py-target",
        args.py_function,

        "--equiv-c-target",
        args.c_function,

        "--function",
        "c:@F@equiv_main",

        "--unwind",
        str(args.unwind),

        "--overflow-check",
    ]

    rc, timed_out = run(
        verify_cmd,
        verify_log,
        args.timeout,
    )

    if timed_out:
        print("UNKNOWN")
        print(
            f"Reason: verification timeout "
            f"({args.timeout}s)"
        )

        print(f"Artifacts: {workdir}")
        return 2

    verdict = classify_verification(
        verify_log
    )

    if verdict == "EQ":
        print("EQ")
        print()

        print("Proof scope:")

        if not args.param:
            print(
                "  no symbolic parameters"
            )

        for name, typ in args.param:
            if typ == "int":
                print(
                    f"  {name}: shared int32 domain "
                    f"[-2147483648, 2147483647]"
                )

            else:
                print(
                    f"  {name}: boolean "
                    f"{{False, True}}"
                )

        print(
            "  semantics: ESBMC Python/C "
            "modeled semantics"
        )

        print(
            f"  unwind bound: {args.unwind}"
        )

        print(
            "  relational preflight: PASS"
        )

        print()
        print(f"Artifacts: {workdir}")

        return 0

    if verdict == "NEQ":
        print("NEQ")

        cex = extract_counterexample(
            verify_log,
            args.param,
        )

        if cex:
            print()
            print("Counterexample:")

            for line in cex:
                print(f"  {line}")

        violation = (
            extract_violated_property(
                verify_log
            )
        )

        if violation:
            print()
            print("Violation:")

            for line in violation:
                print(f"  {line}")

        print()
        print(f"Artifacts: {workdir}")

        return 1

    if verdict == "UNKNOWN_PROPERTY_FAILURE":
        print("UNKNOWN")
        print(
            "Reason: ESBMC reported a failure, "
            "but it was not the relational "
            "equivalence property."
        )

        violation = (
            extract_violated_property(
                verify_log
            )
        )

        if violation:
            print()
            print("Non-relational violation:")

            for line in violation:
                print(f"  {line}")

        print()
        print(f"Artifacts: {workdir}")

        return 2

    print("UNKNOWN")
    print(
        f"Reason: ESBMC did not produce a "
        f"definitive relational verdict "
        f"(rc={rc})"
    )

    for line in tail_interesting(
        verify_log
    ):
        print(f"  {line}")

    print(f"Artifacts: {workdir}")

    return 2


if __name__ == "__main__":
    sys.exit(main())
