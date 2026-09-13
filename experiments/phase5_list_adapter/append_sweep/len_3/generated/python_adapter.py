def f(xs: list[int]) -> int:
    count: int = 0

    for x in xs:
        if x > 0:
            count += 1

    return count



def __VEQ_PY_LIST_INT_ADAPTER(selector: int, e0: int, e1: int, e2: int) -> int:
    xs: list[int] = []
    if selector >= 1:
        xs.append(e0)
    if selector >= 2:
        xs.append(e1)
    if selector >= 3:
        xs.append(e2)
    return f(xs)
