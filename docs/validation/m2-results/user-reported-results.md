# M2 result acceptance — user-reported 2026-09-16

The user supplied the following Codespace output after the M2 implementation
`26925c7`. That identifies the intended implementation; the excerpt does not
show the executed checkout or ESBMC version/hash. No raw archive, report JSON or
solver log was independently inspected locally, and no local formal rerun was
performed. Markdown-escaped underscores are normalized in this transcript.

```text
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/m2-stage/run-w6arGA/checks-d78e3s_l/agent-partial/session-0s7e14xn/report.md
agent-partial: PASS
M2 RESULT ACCEPTANCE: 10/10 passed
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/m2-stage/run-w6arGA/checks-d78e3s_l
Evidence directory: /home/codespace/equiv-evidence/m2-results-20260916T075823Z-xgx7oy
Downloadable archive: /home/codespace/equiv-evidence/m2-results-20260916T075823Z-xgx7oy.tar.gz
```

## Interpretation

This reports all ten acceptance checks passing, not ten equivalence certificates.
According to the [acceptance runner](../../../cases/result_contract/run_checks.py),
the checks cover:

| Check | Required outcome |
|---|---|
| all-inputs | EXACT, all inputs equal |
| conditional | EXACT equivalence region |
| no-inputs | EXACT, no equal inputs in a nonempty domain |
| query-budget | UNKNOWN with exhausted-query diagnostic |
| unsafe-division | UNKNOWN with safety/property diagnostic |
| short-unwind | UNKNOWN with incomplete-unwinding diagnostic |
| missing-solver | UNKNOWN with missing-solver diagnostic |
| empty-domain | EMPTY_DOMAIN, no equivalence claim |
| unsupported | Unsupported-input diagnostic, no equivalence claim |
| agent-partial | PARTIAL sufficient region; completeness not established |

Only the final individual PASS line and the aggregate are in the supplied
excerpt. It does not provide the actual published conditions, detailed costs or
per-query solver evidence. The agent control uses a scripted proposal; it does
not establish autonomous-agent discovery performance. Timeout handling has
separate local child-process/unit coverage, not a dedicated real-ESBMC case in
this ten-check stage. [Local validation](README.md).

## Handoff

Preserve the separate archive above. Inspect `report.md` and
`verification-result.json` for clarity, scope and proof diagnostics before
expanding the interface. Demonstrate the supported scalar M1/M2 workflow, then
address bounded memory/state under M3. This result does not broaden the accepted
C subset. The original transfer engine lock and its historical results remain
unchanged; use their original checkout for reruns.

See [current status](../../PROJECT_STATUS.md), [development plan](../../DEVELOPMENT_PLAN.md)
and [result format](../../RESULT_FORMAT.md).
