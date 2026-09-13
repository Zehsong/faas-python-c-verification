int f(int *b, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
        if (b[i] <= 1)   /* deliberate byte-domain mutation */
            count++;

    return count;
}
