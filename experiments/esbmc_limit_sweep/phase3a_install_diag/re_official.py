import re

assert not re.fullmatch(r"\d+", "123abc")
assert re.fullmatch(r"\d+", "123")
assert not re.fullmatch(r"[a-z]+", "abc123")
assert re.fullmatch(r"[a-z]+", "abc")
