#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
BUDGET_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/popcount-budget-stage
BUDGET_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/popcount-budget-stage/run-XXXXXX")"
BUDGET_STATUS=0
python3 -m unittest discover -s cases/c_external_bits -p 'test_*.py' -v 2>&1 | tee "$BUDGET_RUN/unit-tests.txt" || BUDGET_STATUS=2
if [[ "$BUDGET_STATUS" == 0 ]]; then
    python3 cases/c_external_bits/run_budget.py --esbmc "$BUDGET_ESBMC" --cc "$FINDER_CC" --workdir "$BUDGET_RUN" 2>&1 | tee "$BUDGET_RUN/console.txt" || BUDGET_STATUS=2
fi
if [[ -f "$BUDGET_RUN/results.json" ]]; then
    ESBMC="$BUDGET_ESBMC" bash tools/archive_equiv_runs.sh popcount-budget "$BUDGET_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$BUDGET_RUN" >&2
    BUDGET_STATUS=2
fi
exit "$BUDGET_STATUS"
