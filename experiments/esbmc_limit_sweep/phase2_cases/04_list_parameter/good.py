def transform(xs: list[int], idx: int) -> int:
    xs[1] = xs[1] + 5
    return xs[idx]


a: int = nondet_int()
b: int = nondet_int()
c: int = nondet_int()
idx: int = nondet_int()

__ESBMC_assume(-10 <= a <= 10)
__ESBMC_assume(-10 <= b <= 10)
__ESBMC_assume(-10 <= c <= 10)
__ESBMC_assume(0 <= idx <= 2)

xs: list[int] = [a, b, c]

r: int = transform(xs, idx)

expected: int = 0

if idx == 0:
    expected = a
elif idx == 1:
    expected = b + 5
else:
    expected = c

assert r == expected
