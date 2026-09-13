"""Binding validation, proof gating and native controls for the shared sketch."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cache_sketch import CacheSketch, PROPERTIES
from find_cache_conditions import ROOT, SKETCH, CacheBackend, oracle, parse_args, run
from find_config_conditions import SKETCH as CONFIG_SKETCH

spec = importlib.util.spec_from_file_location("sketch_controls", ROOT / "cases/sketch_reuse/run_checks.py")
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


class SketchTests(unittest.TestCase):
    def load_binding(self, data, directory):
        path = Path(directory) / "sketch.json"
        path.write_text(json.dumps(data))
        return CacheSketch(path)

    def test_invalid_or_executable_bindings_are_rejected(self):
        for change in (
            {"variants": {"good": "cached_good(); abort()"}},
            {"state_fields": ["valid", "value"]},
            {"call_args": ["x", "x"]},
            {"initial_state": {"valid": 2, "key": 0, "value": 0}},
            {"expected_condition": "true"},
        ):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    self.load_binding({**copy.deepcopy(SKETCH.data), **change}, tmp)

    def test_manifest_distinguishes_template_from_instance(self):
        a, b = SKETCH.manifest(), CONFIG_SKETCH.manifest()
        self.assertEqual(a["template_sha256"], b["template_sha256"])
        self.assertNotEqual(a["binding_sha256"], b["binding_sha256"])
        self.assertEqual(PROPERTIES["equal"], oracle.RELATIONAL_PROPERTY)
        self.assertNotIn("verdict", a)

    def test_generated_obligations_bind_environment_and_state_explicitly(self):
        source = CONFIG_SKETCH.render("", "stale", "invariant", "different")
        self.assertIn(".cached_config = finder_cached_config", source)
        self.assertIn("original(finder_x, finder_config)", source)
        self.assertIn("cached_stale(&cache, finder_x, finder_config)", source)
        self.assertIn("r_original != r_cached", source)
        self.assertIn("__ESBMC_assume(invariant(&cache))", source)
        self.assertNotIn("__ESBMC_assume(finder_config == finder_cached_config)", source)

    def test_failed_state_obligation_prevents_search(self):
        for failed in ("init", "preservation"):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as tmp, \
                    patch.object(CacheBackend, "prepare"), patch.object(CacheBackend, "replay"), \
                    patch.object(CacheBackend, "query", side_effect=lambda kind, **kw:
                        {"status": "REFUTED" if kind == failed else "PROVED"}), \
                    patch("find_cache_conditions.search") as search, contextlib.redirect_stdout(io.StringIO()):
                report = run(parse_args(["--workdir", tmp]))
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertIsNone(report["condition"])
                search.assert_not_called()
                self.assertTrue((Path(report["artifacts"]) / "inputs/sketch.json").exists())

    @unittest.skipUnless(shutil.which(os.environ.get("FINDER_CC", "cc")), "C compiler unavailable")
    def test_native_positive_and_negative_controls(self):
        compiler = shutil.which(os.environ.get("FINDER_CC", "cc"))
        with tempfile.TemporaryDirectory() as tmp:
            for family in ("same_language_cache", "config_cache"):
                for control in ("valid_init", "invalid_init", "valid_preservation", "invalid_preservation"):
                    with self.subTest(family=family, control=control):
                        directory = Path(tmp) / f"{family}-{control}"
                        directory.mkdir()
                        source, kind, expected = controls.prepare_control(family, control, directory)
                        # One reachable native state only; Codespace checks all symbolic states.
                        runtime = '''
#include <stdlib.h>
#include <string.h>
static int violated;
uint32_t nondet_u32(void) { return 0; }
bool nondet_bool(void) { return false; }
void __ESBMC_assume(bool condition) { if (!condition) exit(3); }
void __ESBMC_assert(bool condition, const char *message) {
    if (!condition) {
        if (strcmp(message, "PROPERTY")) exit(4);
        violated = 1;
    }
}
int main(void) { finder_entry(); return violated; }
'''.replace("PROPERTY", PROPERTIES[kind])
                        source.write_text(source.read_text() + runtime)
                        executable = directory / ("control.exe" if os.name == "nt" else "control")
                        command = ([compiler, "/nologo", "/std:c11", str(source), "/Fe:" + str(executable),
                                    "/Fo:" + str(directory / "control.obj")]
                                   if Path(compiler).stem.lower() == "cl" else
                                   [compiler, "-std=c11", str(source), "-o", str(executable)])
                        proc = subprocess.run(command, capture_output=True, text=True, timeout=60)
                        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                        proc = subprocess.run([str(executable)], capture_output=True, timeout=10)
                        self.assertEqual(proc.returncode, 1 if expected == "REFUTED" else 0)


if __name__ == "__main__":
    unittest.main()
