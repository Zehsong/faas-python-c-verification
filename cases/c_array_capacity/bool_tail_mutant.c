#include <stdint.h>
#include <stdbool.h>
uint32_t tail(bool a[64], uint32_t n) { if (n == 0u) { a[63u] = !a[63u]; } return n; }
