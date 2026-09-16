#include <stdint.h>
uint32_t clamp(uint32_t x, uint32_t low, uint32_t high)
{
    return x < low ? low : (x > high ? high : x);
}
