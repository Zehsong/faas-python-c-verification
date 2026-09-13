"""Oracle regression tests; simulated solver output is not a proof result."""
import contextlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import verify_equiv as oracle
import verify_c_harness as adapter

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases" / "same_language_cache"


def violation(marker):
    return f"Violated property:\n  file cache_demo.c line 47 function check_call\n  {marker}\n  r_original == r_cached\n\nVERIFICATION FAILED\n"


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def classify(self, text):
        log = self.work / "verify.log"
        log.write_text(text)
        return oracle.classify_verification(log)

    def test_target_counterexample(self):
        self.assertEqual(self.classify(violation(oracle.RELATIONAL_PROPERTY)), "NEQ")

    def test_echoed_marker_does_not_turn_safety_failure_into_neq(self):
        text = oracle.RELATIONAL_PROPERTY + "\n" + violation("arithmetic overflow")
        self.assertEqual(self.classify(text), "UNKNOWN_PROPERTY_FAILURE")

    def test_nearby_marker_in_results_is_not_a_violated_property(self):
        text = violation("unwinding assertion loop") + "NOT CHECKED " + oracle.RELATIONAL_PROPERTY
        self.assertEqual(self.classify(text), "UNKNOWN_PROPERTY_FAILURE")

    def test_multiple_properties_with_safety_failure_are_unknown(self):
        text = violation(oracle.RELATIONAL_PROPERTY).replace("VERIFICATION FAILED\n", "")
        self.assertEqual(self.classify(text + violation("dereference failure")), "UNKNOWN_PROPERTY_FAILURE")

    def test_timeout_and_conflicting_statuses_are_unknown(self):
        for text in ["VERIFICATION SUCCESSFUL\nVERIFY_EQUIV_INTERNAL: timeout after 1s\n",
                     "VERIFICATION SUCCESSFUL\nVERIFICATION FAILED\n",
                     "parser error", "echo VERIFICATION SUCCESSFUL\n"]:
            with self.subTest(text=text):
                self.assertEqual(self.classify(text), "UNKNOWN")

    def test_success(self):
        self.assertEqual(self.classify("VERIFICATION SUCCESSFUL\n"), "EQ")

    def test_process_start_failure(self):
        log = self.work / "process.log"
        self.assertEqual(oracle.run([str(self.work / "missing-executable")], log, 1), (127, False))
        self.assertEqual(oracle.classify_verification(log), "UNKNOWN")

    def test_domains_precede_both_targets_and_preserve_module_entry(self):
        harness = oracle.build_harness([("x", "int"), ("flag", "bool")], "bool", [("x", -2, 7)])
        self.assertIn("__ESBMC_PY_MODULE_ENTRY();", harness)
        self.assertLess(harness.index("__ESBMC_assume(x >= -2)"), harness.index("long r_py ="))
        self.assertLess(harness.index("__ESBMC_assume(x <= 7)"), harness.index("long r_c ="))
        self.assertIn(oracle.RELATIONAL_PROPERTY, harness)

    def run_adapter(self, responses):
        argv = ["--c-harness", str(CASE / "cache_demo.c"), "--entry", "good_sequence",
                "--scope-file", str(CASE / "scopes.json"), "--esbmc", sys.executable,
                "--workdir", str(self.work)]
        iterator = iter(responses)

        def fake_run(cmd, log, timeout):
            rc, timed_out, text = next(iterator)
            Path(log).write_text(text)
            return rc, timed_out

        with patch.object(oracle, "run", side_effect=fake_run), contextlib.redirect_stdout(io.StringIO()):
            code = adapter.main(argv, oracle)
        return code, json.loads((self.work / "result.json").read_text())

    def test_c_adapter_requires_reachable_observation(self):
        code, report = self.run_adapter([(0, False, "test double\n"),
                                         (0, False, "VERIFICATION SUCCESSFUL\n")])
        self.assertEqual(code, 2)
        self.assertEqual(report["verdict"], "UNKNOWN")

    def test_c_adapter_missing_solver_discards_stale_logs(self):
        for filename in ("verify.log", "reachability.log", "version.log"):
            (self.work / filename).write_text("VERIFICATION SUCCESSFUL\n")
        argv = ["--c-harness", str(CASE / "cache_demo.c"), "--entry", "good_sequence",
                "--scope-file", str(CASE / "scopes.json"), "--esbmc", str(self.work / "missing-esbmc"),
                "--workdir", str(self.work)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(adapter.main(argv, oracle), 2)
        self.assertFalse((self.work / "verify.log").exists())
        report = json.loads((self.work / "result.json").read_text())
        self.assertEqual(report["verdict"], "UNKNOWN")
        self.assertIn("not found", report["reason"])

    def test_c_adapter_success_keeps_scope_and_provenance(self):
        code, report = self.run_adapter([(0, False, "test double\n"),
            (1, False, violation(adapter.REACHABILITY_PROPERTY)),
            (0, False, "VERIFICATION SUCCESSFUL\n")])
        self.assertEqual(code, 0)
        self.assertEqual(report["scope"]["bound"], "exactly three symbolic calls, no loops")
        self.assertFalse(report["automatic_condition_discovery"])
        self.assertEqual(len(report["source_sha256"]), 64)

    def test_saved_source_can_be_reused_in_its_output_directory(self):
        snapshot = self.work / "harness-source.c"
        original = (CASE / "cache_demo.c").read_bytes()
        snapshot.write_bytes(original)
        argv = ["--c-harness", str(snapshot), "--entry", "good_sequence",
                "--scope-file", str(CASE / "scopes.json"), "--esbmc", str(self.work / "missing-esbmc"),
                "--workdir", str(self.work)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(adapter.main(argv, oracle), 2)
        self.assertEqual(snapshot.read_bytes(), original)
        report = json.loads((self.work / "result.json").read_text())
        self.assertIn("ESBMC executable not found", report["reason"])

    def test_c_adapter_timeout_error_rc_and_safety_failure(self):
        for response in [(124, True, "VERIFICATION SUCCESSFUL\n"),
                         (9, False, "VERIFICATION SUCCESSFUL\n"),
                         (1, False, violation("cache invariant preserved"))]:
            with self.subTest(response=response):
                code, report = self.run_adapter([(0, False, "test double\n"),
                    (1, False, violation(adapter.REACHABILITY_PROPERTY)), response])
                self.assertEqual((code, report["verdict"]), (2, "UNKNOWN"))

    def test_c_adapter_target_neq_and_trace(self):
        code, report = self.run_adapter([(0, False, "test double\n"),
            (1, False, violation(adapter.REACHABILITY_PROPERTY)),
            (1, False, "x = 1\nr_original = 2\nr_cached = 0\n" + violation(oracle.RELATIONAL_PROPERTY))])
        self.assertEqual((code, report["verdict"]), (1, "NEQ"))
        self.assertEqual(report["counterexample_trace"], ["x = 1", "r_original = 2", "r_cached = 0"])

    def test_legacy_cli_scope_reports_actual_domain(self):
        argv = ["verify-equiv", "--python", str(self.work / "p.py"), "--py-function", "f",
                "--c", str(self.work / "c.c"), "--c-function", "f", "--param", "x:int",
                "--return", "int", "--domain", "x:0:1", "--esbmc", sys.executable,
                "--workdir", str(self.work)]
        (self.work / "p.py").write_text("def f(x):\n    return x\n")
        (self.work / "c.c").write_text("int f(int x) { return x; }\n")
        # Test the report path only; do not pretend the mocked oracle proves C/Python.
        output = io.StringIO()
        with patch.object(sys, "argv", argv), \
             patch.object(oracle.subprocess, "check_output", return_value="--equiv-py-target --equiv-c-target"), \
             patch.object(oracle, "export_goto", return_value=(True, "test double")), \
             patch.object(oracle, "relational_preflight", return_value=(True, "test double")), \
             patch.object(oracle, "run", return_value=(0, False)), \
             patch.object(oracle, "classify_verification", return_value="EQ"), \
             contextlib.redirect_stdout(output):
            code = oracle.main()
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("x: shared int32 domain [0, 1]", output.getvalue())
        self.assertNotIn("[-2147483648, 2147483647]", output.getvalue())


@unittest.skipUnless(os.environ.get("CACHE_REPLAY"), "set CACHE_REPLAY to a compiled native replay executable")
class NativeReplayTests(unittest.TestCase):
    def replay(self, bug, values):
        return subprocess.run([os.environ["CACHE_REPLAY"], str(bug)] + [str(x) for x in values],
                              capture_output=True, text=True)

    def test_correct_cache_repeated_and_boundary_inputs(self):
        rng = random.Random(20260913)
        values = [0, 0, 1, 1, 4294967295, 4294967295, 7, 7, 8]
        values += [rng.randrange(2**32) for _ in range(100)]
        proc = self.replay(0, values)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(len(proc.stdout.splitlines()), len(values))

    def test_bad_empty_miss_witness(self):
        proc = self.replay(1, [1])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("x=1 hit=0 original=2 cached=0 invariant=1", proc.stdout)

    def test_bad_miss_hit_miss_preserves_state(self):
        proc = self.replay(1, [7, 7, 8])
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.splitlines(), [
            "x=7 hit=0 original=8 cached=0 invariant=1",
            "x=7 hit=1 original=8 cached=8 invariant=1",
            "x=8 hit=0 original=9 cached=0 invariant=1"])

    def test_unsigned_wraparound_exception(self):
        proc = self.replay(1, [4294967295, 4294967295])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("hit=0 original=0 cached=0", proc.stdout)

    def test_invalid_replay_input(self):
        for values in [[4294967296], [-1], ["nonsense"]]:
            with self.subTest(values=values):
                self.assertEqual(self.replay(0, values).returncode, 2)


if __name__ == "__main__":
    unittest.main()
