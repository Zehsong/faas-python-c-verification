# External-source C integration: local validation — 2026-09-16

- [Five tests passed, no skips](local-tests.txt): contract admission and engine
  lock, native fixtures, drift blocking, certificate acceptance gates, and
  preservation of UNKNOWN/exploratory labels in the overview.
- Native fixtures were compiled with MSVC. All values 0..255 plus powers of two,
  one-less-than-powers, high-bit and alternating-bit boundaries were checked
  against independent Python reference values. These tests restore a test-only
  safety marker for reviewed bounded loops; this is not ESBMC safety evidence.
  The experiment runner never bypasses the safety gate.
- [Actual missing-solver invocation](local-negative.txt): INCOMPLETE 0/5 required,
  all six discovery reports UNKNOWN with SOLVER_NOT_FOUND, zero solver queries
  and native discovery samples. Native compilation succeeds. The five required
  plus one exploratory rows remain present; no success is inferred from tests.
- The local failure archive passes [internal/sidecar hash and overview-link checks](archive-check.txt).
- Frozen files match committed baseline `7cc44b5` after LF normalization. The
  source adapters and search/proof engine are unchanged; the historical scalar
  transfer lock is preserved. This is a new external-source integration stage,
  not a rerun or repair of that historical experiment.

Formal ESBMC execution is pending in Codespace. This stage uses the existing
modified binary; no stock replacement was installed. The known algorithms and
authored reference functions are not an independent blind evaluation. See the
[source/adaptation record and fixed schedule](../../../cases/c_external_bits/README.md).
