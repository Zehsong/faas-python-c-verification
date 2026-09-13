int c_f(int x)
{
    if (x < 100)
        return x + 1;

    return 0;
}


int main(void)
{
    return c_f(0) == 1 ? 0 : 1;
}
