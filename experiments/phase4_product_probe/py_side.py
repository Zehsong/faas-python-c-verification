def py_f(x: int) -> int:
    if x < 100:
        return x + 1
    return 0


# Keep a tiny top-level use so the function is definitely reachable.
assert py_f(0) == 1
