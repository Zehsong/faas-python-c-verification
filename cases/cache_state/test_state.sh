#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
STATE_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/cache-state-stage
STATE_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/cache-state-stage/run-XXXXXX")"
STATE_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_cache_state.py' -v 2>&1 | tee "$STATE_RUN/unit-tests.txt" || STATE_STATUS=2
python3 cases/cache_state/run_checks.py --esbmc "$STATE_ESBMC" --cc "$FINDER_CC" --workdir "$STATE_RUN" 2>&1 | tee "$STATE_RUN/console.txt" || STATE_STATUS=2
if [[ -f "$STATE_RUN/results.json" ]]; then
    ESBMC="$STATE_ESBMC" bash tools/archive_equiv_runs.sh cache-state "$STATE_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$STATE_RUN" >&2
    STATE_STATUS=2
fi
exit "$STATE_STATUS"
