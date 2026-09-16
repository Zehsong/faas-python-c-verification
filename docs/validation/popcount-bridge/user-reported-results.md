# User-reported three-edge bridge — 2026-09-16

Reported after implementation `0cf3fbe`:

```text
EXACT: false
Outcome: EXACT; domain=NONEMPTY; claim=NO_INPUTS
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-bridge-stage/run-VGjR1x/bridge-dyjtj3oy/mutant/pair-855xklyk/report.md
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-bridge-stage/run-VGjR1x/bridge-dyjtj3oy/mutant/pair-855xklyk
 query 000 expected: REFUTED
mutant: EXACT; full-domain certified=False
POPCOUNT BRIDGE: RECORDED (links certified=2/3; endpoint equivalence=UNKNOWN; mutant rejected=True)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-bridge-stage/run-VGjR1x/bridge-dyjtj3oy/README.md
Evidence directory: /home/codespace/equiv-evidence/popcount-bridge-20260916T132555Z-1lUBtg
Downloadable archive: /home/codespace/equiv-evidence/popcount-bridge-20260916T132555Z-1lUBtg.tar.gz
```

The user subsequently supplied the overview table:

| Connection | Discovery | Full-domain certificate | Queries | Seconds | Diagnostic |
|---|---|---|---|---|---|
| edge_0 | EXACT | True | 5 | 1.120228 | |
| edge_1 | UNKNOWN | False | 5 | 30.912715 | SOLVER_TIMEOUT |
| edge_2 | EXACT | True | 5 | 1.768853 | |
| mutant | EXACT | False | 6 | 1.33478 | |

These rows use the **original three-edge numbering**. edge_0 connects the
original loop to byte loops; edge_1 connects byte loops to byte-parallel counts;
edge_2 connects byte-parallel counts to the original parallel algorithm.
The unresolved link is therefore the simultaneous replacement of all four byte
implementations. Its supplied diagnostic is SOLVER_TIMEOUT; the overview does
not include a query-by-query trace for that edge, so the exact query index/kind
or internal solver phase is not independently identified here.

The mutant correctly produces an exact empty equivalence region on its nonempty
byte domain and a refuted full-domain expectation. It is a negative control,
not a link in the positive chain. Two certified edges do not establish the
original endpoint equality. The endpoint remains UNKNOWN, not inequivalent.

This is user-reported evidence, not an independently opened archive or local
formal rerun. Raw conditions, query harnesses, binary/source identities and
solver logs remain uninspected. No speedup or full-width endpoint proof follows.

The separate [refined chain](../../../cases/c_popcount_bridge/REFINED.md) changes
one byte implementation per middle step. All six edges, including both end
connections, will be rerun on the same full uint32 domain; historical remote
certificates are not imported. No byte-equivalence lemma is assumed. Refined
edge numbers must not be confused with the three-edge labels above.
