# Proposed C tool development plan

2026-09-15 proposal based on inspected implementation `8e85664` and the user's
request to deliver a usable C tool before broadening language support. Review
unlocated school/cloud changes before implementing overlapping work.

## 2026-09-16 implementation update

M1's first pure scalar C slice is implemented: checked contracts, controlled
harness/probe generation, shared discovery and `--case c` agent sessions. Three
new families plus a mutant require only C/JSON fixtures. Native/admission controls
pass locally. The user has now reported 8/8 for the new scalar integration stage;
[provenance and archive paths](validation/c-scalar/user-reported-results.md). This
clears the first scalar acceptance gate at user-reported evidence level. The
subsequent transfer and M2 results are recorded below. See
[scope, commands and remaining limits](C_SCALAR_TOOL.md).
Broader syntax, array interfaces and unseen-case evaluation remain later gates;
the local constant-table slice is recorded below.

## Post-freeze transfer check

The [interval-check experiment](../cases/c_scalar_transfer/README.md) now tests
newly authored three-input programs using only C/JSON bindings. The engine is
locked to the accepted scalar implementation. Default and generic field-order
vocabularies use matched budgets/seeds, with failures retained. Nine local
controls pass. The user now reports 8/8 required runs passed and 8/12 discovery
EXACT, with unchanged engine/inputs/tools.
[Reported result and limits](validation/c-transfer/user-reported-results.md).
The four default-vocabulary exploratory runs were non-EXACT; detailed reasons
remain unavailable. This is integration evidence, not a separately sourced
real-world or blind case, and establishes no paired speedup. The subsequent M2
result/status/reason fields and diagnostic controls preserve this frozen
experiment baseline for future comparisons.

## M2 implementation update

Versioned JSON and human reports are now implemented for finder and agent
sessions, with backward-compatible legacy artifacts, certified partial-union
fallback, explicit empty domains and structured failure codes. Local regression
passes; the user now reports **10/10 passed** for the
[M2 acceptance stage](RESULT_FORMAT.md). [Transcript and provenance](validation/m2-results/user-reported-results.md).
The raw archive and actual run identities remain uninspected. CLI usage/output-
directory failures are not promised artifact-producing runs. The existing frozen
transfer lock is preserved, so its old experiment must be rerun in its original
checkout. The subsequent scalar demonstration result is recorded below.
Report usability and remaining M2 edge-case review precede M3 memory/state expansion.

## M1/M2 demonstration update

A [guided scalar demo](../cases/c_scalar_demo/README.md) is implemented without
engine changes: four existing result scenarios, a report index, editable C/JSON
copies, a backend-replayed counterexample and a separate evidence archive.
Six local assembly controls and a real missing-solver negative run are checked;
the user subsequently reports **READY (5/5 checks; tools unchanged=True)** from
Codespace. [Transcript and provenance](validation/c-demo/user-reported-results.md).
Raw archive inspection and report usability review remain open. The next
capability milestone is M3 bounded arrays/state; the demo need not be rerun
merely to record this result.
This demonstrates the first usable slice ahead of M3. It does not claim a full
M4 release, a disconnected-region demo or independent held-out evaluation.

## M3 first implementation slice

[Bounded local constant tables](../cases/c_readonly_tables/README.md) are now
admitted by the generic scalar C frontend, enabling computation-versus-lookup
through C/JSON alone. Full literal initialization, readonly indexed use, no
pointer decay and whole-domain safety are required. Inputs/observations remain
scalar. This is a preparatory part of M3, not completion of its array-output and
state-copy goals. Search grammar and candidate certification remain shared.

136 local tests pass; the user now reports **9/9 acceptance passed**, including
the scripted agent EXACT condition n != 9 on 0..31.
[Transcript and provenance](validation/c-readonly-tables/user-reported-results.md).
Raw archive inspection and report review remain open. The subsequent bounded
array slice is recorded below. Independent mutable cache state and sequence
obligations remain later; array equality must not be inferred from return equality.

## M3 bounded array implementation

Schema 2 now defines bounded array arguments, identical initialized independent
copies and mandatory observations of every final element plus the return. The
first limit is four input scalar values including all array elements, with no
aliasing or unrestricted pointer syntax. Shared native comparison now covers
full observation vectors throughout search, agent screening and witness replay.
[Contract, examples and commands](../cases/c_bounded_arrays/README.md).

149 local tests pass. The user now reports **array 10/10 passed**;
[transcript](validation/c-bounded-arrays/user-reported-results.md). The current-engine
const-table rerun remains unreported. This implements the small array part of
M3, not cache state/sequence obligations or full release gates. The user prefers
autonomous continuation between stages and summaries only at meaningful milestones.

## M3 cache state admission update

The existing two cache families now gate all native inputs on initialization and
mode-specific preservation, validate typed post-state values, and declare required
state evidence in the common result contract. Resumed agent sessions restore the
gate under unchanged identity. The [14-check acceptance](../cases/cache_state/README.md)
now has user-reported **14/14 passed; inputs/tools unchanged=True**.
[Evidence record](validation/cache-state/user-reported-results.md). It includes real invalid-state
obligations rather than assuming a successful return establishes preservation.

The separate array 10/10 and cache-state 14/14 reports meet the implemented
M3 baseline gate at user-reported evidence level. Their raw archives remain uninspected. Arbitrary stateful C admission and sequence-equivalence certificates are
not implied. Preserve the earlier frozen transfer baseline and use current result
reports for the demonstration release.

## M4 unified demonstration implementation

A [single quickstart](C_TOOL_QUICKSTART.md) now packages scalar, computation/lookup,
array and private-cache reports into a Chinese overview. Seven existing scenarios
plus one same-return/different-array replay check form an 8-check demonstration.
Only actual result conditions are displayed; budget/tool failures remain distinct,
inputs and tool identities are checked, and overview links survive archiving.

Eight assembly tests pass and the absent-solver run correctly stays INCOMPLETE
0/8. The engine and fixtures are unchanged. The user now reports **READY 8/8;
engine unchanged=True** ([record](validation/c-tool-demo/user-reported-results.md)). This is a
presentation/reproduction slice: clean Linux setup, an independently held-out
case and evidence audit are still required before calling M4 complete. Do not
relabel the known demo cases as unseen research evaluation.

## M4 isolated reproduction implementation

A [Linux wrapper](C_TOOL_REPRODUCTION.md) now fixes the source commit, creates an
independent checkout and fresh Python venv, installs/archives pinned dependency
wheels, and reruns the unified demonstration. Host compiler and modified ESBMC
identities are recorded and checked; both remain external rather than rebuilt.
Eight lifecycle tests and a real local Git exclusion control pass; full Linux
execution is pending. This addresses workspace/Python contamination. It must not
be relabelled as fresh-host/container reproduction or completion of all M4 gates.
Held-out integration and broader environment validation remain separate work.

## Release target

A new user supplies two supported C functions, their entry points, build inputs,
input domain and observations. The tool builds a relational harness, searches
conditions, and produces a readable report plus reproducible proof artifacts.
For the first release, manual contracts are acceptable; adding an ordinary new
case should not require editing the finder or writing a new Python backend.

For deterministic, defined, terminating executions under a declared domain D,
let E mean equality of the chosen observations. A sufficient condition proves
`D && condition => E`. An exact region additionally proves
`D && !condition => !E`. Neither formula claims anything outside D.

Keep domain feasibility separate from these claims. Empty domains must be
reported explicitly. A valid nonempty domain with condition `false` can still
have an exact result when all its inputs are proved unequal.

## Milestones and release gates

| Stage | Deliverable | Acceptance criterion |
|---|---|---|
| M0: continuity | Status, change log, branch/evidence inventory; locate cloud work | A fresh task can identify the actual baseline, pending work and validation provenance |
| M1: generic scalar C workflow | One CLI/config format; typed inputs, entry points, source/build context, generated harness and probe | At least three new scalar function pairs run through configuration alone; shared engine unchanged |
| M2: stable result contract | Human report and versioned JSON; explicit sufficiency/exactness, UNKNOWN reasons, replay and evidence | Correct, partly equivalent, fully unequal, empty-domain, timeout, unsupported and insufficient-unwind controls behave as specified |
| M3: bounded memory and state | Bounded array observations; explicit independent state copies and cache sketch adapter | One array case and both existing cache families use the common result/evidence interface without shared-state interference |
| M4: demonstration release | Pinned setup, short quickstart, representative benchmark and release evidence | A clean Linux environment can reproduce the advertised commands; a held-out case can be added without modifying the engine |
| M5: research evaluation | Adaptive predicates, scaling and failure analysis, then second-language feasibility | Same-budget comparisons include failures; distinguish reusable engine code from frontend/semantic adaptation |

M1 and M2 form the first usable vertical slice. Do not wait for M3 or every
research experiment to demonstrate that slice. Target milestones by acceptance
criteria rather than promising dates before reviewing the school work.

## Initial C support contract

- Start with pure, sequential scalar functions with explicitly supported fixed
  width unsigned types and boolean observations. Multiple scalar inputs matter
  more initially than pretending all of C is supported.
- Accept two source files or declared translation-unit inputs and entry names.
  Specify include paths, defines and compiler/target assumptions. Handle symbol
  collisions through a reviewed compilation/renaming strategy; reject unsupported
  cases explicitly rather than rewriting arbitrary C with regular expressions.
- Preserve C arithmetic and integer-promotion semantics. Signed integers require
  a deliberate safety/overflow policy and matching native/solver interpretation;
  defer them if that policy is not ready.
- Loops require explicit bounds and completeness checks. Exhausted unrolling,
  timeout or a failed safety obligation must not become an equivalence result.
- Begin with return observations; add bounded output arrays explicitly in M3.
  Do not silently treat return equality as whole-program equivalence when calls
  mutate visible memory or perform I/O.
- Declare unsupported I/O, concurrency, unrestricted heap/pointers, external
  nondeterminism and unsupported dependencies. UNKNOWN or an explicit unsupported
  diagnostic is a valid tool outcome.
- Stateful support retains manual invariants and initialization/preservation
  obligations. One-step conditional equivalence does not automatically imply
  arbitrary-sequence equivalence.

## Internal structure

The user subsequently approved agent-assisted development. See
[the recorded workflow](AGENT_WORKFLOW.md): a first file-mediated proposal/check/
feedback session is now implemented over the reviewed adapters. It accepts
conditions and inputs; the scalar route now accepts checked initial C bindings
and generates its own harness. Arbitrary agent harnesses remain disallowed. Evaluate unattended
provider transport and predicate selection. This does not change the release
requirement that new supported scalar cases avoid custom Python backends.

Separate a language-neutral condition search interface from the C-specific
frontend/harness, native execution and ESBMC adapter. Keep existing proof and
replay behavior while extracting the cache-specific runner dependencies.

The frontend owns typed inputs, assumptions, state and observations. Discovery
owns predicate proposals and region partitioning. The verifier owns proof
queries and counterexamples. The report records which claims were certified and
under which scope. This separation can later support another language without
claiming its frontend or runtime semantics are already solved.

Proposed CLI names such as `find`, `verify`, `replay` and `report` describe desired
operations only; they are not current executable commands.

## Evaluation and demonstration

Use at least three families: scalar arithmetic/branches, computation versus
lookup, and bounded state/memory. Include positive and intentionally faulty
variants plus cases where the engine cannot decide. Reserve examples not used
to tune predicates or templates.

Measure correctness of claims, certified coverage where measurable, query and
wall time, condition size, manual integration effort, and failure causes. A
condition's character count is not proof of logical minimality. A bounded
exhaustive reference is useful for independent checks on small domains; it must
not supply the answer to the discovery algorithm.

For the demo, show one wholly equivalent pair, one conditional region (including
disconnected regions), one replayed counterexample and one honest UNKNOWN. The
report must show input domain and observations beside the conclusion.

## Priorities and deferred work

The immediate bottleneck is reusable case integration and an understandable
result contract. Modulo predicates helped truncated lookup but harmed the
isolated mutant in existing runs. Adaptive activation is therefore a useful
later experiment, not a prerequisite for the first generic C interface.

Record limitations from the start as the tool's support contract; investigate
their broader research implications after the usable slice exists. Defer
automatic invariant discovery, whole-project extraction, profiler/LLM-driven
optimization, concurrency and claims of arbitrary-language support.
