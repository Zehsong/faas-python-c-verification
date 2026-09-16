#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
DOMAIN_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/c-domain-stage
DOMAIN_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/c-domain-stage/run-XXXXXX")"
DOMAIN_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_c_input_domains.py' -v 2>&1 | tee "$DOMAIN_RUN/unit-tests.txt" || DOMAIN_STATUS=2
python3 -m unittest discover -s cases/c_input_domains -p 'test_*.py' -v 2>&1 | tee "$DOMAIN_RUN/assembly-tests.txt" || DOMAIN_STATUS=2
python3 cases/c_input_domains/run_checks.py --esbmc "$DOMAIN_ESBMC" --cc "$FINDER_CC" --workdir "$DOMAIN_RUN" 2>&1 | tee "$DOMAIN_RUN/console.txt" || DOMAIN_STATUS=2
if [[ -f "$DOMAIN_RUN/results.json" ]]; then
    ESBMC="$DOMAIN_ESBMC" bash tools/archive_equiv_runs.sh c-input-domains "$DOMAIN_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$DOMAIN_RUN" >&2
    DOMAIN_STATUS=2
fi
exit "$DOMAIN_STATUS"
