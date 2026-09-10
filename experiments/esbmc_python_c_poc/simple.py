def f(x: int) -> int:
    if x < 100:
        return x + 1
    return 0


x: int = nondet_int()

__ESBMC_assume(x >= -1000)
__ESBMC_assume(x <= 1000)

r: int = f(x)

assert (x < 100 and r == x + 1) or \
       (x >= 100 and r == 0)
