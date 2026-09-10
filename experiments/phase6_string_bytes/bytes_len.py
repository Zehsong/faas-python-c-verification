def f(b: bytes) -> int:
    return len(b)

assert f(b"") == 0
assert f(b"a") == 1
assert f(b"hello") == 5
