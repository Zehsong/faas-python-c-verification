int f(int *xs, int n)
{
    int count = 0;

    for (int i = 0; i < n; ++i)
    {
        /* mutation: zero incorrectly counts as positive */
        if (xs[i] >= 0)
            count += 1;
    }

    return count;
}
