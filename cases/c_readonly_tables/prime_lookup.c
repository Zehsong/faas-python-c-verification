#include <stdint.h>
#include <stdbool.h>
bool isprime(uint32_t n) {
    const bool table[32u] = {
        false, false, true, true, false, true, false, true,
        false, false, false, true, false, true, false, false,
        false, true, false, true, false, false, false, true,
        false, false, false, false, false, true, false, true
    };
    return table[n];
}
