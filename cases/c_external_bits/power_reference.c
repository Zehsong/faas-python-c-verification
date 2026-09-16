#include <stdint.h>
#include <stdbool.h>

/* Project-authored reference: reject zero, divide out factors of two. */
bool power(uint32_t x) {
    if (x == 0u) return false;
    while ((x & 1u) == 0u) {
        x = x >> 1u;
    }
    return x == 1u;
}
