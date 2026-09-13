def f(s: str) -> int:
    n: int = len(s)

    if n > 0:
        assert len(s[0]) == 1

    return n
