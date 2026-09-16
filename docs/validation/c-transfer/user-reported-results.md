# C transfer acceptance — user-reported result

Recorded on 2026-09-16 from the user's Codespace excerpt, following the commands
for experiment `52df7d1` (engine `5502520`, frozen baseline `61ba47b`). The supplied
text does not show the executed checkout or actual compiler/ESBMC hashes. Those
remain to be checked in the original archive; it has not been opened locally.

## Supplied output

Markdown-escaped underscores in the pasted text are normalized below.

```text
r2-reordered_31-ordered: EXACT queries=32 time=5.920s required=PASS
C TRANSFER ACCEPTANCE: 8/8 required runs passed
Discovery EXACT: 8/12; all reports valid=True; engine unchanged=True; inputs/tools unchanged=True
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/c-transfer-stage/run-ps0Nvj/comparison-x7nfpkai
Evidence directory: /home/codespace/equiv-evidence/c-transfer-20260916T071901Z-BYJDhi
Downloadable archive: /home/codespace/equiv-evidence/c-transfer-20260916T071901Z-BYJDhi.tar.gz
```

## What the summary supports

- All eight required runs are reported passed; eight of twelve discovery runs
  reported EXACT. The runner also reports successful assessment/replay checks
  and unchanged engine, inputs and binaries.
- By the published schedule, the required runs consist of the equivalent and
  fully unequal controls, and both reordered domains with the ordered vocabulary,
  each repeated twice. Since required success demands EXACT and total EXACT is
  eight, **the four exploratory default-vocabulary reordered runs were non-EXACT**.
  This is an inference from the schedule and aggregate totals. Their individual
  PARTIAL/UNKNOWN statuses and failure reasons are not in the excerpt.
- One run is individually shown: repetition two, reordered domain 0..31, ordered
  vocabulary, EXACT, 32 discovery queries, 5.920 seconds. This is one reported
  discovery measurement, excluding the runner's separate assessment phase;
  it is not a mean, paired speedup or total experimental duration.
- These results support configuration-only reuse of the existing engine on this
  new three-input family and the value of an appropriate predicate vocabulary in
  this experiment. They do not establish why each baseline stopped (vocabulary,
  query/time budget or another recorded reason) without the detailed metrics.

The expected equivalence region checked by the acceptance code is
`low <= high || x <= high || x >= low`, relative to the declared rectangular input
domain and return observation. The actual published condition strings are not
shown in this excerpt; do not substitute the expected formula for a retrieved
finder output. Invalid bounds are deliberately allowed in these contracts.

This remains an authored integration experiment, not a blind real-world test or
an autonomous-agent evaluation. No local formal rerun, raw proof-log inspection,
archive download or checksum verification was performed when recording it.

## Follow-up

Preserve the archive. Read `metrics.csv` and `results.json` in the reported
artifact directory to recover all four baseline statuses/reasons, both ordered
repetitions, actual conditions and separate discovery/assessment costs before
calculating comparisons. Next development priority is M2: a versioned result
schema, clear EXACT/PARTIAL/UNKNOWN explanations and explicit safety, feasibility,
sufficiency and complement evidence. Preserve this frozen experiment baseline
when later engine changes are introduced.
