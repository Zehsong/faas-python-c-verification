#include <stdint.h>

typedef unsigned char Bytef;
typedef unsigned int uInt;
typedef unsigned long uLong;
typedef long Py_ssize_t;

typedef struct {
    void *buf;
    Py_ssize_t len;
} Py_buffer;

unsigned char nondet_uchar(void);
unsigned int nondet_uint(void);
void __ESBMC_assert(_Bool, const char *);

static uLong library_result;

static uLong seen_seed;
static const Bytef *seen_buf;
static uInt seen_len;

/* Stand-in for the one shared libz call. */
static uLong mock_adler32(uLong seed, const Bytef *buf, uInt len)
{
    seen_seed = seed;
    seen_buf = buf;
    seen_len = len;
    return library_result;
}

/* CPython 3.12.1 zlib_adler32_impl specialized to len == 4. */
static unsigned long python_wrapper(
    Py_buffer *data,
    unsigned int value)
{
    if (data->len > 1024 * 5) {
        __ESBMC_assert(0, "large-buffer path must be unreachable");
        return 0;
    }

    value = (unsigned int)mock_adler32(
        value,
        (const Bytef *)data->buf,
        (uInt)data->len
    );

    return (unsigned long)(value & 0xffffffffU);
}

int main(void)
{
    Bytef data[4] = {
        nondet_uchar(),
        nondet_uchar(),
        nondet_uchar(),
        nondet_uchar()
    };

    Py_buffer pybuf = { data, 4 };

    /* adler32's checksum result is a 32-bit value. */
    library_result = (uLong)nondet_uint();

    /* Python zlib.adler32(data): default seed = 1. */
    unsigned long py_result =
        python_wrapper(&pybuf, 1U);

    uLong py_seed = seen_seed;
    const Bytef *py_data = seen_buf;
    uInt py_len = seen_len;

    __ESBMC_assert(
        py_seed == 1UL,
        "Python wrapper seed == 1"
    );

    __ESBMC_assert(
        py_data == data,
        "Python wrapper passes same buffer"
    );

    __ESBMC_assert(
        py_len == 4U,
        "Python wrapper passes length 4"
    );

    /*
     * C side:
     *     adler32(1L, data, 4)
     */
    uLong c_result = mock_adler32(1UL, data, 4U);

    __ESBMC_assert(
        seen_seed == py_seed,
        "Python and C pass same seed"
    );

    __ESBMC_assert(
        seen_buf == py_data,
        "Python and C pass same buffer"
    );

    __ESBMC_assert(
        seen_len == py_len,
        "Python and C pass same length"
    );

    __ESBMC_assert(
        py_result == (unsigned long)(unsigned int)c_result,
        "Python and C map same library result"
    );

    return 0;
}
