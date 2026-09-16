# Popcount timeout comparison: local validation — 2026-09-16

- [14 tests passed without skips](local-tests.txt): the 11 existing native,
  integration and scaling controls plus three new timeout-protocol controls.
  They check the unchanged default ten-run schedule, the 30/120/120/30-second
  comparison order, fixed 300-second/96-query limits, absence of hypotheses,
  and the four-run denominator/guide under engine drift. MSVC native checks
  rerun for the original fixtures; synthetic reports are not formal evidence.
- [Actual missing-solver comparison](local-negative.txt) retains all four UNKNOWN
  rows, zero queries and native discovery samples, INCOMPLETE 0/4 and zero
  certificates. The terminal prints the complete CSV including failure reasons.
- [Default-protocol negative regression](local-default-regression.txt) retains ten
  UNKNOWN rows with 30-second timeouts and unchanged 300-second/96-query limits;
  zero queries/samples and the ten-row CSV/overview are checked.
- [Local archive hashes and overview links](archive-check.txt) pass.
- The reusable measurement wrapper now accepts a fixed protocol selected by
  its entrypoint. The original default width experiment keeps its schedule,
  contracts and budgets. Search/proof code, C fixtures and frozen locks are
  unchanged. No production backend or finder parameters change except the
  explicitly declared per-run timeout in the new comparison.

Formal measurements await the user's existing modified ESBMC in Codespace.
The [user-supplied earlier CSV](../popcount-scaling/user-reported-metrics.csv)
motivates this test but is not a result of the new protocol. No budget sensitivity
or performance improvement is claimed before execution.
[Protocol](../../../cases/c_external_bits/BUDGET.md).
