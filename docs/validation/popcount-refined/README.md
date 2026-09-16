# Refined byte replacement chain: local validation — 2026-09-16

- [11 local tests pass without skips](local-tests.txt): the original seven
  composition/native controls plus four refined-chain checks. All six edge
  certificates are required, the original default node list is retained, the
  full domain and bindings are checked, drift blocks execution, and a failed
  post-check stays visible independently of discovery status. Synthetic
  certificates are unit fixtures, never solver evidence.
- Native MSVC execution checks mixed implementations against Python bit counts
  on every byte input, all powers of two, full-width patterns and deterministic
  random words. As in the original native tests, a test-only safety marker is
  restored for inspected bounded loops. Formal execution never uses that bypass.
- [Actual missing-solver refined run](local-negative.txt) retains seven UNKNOWN
  reports (six edges plus mutant), zero solver queries and native discovery
  samples, INCOMPLETE and UNKNOWN endpoint equivalence. The mutant control cannot
  pass without its actual proof checks. Per-edge CSV is printed and archived.
- [Default three-edge negative regression](local-default-regression.txt) retains
  its four runs and 30/120/96 budgets, with UNKNOWN and zero queries/samples.
- [Local archive hash and overview-link checks](archive-check.txt) pass.
- The shared composition wrapper accepts the new six-edge protocol while
  retaining its original three-edge default. Core search/proof files, endpoint
  programs, original bridges and frozen locks are unchanged. Three mixed C
  programs are new proposals, not automatically accepted transformations.

The [original bridge summary and supplied overview](../popcount-bridge/user-reported-results.md)
report two certified links and an unresolved middle link. The user subsequently
reported **6/6 certified links, endpoint PROVED and mutant rejected=True** for
this refinement. [Supplied summary and CSV](user-reported-results.md) are recorded
separately from these local controls; the raw archive remains uninspected.
[Protocol](../../../cases/c_popcount_bridge/REFINED.md).
