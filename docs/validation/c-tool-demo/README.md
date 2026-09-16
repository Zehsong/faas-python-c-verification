# Unified C tool demo validation — 2026-09-16

- [Eight local assembly tests passed](local-unit-tests.txt), without skips.
  Tests exercise same-return/different-array witness selection, complete typed
  observations, domain/witness consistency, safety admission, portable C snapshots,
  cache snapshot binding, budget-specific UNKNOWN, generated relative links,
  incomplete assembly and tool drift. Synthetic proof records test presentation
  and control flow only and do not establish formal equivalence.
- [Actual MSVC/missing-ESBMC run](local-negative.txt): INCOMPLETE (0/8), as expected.
  All seven case summaries are UNKNOWN, with no certified condition and zero
  native samples. Missing solver does not count as the intended budget failure;
  no replayed counterexample is invented. Engine/input/tool identities are stable.
- Engine, existing fixtures and historical transfer lock are unchanged. The
  earlier 157-test engine regression was not rerun for this assembly-only change.
- Syntax, links, negative-report contents and a [local archive/checksum round trip](archive-check.txt)
  are checked: 183 internal file hashes and 48 overview links after relocation.
  The archive retains relative overview links after relocation;
  underlying raw log paths continue to identify the original machine.

The user subsequently reported **C TOOL DEMO READY (8/8; engine unchanged=True)**.
[Transcript and archive paths](user-reported-results.md). The actual raw reports,
witness and tool identities remain independently uninspected.
[Commands and scope](../../../cases/c_tool_demo/README.md).
This is a presentation/reproduction slice of M4. A clean Linux environment run,
independent held-out case and raw historical archive audit are not established.
