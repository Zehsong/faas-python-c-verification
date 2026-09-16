# User-reported timeout comparison — 2026-09-16

The user reports the following after implementation `9f1b907`:

```text
POPCOUNT BUDGET: RECORDED (4/4 valid runs; full-domain certified=0/4)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-budget-stage/run-61ZQ2S/budget-tmvh77gb/README.md
Evidence directory: /home/codespace/equiv-evidence/popcount-budget-20260916T130407Z-nvNYfa
Downloadable archive: /home/codespace/equiv-evidence/popcount-budget-20260916T130407Z-nvNYfa.tar.gz
```

All four supplied traces have this sequence:

```text
query 000 safety: PROVED
query 001 feasible: REFUTED
query 002 equal: UNKNOWN
query 003 equal: PROVED
query 004 different: REFUTED
UNKNOWN: None
Outcome: UNKNOWN; domain=NONEMPTY; claim=NO_EQUIVALENCE_CLAIM
Diagnostics: SOLVER_TIMEOUT
```

The full [supplied metrics](user-reported-metrics.csv) retain all four rows
(escaped underscores normalized). Original report directories under the overview
directory are `r1-t30/pair-6lx5vk98`, `r1-t120/pair-tfkwg1af`,
`r2-t120/pair-oma5jd4i` and `r2-t30/pair-wcf5i6hn`.

| Setting | Repeat 1 discovery seconds | Repeat 2 discovery seconds | Certificates |
|---|---|---|---|
| 30-second query timeout | 30.913635 | 30.961838 | 0/2 |
| 120-second query timeout | 120.913565 | 120.865056 | 0/2 |

Every row is UNKNOWN with five queries and one `equal` timeout. The larger budget
did not establish a full-domain result in either repeat. These elapsed times are
censored failures, not proof completion times. Safety was proved and the domain
was nonempty; no inequivalence claim follows. The later equal PROVED concerns a
different query condition and does not override the final published UNKNOWN.

This is user-reported evidence. Raw harnesses, solver phase timings, binary
identities and the archive have not been independently inspected locally. Do
not claim that the arithmetic is impossible to prove, identify a solver-internal
root cause, or extrapolate a complexity bound from these four runs.

The next separate experiment proposes intermediate C programs and requires
full-domain certification of every adjacent equality before applying transitivity.
It preserves the original endpoints and old records; no larger timeout is
automatically tried. [Bridge protocol](../../../cases/c_popcount_bridge/README.md).
