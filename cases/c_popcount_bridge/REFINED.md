# Refine the unresolved byte-implementation edge

The user-reported original bridge result is RECORDED, links certified 2/3,
endpoint UNKNOWN, mutant rejected=True. The supplied overview identifies:

| Original edge | Meaning | Result | Discovery seconds |
|---|---|---|---|
| edge_0 | original loop -> byte loops | EXACT, full-domain certified | 1.120228 |
| edge_1 | byte loops -> byte parallel counts | UNKNOWN, SOLVER_TIMEOUT | 30.912715 |
| edge_2 | byte parallel counts -> original parallel algorithm | EXACT, full-domain certified | 1.768853 |

The unresolved middle edge changes all four byte implementations together. This
separate experiment proposes changing one byte at a time, starting at the low
byte. The original endpoints, old bridges and old results are preserved.

```text
original loop
  -> loop / loop / loop / loop
  -> parallel / loop / loop / loop
  -> parallel / parallel / loop / loop
  -> parallel / parallel / parallel / loop
  -> parallel / parallel / parallel / parallel
  -> original parallel algorithm
```

This is a proposed structure, not an assumed byte-composition lemma. Every one
of the six edges is proved on the **entire uint32 input domain**, with full
scalar return observation. The helper bodies remain inlined by ESBMC. No
eight-bit proof is lifted without checking the actual enclosing program; the
unchanged byte contributions are not removed from the harness by this wrapper.
Input types, arithmetic, domain, unwind 34 and source admission remain unchanged.

All six edges are rerun, including the two previously reported successful end
connections. The wrapper does not import old claims or reuse uninspected remote
certificates. Each run gets 30 seconds per query, 120 discovery seconds and 96
queries. The same deliberately wrong control is checked separately on 0..255.

The common composition gate now counts the declared edges, so all six certificates,
common source/contract scope, exact intermediate-byte identities, frozen engine,
pinned original endpoints, unchanged tools and rejected mutant are required to
publish `endpoint equivalence=PROVED`. One unresolved edge keeps UNKNOWN, even
if five succeed. A bad bridge cannot refute the original endpoints. The default
three-edge entrypoint retains its original nodes, domains and budgets.

```bash
bash cases/c_popcount_bridge/run_refined.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The script runs local controls and seven formal runs (six edges plus mutant),
then creates a separate `popcount-refined` evidence archive. The runner now
writes and prints per-edge metrics.csv, including discovery diagnostics and
the separate full-domain post-check status/reason. RECORDED denotes completed
measurements and controls; endpoint equivalence is reported independently.
Seven discovery wall budgets total 14 minutes plus setup/post-check overhead,
not a predicted runtime.

This is a manually proposed refinement following an observed failure. It is
not autonomous lemma synthesis, a completed full-width proof, a general
conditional-composition engine or evidence of a speedup until executed. Raw
historical solver logs/identities remain uninspected; the supplied summaries
are kept in the repository's
[evidence record](https://github.com/Zehsong/faas-python-c-verification/blob/codex/same-language-cache/docs/validation/popcount-bridge/user-reported-results.md).
