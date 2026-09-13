#ifndef VERIFY_EQUIV_CACHE_MODEL_H
#define VERIFY_EQUIV_CACHE_MODEL_H
#include <stdbool.h>
#include <stdint.h>

/* The native probe may log this branch. Formal runs use the expression alone.
 * The macro evaluates the condition exactly once in both configurations.
 */
#ifndef CACHE_BRANCH
#define CACHE_BRANCH(condition) (condition)
#endif

typedef struct {
    bool valid;
    uint32_t key;
    uint32_t value;
} Cache;

static uint32_t original(uint32_t x) { return x + UINT32_C(1); }

static uint32_t cached_good(Cache *cache, uint32_t x)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x)) return cache->value;
    cache->value = original(x);
    cache->key = x;
    cache->valid = true;
    return cache->value;
}

static uint32_t cached_bad(Cache *cache, uint32_t x)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x)) return cache->value;
    cache->value = original(x);
    cache->key = x;
    cache->valid = true;
    return 0;
}

static uint32_t cached_bad_hit(Cache *cache, uint32_t x)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x)) return 0;
    cache->value = original(x);
    cache->key = x;
    cache->valid = true;
    return cache->value;
}

static uint32_t cached_bad_miss_two(Cache *cache, uint32_t x)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x)) return cache->value;
    cache->value = original(x);
    cache->key = x;
    cache->valid = true;
    return 2;
}

static bool invariant(const Cache *cache)
{
    return !cache->valid || cache->value == original(cache->key);
}
#endif
