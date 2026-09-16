# Project status and handoff

Updated: 2026-09-16. This is the primary handoff entry point; Git and source code
remain authoritative. Roadmap items are not implemented capabilities.

## Current objective

Deliver a reproducible tool that accepts supported pairs of C functions and an
explicit contract, discovers sufficient equivalence conditions, and certifies
the exact equivalence region when possible. Then evaluate its limitations and
reuse in other same-language backends. See [the plan](DEVELOPMENT_PLAN.md).

## Repository audit

Repository: https://github.com/Zehsong/faas-python-c-verification

- Working branch: `codex/same-language-cache`.
- Latest core implementation: `5502520` (generic C scalar adapter),
  following `23ad4af` (live trial record),
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
| Generic C scalar adapter | Two C files plus checked JSON contract; native probe/harness generation; shared automatic discovery and agent sessions | Pure uint32_t/bool subset, return observation, 1..4 inputs; 8/8 acceptance user-reported, raw archive not independently inspected |
| Agent workflow | Persistent JSON proposal/check/feedback sessions; typed Boolean conditions, native screening, backend certification, cumulative budgets and source/contract/tool drift checks | Built-in adapters plus checked generic scalar C contracts; external chat authors proposals; no automatic model API |
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
admit arbitrary C, tables, pointers or stateful programs through the generic route.

Local validation: 107 distinct tests passed, no skips (105 in the full
regression, followed by 17 targeted scalar tests including two additional controls).
The 17 new tests cover scalar admission, safety gating, bindings and native results.
See [local evidence](validation/c-scalar/README.md). The user subsequently reported
**C SCALAR ACCEPTANCE: 8/8 passed** from Codespace.
[Transcript, evidence paths and provenance](validation/c-scalar/user-reported-results.md).
No raw archive inspection or local formal rerun accompanies this record.

## Current transfer experiment

A new three-input interval-check family is ready under
[`cases/c_scalar_transfer`](../cases/c_scalar_transfer/README.md). The engine is
frozen at `5502520` (pre-experiment checkout `61ba47b`); 16 file hashes are checked
by the stage. Four C sources and four contracts cover full equality, no equal
inputs, and a relational equivalence region on two domains. Optional generic
field-order atoms use the existing hypotheses interface; no engine changes.

Nine targeted local tests passed without skips, including native fixture checks
and missing-solver preservation. [Local evidence](validation/c-transfer/README.md).
The new formal gate and default/ordered results are **pending**, with 8 required
and 12 total runs at the default two repeats. It is an authored integration
experiment, not independent held-out or autonomous-agent evaluation.

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
3. Scalar acceptance is user-reported 8/8; preserve its separate archive. Run
   `cases/c_scalar_transfer/test_transfer.sh` with the existing modified ESBMC.
   Inspect required successes separately from exploratory baseline PARTIAL/UNKNOWN
   outcomes and save the new archive. Then continue M2 result/diagnostic work.
   Raw scalar archive inspection remains open.
4. The school/cloud changes remain unlocated; inspect any supplied branch/patch
   before integrating overlapping work. No remote update was found on the working
   branch beyond `61ba47b` when the transfer experiment was developed.

The workflow is recorded in [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md). It is a working
file protocol, not an autonomous API client or automatic invariant synthesizer.
