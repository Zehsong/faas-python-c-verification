#include <stdint.h>

/* Project-authored reference: inspect each of the 32 bits. */
uint32_t popcount(uint32_t x) {
    uint32_t count = 0u;
    for (uint32_t i = 0u; i < 32u; i = i + 1u) {
        count = count + (x & 1u);
        x = x >> 1u;
    }
    return count;
}
