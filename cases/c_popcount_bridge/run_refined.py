#!/usr/bin/env python3
"""Refine the unresolved middle edge by changing one byte implementation at a time."""
import sys
import run_bridge as bridge


def protocol():
    return dict(nodes=(bridge.NODES[0], bridge.NODES[1],
                       *(bridge.CASE / f'mixed_{n}.c' for n in (1, 2, 3)),
                       bridge.NODES[2], bridge.NODES[3]),
                label='POPCOUNT REFINED BRIDGE', guide='REFINED.md', prefix='refined-',
                title='Popcount：每次替换一个字节的六段证明链')


def main(argv=None):
    return bridge.main(argv, protocol=protocol())


if __name__ == '__main__':
    sys.exit(main())
