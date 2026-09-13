#!/usr/bin/env python3
"""Positive and deliberately invalid sketch instances; all expected results explicit."""
import argparse
import copy
import hashlib
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
from cache_sketch import CacheSketch, PROPERTIES
from find_cache_conditions import save_json, oracle, check_obligation


def prepare_control(family, control, directory):
    case = ROOT / "cases" / family
    model = (case / "cache_model.h").read_text(encoding="utf-8")
    data = copy.deepcopy(CacheSketch(case / "sketch.json").data)
    kind = "init" if control.endswith("init") else "preservation"
    variant = "good"
    if control == "invalid_init":
        data["initial_state"].update(valid=1, key=0, value=7)
    if control == "invalid_preservation":
        variant = "corrupt"
        data["variants"][variant] = "cached_corrupt"
        params = ", ".join("uint32_t " + name for name in data["call_args"])
        args = ", ".join(data["call_args"])
        model += f"""
static uint32_t cached_corrupt(Cache *cache, {params})
{{
    uint32_t result = cached_good(cache, {args});
    cache->value ^= UINT32_C(1);
    return result;
}}
"""
    save_json(directory / "sketch.json", data)
    sketch = CacheSketch(directory / "sketch.json")
    save_json(directory / "sketch-manifest.json", sketch.manifest())
    source = directory / "harness.c"
    source.write_text(sketch.render(model, variant, "invariant", kind), encoding="utf-8")
    return source, kind, "REFUTED" if control.startswith("invalid") else "PROVED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--workdir", default=".verify-equiv-runs/sketch-controls")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be finite and positive")
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="run-", dir=root))
    (run / "cache_sketch.py").write_bytes((ROOT / "tools/find-cond-equiv/cache_sketch.py").read_bytes())
    oracle.run([args.esbmc, "--version"], run / "esbmc-version.txt", args.timeout)
    results = []
    for family in ("same_language_cache", "config_cache"):
        for control in ("valid_init", "invalid_init", "valid_preservation", "invalid_preservation"):
            directory = run / f"{family}-{control}"
            directory.mkdir()
            source, kind, expected = prepare_control(family, control, directory)
            command = [args.esbmc, str(source), "--function", "finder_entry", "--z3", "--unwind", "12", "--overflow-check"]
            result = check_obligation(oracle, command, directory / "verify.log", args.timeout, PROPERTIES[kind])
            result.update(case=directory.name, expected=expected, passed=result["status"] == expected,
                          source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            save_json(directory / "result.json", result)
            results.append(result)
            print(f"{directory.name}: {result['status']} expected={expected}", flush=True)
    save_json(run / "results.json", results)
    save_json(root / "results.json", results)
    count = sum(row["passed"] for row in results)
    print(f"SKETCH CONTROLS: {count}/{len(results)} passed")
    print(f"Artifacts: {run}")
    return 0 if count == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
