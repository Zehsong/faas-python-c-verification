def f(xs: list[int]) -> int:
    count: int = 0

    for x in xs:
        if x > 0:
            count += 1

    return count



def __VEQ_PY_LIST_INT_ADAPTER(selector: int, e0: int) -> int:
    xs: list[int] = []
    if selector >= 1:
        xs.append(e0)
    return f(xs)

# ------------------------------------------------------------------
# Python-list model sanity oracle.
#
# For max_len=1 the adapter semantics MUST be:
#
# selector < 1        -> []
# selector >= 1       -> [e0]
#
# f(xs) counts positive elements.
# ------------------------------------------------------------------

selector: int = nondet_int()
e0: int = nondet_int()

expected: int = 0

if selector >= 1:
    if e0 > 0:
        expected = 1

actual: int = __VEQ_PY_LIST_INT_ADAPTER(
    selector,
    e0
)

assert actual == expected
