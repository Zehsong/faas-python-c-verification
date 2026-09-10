#!/usr/bin/env python3
import json
import itertools
import sys

m = json.load(open(sys.argv[1]))
names = []
domains = []

for name, spec in m["logical_inputs"].items():
    names.append(name)

    if spec["type"] == "bool":
        domains.append([False, True])
    elif spec["type"] == "enum":
        domains.append(spec["values"])
    else:
        raise RuntimeError("unsupported type: " + spec["type"])

for i, values in enumerate(itertools.product(*domains)):
    state = dict(zip(names, values))
    print(i, state)
