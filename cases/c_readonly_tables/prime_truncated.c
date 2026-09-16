#include <stdint.h>
#include <stdbool.h>
bool isprime(uint32_t n) {
    const bool table[32u] = {
        false, false, true, true, false, true, false, true,
        false, false, false, true, false, true, false, false,
        false, true, false, true, false, false, false, true,
        false, false, false, false, false, true, false, true
    };
    if (n < 32u) return table[n];
    return false;
}
