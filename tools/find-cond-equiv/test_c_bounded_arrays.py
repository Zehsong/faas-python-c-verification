"""Bounded array admission, observation and native tests; no formal proof claim."""
import copy
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from c_scalar_contract import Contract, Source
from c_scalar_backend import bind_contract
from find_c_conditions import parse_args
from c_backend import witness_from_log
from predicate_search import observations_equal, entropy
from agent_conditions import parse_condition
import agent_workflow as workflow

CASE = Path(__file__).resolve().parents[2] / 'cases/c_bounded_arrays'


class ArrayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, body, enabled=True):
        path = self.root / 'source.c'
        path.write_text(body, encoding='utf-8')
        return Source(path, array_parameters=enabled)

    def backend(self, name):
        path = CASE / (name + '.json')
        bound = bind_contract(path)
        args = parse_args(['--contract', str(path), '--cc', os.environ.get('FINDER_CC', 'cc'),
                           '--esbmc', 'missing-array-test-solver'])
        directory = self.root / name
        directory.mkdir()
        return bound(args, directory)

    def native(self, name, rows):
        backend = self.backend(name)
        backend.prepare()
        # TEST ONLY: known safe fixtures; this bypass never establishes a proof.
        backend.restore_obligations({'safety': {'status': 'PROVED'}})
        return backend, backend.replay(rows)

    def test_array_parameters_require_opt_in_and_keep_bounds_types(self):
        body = 'uint32_t f(const uint32_t a[2], bool b[1]) { b[0u] = true; return a[0u]; }'
        with self.assertRaises(ValueError):
            self.source(body, enabled=False)
        source = self.source(body)
        self.assertEqual(source.signatures['f'], ('uint32_t', [('array','uint32_t',2,True), ('array','bool',1,False)]))
        self.assertIn(body, source.namespaced('original'))

    def test_rejects_pointer_decay_array_forwarding_and_const_writes(self):
        bodies = [
            'uint32_t f(uint32_t *a) { return a[0u]; }',
            'uint32_t f(uint32_t a[]) { return a[0u]; }',
            'uint32_t f(uint32_t n, uint32_t a[n]) { return a[0u]; }',
            'uint32_t f(uint32_t a[5]) { return a[0u]; }',
            'uint32_t f(uint32_t a[static 2]) { return a[0u]; }',
            'uint32_t f(uint32_t a[2][2]) { return 0u; }',
            'uint32_t f(const uint32_t a[2]) { a[0u] = 0u; return 0u; }',
            'uint32_t f(uint32_t a[2]) { return (uint32_t)a; }',
            'uint32_t f(uint32_t a[2]) { return (uint32_t)&a[0u]; }',
            'uint32_t f(uint32_t a[2]) { a = a; return 0u; }',
            'uint32_t f(uint32_t a[2]) { a[0u] = true; return 0u; }',
            'uint32_t f(uint32_t a[2]) { a[a[0u]++] = 0u; return 0u; }',
            'uint32_t g(uint32_t a[2]) { return a[0u]; } uint32_t f(uint32_t b[2]) { return g(b); }',
        ]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.source(body)

    def test_contract_flattening_observations_and_rejections(self):
        data = json.loads((CASE / 'copy_reverse.json').read_text(encoding='utf-8'))
        for side in ('original','candidate'):
            data[side]['source'] = str(CASE / data[side]['source'])
        path = self.root / 'contract.json'
        def load(value):
            path.write_text(json.dumps(value), encoding='utf-8')
            return Contract(path)
        self.assertEqual(load(data).fields, ('src_0','src_1','dst_0','dst_1'))
        for change in ('schema', 'observation', 'alias', 'length', 'overflow', 'collision'):
            value = copy.deepcopy(data)
            if change == 'schema': value['schema'] = 1
            if change == 'observation': value['observations'] = ['return','dst']
            if change == 'alias': value['candidate']['args'] = ['src','src']
            if change == 'length': value['inputs']['src']['length'] = 1
            if change == 'overflow': value['inputs']['src']['length'] = 3
            if change == 'collision': value['inputs']['src_0'] = dict(type='uint32_t',min=0,max=1)
            with self.subTest(change=change), self.assertRaises(ValueError): load(value)

    def test_harness_copies_and_full_observation_comparison(self):
        backend = self.backend('swap')
        harness = backend.make_harness(backend.model, 'pair','stateless','equal')
        self.assertIn('ce_buf_original_a[2] = {finder_a_0, finder_a_1}', harness)
        self.assertIn('ce_buf_candidate_a[2] = {finder_a_0, finder_a_1}', harness)
        self.assertIn('ce_original_transform(ce_buf_original_a)', harness)
        self.assertIn('ce_candidate_transform(ce_buf_candidate_a)', harness)
        self.assertIn('(ce_buf_original_a[1] == ce_buf_candidate_a[1])', harness)
        self.assertIn('(ce_left == ce_right)', harness)
        self.assertEqual(backend.scope['memory']['entry_field_mapping']['a_1'], 'a[1]')
        self.assertEqual(witness_from_log('finder_a_0 = 1\nfinder_a_1 = 2\n', backend.fields), dict(a_0=1,a_1=2))

    def test_native_swap_detects_different_arrays_with_equal_returns(self):
        backend, rows = self.native('swap', [dict(a_0=a,a_1=b) for a,b in itertools.product(range(4),repeat=2)])
        for r in rows:
            self.assertEqual((r['r_original'],r['r_cached']), (0,0))
            self.assertEqual(r['observations_original'], [0,r['a_1'],r['a_0']])
            self.assertEqual(r['observations_candidate'], [0,r['a_0'],r['a_1']])
            self.assertEqual(observations_equal(r), r['a_0']==r['a_1'])
        self.assertGreater(entropy(rows), 0)
        with patch.object(backend,'query') as query:
            result = workflow.check_candidate(backend, parse_condition(True,backend.atom_type), 'exact')
        self.assertEqual(result['status'],'REFUTED')
        query.assert_not_called()

    def test_independent_memory_and_repeated_inputs_native(self):
        backend, rows = self.native('increment', [dict(a_0=1,a_1=3)])
        self.assertEqual(rows[0]['observations_original'], [0,2,4])
        self.assertEqual(rows[0]['observations_candidate'], [0,2,4])
        again = backend.replay([dict(a_0=1,a_1=3)],repeat=True)
        self.assertEqual(rows,again)

    def test_two_arrays_and_const_source_native(self):
        _, rows = self.native('copy_reverse', [dict(zip(('src_0','src_1','dst_0','dst_1'),v))
                                               for v in itertools.product(range(2),repeat=4)])
        for r in rows:
            self.assertEqual(r['observations_original'], [0,r['src_0'],r['src_1'],r['src_0'],r['src_1']])
            self.assertEqual(r['observations_candidate'], [0,r['src_0'],r['src_1'],r['src_1'],r['src_0']])
            self.assertEqual(observations_equal(r),r['src_0']==r['src_1'])

    def test_return_is_still_observed(self):
        _, rows = self.native('return_mutant',[dict(a_0=0,a_1=1)])
        self.assertFalse(observations_equal(rows[0]))
        self.assertEqual(rows[0]['observations_original'][1:],rows[0]['observations_candidate'][1:])

    def test_vector_shape_type_and_return_consistency(self):
        backend = self.backend('swap')
        row = dict(r_original=0,r_cached=0,observations_original=[0,1,2],observations_candidate=[0,1,2])
        backend.validate_trace(row)
        for value in (None, [], [0,1], [1,1,2], [0,True,2], [0,2**32,0]):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                backend.validate_trace({**row,'observations_original':value})
        with self.assertRaises(ValueError): observations_equal(dict(observations_original=[0]))
        self.assertTrue(observations_equal(dict(r_original=7,r_cached=7)))

    def test_bool_array_and_scalar_binding_native(self):
        source = self.root / 'bool.c'
        source.write_text('bool transform(bool a[2], bool enabled) { a[0u] = enabled; a[1u] = !a[1u]; return a[0u]; }',encoding='utf-8')
        data = dict(schema=2,name='bool_array',
                    original=dict(source='bool.c',entry='transform',args=['a','enabled']),
                    candidate=dict(source='bool.c',entry='transform',args=['a','enabled']),
                    inputs=dict(a=dict(type='bool[]',length=2,min=0,max=1),enabled=dict(type='bool',min=0,max=1)),
                    return_type='bool',observations=['return','a'],unwind=4)
        path = self.root / 'contract.json'
        path.write_text(json.dumps(data),encoding='utf-8')
        bound = bind_contract(path)
        args = parse_args(['--contract',str(path),'--cc',os.environ.get('FINDER_CC','cc'),'--esbmc','missing-array-test-solver'])
        backend = bound(args,self.root)
        backend.prepare()
        backend.restore_obligations({'safety':{'status':'PROVED'}})  # native-only test
        rows = backend.replay([dict(a_0=a,a_1=b,enabled=e) for a,b,e in itertools.product(range(2),repeat=3)])
        for row in rows:
            self.assertEqual(row['observations_original'],[row['enabled'],row['enabled'],1-row['a_1']])
            self.assertTrue(observations_equal(row))
        bad = {**rows[0],'observations_candidate':[0,2,0]}
        with self.assertRaises(RuntimeError): backend.validate_trace(bad)
        self.assertTrue(bound.atom_type.parse('a_0').evaluate(dict(a_0=1)))

    def test_input_names_cannot_collide_with_observation_metadata(self):
        data = json.loads((CASE / 'swap.json').read_text(encoding='utf-8'))
        for name in ('r_original','r_cached','observations_original','observations_candidate'):
            changed = copy.deepcopy(data)
            changed['inputs'][name] = dict(type='uint32_t',min=0,max=1)
            path = self.root / 'collision.json'
            path.write_text(json.dumps(changed),encoding='utf-8')
            with self.subTest(name=name), self.assertRaises(ValueError): Contract(path)

    def test_no_native_execution_without_safety(self):
        backend = self.backend('unsafe_index')
        with patch('c_backend.subprocess.run') as execute, self.assertRaisesRegex(RuntimeError,'safety'):
            backend.replay([dict(a_0=0,a_1=0,i=2)])
        execute.assert_not_called()

    def test_solver_witness_uses_array_observations(self):
        backend = self.backend('swap')
        backend.esbmc = 'mock-only-esbmc'
        def oracle_check(oracle,command,log,timeout,property_name):
            Path(log).write_text('finder_a_0 = 0\nfinder_a_1 = 1\n',encoding='utf-8')
            return dict(status='REFUTED',returncode=1,timed_out=False)
        row = dict(a_0=0,a_1=1,r_original=0,r_cached=0,
                   observations_original=[0,1,0],observations_candidate=[0,0,1])
        with patch('c_backend.check_obligation',oracle_check), patch.object(backend,'replay',return_value=[row]):
            self.assertEqual(backend.query('equal')['status'],'REFUTED')
            self.assertEqual(backend.query('different')['status'],'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
