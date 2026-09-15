"""Admission, binding and native/protocol controls; mock results are not proofs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_conditions import parse_condition
from c_scalar_contract import Contract, Source
from c_scalar_backend import bind_contract
from find_c_conditions import parse_args
from condition_runner import run
import agent_workflow as workflow

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases/c_scalar"


class ScalarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, body):
        path = self.root / "program.c"
        path.write_text(body, encoding="utf-8")
        return Source(path)

    def backend(self, name="max_min"):
        bound = bind_contract(CASE / (name + ".json"))
        args = parse_args(["--contract", str(bound.contract.path), "--cc", os.environ.get("FINDER_CC", "cc"),
                           "--esbmc", "missing-scalar-test-solver", "--workdir", str(self.root)])
        return bound, args

    def config(self):
        return dict(case="c", contract=str(CASE / "max_min.json"), variant="pair", state_mode="stateless",
                    domain=None, goal="exact", esbmc="missing-scalar-test-solver", cc=os.environ.get("FINDER_CC", "cc"),
                    timeout=30, max_seconds=120, max_queries=20, max_rounds=3)

    def test_all_fixture_signatures(self):
        for path in CASE.glob("*.json"):
            with self.subTest(path=path):
                Contract(path)

    def test_rejects_unsupported_effects_and_types(self):
        bodies = [
            "uint32_t global; uint32_t f(uint32_t x) { return x; }",
            "uint32_t f(uint32_t *x) { return *x; }",
            "uint32_t f(uint32_t x) { uint32_t a[2]; return x; }",
            "uint32_t f(uint32_t x) { return system(x); }",
            "uint32_t f(uint32_t x) { return f(x); }",
            "uint32_t f(uint32_t x) { uint32_t y; return y; }",
            "uint32_t f(uint32_t x) { return x + 1; }",
            "uint32_t f(uint32_t x) { return x << x; }",
            "uint32_t f(uint32_t x) { return ++x; }",
            "uint32_t f(uint32_t x) { return (x = 2u); }",
            "uint32_t f(uint32_t x) { static uint32_t y = 0u; return y; }",
            "uint32_t f(uint32_t x) { uint32_t f = 0u; return f; }",
            "uint32_t f(uint32_t x) { if (x == 1u) return x; }",
            "uint32_t f(uint32_t x) { return (uint32_t)(x == 1u) + (x == 2u); }",
        ]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.source(body)

    def test_rejects_preprocessor_bypasses(self):
        for prefix in ('#define false true\n', '#include <stdio.h>\n', '%:define foo bar\n', '#if 0\n', '\\\n'):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                self.source(prefix + 'uint32_t f(uint32_t x) { return x; }')

    def test_comments_and_unsigned_operations(self):
        src = self.source('/* "comments" */\nuint32_t f(uint32_t x) { return (x - 1u) << 2u; } // okay\n')
        self.assertEqual(src.signatures["f"], ("uint32_t", ["uint32_t"]))

    def test_contract_rejects_wrong_binding_and_signature(self):
        data = json.loads((CASE / "max_min.json").read_text())
        for side in ("original", "candidate"):
            data[side]["source"] = str(CASE / data[side]["source"])
        for field, value in (("args", ["x", "x"]), ("entry", "absent")):
            changed = json.loads(json.dumps(data))
            changed["candidate"][field] = value
            path = self.root / "contract.json"
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                Contract(path)
        data["return_type"] = "bool"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            Contract(path)

    def test_contract_rejects_empty_and_out_of_type_domain(self):
        data = json.loads((CASE / "max_min.json").read_text())
        for lo, hi in ((2, 1), (-1, 1), (0, 2**32), (False, 1)):
            data["inputs"]["x"].update(min=lo, max=hi)
            path = self.root / "contract.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                Contract(path)

    def test_predicates_use_only_declared_fields(self):
        bound, _ = self.backend()
        self.assertTrue(parse_condition("x == y", bound.atom_type).evaluate(dict(x=2, y=2)))
        for atom in ("valid", "n == 1", "x % 2 == 0", "x == 0; abort()"):
            with self.subTest(atom=atom), self.assertRaises(ValueError):
                bound.atom_type.parse(atom)

    def test_seed_validation_and_domain(self):
        bound, _ = self.backend()
        with self.assertRaises(ValueError):
            bound.validate_seed({"x": True, "y": 0})
        self.assertFalse(bound.seed_in_domain(dict(x=32, y=0), "stateless"))
        self.assertTrue(all(bound.seed_in_domain(row, "stateless") for row in bound.default_seeds("stateless")))

    def test_replay_refuses_before_safety(self):
        bound, args = self.backend("unsafe_division")
        backend = bound(args, self.root)
        with patch("c_backend.subprocess.run") as execute, self.assertRaisesRegex(RuntimeError, "safety"):
            backend.replay([dict(n=0)])
        execute.assert_not_called()

    def test_unknown_safety_prevents_finder_replay_and_search(self):
        bound, args = self.backend()
        with patch.object(bound, "prepare"), patch.object(bound, "replay") as replay, patch("condition_runner.search") as search:
            report = run(args, bound)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["state_obligations"]["safety"]["status"], "UNKNOWN")
        replay.assert_not_called()
        search.assert_not_called()

    def test_unknown_safety_prevents_agent_replay(self):
        bound, args = self.backend()
        with patch.object(workflow, "adapter", return_value=(bound, args)), patch.object(bound, "prepare"), patch.object(bound, "replay") as replay:
            _, result = workflow.start(self.config(), self.root)
        self.assertEqual(result["phase"], "UNKNOWN")
        replay.assert_not_called()

    def test_harness_checks_full_domain_without_disabling_safety(self):
        bound, _ = self.backend("series")
        harness = bound.make_harness(bound.contract.model(), "pair", "stateless", "safety")
        self.assertIn("ce_original_sum(finder_n)", harness)
        self.assertIn("ce_candidate_sum(finder_n)", harness)
        self.assertIn('"__C_SCALAR_SAFETY__"', harness)
        self.assertIn("volatile uint32_t", harness)
        self.assertNotIn("--no-unwinding-assertions", bound.command_extra)

    def test_source_and_contract_identity_drift(self):
        config = self.config()
        data = json.loads((CASE / "max_min.json").read_text())
        for side in ("original", "candidate"):
            dest = self.root / (side + ".c")
            dest.write_bytes((CASE / data[side]["source"]).read_bytes())
            data[side]["source"] = dest.name
        path = self.root / "contract.json"
        path.write_text(json.dumps(data))
        config["contract"] = str(path)
        before = workflow.fingerprint(config)
        dest.write_text(dest.read_text() + "\n/* changed */\n")
        self.assertNotEqual(before, workflow.fingerprint(config))
        before = workflow.fingerprint(config)
        data["inputs"]["x"]["max"] = 20
        path.write_text(json.dumps(data))
        self.assertNotEqual(before, workflow.fingerprint(config))

    def test_native_fixtures(self):
        for name in ("max_min", "parity", "series", "series_mutant"):
            with self.subTest(name=name):
                bound, args = self.backend(name)
                directory = self.root / name
                directory.mkdir()
                backend = bound(args, directory)
                backend.prepare()
                # TEST ONLY: bypass the gate to compare known, safe fixture executions.
                backend.restore_obligations({"safety": {"status": "PROVED"}})
                if name == "max_min":
                    rows = [dict(x=x, y=y) for x in range(5) for y in range(5)]
                    expected = lambda r: (max(r["x"], r["y"]), min(r["x"], r["y"]))
                else:
                    rows = [dict(n=n) for n in range(32)]
                    expected = (lambda r: (r["n"] % 2, r["n"] % 2)) if name == "parity" else (
                        lambda r: (r["n"] * (r["n"] - 1) // 2, r["n"] * (r["n"] + (1 if name == "series_mutant" else -1)) // 2))
                observed = backend.replay(rows)
                self.assertEqual([(r["r_original"], r["r_cached"]) for r in observed], [expected(r) for r in rows])

    def test_native_same_name_helpers_and_permuted_binding(self):
        data = json.loads((CASE / "max_min.json").read_text())
        body = 'uint32_t helper(uint32_t x) { return x + 1u; }\nuint32_t choose(uint32_t a, uint32_t b) { return helper(a) - b; }\n'
        for side in ("original", "candidate"):
            dest = self.root / (side + ".c")
            dest.write_text(body)
            data[side]["source"] = str(dest)
        data["candidate"]["args"] = ["y", "x"]
        path = self.root / "contract.json"
        path.write_text(json.dumps(data))
        bound = bind_contract(path)
        _, args = self.backend()
        backend = bound(args, self.root)
        backend.prepare()
        backend.restore_obligations({"safety": {"status": "PROVED"}})  # native control only
        row = backend.replay([dict(x=3, y=2)])[0]
        self.assertEqual((row["r_original"], row["r_cached"]), (2, 0))

    def test_native_bool_input_and_condition(self):
        source = self.root / "bool.c"
        source.write_text("bool flip(bool b) { return !b; }")
        data = dict(schema=1, name="boolean", original=dict(source="bool.c", entry="flip", args=["enabled"]),
                    candidate=dict(source="bool.c", entry="flip", args=["enabled"]),
                    inputs=dict(enabled=dict(type="bool", min=0, max=1)), return_type="bool", observations=["return"], unwind=4)
        path = self.root / "contract.json"
        path.write_text(json.dumps(data))
        bound = bind_contract(path)
        self.assertTrue(bound.atom_type.parse("enabled").evaluate(dict(enabled=1)))
        _, args = self.backend()
        backend = bound(args, self.root)
        backend.prepare()
        backend.restore_obligations({"safety": {"status": "PROVED"}})  # native control only
        rows = backend.replay([dict(enabled=0), dict(enabled=1)])
        self.assertEqual([r["r_original"] for r in rows], [1, 0])
        source.write_text(source.read_text() + "\n/* later edit */")
        with self.assertRaisesRegex(ValueError, "changed after binding"):
            bound(args, self.root / "later")

    def test_agent_scalar_session_with_mock_certificates(self):
        bound, args = self.backend()
        def fake_query(backend, kind, *positional, **kwargs):
            return dict(status="REFUTED" if kind == "feasible" else "PROVED")
        with patch.object(workflow, "adapter", return_value=(bound, args)), patch.object(bound, "query", fake_query):
            directory, started = workflow.start(self.config(), self.root)
            self.assertEqual(started["phase"], "READY")
            proposal = self.root / "proposal.json"
            proposal.write_text(json.dumps(dict(session_id=started["session_id"], round=1, condition="x == y")))
            result = workflow.step(directory, proposal)
        self.assertEqual(result["status"], "EXACT")  # protocol mock, not a formal proof
        self.assertTrue(result["goal_reached"])


if __name__ == "__main__":
    unittest.main()
