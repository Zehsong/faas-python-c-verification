#include "prime_model.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    bool (*candidate)(uint32_t) = NULL;
    if (!strcmp(argv[1], "fallback")) candidate = lookup_fallback;
    if (!strcmp(argv[1], "truncated")) candidate = lookup_truncated;
    if (!strcmp(argv[1], "mutant")) candidate = lookup_mutant;
    if (!candidate) return 2;
    uint32_t x;
    int count;
    while ((count = scanf("%" SCNu32, &x)) == 1) {
        printf("{\"x\":%" PRIu32 ",\"r_original\":%d,\"r_cached\":%d}\n",
               x, (int)original(x), (int)candidate(x));
    }
    return count == EOF ? 0 : 2;
}
