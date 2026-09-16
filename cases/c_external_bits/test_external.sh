#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
BITS_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-external-stage
BITS_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-external-stage/run-XXXXXX")"
BITS_STATUS=0
python3 -m unittest discover -s cases/c_external_bits -p 'test_external_bits.py' -v 2>&1 | tee "$BITS_RUN/unit-tests.txt" || BITS_STATUS=2
if [[ "$BITS_STATUS" == 0 ]]; then
    python3 cases/c_external_bits/run_checks.py --esbmc "$BITS_ESBMC" --cc "$FINDER_CC" --workdir "$BITS_RUN" 2>&1 | tee "$BITS_RUN/console.txt" || BITS_STATUS=2
fi
if [[ -f "$BITS_RUN/results.json" ]]; then
    ESBMC="$BITS_ESBMC" bash tools/archive_equiv_runs.sh c-external-bits "$BITS_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$BITS_RUN" >&2
    BITS_STATUS=2
fi
exit "$BITS_STATUS"
