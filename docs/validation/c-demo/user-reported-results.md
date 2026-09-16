# C scalar demo — user-reported 2026-09-16

The user supplied this Codespace output after the instructions for implementation
`75dbd47`. The excerpt does not identify the executed checkout or actual compiler/
ESBMC hashes. No raw archive, overview or solver logs were independently inspected
locally, and this record includes no local formal rerun.

```text
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-demo-stage/run-cAMTav/demo-p6onwune/budget-limited/pair-0gdrz44q/report.md
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-demo-stage/run-cAMTav/demo-p6onwune/budget-limited/pair-0gdrz44q
budget-limited: PASS
Replayed counterexample: PASS
C SCALAR DEMO: READY (5/5 checks; tools unchanged=True)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-demo-stage/run-cAMTav/demo-p6onwune/README.md
Evidence directory: /home/codespace/equiv-evidence/c-scalar-demo-20260916T081954Z-zFJksD
Downloadable archive: /home/codespace/equiv-evidence/c-scalar-demo-20260916T081954Z-zFJksD.tar.gz
```

## Meaning of READY

According to the [demo driver](../../../cases/c_scalar_demo/run_demo.py), READY
requires all four expected result scenarios plus a replayed counterexample:

| Check | Expected behavior |
|---|---|
| all-inputs | EXACT, ALL_INPUTS |
| conditional | EXACT, REGION |
| no-equal-inputs | EXACT, NO_INPUTS in a nonempty domain |
| budget-limited | UNKNOWN with QUERY_BUDGET_EXHAUSTED and four queries |
| Replayed counterexample | An equality refutation with matching native replay after safety was proved |

The first three individual result lines were not supplied; their passing follows
from the aggregate READY/5-of-5 result and this driver's checks. The budget and
replay PASS lines were supplied explicitly. The actual published formula,
counterexample inputs/returns and timings are not in this excerpt.

`tools unchanged=True` compares the requested compiler and ESBMC executable
identities before and after the demo. It does not establish that all source,
headers, libraries or environment state were unchanged, and it is not the
historical transfer experiment's frozen-engine check.

This is successful user-reported integration/demo evidence, not five universal
equivalence certificates. It does not broaden the supported C subset, complete
all M4 release gates, or establish held-out or autonomous-agent performance.

## Handoff

Preserve the archive and inspect the printed overview and per-run reports for
clarity. The existing scalar workflow is now demonstrated at user-reported
acceptance level. Remaining report usability/edge-case review is distinct from
executing this stage again; the next capability milestone is M3 bounded arrays
and state, under the [development plan](../../DEVELOPMENT_PLAN.md).

[Local checks](README.md) remain separate, including the expected missing-solver
INCOMPLETE (0/5) run. [Quickstart](../../../cases/c_scalar_demo/README.md).
