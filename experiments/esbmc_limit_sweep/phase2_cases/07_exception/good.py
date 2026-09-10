def safe_div(x: int) -> int:
    try:
        if x == 0:
            raise ValueError("zero")
        return 100 // x
    except ValueError:
        return -1


x: int = nondet_int()

__ESBMC_assume(-10 <= x <= 10)

r: int = safe_div(x)

if x == 0:
    assert r == -1
else:
    assert r == 100 // x
