#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
ARRAY_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-array-stage
ARRAY_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-array-stage/run-XXXXXX")"
ARRAY_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_bounded_arrays.py' -v 2>&1 | tee "$ARRAY_RUN/unit-tests.txt" || ARRAY_STATUS=2
python3 cases/c_bounded_arrays/run_checks.py --esbmc "$ARRAY_ESBMC" --cc "$FINDER_CC" --workdir "$ARRAY_RUN" 2>&1 | tee "$ARRAY_RUN/console.txt" || ARRAY_STATUS=2
if [[ -f "$ARRAY_RUN/results.json" ]]; then
    ESBMC="$ARRAY_ESBMC" bash tools/archive_equiv_runs.sh c-bounded-arrays "$ARRAY_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$ARRAY_RUN" >&2
    ARRAY_STATUS=2
fi
exit "$ARRAY_STATUS"
