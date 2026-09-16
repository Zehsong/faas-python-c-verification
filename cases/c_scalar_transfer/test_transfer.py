"""Transfer-fixture/native and experiment-accounting controls, not SMT proofs."""
import argparse
from contextlib import redirect_stdout
import io
import itertools
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from run_checks import (CASE, ROOT, assess, bind_contract, check_engine, diagnostics,
                        execute, ordered_hypotheses, parse_args, schedule)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cc = os.environ.get("FINDER_CC", "cc")

    def test_frozen_engine_and_contract_only_binding(self):
        lock = check_engine()
        self.assertEqual(lock["baseline_commit"], "61ba47b")
        for name in ("equivalent_31", "unequal_31", "reordered_7", "reordered_31"):
            bound = bind_contract(CASE / f"{name}.json")
            self.assertEqual(bound.fields, ("x", "low", "high"))
            self.assertEqual(bound.contract.data["original"]["entry"], "clamp")

    def test_engine_lock_rejects_edits_and_extra_modules(self):
        lock = check_engine()
        for name in lock["files"]:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        check_engine(self.root)
        path = self.root / "tools/find-cond-equiv/condition_runner.py"
        original = path.read_text(encoding="utf-8")
        path.write_bytes(original.replace("\n", "\r\n").encode("utf-8"))
        check_engine(self.root)  # platform line endings do not change the lock
        path.write_text(original + "\n# semantic-review-required edit\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "condition_runner"):
            check_engine(self.root)
        path.write_text(original, encoding="utf-8")
        (path.parent / "additional_engine.py").write_text("# new module\n")
        with self.assertRaisesRegex(ValueError, "additional_engine"):
            check_engine(self.root)

    def test_ordered_vocabulary_uses_names_only(self):
        proposal = ordered_hypotheses(("a", "b", "c"))
        self.assertEqual(set(proposal["predicates"]), {f"{a} <= {b}" for a, b in itertools.permutations("abc", 2)})
        self.assertEqual(proposal["seeds"], [])
        bound = bind_contract(CASE / "reordered_31.json")
        self.assertEqual(len(ordered_hypotheses(bound.fields)["predicates"]), 6)
        for text in ordered_hypotheses(bound.fields)["predicates"]:
            bound.atom_type.parse(text)

    def test_paired_schedule_alternates_and_counts_required_runs(self):
        rows = list(schedule(2))
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(row[3] for row in rows), 8)
        for name in ("reordered_7", "reordered_31"):
            first = [method for repeat, case, method, _ in rows if repeat == 1 and case == name]
            second = [method for repeat, case, method, _ in rows if repeat == 2 and case == name]
            self.assertEqual(first, list(reversed(second)))

    def test_claim_assessment_requires_certificates_and_safety(self):
        report = dict(status="EXACT", exact=True, state_obligations={"safety": {"status": "PROVED"}},
                      final_validation={name: {"status": "PROVED"} for name in ("sufficiency", "complement")})
        self.assertEqual(assess(report, {"status": "PROVED"}, True), (True, True))
        self.assertEqual(assess(report, {"status": "UNKNOWN"}, True), (False, False))
        report["final_validation"]["complement"]["status"] = "UNKNOWN"
        self.assertEqual(assess(report, {"status": "PROVED"}, True), (False, False))
        report.update(status="PARTIAL", exact=False)
        self.assertEqual(assess(report, {"status": "PROVED"}, False), (True, True))
        self.assertEqual(assess(report, {"status": "PROVED"}, True), (True, False))
        report.update(status="UNKNOWN", reason="budget exhausted")
        self.assertEqual(assess(report, None, False), (True, True))
        report["state_obligations"]["safety"]["status"] = "UNKNOWN"
        self.assertEqual(assess(report, None, False), (False, False))

    def test_unresolved_reason_kept(self):
        report = dict(status="PARTIAL", search={"history": [
            dict(status="UNKNOWN", evidence={"reason": "query or wall-clock budget exhausted"}),
            dict(status="MIXED", reason="mixed region exceeds predicate vocabulary")]})
        self.assertEqual(diagnostics(report), ["query or wall-clock budget exhausted", "mixed region exceeds predicate vocabulary"])

    def test_predicate_formula_on_larger_finite_domain(self):
        # Arithmetic check of the acceptance expectation, not a backend proof.
        for x, low, high in itertools.product(range(32), repeat=3):
            left = low if x < low else high if x > high else x
            right = high if x > high else low if x < low else x
            self.assertEqual(left == right, low <= high or x <= high or x >= low)

    def test_native_fixtures_on_all_small_domain_inputs(self):
        rows = [dict(zip(("x", "low", "high"), values)) for values in itertools.product(range(8), repeat=3)]
        for name in ("equivalent_31", "unequal_31", "reordered_7"):
            with self.subTest(case=name):
                bound = bind_contract(CASE / f"{name}.json")
                settings = parse_args(["--contract", str(bound.contract.path), "--cc", self.cc,
                                       "--esbmc", "missing-transfer-test-solver"])
                directory = self.root / name
                directory.mkdir()
                backend = bound(settings, directory)
                backend.prepare()
                # Test-only gate bypass for these inspected loop-free fixtures.
                backend.restore_obligations({"safety": {"status": "PROVED"}})
                traces = backend.replay(rows)
                self.assertEqual(len(traces), 512)
                for row in traces:
                    x, low, high = (row[n] for n in bound.fields)
                    reference = low if x < low else high if x > high else x
                    self.assertEqual(row["r_original"], reference)
                    if name == "equivalent_31":
                        self.assertEqual(row["r_cached"], reference)
                    elif name == "unequal_31":
                        self.assertEqual(row["r_cached"], reference + 1)
                    else:
                        self.assertEqual(row["r_cached"], high if x > high else low if x < low else x)
                        self.assertEqual(row["r_original"] == row["r_cached"], low <= high or x <= high or x >= low)

    def test_missing_solver_does_not_pass_experiment(self):
        args = argparse.Namespace(workdir=str(self.root), esbmc="intentionally-missing-transfer-solver",
                                  cc=self.cc, repeats=1, timeout=5, max_seconds=30, max_queries=12)
        output = io.StringIO()
        with redirect_stdout(output):
            summary = execute(args)
        self.assertIn("C TRANSFER ACCEPTANCE: 0/4 required runs passed", output.getvalue())
        self.assertFalse(summary["passed"])
        self.assertEqual((summary["required_passed"], summary["required_total"]), (0, 4))
        self.assertEqual(summary["discovery_exact"], 0)
        self.assertEqual(len(summary["results"]), 6)
        self.assertIn("pycparser_version", summary["environment"])
        for row in summary["results"]:
            self.assertEqual(row["status"], "UNKNOWN")
            self.assertEqual(row["report"]["traces_collected"], 0)
            self.assertFalse(row["integrity"])
            self.assertEqual(row["validation_queries"], 0)
        saved = json.loads((self.root / "results.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, summary)
        self.assertTrue((Path(summary["artifacts"]) / "metrics.csv").is_file())


if __name__ == "__main__":
    unittest.main()
