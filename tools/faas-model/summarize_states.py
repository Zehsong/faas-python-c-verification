#!/usr/bin/env python3
import json, itertools, sys

manifest = json.load(open(sys.argv[1]))
ids = {int(x) for x in sys.argv[2:]}

names = []
domains = []

for name, spec in manifest["logical_inputs"].items():
    names.append(name)
    domains.append(
        [False, True]
        if spec["type"] == "bool"
        else spec["values"]
    )

states = list(itertools.product(*domains))
chosen = [states[i] for i in sorted(ids)]

allowed = []
for d in range(len(names)):
    vals = []
    for s in chosen:
        if s[d] not in vals:
            vals.append(s[d])
    allowed.append(vals)

product_states = set(itertools.product(*allowed))
chosen_states = set(chosen)

print("Target states:", sorted(ids))
print()

if product_states != chosen_states:
    print("Predicate requires multiple cubes/disjunctions.")
    sys.exit(2)

terms = []

for name, vals, universe in zip(names, allowed, domains):
    if len(vals) == len(universe):
        print(f"{name}: *  (don't care)")
        continue

    if len(vals) == 1:
        print(f"{name}: {vals[0]}")
        terms.append(f"{name} == {vals[0]!r}")
    else:
        print(f"{name}: {vals}")
        terms.append(f"{name} in {vals!r}")

print()
print("Predicate:")
print(" AND ".join(terms) if terms else "TRUE")
