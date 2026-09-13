#include "../../../../third_party/zlib-v1.3/adler32.c"

int adler4(int e0, int e1, int e2, int e3)
{
    unsigned char data[4];

    data[0] = (unsigned char)e0;
    data[1] = (unsigned char)e1;
    data[2] = (unsigned char)e2;
    data[3] = (unsigned char)e3;

    return (int)adler32(1L, data, 4);
}
