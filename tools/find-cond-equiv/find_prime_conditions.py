#!/usr/bin/env python3
"""Bounded stateless same-language primality computation vs lookup experiment."""
import argparse
from dataclasses import dataclass
import hashlib
import math
import re
from pathlib import Path
import shutil
import sys
import time

from find_cache_conditions import CacheBackend, PROPERTIES, ROOT, oracle, run as shared_run, save_json
from predicate_search import Atom, matches

CASE = ROOT / "cases/prime_lookup"
VARIANTS = {"fallback": "lookup_fallback", "truncated": "lookup_truncated", "mutant": "lookup_mutant"}
MODULI = tuple(range(2, 17))


@dataclass(frozen=True)
class ModuloAtom:
    divisor: int
    remainder: int

    def __post_init__(self):
        if type(self.divisor) is not int or type(self.remainder) is not int or not 2 <= self.divisor <= 16 or not 0 <= self.remainder < self.divisor:
            raise ValueError("modulo predicate requires 2..16 divisor and 0 <= remainder < divisor")

    def text(self):
        return f"x % {self.divisor} == {self.remainder}"

    def c(self):
        return f"finder_x % UINT32_C({self.divisor}) == UINT32_C({self.remainder})"

    def evaluate(self, sample):
        return sample["x"] % self.divisor == self.remainder


class PrimeAtom(Atom):
    numeric_fields = ("x",)

    @classmethod
    def parse(cls, text):
        if isinstance(text, str):
            match = re.fullmatch(r"\s*x\s*%\s*([0-9]+)\s*==\s*([0-9]+)\s*", text)
            if match:
                return ModuloAtom(*map(int, match.groups()))
        if isinstance(text, str) and text.strip() == "valid":
            raise ValueError("stateless prime model has no valid field")
        return super().parse(text)


def make_harness(model, variant, domain, kind, condition="true", expected=None):
    if variant not in VARIANTS or kind not in ("feasible", "equal", "different", "expected"):
        raise ValueError("unsupported stateless obligation")
    lo, hi = domain
    body = f"""uint32_t finder_x = nondet_u32();
__ESBMC_assume(finder_x >= UINT32_C({lo}) && finder_x <= UINT32_C({hi}));
__ESBMC_assume({condition});
"""
    if kind == "feasible":
        body += f'__ESBMC_assert(false, "{PROPERTIES[kind]}");'
    elif kind == "expected":
        if expected is None:
            raise ValueError("expected expression required")
        body += f'__ESBMC_assert({expected}, "{PROPERTIES[kind]}");'
    else:
        relation = "==" if kind == "equal" else "!="
        body += f"""bool r_original = original(finder_x);
bool r_candidate = {VARIANTS[variant]}(finder_x);
__ESBMC_assert(r_original {relation} r_candidate, "{PROPERTIES[kind]}");"""
    return model + "\nextern uint32_t nondet_u32(void);\nextern void __ESBMC_assume(bool);\n" + \
        "extern void __ESBMC_assert(bool, const char *);\nvoid finder_entry(void)\n{\n" + body + "\n}\n"


class PrimeBackend(CacheBackend):
    # Reuse process, replay, query and region classification infrastructure.
    # No cache model, initialization or invariant is instantiated here.
    fields = ("x",)
    numeric_fields = ("x",)
    atom_type = PrimeAtom
    variants = VARIANTS
    probe_filename = "prime_probe.c"

    @staticmethod
    def initial_atoms():
        # Type boundaries and the declared table bound, not the answer formula.
        return [PrimeAtom.parse(text) for text in ("x == 0", "x == 1", "x <= 31")]

    def __init__(self, args, workdir):
        self.args, self.workdir = args, Path(workdir)
        self.domain = args.domain
        self.unwind = math.isqrt(self.domain[1]) + 2
        self.deadline = time.monotonic() + args.max_seconds
        self.samples, self.queries, self.replays, self.seen = [], [], [], set()
        self.inputs = self.workdir / "inputs"
        self.inputs.mkdir()
        self.model_bytes = (CASE / "prime_model.h").read_bytes()
        self.model = self.model_bytes.decode("utf-8")
        self.probe_bytes = (CASE / self.probe_filename).read_bytes()
        (self.inputs / "prime_model.h").write_bytes(self.model_bytes)
        (self.inputs / self.probe_filename).write_bytes(self.probe_bytes)
        template_bytes = Path(__file__).read_bytes()
        (self.inputs / "find_prime_conditions.py").write_bytes(template_bytes)
        self.sketch_manifest = {
            "template": "stateless-bounded-return-v1", "template_sha256": hashlib.sha256(template_bytes).hexdigest(),
            "domain": list(self.domain), "state_obligations": "not applicable: no mutable state",
            "observations": "boolean return value", "reuse": "search, oracle, replay and final condition checks",
            "trusted_manual_inputs": ["C model", "domain", "loop bound", "predicate vocabulary"]}
        self.sketch_manifest["vocabulary"] = args.vocabulary
        self.sketch_manifest["initial_predicates"] = [atom.text() for atom in self.initial_atoms()]
        self.sketch_manifest["initial_seeds"] = self.default_seeds("stateless")
        save_json(self.workdir / "sketch-manifest.json", self.sketch_manifest)
        self.scope = {
            "language": "C", "research_scope": "same-language equivalence; C is the current backend",
            "inputs": "x:uint32_t", "domain": list(self.domain), "observations": "boolean return value",
            "initial_state": "none", "assumptions": "fixed read-only tables; no external state",
            "bound": f"one call; unwind={self.unwind}; unwinding and safety checks enabled",
            "completeness": "EXACT only within the declared finite input domain",
            "model_sha256": hashlib.sha256(self.model_bytes).hexdigest(),
            "probe_sha256": hashlib.sha256(self.probe_bytes).hexdigest(),
            "trace_schema": "r_cached is the legacy field name for the candidate result; no cache is involved"}
        self.scope["vocabulary"] = args.vocabulary
        self.esbmc, self.version = shutil.which(args.esbmc), None
        self.executable = self.inputs / ("prime-probe.exe" if sys.platform == "win32" else "prime-probe")

    def state_obligations(self):
        return {}

    def present_condition(self, found):
        return compact_condition(found, self.domain)

    def seed_in_domain(self, row, state_mode):
        return self.domain[0] <= row["x"] <= self.domain[1]

    def default_seeds(self, state_mode):
        lo, hi = self.domain
        return [dict(x=x) for x in sorted({lo, hi, 0, 1, 2, 3, 7, 8, 15, 16, 30, 31, 32, 33}) if lo <= x <= hi]

    def validate_trace(self, row):
        if any(type(row.get(field)) is not int or row[field] not in (0, 1) for field in ("r_original", "r_cached")):
            raise RuntimeError("prime probe must return two booleans")

    def make_harness(self, model, variant, state_mode, kind, condition="true", expected=None):
        return make_harness(model, variant, self.domain, kind, condition, expected)


class ModuloPrimeBackend(PrimeBackend):
    @staticmethod
    def initial_atoms():
        # All small divisors, including composite ones. No sieve or expected set.
        return PrimeBackend.initial_atoms() + [ModuloAtom(divisor, 0) for divisor in MODULI]


def compact_condition(found, domain):
    """Re-express certified EQ cubes over the declared small integer domain.

    Evaluates predicates, never original/candidate code or sample labels. Unknown
    regions are not promoted to EQ. The caller still certifies the final output.
    """
    lo, hi = domain
    if not 0 <= lo <= hi <= 255:
        raise ValueError("compact presentation requires an explicit domain within 0..255")
    atoms = [PrimeAtom.parse(text) for text in found["predicates"]]
    included = [x for x in range(lo, hi+1) if any(matches(cube, atoms, {"x": x}) for cube in found["eq_cubes"])]
    excluded = sorted(set(range(lo, hi+1)) - set(included))

    def points(values, equal, c):
        if not values:
            return "false" if equal else "true"
        var = "finder_x" if c else "x"
        terms = [f"({var} {'==' if equal else '!='} " + (f"UINT32_C({x})" if c else str(x)) + ")" for x in values]
        return (" || " if equal else " && ").join(terms)

    options = []
    # Keep the original when it is shorter; choose the same representation for
    # human-readable and C output. All forms are equivalent only inside domain.
    options.append((found["condition"], found["condition_c"]))
    options.extend((points(values, equal, False), points(values, equal, True))
                   for values, equal in ((included, True), (excluded, False)))
    condition, condition_c = min(options, key=lambda pair: len(pair[0]))
    return {"condition": condition, "condition_c": condition_c,
            "basis": "certified EQ union re-expressed exactly within declared finite domain; no sample labels used"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, default="truncated")
    parser.add_argument("--vocabulary", choices=("baseline", "modulo"), default="baseline")
    parser.add_argument("--domain", default="0:63", help="inclusive uint32 interval within 0..255 for this first stage")
    parser.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-seconds", type=float, default=600)
    parser.add_argument("--max-queries", type=int, default=512)
    parser.add_argument("--max-predicates", type=int, default=96)
    parser.add_argument("--hypotheses")
    parser.add_argument("--workdir", default=".verify-equiv-runs/prime-finder")
    args = parser.parse_args(argv)
    try:
        lo, hi = map(int, args.domain.split(":"))
        if not 0 <= lo <= hi <= 255:
            raise ValueError()
    except ValueError:
        parser.error("domain must be LO:HI with 0 <= LO <= HI <= 255")
    args.domain, args.state_mode = (lo, hi), "stateless"
    if not all(math.isfinite(n) and n > 0 for n in (args.timeout, args.max_seconds)) or args.max_queries < 4 or not 3 <= args.max_predicates <= 256:
        parser.error("positive time budgets, >=4 queries and 3..256 predicates required")
    if args.vocabulary == "modulo" and args.max_predicates < 3 + len(MODULI):
        parser.error("modulo vocabulary requires at least 18 predicate slots")
    return args


def run(args):
    return shared_run(args, ModuloPrimeBackend if args.vocabulary == "modulo" else PrimeBackend)


if __name__ == "__main__":
    sys.exit(0 if run(parse_args())["status"] == "EXACT" else 2)
