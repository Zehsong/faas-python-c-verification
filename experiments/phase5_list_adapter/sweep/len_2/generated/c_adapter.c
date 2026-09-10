int f(int *xs, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
    {
        if (xs[i] > 0)
            count += 1;
    }

    return count;
}



int __VEQ_C_LIST_INT_ADAPTER(int selector, int e0, int e1)
{
    int n;

    if (selector <= 0)
        n = 0;
    else if (selector == 1)
        n = 1;
    else
        n = 2;

    int xs[2] = {e0, e1};
    return f(xs, n);
}
