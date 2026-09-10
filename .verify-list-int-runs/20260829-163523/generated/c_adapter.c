int f(int *b, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
        if (b[i] == 0)
            count++;

    return count;
}



int __VEQ_C_LIST_INT_ADAPTER(int selector, int e0, int e1, int e2, int e3)
{
    int n;

    if (selector <= 0)
        n = 0;
    else if (selector == 1)
        n = 1;
    else if (selector == 2)
        n = 2;
    else if (selector == 3)
        n = 3;
    else
        n = 4;

    int xs[4] = {e0, e1, e2, e3};
    return f(xs, n);
}
