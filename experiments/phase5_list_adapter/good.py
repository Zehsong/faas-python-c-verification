def f(xs: list[int]) -> int:
    count: int = 0

    for x in xs:
        if x > 0:
            count += 1

    return count
