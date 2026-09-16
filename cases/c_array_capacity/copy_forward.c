#include <stdint.h>
#include <stdbool.h>
uint32_t copy(uint32_t dst[8], const uint32_t src[8], uint32_t n) { for (uint32_t i = 0u; i < n; i++) { dst[i] = src[i]; } return n; }
