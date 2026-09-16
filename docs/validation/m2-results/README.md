# M2 result-contract local validation — 2026-09-16

- [Full regression](local-regression.txt): 20 oracle and 100 finder/protocol/native
  tests passed, no skips (120 distinct tests, including 13 new result controls).
- [Final targeted run](local-targeted.txt): 13 result tests passed, followed by
  the real acceptance runner with an intentionally absent ESBMC. Its 3/10 is
  expected: only empty-domain, unsupported-input and missing-solver controls pass.
  Positive proofs, safety/unwinding violations and the agent partial certificate
  are not established by a missing executable.
- Environment: Windows, MSVC native compiler, bundled Python and pycparser. No
  actual ESBMC proof was run locally. Mocked query certificates test reporting
  only; an actual Python child process tests timeout handling and termination.
- New coverage includes v1 schema shape/proof invariants, domain nonemptiness,
  EXACT false versus empty domain, partial-union fallback, complement/presentation
  binding, agent best versus latest result, stale evidence, rejection artifacts,
  distinct query/time budgets, timeout/unwinding/non-target-property diagnostics,
  and human report content. Diagnostic parsing does not infer unwinding failure
  merely from an artifact directory containing the word 'unwind'.
- Existing scalar/cache/prime/agent controls remain in the full regression. The
  frozen transfer-stage tests are intentionally not rerun against the changed
  M2 engine; their hash lock remains unchanged and requires its old checkout.

Following these local checks, the user reported **M2 RESULT ACCEPTANCE: 10/10
passed** from Codespace. [Transcript and archive paths](user-reported-results.md).
This is separate user-reported evidence; no local formal rerun or independent
archive inspection accompanies it. Historical scalar/transfer 8/8 results still
belong to their earlier engine versions.
See [result format, scope and commands](../../RESULT_FORMAT.md).
