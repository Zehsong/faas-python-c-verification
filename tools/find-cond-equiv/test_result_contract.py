"""Proof-summary, artifact and failure controls; mocked certificates are not proofs."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from c_backend import oracle
from c_scalar_backend import bind_contract
from condition_runner import run
from find_c_conditions import main, parse_args
from result_contract import build_summary, diagnostic_code, validate_summary, write_summary

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas/verification-result-v1.schema.json").read_text(encoding="utf-8"))


def check_schema(value, node=SCHEMA):
    """Check the small set of JSON Schema keywords used by our artifact schema."""
    if "$ref" in node:
        target = SCHEMA
        for part in node["$ref"].split("/")[1:]:
            target = target[part]
        return check_schema(value, target)
    if "const" in node:
        assert value == node["const"]
    if "enum" in node:
        assert value in node["enum"]
    types = node.get("type", [])
    types = [types] if isinstance(types, str) else types
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
               "integer": type(value) is int, "number": type(value) in (int, float), "null": value is None}
    if types:
        assert any(matches[t] for t in types), (value, types)
    if value is not None and "minimum" in node:
        assert value >= node["minimum"]
    if isinstance(value, dict):
        assert set(node.get("required", [])) <= set(value)
        props = node.get("properties", {})
        for name, item in value.items():
            if name in props:
                check_schema(item, props[name])
            elif node.get("additionalProperties") is False:
                raise AssertionError("unexpected field: " + name)
            elif isinstance(node.get("additionalProperties"), dict):
                check_schema(item, node["additionalProperties"])
    if isinstance(value, list) and "items" in node:
        for item in value:
            check_schema(item, node["items"])


class ResultContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def base_report(self, condition="true"):
        return dict(status="EXACT", exact=True, condition=condition, condition_c=condition,
                    scope={"inputs": "test domain", "observations": "return"},
                    state_obligations={"safety": {"status": "PROVED"}},
                    final_validation={name: {"status": "PROVED"} for name in ("sufficiency", "complement")},
                    artifacts=str(self.root), queries_used=5)

    def test_exact_meanings_and_schema(self):
        for condition, meaning in (("true", "ALL_INPUTS"), ("false", "NO_INPUTS"), ("x == y", "REGION")):
            summary = build_summary(self.base_report(condition), samples=[{"x": 1}])
            self.assertEqual((summary["status"], summary["claim"]["meaning"]), ("EXACT", meaning))
            check_schema(validate_summary(summary))

    def test_missing_complement_does_not_become_exact(self):
        report = self.base_report("x == y")
        report["final_validation"]["complement"] = {"status": "UNKNOWN", "reason_code": "QUERY_BUDGET_EXHAUSTED"}
        summary = build_summary(report, samples=[{"x": 1}])
        self.assertEqual(summary["status"], "PARTIAL")
        self.assertIn("COMPLETENESS_NOT_ESTABLISHED", [d["code"] for d in summary["diagnostics"]])
        forged = copy.deepcopy(summary)
        forged["status"] = "EXACT"
        with self.assertRaises(ValueError):
            validate_summary(forged)

    def test_no_domain_witness_or_safety_means_no_claim(self):
        report = self.base_report()
        self.assertEqual(build_summary(report)["status"], "UNKNOWN")
        report["state_obligations"]["safety"]["status"] = "UNKNOWN"
        summary = build_summary(report, samples=[{"x": 1}])
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertIsNone(summary["claim"]["condition"])

    def test_false_partial_is_not_a_useful_region(self):
        report = self.base_report("false")
        report["status"] = "PARTIAL"
        self.assertEqual(build_summary(report, samples=[{"x": 1}])["status"], "UNKNOWN")

    def test_agent_best_certificate_separate_from_latest_rejection(self):
        report = dict(status="PARTIAL", artifacts=str(self.root), queries_used=4)
        state = dict(scope={"inputs": "test"}, phase="READY", state_obligations={},
                     domain_feasibility={"status": "REFUTED"},
                     best_result=dict(candidate="x == 0", candidate_c="finder_x == 0", checks={"sufficiency": {"status": "PROVED"}}),
                     latest_feedback={"status": "REJECTED", "reason": "incorrect round"})
        summary = build_summary(report, producer="agent", state=state)
        self.assertEqual(summary["status"], "PARTIAL")
        self.assertEqual(summary["latest_candidate"]["status"], "REJECTED")
        check_schema(summary)
        state["phase"] = "BLOCKED"
        stale = build_summary(report, producer="agent", state=state)
        self.assertEqual(stale["status"], "UNKNOWN")
        self.assertEqual(stale["obligations"]["sufficiency"]["status"], "INVALIDATED")

    def test_empty_and_unsupported_inputs_always_write_artifacts(self):
        for name, status, code in (("empty_domain", "EMPTY_DOMAIN", "EMPTY_DOMAIN"),
                                   ("unsupported", "UNKNOWN", "UNSUPPORTED_INPUT")):
            root = self.root / name
            with contextlib.redirect_stdout(io.StringIO()):
                rc = main(["--contract", str(ROOT / f"cases/result_contract/{name}.json"), "--workdir", str(root)])
            self.assertEqual(rc, 2)
            summary = json.loads((root / "verification-result.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], status)
            self.assertIn(code, [d["code"] for d in summary["diagnostics"]])
            self.assertIsNone(summary["claim"]["condition"])
            self.assertEqual(summary["metrics"]["queries"], 0)
            self.assertTrue((root / "report.md").is_file())
            check_schema(summary)

    def test_missing_file_has_io_reason_and_legacy_result(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--contract", str(self.root / "missing.json"), "--workdir", str(self.root)]), 2)
        old = json.loads((self.root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(old["status"], "UNKNOWN")
        self.assertEqual(old["reason_code"], "INPUT_IO_ERROR")

    def backend(self):
        bound = bind_contract(ROOT / "cases/c_scalar/max_min.json")
        args = parse_args(["--contract", str(bound.contract.path), "--workdir", str(self.root), "--esbmc", sys.executable])
        work = self.root / "backend"
        work.mkdir()
        return bound(args, work)

    def test_query_and_time_budget_codes_are_distinct(self):
        backend = self.backend()
        backend.args.max_queries = 0
        self.assertEqual(backend.query("equal")["reason_code"], "QUERY_BUDGET_EXHAUSTED")
        backend.deadline = 0
        self.assertEqual(backend.query("equal")["reason_code"], "TIME_BUDGET_EXHAUSTED")
        self.assertEqual(backend.queries, [])

    def test_query_failure_diagnostics_preserve_unknown(self):
        backend = self.backend()
        cases = [(dict(status="UNKNOWN", returncode=-1, timed_out=True, violation=[]), "SOLVER_TIMEOUT"),
                 (dict(status="UNKNOWN", returncode=1, timed_out=False, violation=["unwinding assertion loop 1"]), "UNWINDING_INCOMPLETE"),
                 (dict(status="UNKNOWN", returncode=1, timed_out=False, violation=["division by zero"]), "SAFETY_OR_OTHER_PROPERTY_FAILURE"),
                 (dict(status="UNKNOWN", returncode=1, timed_out=False, violation=["file /tmp/unwind-case/harness.c", "division by zero"]), "SAFETY_OR_OTHER_PROPERTY_FAILURE"),
                 (dict(status="UNKNOWN", returncode=0, timed_out=False, violation=[]), "UNRECOGNIZED_SOLVER_OUTPUT")]
        for value, code in cases:
            with patch("c_backend.check_obligation", return_value=dict(value)), contextlib.redirect_stdout(io.StringIO()):
                result = backend.query("safety")
            self.assertEqual((result["status"], result["reason_code"]), ("UNKNOWN", code))

    def test_real_process_timeout_is_unknown(self):
        rc, timed_out = oracle.run([sys.executable, "-c", "import time; time.sleep(30)"], self.root / "timeout.log", 0.05)
        self.assertTrue(timed_out)
        self.assertEqual(diagnostic_code(dict(status="UNKNOWN", returncode=rc, timed_out=timed_out)), "SOLVER_TIMEOUT")

    def test_partial_falls_back_to_certified_union(self):
        bound = bind_contract(ROOT / "cases/c_scalar/max_min.json")
        args = parse_args(["--contract", str(bound.contract.path), "--workdir", str(self.root)])
        found = dict(condition="x == y", condition_c="finder_x == finder_y", buckets={"EQ": [[(0, True)]]},
                     history=[dict(status="EQ", cube=[(0, True)], evidence={"status": "PROVED"})])
        def replay(backend, rows, **kwargs):
            backend.samples = [dict(x=1, y=1, r_original=1, r_cached=1)]
        with patch.object(bound, "prepare"), patch.object(bound, "state_obligations", return_value={"safety": {"status": "PROVED"}}), \
             patch.object(bound, "replay", replay), patch("condition_runner.search", return_value=found), \
             patch.object(bound, "present_condition", return_value=dict(condition="true", condition_c="true", basis="test compact presentation")), \
             patch.object(bound, "query", side_effect=[{"status": "UNKNOWN", "reason_code": "SOLVER_TIMEOUT"}, {"status": "PROVED"}]), \
             contextlib.redirect_stdout(io.StringIO()):
            report = run(args, bound)
        self.assertEqual(report["condition"], "x == y")
        summary = json.loads((self.root / "verification-result.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "PARTIAL")
        self.assertEqual(summary["obligations"]["sufficiency"]["basis"], "PROVED_REGION_UNION")
        self.assertEqual(summary["obligations"]["complement"]["status"], "NOT_CHECKED")
        check_schema(summary)

    def test_contradiction_invalidates_prior_proof_display(self):
        report = self.base_report()
        report.update(status="UNKNOWN", reason_code="CERTIFICATE_CONTRADICTION", reason="native/solver disagreement")
        summary = build_summary(report, samples=[{"x": 1}])
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["obligations"]["sufficiency"]["status"], "INVALIDATED")
        self.assertIsNone(summary["claim"]["condition"])

    def test_human_report_links_to_evidence_and_keeps_scope(self):
        report = self.base_report("x == y")
        report["status"] = "PARTIAL"
        report["final_validation"]["complement"] = dict(status="UNKNOWN", reason="deadline", reason_code="SOLVER_TIMEOUT", log="query/verify.log")
        summary = build_summary(report, samples=[{"x": 1}])
        write_summary(self.root, summary)
        text = (self.root / "report.md").read_text(encoding="utf-8")
        for expected in ("PARTIAL", "x == y", "SOLVER_TIMEOUT", "query/verify.log", "test domain"):
            self.assertIn(expected, text)
        check_schema(json.loads((self.root / "verification-result.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
