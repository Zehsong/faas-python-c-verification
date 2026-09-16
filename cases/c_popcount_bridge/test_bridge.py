"""Composition gates and native fixtures; synthetic certificates are not proofs."""
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import run_bridge as bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = bridge.snapshot(self.root / 'contracts')
        self.contracts = [bridge.Contract(p) for p in self.paths[:3]]
        self.identities = {key: True for key in bridge.REQUIRED_IDENTITIES}

    def rows(self):
        # Only tests the composition decision; no file is published as evidence.
        rows = []
        for i, contract in enumerate(self.contracts):
            summary = dict(schema='conditional-equivalence-result', schema_version=1, producer='finder',
                           status='EXACT', diagnostics=[], scope={'source_identity': contract.identity},
                           claim=dict(condition='true', condition_c='true', relative_to_declared_scope=True),
                           domain={'status': 'NONEMPTY'},
                           obligations={'state': {'safety': {'status': 'PROVED'}},
                                        'sufficiency': {'status': 'PROVED'}, 'complement': {'status': 'PROVED'}})
            rows.append(dict(name=f'edge_{i}', summary=summary, full_domain_certified=True,
                             measurement_valid=True, exit_code=0, full_domain_check={'status': 'PROVED'}))
        return rows

    def test_original_endpoints_and_shared_bridges(self):
        self.assertTrue(bridge.endpoints_locked())
        self.assertTrue(bridge.connected(self.contracts))
        self.assertEqual(len(self.paths), 4)
        self.assertEqual(self.contracts[0].sources['original'].data, bridge.NODES[0].read_bytes())
        self.assertEqual(self.contracts[-1].sources['candidate'].data, bridge.NODES[-1].read_bytes())
        for contract in self.contracts:
            self.assertEqual(contract.data['inputs'], bridge.INPUTS)
        with patch.object(bridge.baseline, 'read_json', return_value={'files': {}}):
            self.assertFalse(bridge.endpoints_locked())

    def test_composition_requires_every_edge_and_identity(self):
        rows = self.rows()
        self.assertTrue(bridge.compose(rows, self.contracts, self.identities))
        self.assertFalse(bridge.compose(rows[:2], self.contracts, self.identities))
        self.assertFalse(bridge.compose(rows, self.contracts, dict(self.identities, engine_frozen=False)))
        self.assertFalse(bridge.compose(rows, self.contracts, {}))
        self.assertFalse(bridge.compose(rows[::-1], self.contracts, self.identities))

    def test_partial_unknown_and_failed_postcheck_cannot_compose(self):
        for status in ('PARTIAL', 'UNKNOWN'):
            rows = self.rows()
            rows[1]['summary']['status'] = status
            if status == 'UNKNOWN':
                rows[1]['summary']['claim'].update(condition=None, condition_c=None)
            self.assertFalse(bridge.compose(rows, self.contracts, self.identities))
        for status in ('UNKNOWN', 'REFUTED'):
            rows = self.rows()
            rows[1]['full_domain_check']['status'] = status
            self.assertFalse(bridge.compose(rows, self.contracts, self.identities))

    def test_source_identity_and_safety_are_required(self):
        rows = self.rows()
        rows[1]['summary']['scope']['source_identity'] = {}
        self.assertFalse(bridge.compose(rows, self.contracts, self.identities))
        rows = self.rows()
        rows[1]['summary']['obligations']['state']['safety']['status'] = 'UNKNOWN'
        self.assertFalse(bridge.compose(rows, self.contracts, self.identities))

    def test_negative_control_gates_publication_but_unknown_link_is_recorded(self):
        rows = self.rows()
        self.assertEqual(bridge.outcome(rows, self.contracts, self.identities), (False, False, False))
        control = dict(name='mutant', measurement_valid=True, full_domain_check={'status': 'REFUTED'},
                       summary={'status': 'EXACT', 'claim': {'meaning': 'NO_INPUTS'}})
        rows.append(control)
        self.assertEqual(bridge.outcome(rows, self.contracts, self.identities), (True, True, True))
        control['full_domain_check']['status'] = 'UNKNOWN'
        self.assertEqual(bridge.outcome(rows, self.contracts, self.identities), (False, False, False))
        control['full_domain_check']['status'] = 'REFUTED'
        rows[1]['full_domain_certified'] = False
        self.assertEqual(bridge.outcome(rows, self.contracts, self.identities), (True, False, True))

    def test_domain_gap_and_bridge_gap_rejected(self):
        contracts = [bridge.Contract(p) for p in self.paths[:3]]
        contracts[1].data['inputs']['x']['max'] = 255
        self.assertFalse(bridge.connected(contracts))
        contracts = [bridge.Contract(p) for p in self.paths[:3]]
        contracts[1].sources['original'].data += b'\n/* different bytes */\n'
        self.assertFalse(bridge.connected(contracts))
        contracts = [bridge.Contract(p) for p in self.paths[:3]]
        contracts[-1].data['candidate']['args'] = []
        self.assertFalse(bridge.connected(contracts))

    def test_native_nodes_and_mutant(self):
        rng = random.Random(0)
        values = sorted(set(range(256)) | {2**i for i in range(32)} |
                        {2**32-1, 0xAAAAAAAA, 0x55555555} | {rng.randrange(2**32) for _ in range(256)})
        for path in self.paths:
            bound = bridge.baseline.bind_contract(path)
            args = bridge.baseline.parse_args(['--contract', str(path), '--cc', os.environ.get('FINDER_CC', 'cc'),
                                               '--esbmc', 'missing-bridge-native-solver'])
            directory = self.root / path.stem
            directory.mkdir()
            backend = bound(args, directory)
            backend.prepare()
            # Test-only restoration for reviewed terminating loops; not used by
            # the experiment and never presented as a solver safety proof.
            backend.restore_obligations({'safety': {'status': 'PROVED'}})
            selected = values if path.stem != 'mutant' else list(range(256))
            rows = backend.replay([dict(x=x) for x in selected])
            self.assertEqual(len(rows), len(selected))
            for row in rows:
                expected = bin(row['x']).count('1')
                self.assertEqual(row['r_original'], expected)
                self.assertEqual(row['r_cached'], expected + (path.stem == 'mutant'))


if __name__ == '__main__':
    unittest.main()
