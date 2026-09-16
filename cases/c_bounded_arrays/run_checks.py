#!/usr/bin/env python3
"""M3 bounded array input/output acceptance with complete observations.

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
    parser.add_argument('--workdir', default='.verify-equiv-runs/c-bounded-arrays')
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

    cases = [('swap', 'finder_a_0 == finder_a_1', None), ('increment', 'true', None),
             ('copy_reverse', 'finder_src_0 == finder_src_1', None), ('return_mutant', 'false', None),
             ('unsafe_index', None, 'SAFETY_OR_OTHER_PROPERTY_FAILURE'),
             ('short_unwind', None, 'UNWINDING_INCOMPLETE'),
             ('const_write', None, 'UNSUPPORTED_INPUT'),
             ('alias_rejected', None, 'INPUT_REJECTED'),
             ('missing-solver', None, 'SOLVER_NOT_FOUND')]
    for name, expected, code in cases:
        work = directory / name
        contract = snapshots / ('swap.json' if name == 'missing-solver' else name + '.json')
        command = ['--contract', str(contract), '--esbmc',
                   'intentionally-missing-array-esbmc' if name == 'missing-solver' else args.esbmc,
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

    config = dict(case='c', contract=str(snapshots / 'swap.json'), variant='pair', state_mode='stateless',
                  domain=None, goal='exact', esbmc=args.esbmc, cc=args.cc, timeout=30,
                  max_seconds=300, max_queries=32, max_rounds=3)
    session, started = workflow.start(config, directory / 'agent-array')
    bad = None
    if started['phase'] == 'READY':
        proposal = directory / 'proposal.json'
        save_json(proposal, dict(session_id=started['session_id'], round=1, condition=True, seeds=[]))
        bad = workflow.step(session, proposal)
        save_json(proposal, dict(session_id=started['session_id'], round=2, condition='a_0 == a_1', seeds=[]))
        workflow.step(session, proposal)
    summary = validate_summary(json.loads((session / 'verification-result.json').read_text(encoding='utf-8')))
    passed = (bad is not None and bad['latest_feedback']['status'] == 'REFUTED'
              and bad['queries_used'] == started['queries_used'] and summary['status'] == 'EXACT')
    record('agent-array', passed, first_candidate_feedback=bad, summary=summary)
    binary = shutil.which(args.esbmc)
    report = dict(passed=sum(r['passed'] for r in results), total=len(results), results=results, artifacts=str(directory),
                  esbmc=None if binary is None else dict(path=str(Path(binary).resolve()), sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest()),
                  provenance='Executed bounded array acceptance; expected formulas checked separately; agent proposal scripted')
    save_json(directory / 'results.json', report)
    save_json(root / 'results.json', report)
    print(f"C BOUNDED ARRAY ACCEPTANCE: {report['passed']}/{report['total']} passed")
    print(f'Artifacts: {directory}')
    return 0 if report['passed'] == report['total'] else 2


if __name__ == '__main__':
    sys.exit(main())
