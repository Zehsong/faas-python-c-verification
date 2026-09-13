#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
export FINDER_CC="${CC:-cc}"
"$ESBMC" --version
mkdir -p .verify-equiv-runs/config-stage
CONFIG_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/config-stage/run-XXXXXX")"
printf 'Stage results: %s\n' "$CONFIG_RUN"
"$FINDER_CC" -std=c11 -Wall -Wextra -DREPLAY cases/same_language_cache/cache_demo.c -o "$CONFIG_RUN/cache-replay"
export CACHE_REPLAY="$CONFIG_RUN/cache-replay"
python3 -m unittest discover -s tools/verify-equiv -p 'test_*.py' -v 2>&1 | tee "$CONFIG_RUN/oracle-tests.txt"
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_*.py' -v 2>&1 | tee "$CONFIG_RUN/finder-tests.txt"

# Keep both suites and their exit codes, including unresolved/failed cases.
CONFIG_STATUS=0
python3 cases/same_language_cache/run_finder_checks.py --esbmc "$ESBMC" --cc "$FINDER_CC" \
    --workdir "$CONFIG_RUN/baseline-regression" 2>&1 | tee "$CONFIG_RUN/baseline-regression-console.txt" || CONFIG_STATUS=2
python3 cases/config_cache/run_finder_checks.py --esbmc "$ESBMC" --cc "$FINDER_CC" \
    --workdir "$CONFIG_RUN/config-cache" 2>&1 | tee "$CONFIG_RUN/config-cache-console.txt" || CONFIG_STATUS=2
for CONFIG_SUITE in baseline-regression config-cache; do
    if [[ -f "$CONFIG_RUN/$CONFIG_SUITE/results.json" ]]; then
        cp "$CONFIG_RUN/"*-tests.txt "$CONFIG_RUN/$CONFIG_SUITE/"
        cp "$CONFIG_RUN/$CONFIG_SUITE-console.txt" "$CONFIG_RUN/$CONFIG_SUITE/console.txt"
        bash tools/archive_equiv_runs.sh "$CONFIG_SUITE" "$CONFIG_RUN/$CONFIG_SUITE"
    else
        printf 'No summary produced; inspect %s\n' "$CONFIG_RUN/$CONFIG_SUITE-console.txt" >&2
        CONFIG_STATUS=2
    fi
done
exit "$CONFIG_STATUS"
