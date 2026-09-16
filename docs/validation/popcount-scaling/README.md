# Population-count scaling: local validation — 2026-09-16

- [11 tests passed, no skips](local-tests.txt): six new schedule/measurement
  controls plus the five existing external-integration controls. New checks
  cover reversed repetitions, contract-only domain changes, admission at every
  width, timeout versus infrastructure failure accounting, engine-drift blocking,
  and separate measurement/certificate labels. Existing native reference checks
  reran with MSVC. Synthetic reports in unit tests are not formal evidence.
- [Actual missing-solver execution](local-negative.txt) attempts all ten scheduled
  runs with a real native compiler. All ten publish UNKNOWN/SOLVER_NOT_FOUND,
  zero queries and zero native discovery samples. The overall measurement stage
  remains INCOMPLETE 0/10, with zero certificates; absence of a solver is not
  treated as an ordinary scaling timeout.
- The local failure archive passes [all internal/sidecar hash and overview-link checks](archive-check.txt).
- The two C files, original acceptance runner, original contracts, frozen engine
  and both historical lock files are unchanged. Generated contracts differ from
  the full-width template only by name and input upper bound.

Formal measurements are now [user reported](user-reported-results.md): 10/10
valid runs and 8/10 full-domain certificates, with r2-b8 explicitly EXACT.
The other per-width outcomes, timings and raw archive remain uninspected. The
earlier user-reported 32-bit timeout is [separate evidence](../c-external-bits/user-reported-results.md).
No performance threshold, speedup or ten-run proof claim follows from local
checks. [Fixed protocol](../../../cases/c_external_bits/SCALING.md).
