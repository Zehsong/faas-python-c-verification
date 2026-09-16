# Result format v1 and human reports

M2 adds two files beside the existing `result.json` for automatic discovery and
agent sessions:

- `verification-result.json`: versioned interpretation of the proof evidence.
- `report.md`: readable scope, condition, obligation statuses, diagnostics and
  artifact locations.

The legacy file, command flags and exit codes remain available. The new summary
is deliberately conservative; an old status alone does not create a certificate.
Its JSON schema is [verification-result-v1.schema.json](../schemas/verification-result-v1.schema.json).
The producer validates proof invariants before writing. No JSON Schema runtime
package is required; local tests also check output structure against the schema.

## Read the outcome

| Status | Meaning |
|---|---|
| EXACT | Within a nonempty declared domain, equality is certified inside the condition and inequality outside it |
| PARTIAL | A sufficient condition is certified; the complement is not completely classified |
| UNKNOWN | No certified condition is published; inspect diagnostics and evidence |
| EMPTY_DOMAIN | No admissible input exists; no program-equivalence claim is published |

For EXACT, `claim.meaning` distinguishes `ALL_INPUTS` (literal condition true),
`NO_INPUTS` (literal condition false), and `REGION` (another condition expression).
This is a conservative syntactic distinction; equivalent-looking formulas are
not further simplified by reporting. **NO_INPUTS has a nonempty input domain**:
every admissible input gives unequal observations. It differs from EMPTY_DOMAIN.
PARTIAL uses `SUFFICIENT_REGION`; other outcomes use `NO_EQUIVALENCE_CLAIM`.

Results concern the stated domain, return/state observations, semantics and
verification bounds only. UNKNOWN does not mean unequal. Native input witnesses
may establish that a domain is nonempty; they never prove universal equivalence.

## JSON interface

The root identifies `schema: "conditional-equivalence-result"` and
`schema_version: 1`. Consumers should check both and use these fields:

| Field | Contents |
|---|---|
| producer | finder or agent |
| status / legacy_status | New outcome and original compatibility status |
| scope | Domain, observations, bounds and assumptions supplied by the adapter; null when admission failed |
| claim | Certified condition in readable/C form, meaning and scope restriction; null conditions when uncertified |
| domain | NONEMPTY, EMPTY or NOT_ESTABLISHED, with basis and witness/proof evidence |
| obligations.state | Safety or initialization/preservation results, as applicable |
| obligations.sufficiency / complement | Status, basis, log, property and underlying evidence |
| diagnostics | Stable code, explanatory message, evidence location and optional log |
| latest_candidate | Latest agent feedback, separately from its best retained certificate; null for finder |
| metrics | Query count, native sample count and elapsed/agent-active seconds when available |
| artifacts | Run/session directory and relative filenames for legacy JSON, summary and report |

Check statuses include `PROVED`, `REFUTED`, `UNKNOWN`, `NOT_CHECKED` and
`INVALIDATED`. A REFUTED feasibility assertion is a witness that a region exists:
the harness was trying to prove `false` unreachable. The domain field translates
that convention into NONEMPTY/EMPTY for readers. State obligations and both
relational obligations retain their original meaning.

Diagnostics explain recorded attempts; an earlier budget/timeout diagnostic
need not invalidate a later successful final certificate. Use the top-level
outcome and its published obligations for the current claim, not the presence
of a warning string alone.

## Important failure distinctions

| Code | Interpretation |
|---|---|
| SOLVER_NOT_FOUND | Configured ESBMC executable could not be found |
| SOLVER_STARTUP_TIMEOUT / SOLVER_STARTUP_FAILED | Version/startup check failed |
| QUERY_BUDGET_EXHAUSTED | No query allowance remains, including reserved final-check allowance |
| TIME_BUDGET_EXHAUSTED | Overall backend time allowance was consumed |
| SOLVER_TIMEOUT | A launched verification process exceeded its time limit |
| UNWINDING_INCOMPLETE | Solver violation reports an unwinding assertion |
| SAFETY_OR_OTHER_PROPERTY_FAILURE | A non-target property failed; this is not a relational counterexample |
| UNRECOGNIZED_SOLVER_OUTPUT / SOLVER_FAILED | No acceptable verdict, or solver execution failed |
| UNSUPPORTED_INPUT / INPUT_REJECTED | Unsupported C subset or invalid contract/proposal data |
| EMPTY_DOMAIN | Contradictory inclusive bounds or a domain-feasibility proof |
| COMPILER_NOT_FOUND / COMPILE_TIMEOUT / COMPILE_FAILED | Native probe could not be compiled |
| WITNESS_REPLAY_FAILED / WITNESS_MISMATCH | Solver/native evidence could not be reconciled |
| CERTIFICATE_CONTRADICTION / IDENTITY_CHANGED | Prior evidence must not be used as a current certificate |
| COMPLETENESS_NOT_ESTABLISHED | A sufficient region exists, but exactness has not been established |
| VOCABULARY_EXHAUSTED | A mixed region could not be separated by the admitted predicates |

Adapters/older records may additionally use `BUDGET_EXHAUSTED`,
`SOLVER_UNAVAILABLE`, `NOT_ESTABLISHED` or an input/I/O reason. Consumers should
display unknown reason codes rather than treating them as success. Raw property
details/logs remain authoritative for diagnosis; code classification does not
change a backend verdict.

Contradictory scalar bounds now yield a structured EMPTY_DOMAIN report, zero
queries and no native execution. They remain rejected as runnable contracts;
source admission is not completed in that case. Unsupported/missing input files
also produce report artifacts once CLI arguments are accepted and the output
directory is writable. Command-line usage errors still use argparse diagnostics.

## Partial certificates and agent sessions

If a final check of a compact condition is UNKNOWN but search already proved
nonempty EQ regions, the finder retains their Boolean union, with
`basis: "PROVED_REGION_UNION"`. It does **not** publish an unvalidated compact
substitute as certified. A complement check for a different presentation is
marked NOT_CHECKED for the reverted union. Contradictory final/native evidence
removes the claim and marks prior displayed checks INVALIDATED.

Legacy `final_validation` preserves the actual final query results. Additive
`published_sufficiency` and `published_complement` identify the evidence for the
condition actually published; the v1 summary uses those fields. Consumers
analyzing partial results should use the v1 contract rather than infer a proof
solely from the legacy status string.

Agent reports keep the best certificate separate from the most recent proposal.
A rejected proposal does not erase an earlier valid sufficient region. Source/
contract/tool drift invalidates the claim and displayed checks. Start a fresh
session after updating this implementation; the existing identity checks block
continuation of sessions created with older engine code. A protocol error before
a step starts may leave the existing session report unchanged; its CLI error is
not a new proof result.

## Codespace acceptance

```bash
cd /workspaces/faas-python-c-verification
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
bash cases/result_contract/test_results.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Target: `M2 RESULT ACCEPTANCE: 10/10 passed`, followed by a separate
`m2-results-*.tar.gz` archive. The stage checks all-input equality, conditional
exactness, no equal inputs, a sufficient-only agent candidate, empty domain,
unsupported C, missing solver, query budget, unsafe division and incomplete
unwinding. The candidate is scripted, not an autonomous-agent performance test.
Local tests additionally exercise an actual child-process timeout, mocked solver
outcomes, partial-proof fallback, stale certificates and schema invariants.

Local validation: 120 tests passed in the full regression (20 oracle + 100
finder/protocol/native), including 13 new result tests; final targeted tests and
an intentionally missing-solver stage were also run. That negative stage reports
3/10, as required: only missing-solver, empty-domain and unsupported-input controls
pass. The user subsequently reported **M2 RESULT ACCEPTANCE: 10/10 passed**
from Codespace; [transcript and archive paths](validation/m2-results/user-reported-results.md).
The raw archive has not been independently inspected here.
[Local logs and provenance](validation/m2-results/README.md).

## Frozen transfer baseline

The old transfer experiment's hash lock is unchanged. It intentionally rejects
the M2 engine, which adds reporting and more precise partial-proof handling. Its
recorded 8/8 required and 8/12 EXACT belong to the old code, not this version.
Use an isolated checkout to rerun it:

```bash
git worktree add --detach ../faas-transfer-baseline 52df7d1
cd ../faas-transfer-baseline
bash cases/c_scalar_transfer/test_transfer.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Choose an unused worktree path if that directory already exists. No lock refresh
or unlabelled cross-version performance comparison is part of M2. Future
comparisons should name both engine versions and retain the original baseline.
