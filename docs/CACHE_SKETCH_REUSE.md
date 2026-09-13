# Private-cache sketch reuse: first representation

This stage extracts the duplicated C obligation generator into
`tools/find-cond-equiv/cache_sketch.py`. Both existing adapters now instantiate
that template using their checked-in `sketch.json` bindings. The representation
is experimental and limited to private sequential caches with scalar bool and
uint32_t fields and one uint32_t return observation.

## What is reused

| Component | Shared | Manual per instance |
|---|---|---|
| Proof obligations and property identifiers | One template | Bind input/state names and function arguments |
| Search, witness replay, classification, budgets | Existing engine | Native probe, seeds, allowed entry predicates |
| Initialization and post-call invariant checks | Generated checks | C invariant and initial state |
| Implementation semantics | No abstraction substituted | Original and optimized C, environment assumptions |
| Proof results | None transferred | All obligations rerun against each instance |

The JSON binding contains field types, cache field names, call argument order,
initial values and variant function identifiers. It contains no expected condition
or verdict. Designated C initializers bind cache fields by name. Unsupported data
and code fragments in identifier slots are rejected. This validation does not prove
that a hand-written invariant faithfully models a real application.

Let `I(s)` be the supplied invariant, `P` the original, `Q` the candidate, and `s'`
the state after `Q`. The template generates:

1. `I(s0)` for the declared initial state.
2. `I(s) => I(s')` for an arbitrary call in the modeled domain.
3. Reachability of a candidate region: refute `false` under `I(s) && region`.
4. `I(s) && region => P(x,e) == Q(x,s,e)` and post-call invariant preservation.
5. A separate universally unequal check, with `!=`, to distinguish uniformly
   unequal regions from a single counterexample.
6. Final sufficiency for the union of certified equal regions, and inequality
   throughout its complement before reporting `EXACT`.

For config-cache, `I` relates the stored value to `cached_config`, not current
`config`. The current configuration is independently symbolic and stable only
during a call. A change to it between calls leaves this historical invariant
unchanged. The current report remains a one-call conditional equivalence result;
no unrestricted sequence claim is added by the template extraction.

Each finder run saves `inputs/sketch.json`, `inputs/cache_sketch.py` and
`sketch-manifest.json`, plus existing model/probe snapshots and query sources.
The manifest distinguishes template hash from canonical binding hash. Each query
still records its generated source hash and actual solver command. Matching hashes
are provenance, not permission to reuse an old proof verdict.

## Validation and Codespace command

The user reported the previous config-cache stage at `7ca990d` passed 3/3 and
provided archive locations for both config-cache and baseline regression. These
reports describe the pre-refactoring stage; they do not certify this new template.

Subsequent user feedback confirmed the shared-template stage itself passed baseline
5/5, config-cache 3/3 and sketch controls 8/8. Full solver evidence remains in the
user's Codespace, including the archives timestamped 20260913T102454Z..102456Z.

Local Windows validation after extraction: **53 tests passed, none skipped**, using
MSVC. This includes the previous 48 checks and five new tests for binding validation,
manifest identity, explicit environment binding, failed-obligation gating and actual
native execution of eight positive/negative control harnesses. Native controls run
one reachable state; full symbolic control results require Codespace ESBMC.

```bash
bash cases/sketch_reuse/test_sketch.sh /workspaces/esbmc-current/build/src/esbmc/esbmc
```

Expected solver summaries:

```text
FINDER ACCEPTANCE: 5/5 passed
CONFIG CACHE ACCEPTANCE: 3/3 passed
SKETCH CONTROLS: 8/8 passed
```

The eight controls are four checks for each existing family: valid initialization,
invalid initialization, valid preservation and a candidate that returns the right
value but corrupts the stored value. Invalid controls must be `REFUTED` at the
specific requested assertion. A solver error, UNKNOWN or unrelated safety failure
does not count as successful detection. The stage separately archives baseline,
configuration and control results, including completed failing/UNKNOWN suites.

## Download evidence

Use `tools/prepare_evidence_download.sh` with explicit `.tar.gz` paths. It verifies
available archive sidecar checksums, copies into a fresh `evidence-downloads/bundle-*`
directory and generates portable `SHA256SUMS` using filenames relative to that
bundle. The directory is ignored by Git. Original archives remain untouched.

Download each archive and SHA256SUMS using the Codespace file explorer. The
archives contain full directories; keeping the compressed files is sufficient to
retain their contents. To validate downloaded files on Linux/macOS with sha256sum:

```bash
sha256sum --check SHA256SUMS
```

On Windows, `Get-FileHash -Algorithm SHA256` can be compared to SHA256SUMS.

## Next real-code experiment

Repository inspection found no ready real-project cache optimization in the
available C sources. The existing zlib example
`experiments/library_alignment/zlib/verify/slice_vs_zlib.c` compares four-byte
Adler32 specialization with zlib. It is a useful same-language precedent but
does not exercise cache-sketch reuse. Its source dependency is a gitlink at
`third_party/zlib-v1.3`; the local source checkout is absent.

The next empirical step is selecting and pinning an actual cache optimization,
then documenting original/candidate source, reachable states, external writers,
observations and the adapter work required. We have not selected or verified such
a patch in this stage. The current two-instance reuse demonstrates shared proof
generation, not generalization to arbitrary projects or lower verification cost.
