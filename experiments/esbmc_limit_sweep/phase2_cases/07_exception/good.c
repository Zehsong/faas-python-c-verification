#include <assert.h>

int nondet_int(void);

int safe_div(int x)
{
    if (x == 0)
        return -1;

    return 100 / x;
}

int main(void)
{
    int x = nondet_int();

    __ESBMC_assume(-10 <= x && x <= 10);

    int r = safe_div(x);

    if (x == 0)
        assert(r == -1);
    else
        assert(r == 100 / x);

    return 0;
}
