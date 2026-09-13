def lookup(k: int) -> int:
    table: dict[int, int] = {
        1: 10,
        2: 20,
        3: 30
    }

    # MUTATION
    table[2] = table[2] + 6

    return table[k]


k: int = nondet_int()

__ESBMC_assume(1 <= k <= 3)

r: int = lookup(k)

expected: int = 0

if k == 1:
    expected = 10
elif k == 2:
    expected = 25
else:
    expected = 30

assert r == expected
