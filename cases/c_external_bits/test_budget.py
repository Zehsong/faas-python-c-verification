"""Check that timeout is the only budget factor and old schedule is preserved."""
import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_budget
import run_scaling as scaling


class BudgetTests(unittest.TestCase):
    def test_timeout_schedule_and_original_protocol(self):
        protocol = run_budget.protocol()
        self.assertEqual([r['query_timeout'] for r in protocol['rows']], [30, 120, 120, 30])
        self.assertEqual([r['repeat'] for r in protocol['rows']], [1, 1, 2, 2])
        self.assertEqual({r['width'] for r in protocol['rows']}, {32})
        self.assertEqual(scaling.default_protocol()['rows'], scaling.schedule())
        self.assertEqual(len(scaling.schedule()), 10)
        self.assertTrue(all('query_timeout' not in r for r in scaling.schedule()))

    def test_only_timeout_argument_changes(self):
        args = argparse.Namespace(esbmc='modified-esbmc', cc='cc')
        commands = []
        for row in run_budget.protocol()['rows']:
            command = scaling.invocation('same-contract.json', 'same-work', args, row)
            values = dict(zip(command[::2], command[1::2]))
            self.assertEqual(values.pop('--timeout'), str(row['query_timeout']))
            self.assertEqual(values['--max-seconds'], '300')
            self.assertEqual(values['--max-queries'], '96')
            self.assertNotIn('--hypotheses', values)
            commands.append(values)
        self.assertTrue(all(c == commands[0] for c in commands))
        old = scaling.invocation('same-contract.json', 'same-work', args, scaling.schedule()[0])
        self.assertEqual(old[old.index('--timeout')+1], '30')

    def test_drift_reports_four_run_denominator_and_new_guide(self):
        changed = scaling.baseline.engine_hashes()
        changed[next(iter(changed))] = 'changed'
        with tempfile.TemporaryDirectory() as temp, redirect_stdout(io.StringIO()), \
                patch.object(scaling.baseline, 'engine_hashes', return_value=changed), \
                patch.object(scaling.baseline, 'find_main') as discover:
            self.assertEqual(run_budget.main(['--esbmc', 'missing', '--cc', 'missing', '--workdir', temp]), 2)
            discover.assert_not_called()
            report = scaling.baseline.read_json(Path(temp) / 'results.json')
            self.assertEqual(report['total'], 4)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual(report['label'], 'POPCOUNT BUDGET')
            self.assertIn('0/4', scaling.overview(report))
            self.assertIn('inputs/BUDGET.md', scaling.overview(report))
            self.assertEqual({r['width'] for r in report['plan']['schedule']}, {32})


if __name__ == '__main__':
    unittest.main()
