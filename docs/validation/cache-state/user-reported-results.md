# Cache state acceptance reported — 2026-09-16

The user supplied this Codespace output after implementation `33af517`:

```text
Report: /workspaces/faas-python-c-verification/.verify-equiv-runs/cache-state-stage/run-GQRSpE/checks-15xaj2q0/agent-config-cache/session-6tg2o05q/report.md
agent-config-cache: PASS
CACHE STATE ACCEPTANCE: 14/14 passed; inputs/tools unchanged=True
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/cache-state-stage/run-GQRSpE/checks-15xaj2q0
Evidence directory: /home/codespace/equiv-evidence/cache-state-20260916T095907Z-LKh4Gz
Downloadable archive: /home/codespace/equiv-evidence/cache-state-20260916T095907Z-LKh4Gz.tar.gz
```

This is user-reported acceptance, including invalid-state/missing-solver controls
and scripted resumed-agent checks; it does not mean all 14 checks are equivalence
proofs. The raw archive, individual conditions and actual checkout/binary identities
have not been independently inspected. The intended solver is the user's modified
ESBMC. The unchanged flag is the acceptance runner's result, not a separate audit.

Together with the separate [array 10/10 report](../c-bounded-arrays/user-reported-results.md),
this meets the implemented M3 baseline gate at the user-reported evidence level:
array observations and both private-cache families use the common report interface,
with state isolation and required obligations. It does not establish arbitrary
stateful C, automatic invariant synthesis or unrestricted sequence equivalence.
Clean-environment reproduction and independently held-out examples remain M4 gates.
