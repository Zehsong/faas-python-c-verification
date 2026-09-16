# Project status and handoff

Updated: 2026-09-16. This is the primary handoff entry point; Git and source code
remain authoritative. Roadmap items are not implemented capabilities.

## Current objective

Deliver a reproducible tool that accepts supported pairs of C functions and an
explicit contract, discovers sufficient equivalence conditions, and certifies
the exact equivalence region when possible. Then evaluate its limitations and
reuse in other same-language backends. See [the plan](DEVELOPMENT_PLAN.md).

## Active expansion: composable input contracts

The user approved broader input support after the popcount milestone. Priority
now shifts from a generic bridge interface to a composable type/memory/constraint
frontend, then floating-point semantics and agent-assisted induction. These
larger milestones remain planned; they are not enabled by this first patch.

First slice: [schema 3 input domains](../cases/c_input_domains/README.md) now
normalizes omitted bounds to full uint32_t/bool ranges and admits checked
all/any/not combinations of comparisons among initial scalar/array fields.
Every symbolic obligation, native probe/replay and agent seed check shares this
domain. Existing schema 1/2 semantics and source restrictions remain intact.
Reports preserve declared inputs, normalized ranges and the extra constraints.
The user now reports **13/13 passed; inputs/tools unchanged=True** after
`5446b31`, including agent-domain PASS.
[Supplied summary and archive paths](validation/c-input-domains/user-reported-results.md).
Raw archive remains uninspected; this is not a formal rerun of later changes.

The next [capacity/length slice](../cases/c_array_capacity/README.md) admits
schema 3 arrays up to 64 elements and 128 total initial values, while retaining
four logical parameters. Optional length_field binds an explicit uint32 scalar
and contributes a recorded structural capacity constraint. All physical elements
remain initialized and observed, including the inactive tail. Larger inputs use
at most 256 sparse seeds and 24 initial predicates instead of exponential
Cartesian preparation. Symbolic queries still cover the entire declared domain.
User-reported acceptance after `7ad167b` is **10/11; inputs/tools unchanged=True**.
Only `copy8` (forward/reverse prefix copy) is NOT ESTABLISHED, with UNKNOWN;
the supplied report identifies timeouts in query-002-equal and query-004-different,
with safety PROVED and domain NONEMPTY. The remaining ten checks meet expectations.
Added a fallback that partitions one explicit logical length after an equal/different
timeout, requires solver-proved coverage and every part, and preserves budgets and
full observations. It admits at most 17 parts; no nested partition or loop induction.
The capacity gate remains open pending formal rerun of this fallback.
[Reported evidence](validation/c-array-capacity/user-reported-results.md)
and [local evidence](validation/c-array-capacity/README.md).
Schema 1/2 limits remain unchanged.

This is a core/frontend change: old frozen engine locks are intentionally not
updated. Reproduce frozen external/popcount stages in an independent checkout
of `79e6aa0` (or their recorded original commits). Their old pass counts are
historical and cannot be relabeled as acceptance of the new engine. Restart
agent sessions after updating. New scalar types, structs, dynamic allocation,
unbounded-size arrays, floating point and induction remain unsupported.

## Repository audit

Repository: https://github.com/Zehsong/faas-python-c-verification

- Working branch: `codex/same-language-cache`.
- Latest demonstration: `ff40a6f`, unified scalar/table/array/cache showcase, now
  user-reported READY 8/8 with unchanged engine. Earlier scalar-only demo
  `75dbd47` has user-reported READY (5/5).
- Latest wrapper: `7cc44b5`, committed-checkout/fresh-venv Linux reproduction,
  now user-reported READY. Host compiler/modified ESBMC/system libraries are reused.
- External-source integration: `129df96`, now user-reported READY 5/5 required,
  engine frozen=True. Full-width popcount remains UNKNOWN/SOLVER_TIMEOUT (0/1
  exploratory EXACT); safety PROVED and domain NONEMPTY. Raw archive uninspected.
- New stage: fixed-budget popcount input-domain scaling at 8/12/16/24/32 bits,
  two reversed-order repetitions; original programs, engine and budgets retained.
  Now user-reported RECORDED 10/10 valid runs and 8/10 full-domain certificates.
  User-supplied CSV now identifies EXACT true twice at 8/12/16/24 bits, and
  UNKNOWN/equal-query SOLVER_TIMEOUT twice at 32 bits. All runs use five queries.
  Raw archives, query harnesses and binary identities remain uninspected.
- New stage: full-width popcount timeout comparison at 30/120 seconds, twice
  in opposite order; same 300-second/96-query discovery limits and frozen engine.
  Now user-reported RECORDED 4/4 valid, full-domain certified 0/4. Both settings
  time out in query 002 equal in both repeats; all rows have five queries.
- New experiment: proposed byte-loop and byte-parallel intermediate programs,
  three full-domain edges through the existing C frontend, original endpoints
  pinned to `129df96`. Only complete edge certification plus identity and mutant
  control gates permits a transitive endpoint claim. Now user-reported RECORDED,
  links certified 2/3, endpoint UNKNOWN, mutant rejected=True. Supplied overview
  identifies edge_0 and edge_2 as certified; edge_1 is UNKNOWN/SOLVER_TIMEOUT.
- New refinement: change one byte implementation at a time, producing six full-
  domain edges plus a mutant control. All links are rerun; no old certificate or
  byte lemma is assumed. Implementation `388a2c3` now has user-reported RECORDED,
  6/6 certified links, endpoint PROVED and mutant rejected=True. Six discovery
  times sum to 7.302194 seconds; post-check/setup time is excluded. Eleven local
  controls passed before the run. Raw archive remains uninspected.
  Core engine, original endpoints and original bridge programs remain unchanged.
- Previous core baseline: `33af517`, cache state admission/reporting, now
  user-reported 14/14; preceded by `b1ae3d9` (arrays, user-reported 10/10).
  The demonstration and reproduction wrappers leave the proof/search engine unchanged.
  Prior table frontend `cd2b88c` has user-reported 9/9; the current-engine table
  rerun remains unreported.
- Prior core implementation: `26925c7` (M2 result contract), following `133abe9` (transfer result record),
  `5502520` (scalar adapter) and `23ad4af` (live trial record),
  `62ea51e` (agent workflow) and finder baseline `8e85664`.
- The working branch was explicitly fetched before this change; no newer remote
  implementation was found. Unlocated cloud edits remain unreviewed.
- On 2026-09-15, remote heads showed that working branch still at `8e85664`;
  `main` at `8a686a5`, `recovery-current-work` at `5bb7479`.
- `codespace-refactored-space-parakeet-v6v7r597jj5ghp6qw` at `3f652c4` is a
  **2026-09-10 historical export**, based on the older main lineage. It does not
  contain the current cache/prime tool. It is not a newer development baseline.
- Fetching pull-request head refs revealed no additional heads in this audit.
- The user reports recent school/cloud work. Its branch/commit/patch has not yet
  been identified, so that work is **not reviewed or integrated**. Do not assume
  it is absent from a cloud workspace just because it is absent from these refs.
- The local clone's fetch configuration covered only `recovery-current-work`;
  its working-branch tracking ref was stale. It was refreshed explicitly. Follow
  [AGENTS.md](../AGENTS.md) rather than trusting an unrefreshed tracking ref.

## Implemented and inspected

| Component | Capability | Current boundary |
|---|---|---|
| C harness verifier | Checks a manually prepared relational harness using named assertions and scope metadata | Does not construct a product from arbitrary C files |
| Predicate finder | Uses native traces and solver counterexamples to refine regions; certifies regions with ESBMC | Manual model, admissible predicate grammar and bounded search budget |
| Final condition checks | Proves equality inside the condition and inequality outside it for EXACT | Relative to declared domain, observations and model |
| Cache sketch | Shared generation of initialization, preservation and relational obligations for two cache families | Invariant and bindings are supplied; no automatic invariant synthesis |
| Prime/lookup adapter | Compares fallback, truncated and mutated tables against trial division | Boolean return, one uint32 input, CLI domain constrained to 0..255 |
| Vocabulary comparison | Paired baseline/modulo experiments, shared initial seeds/budgets, alternating order | No adaptive vocabulary yet |
| Generic C scalar adapter | Two C files plus checked JSON contract; native probe/harness generation; shared automatic discovery and agent sessions | Schema 1 scalars/const tables; schema 2 fixed array parameters, independent copies and all final elements observed; array acceptance user-reported 10/10; four input values total, no aliases or persistent state |
| Agent workflow | Persistent JSON proposal/check/feedback sessions; typed Boolean conditions, native screening, backend certification, cumulative budgets and source/contract/tool drift checks | Built-in adapters plus checked generic scalar C contracts; external chat authors proposals; no automatic model API |
| Versioned result contract | verification-result.json v1 and report.md for finder/agent runs; explicit scope, domain, proof basis and diagnostics | Legacy result.json retained; M2 acceptance user-reported 10/10, raw archive not independently inspected |
| Scalar demonstration | Four existing C pairs/runs, archive-relative report index, editable inputs and a solver counterexample already replayed by the backend | User-reported READY (5/5), raw archive uninspected; no engine or C-subset expansion |
| Unified C demonstration | One command and portable Chinese overview for seven executed cases plus a same-return/different-array solver replay | User-reported READY 8/8; engine unchanged; known integration cases, not a held-out or clean-environment release |
| Isolated reproduction | Fixed commit in an independent clone, fresh venv, pinned wheel installation, demo and identity checks, separate archive | User-reported READY; reuses host compiler, modified ESBMC and system libraries; not clean-machine reproduction |
| External-source integration | New power-of-two and population-count C pairs using the existing generic contract; frozen engine and separate evidence | User-reported READY 5/5 required; full-width popcount UNKNOWN/SOLVER_TIMEOUT; not blind evaluation |
| Popcount scaling | Fixed budgets and input-width schedule, CSV/overview with all outcomes and timeout kinds; separate measurement and certificate counts | User-reported 10/10 valid measurements and 8/10 full-domain certificates; 8/12/16/24 bits EXACT twice each, 32 bits equal-query timeout twice; five queries throughout; not a blind/statistical evaluation |
| Certified intermediate-program chain | Full-domain C edges with scope/source/identity gates and a negative control; endpoint equality derived by certified transitivity | Original three-edge experiment 2/3; refined six-edge experiment user-reported 6/6 and endpoint PROVED; no automatic decomposition or partial-region composition |
| Composable input domains | Schema 3 type-default bounds plus Boolean combinations of entry-field comparisons, shared by all proof/native/agent paths | First domain slice user-reported 13/13 after 5446b31; raw archive uninspected |
| Array capacity/logical length | Schema 3 fixed capacities 1..64, 128 total initial values, optional uint32 length fields; all physical elements observed | Eleven-check formal acceptance pending; no dynamic/unbounded memory or aliasing |
| Evidence tooling | Source/command snapshots, JSON/CSV results, archived runs and checksums | Historical archives are in the user's Codespace, not automatically in Git |

Key code: [oracle](../tools/verify-equiv/verify_equiv.py),
[C harness route](../tools/verify-equiv/verify_c_harness.py),
[search](../tools/find-cond-equiv/predicate_search.py),
[shared runner](../tools/find-cond-equiv/condition_runner.py),
[prime adapter](../tools/find-cond-equiv/find_prime_conditions.py).

Process/oracle/replay infrastructure now lives in `c_backend.py`, and discovery
in `condition_runner.py`. The generic C adapter subclasses that base directly;
legacy prime/config adapters retain their compatibility inheritance. See
[C scalar usage and boundaries](C_SCALAR_TOOL.md). Three new pair families and
one mutant are supplied entirely through C files and contracts. This does not
admit arbitrary C, unrestricted pointers or persistent state through the generic
route. M3 includes local const tables and opt-in bounded array arguments for one
call; it does not yet cover mutable cache state across call sequences.

Local validation: 107 distinct tests passed, no skips (105 in the full
regression, followed by 17 targeted scalar tests including two additional controls).
The 17 new tests cover scalar admission, safety gating, bindings and native results.
See [local evidence](validation/c-scalar/README.md). The user subsequently reported
**C SCALAR ACCEPTANCE: 8/8 passed** from Codespace.
[Transcript, evidence paths and provenance](validation/c-scalar/user-reported-results.md).
No raw archive inspection or local formal rerun accompanies this record.

## M2 reporting implementation

[Result format v1](RESULT_FORMAT.md) is implemented for automatic discovery and
agent sessions. The report distinguishes EXACT with no equal inputs from an
empty domain, requires nonempty-domain/state/proof evidence for certified claims,
and explains solver, budget, safety, admission and identity failures. Partial
results retain an actually proved Boolean region union if a compact presentation
cannot be certified; mismatched complement evidence is not reused.

Local regression: 120 tests passed without skips (20 oracle + 100 finder), then
13 targeted result tests passed. An intentionally missing-solver M2 stage yields
3/10, as expected. [Logs](validation/m2-results/README.md). The user subsequently
reported **M2 RESULT ACCEPTANCE: 10/10 passed**, including `agent-partial: PASS`.
[Transcript and separate archive](validation/m2-results/user-reported-results.md).
The raw archive and run-specific binary/checkout identities have not been
independently inspected. Earlier scalar/transfer passes remain historical.

The transfer engine lock is deliberately unchanged. Its original stage must run
in a checkout of `52df7d1`, as documented in the result-format guide; it will reject
current M2 code. Do not refresh it to relabel the old experiment as unchanged.

## M1/M2 demonstration workflow

The [C demo quickstart](../cases/c_scalar_demo/README.md) now provides one command
for all-input equality, a conditional region, no equal inputs and budget-limited
UNKNOWN. An overview links actual reports, copied C/JSON inputs and a solver
counterexample already replayed by the native backend. It never substitutes an
expected formula or a native sample for a certificate. Runs and failures receive
separate archives. The guide includes editing and running a new three-file pair.

Six local assembly controls pass. An actual MSVC/missing-ESBMC run produces
UNKNOWN for all four examples, zero native samples and INCOMPLETE (0/5), as
required; local archive/checksum and relative-link checks pass.
[Local validation](validation/c-demo/README.md). No local formal demo run was
possible. The user subsequently reported **READY (5/5 checks; tools unchanged=True)**,
including explicit budget-limited and replay PASS lines.
[Transcript and archive paths](validation/c-demo/user-reported-results.md). The
raw archive remains independently uninspected. READY requires all four expected
outcomes, one replayed counterexample and unchanged compiler/ESBMC executable
identities; it is not a frozen-engine or full dependency-closure check.
This does not fulfill all M4 release gates: clean-environment reproduction,
held-out cases and broader state/memory support remain future work.

## M3 first slice: local constant tables

[The generic table extension](../cases/c_readonly_tables/README.md) admits automatic
one-dimensional const uint32_t/bool arrays, with full literal initialization and
at most 256 declared elements per source. Indexed reads are allowed; writes,
array decay, pointers, global/static tables and array parameters remain rejected.
The existing whole-domain safety gate covers bounds and unwinding before any
native input execution. Report scope.memory records both sides' table metadata.
Source bodies, scalar contracts, observation and discovery grammar are preserved.

Prime computation/lookup cases now use ordinary C/JSON through find_c_conditions
and --case c sessions, without a prime-specific backend. A new nine-check stage
covers four certified-region targets, genuine out-of-bounds/unwind controls,
rejected writes, missing solver and one scripted agent candidate.

Local regression: 136 passed without skips (20 oracle + 110 finder + six demo).
The actual missing-solver stage gives the expected 2/9 and no native inputs.
[Local evidence](validation/c-readonly-tables/README.md). The user subsequently
reported **C READONLY TABLE ACCEPTANCE: 9/9 passed**, with the scripted agent
result EXACT: n != 9 on n in 0..31.
[Transcript and archive paths](validation/c-readonly-tables/user-reported-results.md).
The raw archive remains independently uninspected; this result is separate from
old scalar/demo pass counts. Restart prior agent sessions after upgrading frontend identity.
The later array/cache results below meet the implemented M3 baseline at the
user-reported evidence level; broader state/sequence support and M4 gates remain open.

## M3 bounded array input/output slice

[Schema 2](../cases/c_bounded_arrays/README.md) admits fixed uint32_t/bool array
parameters with one scalar return, at most four scalar input values including
all elements. Each side receives distinct, initialized arrays with identical
entry values; every array is observed after execution alongside the return.
No aliases, unrestricted pointers, dynamic lengths or persistent state are
admitted. Local writable scratch arrays/array forwarding remain unsupported.

Search entropy/refinement, agent native screening and solver witness replay now
share complete observation comparison. A swap/identity fixture with equal returns
must still find the initial equality region of the two elements. Existing scalar
trace compatibility is preserved. Flattened entry fields and vector positions
are explicit in scope. Session identity changes require fresh agent sessions.

Local regression: 149 passed (20 oracle + 123 finder + six demo), no skips.
[Local evidence](validation/c-bounded-arrays/README.md). An actual missing-solver
stage yields the expected 3/10 with all outcomes UNKNOWN and no native inputs.
The user now reports **C BOUNDED ARRAY ACCEPTANCE: 10/10 passed**.
[Transcript and archive paths](validation/c-bounded-arrays/user-reported-results.md).
The raw archive and actual checkout/binary identity remain uninspected. The
requested current-engine readonly-table rerun remains unreported. Earlier counts
are historical. Cache state admission work is recorded below; sequence claims
remain outside the current result contract.

## M3 cache state admission and reports

Both reviewed cache adapters now prove initialization and mode-specific
preservation before native input execution. Missing/refuted/unknown obligations
block replay and condition discovery. Agent rounds restore this gate only after
the existing source/tool identity checks. Complete typed post-state fields are
validated alongside the native invariant flags.

Reports name private state, call/environment inputs, the initializer, preservation
domain and required state obligations. Missing required evidence cannot be
published as EXACT/PARTIAL. Equality observes the return; private cache bytes are
not compared to a fictitious reference cache. A new [14-check stage](../cases/cache_state/README.md)
uses both families, both entry modes, invalid initialization/preservation, missing
solver and resumed scripted agent sessions. Local evidence is recorded
[here](validation/cache-state/README.md). The user now reports **14/14 passed;
inputs/tools unchanged=True**, including agent-config-cache PASS.
[Transcript and archive paths](validation/cache-state/user-reported-results.md).
The raw archive and actual checkout/binary identities remain independently uninspected.

This strengthens the existing reviewed cache adapters. It does not admit arbitrary
stateful C contracts, synthesize invariants or establish unrestricted sequence
equivalence. In `empty` mode, preservation covers an empty entry only, not all
invariant states. Frozen transfer experiments retain their original checkout.

## M3 baseline gate and M4 demonstration slice

The recorded array 10/10 and cache-state 14/14 meet the implemented M3 baseline
acceptance at the user-reported evidence level. This does not complete the future
arbitrary-stateful-C or sequence-equivalence research goals. The current-engine
full readonly-table rerun remains unreported; its earlier 9/9 is historical.

The [unified C quickstart](C_TOOL_QUICKSTART.md) now runs seven existing scenarios:
scalar all-input equality, prime lookup, array swap, both cache families, no equal
inputs and a real query-budget limit. An eighth check requires a solver equality
counterexample with identical returns but different arrays, already replayed by
the backend. Its Chinese overview shows actual conditions, domains, observations,
state obligations and archive-relative report/input/evidence links. Engine, source,
input-copy and executable identities must remain unchanged for demo READY.

Eight new local assembly tests pass. An actual MSVC/missing-ESBMC run remains
INCOMPLETE 0/8, all seven cases UNKNOWN with no native samples or conditions.
[Local evidence](validation/c-tool-demo/README.md). The user now reports
**C TOOL DEMO READY 8/8; engine unchanged=True**.
[Transcript, overview and archive paths](validation/c-tool-demo/user-reported-results.md).
The raw overview, witness and actual run identities remain independently uninspected.
The proof engine and fixtures were not modified. This packages known examples;
clean Linux environment reproduction, held-out integration and raw archive audit
remain open M4/review work. No new agent or discovery-performance claim is made.

## M4 independent checkout / Python environment reproduction

[The Linux reproduction entrypoint](C_TOOL_REPRODUCTION.md) fixes a Git commit,
clones it without hard links or borrowed objects, creates a fresh venv without
system/user site packages, installs pinned wheels, and runs the unified demo.
It checks custom ESBMC help markers, executable identity, clean checkout and
actual imported dependency location. Input source, wheels, commands, failures and
demo artifacts receive a separate checksum archive; checkout/venv remain outside
that archive for inspection. Uncommitted source files are excluded and untouched.

Eight local lifecycle tests pass, including a real Git dirty/untracked exclusion
check. Windows execution correctly produces INCOMPLETE/LINUX_REQUIRED before any
installation or solver steps. [Local records](validation/c-reproduction/README.md).
Full Linux READY is pending. This is source/Python isolation on the existing host,
not a fresh OS or container; compiler, modified ESBMC and system libraries remain
external dependencies. No backend replacement or automatic solver build occurs.
Independent held-out integration and clean-host release validation remain open.

## Current transfer experiment

The three-input interval-check experiment is implemented at `52df7d1` under
[`cases/c_scalar_transfer`](../cases/c_scalar_transfer/README.md). The engine is
frozen at `5502520` (pre-experiment checkout `61ba47b`); 16 file hashes are checked
by the stage. Four C sources and four contracts cover full equality, no equal
inputs, and a relational equivalence region on two domains. Optional generic
field-order atoms use the existing hypotheses interface; no engine changes.

Nine targeted local tests passed without skips, including native fixture checks
and missing-solver preservation. [Local evidence](validation/c-transfer/README.md).
The user now reports **8/8 required runs passed, 8/12 discovery EXACT**, with
all reports valid and engine/inputs/tools unchanged. By the published schedule,
the four exploratory default-vocabulary reordered runs were non-EXACT; their
PARTIAL/UNKNOWN breakdown and reasons await the detailed metrics. One ordered
0..31 run reports 32 queries and 5.920 seconds.
[Transcript, interpretation and evidence paths](validation/c-transfer/user-reported-results.md).
This is user-reported evidence from an authored integration experiment; raw logs
remain unaudited, and no blind-case, autonomous-agent or speedup claim follows.

## Evidence baseline

For the new agent workflow, local testing has covered 90 distinct tests across
the baseline and final targeted runs, including 21 new tests and no skips.
[Current local validation](validation/agent-workflow/README.md). On 2026-09-16,
the user supplied a Codespace summary reporting **AGENT WORKFLOW ACCEPTANCE:
8/8 passed**. [Result transcript and archive location](validation/agent-workflow/user-reported-results.md).
This is scripted protocol acceptance, separate from the earlier 24/24 vocabulary
comparison and from any future autonomous-agent evaluation.

These are historical results, **not a fresh 2026-09-15 formal rerun**.

| Validation | Result | Provenance |
|---|---|---|
| Windows unit/native tests at 8e85664 | 69 passed | [Committed local log](validation/vocabulary-comparison/local-tests.txt); includes native/mocked checks, not ESBMC proofs |
| Old relational regression | 6/6 | User-pasted Codespace output |
| Cache finder | 5/5 | User-pasted Codespace output |
| Config cache | 3/3 | User-pasted Codespace output |
| Sketch controls | 8/8 | User-pasted Codespace output |
| Extended prime acceptance | 8/8 | User-pasted Codespace output |
| Vocabulary comparison | 24/24 certified; paired inputs match=True | User-pasted summary; [transcribed measurements](validation/vocabulary-comparison/user-reported-results.md) |
| Agent workflow protocol | 8/8 passed, including expected missing-solver UNKNOWN | [User-pasted summary](validation/agent-workflow/user-reported-results.md); original archive not independently opened here |
| C scalar integration | 8/8 passed | [User-pasted summary](validation/c-scalar/user-reported-results.md); run-specific source/binary hashes and raw logs not independently inspected |
| C scalar transfer | 8/8 required passed; 8/12 discovery EXACT; engine/inputs/tools unchanged | [User-pasted summary](validation/c-transfer/user-reported-results.md); baseline PARTIAL/UNKNOWN breakdown and raw logs not supplied |
| M2 result contract | 10/10 passed, including agent-partial | [User-pasted summary](validation/m2-results/user-reported-results.md); includes expected failure/UNKNOWN controls, raw archive not independently inspected |
| Scalar demonstration | READY, 5/5 checks, tools unchanged=True | [User-pasted summary](validation/c-demo/user-reported-results.md); raw overview, formula and witness not independently inspected |
| Generic C local const tables | 9/9 passed; scripted agent EXACT n != 9 on 0..31 | [User-pasted summary](validation/c-readonly-tables/user-reported-results.md); includes expected UNKNOWN/rejection controls, raw archive uninspected |
| Generic C bounded arrays | 10/10 passed | [User-pasted summary](validation/c-bounded-arrays/user-reported-results.md); includes negative controls, raw archive uninspected |
| Private-cache state | 14/14 passed; inputs/tools unchanged=True | [User-pasted summary](validation/cache-state/user-reported-results.md); negative controls and scripted agent resumes included, archive uninspected |
| Unified C demonstration | READY 8/8; engine unchanged=True | [User-pasted summary](validation/c-tool-demo/user-reported-results.md); seven examples plus replay check, raw archive uninspected |
| Isolated source/Python reproduction | READY | [User-pasted transcript](validation/c-reproduction/user-reported-results.md); host toolchain reused, raw archive and identities uninspected |
| External-source C integration | READY 5/5 required; exploratory 0/1 EXACT; engine frozen=True | [User-pasted summary](validation/c-external-bits/user-reported-results.md); popcount_32 UNKNOWN/SOLVER_TIMEOUT, raw archive uninspected |
| Popcount scaling | RECORDED 10/10 valid; full-domain certified 8/10; r2-b8 EXACT | [User-pasted summary](validation/popcount-scaling/user-reported-results.md); subsequent CSV identifies 8/12/16/24-bit EXACT and 32-bit timeout twice each; raw archive uninspected |
| Popcount query-timeout comparison | RECORDED 4/4 valid, certified 0/4; 30/120 seconds both UNKNOWN twice | [Supplied traces and CSV](validation/popcount-budget/user-reported-results.md); equal-query timeouts, raw archive uninspected |
| Popcount three-edge bridge | RECORDED, links certified 2/3, endpoint UNKNOWN, mutant rejected=True | [Supplied summary/overview](validation/popcount-bridge/user-reported-results.md); edge_1 UNKNOWN/SOLVER_TIMEOUT, end links certified, raw archive uninspected |
| Popcount six-edge refinement | RECORDED, links certified 6/6, endpoint PROVED, mutant rejected=True | [Supplied summary/CSV](validation/popcount-refined/user-reported-results.md); six full-domain post-checks PROVED, raw archive uninspected |
| External-chat prime trial | EXACT in 1 round, 4 total queries, 1.118 reported active seconds | [Reported context, assistant proposal and result](validation/agent-workflow/live-prime-trial/README.md); familiar candidate, integration evidence only |

Formal environment: existing Codespace project at
`/workspaces/faas-python-c-verification`, modified ESBMC at
`/workspaces/esbmc-current/build/src/esbmc/esbmc` (historically ESBMC 8.4.0).
Its help was confirmed to expose `--equiv-py-target` and `--equiv-c-target`.
The newer C harness route invokes C assertions directly; it does not itself use
those relational retargeting switches.

Recovery instructions: [Linux IDE migration](LINUX_IDE_MIGRATION.md).
The pinned recovery build workflow has not been independently completed locally.
Keep the working Codespace and its customized binary/source and evidence.

## Next handoff

1. Protocol acceptance is now user-reported 8/8 on Codespace; preserve its archive.
   No local formal rerun or independent archive audit was performed here.
2. The first external-chat proposal session now reports EXACT in one round. Stop
   that completed session; retain its original artifacts. It used a familiar
   candidate and does not establish unseen-case discovery or agent speedup.
3. Scalar acceptance is user-reported 8/8; transfer now reports 8/8 required and
   8/12 EXACT. Preserve both separate archives. Inspect the transfer metrics for
   baseline statuses/reasons and actual conditions before comparing performance.
   M2 acceptance is now user-reported 10/10; preserve its separate archive.
   The scalar demo now reports READY (5/5); preserve its separate archive.
   Inspect its overview and JSON/Markdown reports for usability and remaining
   M2 edge cases. M3 local const-table acceptance is now user-reported 9/9;
   preserve its separate archive and completed agent session. Array input/output
   schema 2 now has user-reported 10/10; the readonly-table rerun remains
   unreported. Cache-state is now user-reported 14/14 with unchanged inputs/tools.
   These separate results meet the implemented M3 baseline gate. The unified
   C demonstration now has user-reported READY 8/8. Independent-checkout/fresh-venv
   reproduction is now user-reported READY; preserve its archive. External-source
   integration now reports READY 5/5 required; full-width popcount stays UNKNOWN
   due to solver timeout. Preserve that original archive. The separate
   [popcount scaling run](validation/popcount-scaling/user-reported-results.md)
   now reports 10/10 valid measurements and 8/10 full-domain certificates. The
   supplied CSV now identifies both uncertified rows as 32-bit UNKNOWN with
   equal-query SOLVER_TIMEOUT. All widths use five queries; the 24-bit successful
   discovery mean is 35.883 seconds (multiple queries). The subsequent
   [30/120-second comparison](validation/popcount-budget/user-reported-results.md)
   now reports UNKNOWN for all four rows, with the same equal-query timeout.
   Retain those failures. The subsequent
   [intermediate-program chain](validation/popcount-bridge/user-reported-results.md)
   reports 2/3 certified links; only its middle edge (all four byte replacements
   together) remains UNKNOWN/SOLVER_TIMEOUT. The separate
   [six-edge refinement](validation/popcount-refined/user-reported-results.md)
   now reports all six links certified, endpoint PROVED and mutant rejected=True.
   This completes the manually guided full-width proof milestone. Preserve the
   archive and all earlier failed attempts; a documentation update needs no rerun.
   Current priority has shifted to the user-approved input-support expansion.
   Schema 3 domain acceptance is user-reported 13/13. Run the new capacity/length
   stage, then continue integer types and structured inputs.
   Reusable chain proposals remain planned; autonomous proposal generation and
   partial-region composition remain unimplemented.
   This is one repeated program pair, not ten independent programs.
   [C prototype milestone](C_TOOL_MILESTONE.md) summarizes the current capability.
   Full clean-host/independently held-out release gates remain open; new external
   cases are known algorithms selected after the engine freeze, not blind tests.
   Continue authorized work directly after evidence updates; reserve summaries
   for meaningful milestones. Preserve the frozen transfer baseline; raw remote
   archive inspection remains open.
4. The school/cloud changes remain unlocated; inspect any supplied branch/patch
   before integrating overlapping work. No remote update was found on the working
   branch beyond `5446b31` when capacity/length development began.

The workflow is recorded in [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md). It is a working
file protocol, not an autonomous API client or automatic invariant synthesizer.
