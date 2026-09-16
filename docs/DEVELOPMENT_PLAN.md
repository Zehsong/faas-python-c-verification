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
Eight lifecycle tests and a real local Git exclusion control pass. Linux
execution is now [user-reported READY](validation/c-reproduction/user-reported-results.md);
the original archive and run identities have not been independently inspected.
This addresses workspace/Python contamination. It must not
be relabelled as fresh-host/container reproduction or completion of all M4 gates.
Held-out integration and broader environment validation remain separate work.

## M4 external-source integration implementation

[Bit-algorithm cases](../cases/c_external_bits/README.md) now compare public-domain
external snippets with authored loop references through ordinary C/JSON files.
The engine is frozen at `7cc44b5` in a new lock; the older transfer lock remains
unchanged. Five required cases cover full-width power-of-two variants and a
byte-domain population count; full-width population count is an exploratory
sixth run. Fixed budgets and roles precede formal execution. Expected regions
are checked separately after discovery. No finder/backend edits or proposals
are supplied. Five local/native controls pass. The user now reports READY
5/5 required, engine frozen=True; the full-width exploratory run remains
UNKNOWN/SOLVER_TIMEOUT (safety PROVED, nonempty domain).
[Transcript](validation/c-external-bits/user-reported-results.md); raw archive uninspected.

This exercises the new-case integration requirement with an external source;
it does not meet the stronger independently held-out/blind evaluation gate.
Known answers, documented adaptations and authored references remain explicit.
Broader environment validation and an independently selected case remain open.

## Scaling follow-up to the first full-width timeout

A [separate fixed-budget sweep](../cases/c_external_bits/SCALING.md) now varies
only the popcount input upper bound through 8/12/16/24/32 bits. Two opposite-order
repetitions retain every outcome, query count, elapsed time and timeout kind.
The C arithmetic stays 32-bit, loops and unwind remain unchanged, and the old
experiment is not retuned. Six new measurement controls and five existing
native/integration controls pass locally. The user now reports RECORDED 10/10
valid measurements and 8/10 full-domain certificates; r2-b8 is explicitly EXACT.
[Transcript and subsequently supplied CSV](validation/popcount-scaling/user-reported-results.md)
identify 8/12/16/24-bit EXACT true twice each and 32-bit UNKNOWN/equal-query timeout
twice. All runs use five queries. Raw query logs and archive remain uninspected.

This starts failure/scale characterization while M4's clean-host/independently
held-out gates remain open. RECORDED indicates valid measurements, not proof
success; certificate counts remain separate. Censored timeout observations and
two repetitions do not establish a precise complexity threshold. Use their
actual reports to choose further work; do not tune or claim improvement first.
The supplied CSV now resolves the uncertified cases as 32-bit equality-query
timeouts. Constant query count points to per-query backend cost on this pair;
individual solver phases and a precise threshold remain unknown. A separate
[query-timeout comparison](../cases/c_external_bits/BUDGET.md) uses 30/120 seconds
in two opposite-order repetitions, with full domain, programs, engine, unwind
and 300-second/96-query discovery limits fixed. All four runs are now
[user-reported UNKNOWN](validation/popcount-budget/user-reported-results.md), with
one equal-query timeout in each; neither setting established a certificate.
Fourteen local controls remain separate local evidence. No further automatic
timeout escalation follows; retain the original censored measurements.
[C prototype milestone](C_TOOL_MILESTONE.md) separates capability from open gates.

## Proposed intermediate-program proof chain

A separate [bridge experiment](../cases/c_popcount_bridge/README.md) proposes
byte-loop and byte-parallel implementations between the original loop/parallel
endpoints. Each adjacent pair is checked on the same complete uint32 domain
through the existing C frontend. The endpoint text and engine are pinned;
bridge identity, common scope, safety, EXACT and full-domain expected-condition
proofs are mandatory. A deliberately wrong control must be rejected. Only then
can a report derive endpoint equality by transitivity. There are no assumed
helper lemmas, no automatic decomposition and no partial-condition composition.

Seven initial local controls pass. The user now reports RECORDED, links
certified 2/3, endpoint UNKNOWN and mutant rejected=True. The supplied overview
identifies edge_0/edge_2 as certified in 1.120228/1.768853 seconds; edge_1 is
UNKNOWN/SOLVER_TIMEOUT after 30.912715 seconds. Raw evidence remains uninspected.
[Record](validation/popcount-bridge/user-reported-results.md).
The three edge runs and negative control use 30-second query timeouts and
120-second/96-query discovery budgets. This is a manually proposed proof
strategy, not a demonstrated optimization or autonomous-agent study. If an edge
fails, keep endpoint UNKNOWN and inspect that connection rather than bypassing
its proof. Original direct/scaling/budget results remain separate baselines.

## Refine the unresolved middle edge

A separate [six-edge protocol](../cases/c_popcount_bridge/REFINED.md) proposes
three mixed implementations, replacing one byte at a time between the existing
byte-loop and byte-parallel programs. Each adjacent equality remains a full
uint32-domain obligation. All six links, including both end connections, are
rerun; no old certificate or byte-level lemma is imported. The original three-
edge default and its results remain intact. Per-edge CSV now shows discovery
and full-domain post-check status independently and is printed automatically.

Eleven local checks pass, including the original seven composition/native
controls. The user now reports RECORDED, all six links certified, endpoint PROVED
and mutant rejected=True after `388a2c3`.
[Summary, CSV and limits](validation/popcount-refined/user-reported-results.md).
Query/wall/count limits remain 30 seconds / 120 seconds / 96 per run. The six
reported discovery times sum to 7.302194 seconds, excluding post-checks/setup.
The direct timeout and three-edge results remain unchanged historical evidence.
This completes the manually guided full-width proof milestone for one pair,
not automatic proposal synthesis or a repeated end-to-end speedup evaluation.

The proposed follow-on (now behind the input-expansion priority below) is a reusable checked chain-proposal interface:
explicit ordered sources, common contract scope, immutable original endpoints,
per-link feedback and cumulative budget accounting. Require all links and
negative controls before publishing composition, and preserve UNKNOWN otherwise.
Start with full-domain equality; partial-region composition needs a separate
soundness design. Later assess agent-generated proposals on separately selected
cases, recording proposal effort and failed attempts as well as solver cost.
These are planned capabilities, not implemented features.

## Approved input expansion after the popcount milestone

The user approved replacing the narrow set of input forms with a composable
contract architecture. Current priority order:

1. Normalize complete type domains and explicit relations; then extend integer
   types, record fields and configurable-capacity arrays with logical lengths.
   Preserve C promotions, overflow policy, independent storage and observations.
2. Admit explicitly modeled floating-point semantics, starting with strict
   comparison under a declared format/rounding policy. Approximate relations
   and their error composition require a separate design.
3. Let agents propose checked invariants, relational loop alignment, summaries
   and intermediate programs. Induction and termination obligations require
   backend support checks on the pinned modified ESBMC. No agent prose is a proof.

The first implemented slice is schema 3: optional type-derived bounds plus
checked Boolean relation constraints on current uint32_t/bool scalar and fixed
array fields. One shared domain representation drives symbolic assumptions,
native guards/replay and agent validation. Empty sampled sets do not establish
empty domains; solver feasibility remains authoritative. All results retain
scope constraints. A 13-check acceptance stage includes full-width defaults,
relation-dependent safety, contradictory domains, mixed bool/array constraints
and an out-of-domain agent seed control. The user now reports **13/13 passed;
inputs/tools unchanged=True** after `5446b31`.
[Summary and evidence paths](validation/c-input-domains/user-reported-results.md).

The next capacity slice is implemented: schema 3 physical array sizes 1..64,
128 total initial values, optional explicit length_field with capacity guards,
and unchanged complete physical-array observations. Sparse bounded seed and
predicate preparation avoids a Cartesian explosion without restricting the
symbolic domain. The user reports 10/11 checks passing after `7ad167b`, including
conditional mutations, inactive-tail differences, empty lengths and safety controls.
[Protocol](../cases/c_array_capacity/README.md). Only copy8 remains UNKNOWN:
whole-domain safety passed, but equality and later complement checks timed out.
A checked finite-length partition fallback is now implemented; it requires
coverage and every sub-obligation and does not narrow array-element domains.
Its user-reported rerun after `441fd89` is still 10/11: copy8 coverage and n=0..3
equality prove, but n=4 times out. The next harness change initializes the
partition length with its constant value while leaving all other inputs symbolic;
after `0059a05`, the user now reports **11/11 passed; inputs/tools unchanged=True**.
[Accepted result](validation/c-array-capacity/accepted-results.md). This clears
the capacity gate at user-reported evidence level; the raw archive is uninspected.
The user ended the session at this milestone. Further capability work is deferred
until the user resumes; no additional implementation was started.

This is not completion of the first milestone: new integer types, structs,
richer expressions and dynamic memory still require work.
Retain historical fixed-engine experiments in their original checkouts.

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
