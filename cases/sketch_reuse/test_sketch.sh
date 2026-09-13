#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
SKETCH_STATUS=0
bash cases/config_cache/test_finder.sh "$ESBMC" || SKETCH_STATUS=2
mkdir -p .verify-equiv-runs/sketch-stage
SKETCH_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/sketch-stage/run-XXXXXX")"
python3 cases/sketch_reuse/run_checks.py --esbmc "$ESBMC" --workdir "$SKETCH_RUN" 2>&1 | tee "$SKETCH_RUN/console.txt" || SKETCH_STATUS=2
if [[ -f "$SKETCH_RUN/results.json" ]]; then
    bash tools/archive_equiv_runs.sh sketch-controls "$SKETCH_RUN"
else
    printf 'No summary; inspect %s\n' "$SKETCH_RUN/console.txt" >&2
    SKETCH_STATUS=2
fi
exit "$SKETCH_STATUS"
