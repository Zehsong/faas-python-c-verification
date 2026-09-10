def f(xs: list[int]) -> int:
    count: int = 0

    for x in xs:
        if x > 0:
            count += 1

    return count



def __VEQ_PY_LIST_INT_ADAPTER(selector: int, e0: int) -> int:
    xs: list[int] = []
    if selector <= 0:
        xs = []
    else:
        xs = [e0]
    return f(xs)
