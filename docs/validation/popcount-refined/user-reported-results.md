# User-reported refined bridge milestone — 2026-09-16

Reported after implementation `388a2c3`, using the existing modified ESBMC
workflow. The pasted summary and CSV are the evidence inspected here; the raw
archive, individual certificates, harnesses and run-specific identities have
not been independently opened or formally rerun locally.

```text
POPCOUNT REFINED BRIDGE: RECORDED (links certified=6/6; endpoint equivalence=PROVED; mutant rejected=True)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-refined-stage/run-uJhdH2/refined-uhirr7h3/README.md
Evidence directory: /home/codespace/equiv-evidence/popcount-refined-20260916T134105Z-uEp15b
Downloadable archive: /home/codespace/equiv-evidence/popcount-refined-20260916T134105Z-uEp15b.tar.gz
```

The supplied [seven CSV rows](user-reported-metrics.csv) retain all outcomes.
Each of the six positive edges is EXACT, full_domain_certified=True, with five
discovery queries and a PROVED full-domain post-check. The mutant is EXACT with
full_domain_certified=False and a REFUTED post-check; it is a separate negative
control on 0..255, not a failed positive edge.

## Claim and measurement

Under the [declared protocol](../../../cases/c_popcount_bridge/REFINED.md), the
six edges connect the unchanged original bit loop and parallel popcount on the
entire uint32 domain, 0..4294967295, observing the scalar return. The composed
condition is true. All edges use the same scope with unwind 34 and require
safety/unwinding checks, matching intermediate sources and identity gates.
The endpoint conclusion is derived by transitivity, not a successful direct
endpoint query or a proof extrapolated from sampled or eight-bit inputs.

The six discovery times sum to **7.302194 seconds**, with **30 discovery queries**.
Including the mutant gives **8.629407 seconds** and **36 discovery queries**.
These sums exclude the separate full-domain post-checks, setup, local controls
and archiving. They are not end-to-end runtime or total solver-call counts.
This is one refined-chain execution, not a repeated performance evaluation.

## What this establishes

The [direct budget experiment](../popcount-budget/user-reported-results.md)
remains UNKNOWN at both 30/120-second query limits. The
[original three-edge chain](../popcount-bridge/user-reported-results.md) remains
2/3 certified with its simultaneous four-byte replacement unresolved. The
six-edge chain replaces one byte at a time and now reports a complete proof.
Those earlier timeouts are retained as historical results; they do not refute
the newly certified endpoint equivalence.

This supports manually guided intermediate-program refinement as a useful
proof strategy for this pair, with the engine and endpoint programs unchanged.
It does not establish a numerical speedup against censored direct runs,
automatic bridge synthesis, general conditional-region composition or an
autonomous-agent performance result. Manual proposal effort and failed prior
attempts are not included in the recorded discovery times.

The immediate research follow-on is a reusable, checked chain-proposal interface
with explicit budgets and feedback. Any later agent may propose intermediates;
the backend must still certify every link. Held-out cases, repeated total-cost
measurements, raw evidence audit and clean-host reproduction remain open gates.
