"""Native/reference and experiment controls. No mocked result is a proof."""
import copy
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import run_checks as experiment
from c_scalar_contract import Contract


class ExternalBitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_contracts_and_locked_sources(self):
        lock = experiment.read_json(experiment.CASE / 'engine-lock.json')
        self.assertEqual(experiment.engine_hashes(), lock['files'])
        self.assertEqual(sum(row[2] for row in experiment.CASES), 5)
        for name, _, _ in experiment.CASES:
            contract = experiment.CASE / (name + '.json')
            Contract(contract)
            data = experiment.read_json(contract)
            self.assertEqual(data['observations'], ['return'])
            self.assertNotIn('hypotheses', data)
            self.assertEqual(data['unwind'], 34)

    def test_native_references_and_adaptations(self):
        # These reviewed loops terminate after <=32 iterations. This test-only
        # safety restoration permits native fixture checks without ESBMC. It
        # is never used in the experiment and establishes no formal safety claim.
        values = sorted(set(range(256)) | {2**i for i in range(32)} |
                        {2**i - 1 for i in range(1, 33)} | {0xAAAAAAAA, 0x55555555, 0x80000001})
        powers = {2**i for i in range(32)}
        cc = os.environ.get('FINDER_CC', 'cc')
        self.assertIsNotNone(shutil.which(cc), 'native compiler required; do not silently skip')
        for name in ('power_guarded_32', 'power_raw_32', 'popcount_32'):
            with self.subTest(name=name):
                bound = experiment.bind_contract(experiment.CASE / (name + '.json'))
                args = experiment.parse_args(['--contract', str(bound.contract.path), '--cc', cc,
                                             '--esbmc', 'missing-native-fixture-solver'])
                directory = self.root / name
                directory.mkdir()
                backend = bound(args, directory)
                backend.prepare()
                backend.restore_obligations({'safety': {'status': 'PROVED'}})
                rows = backend.replay([dict(x=x) for x in values])
                self.assertEqual(len(rows), len(values))
                for row in rows:
                    x = row['x']
                    expected = bin(x).count('1') if name.startswith('popcount') else int(x in powers)
                    self.assertEqual(row['r_original'], expected)
                    self.assertEqual(row['r_cached'], 1 if name == 'power_raw_32' and x == 0 else expected)

    def test_engine_drift_blocks_all_discovery(self):
        actual = experiment.engine_hashes()
        changed = dict(actual, **{'tools/find-cond-equiv/new_engine.py': 'unexpected'})
        with patch.object(experiment, 'engine_hashes', return_value=changed), \
                patch.object(experiment.shutil, 'copyfile'), \
                patch.object(experiment, 'find_main') as discover, redirect_stdout(io.StringIO()):
            rc = experiment.main(['--esbmc', 'missing-solver', '--cc', 'missing-cc', '--workdir', str(self.root)])
        discover.assert_not_called()
        report = experiment.read_json(self.root / 'results.json')
        self.assertEqual(rc, 2)
        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['results'], [])
        self.assertFalse(report['identities']['engine_frozen'])

    def test_acceptance_requires_exact_safety_and_postcheck(self):
        summary = {'status': 'EXACT', 'obligations': {'state': {'safety': {'status': 'PROVED'}}}}
        self.assertTrue(experiment.accepted(summary, 0, {'status': 'PROVED'}))
        for status in ('PARTIAL', 'UNKNOWN'):
            changed = copy.deepcopy(summary)
            changed['status'] = status
            self.assertFalse(experiment.accepted(changed, 0, {'status': 'PROVED'}))
        self.assertFalse(experiment.accepted(summary, 2, {'status': 'PROVED'}))
        for match in (None, {'status': 'UNKNOWN'}, {'status': 'REFUTED'}):
            self.assertFalse(experiment.accepted(summary, 0, match))
        summary['obligations']['state']['safety']['status'] = 'UNKNOWN'
        self.assertFalse(experiment.accepted(summary, 0, {'status': 'PROVED'}))

    def test_overview_retains_unknown_and_marks_exploratory(self):
        report = dict(status='INCOMPLETE', passed=0, total=5, results=[dict(
            name='popcount_32', required=False, passed=False,
            summary=dict(status='UNKNOWN', claim={'condition': None}, metrics={'queries': 3, 'elapsed_seconds': 1}))])
        text = experiment.overview(report)
        self.assertIn('UNKNOWN', text)
        self.assertIn('| False |', text)
        self.assertIn('popcount_32/verification-result.json', text)
        self.assertNotIn(str(self.root), text)


if __name__ == '__main__':
    unittest.main()
