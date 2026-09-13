#!/usr/bin/env python3
"""Manual configuration-cache adapter; shared predicate search and proof backend."""
import itertools
import sys
from find_cache_conditions import CacheBackend, PROPERTIES, ROOT, parse_args as base_args, run as base_run
from predicate_search import Atom, UINT32_MAX

from cache_sketch import CacheSketch

SKETCH = CacheSketch(ROOT / "cases/config_cache/sketch.json")
VARIANTS = SKETCH.data["variants"]
FIELDS = ("x", "valid", "key", "value", "config", "cached_config")


class ConfigAtom(Atom):
    numeric_fields = ("x", "key", "value", "config", "cached_config")


def initial_atoms():
    # Generic pairwise entry-state equalities. No expected formula is supplied.
    fields = ConfigAtom.numeric_fields
    return [ConfigAtom.parse("valid")] + [ConfigAtom.parse(f"{a} == {b}")
        for a, b in itertools.combinations(fields, 2)]


def default_seeds(state_mode):
    numbers = (0, 1, 7, UINT32_MAX)
    if state_mode == "empty":
        return [dict(x=x, valid=0, key=0, value=0, config=config, cached_config=0)
                for x, config in itertools.product(numbers, repeat=2)]
    return [dict(x=x, valid=valid, key=key, value=(key+old)&UINT32_MAX,
                 config=config, cached_config=old)
            for x, valid, key, config, old in itertools.product(numbers, (0, 1), numbers, numbers, numbers)]


def seed_in_domain(row, state_mode):
    if state_mode == "empty":
        return all(row[field] == 0 for field in ("valid", "key", "value", "cached_config"))
    return not row["valid"] or row["value"] == (row["key"] + row["cached_config"]) & UINT32_MAX


def make_harness(model, variant, state_mode, kind, condition="true", expected=None):
    return SKETCH.render(model, variant, state_mode, kind, condition, expected)


class ConfigBackend(CacheBackend):
    sketch = SKETCH
    case = ROOT / "cases/config_cache"
    fields = FIELDS
    numeric_fields = ConfigAtom.numeric_fields
    atom_type = ConfigAtom
    variants = VARIANTS
    initial_atoms = staticmethod(initial_atoms)
    default_seeds = staticmethod(default_seeds)
    seed_in_domain = staticmethod(seed_in_domain)
    make_harness = staticmethod(make_harness)

    def __init__(self, args, workdir):
        super().__init__(args, workdir)
        self.scope.update(
            inputs="x,key,value,config,cached_config:uint32_t; valid:bool; arithmetic modulo 2^32",
            initial_state="empty cache" if args.state_mode == "empty" else
                          "arbitrary cache satisfying !valid || value == original(key,cached_config)",
            assumptions="private sequential cache; config stable within a call, arbitrary between calls; no other cache writers",
            environment_transition="Only config can change externally. The historical-value invariant is independent of config.",
            condition_discovery="shared search with generic pairwise input/state/environment equalities; manual model and invariant",
            sequence_claim="EXACT describes one call under the invariant, not unrestricted sequence equivalence")


def parse_args(argv=None):
    return base_args(argv, variants=VARIANTS, default_variant="stale",
                     default_workdir=".verify-equiv-runs/config-condition-finder")


def run(args):
    return base_run(args, ConfigBackend)


if __name__ == "__main__":
    sys.exit(0 if run(parse_args())["status"] == "EXACT" else 2)
