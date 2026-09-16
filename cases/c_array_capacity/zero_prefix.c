#include <stdint.h>
#include <stdbool.h>
uint32_t clear(uint32_t a[16], uint32_t n) { for (uint32_t i = 0u; i < n; i++) { a[i] = 0u; } return n; }
