extern int __VERIFIER_nondet_int(void);

extern long __ESBMC_PY_TARGET(
    long selector,
    long e0
);

int sanity_main(void)
{
    int selector = __VERIFIER_nondet_int();
    int e0 = __VERIFIER_nondet_int();

    long expected = 0;

    if (selector >= 1 && e0 > 0)
        expected = 1;

    long actual =
        __ESBMC_PY_TARGET(
            (long)selector,
            (long)e0
        );

    __ESBMC_assert(
        actual == expected,
        "__VEQ_PYTHON_LIST_SANITY__"
    );

    return 0;
}

int main(void)
{
    return sanity_main();
}
