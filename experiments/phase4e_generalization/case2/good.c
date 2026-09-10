int f(int x)
{
    int count = 0;

    for (int i = 0; i < 4; ++i)
    {
        if (x > i)
            count += 1;
    }

    return count;
}
