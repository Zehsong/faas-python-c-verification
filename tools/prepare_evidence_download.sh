#!/usr/bin/env bash
# Copy explicitly selected archives into a fresh, ignored workspace directory.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ $# -gt 0 ]] || { echo 'Pass one or more .tar.gz archive paths.' >&2; exit 2; }
for EVIDENCE_FILE in "$@"; do
    [[ -f "$EVIDENCE_FILE" && "$EVIDENCE_FILE" == *.tar.gz ]] || { echo "Missing archive: $EVIDENCE_FILE" >&2; exit 2; }
done
mkdir -p evidence-downloads
EVIDENCE_DEST="$(mktemp -d "$PWD/evidence-downloads/bundle-XXXXXX")"
for EVIDENCE_FILE in "$@"; do
    if [[ -f "$EVIDENCE_FILE.sha256" ]]; then
        sha256sum --check "$EVIDENCE_FILE.sha256"
    fi
    EVIDENCE_NAME="$(basename "$EVIDENCE_FILE")"
    [[ ! -e "$EVIDENCE_DEST/$EVIDENCE_NAME" ]] || { echo "Duplicate archive name: $EVIDENCE_NAME" >&2; exit 2; }
    cp -p "$EVIDENCE_FILE" "$EVIDENCE_DEST/$EVIDENCE_NAME"
    cmp "$EVIDENCE_FILE" "$EVIDENCE_DEST/$EVIDENCE_NAME"
done
(
    cd "$EVIDENCE_DEST"
    sha256sum -- *.tar.gz > SHA256SUMS
    sha256sum --check SHA256SUMS
)
printf 'Download the .tar.gz files and SHA256SUMS from: %s\n' "$EVIDENCE_DEST"
