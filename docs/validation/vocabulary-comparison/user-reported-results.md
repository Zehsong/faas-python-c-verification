# User-reported Codespace vocabulary results

Recorded in the repository on 2026-09-15 from the user's pasted console summary.
Associated development baseline: `8e85664`. The original `experiment.json` and
archive have not been re-opened in this audit to independently verify their
commit, binary hashes or contents. This transcription is not a new experiment.

```text
VOCABULARY COMPARISON: 24/24 certified; paired inputs match=True
```

Each row is a median over two runs in each arm; both arms certified 2/2.
Time is finder time, not the earlier standalone acceptance's elapsed time.

| Variant | Domain | Baseline queries | Modulo queries | Baseline seconds | Modulo seconds | Baseline raw/published chars | Modulo raw/published chars |
|---|---|---:|---:|---:|---:|---:|---:|
| fallback | 0..63 | 4 | 4 | 0.868 | 0.8745 | 4 / 4 | 4 / 4 |
| truncated | 0..63 | 86 | 30 | 17.6515 | 6.1755 | 706 / 87 | 83 / 83 |
| mutant | 0..63 | 10 | 15 | 2.0655 | 3.2255 | 11 / 8 | 30 / 8 |
| fallback | 0..127 | 4 | 4 | 0.9905 | 0.9915 | 4 / 4 | 4 / 4 |
| truncated | 0..127 | 204 | 35 | 42.713 | 7.4615 | 2947 / 262 | 102 / 102 |
| mutant | 0..127 | 10 | 30 | 2.2455 | 6.557 | 11 / 8 | 78 / 8 |

User-reported artifact directory:
`/workspaces/faas-python-c-verification/.verify-equiv-runs/vocabulary-stage/run-sXIUuw/comparison-gy9lx_qe`

User-reported archive:
`/home/codespace/equiv-evidence/vocabulary-comparison-20260913T111140Z-GJTUH4.tar.gz`

Interpretation: modulo predicates reduced work for truncated lookup and increased
it for the isolated erroneous entry. Two repeats in these bounded examples are
exploratory evidence, not a general performance or statistical-significance claim.
