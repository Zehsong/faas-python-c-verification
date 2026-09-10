#include <assert.h>

int nondet_int(void);

int lookup(int k)
{
    if (k == 1)
        return 10;

    if (k == 2)
        return 26;

    return 30;
}

int main(void)
{
    int k = nondet_int();

    __ESBMC_assume(1 <= k && k <= 3);

    int r = lookup(k);

    int expected;

    if (k == 1)
        expected = 10;
    else if (k == 2)
        expected = 25;
    else
        expected = 30;

    assert(r == expected);

    return 0;
}
