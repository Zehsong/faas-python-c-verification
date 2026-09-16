#!/usr/bin/env python3
"""One report index across supported C scalar, table, array and private-cache cases.

Runs existing backends without modifying their search or proof obligations.
This is an integration demonstration, not an independent held-out benchmark.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'cases/c_scalar_demo'))
from run_demo import snapshot_pair, binary_identity, read_json
from c_backend import save_json
from cache_sketch import CacheSketch
from find_c_conditions import main as find_main
from find_cache_conditions import CacheBackend, parse_args as cache_args, run as cache_run
from find_config_conditions import ConfigBackend
from result_contract import validate_summary

CASES = (
    dict(name='scalar-all', title='标量：两种奇偶判断', fixture='c_scalar/parity.json', meaning='ALL_INPUTS'),
    dict(name='prime-lookup', title='计算与查表：带错误表项', fixture='c_readonly_tables/mutant_31.json', meaning='REGION'),
    dict(name='array-swap', title='数组：交换与保持原样', fixture='c_bounded_arrays/swap.json', meaning='REGION'),
    dict(name='cache-miss', title='私有缓存：未命中时返回错误值', family='cache', variant='bad_miss', meaning='REGION'),
    dict(name='config-cache', title='配置缓存：遗漏失效条件', family='config-cache', variant='stale', meaning='REGION'),
    dict(name='no-equal-inputs', title='数组相同、返回值始终不同', fixture='c_bounded_arrays/return_mutant.json', meaning='NO_INPUTS'),
    dict(name='budget-limited', title='预算不足：保留未知结果', fixture='c_scalar/max_min.json', meaning='NO_EQUIVALENCE_CLAIM', budget=4),
)


def file_hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def engine_identity():
    paths = [p for p in (ROOT / 'tools/find-cond-equiv').glob('*.py') if not p.name.startswith('test_')]
    paths += [ROOT / 'tools/verify-equiv' / name for name in ('verify_equiv.py', 'c_obligation.py')]
    return {str(Path(p).relative_to(ROOT)): v for p, v in file_hashes(paths).items()}


def source_identity():
    paths = [Path(__file__), Path(__file__).with_name('run_demo.sh'), ROOT / 'cases/c_scalar_demo/run_demo.py']
    for case in CASES:
        if case.get('fixture'):
            contract = ROOT / 'cases' / case['fixture']
            data = read_json(contract)
            paths += [contract, *[contract.parent / data[side]['source'] for side in ('original', 'candidate')]]
        else:
            family = 'same_language_cache' if case['family'] == 'cache' else 'config_cache'
            paths += [ROOT / 'cases' / family / n for n in ('cache_model.h', 'cache_probe.c', 'sketch.json')]
    return {str(Path(p).relative_to(ROOT)): v for p, v in file_hashes(set(paths)).items()}


def snapshot_cache(family, destination):
    base = CacheBackend if family == 'cache' else ConfigBackend
    destination.mkdir(parents=True)
    for name in ('cache_model.h', 'cache_probe.c', 'sketch.json'):
        shutil.copyfile(base.case / name, destination / name)
    bound = CacheSketch(destination / 'sketch.json')
    class SnapshotBackend(base):
        case = destination
        sketch = bound
        variants = bound.data['variants']
        make_harness = staticmethod(bound.render)
    return SnapshotBackend


def expectation_met(case, summary, rc):
    if 'budget' not in case:
        return rc == 0 and summary['status'] == 'EXACT' and summary['claim']['meaning'] == case['meaning']
    return (rc == 2 and summary['status'] == 'UNKNOWN' and summary['claim']['condition'] is None
            and summary['metrics']['queries'] == case['budget']
            and summary['obligations']['state'].get('safety', {}).get('status') == 'PROVED'
            and 'QUERY_BUDGET_EXHAUSTED' in {d['code'] for d in summary['diagnostics']})


def array_counterexample(summary, queries):
    """Require a replayed equality refutation despite identical scalar returns."""
    scope = summary.get('scope') or {}
    if summary['obligations']['state'].get('safety', {}).get('status') != 'PROVED':
        return None
    fields, arrays = scope.get('inputs'), scope.get('memory', {}).get('arrays')
    if not isinstance(fields, dict) or not fields or not isinstance(arrays, dict) or not arrays:
        return None
    types = [scope['return_type'], *[s['type'][:-2] for s in arrays.values() for _ in range(s['length'])]]
    for index, query in enumerate(queries):
        row, witness = query.get('native_replay'), query.get('witness')
        if query.get('kind') != 'equal' or query.get('status') != 'REFUTED' or not isinstance(row, dict) or not isinstance(witness, dict):
            continue
        if set(witness) != set(fields) or any(type(row.get(k)) is not int or type(witness.get(k)) is not int
                or row[k] != witness[k] or not spec['min'] <= row[k] <= spec['max'] for k, spec in fields.items()):
            continue
        left, right = row.get('observations_original'), row.get('observations_candidate')
        if any(not isinstance(v, list) or len(v) != len(types) or any(type(x) is not int or not 0 <= x <= (1 if t == 'bool' else 2**32 - 1)
               for x, t in zip(v, types)) for v in (left, right)):
            continue
        if any(type(row.get(k)) is not int for k in ('r_original', 'r_cached')):
            continue
        if left[0] != row['r_original'] or right[0] != row['r_cached'] or left[0] != right[0] or left == right:
            continue
        return dict(inputs=witness, original_return=left[0], candidate_return=right[0],
                    original_observations=left, candidate_observations=right,
                    observation_order=scope['memory']['observation_order'], query_directory=f'query-{index:03d}-equal',
                    provenance='ESBMC equality refutation already replayed by the native backend; one input, not a region certificate')
    return None


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render_overview(report):
    lines = ['# C 条件等价工具演示', '',
             f"演示验收：**{'READY' if report['ready'] else 'INCOMPLETE'}**，{report['passed']}/{report['total']} 项。", '',
             '本页汇总本次实际运行的结果。案例来自已有集成测试，不是独立盲测。',
             '条件针对声明的输入域与观察；所有证明仍由后端完成。', '',
             '| 案例 | 实际结果 | 认证条件 | 演示预期满足 | 报告 |', '|---|---|---|---|---|']
    for item in report['results']:
        s = item.get('summary')
        status, condition = (s['status'], s['claim']['condition']) if s else ('DEMO_ERROR', None)
        link = f"[查看]({item['name']}/report.md)" if s else '见下方错误'
        lines.append(f"| {cell(item['title'])} | {status} | {cell(condition) if condition is not None else '无认证条件'} | {'是' if item['passed'] else '否'} | {link} |")
    lines += ['', '## 如何阅读', '',
              '- EXACT：域内满足条件的输入等价，条件外的输入均已证明不等价。',
              '- PARTIAL：条件内已证明等价，条件外尚未完全分类。',
              '- UNKNOWN：没有可发布的认证条件；需查看具体诊断。',
              '- EXACT false：输入域非空，但其中没有等价输入。',
              '- 数组比较返回值和全部最终元素；私有缓存比较返回值，同时检查 invariant。',
              '- 每项都只描述一次调用；私有缓存布局、任意调用序列和任意 C 语法不在承诺内。', '']
    for item in report['results']:
        name, summary = item['name'], item.get('summary')
        lines += [f"## {item['title']}", '']
        if not summary:
            lines += [item.get('error', '没有生成结果。'), '']
            continue
        if item.get('error'):
            lines += ['演示检查错误：' + item['error'], '']
        scope = summary.get('scope') or {}
        if isinstance(scope.get('inputs'), dict):
            lines += ['初始输入域：' + '；'.join(f"{k}: {s['type']} {s['min']}..{s['max']}" for k, s in scope['inputs'].items()), '']
        else:
            lines += ['初始输入：' + str(scope.get('inputs', '未建立')), '', '入口状态：' + str(scope.get('initial_state', '未建立')), '']
        lines += ['观察：' + str(scope.get('observations', '未建立')), '']
        if scope.get('state_contract'):
            state = scope['state_contract']
            lines += ['私有状态：' + ', '.join(state['fields']) + '；保持证明入口模式：' + state['preservation_domain'], '']
        if scope.get('memory', {}).get('entry_field_mapping'):
            lines += ['数组入口字段：' + '；'.join(f'{k} → {v}' for k, v in scope['memory']['entry_field_mapping'].items()), '']
        for key, label in (('assumptions', '假设'), ('bound', '证明边界'), ('safety', '安全要求')):
            if scope.get(key): lines += [label + '：' + str(scope[key]), '']
        lines += ['状态/安全义务：' + '；'.join(f"{k}: {v['status']}" for k, v in summary['obligations']['state'].items()), '']
        if summary['claim']['condition'] is not None:
            lines += ['本次认证条件：', '', '```text', summary['claim']['condition'], '```', '']
        else:
            lines += ['本次未发布认证条件。', '']
        codes = list(dict.fromkeys(d['code'] for d in summary['diagnostics']))
        if codes: lines += ['诊断：' + ', '.join(codes), '']
        lines += [f"[可读报告]({name}/report.md) · [结构化结果]({name}/verification-result.json) · [运行请求]({name}/invocation.json)", '']
        if item.get('fixture'):
            lines += [f"可编辑输入：[约定]({name}/inputs/contract.json)、[原程序]({name}/inputs/original.c)、[候选]({name}/inputs/candidate.c)。", '']
        else:
            lines += [f"经过检查的缓存模型：[C 模型]({name}/inputs/cache_model.h)、[sketch]({name}/inputs/sketch.json)。这不是任意状态 C 的通用前端。", '']
    lines += ['## 返回值相同也可能不等价', '']
    witness = report['array_counterexample']
    if witness:
        base = witness['artifact_directory'] + '/' + witness['query_directory']
        lines += ['以下反例由求解器给出，且已由后端原生重放：', '', '```json', json.dumps(witness, ensure_ascii=False, indent=2), '```', '',
                  f"[求解日志]({base}/verify.log) · [查询结果]({base}/result.json)", '',
                  '两个返回值相同，但最终数组不同。单个反例只否定无条件等价，不能证明整个区域都不等价。', '']
    else:
        lines += ['未取得符合要求且成功重放的数组反例；这项演示检查未通过。', '']
    lines += ['## 证据与可复现性', '',
              f"引擎未变：{report['engine_unchanged']}；输入与演示代码未变：{report['inputs_unchanged']}；工具未变：{report['tools_unchanged']}。", '',
              '[索引与身份记录](results.json) 保存本次实际状态、条件、输入哈希和工具身份。',
              '本页链接为归档相对路径，下载解压后仍可浏览；底层日志中的绝对路径保留原运行环境。',
              'READY 仅表示本次演示预期通过，不表示已完成全新环境复现或独立盲测。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True)
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--workdir', default='.verify-equiv-runs/c-tool-demo')
    args = parser.parse_args(argv)
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='demo-', dir=root))
    before = dict(engine=engine_identity(), sources=source_identity(), tools={n: binary_identity(getattr(args, n)) for n in ('cc', 'esbmc')})
    save_json(directory / 'identity-before.json', before)
    shutil.copyfile(__file__, directory / 'run_showcase.py')
    results, witness = [], None
    for case in CASES:
        item = {**case, 'passed': False}
        work = directory / case['name']
        print('\n' + case['name'], flush=True)
        try:
            if case.get('fixture'):
                contract = snapshot_pair(ROOT / 'cases' / case['fixture'], work / 'inputs')
                backend = None
                command = ['--contract', str(contract)]
                entry = 'find_c_conditions.py'
            else:
                backend = snapshot_cache(case['family'], work / 'inputs')
                command = ['--variant', case['variant'], '--state-mode', 'invariant']
                entry = 'find_cache_conditions.py' if case['family'] == 'cache' else 'find_config_conditions.py'
            inputs_before = file_hashes((work / 'inputs').iterdir())
            command += ['--esbmc', args.esbmc, '--cc', args.cc, '--max-queries', str(case.get('budget', 160)),
                        '--max-seconds', '600', '--workdir', str(work)]
            save_json(work / 'invocation.json', dict(command=[sys.executable, str(ROOT / 'tools/find-cond-equiv' / entry), *command],
                      input_snapshot=str(work / 'inputs'), note='Cache demo executes a snapshot-bound instance; standalone CLI uses repository cache bindings.'))
            if backend is None:
                rc = find_main(command)
            else:
                result = cache_run(cache_args(command, variants=backend.variants), backend)
                rc = 0 if result['status'] == 'EXACT' else 2
            summary = validate_summary(read_json(work / 'verification-result.json'))
            unchanged = inputs_before == file_hashes((work / 'inputs').iterdir())
            item.update(summary=summary, exit_code=rc, input_hashes=inputs_before, inputs_unchanged=unchanged,
                        passed=expectation_met(case, summary, rc) and unchanged and (work / 'report.md').is_file())
            if case['name'] == 'array-swap':
                artifacts = Path(summary['artifacts']['directory'])
                if (artifacts / 'queries.json').is_file():
                    witness = array_counterexample(summary, read_json(artifacts / 'queries.json'))
                    if witness: witness['artifact_directory'] = artifacts.relative_to(directory).as_posix()
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            item.update(passed=False, error=str(exc))
        results.append(item)
        print(f"{case['name']}: {'PASS' if item['passed'] else 'NOT ESTABLISHED'}", flush=True)
    after = dict(engine=engine_identity(), sources=source_identity(), tools={n: binary_identity(getattr(args, n)) for n in ('cc', 'esbmc')})
    report = dict(results=results, array_counterexample=witness, identity_before=before, identity_after=after,
                  engine_unchanged=before['engine'] == after['engine'], tools_unchanged=before['tools'] == after['tools'],
                  inputs_unchanged=before['sources'] == after['sources'] and all(r.get('inputs_unchanged', False) for r in results),
                  passed=sum(r['passed'] for r in results) + int(witness is not None), total=len(CASES) + 1,
                  artifacts=str(directory), python=sys.version,
                  provenance='Executed integration demonstration; no held-out, clean-environment or autonomous-agent claim')
    try:
        report['git_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        report['git_status'] = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    except (OSError, subprocess.CalledProcessError):
        report['git_head'] = report['git_status'] = None
    report['ready'] = report['passed'] == report['total'] and all(report[n] for n in ('engine_unchanged', 'inputs_unchanged', 'tools_unchanged'))
    save_json(directory / 'results.json', report)
    save_json(root / 'results.json', report)
    (directory / 'README.md').write_text(render_overview(report), encoding='utf-8')
    print(f"C TOOL DEMO: {'READY' if report['ready'] else 'INCOMPLETE'} ({report['passed']}/{report['total']} checks; engine unchanged={report['engine_unchanged']})")
    print(f"Open overview: {directory / 'README.md'}")
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    sys.exit(main())
