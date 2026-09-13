def compare_helper(x: int, y: int) -> int:
    if x < y:
        return -1
    if x == y:
        return 0
    return 1

def f(x: int, y: int) -> int:
    return compare_helper(x, y)
