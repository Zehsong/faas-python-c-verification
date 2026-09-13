#ifndef VERIFY_EQUIV_CONFIG_CACHE_H
#define VERIFY_EQUIV_CONFIG_CACHE_H
#include <stdbool.h>
#include <stdint.h>
#ifndef CACHE_BRANCH
#define CACHE_BRANCH(condition) (condition)
#endif

/* Configuration may change between calls, but is stable during one call.
 * cached_config records the environment in which the value was computed. */
typedef struct {
    bool valid;
    uint32_t key, value, cached_config;
} Cache;

static uint32_t original(uint32_t x, uint32_t config) { return x + config; }

static bool invariant(const Cache *cache)
{
    return !cache->valid || cache->value == original(cache->key, cache->cached_config);
}

static uint32_t refresh(Cache *cache, uint32_t x, uint32_t config)
{
    cache->key = x;
    cache->cached_config = config;
    cache->value = original(x, config);
    cache->valid = true;
    return cache->value;
}

static uint32_t cached_good(Cache *cache, uint32_t x, uint32_t config)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x && cache->cached_config == config))
        return cache->value;
    return refresh(cache, x, config);
}

static uint32_t cached_stale(Cache *cache, uint32_t x, uint32_t config)
{
    if (CACHE_BRANCH(cache->valid && cache->key == x)) return cache->value;
    return refresh(cache, x, config);
}
#endif
