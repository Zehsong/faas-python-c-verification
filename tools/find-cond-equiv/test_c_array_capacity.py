"""Larger fixed buffers and symbolic logical lengths; native checks are not proofs."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agent_conditions import validate_proposal
import agent_workflow as workflow
from c_scalar_contract import Contract, Source
from c_scalar_backend import bind_contract
from find_c_conditions import parse_args
from condition_runner import run

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / 'cases/c_array_capacity'


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def data(self, name='copy8'):
        data = json.loads((CASE / (name + '.json')).read_text())
        for side in ('original','candidate'):
            data[side]['source'] = str(CASE / data[side]['source'])
        return data

    def write(self, data):
        path = self.root/'contract.json'
        path.write_text(json.dumps(data))
        return path

    def backend(self, name):
        bound = bind_contract(CASE/(name+'.json'))
        args = parse_args(['--contract',str(bound.contract.path),'--cc',os.environ.get('FINDER_CC','cc'),
                          '--esbmc','missing-capacity-solver','--workdir',str(self.root/name)])
        directory = self.root/(name+'-backend');directory.mkdir()
        return bound,args,bound(args,directory)

    def test_new_contracts_admitted_with_complete_observations(self):
        for path in CASE.glob('*.json'):
            contract = Contract(path)
            self.assertGreater(len(contract.fields),4)
            self.assertEqual(len(contract.observation_types()),1+sum(s['length'] for s in contract.arrays.values()))
        self.assertEqual(len(Contract(CASE/'tail64.json').fields),65)

    def test_capacity_remains_opt_in_for_legacy_source_and_schema(self):
        with self.assertRaises(ValueError): Source(CASE/'copy_forward.c',array_parameters=True)
        data=self.data();data['schema']=2
        for spec in data['inputs'].values():
            spec.pop('length_field',None);spec.update(min=0,max=1)
        with self.assertRaises(ValueError): Contract(self.write(data))

    def test_capacity_and_total_value_limits(self):
        for length in (0,65,True):
            data=self.data();data['inputs']['src']['length']=length
            with self.subTest(length=length),self.assertRaises(ValueError): Contract(self.write(data))
        data=self.data();data['inputs']['src']['length']=64;data['inputs']['dst']['length']=64
        with self.assertRaisesRegex(ValueError,'128'): Contract(self.write(data))
        source=self.root/'large.c'
        source.write_text('uint32_t f(uint32_t a[64], uint32_t b[64]) { a[63u] = b[63u]; return 0u; }')
        data['inputs'].pop('n')
        for spec in data['inputs'].values(): spec.pop('length_field')
        for side in ('original','candidate'): data[side].update(source=str(source),entry='f',args=['dst','src'])
        self.assertEqual(len(Contract(self.write(data)).fields),128)

    def test_logical_length_must_be_declared_uint_scalar(self):
        for field in ('absent','src','src_0',None,False):
            data=self.data();data['inputs']['src']['length_field']=field
            with self.subTest(field=field),self.assertRaises(ValueError): Contract(self.write(data))
        data=self.data();data['inputs']['n']['type']='bool'
        with self.assertRaises(ValueError): Contract(self.write(data))
        data=self.data();data['inputs']['n']['length_field']='n'
        with self.assertRaises(ValueError): Contract(self.write(data))

    def test_structural_domain_and_report_include_capacity_constraint(self):
        bound,_,backend=self.backend('tail64')
        row={name:0 for name in bound.fields}
        for n in (0,1,64):
            self.assertTrue(bound.seed_in_domain({**row,'n':n},'stateless'))
        self.assertFalse(bound.seed_in_domain({**row,'n':65},'stateless'))
        self.assertEqual(backend.scope['input_domain']['structural_constraints'],['n <= 64'])
        self.assertEqual(backend.scope['memory']['logical_lengths'],{'a':'n'})
        self.assertIn('a[63]',backend.scope['memory']['observation_order'])
        self.assertEqual(backend.scope['inputs']['n']['max'],2**32-1)
        self.assertIn('entire physical capacity',backend.scope['memory']['observation_extent'])

    def test_every_query_retains_logical_domain_and_full_array_equality(self):
        bound,_,backend=self.backend('tail64')
        for kind in ('safety','feasible','equal','different','expected'):
            harness=bound.make_harness(backend.model,'pair','stateless',kind,expected='true')
            self.assertIn('finder_n <= UINT32_C(64)',harness)
            if kind in ('equal','different'):
                self.assertIn('ce_buf_original_a[63]',harness)
                self.assertIn('ce_buf_candidate_a[63]',harness)

    def test_large_preparation_never_enumerates_cartesian_product(self):
        for name in ('tail64','copybits32','copy8'):
            bound,_,_=self.backend(name)
            with patch('c_scalar_backend.itertools.product',side_effect=AssertionError('exponential preparation')):
                seeds=bound.default_seeds('stateless')
            self.assertTrue(0<len(seeds)<=256)
            self.assertLessEqual(len(bound.initial_atoms()),24)
            self.assertTrue(all(bound.seed_in_domain(r,'stateless') for r in seeds))
            if 'n' in bound.fields:
                cap=min(s['length'] for s in bound.contract.arrays.values())
                self.assertEqual({r['n'] for r in seeds},{0,cap//2,cap})

    def test_length_domain_can_be_empty_without_being_rewritten(self):
        bound,args,_=self.backend('empty_length')
        self.assertEqual(bound.default_seeds('stateless'),[])
        self.assertEqual(bound.contract.input_specs['n']['min'],17)
        with patch.object(bound,'prepare'),patch.object(bound,'query',return_value={'status':'PROVED'}):
            run(args,bound)
        summary=json.loads((Path(args.workdir)/'verification-result.json').read_text())
        self.assertEqual(summary['status'],'EMPTY_DOMAIN')
        self.assertIsNone(summary['claim']['condition'])

    def test_native_forward_reverse_copy_for_each_legal_length(self):
        bound,_,backend=self.backend('copy8');backend.prepare()
        backend.restore_obligations({'safety':{'status':'PROVED'}})  # inspected native fixture only
        base={**{f'dst_{i}':100+i for i in range(8)},**{f'src_{i}':i*7 for i in range(8)}}
        results=backend.replay([{**base,'n':n} for n in range(9)])
        for n,row in enumerate(results):
            expected=[n,*[i*7 if i<n else 100+i for i in range(8)],*[i*7 for i in range(8)]]
            self.assertEqual(row['observations_original'],expected)
            self.assertEqual(row['observations_candidate'],expected)

    def test_native_tail_mutation_is_visible_even_when_logical_length_zero(self):
        bound,_,backend=self.backend('tail64');backend.prepare()
        backend.restore_obligations({'safety':{'status':'PROVED'}})  # no solver claim
        base={f'a_{i}':0 for i in range(64)}
        rows=backend.replay([{**base,'n':n} for n in (0,1,64)])
        self.assertEqual(rows[0]['r_original'],rows[0]['r_cached'])
        self.assertNotEqual(rows[0]['observations_original'],rows[0]['observations_candidate'])
        self.assertTrue(all(r['observations_original']==r['observations_candidate'] for r in rows[1:]))
        illegal={**base,'n':65}
        result=subprocess.run([str(backend.executable)],input=' '.join(str(illegal[n]) for n in bound.fields)+'\n',
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,'')

    def test_native_clear_and_mixed_bool_buffers(self):
        for name in ('clear16','conditional16','copybits32'):
            bound,_,backend=self.backend(name);backend.prepare()
            backend.restore_obligations({'safety':{'status':'PROVED'}})  # no solver claim
            seeds=bound.default_seeds('stateless')
            results=backend.replay(seeds)
            self.assertEqual(len(results),len(seeds))
            for row in results:
                self.assertEqual(row['observations_original']==row['observations_candidate'],
                                 row['n']==0 if name=='conditional16' else True)

    def test_agent_length_seed_and_identity_checks(self):
        bound,args,_=self.backend('tail64')
        seed={name:0 for name in bound.fields};seed['n']=65
        proposal=dict(session_id='test',round=1,condition=True,seeds=[seed])
        state=dict(session_id='test',rounds=0,config=dict(case='c'))
        with self.assertRaisesRegex(ValueError,'outside'): validate_proposal(proposal,state,bound,args)
        seed['n']=64
        validate_proposal(proposal,state,bound,args)
        data=self.data('tail64');path=self.write(data)
        config=dict(case='c',contract=str(path),cc=os.environ.get('FINDER_CC','cc'),esbmc='missing-capacity-solver')
        before=workflow.fingerprint(config)
        data['inputs']['a'].pop('length_field');self.write(data)
        self.assertNotEqual(before,workflow.fingerprint(config))


if __name__=='__main__': unittest.main()
