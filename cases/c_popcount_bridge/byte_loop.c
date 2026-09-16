#include <stdint.h>

/* Proposed bridge, not an assumed lemma. Every connection must be proved. */
uint32_t count_byte(uint32_t x) {
    uint32_t count = 0u;
    for (uint32_t i = 0u; i < 8u; i = i + 1u) {
        count = count + (x & 1u);
        x = x >> 1u;
    }
    return count;
}

uint32_t popcount(uint32_t x) {
    return count_byte(x & 255u) + count_byte((x >> 8u) & 255u)
         + count_byte((x >> 16u) & 255u) + count_byte(x >> 24u);
}
