def f(b: list[int]) -> int:
    count: int = 0
    for x in b:
        if x == 0:
            count += 1
    return count

def byte_adapter(selector: int, e0: int) -> int:
    b: list[int] = []
    if selector >= 1:
        b.append(e0 & 255)
    return f(b)
