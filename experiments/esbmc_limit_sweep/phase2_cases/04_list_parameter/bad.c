#include <assert.h>

int nondet_int(void);

int transform(int *xs, int idx)
{
    /* MUTATION */
    xs[1] = xs[1] + 6;
    return xs[idx];
}

int main(void)
{
    int a = nondet_int();
    int b = nondet_int();
    int c = nondet_int();
    int idx = nondet_int();

    __ESBMC_assume(-10 <= a && a <= 10);
    __ESBMC_assume(-10 <= b && b <= 10);
    __ESBMC_assume(-10 <= c && c <= 10);
    __ESBMC_assume(0 <= idx && idx <= 2);

    int xs[3] = {a, b, c};

    int r = transform(xs, idx);

    int expected;

    if (idx == 0)
        expected = a;
    else if (idx == 1)
        expected = b + 5;
    else
        expected = c;

    assert(r == expected);

    return 0;
}
