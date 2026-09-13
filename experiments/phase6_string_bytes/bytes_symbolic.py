def f(b: bytes) -> int:
    n: int = len(b)

    if n > 0:
        x: int = b[0]
        assert x >= 0
        assert x <= 255
        return x

    return 0
