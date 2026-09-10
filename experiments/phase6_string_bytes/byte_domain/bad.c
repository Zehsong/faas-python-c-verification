int f(unsigned char *b, int n)
{
    int count = 0;
    for (int i = 0; i < n; ++i)
        if (b[i] <= 1)   /* mutation */
            count++;
    return count;
}

int byte_adapter(int selector, int e0)
{
    int n = selector >= 1 ? 1 : 0;
    unsigned char b[1] = {(unsigned char)e0};
    return f(b, n);
}
