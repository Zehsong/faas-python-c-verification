#include <assert.h>

int nondet_int(void);

int f(int x)
{
    if (x < 100)
        return x + 1;

    return 0;
}

int main(void)
{
    int x = nondet_int();

    __ESBMC_assume(x >= -1000);
    __ESBMC_assume(x <= 1000);

    int r = f(x);

    assert(
        (x < 100 && r == x + 1) ||
        (x >= 100 && r == 0)
    );

    return 0;
}
