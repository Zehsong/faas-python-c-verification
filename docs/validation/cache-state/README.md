# Cache state local validation — 2026-09-16

- [Regression log](local-regression.txt): **157 passed without skips**: 20 oracle,
  131 finder/frontend/native/protocol (eight new cache-state tests), six demo.
  MSVC compiled real native fixtures; mock solver responses exercise gates and
  resumed sessions only and are not formal proof evidence.
- Tests cover both required obligations, revocation of restored evidence,
  REFUTED/UNKNOWN gating before any sample/search, missing-solver agent start,
  typed full post-state validation, missing-evidence summary rejection, explicit
  observation/sequence limits, fresh per-input private caches, and both families'
  agent resume paths. Existing known-safe native fixture tests explicitly bypass
  the new proof gate; no production fallback bypass was added.
- Initial regression found two old missing-solver tests expecting native samples
  (including 512 config samples). They were updated to require zero under the new
  gate; the complete regression then passed. Old historical results are unchanged.
- [Actual missing-solver stage](local-negative.txt): expected **2/14**, only the
  two missing-solver controls pass. All 14 summaries remain UNKNOWN without
  conditions or native samples. Real REFUTED invalid-state controls and positive
  certificates require the modified ESBMC and are not established locally.
- Fixture/source/compiler identities, syntax, local documentation links and
  whitespace checked; frozen transfer files remain untouched.

[Codespace commands and proof boundaries](../../../cases/cache_state/README.md).
The user subsequently reported **14/14 passed; inputs/tools unchanged=True**.
[Transcript and archive paths](user-reported-results.md). The raw archive and
actual run identities have not been independently inspected. Array 10/10 is separately
[user reported](../c-bounded-arrays/user-reported-results.md); its raw archive is
uninspected and the requested readonly-table rerun remains unreported.
