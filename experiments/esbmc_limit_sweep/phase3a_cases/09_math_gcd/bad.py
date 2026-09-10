import math

def reference_gcd(a: int, b: int) -> int:
    while b != 0:
        t: int = b
        b = a % b
        a = t
    return a

a: int = nondet_int()
b: int = nondet_int()

__ESBMC_assume(1 <= a <= 20)
__ESBMC_assume(1 <= b <= 20)

library_result: int = math.gcd(a, b) + 1
reference_result: int = reference_gcd(a, b)

assert library_result == reference_result
