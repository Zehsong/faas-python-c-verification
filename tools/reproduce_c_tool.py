#!/usr/bin/env python3
"""Reproduce the C demo from a committed checkout and fresh Python venv on Linux.

Reuses the explicitly selected host compiler and modified ESBMC. This is not
a clean-machine/container claim, nor independent held-out research evaluation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


class Failure(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(command):
    found = shutil.which(command)
    if not found:
        raise Failure('TOOL_NOT_FOUND', f'Required executable not found: {command}')
    path = Path(found).resolve()
    return dict(path=str(path), sha256=digest(path))


def isolated_environment(source, venv=None):
    # Keep host compiler/library configuration; exclude inherited Python/Git
    # routing and user pip configuration. Do not record environment secrets.
    env = {k: v for k, v in source.items() if not k.startswith(('PYTHON', 'PIP_', 'GIT_')) and k != 'VIRTUAL_ENV'}
    env.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', PIP_CONFIG_FILE=os.devnull)
    if venv:
        env['PATH'] = str(Path(venv) / 'bin') + os.pathsep + env.get('PATH', '')
        env['VIRTUAL_ENV'] = str(venv)
    return env


class Steps:
    def __init__(self, evidence, env):
        self.evidence, self.env, self.records = Path(evidence), env, []
        (self.evidence / 'logs').mkdir()

    def run(self, name, command, cwd, timeout=600, check=True):
        path = self.evidence / 'logs' / f'{len(self.records):02d}-{name}.txt'
        record = dict(name=name, command=[str(x) for x in command], cwd=str(cwd), log=str(path), timed_out=False)
        self.records.append(record)
        print(f'Reproduction: {name}', flush=True)
        with path.open('w', encoding='utf-8') as output:
            try:
                process = subprocess.Popen(record['command'], cwd=cwd, env=self.env, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
                try:
                    record['returncode'] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    record['timed_out'] = True
                    if os.name == 'posix':
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                    else:
                        process.kill()
                    record['returncode'] = process.wait()
            except OSError as exc:
                record.update(returncode=None, error=str(exc))
                output.write(str(exc))
        save(self.evidence / 'steps.json', self.records)
        if check and (record['timed_out'] or record['returncode'] != 0):
            raise Failure('STEP_TIMEOUT' if record['timed_out'] else 'STEP_FAILED', f'{name} failed; see {path}')
        return record, path.read_text(encoding='utf-8', errors='replace')


def require(condition, code, message):
    if not condition:
        raise Failure(code, message)


def inspect_venv(runtime, venv):
    prefix = Path(runtime['prefix']).resolve()
    require(prefix == venv.resolve() and prefix != Path(runtime['base_prefix']).resolve(),
            'VENV_NOT_ISOLATED', 'Python did not run inside the new venv')
    require(Path(runtime['pycparser_file']).is_file() and Path(runtime['pycparser_file']).resolve().is_relative_to(prefix),
            'DEPENDENCY_OUTSIDE_VENV', 'pycparser was imported from outside the new venv')
    config = (venv / 'pyvenv.cfg').read_text(encoding='utf-8').lower()
    require('include-system-site-packages = false' in config and runtime.get('user_site_enabled') is False,
            'VENV_NOT_ISOLATED', 'System or user site packages were not disabled')


def inspect_demo(demo, evidence):
    require(demo.get('ready') is True and demo.get('passed') == 8 and demo.get('total') == 8
            and all(demo.get(n) is True for n in ('engine_unchanged', 'inputs_unchanged', 'tools_unchanged')),
            'DEMO_NOT_READY', 'The isolated demonstration did not establish READY 8/8')
    overview = Path(demo['artifacts']) / 'README.md'
    require(overview.is_file() and overview.resolve().is_relative_to(evidence.resolve()),
            'DEMO_ARTIFACT_MISSING', 'Demo overview is missing or outside this evidence directory')
    return overview.relative_to(evidence).as_posix()


def package_evidence(evidence, directory):
    paths = sorted(p for p in evidence.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (evidence / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(evidence).as_posix()}\n' for p in paths), encoding='utf-8')
    archive = directory / (directory.name + '.tar.gz')
    temporary = archive.with_suffix('.gz.part')
    with tarfile.open(temporary, 'w:gz') as tar:
        tar.add(evidence, arcname=directory.name)
    temporary.replace(archive)
    Path(str(archive) + '.sha256').write_text(f'{digest(archive)}  {archive.name}\n', encoding='utf-8')
    return archive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esbmc', required=True, help='existing modified ESBMC executable; never downloaded or substituted')
    parser.add_argument('--cc', default='cc')
    parser.add_argument('--revision', default='HEAD', help='committed Git revision; uncommitted inputs are not copied')
    parser.add_argument('--wheelhouse', help='optional local wheels for offline dependency setup')
    parser.add_argument('--workdir', default='.verify-equiv-runs/reproduction')
    parser.add_argument('--setup-timeout', type=float, default=600)
    parser.add_argument('--demo-timeout', type=float, default=3600)
    args = parser.parse_args(argv)
    if not all(math.isfinite(n) and n > 0 for n in (args.setup_timeout, args.demo_timeout)):
        parser.error('timeouts must be finite and positive')
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='reproduction-', dir=root))
    evidence = directory / 'evidence'
    evidence.mkdir()
    shutil.copyfile(__file__, evidence / 'reproduce_c_tool.py')
    report = dict(status='INCOMPLETE', created_utc=datetime.now(timezone.utc).isoformat(), request=vars(args),
                  source_repository=str(ROOT), artifacts=str(evidence),
                  isolation='committed independent checkout and fresh venv; host compiler, modified ESBMC and system libraries reused',
                  clean_machine_claim=False, held_out_claim=False, checks={})
    steps = Steps(evidence, isolated_environment(os.environ))
    started = time.monotonic()
    try:
        require(sys.platform.startswith('linux'), 'LINUX_REQUIRED', 'This reproduction entrypoint targets Linux/Codespaces')
        require(sys.version_info >= (3, 10), 'PYTHON_VERSION', 'Python 3.10 or later is required')
        report['tools_before'] = {n: identity(getattr(args, n)) for n in ('esbmc', 'cc')}
        git = identity('git')['path']
        python = str(Path(sys.executable).resolve())
        report['host'] = dict(platform=platform.platform(), machine=platform.machine(), python=sys.version,
                              python_executable=python, git=identity('git'))
        _, commit = steps.run('resolve-commit', [git, 'rev-parse', '--verify', '--end-of-options', args.revision + '^{commit}'], ROOT, args.setup_timeout)
        commit = commit.strip()
        require(len(commit) in (40, 64) and all(c in '0123456789abcdef' for c in commit), 'BAD_REVISION', 'Could not resolve a Git commit')
        report['commit'] = commit
        _, source_status = steps.run('source-status', [git, 'status', '--porcelain'], ROOT, args.setup_timeout)
        report['source_worktree_status'] = source_status
        esbmc, cc = (report['tools_before'][n]['path'] for n in ('esbmc', 'cc'))
        _, help_text = steps.run('esbmc-help', [esbmc, '--help'], ROOT, args.setup_timeout)
        require(all(marker in help_text for marker in ('--equiv-py-target', '--equiv-c-target')),
                'MODIFIED_ESBMC_MARKERS_MISSING', 'Expected modified-ESBMC help markers were not found; no substitute will be installed')
        steps.run('esbmc-version', [esbmc, '--version'], ROOT, args.setup_timeout)
        checkout, venv = directory / 'checkout', directory / 'venv'
        no_hooks = str(directory / 'no-hooks')
        steps.run('clone', [git, '-c', 'core.hooksPath=' + no_hooks, '-c', 'core.autocrlf=false',
                           'clone', '--no-hardlinks', '--dissociate', '--no-checkout', str(ROOT), str(checkout)], ROOT, args.setup_timeout)
        steps.run('checkout', [git, '-c', 'core.hooksPath=' + no_hooks, '-c', 'core.autocrlf=false',
                              'checkout', '--detach', commit], checkout, args.setup_timeout)
        _, actual = steps.run('checkout-commit', [git, 'rev-parse', 'HEAD'], checkout, args.setup_timeout)
        _, clean = steps.run('checkout-clean', [git, 'status', '--porcelain'], checkout, args.setup_timeout)
        require(actual.strip() == commit and not clean.strip(), 'CHECKOUT_MISMATCH', 'Checkout is not clean at the requested commit')
        report['checks']['clean_committed_checkout'] = True
        require((checkout / 'cases/c_tool_demo/run_showcase.py').is_file(), 'REVISION_UNSUPPORTED', 'Selected commit has no unified C demonstration')
        steps.run('source-snapshot', [git, 'archive', '--format=tar.gz', '--output=' + str(evidence / 'source.tar.gz'), 'HEAD'], checkout, args.setup_timeout)
        steps.run('create-venv', [python, '-I', '-m', 'venv', str(venv)], checkout, args.setup_timeout)
        vpython = str(venv / 'bin/python')
        steps.env = isolated_environment(os.environ, venv)
        wheels = evidence / 'wheels'
        wheels.mkdir()
        requirement = checkout / 'tools/find-cond-equiv/requirements.txt'
        shutil.copyfile(requirement, evidence / 'requirements.txt')
        download = [vpython, '-I', '-m', 'pip', '--isolated', '--require-virtualenv', 'download', '--disable-pip-version-check',
                    '--no-cache-dir', '--only-binary=:all:', '--no-deps', '-r', str(requirement), '-d', str(wheels)]
        if args.wheelhouse:
            download += ['--no-index', '--find-links', str(Path(args.wheelhouse).resolve())]
        steps.run('download-pinned-wheels', download, checkout, args.setup_timeout)
        steps.run('install-pinned-wheels', [vpython, '-I', '-m', 'pip', '--isolated', '--require-virtualenv', 'install', '--disable-pip-version-check',
                                          '--no-index', '--no-deps', '--find-links', str(wheels), '-r', str(requirement)], checkout, args.setup_timeout)
        steps.run('dependency-check', [vpython, '-I', '-m', 'pip', '--isolated', '--require-virtualenv', 'check'], checkout, args.setup_timeout)
        steps.run('dependency-freeze', [vpython, '-I', '-m', 'pip', '--isolated', '--require-virtualenv', 'freeze', '--all'], checkout, args.setup_timeout)
        inspect_code = "import json,sys,site,pycparser; print(json.dumps(dict(prefix=sys.prefix,base_prefix=sys.base_prefix,executable=sys.executable,pycparser_version=pycparser.__version__,pycparser_file=pycparser.__file__,user_site_enabled=site.ENABLE_USER_SITE)))"
        _, runtime_text = steps.run('inspect-venv', [vpython, '-I', '-c', inspect_code], checkout, args.setup_timeout)
        runtime = json.loads(runtime_text)
        inspect_venv(runtime, venv)
        report['runtime'] = runtime
        report['checks']['fresh_venv_dependency'] = True
        steps.run('demo-unit-tests', [vpython, '-I', '-m', 'unittest', 'discover', '-s', 'cases/c_tool_demo', '-p', 'test_showcase.py', '-v'], checkout, args.setup_timeout)
        outcome, _ = steps.run('demo', [vpython, '-I', 'cases/c_tool_demo/run_showcase.py', '--esbmc', esbmc,
                                        '--cc', cc, '--workdir', str(evidence / 'demo')], checkout, args.demo_timeout, check=False)
        require(not outcome['timed_out'], 'DEMO_TIMEOUT', 'Isolated demo exceeded its time budget')
        demo = json.loads((evidence / 'demo/results.json').read_text(encoding='utf-8'))
        report['demo_overview'] = inspect_demo(demo, evidence)
        require(outcome['returncode'] == 0, 'DEMO_FAILED', 'Demo process did not finish successfully')
        report['checks']['demo_ready_8_of_8'] = True
        _, final_status = steps.run('checkout-final-status', [git, 'status', '--porcelain'], checkout, args.setup_timeout)
        require(not final_status.strip(), 'CHECKOUT_CHANGED', 'Reproduction modified committed checkout inputs')
        report['tools_after'] = {n: identity(report['tools_before'][n]['path']) for n in ('esbmc', 'cc')}
        require(report['tools_before'] == report['tools_after'], 'TOOL_CHANGED', 'Compiler or ESBMC changed during reproduction')
        report['checks'].update(checkout_unchanged=True, tools_unchanged=True)
        report['status'] = 'READY'
    except (Failure, OSError, ValueError, KeyError, TypeError) as exc:
        report['diagnostic'] = dict(code=getattr(exc, 'code', 'REPRODUCTION_ERROR'), message=str(exc))
    report.update(elapsed_seconds=round(time.monotonic() - started, 3), steps=steps.records)
    save(evidence / 'results.json', report)
    overview = ['# C 工具独立环境复现', '', f"结果：**{report['status']}**", '',
                '范围：独立的已提交源码副本与新 Python venv；复用主机编译器、修改版 ESBMC 和系统库。',
                '这不是全新主机、容器或独立盲测结果。', '', f"提交：{report.get('commit', '尚未解析')}", '']
    if report.get('demo_overview'):
        overview += [f"[打开本次统一演示]({report['demo_overview']})", '']
    if report.get('diagnostic'):
        overview += [f"诊断：{report['diagnostic']['code']} — {report['diagnostic']['message']}", '']
    overview += ['[执行记录与检查](results.json)；logs/ 保留命令输出。',
                 'source.tar.gz 为提交源码，wheels/ 为此次下载并安装的依赖，SHA256SUMS 用于核对归档内容。',
                 '失败时仅保存已完成的材料；完整 checkout 和 venv 留在归档旁，不包含在压缩包中。', '']
    (evidence / 'README.md').write_text('\n'.join(overview), encoding='utf-8')
    try:
        archive = package_evidence(evidence, directory)
    except (OSError, tarfile.TarError) as exc:
        report.update(status='INCOMPLETE', diagnostic=dict(code='ARCHIVE_FAILED', message=str(exc)))
        save(evidence / 'results.json', report)
        overview[2] = '结果：**INCOMPLETE**'
        overview += ['', '归档失败：' + str(exc)]
        (evidence / 'README.md').write_text('\n'.join(overview), encoding='utf-8')
        archive = None
    print(f"ISOLATED C REPRODUCTION: {report['status']}")
    if report.get('diagnostic'): print(f"Diagnostic: {report['diagnostic']['code']} — {report['diagnostic']['message']}")
    print(f"Open overview: {evidence / 'README.md'}")
    if archive: print(f'Downloadable archive: {archive}')
    return 0 if report['status'] == 'READY' else 2


if __name__ == '__main__':
    sys.exit(main())
