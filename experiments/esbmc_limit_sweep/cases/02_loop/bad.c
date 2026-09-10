#include <assert.h>

int nondet_int(void);

int f(int x, int n)
{
    int acc = 0;
    int i = 0;

    while (i < n)
    {
        /* MUTATION */
        acc = acc + x + i + 1;
        i = i + 1;
    }

    return acc;
}

int main(void)
{
    int x = nondet_int();
    int n = nondet_int();

    __ESBMC_assume(0 <= x);
    __ESBMC_assume(x <= 20);

    __ESBMC_assume(0 <= n);
    __ESBMC_assume(n <= 5);

    int result = f(x, n);

    int expected =
        n * x + (n * (n - 1)) / 2;

    assert(result == expected);

    return 0;
}
