extern int __VERIFIER_nondet_int(void);

/*
 * This is intentionally bodyless.
 *
 * After all GOTO binaries are merged, our experimental ESBMC pass will
 * redirect this call to the real Python GOTO function py_f.
 */
extern long __ESBMC_PY_TARGET(long x);

/*
 * This should resolve naturally to the c_f body contained in c.gb.
 */
extern int c_f(int x);

int equiv_main(void)
{
    int x = __VERIFIER_nondet_int();

    long r_py = __ESBMC_PY_TARGET((long)x);
    long r_c  = (long)c_f(x);

    __ESBMC_assert(
        r_py == r_c,
        "Python and C outputs must be equivalent"
    );

    return 0;
}

int main(void)
{
    return equiv_main();
}
