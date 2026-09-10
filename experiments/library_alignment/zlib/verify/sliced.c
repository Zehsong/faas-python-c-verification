int adler4(int e0, int e1, int e2, int e3)
{
    unsigned char b0 = (unsigned char)e0;
    unsigned char b1 = (unsigned char)e1;
    unsigned char b2 = (unsigned char)e2;
    unsigned char b3 = (unsigned char)e3;

    unsigned long adler = 1;
    unsigned long sum2 = 0;

    adler += b0; sum2 += adler;
    adler += b1; sum2 += adler;
    adler += b2; sum2 += adler;
    adler += b3; sum2 += adler;

    return (int)(adler | (sum2 << 16));
}
