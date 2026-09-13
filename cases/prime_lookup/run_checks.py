#!/usr/bin/env python3
"""Independent finite sieve specification, consulted only after finder completion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from find_prime_conditions import make_harness, parse_args, run
from find_cache_conditions import PROPERTIES, check_obligation, oracle, save_json

CASES = [("fallback", "0:63"), ("truncated", "0:63"), ("mutant", "0:63"),
         ("truncated", "0:31"), ("truncated", "37:37")]


def sieve(limit):
    prime = [True] * (limit + 1)
    for x in range(min(2, limit + 1)):
        prime[x] = False
    for p in range(2, math.isqrt(limit) + 1):
        if prime[p]:
            for multiple in range(p*p, limit+1, p):
                prime[multiple] = False
    return prime


def expected_condition(variant, domain):
    lo, hi = domain
    flags = sieve(hi)
    unequal = [x for x in range(lo, hi+1) if
               (variant == "truncated" and x >= 32 and flags[x]) or
               (variant == "mutant" and x == 9)]
    return " && ".join(f"finder_x != UINT32_C({x})" for x in unequal) or "true"


def run_case(variant, domain_text, args, output, name, vocabulary="baseline"):
    settings = parse_args(["--variant", variant, "--domain", domain_text, "--vocabulary", vocabulary,
                           "--esbmc", args.esbmc, "--cc", args.cc,
                           "--timeout", str(args.timeout), "--max-seconds", str(args.max_seconds),
                           "--max-queries", str(getattr(args, "max_queries", 512)),
                           "--max-predicates", str(getattr(args, "max_predicates", 96)),
                           "--workdir", str(output / name)])
    started = time.monotonic()
    report = run(settings)
    finder_seconds = time.monotonic() - started
    validation = {"status": "UNKNOWN", "reason": "finder did not return EXACT"}
    if report["status"] == "EXACT" and report.get("condition_c"):
        directory = Path(report["artifacts"]) / "independent-acceptance"
        directory.mkdir()
        model = (Path(report["artifacts"]) / "inputs/prime_model.h").read_text(encoding="utf-8")
        expected = expected_condition(variant, settings.domain)
        source = directory / "harness.c"
        source.write_text(make_harness(model, variant, settings.domain, "expected",
            expected=f"({report['condition_c']}) == ({expected})"), encoding="utf-8")
        command = [report["esbmc"], str(source), "--function", "finder_entry", "--z3",
                   "--unwind", str(math.isqrt(settings.domain[1])+2), "--overflow-check"]
        validation = check_obligation(oracle, command, directory / "verify.log", args.timeout, PROPERTIES["expected"])
        validation.update(expected_condition=expected, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        save_json(directory / "result.json", validation)
    passed = report["status"] == "EXACT" and validation["status"] == "PROVED"
    result = {"case": name, "passed": passed, "status": report["status"],
                    "condition": report["condition"], "validation": validation,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "queries_used": report.get("queries_used"), "artifacts": report["artifacts"]}
    result.update(vocabulary=vocabulary, finder_seconds=round(finder_seconds, 3),
                  raw_condition_chars=len(report.get("search", {}).get("condition", "")),
                  published_condition_chars=len(report.get("condition") or ""),
                  predicates_used=len(report.get("search", {}).get("predicates", [])),
                  traces_collected=report.get("traces_collected"),
                  unresolved_regions=len(report.get("search", {}).get("buckets", {}).get("UNKNOWN", [])),
                  model_sha256=report.get("scope", {}).get("model_sha256"))
    result["initial_seeds_sha256"] = hashlib.sha256(json.dumps(report.get("sketch", {}).get("initial_seeds"), sort_keys=True).encode()).hexdigest()
    print(f"{name}: {'PASS' if passed else 'NOT PROVED'}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=600)
    parser.add_argument("--workdir", default=".verify-equiv-runs/prime-acceptance")
    parser.add_argument("--extended", action="store_true", help="also test all three variants on 0..127")
    args = parser.parse_args()
    output = Path(args.workdir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    cases = CASES + ([(variant, "0:127") for variant in ("fallback", "truncated", "mutant")] if args.extended else [])
    for variant, domain_text in cases:
        name = variant + "-" + domain_text.replace(":", "-")
        print(f"\n{name}", flush=True)
        results.append(run_case(variant, domain_text, args, output, name))
    save_json(output / "results.json", results)
    count = sum(row["passed"] for row in results)
    for row in results:
        print(f"{row['case']}: {row['status']} queries={row['queries_used']} elapsed={row['elapsed_seconds']}s")
    print(f"PRIME ACCEPTANCE: {count}/{len(results)} passed")
    return 0 if count == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
