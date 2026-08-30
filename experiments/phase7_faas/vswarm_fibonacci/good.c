int fibonacci(int num)
{
    int num1 = 0;
    int num2 = 1;
    int total = 0;

    for (int i = 0; i < num; ++i)
    {
        total = num1 + num2;
        num1 = num2;
        num2 = total;
    }

    return num1;
}

int faas_kernel(int n)
{
    if (n < 0)
        return -1;

    if (n > 20)
        return -1;

    return fibonacci(n);
}
