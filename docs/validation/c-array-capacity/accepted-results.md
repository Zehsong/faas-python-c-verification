# User-reported capacity acceptance after constant binding — 2026-09-17

Reported after implementation `0059a05`:

```text
EXACT: n != 0
Phase: READY; goal reached: True
Latest proposal: EXACT
agent-capacity: PASS
C ARRAY CAPACITY ACCEPTANCE: 11/11 passed; inputs/tools unchanged=True
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-UBFCuj/checks-krlvafao/README.md
Agent report: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-UBFCuj/checks-krlvafao/agent-capacity/session-s8f89fom/report.md
Evidence directory: /home/codespace/equiv-evidence/c-array-capacity-20260916T160331Z-klh0qp
Downloadable archive: /home/codespace/equiv-evidence/c-array-capacity-20260916T160331Z-klh0qp.tar.gz
```

This clears the eleven-check capacity acceptance gate at user-reported evidence
level. The unchanged acceptance script requires copy8 discovery EXACT and an
independent post-check against true; all eleven passing therefore includes that
check. The n != 0 output above belongs to agent-capacity, not copy8. Negative
controls intentionally require UNKNOWN or EMPTY_DOMAIN, not equivalence.

The supported slice is schema 3 fixed uint32_t/bool arrays of capacity 1..64,
at most 128 flattened input values and four logical parameters, explicit logical
lengths, full physical-array observations and checked finite length decomposition.
All claims remain relative to the contract, no-alias memory model, safety and
complete loop unwinding. No arbitrary inputs, unbounded loops or autonomous-agent
performance claim follows from this acceptance.

Provenance: supplied console summary, not a local formal rerun or independently
audited raw archive. Per-query timings, whether this run used the fallback,
individual partition outcomes and run-specific binary identity remain uninspected.
Do not claim a measured speedup or attribute success to a specific internal path
without those records. Original failed attempts remain separately documented:
[initial capacity run](user-reported-results.md) and
[assumption-only partition run](../c-length-partition/user-reported-results.md).

The user asked to stop for the day after this milestone. This handoff records
the result only; no additional feature work or test run was started.
