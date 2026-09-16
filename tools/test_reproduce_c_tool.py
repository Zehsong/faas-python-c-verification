"""Reproduction lifecycle tests; simulated READY is never formal proof evidence."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import reproduce_c_tool as repro


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.silence = contextlib.redirect_stdout(io.StringIO())
        self.silence.__enter__()
        self.addCleanup(self.silence.__exit__, None, None, None)

    def test_environment_excludes_inherited_python_pip_and_git_routing(self):
        env = repro.isolated_environment(dict(PATH='base', PYTHONPATH='old', PYTHONHOME='old',
                                             VIRTUAL_ENV='old', PIP_INDEX_URL='private', GIT_DIR='old', LIB='compiler'), self.root)
        for name in ('PYTHONPATH', 'PYTHONHOME', 'PIP_INDEX_URL', 'GIT_DIR'):
            self.assertNotIn(name, env)
        self.assertEqual(env['LIB'], 'compiler')
        self.assertEqual(env['VIRTUAL_ENV'], str(self.root))
        self.assertTrue(env['PATH'].startswith(str(self.root / 'bin')))

    def test_process_failure_and_timeout_keep_logs(self):
        work = self.root / 'evidence'
        work.mkdir()
        steps = repro.Steps(work, repro.isolated_environment(os.environ))
        for name, code, timeout in (('exit', 'raise SystemExit(7)', 10), ('timeout', 'import time; time.sleep(20)', .05)):
            with self.assertRaises(repro.Failure):
                steps.run(name, [sys.executable, '-I', '-c', code], self.root, timeout)
        self.assertEqual(steps.records[0]['returncode'], 7)
        self.assertTrue(steps.records[1]['timed_out'])
        self.assertEqual(len(list((work / 'logs').glob('*.txt'))), 2)
        self.assertTrue((work / 'steps.json').is_file())

    def test_venv_and_dependency_locations_are_required(self):
        venv = self.root / 'venv'
        venv.mkdir()
        (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n', encoding='utf-8')
        module = venv / 'pycparser.py'
        module.write_text('# test fixture\n', encoding='utf-8')
        info = dict(prefix=str(venv), base_prefix=str(self.root), pycparser_file=str(module), user_site_enabled=False)
        repro.inspect_venv(info, venv)
        for change in (dict(base_prefix=str(venv)), dict(prefix=str(self.root)),
                       dict(pycparser_file=str(self.root / 'outside.py')), dict(user_site_enabled=True)):
            with self.assertRaises(repro.Failure): repro.inspect_venv({**info, **change}, venv)
        (venv / 'pyvenv.cfg').write_text('include-system-site-packages = true\n', encoding='utf-8')
        with self.assertRaises(repro.Failure): repro.inspect_venv(info, venv)

    def test_demo_requires_all_checks_and_a_local_overview(self):
        overview = self.root / 'demo'
        overview.mkdir()
        (overview / 'README.md').write_text('test only', encoding='utf-8')
        report = dict(ready=True, passed=8, total=8, engine_unchanged=True, inputs_unchanged=True,
                      tools_unchanged=True, artifacts=str(overview))
        self.assertEqual(repro.inspect_demo(report, self.root), 'demo/README.md')
        for changed in (dict(ready=False), dict(passed=7), dict(total=9), dict(engine_unchanged=False),
                        dict(inputs_unchanged=False), dict(tools_unchanged=False), dict(artifacts=str(self.root / 'missing'))):
            with self.assertRaises(repro.Failure): repro.inspect_demo({**report, **changed}, self.root)

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_real_clone_uses_commit_and_excludes_dirty_untracked_files(self):
        source, evidence = self.root / 'source', self.root / 'evidence'
        source.mkdir()
        evidence.mkdir()
        steps = repro.Steps(evidence, repro.isolated_environment(os.environ))
        git = shutil.which('git')
        steps.run('init', [git, 'init'], source)
        path = source / 'input.txt'
        path.write_text('committed\n', encoding='utf-8')
        steps.run('add', [git, 'add', 'input.txt'], source)
        steps.run('commit', [git, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                             '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=' + str(self.root / 'no-hooks'),
                             'commit', '-m', 'fixture'], source)
        _, commit = steps.run('revision', [git, 'rev-parse', 'HEAD'], source)
        path.write_text('uncommitted\n', encoding='utf-8')
        (source / 'untracked.txt').write_text('not part of release', encoding='utf-8')
        checkout = self.root / 'checkout'
        steps.run('clone', [git, 'clone', '--no-hardlinks', '--dissociate', '--no-checkout', str(source), str(checkout)], source)
        steps.run('checkout', [git, '-c', 'core.hooksPath=' + str(self.root / 'no-hooks'), 'checkout', '--detach', commit.strip()], checkout)
        self.assertEqual((checkout / 'input.txt').read_text(encoding='utf-8'), 'committed\n')
        self.assertFalse((checkout / 'untracked.txt').exists())
        self.assertEqual(path.read_text(encoding='utf-8'), 'uncommitted\n')

    def fake_steps(self, failure=None):
        """Simulate setup/formal outcomes; no solver or package installer called."""
        def run(steps, name, command, cwd, timeout=600, check=True):
            cwd = Path(cwd)
            record = dict(name=name, command=[str(x) for x in command], cwd=str(cwd), returncode=0, timed_out=False, test_only=True)
            steps.records.append(record)
            text = ''
            if name in ('resolve-commit', 'checkout-commit'): text = 'a' * 40 + '\n'
            if name == 'source-status': text = ' M intentionally-dirty-source.txt\n'
            if name == 'esbmc-help': text = '--equiv-py-target --equiv-c-target'
            if name == 'clone':
                checkout = Path(command[-1])
                (checkout / 'cases/c_tool_demo').mkdir(parents=True)
                (checkout / 'cases/c_tool_demo/run_showcase.py').write_text('# test only', encoding='utf-8')
                (checkout / 'tools/find-cond-equiv').mkdir(parents=True)
                (checkout / 'tools/find-cond-equiv/requirements.txt').write_text('pycparser==3.0\n', encoding='utf-8')
            if name == 'source-snapshot': (steps.evidence / 'source.tar.gz').write_bytes(b'test-only archive placeholder')
            if name == 'create-venv':
                venv = Path(command[-1])
                (venv / 'bin').mkdir(parents=True)
                (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n', encoding='utf-8')
                (venv / 'pycparser.py').write_text('# test only', encoding='utf-8')
            if name == 'download-pinned-wheels': (steps.evidence / 'wheels/mock.whl').write_bytes(b'test-only wheel placeholder')
            if name == 'inspect-venv':
                venv = Path(command[0]).parent.parent
                text = json.dumps(dict(prefix=str(venv), base_prefix=str(self.root),
                                       pycparser_file=str(venv / 'pycparser.py'), user_site_enabled=False))
            if name == 'demo':
                work = steps.evidence / 'demo'
                work.mkdir()
                (work / 'README.md').write_text('TEST ONLY: no formal execution', encoding='utf-8')
                repro.save(work / 'results.json', dict(ready=failure != 'demo', passed=8, total=8, engine_unchanged=True,
                                                      inputs_unchanged=True, tools_unchanged=True, artifacts=str(work)))
            if name == 'checkout-final-status' and failure == 'checkout': text = ' M tools/changed.py\n'
            if name == 'esbmc-help' and failure == 'solver': text = 'unrecognized build'
            if name == 'download-pinned-wheels' and failure == 'dependency':
                raise repro.Failure('STEP_FAILED', 'test dependency failure')
            return record, text
        return run

    def test_lifecycle_ready_and_failures_always_package_evidence(self):
        for failure in (None, 'demo', 'checkout', 'solver', 'dependency', 'tools'):
            target = self.root / str(failure)
            calls = {}
            def identity(value):
                calls[value] = calls.get(value, 0) + 1
                return dict(path=str(value), sha256='changed' if failure == 'tools' and value == 'cc' and calls[value] > 1 else 'test-only')
            with patch.object(repro.sys, 'platform', 'linux'), patch.object(repro.platform, 'platform', return_value='test host'), \
                    patch.object(repro, 'identity', side_effect=identity), \
                    patch.object(repro.Steps, 'run', self.fake_steps(failure)):
                rc = repro.main(['--esbmc', 'mock-esbmc', '--workdir', str(target), '--wheelhouse', str(self.root / 'wheels')])
            self.assertEqual(rc, 0 if failure is None else 2)
            result_path = next(target.glob('*/evidence/results.json'))
            report = json.loads(result_path.read_text(encoding='utf-8'))
            self.assertEqual(report['status'], 'READY' if failure is None else 'INCOMPLETE')
            self.assertFalse(report['clean_machine_claim'])
            archive = next(target.glob('*/*.tar.gz'))
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), Path(str(archive) + '.sha256').read_text()[:64])
            with tarfile.open(archive) as tar:
                self.assertTrue(any(n.endswith('/results.json') for n in tar.getnames()))
                self.assertFalse(any('/venv/' in n or '/checkout/' in n for n in tar.getnames()))
            if failure == 'solver': self.assertFalse(any(s['name'] == 'clone' for s in report['steps']))
            if failure == 'tools': self.assertEqual(report['diagnostic']['code'], 'TOOL_CHANGED')
            if failure is None:
                command = next(s['command'] for s in report['steps'] if s['name'] == 'download-pinned-wheels')
                self.assertIn('--no-index', command)
                self.assertIn('--isolated', command)
                self.assertTrue(all('--require-virtualenv' in s['command'] for s in report['steps']
                                    if s['name'] in ('download-pinned-wheels', 'install-pinned-wheels', 'dependency-check', 'dependency-freeze')))

    def test_missing_tools_fail_before_clone_or_install(self):
        with patch.object(repro.sys, 'platform', 'linux'), patch.object(repro, 'identity', side_effect=repro.Failure('TOOL_NOT_FOUND', 'missing')), \
                patch.object(repro.Steps, 'run') as run:
            rc = repro.main(['--esbmc', 'missing', '--workdir', str(self.root)])
        self.assertEqual(rc, 2)
        run.assert_not_called()
        report = json.loads(next(self.root.glob('*/evidence/results.json')).read_text(encoding='utf-8'))
        self.assertEqual(report['diagnostic']['code'], 'TOOL_NOT_FOUND')

    def test_archive_failure_does_not_leave_ready_overview(self):
        with patch.object(repro.sys, 'platform', 'linux'), patch.object(repro.platform, 'platform', return_value='test host'), \
                patch.object(repro, 'identity', side_effect=lambda value: dict(path=str(value), sha256='test-only')), \
                patch.object(repro.Steps, 'run', self.fake_steps()), patch.object(repro, 'package_evidence', side_effect=OSError('disk failure')):
            rc = repro.main(['--esbmc', 'mock-esbmc', '--workdir', str(self.root)])
        self.assertEqual(rc, 2)
        overview = next(self.root.glob('*/evidence/README.md')).read_text(encoding='utf-8')
        self.assertIn('**INCOMPLETE**', overview)
        self.assertNotIn('**READY**', overview)


if __name__ == '__main__':
    unittest.main()
