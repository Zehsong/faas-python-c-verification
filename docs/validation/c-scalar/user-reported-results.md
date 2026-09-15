# C scalar acceptance — user-reported result

Recorded on 2026-09-16 from the user's pasted Codespace output, following the
instructions for implementation `550252054dd799a9f43eb11dda507f8e6be8bca6` on
`codex/same-language-cache`. The excerpt does not include the executed checkout
hash or ESBMC binary identity; their run-specific values await archive inspection.

## Supplied output (verbatim)

```text
missing-solver: PASS
C SCALAR ACCEPTANCE: 8/8 passed
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-scalar-stage/run-rGbyVJ/checks-go4l67y9
Evidence directory: /home/codespace/equiv-evidence/c-scalar-20260915T172153Z-CWTpqt
Downloadable archive: /home/codespace/equiv-evidence/c-scalar-20260915T172153Z-CWTpqt.tar.gz
```

The archive name's timestamp is preserved exactly as supplied; it is not the
local date on which this result was recorded.

## Interpretation and provenance

The summary reports that all eight scalar acceptance checks passed. In the
published runner, these comprise four exact-region/expected-condition checks
(max/min, parity, series and its mutant), two safety/unwind failures that must
remain UNKNOWN without native execution, a scripted scalar agent proposal, and
a missing-solver UNKNOWN control. The excerpt itself prints only the last
individual check and the aggregate result; per-case results and raw solver logs
have not been independently inspected here.

This satisfies the first scalar integration acceptance gate at the level of a
user-reported result. It supports configuration-only reuse on the supplied
fixtures; it does not establish arbitrary-C support, unseen-case discovery,
autonomous-agent performance, or the remaining M2/M3 release requirements.
The intended environment uses the user's modified ESBMC, but this excerpt alone
does not independently confirm its binary version/hash. No local formal rerun,
archive download or checksum verification was performed for this record.

Next: preserve the archive, then exercise a new supported scalar pair through
C/JSON configuration alone, keeping the engine fixed and recording preparation
work, resulting scope/condition, solver queries and failures. Continue M2's
stable result interface and failure diagnostics after that integration check.
