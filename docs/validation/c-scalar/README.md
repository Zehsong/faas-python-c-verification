# C scalar local validation — 2026-09-16

Windows x64; MSVC 19.50 toolchain under Visual Studio Build Tools 18; bundled
Python and pycparser 3.00. No local ESBMC or Linux proof run was available.

- [Full regression log](local-regression.txt): 20 oracle + 85 finder/protocol/native
  tests passed, no skips. Includes the first 15 scalar tests and all 90 prior tests.
- [Final targeted log](local-targeted.txt): 17 scalar tests passed, no skips, after
  adding boolean input/native checking, stale binding protection and a mocked
  generic agent round. Across both runs, 107 distinct tests passed.
- Native checks compiled and executed the known safe scalar fixtures, comparing
  observations with independent arithmetic expectations. Tests explicitly bypass
  the new safety gate only for these known fixtures; production commands cannot.
- Mock EXACT in the targeted log tests protocol routing only. It is not a proof.
- The new acceptance runner was executed with an intentionally absent solver.
  It reported **1/8**, as required: only missing-solver passed. All six automatic
  cases had UNKNOWN and zero traces. In particular, unsafe-division and short-
  unwind controls did not count a missing tool as a genuine safety counterexample.
- Python syntax, Bash syntax, evidence-result structure and whitespace checked.

New formal acceptance on the user's modified ESBMC is **pending**. Expected 8/8
is a test criterion, not an observed result. Existing user-reported proof results
remain historical evidence. See [commands and supported scope](../../C_SCALAR_TOOL.md).
