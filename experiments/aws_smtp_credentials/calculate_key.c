#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

#define DATE      "11111111"
#define SERVICE   "ses"
#define MESSAGE   "SendRawEmail"
#define TERMINAL  "aws4_request"
#define VERSION   0x04

#define SHA256_LEN 32

static int sign_hmac_sha256(
    const unsigned char *key,
    size_t key_len,
    const char *msg,
    unsigned char out[SHA256_LEN]
) {
    unsigned int out_len = 0;

    unsigned char *ret = HMAC(
        EVP_sha256(),
        key,
        (int)key_len,
        (const unsigned char *)msg,
        strlen(msg),
        out,
        &out_len
    );

    if (ret == NULL || out_len != SHA256_LEN) {
        return 0;
    }

    return 1;
}


static int region_is_valid(const char *region) {
    static const char *valid_regions[] = {
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "ap-southeast-1"
    };

    size_t count =
        sizeof(valid_regions) / sizeof(valid_regions[0]);

    for (size_t i = 0; i < count; i++) {
        if (strcmp(region, valid_regions[i]) == 0) {
            return 1;
        }
    }

    return 0;
}


static char *base64_encode(
    const unsigned char *input,
    size_t input_len
) {
    /*
     * EVP_EncodeBlock needs:
     * 4 * ceil(n / 3) bytes + terminating NUL.
     */
    size_t output_len = 4 * ((input_len + 2) / 3);

    unsigned char *output =
        malloc(output_len + 1);

    if (output == NULL) {
        return NULL;
    }

    int written = EVP_EncodeBlock(
        output,
        input,
        (int)input_len
    );

    if (written < 0) {
        free(output);
        return NULL;
    }

    output[written] = '\0';

    return (char *)output;
}


static char *calculate_key(
    const char *secret_access_key,
    const char *region
) {
    if (!region_is_valid(region)) {
        return NULL;
    }

    unsigned char signature[SHA256_LEN];

    /*
     * Python:
     * ("AWS4" + secret_access_key).encode("utf-8")
     *
     * For this first experiment we restrict the secret to ASCII,
     * so byte concatenation is identical to UTF-8 encoding.
     */
    const char prefix[] = "AWS4";

    size_t secret_len = strlen(secret_access_key);
    size_t first_key_len =
        (sizeof(prefix) - 1) + secret_len;

    unsigned char *first_key =
        malloc(first_key_len);

    if (first_key == NULL) {
        return NULL;
    }

    memcpy(
        first_key,
        prefix,
        sizeof(prefix) - 1
    );

    memcpy(
        first_key + sizeof(prefix) - 1,
        secret_access_key,
        secret_len
    );

    /* signature = sign(("AWS4" + secret).encode(), DATE) */
    if (!sign_hmac_sha256(
            first_key,
            first_key_len,
            DATE,
            signature)) {
        free(first_key);
        return NULL;
    }

    free(first_key);

    /*
     * Subsequent HMAC keys are the previous 32-byte signature.
     */

    unsigned char temp[SHA256_LEN];

    if (!sign_hmac_sha256(
            signature,
            SHA256_LEN,
            region,
            temp)) {
        return NULL;
    }

    memcpy(signature, temp, SHA256_LEN);

    if (!sign_hmac_sha256(
            signature,
            SHA256_LEN,
            SERVICE,
            temp)) {
        return NULL;
    }

    memcpy(signature, temp, SHA256_LEN);

    if (!sign_hmac_sha256(
            signature,
            SHA256_LEN,
            TERMINAL,
            temp)) {
        return NULL;
    }

    memcpy(signature, temp, SHA256_LEN);

    if (!sign_hmac_sha256(
            signature,
            SHA256_LEN,
            MESSAGE,
            temp)) {
        return NULL;
    }

    memcpy(signature, temp, SHA256_LEN);

    /*
     * Python:
     * bytes([VERSION]) + signature
     */
    unsigned char versioned[1 + SHA256_LEN];

    versioned[0] = VERSION;

    memcpy(
        versioned + 1,
        signature,
        SHA256_LEN
    );

    return base64_encode(
        versioned,
        sizeof(versioned)
    );
}


int main(void) {
    const char *secret =
        "TEST_SECRET_ACCESS_KEY";

    const char *region =
        "us-east-1";

    printf(
        "OpenSSL runtime: %s\n",
        OpenSSL_version(OPENSSL_VERSION)
    );

    char *password =
        calculate_key(secret, region);

    if (password == NULL) {
        fprintf(stderr, "calculate_key failed\n");
        return 1;
    }

    printf("%s\n", password);

    free(password);

    return 0;
}
