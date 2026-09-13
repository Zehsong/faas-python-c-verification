"""Finite predicate partitioning. Samples choose splits; only an oracle certifies regions."""
from dataclasses import dataclass
from functools import lru_cache
import math
import re

UINT32_MAX = 2**32 - 1
FIELDS = ("x", "valid", "key", "value")


@dataclass(frozen=True)
class Atom:
    numeric_fields = ("x", "key", "value")
    left: str
    op: str = ""
    right: object = None

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str):
            raise ValueError("predicate must be a string")
        text = text.strip()
        if text == "valid":
            return cls("valid")
        fields = "|".join(re.escape(field) for field in cls.numeric_fields)
        match = re.fullmatch(rf"({fields})\s*(==|!=|<=|>=|<|>)\s*({fields}|UINT32_MAX|[0-9]+)", text)
        if not match:
            raise ValueError(f"unsupported predicate: {text!r}; only entry-state comparisons are allowed")
        left, op, right = match.groups()
        if right == "UINT32_MAX":
            right = UINT32_MAX
        elif right.isdigit():
            right = int(right)
        if isinstance(right, int) and not 0 <= right <= UINT32_MAX:
            raise ValueError("predicate constant outside uint32_t")
        return cls(left, op, right)

    def text(self):
        return self.left if not self.op else f"{self.left} {self.op} {self.right}"

    def c(self):
        left = "finder_" + self.left
        if not self.op:
            return left
        right = f"UINT32_C({self.right})" if isinstance(self.right, int) else "finder_" + self.right
        return f"{left} {self.op} {right}"

    def evaluate(self, sample):
        left = sample[self.left]
        if not self.op:
            return bool(left)
        right = self.right if isinstance(self.right, int) else sample[self.right]
        return {"==": left == right, "!=": left != right, "<": left < right,
                "<=": left <= right, ">": left > right, ">=": left >= right}[self.op]


def initial_atoms():
    # Cache-family vocabulary, not a prewritten sufficient condition. Constants
    # are type boundaries, not read from an expected-result or conditional harness.
    return [Atom.parse("valid"), Atom.parse("x == key")] + [
        Atom.parse(f"{field} == {constant}")
        for field in ("x", "key", "value") for constant in (0, 1, UINT32_MAX)]


def matches(cube, atoms, sample):
    return all(atoms[index].evaluate(sample) == truth for index, truth in cube)


def cube_expression(cube, atoms, c=False):
    terms = []
    for index, truth in cube:
        text = atoms[index].c() if c else atoms[index].text()
        terms.append(f"({text})" if truth else f"!({text})")
    return " && ".join(terms) or "true"


def union_expression(cubes, atoms, c=False):
    if not cubes:
        return "false"
    if () in cubes:
        return "true"
    return " || ".join(f"({cube_expression(cube, atoms, c)})" for cube in cubes)


def simplify_cubes(cubes):
    """Expand cubes only when covered by the original union, by Boolean logic.

    No concrete sample and no presumed infeasible assignment licenses expansion.
    """
    original = tuple(frozenset(cube) for cube in cubes)

    @lru_cache(None)
    def covered(candidate):
        fixed = dict(candidate)
        compatible = [term for term in original if all(
            index not in fixed or fixed[index] == value for index, value in term)]
        if any(term <= candidate for term in compatible):
            return True
        if not compatible:
            return False
        index = min(index for term in compatible for index, _ in term if index not in fixed)
        return all(covered(candidate | {(index, value)}) for value in (False, True))

    expanded = []
    for cube in original:
        current = cube
        for literal in sorted(cube):
            candidate = current - {literal}
            if covered(candidate):
                current = candidate
        expanded.append(current)
    terms = set(expanded)
    terms = {term for term in terms if not any(other < term for other in terms)}
    return sorted((tuple(sorted(term)) for term in terms), key=lambda term: (len(term), term))


def entropy(samples):
    if not samples:
        return 0.0
    positive = sum(row["r_original"] == row["r_cached"] for row in samples)
    p = positive / len(samples)
    return 0.0 if p in (0, 1) else -p * math.log2(p) - (1-p) * math.log2(1-p)


def choose_split(cube, atoms, samples):
    relevant = [row for row in samples if matches(cube, atoms, row)]
    used = {index for index, _ in cube}
    ranked = []
    for index, atom in enumerate(atoms):
        if index in used:
            continue
        branches = [[row for row in relevant if atom.evaluate(row) == truth] for truth in (False, True)]
        gain = entropy(relevant) - sum(len(group) * entropy(group) for group in branches) / max(1, len(relevant))
        balance = min(map(len, branches)) / max(1, len(relevant))
        ranked.append((gain, balance, -index, index))
    return max(ranked)[-1] if ranked else None


def search(backend, atoms, max_predicates=16):
    """backend.classify returns EQ, ALL_NEQ, MIXED, EMPTY or UNKNOWN.

    A REFUTED equality query alone is MIXED/unresolved, never ALL_NEQ.
    The backend may append replayed solver witnesses to backend.samples.
    """
    work = [()]
    buckets = {name: [] for name in ("EQ", "ALL_NEQ", "EMPTY", "UNKNOWN")}
    history = []
    while work:
        cube = work.pop()
        result = backend.classify(cube, atoms)
        event = {"cube": cube, "condition": cube_expression(cube, atoms), **result}
        history.append(event)
        status = result["status"]
        if status != "MIXED":
            if status not in buckets:
                raise ValueError(f"invalid region status {status}")
            buckets[status].append(cube)
            continue
        # Counterexamples can add new entry-state constants to the vocabulary.
        # Limit refinement to states in this region whose existing atom
        # valuations fail to separate equal and unequal observations.
        groups = {}
        for row in backend.samples:
            if matches(cube, atoms, row):
                signature = tuple(atom.evaluate(row) for atom in atoms)
                groups.setdefault(signature, []).append(row)
        for group in groups.values():
            if len({row["r_original"] == row["r_cached"] for row in group}) < 2:
                continue
            for row in group:
                for field in getattr(backend, "numeric_fields", Atom.numeric_fields):
                    atom = getattr(backend, "atom_type", Atom).parse(f"{field} == {row[field]}")
                    if atom not in atoms and len(atoms) < max_predicates:
                        atoms.append(atom)
        index = choose_split(cube, atoms, backend.samples)
        if index is None:
            buckets["UNKNOWN"].append(cube)
            event["reason"] = "mixed region exceeds predicate vocabulary"
            continue
        event["split"] = atoms[index].text()
        # Disjoint and exhaustive partition; concrete traces affect only order.
        work.append(tuple(sorted(cube + ((index, False),))))
        work.append(tuple(sorted(cube + ((index, True),))))
    simplified = simplify_cubes(buckets["EQ"])
    return {"buckets": buckets, "history": history, "eq_cubes": simplified,
            "condition": union_expression(simplified, atoms),
            "condition_c": union_expression(simplified, atoms, c=True),
            "predicates": [atom.text() for atom in atoms]}
