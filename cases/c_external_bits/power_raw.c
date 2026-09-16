#include <stdint.h>
#include <stdbool.h>

/* Sean Eron Anderson, Bit Twiddling Hacks, public-domain snippet.
 * https://graphics.stanford.edu/~seander/bithacks.html#DetermineIfPowerOf2
 * Adaptation: function wrapper, uint32_t, x naming and unsigned literals.
 * The original zero edge case is deliberately preserved. */
bool power(uint32_t x) {
    return (x & (x - 1u)) == 0u;
}
