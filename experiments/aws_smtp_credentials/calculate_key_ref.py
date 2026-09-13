import hmac
import hashlib
import base64

DATE = "11111111"
SERVICE = "ses"
MESSAGE = "SendRawEmail"
TERMINAL = "aws4_request"
VERSION = 0x04

SMTP_REGIONS = {
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-southeast-1",
}

def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(
        key,
        msg.encode("utf-8"),
        hashlib.sha256
    ).digest()

def calculate_key(secret_access_key: str, region: str) -> str:
    if region not in SMTP_REGIONS:
        raise ValueError(
            f"The {region} Region doesn't have an SMTP endpoint."
        )

    signature = sign(
        ("AWS4" + secret_access_key).encode("utf-8"),
        DATE
    )
    signature = sign(signature, region)
    signature = sign(signature, SERVICE)
    signature = sign(signature, TERMINAL)
    signature = sign(signature, MESSAGE)

    signature_and_version = bytes([VERSION]) + signature
    smtp_password = base64.b64encode(signature_and_version)

    return smtp_password.decode("utf-8")


if __name__ == "__main__":
    print(
        calculate_key(
            "TEST_SECRET_ACCESS_KEY",
            "us-east-1"
        )
    )
