def f(x: int, n: int) -> int:
    acc: int = 0
    i: int = 0

    while i < n:
        acc = acc + x + i
        i = i + 1

    return acc


x: int = nondet_int()
n: int = nondet_int()

__ESBMC_assume(0 <= x <= 20)
__ESBMC_assume(0 <= n <= 5)

result: int = f(x, n)

expected: int = n * x + (n * (n - 1)) // 2

assert result == expected
