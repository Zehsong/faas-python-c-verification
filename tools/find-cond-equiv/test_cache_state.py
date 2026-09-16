"""State admission and reporting controls; mocks/native tests are not proofs."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from find_cache_conditions import CacheBackend, parse_args, run
from find_config_conditions import ConfigBackend
from result_contract import build_summary, validate_summary
import agent_workflow as workflow


class CacheStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def backend(self, cls=CacheBackend, name='backend'):
        work = self.root / name
        work.mkdir()
        return cls(parse_args(['--variant', 'good', '--cc', os.environ.get('FINDER_CC', 'cc'),
                               '--esbmc', 'missing-state-test-esbmc']), work)

    def test_gate_requires_both_obligations_and_can_be_revoked(self):
        for cls in (CacheBackend, ConfigBackend):
            backend = self.backend(cls, cls.__name__)
            for evidence in ({}, {'initialization': {'status': 'PROVED'}},
                             {'initialization': {'status': 'PROVED'}, 'preservation': {'status': 'UNKNOWN'}}):
                backend.state_established = True
                backend.restore_obligations(evidence)
                with patch('c_backend.subprocess.run') as native, self.assertRaises(RuntimeError):
                    backend.replay(backend.default_seeds('invariant'))
                native.assert_not_called()
            backend.restore_obligations({name: {'status': 'PROVED'} for name in ('initialization', 'preservation')})
            self.assertTrue(backend.state_established)

    def test_failed_state_check_blocks_samples_and_search(self):
        for cls in (CacheBackend, ConfigBackend):
            for failed in ('init', 'preservation'):
                for status in ('REFUTED', 'UNKNOWN'):
                    args = parse_args(['--variant', 'good', '--workdir', str(self.root)])
                    with patch.object(cls, 'prepare'), patch.object(cls, 'replay') as replay, \
                            patch.object(cls, 'query', side_effect=lambda kind, **kw: {'status': status if kind == failed else 'PROVED'}), \
                            patch('condition_runner.search') as search:
                        report = run(args, cls)
                    replay.assert_not_called()
                    search.assert_not_called()
                    summary = json.loads((Path(report['artifacts']) / 'verification-result.json').read_text(encoding='utf-8'))
                    self.assertEqual(summary['status'], 'UNKNOWN')
                    self.assertEqual(summary['metrics']['native_samples'], 0)
                    self.assertIsNone(summary['claim']['condition'])
                    self.assertIn('STATE_OBLIGATION_NOT_PROVED', {d['code'] for d in summary['diagnostics']})

    def test_missing_solver_blocks_agent_initial_samples(self):
        for case, cls in (('cache', CacheBackend), ('config-cache', ConfigBackend)):
            config = dict(case=case, variant='good', domain=None, state_mode='invariant', goal='exact',
                          esbmc='missing-state-test-esbmc', cc='missing-state-test-cc', timeout=10,
                          max_seconds=60, max_queries=16, max_rounds=2)
            with patch.object(cls, 'prepare'), patch.object(cls, 'replay') as replay:
                session, result = workflow.start(config, self.root)
            replay.assert_not_called()
            self.assertEqual(result['phase'], 'UNKNOWN')
            summary = json.loads((session / 'verification-result.json').read_text(encoding='utf-8'))
            self.assertIn('SOLVER_NOT_FOUND', {d['code'] for d in summary['diagnostics']})

    def test_post_state_values_checked_in_addition_to_flags(self):
        for cls in (CacheBackend, ConfigBackend):
            backend = self.backend(cls, cls.__name__)
            row = dict(x=0, valid=0, key=0, value=0, config=5, cached_config=0,
                       invariant_before=1, invariant_after=1, hit=0,
                       after_valid=1, after_key=0, after_value=1 if cls is CacheBackend else 5,
                       after_cached_config=5)
            backend.validate_trace(row)
            for field in backend.sketch.data['state_fields']:
                missing = dict(row)
                del missing['after_' + field]
                with self.assertRaises(RuntimeError): backend.validate_trace(missing)
                with self.assertRaises(RuntimeError): backend.validate_trace({**row, 'after_' + field: -1})
            with self.assertRaises(RuntimeError): backend.validate_trace({**row, 'after_value': 123})

    def test_missing_required_evidence_cannot_publish_exact(self):
        backend = self.backend()
        report = dict(status='EXACT', scope=backend.scope, condition='true', condition_c='true',
                      final_validation={n: {'status': 'PROVED'} for n in ('sufficiency', 'complement')},
                      state_obligations={'initialization': {'status': 'PROVED'}})
        summary = build_summary(report, samples=[{'x': 0}])
        validate_summary(summary)
        self.assertEqual(summary['status'], 'UNKNOWN')
        self.assertIn('STATE_OBLIGATION_MISSING', {d['code'] for d in summary['diagnostics']})
        report['state_obligations']['preservation'] = {'status': 'PROVED'}
        summary = build_summary(report, samples=[{'x': 0}])
        self.assertEqual(summary['status'], 'EXACT')
        del summary['obligations']['state']['preservation']
        with self.assertRaises(ValueError): validate_summary(summary)

    def test_cache_scope_does_not_claim_byte_or_sequence_equality(self):
        backend = self.backend(ConfigBackend)
        state = backend.scope['state_contract']
        self.assertEqual(state['sequence_equivalence'], 'NOT_CLAIMED')
        self.assertEqual(state['preservation_domain'], 'invariant')
        self.assertEqual(state['call_inputs'], ['x', 'config'])
        self.assertIn('cached_config', state['fields'])
        self.assertNotIn('config', state['fields'])

    @unittest.skipUnless(shutil.which(os.environ.get('FINDER_CC', 'cc')), 'C compiler unavailable')
    def test_native_inputs_reinitialize_private_cache(self):
        for cls in (CacheBackend, ConfigBackend):
            backend = self.backend(cls, cls.__name__)
            backend.prepare()
            # Native-only fixture audit, explicitly bypass formal gate.
            backend.state_established = True
            row = dict(x=7, valid=0, key=0, value=0)
            if cls is ConfigBackend: row.update(config=5, cached_config=0)
            repeated = backend.replay([row, row], repeat=True)
            self.assertEqual(repeated[0], repeated[1])
            self.assertEqual([r['hit'] for r in repeated], [0, 0])
            self.assertEqual(repeated[0]['r_original'], repeated[0]['r_cached'])

    @unittest.skipUnless(shutil.which(os.environ.get('FINDER_CC', 'cc')), 'C compiler unavailable')
    def test_agent_resume_restores_state_gate(self):
        for case, cls in (('cache', CacheBackend), ('config-cache', ConfigBackend)):
            config = dict(case=case, variant='good', domain=None, state_mode='invariant', goal='exact',
                          esbmc='missing-state-test-esbmc', cc=os.environ.get('FINDER_CC', 'cc'), timeout=10,
                          max_seconds=60, max_queries=16, max_rounds=2)
            def query(backend, kind, *args, **kwargs):
                record = dict(status='REFUTED' if kind == 'feasible' else 'PROVED', kind=kind, test_only=True)
                backend.queries.append(record)
                return record
            with patch.object(cls, 'query', query):
                session, started = workflow.start(config, self.root)
                self.assertEqual(started['phase'], 'READY')
                proposal = self.root / 'proposal.json'
                proposal.write_text(json.dumps(dict(session_id=started['session_id'], round=1, condition=True)), encoding='utf-8')
                result = workflow.step(session, proposal)
            self.assertTrue(result['goal_reached'])
            summary = json.loads((session / 'verification-result.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['status'], 'EXACT')  # Mock protocol behavior only.


if __name__ == '__main__':
    unittest.main()
