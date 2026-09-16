#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
REFINED_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/popcount-refined-stage
REFINED_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/popcount-refined-stage/run-XXXXXX")"
REFINED_STATUS=0
python3 -m unittest discover -s cases/c_popcount_bridge -p 'test_*.py' -v 2>&1 | tee "$REFINED_RUN/unit-tests.txt" || REFINED_STATUS=2
if [[ "$REFINED_STATUS" == 0 ]]; then
    python3 cases/c_popcount_bridge/run_refined.py --esbmc "$REFINED_ESBMC" --cc "$FINDER_CC" --workdir "$REFINED_RUN" 2>&1 | tee "$REFINED_RUN/console.txt" || REFINED_STATUS=2
fi
if [[ -f "$REFINED_RUN/results.json" ]]; then
    ESBMC="$REFINED_ESBMC" bash tools/archive_equiv_runs.sh popcount-refined "$REFINED_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$REFINED_RUN" >&2
    REFINED_STATUS=2
fi
exit "$REFINED_STATUS"
