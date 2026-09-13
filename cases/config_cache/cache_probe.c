#include <stdbool.h>
static int branch_hit;
#ifndef PLAIN_PROBE
static bool record_branch(bool condition) { branch_hit = condition; return condition; }
#define CACHE_BRANCH(condition) record_branch(condition)
#endif
#include "cache_model.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    uint32_t (*candidate)(Cache *, uint32_t, uint32_t) = NULL;
    if (!strcmp(argv[1], "good")) candidate = cached_good;
    if (!strcmp(argv[1], "stale")) candidate = cached_stale;
    if (!candidate) return 2;
    uint32_t x, key, value, config, cached_config;
    unsigned valid;
    int count;
    while ((count = scanf("%" SCNu32 " %u %" SCNu32 " %" SCNu32 " %" SCNu32 " %" SCNu32,
                          &x, &valid, &key, &value, &config, &cached_config)) == 6) {
        if (valid > 1) return 2;
        Cache cache = {valid != 0, key, value, cached_config};
        bool before = invariant(&cache);
        branch_hit = -1;
        uint32_t reference = original(x, config);
        uint32_t result = candidate(&cache, x, config);
        printf("{\"x\":%" PRIu32 ",\"valid\":%u,\"key\":%" PRIu32 ",\"value\":%" PRIu32
               ",\"config\":%" PRIu32 ",\"cached_config\":%" PRIu32
               ",\"r_original\":%" PRIu32 ",\"r_cached\":%" PRIu32
               ",\"hit\":%d,\"invariant_before\":%d,\"invariant_after\":%d"
               ",\"after_valid\":%d,\"after_key\":%" PRIu32 ",\"after_value\":%" PRIu32
               ",\"after_cached_config\":%" PRIu32 "}\n",
               x, valid, key, value, config, cached_config, reference, result,
               branch_hit, (int)before, (int)invariant(&cache), (int)cache.valid,
               cache.key, cache.value, cache.cached_config);
    }
    return count == EOF ? 0 : 2;
}
