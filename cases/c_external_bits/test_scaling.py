"""Measurement-accounting controls; synthetic reports are not solver proofs."""
from contextlib import redirect_stdout
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_scaling as scaling
from c_scalar_contract import Contract


class ScalingTests(unittest.TestCase):
    def test_balanced_fixed_schedule(self):
        rows = scaling.schedule()
        self.assertEqual(len(rows), 10)
        self.assertEqual([r['width'] for r in rows[:5]], list(scaling.WIDTHS))
        self.assertEqual([r['width'] for r in rows[5:]], list(reversed(scaling.WIDTHS)))
        self.assertEqual(len({r['name'] for r in rows}), 10)
        self.assertEqual(scaling.BUDGET, dict(timeout=30, max_seconds=300, max_queries=96))

    def test_only_domain_and_name_change(self):
        template = scaling.baseline.read_json(scaling.baseline.CASE / 'popcount_32.json')
        original = copy.deepcopy(template)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for side in ('original', 'candidate'):
                name = template[side]['source']
                (root / name).write_bytes((scaling.baseline.CASE / name).read_bytes())
            for width in scaling.WIDTHS:
                data = scaling.contract_for(template, width)
                self.assertEqual(data['inputs']['x']['max'], 2**width - 1)
                path = root / f'b{width}.json'
                scaling.baseline.save_json(path, data)
                Contract(path)
                data['name'] = original['name']
                data['inputs']['x']['max'] = original['inputs']['x']['max']
                self.assertEqual(data, original)
        self.assertEqual(template, original)
        with self.assertRaises(ValueError):
            scaling.contract_for(template, 7)

    def test_timeouts_are_measurements_not_certificates(self):
        summary = dict(status='UNKNOWN', diagnostics=[dict(code='SOLVER_TIMEOUT')], metrics=dict(queries=1))
        query = dict(kind='equal', status='UNKNOWN', timed_out=True)
        self.assertTrue(scaling.measured(summary, 2, [query], None))
        for code in scaling.INFRASTRUCTURE:
            summary['diagnostics'] = [dict(code=code)]
            self.assertFalse(scaling.measured(summary, 2, [query], None))
        summary['diagnostics'] = []
        self.assertFalse(scaling.measured(summary, 0, [query], None))
        self.assertFalse(scaling.measured(summary, 2, [], None))
        self.assertFalse(scaling.measured(summary, 2, [query], dict(status='REFUTED')))

    def test_metrics_preserve_timeout_kinds_and_unknown(self):
        row = dict(name='r1-b32', repeat=1, width=32, measurement_valid=True, full_domain_certified=False,
                   summary=dict(status='UNKNOWN', claim=dict(condition=None), metrics=dict(queries=3, elapsed_seconds=32),
                                diagnostics=[dict(code='SOLVER_TIMEOUT')]),
                   queries=[dict(kind='safety', timed_out=False), dict(kind='equal', timed_out=True),
                            dict(kind='different', status='UNKNOWN', timed_out=False)])
        result = scaling.flatten(row)
        self.assertEqual(result['timeouts'], 1)
        self.assertEqual(result['timeout_kinds'], 'equal')
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertFalse(result['full_domain_certified'])
        self.assertIsNone(result['condition'])

    def test_drift_blocks_run_but_preserves_evidence(self):
        changed = scaling.baseline.engine_hashes()
        changed[next(iter(changed))] = 'changed'
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()), \
                patch.object(scaling.baseline, 'engine_hashes', return_value=changed), \
                patch.object(scaling.baseline, 'find_main') as discover:
            rc = scaling.main(['--esbmc', 'missing-solver', '--cc', 'missing-cc', '--workdir', temp])
            report = scaling.baseline.read_json(Path(temp) / 'results.json')
            discover.assert_not_called()
            self.assertEqual(rc, 2)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual(report['results'], [])
            directory = Path(report['artifacts'])
            self.assertTrue((directory / 'metrics.csv').is_file())
            self.assertTrue((directory / 'schedule.json').is_file())

    def test_overview_distinguishes_recording_from_proofs(self):
        report = dict(status='RECORDED', valid_runs=10, certified=0, results=[], identities={'engine_frozen': True})
        text = scaling.overview(report)
        self.assertIn('0/10', text)
        self.assertIn('metrics.csv', text)
        self.assertIn('engine_frozen=True', text)
        self.assertNotIn('READY', text)


if __name__ == '__main__':
    unittest.main()
