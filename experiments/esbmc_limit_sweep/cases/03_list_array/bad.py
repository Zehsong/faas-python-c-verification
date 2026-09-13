def f(a: int, b: int, c: int, idx: int) -> int:
    values = [a, b, c]

    # MUTATION
    values[1] = values[1] + 2

    return values[idx]


a: int = nondet_int()
b: int = nondet_int()
c: int = nondet_int()
idx: int = nondet_int()

__ESBMC_assume(-10 <= a <= 10)
__ESBMC_assume(-10 <= b <= 10)
__ESBMC_assume(-10 <= c <= 10)

__ESBMC_assume(0 <= idx <= 2)

expected: int = 0

if idx == 0:
    expected = a
elif idx == 1:
    expected = b + 1
else:
    expected = c

assert f(a, b, c, idx) == expected
