#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
SCALE_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/popcount-scaling-stage
SCALE_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/popcount-scaling-stage/run-XXXXXX")"
SCALE_STATUS=0
python3 -m unittest discover -s cases/c_external_bits -p 'test_scaling.py' -v 2>&1 | tee "$SCALE_RUN/unit-tests.txt" || SCALE_STATUS=2
if [[ "$SCALE_STATUS" == 0 ]]; then
    python3 cases/c_external_bits/run_scaling.py --esbmc "$SCALE_ESBMC" --cc "$FINDER_CC" --workdir "$SCALE_RUN" 2>&1 | tee "$SCALE_RUN/console.txt" || SCALE_STATUS=2
fi
if [[ -f "$SCALE_RUN/results.json" ]]; then
    ESBMC="$SCALE_ESBMC" bash tools/archive_equiv_runs.sh popcount-scaling "$SCALE_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$SCALE_RUN" >&2
    SCALE_STATUS=2
fi
exit "$SCALE_STATUS"
