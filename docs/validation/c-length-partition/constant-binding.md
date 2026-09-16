# Constant-bound length harness: local validation — 2026-09-17

The [previous formal attempt](user-reported-results.md) remained UNKNOWN for
copy8, including a timeout within the n=4 subdomain. This patch changes only
the representation of fixed length in each partition harness: initialize it
with UINT32_C(k) instead of nondet_uint32_t(), while retaining the exact n==k
partition conjunct and original domain constraints. The union still needs a
symbolic coverage proof. Every other input remains nondeterministic.

The shared backend has a harness-generation hook whose default delegates to
the existing builder unchanged. Only the C scalar/array adapter uses a fixed
binding during a partition query; finally cleanup restores symbolic generation,
including on exceptions. Direct, safety, feasibility, expected and native-probe
generation remain unchanged. Source models and original C/JSON fixtures are
not rewritten. Query reserves, timeouts and unwind/safety checks remain active.

- [Full finder regression](constant-regression.txt): 172 tests pass without skips.
  Includes four additional controls for exact binding/condition agreement,
  exception cleanup, unchanged ordinary harnesses, and native compilation and
  execution of all nine specialized copy8 harnesses on deterministic full-width
  sample vectors. A deliberate candidate tail mutation must trigger the generated
  observation assertion. Native tests are construction controls, not proofs.
- Existing scripted-oracle controls still test coverage, missing parts,
  counterexamples, budgets and conservative composition. Generated subqueries
  now also require every non-length input to remain nondeterministic.
- One evidence-assembly check passes. Documentation links, Bash syntax and diff
  whitespace checked; historical frozen locks and original C/JSON inputs unchanged.

No local modified ESBMC is available. The user subsequently reports
[11/11 acceptance after `0059a05`](../c-array-capacity/accepted-results.md), clearing
the capacity gate at user-reported evidence level. Per-query results and timings
are not supplied, so the performance explanation remains a hypothesis and no
speedup is claimed. This patch does not add partial-region extraction from an
incomplete length partition.
