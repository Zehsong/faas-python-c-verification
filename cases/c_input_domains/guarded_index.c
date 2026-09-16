#include <stdint.h>
uint32_t get(const uint32_t a[2], uint32_t n, uint32_t capacity) { if (n < capacity) return a[n]; return 0u; }
