import hashlib

digest: str = hashlib.sha256(b"abc").hexdigest()

assert digest == (
    "ba7816bf8f01cfea414140de5dae2223"
    "b00361a396177a9cb410ff61f20015ad"
)
