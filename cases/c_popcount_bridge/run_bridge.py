#!/usr/bin/env python3
"""Proposed C intermediate programs; every full-domain edge is certified.

This experimental composition report is separate from the core result schema.
No assumptions about helpers, sampled values, or bridge correctness are injected.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'cases/c_external_bits'))
import run_scaling as support
baseline = support.baseline
from c_scalar_contract import Contract

NODES = (ROOT / 'cases/c_external_bits/popcount_reference.c', CASE / 'byte_loop.c',
         CASE / 'byte_parallel.c', ROOT / 'cases/c_external_bits/popcount_parallel.c')
INPUTS = {'x': {'type': 'uint32_t', 'min': 0, 'max': 4294967295}}
REQUIRED_IDENTITIES = {'engine_frozen', 'endpoints_locked', 'connected', 'engine_unchanged',
                       'inputs_unchanged', 'contracts_unchanged', 'tools_unchanged', 'tools_present'}


def snapshot(destination):
    destination.mkdir()
    for index, source in enumerate(NODES):
        shutil.copyfile(source, destination / f'node-{index}.c')
    shutil.copyfile(CASE / 'mutant.c', destination / 'mutant.c')
    paths = []
    for index in range(4):
        control = index == 3
        original = 'node-0.c' if control else f'node-{index}.c'
        candidate = 'mutant.c' if control else f'node-{index+1}.c'
        name = 'mutant' if control else f'edge_{index}'
        data = dict(schema=1, name=name,
                    original=dict(source=original, entry='popcount', args=['x']),
                    candidate=dict(source=candidate, entry='popcount', args=['x']),
                    inputs={'x': dict(INPUTS['x'], max=255)} if control else INPUTS,
                    return_type='uint32_t', observations=['return'], unwind=34)
        path = destination / (name + '.json')
        baseline.save_json(path, data)
        Contract(path)  # Reject unsupported input before invoking anything.
        paths.append(path)
    return paths


def input_files():
    files = set(NODES) | {p for p in CASE.iterdir() if p.is_file()}
    files |= {ROOT / 'cases/c_external_bits' / n for n in ('run_checks.py', 'run_scaling.py', 'engine-lock.json')}
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def endpoints_locked():
    lock = baseline.read_json(CASE / 'endpoint-lock.json')
    if set(lock.get('files', {})) != {NODES[i].relative_to(ROOT).as_posix() for i in (0, 3)}:
        return False
    return all(hashlib.sha256((ROOT / name).read_text(encoding='utf-8').encode()).hexdigest() == digest
               for name, digest in lock['files'].items())


def connected(contracts):
    """Check byte identity, call bindings and a common stateless observation domain."""
    if len(contracts) != 3:
        return False
    for index, c in enumerate(contracts):
        if (c.data['schema'] != 1 or c.data['inputs'] != INPUTS or c.data['return_type'] != 'uint32_t'
                or c.data['observations'] != ['return'] or c.data['unwind'] != 34):
            return False
        if any(c.data[side]['entry'] != 'popcount' or c.data[side]['args'] != ['x']
               for side in ('original', 'candidate')):
            return False
        if index and c.sources['original'].data != contracts[index-1].sources['candidate'].data:
            return False
    return (contracts[0].sources['original'].data == NODES[0].read_bytes()
            and contracts[-1].sources['candidate'].data == NODES[-1].read_bytes())


def compose(rows, contracts, identities):
    if (any(identities.get(key) is not True for key in REQUIRED_IDENTITIES)
            or not connected(contracts) or len(rows) != 3):
        return False
    for index, (row, contract) in enumerate(zip(rows, contracts)):
        summary = row.get('summary')
        try:
            baseline.validate_summary(summary)
        except (ValueError, KeyError, TypeError, AttributeError):
            return False
        if (row.get('name') != f'edge_{index}' or not row.get('full_domain_certified')
                or summary['scope'].get('source_identity') != contract.identity
                or not baseline.accepted(summary, row.get('exit_code'), row.get('full_domain_check'))):
            return False
    return True


def execute(contract, work, args):
    command = ['--contract', str(contract), '--esbmc', args.esbmc, '--cc', args.cc,
               '--timeout', '30', '--max-seconds', '120', '--max-queries', '96', '--workdir', str(work)]
    row = dict(name=contract.stem, full_domain_certified=False, measurement_valid=False)
    try:
        rc = baseline.find_main(command)
        baseline.save_json(work / 'invocation.json', [sys.executable,
                           str(ROOT / 'tools/find-cond-equiv/find_c_conditions.py'), *command])
        summary = baseline.validate_summary(baseline.read_json(work / 'verification-result.json'))
        row.update(summary=summary, exit_code=rc)
        queries = baseline.read_json(Path(summary['artifacts']['directory']) / 'queries.json')
        row['queries'] = queries
        match = None
        if rc == 0 and summary['status'] == 'EXACT':
            post = work / 'full-domain-check'
            post.mkdir()
            backend = baseline.bind_contract(contract)(baseline.parse_args(command), post)
            backend.prepare()
            match = backend.query('expected', summary['claim']['condition_c'], expected='true')
            baseline.save_json(post / 'result.json', match)
        # A refuted expectation is an ordinary recorded negative control here.
        row.update(full_domain_check=match, full_domain_certified=baseline.accepted(summary, rc, match),
                   measurement_valid=support.measured(summary, rc, queries, None))
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        row['error'] = str(exc)
    return row


def outcome(rows, contracts, identities):
    control = rows[-1] if len(rows) == 4 else {}
    rejected = bool(control.get('name') == 'mutant' and control.get('measurement_valid')
                    and control.get('summary', {}).get('status') == 'EXACT'
                    and control['summary']['claim']['meaning'] == 'NO_INPUTS'
                    and (control.get('full_domain_check') or {}).get('status') == 'REFUTED')
    recorded = (len(rows) == 4 and all(r['measurement_valid'] for r in rows) and rejected
                and all(identities.get(key) is True for key in REQUIRED_IDENTITIES))
    return recorded, recorded and compose(rows[:3], contracts, identities), rejected


def overview(report):
    lines = ['# Popcount：经认证的中间程序链实验', '',
             f"实验记录：{report['status']}；原始端点结论：{report['endpoint_claim']['status']}。", '',
             '只有三段在同一个完整输入域上全部认证，才按等价关系的传递性连接原始端点。',
             '任一连接 UNKNOWN 或失败都不能推出原始端点不等价。中间程序不作为假设。', '',
             '| 连接 | 发现结果 | 全域证书 | 查询数 | 秒 | 诊断 |', '|---|---|---|---|---|---|']
    for row in report['results']:
        s = row.get('summary', {})
        metrics = s.get('metrics', {})
        label = f"[{row['name']}]({row['name']}/verification-result.json)" if s else row['name']
        diagnostics = ','.join(sorted({d['code'] for d in s.get('diagnostics', [])}))
        lines.append(f"| {label} | {s.get('status', 'ERROR')} | {row['full_domain_certified']} | "
                     f"{metrics.get('queries')} | {metrics.get('elapsed_seconds')} | {diagnostics} |")
    lines += ['', f"错误版本拒绝检查：{report['mutant_rejected']}。", '',
              'RECORDED 表示实验测量与控制检查完成；端点只有 PROVED 才有组合证明。',
              '这是人工提出中间程序的实验，不是自动分解或 agent 性能评估。', '',
              '[完整证据](results.json) · [实验说明](experiment/README.md)', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/popcount-bridge')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='bridge-', dir=root))
    before_inputs, before_engine = input_files(), baseline.engine_hashes()
    lock = baseline.read_json(ROOT / 'cases/c_external_bits/engine-lock.json')
    tools = lambda: {n: baseline.binary_identity(cmd) for n, cmd in (('esbmc', args.esbmc), ('cc', args.cc))}
    before_tools = tools()
    experiment = directory / 'experiment'
    experiment.mkdir()
    for path in CASE.iterdir():
        if path.is_file():
            shutil.copyfile(path, experiment / path.name)
    for relative in before_engine:
        target = directory / 'engine' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    for name in ('run_checks.py', 'run_scaling.py', 'engine-lock.json'):
        shutil.copyfile(ROOT / 'cases/c_external_bits' / name, experiment / ('external-' + name))
    paths = snapshot(directory / 'contracts')
    contract_hashes = support.hashes(directory / 'contracts')
    contracts = [Contract(p) for p in paths[:3]]
    identities = dict(engine_frozen=before_engine == lock['files'], endpoints_locked=endpoints_locked(),
                      connected=connected(contracts))
    rows = []
    if all(identities.values()):
        for path in paths:
            print(f'\n{path.stem}', flush=True)
            row = execute(path, directory / path.stem, args)
            rows.append(row)
            print(f"{row['name']}: {row.get('summary', {}).get('status', 'ERROR')}; "
                  f"full-domain certified={row['full_domain_certified']}", flush=True)
    after_tools = tools()
    identities.update(engine_unchanged=baseline.engine_hashes() == before_engine,
                      inputs_unchanged=input_files() == before_inputs,
                      contracts_unchanged=support.hashes(directory / 'contracts') == contract_hashes,
                      tools_unchanged=before_tools == after_tools,
                      tools_present=all(v['path'] is not None for v in before_tools.values()))
    recorded, proved, rejected = outcome(rows, contracts, identities)
    report = dict(schema='popcount-bridge-experiment-v1', status='RECORDED' if recorded else 'INCOMPLETE',
                  endpoint_claim=dict(status='PROVED' if proved else 'UNKNOWN', condition='true' if proved else None,
                                      inputs=INPUTS, observations=['return'], unwind=34,
                                      basis='Transitivity of three independently certified full-domain edges; not a direct endpoint query'),
                  results=rows, mutant_rejected=bool(rejected), identities=identities,
                  engine_lock=lock, endpoint_lock=baseline.read_json(CASE / 'endpoint-lock.json'),
                  source_hashes={str(p.relative_to(ROOT)): h for p, h in before_inputs.items()},
                  contract_hashes=contract_hashes, tools_before=before_tools, tools_after=after_tools,
                  artifacts=str(directory))
    baseline.save_json(directory / 'results.json', report)
    baseline.save_json(root / 'results.json', report)
    (directory / 'README.md').write_text(overview(report), encoding='utf-8')
    print(f"POPCOUNT BRIDGE: {report['status']} (links certified={sum(r['full_domain_certified'] for r in rows[:3])}/3; "
          f"endpoint equivalence={report['endpoint_claim']['status']}; mutant rejected={bool(rejected)})")
    print(f'Open overview: {directory / "README.md"}')
    return 0 if recorded else 2


if __name__ == '__main__':
    sys.exit(main())
