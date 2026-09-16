# Checked logical-length partition: local validation — 2026-09-16

This page records the initial `441fd89` implementation's local checks. Its
subsequent [user-reported run](user-reported-results.md) remains 10/11 with a
copy8 timeout at n=4. See [constant-binding validation](constant-binding.md)
for the next harness refinement; do not treat the earlier 168 tests as its rerun.

The prior user-reported capacity run is [10/11](../c-array-capacity/user-reported-results.md).
copy8 safety passed; whole-domain equal and later different queries timed out.
No original contract, C source, unwind limit, timeout or acceptance target changes.

- [Finder regression](local-regression.txt): **168 tests passed without skips**,
  using Windows MSVC for native controls. Ten new scripted-oracle controls check
  coverage and all-part requirements, full observations and element ranges,
  incomplete partitions, counterexample propagation for equality/inequality,
  query reserves and deadlines, mandatory safety, timeout-only activation,
  bounded partition admission, evidence persistence and end-to-end result format.
  Scripted PROVED/EXACT lines in this log are protocol tests, not formal proofs.
- One evidence-assembly test passes, verifying every tool dependency in the
  current platform fingerprint is copied byte-for-byte into the evidence tree.
- [Actual missing-solver run](local-negative.txt) exits 2 as required: **1/11**
  is solely the expected missing-solver control. Every result remains UNKNOWN,
  with no certified condition, zero solver queries and zero native samples;
  inputs/tools unchanged=True. No partition is launched without established safety.
- Negative-run report links, documentation links, Bash syntax and diff whitespace
  are checked. Historical frozen experiment locks are unchanged.

The fallback tries one explicit logical-length field with 2..17 admissible
values after a direct equal/different timeout. A coverage query and all parts
must be PROVED to compose PROVED; individual conditions still retain the full
original domain constraints, element types and observations. Missing coverage,
budget exhaustion and unresolved parts cannot certify the parent query.

All actual backend calls consume the existing shared budgets. Compositions are
recorded separately from solver calls, so query metrics count actual executions.
No cross-query/session certificate cache or automatic loop induction is added.
The direct timed-out attempt is retained in evidence, even if decomposition
later succeeds. Native replay and scripted controls never replace formal proofs.

Formal acceptance of this patch is **pending** in Codespace with the user's
modified ESBMC. Run the unchanged eleven-case target with:

```bash
bash cases/c_array_capacity/test_capacity.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Do not report 11/11 or claim copy8 is solved until that run supplies evidence.
