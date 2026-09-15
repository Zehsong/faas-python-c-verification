#!/usr/bin/env python3
"""Find return-equivalence conditions for two admitted scalar C source files."""
import argparse
import math
import sys

from c_backend import oracle
from c_scalar_backend import bind_contract
from condition_runner import run


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--max-queries", type=int, default=96)
    parser.add_argument("--max-predicates", type=int, default=24)
    parser.add_argument("--hypotheses")
    parser.add_argument("--workdir", default=".verify-equiv-runs/c-scalar")
    args = parser.parse_args(argv)
    if not all(math.isfinite(n) and n > 0 for n in (args.timeout, args.max_seconds)) or args.max_queries < 4 or not 1 <= args.max_predicates <= 24:
        parser.error("positive time budgets, >=4 queries and 1..24 predicates required")
    args.variant, args.state_mode = "pair", "stateless"
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        backend = bind_contract(args.contract)
        report = run(args, backend)
        return 0 if report["status"] == "EXACT" else 2
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        print(f"UNKNOWN: unsupported or invalid C contract: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
