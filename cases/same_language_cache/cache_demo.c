#include "cache_model.h"

#ifndef REPLAY
extern uint32_t nondet_uint32_t(void);
extern bool nondet_bool(void);
extern void __ESBMC_assume(bool);
extern void __ESBMC_assert(bool, const char *);

static void check_call(Cache *cache, uint32_t x, bool bug)
{
    /* The reference is pure; only the optimized implementation owns state. */
    uint32_t r_original = original(x);
    uint32_t r_cached = bug ? cached_bad(cache, x) : cached_good(cache, x);
#ifdef VERIFY_EQUIV_REACHABILITY
    __ESBMC_assert(false, "__VERIFY_EQUIV_REACHABILITY__");
#else
    __ESBMC_assert(r_original == r_cached, "__VERIFY_EQUIV_RELATIONAL_PROPERTY__");
#endif
    __ESBMC_assert(invariant(cache), "cache invariant preserved");
}

static void sequence(bool bug)
{
    Cache cache = {false, 0, 0};
    uint32_t x0 = nondet_uint32_t();
    uint32_t x1 = nondet_uint32_t();
    uint32_t x2 = nondet_uint32_t();
    check_call(&cache, x0, bug);
    check_call(&cache, x1, bug);
    check_call(&cache, x2, bug);
}

static void induction(bool bug, bool conditional)
{
    Cache empty = {false, 0, 0};
    __ESBMC_assert(invariant(&empty), "cache invariant initialized");

    /* Arbitrary state satisfying I, not merely one reached by three calls. */
    Cache cache = {nondet_bool(), nondet_uint32_t(), nondet_uint32_t()};
    uint32_t x = nondet_uint32_t();
    __ESBMC_assume(invariant(&cache));
    if (conditional)
        __ESBMC_assume((cache.valid && cache.key == x) || x == UINT32_MAX);
    check_call(&cache, x, bug);
}

void good_sequence(void) { sequence(false); }
void bad_sequence(void) { sequence(true); }
void good_induction(void) { induction(false, false); }
void bad_induction(void) { induction(true, false); }
void bad_conditional_step(void) { induction(true, true); }
void bad_empty_miss(void)
{
    Cache cache = {false, 0, 0};
    check_call(&cache, UINT32_C(1), true);
}

#else
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

/* Native replay uses the very same three implementations as the harness.
 * Exit 1 means an observed return mismatch; 2 means invalid replay input.
 */
int main(int argc, char **argv)
{
    if (argc < 3 || (argv[1][0] != '0' && argv[1][0] != '1') || argv[1][1]) {
        fprintf(stderr, "usage: cache-replay BUG(0|1) UINT32 [UINT32 ...]\n");
        return 2;
    }
    bool bug = argv[1][0] == '1';
    bool mismatch = false;
    Cache cache = {false, 0, 0};
    for (int i = 2; i < argc; ++i) {
        char *end;
        errno = 0;
        unsigned long long value = strtoull(argv[i], &end, 10);
        if (errno || end == argv[i] || *end || argv[i][0] == '-' || value > UINT32_MAX)
            return 2;
        uint32_t x = (uint32_t)value;
        bool hit = cache.valid && cache.key == x;
        uint32_t expected = original(x);
        uint32_t actual = bug ? cached_bad(&cache, x) : cached_good(&cache, x);
        printf("x=%" PRIu32 " hit=%d original=%" PRIu32 " cached=%" PRIu32 " invariant=%d\n",
               x, (int)hit, expected, actual, (int)invariant(&cache));
        if (!invariant(&cache)) return 2;
        mismatch = mismatch || expected != actual;
    }
    return mismatch ? 1 : 0;
}
#endif
