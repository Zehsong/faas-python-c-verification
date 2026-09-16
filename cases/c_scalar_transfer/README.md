# Scalar transfer experiment: reordered interval checks

This example was authored **after** the scalar engine at `5502520` passed its
user-reported 8/8 integration stage. The baseline immediately before adding these
files is `61ba47b`. No finder, frontend, backend or oracle source changes are part
of this experiment. A checked hash manifest enforces that boundary.

It is a new integration example, not an independently selected blind benchmark:
the same developer authored the C fixtures, contracts and assessment expectations.
No runtime speedup of the C refactoring or autonomous-agent effectiveness is
claimed. The user has reported **8/8 required runs passed and 8/12 discovery EXACT**,
with engine/inputs/tools unchanged. See the [result record and evidence paths](../../docs/validation/c-transfer/user-reported-results.md);
raw solver logs and the detailed baseline outcomes have not been inspected here.

## Program and domain

The reference returns `low` if `x < low`, otherwise `high` if `x > high`, otherwise
`x`. It is compared with three candidates:

| Candidate | Change | Expected return-equivalence condition |
|---|---|---|
| expression | Same ordered checks in a conditional expression | true |
| offset | Add 1u to the reference result | false |
| reordered | Check the upper bound before the lower bound | low <= high OR x <= high OR x >= low |

All three inputs are independent uint32 scalars. **There is no assumption that
low <= high.** The programs have defined behavior even with inverted bounds;
their behavior then differs precisely for `high < x < low`. For example,
`x=3, low=5, high=1` returns 5 in the reference and 1 in the reordered candidate.
At `x=low` or `x=high`, the results again agree. This stresses relations among
three inputs, beyond a single excluded constant or one equality comparison.

The reordered pair is tested on rectangular domains 0..7 and 0..31 for each
input. The fully equivalent and fully unequal controls use 0..31. The latter
also checks the useful meaning of EXACT with condition `false`: the domain is
nonempty, but every input produces unequal returns.

## Frozen engine and vocabulary comparison

The existing default vocabulary contains input equalities and constants; its
counterexample refinement adds more equality constants. A finite vocabulary of
this shape may not describe the relational region within the fixed budget.
The experiment compares it with an optional JSON hypothesis file containing
**all six ordered comparisons between distinct input names**, generated solely
from the contract's fields. No expected formula, output label, extra seed or
program-body analysis is supplied to discovery.

Both modes use the same sources, domains, 27 boundary seeds, 24-predicate limit,
96-query limit, 120-second discovery budget and 20-second per-query timeout.
Each reordered pair is run twice per mode, reversing mode order on repetition
two. Fully equivalent/unequal controls run twice with the default vocabulary.
This produces 12 total discovery runs. Ordered-mode success is a test objective,
not a result assumed by the runner; failures remain visible and fail that gate.

Expected formulas are checked by separate ESBMC obligations **after** discovery.
PARTIAL baseline conditions receive a separate sufficiency check. These
assessment queries/times are separate from discovery metrics and are not used to
continue or repair its search. UNKNOWN is preserved with available reasons.

`engine-lock.json` pins the 16 non-test engine/oracle/dependency-list files as
SHA-256 of UTF-8 text with LF-normalized newlines. It rejects edits and additional
finder Python modules. Original raw sources and generated harnesses retain their
own run snapshots/hashes. Compiler/ESBMC binary identity and experiment inputs
are checked before/after the experiment. This does not lock all system headers,
shared libraries or toolchain dependencies. The manifest guards experimental
consistency; it is not a security boundary against an editor changing the lock.

## M2 compatibility note

This is a frozen historical experiment. Current M2 code intentionally fails its
unchanged engine lock. Rerun in the original checkout using the commands below;
use [the M2 stage](../../docs/RESULT_FORMAT.md) to validate the current engine.
Do not refresh the lock to pretend the engine is unchanged.

## Run in Codespace

```bash
cd /workspaces/faas-python-c-verification
git worktree add --detach ../faas-transfer-baseline 52df7d1
cd ../faas-transfer-baseline
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
bash cases/c_scalar_transfer/test_transfer.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The script keeps your modified ESBMC and creates a separate `c-transfer-*.tar.gz`
archive. Do not delete or overwrite the earlier scalar archive. The new archive
contains the console, local controls, per-run source/contract/harness snapshots,
proof logs, `results.json`, `metrics.csv`, and the experiment's input snapshot.

The intended gate is:

```text
C TRANSFER ACCEPTANCE: 8/8 required runs passed
Discovery EXACT: .../12; all reports valid=True; engine unchanged=True; inputs/tools unchanged=True
```

Eight required runs are the two control pairs and the two ordered-vocabulary
reordered-domain runs, each repeated twice. Four default-vocabulary reordered
runs are exploratory: PARTIAL/UNKNOWN are permitted, and are not counted as
EXACT or as required successes. Any invalid claimed certificate, missing safety
proof, mismatched initial replay or changed inputs/tools fails the experiment.
Read both summary lines and the exit code; `8/8` is **not** a claim of `12/12 EXACT`.
For a shorter smoke run, pass `1` as the script's second argument (4 required,
6 total runs); it will not have the two-repeat order balance.

To run one unassisted pair directly, with no new adapter:

```bash
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract cases/c_scalar_transfer/reordered_31.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

That command uses the engine's ordinary CLI defaults. Use the experiment script
for matched-budget comparisons and the automatically generated ordered JSON.

## Preparation work and current evidence

| Work | Amount | Provenance |
|---|---|---|
| C fixture source | One reference, three candidates | Newly authored synthetic functions |
| Contracts | Four JSON files, including two domains for reordered checks | Explicit domain/parameter/return choices |
| New Python adapter / manual harness / manual probe | Zero | Existing scalar frontend generates both C harnesses |
| Engine edits | Zero | Manifest plus Git diff |
| Optional search guidance | Six generic field-order atoms; zero extra seeds | Generated from names, no condition answer |
| Experiment-only code | Runner, local tests, Bash stage and lock manifest | Measurement and assessment infrastructure |
| Human preparation time | Not measured | Do not infer time savings from file counts |

Nine local tests passed with MSVC, no skips. Native controls execute all 512
triples in 0..7 for each of the three candidates. A separate arithmetic check
checks the expected relational formula over all 32,768 triples in 0..31. Neither
is a universal SMT certificate. A missing-solver run preserves all six UNKNOWN
results, zero traces, and 0/4 required passes. See
[local logs](../../docs/validation/c-transfer/README.md).

The reported totals imply four non-EXACT exploratory default-vocabulary runs;
their PARTIAL/UNKNOWN breakdown and reasons are not supplied. One ordered run
on 0..31 reports 32 queries and 5.920 seconds; this is not a paired speedup.
Next inspect the detailed metrics, then prioritize M2's stable result schema
and diagnostics, informed by observed limitations. A separately sourced real
program pair and any unattended-agent comparison remain further evaluation work.
