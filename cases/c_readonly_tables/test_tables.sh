#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
TABLE_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-table-stage
TABLE_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-table-stage/run-XXXXXX")"
TABLE_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_readonly_tables.py' -v 2>&1 | tee "$TABLE_RUN/unit-tests.txt" || TABLE_STATUS=2
python3 cases/c_readonly_tables/run_checks.py --esbmc "$TABLE_ESBMC" --cc "$FINDER_CC" --workdir "$TABLE_RUN" 2>&1 | tee "$TABLE_RUN/console.txt" || TABLE_STATUS=2
if [[ -f "$TABLE_RUN/results.json" ]]; then
    ESBMC="$TABLE_ESBMC" bash tools/archive_equiv_runs.sh c-readonly-tables "$TABLE_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$TABLE_RUN" >&2
    TABLE_STATUS=2
fi
exit "$TABLE_STATUS"
