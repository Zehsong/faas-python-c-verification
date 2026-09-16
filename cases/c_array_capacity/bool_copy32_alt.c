#include <stdint.h>
#include <stdbool.h>
uint32_t copybits(bool dst[32], const bool src[32]) { if (src[31u]) { dst[31u] = true; } else { dst[31u] = false; } return 0u; }
