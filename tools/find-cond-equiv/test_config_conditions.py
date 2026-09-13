"""Native and finite-domain checks, not substitutes for ESBMC certification."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from find_config_conditions import (ConfigAtom, ConfigBackend, FIELDS, default_seeds,
                                    initial_atoms, make_harness, parse_args, run, seed_in_domain)
from find_cache_conditions import witness_from_log
from predicate_search import Atom, UINT32_MAX, matches, search
from test_predicate_search import FiniteOracle


class ConfigTests(unittest.TestCase):
    def test_configuration_is_not_assumed_fresh(self):
        row = dict(x=7, valid=1, key=7, value=8, config=2, cached_config=1)
        self.assertTrue(seed_in_domain(row, "invariant"))
        self.assertFalse(ConfigAtom.parse("config == cached_config").evaluate(row))
        with self.assertRaises(ValueError):
            Atom.parse("config == cached_config")  # Original adapter vocabulary unchanged.
        with self.assertRaises(ValueError):
            ConfigAtom.parse("config = cached_config")

    def test_witness_requires_both_environment_fields(self):
        row = dict(x=7, valid=1, key=7, value=8, config=2, cached_config=1)
        log = "\n".join(f"finder_{key} = {value}" for key, value in row.items())
        self.assertEqual(witness_from_log(log, FIELDS), row)
        self.assertIsNone(witness_from_log(log.replace("finder_config", "other"), FIELDS))

    def test_input_only_vocabulary_cannot_separate_stale_configuration(self):
        rows = [dict(x=7, valid=1, key=7, value=8, config=c, cached_config=1,
                     r_original=7+c, r_cached=8) for c in (1, 2)]
        atoms = [Atom.parse("x == key")]
        result = search(FiniteOracle(rows), atoms, max_predicates=1)
        self.assertTrue(result["buckets"]["UNKNOWN"])
        self.assertFalse(result["buckets"]["EQ"])
        atoms = initial_atoms()
        result = search(FiniteOracle(rows), atoms, max_predicates=len(atoms))
        self.assertFalse(result["buckets"]["UNKNOWN"])


@unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
class NativeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.args = parse_args(["--cc", os.environ.get("FINDER_CC", "cc"), "--esbmc", "missing-test-esbmc"])
        cls.backend = ConfigBackend(cls.args, cls.temp.name)
        cls.backend.prepare()

    def test_native_variants_and_finite_search(self):
        seeds = default_seeds("invariant")
        for variant in ("good", "stale"):
            self.backend.args.variant = variant
            rows = self.backend.replay(seeds, repeat=True)
            atoms = initial_atoms()
            found = search(FiniteOracle(rows), atoms, max_predicates=len(atoms))
            self.assertFalse(found["buckets"]["UNKNOWN"])
            for row in rows:
                same = row["r_original"] == row["r_cached"]
                expected = variant == "good" or not (row["valid"] and row["x"] == row["key"]) or row["config"] == row["cached_config"]
                self.assertEqual(same, expected)
                self.assertEqual(any(matches(cube, atoms, row) for cube in found["eq_cubes"]), same)

    def test_two_calls_with_environment_change_reproduce_stale_bug(self):
        for variant in ("good", "stale"):
            self.backend.args.variant = variant
            first = self.backend.replay([dict(x=UINT32_MAX, valid=0, key=0, value=0,
                                             config=1, cached_config=0)], repeat=True)[0]
            self.assertEqual(first["r_cached"], 0)  # Modular arithmetic.
            second = self.backend.replay([dict(x=UINT32_MAX, valid=first["after_valid"],
                key=first["after_key"], value=first["after_value"], config=2,
                cached_config=first["after_cached_config"])], repeat=True)[0]
            self.assertEqual(second["r_original"], 1)
            self.assertEqual(second["r_cached"], 1 if variant == "good" else 0)

    def test_plain_probe_matches_instrumented_state_and_returns(self):
        command = json.loads((self.backend.inputs / "compile-command.json").read_text())
        plain = self.backend.inputs / ("plain.exe" if os.name == "nt" else "plain")
        if Path(command[0]).stem.lower() == "cl":
            command = [part if not part.startswith("/Fe:") else "/Fe:" + str(plain) for part in command]
            command.insert(1, "/DPLAIN_PROBE")
        else:
            command[command.index("-o") + 1] = str(plain)
            command.insert(1, "-DPLAIN_PROBE")
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        seeds = default_seeds("invariant")
        data = "".join(" ".join(str(row[f]) for f in FIELDS) + "\n" for row in seeds)
        for variant in ("good", "stale"):
            self.backend.args.variant = variant
            traced = self.backend.replay(seeds, repeat=True)
            proc = subprocess.run([str(plain), variant], input=data, capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rows = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(rows), len(traced))
            for left, right in zip(rows, traced):
                self.assertEqual({k:v for k,v in left.items() if k != "hit"},
                                 {k:v for k,v in right.items() if k != "hit"})

    def test_all_formal_templates_compile(self):
        model = self.backend.model
        pieces = [model]
        for variant in ("good", "stale"):
            for state in ("empty", "invariant"):
                for kind in ("init", "preservation", "feasible", "equal", "different", "expected"):
                    text = make_harness(model, variant, state, kind, expected="finder_config == finder_cached_config")
                    pieces.append(text[len(model):].replace("finder_entry", f"{variant}_{state}_{kind}"))
        source = self.backend.inputs / "obligations.c"
        source.write_text("\n".join(pieces))
        compiler = shutil.which(self.args.cc)
        output = str(self.backend.inputs / "formal.obj")
        command = ([compiler, "/nologo", "/std:c11", "/c", str(source), "/Fo:" + output]
                   if Path(compiler).stem.lower() == "cl" else
                   [compiler, "-std=c11", "-c", str(source), "-o", output])
        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_missing_solver_does_not_certify_native_results(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            report = run(parse_args(["--cc", self.args.cc, "--esbmc", "missing-test-esbmc", "--workdir", tmp]))
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIsNone(report["condition"])
        self.assertEqual(report["traces_collected"], 512)


if __name__ == "__main__":
    unittest.main()
