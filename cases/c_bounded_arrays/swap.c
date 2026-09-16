#include <stdint.h>
uint32_t transform(uint32_t a[2]) { uint32_t t = a[0u]; a[0u] = a[1u]; a[1u] = t; return 0u; }
