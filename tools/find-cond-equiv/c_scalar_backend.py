"""Contract-bound scalar/bounded-array C adapter for discovery and agent sessions."""
import hashlib
import itertools
from pathlib import Path
import shutil
import sys
import time

from c_backend import CBackend, save_json
from c_scalar_contract import Contract
from predicate_search import UINT32_MAX


def bind_contract(path):
    contract = Contract(path)

    ScalarAtom = contract.domain.atom_type

    class ScalarBackend(CBackend):
        proof_before_replay = True
        command_extra = ("--no-slice",)
        properties = {**CBackend.properties, "safety": "__C_SCALAR_SAFETY__"}
        probe_filename = "scalar_probe.c"
        fields = contract.fields
        numeric_fields = contract.fields
        atom_type = ScalarAtom
        variants = {"pair": contract.data["candidate"]["entry"]}
        unwind = contract.data["unwind"]

        def __init__(self, args, workdir):
            if Contract(contract.path).identity != contract.identity:
                raise ValueError("C contract/source changed after binding; start again")
            self.args, self.workdir = args, Path(workdir)
            self.deadline = time.monotonic() + args.max_seconds
            self.samples, self.queries, self.replays, self.seen = [], [], [], set()
            self.safety_established = False
            self.inputs = self.workdir / "inputs"
            self.inputs.mkdir()
            self.model = contract.model()
            save_json(self.inputs / "contract.json", contract.data)
            for side, source in contract.sources.items():
                (self.inputs / f"{side}.c").write_bytes(source.data)
            (self.inputs / "bound_model.h").write_text(self.model, encoding="utf-8")
            (self.inputs / self.probe_filename).write_text(self.probe(), encoding="utf-8")
            adapter_name = "c-bounded-array-v2" if contract.arrays else "c-scalar-v1"
            if contract.data["schema"] == 3:
                adapter_name = "c-domain-v3"
            self.sketch_manifest = {"template": adapter_name, "contract": contract.data,
                                    "source_identity": contract.identity,
                                    "model_sha256": hashlib.sha256(self.model.encode()).hexdigest()}
            save_json(self.workdir / "sketch-manifest.json", self.sketch_manifest)
            self.scope = {"language": "C", "adapter": adapter_name, "inputs": contract.input_specs,
                          "observations": "return value of one call", "return_type": contract.data["return_type"],
                          "state": "pure functions with scalar inputs/return and optional automatic const tables; no globals, pointers or external calls",
                          "memory": {"tables": {side: source.tables for side, source in contract.sources.items()},
                                     "policy": "read-only local tables, fully literal-initialized; at most 256 elements per source; no pointer decay",
                                     "bounds": "all indexed reads require whole-domain ESBMC safety before native replay"},
                          "arithmetic": "uint32_t modulo 2^32; bool; 32-bit int/unsigned int; 8-bit bytes",
                          "bound": {"unwind": self.unwind, "unwinding_assertions": True},
                          "safety": "whole declared domain must pass safety and unwinding before native replay",
                          "condition_discovery": "finite entry-state comparison vocabulary; no completeness beyond certified domain",
                          "source_identity": contract.identity}
            if contract.data["schema"] == 3:
                self.scope.update(declared_inputs=contract.data["inputs"],
                    input_domain={"constraints": contract.data.get("constraints", True),
                                  "structural_constraints": contract.structural_constraints,
                                  "expression": contract.domain.expression(),
                                  "expression_c": contract.domain.expression(c=True),
                                  "bounds": "omitted bounds use the complete declared type range",
                                  "meaning": "normalized input bounds AND user constraints AND structural constraints; all claims are relative to this domain"})
            if contract.arrays:
                self.scope.update(declared_inputs=contract.data["inputs"],
                                  observations=contract.data["observations"],
                                  state="one call with independent, fully initialized, non-aliasing array copies per side; no persistent globals")
                self.scope["memory"].update(arrays=contract.arrays,
                    policy="local const tables plus fixed array parameters; every array element observed after both calls; no pointer operations or aliasing",
                    bounds="all array reads/writes require whole-domain safety and complete unwinding before native replay",
                    observation_order=["return", *[f"{n}[{i}]" for n, s in contract.arrays.items() for i in range(s["length"])]],
                    entry_field_mapping={f"{n}_{i}": f"{n}[{i}]" for n, s in contract.arrays.items() for i in range(s["length"])})
                if contract.data["schema"] == 3:
                    self.scope["memory"].update(logical_lengths=contract.logical_lengths,
                        observation_extent="entire physical capacity, including elements beyond the logical length",
                        limits={"array_capacity": 64, "total_initial_values": 128})
            if len(contract.fields) > 4:
                self.scope["condition_discovery"] = "at most 24 initial predicates; at most 256 sparse boundary seeds; solver queries still cover the entire declared domain"
            if contract.logical_lengths:
                self.scope["proof_decomposition"] = {
                    "strategy": "after equal/different timeout, partition one explicit logical length",
                    "max_parts": 17,
                    "requirements": "whole-domain safety, solver-proved coverage and every part proved; shared query/time budgets",
                    "observations": "unchanged complete observation vector; all other inputs remain symbolic"}
            self.esbmc, self.version = shutil.which(args.esbmc), None
            self.executable = self.inputs / ("scalar-probe.exe" if sys.platform == "win32" else "scalar-probe")

        @classmethod
        def validate_seed(cls, row):
            if not isinstance(row, dict) or set(row) != set(cls.fields):
                raise ValueError("seed must contain exactly the contract inputs")
            for name, value in row.items():
                spec = contract.input_specs[name]
                limit = 1 if spec["type"] == "bool" else UINT32_MAX
                if type(value) is not int or not 0 <= value <= limit:
                    raise ValueError(f"invalid scalar seed: {name}")
            return dict(row)

        @staticmethod
        def seed_in_domain(row, state_mode):
            return contract.domain.contains(row)

        @classmethod
        def initial_atoms(cls):
            if len(cls.fields) > 4:
                # Prioritize scalar controls, then both ends of each array.
                # This is a heuristic vocabulary, never an input restriction.
                priority = [n for n in contract.data["inputs"] if n not in contract.arrays]
                for name, spec in contract.arrays.items():
                    priority += [f"{name}_0", f"{name}_{spec['length'] - 1}"]
                priority = list(dict.fromkeys(priority))
                texts = [f"{n} == {v}" for n in priority
                         for v in sorted({contract.input_specs[n]['min'], contract.input_specs[n]['max']})]
                texts += [f"{a} == {b}" for a, b in itertools.combinations(priority, 2)]
                return [cls.atom_type.parse(text) for text in texts[:24]]
            atoms = [cls.atom_type.parse(f"{a} == {b}") for a, b in itertools.combinations(cls.fields, 2)]
            for name, spec in contract.input_specs.items():
                atoms += [cls.atom_type.parse(f"{name} == {n}") for n in sorted({spec["min"], spec["max"]})]
            return atoms

        @classmethod
        def default_seeds(cls, state_mode):
            values = []
            for name, spec in contract.input_specs.items():
                upper = min([spec['max'], *[contract.arrays[a]['length']
                            for a, field in contract.logical_lengths.items() if field == name]])
                if spec['min'] > upper:
                    return []  # Feasibility still requires a solver query.
                values.append(sorted({spec['min'], upper, (spec['min'] + upper) // 2}))
            if len(cls.fields) <= 4:
                rows = itertools.product(*values)
            else:
                base = tuple(v[0] for v in values)
                rows = [base, tuple(v[-1] for v in values), tuple(v[len(v)//2] for v in values)]
                for index, choices in enumerate(values):
                    rows += [base[:index] + (value,) + base[index+1:] for value in choices[1:]]
                rows = list(dict.fromkeys(rows))[:256]
            return [seed for row in rows if contract.domain.contains(seed := dict(zip(cls.fields, row)))]

        def state_obligations(self):
            result = self.query("safety", reserve=2)
            self.safety_established = result["status"] == "PROVED"
            return {"safety": result}

        def restore_obligations(self, obligations):
            # Called only after agent_workflow checks source/contract/tool identity.
            self.safety_established = obligations.get("safety", {}).get("status") == "PROVED"

        def query(self, kind, condition="true", reserve=0, expected=None):
            direct = super().query(kind, condition, reserve, expected)
            if (kind not in ("equal", "different") or not self.safety_established
                    or direct.get("status") != "UNKNOWN"
                    or direct.get("reason_code") != "SOLVER_TIMEOUT"):
                return direct
            choices = []
            for field in sorted(set(contract.logical_lengths.values())):
                spec = contract.input_specs[field]
                upper = min([spec['max'], *[contract.arrays[a]['length']
                            for a, name in contract.logical_lengths.items() if name == field]])
                count = upper - spec['min'] + 1
                if 2 <= count <= 17:
                    choices.append((count, field, spec['min'], upper))
            if not choices:
                return direct
            count, field, lower, upper = min(choices)
            # One coverage obligation plus each part, preserving caller reserves.
            # All actual calls still enforce both budgets in CBackend.query.
            if self.remaining() <= 0 or len(self.queries) + count + 1 > self.args.max_queries - reserve:
                return direct
            parts = [f"finder_{field} == UINT32_C({value})" for value in range(lower, upper + 1)]
            union = " || ".join(f"({part})" for part in parts)
            proof_path = self.workdir / f"length-partition-{len(self.queries):03d}.json"
            coverage = super().query("feasible", f"({condition}) && !({union})", reserve)
            result = {"status": "UNKNOWN", "basis": "EXHAUSTIVE_LENGTH_PARTITION",
                      "kind": kind, "condition_c": condition, "field": field,
                      "parts": parts, "direct_attempt": direct, "coverage": coverage,
                      "checks": [], "evidence_file": str(proof_path)}
            if coverage['status'] == 'PROVED':
                for part in parts:
                    checked = super().query(kind, f"({condition}) && ({part})", reserve, expected)
                    result['checks'].append(checked)
                    if checked['status'] == 'REFUTED':
                        # This is also a counterexample in the parent region.
                        result.update(status='REFUTED', witness=checked.get('witness'),
                                      native_replay=checked.get('native_replay'))
                        break
                    if checked['status'] != 'PROVED':
                        break
                if len(result['checks']) == count and all(q['status'] == 'PROVED' for q in result['checks']):
                    result['status'] = 'PROVED'
            if result['status'] == 'UNKNOWN':
                result['reason'] = 'Length partition did not establish coverage and every part; no composed proof'
            save_json(proof_path, result)
            print(f"  length partition {field} [{lower}, {upper}] {kind}: {result['status']}", flush=True)
            return result

        def replay(self, rows, origin="boundary_seeds", repeat=False):
            if not self.safety_established:
                raise RuntimeError("native replay disabled until whole-domain safety is proved")
            return super().replay(rows, origin, repeat)

        def validate_trace(self, row):
            if contract.data["return_type"] == "bool" and any(row.get(n) not in (0, 1) for n in ("r_original", "r_cached")):
                raise RuntimeError("native boolean return outside 0/1")
            if contract.arrays:
                for side, return_name in (("original", "r_original"), ("candidate", "r_cached")):
                    values = row.get("observations_" + side)
                    types = contract.observation_types()
                    if not isinstance(values, list) or len(values) != len(types) or any(
                            type(v) is not int or not 0 <= v <= (1 if t == "bool" else UINT32_MAX)
                            for v, t in zip(values, types)) or values[0] != row.get(return_name):
                        raise RuntimeError("invalid native array observation vector")

        @staticmethod
        def make_harness(model, variant, state_mode, kind, condition="true", expected=None):
            if kind not in ("safety", "feasible", "equal", "different", "expected"):
                raise ValueError("unsupported scalar obligation")
            declarations = []
            for name, spec in contract.input_specs.items():
                declarations += [f"  uint32_t finder_{name} = nondet_uint32_t();",
                                 f"  __ESBMC_assume(finder_{name} >= UINT32_C({spec['min']}) && finder_{name} <= UINT32_C({spec['max']}));"]
            if contract.data["schema"] == 3:
                declarations.append(f"  __ESBMC_assume({contract.domain.expression(c=True)});")
            statements = [] if kind == "expected" else [f"  __ESBMC_assume({condition});"]
            if kind != "feasible":
                statements += contract.argument_copies()
                statements += [f"  volatile {contract.data['return_type']} ce_left = {contract.call('original')};",
                               f"  volatile {contract.data['return_type']} ce_right = {contract.call('candidate')};"]
            equality = contract.equality()
            assertion = {"safety": "true", "feasible": "false", "equal": equality, "different": f"!({equality})",
                         "expected": f"({condition}) == ({expected})"}[kind]
            statements += [f'  __ESBMC_assert({assertion}, "{ScalarBackend.properties[kind]}");']
            return model + "\nextern uint32_t nondet_uint32_t(void);\nvoid finder_entry(void) {\n" + "\n".join(declarations + statements) + "\n}\n"

        @staticmethod
        def probe():
            # Every input reaching this executable is revalidated by replay().
            names = contract.fields
            temps = ", ".join("ce_input_" + name for name in names)
            formats = " ".join("%llu" for _ in names)
            addresses = ", ".join("&ce_input_" + name for name in names)
            lines = [contract.model(), "#include <stdio.h>", "int main(void) {", f"  unsigned long long {temps};",
                     f'  while (scanf("{formats}", {addresses}) == {len(names)}) {{']
            for name, spec in contract.input_specs.items():
                lines += [f"    if (ce_input_{name} < {spec['min']}ull || ce_input_{name} > {spec['max']}ull) return 2;",
                          f"    {spec['type']} finder_{name} = ({spec['type']})ce_input_{name};"]
            if contract.data["schema"] == 3:
                lines.append(f"    if (!({contract.domain.expression(c=True)})) return 2;")
            lines += contract.argument_copies()
            lines += [f"    {contract.data['return_type']} ce_left = {contract.call('original')};",
                      f"    {contract.data['return_type']} ce_right = {contract.call('candidate')};"]
            fields = [*names, "r_original", "r_cached"]
            values = [*("finder_" + n for n in names), "ce_left", "ce_right"]
            fragments = ['\\"' + n + '\\":%llu' for n in fields]
            if contract.arrays:
                for side in ("original", "candidate"):
                    observed = contract.observation_values(side)
                    fragments.append('\\"observations_' + side + '\\":[' + ','.join('%llu' for _ in observed) + ']')
                    values += observed
            fmt = "{" + ",".join(fragments) + "}\\n"
            lines += ['    printf("' + fmt + '", ' + ", ".join("(unsigned long long)" + v for v in values) + ");",
                      "  }", "  return 0;", "}"]
            return "\n".join(lines) + "\n"

    ScalarBackend.contract = contract
    return ScalarBackend
