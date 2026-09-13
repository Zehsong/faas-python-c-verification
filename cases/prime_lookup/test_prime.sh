#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
export FINDER_CC="${CC:-cc}"
PRIME_STATUS=0
# Shared infrastructure changed: retain the existing regression suites.
bash cases/sketch_reuse/test_sketch.sh "$ESBMC" || PRIME_STATUS=2
mkdir -p .verify-equiv-runs/prime-stage
PRIME_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/prime-stage/run-XXXXXX")"
printf 'Prime stage: %s\n' "$PRIME_RUN"
python3 cases/prime_lookup/run_checks.py --esbmc "$ESBMC" --cc "$FINDER_CC" --workdir "$PRIME_RUN" 2>&1 | tee "$PRIME_RUN/console.txt" || PRIME_STATUS=2
if [[ -f "$PRIME_RUN/results.json" ]]; then
    bash tools/archive_equiv_runs.sh prime-lookup "$PRIME_RUN"
else
    printf 'No summary; inspect %s\n' "$PRIME_RUN/console.txt" >&2
    PRIME_STATUS=2
fi
exit "$PRIME_STATUS"
