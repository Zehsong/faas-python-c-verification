#include <stdint.h>
uint32_t transform(const uint32_t src[2], uint32_t dst[2]) { dst[0u] = src[1u]; dst[1u] = src[0u]; return 0u; }
