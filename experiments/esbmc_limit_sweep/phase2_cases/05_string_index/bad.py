def classify(s: str, idx: int) -> int:
    if s[idx] == "a":
        return 1
    if s[idx] == "b":
        # MUTATION
        return 9
    return 3


idx: int = nondet_int()

__ESBMC_assume(0 <= idx <= 2)

s: str = "abc"

r: int = classify(s, idx)

expected: int = 3

if idx == 0:
    expected = 1
elif idx == 1:
    expected = 2

assert r == expected
