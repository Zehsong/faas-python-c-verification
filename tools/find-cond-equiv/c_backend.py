"""Shared C process, oracle, replay and region classification infrastructure.

No case model or sketch binding is loaded by this module.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from predicate_search import FIELDS, UINT32_MAX, cube_expression, matches
from cache_sketch import PROPERTIES
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/verify-equiv"))
import verify_equiv as oracle
from c_obligation import check as check_obligation
from result_contract import ExecutionFailure, diagnostic_code

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



class CBackend:
    properties = PROPERTIES
    command_extra = ()
    proof_before_replay = False

    def restore_obligations(self, obligations):
        pass

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())


    def present_condition(self, found):
        return {"condition": found["condition"], "condition_c": found["condition_c"],
                "basis": "disjunction of individually proved regions; Boolean-only simplification"}


    def prepare(self):
        compiler = shutil.which(self.args.cc)
        if compiler is None:
            raise ExecutionFailure("COMPILER_NOT_FOUND", f"C compiler not found: {self.args.cc}")
        source = str(self.inputs / self.probe_filename)
        if Path(compiler).stem.lower() == "cl":
            command = [compiler, "/nologo", "/std:c11", "/W4", source,
                       "/Fe:" + str(self.executable), "/Fo:" + str(self.inputs / "probe.obj")]
        else:
            command = [compiler, "-std=c11", "-O0", "-Wall", "-Wextra", source, "-o", str(self.executable)]
        save_json(self.inputs / "compile-command.json", command)
        rc, timed_out = oracle.run(command, self.inputs / "compile.log", max(0.01, min(60, self.remaining())))
        if timed_out or rc != 0:
            raise ExecutionFailure("COMPILE_TIMEOUT" if timed_out else "COMPILE_FAILED",
                                   "native probe compilation failed; see inputs/compile.log")
        if self.esbmc:
            self.esbmc = str(Path(self.esbmc).resolve())
            rc, timed_out = oracle.run([self.esbmc, "--version"], self.workdir / "version.log",
                                      max(0.01, min(self.args.timeout, self.remaining())))
            self.version = oracle.read_text(self.workdir / "version.log")
            if timed_out or rc != 0:
                self.esbmc = None
                self.solver_unavailable_code = "SOLVER_STARTUP_TIMEOUT" if timed_out else "SOLVER_STARTUP_FAILED"


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
            return {"status": "UNKNOWN", "reason": f"ESBMC unavailable: {self.args.esbmc}",
                    "reason_code": getattr(self, "solver_unavailable_code", "SOLVER_NOT_FOUND"), "kind": kind}
        if self.remaining() <= 0:
            return {"status": "UNKNOWN", "reason": "wall-clock budget exhausted", "reason_code": "TIME_BUDGET_EXHAUSTED", "kind": kind}
        if len(self.queries) >= self.args.max_queries - reserve:
            return {"status": "UNKNOWN", "reason": "query budget exhausted", "reason_code": "QUERY_BUDGET_EXHAUSTED", "kind": kind}
        index = len(self.queries)
        path = self.workdir / f"query-{index:03d}-{kind}"
        path.mkdir()
        source = path / "harness.c"
        source.write_text(self.make_harness(self.model, self.args.variant, self.args.state_mode,
                                      kind, condition, expected), encoding="utf-8")
        command = [self.esbmc, str(source), "--function", "finder_entry", "--z3",
                   "--unwind", str(self.unwind), "--overflow-check", *self.command_extra]
        result = check_obligation(oracle, command, path / "verify.log",
                                  min(self.args.timeout, self.remaining()), self.properties[kind])
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
                    result.update(status="UNKNOWN", reason=str(exc), reason_code="WITNESS_REPLAY_FAILED")
        if result["status"] == "UNKNOWN" and not result.get("reason_code"):
            if result.get("timed_out"):
                result["reason_code"] = "SOLVER_TIMEOUT"
            elif result.get("violation"):
                result["reason_code"] = diagnostic_code(result)
            else:
                result["reason_code"] = "SOLVER_FAILED" if result.get("returncode") != 0 else "UNRECOGNIZED_SOLVER_OUTPUT"
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
