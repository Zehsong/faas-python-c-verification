#!/usr/bin/env python3
"""Held-out formulas are used only after automatic search and certification."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/find-cond-equiv"))
sys.path.insert(0, str(ROOT / "cases/same_language_cache"))
import find_config_conditions as adapter
from run_finder_checks import main

CASES = [
    ("good", "invariant", "true"),
    ("stale", "invariant", "!(finder_valid && finder_key == finder_x) || finder_config == finder_cached_config"),
    ("stale", "empty", "true"),
]

if __name__ == "__main__":
    sys.exit(main(CASES, adapter, ".verify-equiv-runs/config-cache-acceptance", "CONFIG CACHE ACCEPTANCE"))
