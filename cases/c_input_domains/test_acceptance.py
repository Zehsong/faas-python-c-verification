"""Cross-platform evidence assembly control; no mocked formal verdicts."""
from pathlib import Path
import tempfile
import unittest

import run_checks


class EvidenceTests(unittest.TestCase):
    def test_snapshots_new_dependency_using_real_platform_fingerprint(self):
        config=dict(case='c',contract=str(run_checks.CASE/'ordered_full.json'),
                    esbmc='intentionally-missing-domain-esbmc',cc='intentionally-missing-domain-cc')
        identity=run_checks.workflow.fingerprint(config)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)
            run_checks.snapshot_engine(identity,target)
            files=[p for p in identity['files'] if Path(p).parts[0]=='tools']
            self.assertTrue(files)
            for relative in files:
                self.assertEqual((target/relative).read_bytes(),(run_checks.ROOT/relative).read_bytes())
            self.assertTrue((target/'tools/find-cond-equiv/c_input_domain.py').is_file())
            self.assertFalse((target/'pycparser').exists())


if __name__=='__main__':
    unittest.main()
