"""Showcase assembly controls. All synthetic certificates are test-only mocks."""
import contextlib
import copy
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import run_showcase as demo
from c_scalar_contract import Contract
from c_scalar_backend import bind_contract
from find_c_conditions import parse_args as scalar_args
from result_contract import build_summary, write_summary


class ShowcaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.summary = dict(scope=dict(inputs={n: dict(type='uint32_t', min=0, max=3) for n in ('a_0', 'a_1')},
                                       return_type='uint32_t', memory=dict(arrays={'a': dict(type='uint32_t[]', length=2)},
                                                                        observation_order=['return', 'a[0]', 'a[1]'])),
                            obligations=dict(state=dict(safety=dict(status='PROVED'))))
        self.query = dict(kind='equal', status='REFUTED', witness=dict(a_0=0, a_1=1),
                          native_replay=dict(a_0=0, a_1=1, r_original=0, r_cached=0,
                                             observations_original=[0, 1, 0], observations_candidate=[0, 0, 1]))

    def test_same_return_different_array_is_a_counterexample(self):
        witness = demo.array_counterexample(self.summary, [dict(kind='safety'), self.query])
        self.assertEqual(witness['original_return'], witness['candidate_return'])
        self.assertNotEqual(witness['original_observations'], witness['candidate_observations'])
        self.assertEqual(witness['query_directory'], 'query-001-equal')

    def test_missing_mismatched_or_unreplayed_witness_is_rejected(self):
        for changes in (dict(status='UNKNOWN'), dict(kind='feasible'), dict(witness=None),
                        dict(native_replay='unavailable'), dict(witness=dict(a_0=1, a_1=1)),
                        dict(witness=dict(a_0=False, a_1=1))):
            self.assertIsNone(demo.array_counterexample(self.summary, [{**self.query, **changes}]))

    def test_complete_typed_observation_and_safety_are_required(self):
        for changed in ([0], [0, 0, 1], [0, 4, -1], [0, True, 1], [1, 1, 0], None):
            q = copy.deepcopy(self.query)
            q['native_replay']['observations_original'] = changed
            self.assertIsNone(demo.array_counterexample(self.summary, [q]))
        for status in ('UNKNOWN', 'REFUTED', 'NOT_CHECKED', 'INVALIDATED'):
            s = copy.deepcopy(self.summary)
            s['obligations']['state']['safety']['status'] = status
            self.assertIsNone(demo.array_counterexample(s, [self.query]))

    def test_snapshot_pairs_preserve_contract_and_bodies(self):
        for case in demo.CASES:
            if not case.get('fixture'): continue
            source = demo.ROOT / 'cases' / case['fixture']
            before = Contract(source)
            path = demo.snapshot_pair(source, self.root / case['name'])
            after = Contract(path)
            self.assertEqual(before.data['inputs'], after.data['inputs'])
            self.assertEqual(before.data['observations'], after.data['observations'])
            for side in ('original', 'candidate'):
                self.assertEqual(before.sources[side].data, after.sources[side].data)
            with self.assertRaises(FileExistsError): demo.snapshot_pair(source, path.parent)

    def test_cache_snapshot_is_used_for_model_and_harness(self):
        for family in ('cache', 'config-cache'):
            backend_type = demo.snapshot_cache(family, self.root / (family + '-inputs'))
            work = self.root / family
            work.mkdir()
            settings = demo.cache_args(['--variant', 'good'])
            backend = backend_type(settings, work)
            self.assertEqual(backend.model_bytes, (backend_type.case / 'cache_model.h').read_bytes())
            self.assertEqual(backend.scope['state_contract']['sequence_equivalence'], 'NOT_CLAIMED')
            self.assertEqual(backend.make_harness('', 'good', 'invariant', 'init'), backend.sketch.render('', 'good', 'invariant', 'init'))

    def test_unknown_must_be_the_requested_budget_failure(self):
        case = demo.CASES[-1]
        summary = dict(status='UNKNOWN', claim=dict(condition=None), metrics=dict(queries=4),
                       diagnostics=[dict(code='QUERY_BUDGET_EXHAUSTED')],
                       obligations=dict(state=dict(safety=dict(status='PROVED'))))
        self.assertTrue(demo.expectation_met(case, summary, 2))
        for change in (dict(diagnostics=[dict(code='SOLVER_NOT_FOUND')]), dict(metrics=dict(queries=0)),
                       dict(obligations=dict(state=dict(safety=dict(status='UNKNOWN'))))):
            self.assertFalse(demo.expectation_met(case, {**summary, **change}, 2))

    def fake_run(self, settings, backend_type):
        """Exercise positive assembly paths without executing or claiming proofs."""
        work = Path(settings.workdir)
        artifact = work / 'mock-run'
        artifact.mkdir()
        backend = backend_type(settings, artifact)
        name = work.name
        condition = {'scalar-all': 'true', 'prime-lookup': 'n != 9', 'array-swap': 'a_0 == a_1',
                     'cache-miss': 'valid', 'config-cache': 'config == cached_config',
                     'no-equal-inputs': 'false', 'budget-limited': None}[name]
        states = backend.scope.get('required_state_obligations', ['safety'])
        report = dict(status='UNKNOWN' if condition is None else 'EXACT', scope=backend.scope,
                      state_obligations={k: dict(status='PROVED', basis='TEST_ONLY_MOCK') for k in states},
                      final_validation={k: dict(status='PROVED', basis='TEST_ONLY_MOCK') for k in ('sufficiency', 'complement')},
                      condition=condition, condition_c=condition, artifacts=str(artifact), queries_used=4)
        if condition is None: report.update(reason_code='QUERY_BUDGET_EXHAUSTED', reason='Mock budget control')
        summary = build_summary(report, samples=[{'mock_input': 0}])
        write_summary(work, summary)
        demo.save_json(artifact / 'queries.json', [self.query] if name == 'array-swap' else [])
        if name == 'array-swap':
            query_dir = artifact / 'query-000-equal'
            query_dir.mkdir()
            (query_dir / 'verify.log').write_text('TEST-ONLY MOCK, NOT A SOLVER RUN', encoding='utf-8')
            demo.save_json(query_dir / 'result.json', self.query)
        return report

    def fake_find(self, command):
        settings = scalar_args(command)
        report = self.fake_run(settings, bind_contract(settings.contract))
        return 0 if report['status'] == 'EXACT' else 2

    def test_complete_assembly_portable_links_and_drift_gate(self):
        for drift in (False, True):
            root = self.root / str(drift)
            call_count = 0
            def identity(command):
                nonlocal call_count
                call_count += 1
                return dict(requested=command, path=None, sha256='changed' if drift and call_count > 2 else 'stable')
            with patch.object(demo, 'find_main', self.fake_find), patch.object(demo, 'cache_run', self.fake_run), \
                    patch.object(demo, 'binary_identity', identity), contextlib.redirect_stdout(io.StringIO()):
                rc = demo.main(['--esbmc', 'missing-test-solver', '--workdir', str(root)])
            self.assertEqual(rc, 2 if drift else 0)
            result = demo.read_json(root / 'results.json')
            self.assertEqual(result['passed'], 8)
            self.assertEqual(result['ready'], not drift)
            self.assertTrue(result['engine_unchanged'])
            directory = Path(result['artifacts'])
            text = (directory / 'README.md').read_text(encoding='utf-8')
            for target in re.findall(r'\]\(([^)]+)\)', text):
                self.assertTrue((directory / target).is_file(), target)
            self.assertIn('n != 9', text)
            self.assertIn('initialization: PROVED', text)
            self.assertIn('无认证条件', text)

    def test_assembly_errors_never_report_ready_or_invent_conditions(self):
        with patch.object(demo, 'find_main', side_effect=OSError('test input unavailable')), \
                patch.object(demo, 'cache_run', side_effect=OSError('test input unavailable')), contextlib.redirect_stdout(io.StringIO()):
            rc = demo.main(['--esbmc', 'missing-test-solver', '--workdir', str(self.root)])
        self.assertEqual(rc, 2)
        result = demo.read_json(self.root / 'results.json')
        self.assertEqual(result['passed'], 0)
        text = (Path(result['artifacts']) / 'README.md').read_text(encoding='utf-8')
        self.assertIn('test input unavailable', text)
        self.assertIn('DEMO_ERROR', text)
        self.assertNotIn('本次认证条件：', text)


if __name__ == '__main__':
    unittest.main()
