#include <assert.h>

int nondet_int(void);

int f(int a, int b, int c, int idx)
{
    int values[3] = {a, b, c};

    /* MUTATION */
    values[1] = values[1] + 2;

    return values[idx];
}

int main(void)
{
    int a = nondet_int();
    int b = nondet_int();
    int c = nondet_int();
    int idx = nondet_int();

    __ESBMC_assume(-10 <= a);
    __ESBMC_assume(a <= 10);

    __ESBMC_assume(-10 <= b);
    __ESBMC_assume(b <= 10);

    __ESBMC_assume(-10 <= c);
    __ESBMC_assume(c <= 10);

    __ESBMC_assume(0 <= idx);
    __ESBMC_assume(idx <= 2);

    int expected;

    if (idx == 0)
        expected = a;
    else if (idx == 1)
        expected = b + 1;
    else
        expected = c;

    assert(f(a, b, c, idx) == expected);

    return 0;
}
