# Development log

Record each meaningful code/feature change here in the same commit. Git history
supplies the commit identity. Distinguish implementation, local checks, formal
solver results and user-reported evidence. Current state is summarized in
[PROJECT_STATUS](docs/PROJECT_STATUS.md).

## 2026-09-16 — Unified demo accepted; isolated source/Python reproduction

- Recorded user-reported **C TOOL DEMO READY (8/8; engine unchanged=True)** after
  `ff40a6f`, preserving overview and archive paths. Raw reports, counterexample
  and actual tool/checkout identities remain independently uninspected.
  [Transcript](docs/validation/c-tool-demo/user-reported-results.md).
- Added a Linux reproduction entrypoint: resolve a committed revision, create an
  independent clone without hard links/borrowed objects, create a fresh isolated
  Python venv, download/archive pinned wheels and install only from those copies.
  Optional wheelhouse enables offline dependency setup. Current pycparser pin is
  unchanged. Original dirty/untracked files and global Python are not modified.
- The wrapper verifies modified-ESBMC help markers and actual binary identities,
  venv/import locations, unified demo READY 8/8 and an unchanged checkout. It
  records source, commands, dependency evidence and failures in a separate
  checksum archive; full checkout/venv remain outside the archive. No ESBMC
  replacement, rebuild or automatic cleanup occurs. Linux timeouts kill only
  the invoked step's process group. Failed setup/demo/archive never reports READY.
- Validation: **eight local lifecycle tests passed, no skips**, including real
  Git clone/commit exclusion of dirty and untracked files, process timeout,
  simulated lifecycle failures, tool drift and offline argument selection.
  Actual Windows entrypoint gives INCOMPLETE/LINUX_REQUIRED before setup/proofs;
  its archive hashes pass. [Records](docs/validation/c-reproduction/README.md).
  Syntax, links and whitespace checked. Proof/search engine, fixtures and frozen
  transfer lock remain unchanged; core regression was not rerun for this wrapper.
- Full **ISOLATED C REPRODUCTION READY** is pending on Linux. This checks source
  and Python isolation using existing host compiler, modified ESBMC and system
  libraries; it is not clean-host/container reproduction. Independent held-out
  cases and broader environment validation remain release gates. Current full
  readonly-table rerun and raw historical archive review remain open.

## 2026-09-16 — Cache-state acceptance recorded; unified C demonstration

- Recorded user-reported **CACHE STATE ACCEPTANCE: 14/14 passed; inputs/tools
  unchanged=True**, including agent-config-cache PASS, after `33af517`.
  [Transcript and archive paths](docs/validation/cache-state/user-reported-results.md).
  Raw artifacts and actual identities remain uninspected. Together with array
  10/10, this meets the implemented M3 baseline at user-reported evidence level;
  arbitrary stateful C and unrestricted sequence claims are not established.
- Added a single C demonstration/quickstart spanning scalar, prime lookup, array
  and both private-cache adapters, plus no-equal-input and budget UNKNOWN examples.
  An eighth check requires an ESBMC equality counterexample replayed natively with
  identical returns but unequal arrays. Chinese overview copies actual conditions
  and shows domain/observations/state proof scope with archive-relative links.
- Inputs are copied before running; C bodies remain unchanged, cache backends bind
  to their copied models/sketches. Engine/source/input-copy/tool identities gate
  READY. Original run requests, reports and evidence are retained. The new demo
  does not alter search, proof engine, fixtures or the historical transfer lock.
- Validation: eight new local assembly tests passed without skips. Actual MSVC/
  absent-ESBMC execution gives expected INCOMPLETE 0/8, seven UNKNOWN summaries,
  zero native samples and no certified condition. Native compilation/mock assembly
  is not formal proof. [Local records](docs/validation/c-tool-demo/README.md).
  Syntax, relative links, negative reports, local archive/checksum round trip and
  whitespace checked. Earlier 157-test engine regression was not rerun.
- Formal **C TOOL DEMO READY 8/8** remains pending. This is an M4 presentation and
  reproduction slice, not completion: clean Linux environment execution, held-out
  integration and independent raw archive review remain open. The requested full
  current-engine readonly-table rerun is still unreported.

## 2026-09-16 — Array acceptance recorded; private-cache state admission

- Recorded user-reported **C BOUNDED ARRAY ACCEPTANCE: 10/10 passed** after
  `b1ae3d9`, preserving the transcript and archive paths. The raw archive and
  actual binary/checkout identities remain uninspected. The requested current-
  engine readonly-table result was not supplied; its earlier 9/9 is historical.
- Both cache adapters now prove initialization and mode-specific preservation
  before executing native inputs. Failed/missing proofs disable sampling and
  discovery. Agent rounds restore this gate only under the existing identity
  checks. The legacy stateless prime adapter retains its own behavior.
- Added structured state scope and required-obligation declarations. The common
  result publisher/validator refuses certificates missing required state evidence.
  Cache native post-state fields must have valid types and satisfy the invariant,
  in addition to probe flags. Private cache bytes remain unobserved relationally;
  no arbitrary-stateful-C admission or sequence certificate is introduced.
- Added a 14-check stage across both cache families: good and conditional regions,
  empty versus invariant entries, wrong initialization, return-correct state
  corruption, absent solver and resumed scripted agent candidates. It snapshots
  inputs, records tool identities, checks drift and archives independently.
- Validation: **157 local tests passed without skips** (20 oracle + 131 finder,
  including eight new controls + six demo). Two old absent-solver expectations
  were updated from sampled inputs to zero under the new gate. Actual absent-
  solver stage gives expected **2/14**, all UNKNOWN/no condition/no samples.
  [Logs and limits](docs/validation/cache-state/README.md). Native/mock controls
  are not formal proofs; modified-ESBMC 14/14 remains pending. Syntax, links,
  source identity and whitespace checks pass; frozen transfer is unchanged.
- Updated status, plan, result/agent guides and usage. Assess the M3 gate after
  separate array/cache acceptance evidence; clean-environment release and
  held-out-case evaluation remain later gates.

## 2026-09-16 — Bounded array arguments and complete observations

- Added opt-in C contract schema 2: fixed uint32_t/bool array parameters, scalar
  return, explicit full post-call observations, four input values total counting
  all array elements. Each side and logical array has distinct initialized memory;
  alias bindings, pointer syntax/decay, dynamic lengths and const writes are rejected.
  Schema 1 retains scalar inputs and local const tables. Reserved trace-field names
  cannot be used as input fields, preventing wire-format collisions.
- Generated harnesses compare return plus all final array elements; inequality
  negates that complete comparison. Native probes preserve actual return fields
  and add validated observation vectors. Shared search, agent native screening
  and counterexample replay now use the full observation, retaining scalar behavior.
  Reports record declared arrays, flattened initial fields and observation order.
- Added swap/identity, independent increment, copy/reverse and return-mutant pairs,
  real bounds/unwind controls, alias/const rejection, missing solver and a scripted
  two-round agent check. Separate ten-check stage validates expected regions after
  discovery and archives all artifacts. Existing readonly-table rerun is requested
  because shared comparison paths changed. Historical transfer lock is unchanged.
- Validation: 149 local tests passed without skips (20 oracle + 123 finder,
  including 13 new array tests + six demo). Actual missing-solver stage gives 3/10
  as expected, all UNKNOWN/no native input execution. Native/mocked checks are not
  formal proofs. [Logs](docs/validation/c-bounded-arrays/README.md). Syntax, links,
  fixture contracts and whitespace checked. Formal array 10/10 and current-engine
  readonly-table 9/9 remain pending on modified ESBMC.
- Recorded the user's preference to proceed directly between stages and summarize
  at milestones. Updated interface, result, agent and handoff documentation.
  This is single-call array behavior, not persistent cache-state/sequence support.

## 2026-09-16 — Local constant-table acceptance reported

- Recorded user-reported **C READONLY TABLE ACCEPTANCE: 9/9 passed** after
  implementation `cd2b88c`, including agent-table PASS and EXACT: n != 9.
  [Transcript and archive paths](docs/validation/c-readonly-tables/user-reported-results.md).
  That condition applies to the declared 0..31 domain and Boolean return; it was
  a scripted candidate, not an autonomous-agent discovery claim.
- Preserved the separate evidence and completed session locations. Raw solver
  logs, actual checkout/binary identities and other individual conditions remain
  independently uninspected. The aggregate includes expected safety/unwind,
  rejection and missing-solver outcomes; local 2/9 negative evidence is separate.
- Updated support guides, README, status and plan. Next review memory diagnostics
  and define bounded array inputs/outputs, observations and independent copies;
  mutable cache state and the full M3/M4 release goals remain future work.
- Documentation only: checked transcript, local links, consistency and whitespace;
  no runtime edits or formal rerun.

## 2026-09-16 — M3 local constant-table frontend slice

- Extended the generic C admission checker to automatic one-dimensional const
  uint32_t/bool tables with explicit sizes, full literal initializers and at most
  256 elements per source. Only indexed reads are allowed; writes, decay,
  addresses, global/static tables and array parameters remain rejected.
- Preserved source bodies, scalar schema/CLI, return observation and predicate
  discovery. Existing whole-domain safety/unwinding gating remains mandatory
  before native execution. Added scope.memory table metadata; agent source and
  frontend identity cover table edits, so prior sessions must be restarted.
- Added prime full/fallback/truncated/mutant C/JSON fixtures using the generic
  adapter, plus out-of-bounds, short-unwind and rejected-write controls. New
  nine-check stage adds missing-solver and scripted agent checks, compares found
  formulas against expected answers only after discovery, and archives separately.
- Validation: 136 local tests passed, no skips (20 oracle + 110 finder including
  ten new table tests + six demo). Known-safe native fixture checks are not
  formal proofs. Actual absent-solver stage correctly gives 2/9, with no native
  inputs. [Logs](docs/validation/c-readonly-tables/README.md). Syntax, links,
  fixture consistency and whitespace checked. Real modified-ESBMC 9/9 pending.
- Updated support/agent guides, status and plan. Kept historical prime/cache
  adapters and transfer lock; no query speedup or old-result recertification claim.
  This is only the first M3 slice: array input/output and mutable state remain
  future work. Next run the new Codespace stage and inspect memory diagnostics.

## 2026-09-16 — Scalar demo READY reported

- Recorded user-reported **C SCALAR DEMO: READY (5/5 checks; tools unchanged=True)**
  after implementation `75dbd47`, including explicit budget-limited and replay
  PASS lines. [Transcript and archive paths](docs/validation/c-demo/user-reported-results.md).
- The actual formulas, witness values, run checkout and binary hashes are not in
  the excerpt; raw evidence remains independently uninspected. Unchanged tools
  refers to compiler/ESBMC executable identities, not the frozen transfer engine
  or full dependencies. Five passing checks are not five equivalence certificates.
- Updated README, quickstart, status, validation index and plan. Preserve this
  archive, review report usability and proceed toward M3 bounded arrays/state.
  This does not complete all M4 release gates or expand the C support contract.
- Documentation only: checked transcript, local links, consistency and whitespace;
  no runtime edits or formal rerun.

## 2026-09-16 — Guided scalar C demonstration

- Added `cases/c_scalar_demo/run_demo.sh` and its Python assembly driver, reusing
  four existing fixtures for full equality, a conditional region, no equal
  inputs and deliberately query-limited UNKNOWN. Copies portable editable C/JSON
  inputs, records commands/tool hashes and links actual reports in a Markdown
  overview. A fifth check requires an equality counterexample already replayed
  by the backend; absent or inconsistent replay is never fabricated.
- Conditions are taken from versioned results. Expected statuses are checked
  only after discovery, and expected formulas are not injected. The proof engine,
  result schema, C subset and historical transfer lock remain unchanged.
- Added Chinese quickstart, a three-file editable example, report/harness reading
  instructions and evidence-download steps. Each run uses a fresh directory;
  failed runs retain reports and can be archived. No new solver is installed.
- Validation: six local assembly controls; actual MSVC/missing-ESBMC run gives
  four UNKNOWN results, no native samples, INCOMPLETE (0/5). An earlier unresolved
  compiler-name run also remained INCOMPLETE. Archive checksums, relative links,
  Bash/Python syntax and whitespace checked. [Evidence](docs/validation/c-demo/README.md).
  No local ESBMC proof or demo READY claim; the dedicated Codespace run is pending.
- Next: run the demo with the existing modified ESBMC, inspect report usability,
  then proceed to bounded memory/state. This is not a new research benchmark or
  completion of all M4 release requirements. Updated README, status and plan.

## 2026-09-16 — M2 acceptance reported

- Recorded the user's **M2 RESULT ACCEPTANCE: 10/10 passed**, including the
  explicit `agent-partial: PASS`, following implementation `26925c7`.
  [Transcript and evidence paths](docs/validation/m2-results/user-reported-results.md).
  These checks include expected UNKNOWN/rejection outcomes, not ten proofs of
  equivalence. Scripted agent controls establish no autonomous-agent performance.
- Preserved the separate Codespace archive path. Its contents and actual run
  checkout/binary identities remain independently uninspected. The local 3/10
  missing-solver control is distinct from this reported 10/10 solver-stage result.
- Updated README, status, workflow, result guide and plan. Next inspect report
  usability and remaining M2 edge cases, demonstrate the M1/M2 scalar workflow,
  then expand bounded memory/state. The frozen transfer baseline is unchanged.
- Documentation only: checked transcript, local links, consistency and whitespace;
  no runtime changes or formal rerun.

## 2026-09-16 — M2 versioned results and proof diagnostics

- Added verification-result.json schema v1 and report.md for finder/agent runs,
  preserving legacy result.json, CLI flags and exit codes. Reports distinguish
  full equality, exact no-equal-inputs, exact regions, sufficient regions, UNKNOWN
  and EMPTY_DOMAIN, with scope, domain evidence, proof checks, diagnostics and cost.
- Added structured query/time/startup/compile/safety/unwinding/replay reason codes.
  Empty/rejected generic C inputs now leave report artifacts after argument
  parsing; contradictory typed bounds are classified before program admission.
  Unsupported C still makes no proof claim. No safety flags were relaxed.
- Tightened partial output: when final presentation checking is UNKNOWN, retain
  only the Boolean union of actually proved nonempty regions. A complement proof
  for another presentation is not reused. Contradictions or source identity drift
  remove the claim and invalidate displayed checks. Agent latest feedback remains
  separate from its best certificate.
- Added JSON schema, 13 reporting/failure tests and a ten-case M2 acceptance stage
  with independent archives. Local regression: 120 passed, no skips; final 13
  targeted tests passed. A real child-process timeout is covered, but mocked
  certificates are not proofs. Missing-solver acceptance correctly yields 3/10.
  [Logs/provenance](docs/validation/m2-results/README.md). Python/Bash syntax,
  schema/output shape, links and whitespace checked; formal M2 ESBMC run pending.
- Preserved the original transfer engine lock; documented isolated checkout of
  52df7d1 for historical reruns. No relabelling of its 8/12 result or speedup claim.
- Next: run [M2 acceptance](docs/RESULT_FORMAT.md), inspect reports and any remaining
  result-interface edge cases, then prioritize broader C support. Updated handoff
  status and development plan in the same change.

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
