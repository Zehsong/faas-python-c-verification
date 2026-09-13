# Configuration-dependent cache experiment

This is a second, manually modelled C cache instance. It reuses the existing
predicate partition search, counterexample replay, obligation classifier and
final sufficiency/complement checks. It is not yet automatic extraction from a
real project or evidence of cross-project generalization.

`original(x, config)` returns `x + config` with uint32_t modular arithmetic.
The environment may change `config` between calls, but not during a call.
The private cache stores `valid, key, value, cached_config`.

The supplied invariant is:

```c
!cache.valid || cache.value == original(cache.key, cache.cached_config)
```

It permits stale entries: there is deliberately no assumption that current
`config` equals `cached_config`. External changes to `config` leave this historical
invariant intact. Both implementations preserve it. `good` checks the saved
configuration on a hit; `stale` only checks the key.

The finder starts with `valid` and all ten pairwise equalities between the five
numeric entry fields. The search chooses combinations using native observations;
it never reads the acceptance formulas. This vocabulary is supplied by the adapter,
not automatically inferred from arbitrary source code. The model, invariant and
field bindings are the new manual work; the search and proof engine are reused.

The independent acceptance runner checks these expected answers only after search:

| Variant / domain | Expected exact one-call condition |
|---|---|
| good / invariant | true |
| stale / invariant | `!(valid && key == x) || config == cached_config` |
| stale / empty | true |

These are expected results until Codespace ESBMC reports them as proved. A predicate
over `x` alone cannot distinguish a fresh and stale cache for the same input.
Even an exact result here covers only this return observation and declared domain.
An unrestricted sequence theorem for conditional variants is not claimed.

## Codespace

Archive the previous five-case results separately:

```bash
bash tools/archive_equiv_runs.sh baseline-5of5 .verify-equiv-runs/finder-acceptance
```

Then run the new stage using the existing custom binary:

```bash
bash cases/config_cache/test_finder.sh /workspaces/esbmc-current/build/src/esbmc/esbmc
```

This runs 48 local/native tests, repeats the original five-case solver acceptance,
and runs three new solver cases. Each stage has a fresh directory; the previous
baseline remains untouched. Expected summaries are `FINDER ACCEPTANCE: 5/5 passed`
and `CONFIG CACHE ACCEPTANCE: 3/3 passed`.

The runner archives baseline regression and new results separately under
`$HOME/equiv-evidence`, including failed/UNKNOWN completed suites, console output,
source snapshots, replay logs, hashes and run reports. Each archive has SHA256SUMS
and a sibling `.tar.gz` for download. Download archives for retention beyond the
Codespace lifecycle. Archive-time checkout/version metadata is explicitly separate
from per-run source/version evidence; old absolute log paths remain historical.

For a single search:

```bash
python3 tools/find-cond-equiv/find_config_conditions.py --variant stale \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --workdir .verify-equiv-runs/config-condition-finder
```

Local Windows verification: all 48 tests passed with MSVC, including native stale
reproduction across a configuration change, uint32_t wraparound, instrumented/plain
probe parity, formal-template compilation, and missing-solver UNKNOWN behavior.
No ESBMC proof was run locally. The preceding baseline's five-case Codespace pass
was reported by the user; its full run artifacts are not present locally.
