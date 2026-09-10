int f(int *b, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
        if (b[i] <= 1)   /* deliberate byte-domain mutation */
            count++;

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
