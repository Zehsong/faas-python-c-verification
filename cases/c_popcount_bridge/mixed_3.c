#include <stdint.h>

/* Proposed bridge: replace low bytes one at a time, with no assumed lemmas.
 * Byte parallel recipe is specialized from the attributed original at
 * ../c_external_bits/popcount_parallel.c. All connections need full proofs. */
uint32_t count_loop(uint32_t x) {
    uint32_t count = 0u;
    for (uint32_t i = 0u; i < 8u; i = i + 1u) {
        count = count + (x & 1u);
        x = x >> 1u;
    }
    return count;
}

uint32_t count_parallel(uint32_t x) {
    x = x - ((x >> 1u) & 0x55u);
    x = (x & 0x33u) + ((x >> 2u) & 0x33u);
    return (x + (x >> 4u)) & 0x0Fu;
}

uint32_t popcount(uint32_t x) {
    return count_parallel(x & 255u) + count_parallel((x >> 8u) & 255u)
         + count_parallel((x >> 16u) & 255u) + count_loop(x >> 24u);
}
