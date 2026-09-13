"""Tests for candidate predicates and the paired experimental protocol."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from find_cache_conditions import ROOT
from find_prime_conditions import (MODULI, ModuloAtom, ModuloPrimeBackend, PrimeAtom,
                                   PrimeBackend, compact_condition, parse_args)
from predicate_search import matches, search
from test_predicate_search import FiniteOracle

sys.path.insert(0, str(ROOT / "cases/prime_lookup"))
spec = importlib.util.spec_from_file_location("vocabulary_experiment", ROOT / "cases/prime_lookup/compare_vocabularies.py")
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


class ModuloTests(unittest.TestCase):
    def test_safe_modulo_grammar_and_bounds(self):
        self.assertEqual(PrimeAtom.parse(" x % 03 == 2 "), ModuloAtom(3, 2))
        for text in ("x % 0 == 0", "x % 1 == 0", "x % 17 == 0", "x % 3 == 3",
                     "x % -2 == 0", "x % key == 0", "x % 3 == 0; abort()"):
            with self.assertRaises(ValueError):
                PrimeAtom.parse(text)

    def test_same_seeds_and_budgets_different_vocabulary(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            base = PrimeBackend(parse_args(["--domain", "0:127"]), a)
            mod = ModuloPrimeBackend(parse_args(["--domain", "0:127", "--vocabulary", "modulo"]), b)
            self.assertEqual(base.default_seeds("stateless"), mod.default_seeds("stateless"))
            self.assertEqual(base.args.max_predicates, mod.args.max_predicates)
            self.assertEqual(base.args.max_queries, mod.args.max_queries)
            self.assertEqual(len(base.initial_atoms()), 3)
            self.assertEqual(len(mod.initial_atoms()), 18)
            self.assertIn(ModuloAtom(4, 0), mod.initial_atoms())

    def test_compaction_understands_certified_modulo_regions(self):
        found = {"predicates": ["x % 2 == 0"], "eq_cubes": [((0, True),)],
                 "condition": "(x % 2 == 0)", "condition_c": "(finder_x % UINT32_C(2) == UINT32_C(0))"}
        result = compact_condition(found, (0, 127))
        self.assertEqual(result["condition"], found["condition"])

    def test_repeat_order_is_balanced(self):
        jobs = list(experiment.plan(2))
        self.assertEqual(len(jobs), 24)
        for domain in experiment.DOMAINS:
            for variant in experiment.VARIANTS:
                first = [mode for repeat, d, v, mode in jobs if repeat == 0 and d == domain and v == variant]
                second = [mode for repeat, d, v, mode in jobs if repeat == 1 and d == domain and v == variant]
                self.assertEqual(first, second[::-1])

    def test_unknown_runs_are_included_in_summaries(self):
        rows = [{"domain": "0:63", "variant": "truncated", "vocabulary": "baseline", "passed": passed,
                 "status": "EXACT" if passed else "UNKNOWN", "queries_used": 10, "finder_seconds": seconds,
                 "elapsed_seconds": seconds, "raw_condition_chars": 12, "published_condition_chars": 12}
                for passed, seconds in ((True, 2), (False, 600))]
        summary = next(row for row in experiment.summarize(rows) if row["domain"] == "0:63" and row["variant"] == "truncated")
        self.assertEqual(summary["modes"]["baseline"]["finder_seconds"], 301)
        self.assertEqual(summary["modes"]["baseline"]["certified"], 1)

    @unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
    def test_modulo_c_semantics_and_native_search(self):
        compiler = shutil.which(os.environ.get("FINDER_CC", "cc"))
        with tempfile.TemporaryDirectory() as tmp:
            backend = ModuloPrimeBackend(parse_args(["--vocabulary", "modulo", "--domain", "0:127", "--cc", compiler, "--esbmc", "missing-test-esbmc"]), tmp)
            backend.prepare()
            for variant in ("fallback", "truncated", "mutant"):
                backend.args.variant = variant
                rows = backend.replay([{"x": x} for x in range(128)], repeat=True)
                finite = FiniteOracle(rows)
                finite.numeric_fields, finite.atom_type = ("x",), PrimeAtom
                atoms = backend.initial_atoms()
                found = search(finite, atoms, 96)
                self.assertFalse(found["buckets"]["UNKNOWN"])
                for row in rows:
                    self.assertEqual(any(matches(cube, atoms, row) for cube in found["eq_cubes"]), row["r_original"] == row["r_cached"])
            # Check emitted C against Python for all small inputs and uint32 max.
            atoms = [ModuloAtom(d, r) for d in MODULI for r in range(d)]
            lines = ['#include <stdint.h>', 'int main(void) {']
            for x in (*range(256), 4294967295):
                lines.append(f'{{ uint32_t finder_x = UINT32_C({x});')
                for atom in atoms:
                    lines.append(f'if (({atom.c()}) != {int(atom.evaluate({"x": x}))}) return 1;')
                lines.append('}')
            lines.append('return 0; }')
            source = Path(tmp) / "modulo.c"
            source.write_text('\n'.join(lines))
            exe = Path(tmp) / ("modulo.exe" if os.name == "nt" else "modulo")
            command = ([compiler, "/nologo", "/std:c11", str(source), "/Fe:"+str(exe), "/Fo:"+str(Path(tmp)/"modulo.obj")]
                       if Path(compiler).stem.lower() == "cl" else [compiler, "-std=c11", str(source), "-o", str(exe)])
            proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(subprocess.run([str(exe)], timeout=10).returncode, 0)


if __name__ == "__main__":
    unittest.main()
