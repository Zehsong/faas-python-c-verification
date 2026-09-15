"""Protocol and native checks. Mocked query results are NOT formal proofs."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_conditions import parse_condition, strict_json, validate_proposal
import agent_workflow as workflow
from find_prime_conditions import PrimeAtom, PrimeBackend


def config(**changes):
    return {"case": "prime", "variant": "fallback", "domain": "0:63", "state_mode": "invariant",
            "goal": "exact", "esbmc": "missing-test-esbmc", "cc": os.environ.get("FINDER_CC", "cc"),
            "timeout": 10, "max_seconds": 120, "max_queries": 32, "max_rounds": 8, **changes}


def row(x, same=True):
    return {"x": x, "r_original": 1, "r_cached": int(same)}


class ConditionTests(unittest.TestCase):
    def test_boolean_tree_and_uint_boundaries(self):
        condition = parse_condition({"any": ["x <= 31", {"all": ["x % 2 == 0", {"not": "x == 40"}]}]}, PrimeAtom)
        for x in (0, 2, 31, 32, 37, 40, 42, 4294967295):
            self.assertEqual(condition.evaluate({"x": x}), x <= 31 or (x % 2 == 0 and x != 40))
        self.assertIn("UINT32_C(40)", condition.expression(c=True))
        self.assertFalse(parse_condition(False, PrimeAtom).evaluate({"x": 0}))

    def test_code_outputs_invalid_operators_and_sizes_rejected(self):
        deep = True
        for _ in range(14):
            deep = {"not": deep}
        for value in ("original(x)", "r_cached == 1", "x == 0); assert(1);", "x % 0 == 0", "valid",
                      {"any": []}, {"all": [True], "not": False}, {"assume": True}, 1,
                      {"any": [True] * 129}, deep):
            with self.subTest(value=str(value)[:60]), self.assertRaises(ValueError):
                parse_condition(value, PrimeAtom)

    def test_duplicate_json_keys_and_nonfinite_values_rejected(self):
        for text in ('{"condition":true,"condition":false}', '{"seeds":[{"x":NaN}]}'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_contract_scope_and_labels_cannot_be_proposed(self):
        settings = workflow.adapter(config())[1]
        state = {"session_id": "a", "rounds": 0, "config": config()}
        good = {"session_id": "a", "round": 1, "condition": "x != 9"}
        for proposal in ({**good, "domain": "0:31"}, {**good, "verdict": "EXACT"},
                         {**good, "session_id": "b"}, {**good, "round": True},
                         {**good, "round": 2}, {**good, "seeds": [{"x": 64}]},
                         {**good, "seeds": [{"x": 9, "r_cached": 0}]}):
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                validate_proposal(proposal, state, PrimeBackend, settings)


class CandidateTests(unittest.TestCase):
    def backend(self, samples, replies):
        calls = []
        def query(kind, condition):
            calls.append((kind, condition))
            expected_kind, status = replies.pop(0)
            self.assertEqual(kind, expected_kind)
            return {"status": status, "test_only": True}
        return SimpleNamespace(samples=samples, query=query), calls

    def test_native_refutation_requires_no_solver(self):
        backend, calls = self.backend([row(9, False)], [])
        result = workflow.check_candidate(backend, parse_condition(True, PrimeAtom), "exact")
        self.assertEqual(result["status"], "REFUTED")
        self.assertEqual(calls, [])

    def test_partial_has_a_proof_and_native_equal_outside_feedback(self):
        backend, calls = self.backend([row(2), row(32)], [("feasible", "REFUTED"), ("equal", "PROVED")])
        result = workflow.check_candidate(backend, parse_condition("x <= 31", PrimeAtom), "exact")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["feedback"][0]["kind"], "equal_outside")
        self.assertEqual(len(calls), 2)

    def test_exact_requires_both_proofs(self):
        for status in ("PROVED", "UNKNOWN", "REFUTED"):
            backend, _ = self.backend([row(2)], [("feasible", "REFUTED"), ("equal", "PROVED"), ("different", status)])
            result = workflow.check_candidate(backend, parse_condition(True, PrimeAtom), "exact")
            self.assertEqual(result["status"], "EXACT" if status == "PROVED" else "PARTIAL")

    def test_unproved_sufficiency_never_publishes_partial(self):
        backend, _ = self.backend([row(2)], [("feasible", "REFUTED"), ("equal", "UNKNOWN")])
        self.assertEqual(workflow.check_candidate(backend, parse_condition(True, PrimeAtom), "exact")["status"], "UNKNOWN")

    def test_empty_candidate_is_not_useful_but_can_be_exact_for_all_unequal(self):
        backend, _ = self.backend([row(2)], [("feasible", "PROVED"), ("equal", "PROVED")])
        self.assertEqual(workflow.check_candidate(backend, parse_condition(False, PrimeAtom), "exact")["status"], "EMPTY_CANDIDATE")
        backend, _ = self.backend([row(9, False)], [("feasible", "PROVED"), ("equal", "PROVED"), ("different", "PROVED")])
        self.assertEqual(workflow.check_candidate(backend, parse_condition(False, PrimeAtom), "exact")["status"], "EXACT")

    def test_sufficient_goal_does_not_query_complement(self):
        backend, calls = self.backend([row(2)], [("feasible", "REFUTED"), ("equal", "PROVED")])
        result = workflow.check_candidate(backend, parse_condition(True, PrimeAtom), "sufficient")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(len(calls), 2)

    def test_out_of_region_solver_witness_fails_closed(self):
        backend = SimpleNamespace(samples=[], query=lambda *args: {"status": "REFUTED", "native_replay": row(40)})
        result = workflow.check_candidate(backend, parse_condition("x <= 31", PrimeAtom), "exact")
        self.assertEqual(result["status"], "UNKNOWN")


@unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
class NativeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def mock_queries(self, replies):
        def query(backend, kind, condition="true", **kwargs):
            if len(backend.queries) >= backend.args.max_queries:
                return {"status": "UNKNOWN", "reason": "test query budget exhausted"}
            expected, status = replies.pop(0)
            self.assertEqual(kind, expected)
            result = {"status": status, "kind": kind, "test_only": "mock protocol check, NOT formal proof"}
            backend.queries.append(result)
            return result
        return patch.object(PrimeBackend, "query", query)

    def propose(self, directory, condition, **extra):
        context = json.loads((directory / "agent-context.json").read_text())
        proposal = {"session_id": context["session_id"], "round": context["next_round"], "condition": condition, **extra}
        path = self.root / "proposal.json"
        path.write_text(json.dumps(proposal))
        return workflow.step(directory, path)

    def test_missing_solver_produces_context_but_no_certificate(self):
        directory, result = workflow.start(config(), self.root)
        self.assertEqual(result["phase"], "UNKNOWN")
        self.assertIsNone(result["condition"])
        self.assertTrue(json.loads((directory / "agent-context.json").read_text())["samples"])

    def test_resume_refine_and_rejected_data_preserve_prior_proof(self):
        replies = [("feasible", "REFUTED"), ("feasible", "REFUTED"), ("equal", "PROVED"),
                   ("feasible", "REFUTED"), ("equal", "PROVED"), ("different", "PROVED")]
        with self.mock_queries(replies):
            directory, _ = workflow.start(config(), self.root)
            partial = self.propose(directory, "x <= 31")
            self.assertEqual(partial["status"], "PARTIAL")
            rejected = self.propose(directory, True, domain="0:31")
            self.assertEqual(rejected["latest_feedback"]["status"], "REJECTED")
            self.assertEqual(rejected["queries_used"], partial["queries_used"])
            self.assertEqual(rejected["condition"], partial["condition"])
            exact = self.propose(directory, True)
            self.assertEqual(exact["status"], "EXACT")
            self.assertTrue(exact["goal_reached"])
            self.assertEqual(exact["rounds"], 3)
            self.assertFalse(replies)

    def test_native_seed_refutes_wrong_candidate_without_queries(self):
        with self.mock_queries([("feasible", "REFUTED")]):
            directory, initial = workflow.start(config(variant="mutant"), self.root)
            result = self.propose(directory, True, seeds=[{"x": 9}])
            self.assertEqual(result["latest_feedback"]["status"], "REFUTED")
            self.assertEqual(result["queries_used"], initial["queries_used"])
            self.assertIsNone(result["condition"])

    def test_source_identity_drift_blocks_resume(self):
        with self.mock_queries([("feasible", "REFUTED")]):
            directory, _ = workflow.start(config(), self.root)
        with patch.object(workflow, "fingerprint", return_value={"changed": True}):
            result = self.propose(directory, True)
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_contract_file_drift_is_detected(self):
        with self.mock_queries([("feasible", "REFUTED")]):
            directory, _ = workflow.start(config(), self.root)
        path = directory / "session.json"
        state = json.loads(path.read_text())
        state["config"]["domain"] = "0:31"
        workflow.save(path, state)
        result = self.propose(directory, True)
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertIsNone(result["condition"])

    def test_drift_on_failed_round_withdraws_prior_current_certificate(self):
        with self.mock_queries([("feasible", "REFUTED"), ("feasible", "REFUTED"), ("equal", "PROVED")]):
            directory, _ = workflow.start(config(), self.root)
            self.assertEqual(self.propose(directory, "x <= 31")["status"], "PARTIAL")
        state = json.loads((directory / "session.json").read_text())
        with patch.object(workflow, "fingerprint", side_effect=[state["identity"], OSError("input disappeared")]), \
                patch.object(PrimeBackend, "prepare", side_effect=RuntimeError("compile failed")):
            result = self.propose(directory, True)
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertIsNone(result["best_result"])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_round_budget_and_session_lock_prevent_extra_updates(self):
        with self.mock_queries([("feasible", "REFUTED")]):
            directory, _ = workflow.start(config(max_rounds=1), self.root)
            self.propose(directory, True, domain="0:31")
        with self.assertRaisesRegex(ValueError, "round budget"):
            self.propose(directory, True)
        with workflow.session_lock(directory), self.assertRaises(FileExistsError):
            self.propose(directory, True)

    def test_active_time_budget_does_not_reset_on_resume(self):
        with self.mock_queries([("feasible", "REFUTED")]):
            directory, _ = workflow.start(config(), self.root)
        path = directory / "session.json"
        state = json.loads(path.read_text())
        state["active_seconds"] = state["config"]["max_seconds"]
        workflow.save(path, state)
        with patch.object(PrimeBackend, "prepare") as prepare:
            result = self.propose(directory, True)
        prepare.assert_not_called()
        self.assertEqual(result["latest_feedback"]["status"], "UNKNOWN")
        self.assertIn("budget", result["latest_feedback"]["reason"])

    def test_query_budget_is_shared_across_rounds(self):
        # Start consumes one, first partial consumes two; the next round has
        # only one query left, so its equality cannot be certified.
        with self.mock_queries([("feasible", "REFUTED"), ("feasible", "REFUTED"), ("equal", "PROVED"), ("feasible", "REFUTED")]):
            directory, _ = workflow.start(config(max_queries=4), self.root)
            self.propose(directory, "x <= 31")
            result = self.propose(directory, True)
        self.assertEqual(result["queries_used"], 4)
        self.assertEqual(result["latest_feedback"]["status"], "UNKNOWN")
        self.assertEqual(result["condition"], "x <= 31")

    def test_generated_boolean_tree_matches_native_c(self):
        condition = parse_condition({"any": ["x <= 31", {"all": ["x % 3 == 0", {"not": "x == 33"}]}]}, PrimeAtom)
        source = self.root / "condition.c"
        values = list(range(128)) + [4294967295]
        source.write_text('#include <stdint.h>\n#include <stdbool.h>\n#include <stdio.h>\nint main(void) {\n'
                          + 'uint32_t xs[] = {' + ','.join(f'UINT32_C({x})' for x in values) + '};\n'
                          + f'for (unsigned i=0;i<{len(values)};i++) {{ uint32_t finder_x=xs[i]; '
                          + f'printf("%d\\n", (int)({condition.expression(c=True)})); }} return 0; }}\n')
        compiler = shutil.which(config()["cc"])
        executable = self.root / ("condition.exe" if sys.platform == "win32" else "condition")
        command = ([compiler, "/nologo", "/std:c11", str(source), "/Fe:"+str(executable), "/Fo:"+str(self.root / "condition.obj")]
                   if Path(compiler).stem.lower() == "cl" else [compiler, "-std=c11", str(source), "-o", str(executable)])
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(list(map(int, proc.stdout.split())), [int(condition.evaluate({"x": x})) for x in values])


if __name__ == "__main__":
    unittest.main()
