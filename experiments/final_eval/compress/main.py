#!/usr/bin/env python3
"""Portable CLI for vSwarm's whole-file Python compression core."""

from __future__ import annotations

import sys
import zlib


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} <input> <zlib-output>")
    source, destination = sys.argv[1:]
    with open(source, "rb") as inp:
        data = inp.read()
    compressed = zlib.compress(data, zlib.Z_BEST_COMPRESSION)
    with open(destination, "wb") as out:
        out.write(compressed)


if __name__ == "__main__":
    main()

