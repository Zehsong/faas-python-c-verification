def f(x: int) -> int:
    b: bytes = bytes([x])
    return b[0]

x: int = nondet_int()
assume(x >= 0)
assume(x <= 255)

assert f(x) == x
