#!/usr/bin/env python3
import argparse
import subprocess
import sys

# Preserve the original Python/C interval baseline; the cache-family adapter
# reuses its oracle while searching predicates over input and entry state.
if "--cache" in sys.argv[1:]:
    from find_cache_conditions import main
    sys.exit(main(sys.argv[1:]))

p = argparse.ArgumentParser()
p.add_argument("--python", required=True)
p.add_argument("--py-function", required=True)
p.add_argument("--c", required=True)
p.add_argument("--c-function", required=True)
p.add_argument("--param", action="append", required=True)
p.add_argument("--return", dest="ret", required=True)
p.add_argument("--search", required=True)
p.add_argument("--unwind", type=int, default=12)
p.add_argument("--timeout", type=int, default=60)
args = p.parse_args()

name, lo, hi = args.search.split(":")
lo, hi = int(lo), int(hi)

work = [(lo, hi)]
eq = []
neq = []
unknown = []
queries = 0

while work:
    a, b = work.pop(0)
    queries += 1

    cmd = [
        "./tools/verify-equiv/verify-equiv",
        "--python", args.python,
        "--py-function", args.py_function,
        "--c", args.c,
        "--c-function", args.c_function,
    ]

    for x in args.param:
        cmd += ["--param", x]

    cmd += [
        "--return", args.ret,
        "--domain", f"{name}:{a}:{b}",
        "--unwind", str(args.unwind),
        "--timeout", str(args.timeout),
    ]

    r = subprocess.run(cmd, stdout=subprocess.DEVNULL)

    if r.returncode == 0:
        print(f"[{a},{b}] -> EQ")
        eq.append((a, b))

    elif r.returncode == 1:
        if a == b:
            print(f"[{a},{b}] -> NEQ")
            neq.append(a)
        else:
            print(f"[{a},{b}] -> NEQ, split")
            m = (a + b) // 2
            work.append((a, m))
            work.append((m + 1, b))

    else:
        print(f"[{a},{b}] -> UNKNOWN")
        unknown.append((a, b))

eq.sort()
merged = []

for a, b in eq:
    if merged and a == merged[-1][1] + 1:
        merged[-1] = (merged[-1][0], b)
    else:
        merged.append((a, b))

print("\n=== RESULT ===")
print("queries:", queries)
print("EQ regions:", merged)
print("NEQ points:", sorted(neq))
print("UNKNOWN regions:", unknown)
