# Project status and handoff

Updated: 2026-09-15. This is the primary handoff entry point; Git and source code
remain authoritative. Roadmap items are not implemented capabilities.

## Current objective

Deliver a reproducible tool that accepts supported pairs of C functions and an
explicit contract, discovers sufficient equivalence conditions, and certifies
the exact equivalence region when possible. Then evaluate its limitations and
reuse in other same-language backends. See [the plan](DEVELOPMENT_PLAN.md).

## Repository audit

Repository: https://github.com/Zehsong/faas-python-c-verification

- Working branch: `codex/same-language-cache`.
- Latest implementation inspected: `8e856641015ef10ffd0e2262b61b0d3dcf3aa3a9`.
  The handoff documentation is added in a later commit on this same branch.
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
| Evidence tooling | Source/command snapshots, JSON/CSV results, archived runs and checksums | Historical archives are in the user's Codespace, not automatically in Git |

Key code: [oracle](../tools/verify-equiv/verify_equiv.py),
[C harness route](../tools/verify-equiv/verify_c_harness.py),
[search](../tools/find-cond-equiv/predicate_search.py),
[shared runner](../tools/find-cond-equiv/find_cache_conditions.py),
[prime adapter](../tools/find-cond-equiv/find_prime_conditions.py).

The shared runner is still cache-oriented: the prime adapter subclasses
`CacheBackend`, and importing the runner loads a cache sketch. New cases still
need Python adapters, model/probe code and hand-specified proof obligations.
These are the main integration gaps before a reusable C tool release.

## Evidence baseline

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

1. Locate the school/cloud changes before implementing overlapping functionality.
2. Agree the C v0.1 contract and unsupported-feature behavior.
3. Build a generic scalar C input adapter and neutral shared runner, then reuse
   it on an unseen function pair without changing the search engine.
4. Prioritize adaptive vocabulary after the generic workflow is usable, or only
   earlier if review of the school changes shows it already exists.

This audit changes documentation only. No generic adapter or adaptive algorithm
has been implemented by the audit itself.
