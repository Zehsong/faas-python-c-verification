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

SKETCH = CacheSketch(CASE / "sketch.json")
VARIANTS = SKETCH.data["variants"]
assert PROPERTIES["equal"] == oracle.RELATIONAL_PROPERTY


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_seed(row, fields=FIELDS):
    if not isinstance(row, dict) or set(row) != set(fields):
        raise ValueError("seed must have exactly " + ", ".join(fields))
    for field in fields:
        if field == "valid":
            continue
        if type(row[field]) is not int or not 0 <= row[field] <= UINT32_MAX:
            raise ValueError(f"invalid uint32_t seed field {field}")
    if "valid" in fields:
        if type(row["valid"]) not in (bool, int) or row["valid"] not in (0, 1):
            raise ValueError("valid must be boolean or 0/1")
        return {**row, "valid": int(row["valid"])}
    return dict(row)


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


def witness_from_log(text, fields=FIELDS):
    values = {}
    for field in fields:
        found = re.findall(rf"(?m)^\s*finder_{field}\s*=(?!=)\s*(true|false|[0-9]+)(?=\s|$)", text)
        if not found:
            return None
        # These entry-state variables are never assigned after initialization.
        token = found[-1]
        values[field] = int(token == "true") if token in ("true", "false") else int(token)
    try:
        return validate_seed(values, fields)
    except ValueError:
        return None


def make_harness(model, variant, state_mode, kind, condition="true", expected=None):
    return SKETCH.render(model, variant, state_mode, kind, condition, expected)


class CacheBackend:
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

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())

    def state_obligations(self):
        return {"initialization": self.query("init", reserve=2),
                "preservation": self.query("preservation", reserve=2)}

    def present_condition(self, found):
        return {"condition": found["condition"], "condition_c": found["condition_c"],
                "basis": "disjunction of individually proved regions; Boolean-only simplification"}

    def validate_trace(self, row):
        if row.get("invariant_before") != 1 or row.get("invariant_after") != 1:
            raise RuntimeError("native trace violates the declared cache invariant")
        if row.get("hit") not in (0, 1):
            raise RuntimeError("native branch trace missing")

    def prepare(self):
        compiler = shutil.which(self.args.cc)
        if compiler is None:
            raise RuntimeError(f"C compiler not found: {self.args.cc}")
        source = str(self.inputs / self.probe_filename)
        if Path(compiler).stem.lower() == "cl":
            command = [compiler, "/nologo", "/std:c11", "/W4", source,
                       "/Fe:" + str(self.executable), "/Fo:" + str(self.inputs / "probe.obj")]
        else:
            command = [compiler, "-std=c11", "-O0", "-Wall", "-Wextra", source, "-o", str(self.executable)]
        save_json(self.inputs / "compile-command.json", command)
        rc, timed_out = oracle.run(command, self.inputs / "compile.log", max(0.01, min(60, self.remaining())))
        if timed_out or rc != 0:
            raise RuntimeError("native probe compilation failed; see inputs/compile.log")
        if self.esbmc:
            self.esbmc = str(Path(self.esbmc).resolve())
            rc, timed_out = oracle.run([self.esbmc, "--version"], self.workdir / "version.log",
                                      max(0.01, min(self.args.timeout, self.remaining())))
            self.version = oracle.read_text(self.workdir / "version.log")
            if timed_out or rc != 0:
                self.esbmc = None

    def replay(self, rows, origin="boundary_seeds", repeat=False):
        inputs = [self.validate_seed(row) for row in rows]
        inputs = [row for row in inputs if self.seed_in_domain(row, self.args.state_mode)]
        if not repeat:
            inputs = [row for row in inputs if tuple(row[field] for field in self.fields) not in self.seen]
        if not inputs:
            return []
        data = "".join(" ".join(str(row[field]) for field in self.fields) + "\n" for row in inputs)
        command = [str(self.executable), self.args.variant]
        try:
            proc = subprocess.run(command, input=data, capture_output=True, text=True,
                                  timeout=max(0.01, min(10, self.remaining())))
            if proc.returncode != 0:
                raise RuntimeError(f"native probe returned {proc.returncode}: {proc.stderr}")
            observed = [json.loads(line) for line in proc.stdout.splitlines()]
            if len(observed) != len(inputs):
                raise RuntimeError("native probe did not return one trace per input")
            for given, row in zip(inputs, observed):
                if any(row.get(field) != given[field] for field in self.fields):
                    raise RuntimeError("native trace/input mismatch")
                self.validate_trace(row)
                for field in ("r_original", "r_cached"):
                    if type(row.get(field)) is not int or not 0 <= row[field] <= UINT32_MAX:
                        raise RuntimeError("invalid return value in native trace")
                key = tuple(given[field] for field in self.fields)
                if key not in self.seen:
                    self.samples.append(row)
                    self.seen.add(key)
            self.replays.append({"origin": origin, "command": command, "stdin": data,
                                 "stdout": proc.stdout, "returncode": proc.returncode})
            return observed
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise RuntimeError(f"native replay failed: {exc}") from exc

    def query(self, kind, condition="true", reserve=0, expected=None):
        if not self.esbmc:
            return {"status": "UNKNOWN", "reason": f"ESBMC unavailable: {self.args.esbmc}"}
        if len(self.queries) >= self.args.max_queries - reserve or self.remaining() <= 0:
            return {"status": "UNKNOWN", "reason": "query or wall-clock budget exhausted"}
        index = len(self.queries)
        path = self.workdir / f"query-{index:03d}-{kind}"
        path.mkdir()
        source = path / "harness.c"
        source.write_text(self.make_harness(self.model, self.args.variant, self.args.state_mode,
                                      kind, condition, expected), encoding="utf-8")
        command = [self.esbmc, str(source), "--function", "finder_entry", "--z3",
                   "--unwind", str(self.unwind), "--overflow-check"]
        result = check_obligation(oracle, command, path / "verify.log",
                                  min(self.args.timeout, self.remaining()), PROPERTIES[kind])
        result.update(kind=kind, condition_c=condition,
                      source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        if result["status"] == "REFUTED" and kind in ("feasible", "equal", "different"):
            witness = witness_from_log(oracle.read_text(path / "verify.log"), self.fields)
            result["witness"] = witness
            result["native_replay"] = "unavailable: entry-state assignments not parsed"
            if witness is not None:
                try:
                    observed = self.replay([witness], origin=f"query-{index}-{kind}", repeat=True)
                    if not observed:
                        raise RuntimeError("solver witness is outside the declared state domain")
                    same = observed[0]["r_original"] == observed[0]["r_cached"]
                    if (kind == "equal" and same) or (kind == "different" and not same):
                        raise RuntimeError("solver/native observation disagreement")
                    result["native_replay"] = observed[0]
                except RuntimeError as exc:
                    result.update(status="UNKNOWN", reason=str(exc))
        self.queries.append(result)
        save_json(path / "result.json", result)
        print(f"  query {index:03d} {kind}: {result['status']}", flush=True)
        return result

    def classify(self, cube, atoms):
        condition = cube_expression(cube, atoms, c=True)
        def query(kind):
            result = self.query(kind, condition, reserve=2)
            replay = result.get("native_replay")
            if isinstance(replay, dict) and not matches(cube, atoms, replay):
                return {"status": "UNKNOWN", "reason": "native replay did not reach the requested predicate region",
                        "property_result": result}
            return result
        feasible = query("feasible")
        if feasible["status"] == "PROVED":
            return {"status": "EMPTY", "evidence": feasible}
        if feasible["status"] != "REFUTED":
            return {"status": "UNKNOWN", "evidence": feasible}
        equal = query("equal")
        if equal["status"] == "PROVED":
            return {"status": "EQ", "evidence": equal}
        if equal["status"] != "REFUTED":
            return {"status": "UNKNOWN", "evidence": equal}
        different = query("different")
        if different["status"] == "PROVED":
            return {"status": "ALL_NEQ", "evidence": different}
        if different["status"] == "REFUTED":
            return {"status": "MIXED", "unequal_witness": equal, "equal_witness": different}
        return {"status": "UNKNOWN", "evidence": different, "unequal_witness": equal}


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
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix=args.variant + "-", dir=root))
    report = {"status": "UNKNOWN", "variant": args.variant, "state_mode": args.state_mode,
              "created_utc": datetime.now(timezone.utc).isoformat(), "artifacts": str(workdir),
              "condition": None, "exact": False, "uses_llm_api": False,
              "method": "trace-guided finite predicate partition with ESBMC certification"}
    backend = None
    try:
        atoms = backend_type.initial_atoms()
        extra_seeds = []
        if args.hypotheses:
            proposal = json.loads(Path(args.hypotheses).read_text(encoding="utf-8"))
            if not isinstance(proposal, dict) or set(proposal) - {"predicates", "seeds"}:
                raise ValueError("hypotheses only accept predicates and seeds; no claimed verdicts")
            if not isinstance(proposal.get("predicates", []), list) or not isinstance(proposal.get("seeds", []), list):
                raise ValueError("predicates and seeds must be arrays")
            if len(proposal.get("seeds", [])) > 256:
                raise ValueError("at most 256 proposed seeds are supported")
            for text in proposal.get("predicates", []):
                atom = backend_type.atom_type.parse(text)
                if atom not in atoms:
                    atoms.append(atom)
            extra_seeds = [backend_type.validate_seed(row) for row in proposal.get("seeds", [])]
            save_json(workdir / "hypotheses.json", proposal)
        if len(atoms) > args.max_predicates:
            raise ValueError("initial vocabulary exceeds --max-predicates")
        backend = backend_type(args, workdir)
        report["scope"] = backend.scope
        report["sketch"] = backend.sketch_manifest
        backend.prepare()
        backend.replay(backend.default_seeds(args.state_mode))
        backend.replay(extra_seeds, origin="untrusted_hypotheses")
        obligations = backend.state_obligations()
        report["state_obligations"] = obligations
        if any(result["status"] != "PROVED" for result in obligations.values()):
            raise RuntimeError("initialization/invariant preservation not established; no certified condition")
        found = search(backend, atoms, args.max_predicates)
        report["search"] = found
        presentation = backend.present_condition(found)
        report["condition"] = presentation["condition"]
        # Revalidate the published condition; prove its complement contains only
        # unequal observations before claiming an exact domain within this model.
        final = backend.query("equal", presentation["condition_c"])
        outside = backend.query("different", f"!({presentation['condition_c']})")
        report["final_validation"] = {"sufficiency": final, "complement": outside}
        report["exact"] = final["status"] == "PROVED" and outside["status"] == "PROVED"
        report["status"] = "EXACT" if report["exact"] else "PARTIAL" if found["buckets"]["EQ"] else "UNKNOWN"
        report["condition_c"] = presentation["condition_c"]
        report["condition_basis"] = presentation["basis"]
        if final["status"] == "REFUTED" or (final["status"] == "UNKNOWN" and final.get("reason", "").startswith("solver/native")):
            report.update(status="UNKNOWN", exact=False, condition=None, condition_c=None,
                          reason="final validation contradicted prior certificates; do not use this condition")
        # Do not present an empty sufficient condition as a useful discovery.
        if not found["buckets"]["EQ"] and not report["exact"]:
            report["condition"] = None
    except (OSError, ValueError, RuntimeError) as exc:
        report["reason"] = str(exc)
    if backend:
        report.update(esbmc=backend.esbmc, esbmc_version_output=backend.version,
                      queries_used=len(backend.queries), traces_collected=len(backend.samples))
        save_json(workdir / "traces.json", backend.samples)
        save_json(workdir / "replays.json", backend.replays)
        save_json(workdir / "queries.json", backend.queries)
        save_json(workdir / "agent-context.json", {
            "scope": backend.scope, "model_source": backend.model,
            "variant_function": backend.variants[args.variant], "traces": backend.samples,
            "current_result": report, "proposal_schema": {"predicates": ["x == 42"], "seeds": []},
            "trust": "Propose only entry-state predicates or inputs; labels and proof claims are not accepted."})
    save_json(workdir / "result.json", report)
    save_json(root / "result.json", report)
    print(f"{report['status']}: {report['condition']}")
    print(f"Artifacts: {workdir}")
    return report


def main(argv=None):
    report = run(parse_args(argv))
    return 0 if report["status"] == "EXACT" else 2


if __name__ == "__main__":
    sys.exit(main())
