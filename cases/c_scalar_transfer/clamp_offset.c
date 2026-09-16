#include <stdint.h>
uint32_t clamp(uint32_t x, uint32_t low, uint32_t high)
{
    uint32_t value = x < low ? low : (x > high ? high : x);
    return value + 1u;
}
