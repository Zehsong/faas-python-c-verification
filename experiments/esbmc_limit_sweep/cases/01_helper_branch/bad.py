def helper(v: int) -> int:
    if v < 0:
        return -v
    if v < 10:
        return v * 2

    # MUTATION
    return v - 2


def f(x: int) -> int:
    return helper(x) + helper(x + 1)


x: int = nondet_int()
__ESBMC_assume(-20 <= x <= 20)

a: int = 0
if x < 0:
    a = -x
elif x < 10:
    a = x * 2
else:
    a = x - 3

y: int = x + 1
b: int = 0
if y < 0:
    b = -y
elif y < 10:
    b = y * 2
else:
    b = y - 3

assert f(x) == a + b
