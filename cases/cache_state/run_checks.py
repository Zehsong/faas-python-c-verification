#!/usr/bin/env python3
"""Private-cache state admission and common-result acceptance for both families.

All solver obligations execute afresh. Agent proposals are scripted controls.
Expected formulas are used only in separate checks after discovery.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/find-cond-equiv'))
from cache_sketch import CacheSketch
from c_backend import save_json
from find_cache_conditions import CacheBackend, parse_args, run
from find_config_conditions import ConfigBackend
from result_contract import validate_summary
import agent_workflow as workflow


def snapshot_backend(base, directory, control=None):
    directory.mkdir()
    for path in base.case.iterdir():
        if path.name in ('cache_model.h', 'cache_probe.c', 'sketch.json'):
            shutil.copyfile(path, directory / path.name)
    binding = json.loads((directory / 'sketch.json').read_text(encoding='utf-8'))
    if control == 'invalid-init':
        binding['initial_state'].update(valid=1, key=0, value=7)
    if control == 'invalid-preservation':
        params = ', '.join('uint32_t ' + n for n in binding['call_args'])
        args = ', '.join(binding['call_args'])
        model = directory / 'cache_model.h'
        model.write_text(model.read_text(encoding='utf-8') + f'''
static uint32_t cached_corrupt(Cache *cache, {params}) {{
    uint32_t result = cached_good(cache, {args});
    cache->value ^= UINT32_C(1);
    return result;
}}
''', encoding='utf-8')
        probe = directory / 'cache_probe.c'
        probe.write_text(probe.read_text(encoding='utf-8').replace('candidate = cached_good;', 'candidate = cached_corrupt;'), encoding='utf-8')
        binding['variants']['good'] = 'cached_corrupt'
    save_json(directory / 'sketch.json', binding)
    bound = CacheSketch(directory / 'sketch.json')
    class SnapshotBackend(base):
        case = directory
        sketch = bound
        variants = bound.data['variants']
        make_harness = staticmethod(bound.render)
    return SnapshotBackend


def identities():
    paths = list((ROOT / 'tools/find-cond-equiv').glob('*.py'))
    paths += list((ROOT / 'tools/verify-equiv').glob('*.py'))
    for family in ('same_language_cache', 'config_cache'):
        paths += [ROOT / 'cases' / family / n for n in ('sketch.json', 'cache_model.h', 'cache_probe.c')]
    paths += [Path(__file__), Path(__file__).with_name('test_state.sh')]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def binary_identities(args):
    result = {}
    for name in ('esbmc', 'cc'):
        executable = shutil.which(getattr(args, name))
        result[name] = None if executable is None else dict(path=str(Path(executable).resolve()), sha256=hashlib.sha256(Path(executable).read_bytes()).hexdigest())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/cache-state')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='checks-', dir=root))
    before = identities()
    binaries = binary_identities(args)
    save_json(directory / 'source-identities.json', before)
    shutil.copyfile(__file__, directory / 'acceptance-runner.py')
    save_json(directory / 'invocation.json', vars(args))
    results = []

    def record(name, passed, **details):
        results.append(dict(name=name, passed=bool(passed), **details))
        print(f"{name}: {'PASS' if passed else 'NOT ESTABLISHED'}", flush=True)

    families = [
        ('cache', CacheBackend, 'bad_miss', '(finder_valid && finder_x == finder_key) || finder_x == UINT32_MAX',
         'finder_x == UINT32_MAX', {'any': [{'all': ['valid', 'x == key']}, 'x == 4294967295']}),
        ('config-cache', ConfigBackend, 'stale', '!finder_valid || finder_x != finder_key || finder_config == finder_cached_config',
         'true', {'any': [{'not': 'valid'}, {'not': 'x == key'}, 'config == cached_config']})]
    for family, base, mutant, expected, empty_expected, proposal_condition in families:
        for label, variant, mode, formula, control in (
                ('good', 'good', 'invariant', 'true', None),
                ('conditional', mutant, 'invariant', expected, None),
                ('empty', mutant, 'empty', empty_expected, None),
                ('invalid-init', 'good', 'invariant', None, 'invalid-init'),
                ('invalid-preservation', 'good', 'invariant', None, 'invalid-preservation'),
                ('missing-solver', 'good', 'invariant', None, 'missing-solver')):
            name = family + '-' + label
            backend_type = snapshot_backend(base, directory / (name + '-inputs'), control)
            inputs_before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in backend_type.case.iterdir()}
            work = directory / name
            settings = parse_args(['--variant', variant, '--state-mode', mode, '--esbmc',
                                   'intentionally-missing-state-esbmc' if control == 'missing-solver' else args.esbmc,
                                   '--cc', args.cc, '--max-queries', '160', '--max-seconds', '600',
                                   '--workdir', str(work)], variants=backend_type.variants)
            print('\n' + name, flush=True)
            report = run(settings, backend_type)
            summary = validate_summary(json.loads((work / 'verification-result.json').read_text(encoding='utf-8')))
            match = None
            state = summary['obligations']['state']
            if formula is not None:
                passed = summary['status'] == 'EXACT' and all(state[n]['status'] == 'PROVED' for n in ('initialization', 'preservation'))
                if passed:
                    checkdir = Path(report['artifacts']) / 'expected-condition-check'
                    checkdir.mkdir()
                    backend = backend_type(settings, checkdir)
                    backend.prepare()
                    match = backend.query('expected', expected=f"({summary['claim']['condition_c']}) == ({formula})")
                    passed = match['status'] == 'PROVED'
            else:
                passed = summary['status'] == 'UNKNOWN' and summary['claim']['condition'] is None and summary['metrics']['native_samples'] == 0
                if control == 'missing-solver':
                    passed = passed and summary['metrics']['queries'] == 0 and 'SOLVER_NOT_FOUND' in {d['code'] for d in summary['diagnostics']}
                else:
                    key = 'initialization' if control == 'invalid-init' else 'preservation'
                    detail = state[key]['details']
                    passed = passed and state[key]['status'] == 'REFUTED' and bool(detail.get('violation')) and not detail.get('timed_out')
            inputs_after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in backend_type.case.iterdir()}
            record(name, passed and inputs_before == inputs_after, summary=summary, expected_condition=formula,
                   expected_condition_check=match, input_hashes=inputs_before, inputs_unchanged=inputs_before == inputs_after)

        config = dict(case=family, variant=mutant, state_mode='invariant', domain=None, goal='exact',
                      esbmc=args.esbmc, cc=args.cc, timeout=30, max_seconds=300, max_queries=32, max_rounds=3)
        session, started = workflow.start(config, directory / ('agent-' + family))
        bad = None
        if started['phase'] == 'READY':
            proposal = directory / (family + '-proposal.json')
            save_json(proposal, dict(session_id=started['session_id'], round=1, condition=True, seeds=[]))
            bad = workflow.step(session, proposal)
            save_json(proposal, dict(session_id=started['session_id'], round=2, condition=proposal_condition, seeds=[]))
            workflow.step(session, proposal)
        summary = validate_summary(json.loads((session / 'verification-result.json').read_text(encoding='utf-8')))
        passed = (bad is not None and bad['latest_feedback']['status'] == 'REFUTED'
                  and bad['queries_used'] == started['queries_used'] and summary['status'] == 'EXACT')
        record('agent-' + family, passed, first_candidate_feedback=bad, summary=summary)
    binaries_after = binary_identities(args)
    report = dict(passed=sum(r['passed'] for r in results), total=len(results), results=results,
                  inputs_tools_unchanged=before == identities() and binaries == binaries_after and all(r.get('inputs_unchanged', True) for r in results),
                  binaries=binaries, binaries_after=binaries_after, artifacts=str(directory),
                  provenance='Fresh cache obligations and discovery; scripted agent controls; no sequence-equivalence claim')
    save_json(directory / 'results.json', report)
    save_json(root / 'results.json', report)
    print(f"CACHE STATE ACCEPTANCE: {report['passed']}/{report['total']} passed; inputs/tools unchanged={report['inputs_tools_unchanged']}")
    print(f'Artifacts: {directory}')
    return 0 if report['passed'] == report['total'] and report['inputs_tools_unchanged'] else 2


if __name__ == '__main__':
    sys.exit(main())
