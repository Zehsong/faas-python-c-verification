"""Finite/native prime tests; ESBMC acceptance is a separate Linux run."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from find_cache_conditions import ROOT, witness_from_log
from find_prime_conditions import PrimeAtom, PrimeBackend, compact_condition, make_harness, parse_args, run
from predicate_search import matches, search
from test_predicate_search import FiniteOracle

spec = importlib.util.spec_from_file_location("prime_checks", ROOT / "cases/prime_lookup/run_checks.py")
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


class PrimeTests(unittest.TestCase):
    def test_compact_condition_preserves_certified_union(self):
        # The certified region is all points except 3 and 7. Labels are absent.
        atoms = [PrimeAtom.parse(f"x == {x}") for x in range(10)]
        cubes = [((x, True),) for x in range(10) if x not in (3, 7)]
        found = {"predicates": [a.text() for a in atoms], "eq_cubes": cubes,
                 "condition": "long original " * 30, "condition_c": "unused"}
        result = compact_condition(found, (0, 9))
        self.assertEqual(result["condition"], "(x != 3) && (x != 7)")
        self.assertEqual(result["condition_c"], "(finder_x != UINT32_C(3)) && (finder_x != UINT32_C(7))")

    def test_compact_condition_does_not_promote_unknown_points(self):
        found = {"predicates": ["x == 2"], "eq_cubes": [((0, True),)],
                 "condition": "((x == 2))", "condition_c": "((finder_x == UINT32_C(2)))"}
        self.assertEqual(compact_condition(found, (0, 7))["condition"], "(x == 2)")
        found["eq_cubes"] = []
        self.assertEqual(compact_condition(found, (0, 7))["condition"], "false")
        found["eq_cubes"] = [()]
        self.assertEqual(compact_condition(found, (0, 7))["condition"], "true")

    def test_stateless_predicates_and_witness(self):
        self.assertEqual(witness_from_log("finder_x = 37", ("x",)), {"x": 37})
        for text in ("valid", " valid ", "key == x", "original(x)"):
            with self.assertRaises(ValueError):
                PrimeAtom.parse(text)

    def test_domain_validation(self):
        for domain in ("-1:63", "0:256", "7:3", "foo", "0:1:2"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parse_args(["--domain", domain])

    def test_formal_template_has_domain_and_no_cache_assumptions(self):
        source = make_harness("", "truncated", (0, 63), "different")
        self.assertIn("finder_x <= UINT32_C(63)", source)
        self.assertIn("r_original != r_candidate", source)
        self.assertNotIn("invariant", source)
        self.assertNotIn("Cache", source)

    def test_stateless_backend_has_no_dummy_state_proofs(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = PrimeBackend(parse_args([]), tmp)
            with patch.object(backend, "query") as query:
                self.assertEqual(backend.state_obligations(), {})
                query.assert_not_called()


@unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
class NativePrimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.args = parse_args(["--cc", os.environ.get("FINDER_CC", "cc"), "--esbmc", "missing-test-esbmc", "--domain", "0:255"])
        cls.backend = PrimeBackend(cls.args, cls.temp.name)
        cls.backend.prepare()

    def test_native_algorithms_against_independent_sieve(self):
        flags = acceptance.sieve(255)
        for variant in ("fallback", "truncated", "mutant"):
            self.backend.args.variant = variant
            rows = self.backend.replay([{"x": x} for x in range(256)], repeat=True)
            for row in rows:
                x = row["x"]
                self.assertEqual(row["r_original"], int(flags[x]))
                expected = False if variant == "truncated" and x >= 32 else True if variant == "mutant" and x == 9 else flags[x]
                self.assertEqual(row["r_cached"], int(expected))

    def test_trace_guided_discovery_includes_out_of_table_composites(self):
        self.backend.args.variant = "truncated"
        rows = self.backend.replay([{"x": x} for x in range(64)], repeat=True)
        fixture = FiniteOracle(rows, hints=rows[:4])
        fixture.numeric_fields, fixture.atom_type = ("x",), PrimeAtom
        atoms = PrimeBackend.initial_atoms()
        found = search(fixture, atoms, 96)
        self.assertFalse(found["buckets"]["UNKNOWN"])
        for row in rows:
            self.assertEqual(any(matches(cube, atoms, row) for cube in found["eq_cubes"]), row["r_original"] == row["r_cached"])
        self.assertTrue(any(matches(cube, atoms, {"x": 49}) for cube in found["eq_cubes"]))
        self.assertFalse(any(matches(cube, atoms, {"x": 37}) for cube in found["eq_cubes"]))
        limited = search(fixture, PrimeBackend.initial_atoms(), 3)
        self.assertTrue(limited["buckets"]["UNKNOWN"])

    def test_all_generated_harnesses_compile(self):
        model = self.backend.model
        pieces = [model]
        for variant in ("fallback", "truncated", "mutant"):
            for kind in ("feasible", "equal", "different", "expected"):
                source = make_harness(model, variant, (0, 63), kind, expected="finder_x != 9")
                pieces.append(source[len(model):].replace("finder_entry", variant + "_" + kind))
        source = self.backend.inputs / "formal.c"
        source.write_text("\n".join(pieces))
        compiler = shutil.which(self.args.cc)
        target = str(self.backend.inputs / "formal.obj")
        command = ([compiler, "/nologo", "/std:c11", "/c", str(source), "/Fo:"+target]
                   if Path(compiler).stem.lower() == "cl" else
                   [compiler, "-std=c11", "-c", str(source), "-o", target])
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_missing_solver_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            report = run(parse_args(["--cc", self.args.cc, "--esbmc", "missing-test-esbmc", "--workdir", tmp]))
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIsNone(report["condition"])
        self.assertEqual(report["scope"]["domain"], [0, 63])
        self.assertEqual(report["state_obligations"], {})


if __name__ == "__main__":
    unittest.main()
