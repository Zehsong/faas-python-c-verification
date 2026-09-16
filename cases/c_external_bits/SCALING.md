# Population-count domain scaling

The user-reported external integration at `129df96` passed five required cases,
while full-width population count returned UNKNOWN/SOLVER_TIMEOUT. This new
experiment investigates that outcome without changing the programs or engine.
It does not replace the original run, enlarge its budget, or call its timeout
an inequivalence counterexample.

## Fixed protocol

- The identical loop and parallel population-count files from the external
  integration are used; attribution and adaptation notes remain in README.md.
- Input remains `uint32_t`. Only the upper bound changes: 2^b - 1 for
  b = 8, 12, 16, 24, 32. The lower bound stays zero and unwind stays 34.
  Contract names also identify their width. No loop shortening or arithmetic
  width change occurs; C source bytes are preserved in the evidence.
- Two repetitions, first ascending and then descending width. Each invocation
  starts a new finder/backend run; no discovered predicates, native labels,
  proposed conditions or artifacts are carried between runs.
- Same per-query timeout 30 seconds, discovery wall budget 300 seconds and
  query budget 96 as the external integration. No automatic retries or tuning.
- Full-domain expected condition `true` is checked separately only after an
  EXACT result. Its query/log is outside discovery metrics. This known answer
  is never supplied to discovery.
- Existing `engine-lock.json` fixes the 17 core/dependency files at `7cc44b5`.
  Source, snapshot, generated-contract and tool identities are checked before
  and after execution. No changes to search, safety gates or proof interpretation.

## Outputs and interpretation

The overview and metrics.csv retain every scheduled run: status, actual condition,
query count, discovery seconds, timeout count/kinds and diagnostic codes. Raw
queries, original reports, source and engine snapshots, tools, full-domain
post-checks and the fixed schedule are preserved in results.json/the archive.

`POPCOUNT SCALING: RECORDED` means all ten runs have valid measurement records
and identities are unchanged. **It does not mean ten successful proofs.**
UNKNOWN/PARTIAL, including safety timeouts, can be valid measurements; missing
tools, compile failures, malformed reports, replay errors and engine drift make
the stage INCOMPLETE. The full-domain certificate count is reported separately.
A failed or unknown post-check never contributes to that certificate count.
An unexpected refutation of the full-domain post-check makes measurement review
necessary and the stage INCOMPLETE; the result is retained.

Timeouts are censored observations, not proof completion times. Do not average
successful runs alone or infer an exact complexity threshold from two repeats.
Reversing order reduces a simple order confound but does not control host load
or provide a statistical performance claim. Domains also affect generated
default predicates/seeds, so this measures the whole unchanged tool workflow,
not just an isolated solver algorithm. This is a follow-up to an observed
failure on a known case, not a blind benchmark or autonomous-agent evaluation.

## Run

```bash
bash cases/c_external_bits/run_scaling.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The wrapper runs six measurement controls and the ten scheduled runs, and stores
a separate `popcount-scaling` archive in `$HOME/equiv-evidence`, including failure
records. Existing external-integration results are untouched. Ten discovery
budgets can take up to about 50 minutes in total, plus compilation, startup and
post-checks; this is a budget bound, not a runtime prediction. Do not interrupt
just because a 32-bit case times out: it is retained and the next scheduled run
continues.

Local unit and missing-solver controls are separate from formal measurements;
formal results are pending. See the repository's
[validation record](https://github.com/Zehsong/faas-python-c-verification/blob/codex/same-language-cache/docs/validation/popcount-scaling/README.md).
