"""Schema 3 domain controls. Mock/native results are not formal certificates."""
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agent_conditions import validate_proposal
import agent_workflow as workflow
from c_input_domain import normalize_bounds
from c_scalar_contract import Contract
from c_scalar_backend import bind_contract
from condition_runner import run
from find_c_conditions import parse_args
from result_contract import validate_summary

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'cases/c_input_domains'


class InputDomainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def data(self, name='ordered_full'):
        data = json.loads((CASE / (name + '.json')).read_text(encoding='utf-8'))
        for side in ('original', 'candidate'):
            data[side]['source'] = str(CASE / data[side]['source'])
        return data

    def contract(self, data):
        path = self.root / 'contract.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return Contract(path)

    def backend(self, name):
        bound = bind_contract(CASE / (name + '.json'))
        args = parse_args(['--contract', str(bound.contract.path), '--cc', os.environ.get('FINDER_CC', 'cc'),
                           '--esbmc', 'missing-domain-test-solver', '--workdir', str(self.root / name)])
        directory = self.root / (name + '-backend')
        directory.mkdir()
        return bound, args, bound(args, directory)

    def test_type_domains_and_partial_bounds(self):
        for spec, expected in (({'type':'uint32_t'}, (0, 2**32-1)),
                               ({'type':'bool'}, (0, 1)),
                               ({'type':'uint32_t','max':7}, (0, 7)),
                               ({'type':'uint32_t','min':7}, (7, 2**32-1))):
            actual = normalize_bounds(spec, defaults=True)
            self.assertEqual((actual['min'], actual['max']), expected)
        for spec in ({'type':'bool','max':2}, {'type':'uint32_t','min':False},
                     {'type':'uint32_t','max':2**32}, {'type':'uint32_t','min':-1}):
            with self.assertRaises(ValueError): normalize_bounds(spec, defaults=True)

    def test_all_new_contracts_and_legacy_contracts_admitted(self):
        for directory in ('c_input_domains', 'c_scalar', 'c_bounded_arrays', 'c_readonly_tables'):
            for path in (ROOT / 'cases' / directory).glob('*.json'):
                if path.stem in ('const_write', 'alias_rejected', 'readonly_write'): continue
                with self.subTest(path=path): Contract(path)

    def test_legacy_schemas_do_not_silently_gain_defaults_or_constraints(self):
        data = self.data()
        for schema in (1, 2):
            data['schema'] = schema
            with self.assertRaises(ValueError): self.contract(data)
        data['schema'] = 1
        del data['constraints']
        with self.assertRaises(ValueError): self.contract(data)

    def test_rejects_undeclared_fields_code_and_unbounded_expression_trees(self):
        invalid = ['n < 3', 'x + y < 9', 'x == 0; abort()', 'valid', 'x', 'r_original == 0',
                   {'all':[]}, {'any':[]}, {'assume':'x == y'}, {'not':True,'all':[True]}]
        deep = True
        for _ in range(15): deep = {'not':deep}
        invalid += [deep, {'all':[True]*130}]
        for constraint in invalid:
            data = self.data(); data['constraints'] = constraint
            with self.subTest(constraint=constraint), self.assertRaises(ValueError): self.contract(data)

    def test_boolean_composition_and_flattened_array_fields(self):
        domain = Contract(CASE / 'mixed_bool.json').domain
        for x, y, enabled in itertools.product(range(3), range(3), (0, 1)):
            self.assertEqual(domain.contains(dict(x=x,y=y,enabled=enabled)),
                             (bool(enabled) and x < y) or (not enabled and x == y))
        array = Contract(CASE / 'array_equal.json').domain
        self.assertTrue(array.contains(dict(a_0=4,a_1=4,n=1,capacity=2)))
        self.assertFalse(array.contains(dict(a_0=4,a_1=5,n=1,capacity=2)))
        self.assertFalse(array.contains(dict(a_0=4,a_1=4,n=2,capacity=2)))

    def test_declared_scope_keeps_raw_and_effective_domain(self):
        bound, _, backend = self.backend('array_index')
        self.assertEqual(backend.scope['adapter'], 'c-domain-v3')
        self.assertEqual(backend.scope['declared_inputs']['n'], {'type':'uint32_t'})
        self.assertEqual(backend.scope['inputs']['n']['max'], 2**32-1)
        self.assertEqual(backend.scope['input_domain']['constraints'], bound.contract.data['constraints'])
        self.assertEqual(backend.scope['observations'], ['return','a'])

    def test_all_obligation_kinds_assume_same_domain_before_program_calls(self):
        bound, _, backend = self.backend('safe_division')
        guard = '__ESBMC_assume(finder_x < finder_y);'
        for kind in ('safety','feasible','equal','different','expected'):
            harness = bound.make_harness(backend.model, 'pair', 'stateless', kind,
                                         'finder_x == 0', expected='true')
            self.assertEqual(harness.count(guard), 1)
            if kind not in ('expected','feasible'):
                self.assertLess(harness.index(guard), harness.index('volatile uint32_t ce_left'))
        self.assertNotIn('finder_x + finder_y', harness)

    def test_empty_seed_set_does_not_establish_empty_domain(self):
        bound, args, _ = self.backend('no_boundary_seed')
        self.assertEqual(bound.default_seeds('stateless'), [])
        self.assertTrue(bound.seed_in_domain(dict(x=7,y=11),'stateless'))
        with patch.object(bound,'prepare'), patch.object(bound,'query',return_value={'status':'UNKNOWN','reason_code':'SOLVER_NOT_FOUND'}):
            run(args, bound)
        summary = validate_summary(json.loads((Path(args.workdir)/'verification-result.json').read_text()))
        self.assertEqual(summary['status'], 'UNKNOWN')
        self.assertEqual(summary['domain']['status'], 'NOT_ESTABLISHED')

    def test_contradiction_is_reported_empty_only_after_solver_evidence(self):
        bound, args, _ = self.backend('empty_relation')
        self.assertEqual(bound.default_seeds('stateless'), [])
        with patch.object(bound,'prepare'), patch.object(bound,'query',return_value={'status':'PROVED'}):
            run(args,bound)
        summary = validate_summary(json.loads((Path(args.workdir)/'verification-result.json').read_text()))
        self.assertEqual(summary['status'],'EMPTY_DOMAIN')
        self.assertIsNone(summary['claim']['condition'])

    def test_native_probe_rejects_outside_domain_before_unsafe_execution(self):
        bound, _, backend = self.backend('safe_division')
        backend.prepare()
        # Native fixture check only; no formal claim or production bypass.
        backend.restore_obligations({'safety':{'status':'PROVED'}})
        rows = backend.replay([dict(x=0,y=1),dict(x=7,y=11),dict(x=2,y=1),dict(x=0,y=0)])
        self.assertEqual([(r['x'],r['y'],r['r_original'],r['r_cached']) for r in rows],[(0,1,0,0),(7,11,0,0)])
        for stdin in ('0 0\n','2 1\n'):
            result = subprocess.run([str(backend.executable)],input=stdin,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,2)
            self.assertEqual(result.stdout,'')

    def test_native_boolean_and_array_constraints_match_python_domain(self):
        for name in ('mixed_bool','array_index','array_equal'):
            bound, _, backend = self.backend(name)
            backend.prepare()
            backend.restore_obligations({'safety':{'status':'PROVED'}})  # native controls only
            seeds = bound.default_seeds('stateless')
            if name=='array_index': seeds=[dict(a_0=7,a_1=9,n=1,capacity=2),dict(a_0=7,a_1=9,n=0,capacity=1)]
            self.assertTrue(seeds)
            observed = backend.replay(seeds)
            self.assertEqual(len(observed),len(seeds))
            self.assertTrue(all(r['r_original']==r['r_cached'] for r in observed))
            if name.startswith('array'):
                self.assertTrue(all(r['observations_original']==r['observations_candidate'] for r in observed))

    def test_native_guard_matches_nested_boolean_semantics_on_all_small_inputs(self):
        bound, _, backend = self.backend('mixed_bool')
        backend.prepare()
        # Direct execution of inspected, total fixture functions; not solver evidence.
        for x,y,enabled in itertools.product(range(3),range(3),(0,1)):
            allowed=bound.contract.domain.contains(dict(x=x,y=y,enabled=enabled))
            result=subprocess.run([str(backend.executable)],input=f'{x} {y} {enabled}\n',
                                  capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0 if allowed else 2)
            self.assertEqual(bool(result.stdout),allowed)

    def test_agent_seeds_cannot_escape_contract_constraints(self):
        bound,args,_ = self.backend('ordered_full')
        state=dict(session_id='test',rounds=0,config=dict(case='c'))
        proposal=dict(session_id='test',round=1,condition=True,seeds=[dict(x=2,y=1)])
        with self.assertRaisesRegex(ValueError,'outside'): validate_proposal(proposal,state,bound,args)
        proposal['seeds']=[dict(x=1,y=2)]
        _, seeds = validate_proposal(proposal,state,bound,args)
        self.assertEqual(seeds,proposal['seeds'])

    def test_constraint_change_invalidates_binding_and_agent_identity(self):
        data=self.data();contract=self.contract(data);bound=bind_contract(contract.path)
        config=dict(case='c',contract=str(contract.path),esbmc='missing-domain-test-solver',cc=os.environ.get('FINDER_CC','cc'))
        old=workflow.fingerprint(config)
        data['constraints']='x >= y';self.contract(data)
        self.assertNotEqual(old,workflow.fingerprint(config))
        with self.assertRaisesRegex(ValueError,'changed'): bound(None,self.root)

    def test_missing_solver_blocks_native_execution_with_constraints(self):
        bound,args,_ = self.backend('safe_division')
        with patch.object(bound,'prepare'), patch.object(bound,'replay') as replay:
            run(args,bound)
        replay.assert_not_called()
        summary=json.loads((Path(args.workdir)/'verification-result.json').read_text())
        self.assertEqual(summary['status'],'UNKNOWN')
        self.assertEqual(summary['metrics']['native_samples'],0)
        self.assertEqual(summary['scope']['input_domain']['constraints'],'x < y')


if __name__=='__main__':
    unittest.main()
