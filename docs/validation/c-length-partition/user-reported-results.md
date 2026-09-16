# User-reported logical-length partition run — 2026-09-16

Reported after `441fd89`: **C ARRAY CAPACITY ACCEPTANCE: 10/11 passed;
inputs/tools unchanged=True**. The supplied extraction identifies only copy8
as failed: UNKNOWN, 13 queries, 38 native samples, 130.785482 elapsed seconds.
The scripted agent-capacity control still passes. The expected-condition
post-check for copy8 was not run because discovery did not establish EXACT.

| Attempt | Coverage | Checked parts | Result |
|---|---|---|---|
| Direct equal, query-002 | n/a | Whole domain | SOLVER_TIMEOUT |
| length-partition-003, equal | PROVED | n=0,1,2,3 PROVED; n=4 SOLVER_TIMEOUT; n=5..8 not run | UNKNOWN |
| Direct different, query-010 | n/a | Complement of false | SOLVER_TIMEOUT |
| length-partition-011, different | PROVED | n=0 SOLVER_TIMEOUT; n=1..8 not run | UNKNOWN |

The partition mechanism executed, but did not prove every part. No full-domain
equivalence or inequivalence follows. Individual successful sub-obligations
were retained as evidence; this adapter version does not publish their partial
union when the enclosing query is unresolved.

The supplied commands use the modified ESBMC path below, Z3, unwind 20,
overflow checking and --no-slice. Timed-out subqueries report returncode 124.
The original partition harness initializes length nondeterministically and adds
an equality assumption. Whether changing that representation improves solver
performance is an experiment, not established by these logs.

```text
ESBMC: /workspaces/esbmc-current/build/src/esbmc/esbmc
Overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-vzVBPX/checks-y50pu7q4/README.md
copy8: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-array-capacity-stage/run-vzVBPX/checks-y50pu7q4/copy8/pair-9mkf8_h1
Evidence directory: /home/codespace/equiv-evidence/c-array-capacity-20260916T155210Z-Y5zoeB
Archive: /home/codespace/equiv-evidence/c-array-capacity-20260916T155210Z-Y5zoeB.tar.gz
```

Provenance: user-provided console summary and extracted JSON fields, including
coverage/subquery results, commands and source hashes. Raw archive, verify.log
contents and actual harness files remain uninspected. No local formal rerun.
This result keeps the original 11/11 gate open. The subsequent constant-binding
harness change requires new acceptance and does not overwrite this failure.
