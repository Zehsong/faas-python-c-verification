#include <stdint.h>

/* Project-authored byte specialization of the attributed parallel recipe in
 * ../c_external_bits/popcount_parallel.c. Callers supply values in 0..255.
 * No precondition or helper equivalence is assumed by the proof runner. */
uint32_t count_byte(uint32_t x) {
    x = x - ((x >> 1u) & 0x55u);
    x = (x & 0x33u) + ((x >> 2u) & 0x33u);
    return (x + (x >> 4u)) & 0x0Fu;
}

uint32_t popcount(uint32_t x) {
    return count_byte(x & 255u) + count_byte((x >> 8u) & 255u)
         + count_byte((x >> 16u) & 255u) + count_byte(x >> 24u);
}
