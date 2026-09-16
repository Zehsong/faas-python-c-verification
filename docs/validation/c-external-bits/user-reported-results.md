# User-reported external-source integration — 2026-09-16

Reported after implementation `129df96`:

```text
popcount_8: PASS

popcount_32
 query 000 safety: PROVED
 query 001 feasible: REFUTED
 query 002 equal: UNKNOWN
 query 003 equal: PROVED
 query 004 different: REFUTED
UNKNOWN: None
Outcome: UNKNOWN; domain=NONEMPTY; claim=NO_EQUIVALENCE_CLAIM
Diagnostics: SOLVER_TIMEOUT
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-external-stage/run-mX3Qos/checks-r1gothwq/popcount_32/pair-1lyabm9w/report.md
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-external-stage/run-mX3Qos/checks-r1gothwq/popcount_32/pair-1lyabm9w
popcount_32: NOT ESTABLISHED
EXTERNAL C INTEGRATION: READY (5/5 required; exploratory EXACT=0/1; engine frozen=True)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-external-stage/run-mX3Qos/checks-r1gothwq/README.md
Evidence directory: /home/codespace/equiv-evidence/c-external-bits-20260916T121754Z-TSSEGh
Downloadable archive: /home/codespace/equiv-evidence/c-external-bits-20260916T121754Z-TSSEGh.tar.gz
```

The five required cases were fixed before execution: guarded/raw/positive-domain/
zero-only power-of-two checks and byte-domain population count. The summary
reports that all passed with the frozen engine. Exact formulas, their post-checks,
source/tool identities and the full archive have not been independently opened
here. This is user-reported evidence, not a local formal rerun or blind evaluation.

Full-width population count passed its safety check and established a nonempty
domain, but did not establish equivalence under the fixed query budget/timeout.
The final published status is UNKNOWN with SOLVER_TIMEOUT, not inequivalent.
An individual later equality query returning PROVED does not establish equality
on the entire domain: it concerns the condition of that query. The pasted log
does not include its harness/condition. Likewise REFUTED for feasibility or
`different` is relative to those assertions, not a blanket inequivalence result.

The byte-domain and full-width runs provide a motivation to measure scaling;
they do not locate a precise size threshold or show that equivalence is
impossible to prove. The original protocol/results remain intact. A separate
[fixed-budget domain sweep](../../../cases/c_external_bits/SCALING.md) records
all statuses at 8, 12, 16, 24 and 32 input bits, in two opposite-order repetitions.
