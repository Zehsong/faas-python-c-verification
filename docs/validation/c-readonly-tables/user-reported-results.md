# Read-only table acceptance — user-reported 2026-09-16

The user supplied this Codespace output following the instructions for frontend
implementation `cd2b88c`. The actual executed checkout and ESBMC binary identity
are not in the excerpt. No raw archive, solver logs or JSON certificates were
independently inspected locally; this record includes no local formal rerun.

```text
EXACT: n != 9
Phase: READY; goal reached: True
Latest proposal: EXACT
Agent context: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-table-stage/run-tM4KAQ/checks-4sztzl8w/agent-table/session-c12d8qw6/agent-context.json
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-table-stage/run-tM4KAQ/checks-4sztzl8w/agent-table/session-c12d8qw6/report.md
agent-table: PASS
C READONLY TABLE ACCEPTANCE: 9/9 passed
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-table-stage/run-tM4KAQ/checks-4sztzl8w
Evidence directory: /home/codespace/equiv-evidence/c-readonly-tables-20260916T085115Z-Mh3RPv
Downloadable archive: /home/codespace/equiv-evidence/c-readonly-tables-20260916T085115Z-Mh3RPv.tar.gz
```

## Interpretation

The explicit agent result certifies `n != 9` for the mutated prime table under
its contract: uint32_t n in **0..31**, Boolean return observation. The table marks
9 as prime. EXACT means equal returns inside the condition and unequal returns
outside it, within that domain. It is not a claim for arbitrary uint32_t inputs.

The [acceptance runner](../../../cases/c_readonly_tables/run_checks.py) supplies
this known candidate to the agent session. This result demonstrates shared
frontend/protocol/backend integration, not autonomous discovery of that formula.
The completed session should be retained as evidence rather than given further
proposals merely because its phase still says READY; goal reached is True.

The aggregate reports nine passing controls:

| Check | Required result |
|---|---|
| full_31 | EXACT plus separate expected-formula proof for true |
| fallback_63 | EXACT plus separate expected-formula proof for true |
| truncated_63 | EXACT plus expected-formula proof excluding 37, 41, 43, 47, 53, 59, 61 |
| mutant_31 | EXACT plus expected-formula proof for n != 9 |
| unsafe_index | UNKNOWN with real safety violation and no native input execution |
| short_unwind | UNKNOWN with real unwinding violation and no native input execution |
| readonly_write | UNSUPPORTED_INPUT, no queries or native execution |
| missing-solver | SOLVER_NOT_FOUND, no queries or native execution |
| agent-table | Scripted candidate certified EXACT |

Only the agent's individual PASS and formula are included in this excerpt; the
other passing outcomes follow from the aggregate and runner checks. Their raw
conditions, exact diagnostic text and timings have not been supplied. Expected
formulas for the automatic cases are checked after discovery, not injected into
its predicate proposals. Nine passing controls are not nine equivalence proofs.

## Handoff

Preserve the separate archive above and inspect memory scope/safety diagnostics
in the reports when available. The local const-table slice has user-reported
9/9 acceptance; scalar inputs and return observations remain its boundary.
The next M3 slice is bounded array input/output bindings, explicit observed
contents and independent memory copies, followed by mutable cache state.
Array parameters, writable arrays and whole-program state equivalence are not
implemented by this result. No scaling, blind-case or agent-speedup claim follows.

[Local tests and missing-solver 2/9 control](README.md),
[usage and boundaries](../../../cases/c_readonly_tables/README.md),
[development plan](../../DEVELOPMENT_PLAN.md).
