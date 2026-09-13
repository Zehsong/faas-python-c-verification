def f(xs: list[int]) -> int:
    count: int = 0

    for x in xs:
        if x > 0:
            count += 1

    return count



def __VEQ_PY_LIST_INT_ADAPTER(selector: int, e0: int, e1: int, e2: int, e3: int) -> int:
    xs: list[int] = []
    if selector <= 0:
        xs = []
    elif selector == 1:
        xs = [e0]
    elif selector == 2:
        xs = [e0, e1]
    elif selector == 3:
        xs = [e0, e1, e2]
    else:
        xs = [e0, e1, e2, e3]
    return f(xs)
