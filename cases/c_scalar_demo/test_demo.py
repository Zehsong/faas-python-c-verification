"""Demo assembly controls; synthetic evidence is not a formal solver run."""
import copy
import tempfile
from pathlib import Path
import unittest

import run_demo as demo
from c_scalar_contract import Contract


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.summary = {"scope": {"inputs": {"x": {"type": "uint32_t", "min": 0, "max": 31}}},
                        "obligations": {"state": {"safety": {"status": "PROVED"}}}}
        self.query = {"kind": "equal", "status": "REFUTED", "witness": {"x": 2},
                      "native_replay": {"x": 2, "r_original": 3, "r_cached": 4}}

    def test_only_replayed_equality_counterexample_is_selected(self):
        queries = [{**self.query, "kind": "feasible"}, self.query]
        result = demo.replayed_counterexample(self.summary, queries)
        self.assertEqual(result["query_directory"], "query-001-equal")
        self.assertEqual((result["inputs"], result["original_return"], result["candidate_return"]), ({"x": 2}, 3, 4))

    def test_missing_or_inconsistent_replay_cannot_be_presented(self):
        changes = [dict(status="UNKNOWN"), dict(kind="different"), dict(witness=None),
                   dict(native_replay="unavailable"), dict(witness={"x": 1}),
                   dict(native_replay={"x": 32, "r_original": 3, "r_cached": 4}, witness={"x": 32}),
                   dict(native_replay={"x": 2, "r_original": 4, "r_cached": 4}),
                   dict(native_replay={"x": 2, "r_original": 3})]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNone(demo.replayed_counterexample(self.summary, [{**self.query, **change}]))

    def test_safety_failure_invalidates_demo_replay(self):
        for status in ("UNKNOWN", "REFUTED", "INVALIDATED", "NOT_CHECKED"):
            summary = copy.deepcopy(self.summary)
            summary["obligations"]["state"]["safety"]["status"] = status
            self.assertIsNone(demo.replayed_counterexample(summary, [self.query]))

    def test_copied_pairs_remain_admissible_and_portable(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, fixture, *_ in demo.CASES:
                source = demo.ROOT / "cases" / fixture
                before = Contract(source)
                path = demo.snapshot_pair(source, Path(folder) / name)
                after = Contract(path)
                self.assertEqual(before.data["inputs"], after.data["inputs"])
                for side in ("original", "candidate"):
                    self.assertEqual(before.sources[side].data, after.sources[side].data)
                    self.assertEqual(after.data[side]["source"], f"{side}.c")
                with self.assertRaises(FileExistsError):
                    demo.snapshot_pair(source, path.parent)

    def test_failed_assembly_has_no_success_or_fabricated_condition(self):
        text = demo.render_overview([{"name": "conditional", "passed": False, "error": "missing report"}], None)
        self.assertIn("DEMO_ERROR", text)
        self.assertIn("missing report", text)
        self.assertIn("No suitable solver counterexample", text)
        self.assertNotIn("Certified condition:", text)

    def test_overview_keeps_actual_condition_and_relative_evidence_links(self):
        summary = {**self.summary, "status": "PARTIAL", "diagnostics": [],
                   "claim": {"meaning": "SUFFICIENT_REGION", "condition": "x == 17"}}
        witness = {**demo.replayed_counterexample(self.summary, [self.query]), "artifact_directory": "pair-test"}
        text = demo.render_overview([{"name": "conditional", "passed": False, "summary": summary}], witness)
        self.assertIn("```text\nx == 17\n```", text)
        self.assertIn("conditional/pair-test/query-000-equal/verify.log", text)
        self.assertIn("PARTIAL | SUFFICIENT_REGION | no", text)
        self.assertIn("Original returns 3; candidate returns 4.", text)


if __name__ == "__main__":
    unittest.main()
