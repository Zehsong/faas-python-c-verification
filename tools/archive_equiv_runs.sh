#!/usr/bin/env bash
# Copy evidence into a fresh directory; never move or overwrite prior runs.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ARCHIVE_LABEL="${1:-baseline}"
ARCHIVE_SOURCE="${2:-.verify-equiv-runs/finder-acceptance}"
ARCHIVE_ROOT="${3:-$HOME/equiv-evidence}"
ARCHIVE_ESBMC="${ESBMC:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
[[ "$ARCHIVE_LABEL" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid archive label' >&2; exit 2; }
[[ -f "$ARCHIVE_SOURCE/results.json" ]] || { echo "Missing $ARCHIVE_SOURCE/results.json" >&2; exit 2; }
mkdir -p "$ARCHIVE_ROOT"
ARCHIVE_DEST="$(mktemp -d "$ARCHIVE_ROOT/${ARCHIVE_LABEL}-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
ARCHIVE_DEST="$(cd "$ARCHIVE_DEST" && pwd)"
cp -a "$ARCHIVE_SOURCE" "$ARCHIVE_DEST/results"
git rev-parse HEAD > "$ARCHIVE_DEST/checkout-at-archive.txt"
git status --porcelain=v1 > "$ARCHIVE_DEST/worktree-at-archive.txt"
git diff HEAD --binary > "$ARCHIVE_DEST/tracked-changes-at-archive.patch"
printf '%s\n' "$ARCHIVE_SOURCE" > "$ARCHIVE_DEST/original-results-path.txt"
printf '%s\n' 'Checkout metadata describes archive time; per-run source snapshots/hashes and version logs describe the actual verification.' > "$ARCHIVE_DEST/README.txt"
if [[ -x "$ARCHIVE_ESBMC" ]]; then
    "$ARCHIVE_ESBMC" --version > "$ARCHIVE_DEST/esbmc-at-archive.txt" 2>&1 || true
fi
(
    cd "$ARCHIVE_DEST"
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
    sha256sum --check --quiet SHA256SUMS
)
tar -czf "$ARCHIVE_DEST.tar.gz" -C "$(dirname "$ARCHIVE_DEST")" "$(basename "$ARCHIVE_DEST")"
sha256sum "$ARCHIVE_DEST.tar.gz" > "$ARCHIVE_DEST.tar.gz.sha256"
printf 'Evidence directory: %s\nDownloadable archive: %s.tar.gz\n' "$ARCHIVE_DEST" "$ARCHIVE_DEST"
