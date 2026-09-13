#ifndef EQUIV_PRIME_MODEL_H
#define EQUIV_PRIME_MODEL_H
#include <stdbool.h>
#include <stdint.h>

/* Reviewed example, not an extracted real-project optimization. */
static bool original(uint32_t x)
{
    if (x < 2) return false;
    for (uint32_t d = 2; d <= x / d; ++d)
        if (x % d == 0) return false;
    return true;
}

static const bool prime_table[32] = {
    false, false, true, true, false, true, false, true,
    false, false, false, true, false, true, false, false,
    false, true, false, true, false, false, false, true,
    false, false, false, false, false, true, false, true
};

static bool lookup_fallback(uint32_t x)
{
    if (x < 32) return prime_table[x];
    return original(x);
}

static bool lookup_truncated(uint32_t x)
{
    if (x < 32) return prime_table[x];
    return false;
}

static const bool mutant_table[32] = {
    false, false, true, true, false, true, false, true,
    false, true, false, true, false, true, false, false,
    false, true, false, true, false, false, false, true,
    false, false, false, false, false, true, false, true
};

static bool lookup_mutant(uint32_t x)
{
    if (x < 32) return mutant_table[x];
    return original(x);
}
#endif
