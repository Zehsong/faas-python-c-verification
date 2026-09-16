#!/usr/bin/env python3
"""Externally sourced post-freeze integration; not a blind evaluation.

The finder sees only C files/contracts and fixed budgets. Expectations are
used after discovery in a separate solver query, never as proposed predicates.
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

CASES = (
    ('power_guarded_32', 'true', True),
    ('power_raw_32', 'finder_x != 0u', True),
    ('power_positive_32', 'true', True),
    ('power_zero', 'false', True),
    ('popcount_8', 'true', True),
    ('popcount_32', 'true', False),
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def binary_identity(command):
    binary = shutil.which(command)
    if binary is None:
        return dict(requested=command, path=None, sha256=None)
    path = Path(binary).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return dict(requested=command, path=str(path), sha256=digest.hexdigest())


def engine_paths(root=ROOT):
    paths = [p for p in (root / 'tools/find-cond-equiv').glob('*.py')
             if not p.name.startswith('test_')]
    paths += [root / 'tools/find-cond-equiv/requirements.txt']
    paths += [root / 'tools/verify-equiv' / n for n in ('verify_equiv.py', 'c_obligation.py')]
    return sorted(paths)


def engine_hashes(root=ROOT):
    # Git checkouts on Windows may use CRLF. Match committed semantic text.
    return {p.relative_to(root).as_posix(): hashlib.sha256(
        p.read_text(encoding='utf-8').encode('utf-8')).hexdigest() for p in engine_paths(root)}


def input_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CASE.iterdir())
            if p.is_file() and p.suffix in ('.c', '.json', '.py', '.sh', '.md')}


def accepted(summary, exit_code, match):
    return (exit_code == 0 and summary['status'] == 'EXACT'
            and summary['obligations']['state'].get('safety', {}).get('status') == 'PROVED'
            and (match or {}).get('status') == 'PROVED')


def overview(report):
    lines = ['# 外部来源 C 案例：固定引擎接入', '',
             f"状态：{report['status']}；必要案例 {report['passed']}/{report['total']}。", '',
             '这是已知算法的外部来源接入实验，不是盲测或自主 agent 性能实验。',
             '结论仅覆盖每份契约的输入域和返回值；完整 32 位计数作为探索项保留所有结果。', '',
             '| 案例 | 必要 | 结果 | 实际条件 | 查询数 | 秒 | 验收 |',
             '|---|---|---|---|---|---|---|']
    for row in report['results']:
        s = row.get('summary', {})
        condition = str(s.get('claim', {}).get('condition')).replace('|', '&#124;')
        metrics = s.get('metrics', {})
        label = (f"[{row['name']}]({row['name']}/verification-result.json)" if s else row['name'])
        lines.append(f"| {label} | {row['required']} | "
                     f"{s.get('status', 'ERROR')} | {condition} | {metrics.get('queries')} | "
                     f"{metrics.get('elapsed_seconds')} | {row['passed']} |")
    lines += ['', '查询数和时间取自 discovery；事后期望条件检查单独存档，不算入发现预算。',
              'UNKNOWN/PARTIAL 和错误仍保存在 results.json；READY 不要求探索项 EXACT。', '',
              '[案例、来源与改写说明](acceptance-inputs/README.md) · [完整结果](results.json)', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/c-external-bits')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='checks-', dir=root))
    snapshots = directory / 'acceptance-inputs'
    snapshots.mkdir()
    before_inputs, before_engine = input_hashes(), engine_hashes()
    lock = read_json(CASE / 'engine-lock.json')
    before_tools = {n: binary_identity(cmd) for n, cmd in (('esbmc', args.esbmc), ('cc', args.cc))}
    for name in before_inputs:
        shutil.copyfile(CASE / name, snapshots / name)
    # Preserve the measured engine text alongside the expected baseline lock.
    for relative in before_engine:
        target = directory / 'engine' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    results = []
    frozen = before_engine == lock['files']
    if frozen:
        for name, expected, required in CASES:
            work = directory / name
            command = ['--contract', str(snapshots / (name + '.json')), '--esbmc', args.esbmc,
                       '--cc', args.cc, '--timeout', '30', '--max-seconds', '300',
                       '--max-queries', '96', '--workdir', str(work)]
            row = dict(name=name, required=required, passed=False, expected_condition=expected)
            try:
                print(f'\n{name}', flush=True)
                rc = find_main(command)
                save_json(work / 'invocation.json', [sys.executable,
                          str(ROOT / 'tools/find-cond-equiv/find_c_conditions.py'), *command])
                summary = validate_summary(read_json(work / 'verification-result.json'))
                row.update(exit_code=rc, summary=summary)
                match = None
                if rc == 0 and summary['status'] == 'EXACT':
                    checkdir = work / 'expected-condition-check'
                    checkdir.mkdir()
                    backend = bind_contract(command[1])(parse_args(command), checkdir)
                    backend.prepare()
                    match = backend.query('expected', summary['claim']['condition_c'], expected=expected)
                    save_json(checkdir / 'result.json', match)
                row.update(expected_condition_check=match, passed=accepted(summary, rc, match))
            except (OSError, ValueError, RuntimeError) as exc:
                row['error'] = str(exc)
            results.append(row)
            print(f"{name}: {'PASS' if row['passed'] else 'NOT ESTABLISHED'}", flush=True)
    after_tools = {n: binary_identity(cmd) for n, cmd in (('esbmc', args.esbmc), ('cc', args.cc))}
    identities = dict(engine_frozen=frozen, engine_unchanged=engine_hashes() == before_engine,
                      inputs_unchanged=input_hashes() == before_inputs, tools_unchanged=before_tools == after_tools)
    passed = sum(r['passed'] for r in results if r['required'])
    total = sum(required for _, _, required in CASES)
    ready = passed == total and len(results) == len(CASES) and all(identities.values())
    report = dict(status='READY' if ready else 'INCOMPLETE', passed=passed, total=total,
                  exploratory_exact=sum(r.get('summary', {}).get('status') == 'EXACT' for r in results if not r['required']),
                  results=results, identities=identities, tools_before=before_tools, tools_after=after_tools,
                  engine_before=before_engine, inputs_before=before_inputs, lock=lock,
                  artifacts=str(directory), provenance='External-source post-freeze integration, not blind; actual execution only')
    save_json(directory / 'results.json', report)
    save_json(root / 'results.json', report)
    (directory / 'README.md').write_text(overview(report), encoding='utf-8')
    print(f"EXTERNAL C INTEGRATION: {report['status']} ({passed}/{total} required; "
          f"exploratory EXACT={report['exploratory_exact']}/1; engine frozen={frozen})")
    print(f'Open overview: {directory / "README.md"}')
    return 0 if ready else 2


if __name__ == '__main__':
    sys.exit(main())
