"""Proof composition controls with scripted oracle responses, not formal evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from c_scalar_backend import bind_contract
from condition_runner import run
from find_c_conditions import parse_args

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'cases/c_array_capacity'


class LengthPartitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = []

    def backend(self, name='copy8', **budgets):
        bound = bind_contract(CASE / (name + '.json'))
        args = parse_args(['--contract', str(bound.contract.path), '--esbmc', 'scripted-oracle',
                          '--workdir', str(self.root / 'runs')])
        for key, value in budgets.items():
            setattr(args, key, value)
        directory = self.root / name
        directory.mkdir()
        backend = bound(args, directory)
        backend.esbmc = 'scripted-oracle'
        backend.safety_established = True
        return bound, args, backend

    def oracle(self, statuses):
        sequence = iter(statuses)
        def check(oracle, command, log, timeout, property_name):
            status = next(sequence)
            log.write_text('Scripted protocol control; not a solver execution.\n')
            self.calls.append((Path(command[1]).read_text(), timeout))
            result = dict(status=status, log=str(log), property=property_name,
                          returncode=0 if status == 'PROVED' else 10, timed_out=False)
            if status == 'TIMEOUT':
                result.update(status='UNKNOWN', timed_out=True, returncode=None)
            return result
        return patch('c_backend.check_obligation', side_effect=check)

    def test_all_parts_and_coverage_required_preserve_domain_observations(self):
        _, _, backend = self.backend()
        with self.oracle(['TIMEOUT', 'PROVED', *['PROVED'] * 9]):
            result = backend.query('equal', 'finder_src_0 != UINT32_C(7)', reserve=2)
        self.assertEqual(result['status'], 'PROVED')
        self.assertEqual(result['basis'], 'EXHAUSTIVE_LENGTH_PARTITION')
        self.assertEqual(len(backend.queries), 11)
        self.assertEqual(len(result['checks']), 9)
        self.assertEqual(json.loads(Path(result['evidence_file']).read_text()), result)
        self.assertEqual(result['direct_attempt']['status'], 'UNKNOWN')
        self.assertEqual(result['coverage']['status'], 'PROVED')
        for index, (harness, _) in enumerate(self.calls[2:]):
            self.assertIn(f'finder_n == UINT32_C({index})', harness)
            self.assertIn('finder_n <= UINT32_C(8)', harness)
            self.assertIn('finder_src_0 != UINT32_C(7)', harness)
            self.assertIn('finder_dst_0 <= UINT32_C(4294967295)', harness)
            self.assertIn('ce_buf_original_dst[7]', harness)
            self.assertIn('ce_buf_candidate_src[7]', harness)
        coverage = self.calls[1][0]
        self.assertIn('&& !(', coverage)
        self.assertIn('finder_n == UINT32_C(8)', coverage)

    def test_unknown_part_never_promotes_remaining_parts(self):
        _, _, backend = self.backend()
        with self.oracle(['TIMEOUT', 'PROVED', 'PROVED', 'TIMEOUT']):
            result = backend.query('equal')
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(len(result['checks']), 2)
        self.assertEqual(len(backend.queries), 4)

    def test_refuted_part_refutes_parent_for_both_obligations(self):
        for kind in ('equal', 'different'):
            with self.subTest(kind=kind):
                name = 'copy8' if kind == 'equal' else 'clear16'
                _, _, backend = self.backend(name)
                with self.oracle(['TIMEOUT', 'PROVED', 'REFUTED']):
                    result = backend.query(kind)
                self.assertEqual(result['status'], 'REFUTED')
                self.assertEqual(result['condition_c'], 'true')
                self.assertEqual(len(result['checks']), 1)

    def test_coverage_failure_does_not_prove_or_refute_parent(self):
        for index, status in enumerate(('TIMEOUT', 'REFUTED')):
            _, _, backend = self.backend('copy8' if index == 0 else 'clear16')
            with self.oracle(['TIMEOUT', status]):
                result = backend.query('equal')
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['checks'], [])

    def test_query_reserve_prevents_partial_launch(self):
        _, _, backend = self.backend(max_queries=12)
        with self.oracle(['TIMEOUT']):
            result = backend.query('equal', reserve=2)
        self.assertEqual(result['reason_code'], 'SOLVER_TIMEOUT')
        self.assertEqual(len(backend.queries), 1)
        self.assertNotIn('parts', result)

    def test_wall_budget_applies_during_decomposition(self):
        _, _, backend = self.backend()
        # Initial query, launch gate and coverage execute within budget;
        # then the first part finds the global deadline exhausted.
        with patch.object(backend, 'remaining', side_effect=[100, 100, 100, 100, 100, 0]), \
                self.oracle(['TIMEOUT', 'PROVED']):
            result = backend.query('equal')
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['checks'][0]['reason_code'], 'TIME_BUDGET_EXHAUSTED')
        self.assertEqual(len(backend.queries), 2)

    def test_no_fallback_without_safety_or_on_other_query_kinds(self):
        _, _, backend = self.backend()
        backend.safety_established = False
        with self.oracle(['TIMEOUT']):
            self.assertNotIn('parts', backend.query('equal'))
        backend.safety_established = True
        for kind in ('safety', 'feasible', 'expected'):
            with self.oracle(['TIMEOUT']):
                self.assertNotIn('parts', backend.query(kind, expected='true'))

    def test_direct_success_refutation_and_non_timeout_failure_retained(self):
        _, _, backend = self.backend()
        for status in ('PROVED', 'REFUTED', 'UNKNOWN'):
            with self.oracle([status]):
                result = backend.query('equal')
            self.assertEqual(result['status'], status)
            self.assertNotIn('parts', result)
        self.assertEqual(len(backend.queries), 3)

    def test_no_length_or_excessive_partition_not_enumerated(self):
        for name in ('copybits32', 'tail64'):
            _, _, backend = self.backend(name)
            with self.oracle(['TIMEOUT']):
                self.assertNotIn('parts', backend.query('equal'))
            self.assertEqual(len(backend.queries), 1)

    def test_composed_result_survives_discovery_final_checks_and_summary(self):
        bound, args, _ = self.backend()
        def prepare(backend):
            backend.esbmc = 'scripted-oracle'
        statuses = ['PROVED', 'REFUTED', 'TIMEOUT', 'PROVED', *['PROVED'] * 9,
                    'TIMEOUT', 'PROVED', *['PROVED'] * 9, 'PROVED']
        with patch.object(bound, 'prepare', prepare), patch.object(bound, 'replay', return_value=[]), \
                self.oracle(statuses):
            report = run(args, bound)
        summary = json.loads((Path(args.workdir) / 'verification-result.json').read_text())
        self.assertEqual(report['status'], 'EXACT')
        self.assertEqual(summary['claim']['condition'], 'true')
        self.assertEqual(summary['domain']['status'], 'NONEMPTY')
        self.assertEqual(summary['obligations']['sufficiency']['basis'], 'EXHAUSTIVE_LENGTH_PARTITION')
        self.assertEqual(summary['obligations']['complement']['status'], 'PROVED')
        self.assertEqual(summary['metrics']['queries'], 25)
        self.assertEqual(summary['metrics']['native_samples'], 0)
        self.assertEqual(len(list(Path(report['artifacts']).glob('length-partition-*.json'))), 2)


if __name__ == '__main__':
    unittest.main()
