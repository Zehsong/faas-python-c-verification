import hashlib
import hmac

digest: str = hmac.new(
    b"key",
    b"abc",
    hashlib.sha256
).hexdigest()

assert digest == (
    "9c196e32dc0175f86f4b1cb89289d661"
    "9de6bee699e4c378e68309ed97a1a6ac"
)
