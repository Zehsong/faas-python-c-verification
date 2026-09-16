#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
TRANSFER_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
TRANSFER_REPEATS="${2:-2}"
mkdir -p .verify-equiv-runs/c-transfer-stage
TRANSFER_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-transfer-stage/run-XXXXXX")"
TRANSFER_STATUS=0
python3 -m unittest discover -s cases/c_scalar_transfer -p 'test_transfer.py' -v 2>&1 | tee "$TRANSFER_RUN/unit-tests.txt" || TRANSFER_STATUS=2
python3 cases/c_scalar_transfer/run_checks.py --esbmc "$TRANSFER_ESBMC" --cc "$FINDER_CC" --repeats "$TRANSFER_REPEATS" --workdir "$TRANSFER_RUN" 2>&1 | tee "$TRANSFER_RUN/console.txt" || TRANSFER_STATUS=2
if [[ -f "$TRANSFER_RUN/results.json" ]]; then
    ESBMC="$TRANSFER_ESBMC" bash tools/archive_equiv_runs.sh c-transfer "$TRANSFER_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$TRANSFER_RUN" >&2
    TRANSFER_STATUS=2
fi
exit "$TRANSFER_STATUS"
