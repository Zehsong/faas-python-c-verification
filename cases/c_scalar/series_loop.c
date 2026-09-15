#include <stdint.h>
uint32_t sum(uint32_t n) {
    uint32_t total = 0u;
    for (uint32_t i = 0u; i < n; ++i) total += i;
    return total;
}
