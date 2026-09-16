# Full-width popcount: query-timeout comparison

The user-supplied scaling CSV shows EXACT/true for both runs at input widths
8, 12, 16 and 24. Both 32-bit runs are UNKNOWN with one `equal` timeout each.
Every run uses five queries. The 24-bit runs take 36.611070 and 35.155166 seconds
overall with no individual query timeout. Total discovery time is not the
duration of one solver query. The 32-bit elapsed times are censored failure
observations, not times to finish a proof.

This suggests query cost rather than increasing query count as the immediate
obstacle. It does not identify which solver phase is expensive, rule out a
better search/encoding strategy, or prove a width threshold.

## Separate protocol

Run the identical full `uint32_t` domain and original loop/parallel C programs
with query timeouts 30 and 120 seconds, twice in reversed order:

| Run | Query timeout | Domain | Discovery wall/query limits |
|---|---|---|---|
| r1-t30 | 30 seconds | 0..4294967295 | 300 seconds / 96 queries |
| r1-t120 | 120 seconds | 0..4294967295 | 300 seconds / 96 queries |
| r2-t120 | 120 seconds | 0..4294967295 | 300 seconds / 96 queries |
| r2-t30 | 30 seconds | 0..4294967295 | 300 seconds / 96 queries |

Unwind remains 34. No supplied condition, predicates or native labels enter
discovery. Every run starts fresh. `--timeout` is the only varying finder
setting; this existing flag also bounds solver version startup and the separate
post-discovery expected-condition query. The wall budget can cap an individual
query before its timeout, and no budget is extended automatically.

The search/proof engine remains frozen at `7cc44b5`. The measurement wrapper is
shared with domain scaling; its default ten-run width schedule and budgets are
unchanged. It now prints CSV rows automatically and records per-row timeout.
Original results remain untouched, and the 30-second controls are rerun here
so the comparison does not rely only on historical host conditions.

## Interpretation and artifacts

RECORDED means four valid measurements with unchanged identities, not four
equivalence proofs. Full-domain certificates require the existing EXACT/safety
checks and a separately proved expected-condition check. All UNKNOWN/PARTIAL,
timeout and budget reasons remain in JSON/CSV. Missing tools or infrastructure
errors yield INCOMPLETE. A larger budget succeeding would demonstrate budget
sensitivity on this pair, not a faster solver or a general improvement. Failure
at 120 seconds would remain inconclusive and motivate inspecting the actual
queries/encoding before choosing an intervention. Two repetitions do not provide
a robust statistical comparison.

```bash
bash cases/c_external_bits/run_budget.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The wrapper runs local controls and the four formal runs, prints per-run metrics,
and creates a separate `popcount-budget` checksum archive. Four discovery wall
budgets sum to 20 minutes, plus setup/post-check/archive overhead; this is a bound,
not a predicted duration. Solver and compiler identities, original source,
generated contracts, engine snapshot, schedule and failures are retained.

The user now reports RECORDED 4/4 valid measurements and zero full-domain
certificates: both settings remain UNKNOWN with an equality-query timeout in
both repeats. Raw query logs and archives are uninspected. The supplied prior metrics are stored in the
[scaling evidence record](https://github.com/Zehsong/faas-python-c-verification/blob/codex/same-language-cache/docs/validation/popcount-scaling/user-reported-results.md).
