#include <stdint.h>
uint32_t clamp(uint32_t x, uint32_t low, uint32_t high)
{
    if (x > high) return high;
    if (x < low) return low;
    return x;
}
