#!/usr/bin/env bash
# Run from any directory. Missing engines or unproved conditions fail the script.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
FINDER_ESBMC="${1:-/workspaces/esbmc-current/build/src/esbmc/esbmc}"
FINDER_COMPILER="${CC:-cc}"
"$FINDER_ESBMC" --version
mkdir -p .verify-equiv-runs/cache-native
"$FINDER_COMPILER" -std=c11 -Wall -Wextra -DREPLAY \
  cases/same_language_cache/cache_demo.c \
  -o .verify-equiv-runs/cache-native/cache-replay
CACHE_REPLAY="$PWD/.verify-equiv-runs/cache-native/cache-replay" \
  python3 -m unittest discover -s tools/verify-equiv -p 'test_*.py' -v
FINDER_CC="$FINDER_COMPILER" \
  python3 -m unittest discover -s tools/find-cond-equiv -p 'test_*.py' -v
python3 cases/same_language_cache/run_cache.py --esbmc "$FINDER_ESBMC"
python3 cases/same_language_cache/run_finder_checks.py \
  --esbmc "$FINDER_ESBMC" --cc "$FINDER_COMPILER"
