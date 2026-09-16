# Read-only C tables: local validation — 2026-09-16

- [Full regression](local-regression.txt): 136 tests passed without skips:
  20 oracle, 110 finder/frontend/protocol/native (including ten new table tests),
  and six demo assembly tests. MSVC compiled the native fixtures on Windows.
- New controls cover constant initialization, aggregate size limits, type/scope
  checks, array decay/address/write rejection, source identity, report memory
  scope and UNKNOWN safety gating. Known safe fixtures are exhaustively compared
  to a Python reference on their small declared domains in native tests, with an
  explicit test-only gate bypass. These are native checks, not formal proofs.
- [Actual missing-solver stage](local-negative.txt): **2/9**, as expected. Only
  rejected writes and the explicit missing-solver control pass. Positive proofs,
  actual bounds/unwinding violations and the agent certificate are not established
  without ESBMC. Reports retain UNKNOWN and zero native samples.
- The new table stage invokes the generic C entry point. Expected formulas are
  checked separately after discovery; one agent proposal is scripted. No special
  prime Python backend or table-specific predicate search was added.
- Source syntax, fixture/contract consistency, Bash syntax, links and whitespace
  are checked. Existing transfer locks remain unchanged; the frozen transfer
  stage requires its historical checkout and is not rerun on the changed frontend.

There is no local ESBMC installation. Formal **9/9** remains pending on the
user's existing modified ESBMC. Historical scalar/demo/M2 successes do not certify
the newly admitted memory reads. No scaling, autonomous-agent or blind-case claim
follows from this implementation.

[Scope and Codespace commands](../../../cases/c_readonly_tables/README.md).
