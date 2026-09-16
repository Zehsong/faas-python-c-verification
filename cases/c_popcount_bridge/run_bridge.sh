#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
BRIDGE_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/popcount-bridge-stage
BRIDGE_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/popcount-bridge-stage/run-XXXXXX")"
BRIDGE_STATUS=0
python3 -m unittest discover -s cases/c_popcount_bridge -p 'test_bridge.py' -v 2>&1 | tee "$BRIDGE_RUN/unit-tests.txt" || BRIDGE_STATUS=2
if [[ "$BRIDGE_STATUS" == 0 ]]; then
    python3 cases/c_popcount_bridge/run_bridge.py --esbmc "$BRIDGE_ESBMC" --cc "$FINDER_CC" --workdir "$BRIDGE_RUN" 2>&1 | tee "$BRIDGE_RUN/console.txt" || BRIDGE_STATUS=2
fi
if [[ -f "$BRIDGE_RUN/results.json" ]]; then
    ESBMC="$BRIDGE_ESBMC" bash tools/archive_equiv_runs.sh popcount-bridge "$BRIDGE_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$BRIDGE_RUN" >&2
    BRIDGE_STATUS=2
fi
exit "$BRIDGE_STATUS"
