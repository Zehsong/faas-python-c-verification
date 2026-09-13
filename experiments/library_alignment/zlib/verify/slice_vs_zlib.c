#include "../../../../third_party/zlib-v1.3/adler32.c"
#include "sliced.c"

unsigned char nondet_uchar(void);
void __ESBMC_assert(_Bool, const char *);

int main(void)
{
    unsigned char e0 = nondet_uchar();
    unsigned char e1 = nondet_uchar();
    unsigned char e2 = nondet_uchar();
    unsigned char e3 = nondet_uchar();

    unsigned char data[4] = {e0, e1, e2, e3};

    uLong original = adler32(1L, data, 4);

    int sliced = adler4(
        (int)e0, (int)e1, (int)e2, (int)e3
    );

    __ESBMC_assert(
        original == (uLong)sliced,
        "specialized slice matches zlib adler32"
    );

    return 0;
}
