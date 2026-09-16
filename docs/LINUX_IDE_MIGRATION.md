# Migrating to a Linux cloud IDE

The migration target is the `codex/same-language-cache` branch. The research goal
is conditional equivalence between programs in the **same language**, with multiple
language backends over time. C is the current backend, not the research boundary.
The procedure below preserves the historical recovery/build workflow and early
cache checks. Current use is documented in the [C quickstart](C_TOOL_QUICKSTART.md)
and [independent-checkout/venv reproduction](C_TOOL_REPRODUCTION.md); the old
migration test alone does not cover the later table, array and unified demo stages.

## What can be recovered

- All pushed project code, models, bindings, tests and documentation.
- The historical ESBMC base `679fc5c26c27d3049beffb99960de55f88bfadfa` plus
  `ESBMC_LOCAL_CHANGES.patch` from this repository.
- Previously downloaded evidence archives, by uploading those files separately.

Old Codespace files, unpublished ESBMC edits and archives stored only on the old
machine are not copied by cloning this project. Keep that Codespace until its
remaining files can be recovered. A new build must be labelled reconstructed,
not asserted to be byte-identical to the old binary.

## Procedure

Clone the development branch into a persistent directory in the new IDE (consult
the IDE's storage configuration; the script cannot establish persistence):

```bash
git clone --branch codex/same-language-cache https://github.com/Zehsong/faas-python-c-verification.git
cd faas-python-c-verification
bash tools/migrate_linux.sh inspect
```

Send the output before building if the OS is not Ubuntu 22.04/24.04 x86_64.
The `build` mode installs apt dependencies, downloads the pinned source and build
dependencies, applies the saved patch in a fresh directory, and compiles with two
parallel jobs by default. It requires root/sudo and network access to upstream
repositories and release assets. It does not replace an existing toolchain.

```bash
bash tools/migrate_linux.sh build
bash tools/migrate_linux.sh test
```

Toolchains default to `$HOME/equiv-toolchain`. Set `EQUIV_TOOLCHAIN_ROOT` consistently
for all modes if another path is persistent. Set `EQUIV_BUILD_JOBS` to adjust memory
pressure. Build failures retain source/build state and `migration.log`; report that
log before restarting the entire build. Do not paste credentials or tokens.

The saved `current.env` is written only after the build and both custom option
checks succeed. Test mode passes the actual binary path to the existing scripts,
so the new IDE does not need the old `/workspaces` layout. Expected summaries:

```text
FINDER ACCEPTANCE: 5/5 passed
CONFIG CACHE ACCEPTANCE: 3/3 passed
SKETCH CONTROLS: 8/8 passed
```

Test artifacts are saved under `.verify-equiv-runs` and archived separately under
`$HOME/equiv-evidence`. Download the archives for retention outside the IDE.
This command covers the pending same-language stage; the historical Python/C
regression still has fixed paths and is not claimed to have been migrated here.

## Checks performed before delivery

The exact upstream source commit was fetched locally. Both patched source blobs
were restored from Git objects with Linux line endings, and the LF-normalized
saved patch passed `git apply --check` without ignoring context. The initial
Windows checkout failure was due to line-ending differences. Unrelated upstream
regression filenames also exceeded Windows path limits; they do not affect this
two-file patch check and the Linux build recipe does not use that Windows checkout.

The build flags and dependencies were checked against the pinned source's
`CMakeLists.txt`, `scripts/cmake/Options.cmake`, and `scripts/build.sh`.
The shell script passed Bash syntax validation. A Linux build and remote test run
have **not** been completed locally. The IDE OS/resources/access must still be
confirmed, and build/download incompatibilities must be resolved from actual logs.
