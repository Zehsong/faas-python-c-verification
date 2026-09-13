int f(int *xs, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
    {
        /* deliberate mutation: 0 is incorrectly counted */
        if (xs[i] >= 0)
            count += 1;
    }

    return count;
}

int __VEQ_C_LIST_INT_ADAPTER(int selector, int e0)
{
    int n;

    if (selector <= 0)
        n = 0;
    else
        n = 1;

    int xs[1] = {e0};

    return f(xs, n);
}
