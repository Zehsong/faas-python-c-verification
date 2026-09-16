#!/usr/bin/env python3
"""M3 first slice: generic C local constant tables, with real backend controls.

Expected formulas are checked only after discovery, never supplied as proposals.
The agent case is a scripted integration check, not autonomous performance.
"""
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/c-readonly-tables')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='checks-', dir=root))
    snapshots = directory / 'acceptance-inputs'
    snapshots.mkdir()
    for path in CASE.iterdir():
        if path.suffix in ('.py', '.c', '.json', '.sh', '.md'):
            shutil.copyfile(path, snapshots / path.name)
    results = []

    def record(name, passed, **details):
        results.append(dict(name=name, passed=bool(passed), **details))
        print(f"{name}: {'PASS' if passed else 'NOT ESTABLISHED'}", flush=True)

    truncated = ' && '.join(f'(finder_n != {n}u)' for n in (37, 41, 43, 47, 53, 59, 61))
    cases = [('full_31', 'true', None), ('fallback_63', 'true', None),
             ('truncated_63', truncated, None), ('mutant_31', 'finder_n != 9u', None),
             ('unsafe_index', None, 'SAFETY_OR_OTHER_PROPERTY_FAILURE'),
             ('short_unwind', None, 'UNWINDING_INCOMPLETE'),
             ('readonly_write', None, 'UNSUPPORTED_INPUT'),
             ('missing-solver', None, 'SOLVER_NOT_FOUND')]
    for name, expected, code in cases:
        work = directory / name
        contract = snapshots / ('full_31.json' if name == 'missing-solver' else name + '.json')
        command = ['--contract', str(contract), '--esbmc',
                   'intentionally-missing-table-esbmc' if name == 'missing-solver' else args.esbmc,
                   '--cc', args.cc, '--max-queries', '160', '--max-seconds', '600', '--workdir', str(work)]
        print(f'\n{name}', flush=True)
        rc = find_main(command)
        save_json(work / 'invocation.json', [sys.executable, str(ROOT / 'tools/find-cond-equiv/find_c_conditions.py'), *command])
        summary = validate_summary(json.loads((work / 'verification-result.json').read_text(encoding='utf-8')))
        match = None
        if expected is not None:
            passed = rc == 0 and summary['status'] == 'EXACT'
            if passed:
                checkdir = Path(summary['artifacts']['directory']) / 'expected-condition-check'
                checkdir.mkdir()
                settings = parse_args(command)
                backend = bind_contract(contract)(settings, checkdir)
                backend.prepare()
                match = backend.query('expected', summary['claim']['condition_c'], expected=expected)
                passed = match['status'] == 'PROVED'
        else:
            passed = (rc == 2 and summary['status'] == 'UNKNOWN' and summary['claim']['condition'] is None
                      and summary['metrics']['native_samples'] == 0
                      and code in {d['code'] for d in summary['diagnostics']})
            if name in ('unsafe_index', 'short_unwind'):
                safety = summary['obligations']['state'].get('safety', {}).get('details', {})
                passed = (passed and safety.get('returncode') not in (None, 0)
                          and not safety.get('timed_out') and bool(safety.get('violation')))
            else:
                passed = passed and summary['metrics']['queries'] == 0
        record(name, passed, summary=summary, exit_code=rc, expected_condition=expected,
               expected_condition_check=match)

    config = dict(case='c', contract=str(snapshots / 'mutant_31.json'), variant='pair', state_mode='stateless',
                  domain=None, goal='exact', esbmc=args.esbmc, cc=args.cc, timeout=30,
                  max_seconds=300, max_queries=32, max_rounds=2)
    session, started = workflow.start(config, directory / 'agent-table')
    if started['phase'] == 'READY':
        proposal = directory / 'proposal.json'
        save_json(proposal, dict(session_id=started['session_id'], round=1, condition='n != 9', seeds=[]))
        workflow.step(session, proposal)
    summary = validate_summary(json.loads((session / 'verification-result.json').read_text(encoding='utf-8')))
    record('agent-table', summary['status'] == 'EXACT' and summary['claim']['meaning'] == 'REGION', summary=summary)
    binary = shutil.which(args.esbmc)
    report = dict(passed=sum(r['passed'] for r in results), total=len(results), results=results, artifacts=str(directory),
                  esbmc=None if binary is None else dict(path=str(Path(binary).resolve()), sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest()),
                  provenance='Executed generic C table acceptance; expected formulas checked separately; agent proposal scripted')
    save_json(directory / 'results.json', report)
    save_json(root / 'results.json', report)
    print(f"C READONLY TABLE ACCEPTANCE: {report['passed']}/{report['total']} passed")
    print(f'Artifacts: {directory}')
    return 0 if report['passed'] == report['total'] else 2


if __name__ == '__main__':
    sys.exit(main())
