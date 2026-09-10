extern int __VERIFIER_nondet_int(void);

extern void __ESBMC_PY_INIT_ENTRY(void);

extern long __ESBMC_PY_TARGET(
    long selector,
    long e0
);

extern int __ESBMC_C_TARGET(
    int selector,
    int e0
);

int equiv_main(void)
{
    __ESBMC_PY_INIT_ENTRY();

    int selector = __VERIFIER_nondet_int();
    int e0       = __VERIFIER_nondet_int();

    long r_py =
        __ESBMC_PY_TARGET(
            (long)selector,
            (long)e0
        );

    long r_c =
        (long)__ESBMC_C_TARGET(
            selector,
            e0
        );

    __ESBMC_assert(
        r_py == r_c,
        "__VERIFY_EQUIV_RELATIONAL_PROPERTY__"
    );

    return 0;
}

int main(void)
{
    return equiv_main();
}
