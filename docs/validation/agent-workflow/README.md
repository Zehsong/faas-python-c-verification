# Local agent-workflow validation

2026-09-15, Windows/MSVC C11, bundled Python. No local ESBMC installation.

- Initial regression: original oracle tests 20/20 and finder tests 66/66 (49
  existing plus the first 17 agent tests), no skips. Command was the local
  ignored `.verify-equiv-runs/prime-local-test.cmd`, which configures MSVC, sets
  `FINDER_CC`/`CACHE_REPLAY`, and runs both unittest discovery suites.
- Final targeted run: **21/21 agent tests**, no skips, after adding four further
  contract/budget/drift checks. Exact command after compiler environment setup:
  `python -m unittest discover -s tools/find-cond-equiv -p test_agent_workflow.py -v`.
  [Captured output](local-tests.txt). There are 90 distinct tests across these
  completed runs; this is not a claim that the final log alone contains 90 tests.
- C condition-tree evaluation was checked against real native execution on
  0..127 and UINT32_MAX. Session tests compile/replay the real prime model, with
  explicitly mocked proof responses where needed to test protocol transitions.
  Mock responses are not ESBMC certificates.
- Missing-solver smoke: `python cases/agent_workflow/run_checks.py` with
  `--cc` set to MSVC and `--esbmc missing-agent-test-esbmc` returned **2**, as
  expected. All sessions remained UNKNOWN; the intentional missing-solver
  control alone passed, producing **1/8**. [Captured output](missing-solver.txt).
- `py_compile` checked the new Python modules, and Git Bash `-n` checked the
  acceptance script. Relative documentation links and `git diff --check` passed.

At the time of these local tests, formal acceptance was pending. The user later
reported **8/8 passed** in Codespace; see [the result transcript](user-reported-results.md).
To reproduce that suite:

```bash
bash cases/agent_workflow/test_agent.sh /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Expected **8/8**, including one intentional UNKNOWN control. This tests the
protocol and proof boundaries with scripted proposals, not autonomous discovery.
