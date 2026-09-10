def f(x: int) -> int:
    count: int = 0

    for i in range(4):
        if x > i:
            count += 1

    return count
