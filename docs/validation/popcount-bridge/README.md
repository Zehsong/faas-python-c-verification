# Intermediate-program bridge: local validation — 2026-09-16

- [Seven local tests passed without skips](local-tests.txt). Composition requires
  all three ordered edges, all identity gates, safety, EXACT and full-domain
  post-checks. Missing/false identities, UNKNOWN/PARTIAL, changed source identity,
  domain mismatch, bridge-byte mismatch and binding mismatch are rejected.
  An empty endpoint lock is rejected. Synthetic certificates are unit fixtures,
  not formal evidence.
- Native MSVC checks compare all proposed nodes with Python bit counts on
  0..255, all 32 powers of two, full-width patterns and deterministic random
  inputs. The deliberately wrong program differs on every byte input. Reviewed
  bounded loops use a test-only restored safety marker for native checking;
  the experiment itself never bypasses backend safety obligations.
- [Actual missing-solver run](local-negative.txt) keeps all four UNKNOWN reports,
  zero queries/native discovery samples, INCOMPLETE, zero certified links and
  UNKNOWN endpoint equivalence. The negative control also remains unestablished;
  missing tools cannot pass it or publish a composed endpoint claim.
- [Archive hash and overview-link checks](archive-check.txt) pass for the local
  missing-solver evidence.
- Original endpoint text is pinned to `129df96` and copied byte-for-byte into
  each run. The 17-file proof/search engine lock is unchanged. The wrapper uses
  the existing C/JSON frontend for every edge; no assumptions or algebraic
  lemmas are inserted. Existing core regression was not rerun for this wrapper.

Formal execution is now [user reported](user-reported-results.md): RECORDED,
two certified edges, endpoint UNKNOWN and mutant rejected=True. The overview
identifies only the middle edge as UNKNOWN/SOLVER_TIMEOUT; raw logs are uninspected. No successful full-width composition or speedup
has been measured locally. [Protocol](../../../cases/c_popcount_bridge/README.md).
