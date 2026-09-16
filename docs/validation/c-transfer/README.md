# Scalar transfer local validation — 2026-09-16

[Local test transcript](local-tests.txt): nine tests passed, no skips, using
Windows/MSVC and the bundled Python/pycparser installation. This turn did not
rerun the historical 107-test baseline: engine code is unchanged and checked
against `engine-lock.json`. No ESBMC is available locally.

The tests cover contract admission, frozen-file drift/addition detection,
platform newline normalization, field-only vocabulary generation, balanced
scheduling, strict certificate assessment, retained UNKNOWN reasons, native
fixture results and missing-solver result/CSV persistence.

Native execution compares all 512 triples of the smaller domain for each of
three candidates (1,536 observations) with independent arithmetic calculations.
The test explicitly bypasses the safety gate only for these inspected loop-free
fixtures; production discovery still requires its whole-domain safety proof.
A separate arithmetic assertion checks the expected relational predicate on
32,768 triples. These are fixture tests, not solver certificates.

The local missing-solver experiment uses one repeat. Its captured output reports
`C TRANSFER ACCEPTANCE: 0/4 required runs passed`, `Discovery EXACT: 0/6`, and
`all reports valid=False`. Every run remains UNKNOWN with zero traces. The unit
test passes because it verifies this failure is preserved, not because the
formal gate was satisfied. The test captures this negative-control output to
avoid confusing it with the real stage's summary in Codespace. No discovery
speedup or real-solver success is claimed.

These local tests preceded the user-reported Codespace result: **8/8 required
runs passed, 8/12 discovery EXACT**. See the separate
[result record and evidence paths](user-reported-results.md). No raw archive
inspection or local formal rerun accompanies that record. The local missing-
solver result above remains unchanged. See the
[experiment design and Codespace command](../../../cases/c_scalar_transfer/README.md).
