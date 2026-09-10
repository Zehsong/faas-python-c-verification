/* Whole-file C port of the Python Original vSwarm compression function. */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zlib.h>

static void fail(const char *operation) {
    fprintf(stderr, "%s failed: %s\n", operation, strerror(errno));
    exit(EXIT_FAILURE);
}

static double monotonic_seconds(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        fail("clock_gettime");
    }
    return (double)now.tv_sec + (double)now.tv_nsec / 1000000000.0;
}

static uint64_t pss_anon_bytes(void) {
    FILE *input = fopen("/proc/self/smaps_rollup", "r");
    if (input == NULL) {
        return 0;
    }
    char line[256];
    uint64_t kib = 0;
    while (fgets(line, sizeof(line), input) != NULL) {
        if (sscanf(line, "Pss_Anon: %" SCNu64 " kB", &kib) == 1) {
            break;
        }
    }
    fclose(input);
    return kib * 1024;
}

static unsigned char *read_whole_file(const char *path, size_t *size_out) {
    FILE *input = fopen(path, "rb");
    if (input == NULL) {
        fail("open input");
    }
    if (fseeko(input, 0, SEEK_END) != 0) {
        fail("seek input end");
    }
    off_t length = ftello(input);
    if (length < 0 || (uintmax_t)length > SIZE_MAX) {
        fprintf(stderr, "input is too large\n");
        exit(EXIT_FAILURE);
    }
    if (fseeko(input, 0, SEEK_SET) != 0) {
        fail("seek input start");
    }
    size_t size = (size_t)length;
    unsigned char *data = malloc(size == 0 ? 1 : size);
    if (data == NULL) {
        fail("allocate input");
    }
    if (size != 0 && fread(data, 1, size, input) != size) {
        fail("read input");
    }
    if (fclose(input) != 0) {
        fail("close input");
    }
    *size_out = size;
    return data;
}

static void write_whole_file(const char *path, const unsigned char *data, size_t size) {
    FILE *output = fopen(path, "wb");
    if (output == NULL) {
        fail("open output");
    }
    if (size != 0 && fwrite(data, 1, size, output) != size) {
        fail("write output");
    }
    if (fclose(output) != 0) {
        fail("close output");
    }
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <input> <zlib-output>\n", argv[0]);
        return EXIT_FAILURE;
    }

    double started = monotonic_seconds();
    size_t input_size = 0;
    unsigned char *input = read_whole_file(argv[1], &input_size);
    uLong source_size = (uLong)input_size;
    uLongf capacity = compressBound(source_size);
    unsigned char *compressed = malloc((size_t)capacity);
    if (compressed == NULL) {
        fail("allocate compressed output");
    }
    uLongf compressed_size = capacity;
    int status = compress2(compressed, &compressed_size, input, source_size, Z_BEST_COMPRESSION);
    if (status != Z_OK) {
        fprintf(stderr, "compress2 failed with zlib status %d\n", status);
        return EXIT_FAILURE;
    }
    write_whole_file(argv[2], compressed, (size_t)compressed_size);

    printf("%.9f\t%" PRIu64 "\n", monotonic_seconds() - started, pss_anon_bytes());
    free(compressed);
    free(input);
    return EXIT_SUCCESS;
}

