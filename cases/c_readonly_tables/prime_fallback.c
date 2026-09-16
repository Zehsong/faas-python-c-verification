#include <stdint.h>
#include <stdbool.h>
bool trial(uint32_t n) {
    if (n < 2u) return false;
    for (uint32_t d = 2u; d * d <= n; d += 1u) {
        if (n % d == 0u) return false;
    }
    return true;
}

bool isprime(uint32_t n) {
    const bool table[32u] = {
        false, false, true, true, false, true, false, true,
        false, false, false, true, false, true, false, false,
        false, true, false, true, false, false, false, true,
        false, false, false, false, false, true, false, true
    };
    if (n < 32u) return table[n];
    return trial(n);
}
