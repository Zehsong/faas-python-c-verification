#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
RESULT_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/m2-stage
RESULT_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/m2-stage/run-XXXXXX")"
RESULT_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_result_contract.py' -v 2>&1 | tee "$RESULT_RUN/unit-tests.txt" || RESULT_STATUS=2
python3 cases/result_contract/run_checks.py --esbmc "$RESULT_ESBMC" --cc "$FINDER_CC" --workdir "$RESULT_RUN" 2>&1 | tee "$RESULT_RUN/console.txt" || RESULT_STATUS=2
if [[ -f "$RESULT_RUN/results.json" ]]; then
    ESBMC="$RESULT_ESBMC" bash tools/archive_equiv_runs.sh m2-results "$RESULT_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$RESULT_RUN" >&2
    RESULT_STATUS=2
fi
exit "$RESULT_STATUS"
