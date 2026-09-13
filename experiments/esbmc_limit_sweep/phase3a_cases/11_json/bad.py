import json

obj = json.loads('{"x": 7, "y": 9}')

assert obj["x"] == 8
