# Bounded array local validation — 2026-09-16

- [Regression](local-regression.txt): **149 passed, no skips**: 20 oracle,
  123 finder/frontend/native/protocol (including 13 new array tests), six demo.
  MSVC compiled known-safe native fixtures; mocked solver records test control
  flow only. No local ESBMC proof was performed.
- New coverage includes opt-in array parameter admission, exact shape/binding,
  mandatory observations, flattened-name collisions, independent initialized
  storage, repeated inputs, multiple arrays, bool arrays and scalar bindings,
  readonly/write restrictions, complete native vectors and witness comparison.
  Same-return/different-array traces affect search entropy and refute an agent
  candidate before solver calls. Known-safe native tests explicitly bypass the
  safety gate for execution comparison only; this is not proof evidence.
- [Actual absent-solver stage](local-negative.txt) yields **3/10**, as expected:
  rejected alias binding, rejected const write and missing solver pass. All ten
  summaries remain UNKNOWN, publish no condition and contain zero native samples.
  Successful proofs, actual bounds/unwind violations and the agent certificate
  are not established without the backend.
- Syntax, contracts, fixture consistency, links and whitespace are checked.
  The historical frozen transfer lock remains untouched. Shared observation
  comparisons changed, so the Codespace command also reruns readonly-table 9/9
  with its separate archive before the new array 10/10 stage.

Formal array 10/10 and the current-engine readonly-table rerun are pending on
the user's existing modified ESBMC. Earlier scalar/table/demo pass counts are
historical and do not certify the new array semantics. The complete M3 cache
state/sequence obligations remain open.

[Commands and semantics](../../../cases/c_bounded_arrays/README.md).
