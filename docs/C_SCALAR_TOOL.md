# Two C files and a contract

The `c-scalar-v1` adapter constructs the native probe and relational harness from
two admitted C files plus one JSON contract. New pairs within this subset do not
need a Python adapter. Both automatic predicate discovery and external-agent
sessions use the same contract and backend. This is the first M1 implementation;
the user has reported **8/8 scalar acceptance** from Codespace.
[Transcript and provenance](validation/c-scalar/user-reported-results.md); raw
logs and run-specific binary identity have not been independently inspected here.

Each run now also writes [versioned verification results and a human report](RESULT_FORMAT.md).
The legacy scalar 8/8 is historical; the new M2 stage has separate acceptance.

For a guided end-to-end walkthrough, use the [C demo quickstart](../cases/c_scalar_demo/README.md).
It assembles a report index, editable input copies and a replayed counterexample
from actual finder artifacts, retaining failures and a separate archive.

The first M3 extension admits [bounded local constant tables](../cases/c_readonly_tables/README.md)
inside otherwise scalar functions. It uses the same contract and CLI; its separate
nine-check acceptance is now [user-reported 9/9](validation/c-readonly-tables/user-reported-results.md).
The raw archive remains independently uninspected; older scalar passes remain
separate historical evidence. Start fresh agent sessions after upgrading.

## Run the acceptance stage

Use the existing modified ESBMC binary; this command does not install or replace
it. Python 3.10+ and a native C11 compiler are required. The frontend additionally
uses [pycparser 3.0](https://pypi.org/project/pycparser/3.0/), pinned in requirements.
The [parser documentation](https://github.com/eliben/pycparser) describes its AST;
our admission/type checks and harness binding are separate project code.

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
bash cases/c_scalar/test_scalar.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Expected completion: `C SCALAR ACCEPTANCE: 8/8 passed`. The script preserves fresh
logs, contracts, original sources, generated code, solver commands/results and
binary identity, then creates a separate `c-scalar-*.tar.gz` evidence archive.
The eight checks are four discovered regions, two genuine solver safety/bound
failures that must remain UNKNOWN without native execution, one scripted agent
proposal, and a missing-solver control. Missing ESBMC must not pass the safety
failure controls. These acceptance formulas are not supplied to discovery.

| Pair | Declared domain | Expected equivalence region |
|---|---|---|
| maximum / minimum | x,y in 0..31 | x == y |
| odd by remainder / bit test | n in 0..UINT32_MAX | true |
| loop sum / closed formula | n in 0..31 | true |
| loop sum / off-by-one formula | n in 0..31 | n == 0 |

These are configuration and integration fixtures, not held-out research
benchmarks. Local native/mocked tests do not establish these universal formulas.

## Add a pair

Create `original.c`, `candidate.c` and `contract.json` in one directory. The two
functions may share the same name. For example, maximum and minimum:

```c
/* original.c */
#include <stdint.h>
uint32_t choose(uint32_t a, uint32_t b) { return a > b ? a : b; }
```

```c
/* candidate.c */
#include <stdint.h>
uint32_t choose(uint32_t a, uint32_t b) { return a < b ? a : b; }
```

```json
{
  "schema": 1,
  "name": "max_min",
  "original": {"source": "original.c", "entry": "choose", "args": ["x", "y"]},
  "candidate": {"source": "candidate.c", "entry": "choose", "args": ["x", "y"]},
  "inputs": {
    "x": {"type": "uint32_t", "min": 0, "max": 31},
    "y": {"type": "uint32_t", "min": 0, "max": 31}
  },
  "return_type": "uint32_t",
  "observations": ["return"],
  "unwind": 40
}
```

Paths are relative to the contract. `args` maps logical input names to each
function's positional parameters; each side must use all inputs exactly once.
Signatures must match the bound types and declared result. Domain bounds are
inclusive; bool inputs use integer 0/1. Unknown JSON keys and duplicate keys are
rejected. Run automatic discovery:

```bash
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract cases/c_scalar/max_min.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

The result reports EXACT, PARTIAL or UNKNOWN and an artifact directory. EXACT
means equality inside the published condition and inequality outside it, both
within the declared domain and return observation. It does not extend the domain
or claim equivalence of arbitrary program state. Exhausting the finite comparison
vocabulary or budgets can leave the result PARTIAL/UNKNOWN.

## Use an external agent

```bash
python3 tools/find-cond-equiv/agent_workflow.py start \
  --case c --contract cases/c_scalar/max_min.json --goal exact \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Give the printed `agent-context.json` to the external chat. After initialization
reports READY, it may submit a separate proposal with that session's UUID and
next round, for example `condition: "x == y"`. This example is a known fixture
answer, not a discovery experiment. Submit the file using:

```bash
python3 tools/find-cond-equiv/agent_workflow.py step \
  --session /absolute/path/printed/session-directory \
  --proposal /absolute/path/proposal.json
```

The existing Boolean condition AST and entry-state comparisons apply; generic
modulo predicates are not yet supported. Agents may help author the initial C
contract, but its domain and observations define the theorem and require human
review. Once a session starts, proposals cannot alter the sources, contract,
safety flags or result labels. No unattended agent API is integrated.

## Admission and proof boundary

- 1..4 `uint32_t`/`bool` inputs; one scalar return; independent rectangular input
  ranges. Arithmetic operands must be unsigned scalars (use `1u`, explicit casts
  where needed); unsigned arithmetic wraps modulo 2^32. The generated C checks
  8-bit bytes, 32-bit int/unsigned int, and uint32_t as unsigned int.
- Initialized automatic scalar locals, pure helper calls, branches, `for` and
  `while` loops. Helpers must appear before callers; recursion is rejected.
  Every function must structurally return on every path. Assignments/increments
  are statement-only, avoiding side effects in expressions. Shift counts must
  be literal values 0u..31u.
- Local automatic const uint32_t/bool tables are admitted with explicit literal
  lengths and complete literal initializers, at most 256 elements per source.
  Only indexed reads with uint32_t indices are allowed; whole-domain safety must
  prove bounds before replay. Report scope.memory lists table declarations.
  No table writes, address-taking, decay, array parameters/returns, static tables
  or implicit zero-fill. See the table guide for the precise supported syntax.
- No globals, pointers, mutable arrays, structs, external calls, signed types,
  floating point, custom includes/macros, I/O or concurrency. Source identifiers
  start with lowercase letters and cannot use the reserved `ce_`/`finder_`
  prefixes; shadowing is rejected. Unsupported input gives a diagnostic and no
  equivalence claim. The existing prime-table and cache adapters remain available
  separately. The generic frontend now supports local constant lookup tables,
  but does not yet replace the stateful cache adapters.
- A real C parser validates the subset. The generated model preserves the
  admitted function bodies, removing only comments and approved standard include
  lines. Checked macros namespace function definitions/calls on each side; local
  names cannot collide with any function. There is no arbitrary C text rewrite
  or agent-generated proof harness.
- Before native execution, a whole-domain harness calls both entries and checks
  safety with unwinding assertions enabled and slicing disabled. Failed safety,
  insufficient unwind, timeout or missing solver leaves UNKNOWN and no traces.
  Equality checks also keep backend safety and unwinding enabled. A native C
  compiler is needed even for startup, but compilation does not execute the
  admitted functions. This checker is not an OS sandbox for hostile files/tools.
- Agent sessions bind source/contract hashes, frontend/parser Python files and
  compiler/ESBMC binaries. Every round checks identity before and after work;
  prior safety is reused only under that identity. Session files remain
  runner-owned, as in the existing protocol. Full compiler dependency closure
  (system headers, shared libraries, environment) is not fingerprinted.

The [post-freeze interval-check experiment](../cases/c_scalar_transfer/README.md)
kept the engine unchanged; its [user-reported result](validation/c-transfer/user-reported-results.md)
is 8/8 required passes and 8/12 discovery EXACT. Future
work includes useful input diagnostics, broader C syntax, array inputs/outputs,
and measuring preparation effort and discovery effectiveness on unseen cases.
