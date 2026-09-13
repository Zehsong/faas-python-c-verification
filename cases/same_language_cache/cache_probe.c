/* Batch native execution for trace-guided search. No solver or expected phi. */
#include <stdbool.h>
static int branch_hit;
static bool record_branch(bool condition) { branch_hit = condition; return condition; }
#ifndef PLAIN_PROBE
#define CACHE_BRANCH(condition) record_branch(condition)
#endif
#include "cache_model.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    uint32_t (*candidate)(Cache *, uint32_t) = NULL;
    if (!strcmp(argv[1], "good")) candidate = cached_good;
    if (!strcmp(argv[1], "bad_miss")) candidate = cached_bad;
    if (!strcmp(argv[1], "bad_hit")) candidate = cached_bad_hit;
    if (!strcmp(argv[1], "bad_miss_two")) candidate = cached_bad_miss_two;
    if (!candidate) return 2;
    uint32_t x, key, value;
    unsigned valid;
    int count;
    while ((count = scanf("%" SCNu32 " %u %" SCNu32 " %" SCNu32, &x, &valid, &key, &value)) == 4) {
        if (valid > 1) return 2;
        Cache cache = {valid != 0, key, value};
        bool before = invariant(&cache);
        branch_hit = -1;
        uint32_t r_original = original(x);
        uint32_t r_cached = candidate(&cache, x);
        printf("{\"x\":%" PRIu32 ",\"valid\":%u,\"key\":%" PRIu32 ",\"value\":%" PRIu32
               ",\"r_original\":%" PRIu32 ",\"r_cached\":%" PRIu32
               ",\"hit\":%d,\"invariant_before\":%d,\"invariant_after\":%d"
               ",\"after_valid\":%d,\"after_key\":%" PRIu32 ",\"after_value\":%" PRIu32 "}\n",
               x, valid, key, value, r_original, r_cached, branch_hit, (int)before,
               (int)invariant(&cache), (int)cache.valid, cache.key, cache.value);
    }
    return count == EOF ? 0 : 2;
}
