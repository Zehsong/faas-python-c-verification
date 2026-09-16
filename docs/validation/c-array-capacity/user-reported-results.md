# User-reported array capacity acceptance — 2026-09-16

Reported after implementation `7ad167b`: **10/11 passed; inputs/tools unchanged=True**.
The supplied overview identifies the following outcomes:

| Case | Acceptance check | Outcome |
|---|---|---|
| copy8 | NOT ESTABLISHED | UNKNOWN |
| clear16 | PASS | EXACT |
| empty_prefix | PASS | EXACT |
| conditional16 | PASS | EXACT |
| tail64 | PASS | EXACT |
| copybits32 | PASS | EXACT |
| empty_length | PASS | EMPTY_DOMAIN |
| unsafe_index | PASS | UNKNOWN |
| short_unwind | PASS | UNKNOWN |
| missing-solver | PASS | UNKNOWN |
| agent-capacity | PASS | EXACT |

The scripted agent reports `n != 0`, phase READY, goal reached=True. The negative
controls intentionally require UNKNOWN or EMPTY_DOMAIN; their PASS labels do
not assert program equivalence.

The only unmet acceptance check is forward/reverse prefix copy (`copy8`). Its
UNKNOWN outcome does not establish inequivalence. The subsequently supplied
copy8 report shows domain NONEMPTY, safety PROVED, sufficiency PROVED,
complement UNKNOWN, five queries, 38 native samples and 60.718313 elapsed seconds.
Both `query-002-equal` and `query-004-different` have SOLVER_TIMEOUT. The report
publishes no equivalence claim: the successful sufficiency check alone is not
a proof of full-domain equality. The eleven-check capacity gate remains open.

The next patch adds checked length partitioning after equality/inequality
timeouts; its formal acceptance is pending. It does not replace this historical
failure, reduce the domain or change the required expected results.

```text
Overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-kzz6iR/checks-5_m0j468/README.md
copy8 report: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-kzz6iR/checks-5_m0j468/copy8/pair-tlphcxou/report.md
Evidence directory: /home/codespace/equiv-evidence/c-array-capacity-20260916T151631Z-mheAo4
Archive: /home/codespace/equiv-evidence/c-array-capacity-20260916T151631Z-mheAo4.tar.gz
```

These are user-supplied logs, overview and copy8 report, not a local formal rerun or an
independently audited raw archive. Run-specific tool identities, query evidence
and individual conditions other than the displayed agent result remain
uninspected. Historical engine locks and acceptance criteria are unchanged.
