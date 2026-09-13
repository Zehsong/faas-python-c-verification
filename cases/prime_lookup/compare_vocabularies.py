#!/usr/bin/env python3
"""Paired exploratory comparison; correctness and speed are separate outcomes."""
import argparse
import csv
import hashlib
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile

from run_checks import ROOT, run_case, oracle, save_json

VARIANTS = ("fallback", "truncated", "mutant")
DOMAINS = ("0:63", "0:127")


def plan(repeats):
    for repeat in range(repeats):
        modes = ("baseline", "modulo") if repeat % 2 == 0 else ("modulo", "baseline")
        for domain in DOMAINS:
            for variant in VARIANTS:
                for vocabulary in modes:
                    yield repeat, domain, variant, vocabulary


def summarize(rows):
    summaries = []
    for domain in DOMAINS:
        for variant in VARIANTS:
            selected = [row for row in rows if row["domain"] == domain and row["variant"] == variant]
            modes = {}
            for vocabulary in ("baseline", "modulo"):
                group = [row for row in selected if row["vocabulary"] == vocabulary]
                # Do not discard slow UNKNOWN/failed runs from time summaries.
                modes[vocabulary] = {
                    "runs": len(group), "certified": sum(row["passed"] for row in group),
                    "statuses": [row["status"] for row in group],
                    **{key: statistics.median(row[key] for row in group) if group and all(isinstance(row.get(key), (int, float)) for row in group) else None
                       for key in ("queries_used", "finder_seconds", "elapsed_seconds", "raw_condition_chars", "published_condition_chars")}}
            summaries.append({"variant": variant, "domain": domain, "modes": modes})
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=600)
    parser.add_argument("--max-queries", type=int, default=512)
    parser.add_argument("--max-predicates", type=int, default=96)
    parser.add_argument("--workdir", default=".verify-equiv-runs/vocabulary-comparison")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be 1..10")
    if not 18 <= args.max_predicates <= 256 or args.max_queries < 4 or not all(math.isfinite(x) and x > 0 for x in (args.timeout, args.max_seconds)):
        parser.error("both arms require 18..256 predicates, >=4 queries, and finite positive time budgets")
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="comparison-", dir=root))
    executable = shutil.which(args.esbmc)
    manifest = {"repeats": args.repeats, "budgets": {key: getattr(args, key) for key in
                ("timeout", "max_seconds", "max_queries", "max_predicates")},
                "mode_order": "alternate baseline/modulo order by repeat; sequential runs",
                "changed_factor": "initial predicate vocabulary only; same total predicate cap",
                "note": "later solver witnesses may differ because search paths differ; no expected speedup",
                "esbmc": executable, "esbmc_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest() if executable else None}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    manifest["project_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
    oracle.run([args.esbmc, "--version"], output / "esbmc-version.txt", args.timeout)
    save_json(output / "experiment.json", manifest)
    rows = []
    for repeat, domain, variant, vocabulary in plan(args.repeats):
        name = f"r{repeat+1}-{variant}-{domain.replace(':', '-')}-{vocabulary}"
        print(f"\n{name}", flush=True)
        row = run_case(variant, domain, args, output, name, vocabulary)
        row.update(repeat=repeat+1, domain=domain, variant=variant)
        rows.append(row)
        save_json(output / "results.json", rows)  # Keep partial experiment progress.
    summaries = summarize(rows)
    save_json(output / "summary.json", summaries)
    paired = all(row["model_sha256"] is not None for row in rows) and all(len({row[key] for row in rows if row["domain"] == domain and row["variant"] == variant}) == 1
                 for domain in DOMAINS for variant in VARIANTS for key in ("model_sha256", "initial_seeds_sha256"))
    manifest["paired_inputs_match"] = paired
    save_json(output / "experiment.json", manifest)
    columns = ["case", "repeat", "variant", "domain", "vocabulary", "status", "passed", "queries_used",
               "finder_seconds", "elapsed_seconds", "raw_condition_chars", "published_condition_chars", "predicates_used",
               "traces_collected", "unresolved_regions", "artifacts"]
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    for summary in summaries:
        b, m = (summary["modes"][name] for name in ("baseline", "modulo"))
        print(f"{summary['variant']} {summary['domain']}: baseline queries={b['queries_used']} time={b['finder_seconds']}s "
              f"raw_chars={b['raw_condition_chars']} published_chars={b['published_condition_chars']} "
              f"certified={b['certified']}/{b['runs']}; modulo queries={m['queries_used']} time={m['finder_seconds']}s "
              f"raw_chars={m['raw_condition_chars']} published_chars={m['published_condition_chars']} certified={m['certified']}/{m['runs']}")
    count = sum(row["passed"] for row in rows)
    print(f"VOCABULARY COMPARISON: {count}/{len(rows)} certified; paired inputs match={paired}")
    print(f"Artifacts: {output}")
    save_json(root / "results.json", rows)
    save_json(root / "latest.json", {"artifacts": str(output), "certified": count, "total": len(rows), "paired_inputs_match": paired})
    return 0 if paired and count == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
