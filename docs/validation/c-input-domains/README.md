# Input domain validation — 2026-09-16

This is local Windows/MSVC validation, not an ESBMC proof run. The user subsequently reported
**13/13 acceptance passed; inputs/tools unchanged=True** after `5446b31`.
[Reported summary and archive paths](user-reported-results.md) are separate from
these local controls; the raw archive remains independently uninspected.

- [Full finder regression](local-regression.txt): 145 tests passed, no skips.
- [Final domain controls](local-domain-tests.txt): 15 tests passed, no skips;
  includes one additional native Boolean-guard check after the full regression.
  This is 146 distinct finder tests across the two runs, not 160.
- [Evidence assembly](local-assembly.txt): one cross-platform dependency-snapshot
  test passed. It catches Windows path separators omitting the new domain module.
- [Oracle tests](local-oracle.txt): 15 passed, five existing cache native-replay
  tests skipped because CACHE_REPLAY was not configured. These are not five passes.
- [Actual missing-ESBMC integration](local-negative.txt): process exit 2, expected
  1/13 (only the missing-solver control passes). All thirteen reports remain
  UNKNOWN with zero solver queries and zero native samples. Neither contradictory
  constraints nor an empty default seed list is promoted to EMPTY_DOMAIN without
  solver evidence. Inputs/tools unchanged=True.
- [Archive checks](archive-check.txt): all 13 overview links exist, the new domain
  dependency is copied, 618/618 internal SHA256 checks and the archive sidecar pass.
  This local archive contains two negative runs, including the earlier assembly
  attempt; the current root results.json selects the corrected latest run.
- Bash syntax and changed documentation links were checked. Historical engine
  lock files, original popcount endpoints and the core search algorithm are unchanged.
  The contract/backend implementation changed, so historical frozen experiments
  must be reproduced in their original checkout, not relabeled as current-engine runs.

Domain controls cover full/partial type defaults, legacy schema rejection,
unknown fields/code injection/tree limits, all/any/not and flattened array fields,
consistent domain guards for all query kinds, solver-only empty-domain evidence,
missing-solver native gating, direct native rejection of unsafe out-of-domain
inputs, agent seed rejection and contract-identity invalidation.

Mocked verdicts and native execution are controls only. The reported formal stage includes eight positive finder cases, an empty-domain
case, two unsafe controls, a missing-solver control and a scripted agent case.
Its result does not certify subsequent implementation changes.

[Run the 13-check acceptance](../../../cases/c_input_domains/README.md).
