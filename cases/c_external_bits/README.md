# External-source C integration with a frozen engine

These are new integration cases selected after baseline `7cc44b5`. No finder,
frontend, proof or search code is changed. `engine-lock.json` pins the existing
17 implementation/dependency files by LF-normalized SHA-256, checks the file set,
and is separate from the older scalar-transfer lock. The two families use only
ordinary C source files and schema-1 contracts. No custom backend, supplied
condition, seed file or predicate list is passed to discovery.

## Source and adaptations

Sean Eron Anderson's [Bit Twiddling Hacks](https://graphics.stanford.edu/~seander/bithacks.html),
accessed 2026-09-16, supplies the three candidate snippets:

- [Power of two](https://graphics.stanford.edu/~seander/bithacks.html#DetermineIfPowerOf2):
  raw bit test and its zero-guarded variant. The zero discrepancy is already
  documented at the source; it is deliberately preserved, not a newly found bug.
- [Parallel population count](https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetParallel):
  the 32-bit subtract/mask/add/multiply recipe, not the table variant.

The page places individual snippets in the public domain unless otherwise
noted. No exception is shown for these snippets. Its explanatory collection is
copyrighted; this repository includes the small adapted snippets with attribution,
not a copy of that collection. Candidate comments link directly to their source.

Adaptations: wrap expressions in a function, rename `v` to `x`, fix the input
width to `uint32_t`, add unsigned literal suffixes, and return the result instead
of assigning `f`/`c`. The population-count parentheses spell out the original C
precedence; hexadecimal constants retain their values. Both loop references are
project-authored, not external programs. Integer arithmetic is unsigned modulo
2^32; the population-count multiplication deliberately wraps on some inputs.

This selection is an **external-source post-freeze integration**, not a blind
held-out benchmark, independent author study or autonomous-agent evaluation.
Expected answers were known to the author. They are checked only after discovery
with a separate solver query. Native checks cover all 0..255 values plus 32-bit
boundaries; those checks are not formal proofs of the full domain.

## Fixed experiment schedule

| Case | Domain x | Expected region, checked afterwards | Role |
|---|---|---|---|
| power_guarded_32 | 0..4294967295 | true | Required |
| power_raw_32 | 0..4294967295 | x != 0 | Required |
| power_positive_32 | 1..4294967295 | true | Required |
| power_zero | 0..0 | false (nonempty domain) | Required |
| popcount_8 | 0..255 | true | Required |
| popcount_32 | 0..4294967295 | true | Exploratory |

Each run observes only the return value, uses unwind 34, query timeout 30 seconds,
96 discovery queries and 300 discovery seconds. Domain-wide safety/unwinding
checks remain mandatory before native discovery. The input types stay 32-bit even
in the byte-domain run. Required/exploratory roles are fixed before formal runs;
full-width population count is exploratory because solver cost is not measured
here yet. UNKNOWN/PARTIAL/errors remain in the archive, with diagnostics; no
automatic retuning, narrower-domain retry or replacement of the frozen engine.

READY requires all five required EXACT results, their separate expected-region
proofs, completion of all six runs and unchanged engine/input/tool identities.
Exploratory failure is displayed and does not turn into a proof or disappear
from the denominator. Discovery metrics exclude the post-check query, whose
result and logs are saved separately. The overview uses actual result formulas.

## Run and retain

```bash
bash cases/c_external_bits/test_external.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The wrapper runs five local/native experiment controls, then all six formal
cases. It writes a separate `c-external-bits` evidence archive, including failures.
The stage snapshots contracts, C programs, runner, source notes, baseline lock,
measured engine files, actual compiler/solver identities, commands and reports.
Default evidence output is `$HOME/equiv-evidence`. Keep both the archive and its
checksum sidecar. This stage does not rerun the known unified demonstration.

The user reports READY 5/5 required with a frozen engine. Full-width exploratory
popcount remains UNKNOWN/SOLVER_TIMEOUT; the raw archive is uninspected locally.
A separate [scaling protocol](SCALING.md) retains this original experiment and
measures five input domains with fixed budgets. See
[local validation](https://github.com/Zehsong/faas-python-c-verification/blob/codex/same-language-cache/docs/validation/c-external-bits/README.md)
and [project status](https://github.com/Zehsong/faas-python-c-verification/blob/codex/same-language-cache/docs/PROJECT_STATUS.md).
