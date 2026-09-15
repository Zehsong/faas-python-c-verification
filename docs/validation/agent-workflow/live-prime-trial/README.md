# First external-chat proposal trial

Recorded 2026-09-16. This trial exercises the live file handoff on the familiar
prime/truncated-lookup example. It is not a held-out discovery or speed benchmark.

## Provenance

- Workflow implementation: `62ea51e`; the initial pasted terminal output shows
  the Codespace checkout advancing to documentation commit `2de886b`.
- [Initial context](initial-context.user-reported.json) and
  [result](result.user-reported.json) were extracted from user-pasted terminal
  output. JSON formatting was normalized; field values were preserved.
- [Assistant proposal](proposal.assistant.json) records the JSON suggested in
  the preceding chat response. The submitted terminal echo is visibly truncated;
  the original on-disk submitted proposal and full solver logs were not retrieved.
  The result's checked condition matches the assistant's proposed expression.
- No local formal verification was run. Consistency checks confirmed matching
  session IDs/scopes, round and query counts, proof statuses and exit codes.

## Trial sequence

1. The user started a prime/truncated session for `0..127`, with exactness as the
   goal, and supplied its context: 13 native samples, READY, one initialization
   feasibility query, no certified condition yet.
2. The assistant proposed `x <= 31` OR divisibility by one of `2,3,5,7,11`, with
   additional inputs `35,49,121,37`. The rationale was the table boundary and
   the small-prime factors of composite numbers up to 127. This formula was
   already known from prior conversation and scripted controls.
3. The user submitted the JSON through `step` and supplied the resulting report.
   The candidate was certified in the first round; no refinement was necessary.

## Reported outcome

```text
EXACT: ((x <= 31) || (x % 2 == 0) || (x % 3 == 0) || (x % 5 == 0) || (x % 7 == 0) || (x % 11 == 0))
goal_reached: true
rounds: 1
queries_used: 4
active_seconds: 1.1177481559998341
```

| Obligation | Reported status | Meaning |
|---|---|---|
| Initial domain feasibility | REFUTED | The false assertion has a witness; the declared domain is nonempty |
| Candidate feasibility | REFUTED | Candidate nonempty; reported witness x=12 replayed with both returns 0 |
| Sufficiency | PROVED, exit 0, no timeout | Every input satisfying the condition has equal Boolean returns |
| Complement | PROVED, exit 0, no timeout | Every input outside it, within the declared domain, has unequal Boolean returns |

The total is one start query plus three candidate queries. Printed per-round
query numbering restarts at 000; it is not the session-total counter.

Scope: C, uint32 input in `0..127`, Boolean return observations, fixed read-only
tables, no external/mutable state, one call, unwind 13 with safety/unwinding
checks enabled. The claim does not extend to all uint32 inputs or whole-program
effects. The context's legacy `state_mode: invariant` configuration field does
not add cache state to this stateless adapter; the scope says `initial_state: none`.

The reported ESBMC binary is `/workspaces/esbmc-current/build/src/esbmc/esbmc`,
with SHA256 `909682a1a99cd4a01d7c099ee5629dc65cb11993965eaf1ecda33e924c0fe3ee`.
Its identity and command details are in the supplied JSON, not independently
remeasured on the Windows host.

Full original artifacts remain at:
`/workspaces/faas-python-c-verification/.verify-equiv-runs/agent-live/run-l0selh/session-xsryjyoh`

This session has no separately reported downloadable archive yet. It is distinct
from the earlier scripted-acceptance archive.

## Interpretation and next step

The result demonstrates that an external chat's structured candidate can pass
through the fixed-contract checker and obtain backend certification. It does not
demonstrate autonomous invocation, multi-round recovery from a bad proposal,
generalization to unseen programs or automatic harness generation.

Active time is runner processing time; it excludes model reasoning, chat transfer
and user waiting, and is not an end-to-end latency measurement. Do not compare
these four queries directly with baseline/modulo search runs as an agent speedup:
this trial supplied an already-known complete candidate.

Stop this successful session. The next development priority remains a generic C
scalar binding/configuration layer with controlled harness generation, followed
by independently selected cases and explicit recording of manual/model effort.
