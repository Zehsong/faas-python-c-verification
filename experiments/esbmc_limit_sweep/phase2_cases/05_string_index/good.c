#include <assert.h>

int nondet_int(void);

int classify(const char *s, int idx)
{
    if (s[idx] == 'a')
        return 1;

    if (s[idx] == 'b')
        return 2;

    return 3;
}

int main(void)
{
    int idx = nondet_int();

    __ESBMC_assume(0 <= idx && idx <= 2);

    const char s[] = "abc";

    int r = classify(s, idx);

    int expected = 3;

    if (idx == 0)
        expected = 1;
    else if (idx == 1)
        expected = 2;

    assert(r == expected);

    return 0;
}
