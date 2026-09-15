# Development log

Record each meaningful code/feature change here in the same commit. Git history
supplies the commit identity. Distinguish implementation, local checks, formal
solver results and user-reported evidence. Current state is summarized in
[PROJECT_STATUS](docs/PROJECT_STATUS.md).

## 2026-09-15 — Repository continuity and proposed C release plan

- Audited local code, remote branches and available PR head refs. Confirmed
  working implementation `8e85664`; recent school/cloud changes remain unlocated.
  The `3f652c4` Codespace export is historical, not the current finder baseline.
- Added repository-level agent handoff instructions, current status, and a
  milestone/acceptance plan prioritizing a reusable C interface.
- Recorded the user's earlier 24/24 vocabulary summary and evidence location;
  updated the README's stale pending-result statement.
- Validation: documentation links, referenced source/entry points and Git diff
  whitespace checked. No runtime changes or new formal verification runs.
- Next: locate cloud changes, then implement the agreed scalar C contract.

## Implementation baseline (historical)

| Commit | Change | Historical validation |
|---|---|---|
| `8e85664` | Baseline/modulo vocabulary comparison with paired budgets and evidence | 69 local unit/native tests; user later reported 24/24 certified |
| `2c4ed25` | Compact certified prime conditions; extend comparison to 0..127 | 63 local tests; user later reported extended prime 8/8 |
| `3a78f9b` | Bounded prime computation versus lookup finder | 61 local tests; user later reported initial prime 5/5 |
| `c494999` | Pinned modified ESBMC recovery and Linux IDE migration workflow | Prepared and locally checked; full fresh Linux build not established here |
| `ae8537c` | Shared cache sketch with invalid initialization/preservation controls | 53 local tests; user later reported finder/config/sketch 5/5, 3/3, 8/8 |
| `7ca990d` | Configuration-dependent cache and separate evidence archives | 48 local tests; user later reported config 3/3 |
| `94188b7` | Trace-guided condition search with backend certification | User reported finder 5/5 |
| `faf3ddc` | C cache harness route and stricter oracle verdict handling | User reported 20 tests, 6 cache checks and 6 old relational regressions |

These rows summarize historical evidence, not reruns at the documentation commit.
