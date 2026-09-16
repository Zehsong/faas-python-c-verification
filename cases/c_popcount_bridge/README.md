# Popcount: certified intermediate-program experiment

Both 30- and 120-second direct-query budgets left full-width popcount UNKNOWN.
This experiment proposes two intermediate C programs and checks three adjacent
equivalences, using the existing generic C finder and frozen proof engine.

```text
original 32-iteration loop
  -> four byte-loop counts
  -> four byte-parallel counts
  -> original whole-word parallel algorithm
```

The original endpoint C files are copied byte-for-byte. `endpoint-lock.json`
also pins their LF-normalized text to commit `129df96`. Bridge programs are
project-authored proposals. The byte-parallel version specializes the attributed
public-domain recipe already documented in the external-source case; this is not
a new claim about the source algorithm. No helper precondition/equality or local
lemma is injected as an assumption. Helpers are still inlined by the backend.

## Certification rule

All three edges use exactly the same full input domain x in 0..4294967295,
uint32 arithmetic, scalar return observation, entry binding and unwind 34.
Adjacent bridge bytes must match. Source/contract identities in each result must
match the generated contracts; engine, endpoint, source, contract and tool checks
must pass. Each edge must have a valid EXACT result, whole-domain safety and a
separate proof that its discovered condition equals `true` on the domain.

Only then does transitivity establish equality of the **original endpoints**.
An UNKNOWN or refuted link yields no endpoint claim: a bad bridge does not
demonstrate that the endpoints differ. Partial-region composition is not
implemented. This is currently a fixture-specific, stateless scalar experiment,
not a general decomposition synthesizer or a new core result-schema status.

The experiment emits `endpoint_claim.status=PROVED` only when all three links,
identity checks and the negative control pass. Its report schema is
`popcount-bridge-experiment-v1`, separate from each edge's normal v1 result.
The claim records its domain, observations, unwind and transitivity basis.

A deliberately incorrect control adds one to the original count on 0..255.
It must produce EXACT with no equal inputs and a refutation of the whole-domain
expected condition. It is **not** an edge in the positive chain. Failure to reject
it makes the experiment INCOMPLETE and blocks the endpoint claim.

## Fixed execution

Every edge/control gets 30 seconds per query, 120 discovery seconds and 96
queries. Budgets are not increased after failures. All four runs are attempted
and retained. `POPCOUNT BRIDGE: RECORDED` means the experiment and negative
control were recorded successfully, not that the chain was proved. Read the
separate `endpoint equivalence=PROVED/UNKNOWN` and per-edge statuses.

```bash
bash cases/c_popcount_bridge/run_bridge.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The script runs seven local controls and four formal runs, then creates a separate
`popcount-bridge` evidence archive. Original direct/scaling/budget experiments
are preserved. Core search/proof files retain the existing 17-file engine lock.
All C sources, generated contracts, wrapper sources, hashes, tools and query
reports are archived. Four discovery wall budgets sum to eight minutes, plus
setup and post-check overhead; this is not a timing prediction.

This is a manually proposed proof strategy inspired by the possibility of agent
assistance: proposing a bridge can be untrusted; certifying every connection is
mandatory. No autonomous agent, assumed algebraic lemma, successful full-width
proof or performance improvement is claimed before formal execution.

## Reported outcome and separate refinement

The user now reports RECORDED, links certified 2/3, endpoint UNKNOWN and mutant
rejected=True. The supplied overview identifies edge_0 and edge_2 as certified;
edge_1 (byte loops -> byte parallel counts) is UNKNOWN/SOLVER_TIMEOUT. Raw logs
and identities remain uninspected. A separate [six-edge refinement](REFINED.md)
changes one byte at a time and reruns all connections, keeping this original
protocol intact. The shared runner now also writes/prints per-edge metrics.csv,
including the separate full-domain post-check status and reason.
