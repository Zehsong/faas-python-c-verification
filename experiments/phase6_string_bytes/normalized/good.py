# Normalized form of:
#
# def f(b: bytes) -> int:
#     count = 0
#     for x in b:
#         if x == 0:
#             count += 1
#     return count

def f(b: list[int]) -> int:
    count: int = 0
    for x in b:
        if x == 0:
            count += 1
    return count
