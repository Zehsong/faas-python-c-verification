#!/usr/bin/env python3
"""Configurable array capacity acceptance; expected formulas are post-checks only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/find-cond-equiv'))
from c_backend import save_json
from c_scalar_backend import bind_contract
from find_c_conditions import main as find_main, parse_args
from result_contract import validate_summary
import agent_workflow as workflow


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def snapshot_engine(identity, destination):
    for relative in identity['files']:
        key = Path(relative)
        path = ROOT / key
        if key.parts and key.parts[0] == 'tools' and path.is_file():
            target = destination / key
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/c-array-capacity')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='checks-', dir=root))
    snapshots = directory / 'acceptance-inputs'
    snapshots.mkdir()
    for path in CASE.iterdir():
        if path.is_file(): shutil.copyfile(path, snapshots / path.name)
    source_paths = [p for p in CASE.iterdir() if p.is_file()]
    snapshot_paths = [p for p in snapshots.iterdir() if p.is_file()]
    before_inputs = file_hashes([*source_paths, *snapshot_paths])
    config = dict(case='c',contract=str(snapshots/'tail64.json'),variant='pair',state_mode='stateless',
                  domain=None,goal='exact',esbmc=args.esbmc,cc=args.cc,timeout=30,
                  max_seconds=300,max_queries=96,max_rounds=3)
    before = workflow.fingerprint(config)
    snapshot_engine(before, directory / 'engine')
    results=[]

    def record(name, passed, **details):
        results.append(dict(name=name,passed=bool(passed),**details))
        print(f"{name}: {'PASS' if passed else 'NOT ESTABLISHED'}",flush=True)

    cases=[('copy8','true',None),('clear16','true',None),('empty_prefix','true',None),
           ('conditional16','finder_n == 0',None),('tail64','finder_n != 0',None),
           ('copybits32','true',None),('empty_length',None,'EMPTY_DOMAIN'),
           ('unsafe_index',None,'SAFETY_OR_OTHER_PROPERTY_FAILURE'),
           ('short_unwind',None,'UNWINDING_INCOMPLETE'),
           ('missing-solver',None,'SOLVER_NOT_FOUND')]
    for name,expected,code in cases:
        contract=snapshots/('tail64.json' if name=='missing-solver' else name+'.json')
        work=directory/name
        command=['--contract',str(contract),'--esbmc','intentionally-missing-capacity-esbmc' if name=='missing-solver' else args.esbmc,
                 '--cc',args.cc,'--max-queries','96','--max-seconds','300','--workdir',str(work)]
        print(f'\n{name}',flush=True)
        rc=find_main(command)
        save_json(work/'invocation.json',[sys.executable,str(ROOT/'tools/find-cond-equiv/find_c_conditions.py'),*command])
        summary=validate_summary(read(work/'verification-result.json'))
        match=None
        if expected is not None:
            passed=rc==0 and summary['status']=='EXACT'
            if passed:
                checkdir=Path(summary['artifacts']['directory'])/'expected-condition-check'
                checkdir.mkdir()
                backend=bind_contract(contract)(parse_args(command),checkdir)
                backend.prepare()
                match=backend.query('expected',summary['claim']['condition_c'],expected=expected)
                passed=match['status']=='PROVED'
        elif code=='EMPTY_DOMAIN':
            passed=(rc==2 and summary['status']=='EMPTY_DOMAIN' and summary['domain']['status']=='EMPTY'
                    and summary['claim']['condition'] is None and summary['metrics']['native_samples']==0)
        else:
            passed=(rc==2 and summary['status']=='UNKNOWN' and summary['claim']['condition'] is None
                    and summary['metrics']['native_samples']==0 and code in {d['code'] for d in summary['diagnostics']})
            if name in ('unsafe_index','short_unwind'):
                safety=summary['obligations']['state'].get('safety',{}).get('details',{})
                passed=passed and safety.get('returncode') not in (None,0) and not safety.get('timed_out') and bool(safety.get('violation'))
            else:
                passed=passed and summary['metrics']['queries']==0
        bound=bind_contract(contract)
        passed=(passed and summary['scope']['adapter']=='c-domain-v3'
                and summary['scope']['input_domain']['constraints']==bound.contract.data.get('constraints',True)
                and summary['scope']['inputs']==bound.contract.input_specs
                and summary['scope']['input_domain']['structural_constraints']==bound.contract.structural_constraints
                and summary['scope']['memory']['logical_lengths']==bound.contract.logical_lengths
                and len(summary['scope']['memory']['observation_order'])==len(bound.contract.observation_types()))
        record(name,passed,summary=summary,exit_code=rc,expected_condition=expected,expected_condition_check=match)

    session,started=workflow.start(config,directory/'agent-capacity')
    rejected=None
    if started['phase']=='READY':
        proposal=directory/'proposal.json'
        seed={name:0 for name in bind_contract(config['contract']).fields}
        seed['n']=65
        save_json(proposal,dict(session_id=started['session_id'],round=1,condition=True,seeds=[seed]))
        rejected=workflow.step(session,proposal)
        seed['n']=1
        save_json(proposal,dict(session_id=started['session_id'],round=2,condition='n != 0',seeds=[seed]))
        workflow.step(session,proposal)
    summary=validate_summary(read(session/'verification-result.json'))
    passed=(rejected is not None and rejected['latest_feedback']['status']=='REJECTED'
            and rejected['queries_used']==started['queries_used'] and summary['status']=='EXACT'
            and summary['scope']['input_domain']['structural_constraints']==['n <= 64'])
    record('agent-capacity',passed,rejected_outside_domain_seed=rejected,summary=summary)
    after=workflow.fingerprint(config)
    unchanged=before==after and before_inputs==file_hashes([*source_paths,*snapshot_paths])
    report=dict(passed=sum(row['passed'] for row in results),total=len(results),results=results,
                inputs_tools_unchanged=unchanged,identity_before=before,identity_after=after,
                input_hashes_before=before_inputs,artifacts=str(directory),
                provenance='Executed capacity/length acceptance; expected formulas checked after discovery; agent proposals scripted, not autonomous performance')
    save_json(directory/'results.json',report)
    save_json(root/'results.json',report)
    lines=['# C array capacity acceptance','',
           f"Checks: {report['passed']}/{report['total']}; inputs/tools unchanged={unchanged}.",'',
           'Each condition is relative to type bounds, user constraints AND explicit logical-length capacity bounds.',
           'All physical elements remain observed, including inactive tails. Unsafe accesses/unwinding must fail; empty length domains give EMPTY_DOMAIN.',
           'Expected conditions are checked separately, never supplied to discovery. The agent control is scripted.','',
           '| Case | Check | Outcome | Report |','|---|---|---|---|']
    for row in results:
        link=Path(row['summary']['artifacts']['directory']).relative_to(directory).as_posix()+'/report.md'
        lines.append(f"| {row['name']} | {'PASS' if row['passed'] else 'NOT ESTABLISHED'} | {row['summary']['status']} | [report]({link}) |")
    (directory/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"C ARRAY CAPACITY ACCEPTANCE: {report['passed']}/{report['total']} passed; inputs/tools unchanged={unchanged}")
    print(f'Open overview: {directory / "README.md"}')
    return 0 if report['passed']==report['total'] and unchanged else 2


if __name__=='__main__':
    sys.exit(main())
