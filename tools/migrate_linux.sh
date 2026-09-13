#!/usr/bin/env bash
# Recover the saved ESBMC source + patch, then rerun the pending sketch stage.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
MIGRATION_PROJECT="$PWD"
MIGRATION_MODE="${1:-inspect}"
MIGRATION_ROOT="${EQUIV_TOOLCHAIN_ROOT:-$HOME/equiv-toolchain}"
MIGRATION_COMMIT=679fc5c26c27d3049beffb99960de55f88bfadfa

case "$MIGRATION_MODE" in
inspect)
    uname -sm
    cat /etc/os-release
    printf '\nProject: %s\n' "$MIGRATION_PROJECT"
    git log -1 --oneline
    for MIGRATION_TOOL in python3 cc cmake ninja git sudo; do
        command -v "$MIGRATION_TOOL" || true
    done
    free -h || true
    df -h .
    exit 0
    ;;
test)
    [[ -f "$MIGRATION_ROOT/current.env" ]] || { echo 'Run build first, or pass your verified ESBMC path directly to test_sketch.sh.' >&2; exit 2; }
    source "$MIGRATION_ROOT/current.env"
    [[ -x "$ESBMC" ]] || { echo 'Saved ESBMC executable is missing.' >&2; exit 2; }
    exec bash cases/sketch_reuse/test_sketch.sh "$ESBMC"
    ;;
build) ;;
*) echo 'Usage: bash tools/migrate_linux.sh inspect|build|test' >&2; exit 2 ;;
esac

[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || { echo 'This recovery recipe currently requires Linux x86_64.' >&2; exit 2; }
source /etc/os-release
[[ "$ID" == ubuntu && ( "$VERSION_ID" == 22.04 || "$VERSION_ID" == 24.04 ) ]] || {
    echo 'This recipe targets Ubuntu 22.04/24.04. Send inspect output to adapt it to your IDE.' >&2; exit 2;
}
MIGRATION_SUDO=()
if [[ "$(id -u)" != 0 ]]; then MIGRATION_SUDO=(sudo); fi
mkdir -p "$MIGRATION_ROOT"
MIGRATION_RUN="$(mktemp -d "$MIGRATION_ROOT/recovery-XXXXXX")"
exec > >(tee "$MIGRATION_RUN/migration.log") 2>&1
printf 'Recovery artifacts: %s\n' "$MIGRATION_RUN"
git rev-parse HEAD > "$MIGRATION_RUN/project-commit.txt"
cat /etc/os-release > "$MIGRATION_RUN/os-release.txt"
"${MIGRATION_SUDO[@]}" apt-get update
"${MIGRATION_SUDO[@]}" apt-get install -y build-essential git cmake ninja-build python3 python3-dev python3-pip python3-venv python3-setuptools python3-toml curl wget unzip xz-utils bison flex gperf pkg-config libboost-all-dev libgmp-dev libmpfr-dev libncurses-dev libz-dev libbz2-dev liblzma-dev g++-multilib

git -c core.autocrlf=false init "$MIGRATION_RUN/source"
git -C "$MIGRATION_RUN/source" fetch --depth=1 https://github.com/esbmc/esbmc.git "$MIGRATION_COMMIT"
git -C "$MIGRATION_RUN/source" -c core.autocrlf=false checkout --detach FETCH_HEAD
[[ "$(git -C "$MIGRATION_RUN/source" rev-parse HEAD)" == "$MIGRATION_COMMIT" ]]
python3 - "$MIGRATION_PROJECT/ESBMC_LOCAL_CHANGES.patch" "$MIGRATION_RUN/saved.patch" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes().replace(b'\r\n', b'\n'))
PY
git -C "$MIGRATION_RUN/source" apply --check "$MIGRATION_RUN/saved.patch"
git -C "$MIGRATION_RUN/source" apply "$MIGRATION_RUN/saved.patch"
git -C "$MIGRATION_RUN/source" diff --binary > "$MIGRATION_RUN/applied.patch"
sha256sum "$MIGRATION_RUN/saved.patch" > "$MIGRATION_RUN/patch.sha256"

cmake -S "$MIGRATION_RUN/source" -B "$MIGRATION_RUN/source/build" -G Ninja -DDOWNLOAD_DEPENDENCIES=On -DENABLE_Z3=On -DENABLE_PYTHON_FRONTEND=On -DCMAKE_BUILD_TYPE=Release
cmake --build "$MIGRATION_RUN/source/build" --parallel "${EQUIV_BUILD_JOBS:-2}"
MIGRATION_ESBMC="$MIGRATION_RUN/source/build/src/esbmc/esbmc"
"$MIGRATION_ESBMC" --version | tee "$MIGRATION_RUN/esbmc-version.txt"
"$MIGRATION_ESBMC" --help > "$MIGRATION_RUN/esbmc-help.txt"
grep -F -- '--equiv-py-target' "$MIGRATION_RUN/esbmc-help.txt"
grep -F -- '--equiv-c-target' "$MIGRATION_RUN/esbmc-help.txt"
sha256sum "$MIGRATION_ESBMC" > "$MIGRATION_RUN/esbmc.sha256"
printf 'export ESBMC=%q\n' "$MIGRATION_ESBMC" > "$MIGRATION_ROOT/current.env"
printf '\nBuild finished. This reconstructs the saved patch, not any unsaved old Codespace changes.\nRun: bash tools/migrate_linux.sh test\n'
