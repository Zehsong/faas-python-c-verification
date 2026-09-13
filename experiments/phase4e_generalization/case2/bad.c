int f(int x)
{
    int count = 0;

    /* mutation: only three iterations */
    for (int i = 0; i < 3; ++i)
    {
        if (x > i)
            count += 1;
    }

    return count;
}
