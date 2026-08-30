# Kernel extracted from:
# vhive-serverless/vSwarm
# benchmarks/fibonacci/python/server.py

def fibonacci(num: int) -> int:
    num1: int = 0
    num2: int = 1
    total: int = 0

    for i in range(num):
        total = num1 + num2
        num1 = num2
        num2 = total

    return num1


def faas_kernel(n: int) -> int:
    # First real-FaaS verification domain.
    if n < 0:
        return -1
    if n > 20:
        return -1

    return fibonacci(n)
