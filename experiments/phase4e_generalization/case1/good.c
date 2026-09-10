static int compare_helper(int x, int y)
{
    if (x < y)
        return -1;

    if (x == y)
        return 0;

    return 1;
}

int f(int x, int y)
{
    return compare_helper(x, y);
}
