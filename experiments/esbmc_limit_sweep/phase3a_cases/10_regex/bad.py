import re

k: int = nondet_int()
__ESBMC_assume(0 <= k <= 2)

s: str = "abc"

if k == 0:
    s = "abc"
elif k == 1:
    s = "a1"
else:
    s = "xyz"

matched: bool = re.fullmatch("[0-9]+", s) is not None

expected: bool = False

if k == 0:
    expected = True
elif k == 2:
    expected = True

assert matched == expected
