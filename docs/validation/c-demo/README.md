# Scalar demo local validation — 2026-09-16

- [Six assembly tests](local-tests.txt) passed without skips. These check portable
  copied contracts, original source preservation, safety gating of displayed
  witnesses, missing/mismatched replay rejection, failure presentation and exact
  preservation of the actual condition/relative evidence links. Synthetic query
  records in these unit tests are not solver proofs.
- [Executed negative run](local-negative.json): real MSVC compilation with an
  intentionally absent ESBMC produced four UNKNOWN reports, zero native samples,
  no counterexample and `C SCALAR DEMO: INCOMPLETE (0/5 checks; tools unchanged=True)`.
  Expected UNKNOWN from query exhaustion was not satisfied by missing-tool
  UNKNOWN. An initial run with unresolved compiler name `cl` likewise stayed
  incomplete; the negative solver run used the compiler's absolute path.
- Generated overview links were checked against the actual run files. The
  shared archive script created a local archive, validated its checksums, and
  each archived member's checksum and overview link were independently checked
  from the tar contents. Local archives remain ignored, outside the Git evidence
  record. The full shell wrapper has not been executed in Linux here.
- Python/Bash syntax and documentation links were checked. No finder, backend,
  schema, existing fixture or transfer-lock file changed. The old 120-test M2
  regression was not relabelled as a new demo regression.

There is no local ESBMC installation. The dedicated demo READY run remains
pending on the user's modified ESBMC in Codespace. Earlier user-reported M2
10/10 and scalar 8/8 results are separate evidence, not this run. A successful
demo still does not establish held-out discovery or autonomous-agent performance.

See [quickstart and commands](../../../cases/c_scalar_demo/README.md).
