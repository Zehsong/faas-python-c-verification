#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
DEMO_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-tool-demo-stage
DEMO_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-tool-demo-stage/run-XXXXXX")"
DEMO_STATUS=0
python3 -m unittest discover -s cases/c_tool_demo -p 'test_showcase.py' -v 2>&1 | tee "$DEMO_RUN/unit-tests.txt" || DEMO_STATUS=2
python3 cases/c_tool_demo/run_showcase.py --esbmc "$DEMO_ESBMC" --cc "$FINDER_CC" --workdir "$DEMO_RUN" 2>&1 | tee "$DEMO_RUN/console.txt" || DEMO_STATUS=2
if [[ -f "$DEMO_RUN/results.json" ]]; then
    ESBMC="$DEMO_ESBMC" bash tools/archive_equiv_runs.sh c-tool-demo "$DEMO_RUN"
else
    printf 'Incomplete demonstration; inspect %s\n' "$DEMO_RUN" >&2
    DEMO_STATUS=2
fi
exit "$DEMO_STATUS"
