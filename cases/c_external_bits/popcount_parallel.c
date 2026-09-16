#include <stdint.h>

/* Sean Eron Anderson, Bit Twiddling Hacks, public-domain snippet.
 * https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetParallel
 * Adaptation: wrapper, uint32_t, x naming, unsigned literals, explicit
 * parentheses and return instead of assigning c. Modulo-2^32 multiplication
 * is intentional, including for inputs with high bits set. */
uint32_t popcount(uint32_t x) {
    x = x - ((x >> 1u) & 0x55555555u);
    x = (x & 0x33333333u) + ((x >> 2u) & 0x33333333u);
    return (((x + (x >> 4u)) & 0x0F0F0F0Fu) * 0x01010101u) >> 24u;
}
