# Development log

Record each meaningful code/feature change here in the same commit. Git history
supplies the commit identity. Distinguish implementation, local checks, formal
solver results and user-reported evidence. Current state is summarized in
[PROJECT_STATUS](docs/PROJECT_STATUS.md).

## 2026-09-16 — C transfer acceptance and discovery totals reported

- Recorded the user's **8/8 required passes, 8/12 discovery EXACT**, with all
  reports valid and unchanged engine/inputs/tools, following experiment `52df7d1`.
  Preserved the supplied archive paths and the single reported ordered 0..31
  measurement: 32 queries, 5.920 seconds. [Transcript](docs/validation/c-transfer/user-reported-results.md).
- From the schedule and totals, the four exploratory default-vocabulary reordered
  runs were non-EXACT. Their PARTIAL/UNKNOWN breakdown, reasons, conditions and
  paired costs remain unavailable; no mean or speedup is claimed. Raw archives
  and run-specific checkout/binary identities have not been independently audited.
- Updated status, workflow and plan toward M2 versioned results and diagnostics,
  preserving the frozen experiment baseline. This is authored integration
  evidence, not blind-case or autonomous-agent evaluation.
- Documentation only: transcript, schedule/count inference, local links and
  whitespace checked. No runtime changes, engine-lock updates or solver reruns.

## 2026-09-16 — Post-freeze C scalar transfer experiment

- Added a new three-input interval-check family through four C files and four
  JSON contracts only: expression/full-equivalence and offset/full-inequality
  controls, plus reordered checks on 0..7 and 0..31 rectangular domains.
  The last pair requires relations among inputs and permits inverted bounds.
- Finder/frontend/backend/oracle files are unchanged. A 16-file LF-normalized
  hash lock records the `61ba47b` baseline (engine implementation `5502520`) and
  rejects drift. No per-case adapter, handwritten harness or probe was added.
- Added an experiment runner using the existing hypotheses interface to compare
  default predicates with all six field-order atoms. Matched budgets/seeds,
  alternating mode order and two repeats yield 8 required / 12 total runs.
  Exploratory PARTIAL/UNKNOWN results stay visible; they do not count as EXACT.
  Post-discovery assessment budgets and discovery metrics are reported separately.
- Added fresh evidence archival, CSV/JSON measurements, source/binary checks,
  preparation-work inventory and honest authored-example provenance. This is not
  an independent blind case, autonomous-agent experiment or measured speedup.
- Validation: nine targeted Windows/MSVC tests pass without skips; 1,536 native
  observations plus a finite arithmetic expectation check. The missing-solver
  experiment correctly retains six UNKNOWN results and 0/4 required passes.
  [Logs](docs/validation/c-transfer/README.md). Python/Bash syntax, links, engine
  identity and whitespace checked. Existing core tests were not rerun because
  the engine is unchanged. Formal ESBMC results are pending.
- Next: run [the transfer stage](cases/c_scalar_transfer/README.md), inspect
  outcomes/costs/limitations, then develop M2 result schemas and diagnostics.

## 2026-09-16 — C scalar integration acceptance reported

- Recorded the user's **C SCALAR ACCEPTANCE: 8/8 passed** summary, following
  implementation `5502520`, including the explicit missing-solver PASS and exact
  artifact/archive paths. [Result and provenance](docs/validation/c-scalar/user-reported-results.md).
- Updated current status, quickstart, agent workflow and plan: the first scalar
  integration gate is now user-reported passed. Raw per-case logs, executed
  checkout and binary identity remain unaudited; no arbitrary-C or autonomous-agent
  claim follows from these fixture/protocol results.
- Documentation only. Checked preserved transcript, relative links and whitespace;
  no runtime changes or formal solver rerun. Next: a new supported C pair through
  configuration alone with the engine fixed, then M2 result/failure diagnostics.

## 2026-09-16 — Generic C scalar contracts and controlled harness generation

- Added `find_c_conditions.py --contract` and `agent_workflow.py start --case c
  --contract`: two admitted C files and a typed input/observation contract now
  reuse the existing search, native replay and ESBMC certification pipeline.
- Added AST admission/type checks using pinned pycparser 3.0, checked function/
  helper namespacing, positional input binding, source snapshots and identity
  checks. No arbitrary agent harness code is accepted. The initial subset is
  pure uint32_t/bool scalars, 1..4 inputs, branches/helpers/bounded loops and return
  observation; arrays, pointers, signed arithmetic and state remain outside it.
- Extracted shared process/oracle/replay logic into `c_backend.py` and search/final
  certification into `condition_runner.py`; preserved old case entry points.
  Generic native execution requires a prior whole-domain safety/unwinding proof.
  Missing solver, unsafe code or insufficient bounds cannot produce native traces
  or an equivalence certificate. Agent rounds bind the contract/sources/parser/
  tool identity and reuse safety only when that identity remains unchanged.
- Added configuration-only max/min, parity, series and series-mutant fixtures,
  two safety/bound controls, a generic scripted agent trial and missing-solver
  control. The new stage archives evidence independently as `c-scalar-*`.
- Validation: 107 distinct local tests passed without skips across full baseline
  and final scalar runs. Actual native fixture results, admission failures, safety
  gating and protocol controls are covered. The intentionally missing-solver
  acceptance run correctly reports 1/8, not formal success. Python/Bash syntax
  and diff checks passed. [Local logs and provenance](docs/validation/c-scalar/README.md).
- [Usage and limitations](docs/C_SCALAR_TOOL.md); status, workflow and development
  plan updated. Next: user runs the 8-check stage with their modified ESBMC, then
  supplies an unseen C pair. Formal acceptance and autonomous-agent effectiveness
  are not yet established for this new adapter.

## 2026-09-16 — First live external-chat candidate certified

- Recorded the user-reported prime/truncated `0..127` session: EXACT, one round,
  four total queries and 1.1177481559998341 runner active seconds. Candidate
  feasibility, sufficiency and complement results agree with the final status.
- Saved the [reported context/result and assistant proposal](docs/validation/agent-workflow/live-prime-trial/README.md),
  with source/tool identities, scope, provenance and original artifact location.
  Raw remote solver logs and the submitted proposal file were not fetched.
- This is a successful external-chat integration trial using a known formula;
  no unseen-case discovery, autonomous invocation or speedup is claimed.
- Documentation/data only: JSON consistency, relative links and whitespace
  checked. No runtime changes or local solver rerun. Next priority: generic C
  scalar bindings/configuration and controlled harness generation.

## 2026-09-16 — Codespace agent-workflow acceptance reported

- Recorded the user's **AGENT WORKFLOW ACCEPTANCE: 8/8 passed**, associated with
  implementation `62ea51e`, including the expected missing-solver UNKNOWN.
- Preserved the supplied output and exact evidence/archive paths in
  [the result record](docs/validation/agent-workflow/user-reported-results.md).
  The original archive and its source/binary hashes were not independently read.
- Updated current status and workflow instructions. Next is a real external-agent
  proposal loop; familiar prime cases count as integration trials, not held-out
  agent-discovery evidence.
- Documentation only: link and whitespace checks; no runtime changes or new
  solver runs, and no autonomous-agent performance claim.

## 2026-09-15 — Agent proposal/check/feedback sessions

- Recorded [the approved workflow and trust boundaries](docs/AGENT_WORKFLOW.md),
  including agent-assisted configuration as part of the planned generic C layer.
- Added `agent_workflow.py start/step` for the existing prime/cache/config-cache
  adapters. External agents exchange JSON files; no model API is invoked.
- Added bounded Boolean condition syntax, strict proposal validation, replay of
  actual C inputs, native screening, named backend obligations and separate
  sufficient/exact goals. Agent proposals cannot change the fixed scope, provide
  output labels or inject harness code.
- Sessions retain evidence and feedback, share round/query/active-time budgets,
  reject stale submissions, detect source/contract/tool drift and lock updates.
  Retained certificates and latest proposal status are reported separately.
- Added eight scripted protocol controls, independent checks for six EXACT
  outcomes, Codespace execution/archiving and 21 new local tests. These fixtures
  are not an autonomous-agent discovery or performance benchmark.
- Validation: 69 existing tests passed during the initial regression run; all
  21 new tests passed on the final source (90 distinct tests across runs, none
  skipped). Python compilation, shell syntax and documentation links checked.
  [Local evidence](docs/validation/agent-workflow/README.md).
- Missing-solver injection gave UNKNOWN for all sessions and only the intentional
  UNKNOWN control passed (1/8; expected exit 2). Formal 8/8 acceptance remains for
  the user's modified ESBMC in Codespace; no new formal success is claimed here.
- Next: run formal protocol acceptance, then try genuine agent-authored proposals
  and develop the generic scalar C binding/configuration layer. General harness
  inference, automatic invariants and unattended model-provider integration are
  not implemented by this change.

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
