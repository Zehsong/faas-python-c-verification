"""Data-only candidate conditions. No agent text is evaluated as Python or C."""
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Condition:
    op: str
    value: object

    def expression(self, c=False):
        if self.op == "literal":
            return "true" if self.value else "false"
        if self.op == "atom":
            return self.value.c() if c else self.value.text()
        if self.op == "not":
            return f"!({self.value.expression(c)})"
        joiner = " && " if self.op == "all" else " || "
        return "(" + joiner.join(f"({child.expression(c)})" for child in self.value) + ")"

    def evaluate(self, row):
        if self.op == "literal":
            return self.value
        if self.op == "atom":
            return bool(self.value.evaluate(row))
        if self.op == "not":
            return not self.value.evaluate(row)
        values = (child.evaluate(row) for child in self.value)
        return all(values) if self.op == "all" else any(values)


def parse_condition(value, atom_type):
    remaining = 128

    def visit(node, depth=0):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 12:
            raise ValueError("condition exceeds 128 nodes or depth 12")
        if type(node) is bool:
            return Condition("literal", node)
        if isinstance(node, str):
            if len(node) > 128:
                raise ValueError("predicate is too long")
            return Condition("atom", atom_type.parse(node))
        if not isinstance(node, dict) or len(node) != 1:
            raise ValueError("condition must be a boolean, supported atom, or all/any/not object")
        op, children = next(iter(node.items()))
        if op == "not":
            return Condition(op, visit(children, depth + 1))
        if op not in ("all", "any") or not isinstance(children, list) or not children:
            raise ValueError("all/any require a nonempty array; only all/any/not are allowed")
        return Condition(op, tuple(visit(child, depth + 1) for child in children))

    return visit(value)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def validate_proposal(proposal, session, backend_type, args):
    required = {"session_id", "round", "condition"}
    if not isinstance(proposal, dict) or not required <= proposal.keys() or set(proposal) - required - {"seeds"}:
        raise ValueError("proposal accepts only session_id, round, condition and optional seeds")
    if proposal["session_id"] != session["session_id"]:
        raise ValueError("proposal belongs to a different session")
    if type(proposal["round"]) is not int or proposal["round"] != session["rounds"] + 1:
        raise ValueError("stale or incorrect proposal round; read the latest agent-context.json")
    condition = parse_condition(proposal["condition"], backend_type.atom_type)
    seeds = proposal.get("seeds", [])
    if not isinstance(seeds, list) or len(seeds) > 256:
        raise ValueError("seeds must be an array of at most 256 entry-state inputs")
    seeds = [backend_type.validate_seed(row) for row in seeds]
    # Prime's domain check is an instance method; checking the fixed domain here
    # avoids constructing a backend or starting a compiler for rejected data.
    if session["config"]["case"] == "prime":
        valid = lambda row: args.domain[0] <= row["x"] <= args.domain[1]
    else:
        valid = lambda row: backend_type.seed_in_domain(row, args.state_mode)
    if not all(valid(row) for row in seeds):
        raise ValueError("seed outside the fixed input/state domain")
    return condition, seeds
