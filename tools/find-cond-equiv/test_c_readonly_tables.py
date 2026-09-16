"""Read-only table admission and native/protocol controls, not solver proofs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from c_scalar_contract import Contract, Source
from c_scalar_backend import bind_contract
from find_c_conditions import parse_args
from condition_runner import run
import agent_workflow as workflow

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "cases/c_readonly_tables"


class ReadonlyTableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, body):
        path = self.root / "source.c"
        path.write_text(body, encoding="utf-8")
        return Source(path)

    def test_table_metadata_and_original_body_preserved(self):
        source = self.source('uint32_t f(uint32_t n) { const uint32_t table[2u] = {7u, 11u}; return table[n]; }')
        self.assertEqual(source.tables, [dict(function="f", name="table", element_type="uint32_t", length=2)])
        self.assertIn('const uint32_t table[2u] = {7u, 11u}; return table[n];', source.namespaced("original"))
        boolean = self.source('bool f(uint32_t n) { const bool table[2] = {false, true}; return table[n]; }')
        self.assertEqual(boolean.tables[0]["element_type"], "bool")

    def test_rejects_incomplete_or_dynamic_or_oversized_tables(self):
        declarations = [
            'const uint32_t t[2u] = {1u};', 'const uint32_t t[1u] = {1u, 2u};',
            'const uint32_t t[] = {1u};', 'const uint32_t t[n] = {1u};',
            'const uint32_t t[0] = {};', 'const uint32_t t[257] = {1u};',
            'const uint32_t t[1u] = {n};', 'const uint32_t t[1u] = {1u + 2u};',
            'const uint32_t t[1u] = {[0] = 1u};', 'const uint32_t t[1u] = {true};',
            'const bool t[1u] = {1u};', 'const uint32_t t[1u][1u] = {{1u}};',
            'const uint32_t t[1u];', 'uint32_t t[1u] = {1u};',
            'static const uint32_t t[1u] = {1u};', 'volatile const uint32_t t[1u] = {1u};',
        ]
        for declaration in declarations:
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                self.source('uint32_t f(uint32_t n) { ' + declaration + ' return 0u; }')

    def test_rejects_writes_addresses_and_array_decay(self):
        statements = ['t[0u] = 1u;', 't[0u]++;', 't[0u] += 1u;',
                      'uint32_t v = (uint32_t)t;', 'bool v = (bool)t;',
                      'bool v = t == t;', 'bool v = !t;', 'uint32_t v = t ? 1u : 2u;',
                      'uint32_t v = (uint32_t)&t[0u];', 'uint32_t v = t[n++];',
                      'uint32_t v = t[true];', 'uint32_t v = t[0u][0u];',
                      'uint32_t v = helper(t);']
        for statement in statements:
            with self.subTest(statement=statement), self.assertRaises(ValueError):
                self.source('uint32_t helper(uint32_t n) { return n; }\n'
                            'uint32_t f(uint32_t n) { const uint32_t t[2u] = {0u, 1u}; '
                            + statement + ' return 0u; }')

    def test_rejects_global_and_parameter_tables(self):
        for body in ('const uint32_t t[1u] = {0u}; uint32_t f(uint32_t n) { return t[n]; }',
                     'uint32_t f(const uint32_t t[1u]) { return t[0u]; }',
                     'uint32_t f(const uint32_t *t) { return t[0u]; }'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.source(body)

    def test_aggregate_table_limit_across_functions(self):
        values = ','.join(['0u'] * 128)
        helper = 'uint32_t helper(uint32_t n) { const uint32_t a[128] = {' + values + '}; return a[n]; }'
        caller = 'uint32_t f(uint32_t n) { const uint32_t b[128] = {' + values + '}; return b[n]; }'
        self.assertEqual(self.source(helper + caller).table_elements, 256)
        with self.assertRaisesRegex(ValueError, '256'):
            self.source(helper + caller + 'uint32_t g(uint32_t n) { const uint32_t c[1] = {0u}; return c[n]; }')

    def test_fixture_admission_scope_and_safety_gating(self):
        for path in CASE.glob('*.json'):
            if path.stem == 'readonly_write':
                with self.assertRaises(ValueError):
                    Contract(path)
                continue
            bound = bind_contract(path)
            args = parse_args(['--contract', str(path), '--esbmc', 'missing-table-test-solver',
                               '--workdir', str(self.root / path.stem)])
            with patch.object(bound, 'prepare'), patch.object(bound, 'replay') as replay:
                report = run(args, bound)
            self.assertEqual(report['status'], 'UNKNOWN')
            replay.assert_not_called()
            tables = report['scope']['memory']['tables']
            self.assertEqual(tables['original'], [])
            self.assertEqual(tables['candidate'][0]['length'], 32)

    def test_local_table_names_cannot_shadow_and_do_not_escape_scope(self):
        statements = [
            'const uint32_t n[1] = {0u}; return 0u;',
            'const uint32_t f[1] = {0u}; return 0u;',
            '{ const uint32_t t[1] = {0u}; } return t[0u];',
            'const uint32_t t[1] = {0u}; { uint32_t t = 1u; } return 0u;',
        ]
        for body in statements:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.source('uint32_t f(uint32_t n) { ' + body + ' }')

    def backend(self, name):
        path = CASE / (name + '.json')
        bound = bind_contract(path)
        args = parse_args(['--contract', str(path), '--esbmc', 'missing-table-test-solver',
                           '--cc', os.environ.get('FINDER_CC', 'cc'), '--workdir', str(self.root)])
        directory = self.root / name
        directory.mkdir()
        return bound(args, directory)

    def test_native_prime_fixtures_exhaustively_on_declared_domains(self):
        def prime(n):
            return n >= 2 and all(n % d for d in range(2, n))
        for name in ('full_31', 'fallback_63', 'truncated_63', 'mutant_31'):
            backend = self.backend(name)
            backend.prepare()
            # TEST ONLY: these known safe fixtures are sampled without claiming proof.
            backend.restore_obligations({'safety': {'status': 'PROVED'}})
            maximum = backend.contract.data['inputs']['n']['max']
            rows = backend.replay([dict(n=n) for n in range(maximum + 1)])
            for row in rows:
                n = row['n']
                candidate = prime(n) and (name != 'truncated_63' or n < 32)
                if name == 'mutant_31' and n == 9:
                    candidate = True
                self.assertEqual((row['r_original'], row['r_cached']), (int(prime(n)), int(candidate)))

    def test_nonprime_uint32_table_and_same_names_native(self):
        data = json.loads((CASE / 'full_31.json').read_text(encoding='utf-8'))
        data['return_type'] = 'uint32_t'
        data['inputs']['n']['max'] = 3
        for side in ('original', 'candidate'):
            path = self.root / (side + '.c')
            path.write_text('uint32_t isprime(uint32_t n) { const uint32_t t[4] = {9u, 7u, 5u, 3u}; return t[n]; }', encoding='utf-8')
            data[side]['source'] = str(path)
        path = self.root / 'contract.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        bound = bind_contract(path)
        args = parse_args(['--contract', str(path), '--cc', os.environ.get('FINDER_CC', 'cc'), '--esbmc', 'missing-table-test-solver'])
        backend = bound(args, self.root)
        backend.prepare()
        backend.restore_obligations({'safety': {'status': 'PROVED'}})  # native test only
        rows = backend.replay([dict(n=n) for n in range(4)])
        self.assertEqual([(r['r_original'], r['r_cached']) for r in rows], [(9,9), (7,7), (5,5), (3,3)])

    def test_table_content_is_part_of_agent_identity(self):
        data = json.loads((CASE / 'mutant_31.json').read_text(encoding='utf-8'))
        for side in ('original', 'candidate'):
            path = self.root / (side + '.c')
            path.write_bytes((CASE / data[side]['source']).read_bytes())
            data[side]['source'] = str(path)
        contract = self.root / 'contract.json'
        contract.write_text(json.dumps(data), encoding='utf-8')
        config = dict(case='c', contract=str(contract), esbmc='missing-table-test-solver', cc=os.environ.get('FINDER_CC', 'cc'))
        before = workflow.fingerprint(config)
        path.write_text(path.read_text(encoding='utf-8').replace('false', 'true', 1), encoding='utf-8')
        self.assertNotEqual(before, workflow.fingerprint(config))


if __name__ == '__main__':
    unittest.main()
