#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
CAPACITY_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-array-capacity-stage
CAPACITY_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-array-capacity-stage/run-XXXXXX")"
CAPACITY_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_array_capacity.py' -v 2>&1 | tee "$CAPACITY_RUN/unit-tests.txt" || CAPACITY_STATUS=2
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_length_partition.py' -v 2>&1 | tee "$CAPACITY_RUN/partition-tests.txt" || CAPACITY_STATUS=2
python3 -m unittest discover -s cases/c_array_capacity -p 'test_*.py' -v 2>&1 | tee "$CAPACITY_RUN/assembly-tests.txt" || CAPACITY_STATUS=2
python3 cases/c_array_capacity/run_checks.py --esbmc "$CAPACITY_ESBMC" --cc "$FINDER_CC" --workdir "$CAPACITY_RUN" 2>&1 | tee "$CAPACITY_RUN/console.txt" || CAPACITY_STATUS=2
if [[ -f "$CAPACITY_RUN/results.json" ]]; then
    ESBMC="$CAPACITY_ESBMC" bash tools/archive_equiv_runs.sh c-array-capacity "$CAPACITY_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$CAPACITY_RUN" >&2
    CAPACITY_STATUS=2
fi
exit "$CAPACITY_STATUS"
