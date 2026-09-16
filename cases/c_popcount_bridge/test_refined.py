"""Refined-chain controls; synthetic certificates and native tests are not proofs."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import run_bridge as bridge
import run_refined as refined


class RefinedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = bridge.snapshot(self.root / 'contracts', refined.protocol()['nodes'])
        self.contracts = [bridge.Contract(p) for p in self.paths[:6]]

    def test_refined_scope_and_every_edge_required(self):
        self.assertEqual(len(self.paths), 7)
        self.assertEqual(bridge.default_protocol()['nodes'], bridge.NODES)
        self.assertTrue(bridge.connected(self.contracts, 6))
        self.assertFalse(bridge.connected(self.contracts))
        rows = []
        for i, contract in enumerate(self.contracts):
            self.assertEqual(contract.data['inputs'], bridge.INPUTS)
            summary = dict(schema='conditional-equivalence-result', schema_version=1, producer='finder',
                           status='EXACT', diagnostics=[], scope={'source_identity': contract.identity},
                           claim=dict(condition='true', condition_c='true', relative_to_declared_scope=True),
                           domain={'status': 'NONEMPTY'},
                           obligations={'state': {'safety': {'status': 'PROVED'}},
                                        'sufficiency': {'status': 'PROVED'}, 'complement': {'status': 'PROVED'}})
            rows.append(dict(name=f'edge_{i}', summary=summary, full_domain_certified=True,
                             measurement_valid=True, exit_code=0, full_domain_check={'status': 'PROVED'}))
        identities = {k: True for k in bridge.REQUIRED_IDENTITIES}
        self.assertTrue(bridge.compose(rows, self.contracts, identities, 6))
        self.assertFalse(bridge.compose(rows[:3], self.contracts, identities, 6))
        for index in range(6):
            rows[index]['full_domain_certified'] = False
            self.assertFalse(bridge.compose(rows, self.contracts, identities, 6))
            rows[index]['full_domain_certified'] = True

    def test_mixed_byte_native_results(self):
        rng = random.Random(1)
        values = sorted(set(range(256)) | {2**i for i in range(32)} |
                        {2**32-1, 0xAAAAAAAA, 0x55555555} | {rng.randrange(2**32) for _ in range(256)})
        for path in self.paths[1:5]:
            bound = bridge.baseline.bind_contract(path)
            args = bridge.baseline.parse_args(['--contract', str(path), '--cc', os.environ.get('FINDER_CC', 'cc'),
                                               '--esbmc', 'missing-refined-native-solver'])
            work = self.root / path.stem
            work.mkdir()
            backend = bound(args, work)
            backend.prepare()
            # Test-only bypass for these inspected finite loops, never used by
            # the experiment or as evidence of formal safety/equivalence.
            backend.restore_obligations({'safety': {'status': 'PROVED'}})
            rows = backend.replay([dict(x=x) for x in values])
            self.assertEqual(len(rows), len(values))
            for row in rows:
                expected = bin(row['x']).count('1')
                self.assertEqual(row['r_original'], expected)
                self.assertEqual(row['r_cached'], expected)

    def test_six_edge_protocol_drift_blocks_execution(self):
        changed = bridge.baseline.engine_hashes()
        changed[next(iter(changed))] = 'changed'
        with patch.object(bridge.baseline, 'engine_hashes', return_value=changed), \
                patch.object(bridge, 'execute') as execute, redirect_stdout(io.StringIO()):
            self.assertEqual(refined.main(['--esbmc', 'missing', '--cc', 'missing',
                                           '--workdir', str(self.root / 'run')]), 2)
        execute.assert_not_called()
        report = bridge.baseline.read_json(self.root / 'run/results.json')
        self.assertEqual(report['edge_count'], 6)
        self.assertEqual(report['endpoint_claim']['status'], 'UNKNOWN')
        self.assertEqual(len(report['node_sources']), 7)
        self.assertIn('experiment/REFINED.md', bridge.overview(report))
        self.assertTrue((Path(report['artifacts']) / 'metrics.csv').is_file())

    def test_metrics_preserve_unknown_postcheck(self):
        report = dict(results=[dict(name='edge_3', full_domain_certified=False,
                                    summary={'status': 'EXACT', 'metrics': {'queries': 5, 'elapsed_seconds': 2},
                                             'diagnostics': []},
                                    full_domain_check={'status': 'UNKNOWN', 'reason_code': 'SOLVER_TIMEOUT'})])
        row = list(bridge.metric_rows(report))[0]
        self.assertEqual(row['status'], 'EXACT')
        self.assertFalse(row['full_domain_certified'])
        self.assertEqual(row['post_check'], 'UNKNOWN')
        self.assertEqual(row['post_check_reason'], 'SOLVER_TIMEOUT')


if __name__ == '__main__':
    unittest.main()
