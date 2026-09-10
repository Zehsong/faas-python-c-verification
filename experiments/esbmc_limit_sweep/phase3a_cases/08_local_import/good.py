from helper_good import transform

x: int = nondet_int()
__ESBMC_assume(-20 <= x <= 20)

expected: int = 0

if x < 0:
    expected = -x + 3
else:
    expected = x * 2 + 1

assert transform(x) == expected
