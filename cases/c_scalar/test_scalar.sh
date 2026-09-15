#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
SCALAR_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-scalar-stage
SCALAR_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-scalar-stage/run-XXXXXX")"
SCALAR_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_scalar.py' -v 2>&1 | tee "$SCALAR_RUN/unit-tests.txt" || SCALAR_STATUS=2
python3 cases/c_scalar/run_checks.py --esbmc "$SCALAR_ESBMC" --cc "$FINDER_CC" --workdir "$SCALAR_RUN" 2>&1 | tee "$SCALAR_RUN/console.txt" || SCALAR_STATUS=2
if [[ -f "$SCALAR_RUN/results.json" ]]; then
    ESBMC="$SCALAR_ESBMC" bash tools/archive_equiv_runs.sh c-scalar "$SCALAR_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$SCALAR_RUN" >&2
    SCALAR_STATUS=2
fi
exit "$SCALAR_STATUS"
