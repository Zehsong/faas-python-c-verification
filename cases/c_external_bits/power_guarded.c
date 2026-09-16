#include <stdint.h>
#include <stdbool.h>

/* Sean Eron Anderson, Bit Twiddling Hacks, public-domain snippet.
 * https://graphics.stanford.edu/~seander/bithacks.html#DetermineIfPowerOf2
 * Adaptation: wrapper, uint32_t, x naming and unsigned literal. */
bool power(uint32_t x) {
    return x && !(x & (x - 1u));
}
