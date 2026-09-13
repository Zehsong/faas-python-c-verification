#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
export FINDER_CC="${CC:-cc}"
VOCABULARY_STATUS=0
# Regression also executes the added native/unit tests.
bash cases/sketch_reuse/test_sketch.sh "$ESBMC" || VOCABULARY_STATUS=2
mkdir -p .verify-equiv-runs/vocabulary-stage
VOCABULARY_RUN="$(mktemp -d "$PWD/.verify-equiv-runs/vocabulary-stage/run-XXXXXX")"
python3 cases/prime_lookup/compare_vocabularies.py --esbmc "$ESBMC" --cc "$FINDER_CC" --workdir "$VOCABULARY_RUN" 2>&1 | tee "$VOCABULARY_RUN/console.txt" || VOCABULARY_STATUS=2
if [[ -f "$VOCABULARY_RUN/results.json" ]]; then
    bash tools/archive_equiv_runs.sh vocabulary-comparison "$VOCABULARY_RUN"
else
    printf 'Incomplete comparison; inspect %s\n' "$VOCABULARY_RUN" >&2
    VOCABULARY_STATUS=2
fi
exit "$VOCABULARY_STATUS"
