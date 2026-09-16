# User-reported input-domain acceptance — 2026-09-16

Reported after implementation `5446b31`:

```text
agent-domain: PASS
C INPUT DOMAIN ACCEPTANCE: 13/13 passed; inputs/tools unchanged=True
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-domain-stage/run-2gZmI5/checks-fegf3y_e/README.md
Evidence directory: /home/codespace/equiv-evidence/c-input-domains-20260916T144518Z-CRnvnQ
Downloadable archive: /home/codespace/equiv-evidence/c-input-domains-20260916T144518Z-CRnvnQ.tar.gz
```

This clears the first schema 3 domain acceptance gate at user-reported evidence
level. The stage includes complete type-default ranges, relational constraints,
array/bool combinations, relation-dependent safety and unconstrained unsafe
controls, empty domains, no initial boundary witness, missing solver and a
scripted agent seed/condition check. Expected formulas are separate post-checks.

The supplied summary is not a local formal rerun or an independently inspected
raw archive. Individual conditions, harnesses, timings and run-specific binary
identities have not been inspected here. This does not establish autonomous
agent performance, arbitrary input types, dynamic memory or unbounded loops.
Subsequent capacity/length work has its own acceptance stage; these thirteen
passes must not be relabeled as certification of that later implementation.
