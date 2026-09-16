# Array capacity/logical length: local validation — 2026-09-16

- [Full finder regression](local-regression.txt): **158 tests pass without skips**,
  including twelve capacity/length controls and fifteen input-domain controls.
  Native checks use MSVC; mocked solver results are not formal certificates.
- New controls cover schema opt-in, capacity/total-value limits (including 128
  value admission), length-field binding, shared symbolic/native/agent domains,
  whole-array observations, sparse preparation without a Cartesian product,
  empty length domains, native forward/reverse copy at all lengths 0..8,
  clear/conditional/bool buffers and visible inactive-tail mutation at capacity 64.
- [Assembly test](local-assembly.txt): one test passes, confirming every tool
  dependency in the real platform fingerprint is copied into the evidence tree.
- [Actual missing-solver execution](local-negative.txt): exit 2; 1/11 is only the
  expected missing-solver control, not successful acceptance. All eleven reports
  are UNKNOWN with zero queries/native samples and no published condition;
  inputs/tools unchanged=True. There is no local modified-ESBMC formal run.
- [Archive checks](archive-check.txt): 11/11 report links, complete engine copy,
  internal SHA256 manifest and archive sidecar pass. Bash syntax and changed
  documentation links are checked. Historical engine locks remain unchanged.

The [new eleven-check formal stage](../../../cases/c_array_capacity/README.md)
is pending in Codespace. The prior schema 3 domain result is separately
[user-reported 13/13](../c-input-domains/user-reported-results.md) after `5446b31`;
it does not certify this later capacity implementation.
