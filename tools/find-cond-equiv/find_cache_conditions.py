#!/usr/bin/env python3
"""Trace-guided condition search for a reviewed, private single-entry C cache.

Inspired by Agentic Concolic Execution: native traces/hypotheses guide search,
but every published region is checked against uninstrumented C by ESBMC.
There is no LLM API call or automatic invariant discovery in this baseline.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases" / "same_language_cache"
sys.path.insert(0, str(ROOT / "tools" / "verify-equiv"))
import verify_equiv as oracle
from c_obligation import check as check_obligation
from predicate_search import Atom, FIELDS, UINT32_MAX, cube_expression, initial_atoms, matches, search

from cache_sketch import CacheSketch, PROPERTIES
from c_backend import CBackend, save_json, validate_seed, witness_from_log
from condition_runner import run as run_conditions

SKETCH = CacheSketch(CASE / "sketch.json")
VARIANTS = SKETCH.data["variants"]
assert PROPERTIES["equal"] == oracle.RELATIONAL_PROPERTY


def default_seeds(state_mode):
    # Generic boundary and ordinary inputs; labels come only from actual C.
    numbers = (0, 1, 7, 8, UINT32_MAX)
    if state_mode == "empty":
        return [dict(x=x, valid=0, key=0, value=0) for x in numbers]
    return [dict(x=x, valid=valid, key=key, value=(key+1) & UINT32_MAX)
            for x, valid, key in itertools.product(numbers, (0, 1), numbers)]


def seed_in_domain(row, state_mode):
    if state_mode == "empty":
        return row["valid"] == 0 and row["key"] == 0 and row["value"] == 0
    return not row["valid"] or row["value"] == (row["key"]+1) & UINT32_MAX


def make_harness(model, variant, state_mode, kind, condition="true", expected=None):
    return SKETCH.render(model, variant, state_mode, kind, condition, expected)


class CacheBackend(CBackend):
    probe_filename = "cache_probe.c"
    unwind = 12
    sketch = SKETCH
    case = CASE
    fields = FIELDS
    numeric_fields = Atom.numeric_fields
    atom_type = Atom
    variants = VARIANTS
    initial_atoms = staticmethod(initial_atoms)
    default_seeds = staticmethod(default_seeds)
    seed_in_domain = staticmethod(seed_in_domain)
    make_harness = staticmethod(make_harness)

    @classmethod
    def validate_seed(cls, row):
        return validate_seed(row, cls.fields)

    def __init__(self, args, workdir):
        self.args, self.workdir = args, Path(workdir)
        if tuple(self.sketch.data["fields"]) != tuple(self.fields) or self.sketch.data["variants"] != self.variants:
            raise ValueError("adapter fields/variants disagree with sketch bindings")
        self.deadline = time.monotonic() + args.max_seconds
        self.samples, self.queries, self.replays = [], [], []
        self.seen = set()
        self.model_bytes = (self.case / "cache_model.h").read_bytes()
        self.model = self.model_bytes.decode("utf-8")
        self.probe_bytes = (self.case / "cache_probe.c").read_bytes()
        self.inputs = self.workdir / "inputs"
        self.inputs.mkdir()
        save_json(self.inputs / "sketch.json", self.sketch.data)
        (self.inputs / "cache_sketch.py").write_bytes((ROOT / "tools/find-cond-equiv/cache_sketch.py").read_bytes())
        self.sketch_manifest = self.sketch.manifest()
        save_json(self.workdir / "sketch-manifest.json", self.sketch_manifest)
        (self.inputs / "cache_model.h").write_bytes(self.model_bytes)
        (self.inputs / "cache_probe.c").write_bytes(self.probe_bytes)
        self.scope = {
            "language": "C", "inputs": "x,key,value:uint32_t; valid:bool; unsigned arithmetic modulo 2^32",
            "state_mode": args.state_mode,
            "initial_state": "empty {0,0,0}" if args.state_mode == "empty" else "arbitrary state satisfying !valid || value == original(key)",
            "observations": "one return value; cache invariant also checked after the call",
            "assumptions": "private cache; sequential execution; pure original; no environment or other writers",
            "bound": "one loop-free call; initialization and invariant preservation are separate obligations",
            "condition_discovery": "automatic combination within a bounded vocabulary; invariant/model supplied by hand",
            "sequence_claim": "no unrestricted sequence equivalence claimed for conditional variants",
            "model_sha256": hashlib.sha256(self.model_bytes).hexdigest(),
            "probe_sha256": hashlib.sha256(self.probe_bytes).hexdigest(),
        }
        self.esbmc = shutil.which(args.esbmc)
        self.version = None
        self.executable = self.inputs / ("cache-probe.exe" if sys.platform == "win32" else "cache-probe")


    def state_obligations(self):
        return {"initialization": self.query("init", reserve=2),
                "preservation": self.query("preservation", reserve=2)}


    def validate_trace(self, row):
        if row.get("invariant_before") != 1 or row.get("invariant_after") != 1:
            raise RuntimeError("native trace violates the declared cache invariant")
        if row.get("hit") not in (0, 1):
            raise RuntimeError("native branch trace missing")


def parse_args(argv=None, variants=VARIANTS, default_variant="bad_miss", default_workdir=".verify-equiv-runs/condition-finder"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--variant", choices=variants, default=default_variant)
    parser.add_argument("--state-mode", choices=("invariant", "empty"), default="invariant")
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc", help="C compiler executable (cc/gcc/clang/cl)")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--max-queries", type=int, default=96)
    parser.add_argument("--max-predicates", type=int, default=16)
    parser.add_argument("--hypotheses", help="optional untrusted JSON {predicates:[...],seeds:[...]}; no code execution")
    parser.add_argument("--workdir", default=default_workdir)
    args = parser.parse_args(argv)
    if not all(math.isfinite(value) and value > 0 for value in (args.timeout, args.max_seconds)) or args.max_queries < 4 or not 11 <= args.max_predicates <= 24:
        parser.error("positive time budgets, >=4 queries and 11..24 predicates are required")
    return args


def run(args, backend_type=CacheBackend):
    return run_conditions(args, backend_type)


def main(argv=None):
    report = run(parse_args(argv))
    return 0 if report["status"] == "EXACT" else 2


if __name__ == "__main__":
    sys.exit(main())
