#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
DEMO_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-demo-stage
DEMO_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-demo-stage/run-XXXXXX")"
DEMO_STATUS=0
python3 cases/c_scalar_demo/run_demo.py --esbmc "$DEMO_ESBMC" --cc "${CC:-cc}" --workdir "$DEMO_RUN" 2>&1 | tee "$DEMO_RUN/console.txt" || DEMO_STATUS=2
if [[ -f "$DEMO_RUN/results.json" ]]; then
    ESBMC="$DEMO_ESBMC" bash tools/archive_equiv_runs.sh c-scalar-demo "$DEMO_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$DEMO_RUN" >&2
    DEMO_STATUS=2
fi
exit "$DEMO_STATUS"
