extern int __VERIFIER_nondet_int(void);

extern void __ESBMC_PY_INIT_ENTRY(void);

extern long __ESBMC_PY_TARGET(
    long selector,
    long e0,
    long e1,
    long e2,
    long e3
);

extern int __ESBMC_C_TARGET(
    int selector,
    int e0,
    int e1,
    int e2,
    int e3
);

int equiv_main(void)
{
    /*
     * Restore Python frontend/module initialization semantics
     * before executing the relational request.
     */
    __ESBMC_PY_INIT_ENTRY();

    int selector = __VERIFIER_nondet_int();
    int e0 = __VERIFIER_nondet_int();
    int e1 = __VERIFIER_nondet_int();
    int e2 = __VERIFIER_nondet_int();
    int e3 = __VERIFIER_nondet_int();

    long r_py = __ESBMC_PY_TARGET(
        (long)selector,
        (long)e0,
        (long)e1,
        (long)e2,
        (long)e3
    );

    long r_c = (long)__ESBMC_C_TARGET(
        selector,
        e0,
        e1,
        e2,
        e3
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
