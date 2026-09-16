# Isolated reproduction local checks — 2026-09-16

- [Eight local lifecycle tests passed](local-tests.txt), without skips. They cover
  inherited Python/Git/pip routing, subprocess exit/timeout logs, venv/module
  location checks, complete demo readiness, setup/demo/checkout failures,
  missing tools, tool drift, offline arguments and archive failure. Simulated READY records are test fixtures,
  not ESBMC evidence.
- One test actually creates and commits a temporary Git repository, adds dirty
  tracked and untracked files, then clones and checks out the commit. Only the
  committed content appears in the new copy; the original dirty file is preserved.
- [Actual invocation](local-platform-negative.txt) on this Windows host correctly returns INCOMPLETE with
  LINUX_REQUIRED before installation or formal execution, and packages the
  failure report ([JSON](local-platform-result.json)). Exit 2 and zero setup/proof
  steps are verified, together with [archive checksums](archive-check.txt).
- No Linux venv install, ESBMC build, formal demo rerun or clean-host execution
  was completed locally. The core proof/search engine and fixtures are unchanged;
  the earlier core regression is historical and was not rerun for this wrapper.

Full **ISOLATED C REPRODUCTION: READY** remains pending on Linux using the existing
modified ESBMC. Even success reuses the host compiler/ESBMC/system libraries; it
must not be described as clean-machine or container reproduction.
[Commands and evidence layout](../../C_TOOL_REPRODUCTION.md).
