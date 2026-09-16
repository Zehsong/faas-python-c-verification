"""Checked input-domain expressions shared by symbolic and native execution.

This first composable-domain slice uses uint32/bool leaves. It deliberately
accepts data-only Boolean syntax, not arbitrary C, Python or agent assumptions.
"""
from agent_conditions import parse_condition
from predicate_search import Atom, UINT32_MAX


TYPE_LIMITS = {"uint32_t": UINT32_MAX, "bool": 1}


def input_atom_type(specs):
    class InputAtom(Atom):
        numeric_fields = tuple(specs)

        @classmethod
        def parse(cls, text):
            if isinstance(text, str):
                text = text.strip()
                if text in specs and specs[text]["type"] == "bool":
                    return cls(text)
                if text == "valid":
                    raise ValueError("bare valid is allowed only for a declared bool input")
            return super().parse(text)

    return InputAtom


def normalize_bounds(spec, *, defaults=False):
    """Normalize leaves without mutating the user's contract or source identity."""
    element = spec["type"].removesuffix("[]")
    if element not in TYPE_LIMITS:
        raise ValueError("unsupported input type")
    limit = TYPE_LIMITS[element]
    if not defaults and not {"min", "max"} <= spec.keys():
        raise ValueError("legacy input requires explicit min/max")
    lo, hi = spec.get("min", 0), spec.get("max", limit)
    if type(lo) is not int or type(hi) is not int or not (0 <= lo <= limit and 0 <= hi <= limit):
        raise ValueError("invalid scalar input domain")
    return dict(type=element, min=lo, max=hi)


class InputDomain:
    def __init__(self, specs, constraints=True):
        self.specs = specs
        self.atom_type = input_atom_type(specs)
        self.constraints = parse_condition(constraints, self.atom_type)

    def contains(self, row):
        return (all(type(row.get(name)) is int and spec["min"] <= row[name] <= spec["max"]
                    for name, spec in self.specs.items())
                and self.constraints.evaluate(row))

    def expression(self, c=False):
        return self.constraints.expression(c)
