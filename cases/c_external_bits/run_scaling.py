#!/usr/bin/env python3
"""Fixed-budget population-count domain sweep; recording is not proof success."""
import argparse
import copy
import csv
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile

import run_checks as baseline

WIDTHS = (8, 12, 16, 24, 32)
BUDGET = dict(timeout=30, max_seconds=300, max_queries=96)
INFRASTRUCTURE = {'COMPILER_NOT_FOUND', 'COMPILE_FAILED', 'COMPILE_TIMEOUT',
                  'SOLVER_NOT_FOUND', 'SOLVER_UNAVAILABLE', 'SOLVER_STARTUP_FAILED',
                  'SOLVER_STARTUP_TIMEOUT', 'UNSUPPORTED_INPUT', 'IDENTITY_CHANGED',
                  'WITNESS_MISMATCH', 'WITNESS_REPLAY_FAILED', 'NATIVE_REPLAY_FAILED'}


def schedule():
    return [dict(name=f'r{repeat}-b{width}', repeat=repeat, width=width)
            for repeat in (1, 2) for width in (WIDTHS if repeat == 1 else WIDTHS[::-1])]


def contract_for(template, width):
    if width not in WIDTHS:
        raise ValueError('width is outside the fixed schedule')
    data = copy.deepcopy(template)
    data['name'] = f'popcount_domain_{width}'
    data['inputs']['x']['max'] = 2**width - 1
    return data


def hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file()}


def measured(summary, rc, queries, match):
    """Admit valid failure measurements without labelling them proofs."""
    codes = {d['code'] for d in summary['diagnostics']}
    return (rc == (0 if summary['status'] == 'EXACT' else 2)
            and summary['metrics']['queries'] == len(queries) and bool(queries)
            and not codes.intersection(INFRASTRUCTURE)
            and (match or {}).get('status') != 'REFUTED')


def flatten(row):
    summary = row.get('summary', {})
    metrics = summary.get('metrics', {})
    queries = row.get('queries', [])
    return dict(name=row['name'], repeat=row['repeat'], width=row['width'],
                maximum=2**row['width']-1, status=summary.get('status', 'ERROR'),
                condition=summary.get('claim', {}).get('condition'),
                full_domain_certified=row.get('full_domain_certified', False),
                measurement_valid=row.get('measurement_valid', False),
                queries=metrics.get('queries'), seconds=metrics.get('elapsed_seconds'),
                timeouts=sum(q.get('timed_out') is True for q in queries),
                timeout_kinds=','.join(q.get('kind', '?') for q in queries if q.get('timed_out')),
                diagnostics=','.join(sorted({d['code'] for d in summary.get('diagnostics', [])})),
                error=row.get('error', ''))


def overview(report):
    lines = ['# Popcount：固定预算的输入域规模实验', '',
             f"记录状态：{report['status']}；有效测量 {report['valid_runs']}/10；"
             f"全域等价证书 {report['certified']}/10。", '',
             'RECORDED 仅表示测量完整且身份检查通过，不表示十次都证明成功。',
             '身份检查：' + ', '.join(f'{k}={v}' for k, v in report['identities'].items()),
             '所有运算仍是 uint32_t；位数仅限制输入范围，不改变循环或运算语义。', '',
             '| 运行 | 输入位数 | 结果 | 全域证书 | 查询 | 秒 | 超时查询种类 | 诊断 |',
             '|---|---|---|---|---|---|---|---|']
    for row in report['results']:
        r = flatten(row)
        label = f"[{r['name']}]({r['name']}/verification-result.json)" if row.get('summary') else r['name']
        lines.append(f"| {label} | {r['width']} | {r['status']} | {r['full_domain_certified']} | "
                     f"{r['queries']} | {r['seconds']} | {r['timeout_kinds']} | {r['diagnostics']} |")
    lines += ['', '超时保留为截断的失败观测，不计作完成证明耗时。两轮不足以建立稳定性能结论。',
              '查询数和秒数来自 discovery；事后的全域条件检查单独存档。', '',
              '[所有结果与查询](results.json) · [CSV](metrics.csv) · [固定计划](schedule.json)',
              '[实验说明](inputs/SCALING.md)', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/popcount-scaling')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='scaling-', dir=root))
    inputs, contracts = directory / 'inputs', directory / 'contracts'
    inputs.mkdir()
    contracts.mkdir()
    initial_inputs, initial_engine = baseline.input_hashes(), baseline.engine_hashes()
    lock = baseline.read_json(baseline.CASE / 'engine-lock.json')
    tools = lambda: {name: baseline.binary_identity(cmd) for name, cmd in (('esbmc', args.esbmc), ('cc', args.cc))}
    before_tools = tools()
    for name in initial_inputs:
        shutil.copyfile(baseline.CASE / name, inputs / name)
    for name in initial_engine:
        target = directory / 'engine' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline.ROOT / name, target)
    template = baseline.read_json(inputs / 'popcount_32.json')
    for side in ('original', 'candidate'):
        name = template[side]['source']
        shutil.copyfile(inputs / name, contracts / name)
    for width in WIDTHS:
        baseline.save_json(contracts / f'b{width}.json', contract_for(template, width))
    initial_contracts, initial_snapshots = hashes(contracts), hashes(inputs)
    plan = dict(schedule=schedule(), budget=BUDGET, unwind=34,
                changed='Only contract name and input upper bound; all operations remain uint32_t',
                baseline_commit=lock['baseline_commit'], repetitions=2)
    baseline.save_json(directory / 'schedule.json', plan)
    rows = []
    if initial_engine == lock['files']:
        for item in plan['schedule']:
            work = directory / item['name']
            command = ['--contract', str(contracts / f"b{item['width']}.json"), '--esbmc', args.esbmc,
                       '--cc', args.cc, '--workdir', str(work)]
            for key, value in BUDGET.items():
                command += ['--' + key.replace('_', '-'), str(value)]
            row = dict(item, measurement_valid=False, full_domain_certified=False)
            try:
                print(f"\n{item['name']}", flush=True)
                rc = baseline.find_main(command)
                baseline.save_json(work / 'invocation.json', [sys.executable,
                                   str(baseline.ROOT / 'tools/find-cond-equiv/find_c_conditions.py'), *command])
                summary = baseline.validate_summary(baseline.read_json(work / 'verification-result.json'))
                row.update(summary=summary, exit_code=rc)
                raw_directory = Path(summary['artifacts']['directory'])
                queries = baseline.read_json(raw_directory / 'queries.json')
                match = None
                row['queries'] = queries
                if summary['status'] == 'EXACT' and rc == 0:
                    checkdir = work / 'full-domain-check'
                    checkdir.mkdir()
                    backend = baseline.bind_contract(command[1])(baseline.parse_args(command), checkdir)
                    backend.prepare()
                    match = backend.query('expected', summary['claim']['condition_c'], expected='true')
                    baseline.save_json(checkdir / 'result.json', match)
                row.update(full_domain_check=match, measurement_valid=measured(summary, rc, queries, match),
                           full_domain_certified=baseline.accepted(summary, rc, match))
            except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
                row['error'] = str(exc)
            rows.append(row)
            print(f"{item['name']}: {row.get('summary', {}).get('status', 'ERROR')}; "
                  f"full-domain certified={row['full_domain_certified']}", flush=True)
    after_tools = tools()
    identities = dict(engine_frozen=initial_engine == lock['files'],
                      engine_unchanged=initial_engine == baseline.engine_hashes(),
                      inputs_unchanged=initial_inputs == baseline.input_hashes(),
                      snapshots_unchanged=initial_snapshots == hashes(inputs),
                      contracts_unchanged=initial_contracts == hashes(contracts),
                      tools_unchanged=before_tools == after_tools,
                      tools_present=all(t['path'] is not None for t in before_tools.values()))
    valid, certified = sum(r['measurement_valid'] for r in rows), sum(r['full_domain_certified'] for r in rows)
    report = dict(status='RECORDED' if valid == 10 and all(identities.values()) else 'INCOMPLETE',
                  valid_runs=valid, total=10, certified=certified, results=rows, identities=identities,
                  tools_before=before_tools, tools_after=after_tools, inputs_before=initial_inputs,
                  contracts_before=initial_contracts, snapshots_before=initial_snapshots,
                  engine_before=initial_engine, lock=lock, plan=plan, artifacts=str(directory))
    baseline.save_json(directory / 'results.json', report)
    baseline.save_json(root / 'results.json', report)
    with (directory / 'metrics.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = list(flatten(dict(name='', repeat=0, width=8)))
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flatten(r) for r in rows)
    (directory / 'README.md').write_text(overview(report), encoding='utf-8')
    print(f"POPCOUNT SCALING: {report['status']} ({valid}/10 valid runs; full-domain certified={certified}/10)")
    print(f'Open overview: {directory / "README.md"}')
    return 0 if report['status'] == 'RECORDED' else 2


if __name__ == '__main__':
    sys.exit(main())
