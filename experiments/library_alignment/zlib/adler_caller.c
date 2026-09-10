#include <zlib.h>

int main(void)
{
    const unsigned char data[] = "faaslim";

    uLong r = adler32(0L, Z_NULL, 0);
    r = adler32(r, data, 7);

    return (int)(r & 255);
}
