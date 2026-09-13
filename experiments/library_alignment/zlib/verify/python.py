def adler4(e0: int, e1: int, e2: int, e3: int) -> int:
    a = 1
    b = 0

    x = e0 & 255
    a = (a + x) % 65521
    b = (b + a) % 65521

    x = e1 & 255
    a = (a + x) % 65521
    b = (b + a) % 65521

    x = e2 & 255
    a = (a + x) % 65521
    b = (b + a) % 65521

    x = e3 & 255
    a = (a + x) % 65521
    b = (b + a) % 65521

    return (b << 16) | a
