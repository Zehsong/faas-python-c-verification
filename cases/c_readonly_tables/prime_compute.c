#include <stdint.h>
#include <stdbool.h>
bool isprime(uint32_t n) {
    if (n < 2u) return false;
    for (uint32_t d = 2u; d * d <= n; d += 1u) {
        if (n % d == 0u) return false;
    }
    return true;
}
