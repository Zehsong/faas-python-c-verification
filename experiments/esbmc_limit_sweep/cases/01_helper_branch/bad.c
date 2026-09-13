#include <assert.h>

int nondet_int(void);

int helper(int v)
{
    if (v < 0)
        return -v;

    if (v < 10)
        return v * 2;

    /* MUTATION */
    return v - 2;
}

int f(int x)
{
    return helper(x) + helper(x + 1);
}

int main(void)
{
    int x = nondet_int();

    __ESBMC_assume(-20 <= x);
    __ESBMC_assume(x <= 20);

    int a;

    if (x < 0)
        a = -x;
    else if (x < 10)
        a = x * 2;
    else
        a = x - 3;

    int y = x + 1;
    int b;

    if (y < 0)
        b = -y;
    else if (y < 10)
        b = y * 2;
    else
        b = y - 3;

    assert(f(x) == a + b);

    return 0;
}
