#include <stdint.h>

/* Negative control: deliberately different on every declared byte input. */
uint32_t popcount(uint32_t x) {
    uint32_t count = 1u;
    for (uint32_t i = 0u; i < 32u; i = i + 1u) {
        count = count + (x & 1u);
        x = x >> 1u;
    }
    return count;
}
