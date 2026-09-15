#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export FINDER_CC="${CC:-cc}"
AGENT_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
mkdir -p .verify-equiv-runs/agent-stage
AGENT_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/agent-stage/run-XXXXXX")"
AGENT_STATUS=0
python3 -m unittest discover -s tools/find-cond-equiv -p 'test_*.py' -v 2>&1 | tee "$AGENT_RUN/unit-tests.txt" || AGENT_STATUS=2
python3 cases/agent_workflow/run_checks.py --esbmc "$AGENT_ESBMC" --cc "$FINDER_CC" --workdir "$AGENT_RUN" 2>&1 | tee "$AGENT_RUN/console.txt" || AGENT_STATUS=2
if [[ -f "$AGENT_RUN/results.json" ]]; then
    bash tools/archive_equiv_runs.sh agent-workflow "$AGENT_RUN"
else
    printf 'Incomplete run; inspect %s\n' "$AGENT_RUN" >&2
    AGENT_STATUS=2
fi
exit "$AGENT_STATUS"
