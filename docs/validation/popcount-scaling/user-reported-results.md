# User-reported popcount scaling — 2026-09-16

Reported after implementation `ed1fe9b`:

```text
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-scaling-stage/run-K0LJAV/scaling-97kf3lz4/r2-b8/pair-rh137u1w
 query 000 expected: PROVED
r2-b8: EXACT; full-domain certified=True
POPCOUNT SCALING: RECORDED (10/10 valid runs; full-domain certified=8/10)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-scaling-stage/run-K0LJAV/scaling-97kf3lz4/README.md
Evidence directory: /home/codespace/equiv-evidence/popcount-scaling-20260916T123626Z-qpnxZE
Downloadable archive: /home/codespace/equiv-evidence/popcount-scaling-20260916T123626Z-qpnxZE.tar.gz
```

The user subsequently supplied [all ten CSV rows](user-reported-metrics.csv).
They identify the per-width outcomes and timing below. The CSV is transcribed
user-provided evidence (escaped underscores normalized); the original archive,
solver logs, actual binary identities and query harnesses remain uninspected.

| Input width | Full-domain certificates | Discovery seconds, repeat 1 / 2 | Result |
|---|---|---|---|
| 8 | 2/2 | 1.116534 / 1.065957 | EXACT true |
| 12 | 2/2 | 1.158889 / 1.269177 | EXACT true |
| 16 | 2/2 | 1.868488 / 1.818997 | EXACT true |
| 24 | 2/2 | 36.611070 / 35.155166 | EXACT true |
| 32 | 0/2 | 30.852673 / 30.965475 | UNKNOWN; one equal timeout per run |

All ten rows report five queries, valid measurements and no infrastructure
error. Both 32-bit rows specifically report SOLVER_TIMEOUT in an equality query,
not a failed expected-condition post-check. This resolves the uncertainty left
by the first aggregate excerpt. It is not a proof of inequivalence.

The mean successful discovery times are approximately 1.091, 1.214, 1.844 and
35.883 seconds for 8/12/16/24 bits, respectively. The 32-bit observations are
censored failures and must not be treated as faster proof completion than the
24-bit case. The 24-bit total can exceed the 30-second per-query timeout because
it covers several queries; individual query durations were not supplied.

Constant query count with increased time and equal-query timeouts points toward
backend cost per query as the immediate obstacle on this pair, rather than an
increase in search query count. The data do not isolate solver subphases or
establish a precise width threshold. They also do not show that a different
search strategy or encoding could not help. This is repeated measurement of
one pair, not an 80% success rate across independent programs.

A separate [30/120-second timeout comparison](../../../cases/c_external_bits/BUDGET.md)
keeps full uint32 inputs, C sources, engine, unwind and the 300-second/96-query
discovery limits fixed. It repeats both settings in opposite orders and preserves
all incomplete outcomes. No automatic timeout increase or alteration of the
original experiment is made. A success at 120 seconds would show budget
sensitivity on this pair, not a solver speedup.

[Original protocol](../../../cases/c_external_bits/SCALING.md) · [Local controls](README.md)
