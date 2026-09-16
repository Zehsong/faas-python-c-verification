"""Finite-domain and mocked-backend tests; these are not uint32_t proofs."""
import contextlib
import io
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from predicate_search import (Atom, UINT32_MAX, choose_split, cube_expression,
                              initial_atoms, matches, search, simplify_cubes, union_expression)
from find_cache_conditions import (CASE, CacheBackend, default_seeds, make_harness,
                                  parse_args, run, validate_seed, witness_from_log)


class FiniteOracle:
    """Exhaustive only over explicitly supplied finite rows, not all C states."""
    def __init__(self, rows, hints=None):
        self.rows = rows
        self.samples = list(rows if hints is None else hints)

    def classify(self, cube, atoms):
        rows = [row for row in self.rows if matches(cube, atoms, row)]
        if not rows:
            return {"status": "EMPTY"}
        labels = {row["r_original"] == row["r_cached"] for row in rows}
        for row in rows:
            if row not in self.samples:
                self.samples.append(row)
        status = "MIXED" if len(labels) == 2 else "EQ" if True in labels else "ALL_NEQ"
        return {"status": status, "proof_scope": "test fixture finite rows only"}


class PredicateTests(unittest.TestCase):
    def test_safe_predicate_grammar(self):
        for text in ["x == UINT32_MAX", "x <= 7", "value != key", "valid"]:
            self.assertIsInstance(Atom.parse(text), Atom)
        for text in ["r_original == r_cached", "original(x) == 0", "x = 1", "x == 4294967296",
                     "x == -1", "valid || true", "x == 1; abort()", "__import__('os')", 42]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                Atom.parse(text)

    def test_uint32_boundary_and_state_predicates(self):
        row = {"x": UINT32_MAX, "key": UINT32_MAX, "value": 0, "valid": 1}
        self.assertTrue(Atom.parse("x == key").evaluate(row))
        self.assertTrue(Atom.parse("x == UINT32_MAX").evaluate(row))
        self.assertIn("UINT32_C(4294967295)", Atom.parse("x == UINT32_MAX").c())

    def test_simplification_preserves_truth_table(self):
        # A or (!A and B and C) becomes A or (B and C).
        cubes = [((0, True),), ((0, False), (1, True), (2, True))]
        simplified = simplify_cubes(cubes)
        self.assertIn(((1, True), (2, True)), simplified)
        for values in itertools.product((False, True), repeat=3):
            evaluate = lambda terms: any(all(values[i] == v for i, v in term) for term in terms)
            self.assertEqual(evaluate(cubes), evaluate(simplified))

    def test_simplification_random_covers(self):
        rng = random.Random(26)
        valuations = list(itertools.product((False, True), repeat=4))
        for _ in range(25):
            cubes = [tuple(enumerate(v)) for v in valuations if rng.randrange(2)]
            simplified = simplify_cubes(cubes)
            for values in valuations:
                self.assertEqual(any(all(values[i] == v for i, v in term) for term in cubes),
                                 any(all(values[i] == v for i, v in term) for term in simplified))

    def test_mixed_region_is_refined_not_marked_all_neq(self):
        atoms = [Atom.parse("x == 1")]
        rows = [{"x": x, "key": 0, "value": 0, "valid": 0,
                 "r_original": 1, "r_cached": int(x == 1)} for x in (0, 1)]
        result = search(FiniteOracle(rows), atoms, max_predicates=1)
        self.assertEqual(result["condition"], "((x == 1))")
        self.assertEqual(len(result["buckets"]["ALL_NEQ"]), 1)

    def test_exhausted_vocabulary_keeps_mixed_unknown(self):
        atoms = [Atom.parse("valid")]
        rows = [{"x": x, "key": 0, "value": 0, "valid": 0,
                 "r_original": x, "r_cached": 0} for x in (0, 1)]
        result = search(FiniteOracle(rows), atoms, max_predicates=1)
        self.assertTrue(result["buckets"]["UNKNOWN"])
        self.assertFalse(result["buckets"]["ALL_NEQ"])

    def test_misleading_positive_hints_cannot_certify_a_region(self):
        rows = [{"x": x, "key": 0, "value": 0, "valid": 0,
                 "r_original": x, "r_cached": 0} for x in (0, 1)]
        result = search(FiniteOracle(rows, hints=rows[:1]), [Atom.parse("x == 0")], 1)
        self.assertNotEqual(result["condition"], "true")

    def test_counterexample_can_add_a_non_boundary_constant(self):
        rows = [{"x": x, "valid": 0, "key": 0, "value": 0,
                 "r_original": 1, "r_cached": int(x == 42)} for x in (0, 7, 42)]
        atoms = initial_atoms()
        self.assertNotIn(Atom.parse("x == 42"), atoms)
        result = search(FiniteOracle(rows, hints=rows[:1]), atoms)
        self.assertIn(Atom.parse("x == 42"), atoms)
        self.assertFalse(result["buckets"]["UNKNOWN"])
        for row in rows:
            self.assertEqual(any(matches(cube, atoms, row) for cube in result["eq_cubes"]), row["x"] == 42)

    def test_unknown_never_becomes_eq(self):
        class UnknownOracle:
            samples = [{"x": 1, "valid": 0, "key": 0, "value": 0, "r_original": 2, "r_cached": 2}]
            def classify(self, cube, atoms):
                return {"status": "UNKNOWN"}
        result = search(UnknownOracle(), initial_atoms())
        self.assertEqual(result["condition"], "false")
        self.assertEqual(result["buckets"]["UNKNOWN"], [()])

    def test_negative_assertion_needs_its_own_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CacheBackend(parse_args([]), tmp)
            with patch.object(backend, "query", side_effect=[{"status": "REFUTED"},
                              {"status": "REFUTED"}, {"status": "UNKNOWN"}]):
                self.assertEqual(backend.classify((), initial_atoms())["status"], "UNKNOWN")

    def test_replayed_witness_must_reach_target_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = CacheBackend(parse_args([]), tmp)
            with patch.object(backend, "query", return_value={"status": "REFUTED", "native_replay": {
                    "x": 0, "valid": 0, "key": 0, "value": 0}}):
                result = backend.classify(((0, True),), [Atom.parse("x == 1")])
                self.assertEqual(result["status"], "UNKNOWN")

    def test_query_and_wall_clock_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = parse_args(["--max-queries", "4"])
            backend = CacheBackend(args, tmp)
            backend.esbmc = "must-not-be-executed"
            backend.queries = [{}, {}]
            self.assertEqual(backend.query("equal", reserve=2)["status"], "UNKNOWN")
            backend.queries = []
            backend.deadline = 0
            self.assertEqual(backend.query("equal")["status"], "UNKNOWN")

    def test_seed_validation(self):
        for row in [{"x": -1, "valid": 0, "key": 0, "value": 0},
                    {"x": 1, "valid": 2, "key": 0, "value": 0},
                    {"x": 1, "valid": 0, "key": 0, "value": 0, "label": "EQ"}]:
            with self.assertRaises(ValueError):
                validate_seed(row)

    def test_witness_parser_uses_entry_variables_only(self):
        log = "x = 99\nfinder_x = 4294967295 (1111)\nfinder_valid = true\nfinder_key = 7\nfinder_value = 8\n"
        self.assertEqual(witness_from_log(log), {"x": UINT32_MAX, "valid": 1, "key": 7, "value": 8})
        self.assertIsNone(witness_from_log("finder_x = 1"))

    def test_harness_has_shared_input_separate_inequality_property_and_no_golden_condition(self):
        model = (CASE / "cache_model.h").read_text()
        text = make_harness(model, "bad_miss", "invariant", "different", "finder_x == UINT32_C(7)")
        self.assertIn("r_original != r_cached", text)
        self.assertIn("__FINDER_ALL_DIFFERENT__", text)
        self.assertIn("__ESBMC_assume(invariant(&cache))", text)
        self.assertNotIn("bad_conditional_step", text)
        self.assertNotIn("x == UINT32_MAX", text)
        self.assertLess(text.index("__ESBMC_assume(finder_x"), text.index("uint32_t r_original"))

    def test_proposed_verdict_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proposal.json"
            path.write_text('{"verdict":"EQ"}')
            with contextlib.redirect_stdout(io.StringIO()):
                result = run(parse_args(["--workdir", tmp, "--hypotheses", str(path)]))
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertIsNone(result["condition"])


@unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
class NativeSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.args = parse_args(["--cc", os.environ.get("FINDER_CC", "cc"), "--esbmc", "not-installed-test-esbmc"])
        cls.backend = CacheBackend(cls.args, cls.temp.name)
        cls.backend.prepare()
        # Native fixture tests only; this bypass is not a formal certificate.
        cls.backend.state_established = True

    def test_real_trace_guided_partitions_for_four_variants(self):
        numbers = (0, 1, 7, 8, UINT32_MAX)
        seeds = []
        for x, key in itertools.product(numbers, repeat=2):
            seeds.append(dict(x=x, valid=1, key=key, value=(key+1)&UINT32_MAX))
            for value in (0, 1, 3, UINT32_MAX):
                seeds.append(dict(x=x, valid=0, key=key, value=value))
        for variant in ("good", "bad_miss", "bad_hit", "bad_miss_two"):
            with self.subTest(variant=variant):
                self.backend.args.variant = variant
                rows = self.backend.replay(seeds, repeat=True)
                self.assertEqual({row["hit"] for row in rows}, {0, 1})
                atoms = initial_atoms()
                found = search(FiniteOracle(rows), atoms)
                self.assertFalse(found["buckets"]["UNKNOWN"])
                for row in rows:
                    predicted = any(matches(cube, atoms, row) for cube in found["eq_cubes"])
                    self.assertEqual(predicted, row["r_original"] == row["r_cached"])
                if variant == "good":
                    self.assertEqual(found["condition"], "true")

    def test_missing_esbmc_blocks_native_evidence(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            args = parse_args(["--cc", os.environ.get("FINDER_CC", "cc"), "--esbmc", "not-installed-test-esbmc", "--workdir", tmp])
            report = run(args)
            self.assertEqual(report["status"], "UNKNOWN")
            self.assertIsNone(report["condition"])
            self.assertEqual(report["traces_collected"], 0)
            self.assertFalse(report["exact"])

    def test_instrumentation_preserves_native_outputs_and_state(self):
        command = json.loads((self.backend.inputs / "compile-command.json").read_text())
        plain = self.backend.inputs / ("plain-probe.exe" if os.name == "nt" else "plain-probe")
        if Path(command[0]).stem.lower() == "cl":
            command = [part if not part.startswith("/Fe:") else "/Fe:" + str(plain) for part in command]
            command.insert(1, "/DPLAIN_PROBE")
        else:
            command[command.index("-o") + 1] = str(plain)
            command.insert(1, "-DPLAIN_PROBE")
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rows = default_seeds("invariant")
        data = "".join(f"{r['x']} {r['valid']} {r['key']} {r['value']}\n" for r in rows)
        for variant in ("good", "bad_miss", "bad_hit", "bad_miss_two"):
            self.backend.args.variant = variant
            traced = self.backend.replay(rows, repeat=True)
            proc = subprocess.run([str(plain), variant], input=data, capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0)
            plain_rows = [json.loads(line) for line in proc.stdout.splitlines()]
            for left, right in zip(traced, plain_rows):
                self.assertEqual({k:v for k,v in left.items() if k != "hit"},
                                 {k:v for k,v in right.items() if k != "hit"})

    def test_generated_solver_harnesses_compile_as_c(self):
        model = (CASE / "cache_model.h").read_text()
        pieces = [model]
        for variant in ("good", "bad_miss", "bad_hit", "bad_miss_two"):
            for kind in ("init", "preservation", "feasible", "equal", "different", "expected"):
                text = make_harness(model, variant, "invariant", kind,
                    "finder_x <= UINT32_C(7)", expected="finder_x == finder_key")
                pieces.append(text[len(model):].replace("finder_entry", f"{variant}_{kind}"))
        source = self.backend.inputs / "all_obligations.c"
        source.write_text("\n".join(pieces))
        compiler = json.loads((self.backend.inputs / "compile-command.json").read_text())[0]
        if Path(compiler).stem.lower() == "cl":
            command = [compiler, "/nologo", "/std:c11", "/c", str(source), "/Fo:" + str(self.backend.inputs / "formal.obj")]
        else:
            command = [compiler, "-std=c11", "-c", str(source), "-o", str(self.backend.inputs / "formal.o")]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
